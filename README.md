# A 股自选股波段切换决策助手

本项目是一个本地运行的研究与决策辅助工具。第一版优先打通 mock MVP：自选股配置、mock 行情、基础指标、波段状态、手动成交记录、基础盈亏、14:55 结构化报告、可选解释摘要和本地 Web 展示。

本项目只展示基于本地规则和当前数据的观察结果，不构成投资建议。请结合个人风险承受能力独立决策。

## 功能清单

- 自选股配置：读取 `config/watchlist.yaml`。
- Mock 行情：默认生成稳定日线样例，不访问网络。
- AkShare adapter：可选真实日线数据源，必须显式开启。
- 基础指标：MA20、MA60、5/10/20 日动量、最大回撤、简化 ATR、成交量比值。
- 手动台账：记录中性方向的成交事实，使用移动平均成本法计算基础盈亏。
- 组合风控：展示持仓市值、盈亏、集中度和数据完整性状态。
- 波段状态：输出允许状态标签、分项分数和原因。
- 14:55 报告：生成结构化 JSON，支持 `as_of` 测试参数。
- 14:55 run-once：可手动触发一次报告生成并写入本地 `REPORT_DIR`。
- Codex CLI 解释层：默认 fake provider；真实模式需要显式启用。
- 本地 Web MVP：提供总览、指标、风控、波段、台账、报告和设置/自检页面。

## 不做什么

- 不连接券商账户。
- 不保存交易密码、资金账号或其他交易凭据。
- 不生成订单，不做自动交易。
- 不默认接真实 AkShare 数据源；真实模式必须由用户显式开启。
- 不做定时调度；14:55 报告当前通过 API 或页面手动触发。
- 不默认启动后台常驻 scheduler；第一版只提供 run-once 入口。
- 不让 Codex 或任何 LLM 参与行情、指标、盈亏、风控或波段状态计算。
- 不提供个股推介、直接交易指令、预设价位或收益承诺。

## 安装

需要 Python 3.11+、Node.js 和 npm。

```powershell
py -m pip install -e ".[test]"
npm.cmd install
Copy-Item .env.example .env
```

默认配置已经是 mock/fake 模式。clone 后不需要真实密钥，也不需要真实 Codex CLI，即可运行 MVP。

如需手动验证真实 AkShare 数据源，可安装可选 extra：

```powershell
py -m pip install -e ".[akshare,test]"
```

## 启动后端

```powershell
py -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

常用接口：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/config/status
Invoke-RestMethod "http://127.0.0.1:8000/api/reports/preclose?as_of=2026-07-01T14:55:00"
Invoke-RestMethod -Method Post -ContentType "application/json" -Body '{"as_of":"2026-07-01T14:55:00"}' http://127.0.0.1:8000/api/reports/preclose/run-once
```

本地 run-once CLI：

```powershell
py -m app.cli.preclose_report --as-of 2026-07-01T14:55:00
```

## 启动前端

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

浏览器打开 `http://127.0.0.1:5173`。如后端地址不同，可设置：

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000"
```

## 测试

```powershell
py -m pytest -q
npm.cmd run build
$terms = @("买"+"入", "卖"+"出", "推"+"荐", "目标"+"价", "保证"+"收益")
rg -n ($terms -join "|") app web tests config docs README.md
```

本仓库的默认测试不得访问网络，不得调用真实 AkShare，不得真实调用 Codex CLI。

## 配置说明

主要配置文件：

- `.env.example`：环境变量示例。
- `config/app.yaml`：应用模式、provider、SQLite 路径和 Codex 配置。
- `config/watchlist.yaml`：自选股清单，mock 模式下代码可以留空。
- `config/preferences.yaml`：A 股交易时段、14:55 报告时间和显示偏好。
- `config/factors.yaml`：基础指标窗口、权重和阈值。

SQLite 默认路径是项目相对路径 `./data/app.db`。该目录已被 `.gitignore` 忽略。
报告默认写入项目相对路径 `./data/reports`。该目录已被 `.gitignore` 忽略。

## Codex CLI 模式

默认：

```text
ENABLE_CODEX_CLI=false
LLM_PROVIDER=codex_cli
CODEX_MODEL=gpt-5.5
CODEX_TIMEOUT_SECONDS=120
CODEX_SANDBOX_MODE=read-only
```

fake provider 会返回稳定中文摘要，适合测试和本地 MVP。

真实 Codex CLI 模式需要用户本机已安装并登录 Codex CLI，然后显式配置：

```text
ENABLE_CODEX_CLI=true
CODEX_CLI_PATH=<path-to-codex-cli>
```

真实 provider 只解释 14:55 结构化报告 JSON，不参与核心计算。`/api/config/status` 只展示安全摘要，不返回本地路径。

## 数据源说明

当前默认数据源是 mock provider。它从 `config/watchlist.yaml` 读取名称，使用固定 seed 生成稳定样例，并保留历史不足、成交量异常、价格缺失等降级场景。

真实 AkShare provider 已通过 adapter 接入，但默认关闭。启用前需要：

1. 在 `config/watchlist.yaml` 中填写股票代码，例如 `000001.SZ` 或 `600000.SH`。
2. 安装可选依赖：`py -m pip install -e ".[akshare,test]"`。
3. 设置 `MARKET_PROVIDER=akshare`。
4. 启动后端并检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/market/snapshot
Invoke-RestMethod http://127.0.0.1:8000/api/indicators/snapshot
```

如果代码为空、AkShare 缺失、网络失败、字段变化或返回空数据，接口会返回结构化降级状态。默认测试仍保持 mock/fake，不访问网络。

## 文档

- [配置说明](docs/configuration.md)
- [架构说明](docs/architecture.md)
- [API 概览](docs/api-overview.md)
- [状态标签说明](docs/status-labels.md)
- [后续路线图](docs/roadmap.md)

## 免责声明

本项目只做研究和决策辅助，不构成投资建议。结构化报告、状态标签、分数和解释摘要都需要用户自行复核。
