"""COMPARE: end-to-end tests (plan: plan/COMPARE.md)."""
import os
import subprocess
import time

import pytest

from harness.sci import *  # noqa: F401,F403
from _util_compare import (
    BACKGROUND_BITS, CHAR_DIFFS, CLEAR, CLEAR_ALL, COMPARE, COMPARE_BITS, DEFAULTS, DETECT_MOVES, FIRST,
    GIT_CLEAR, GIT_HEAD, IDENTICAL, IGNORE_CASE, IGNORE_EMPTY, IGNORE_SPACES, LAST, MOVED_NEW, MOVED_OLD,
    NEW, NEXT, NOTHING_INFO, NOTHING_TITLE, OLD, OPTION_PREFS, PREV, SET_FIRST, SUMMARY, SUMMARY_MOVED,
    SUMMARY_NEW_OLD, alerts, all_marks, bar, bar_buttons, caret_line, clear_all, compare_with_file, has,
    ind18, line_count, margin5, marks, open_and_compare, pane_text, restore_options, second_pane_shown,
    wait_bar, write,
)


@pytest.fixture
def cmp(app):
    """The app with no comparison, no first file and the default options; put back afterwards."""
    restore_options(app)
    clear_all(app)
    app.counters(reset=True)
    yield app
    app.answers(clear=True)
    try:
        clear_all(app)
    finally:
        restore_options(app)


def pair(tmp):
    return write(tmp, "old.txt", OLD), write(tmp, "new.txt", NEW)


def compared_new_old(app, tmp):
    old, new = pair(tmp)
    info = open_and_compare(app, new, old)
    assert info == SUMMARY_NEW_OLD
    return old, new


def assert_view_cleared(app):
    assert bar(app) is None
    assert bar_buttons(app) == []
    assert not second_pane_shown(app)
    assert margin5(app) == 0
    assert all(m & COMPARE_BITS == 0 for m in all_marks(app))


# ---- Starting a comparison ---------------------------------------------------

@pytest.mark.case("COMPARE-001")
def test_compare_001_set_as_first_to_compare_remembers_a_saved_file_and_says_so(cmp, tmp):
    """COMPARE-001: Set as First to Compare remembers a saved file and says so"""
    app = cmp
    old = write(tmp, "old.txt", OLD)
    app.open(old)
    app.run(SET_FIRST)
    log = alerts(app.modal_log())
    assert len(log) == 1
    assert log[0]["message"] == "Set as the first file to compare."
    assert app.same_path(log[0]["informative"], old)
    assert bar(app) is None
    assert not second_pane_shown(app)
    assert app.text() == OLD


@pytest.mark.case("COMPARE-002")
def test_compare_002_set_as_first_on_an_untitled_document_sets_nothing(cmp):
    """COMPARE-002: Set as First takes an untitled document too, and names its tab

    ComparePlus's setFirst takes any buffer (no file needed: it compares the text); the alert
    names the tab. Compare from that same tab then has nothing else to compare with."""
    app = cmp
    app.new("x")
    title = app.doc()["title"]
    app.run(SET_FIRST)
    log = alerts(app.modal_log())
    assert len(log) == 1 and log[0]["message"] == "Set as the first file to compare."
    assert log[0].get("informative", "") == title
    app.run(COMPARE)
    log = alerts(app.modal_log())
    assert [e["message"] for e in log] == [NOTHING_TITLE]
    assert log[0]["informative"] == NOTHING_INFO
    assert bar(app) is None
    assert margin5(app) == 0


@pytest.mark.case("COMPARE-003")
def test_compare_003_compare_with_nothing_set_first_explains_what_to_do(cmp, tmp):
    """COMPARE-003: Compare with nothing set first explains what to do"""
    app = cmp
    _, new = pair(tmp)
    app.open(new)
    app.run(COMPARE)
    log = alerts(app.modal_log())
    assert len(log) == 1
    assert log[0]["message"] == NOTHING_TITLE and log[0]["informative"] == NOTHING_INFO
    assert bar(app) is None and bar_buttons(app) == []
    assert margin5(app) == 0


