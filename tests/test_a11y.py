"""A11Y: end-to-end tests (plan: plan/A11Y.md).

What VoiceOver is given, read from the accessibility server itself (e2e_ax): every element a user
operates has a role and a name, the custom views (tab bars, dock strips, the Document Map, the
status bar's path, Compare's bar) say what they are and act when pressed, the editor is a text
area with its text and selection, and the dialogs can be worked from the keyboard."""
import pytest

from harness.sci import *  # noqa: F401,F403
from _util_a11y import (INTERACTIVE, ax, close_window, describe, find, name, nodes, open_window, skip_unless_ax,
                        unknown_roles, unnamed)
from _util_view import cleanup, dock, fresh_doc, write
from _util_ftp import ftp  # noqa: F401 - the fixture


@pytest.fixture(autouse=True)
def _tidy(app_session):
    yield
    cleanup(app_session)


@pytest.fixture
def axapp(app):
    skip_unless_ax(app)
    return app


def tab_group(tree, label="Tab Bar"):
    groups = [n for n in find(tree, role="AXTabGroup") if n.get("label") == label]
    assert groups, [describe(n) for n in find(tree, role="AXTabGroup")]
    return groups[0]


def tabs_of(group):
    return [c for c in group.get("children", []) if c.get("subrole") == "AXTabButton"]


def text_areas(tree):
    return find(tree, role="AXTextArea")


# ---------------------------------------------------------------- the main window

@pytest.mark.case("A11Y-001")
def test_a11y_001_the_main_window_has_no_element_without_a_role_or_a_name(axapp):
    app = axapp
    fresh_doc(app, "alpha\nbeta\n")
    app.run("IDM_FILE_NEW")
    tree = ax(app)["tree"]
    assert tree["role"] == "AXWindow" and name(tree) == next(d for d in app.docs() if d["current"])["title"]
    assert not unknown_roles(tree), unknown_roles(tree)
    assert not unnamed(tree), unnamed(tree)


@pytest.mark.case("A11Y-002")
def test_a11y_002_the_toolbar_buttons_are_named_as_their_tooltips(axapp):
    app = axapp
    tree = ax(app)["tree"]
    bars = find(tree, role="AXToolbar")
    assert bars
    buttons = [n for n, _ in nodes(bars[0]) if n.get("role") == "AXButton"]
    assert len(buttons) >= 10
    for b in buttons:
        assert name(b), describe(b)
        if b.get("tooltip"):
            assert name(b) == b["tooltip"], describe(b)
        assert "AXPress" in b.get("actions", []), describe(b)


@pytest.mark.case("A11Y-003")
def test_a11y_003_the_tab_bar_is_a_tab_group_of_the_documents(axapp, tmp):
    app = axapp
    a = write(tmp, "one.txt", "1\n")
    b = write(tmp, "two.txt", "2\n")
    app.close_all()
    app.open(a)
    app.open(b)
    app.set_text("changed\n")
    group = tab_group(ax(app)["tree"])
    tabs = tabs_of(group)
    labels = [t.get("label") for t in tabs]
    assert labels[-2:] == ["one.txt", "*two.txt"], labels   # upstream's title bar marks a modified document with "*"
    assert [t.get("value") for t in tabs][-2:] == [0, 1]
    for t in tabs:
        assert t["role"] == "AXRadioButton" and t.get("frame") and t["frame"][2] > 0, describe(t)
        assert {"AXPress", "AXShowMenu"} <= set(t.get("actions", [])), describe(t)   # the tab's right-click menu


@pytest.mark.case("A11Y-004")
def test_a11y_004_pressing_a_tab_and_its_close_button(axapp, tmp):
    app = axapp
    app.set_prefs(tabShowCloseButton=True)
    try:
        _press_tab_and_close(app, tmp)
    finally:
        app.set_prefs(tabShowCloseButton=False)


def _press_tab_and_close(app, tmp):
    app.close_all()
    app.open(write(tmp, "one.txt", "1\n"))
    app.open(write(tmp, "two.txt", "2\n"))
    group = tab_group(ax(app)["tree"])
    first = next(t for t in tabs_of(group) if t.get("label") == "one.txt")
    app.call("e2e_ax", window="main", perform={"path": first["path"], "action": "AXPress"})
    app.wait(lambda: next(d for d in app.docs() if d["current"])["title"] == "one.txt", message="one.txt in front")
    group = tab_group(ax(app)["tree"])
    two = next(t for t in tabs_of(group) if t.get("label") == "two.txt")
    close = [c for c in two.get("children", []) if c.get("role") == "AXButton"]
    assert close and name(close[0]) == "Close", describe(two)
    app.call("e2e_ax", window="main", perform={"path": close[0]["path"], "action": "AXPress"})
    app.wait(lambda: "two.txt" not in [d["title"] for d in app.docs()], message="two.txt closed")


