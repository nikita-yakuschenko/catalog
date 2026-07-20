"""Generate QR code data URIs for project links."""

from __future__ import annotations

import base64
import io
from typing import Optional


def qr_data_uri(url: str, box_size: int = 6, border: int = 1) -> Optional[str]:
    if not url:
        return None
    try:
        import qrcode
    except ImportError:
        return None

    qr = qrcode.QRCode(version=None, box_size=box_size, border=border)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#111111", back_color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"