@pytest.mark.case("COMPARE-004")
def test_compare_004_compare_two_open_documents_first_set_aside_second_in_front(cmp, tmp):
    """COMPARE-004: Compare two open documents: first set aside, second in front"""
    app = cmp
    old, new = pair(tmp)
    app.open(old)
    app.run(SET_FIRST)
    app.open(new)
    app.modal_log(clear=True)
    app.run(COMPARE)
    log = alerts(app.modal_log())
    assert len(log) == 1
    assert log[0]["message"] == "Compare"
    assert log[0]["buttons"] == ["OK", "Copy"]
    assert log[0]["informative"] == SUMMARY_NEW_OLD
    assert pane_text(app) == OLD
    assert app.sci(SCI_GETREADONLY, view="sub") == 1
    d = app.doc()
    assert app.same_path(d["path"], new) and not d["modified"]
    assert bar(app) == SUMMARY_NEW_OLD
    buttons = {c["title"]: c for c in bar_buttons(app)}
    assert set(buttons) == {"◀", "▶", "✕"}
    tips = {t: c["tooltip"] for t, c in buttons.items()}
    assert tips == {"◀": "Previous Difference", "▶": "Next Difference", "✕": "Clear Active Compare"}
    assert caret_line(app) == 2


@pytest.mark.case("COMPARE-005")
def test_compare_005_compare_takes_the_first_document_s_current_text_not_only_its(cmp, tmp):
    """COMPARE-005: Compare takes the first document's current text, not only its saved file"""
    app = cmp
    old, new = pair(tmp)
    app.open(old)
    app.set_text("alpha\nCHANGED\ngamma\n")
    app.run(SET_FIRST)
    app.open(new)
    app.run(COMPARE)
    assert pane_text(app) == "alpha\nCHANGED\ngamma\n"


@pytest.mark.case("COMPARE-006")
def test_compare_006_compare_with_file_compares_the_document_in_front_with_a_chos(cmp, tmp):
    """COMPARE-006: Compare with File compares the document in front with a chosen file"""
    app = cmp
    old, new = pair(tmp)
    app.open(new)
    log = compare_with_file(app, old)
    panels = [e for e in log if e.get("kind") != "alert"]
    assert panels and app.same_path((panels[0].get("answered") or [None])[0], old), panels
    a = alerts(log)
    assert a[-1]["message"] == "Compare" and a[-1]["informative"] == SUMMARY_NEW_OLD
    assert log.index(panels[0]) < log.index(a[-1])
    assert pane_text(app) == OLD
    app.run(CLEAR)
    app.run(COMPARE)
    assert [e["message"] for e in alerts(app.modal_log())] == [NOTHING_TITLE]


@pytest.mark.case("COMPARE-007")
def test_compare_007_cancelling_or_failing_compare_with_file_changes_nothing(cmp, tmp):
    """COMPARE-007: Cancelling or failing Compare with File changes nothing"""
    app = cmp
    _, new = pair(tmp)
    app.open(new)
    for answer in (None, str(tmp / "does-not-exist.txt")):
        app.answers(panels=[answer])
        app.run("Plugins|Compare|Compare with File...")
        log = app.modal_log()
        assert alerts(log) == [], log
        assert len(log) == 1
        assert bar(app) is None and bar_buttons(app) == []
        assert margin5(app) == 0
        assert not second_pane_shown(app)
        assert app.text() == NEW


@pytest.mark.case("COMPARE-008")
def test_compare_008_identical_texts_are_reported_identical_and_nothing_is_marked(cmp, tmp):
    """COMPARE-008: Identical texts are reported identical and nothing is marked"""
    app = cmp
    old = write(tmp, "old.txt", OLD)
    same = write(tmp, "same.txt", OLD)
    assert open_and_compare(app, same, old) == IDENTICAL
    assert bar(app) == IDENTICAL
    for view in ("main", "sub"):
        assert all(m & COMPARE_BITS == 0 for m in all_marks(app, view)), view
    assert margin5(app) == 0


@pytest.mark.case("COMPARE-009")
def test_compare_009_the_compare_shortcut_runs_compare(cmp, tmp):
    """COMPARE-009: The Compare shortcut runs Compare"""
    app = cmp
    assert app.menu_item(COMPARE)["key"] == "alt+cmd+d"
    old, new = pair(tmp)
    app.open(old)
    app.run(SET_FIRST)
    app.open(new)
    app.modal_log(clear=True)
    app.keys("alt+cmd+d")
    log = app.wait(lambda: alerts(app.modal_log(clear=False)), message="the Compare alert")
    assert log[-1]["message"] == "Compare" and log[-1]["informative"] == SUMMARY_NEW_OLD
    assert bar(app) == SUMMARY_NEW_OLD


@pytest.mark.case("COMPARE-010")
def test_compare_010_line_endings_and_a_latin_1_file_do_not_make_lines_differ(cmp, tmp):
    """COMPARE-010: Line endings and a Latin-1 file do not make lines differ"""
    app = cmp
    u = write(tmp, "u.txt", "a\nb\n")
    w = write(tmp, "w.txt", b"a\r\nb\r\n")
    assert open_and_compare(app, u, w) == IDENTICAL
    app.run(CLEAR)
    u2 = write(tmp, "u2.txt", "café\n")
    lat = write(tmp, "l.txt", "café\n", encoding="latin-1")
    assert open_and_compare(app, u2, lat) == IDENTICAL


