# A 股自选股波段切换决策助手设计规格

## 目标

构建一个本地运行的 A 股自选股波段观察与风险辅助工具。第一版只做最小纵向闭环，验证用户能否从配置自选股、读取行情、计算基础因子、生成波段状态、记录交易事实、计算基础盈亏，到生成 14:55 结构化报告并在本地 Web 中查看。

本项目不是荐股、投顾、自动交易或量化平台。所有核心计算必须由确定性代码完成；AI 只解释已经生成的结构化结果。

## 第一版最小纵向闭环

第一版必须优先打通以下闭环，不一次性铺完整平台：

1. 配置自选股。
2. 使用 mock 行情或少量缓存行情。
3. 计算基础因子。
4. 生成波段状态。
5. 录入一笔交易事实。
6. 计算基础盈亏。
7. 生成一份 14:55 JSON 报告。
8. 可选调用 Codex CLI，把 JSON 报告解释成中文总结。
9. 本地 Web 能展示以上结果。

不进入第一版闭环的内容：

- 自动交易、券商接口、订单生成。
- 真实账户同步。
- 高频或分钟级策略。
- 机器学习预测。
- 自动因子挖掘。
- 完整回测平台。
- 多数据源复杂聚合。
- 云同步、多用户服务化部署。

## 强制边界

### 投资与合规边界

- 不连接券商账户。
- 不保存交易密码、资金账号或其他交易凭据。
- 不生成订单。
- 不模拟一键下单。
- 不输出直接交易指令。
- 不承诺收益。
- 不把历史样例写成有效性证明。

所有 UI、报告、测试样例和 README 都必须保留边界说明：

> 本工具仅展示基于本地规则和当前数据的观察结果，不构成投资建议。请结合个人风险承受能力独立决策。

### 禁止越界表达

UI、报告、测试样例中不得出现直接交易动作、个股推介、预设价位、收益承诺或类似确定性措辞。为保证自动扫描稳定，文档也不保留这些词的原文清单，只保留类别说明。

可用状态标签：

- 重点观察
- 正常跟踪
- 风险关注
- 数据不足
- 仓位复核候选
- 切换观察候选
- 需要复盘

### AI/LLM 边界

- 默认 provider 名称必须是 `codex_cli`。
- 默认模型必须是 `gpt-5.5`。
- Codex CLI 路径必须支持配置覆盖；示例配置不得写入个人机器路径。
- 支持配置覆盖：
  - `CODEX_CLI_PATH`
  - `CODEX_MODEL`
  - `CODEX_TIMEOUT_SECONDS`
  - `CODEX_SANDBOX_MODE`
- Codex CLI 只能用于解释层和报告层。
- Codex CLI 不得用于行情计算、因子计算、盈亏计算、仓位计算、风控计算。
- Codex CLI 调用失败时，结构化报告仍必须可用。
- 每次 Codex CLI 调用必须记录模型、路径、超时、sandbox、输入摘要、输出摘要、开始结束时间、退出码、错误信息、报告路径。

## Mock/Fake 优先原则

所有核心模块必须先支持 mock/fake 模式。

默认测试不得依赖：

- 真实 AkShare。
- 真实网络。
- 真实 Codex CLI。
- 当前真实交易日。
- 当前真实行情。

必须通过封装隔离外部依赖：

- `MarketDataProvider` 封装真实 AkShare 与 mock 行情。
- `LLMProvider` 封装真实 Codex CLI 与 fake provider。
- `TradingCalendar` 封装 A 股交易日、交易时间和 fake clock。
- `ReportStorage` 封装本地文件或 SQLite 存储。

mock/fake 模式必须能完成最小闭环：

```text
mock watchlist
-> mock daily bars
-> deterministic indicators
-> wave state
-> one ledger entry
-> pnl summary
-> 14:55 JSON report
-> fake Codex summary
-> local Web display
```

## A 股交易日与交易时间

所有时间默认使用 `Asia/Shanghai`。

交易时段：

- 上午：`09:30-11:30`
- 下午：`13:00-15:00`

14:55 报告触发规则：

- 只在交易日触发。
- 触发时间为 `14:55`。
- 非交易日不生成盘中总结。
- 午休时段不生成盘中总结。
- 收盘后允许查看或重新生成当天报告，但报告必须标记实际生成时间。
- 若行情数据延迟、缺失或字段不完整，报告必须降级为 `partial` 或 `blocked`，并显示原因。

