def test_tools_listed(app):
    names = {t["name"] for t in app.tools()}
    assert {"run_command", "get_document", "e2e_sci", "e2e_ui"} <= names


def test_sort_lines(app):
    app.new("b\na\nc\n")
    app.run("IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING")
    assert app.text() == "a\nb\nc\n"
