from __future__ import annotations

import pytest

from extractors import extract_soc_kwh
from status_publisher.charge.chrg_mgmt_data_resp import ChrgMgmtDataRespProcessingResult


def _make_charge_result(
    *,
    soc_kwh: float | None = None,
    real_total_battery_capacity: float = 64.0,
) -> ChrgMgmtDataRespProcessingResult:
    return ChrgMgmtDataRespProcessingResult(
        charge_current_limit=None,
        target_soc=None,
        scheduled_charging=None,
        is_charging=None,
        remaining_charging_time=None,
        power=None,
        real_total_battery_capacity=real_total_battery_capacity,
        raw_soc=None,
        raw_fuel_range_elec=None,
        soc_kwh=soc_kwh,
    )


class TestExtractSocKwh:
    def test_prefers_realtime_power_soc_kwh(self) -> None:
        result = extract_soc_kwh(_make_charge_result(soc_kwh=42.0), soc=80.0)
        assert result == pytest.approx(42.0)

    def test_fallback_to_soc_times_capacity(self) -> None:
        # 80% of 64 kWh = 51.2 kWh
        result = extract_soc_kwh(_make_charge_result(soc_kwh=None), soc=80.0)
        assert result == pytest.approx(51.2)

    def test_fallback_returns_none_when_soc_is_none(self) -> None:
        result = extract_soc_kwh(_make_charge_result(soc_kwh=None), soc=None)
        assert result is None

    def test_fallback_returns_none_when_charge_status_is_none(self) -> None:
        result = extract_soc_kwh(None, soc=80.0)
        assert result is None

    def test_fallback_returns_none_when_capacity_is_zero(self) -> None:
        result = extract_soc_kwh(
            _make_charge_result(soc_kwh=None, real_total_battery_capacity=0.0), soc=80.0
        )
        assert result is None

    def test_fallback_used_when_soc_kwh_is_zero(self) -> None:
        # soc_kwh=0 is not a valid primary reading; fall back to soc * capacity
        result = extract_soc_kwh(_make_charge_result(soc_kwh=0.0), soc=80.0)
        assert result == pytest.approx(51.2)
