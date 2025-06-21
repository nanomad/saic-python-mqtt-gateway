from __future__ import annotations

import logging
from typing import override

from handlers.command.base import (
    RESULT_REFRESH_AND_CLEAR,
    BooleanCommandHandler,
    CommandProcessingResult,
)
from mqtt_topics import DRIVETRAIN_CHARGING_SET

LOG = logging.getLogger(__name__)


class DrivetrainChargingCommand(BooleanCommandHandler[None]):
    @classmethod
    @override
    def topic(cls) -> str:
        return DRIVETRAIN_CHARGING_SET

    @override
    async def handle_true(self) -> None:
        LOG.info("Charging will be started")
        await self.saic_api.control_charging(self.vin, stop_charging=False)

    @override
    async def handle_false(self) -> None:
        LOG.info("Charging will be stopped")
        await self.saic_api.control_charging(self.vin, stop_charging=True)

    @override
    async def _get_action_result(self, _action_result: None) -> CommandProcessingResult:
        return RESULT_REFRESH_AND_CLEAR
