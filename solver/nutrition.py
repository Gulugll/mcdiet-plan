"""营养库：加载、忌口过滤、人工数据与 MCP 数据合并。"""
from __future__ import annotations

import json
from pathlib import Path

from solver.models import FoodItem


def load_nutrition(path: str | Path) -> list[FoodItem]:
    """从缓存 JSON 加载营养库。"""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [FoodItem(**item) for item in data["items"]]


def filter_foods(items: list[FoodItem], avoid: list[str] | tuple[str, ...]) -> list[FoodItem]:
    """按忌口关键词过滤（名称包含即排除）。"""
    return [f for f in items if not any(kw in f.name for kw in avoid)]


def merge_manual(
    mcp_items: list[dict], manual_items: list[dict]
) -> list[dict]:
    """以 code 为主键合并：manual 覆盖 mcp 的同码条目。"""
    merged: dict[str, dict] = {item["code"]: dict(item) for item in mcp_items}
    for item in manual_items:
        merged[item["code"]] = dict(item)
    return list(merged.values())
