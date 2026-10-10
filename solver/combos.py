"""套餐（组合餐）匹配与展开。"""
from __future__ import annotations

import json
from pathlib import Path

COMBOS_PATH = Path(__file__).resolve().parent.parent / "data" / "combos.json"


def load_combos(path: str | Path = COMBOS_PATH) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["combos"]


def match_combo(combos: list[dict], codes: list[str]) -> str | None:
    """给一组单品 code，返回完全匹配的套餐名（顺序无关）。"""
    want = set(codes)
    for c in combos:
        if set(c["items"]) == want and len(c["items"]) == len(codes):
            return c["name"]
    return None


def expand_combo(combos: list[dict], name: str) -> list[str] | None:
    """按名称（支持包含匹配，自动去掉泛称"套餐"）展开为单品 code 列表。"""
    q = name.replace("套餐", "").replace("中套餐", "")
    for c in combos:
        if name == c["name"] or (q and q in c["name"]):
            return list(c["items"])
    return None