@pytest.mark.case("A11Y-005")
def test_a11y_005_the_editor_is_a_text_area_with_its_text_and_selection(axapp):
    app = axapp
    fresh_doc(app, "alpha\nbeta\n")
    app.select(2, 1, 2, 5)
    assert app.sci(SCI_GETACCESSIBILITY) == SC_ACCESSIBILITY_ENABLED   # Scintilla's Cocoa layer has it on, always
    areas = text_areas(ax(app)["tree"])
    assert len(areas) == 1, [describe(a) for a in areas]
    area = areas[0]
    title = next(d for d in app.docs() if d["current"])["title"]
    assert area.get("label") == title
    assert area.get("role_description") and area["role_description"] != "source code editor"   # the system's words
    assert area.get("value") == "alpha\nbeta\n"
    assert area.get("number_of_characters") == 11
    assert area.get("selected_range") == [6, 4] and area.get("selected_text") == "beta"
    assert area.get("insertion_line") == 1
    # The second view is a text area of its own, named after its document.
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    areas = text_areas(ax(app)["tree"])
    assert len(areas) == 2 and all(a.get("label") == title for a in areas), [describe(a) for a in areas]


@pytest.mark.case("A11Y-006")
def test_a11y_006_the_status_bar_path_is_a_button_that_copies_it(axapp, tmp):
    app = axapp
    p = write(tmp, "status.txt", "x\n")
    app.close_all()
    app.open(p)
    tree = ax(app)["tree"]
    path = [n for n in find(tree, role="AXButton") if n.get("view_class") == "NppStatusPathField"]
    assert path, [describe(n) for n in find(tree, role="AXButton")]
    assert app.same_path(path[0]["label"], p)
    assert path[0].get("help") == "Click to copy the full path"
    texts = [n for n in find(tree, role="AXStaticText") if "Ln" in str(n.get("value"))]
    assert texts, "the status bar's fields"
    app.call("e2e_ax", window="main", perform={"path": path[0]["path"], "action": "AXPress"})
    assert app.same_path(app.clipboard(), p)


# ---------------------------------------------------------------- panels

PANEL_COMMANDS = ["IDM_VIEW_DOC_MAP", "IDM_VIEW_FUNC_LIST", "IDM_VIEW_DOCLIST", "IDM_VIEW_PROJECT_PANEL_1",
                  "IDM_EDIT_CHAR_PANEL", "IDM_EDIT_CLIPBOARDHISTORY_PANEL", "Plugins|Git|Git Panel",
                  "Plugins|Markdown Preview", "Plugins|NppExec|Show NppExec Console"]


@pytest.mark.case("A11Y-007")
def test_a11y_007_docked_panels_are_named_groups_with_tabs_and_a_close_button(axapp):
    app = axapp
    fresh_doc(app, "def f():\n    pass\n")
    app.run("IDM_LANG_PYTHON")
    for c in PANEL_COMMANDS:
        app.run(c)
    app.idle(0.5)
    tree = ax(app)["tree"]
    assert not unknown_roles(tree), unknown_roles(tree)
    assert not unnamed(tree), unnamed(tree)
    docks = [n for n in find(tree, role="AXGroup") if n.get("view_class") == "NppDockContainerView" or
             any(c.get("subrole") == "AXTabButton" for c in n.get("children", []))]
    assert len(docks) >= 2, [describe(n) for n in find(tree, role="AXGroup")]
    for d in docks:
        tabs = [c for c in d["children"] if c.get("subrole") == "AXTabButton"]
        assert tabs and all(name(t) for t in tabs), describe(d)
        front = [t for t in tabs if t.get("value") == 1]
        assert len(front) == 1 and name(front[0]) == name(d), (name(d), [name(t) for t in tabs])
        assert any(c.get("role") == "AXButton" and name(c) == "Close" for c in d["children"]), describe(d)


