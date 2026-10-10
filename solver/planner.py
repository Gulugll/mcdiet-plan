"""三餐求解器：候选组合枚举 + 随机重启贪心，纯标准库。

设计说明：
- 热量带是主约束；钠在当前菜单数据下无法在 2300mg 内同时满足较高热量目标，
  因此作为强权重软约束处理，由调用方（网页/SKILL）展示"钠超标提醒"。
- 多样性：同一餐内不重复单品（惩罚）；与前一天同餐位重复的单品在存在
  替代方案时被硬排除。
"""
from __future__ import annotations

import random

from solver.models import FoodItem, Profile
from solver.nutrition import filter_foods
from solver.targets import daily_targets

SLOTS = ("breakfast", "lunch", "dinner")
SLOT_SHARES = {"breakfast": 0.30, "lunch": 0.40, "dinner": 0.30}
SLOT_NAMES = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"}

KCAL_BAND = (0.55, 1.45)   # 单餐组合热量窗口（相对单餐目标）
N_RESTARTS = 300           # 随机重启次数

# 归一化目标函数权重（各项均在相近量级上比较）
W_KCAL = 2.0               # |热量偏差| / 100 kcal（主约束）
W_PROTEIN = 0.3            # 蛋白缺口 / 10 g
W_FAT = 0.3                # 脂肪缺口 / 10 g
W_FAT_MAX = 0.5            # 脂肪超上限 / 10 g（减脂向硬倾向）
W_CARB = 0.3               # 碳水缺口 / 10 g
W_SODIUM = 1.0             # 钠超标 / 100 mg
W_REPEAT = 10.0            # 同餐内重复单品，每个


def _slot_categories(slot: str) -> tuple[str, str, str]:
    """返回（主项, 加项, 饮料）的品类。"""
    if slot == "breakfast":
        return ("早餐", "早餐", "饮料")
    return ("主餐", "小食", "饮料")


def totals(foods: list[FoodItem]) -> dict:
    return {
        "kcal": sum(f.kcal for f in foods),
        "protein_g": sum(f.protein_g for f in foods),
        "fat_g": sum(f.fat_g for f in foods),
        "carb_g": sum(f.carb_g for f in foods),
        "sodium_mg": sum(f.sodium_mg for f in foods),
        "price": sum(f.price for f in foods),
    }


def _slot_cost(foods: list[FoodItem], slot_kcal: float, slot_protein: float,
               slot_fat_min: float, slot_fat_max: float, slot_sodium: float,
               slot_carb: float) -> float:
    t = totals(foods)
    cost = W_KCAL * abs(t["kcal"] - slot_kcal) / 100.0
    cost += W_PROTEIN * max(0.0, slot_protein - t["protein_g"]) / 10.0
    cost += W_FAT * max(0.0, slot_fat_min - t["fat_g"]) / 10.0
    cost += W_FAT_MAX * max(0.0, t["fat_g"] - slot_fat_max) / 10.0
    cost += W_CARB * max(0.0, slot_carb - t["carb_g"]) / 10.0
    cost += W_SODIUM * max(0.0, t["sodium_mg"] - slot_sodium) / 100.0
    return cost


def build_candidates(items: list[FoodItem], slot: str, slot_kcal: float,
                     avoid: tuple[str, ...] = ()) -> list[list[FoodItem]]:
    """枚举某餐位候选组合：主项 + 可选加项 + 饮料，热量窗口过滤。"""
    cat_main, cat_extra, cat_drink = _slot_categories(slot)
    ok = filter_foods(items, avoid)
    mains = [f for f in ok if f.category == cat_main]
    extras = [f for f in ok if f.category == cat_extra]
    drinks = [f for f in ok if f.category == cat_drink]
    if not mains or not drinks:
        return []

    lo, hi = KCAL_BAND[0] * slot_kcal, KCAL_BAND[1] * slot_kcal
    out: list[list[FoodItem]] = []
    for main in mains:
        for extra in extras + [None]:
            base = [main] + ([extra] if extra else [])
            base_kcal = sum(f.kcal for f in base)
            for drink in drinks:
                kcal = base_kcal + drink.kcal
                if lo <= kcal <= hi:
                    out.append(base + [drink])
    return out


def _diversity_penalty(combo: list[FoodItem], prev_slot: list[str]) -> float:
    codes = [f.code for f in combo]
    cost = W_REPEAT * (len(codes) - len(set(codes)))
    return cost


