# 架构说明

第一版采用本地单机架构，目标是先完成最小纵向闭环，而不是一次性铺完整平台。

## 组件

- FastAPI 后端：提供配置、行情快照、指标快照、台账、盈亏、风控、波段状态、14:55 报告和解释摘要接口。
- React/Vite 前端：提供本地 Web MVP，面向盘中快速扫描和手动复核。
- SQLite：保存本地应用元信息、自选股配置映射和手动成交记录。
- YAML + `.env`：保存用户配置和 provider 开关。
- Mock provider：默认行情源，保证测试稳定且离线。
- Fake Codex provider：默认解释层，保证测试不调用真实 CLI。

## 数据流

```text
watchlist.yaml
-> mock daily bars
-> indicator snapshot
-> ledger summary
-> risk summary
-> wave states
-> preclose report JSON
-> fake or Codex CLI explanation
-> local Web MVP
```

核心计算全部由确定性代码完成。Codex CLI 只解释结构化报告，不重新计算、不改写状态、不添加报告外事实。

## 主要目录

- `app/core/`：配置加载和公共设置。
- `app/data/`：行情 provider。
- `app/domain/`：指标、盈亏、风控、波段状态、交易时间和报告构建。
- `app/providers/llm/`：Codex CLI provider、fake provider 行为和自检。
- `app/schemas/`：API request/response schema。
- `app/services/`：台账读写和当前组合聚合。
- `app/api/routes/`：HTTP 路由。
- `web/src/`：本地 Web MVP。
- `tests/`：单元、API 和 smoke 测试。

## 外部依赖边界

- AkShare 后续通过 market adapter 接入；当前默认不接。
- Codex CLI 后续可显式启用；当前默认 fake。
- 测试不依赖真实网络、真实行情、真实交易日或真实 Codex CLI。

## 错误和降级

数据不足、价格缺失、非交易日、账户总资产缺失等情况不会静默吞掉。API 会返回结构化状态和原因，前端以数据状态或提示区域展示。
