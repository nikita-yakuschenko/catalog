from abc import ABC, abstractmethod
from pathlib import Path


class PdfRenderer(ABC):
    name: str = "base"

    @abstractmethod
    async def render_html(self, html: str, output_path: Path) -> Path:
        raise NotImplementedError
