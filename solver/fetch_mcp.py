"""从麦当劳 MCP 拉取真实营养数据并刷新缓存。

用法：
  MCD_MCP_TOKEN=xxx python -m solver.fetch_mcp

- Token 只从环境变量读取，绝不写入任何文件。
- 数据格式：tools/call list-nutrition-foods 返回的文本块（\n 字面量分隔）。
- 类别按名称启发式归类；价格沿用人工表（同名匹配），缺省 0。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "data" / "nutrition_cache.json"
MCP_URL = "https://mcp.mcd.cn"

SNACK_KW = ("薯条", "派", "新地", "旋风", "玉米杯", "麦乐鸡", "鸡翅", "圆筒",
            "色拉", "沙拉", "脆薯饼")
DRINK_KW = ("可乐", "咖啡", "拿铁", "茶", "汁", "牛奶", "豆浆", "水", "奶昔",
            "冰饮", "柠檬", "鲜煮", "零度")
BREAKFAST_KW = ("麦满分", "早晨全餐", "热香饼")


def _classify(name: str) -> str:
    if any(k in name for k in BREAKFAST_KW):
        return "早餐"
    if any(k in name for k in DRINK_KW):
        return "饮料"
    if any(k in name for k in SNACK_KW):
        return "小食"
    return "主餐"


def _code(name: str) -> str:
    return "MCP" + hashlib.md5(name.encode()).hexdigest()[:6]


def _call_tool(token: str, name: str, arguments: dict) -> str:
    req = urllib.request.Request(
        MCP_URL,
        data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                         "params": {"name": name, "arguments": arguments}}).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read())
    return raw["result"]["content"][0]["text"]


def parse_nutrition_text(text: str) -> list[dict]:
    row = re.compile(
        r"^\s*(.+?),[^,]*,(\d+),(\d+),([\d.]+),([\d.]+),([\d.]+),([\d.]+),([\d.]+)\s*$")
    items = []
    for line in text.split("\\n"):
        m = row.match(line)
        if not m:
            continue
        name, _kj, kcal, protein, fat, carb, sodium, _ca = m.groups()
        items.append({
            "code": _code(name.strip()),
            "name": name.strip(),
            "category": _classify(name.strip()),
            "kcal": float(kcal),
            "protein_g": float(protein),
            "fat_g": float(fat),
            "carb_g": float(carb),
            "sodium_mg": float(sodium),
            "price": 0.0,
            "source": "mcp",
        })
    return items


def refresh_cache(token: str) -> dict:
    text = _call_tool(token, "list-nutrition-foods", {})
    mcp_items = parse_nutrition_text(text)
    if len(mcp_items) < 20:
        raise RuntimeError(f"MCP 返回条目异常: {len(mcp_items)}")

    # 价格沿用人工表（同名匹配），人工独有单品保留
    manual = json.loads(CACHE_PATH.read_text(encoding="utf-8"))["items"]
    price_by_name = {i["name"]: i["price"] for i in manual if i["source"] == "manual"}
    manual_only = [i for i in manual
                   if i["name"] not in {m["name"] for m in mcp_items}]
    for m in mcp_items:
        m["price"] = price_by_name.get(m["name"], 0.0)

    cache = {"fetched_at": date.today().isoformat(),
             "note": "list-nutrition-foods 实拉数据 + 人工补充表合并；价格来自人工表",
             "items": mcp_items + manual_only}
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    _remap_combos(manual, mcp_items)
    return cache


def _remap_combos(manual: list[dict], mcp_items: list[dict]) -> None:
    """套餐 code 重映射：旧人工 code → 名称 → 新 MCP code（MCP 接管后）。"""
    combos_path = ROOT / "data" / "combos.json"
    if not combos_path.exists():
        return
    old_name = {i["code"]: i["name"] for i in manual}
    new_code = {i["name"]: i["code"] for i in mcp_items}
    data = json.loads(combos_path.read_text(encoding="utf-8"))
    changed = False
    for cb in data["combos"]:
        for idx, code in enumerate(cb["items"]):
            name = old_name.get(code)
            if name and name in new_code and new_code[name] != code:
                cb["items"][idx] = new_code[name]
                changed = True
    if changed:
        combos_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                               encoding="utf-8")


if __name__ == "__main__":
    token = os.environ.get("MCD_MCP_TOKEN")
    if not token:
        raise SystemExit("需要环境变量 MCD_MCP_TOKEN")
    cache = refresh_cache(token)
    cats: dict[str, int] = {}
    for i in cache["items"]:
        cats[i["category"]] = cats.get(i["category"], 0) + 1
    print(f"缓存已刷新: 共 {len(cache['items'])} 条 "
          f"(MCP {len(cache['items']) - len(manual_only if (manual_only := [i for i in cache['items'] if i['source'] == 'manual']) else [])} + "
          f"人工 {len([i for i in cache['items'] if i['source'] == 'manual'])})")
    print("分类:", cats)