@pytest.mark.case("A11Y-008")
def test_a11y_008_a_dock_tab_and_its_close_button_act_when_pressed(axapp):
    app = axapp
    fresh_doc(app, "x\n")
    app.run("IDM_VIEW_FUNC_LIST")
    app.run("IDM_VIEW_DOC_MAP")   # both on the right: two tabs of one dock
    tree = ax(app)["tree"]
    group = next(n for n in find(tree, role="AXGroup")
                 if {name(c) for c in n.get("children", []) if c.get("subrole") == "AXTabButton"} >= {"Function List", "Document Map"})
    tab = next(c for c in group["children"] if name(c) == "Function List")
    app.call("e2e_ax", window="main", perform={"path": tab["path"], "action": "AXPress"})
    assert dock(app, "frontPanelIn:", dock(app, "placeOfPanel:", "functionList")) == "functionList"
    group = next(n for n in find(ax(app)["tree"], role="AXGroup") if name(n) == "Function List")
    close = next(c for c in group["children"] if c.get("role") == "AXButton" and name(c) == "Close")
    app.call("e2e_ax", window="main", perform={"path": close["path"], "action": "AXPress"})
    app.wait(lambda: not dock(app, "isPanelVisible:", "functionList"), message="Function List hidden")
    assert dock(app, "isPanelVisible:", "documentMap")


@pytest.mark.case("A11Y-009")
def test_a11y_009_the_document_map_is_a_slider_over_the_document(axapp):
    app = axapp
    fresh_doc(app, "".join(f"line {i}\n" for i in range(500)))
    app.sci(SCI_SETFIRSTVISIBLELINE, 0)
    app.run("IDM_VIEW_DOC_MAP")
    app.idle(0.3)
    tree = ax(app)["tree"]
    sliders = [n for n in find(tree, role="AXSlider") if name(n) == "Document Map"]
    assert len(sliders) == 1, [describe(n) for n in find(tree, role="AXSlider")]
    assert sliders[0].get("value") == 0
    assert {"AXIncrement", "AXDecrement"} <= set(sliders[0].get("actions", []))
    assert len(text_areas(tree)) == 1   # the map's small copy of the text is not a second editor to VoiceOver
    app.call("e2e_ax", window="main", perform={"path": sliders[0]["path"], "action": "AXIncrement"})
    assert app.sci(SCI_GETFIRSTVISIBLELINE) > 0
    slider = next(n for n in find(ax(app)["tree"], role="AXSlider") if name(n) == "Document Map")
    assert slider["value"] > 0


@pytest.mark.case("A11Y-010")
def test_a11y_010_a_floating_panel_is_named_too(axapp):
    app = axapp
    fresh_doc(app, "def f():\n    pass\n")
    app.run("IDM_LANG_PYTHON")
    app.run("IDM_VIEW_FUNC_LIST")
    before = {w["number"] for w in app.windows()}
    dock(app, "movePanel:to:", "functionList", 4)   # NppDockFloating
    try:
        w = app.wait(lambda: next((w for w in app.windows() if w["number"] not in before and w["visible"]), None),
                     message="the floating panel")
        tree = ax(app, w["number"])["tree"]
        assert not unknown_roles(tree), unknown_roles(tree)
        assert not unnamed(tree), unnamed(tree)
        assert any(name(n) == "Function List" for n in find(tree, role="AXGroup")), [describe(n) for n in find(tree, role="AXGroup")]
    finally:
        dock(app, "movePanel:to:", "functionList", 2)


@pytest.mark.case("A11Y-011")
def test_a11y_011_compare_s_bar_buttons_are_named_by_their_tooltips(axapp, tmp):
    app = axapp
    a = write(tmp, "a.txt", "alpha\nbeta\ngamma\n")
    b = write(tmp, "b.txt", "alpha\nbetta\ngamma\ndelta\n")
    app.close_all()
    app.open(a)
    app.answers(panels=[str(b)])
    app.run("Plugins|Compare|Compare with File…")
    try:
        app.wait(lambda: app.get("editor", "compareBar.window") is not None, message="the compare bar")
        tree = ax(app)["tree"]
        buttons = {name(n): n for n in find(tree, role="AXButton")}
        for label in ("Previous Difference", "Next Difference", "Clear Active Compare"):
            assert label in buttons, sorted(buttons)
        assert not unnamed(tree), unnamed(tree)
        app.call("e2e_ax", window="main", perform={"path": buttons["Clear Active Compare"]["path"], "action": "AXPress"})
        app.wait(lambda: app.get("editor", "compareBar.window") is None, message="the compare cleared")
    finally:
        app.run("Plugins|Compare|Clear All Compares", expect_ran=False)


# ---------------------------------------------------------------- dialogs and windows

