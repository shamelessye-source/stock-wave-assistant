# 后续路线图

当前版本完成本地 mock MVP。后续任务应继续保持 mock/fake 默认和最小改动原则。

## 已完成

- Task 1：项目脚手架和设计规格。
- Task 2：配置加载和 SQLite 初始化。
- Task 3：mock 行情与基础指标。
- Task 4：手动交易台账和基础盈亏。
- Task 5：组合风控和波段状态。
- Task 6：14:55 结构化报告 JSON。
- Task 7：Codex CLI provider 和 fake 解释层。
- Task 8：本地 Web MVP。
- Task 9：测试收口、README 和文档整理。
- Task 10：AkShare adapter 和本地缓存。
- Task 11：交易日历本地配置、14:55 run-once 和报告落盘。
- Task 12：自选股配置编辑、格式校验和本地 Web 维护入口。

## 近期待办

- 增加更清晰的前端 smoke 脚本，便于 CI 或本地一键验证。
- 扩展 AkShare adapter 的真实环境 smoke 记录，但默认测试继续使用 mock/fake。
- 后续可接 Windows Task Scheduler 或轻量常驻 scheduler。
- 增加更完整的配置导入/导出说明和示例。

## 暂不进入 MVP 的事项

- 券商账户连接。
- 自动化交易动作。
- 桌面封装。
- 云同步和多用户部署。
- 机器学习预测。
- 完整回测平台。

## 质量要求

- 默认测试不得访问网络。
- 默认测试不得调用真实 Codex CLI。
- 核心计算不得依赖 LLM。
- UI、报告和测试样例保持中性表达。
- 配置状态接口不得暴露本地敏感路径。
