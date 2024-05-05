import json
import logging
from typing import List, override, Tuple, Any

from saic_ismart_client_ng.api.vehicle import VehicleStatusResp
from saic_ismart_client_ng.api.vehicle.schema import BasicVehicleStatus
from saic_ismart_client_ng.api.vehicle_charging import ChrgMgmtDataResp
from saic_ismart_client_ng.api.vehicle_charging.schema import RvsChargeStatus

from configuration import Configuration
from integrations import SaicMqttGatewayIntegration
from integrations.openwb.model import ChargingStation
from publisher.core import MqttCommandListener, Publisher
from utils import value_in_range

LOG = logging.getLogger(__name__)

CHARGING_STATIONS_FILE = 'charging-stations.json'


def process_charging_stations_file(json_file: str) -> dict[str, ChargingStation]:
    result = dict()
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            for item in data:
                charge_state_topic = item['chargeStateTopic']
                charging_value = item['chargingValue']
                vin = item['vin']
                if 'socTopic' in item:
                    charging_station = ChargingStation(vin, charge_state_topic, charging_value, item['socTopic'])
                else:
                    charging_station = ChargingStation(vin, charge_state_topic, charging_value)
                if 'rangeTopic' in item:
                    charging_station.range_topic = item['rangeTopic']
                if 'chargerConnectedTopic' in item:
                    charging_station.connected_topic = item['chargerConnectedTopic']
                if 'chargerConnectedValue' in item:
                    charging_station.connected_value = item['chargerConnectedValue']
                result[vin] = charging_station
    except FileNotFoundError:
        LOG.warning(f'File {json_file} does not exist')
    except json.JSONDecodeError as e:
        LOG.exception(f'Reading {json_file} failed', exc_info=e)
    return result


class OpenWBIntegration(SaicMqttGatewayIntegration):
    def __init__(self, *, configuration: Configuration, publisher: Publisher, listener: MqttCommandListener):
        super().__init__(name='OpenWB', configuration=configuration, publisher=publisher, listener=listener)
        charging_stations_file = self.configuration.charging_stations_file or f'./{CHARGING_STATIONS_FILE}'
        self.__charging_stations_by_vin = process_charging_stations_file(charging_stations_file)
        self.__vin_by_charge_state_topic: dict[str, str] = {}
        self.__last_charge_state_by_vin: [str, str] = {}
        self.__vin_by_charger_connected_topic: dict[str, str] = {}
        for charging_station in self.__charging_stations_by_vin.values():
            LOG.debug(f'Subscribing to MQTT topic {charging_station.charge_state_topic}')
            self.__vin_by_charge_state_topic[charging_station.charge_state_topic] = charging_station.vin
            if charging_station.connected_topic:
                LOG.debug(f'Subscribing to MQTT topic {charging_station.connected_topic}')
                self.__vin_by_charger_connected_topic[charging_station.connected_topic] = charging_station.vin

    @override
    async def on_raw_mqtt_message(
            self, *,
            topic: str,
            payload: str
    ):
        handled = False
        if topic in self.__vin_by_charge_state_topic:
            LOG.debug(f'Received message over topic {topic} with payload {payload}')
            handled = True
            vin = self.__vin_by_charge_state_topic[topic]
            charging_station = self.__charging_stations_by_vin[vin]
            if self.__should_force_refresh(payload, charging_station):
                LOG.info(f'Vehicle with vin {vin} is charging. Setting refresh mode to force')
                if self.listener is not None:
                    await self.listener.on_charging_detected(vin)
        elif topic in self.__vin_by_charger_connected_topic:
            LOG.debug(f'Received message over topic {topic} with payload {payload}')
            handled = True
            vin = self.__vin_by_charger_connected_topic[topic]
            charging_station = self.__charging_stations_by_vin[vin]
            if payload == charging_station.connected_value:
                LOG.debug(f'Vehicle with vin {vin} is connected to its charging station')
            else:
                LOG.debug(f'Vehicle with vin {vin} is disconnected from its charging station')

        return handled, '' if handled else f'Topic {topic} not supported by OpenWB integration'

    async def on_full_refresh_done(
            self,
            *,
            vin: str,
            vehicle_status: VehicleStatusResp,
            charge_info: ChrgMgmtDataResp
    ) -> Tuple[bool, Any | None]:
        handled = False
        charging_station = self.__get_charging_station(vin)
        if charging_station:
            if (
                    charging_station.soc_topic
                    and charge_info
                    and charge_info.chrgMgmtData
                    and charge_info.chrgMgmtData.bmsPackSOCDsp is not None
            ):
                soc = charge_info.chrgMgmtData.bmsPackSOCDsp / 10.0
                if soc <= 100.0:
                    self.publisher.publish_int(charging_station.soc_topic, int(soc), True)
                    handled = True
            if charging_station.range_topic:
                electric_range = self.__extract_electric_range(
                    basic_vehicle_status=vehicle_status.basicVehicleStatus if vehicle_status is not None else None,
                    charge_status=charge_info.rvsChargeStatus if charge_info is not None else None
                )
                if electric_range is not None:
                    self.publisher.publish_float(charging_station.range_topic, electric_range, True)
                    handled = True
        return handled, '' if handled else f'Car with vin {vin} does not have an OpenWB configuration'

    @override
    def additional_mqtt_topics(self) -> List[str]:
        return list(self.__vin_by_charge_state_topic.keys()) + list(self.__vin_by_charge_state_topic.keys())

    def __should_force_refresh(self, current_charging_value: str, charging_station: ChargingStation):
        vin = charging_station.vin
        last_charging_value: str | None = None
        if vin in self.__last_charge_state_by_vin:
            last_charging_value = self.__last_charge_state_by_vin[vin]
        self.__last_charge_state_by_vin[vin] = current_charging_value

        if last_charging_value:
            if last_charging_value == current_charging_value:
                LOG.debug('Last charging value equals current charging value. No refresh needed.')
                return False
            else:
                LOG.info(f'Charging value has changed from {last_charging_value} to {current_charging_value}.')
                return True
        else:
            return True

    def __get_charging_station(self, vin) -> ChargingStation | None:
        if vin in self.__charging_stations_by_vin:
            return self.__charging_stations_by_vin[vin]
        else:
            return None

    def __extract_electric_range(
            self,
            basic_vehicle_status: BasicVehicleStatus | None,
            charge_status: RvsChargeStatus | None
    ) -> float | None:

        range_elec_vehicle = 0.0
        if basic_vehicle_status is not None:
            range_elec_vehicle = self.__parse_electric_range(raw_value=basic_vehicle_status.fuelRangeElec)

        range_elec_bms = 0.0
        if charge_status is not None:
            range_elec_bms = self.__parse_electric_range(raw_value=charge_status.fuelRangeElec)

        range_elec = max(range_elec_vehicle, range_elec_bms)
        if range_elec > 0:
            return range_elec

        return None

    @staticmethod
    def __parse_electric_range(raw_value) -> float:
        if value_in_range(raw_value, 1, 65535):
            return float(raw_value) / 10.0
        return 0.0
