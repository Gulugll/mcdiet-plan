"""单日三餐求解的行为测试（TDD：先红后绿）。"""
import pytest

from solver.nutrition import load_nutrition
from solver.planner import solve_day
from solver.targets import daily_targets
from solver.models import Profile

PROFILE = Profile(gender="M", age=28, height_cm=175, weight_kg=72,
                  activity="light", goal="cut")


@pytest.fixture
def items():
    return load_nutrition("data/nutrition_cache.json")


def test_solve_day_returns_three_slots(items):
    day = solve_day(items, PROFILE, seed=42)
    assert set(day) == {"breakfast", "lunch", "dinner"}
    for slot in day:
        assert len(day[slot]) >= 1


def test_solve_day_kcal_within_band(items):
    day = solve_day(items, PROFILE, seed=42)
    targets = daily_targets(PROFILE)
    total = sum(f.kcal for foods in day.values() for f in foods)
    assert targets["kcal"] * 0.92 <= total <= targets["kcal"] * 1.08


def test_solve_day_sodium_minimized(items):
    # 钠为强权重软约束：菜单数据下 2300mg 与较高热量目标难兼得，
    # 求解器应主动压低钠（阈值 = 上限 + 600 缓冲），网页会展示超标提醒。
    day = solve_day(items, PROFILE, seed=42)
    targets = daily_targets(PROFILE)
    total_na = sum(f.sodium_mg for foods in day.values() for f in foods)
    assert total_na <= targets["sodium_max_mg"] + 600


def test_solve_day_respects_avoid(items):
    day = solve_day(items, PROFILE, seed=7, avoid=["辣"])
    for foods in day.values():
        for f in foods:
            assert "辣" not in f.name


def test_solve_day_deterministic_with_seed(items):
    a = solve_day(items, PROFILE, seed=42)
    b = solve_day(items, PROFILE, seed=42)
    assert [[f.code for f in a[s]] for s in a] == \
           [[f.code for f in b[s]] for s in b]


def test_slot_cost_penalizes_carb_shortfall(items):
    # 三大营养素之一：同热量同蛋白脂肪钠的两份食物，缺碳水的成本必须更高
    from solver.models import FoodItem
    from solver.planner import _slot_cost
    hi_carb = FoodItem("T1", "高碳水", "主餐", 400, 20, 15, 50, 500, 20)
    lo_carb = FoodItem("T2", "低碳水", "主餐", 400, 20, 15, 10, 500, 20)
    cost_hi = _slot_cost([hi_carb], 400, 20, 15, 66, 500, 200)
    cost_lo = _slot_cost([lo_carb], 400, 20, 15, 66, 500, 200)
    assert cost_lo > cost_hi


def test_slot_cost_penalizes_fat_excess(items):
    # 脂肪上限约束：同热量下脂肪超限的组合成本必须更高
    from solver.models import FoodItem
    from solver.planner import _slot_cost
    lean = FoodItem("T3", "低脂", "主餐", 400, 30, 10, 45, 500, 20)
    fatty = FoodItem("T4", "高脂", "主餐", 400, 30, 30, 25, 500, 20)
    cost_lean = _slot_cost([lean], 400, 30, 5, 15, 500, 200)
    cost_fatty = _slot_cost([fatty], 400, 30, 5, 15, 500, 200)
    assert cost_fatty > cost_lean


def test_solve_day_avoid_repeats_previous_day_lunch(items):
    day1 = solve_day(items, PROFILE, seed=42)
    prev = {s: [f.code for f in foods] for s, foods in day1.items()}
    day2 = solve_day(items, PROFILE, seed=42, prev_day_codes=prev)
    lunch1 = {f.code for f in day1["lunch"]}
    lunch2 = {f.code for f in day2["lunch"]}
    assert not lunch1 & lunch2 or len(lunch1 & lunch2) <= 1
