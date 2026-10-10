"""命令行入口。

用法：
  python -m solver.cli plan --demo                 # 示例档案，生成 state.json + plan.json
  python -m solver.cli plan --gender M --age 28 --height 175 --weight 72 \
         --activity light --goal cut [--budget 60] [--avoid 辣]
  python -m solver.cli checkin --date 2026-10-12 --slot lunch --codes B01,S01
  python -m solver.cli render [--state state.json] [--out plan.html]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

from solver.checkin import apply_checkin, new_state, replan_day, serialize_food, used_today
from solver.models import Profile
from solver.nutrition import load_nutrition
from solver.planner import SLOT_NAMES, SLOTS, solve_week
from solver.targets import daily_targets

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "nutrition_cache.json"
STATE_PATH = ROOT / "state.json"


def _demo_profile() -> Profile:
    return Profile(gender="M", age=28, height_cm=175, weight_kg=72,
                   activity="light", goal="cut", avoid=())


def _gen_dates(start: str, n: int = 7) -> list[str]:
    d0 = date.fromisoformat(start)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


def cmd_plan(args: argparse.Namespace) -> None:
    if args.demo:
        profile = _demo_profile()
        start = date.today().isoformat()
    else:
        required = ("gender", "age", "height", "weight")
        missing = [a for a in required if getattr(args, a) is None]
        if missing:
            sys.exit(f"缺少参数: {missing}（或使用 --demo）")
        profile = Profile(
            gender=args.gender, age=args.age, height_cm=args.height,
            weight_kg=args.weight, activity=args.activity, goal=args.goal,
            budget_per_day=args.budget, avoid=tuple(args.avoid or ()))
        start = args.start or date.today().isoformat()

    items = load_nutrition(DATA_PATH)
    week = solve_week(items, profile, seed=args.seed, avoid=tuple(profile.avoid))
    dates = _gen_dates(start)

    state = new_state(profile, start)
    for d, day in zip(dates, week):
        state["plan"][d] = {
            slot: [serialize_food(f) for f in foods]
            for slot, foods in day.items()
        }
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已生成 7 天计划 → {STATE_PATH}")
    t = state["targets"]
    print(f"每日目标: {t['kcal']:.0f} kcal ｜ 三大营养素: "
          f"蛋白 {t['protein_g']:.0f}g / 脂肪 ≥{t['fat_min_g']:.0f}g / "
          f"碳水 ~{t['carb_hint_g']:.0f}g ｜ 钠 ≤ {t['sodium_max_mg']:.0f} mg")
    print(f"下一步: python -m solver.cli render")


def cmd_checkin(args: argparse.Namespace) -> None:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    profile = Profile(**state["profile"])
    items = load_nutrition(DATA_PATH)

    state = apply_checkin(state, args.date, args.slot, args.codes)
    if args.weight:
        state["weight_log"][args.date] = args.weight

    lookup = {i.code: i for i in items}
    used = used_today(state, args.date, items)
    remaining = state["targets"]["kcal"] - used["kcal"]

    state = replan_day(state, args.date, items, seed=args.seed)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已打卡 {args.date} {SLOT_NAMES[args.slot]}: "
          f"{', '.join(args.codes)}")
    for c in args.codes:
        f = lookup.get(c)
        if f:
            print(f"  {c} {f.name}: {f.kcal:.0f} kcal / 钠 {f.sodium_mg:.0f} mg")
    print(f"今日已摄入 {used['kcal']:.0f} kcal（蛋白 {used['protein_g']:.0f}g / "
          f"脂肪 {used['fat_g']:.0f}g / 碳水 {used['carb_g']:.0f}g / "
          f"钠 {used['sodium_mg']:.0f}mg），剩余预算 {remaining:.0f} kcal，"
          f"已重排未打卡餐位。")
    print(f"下一步: python -m solver.cli render")


def cmd_render(args: argparse.Namespace) -> None:
    from solver.render import render_plan
    state_path = Path(args.state) if args.state else STATE_PATH
    out_path = Path(args.out) if args.out else ROOT / "plan.html"
    html = render_plan(state_path, ROOT / "web" / "template" / "plan.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"已渲染网页 → {out_path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mcdiet", description="麦门膳食师")
    sub = p.add_subparsers(dest="command", required=True)

    plan_p = sub.add_parser("plan", help="生成 7 天计划")
    plan_p.add_argument("--demo", action="store_true", help="使用示例档案")
    plan_p.add_argument("--gender", choices=["M", "F"])
    plan_p.add_argument("--age", type=int)
    plan_p.add_argument("--height", type=float)
    plan_p.add_argument("--weight", type=float)
    plan_p.add_argument("--activity", default="light",
                        choices=["sedentary", "light", "moderate", "high", "extreme"])
    plan_p.add_argument("--goal", default="maintain",
                        choices=["cut", "maintain", "bulk"])
    plan_p.add_argument("--budget", type=float, default=None)
    plan_p.add_argument("--avoid", nargs="*", default=[])
    plan_p.add_argument("--start", help="开始日期 YYYY-MM-DD")
    plan_p.add_argument("--seed", type=int, default=42)
    plan_p.set_defaults(func=cmd_plan)

    ck_p = sub.add_parser("checkin", help="打卡并重排")
    ck_p.add_argument("--date", required=True)
    ck_p.add_argument("--slot", required=True, choices=SLOTS)
    ck_p.add_argument("--codes", nargs="+", required=True)
    ck_p.add_argument("--weight", type=float, default=None, help="当日晨重 kg")
    ck_p.add_argument("--seed", type=int, default=42)
    ck_p.set_defaults(func=cmd_checkin)

    rd_p = sub.add_parser("render", help="渲染网页")
    rd_p.add_argument("--state", default=None)
    rd_p.add_argument("--out", default=None)
    rd_p.set_defaults(func=cmd_render)
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
