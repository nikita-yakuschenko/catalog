from pathlib import Path

from playwright.async_api import async_playwright

from app.renderers.base import PdfRenderer


class ChromiumPdfRenderer(PdfRenderer):
    name = "chromium"

    async def render_html(self, html: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            try:
                page = await browser.new_page()
                await page.set_content(html, wait_until="networkidle")
                await page.pdf(
                    path=str(output_path),
                    format="A4",
                    landscape=True,
                    print_background=True,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                    prefer_css_page_size=True,
                )
            finally:
                await browser.close()
        return output_path
