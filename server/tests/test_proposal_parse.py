from app.services.proposal_parse import merge_documents, normalize_document, parse_markdown


def test_parse_markdown_sample():
    text = """
Зимний 54
Базовая
2 768 000
221 000
48 000
6 000
Итого:
Проект дома
Внешняя отделка
""".strip()
    doc = parse_markdown(text)
    assert doc["project_name"] == "Зимний 54"
    assert doc["package_name"] == "Базовая"
    assert doc["house_price"] == 2768000
    assert doc["totals"]["grand"] >= 2768000


def test_merge_prefers_api():
    parsed = parse_markdown("Зимний 54\nБазовая\n1000000")
    merged = merge_documents(
        {
            "project_name": "Куб 100",
            "house_price": 5_458_000,
            "options": [{"title": "Терраса", "price": 120_000}],
        },
        parsed,
    )
    assert merged["project_name"] == "Куб 100"
    assert merged["house_price"] == 5_458_000
    assert merged["options"][0]["title"] == "Терраса"


def test_normalize_totals():
    doc = normalize_document(
        {
            "house_price": 1_000_000,
            "options": [{"title": "A", "price": 50_000}, {"title": "B", "price": 30_000}],
        }
    )
    assert doc["totals"]["options"] == 80_000
    assert doc["totals"]["grand"] == 1_080_000
