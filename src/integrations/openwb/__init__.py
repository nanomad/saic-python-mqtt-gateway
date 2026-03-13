from __future__ import annotations

import datetime
import logging
import math
from typing import TYPE_CHECKING

import extractors
from integrations.openwb.charging_station import ChargingStation

if TYPE_CHECKING:
    from publisher.core import Publisher
    from status_publisher.charge.chrg_mgmt_data_resp import (
        ChrgMgmtDataRespProcessingResult,
    )
    from status_publisher.vehicle.vehicle_status_resp import (
        VehicleStatusRespProcessingResult,
    )

LOG = logging.getLogger(__name__)

__all__ = [
    "ChargingStation",
    "OpenWBIntegration",
]


class OpenWBIntegration:
    def __init__(
        self, *, charging_station: ChargingStation, publisher: Publisher
    ) -> None:
        self.__charging_station = charging_station
        self.__publisher = publisher
        self.__charger_connected: bool | None = None
        self.__last_imported_energy_wh: float | None = None
        self.__next_refresh_energy_wh: float | None = None

    def update_openwb(
        self,
        vehicle_status: VehicleStatusRespProcessingResult,
        charge_status: ChrgMgmtDataRespProcessingResult | None,
    ) -> None:
        range_topic = self.__charging_station.range_topic
        electric_range = extractors.extract_electric_range(
            vehicle_status, charge_status
        )
        if electric_range is not None and range_topic is not None:
            LOG.info("OpenWB Integration published range to %s", range_topic)
            self.__publisher.publish_float(
                key=range_topic,
                value=electric_range,
                no_prefix=True,
            )

        soc_topic = self.__charging_station.soc_topic
        soc = extractors.extract_soc(vehicle_status, charge_status)
        if soc is not None and soc_topic is not None:
            LOG.info("OpenWB Integration published SoC to %s", soc_topic)
            self.__publisher.publish_float(
                key=soc_topic,
                value=soc,
                no_prefix=True,
            )

            soc_ts_topic = self.__charging_station.soc_ts_topic
            if soc_ts_topic is not None:
                soc_ts = int(datetime.datetime.now(tz=datetime.UTC).timestamp())
                LOG.info("OpenWB Integration published SoC timestamp to %s", soc_ts_topic)
                self.__publisher.publish_int(
                    key=soc_ts_topic,
                    value=soc_ts,
                    no_prefix=True,
                )

    def set_charger_connection_state(self, connected: bool) -> None:
        if self.__charger_connected == connected:
            return
        self.__charger_connected = connected
        if not connected:
            self.__last_imported_energy_wh = None
            self.__next_refresh_energy_wh = None

    def should_refresh_by_imported_energy(
        self,
        imported_energy_wh: float,
        battery_capacity_kwh: float | None,
        charge_polling_min_percent: float,
    ) -> bool:
        """Determine if the vehicle status should be refreshed based on imported energy.

        Triggers a refresh when imported energy since the last refresh exceeds a
        threshold derived from battery capacity and the minimum polling percentage.
        If imported energy decreases (e.g. daily counter reset), the threshold is
        recalculated from the new baseline.
        """
        if self.__charger_connected is False:
            LOG.debug("Charger is disconnected, skipping imported energy check")
            return False

        if battery_capacity_kwh is None or battery_capacity_kwh <= 0:
            LOG.warning(
                "Battery capacity not available or invalid, cannot calculate energy threshold"
            )
            return False

        if charge_polling_min_percent <= 0:
            LOG.warning(
                "charge_polling_min_percent is %.2f, must be positive; "
                "skipping energy threshold check",
                charge_polling_min_percent,
            )
            return False

        energy_per_percent = (battery_capacity_kwh * 1000.0) / 100.0
        energy_for_min_pct = math.ceil(charge_polling_min_percent * energy_per_percent)

        # Detect counter reset (energy decreased) or first call
        if (
            self.__next_refresh_energy_wh is None
            or self.__last_imported_energy_wh is None
            or imported_energy_wh < self.__last_imported_energy_wh
        ):
            self.__next_refresh_energy_wh = imported_energy_wh + energy_for_min_pct
            self.__last_imported_energy_wh = imported_energy_wh
            LOG.debug(
                "Imported energy threshold initialized to %.0f Wh",
                self.__next_refresh_energy_wh,
            )
            return False

        self.__last_imported_energy_wh = imported_energy_wh

        if imported_energy_wh >= self.__next_refresh_energy_wh:
            LOG.info(
                "Imported energy threshold of %.0f Wh reached (current: %.0f Wh), "
                "triggering vehicle refresh",
                self.__next_refresh_energy_wh,
                imported_energy_wh,
            )
            self.__next_refresh_energy_wh = imported_energy_wh + energy_for_min_pct
            LOG.debug(
                "Next imported energy threshold set to %.0f Wh",
                self.__next_refresh_energy_wh,
            )
            return True

        return False
