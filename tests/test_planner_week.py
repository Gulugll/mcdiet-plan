"""7 天计划生成与多样性约束的行为测试（TDD：先红后绿）。"""
import pytest

from solver.models import Profile
from solver.nutrition import load_nutrition
from solver.planner import solve_week

PROFILE = Profile(gender="M", age=28, height_cm=175, weight_kg=72,
                  activity="light", goal="cut")


@pytest.fixture
def items():
    return load_nutrition("data/nutrition_cache.json")


def test_solve_week_returns_seven_days(items):
    week = solve_week(items, PROFILE, seed=42)
    assert len(week) == 7
    for day in week:
        assert set(day) == {"breakfast", "lunch", "dinner"}


def test_solve_week_no_food_more_than_three_times(items):
    week = solve_week(items, PROFILE, seed=42)
    counts: dict[str, int] = {}
    for day in week:
        for foods in day.values():
            for f in foods:
                counts[f.code] = counts.get(f.code, 0) + 1
    offenders = {c: n for c, n in counts.items() if n > 3}
    assert not offenders, f"单品出现超过 3 次: {offenders}"


def test_solve_week_lunch_varies_across_days(items):
    week = solve_week(items, PROFILE, seed=42)
    lunch_signatures = [tuple(sorted(f.code for f in d["lunch"])) for d in week]
    assert len(set(lunch_signatures)) >= 4


def test_solve_week_deterministic(items):
    a = solve_week(items, PROFILE, seed=42)
    b = solve_week(items, PROFILE, seed=42)
    assert a == b


def test_solve_week_respects_avoid(items):
    week = solve_week(items, PROFILE, seed=42, avoid=("辣",))
    for day in week:
        for foods in day.values():
            for f in foods:
                assert "辣" not in f.name