@pytest.mark.case("COMPARE-011")
def test_compare_011_a_new_comparison_replaces_the_one_on_screen(cmp, tmp):
    """COMPARE-011: A new comparison replaces the one on screen"""
    app = cmp
    h1 = write(tmp, "h1.txt", "say hello world now\n")
    h2 = write(tmp, "h2.txt", "say hallo world now\n")
    big = write(tmp, "L1.txt", "".join(f"big line {i}\n" for i in range(5000)))
    assert open_and_compare(app, h2, h1) == "0 added, 0 removed, 1 changed, 0 unchanged."
    assert any(ind18(app, 0, 19))
    log = compare_with_file(app, big)
    summary = "1 added, 5000 removed, 0 changed, 0 unchanged."
    assert alerts(log)[-1]["informative"] == summary
    assert line_count(app, "sub") == 5001
    assert bar(app) == summary
    assert not any(ind18(app, 0, 19))


@pytest.mark.case("COMPARE-012")
def test_compare_012_compare_with_head_compares_the_file_with_its_committed_text(cmp, tmp):
    """COMPARE-012: Compare with HEAD compares the file with its committed text"""
    app = cmp
    repo = tmp / "repo"
    repo.mkdir()
    git = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)  # noqa: E731
    git("init", "-q")
    git("config", "user.name", "Tester")
    git("config", "user.email", "tester@example.org")
    f = write(repo, "f.txt", "one\ntwo\nthree\n")
    git("add", "f.txt")
    git("commit", "-q", "-m", "first")
    f.write_text("one\nTWO\nthree\nfour\n")
    app.open(f)
    app.modal_log(clear=True)
    app.run(GIT_HEAD)
    app.wait(lambda: second_pane_shown(app), message="the second pane")
    assert pane_text(app) == "one\ntwo\nthree\n"
    assert bar(app) and "added" in bar(app)
    assert has(app, 3, 2)
    assert alerts(app.modal_log()) == []
    app.run(GIT_CLEAR)
    assert bar(app) is None
    assert not second_pane_shown(app)


@pytest.mark.case("COMPARE-013")
def test_compare_013_the_mcp_compare_tool_with_show_opens_the_compare_view_withou(cmp, tmp):
    """COMPARE-013: The MCP compare tool with show opens the Compare view without changing the user's options"""
    app = cmp
    old, new = pair(tmp)
    assert not app.checked(IGNORE_CASE)
    r = app.call("compare", left={"path": str(old)}, right={"path": str(new)}, show=True, ignore_case=True)
    assert r["shown"] is True
    assert r["summary"] == SUMMARY_NEW_OLD
    assert app.same_path(app.doc()["path"], new)
    assert bar(app) == SUMMARY_NEW_OLD
    assert not app.checked(IGNORE_CASE)
    assert app.pref("compareIgnoreCase") in (False, 0, "NO", None)


# ---- Marks in the panes --------------------------------------------------------

@pytest.mark.case("COMPARE-014")
def test_compare_014_a_changed_line_is_marked_in_both_panes_with_its_margin_symbo(cmp, tmp):
    """COMPARE-014: A changed line is marked in both panes with its margin symbol"""
    app = cmp
    compared_new_old(app, tmp)
    for view in ("main", "sub"):
        assert has(app, 1, 0, view) and has(app, 1, 10, view), view
    assert margin5(app) > 0
    assert app.sci(SCI_GETMARGINMASKN, 1) & 0x1D == 0x1D   # markers 0, 2, 3, 4 drawn through margin 1
    for line in (0, 2):
        assert marks(app, line) & BACKGROUND_BITS == 0


@pytest.mark.case("COMPARE-015")
def test_compare_015_an_added_line_is_marked_in_the_document_nothing_opposite(cmp, tmp):
    """COMPARE-015: An added line is marked in the document, nothing opposite"""
    app = cmp
    compared_new_old(app, tmp)
    assert has(app, 3, 2) and has(app, 3, 12)
    assert all(m & ((1 << 2) | (1 << 3)) == 0 for m in all_marks(app, "sub"))


@pytest.mark.case("COMPARE-016")
def test_compare_016_a_removed_line_is_marked_in_the_second_pane(cmp, tmp):
    """COMPARE-016: A removed line is marked in the second pane"""
    app = cmp
    old = write(tmp, "old.txt", OLD)
    doc = write(tmp, "short.txt", "alpha\ngamma\n")
    assert open_and_compare(app, doc, old) == "0 added, 1 removed, 0 changed, 2 unchanged."
    assert has(app, 1, 3, "sub") and has(app, 1, 14, "sub")
    assert all(m & (1 << 3) == 0 for m in all_marks(app))


