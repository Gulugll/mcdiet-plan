"""渲染器的行为测试（TDD：先红后绿）。"""
import json
from pathlib import Path

from solver.render import render_plan

TEMPLATE = Path(__file__).parent.parent / "web" / "template" / "plan.html"


def test_render_injects_valid_json(tmp_path):
    state = {
        "profile": {"gender": "M", "age": 28, "height_cm": 175,
                     "weight_kg": 72, "activity": "light", "goal": "cut",
                     "budget_per_day": None, "avoid": []},
        "targets": {"kcal": 1962, "protein_g": 115, "fat_min_g": 43.6,
                     "carb_hint_g": 200, "sodium_max_mg": 2300},
        "start_date": "2026-10-12",
        "plan": {"2026-10-12": {"breakfast": [], "lunch": [], "dinner": []}},
        "checkins": {}, "weight_log": {},
    }
    p = Path(__file__).parent / ".tmp" / "render_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    try:
        html = render_plan(p, TEMPLATE)
    finally:
        p.unlink(missing_ok=True)
    assert "__PLAN_DATA__" not in html
    m = html.split('<script id="plan-data" type="application/json">')[1]
    data = json.loads(m.split("</script>")[0])
    assert data["profile"]["weight_kg"] == 72
