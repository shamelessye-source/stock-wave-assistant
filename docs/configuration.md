# 配置说明

本项目默认使用 mock/fake 模式。clone 后复制 `.env.example`，无需真实密钥、真实 AkShare 或真实 Codex CLI，即可运行本地 MVP。

## 快速开始

```powershell
Copy-Item .env.example .env
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

## 配置文件

- `.env.example`：环境变量模板。复制为 `.env` 后可覆盖 YAML 配置。
- `config/app.yaml`：应用模式、provider、数据库路径和 Codex 配置。
- `config/watchlist.yaml`：自选股清单。mock 模式下 `symbol` 可以为空。
- `config/preferences.yaml`：交易时段、14:55 报告时间和页面偏好。
- `config/factors.yaml`：指标窗口、权重和风险阈值。

## 默认环境变量

```text
APP_MODE=mock
MARKET_PROVIDER=mock
LLM_PROVIDER=codex_cli
ENABLE_CODEX_CLI=false
DATABASE_PATH=./data/app.db
CACHE_DIR=./data/cache
REPORT_DIR=./data/reports
```

`./data/app.db` 和 `./data/reports` 都是项目相对路径，已被 `.gitignore` 忽略。测试会使用临时目录，不污染真实数据目录。

## 自选股配置编辑

普通用户可以在本地 Web 的“设置/自检”页查看和维护自选股清单，不需要直接编辑 YAML。后端仍以 `config/watchlist.yaml` 为本地事实来源，保存时先做格式校验，再通过临时文件替换目标文件，避免半写入配置。

Web/API 字段：

- `name`：名称，必填。
- `symbol`：代码，可留空；填写时使用 `600000.SH`、`000001.SZ`、`430000.BJ` 这类格式。
- `market`：市场，可留空，支持 `SH`、`SZ`、`BJ`。
- `group`：分组。
- `theme`：主题；写回 YAML 时也会同步到兼容字段 `direction`。
- `enabled`：是否启用。
- `observation_note`：观察理由；写回 YAML 时也会同步到兼容字段 `watch_reason`。
- `risk_note`：风险点；写回 YAML 时也会同步到兼容字段 `risk_points`。

接口只做本地格式校验。默认不会访问网络，不调用真实 AkShare，也不会按名称自动补代码。

## Codex CLI

默认解释层使用 fake provider：

```text
ENABLE_CODEX_CLI=false
CODEX_MODEL=gpt-5.5
CODEX_TIMEOUT_SECONDS=120
CODEX_SANDBOX_MODE=read-only
CODEX_CLI_PATH=
```

启用真实 Codex CLI 时，需要用户本机已安装并登录 Codex CLI：

```text
ENABLE_CODEX_CLI=true
CODEX_CLI_PATH=<path-to-codex-cli>
```

真实 provider 只解释 14:55 结构化报告 JSON，不参与行情、指标、盈亏、风控或波段状态计算。配置状态接口只返回安全摘要，不返回本地路径。

## 交易时间

当前 A 股交易时段来自 `config/preferences.yaml`：

```yaml
trading_sessions:
  morning:
    start: "09:30"
    end: "11:30"
  afternoon:
    start: "13:00"
    end: "15:00"
daily_report_time: "14:55"
market:
  closed_dates: []
  extra_open_dates: []
```

交易日判断默认使用工作日 fallback。`market.closed_dates` 可以配置本地休市日，`market.extra_open_dates` 可以配置本地补交易日。非交易日和交易时段外不会写入 run-once 报告。

14:55 run-once 报告默认写入 `REPORT_DIR`：

```powershell
py -m app.cli.preclose_report --as-of 2026-07-01T14:55:00
```

同一交易日重复触发默认返回已有报告；需要覆盖时显式加 `--force`。

## 数据源

当前默认数据源是 mock provider。它读取 `config/watchlist.yaml` 的名称和可选代码，使用固定 seed 生成稳定样例，并覆盖历史不足、成交量异常、价格缺失等降级场景。

AkShare provider 是可选真实数据 adapter。默认关闭，只有设置 `MARKET_PROVIDER=akshare` 时才会启用。启用前需要先安装可选依赖：

```powershell
py -m pip install -e ".[akshare,test]"
```

并在 `config/watchlist.yaml` 中填写股票代码。代码为空时，系统会返回 `code_missing`，不会按名称静默猜测。

AkShare 日线数据会标准化为与 mock 行情一致的字段：

- `trade_date`
- `open`
- `high`
- `low`
- `close`
- `volume`
- `amount`
- `prev_close`

本地缓存目录来自 `CACHE_DIR` 或 `config/app.yaml` 的 `cache.dir`。缓存命中时优先读取本地 JSON，避免每次启动都请求网络。

真实数据模式可能遇到 AkShare 缺失、网络失败、字段变化、返回空数据或数据延迟。系统会返回结构化降级状态，不影响 mock 模式。

手动 smoke：

```powershell
$env:MARKET_PROVIDER="akshare"
$env:CACHE_DIR="./data/cache"
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Invoke-RestMethod http://127.0.0.1:8000/api/market/snapshot
Invoke-RestMethod http://127.0.0.1:8000/api/indicators/snapshot
```

默认测试必须继续保持 mock/fake，不访问网络。

## 边界扫描

可用以下 PowerShell 命令扫描 UI、报告、测试、配置和文档中的越界表达：

```powershell
$terms = @("买"+"入", "卖"+"出", "推"+"荐", "目标"+"价", "保证"+"收益")
rg -n ($terms -join "|") app web tests config docs README.md
```
