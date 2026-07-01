#!/usr/bin/env python3
"""从穷举 JSON 生成 HTML 报告（委托 flight-monitor-agent Skill 脚本）。"""
from __future__ import annotations

import sys
from pathlib import Path

_SKILL_DIR = (
    Path(__file__).resolve().parents[1] / ".cursor/skills/flight-monitor-agent/scripts"
)
sys.path.insert(0, str(_SKILL_DIR))

from generate_flight_report import main  # noqa: E402

if __name__ == "__main__":
    main()
