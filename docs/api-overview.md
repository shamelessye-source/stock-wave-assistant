# API 概览

后端默认运行在 `http://127.0.0.1:8000`。所有接口返回结构化 JSON，不返回本地敏感路径。

## 健康与配置

```text
GET /api/health
GET /api/config/status
```

`/api/config/status` 返回 provider、mock 模式、Codex enabled、模型、timeout、sandbox 和自检状态。它只展示安全摘要。

## 行情与指标

```text
GET /api/market/snapshot
GET /api/indicators/snapshot
```

当前默认使用 mock 行情。指标快照包含名称、代码、最新交易日、最新收盘价、MA20、MA60、动量、最大回撤、ATR、成交量比值、数据状态和降级原因。

## 交易台账与盈亏

```text
GET /api/ledger/trades
POST /api/ledger/trades
GET /api/ledger/summary
```

`POST /api/ledger/trades` 使用中性方向枚举：

- `increase_position`
- `decrease_position`

输入校验包含：名称不能为空、日期不能为空、数量必须大于 0、价格和费用不能为负。

## 风控与波段状态

```text
GET /api/risk/summary
GET /api/wave/states
```

风控摘要包含总持仓市值、浮动盈亏、已实现盈亏、总盈亏、单标的占比、方向/分组集中度和数据完整性状态。

波段状态包含名称、代码、最新交易日、指标摘要、持仓摘要、风险摘要、状态、原因、分项分数和总分。总分只用于排序和解释。

## 14:55 报告

```text
GET /api/reports/preclose
GET /api/reports/preclose?as_of=2026-07-01T14:55:00
```

`as_of` 可用于测试固定时间。报告包含：

- `report_type`
- `as_of_date`
- `as_of_time`
- `market_session_status`
- `not_advice`
- `data_status`
- `portfolio_summary`
- `risk_flags`
- `watchlist_rankings`
- `state_distribution`
- `attention_items`
- `rotation_watch_candidates`
- `position_review_candidates`
- `data_quality_notes`
- `generated_at`

## 解释摘要

```text
POST /api/reports/preclose/explain
```

请求体可以传入已有报告 JSON，也可以传入 `as_of` 让后端先生成报告。默认 fake provider 返回稳定中文摘要。真实 Codex CLI 需要显式启用，并且只解释报告 JSON。
