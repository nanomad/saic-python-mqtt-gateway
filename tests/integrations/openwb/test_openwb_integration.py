from __future__ import annotations

import datetime
import math
from typing import Any
import unittest
from unittest.mock import patch

from apscheduler.schedulers.blocking import BlockingScheduler
import pytest
from saic_ismart_client_ng.api.vehicle.schema import VinInfo

from configuration import Configuration
from integrations.openwb import ChargingStation, OpenWBIntegration
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
from vehicle import VehicleState
from vehicle_info import VehicleInfo

RANGE_TOPIC = "/mock/range"
CHARGE_STATE_TOPIC = "/mock/charge/state"
SOC_TOPIC = "/mock/soc/state"
SOC_TS_TOPIC = "/mock/soc/timestamp"
CHARGING_VALUE = "VehicleIsCharging"

FROZEN_TIME = datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)

# Constants for imported energy tests
BATTERY_CAPACITY_KWH = 64.0
CHARGE_POLLING_MIN_PERCENT = 1.0
ENERGY_PER_PERCENT = BATTERY_CAPACITY_KWH * 1000.0 / 100.0
ENERGY_THRESHOLD = math.ceil(CHARGE_POLLING_MIN_PERCENT * ENERGY_PER_PERCENT)


def _make_vehicle_state(publisher: MessageCapturingConsolePublisher) -> VehicleState:
    vin_info = VinInfo()
    vin_info.vin = VIN
    vehicle_info = VehicleInfo(vin_info, None)
    account_prefix = f"/vehicles/{VIN}"
    scheduler = BlockingScheduler()
    return VehicleState(publisher, scheduler, account_prefix, vehicle_info)


def _make_integration(
    publisher: MessageCapturingConsolePublisher,
    *,
    soc_topic: str | None = SOC_TOPIC,
    soc_ts_topic: str | None = SOC_TS_TOPIC,
) -> OpenWBIntegration:
    charging_station = ChargingStation(
        vin=VIN,
        charge_state_topic=CHARGE_STATE_TOPIC,
        charging_value=CHARGING_VALUE,
        soc_topic=soc_topic,
        soc_ts_topic=soc_ts_topic,
        range_topic=RANGE_TOPIC,
    )
    return OpenWBIntegration(
        charging_station=charging_station,
        publisher=publisher,
    )


class TestOpenWBIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        config = Configuration()
        config.anonymized_publishing = False
        self.publisher = MessageCapturingConsolePublisher(config)
        self.vehicle_state = _make_vehicle_state(self.publisher)
        self.openwb_integration = _make_integration(self.publisher)

    @patch("integrations.openwb.datetime")
    async def test_update_soc_with_no_bms_data(self, mock_datetime: Any) -> None:
        mock_datetime.datetime.now.return_value = FROZEN_TIME
        mock_datetime.UTC = datetime.UTC
        vehicle_status_resp = get_mock_vehicle_status_resp()
        result = self.vehicle_state.handle_vehicle_status(vehicle_status_resp)

        # Reset topics since we are only asserting the differences
        self.publisher.map.clear()

        self.openwb_integration.update_openwb(vehicle_status=result, charge_status=None)
        self.assert_mqtt_topic(
            SOC_TOPIC,
            float(DRIVETRAIN_SOC_VEHICLE),
        )
        self.assert_mqtt_topic(
            SOC_TS_TOPIC,
            int(FROZEN_TIME.timestamp()),
        )
        self.assert_mqtt_topic(
            RANGE_TOPIC,
            DRIVETRAIN_RANGE_VEHICLE,
        )
        expected_topics = {
            SOC_TOPIC,
            SOC_TS_TOPIC,
            RANGE_TOPIC,
        }
        assert expected_topics == set(self.publisher.map.keys())
        mock_datetime.datetime.now.assert_called_with(tz=datetime.UTC)

    @patch("integrations.openwb.datetime")
    async def test_update_soc_with_bms_data(self, mock_datetime: Any) -> None:
        mock_datetime.datetime.now.return_value = FROZEN_TIME
        mock_datetime.UTC = datetime.UTC
        vehicle_status_resp = get_mock_vehicle_status_resp()
        chrg_mgmt_data_resp = get_mock_charge_management_data_resp()
        vehicle_status_resp_result = self.vehicle_state.handle_vehicle_status(
            vehicle_status_resp
        )
        chrg_mgmt_data_resp_result = self.vehicle_state.handle_charge_status(
            chrg_mgmt_data_resp
        )

        # Reset topics since we are only asserting the differences
        self.publisher.map.clear()

        self.openwb_integration.update_openwb(
            vehicle_status=vehicle_status_resp_result,
            charge_status=chrg_mgmt_data_resp_result,
        )

        self.assert_mqtt_topic(SOC_TOPIC, DRIVETRAIN_SOC_BMS)
        self.assert_mqtt_topic(
            RANGE_TOPIC,
            DRIVETRAIN_RANGE_BMS,
        )
        self.assert_mqtt_topic(
            SOC_TS_TOPIC,
            int(FROZEN_TIME.timestamp()),
        )
        expected_topics = {
            SOC_TOPIC,
            SOC_TS_TOPIC,
            RANGE_TOPIC,
        }
        assert expected_topics == set(self.publisher.map.keys())
        mock_datetime.datetime.now.assert_called_with(tz=datetime.UTC)

    async def test_no_soc_ts_topic_configured(self) -> None:
        """SoC timestamp is not published when socTsTopic is not configured."""
        integration = _make_integration(self.publisher, soc_ts_topic=None)
        vehicle_status_resp = get_mock_vehicle_status_resp()
        result = self.vehicle_state.handle_vehicle_status(vehicle_status_resp)

        self.publisher.map.clear()

        integration.update_openwb(vehicle_status=result, charge_status=None)
        expected_topics = {
            SOC_TOPIC,
            RANGE_TOPIC,
        }
        assert expected_topics == set(self.publisher.map.keys())

    async def test_no_soc_topic_skips_soc_ts(self) -> None:
        """SoC timestamp is not published when socTopic is not configured, even if socTsTopic is."""
        integration = _make_integration(
            self.publisher, soc_topic=None, soc_ts_topic=SOC_TS_TOPIC
        )
        vehicle_status_resp = get_mock_vehicle_status_resp()
        result = self.vehicle_state.handle_vehicle_status(vehicle_status_resp)

        self.publisher.map.clear()

        integration.update_openwb(vehicle_status=result, charge_status=None)
        expected_topics = {
            RANGE_TOPIC,
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


class TestImportedEnergyRefresh(unittest.TestCase):
    def setUp(self) -> None:
        config = Configuration()
        config.anonymized_publishing = False
        publisher = MessageCapturingConsolePublisher(config)
        self.integration = _make_integration(publisher)

    def _should_refresh(self, energy_wh: float) -> bool:
        return self.integration.should_refresh_by_imported_energy(
            imported_energy_wh=energy_wh,
            battery_capacity_kwh=BATTERY_CAPACITY_KWH,
            charge_polling_min_percent=CHARGE_POLLING_MIN_PERCENT,
        )

    def test_no_battery_capacity_returns_false(self) -> None:
        result = self.integration.should_refresh_by_imported_energy(
            imported_energy_wh=1000.0,
            battery_capacity_kwh=None,
            charge_polling_min_percent=CHARGE_POLLING_MIN_PERCENT,
        )
        assert not result

    def test_zero_battery_capacity_returns_false(self) -> None:
        result = self.integration.should_refresh_by_imported_energy(
            imported_energy_wh=1000.0,
            battery_capacity_kwh=0.0,
            charge_polling_min_percent=CHARGE_POLLING_MIN_PERCENT,
        )
        assert not result

    def test_negative_battery_capacity_returns_false(self) -> None:
        result = self.integration.should_refresh_by_imported_energy(
            imported_energy_wh=1000.0,
            battery_capacity_kwh=-1.0,
            charge_polling_min_percent=CHARGE_POLLING_MIN_PERCENT,
        )
        assert not result

    def test_zero_polling_percent_returns_false(self) -> None:
        result = self.integration.should_refresh_by_imported_energy(
            imported_energy_wh=1000.0,
            battery_capacity_kwh=BATTERY_CAPACITY_KWH,
            charge_polling_min_percent=0.0,
        )
        assert not result

    def test_first_call_initializes_threshold(self) -> None:
        assert not self._should_refresh(1000.0)

    def test_below_threshold_no_refresh(self) -> None:
        self._should_refresh(1000.0)  # initialize
        assert not self._should_refresh(1000.0 + ENERGY_THRESHOLD - 1)

    def test_at_threshold_triggers_refresh(self) -> None:
        self._should_refresh(1000.0)  # initialize
        assert self._should_refresh(1000.0 + ENERGY_THRESHOLD)

    def test_next_threshold_after_refresh(self) -> None:
        self._should_refresh(1000.0)  # initialize
        energy_at_first_refresh = 1000.0 + ENERGY_THRESHOLD
        assert self._should_refresh(energy_at_first_refresh)
        # Should not refresh again immediately
        assert not self._should_refresh(energy_at_first_refresh + 1)
        # Should refresh at second threshold
        assert self._should_refresh(energy_at_first_refresh + ENERGY_THRESHOLD)

    def test_counter_reset_reinitializes(self) -> None:
        self._should_refresh(5000.0)  # initialize at 5kWh
        assert self._should_refresh(5000.0 + ENERGY_THRESHOLD)  # first refresh
        # Counter resets to 0 (e.g. daily reset)
        assert not self._should_refresh(0.0)
        # New threshold from 0
        assert self._should_refresh(float(ENERGY_THRESHOLD))

    def test_unknown_charger_state_allows_energy_check(self) -> None:
        """Energy check proceeds when charger connection state is unknown (no topic configured)."""
        assert not self._should_refresh(1000.0)  # initializes
        assert self._should_refresh(1000.0 + ENERGY_THRESHOLD)  # triggers

    def test_charger_disconnected_skips_check(self) -> None:
        self.integration.set_charger_connection_state(False)
        assert not self._should_refresh(99999.0)

    def test_charger_reconnect_resets_state(self) -> None:
        self._should_refresh(1000.0)  # initialize
        self.integration.set_charger_connection_state(False)
        self.integration.set_charger_connection_state(True)
        # After reconnect, first call re-initializes (returns False)
        assert not self._should_refresh(0.0)
        # Then threshold works from new baseline
        assert self._should_refresh(float(ENERGY_THRESHOLD))
