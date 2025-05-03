from __future__ import annotations

from enum import Enum, unique


@unique
class RefreshMode(Enum):
    FORCE = "force"
    OFF = "off"
    PERIODIC = "periodic"

    @staticmethod
    def get(mode: str) -> RefreshMode:
        return RefreshMode[mode.upper()]
