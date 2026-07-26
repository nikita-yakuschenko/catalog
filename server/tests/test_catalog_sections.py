from app.services.assembler import should_include_contents, should_include_dividers


def test_contents_only_when_more_than_one_project():
    assert should_include_contents(show_flag=True, project_count=0) is False
    assert should_include_contents(show_flag=True, project_count=1) is False
    assert should_include_contents(show_flag=True, project_count=2) is True
    assert should_include_contents(show_flag=False, project_count=5) is False


def test_dividers_need_both_technologies_and_multiple_projects():
    assert should_include_dividers(
        show_flag=True, project_count=1, modular_count=1, panel_count=0
    ) is False
    assert should_include_dividers(
        show_flag=True, project_count=2, modular_count=2, panel_count=0
    ) is False
    assert should_include_dividers(
        show_flag=True, project_count=2, modular_count=1, panel_count=1
    ) is True
    assert should_include_dividers(
        show_flag=False, project_count=2, modular_count=1, panel_count=1
    ) is False