def solve_day(items: list[FoodItem], profile: Profile, seed: int = 0,
              avoid: tuple[str, ...] | None = None,
              prev_day_codes: dict[str, list[str]] | None = None,
              kcal_overrides: dict[str, float] | None = None,
              open_slots: tuple[str, ...] | None = None
              ) -> dict[str, list[FoodItem]]:
    """求解一天三餐。

    prev_day_codes: 前一天各餐位的单品 code（多样性约束）。
    kcal_overrides: 打卡重排用，{"used_kcal": 当日已摄入}。
    open_slots: 只求解这些餐位（已打卡餐位由调用方保留），份额按比例重归一。
    """
    avoid = tuple(avoid) if avoid is not None else tuple(profile.avoid)
    slots = tuple(open_slots) if open_slots else SLOTS
    prev = prev_day_codes or {}
    targets = daily_targets(profile)
    used_kcal = (kcal_overrides or {}).get("used_kcal", 0.0)
    remaining_kcal = max(targets["kcal"] - used_kcal, targets["kcal"] * 0.3)
    share_sum = sum(SLOT_SHARES[s] for s in slots) or 1.0

    rng = random.Random(seed)
    cands: dict[str, list[list[FoodItem]]] = {}
    for slot in slots:
        cands[slot] = build_candidates(
            items, slot, remaining_kcal * SLOT_SHARES[slot] / share_sum, avoid)
        # 硬排除与前一天同餐位重复的组合（存在替代方案时）
        prev_codes = set(prev.get(slot, []))
        if prev_codes:
            fresh = [c for c in cands[slot]
                     if not {f.code for f in c} & prev_codes]
            if fresh:
                cands[slot] = fresh

    slot_ctx = {
        slot: (remaining_kcal * SLOT_SHARES[slot] / share_sum,
               targets["protein_g"] * SLOT_SHARES[slot] / share_sum,
               targets["fat_min_g"] * SLOT_SHARES[slot] / share_sum,
               targets["fat_max_g"] * SLOT_SHARES[slot] / share_sum,
               targets["sodium_max_mg"] * SLOT_SHARES[slot] / share_sum,
               targets["carb_hint_g"] * SLOT_SHARES[slot] / share_sum)
        for slot in slots
    }

    # 基线：每餐独立取代价最小组合（贪心）
    plan: dict[str, list[FoodItem]] = {}
    for slot in slots:
        if cands[slot]:
            plan[slot] = min(
                cands[slot],
                key=lambda c: _slot_cost(c, *slot_ctx[slot]))
        else:
            plan[slot] = []

    def day_cost(p: dict[str, list[FoodItem]]) -> float:
        cost = sum(_slot_cost(p[s], *slot_ctx[s]) for s in slots if p[s])
        for foods in p.values():
            cost += _diversity_penalty(foods, [])
        # 跨餐位重复惩罚：同一天同一单品只应出现一次
        codes = [f.code for foods in p.values() for f in foods]
        cost += W_REPEAT * (len(codes) - len(set(codes)))
        return cost

    # 局部搜索：随机变异一餐，保留改进
    best_cost = day_cost(plan)
    best_plan = plan
    for _ in range(N_RESTARTS):
        slot = rng.choice(slots)
        if not cands[slot]:
            continue
        trial = {s: list(v) for s, v in best_plan.items()}
        trial[slot] = rng.choice(cands[slot])
        tc = day_cost(trial)
        if tc < best_cost:
            best_cost = tc
            best_plan = trial

    return best_plan or {slot: [] for slot in slots}


MAX_WEEKLY_REPEATS = 3  # 同一单品全周最多出现次数


def solve_week(items: list[FoodItem], profile: Profile, seed: int = 0,
               avoid: tuple[str, ...] | None = None
               ) -> list[dict[str, list[FoodItem]]]:
    """生成 7 天计划：逐日求解，滚动传递前一天 code，并限制全周重复。"""
    avoid = tuple(avoid) if avoid is not None else tuple(profile.avoid)
    week: list[dict[str, list[FoodItem]]] = []
    week_counts: dict[str, int] = {}
    slot_history: dict[str, list[str]] = {s: [] for s in SLOTS}

    for day_idx in range(7):
        day_seed = seed + day_idx
        # 多样性：与本周同餐位所有历史天的 code 错开（存在替代方案时）
        prev = {s: list(codes) for s, codes in slot_history.items()} if week else None
        # 过滤全周已用满次数的单品
        exhausted = {c for c, n in week_counts.items() if n >= MAX_WEEKLY_REPEATS}
        day_items = [f for f in items if f.code not in exhausted]
        day = solve_day(day_items, profile, seed=day_seed, avoid=avoid,
                        prev_day_codes=prev)
        for slot in SLOTS:
            slot_history[slot].extend(f.code for f in day.get(slot, []))
            for f in day.get(slot, []):
                week_counts[f.code] = week_counts.get(f.code, 0) + 1
        week.append(day)
    return week
