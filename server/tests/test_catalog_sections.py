from app.services.assembler import (
    ru_project_word,
    section_subtitle,
    should_include_contents,
    should_include_dividers,
)


def test_contents_only_when_more_than_one_project():
    assert should_include_contents(show_flag=True, project_count=0) is False
    assert should_include_contents(show_flag=True, project_count=1) is False
    assert should_include_contents(show_flag=True, project_count=2) is True
    assert should_include_contents(show_flag=False, project_count=5) is False


def test_dividers_need_both_technologies_and_multiple_projects():
    assert (
        should_include_dividers(show_flag=True, project_count=1, modular_count=1, panel_count=0)
        is False
    )
    assert (
        should_include_dividers(show_flag=True, project_count=2, modular_count=2, panel_count=0)
        is False
    )
    assert (
        should_include_dividers(show_flag=True, project_count=2, modular_count=1, panel_count=1)
        is True
    )
    assert (
        should_include_dividers(show_flag=False, project_count=2, modular_count=1, panel_count=1)
        is False
    )


def test_russian_project_word():
    assert ru_project_word(1) == "проект"
    assert ru_project_word(2) == "проекта"
    assert ru_project_word(3) == "проекта"
    assert ru_project_word(4) == "проекта"
    assert ru_project_word(5) == "проектов"
    assert ru_project_word(11) == "проектов"
    assert ru_project_word(21) == "проект"
    assert section_subtitle(1, kind="modular") == "1 проект по модульной технологии"
    assert section_subtitle(2, kind="panel") == "2 проекта по панельно-каркасной технологии"