MVP 的交易日判断：

- 默认使用本地交易日配置文件和 fake calendar。
- 若没有配置节假日，默认仅按工作日判断，并在 UI/报告中标记 `calendar_mode=weekday_fallback`。
- 后续可增加真实 A 股交易日数据源，但不得让测试依赖网络。

数据延迟处理：

```text
if data_missing:
    data_status = "missing"
    report_status = "blocked" 或 "partial"

if data_delayed_minutes > configured_threshold:
    data_status = "delayed"
    report_status = "partial"

if data_time not in current trading session:
    data_status = "stale"
    report_status = "partial"
```

## 技术架构

第一版建议采用：

- 后端：Python + FastAPI。
- 前端：React + Vite。
- 数据库：SQLite。
- 数据处理：pandas 或纯 Python，按实现复杂度选择。
- 数据源：AkShare adapter，默认测试用 mock provider。
- 调度：APScheduler 或轻量自定义 scheduler，第一版所有任务也必须可手动触发。
- 配置：`.env` + YAML。
- AI 解释层：Codex CLI provider，默认 `gpt-5.5`。

核心设计原则：

- 业务计算与外部依赖分离。
- 结构化报告先于 AI 解释。
- 台账是持仓和盈亏的唯一可信来源。
- 所有状态都带原因、数据时间、数据来源和数据质量。
- 默认可离线跑通 mock 闭环。

## 建议目录结构

```text
stock-wave-assistant/
  pyproject.toml
  package.json
  README.md
  .env.example
  config/
    watchlist.example.yaml
    strategy.example.yaml
    trading_calendar.example.yaml
  data/
    cache/
    reports/
    app.db
  app/
    main.py
    core/
      config.py
      clock.py
      errors.py
      logging.py
    schemas/
      watchlist.py
      ledger.py
      indicators.py
      wave_state.py
      alerts.py
      reports.py
      llm.py
    db/
      session.py
      models.py
      bootstrap.py
    providers/
      market/
        base.py
        mock_provider.py
        akshare_provider.py
      llm/
        base.py
        fake_provider.py
        codex_cli.py
      calendar/
        base.py
        local_calendar.py
        fake_calendar.py
    domain/
      indicators.py
      ledger.py
      pnl.py
      risk.py
      wave_state.py
      report_builder.py
      forbidden_terms.py
    services/
      watchlist_service.py
      market_service.py
      ledger_service.py
      report_service.py
      llm_service.py
    api/
      routes/
        health.py
        watchlist.py
        market.py
        ledger.py
        reports.py
        ai.py
  web/
    src/
      App.tsx
      api/
      components/
      pages/
      styles/
  tests/
    unit/
    integration/
    fixtures/
```

## Schema 定义

以下 schema 是 MVP 的契约。实现可以用 Pydantic model、JSON Schema 或 TypeScript type 同步表达，但字段语义不得漂移。

### Watchlist Config Schema

用途：配置自选股池，不硬编码股票代码。

```json
{
  "version": 1,
  "stocks": [
    {
      "symbol": "002000.SZ",
      "name": "示例股票",
      "market": "SZ",
      "enabled": true,
      "group": "核心观察",
      "direction": "光通信",
      "watch_reason": "用户自定义关注理由",
      "core_logic": "用户自定义中期逻辑",
      "risk_points": ["业绩波动", "主题退潮"],
      "status": "正常跟踪",
      "tags": ["半导体", "设备"],
      "position_plan": {
        "target_weight_pct": 10.0,
        "max_weight_pct": 20.0
      },
      "alert_rules": {
        "price_change_pct_abs": 5.0,
        "volume_ratio_min": 1.5,
        "score_change_min": 15.0
      }
    }
  ]
}
```

约束：

- `symbol` 由用户配置或后续解析，不在代码中硬编码。
- `status` 只能使用允许状态标签。
- `risk_points` 是用户备注，不参与直接交易指令生成。

### Trade Ledger Schema

用途：记录交易事实，用于持仓与盈亏计算。交易事实可以描述仓位变化，但不得作为系统建议输出。

