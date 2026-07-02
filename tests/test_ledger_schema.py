import pytest
from pydantic import ValidationError

from app.schemas.ledger import TradeRecordCreate


def valid_payload() -> dict[str, str]:
    return {
        "instrument_name": "中天科技",
        "instrument_code": "",
        "trade_date": "2026-06-30",
        "side": "increase_position",
        "quantity": "100",
        "price": "12.34",
        "fee": "1.23",
        "note": "manual fact",
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quantity", "0"),
        ("price", "-0.01"),
        ("fee", "-0.01"),
        ("trade_date", " "),
    ],
)
def test_trade_record_create_rejects_invalid_input(field: str, value: str) -> None:
    payload = valid_payload()
    payload[field] = value

    with pytest.raises(ValidationError):
        TradeRecordCreate(**payload)
