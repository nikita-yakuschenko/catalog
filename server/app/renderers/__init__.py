from app.core.config import settings
from app.renderers.base import PdfRenderer
from app.renderers.chromium import ChromiumPdfRenderer
from app.renderers.print_renderer import PrintPdfRenderer


def get_renderer(profile: str = "screen") -> tuple[PdfRenderer, list[str]]:
    warnings: list[str] = []
    if profile == "print":
        prince = PrintPdfRenderer()
        if prince.available:
            return prince, warnings
        warnings.append(
            "PDF подготовлен через Chromium для проверки, но не сертифицирован как PDF/X-4. "
            "PrinceXML не установлен."
        )
    return ChromiumPdfRenderer(), warnings
