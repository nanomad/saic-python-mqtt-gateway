from __future__ import annotations

import logging
from typing import override

from handlers.command.base import (
    RESULT_REFRESH_AND_CLEAR,
    BooleanCommandHandler,
    CommandProcessingResult,
)
from mqtt_topics import DRIVETRAIN_HV_BATTERY_ACTIVE_SET

LOG = logging.getLogger(__name__)


class DrivetrainHVBatteryActiveCommand(BooleanCommandHandler[None]):
    @classmethod
    @override
    def topic(cls) -> str:
        return DRIVETRAIN_HV_BATTERY_ACTIVE_SET

    @override
    async def handle_true(self) -> None:
        LOG.info("HV battery is now active")
        self.vehicle_state.hv_battery_active = True

    @override
    async def handle_false(self) -> None:
        LOG.info("HV battery is now inactive")
        self.vehicle_state.hv_battery_active = False

    @override
    async def _get_action_result(self, _action_result: None) -> CommandProcessingResult:
        return RESULT_REFRESH_AND_CLEAR