DIALOGS = ["Search|Find…", "Search|Replace…", "Search|Find in Files…", "Search|Mark…", "Search|Go to…",
           "Search|Find characters in range…", "Edit|Column Editor…", "Settings|Style Configurator…",
           "Settings|Shortcut Mapper…", "Language|User Defined Language|Define your language…",
           "Tools|Hashes|SHA-256|Generate…", "Tools|Hashes|SHA-256|Generate from files…",
           "Tools|Hashes|bcrypt|Generate…", "Tools|Hashes|Argon2|Generate…", "Tools|Base|Base64…",
           "Tools|Password Generator", "Tools|HTTP Request", "Run|Run…",
           "Plugins|NppExec|Execute NppExec Script…", "Plugins|Converter|Conversion Panel",
           "Plugins|XML|Evaluate XPath Expression…", "Window|Windows…", "Help|Debug Info…", "IDM_ABOUT"]


def _judge(app, command):
    fresh_doc(app, '{"a": 1}\n')
    w, pending = open_window(app, command)
    try:
        tree = ax(app, w["number"])["tree"]
        return tree, unknown_roles(tree), unnamed(tree)
    finally:
        close_window(app, w, pending)


@pytest.mark.case("A11Y-012")
@pytest.mark.parametrize("command", DIALOGS)
def test_a11y_012_every_control_of_a_window_has_a_role_and_a_name(axapp, command):
    tree, unknown, missing = _judge(axapp, command)
    assert tree["role"] == "AXWindow" and name(tree)
    assert not unknown, unknown
    assert not missing, missing


def _pref_pages(app, w):
    return next(c for c in app.ui(w["number"])["controls"] if c["class"] == "NSTableView")


@pytest.mark.case("A11Y-013")
def test_a11y_013_every_page_of_preferences_has_its_controls_named(axapp):
    app = axapp
    w, pending = open_window(app, "Settings|Settings…")
    problems = {}
    try:
        table = _pref_pages(app, w)
        for row in range(table["rows"]):
            app.act(w["number"], "select", value=row, path=table["path"], send_action=True)
            app.idle(0.1)
            tree = ax(app, w["number"])["tree"]
            bad = unknown_roles(tree) + unnamed(tree)
            if bad:
                problems[table["cells"][row][0]] = bad
    finally:
        close_window(app, w, pending)
    assert not problems, problems


@pytest.mark.case("A11Y-014")
def test_a11y_014_the_git_panel_and_the_commit_window(axapp, tmp):
    from _util_git import hide_panel, make_repo, open_commit_window
    app = axapp
    repo = make_repo(tmp)
    (repo / "a.txt").write_text("changed\n")
    app.close_all()
    app.open(repo / "a.txt")
    app.run("Plugins|Git|Git Panel")
    try:
        app.idle(0.3)
        tree = ax(app)["tree"]
        assert not unknown_roles(tree), unknown_roles(tree)
        assert not unnamed(tree), unnamed(tree)
        cw = open_commit_window(app)
        tree = ax(app, cw)["tree"]
        assert not unknown_roles(tree), unknown_roles(tree)
        assert not unnamed(tree), unnamed(tree)
        app.close_window(cw)
    finally:
        hide_panel(app)


@pytest.mark.case("A11Y-015")
def test_a11y_015_the_remote_files_window_of_ftp(axapp, ftp):
    app = axapp
    ftp.write("greeting.txt", "remote hello\n")
    ftp.add("local")
    ftp.connect("local")
    w = app.wait(ftp.panel, message="the Remote Files window")
    tree = ax(app, w["number"])["tree"]
    assert not unknown_roles(tree), unknown_roles(tree)
    assert not unnamed(tree), unnamed(tree)


# ---------------------------------------------------------------- keyboard

KEYBOARD_DIALOGS = ["Search|Find…", "Search|Replace…", "Search|Find in Files…", "Search|Mark…",
                    "Settings|Style Configurator…", "Settings|Shortcut Mapper…", "Tools|Hashes|SHA-256|Generate…",
                    "Tools|Base|Base64…", "Tools|Password Generator", "Tools|HTTP Request", "Run|Run…"]


def _operable(tree):
    """The enabled controls on screen a user sets or presses (not the window's own buttons, not
    table cells, not the parts of a control), by their view."""
    out = {}
    for n, parents in nodes(tree):
        if n.get("role") not in INTERACTIVE or n.get("subrole") or n.get("enabled") is False:
            continue
        if any(p.get("role") in ("AXRow", "AXCell", "AXToolbar", "AXScrollBar") or p.get("role") in INTERACTIVE for p in parents):
            continue
        if n.get("view_path"):
            out.setdefault(n["view_path"], n)
    return out