```json
{
  "ledger_id": "ledger-20260630-0001",
  "trade_date": "2026-06-30",
  "trade_time": "14:58:00",
  "symbol": "002000.SZ",
  "name": "示例股票",
  "quantity_delta": 1000,
  "price": 12.34,
  "fee": 5.0,
  "tax": 0.0,
  "cash_delta": -12345.0,
  "reason": "用户手工记录的交易事实",
  "related_report_id": "report-20260630-1455",
  "source": "manual",
  "created_at": "2026-06-30T15:10:00+08:00"
}
```

约束：

- `quantity_delta` 为正表示持仓数量增加，为负表示持仓数量减少。
- `cash_delta` 为现金变化，不能由 UI 文案包装成系统建议。
- 后端必须校验数量、价格、费用非负或符合现金流约束。
- 若减少数量超过当前持仓，记录必须被拒绝或标记为 invalid。

### Indicator Snapshot Schema

用途：保存确定性因子结果。

```json
{
  "snapshot_id": "ind-20260630-002000",
  "symbol": "002000.SZ",
  "trade_date": "2026-06-30",
  "data_source": "mock",
  "data_timestamp": "2026-06-30T14:54:30+08:00",
  "data_status": "ok",
  "prices": {
    "close": 12.34,
    "pre_close": 11.90
  },
  "factors": {
    "ma20": 11.80,
    "ma60": 10.95,
    "ret_5d_pct": 4.2,
    "ret_20d_pct": 9.8,
    "volume_ratio_20d": 1.35,
    "atr_pct": 3.1,
    "max_drawdown_60d_pct": -8.4,
    "relative_strength_20d_pct": 2.5
  },
  "factor_scores": {
    "trend": 75,
    "momentum": 70,
    "volume": 60,
    "risk": 80,
    "relative_strength": 65
  },
  "warnings": []
}
```

约束：

- `data_status` 可取 `ok`、`delayed`、`missing`、`stale`、`insufficient_history`、`invalid`。
- 数据不足时不得输出正常波段状态。
- 所有分数必须可由 `factors` 复算或解释。

### Wave State Schema

用途：给出可解释、非指令化的波段状态。

```json
{
  "wave_state_id": "wave-20260630-002000",
  "symbol": "002000.SZ",
  "trade_date": "2026-06-30",
  "label": "重点观察",
  "total_score": 72.5,
  "confidence": "medium",
  "evidence": [
    "收盘价高于 20 日均线",
    "20 日涨幅强于自选股均值",
    "成交量高于 20 日均量"
  ],
  "risk_flags": [
    "接近单票仓位上限"
  ],
  "data_status": "ok",
  "invalidated_if": [
    "后续数据跌破 20 日均线",
    "成交量持续低于 20 日均量"
  ]
}
```

约束：

- `label` 只能使用允许状态标签。
- `evidence` 必须引用确定性指标。
- 不得包含直接交易指令。

### Alert Event Schema

用途：记录提醒事件，供 UI 和报告引用。

```json
{
  "alert_id": "alert-20260630-001",
  "symbol": "002000.SZ",
  "trade_date": "2026-06-30",
  "triggered_at": "2026-06-30T14:54:30+08:00",
  "alert_type": "score_change",
  "severity": "medium",
  "title": "波段评分变化",
  "reason": "总分较上一交易日上升 16.5 分",
  "data_status": "ok",
  "dedupe_key": "002000.SZ:2026-06-30:score_change",
  "user_state": "unread",
  "related_snapshot_id": "ind-20260630-002000"
}
```

约束：

- 同一 `dedupe_key` 当日只提醒一次。
- `user_state` 可取 `unread`、`viewed`、`marked`、`ignored`、`expired`。
- 数据缺失时提醒原因必须说明缺失字段。

### 14:55 Report JSON Schema

用途：每日 14:55 结构化报告。AI 解释必须只消费此 JSON。