@pytest.mark.case("COMPARE-017")
def test_compare_017_a_moved_line_is_marked_moved_on_both_sides_and_counted(cmp, tmp):
    """COMPARE-017: A moved line is marked moved on both sides and counted"""
    app = cmp
    mo = write(tmp, "mo.txt", MOVED_OLD)
    mn = write(tmp, "mn.txt", MOVED_NEW)
    assert open_and_compare(app, mn, mo) == SUMMARY_MOVED
    assert has(app, 0, 4) and has(app, 0, 16)
    assert has(app, 5, 4, "sub")
    assert has(app, 2, 0)
    assert has(app, 4, 2)
    assert has(app, 4, 3, "sub")


@pytest.mark.case("COMPARE-018")
def test_compare_018_a_moved_block_carries_begin_middle_end_symbols(cmp, tmp):
    """COMPARE-018: A moved block carries begin / middle / end symbols"""
    app = cmp
    lines = [f"distinct line number {i} here" for i in range(12)]
    order = [0, 1, 8, 9, 10, 2, 3, 4, 5, 6, 7, 11]
    old = write(tmp, "blk_old.txt", "\n".join(lines) + "\n")
    new = write(tmp, "blk_new.txt", "\n".join(lines[i] for i in order) + "\n")
    assert open_and_compare(app, new, old) == "0 added, 0 removed, 3 moved, 0 changed, 9 unchanged."
    for line, sym in ((2, 17), (3, 18), (4, 19)):
        assert has(app, line, 4) and has(app, line, sym), line
    for line in (0, 1, 5, 6, 7, 8, 9, 10):
        assert not has(app, line, 4), line


@pytest.mark.case("COMPARE-019")
def test_compare_019_only_the_changed_characters_of_a_changed_line_are_under_indi(cmp, tmp):
    """COMPARE-019: Only the changed characters of a changed line are under indicator 18"""
    app = cmp
    mo = write(tmp, "mo.txt", MOVED_OLD)
    mn = write(tmp, "mn.txt", MOVED_NEW)
    open_and_compare(app, mn, mo)
    v = ind18(app, 2, 10)   # "int B = 2;"
    assert v[4]
    assert not any(v[0:3]) and not v[6] and not v[8]
    app.run(CLEAR)
    h1 = write(tmp, "h1.txt", "say hello world now\n")
    h2 = write(tmp, "h2.txt", "say hallo world now\n")
    open_and_compare(app, h2, h1)
    v = ind18(app, 0, 19)
    assert [i for i, x in enumerate(v) if x] == [5]


@pytest.mark.case("COMPARE-020")
def test_compare_020_blank_annotations_align_both_panes(cmp, tmp):
    """COMPARE-020: Blank annotations align both panes"""
    app = cmp
    mo = write(tmp, "mo.txt", MOVED_OLD)
    mn = write(tmp, "mn.txt", MOVED_NEW)
    open_and_compare(app, mn, mo)
    assert app.sci(SCI_VISIBLEFROMDOCLINE, 6) == app.sci(SCI_VISIBLEFROMDOCLINE, 3, view="sub")
    assert app.sci(SCI_VISIBLEFROMDOCLINE, 7) == app.sci(SCI_VISIBLEFROMDOCLINE, 6, view="sub")
    main_ann = [app.sci(SCI_ANNOTATIONGETLINES, i) for i in range(line_count(app))]
    sub_ann = [app.sci(SCI_ANNOTATIONGETLINES, i, view="sub") for i in range(line_count(app, "sub"))]
    assert any(main_ann) and any(sub_ann)
    app.run(CLEAR)
    assert not any(app.sci(SCI_ANNOTATIONGETLINES, i) for i in range(line_count(app)))


@pytest.mark.case("COMPARE-021")
def test_compare_021_the_second_pane_gets_the_document_s_language(cmp, tmp):
    """COMPARE-021: The second pane gets the document's language"""
    app = cmp
    a = write(tmp, "a.py", "def f():\n    return 1\n")
    b = write(tmp, "b.py", "def f():\n    return 2\n")
    assert open_and_compare(app, b, a) == "0 added, 0 removed, 1 changed, 1 unchanged."
    assert app.sci(SCI_GETLEXER) == app.sci(SCI_GETLEXER, view="sub")
    assert app.sci(SCI_GETSTYLEAT, 0) == app.sci(SCI_GETSTYLEAT, 0, view="sub") != 0
    for msg in (SCI_STYLEGETBACK, SCI_STYLEGETSIZE):
        assert app.sci(msg, 32) == app.sci(msg, 32, view="sub")


