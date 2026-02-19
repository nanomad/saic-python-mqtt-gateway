from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, MagicMock

from saic_ismart_client_ng.api.vehicle.schema import VehicleModelConfiguration, VinInfo
from saic_ismart_client_ng.api.vehicle_charging import TargetBatteryCode

from handlers.command.base import RESULT_DO_NOTHING, RESULT_REFRESH_ONLY
from handlers.command.drivetrain.drivetrain_charging_schedule import (
    DrivetrainChargingScheduleCommand,
)
from handlers.command.drivetrain.drivetrain_soc_target import DrivetrainSoCTargetCommand
from vehicle_info import VehicleInfo


def _make_vehicle_state(*, supports_target_soc: bool) -> MagicMock:
    """Create a minimal mock VehicleState with the desired supports_target_soc flag."""
    configurations = []
    if supports_target_soc:
        configurations.append(
            VehicleModelConfiguration(itemCode="BType", itemValue="1")
        )
    vin_info = VinInfo()
    vin_info.vin = "vin_test_000000000"
    vin_info.vehicleModelConfiguration = configurations
    vehicle_info = VehicleInfo(vin_info, None)

    vehicle_state = MagicMock()
    vehicle_state.vehicle = vehicle_info
    vehicle_state.vin = vehicle_info.vin
    return vehicle_state


class TestDrivetrainSoCTargetGuard(unittest.IsolatedAsyncioTestCase):
    async def test_reject_target_soc_when_unsupported(self) -> None:
        vehicle_state = _make_vehicle_state(supports_target_soc=False)
        saic_api = AsyncMock()
        handler = DrivetrainSoCTargetCommand(saic_api, vehicle_state)

        result = await handler.handle("80")

        assert result == RESULT_DO_NOTHING
        saic_api.set_target_battery_soc.assert_not_called()

    async def test_allow_target_soc_when_supported(self) -> None:
        vehicle_state = _make_vehicle_state(supports_target_soc=True)
        saic_api = AsyncMock()
        handler = DrivetrainSoCTargetCommand(saic_api, vehicle_state)

        result = await handler.handle("80")

        assert result == RESULT_REFRESH_ONLY
        saic_api.set_target_battery_soc.assert_called_once_with(
            vehicle_state.vin, target_soc=TargetBatteryCode.P_80
        )


class TestDrivetrainChargingScheduleGuard(unittest.IsolatedAsyncioTestCase):
    async def test_reject_until_configured_soc_when_unsupported(self) -> None:
        vehicle_state = _make_vehicle_state(supports_target_soc=False)
        saic_api = AsyncMock()
        handler = DrivetrainChargingScheduleCommand(saic_api, vehicle_state)

        payload = json.dumps(
            {"startTime": "01:00", "endTime": "06:00", "mode": "UNTIL_CONFIGURED_SOC"}
        )
        result = await handler.handle(payload)

        assert result == RESULT_DO_NOTHING
        saic_api.set_schedule_charging.assert_not_called()

    async def test_allow_until_configured_soc_when_supported(self) -> None:
        vehicle_state = _make_vehicle_state(supports_target_soc=True)
        saic_api = AsyncMock()
        handler = DrivetrainChargingScheduleCommand(saic_api, vehicle_state)

        payload = json.dumps(
            {"startTime": "01:00", "endTime": "06:00", "mode": "UNTIL_CONFIGURED_SOC"}
        )
        result = await handler.handle(payload)

        assert result == RESULT_REFRESH_ONLY
        saic_api.set_schedule_charging.assert_called_once()

    async def test_allow_until_configured_time_regardless(self) -> None:
        """UNTIL_CONFIGURED_TIME should work even without SoC support."""
        vehicle_state = _make_vehicle_state(supports_target_soc=False)
        saic_api = AsyncMock()
        handler = DrivetrainChargingScheduleCommand(saic_api, vehicle_state)

        payload = json.dumps(
            {"startTime": "01:00", "endTime": "06:00", "mode": "UNTIL_CONFIGURED_TIME"}
        )
        result = await handler.handle(payload)

        assert result == RESULT_REFRESH_ONLY
        saic_api.set_schedule_charging.assert_called_once()

    async def test_allow_disabled_regardless(self) -> None:
        """DISABLED should work even without SoC support."""
        vehicle_state = _make_vehicle_state(supports_target_soc=False)
        saic_api = AsyncMock()
        handler = DrivetrainChargingScheduleCommand(saic_api, vehicle_state)

        payload = json.dumps(
            {"startTime": "01:00", "endTime": "06:00", "mode": "DISABLED"}
        )
        result = await handler.handle(payload)

        assert result == RESULT_REFRESH_ONLY
        saic_api.set_schedule_charging.assert_called_once()