```json
{
  "report_id": "report-20260630-1455",
  "report_type": "daily_1455",
  "trade_date": "2026-06-30",
  "generated_at": "2026-06-30T14:55:00+08:00",
  "calendar_status": {
    "is_trading_day": true,
    "session": "afternoon",
    "calendar_mode": "fake"
  },
  "report_status": "ready",
  "data_quality": {
    "overall_status": "ok",
    "missing_symbols": [],
    "delayed_symbols": [],
    "notes": []
  },
  "market_summary": {
    "source": "mock",
    "data_timestamp": "2026-06-30T14:54:30+08:00"
  },
  "watchlist_summary": {
    "total_symbols": 8,
    "active_symbols": 8,
    "alerts_count": 2
  },
  "items": [
    {
      "symbol": "002000.SZ",
      "name": "示例股票",
      "wave_label": "重点观察",
      "total_score": 72.5,
      "factor_scores": {
        "trend": 75,
        "momentum": 70,
        "volume": 60,
        "risk": 80,
        "relative_strength": 65
      },
      "position": {
        "quantity": 1000,
        "avg_cost": 11.20,
        "market_value": 12340.0,
        "unrealized_pnl": 1140.0,
        "unrealized_pnl_pct": 10.18,
        "weight_pct": 12.34
      },
      "risk_flags": ["接近单票仓位上限"],
      "review_questions": [
        "当前仓位是否仍符合用户原计划？"
      ],
      "data_status": "ok"
    }
  ],
  "portfolio_risk": {
    "total_market_value": 12340.0,
    "cash": 50000.0,
    "total_equity": 62340.0,
    "max_position_weight_pct": 12.34,
    "risk_level": "low",
    "risk_reasons": []
  },
  "next_review_items": [
    "复核今日触发提醒的股票",
    "补充交易事实和复盘备注"
  ],
  "not_advice": true,
  "allowed_labels": [
    "重点观察",
    "正常跟踪",
    "风险关注",
    "数据不足",
    "仓位复核候选",
    "切换观察候选",
    "需要复盘"
  ]
}
```

约束：

- 非交易日时 `report_status` 必须是 `blocked`，并说明原因。
- 数据延迟或缺失时 `report_status` 必须是 `partial` 或 `blocked`。
- `not_advice` 必须为 `true`。
- `items[*].wave_label` 只能使用允许状态标签。

### Codex CLI Prompt Input Schema

用途：传给 Codex CLI 的结构化输入。只允许解释报告，不允许生成新信号。

```json
{
  "prompt_type": "daily_1455_explanation",
  "provider": "codex_cli",
  "model": "gpt-5.5",
  "language": "zh-CN",
  "instructions": [
    "只能解释 report_json 中已经存在的确定性数据",
    "不得新增 report_json 中没有的事实",
    "不得输出直接交易指令",
    "必须说明数据缺失或延迟",
    "必须保留不构成投资建议声明"
  ],
  "forbidden_term_categories": [
    "direct_trade_action",
    "stock_promotion",
    "preset_price",
    "return_promise"
  ],
  "allowed_labels": [
    "重点观察",
    "正常跟踪",
    "风险关注",
    "数据不足",
    "仓位复核候选",
    "切换观察候选",
    "需要复盘"
  ],
  "report_json": {}
}
```

### Codex CLI Output Schema

用途：解析或校验 Codex CLI 输出。

```json
{
  "summary_cn": "中文解释摘要",
  "risk_notes": [
    "风险说明"
  ],
  "review_questions": [
    "需要用户人工复核的问题"
  ],
  "data_limitations": [
    "数据延迟或缺失说明"
  ],
  "not_advice_text": "本工具仅展示基于本地规则和当前数据的观察结果，不构成投资建议。",
  "source_report_id": "report-20260630-1455",
  "contains_forbidden_terms": false
}
```

约束：

- 若输出包含禁用表达，后端必须标记为 `contains_forbidden_terms=true`，UI 不展示该解释文本。
- fake provider 必须能输出同结构 JSON，用于默认测试。

## 计算逻辑

### 基础因子

MVP 只做少量、可解释、可复算因子：

```text
ret_1d = close / pre_close - 1
ret_n = close / close_n_days_ago - 1
ma_n = mean(close, n)
volume_ratio_20d = volume / mean(volume, 20)
atr_pct = atr_14 / close
max_drawdown_60d = close / rolling_peak_60d - 1
relative_strength_20d = stock_ret_20d - index_ret_20d
```

没有指数数据时，`relative_strength_20d` 使用自选股横截面排名 fallback，并标记 `relative_strength_mode=watchlist_rank_fallback`。

### 波段状态

建议权重：

```text
total_score =
  0.30 * trend_score
+ 0.25 * momentum_score
+ 0.15 * volume_score
+ 0.20 * relative_strength_score
+ 0.10 * risk_score
```

状态映射：

