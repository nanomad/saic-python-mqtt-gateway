from abc import ABC
from typing import Tuple, Any, List

from saic_ismart_client_ng.api.vehicle import VehicleStatusResp
from saic_ismart_client_ng.api.vehicle_charging import ChrgMgmtDataResp

from configuration import Configuration
from publisher.core import Publisher
from publisher.core import MqttCommandListener


class SaicMqttGatewayIntegrationException(Exception):
    pass


class SaicMqttGatewayIntegration(ABC):

    def __init__(
            self, *,
            name: str,
            configuration: Configuration,
            publisher: Publisher,
            listener: MqttCommandListener,
    ):
        self.__name = name
        self.__configuration = configuration
        self.__publisher = publisher
        self.__listener = listener

    async def on_full_refresh_done(
            self,
            *,
            vin: str,
            vehicle_status: VehicleStatusResp,
            charge_info: ChrgMgmtDataResp
    ) -> Tuple[bool, Any | None]:
        return False, 'Not supported'

    async def on_raw_mqtt_message(
            self,
            topic: str,
            payload: str
    ) -> Tuple[bool, Any | None]:
        return False, 'Not supported'

    async def on_mqtt_command(
            self,
            *,
            vin: str,
            topic: str,
            payload: str
    ) -> Tuple[bool, Any | None]:
        return False, 'Not supported'

    @property
    def additional_mqtt_topics(self) -> List[str]:
        return []

    @property
    def name(self):
        return str(self.__name).lower()

    @property
    def configuration(self) -> Configuration:
        return self.__configuration

    @property
    def publisher(self):
        return self.__publisher

    @property
    def listener(self):
        return self.__listener
