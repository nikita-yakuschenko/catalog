"""Pagination of KP option rows: first page accounts for fixed house/delivery/assembly."""

from app.services.proposal_assembler import (
    FIRST_WITHOUT_SUMMARY,
    ROWS_WITH_SUMMARY,
    ROWS_WITHOUT_SUMMARY,
    ProposalAssembler,
    split_option_page_sizes,
)


def test_split_sizes_single_page_up_to_12():
    for n in range(0, ROWS_WITH_SUMMARY + 1):
        assert split_option_page_sizes(n) == [n]


def test_split_sizes_key_cases():
    # 1-я страница без резюме: max 12 опций (15 − 3 фикса)
    assert split_option_page_sizes(13) == [12, 1]
    assert split_option_page_sizes(14) == [12, 2]
    assert split_option_page_sizes(15) == [12, 3]
    assert split_option_page_sizes(16) == [12, 4]
    assert split_option_page_sizes(24) == [12, 12]
    assert split_option_page_sizes(25) == [12, 12, 1]
    assert split_option_page_sizes(27) == [12, 14, 1]
    assert split_option_page_sizes(28) == [12, 15, 1]


def test_split_sizes_invariants_up_to_80():
    for n in range(0, 81):
        sizes = split_option_page_sizes(n)
        assert sum(sizes) == n
        assert sizes[-1] <= ROWS_WITH_SUMMARY
        if n > 0:
            assert sizes[-1] >= 1
        for idx, size in enumerate(sizes[:-1]):
            cap = FIRST_WITHOUT_SUMMARY if idx == 0 else ROWS_WITHOUT_SUMMARY
            assert 1 <= size <= cap


def test_package_pages_empty_still_shows_summary():
    pages = ProposalAssembler()._package_pages({"options": []})
    assert len(pages) == 1
    assert pages[0]["options"] == []
    assert pages[0]["is_first"] is True
    assert pages[0]["is_last"] is True
    assert pages[0]["show_delivery"] is True
    assert pages[0]["show_summary"] is True


def test_package_pages_first_page_caps_at_twelve_options():
    options = [{"title": f"Опция {i}", "price": 1000 * (i + 1), "selected": True} for i in range(16)]
    pages = ProposalAssembler()._package_pages({"options": options})
    assert [len(p["options"]) for p in pages] == [12, 4]
    assert pages[0]["show_summary"] is False
    assert pages[0]["show_delivery"] is True
    assert pages[1]["show_summary"] is True
    assert pages[1]["show_delivery"] is False
    assert pages[1]["options"][0]["title"] == "Опция 12"


def test_package_pages_filters_delivery_assembly_duplicate():
    options = [
        {"title": "Сваи", "price": 100, "selected": True},
        {"title": "Доставка и сборка", "price": 50_000, "selected": True},
        {"title": "Отопление", "price": 200, "selected": True},
    ]
    pages = ProposalAssembler()._package_pages({"options": options})
    titles = [o["title"] for p in pages for o in p["options"]]
    assert titles == ["Сваи", "Отопление"]
