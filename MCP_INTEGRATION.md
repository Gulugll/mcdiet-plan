# MCP_INTEGRATION.md — 麦当劳 MCP 集成说明

本项目基于麦当劳中国 MCP Server（`https://mcp.mcd.cn`，Streamable HTTP + Bearer Token）开发。

## 实际使用的 Tools

| Tool | 用途 | 调用时机 | 业务价值 |
|---|---|---|---|
| `list-nutrition-foods` | **核心数据源**：餐品营养成分（能量/蛋白/脂肪/碳水/钠等） | 首次运行拉取并缓存至 `data/nutrition_cache.json`；此后读缓存 | 求解器的全部营养输入；项目差异化所在 |
| `query-meals` | 当前门店可售菜单 | 生成计划前（可选） | 过滤不可售单品，保证计划可执行 |
| `query-meal-detail` | 套餐组成与替换项 | 细化套餐配置（可选） | 打卡套餐拆分到单品 |
| `calculate-price` | 含券价格计算 | P2 价格约束 | "预算内最优营养" |
| `auto-bind-coupons` | 一键领券 | P2 下单前 | 省钱叙事 |
| `create-order` | 创建订单 | P2 可选 | 计划页一键下单当天某餐 |
| `now-time-info` | 当前时间 | 会话开始 | 确定挑战开始日期与 Day N |

## 调用流程

```
用户对话（WorkBuddy / 任意 MCP Client，由 SKILL.md 编排）
  │
  ├─ 1. now-time-info                 → 确定挑战起始日
  ├─ 2. list-nutrition-foods          → 营养数据（有缓存则跳过，最多每会话 1 次）
  │      └─ 与 data/nutrition_cache.json 合并（人工补充表兜底缺项）
  ├─ 3. query-meals（可选）           → 过滤不可售单品
  ├─ 4. python -m solver.cli plan     → 本地求解 7×3 餐（不消耗 MCP 调用）
  ├─ 5. python -m solver.cli render   → 本地渲染网页（不消耗 MCP 调用）
  └─ 6. 每日打卡：query-meal-detail（套餐拆分，可选）
         → python -m solver.cli checkin → 本地重排
```

关键设计：**重计算全部在本地完成**，MCP 只承担数据获取，单用户日常使用每天 ≤3 次调用，远低于 600 次/分钟限流。

## 配置示例

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer YOUR_MCP_TOKEN" }
    }
  }
}
```

安全约定：Token 只存在于 MCP Client 配置中，绝不写入本仓库任何文件；仓库内 `data/nutrition_cache.json` 为纯营养数据，无凭证。

## 数据口径说明

- `nutrition_cache.json` 中 `"source": "mcp"` 表示 MCP 实拉数据；`"manual"` 表示人工依据麦当劳中国公开营养信息整理的近似值（当前示例数据，等待接入真实 Token 后替换）。
- 页面输出均注明数据口径与"以麦当劳官方渠道为准"。
