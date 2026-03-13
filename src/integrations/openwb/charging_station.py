from __future__ import annotations

from typing import Final


class ChargingStation:
    def __init__(
        self,
        *,
        vin: str,
        charge_state_topic: str,
        charging_value: str,
        soc_topic: str | None = None,
        soc_ts_topic: str | None = None,
        range_topic: str | None = None,
        connected_topic: str | None = None,
        connected_value: str | None = None,
        imported_energy_topic: str | None = None,
    ) -> None:
        self.vin: Final = vin
        self.charge_state_topic: Final = charge_state_topic
        self.charging_value: Final = charging_value
        self.soc_topic: Final = soc_topic
        self.soc_ts_topic: Final = soc_ts_topic
        self.range_topic: Final = range_topic
        self.connected_topic: Final = connected_topic
        self.connected_value: Final = connected_value
        self.imported_energy_topic: Final = imported_energy_topic
