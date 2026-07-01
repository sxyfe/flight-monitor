## 1. Agent Skill

- [x] 1.1 创建 `.cursor/skills/flight-monitor-agent/SKILL.md`（工作流、域知识、禁止事项）
- [x] 1.2 Skill 不含视频分镜/旁白/slides 章节
- [x] 1.3 文档引用 `docs/video-bilibili-monitor.md` 作为外部录屏材料

## 2. HTML 报告生成

- [x] 2.1 实现 `scripts/generate_flight_report.py`
- [x] 2.2 支持 `--input` / `--output`，默认 `output/reports/<timestamp>/`
- [x] 2.3 输出 `report.html`、`summary.json`、`monitor_suggestion.json`
- [x] 2.4 复用 `aggregate()`；中文路线与 exhaustive-viz 一致
- [x] 2.5 往返/开口程 Tab 切换；价格分布与目的地 TOP

## 3. 视频演示文档

- [x] 3.1 创建 `docs/video-bilibili-monitor.md`（五幕旁白 + Agent 台词）
- [x] 3.2 固化演示对话脚本（读缓存 → 报告 → 监控规则）
- [x] 3.3 录屏清单：Tauri Dashboard、终端、浏览器、MonitorForm

## 4. 验证

- [x] 4.1 对 `scripts/exhaustive_results.json` 跑通报告生成
- [x] 4.2 确认 summary 命中数与 JSON rt_hits/oj_hits 一致
- [x] 4.3 确认 monitor_suggestion 为 round_trip + bookable 最低价
