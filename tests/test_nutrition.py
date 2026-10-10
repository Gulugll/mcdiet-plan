"""营养库加载 / 忌口过滤 / 数据源合并的行为测试（TDD：先红后绿）。"""
import json
from pathlib import Path

import pytest

from solver.nutrition import filter_foods, load_nutrition, merge_manual

SAMPLE = {
    "fetched_at": "2026-10-10",
    "items": [
        {"code": "M001", "name": "板烧鸡腿堡", "category": "主餐",
         "kcal": 415, "protein_g": 22, "fat_g": 17, "carb_g": 41,
         "sodium_mg": 890, "price": 24.5, "source": "manual"},
        {"code": "M002", "name": "麦辣鸡腿堡", "category": "主餐",
         "kcal": 530, "protein_g": 24, "fat_g": 27, "carb_g": 46,
         "sodium_mg": 1030, "price": 25.5, "source": "manual"},
        {"code": "M003", "name": "无糖可乐", "category": "饮料",
         "kcal": 0, "protein_g": 0, "fat_g": 0, "carb_g": 0,
         "sodium_mg": 10, "price": 0, "source": "manual"},
    ],
}

_CACHE_PATH = Path(__file__).parent / ".tmp" / "nutrition_test_cache.json"


@pytest.fixture
def cache_file():
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(SAMPLE, ensure_ascii=False), encoding="utf-8")
    yield _CACHE_PATH
    _CACHE_PATH.unlink(missing_ok=True)


def test_load_returns_food_items(cache_file):
    items = load_nutrition(cache_file)
    assert len(items) == 3
    board = items[0]
    assert board.code == "M001"
    assert board.name == "板烧鸡腿堡"
    assert board.kcal == 415
    assert board.category == "主餐"


def test_filter_foods_removes_avoid_keyword(cache_file):
    items = load_nutrition(cache_file)
    kept = filter_foods(items, avoid=["辣"])
    names = [f.name for f in kept]
    assert "麦辣鸡腿堡" not in names
    assert "板烧鸡腿堡" in names


def test_filter_foods_empty_avoid_keeps_all(cache_file):
    items = load_nutrition(cache_file)
    assert len(filter_foods(items, avoid=[])) == 3


def test_merge_manual_overrides_mcp_on_same_code():
    mcp = [SAMPLE["items"][0] | {"source": "mcp", "price": 0}]
    manual = [SAMPLE["items"][0] | {"price": 24.5, "source": "manual"}]
    merged = merge_manual(mcp, manual)
    assert len(merged) == 1
    assert merged[0]["price"] == 24.5
    assert merged[0]["source"] == "manual"