def _reached(path, loop_paths):
    """A control is in the loop itself, by a view inside it (a combo box's field) or by the view it
    lies in (a text view's scroll view)."""
    return any(f == path or f.startswith(path + ".") or path.startswith(f + ".") for f in loop_paths if f)


@pytest.mark.case("A11Y-016")
@pytest.mark.parametrize("command", KEYBOARD_DIALOGS)
def test_a11y_016_every_control_is_in_the_key_view_loop(axapp, command):
    app = axapp
    fresh_doc(app, "abc\n")
    w, pending = open_window(app, command)
    try:
        app.keys("tab", window=w["number"])   # AppKit works the loop out on the first Tab
        got = ax(app, w["number"], key_loop=True)
        loop = [e for e in got["key_loop"] if not e.get("hidden")]
        operable = _operable(got["tree"])
        refusing = [e for e in loop if e.get("refuses") and e["path"] in operable]   # (not a label inside a control)
        paths = [e["path"] for e in loop if not e.get("refuses")]
        missed = [describe(n) for p, n in operable.items() if not _reached(p, paths)]
        assert not missed, missed
        assert not refusing, refusing
    finally:
        close_window(app, w, pending)


ESCAPE_DIALOGS = ["Search|Find…", "Search|Go to…", "Edit|Column Editor…", "Settings|Settings…",
                  "Settings|Style Configurator…", "Settings|Shortcut Mapper…", "Tools|Hashes|SHA-256|Generate…",
                  "Tools|Base|Base64…", "Tools|Password Generator", "Tools|HTTP Request", "Run|Run…",
                  "Window|Windows…", "Help|Debug Info…", "IDM_ABOUT"]


@pytest.mark.case("A11Y-017")
@pytest.mark.parametrize("command", ESCAPE_DIALOGS)
def test_a11y_017_escape_closes_a_dialog(axapp, command):
    app = axapp
    fresh_doc(app, "abc\n")
    w, pending = open_window(app, command)
    try:
        app.keys("escape", window=w["number"])
        app.wait(lambda: not any(x["number"] == w["number"] and x["visible"] for x in app.windows()),
                 timeout=3, message=f"{command} closed by Escape")
    finally:
        close_window(app, None if not any(x["number"] == w["number"] and x["visible"] for x in app.windows()) else w, pending)


RETURN_DIALOGS = {"Search|Go to…": "OK", "Edit|Column Editor…": "OK", "Run|Run…": "OK"}


@pytest.mark.case("A11Y-018")
@pytest.mark.parametrize("command", sorted(RETURN_DIALOGS))
def test_a11y_018_a_dialog_s_default_button_is_the_one_return_presses(axapp, command):
    app = axapp
    fresh_doc(app, "abc\n")
    w, pending = open_window(app, command)
    try:
        tree = ax(app, w["number"])["tree"]
        assert RETURN_DIALOGS[command].lower() in (tree.get("default_button") or "").lower(), tree.get("default_button")
    finally:
        close_window(app, w, pending)


# ---------------------------------------------------------------- in another language

@pytest.fixture
def russian(app_session):
    app_session.start(args=["-NppMac.localizationFile", "russian.xml"])
    app_session.wait(lambda: app_session.docs(), timeout=10)
    yield app_session
    app_session.start()


@pytest.mark.case("A11Y-019")
def test_a11y_019_the_names_the_port_gives_are_in_the_interface_language(russian):
    app = russian
    skip_unless_ax(app)
    app.close_all()
    app.set_text("".join(f"line {i}\n" for i in range(200)))
    app.run("IDM_VIEW_DOC_MAP")
    app.set_prefs(tabShowCloseButton=True)
    tree = ax(app)["tree"]
    group = tab_group(tree, "Панель Вкладок")   # russian.xml: <Tabbar title="Панель Вкладок">
    close = [c for t in tabs_of(group) for c in t.get("children", []) if c.get("role") == "AXButton"]
    assert close and all(name(c) == "Закрыть" for c in close), [name(c) for c in close]
    assert [n for n in find(tree, role="AXSlider") if name(n) == "Карта Документа"], [describe(n) for n in find(tree, role="AXSlider")]
    assert not unnamed(tree), unnamed(tree)
