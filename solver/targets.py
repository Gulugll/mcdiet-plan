"""每日目标热量与宏量营养计算（Mifflin-St Jeor）。"""
from __future__ import annotations

from solver.models import Profile

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "high": 1.725,
    "extreme": 1.9,
}

GOAL_FACTOR = {"cut": 0.85, "maintain": 1.0, "bulk": 1.10}

PROTEIN_G_PER_KG = {"cut": 1.6, "maintain": 1.4, "bulk": 1.8}

MIN_KCAL = 1200.0
SODIUM_MAX_MG = 2300.0
MIN_FAT_PCT = 0.20  # 脂肪供能占比下限


def bmr(profile: Profile) -> float:
    """Mifflin-St Jeor 基础代谢率。"""
    base = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age
    return base + (5 if profile.gender == "M" else -161)


def tdee(profile: Profile) -> float:
    """每日总消耗 = BMR × 活动系数。"""
    return bmr(profile) * ACTIVITY_FACTORS[profile.activity]


def daily_targets(profile: Profile) -> dict:
    """输出每日目标：热量、蛋白质、脂肪下限、钠上限。"""
    kcal = max(tdee(profile) * GOAL_FACTOR[profile.goal], MIN_KCAL)
    protein_g = profile.weight_kg * PROTEIN_G_PER_KG[profile.goal]
    fat_min_g = kcal * MIN_FAT_PCT / 9.0
    return {
        "kcal": kcal,
        "protein_g": protein_g,
        "fat_min_g": fat_min_g,
        "carb_hint_g": (kcal - protein_g * 4 - fat_min_g * 9) / 4.0,
        "sodium_max_mg": SODIUM_MAX_MG,
    }
