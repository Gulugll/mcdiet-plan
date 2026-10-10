---
name: mcdiet-plan
description: 麦门膳食师——一周只吃麦当劳的营养规划挑战。输入身体数据与目标（减脂/维持/增肌），基于麦当劳 MCP 营养数据生成 7×3 餐计划并渲染可视化网页，支持每日打卡动态重排。触发词：一周麦麦挑战、麦麦膳食计划、只吃麦当劳、McDiet。
---

# 麦门膳食师（McDiet Plan）

反向《大号的我》：用麦当劳自己的营养数据证明，目标驱动下连吃一周麦当劳也能落在科学区间。

## 何时触发本 Skill

用户提到：开启"一周麦麦挑战"、想要一周麦麦饮食计划、只吃麦当劳如何减脂/增肌/维持、打卡今天吃的麦麦、查看麦麦计划进度。

## 前置条件

- 项目目录含 `solver/`、`web/template/plan.html`、`data/nutrition_cache.json`
- Python 3.10+（无第三方运行时依赖）
- 如需实时菜单/价格/优惠券：麦当劳 MCP Token（见 MCP_INTEGRATION.md）

## 工作流 A：生成一周计划

1. **收集身体数据**（缺什么问什么，一次问齐）：
   - 性别、年龄、身高 cm、体重 kg
   - 活动量：久坐 / 轻度 / 中度 / 高强度 / 极高
   - 目标：减脂 / 维持 / 增肌
   - 可选：每日预算（元）、忌口关键词（如"辣""牛肉"）
2. **准备营养数据**：优先读 `data/nutrition_cache.json`；若启用 MCP，调用
   `list-nutrition-foods` 刷新缓存（见工作流 C）。**不要在对话中反复调用营养 Tool。**
3. **运行求解器**：
   ```
   python -m solver.cli plan --gender M --age 28 --height 175 --weight 72 \
     --activity light --goal cut --budget 60 --avoid 辣
   ```
4. **渲染网页**：`python -m solver.cli render`，然后把生成的 `plan.html` 展示给用户（present_files / 打开预览）。
5. **解读要点**：向用户说明每日目标热量、蛋白目标，并提醒钠上限与免责声明（非医疗建议）。

## 工作流 B：每日打卡与动态重排

1. 用户说"打卡：中午吃了麦辣鸡腿堡套餐"时，先用套餐名展开（`data/combos.json`，
   如"麦辣鸡腿堡套餐"→ B03+S01+D01），匹配不到预设套餐再按单品模糊匹配营养库。
2. 运行：
   ```
   python -m solver.cli checkin --date 2026-10-12 --slot lunch --combo 麦辣鸡腿堡中套餐
   # 或按单品：--codes B03 S01 D01
   ```
   用户报了晨重就加 `--weight 71.8`。
3. 命令输出会给出**今日剩余热量预算**与三大营养素摄入，并自动重排未打卡餐位。
4. 重新 `render` 并展示网页，用一句话总结："今天还剩 X kcal，晚餐推荐…"。
5. 第 7 天全部打卡后，引导用户查看网页底部的总结图表（体重曲线、达标率）。

## 工作流 C：一键点餐（需 MCP Token）

1. 用户说"帮我把明天的午餐点了"时，运行：
   ```
   python -m solver.cli order --date 2026-10-13 --slot lunch --mode carryout
   ```
   输出该餐的下单内容（含匹配套餐名）与 MCP create-order payload。
2. AI 侧流程：`query-nearby-stores` 选门店（payload 中 store 为空时）→
   `query-meals`/`query-meal-detail` 核对可售与套餐组成 → `calculate-price`（可先
   `auto-bind-coupons` 领券）→ `create-order` → 把支付链接给用户。
3. 用户要取消：`cancel-order`；查进度：`query-order`。
4. 下单前必须把完整订单内容复述给用户确认，确认后才调 create-order。

## 工作流 D：MCP 数据刷新（可选，需 Token）

- `list-nutrition-foods`：拉取营养数据 → 与 `data/nutrition_cache.json` 合并
  （同 code 以 MCP 为准，本地人工补充表用于补缺）。
- `query-meals`：过滤当前门店不可售单品后再求解。
- `calculate-price` / `auto-bind-coupons` / `create-order`：价格约束与下单（P2）。
- **纪律**：所有 MCP 数据先读缓存；单次会话营养 Tool 至多调用 1 次；
  严禁把 Token 写入任何生成文件或对话输出。

## 硬性规则

1. 钠是软约束：求解器会尽量压钠，但麦当劳餐常超 2300mg/天——网页会展示超标提醒，必须向用户如实说明。
2. 每次输出计划都附带免责声明："仅供参考，不构成医疗或营养建议"。
3. 目标热量下限 1200 kcal/天，不可为加速减脂突破。
4. 用户报告的餐品若不在营养库，宁可问清，不要编造营养数据。
