from __future__ import annotations

import unittest

import pytest
from saic_ismart_client_ng.api.vehicle.schema import VehicleModelConfiguration, VinInfo
from saic_ismart_client_ng.api.vehicle_charging.schema import RvsChargeStatus

from configuration import Configuration
from status_publisher.charge.rvs_charge_status import RvsChargeStatusPublisher
from tests.common_mocks import VIN
from tests.mocks import MessageCapturingConsolePublisher
from vehicle_info import VehicleInfo

# EH32 S with BType=1 → real_battery_capacity = 64.0, raw=72.5 kWh
REAL_CAPACITY = 64.0
RAW_CAPACITY = 72.5
CORRECTION = REAL_CAPACITY / RAW_CAPACITY


def _make_publisher() -> tuple[
    RvsChargeStatusPublisher, MessageCapturingConsolePublisher
]:
    config = Configuration()
    config.anonymized_publishing = False
    pub = MessageCapturingConsolePublisher(config)
    vin_info = VinInfo()
    vin_info.vin = VIN
    vin_info.series = "EH32 S"
    vin_info.modelName = "MG4 Electric"
    vin_info.modelYear = "2022"
    vin_info.vehicleModelConfiguration = [
        VehicleModelConfiguration("BType", "Battery", "1"),
    ]
    vehicle_info = VehicleInfo(vin_info, None)
    return RvsChargeStatusPublisher(vehicle_info, pub, f"/vehicles/{VIN}"), pub


class TestRvsChargeStatusSocKwh(unittest.TestCase):
    def setUp(self) -> None:
        self.publisher, _ = _make_publisher()

    def test_soc_kwh_present_when_realtime_power_set(self) -> None:
        charge_status = RvsChargeStatus(
            realtimePower=int((42.0 / CORRECTION) * 10),
            totalBatteryCapacity=int(RAW_CAPACITY * 10),
        )
        result = self.publisher.publish(charge_status)

        assert result.soc_kwh is not None
        assert result.soc_kwh == pytest.approx(42.0, abs=0.1)

    def test_soc_kwh_none_when_realtime_power_is_none(self) -> None:
        charge_status = RvsChargeStatus(
            realtimePower=None,
            totalBatteryCapacity=int(RAW_CAPACITY * 10),
        )
        result = self.publisher.publish(charge_status)

        assert result.soc_kwh is None

    def test_soc_kwh_none_when_realtime_power_is_zero(self) -> None:
        charge_status = RvsChargeStatus(
            realtimePower=0,
            totalBatteryCapacity=int(RAW_CAPACITY * 10),
        )
        result = self.publisher.publish(charge_status)

        assert result.soc_kwh is None
