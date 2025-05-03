from __future__ import annotations

from typing import Any
import unittest
from unittest.mock import patch

from apscheduler.schedulers.blocking import BlockingScheduler
import pytest

from saic_ismart_client_ng import SaicApi
from saic_ismart_client_ng.api.vehicle.schema import (
    VehicleModelConfiguration,
    VinInfo,
)
from saic_ismart_client_ng.model import SaicApiConfiguration
from saic_python_mqtt_gateway import mqtt_topics
from saic_python_mqtt_gateway.configuration import Configuration
from saic_python_mqtt_gateway.handlers.relogin import ReloginHandler
from saic_python_mqtt_gateway.handlers.vehicle import VehicleHandler
from saic_python_mqtt_gateway.model import VehicleInfo
from tests.common_mocks import (
    BMS_CHARGE_STATUS,
    CLIMATE_EXTERIOR_TEMPERATURE,
    CLIMATE_INTERIOR_TEMPERATURE,
    DOORS_BONNET,
    DOORS_BOOT,
    DOORS_DRIVER,
    DOORS_LOCKED,
    DOORS_PASSENGER,
    DOORS_REAR_LEFT,
    DOORS_REAR_RIGHT,
    DRIVETRAIN_AUXILIARY_BATTERY_VOLTAGE,
    DRIVETRAIN_CHARGER_CONNECTED,
    DRIVETRAIN_CHARGING,
    DRIVETRAIN_CHARGING_CABLE_LOCK,
    DRIVETRAIN_CHARGING_TYPE,
    DRIVETRAIN_CURRENT,
    DRIVETRAIN_HYBRID_ELECTRICAL_RANGE,
    DRIVETRAIN_LAST_CHARGE_ENDING_POWER,
    DRIVETRAIN_MILEAGE,
    DRIVETRAIN_MILEAGE_OF_DAY,
    DRIVETRAIN_MILEAGE_SINCE_LAST_CHARGE,
    DRIVETRAIN_POWER,
    DRIVETRAIN_REMAINING_CHARGING_TIME,
    DRIVETRAIN_RUNNING,
    DRIVETRAIN_SOC_KWH,
    DRIVETRAIN_VOLTAGE,
    LIGHTS_DIPPED_BEAM,
    LIGHTS_MAIN_BEAM,
    LIGHTS_SIDE,
    LOCATION_ELEVATION,
    LOCATION_HEADING,
    LOCATION_LATITUDE,
    LOCATION_LONGITUDE,
    LOCATION_SPEED,
    REAL_TOTAL_BATTERY_CAPACITY,
    TYRES_FRONT_LEFT_PRESSURE,
    TYRES_FRONT_RIGHT_PRESSURE,
    TYRES_REAR_LEFT_PRESSURE,
    TYRES_REAR_RIGHT_PRESSURE,
    VIN,
    WINDOWS_DRIVER,
    WINDOWS_PASSENGER,
    WINDOWS_REAR_LEFT,
    WINDOWS_REAR_RIGHT,
    WINDOWS_SUN_ROOF,
    get_mock_charge_management_data_resp,
    get_mock_vehicle_status_resp,
)
from tests.mocks import MessageCapturingConsolePublisher


