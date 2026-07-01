"""自然语言 → SearchIntent（实现位于 flight-monitor-agent Skill）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SKILL_NL = (
    Path(__file__).resolve().parents[2]
    / ".cursor/skills/flight-monitor-agent/scripts/nl_parser.py"
)
_SKILL_SCRIPTS = _SKILL_NL.parent
if str(_SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SKILL_SCRIPTS))
_spec = importlib.util.spec_from_file_location("flight_monitor_skill_nl_parser", _SKILL_NL)
if _spec is None or _spec.loader is None:
    raise ImportError(f"无法加载 Skill 解析器: {_SKILL_NL}")
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)

SYSTEM_PROMPT = _mod.SYSTEM_PROMPT
enrich_intent = _mod.enrich_intent
parse_query = _mod.parse_query
parse_with_llm = _mod.parse_with_llm
parse_with_rules = _mod.parse_with_rules

__all__ = [
    "SYSTEM_PROMPT",
    "enrich_intent",
    "parse_query",
    "parse_with_llm",
    "parse_with_rules",
]
