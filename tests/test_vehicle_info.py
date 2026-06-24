from __future__ import annotations

import pytest
from saic_ismart_client_ng.api.vehicle.schema import VehicleModelConfiguration, VinInfo

from tests.common_mocks import VIN
from vehicle_info import VehicleInfo


def _make_vehicle_info(
    series: str,
    model: str = "",
    btype: str | None = None,
    custom_battery_capacity: float | None = None,
) -> VehicleInfo:
    vin_info = VinInfo()
    vin_info.vin = VIN
    vin_info.series = series
    vin_info.modelName = model
    if btype is not None:
        vin_info.vehicleModelConfiguration = [
            VehicleModelConfiguration("BType", "Battery", btype),
        ]
    return VehicleInfo(vin_info, custom_battery_capacity)


class TestMg4RealBatteryCapacity:
    def test_mg4_lfp_51kwh(self) -> None:
        assert _make_vehicle_info("EH32 S", btype=None).real_battery_capacity == 51.0

    def test_mg4_nmc_64kwh(self) -> None:
        assert _make_vehicle_info("EH32 S", btype="1").real_battery_capacity == 64.0

    def test_mg4_trophy_extended_range_77kwh(self) -> None:
        assert _make_vehicle_info("EH32 S", model="EH32 X3").real_battery_capacity == 77.0


class TestMg4UrbanRealBatteryCapacity:
    def test_standard_range_43kwh(self) -> None:
        assert _make_vehicle_info("AH4EM L", model="MG4 EV URBAN").real_battery_capacity == 43.0

    def test_unknown_urban_variant_returns_none(self) -> None:
        # 54kWh Long Range series code not yet confirmed — should return None until a
        # real device report is available so the user is prompted to set a custom capacity.
        assert _make_vehicle_info("AH4EM LL", model="MG4 EV URBAN LR").real_battery_capacity is None

    def test_custom_capacity_overrides_lookup(self) -> None:
        vi = _make_vehicle_info("AH4EM L", model="MG4 EV URBAN", custom_battery_capacity=54.0)
        assert vi.real_battery_capacity == 54.0
