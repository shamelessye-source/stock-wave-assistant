from datetime import datetime

from app.domain.trading_calendar import evaluate_market_session


def test_evaluate_market_session_marks_preclose_time() -> None:
    status = evaluate_market_session(datetime.fromisoformat("2026-07-01T14:55:00"))

    assert status.status == "preclose"
    assert status.is_trading_day is True
    assert status.is_preclose_time is True
    assert status.session == "afternoon"
    assert status.calendar_mode == "weekday_fallback"


def test_evaluate_market_session_marks_non_trading_day() -> None:
    status = evaluate_market_session(datetime.fromisoformat("2026-07-04T14:55:00"))

    assert status.status == "non_trading_day"
    assert status.is_trading_day is False
    assert status.is_preclose_time is False


def test_evaluate_market_session_marks_break_and_after_close() -> None:
    lunch = evaluate_market_session(datetime.fromisoformat("2026-07-01T12:00:00"))
    after_close = evaluate_market_session(datetime.fromisoformat("2026-07-01T15:30:00"))

    assert lunch.status == "lunch_break"
    assert after_close.status == "after_close"
