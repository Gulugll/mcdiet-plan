"""套餐匹配与展开的行为测试（TDD：先红后绿）。"""
import pytest

from solver.combos import expand_combo, load_combos, match_combo


@pytest.fixture
def combos():
    return load_combos()


def test_load_combos_returns_list(combos):
    assert isinstance(combos, list) and len(combos) >= 5
    assert {"name", "items"} <= set(combos[0])


def test_match_combo_exact_code_set():
    combos = [{"name": "巨无霸中套餐", "items": ["B01", "S01", "D01"]}]
    assert match_combo(combos, ["D01", "B01", "S01"]) == "巨无霸中套餐"


def test_match_combo_no_match_returns_none():
    combos = [{"name": "巨无霸中套餐", "items": ["B01", "S01", "D01"]}]
    assert match_combo(combos, ["B01"]) is None


def test_expand_combo_by_name(combos):
    codes = expand_combo(combos, "巨无霸中套餐")
    assert codes == ["B01", "S01", "D01"]


def test_expand_combo_partial_name(combos):
    codes = expand_combo(combos, "麦辣套餐")
    assert "B03" in codes


def test_expand_combo_unknown_returns_none(combos):
    assert expand_combo(combos, "不存在的套餐") is None
