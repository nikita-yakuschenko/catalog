import asyncio
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from app.renderers.base import PdfRenderer


def _render_in_process(html: str, output_path_str: str, landscape: bool) -> str:
    # Fresh process: avoids Windows SelectorEventLoop from uvicorn (no subprocess support).
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    from playwright.sync_api import sync_playwright

    output_path = Path(output_path_str)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            page.pdf(
                path=str(output_path),
                format="A4",
                landscape=landscape,
                print_background=True,
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                prefer_css_page_size=True,
            )
        finally:
            browser.close()
    return output_path_str


class ChromiumPdfRenderer(PdfRenderer):
    name = "chromium"

    async def render_html(
        self, html: str, output_path: Path, *, landscape: bool = True
    ) -> Path:
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(max_workers=1) as pool:
            await loop.run_in_executor(
                pool, _render_in_process, html, str(output_path), landscape
            )
        return output_path
