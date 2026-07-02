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
```

`./data/app.db` 是项目相对路径，已被 `.gitignore` 忽略。测试会使用临时数据库，不污染真实数据目录。

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
```

第一版交易日判断只使用工作日 fallback。非交易日和交易时段外会在报告中返回降级状态。

## 数据源

当前默认数据源是 mock provider。它读取 `config/watchlist.yaml` 的名称和可选代码，使用固定 seed 生成稳定样例，并覆盖历史不足、成交量异常、价格缺失等降级场景。

真实 AkShare provider 是后续任务。默认测试必须继续保持 mock/fake。

## 边界扫描

可用以下 PowerShell 命令扫描 UI、报告、测试、配置和文档中的越界表达：

```powershell
$terms = @("买"+"入", "卖"+"出", "推"+"荐", "目标"+"价", "保证"+"收益")
rg -n ($terms -join "|") app web tests config docs README.md
```
