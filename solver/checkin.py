"""打卡状态管理与当日动态重排。"""
from __future__ import annotations

from dataclasses import asdict

from solver.models import FoodItem, Profile
from solver.planner import SLOTS, solve_day
from solver.targets import daily_targets


def new_state(profile: Profile, start_date: str) -> dict:
    """创建初始挑战状态。"""
    return {
        "profile": asdict(profile),
        "targets": daily_targets(profile),
        "start_date": start_date,
        "plan": {},        # {date: {slot: [food dict | code]}}
        "checkins": {},    # {date: {slot: [code, ...]}}
        "weight_log": {},  # {date: kg}
    }


def apply_checkin(state: dict, date: str, meal_slot: str,
                  food_codes: list[str]) -> dict:
    """记录一次打卡（同餐位多次打卡合并去重）。"""
    slot_log = state["checkins"].setdefault(date, {}).setdefault(meal_slot, [])
    for code in food_codes:
        if code not in slot_log:
            slot_log.append(code)
    return state


def used_today(state: dict, date: str, items: list[FoodItem]) -> dict:
    """汇总当日已打卡摄入。"""
    lookup = {i.code: i for i in items}
    sums = {"kcal": 0.0, "protein_g": 0.0, "fat_g": 0.0,
            "carb_g": 0.0, "sodium_mg": 0.0, "price": 0.0}
    for slot_codes in state["checkins"].get(date, {}).values():
        for code in slot_codes:
            food = lookup.get(code)
            if food is None:
                continue
            for key in sums:
                sums[key] += getattr(food, key)
    return sums


def serialize_food(f: FoodItem) -> dict:
    return {
        "code": f.code, "name": f.name, "category": f.category,
        "kcal": f.kcal, "protein_g": f.protein_g, "fat_g": f.fat_g,
        "carb_g": f.carb_g, "sodium_mg": f.sodium_mg,
        "price": f.price, "source": f.source,
    }


def replan_day(state: dict, date: str, items: list[FoodItem],
               seed: int = 0) -> dict:
    """当日动态重排：保留已打卡餐位，按剩余预算重解其余餐位。"""
    profile = Profile(**state["profile"])
    used = used_today(state, date, items)
    checked = state["checkins"].get(date, {})
    open_slots = tuple(s for s in SLOTS if not checked.get(s))

    if not open_slots:
        return state

    # 多样性：以第一天求解时的种子滚动，避免每次重排结果相同
    day = solve_day(items, profile, seed=seed, open_slots=open_slots,
                    kcal_overrides={"used_kcal": used["kcal"]})
    day_plan = state["plan"].setdefault(date, {})
    for slot in open_slots:
        day_plan[slot] = [serialize_food(f) for f in day.get(slot, [])]
    return state


def remaining_today(state: dict, date: str, items: list[FoodItem]) -> dict:
    """当日剩余预算 = 目标 − 已摄入。"""
    used = used_today(state, date, items)
    targets = state.get("targets") or daily_targets(Profile(**state["profile"]))
    return {key: targets[key] - used[key] for key in used}