@pytest.mark.case("COMPARE-022")
def test_compare_022_the_two_panes_scroll_together_while_comparing(cmp, tmp):
    """COMPARE-022: The two panes scroll together while comparing"""
    app = cmp
    base = [f"row {i}" for i in range(300)]
    changed = list(base)
    changed[150] = "row 150 changed"
    a = write(tmp, "s1.txt", "\n".join(base) + "\n")
    b = write(tmp, "s2.txt", "\n".join(changed) + "\n")
    open_and_compare(app, b, a)
    assert caret_line(app) == 151
    assert app.sci(SCI_GETFIRSTVISIBLELINE) == app.sci(SCI_GETFIRSTVISIBLELINE, view="sub")
    app.sci(SCI_SETFIRSTVISIBLELINE, 20)
    app.wait(lambda: app.sci(SCI_GETFIRSTVISIBLELINE, view="sub") == 20, message="sub at 20")
    app.sci(SCI_LINESCROLL, 0, 30)
    app.wait(lambda: app.sci(SCI_GETFIRSTVISIBLELINE, view="sub") == 50, message="sub at 50")
    assert app.sci(SCI_GETFIRSTVISIBLELINE) == 50


@pytest.mark.case("COMPARE-023")
def test_compare_023_a_big_comparison_is_quick(cmp, tmp):
    """COMPARE-023: A big comparison is quick"""
    app = cmp
    base = [f"line {i} of the big file" for i in range(5000)]
    changed = [f"{s} CHANGED" if i % 100 == 0 else s for i, s in enumerate(base)]
    a = write(tmp, "b1.txt", "\n".join(base) + "\n")
    b = write(tmp, "b2.txt", "\n".join(changed) + "\n")
    app.open(b)
    t = time.monotonic()
    log = compare_with_file(app, a)
    elapsed = time.monotonic() - t
    assert alerts(log)[-1]["informative"] == "0 added, 0 removed, 50 changed, 4950 unchanged."
    assert elapsed < 5.0


# ---- Navigation ------------------------------------------------------------------

@pytest.mark.case("COMPARE-024")
def test_compare_024_next_and_previous_difference_walk_the_runs_and_wrap_around(cmp, tmp):
    """COMPARE-024: Next and Previous Difference walk the runs and wrap around"""
    app = cmp
    compared_new_old(app, tmp)
    app.select(1)
    seen = []
    for cmd in (NEXT, NEXT, NEXT, PREV, PREV):
        app.run(cmd)
        s = app.selection()
        assert s["text"] == "" and s["caret"]["column"] == 1
        seen.append(s["caret"]["line"])
    assert seen == [2, 4, 2, 4, 2]


@pytest.mark.case("COMPARE-025")
def test_compare_025_first_and_last_difference(cmp, tmp):
    """COMPARE-025: First and Last Difference"""
    app = cmp
    mo = write(tmp, "mo.txt", MOVED_OLD)
    mn = write(tmp, "mn.txt", MOVED_NEW)
    open_and_compare(app, mn, mo)
    app.select(4)
    app.run(LAST)
    assert app.selection()["caret"] == {**app.selection()["caret"], "line": 7, "column": 1}
    app.run(FIRST)
    assert caret_line(app) == 1


@pytest.mark.case("COMPARE-026")
def test_compare_026_navigation_stops_at_a_removal_that_shows_only_in_the_second(cmp, tmp):
    """COMPARE-026: Navigation stops at a removal that shows only in the second pane"""
    app = cmp
    x1 = write(tmp, "x1.txt", "a\nb\nc\nd\n")
    x2 = write(tmp, "x2.txt", "a\nc\nd\nX\n")
    assert open_and_compare(app, x2, x1) == "1 added, 1 removed, 0 changed, 3 unchanged."
    app.select(1)
    lines = []
    for _ in range(2):
        before = caret_line(app)
        app.run(NEXT)
        lines.append(caret_line(app))
        assert lines[-1] > before or (lines[-1] == 4), lines
    assert lines[-1] == 4
    app.run(NEXT)
    assert caret_line(app) < 4


@pytest.mark.case("COMPARE-027")
def test_compare_027_navigation_without_a_comparison_does_nothing(cmp):
    """COMPARE-027: Navigation without a comparison does nothing"""
    app = cmp
    text = "1\n2\n3\n4\n5\n"
    app.new(text)
    app.select(3)
    for cmd in (NEXT, PREV, FIRST, LAST):
        assert app.run(cmd)["ran"]
        c = app.selection()["caret"]
        assert (c["line"], c["column"]) == (3, 1)
    assert app.text() == text
    assert alerts(app.modal_log()) == []


