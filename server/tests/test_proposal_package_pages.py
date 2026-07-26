"""Pagination of KP option rows: 15 without summary, 12 with summary."""

from app.services.proposal_assembler import (
    ROWS_WITH_SUMMARY,
    ROWS_WITHOUT_SUMMARY,
    ProposalAssembler,
    split_option_page_sizes,
)


def test_split_sizes_single_page_up_to_12():
    for n in range(0, ROWS_WITH_SUMMARY + 1):
        assert split_option_page_sizes(n) == [n]


def test_split_sizes_key_cases():
    assert split_option_page_sizes(13) == [12, 1]
    assert split_option_page_sizes(14) == [13, 1]
    assert split_option_page_sizes(15) == [14, 1]
    assert split_option_page_sizes(16) == [15, 1]
    assert split_option_page_sizes(17) == [15, 2]
    assert split_option_page_sizes(27) == [15, 12]
    assert split_option_page_sizes(28) == [15, 12, 1]


def test_split_sizes_invariants_up_to_80():
    for n in range(0, 81):
        sizes = split_option_page_sizes(n)
        assert sum(sizes) == n
        assert sizes[-1] <= ROWS_WITH_SUMMARY
        if n > 0:
            assert sizes[-1] >= 1
        for size in sizes[:-1]:
            assert 1 <= size <= ROWS_WITHOUT_SUMMARY


def test_package_pages_empty_still_shows_summary():
    pages = ProposalAssembler()._package_pages({"options": []})
    assert len(pages) == 1
    assert pages[0]["options"] == []
    assert pages[0]["is_first"] is True
    assert pages[0]["is_last"] is True
    assert pages[0]["show_delivery"] is True
    assert pages[0]["show_summary"] is True


def test_package_pages_sixteen_avoids_orphan_summary():
    options = [{"title": f"Опция {i}", "price": 1000 * (i + 1), "selected": True} for i in range(16)]
    pages = ProposalAssembler()._package_pages({"options": options})
    assert [len(p["options"]) for p in pages] == [15, 1]
    assert pages[0]["show_summary"] is False
    assert pages[0]["show_delivery"] is True
    assert pages[1]["show_summary"] is True
    assert pages[1]["show_delivery"] is False
    assert pages[1]["options"][0]["title"] == "Опция 15"


def test_package_pages_filters_delivery_assembly_duplicate():
    options = [
        {"title": "Сваи", "price": 100, "selected": True},
        {"title": "Доставка и сборка", "price": 50_000, "selected": True},
        {"title": "Отопление", "price": 200, "selected": True},
    ]
    pages = ProposalAssembler()._package_pages({"options": options})
    titles = [o["title"] for p in pages for o in p["options"]]
    assert titles == ["Сваи", "Отопление"]
