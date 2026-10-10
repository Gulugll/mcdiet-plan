"""核心数据模型。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FoodItem:
    """一个可售餐品的营养与价格快照。"""

    code: str
    name: str
    category: str  # 主餐 / 小食 / 饮料 / 早餐 ...
    kcal: float
    protein_g: float
    fat_g: float
    carb_g: float
    sodium_mg: float
    price: float
    source: str = "manual"  # mcp / manual


@dataclass(frozen=True)
class Profile:
    """用户身体数据与目标。"""

    gender: str  # M / F
    age: int
    height_cm: float
    weight_kg: float
    activity: str = "light"  # sedentary / light / moderate / high / extreme
    goal: str = "maintain"  # cut / maintain / bulk
    budget_per_day: float | None = None
    avoid: tuple[str, ...] = ()
