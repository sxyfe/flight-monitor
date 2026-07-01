#!/usr/bin/env python3
"""逐块截取 skill-intro-1080x1440.html 的 .frame，输出小红书竖图（宽 1080px）。"""

from pathlib import Path
from playwright.sync_api import sync_playwright

DIR = Path(__file__).resolve().parent
HTML = DIR / "skill-intro-1080x1440.html"
OUT = DIR / "xhs"
NAMES = [
    "01-封面",
    "02-怎么查",
    "03-报告总览",
    "04-全量穷举",
    "05-筛选控制台",
    "06-国家价格筛选",
    "07-开口程明细",
    "08-图表维度",
    "09-安装指引",
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    url = HTML.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 900}, device_scale_factor=1)
        page.goto(url, wait_until="networkidle")
        page.evaluate("() => document.fonts.ready")
        page.wait_for_timeout(800)

        frames = page.locator("section.frame")
        count = frames.count()
        if count != len(NAMES):
            print(f"警告: 期望 {len(NAMES)} 屏，实际 {count} 屏")

        for i in range(count):
            el = frames.nth(i)
            el.scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            name = NAMES[i] if i < len(NAMES) else f"{i + 1:02d}-slide"
            path = OUT / f"{name}.jpg"
            el.screenshot(path=str(path), type="jpeg", quality=92)
            box = el.bounding_box()
            w = int(box["width"]) if box else 0
            h = int(box["height"]) if box else 0
            print(f"✓ {path} ({w}×{h})")

        browser.close()

    print(f"\n共导出 {count} 张 → {OUT}")


if __name__ == "__main__":
    main()