```text
if data_status != "ok":
    label = "数据不足"
elif portfolio_or_position_needs_review:
    label = "仓位复核候选"
elif total_score >= 75 and risk_score >= 70:
    label = "重点观察"
elif total_score >= 60:
    label = "正常跟踪"
elif total_score >= 45:
    label = "需要复盘"
else:
    label = "风险关注"
```

切换观察候选仅表示在自选池内相对强弱变化值得人工复核，不表示交易指令：

```text
if score_rank_improved and data_status == "ok":
    optional_label = "切换观察候选"
```

### 盈亏计算

持仓由交易台账复算。

```text
new_quantity = previous_quantity + quantity_delta
unrealized_pnl = quantity * (current_price - avg_cost)
unrealized_pnl_pct = current_price / avg_cost - 1
```

若 `quantity_delta > 0`：

```text
new_avg_cost =
  (old_quantity * old_avg_cost + quantity_delta * price + fee)
  / new_quantity
```

若 `quantity_delta < 0`：

```text
realized_pnl =
  abs(quantity_delta) * (price - avg_cost)
  - fee
  - tax
```

## 本地 Web MVP

第一版 Web 只展示最小闭环，不铺完整平台。

页面：

1. 仪表盘：展示自选股、数据状态、波段状态、基础盈亏、14:55 报告入口。
2. 自选股：展示配置列表和状态。
3. 交易台账：录入一笔交易事实，展示持仓与盈亏。
4. 14:55 报告：展示 JSON 报告和可选中文解释。
5. 设置/自检：展示 mock/fake 模式、Codex CLI 状态、数据源状态。

UI 规则：

- 所有判断性内容必须带触发原因和数据状态。
- 数据缺失或延迟必须显式展示。
- 禁止出现越界表达。
- 默认展示 mock 数据，用户可手动切换真实 provider。

## API 草案

```http
GET /api/health
GET /api/selfcheck

GET /api/watchlist
PUT /api/watchlist

POST /api/market/mock/load
POST /api/market/sync
GET /api/market/snapshots

POST /api/ledger
GET /api/ledger
GET /api/pnl/summary

POST /api/wave-states/recompute
GET /api/wave-states

POST /api/reports/daily-1455
GET /api/reports/{report_id}

POST /api/ai/explain/{report_id}
GET /api/ai/calls
```

## 测试策略

默认测试必须使用 mock/fake：

- `MockMarketDataProvider`
- `FakeLLMProvider`
- `FakeTradingCalendar`
- 临时 SQLite 数据库
- 固定 fixture 行情

最小测试清单：

1. 配置解析：默认值、缺字段、非法阈值、中文路径。
2. 交易时间：交易日 14:55 允许生成，非交易日阻止生成。
3. 行情数据：正常、缺字段、重复日期、历史不足、停牌或 volume 为 0。
4. 因子计算：均线、收益率、成交量比、回撤。
5. 波段状态：同一输入输出稳定，数据不足降级。
6. 台账盈亏：数量增加、数量减少、费用、税费、超持仓校验。
7. 报告 JSON：schema 完整、`not_advice=true`、禁用表达不出现。
8. Codex provider：路径不存在、timeout、非零退出、fake provider 成功。
9. Web MVP：页面可加载，展示 mock 闭环结果。

## README 必须说明

- 本项目仅用于个人本地研究、记录和风险提示，不构成证券投资咨询、投资建议或交易指令。
- 本项目不会自动下单，不连接真实交易账户，不代替用户决策。
- LLM 仅用于解释确定性计算结果和生成报告，不作为核心交易信号来源。
- 默认 AI provider 为 `codex_cli`，默认模型为 `gpt-5.5`。
- 本项目依赖用户本机已安装并登录 Codex CLI。
- 默认测试不依赖真实网络、真实 AkShare 或真实 Codex CLI。
- 数据可能存在延迟、缺失、错误、复权差异和来源限制。

## 实现计划

### Task 1: 项目脚手架

目标：创建可安装、可测试、可启动的最小项目结构。

文件：

- `pyproject.toml`
- `package.json`
- `.env.example`
- `app/main.py`
- `web/src/App.tsx`
- `tests/`

验收：

- `python -m pytest` 可运行。
- 后端 `GET /api/health` 返回 ok。
- 前端 dev server 可启动并显示 MVP 壳。

### Task 2: 配置和数据库

目标：实现配置加载、SQLite 初始化和基础 schema。

文件：

