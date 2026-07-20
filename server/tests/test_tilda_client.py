import json
from pathlib import Path

import pytest

from app.sources.tilda.client import TildaCatalogClient, gallery_urls, product_price, product_uid


FIXTURE = Path(__file__).parent / "fixtures" / "tilda_products.json"


@pytest.fixture
def products():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_extract_products_from_wrapped_payload():
    client = TildaCatalogClient()
    payload = {"products": [{"uid": "1", "title": "A"}, {"uid": "2", "title": "B"}]}
    assert len(client._extract_products(payload)) == 2


def test_gallery_and_price(products):
    product = products[0]
    assert product_uid(product) == "1001"
    urls = gallery_urls(product)
    assert len(urls) >= 2
    assert product_price(product) == 5558000
