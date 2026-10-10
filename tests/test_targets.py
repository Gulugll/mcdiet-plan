"""每日目标热量与宏量计算的行为测试（TDD：先红后绿）。"""
import pytest

from solver.models import Profile
from solver.targets import bmr, daily_targets, tdee


def test_bmr_mifflin_st_jeor_male():
    # 男性 28 岁 175cm 72kg → 10*72 + 6.25*175 - 5*28 + 5 = 1678.75
    p = Profile(gender="M", age=28, height_cm=175, weight_kg=72)
    assert bmr(p) == pytest.approx(1678.75)


def test_bmr_mifflin_st_jeor_female():
    # 女性 30 岁 160cm 55kg → 10*55 + 6.25*160 - 5*30 - 161 = 1239.0
    p = Profile(gender="F", age=30, height_cm=160, weight_kg=55)
    assert bmr(p) == pytest.approx(1239.0)


def test_tdee_activity_factor():
    p = Profile(gender="M", age=28, height_cm=175, weight_kg=72, activity="light")
    assert tdee(p) == pytest.approx(1678.75 * 1.375)


def test_cut_target_is_15pct_below_tdee():
    p = Profile(gender="M", age=28, height_cm=175, weight_kg=72,
                activity="light", goal="cut")
    t = daily_targets(p)
    assert t["kcal"] == pytest.approx(1678.75 * 1.375 * 0.85, rel=1e-6)


def test_cut_target_floor_1200_kcal():
    # 极端小个子女性减脂也不得低于 1200 kcal
    p = Profile(gender="F", age=45, height_cm=145, weight_kg=40,
                activity="sedentary", goal="cut")
    t = daily_targets(p)
    assert t["kcal"] == pytest.approx(1200.0)


def test_bulk_target_is_10pct_above_tdee():
    p = Profile(gender="M", age=28, height_cm=175, weight_kg=72,
                activity="light", goal="bulk")
    t = daily_targets(p)
    assert t["kcal"] == pytest.approx(1678.75 * 1.375 * 1.10, rel=1e-6)


def test_protein_gram_target_for_cut():
    # 健身向：减脂 2.0 g/kg → 72 * 2.0 = 144
    p = Profile(gender="M", age=28, height_cm=175, weight_kg=72, goal="cut")
    t = daily_targets(p)
    assert t["protein_g"] == pytest.approx(144.0)


def test_fat_upper_bound_present():
    # 脂肪上限 = 30% 供能：1962*1.077... 具体值按目标热量算，占位断言键存在且为正
    p = Profile(gender="M", age=28, height_cm=175, weight_kg=72, goal="cut")
    t = daily_targets(p)
    assert t["fat_max_g"] == pytest.approx(t["kcal"] * 0.30 / 9.0)
    assert t["fat_max_g"] > t["fat_min_g"]


def test_sodium_cap_present():
    p = Profile(gender="M", age=28, height_cm=175, weight_kg=72)
    t = daily_targets(p)
    assert t["sodium_max_mg"] == 2300
