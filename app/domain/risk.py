from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping

from app.domain.pnl import PnlItem


@dataclass(frozen=True)
class RiskPosition:
    instrument_name: str
    instrument_code: str
    group: str
    direction: str
    market_value: Decimal
    position_weight_pct: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    total_pnl: Decimal
    risk_status: str
    reasons: list[str]

    @property
    def weight_pct(self) -> Decimal:
        return self.position_weight_pct


@dataclass(frozen=True)
class ConcentrationItem:
    name: str
    market_value: Decimal
    weight_pct: Decimal
    risk_status: str


@dataclass(frozen=True)
class RiskSummary:
    total_market_value: Decimal
    floating_pnl: Decimal
    realized_pnl: Decimal
    total_pnl: Decimal
    max_single_position: RiskPosition
    max_single_position_risk_status: str
    direction_concentration: list[ConcentrationItem]
    group_concentration: list[ConcentrationItem]
    positions: list[RiskPosition]
    data_status: str
    degradation_reasons: list[str]


def calculate_risk_summary(
    pnl_items: list[PnlItem],
    watchlist_config: Mapping[str, object],
    preferences_config: Mapping[str, object],
    factor_config: Mapping[str, object],
) -> RiskSummary:
    stock_meta = _watchlist_meta(watchlist_config)
    thresholds = _thresholds(preferences_config, factor_config)
    account_total_assets = _optional_decimal(
        _nested_get(preferences_config, "account.total_assets")
        or _nested_get(preferences_config, "portfolio.total_assets")
    )

    degradation_reasons: list[str] = []
    market_items: list[tuple[PnlItem, Decimal]] = []
    for item in pnl_items:
        if item.status != "ok":
            degradation_reasons.append(f"{item.status}:{item.instrument_name}")
        if item.current_market_value is None:
            degradation_reasons.append(f"price_missing:{item.instrument_name}")
            continue
        if item.current_market_value <= 0:
            continue
        market_items.append((item, item.current_market_value))

    total_market_value = _money(sum((value for _, value in market_items), Decimal("0")))
    floating_pnl = _money(
        sum(
            ((item.unrealized_pnl or Decimal("0")) for item, _ in market_items),
            Decimal("0"),
        )
    )
    realized_pnl = _money(sum((item.realized_pnl for item in pnl_items), Decimal("0")))
    total_pnl = _money(sum((item.total_pnl for item in pnl_items), Decimal("0")))

    if account_total_assets is None or account_total_assets <= 0:
        degradation_reasons.append("capital_base_missing")
        weight_base = total_market_value
    else:
        weight_base = account_total_assets

    positions = [
        _position_from_item(
            item,
            market_value,
            weight_base,
            stock_meta,
            thresholds["max_single_position_pct"],
        )
        for item, market_value in market_items
    ]
    max_position = max(
        positions,
        key=lambda position: position.position_weight_pct,
        default=_empty_position(),
    )
    direction_concentration = _concentration(
        positions,
        field="direction",
        threshold_pct=thresholds["max_direction_position_pct"],
    )
    group_concentration = _concentration(
        positions,
        field="group",
        threshold_pct=thresholds["max_direction_position_pct"],
    )

    return RiskSummary(
        total_market_value=total_market_value,
        floating_pnl=floating_pnl,
        realized_pnl=realized_pnl,
        total_pnl=total_pnl,
        max_single_position=max_position,
        max_single_position_risk_status=max_position.risk_status,
        direction_concentration=direction_concentration,
        group_concentration=group_concentration,
        positions=positions,
        data_status=_data_status(positions, degradation_reasons),
        degradation_reasons=list(dict.fromkeys(degradation_reasons)),
    )


