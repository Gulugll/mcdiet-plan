"""网页渲染：将 state.json 注入模板。"""
from __future__ import annotations

import json
from pathlib import Path

PLACEHOLDER = "__PLAN_DATA__"


def render_plan(state_path: str | Path, template_path: str | Path) -> str:
    """读取状态文件，替换模板占位符，返回完整 HTML 字符串。"""
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    template = Path(template_path).read_text(encoding="utf-8")
    payload = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    # </script> 注入防护
    payload = payload.replace("</script>", "<\\/script>")
    return template.replace(PLACEHOLDER, payload, 1)
