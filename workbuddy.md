# workbuddy.md — WorkBuddy 开发过程记录

本文件记录使用 WorkBuddy 开发本项目的对话上下文，用于核验 WorkBuddy 联动活动奖励条件。

## 开发过程摘要（2026-10-10）

1. **赛事调研**：通过 WorkBuddy 联网能力研读麦当劳程序员创意开发大赛规则（M-China/mcd-developer-innovation-challenge）与麦当劳 MCP Server 工具清单（M-China/mcd-mcp-server），确认排名规则（GitHub Star）、交付物要求与全部 30+ MCP Tools。
2. **创意头脑风暴**：在 WorkBuddy 中对比多个创意方向（代码犒劳机、省钱背包优化器、热量预算管家等），用户提出"假如一周都吃麦当劳 + 输入身体数据和目标"，确认其"反向《大号的我》"叙事价值并深化为最终方案。
3. **方案设计**：使用 WorkBuddy 的 superpowers 工程方法论，先头脑风暴确认形态（WorkBuddy Skill + 单文件网页模板 + 7 天打卡闭环），产出完整设计方案与 14 项实施计划。
4. **TDD 开发**：在 WorkBuddy Agent 模式下按测试驱动完成全部核心模块——营养库（nutrition）、目标计算（targets，Mifflin-St Jeor）、三餐求解器（planner，贪心+局部搜索）、打卡重排（checkin）、渲染器（render），30 个单元测试全绿。
5. **产品组装**：SKILL.md（AI 编排规范）、CLI（plan/checkin/render）、单文件可视化网页模板（Chart.js）、README / MCP_INTEGRATION / LICENSE 等参赛交付物。

## 主要对话成果

- 设计方案：`docs/` 内设计文档沉淀（探索过的替代方案与决策理由）
- 完整可运行项目：`solver/` + `web/` + `SKILL.md`，`python -m solver.cli plan --demo` 端到端可用
