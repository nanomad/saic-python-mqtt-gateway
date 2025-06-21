from __future__ import annotations

from typing import override

from handlers.command.base import (
    RESULT_DO_NOTHING,
    CommandProcessingResult,
    PayloadConvertingCommandHandler,
)
import mqtt_topics
from vehicle import RefreshMode


class RefreshModeCommand(PayloadConvertingCommandHandler[RefreshMode]):
    @classmethod
    @override
    def topic(cls) -> str:
        return mqtt_topics.REFRESH_MODE_SET

    @staticmethod
    @override
    def convert_payload(payload: str) -> RefreshMode:
        normalized_payload = payload.strip().lower()
        return RefreshMode.get(normalized_payload)

    @override
    async def handle_typed_payload(
        self, refresh_mode: RefreshMode
    ) -> CommandProcessingResult:
        self.vehicle_state.set_refresh_mode(
            refresh_mode, "MQTT direct set refresh mode command execution"
        )
        return RESULT_DO_NOTHING