class TestVehicleHandler(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        config = Configuration()
        config.saic_user = "aaa@nowhere.org"
        config.anonymized_publishing = False
        self.saicapi = SaicApi(
            configuration=SaicApiConfiguration(
                username="aaa@nowhere.org",
                password="xxxxxxxxx",  # noqa: S106
            ),
            listener=None,
        )
        self.publisher = MessageCapturingConsolePublisher(config)
        vin_info = VinInfo()
        vin_info.vin = VIN
        vin_info.series = "EH32 S"
        vin_info.modelName = "MG4 Electric"
        vin_info.modelYear = "2022"
        vin_info.vehicleModelConfiguration = [
            VehicleModelConfiguration("BATTERY", "BATTERY", "1"),
            VehicleModelConfiguration("BType", "Battery", "1"),
        ]
        vehicle_info = VehicleInfo(vin_info, None)
        scheduler = BlockingScheduler()
        mock_relogin_handler = ReloginHandler(
            relogin_relay=30, api=self.saicapi, scheduler=scheduler
        )
        self.vehicle_handler = VehicleHandler(
            config,
            mock_relogin_handler,
            self.saicapi,
            self.publisher,
            vehicle_info,
            scheduler=scheduler,
        )

    async def test_update_vehicle_status(self) -> None:
        with patch.object(
            self.saicapi, "get_vehicle_status"
        ) as mock_get_vehicle_status:
            mock_get_vehicle_status.return_value = get_mock_vehicle_status_resp()
            await self.vehicle_handler.update_vehicle_status()

        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_RUNNING),
            DRIVETRAIN_RUNNING,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_AUXILIARY_BATTERY_VOLTAGE),
            DRIVETRAIN_AUXILIARY_BATTERY_VOLTAGE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_MILEAGE),
            DRIVETRAIN_MILEAGE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.CLIMATE_INTERIOR_TEMPERATURE),
            CLIMATE_INTERIOR_TEMPERATURE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.CLIMATE_EXTERIOR_TEMPERATURE),
            CLIMATE_EXTERIOR_TEMPERATURE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.CLIMATE_REMOTE_CLIMATE_STATE), "on"
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.CLIMATE_BACK_WINDOW_HEAT), "on"
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.LOCATION_SPEED), LOCATION_SPEED
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.LOCATION_HEADING), LOCATION_HEADING
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.LOCATION_LATITUDE),
            LOCATION_LATITUDE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.LOCATION_LONGITUDE),
            LOCATION_LONGITUDE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.LOCATION_ELEVATION),
            LOCATION_ELEVATION,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.WINDOWS_DRIVER), WINDOWS_DRIVER
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.WINDOWS_PASSENGER),
            WINDOWS_PASSENGER,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.WINDOWS_REAR_LEFT),
            WINDOWS_REAR_LEFT,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.WINDOWS_REAR_RIGHT),
            WINDOWS_REAR_RIGHT,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.WINDOWS_SUN_ROOF), WINDOWS_SUN_ROOF
        )
        self.assert_mqtt_topic(self.get_topic(mqtt_topics.DOORS_LOCKED), DOORS_LOCKED)
        self.assert_mqtt_topic(self.get_topic(mqtt_topics.DOORS_DRIVER), DOORS_DRIVER)
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DOORS_PASSENGER), DOORS_PASSENGER
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DOORS_REAR_LEFT), DOORS_REAR_LEFT
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DOORS_REAR_RIGHT), DOORS_REAR_RIGHT
        )
        self.assert_mqtt_topic(self.get_topic(mqtt_topics.DOORS_BONNET), DOORS_BONNET)
        self.assert_mqtt_topic(self.get_topic(mqtt_topics.DOORS_BOOT), DOORS_BOOT)
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.TYRES_FRONT_LEFT_PRESSURE),
            TYRES_FRONT_LEFT_PRESSURE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.TYRES_FRONT_RIGHT_PRESSURE),
            TYRES_FRONT_RIGHT_PRESSURE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.TYRES_REAR_LEFT_PRESSURE),
            TYRES_REAR_LEFT_PRESSURE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.TYRES_REAR_RIGHT_PRESSURE),
            TYRES_REAR_RIGHT_PRESSURE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.LIGHTS_MAIN_BEAM), LIGHTS_MAIN_BEAM
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.LIGHTS_DIPPED_BEAM),
            LIGHTS_DIPPED_BEAM,
        )
        self.assert_mqtt_topic(self.get_topic(mqtt_topics.LIGHTS_SIDE), LIGHTS_SIDE)
        expected_topics = {
            self.get_topic(mqtt_topics.DRIVETRAIN_RUNNING),
            self.get_topic(mqtt_topics.CLIMATE_INTERIOR_TEMPERATURE),
            self.get_topic(mqtt_topics.CLIMATE_EXTERIOR_TEMPERATURE),
            self.get_topic(mqtt_topics.DRIVETRAIN_AUXILIARY_BATTERY_VOLTAGE),
            self.get_topic(mqtt_topics.LOCATION_HEADING),
            self.get_topic(mqtt_topics.LOCATION_LATITUDE),
            self.get_topic(mqtt_topics.LOCATION_LONGITUDE),
            self.get_topic(mqtt_topics.LOCATION_ELEVATION),
            self.get_topic(mqtt_topics.LOCATION_POSITION),
            self.get_topic(mqtt_topics.LOCATION_SPEED),
            self.get_topic(mqtt_topics.WINDOWS_DRIVER),
            self.get_topic(mqtt_topics.WINDOWS_PASSENGER),
            self.get_topic(mqtt_topics.WINDOWS_REAR_LEFT),
            self.get_topic(mqtt_topics.WINDOWS_REAR_RIGHT),
            self.get_topic(mqtt_topics.WINDOWS_SUN_ROOF),
            self.get_topic(mqtt_topics.DOORS_LOCKED),
            self.get_topic(mqtt_topics.DOORS_DRIVER),
            self.get_topic(mqtt_topics.DOORS_PASSENGER),
            self.get_topic(mqtt_topics.DOORS_REAR_LEFT),
            self.get_topic(mqtt_topics.DOORS_REAR_RIGHT),
            self.get_topic(mqtt_topics.DOORS_BONNET),
            self.get_topic(mqtt_topics.DOORS_BOOT),
            self.get_topic(mqtt_topics.TYRES_FRONT_LEFT_PRESSURE),
            self.get_topic(mqtt_topics.TYRES_FRONT_RIGHT_PRESSURE),
            self.get_topic(mqtt_topics.TYRES_REAR_LEFT_PRESSURE),
            self.get_topic(mqtt_topics.TYRES_REAR_RIGHT_PRESSURE),
            self.get_topic(mqtt_topics.LIGHTS_MAIN_BEAM),
            self.get_topic(mqtt_topics.LIGHTS_DIPPED_BEAM),
            self.get_topic(mqtt_topics.LIGHTS_SIDE),
            self.get_topic(mqtt_topics.CLIMATE_REMOTE_CLIMATE_STATE),
            self.get_topic(mqtt_topics.CLIMATE_BACK_WINDOW_HEAT),
            self.get_topic(mqtt_topics.CLIMATE_HEATED_SEATS_FRONT_LEFT_LEVEL),
            self.get_topic(mqtt_topics.CLIMATE_HEATED_SEATS_FRONT_RIGHT_LEVEL),
            self.get_topic(mqtt_topics.DRIVETRAIN_MILEAGE),
            self.get_topic(mqtt_topics.REFRESH_LAST_VEHICLE_STATE),
        }
        assert expected_topics == set(self.publisher.map.keys())

    async def test_update_charge_status(self) -> None:
        with patch.object(
            self.saicapi, "get_vehicle_charging_management_data"
        ) as mock_get_vehicle_charging_management_data:
            mock_get_vehicle_charging_management_data.return_value = (
                get_mock_charge_management_data_resp()
            )
            await self.vehicle_handler.update_charge_status()

        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_CHARGING),
            DRIVETRAIN_CHARGING,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_CURRENT),
            DRIVETRAIN_CURRENT,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_VOLTAGE),
            DRIVETRAIN_VOLTAGE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_POWER), DRIVETRAIN_POWER
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_HYBRID_ELECTRICAL_RANGE),
            DRIVETRAIN_HYBRID_ELECTRICAL_RANGE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_MILEAGE_OF_DAY),
            DRIVETRAIN_MILEAGE_OF_DAY,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_MILEAGE_SINCE_LAST_CHARGE),
            DRIVETRAIN_MILEAGE_SINCE_LAST_CHARGE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_SOC_KWH),
            DRIVETRAIN_SOC_KWH,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_CHARGING_TYPE),
            DRIVETRAIN_CHARGING_TYPE,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_CHARGER_CONNECTED),
            DRIVETRAIN_CHARGER_CONNECTED,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_REMAINING_CHARGING_TIME),
            DRIVETRAIN_REMAINING_CHARGING_TIME,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_LAST_CHARGE_ENDING_POWER),
            DRIVETRAIN_LAST_CHARGE_ENDING_POWER,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_TOTAL_BATTERY_CAPACITY),
            REAL_TOTAL_BATTERY_CAPACITY,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.DRIVETRAIN_CHARGING_CABLE_LOCK),
            DRIVETRAIN_CHARGING_CABLE_LOCK,
        )
        self.assert_mqtt_topic(
            self.get_topic(mqtt_topics.BMS_CHARGE_STATUS),
            BMS_CHARGE_STATUS,
        )
        expected_topics = {
            self.get_topic(mqtt_topics.DRIVETRAIN_CHARGING),
            self.get_topic(mqtt_topics.DRIVETRAIN_CURRENT),
            self.get_topic(mqtt_topics.DRIVETRAIN_VOLTAGE),
            self.get_topic(mqtt_topics.DRIVETRAIN_POWER),
            self.get_topic(mqtt_topics.OBC_CURRENT),
            self.get_topic(mqtt_topics.OBC_VOLTAGE),
            self.get_topic(mqtt_topics.DRIVETRAIN_HYBRID_ELECTRICAL_RANGE),
            self.get_topic(mqtt_topics.DRIVETRAIN_MILEAGE_OF_DAY),
            self.get_topic(mqtt_topics.DRIVETRAIN_MILEAGE_SINCE_LAST_CHARGE),
            self.get_topic(mqtt_topics.DRIVETRAIN_CHARGING_TYPE),
            self.get_topic(mqtt_topics.DRIVETRAIN_CHARGER_CONNECTED),
            self.get_topic(mqtt_topics.DRIVETRAIN_REMAINING_CHARGING_TIME),
            self.get_topic(mqtt_topics.REFRESH_LAST_CHARGE_STATE),
            self.get_topic(mqtt_topics.DRIVETRAIN_TOTAL_BATTERY_CAPACITY),
            self.get_topic(mqtt_topics.DRIVETRAIN_SOC_KWH),
            self.get_topic(mqtt_topics.DRIVETRAIN_LAST_CHARGE_ENDING_POWER),
            self.get_topic(mqtt_topics.DRIVETRAIN_BATTERY_HEATING),
            self.get_topic(mqtt_topics.DRIVETRAIN_CHARGING_CABLE_LOCK),
            self.get_topic(mqtt_topics.BMS_CHARGE_STATUS),
            self.get_topic(mqtt_topics.REFRESH_PERIOD_CHARGING),
        }
        assert expected_topics == set(self.publisher.map.keys())

    # Note: The closer the decorator is to the function definition, the earlier it is in the parameter list
    async def test_should_not_publish_same_data_twice(self) -> None:
        with patch.object(
            self.saicapi, "get_vehicle_charging_management_data"
        ) as mock_get_vehicle_charging_management_data:
            mock_get_vehicle_charging_management_data.return_value = (
                get_mock_charge_management_data_resp()
            )
            with patch.object(
                self.saicapi, "get_vehicle_status"
            ) as mock_get_vehicle_status:
                mock_get_vehicle_status.return_value = get_mock_vehicle_status_resp()

                await self.vehicle_handler.update_vehicle_status()
                vehicle_mqtt_map = dict(self.publisher.map.items())
                self.publisher.map.clear()

                await self.vehicle_handler.update_charge_status()
                charge_data_mqtt_map = dict(self.publisher.map.items())
                self.publisher.map.clear()

        common_data = set(vehicle_mqtt_map.keys()).intersection(
            set(charge_data_mqtt_map.keys())
        )

        assert len(common_data) == 0, (
            f"Some topics have been published from both car state and BMS state: {common_data!s}"
        )

    def assert_mqtt_topic(self, topic: str, value: Any) -> None:
        mqtt_map = self.publisher.map
        if topic in mqtt_map:
            if isinstance(value, float) or isinstance(mqtt_map[topic], float):
                assert value == pytest.approx(mqtt_map[topic], abs=0.1)
            else:
                assert value == mqtt_map[topic]
        else:
            self.fail(f"MQTT does not contain topic {topic}")

    def get_topic(self, sub_topic: str) -> str:
        return f"{self.vehicle_handler.vehicle_prefix}/{sub_topic}"
