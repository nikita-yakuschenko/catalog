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
    titles = [o["title"] for o in doc["options"]]
    assert "Проект дома" not in titles
    assert "Внешняя отделка" in titles


def test_parse_markitdown_split_table():
    text = """
А-фрейм 54
Премиум
2 768 000
221 000
48 000
6 000
161 000
66 000
37 000
ИтогО:
?
Стяжка пола
Закрытие цоколя ЦСП без утепления (высота 400мм)
Вентиляция
Стоимость дома
Дополнительные услуги
Забивные сваи 150х150х3000мм
Внутренняя контробрешетка наружных стен - брус 45х45мм
Внутренняя контробрешетка по потолку - брус 45х45мм
""".strip()
    doc = parse_markdown(text)
    assert doc["project_name"] == "А-фрейм 54"
    assert doc["package_name"] == "Премиум"
    assert doc["house_price"] == 2_768_000
    titles = [o["title"] for o in doc["options"]]
    assert "Стоимость дома" not in titles
    assert "Дополнительные услуги" not in titles
    assert len(doc["options"]) == 6
    assert doc["options"][0]["price"] == 221_000
    assert doc["options"][3]["title"].startswith("Забивные сваи")
    assert doc["options"][3]["price"] == 161_000
    assert doc["totals"]["grand"] == 2_768_000 + 221_000 + 48_000 + 6_000 + 161_000 + 66_000 + 37_000


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
    # PDF estimate wins on money when present
    assert merged["house_price"] == 1_000_000
    assert merged["options"][0]["title"] == "Терраса"


def test_merge_keeps_pdf_name_over_generic_bitrix():
    parsed = parse_markdown("А-фрейм 54\nПремиум\n2768000")
    merged = merge_documents(
        {"project_name": "Коммерческое предложение #31", "client": {"name": "Иван"}},
        parsed,
    )
    assert merged["project_name"] == "А-фрейм 54"
    assert merged["client"]["name"] == "Иван"


def test_merge_prefers_base_project_title():
    parsed = parse_markdown("А-фрейм 54\nПремиум\n2768000\n221000\nИтого:\nСтяжка пола")
    merged = merge_documents(
        {"project_name": "Экохаус 132", "client": {"name": "Иван"}},
        parsed,
    )
    assert merged["project_name"] == "Экохаус 132"
    assert merged["house_price"] == 2_768_000
    assert merged["options"][0]["title"] == "Стяжка пола"
    assert merged["client"]["name"] == "Иван"


def test_normalize_totals():
    doc = normalize_document(
        {
            "house_price": 1_000_000,
            "options": [{"title": "A", "price": 50_000}, {"title": "B", "price": 30_000}],
        }
    )
    assert doc["totals"]["options"] == 80_000
    assert doc["totals"]["grand"] == 1_080_000
