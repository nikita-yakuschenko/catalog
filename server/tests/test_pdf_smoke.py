from pathlib import Path


def test_sample_pdf_exists_from_smoke():
    """Optional smoke: pass if a recent render exists after CLI smoke."""
    output = Path(__file__).resolve().parents[2] / "output"
    pdfs = list(output.glob("*/*/catalog.pdf"))
    if not pdfs:
        # Skip soft: environment without rendered catalog
        return
    latest = max(pdfs, key=lambda p: p.stat().st_mtime)
    assert latest.stat().st_size > 50_000
    import fitz

    doc = fitz.open(latest)
    assert doc.page_count >= 5
    doc.close()