- `app/core/config.py`
- `app/db/session.py`
- `app/db/models.py`
- `app/db/bootstrap.py`
- `config/watchlist.example.yaml`

验收：

- 默认配置使用 mock/fake provider。
- 数据库可创建 watchlist、ledger、indicator snapshot、wave state、alert、report、ai call log 表。
- 配置测试覆盖 Codex CLI 默认值和覆盖值。

### Task 3: Mock 行情与指标

目标：用 mock 行情完成基础因子计算。

文件：

- `app/providers/market/base.py`
- `app/providers/market/mock_provider.py`
- `app/domain/indicators.py`
- `app/schemas/indicators.py`
- `tests/fixtures/mock_bars.json`

验收：

- 不联网即可生成 indicator snapshot。
- 均线、收益率、成交量比、回撤测试通过。
- 历史不足时输出 `data_status=insufficient_history`。

### Task 4: 交易台账和盈亏

目标：录入一笔交易事实，并计算持仓与基础盈亏。

文件：

- `app/schemas/ledger.py`
- `app/domain/ledger.py`
- `app/domain/pnl.py`
- `app/services/ledger_service.py`
- `app/api/routes/ledger.py`

验收：

- 能新增 ledger entry。
- 能按台账复算数量、成本、已实现和未实现盈亏。
- 减少数量超过持仓时返回明确错误。

### Task 5: 风控和波段状态

目标：基于指标、台账和配置生成非指令化波段状态。

文件：

- `app/schemas/wave_state.py`
- `app/domain/risk.py`
- `app/domain/wave_state.py`
- `app/domain/forbidden_terms.py`
- `app/api/routes/wave_states.py`

验收：

- 输出只使用允许状态标签。
- 数据不足时降级为 `数据不足`。
- 仓位超阈值时输出 `仓位复核候选` 或风险标记。
- 禁用表达扫描测试通过。

### Task 6: 14:55 报告 JSON

目标：只在交易日 14:55 生成结构化 JSON 报告。

文件：

- `app/providers/calendar/base.py`
- `app/providers/calendar/fake_calendar.py`
- `app/providers/calendar/local_calendar.py`
- `app/schemas/reports.py`
- `app/domain/report_builder.py`
- `app/api/routes/reports.py`

验收：

- fake trading day 14:55 可生成报告。
- 非交易日返回 `report_status=blocked`。
- 数据缺失返回 `partial` 或 `blocked`。
- 报告包含 `not_advice=true`。

### Task 7: Codex CLI Provider

目标：实现 fake provider 和真实 Codex CLI provider 封装。

文件：

- `app/schemas/llm.py`
- `app/providers/llm/base.py`
- `app/providers/llm/fake_provider.py`
- `app/providers/llm/codex_cli.py`
- `app/services/llm_service.py`
- `app/api/routes/ai.py`

验收：

- fake provider 可解释 14:55 JSON 报告。
- 真实 provider 检查路径、版本、timeout、退出码。
- 调用日志写入 ai call log。
- 输出含禁用表达时不展示。

### Task 8: 本地 Web MVP

目标：Web 展示最小闭环结果。

文件：

- `web/src/App.tsx`
- `web/src/api/client.ts`
- `web/src/pages/Dashboard.tsx`
- `web/src/pages/Ledger.tsx`
- `web/src/pages/Report.tsx`
- `web/src/components/DataStatusBadge.tsx`
- `web/src/components/RiskBoundaryNotice.tsx`

验收：

- 本地页面可展示自选股、指标、波段状态、盈亏、报告。
- 可录入一笔交易事实。
- 可触发 mock report。
- 页面无越界表达。

### Task 9: 测试和 README

目标：补齐最小验证和普通用户运行说明。

文件：

- `README.md`
- `docs/configuration.md`
- `docs/codex-cli.md`
- `docs/disclaimer.md`
- `tests/unit/`
- `tests/integration/`

验收：

- 默认测试全通过且不依赖网络。
- README 说明 mock/fake 模式、Codex CLI 依赖、免责声明。
- 最小运行命令在 Windows PowerShell 可执行。
- README、报告模板、Web 文案均通过禁用表达扫描。

## 自检结论

本规格明确收缩到最小纵向闭环，所有外部依赖都有 mock/fake 路径，核心计算与 AI 解释层分离，Schema、交易时间、报告降级、禁用表达和测试边界均有明确契约。下一步可以从 Task 1 开始脚手架。
