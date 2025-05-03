from __future__ import annotations

from typing import Any
import unittest

from apscheduler.schedulers.blocking import BlockingScheduler
import pytest

from saic_ismart_client_ng.api.vehicle.schema import VinInfo
from saic_python_mqtt_gateway import mqtt_topics
from saic_python_mqtt_gateway.configuration import Configuration
from saic_python_mqtt_gateway.model import VehicleInfo
from saic_python_mqtt_gateway.state.vehicle import VehicleState
from saic_python_mqtt_gateway.status_publisher.charge.chrg_mgmt_data_resp import (
    ChrgMgmtDataRespPublisher,
)
from saic_python_mqtt_gateway.status_publisher.vehicle.vehicle_status_resp import (
    VehicleStatusRespPublisher,
)
from tests.common_mocks import (
    DRIVETRAIN_RANGE_BMS,
    DRIVETRAIN_RANGE_VEHICLE,
    DRIVETRAIN_SOC_BMS,
    DRIVETRAIN_SOC_VEHICLE,
    VIN,
    get_mock_charge_management_data_resp,
    get_mock_vehicle_status_resp,
)
from tests.mocks import MessageCapturingConsolePublisher


class TestVehicleState(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        config = Configuration()
        config.anonymized_publishing = False
        self.publisher = MessageCapturingConsolePublisher(config)
        vin_info = VinInfo()
        vin_info.vin = VIN
        vehicle_info = VehicleInfo(vin_info, None)
        account_prefix = f"/vehicles/{VIN}"
        scheduler = BlockingScheduler()
        self.vehicle_state = VehicleState(
            self.publisher, scheduler, account_prefix, vehicle_info
        )
        self.vehicle_state_processor = VehicleStatusRespPublisher(
            vehicle_info, self.publisher, account_prefix
        )
        self.charge_state_processor = ChrgMgmtDataRespPublisher(
            vehicle_info, self.publisher, account_prefix
        )

    async def test_update_soc_with_no_bms_data(self) -> None:
        vehicle_status_resp = get_mock_vehicle_status_resp()
        result = self.vehicle_state_processor.on_vehicle_status_resp(
            vehicle_status_resp
        )

        # Reset topics since we are only asserting the differences
        self.publisher.map.clear()

        self.vehicle_state.update_data_conflicting_in_vehicle_and_bms(
            vehicle_status=result, charge_status=None
        )
        self.assert_mqtt_topic(
            TestVehicleState.get_topic(mqtt_topics.DRIVETRAIN_SOC),
            DRIVETRAIN_SOC_VEHICLE,
        )
        self.assert_mqtt_topic(
            TestVehicleState.get_topic(mqtt_topics.DRIVETRAIN_RANGE),
            DRIVETRAIN_RANGE_VEHICLE,
        )
        self.assert_mqtt_topic(
            TestVehicleState.get_topic(mqtt_topics.DRIVETRAIN_HV_BATTERY_ACTIVE), True
        )
        expected_topics = {
            "/vehicles/vin10000000000000/drivetrain/hvBatteryActive",
            "/vehicles/vin10000000000000/refresh/lastActivity",
            "/vehicles/vin10000000000000/drivetrain/soc",
            "/vehicles/vin10000000000000/drivetrain/range",
        }
        assert expected_topics == set(self.publisher.map.keys())

    async def test_update_soc_with_bms_data(self) -> None:
        vehicle_status_resp = get_mock_vehicle_status_resp()
        chrg_mgmt_data_resp = get_mock_charge_management_data_resp()
        vehicle_status_resp_result = (
            self.vehicle_state_processor.on_vehicle_status_resp(vehicle_status_resp)
        )
        chrg_mgmt_data_resp_result = self.charge_state_processor.on_chrg_mgmt_data_resp(
            chrg_mgmt_data_resp
        )

        # Reset topics since we are only asserting the differences
        self.publisher.map.clear()

        self.vehicle_state.update_data_conflicting_in_vehicle_and_bms(
            vehicle_status=vehicle_status_resp_result,
            charge_status=chrg_mgmt_data_resp_result,
        )
        self.assert_mqtt_topic(
            TestVehicleState.get_topic(mqtt_topics.DRIVETRAIN_SOC), DRIVETRAIN_SOC_BMS
        )
        self.assert_mqtt_topic(
            TestVehicleState.get_topic(mqtt_topics.DRIVETRAIN_RANGE),
            DRIVETRAIN_RANGE_BMS,
        )
        self.assert_mqtt_topic(
            TestVehicleState.get_topic(mqtt_topics.DRIVETRAIN_HV_BATTERY_ACTIVE), True
        )
        expected_topics = {
            "/vehicles/vin10000000000000/drivetrain/hvBatteryActive",
            "/vehicles/vin10000000000000/refresh/lastActivity",
            "/vehicles/vin10000000000000/drivetrain/soc",
            "/vehicles/vin10000000000000/drivetrain/range",
        }
        assert expected_topics == set(self.publisher.map.keys())

    def assert_mqtt_topic(self, topic: str, value: Any) -> None:
        mqtt_map = self.publisher.map
        if topic in mqtt_map:
            if isinstance(value, float) or isinstance(mqtt_map[topic], float):
                assert value == pytest.approx(mqtt_map[topic], abs=0.1)
            else:
                assert value == mqtt_map[topic]
        else:
            self.fail(f"MQTT map does not contain topic {topic}")

    @staticmethod
    def get_topic(sub_topic: str) -> str:
        return f"/vehicles/{VIN}/{sub_topic}"
