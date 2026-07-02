from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Mapping


@dataclass(frozen=True)
class MarketSessionStatus:
    status: str
    is_trading_day: bool
    is_preclose_time: bool
    session: str
    calendar_mode: str
    as_of_date: str
    as_of_time: str
    report_time: str


def evaluate_market_session(
    as_of: datetime,
    preferences_config: Mapping[str, object] | None = None,
) -> MarketSessionStatus:
    config = preferences_config or {}
    morning_start = _config_time(config, "trading_sessions.morning.start", "09:30")
    morning_end = _config_time(config, "trading_sessions.morning.end", "11:30")
    afternoon_start = _config_time(config, "trading_sessions.afternoon.start", "13:00")
    afternoon_end = _config_time(config, "trading_sessions.afternoon.end", "15:00")
    report_time = _config_time(config, "daily_report_time", "14:55")

    as_of_date = as_of.date().isoformat()
    closed_dates = _config_text_set(config, "market.closed_dates")
    extra_open_dates = _config_text_set(config, "market.extra_open_dates")
    if as_of_date in closed_dates:
        is_trading_day = False
        calendar_mode = "local_config"
    elif as_of_date in extra_open_dates:
        is_trading_day = True
        calendar_mode = "local_config"
    else:
        is_trading_day = as_of.weekday() < 5
        calendar_mode = "weekday_fallback"
    as_time = as_of.time().replace(microsecond=0)
    is_preclose = (
        is_trading_day
        and as_time.hour == report_time.hour
        and as_time.minute == report_time.minute
    )

    if not is_trading_day:
        status = "non_trading_day"
        session = "closed"
    elif is_preclose:
        status = "preclose"
        session = "afternoon"
    elif morning_start <= as_time <= morning_end:
        status = "morning_session"
        session = "morning"
    elif morning_end < as_time < afternoon_start:
        status = "lunch_break"
        session = "break"
    elif afternoon_start <= as_time <= afternoon_end:
        status = "afternoon_session"
        session = "afternoon"
    elif as_time < morning_start:
        status = "before_open"
        session = "closed"
    else:
        status = "after_close"
        session = "closed"

    return MarketSessionStatus(
        status=status,
        is_trading_day=is_trading_day,
        is_preclose_time=is_preclose,
        session=session,
        calendar_mode=calendar_mode,
        as_of_date=as_of_date,
        as_of_time=as_time.isoformat(),
        report_time=_format_time(report_time),
    )


def _config_time(
    config: Mapping[str, object],
    dotted_key: str,
    default_value: str,
) -> time:
    value = _nested_get(config, dotted_key) or default_value
    return time.fromisoformat(str(value))


def _nested_get(config: Mapping[str, object], dotted_key: str) -> object | None:
    current: object = config
    for part in dotted_key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _config_text_set(config: Mapping[str, object], dotted_key: str) -> set[str]:
    value = _nested_get(config, dotted_key)
    if value is None:
        return set()
    if not isinstance(value, list):
        return {str(value)}
    return {str(item) for item in value}


def _format_time(value: time) -> str:
    return value.strftime("%H:%M")