@pytest.mark.case("COMPARE-028")
def test_compare_028_the_bar_s_buttons_navigate_and_close(cmp, tmp):
    """COMPARE-028: The bar's buttons navigate and close"""
    app = cmp
    compared_new_old(app, tmp)
    app.select(1)
    app.click("main", "▶")
    assert caret_line(app) == 2
    app.click("main", "◀")
    assert caret_line(app) == 4
    app.click("main", "✕")
    assert_view_cleared(app)


# ---- Summary -----------------------------------------------------------------

@pytest.mark.case("COMPARE-029")
def test_compare_029_compare_summary_shows_the_counts_and_copies_them(cmp, tmp):
    """COMPARE-029: Compare Summary shows the counts and copies them"""
    app = cmp
    compared_new_old(app, tmp)
    app.run(SUMMARY)
    a = alerts(app.modal_log())
    assert a[-1]["message"] == "Compare" and a[-1]["informative"] == SUMMARY_NEW_OLD
    app.answers(alerts=[2])
    app.run(SUMMARY)
    app.modal_log()
    assert app.clipboard() == SUMMARY_NEW_OLD


@pytest.mark.case("COMPARE-030")
def test_compare_030_compare_summary_before_any_comparison(cmp):
    """COMPARE-030: Compare Summary before any comparison"""
    app = cmp
    app.run(SUMMARY)
    assert alerts(app.modal_log())[-1]["informative"] == "Nothing has been compared."


# ---- Options -------------------------------------------------------------------

def _truthy(v):
    return v in (True, 1, "1", "YES", "true")


@pytest.mark.case("COMPARE-031")
@pytest.mark.restart
def test_compare_031_the_option_items_show_and_store_their_state(fresh_app):
    """COMPARE-031: The option items show and store their state"""
    app = fresh_app
    try:
        expected = {IGNORE_CASE: False, IGNORE_SPACES: False, IGNORE_EMPTY: False, DETECT_MOVES: True, CHAR_DIFFS: True}
        for cmd, default in expected.items():
            assert app.checked(cmd) is default, cmd
        for cmd, default in expected.items():
            pref = OPTION_PREFS[cmd]
            app.run(cmd)
            assert app.checked(cmd) is (not default), cmd
            assert _truthy(app.pref(pref)) is (not default), pref
            app.run(cmd)
            assert app.checked(cmd) is default, cmd
            assert _truthy(app.pref(pref)) is default, pref
        app.run(IGNORE_CASE)
        app.restart()
        assert app.checked(IGNORE_CASE) is True
    finally:
        app.set_prefs(**DEFAULTS)


IGNORE_PAIRS = {
    IGNORE_CASE: ("alpha\nx\n", "Alpha\nx\n", "1 added, 1 removed, 0 changed, 1 unchanged."),
    IGNORE_SPACES: ("a b\nc\n", "a  b\nc\n", "0 added, 0 removed, 1 changed, 1 unchanged."),
    IGNORE_EMPTY: ("a\nb\n", "a\n\n\nb\n", "0 added, 2 removed, 0 changed, 2 unchanged."),
}


@pytest.mark.case("COMPARE-032")
@pytest.mark.parametrize("option", list(IGNORE_PAIRS), ids=["case", "spaces", "empty"])
def test_compare_032_each_ignore_option_makes_its_kind_of_difference_equal(cmp, tmp, option):
    """COMPARE-032: Each ignore option makes its kind of difference equal"""
    app = cmp
    doc_text, other_text, off_summary = IGNORE_PAIRS[option]
    doc = write(tmp, "doc.txt", doc_text)
    other = write(tmp, "other.txt", other_text)
    assert open_and_compare(app, doc, other) == off_summary
    app.run(CLEAR)
    app.run(option)
    try:
        assert alerts(compare_with_file(app, other))[-1]["informative"] == IDENTICAL
    finally:
        app.run(option)


@pytest.mark.case("COMPARE-033")
@pytest.mark.parametrize("option", [
    IGNORE_CASE,
    IGNORE_SPACES,
    IGNORE_EMPTY,
], ids=["case", "spaces", "empty"])
def test_compare_033_toggling_an_option_while_comparing_re_runs_the_comparison_at(cmp, tmp, option):
    """COMPARE-033: Toggling an option while comparing re-runs the comparison at once"""
    app = cmp
    doc_text, other_text, off_summary = IGNORE_PAIRS[option]
    doc = write(tmp, "doc.txt", doc_text)
    other = write(tmp, "other.txt", other_text)
    assert open_and_compare(app, doc, other) == off_summary
    app.run(option)
    try:
        app.idle(0.2)
        assert bar(app) == IDENTICAL
    finally:
        app.run(option)


