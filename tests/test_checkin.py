"""打卡状态管理与动态重排的行为测试（TDD：先红后绿）。"""
import copy

import pytest

from solver.checkin import apply_checkin, new_state, replan_day, used_today
from solver.models import Profile
from solver.nutrition import load_nutrition
from solver.planner import solve_week
from solver.targets import daily_targets

PROFILE = Profile(gender="M", age=28, height_cm=175, weight_kg=72,
                  activity="light", goal="cut")
DATE = "2026-10-12"


@pytest.fixture
def items():
    return load_nutrition("data/nutrition_cache.json")


@pytest.fixture
def state(items):
    st = new_state(PROFILE, DATE)
    st["plan"] = {DATE: serialize_week_day(solve_week(items, PROFILE, seed=42)[0])}
    return st


def serialize_week_day(day):
    return {slot: [f.code for f in foods] for slot, foods in day.items()}


def test_new_state_has_profile_and_empty_checkins():
    st = new_state(PROFILE, DATE)
    assert st["profile"]["weight_kg"] == 72
    assert st["checkins"] == {}
    assert st["weight_log"] == {}


def test_apply_checkin_records_codes(state):
    st = apply_checkin(state, DATE, "lunch", ["B01", "S01", "D01"])
    assert st["checkins"][DATE]["lunch"] == ["B01", "S01", "D01"]


def test_apply_checkin_twice_merges(state):
    st = apply_checkin(state, DATE, "lunch", ["B01"])
    st = apply_checkin(state, DATE, "lunch", ["S01"])
    assert st["checkins"][DATE]["lunch"] == ["B01", "S01"]


def test_used_today_sums_from_items(state, items):
    st = apply_checkin(state, DATE, "lunch", ["B01"])  # 巨无霸 508 kcal
    u = used_today(st, DATE, items)
    assert u["kcal"] == pytest.approx(508)
    assert u["sodium_mg"] == pytest.approx(930)


def test_replan_day_shrinks_dinner_after_big_lunch(state, items):
    # 打卡一份约 1300 kcal 的午餐 → 剩余预算骤减 → 晚餐应被重排到预算内
    st = apply_checkin(state, DATE, "lunch", ["B01", "S01", "D06"])  # 508+328+150=986
    targets = daily_targets(PROFILE)
    remaining = targets["kcal"] - 986

    st2 = replan_day(st, DATE, items, seed=42)
    dinner = st2["plan"][DATE]["dinner"]
    codes = [f["code"] for f in dinner]
    dinner_kcal = sum(next(i.kcal for i in items if i.code == c) for c in codes)

    assert 0 < dinner_kcal <= remaining * 1.10 + 1


def test_replan_day_keeps_checked_slots(state, items):
    st = apply_checkin(state, DATE, "lunch", ["B01"])
    st2 = replan_day(st, DATE, items, seed=42)
    assert st2["plan"][DATE]["lunch"] == state["plan"][DATE]["lunch"]
