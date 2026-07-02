# 状态标签说明

本项目的 UI、报告和解释摘要只能使用中性观察标签。状态标签用于排序、复核和风险提示，不是交易指令。

## 允许状态

| 状态值 | 中文标签 | 含义 |
| --- | --- | --- |
| `focus_watch` | 重点观察 | 指标或状态较突出，适合加入观察列表。 |
| `normal_tracking` | 正常跟踪 | 数据质量可用，未触发明显复核条件。 |
| `risk_attention` | 风险关注 | 回撤、波动、集中度或数据质量触发风险提示。 |
| `data_insufficient` | 数据不足 | 历史、价格、成交量或交易时间信息不足。 |
| `position_review_candidate` | 仓位复核候选 | 持仓占比或盈亏状态需要人工复核。 |
| `rotation_watch_candidate` | 切换观察候选 | 相对状态变化明显，适合作为观察对象。 |
| `needs_review` | 需要复盘 | 多项数据或规则触发复核原因。 |

## 数据状态

- `ok`：数据可用于当前计算。
- `data_insufficient`：历史或关键字段不足。
- `price_missing`：最新价格缺失。
- `capital_base_missing`：未配置账户总资产，系统按当前持仓市值内部占比计算。
- `non_trading_day`：非交易日。
- `before_open`、`lunch_break`、`after_close`：交易时段外。

## 展示原则

- 每个状态必须带 `reasons`。
- 总分只能用于排序和解释。
- 报告必须包含 `not_advice=true`。
- Codex CLI 只解释已有 JSON，不参与状态生成。