@pytest.mark.case("COMPARE-034")
def test_compare_034_turning_an_option_off_again_brings_the_differences_back(cmp, tmp):
    """COMPARE-034: Turning an option off again brings the differences back"""
    app = cmp
    doc = write(tmp, "doc.txt", "a\nb\n")
    other = write(tmp, "other.txt", "a\n\n\nb\n")
    open_and_compare(app, doc, other)
    app.run(IGNORE_EMPTY)
    wait_bar(app, IDENTICAL)
    app.run(IGNORE_EMPTY)
    app.idle(0.2)
    assert bar(app) == "0 added, 2 removed, 0 changed, 2 unchanged."
    assert has(app, 1, 3, "sub")


@pytest.mark.case("COMPARE-035")
def test_compare_035_detect_moves_off_turns_a_move_into_a_removal_and_an_addition(cmp, tmp):
    """COMPARE-035: Detect Moves off turns a move into a removal and an addition"""
    app = cmp
    mo = write(tmp, "mo.txt", MOVED_OLD)
    mn = write(tmp, "mn.txt", MOVED_NEW)
    open_and_compare(app, mn, mo)
    app.run(DETECT_MOVES)
    try:
        wait_bar(app, "3 added, 2 removed, 1 changed, 4 unchanged.")
        assert has(app, 0, 2) and not has(app, 0, 4)
    finally:
        app.run(DETECT_MOVES)
    wait_bar(app, SUMMARY_MOVED)


@pytest.mark.case("COMPARE-036")
def test_compare_036_detect_character_differences_off_marks_the_whole_differing_w(cmp, tmp):
    """COMPARE-036: Detect Character Differences off marks the whole differing word"""
    app = cmp
    h1 = write(tmp, "h1.txt", "say hello world now\n")
    h2 = write(tmp, "h2.txt", "say hallo world now\n")
    open_and_compare(app, h2, h1)
    marked = lambda: [i for i, x in enumerate(ind18(app, 0, 12)) if x]  # noqa: E731
    assert marked() == [5]
    app.run(CHAR_DIFFS)
    try:
        assert marked() == [4, 5, 6, 7, 8]
    finally:
        app.run(CHAR_DIFFS)
    assert marked() == [5]


# ---- Typing, the revert arrow, leaving -----------------------------------------------

@pytest.mark.case("COMPARE-037")
def test_compare_037_typing_while_comparing_updates_marks_arrows_and_summary(cmp, tmp):
    """COMPARE-037: Typing while comparing updates marks, arrows and summary"""
    app = cmp
    compared_new_old(app, tmp)
    first = app.sci(SCI_GETFIRSTVISIBLELINE)
    app.select(4, 1)
    app.type("epsilon\n")
    app.wait(lambda: has(app, 3, 2) and has(app, 4, 2), timeout=5, message="added marks on lines 4-5")
    wait_bar(app, "2 added, 0 removed, 1 changed, 2 unchanged.")
    assert has(app, 3, 9) and has(app, 4, 9)
    assert app.doc()["modified"]
    assert app.sci(SCI_GETFIRSTVISIBLELINE) == first


@pytest.mark.case("COMPARE-038")
def test_compare_038_editing_the_texts_equal_turns_the_view_identical(cmp, tmp):
    """COMPARE-038: Editing the texts equal turns the view identical"""
    app = cmp
    compared_new_old(app, tmp)
    app.set_text(OLD)
    wait_bar(app, IDENTICAL)
    mask = BACKGROUND_BITS | (1 << 9)
    for view in ("main", "sub"):
        assert all(m & mask == 0 for m in all_marks(app, view)), view
    assert margin5(app) == 0


@pytest.mark.case("COMPARE-039")
def test_compare_039_revert_arrows_stand_beside_each_run_of_differences(cmp, tmp):
    """COMPARE-039: Revert arrows stand beside each run of differences"""
    app = cmp
    old, _ = compared_new_old(app, tmp)
    assert [has(app, i, 9) for i in range(4)] == [False, True, False, True]
    app.run(CLEAR)
    short = write(tmp, "short.txt", "alpha\ngamma\n")
    open_and_compare(app, short, old)
    assert has(app, 1, 9)
    assert not has(app, 0, 9)