def _position_from_item(
    item: PnlItem,
    market_value: Decimal,
    weight_base: Decimal,
    stock_meta: Mapping[tuple[str, str], dict[str, str]],
    max_single_position_pct: Decimal,
) -> RiskPosition:
    meta = stock_meta.get((item.instrument_name, item.instrument_code), {})
    weight_pct = _pct(market_value, weight_base)
    reasons: list[str] = []
    risk_status = "normal"
    if weight_pct > max_single_position_pct:
        risk_status = "high_concentration"
        reasons.append("single_position_weight_high")
    return RiskPosition(
        instrument_name=item.instrument_name,
        instrument_code=item.instrument_code,
        group=meta.get("group", "未分组"),
        direction=meta.get("direction", "未分类"),
        market_value=_money(market_value),
        position_weight_pct=weight_pct,
        unrealized_pnl=_money(item.unrealized_pnl or Decimal("0")),
        realized_pnl=_money(item.realized_pnl),
        total_pnl=_money(item.total_pnl),
        risk_status=risk_status,
        reasons=reasons,
    )


def _concentration(
    positions: list[RiskPosition],
    *,
    field: str,
    threshold_pct: Decimal,
) -> list[ConcentrationItem]:
    total_market_value = sum(position.market_value for position in positions)
    buckets: dict[str, Decimal] = {}
    for position in positions:
        name = getattr(position, field)
        buckets[name] = buckets.get(name, Decimal("0")) + position.market_value
    items = []
    for name, market_value in buckets.items():
        weight_pct = _pct(market_value, total_market_value)
        items.append(
            ConcentrationItem(
                name=name,
                market_value=_money(market_value),
                weight_pct=weight_pct,
                risk_status=(
                    "high_concentration"
                    if weight_pct > threshold_pct
                    else "normal"
                ),
            )
        )
    return sorted(items, key=lambda item: item.weight_pct, reverse=True)


def _watchlist_meta(config: Mapping[str, object]) -> dict[tuple[str, str], dict[str, str]]:
    stocks = config.get("stocks", [])
    if not isinstance(stocks, list):
        return {}
    meta: dict[tuple[str, str], dict[str, str]] = {}
    for stock in stocks:
        if not isinstance(stock, Mapping) or stock.get("enabled", True) is False:
            continue
        name = str(stock.get("name") or "")
        symbol = str(stock.get("symbol") or "")
        meta[(name, symbol)] = {
            "group": str(stock.get("group") or "未分组"),
            "direction": str(stock.get("direction") or "未分类"),
        }
    return meta


def _thresholds(
    preferences_config: Mapping[str, object],
    factor_config: Mapping[str, object],
) -> dict[str, Decimal]:
    return {
        "max_single_position_pct": _optional_decimal(
            _nested_get(preferences_config, "risk.max_single_position_pct")
            or _nested_get(factor_config, "thresholds.max_single_position_pct")
        )
        or Decimal("20"),
        "max_direction_position_pct": _optional_decimal(
            _nested_get(preferences_config, "risk.max_direction_position_pct")
            or _nested_get(factor_config, "thresholds.max_direction_position_pct")
        )
        or Decimal("40"),
    }


def _data_status(
    positions: list[RiskPosition],
    degradation_reasons: list[str],
) -> str:
    if any(reason.startswith("price_missing:") for reason in degradation_reasons):
        return "data_incomplete"
    if not positions:
        return "data_insufficient"
    if degradation_reasons == ["capital_base_missing"]:
        return "capital_base_missing"
    if "capital_base_missing" in degradation_reasons:
        return "capital_base_missing"
    return "ok"


def _nested_get(config: Mapping[str, object], dotted_key: str) -> object | None:
    current: object = config
    for part in dotted_key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _optional_decimal(value: object | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _pct(value: Decimal, base: Decimal) -> Decimal:
    if base <= 0:
        return Decimal("0.00")
    return _money(value / base * Decimal("100"))


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _empty_position() -> RiskPosition:
    return RiskPosition(
        instrument_name="",
        instrument_code="",
        group="",
        direction="",
        market_value=Decimal("0.00"),
        position_weight_pct=Decimal("0.00"),
        unrealized_pnl=Decimal("0.00"),
        realized_pnl=Decimal("0.00"),
        total_pnl=Decimal("0.00"),
        risk_status="data_insufficient",
        reasons=["no_positions"],
    )
