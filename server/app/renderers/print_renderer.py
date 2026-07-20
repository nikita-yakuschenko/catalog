from pathlib import Path

from app.core.config import settings
from app.renderers.base import PdfRenderer


class PrintPdfRenderer(PdfRenderer):
    """Optional PrinceXML adapter. Falls back gracefully when unavailable."""

    name = "prince"

    def __init__(self) -> None:
        self.available = bool(settings.prince_bin) and Path(settings.prince_bin).exists()

    async def render_html(self, html: str, output_path: Path) -> Path:
        if not self.available:
            raise RuntimeError(
                "PrinceXML не установлен. Print profile через PDF/X недоступен. "
                "Используйте Chromium с предупреждением в preflight."
            )
        # Placeholder for future PrinceXML integration
        raise NotImplementedError("PrinceXML adapter is prepared but not wired in MVP")