@pytest.mark.case("COMPARE-040")
def test_compare_040_the_revert_arrow_puts_a_run_back_in_one_undo_step(cmp, tmp):
    """COMPARE-040: The revert arrow puts a run back, in one undo step"""
    app = cmp
    old, _ = compared_new_old(app, tmp)
    # The revert margin is clicked through the editor's own handler: e2e_mouse's margin
    # point does not reach Scintilla's margin view (a click in margin 1 does not bookmark
    # either).
    revert = lambda line: app.invoke("editor", "compareRevertChangeAtLine:", [line])  # noqa: E731
    assert revert(1) in (True, 1)
    assert app.text() == "alpha\nbeta x\ngamma\ndelta\n"
    wait_bar(app, "1 added, 0 removed, 0 changed, 3 unchanged.")
    assert revert(3) in (True, 1)
    assert app.text() == OLD
    wait_bar(app, IDENTICAL)
    app.select(1)
    app.keys("cmd+z")
    app.keys("cmd+z")
    assert app.text() == NEW
    app.run(CLEAR)
    short = write(tmp, "short.txt", "alpha\ngamma\n")
    open_and_compare(app, short, old)
    assert revert(1) in (True, 1)
    assert app.text() == OLD
    # no arrow on line 1 of a fresh comparison: nothing happens
    app.run(CLEAR)
    open_and_compare(app, short, old)
    before = app.text()
    assert app.invoke("editor", "compareRevertChangeAtLine:", [0]) in (False, 0)
    assert app.text() == before


@pytest.mark.case("COMPARE-041")
def test_compare_041_escape_in_the_document_ends_the_comparison(cmp, tmp):
    """COMPARE-041: Escape in the document ends the comparison"""
    app = cmp
    old, new = pair(tmp)
    app.open(old)
    app.run(SET_FIRST)
    app.open(new)
    app.run(COMPARE)
    app.modal_log(clear=True)
    app.select(1)   # the main pane has the keys
    app.keys("escape")
    app.wait(lambda: bar(app) is None, message="the bar gone")
    assert_view_cleared(app)
    assert app.text() == NEW
    app.run(COMPARE)
    assert alerts(app.modal_log())[-1]["informative"] == SUMMARY_NEW_OLD


@pytest.mark.case("COMPARE-042")
def test_compare_042_escape_also_leaves_a_comparison_of_identical_files(cmp, tmp):
    """COMPARE-042: Escape also leaves a comparison of identical files"""
    app = cmp
    old = write(tmp, "old.txt", OLD)
    same = write(tmp, "same.txt", OLD)
    assert open_and_compare(app, same, old) == IDENTICAL
    app.select(1)
    app.keys("escape")
    app.idle(0.2)
    assert bar(app) is None
    assert not second_pane_shown(app)


@pytest.mark.case("COMPARE-043")
def test_compare_043_clear_active_compare_from_the_compare_and_the_git_menu_keeps(cmp, tmp):
    """COMPARE-043: Clear Active Compare, from the Compare and the Git menu, keeps the first file"""
    app = cmp
    old, new = pair(tmp)
    app.open(old)
    app.run(SET_FIRST)
    app.open(new)
    app.run(COMPARE)
    for clear in (CLEAR, GIT_CLEAR):
        app.run(clear)
        assert_view_cleared(app)
        app.modal_log(clear=True)
        app.run(COMPARE)
        assert alerts(app.modal_log())[-1]["informative"] == SUMMARY_NEW_OLD


@pytest.mark.case("COMPARE-044")
def test_compare_044_clear_all_compares_also_forgets_the_first_file(cmp, tmp):
    """COMPARE-044: Clear All Compares also forgets the first file"""
    app = cmp
    old, new = pair(tmp)
    app.open(old)
    app.run(SET_FIRST)
    app.open(new)
    app.run(COMPARE)
    app.run(CLEAR_ALL)
    assert_view_cleared(app)
    app.modal_log(clear=True)
    app.run(COMPARE)
    assert [e["message"] for e in alerts(app.modal_log())] == [NOTHING_TITLE]


@pytest.mark.case("COMPARE-045")
def test_compare_045_switching_tabs_keeps_the_compared_document_s_marks_closing_i(cmp, tmp):
    """COMPARE-045: Switching tabs keeps the compared document's marks; closing it ends the comparison"""
    app = cmp
    old, new = pair(tmp)
    c2 = write(tmp, "c2.txt", "one\ntwo\nthree\nfour\nfive\n")
    app.open(c2)
    open_and_compare(app, new, old)
    app.call("go_to", document="c2.txt", line=1)
    app.call("go_to", document="new.txt", line=1)
    assert has(app, 1, 0) and has(app, 1, 10)
    app.call("close_document", document="new.txt", discard_changes=True)
    app.wait(lambda: app.doc()["title"] != "new.txt", message="another document in front")
    app.select(3)
    assert bar(app) is None
    assert not second_pane_shown(app)
    assert margin5(app) == 0
    app.run(NEXT)
    assert caret_line(app) == 3
