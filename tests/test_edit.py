"""EDIT: end-to-end tests (plan: plan/EDIT.md)."""
import datetime
import json
import os
import re
import stat

import pytest

from harness.app import ToolError
from harness.sci import *  # noqa: F401,F403
from _util_edit import (prefs, caret, pos, anchor, ranges, sorted_ranges, ac_active, ac_current, ac_list,
                        ac_cancel, calltip_active, calltip_cancel, column_rect, write, invoke_menu, log_kinds)


def new(app, text="", language=None):
    app.new(text, language=language)
    app.keys("cmd+up")


def rc(app):
    c = app.selection()["caret"]
    return c["line"], c["column"]


def select_all(app):
    app.run("IDM_EDIT_SELECTALL")


def goto_doc(app, index):
    app.call("go_to", document=index, line=1)


def current_doc(app):
    return next(d for d in app.docs() if d.get("current"))


# ---- undo, redo, clipboard -----------------------------------------------------------------

@pytest.mark.case("EDIT-001")
def test_edit_001_undo_and_redo_revert_and_reapply_a_typed_edit(app):
    """EDIT-001: Undo and Redo revert and reapply a typed edit"""
    # "abc" is an edit of a new document, not its saved state (open_document with the text would
    # make it one, and Undo back to it would rightly clear "modified"), and a step of its own
    # (typed, it would join the "d" in one undo step, as Scintilla groups typing).
    new(app, "")
    app.set_text("abc")
    app.keys("cmd+down")
    app.type("d")
    assert app.text() == "abcd"
    app.run("IDM_EDIT_UNDO")
    assert app.text() == "abc"
    app.run("IDM_EDIT_REDO")
    assert app.text() == "abcd"
    app.keys("cmd+z")
    assert app.text() == "abc"
    assert app.doc()["modified"] is True
    # Shift+Cmd+Z through e2e_keys arrives unshifted; the key is checked on the menu item instead.
    app.run("IDM_EDIT_REDO")
    assert app.text() == "abcd"
    assert app.menu_item("IDM_EDIT_UNDO")["key"] == "cmd+z"
    assert app.menu_item("IDM_EDIT_REDO")["key"] == "shift+cmd+z"


@pytest.mark.case("EDIT-002")
def test_edit_002_undo_and_redo_are_enabled_only_when_there_is_something_to_un(app):
    """EDIT-002: Undo and Redo are enabled only when there is something to undo or redo"""
    new(app)

    def state():
        m = app.menu("IDM_EDIT_UNDO", "IDM_EDIT_REDO")
        return m["IDM_EDIT_UNDO"]["enabled"], m["IDM_EDIT_REDO"]["enabled"]

    assert state() == (False, False)
    app.type("x")
    assert state() == (True, False)
    app.run("IDM_EDIT_UNDO")
    assert state() == (False, True)
    app.type("y")
    assert state()[1] is False


@pytest.mark.case("EDIT-003")
def test_edit_003_one_undo_takes_back_a_whole_document_command(app):
    """EDIT-003: One Undo takes back a whole-document command"""
    new(app, "c\nb\na\n")
    app.run("IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING")
    assert app.text() == "a\nb\nc\n"
    app.keys("cmd+z")
    assert app.text() == "c\nb\na\n"
    app.run("IDM_EDIT_REDO")
    assert app.text() == "a\nb\nc\n"
    new(app, "one two")
    select_all(app)
    app.run("IDM_EDIT_UPPERCASE")
    app.keys("cmd+z")
    assert app.text() == "one two"
    app.run("IDM_EDIT_REDO")
    assert app.text() == "ONE TWO"


@pytest.mark.case("EDIT-004")
def test_edit_004_undoing_back_to_the_saved_state_clears_the_modified_mark(app, tmp):
    """EDIT-004: Undoing back to the saved state clears the modified mark"""
    p = write(tmp / "u.txt", "saved\n")
    app.open(p)
    app.keys("cmd+up")
    app.type("X")
    assert app.doc()["modified"] is True
    app.keys("cmd+z")
    assert app.text() == "saved\n"
    assert app.doc()["modified"] is False
    assert p.read_text() == "saved\n"


@pytest.mark.case("EDIT-005")
def test_edit_005_copy_puts_exactly_the_selection_on_the_clipboard(app):
    """EDIT-005: Copy puts exactly the selection on the clipboard"""
    text = "héllo wörld 👍\r\nline two"
    new(app, text)
    app.select(1, 1, 2, 5)
    app.run("IDM_EDIT_COPY")
    assert app.clipboard() == "héllo wörld 👍\r\nline"
    assert app.text() == text
    assert app.selection()["text"] == "héllo wörld 👍\r\nline"
    app.select(1, 7, 1, 12)
    app.keys("cmd+c")
    assert app.clipboard() == "wörld"


@pytest.mark.case("EDIT-006")
def test_edit_006_cut_removes_the_selection_and_puts_it_on_the_clipboard(app):
    """EDIT-006: Cut removes the selection and puts it on the clipboard"""
    new(app, "cut this text")
    app.select(1, 5, 1, 10)
    app.run("IDM_EDIT_CUT")
    assert app.text() == "cut text"
    assert app.clipboard() == "this "
    app.keys("cmd+z")
    assert app.text() == "cut this text"
    app.select(1, 10, 1, 14)
    app.keys("cmd+x")
    assert app.text() == "cut this "
    assert app.clipboard() == "text"


@pytest.mark.case("EDIT-007")
def test_edit_007_copy_and_cut_with_nothing_selected_take_the_whole_line(app):
    """EDIT-007: Copy and Cut with nothing selected take the whole line"""
    with prefs(app, lineCopyCutWithoutSelection=True):
        new(app, "line1\nline2\nlast")
        app.select(1, 3)
        app.keys("cmd+c")
        assert app.clipboard() == "line1\n"
        assert app.text() == "line1\nline2\nlast"
        app.select(2, 2)
        app.keys("cmd+x")
        assert app.clipboard() == "line2\n"
        assert app.text() == "line1\nlast"
        app.select(2, 2)
        app.keys("cmd+c")
        assert app.clipboard() == "last\n"


@pytest.mark.case("EDIT-008")
def test_edit_008_with_line_copy_turned_off_copy_and_cut_with_no_selection_do(app):
    """EDIT-008: With line copy turned off, Copy and Cut with no selection do nothing"""
    with prefs(app, lineCopyCutWithoutSelection=False):
        app.clipboard(set="keep")
        new(app, "line1\nline2\n")
        app.select(1, 3)
        app.run("IDM_EDIT_COPY")
        app.run("IDM_EDIT_CUT")
        assert app.clipboard() == "keep"
        assert app.text() == "line1\nline2\n"


@pytest.mark.case("EDIT-009")
def test_edit_009_paste_inserts_at_the_caret_and_replaces_a_selection(app):
    """EDIT-009: Paste inserts at the caret and replaces a selection"""
    app.clipboard(set="XY")
    new(app, "abc")
    app.select(1, 2)
    assert app.enabled("IDM_EDIT_PASTE")
    app.run("IDM_EDIT_PASTE")
    assert app.text() == "aXYbc"
    assert rc(app) == (1, 4)
    app.select(1, 5, 1, 6)
    app.keys("cmd+v")
    assert app.text() == "aXYbXY"


@pytest.mark.case("EDIT-010")
def test_edit_010_paste_is_disabled_with_an_empty_clipboard_and_in_a_read_only(app):
    """EDIT-010: Paste is disabled with an empty clipboard and in a read-only document"""
    app.clipboard(clear=True)
    new(app, "abc")
    assert not app.enabled("IDM_EDIT_PASTE")
    app.clipboard(set="z")
    assert app.enabled("IDM_EDIT_PASTE")
    app.run("IDM_EDIT_TOGGLEREADONLY")
    try:
        assert not app.enabled("IDM_EDIT_PASTE")
        r = app.run("IDM_EDIT_PASTE", expect_ran=False)
        assert not r.get("ran")
        assert app.text() == "abc"
    finally:
        app.run("IDM_EDIT_TOGGLEREADONLY")


@pytest.mark.case("EDIT-011")
def test_edit_011_pasted_line_endings_follow_the_document_s_end_of_line_format(app, tmp):
    """EDIT-011: Pasted line endings follow the document's end-of-line format"""
    p = write(tmp / "crlf.txt", b"a\r\nb\r\n")
    app.open(p)
    assert app.doc()["eol"] == "CRLF"
    app.clipboard(set="x\ny\n")
    app.keys("cmd+down")
    app.run("IDM_EDIT_PASTE")
    assert app.text() == "a\r\nb\r\nx\r\ny\r\n"
    assert app.doc()["eol"] == "CRLF"


@pytest.mark.case("EDIT-012")
def test_edit_012_pasting_code_into_an_empty_document_detects_its_language(app):
    """EDIT-012: Pasting code into an empty document detects its language"""
    code = "#!/usr/bin/env python3\nprint('hi')\n"
    app.clipboard(set=code)
    new(app)
    app.run("IDM_EDIT_PASTE")
    app.wait(lambda: app.doc()["language"] == "python")
    assert app.modal_log() == []
    new(app, "x\n")
    app.keys("cmd+down")
    app.run("IDM_EDIT_PASTE")
    app.idle(0.3)
    assert app.doc()["language"] == "normal"


@pytest.mark.case("EDIT-013")
def test_edit_013_delete_removes_the_selection_or_the_character_after_the_care(app):
    """EDIT-013: Delete removes the selection, or the character after the caret"""
    app.clipboard(set="clip")
    new(app, "delete me")
    app.select(1, 1, 1, 8)
    app.run("IDM_EDIT_DELETE")
    assert app.text() == "me"
    app.select(1, 1)
    app.run("IDM_EDIT_DELETE")
    assert app.text() == "e"
    new(app, "é👍x")
    app.keys("right")
    app.run("IDM_EDIT_DELETE")
    assert app.text() == "éx"
    assert app.clipboard() == "clip"


@pytest.mark.case("EDIT-014")
def test_edit_014_select_all_selects_the_whole_document(app):
    """EDIT-014: Select All selects the whole document"""
    text = "one\ntwo 日本\n"
    new(app, text)
    app.run("IDM_EDIT_SELECTALL")
    s = app.selection()
    assert s["text"] == text
    assert s["end"]["position"] - s["start"]["position"] == len(text.encode())
    app.keys("right")
    app.keys("cmd+a")
    assert app.selection()["text"] == text
    new(app)
    app.run("IDM_EDIT_SELECTALL")
    assert app.selection()["text"] == ""


@pytest.mark.case("EDIT-015")
def test_edit_015_copy_works_in_a_read_only_document_but_cut_paste_and_delete(app):
    """EDIT-015: Copy works in a read-only document but Cut, Paste and Delete do not change it"""
    new(app, "locked text")
    app.run("IDM_EDIT_TOGGLEREADONLY")
    try:
        app.select(1, 1, 1, 7)
        app.keys("cmd+c")
        assert app.clipboard() == "locked"
        app.keys("cmd+x")
        assert app.text() == "locked text"
        app.clipboard(set="Z")
        app.keys("cmd+v")
        assert app.text() == "locked text"
        app.run("IDM_EDIT_DELETE", expect_ran=False)
        assert app.text() == "locked text"
    finally:
        app.run("IDM_EDIT_TOGGLEREADONLY")


# ---- begin/end select ------------------------------------------------------------------

@pytest.mark.case("EDIT-016")
def test_edit_016_begin_end_select_anchors_then_selects_to_the_caret(app):
    """EDIT-016: Begin/End Select anchors, then selects to the caret"""
    new(app, "0123456789\n")
    app.select(1, 3)
    app.run("IDM_EDIT_BEGINENDSELECT")
    assert app.selection()["text"] == ""
    app.select(1, 7)
    app.run("IDM_EDIT_BEGINENDSELECT")
    assert app.selection()["text"] == "2345"
    app.select(1, 8)
    app.run("IDM_EDIT_BEGINENDSELECT")
    app.select(1, 2)
    app.run("IDM_EDIT_BEGINENDSELECT")
    assert app.selection()["text"] == "123456"
    assert pos(app) == 1 and anchor(app) == 7


@pytest.mark.case("EDIT-017")
def test_edit_017_begin_end_select_in_column_mode_makes_a_rectangle(app):
    """EDIT-017: Begin/End Select in Column Mode makes a rectangle"""
    new(app, "0123456789\nabcdefghij\n")
    app.select(1, 3)
    app.run("IDM_EDIT_BEGINENDSELECT_COLUMNMODE")
    app.select(2, 6)
    app.run("IDM_EDIT_BEGINENDSELECT_COLUMNMODE")
    assert app.selection()["rectangular"]
    assert sorted_ranges(app) == [(2, 5), (13, 16)]
    app.type("#")
    assert app.text() == "01#56789\nab#fghij\n"


@pytest.mark.case("EDIT-018")
def test_edit_018_begin_end_select_shows_that_it_has_started(app):
    """EDIT-018: Begin/End Select shows that it has started"""
    new(app, "0123456789\n")
    app.run("IDM_EDIT_BEGINENDSELECT")
    try:
        m = app.menu("IDM_EDIT_BEGINENDSELECT", "IDM_EDIT_BEGINENDSELECT_COLUMNMODE")
        assert m["IDM_EDIT_BEGINENDSELECT"]["checked"]
        assert not m["IDM_EDIT_BEGINENDSELECT_COLUMNMODE"]["enabled"]
    finally:
        app.run("IDM_EDIT_BEGINENDSELECT")
    m = app.menu("IDM_EDIT_BEGINENDSELECT", "IDM_EDIT_BEGINENDSELECT_COLUMNMODE")
    assert not m["IDM_EDIT_BEGINENDSELECT"]["checked"]
    assert m["IDM_EDIT_BEGINENDSELECT_COLUMNMODE"]["enabled"]


# ---- insert date/time ---------------------------------------------------------------------

TIME_RE = r"\d{1,2}:\d{2}(?:[\s ]?[AaPp]\.?[Mm]\.?)?"


def stamp_in_brackets(app, command):
    new(app, "[]")
    app.keys("right")
    app.run(command)
    t = app.text()
    assert t.startswith("[") and t.endswith("]")
    assert pos(app) == len(t.encode()) - 1
    return t[1:-1]


@pytest.mark.case("EDIT-019")
def test_edit_019_insert_date_time_short_and_long(app):
    """EDIT-019: Insert Date Time (short) and (long)"""
    today = datetime.date.today()
    with prefs(app, reverseDateTimeOrder=False):
        short = stamp_in_brackets(app, "IDM_EDIT_INSERT_DATETIME_SHORT")
        assert re.match(TIME_RE + r"\s", short), short
        assert str(today.day) in short and (str(today.year) in short or str(today.year)[2:] in short)
        long = stamp_in_brackets(app, "IDM_EDIT_INSERT_DATETIME_LONG")
        assert re.match(TIME_RE + r"\s", long), long
        assert today.strftime("%B") in long and str(today.year) in long


@pytest.mark.case("EDIT-020")
def test_edit_020_reverse_date_time_order_puts_the_date_first(app):
    """EDIT-020: Reverse date/time order puts the date first"""
    with prefs(app, reverseDateTimeOrder=True):
        for cmd in ("IDM_EDIT_INSERT_DATETIME_SHORT", "IDM_EDIT_INSERT_DATETIME_LONG"):
            s = stamp_in_brackets(app, cmd)
            assert re.search(r"\s" + TIME_RE + "$", s), s
            assert not re.match(TIME_RE + r"\s", s), s


@pytest.mark.case("EDIT-021")
def test_edit_021_insert_date_time_customized_uses_the_format_from_preferences(app):
    """EDIT-021: Insert Date Time (customized) uses the format from Preferences"""
    today = datetime.date.today()
    with prefs(app, customDateFormat="yyyy-MM-dd HH:mm:ss"):
        new(app)
        app.run("IDM_EDIT_INSERT_DATETIME_CUSTOMIZED")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", app.text())
        assert app.text().startswith(today.strftime("%Y-%m-%d"))
    with prefs(app, customDateFormat="yyyy/MM/dd"):
        new(app)
        app.run("IDM_EDIT_INSERT_DATETIME_CUSTOMIZED")
        assert app.text() == today.strftime("%Y/%m/%d")
    with prefs(app, customDateFormat="HH:mm"):
        new(app)
        app.run("IDM_EDIT_INSERT_DATETIME_CUSTOMIZED")
        assert re.fullmatch(r"\d{2}:\d{2}", app.text())
    assert app.modal_log() == []


@pytest.mark.case("EDIT-022")
def test_edit_022_an_inserted_stamp_replaces_the_selection_in_one_undo_step(app):
    """EDIT-022: An inserted stamp replaces the selection in one undo step"""
    with prefs(app, customDateFormat="yyyy"):
        new(app, "year: XXXX.")
        app.select(1, 7, 1, 11)
        app.run("IDM_EDIT_INSERT_DATETIME_CUSTOMIZED")
        assert app.text() == f"year: {datetime.date.today().year}."
        app.keys("cmd+z")
        assert app.text() == "year: XXXX."


# ---- copy paths --------------------------------------------------------------------------

@pytest.mark.case("EDIT-023")
def test_edit_023_copy_full_path_file_name_and_folder_of_a_saved_file(app, tmp):
    """EDIT-023: Copy full path, file name and folder of a saved file"""
    p = write(tmp / "dir with space" / "Ünï file.txt", "x\n")
    app.open(p)
    app.clipboard(set="zzz")
    app.run("IDM_EDIT_FULLPATHTOCLIP")
    assert app.same_path(app.clipboard(), p)
    app.clipboard(set="zzz")
    app.run("IDM_EDIT_FILENAMETOCLIP")
    assert app.clipboard() == "Ünï file.txt"
    app.clipboard(set="zzz")
    app.run("IDM_EDIT_CURRENTDIRTOCLIP")
    d = app.clipboard()
    assert not d.endswith("/")
    assert app.same_path(d, tmp / "dir with space")


@pytest.mark.case("EDIT-024")
def test_edit_024_copy_path_and_name_of_an_untitled_document(app):
    """EDIT-024: Copy path and name of an untitled document"""
    title = app.doc()["title"]
    app.clipboard(set="zzz")
    app.run("IDM_EDIT_FILENAMETOCLIP")
    assert app.clipboard() == title
    app.clipboard(set="zzz")
    app.run("IDM_EDIT_CURRENTDIRTOCLIP")
    assert app.clipboard() == ""
    app.clipboard(set="zzz")
    app.run("IDM_EDIT_FULLPATHTOCLIP")
    assert app.clipboard() == title


@pytest.mark.case("EDIT-025")
def test_edit_025_copy_all_filenames_and_copy_all_file_paths_list_every_tab_in(app, tmp):
    """EDIT-025: Copy All Filenames and Copy All File Paths list every tab in order

    The untitled tab gets a character first: a lone clean "new 1" is taken over by the next
    file opened (FILE-007, upstream's loadBufferIntoView), and there would be none to list."""
    app.type("x")
    untitled = app.docs()[0]["title"]
    a = write(tmp / "a.txt", "a")
    b = write(tmp / "b.md", "b")
    app.open(a)
    app.open(b)
    app.run("IDM_EDIT_COPY_ALL_NAMES")
    assert app.clipboard() == f"{untitled}\na.txt\nb.md"
    app.run("IDM_EDIT_COPY_ALL_PATHS")
    lines = app.clipboard().split("\n")
    assert len(lines) == 3
    assert lines[0] == untitled
    assert app.same_path(lines[1], a) and app.same_path(lines[2], b)


# ---- indent --------------------------------------------------------------------------------

@pytest.mark.case("EDIT-026")
def test_edit_026_increase_and_decrease_line_indent_shift_whole_lines(app):
    """EDIT-026: Increase and Decrease Line Indent shift whole lines"""
    with prefs(app, useSpaces=False, tabWidth=4):
        new(app, "a\n  b\nc\n")
        app.select(1, 1, 2, 2)
        app.run("IDM_EDIT_INS_TAB")
        assert app.text() == "\ta\n\t  b\nc\n"
        app.run("IDM_EDIT_RMV_TAB")
        app.run("IDM_EDIT_RMV_TAB")
        assert app.text() == "a\nb\nc\n"
    with prefs(app, useSpaces=True, tabWidth=2):
        new(app, "a\n  b\nc\n")
        app.select(3, 1)
        app.run("IDM_EDIT_INS_TAB")
        assert app.text() == "a\n  b\n  c\n"


@pytest.mark.case("EDIT-027")
def test_edit_027_indent_keys_cmd_and_cmd_and_indenting_a_line_in_the_middle_o(app):
    """EDIT-027: Indent keys Cmd+] and Cmd+[ and indenting a line in the middle of text"""
    with prefs(app, useSpaces=False, tabWidth=4):
        new(app, "x = 1\n")
        app.select(1, 3)
        app.keys("cmd+]")
        assert app.text() == "\tx = 1\n"
        assert pos(app) == 3
        app.keys("cmd+[")
        assert app.text() == "x = 1\n"
        app.keys("cmd+[")
        assert app.text() == "x = 1\n"


# ---- convert case ----------------------------------------------------------------------------

CASES = [
    ("IDM_EDIT_UPPERCASE", "hello Wörld é", "HELLO WÖRLD É"),
    ("IDM_EDIT_LOWERCASE", "HeLLo WÖRLD", "hello wörld"),
    ("IDM_EDIT_PROPERCASE_FORCE", "hELLO wORLD don't 3rd", "Hello World Don't 3rd"),
    ("IDM_EDIT_PROPERCASE_BLEND", "hELLO wORLD", "HELLO WORLD"),
    ("IDM_EDIT_SENTENCECASE_FORCE", "hi THERE. bye! ok? i think so", "Hi there. Bye! Ok? I think so"),
    ("IDM_EDIT_SENTENCECASE_BLEND", "hi THERE. bye", "Hi THERE. Bye"),
    ("IDM_EDIT_INVERTCASE", "AbC dÉ", "aBc Dé"),
]


@pytest.mark.case("EDIT-028")
def test_edit_028_each_case_conversion_transforms_the_selected_text(app):
    """EDIT-028: Each case conversion transforms the selected text"""
    for cmd, before, after in CASES:
        new(app, before)
        select_all(app)
        app.run(cmd)
        assert app.text() == after, cmd
        s = app.selection()
        assert s["end"]["position"] - s["start"]["position"] == len(after.encode()), cmd


@pytest.mark.case("EDIT-029")
def test_edit_029_random_case_keeps_the_letters_and_scrambles_their_case(app):
    """EDIT-029: Random case keeps the letters and scrambles their case"""
    src = "abcdefgh" * 8
    changed = False
    for _ in range(5):
        new(app, src)
        select_all(app)
        app.run("IDM_EDIT_RANDOMCASE")
        t = app.text()
        assert t.lower() == src and len(t) == len(src)
        if t != src:
            changed = True
            break
    assert changed


@pytest.mark.case("EDIT-030")
def test_edit_030_convert_case_with_nothing_selected_leaves_the_document_alone(app):
    """EDIT-030: Convert case with nothing selected leaves the document alone"""
    new(app, "hello world")
    app.select(1, 3)
    app.run("IDM_EDIT_UPPERCASE")
    assert app.text() == "hello world"
    assert app.doc()["modified"] is False
    new(app, "HELLO")
    app.run("IDM_EDIT_LOWERCASE")
    assert app.text() == "HELLO"


@pytest.mark.case("EDIT-031")
def test_edit_031_convert_case_in_a_rectangular_or_multiple_selection_converts(app):
    """EDIT-031: Convert case in a rectangular or multiple selection converts only what is selected"""
    new(app, "abcd\nabcd\n")
    column_rect(app, 1, 2, 2, 4)
    app.run("IDM_EDIT_UPPERCASE")
    assert app.text() == "aBCd\naBCd\n"
    new(app, "ab ab ab")
    app.select(1, 1, 1, 3)
    app.run("IDM_EDIT_MULTISELECTALL")
    app.run("IDM_EDIT_INVERTCASE")
    assert app.text() == "AB AB AB"
    assert app.sci(SCI_GETSELECTIONS) == 3


@pytest.mark.case("EDIT-032")
def test_edit_032_case_conversion_of_non_ascii_text_and_text_that_changes_leng(app):
    """EDIT-032: Case conversion of non-ASCII text and text that changes length"""
    new(app, "straße ǆ ﬁ ΣΑΣ x")
    app.select(1, 1, 1, 11)
    assert app.selection()["text"] == "straße ǆ ﬁ"
    app.run("IDM_EDIT_UPPERCASE")
    assert app.text() == "STRASSE Ǆ FI ΣΑΣ x"
    assert app.selection()["text"] == "STRASSE Ǆ FI"
    t = app.text()
    start = len(t) - len("ΣΑΣ x")
    app.select(1, start + 1, 1, start + 4)
    assert app.selection()["text"] == "ΣΑΣ"
    app.run("IDM_EDIT_LOWERCASE")
    assert app.text() in ("STRASSE Ǆ FI σας x", "STRASSE Ǆ FI σασ x")


# ---- line operations -----------------------------------------------------------------------

@pytest.mark.case("EDIT-033")
def test_edit_033_duplicate_current_line(app):
    """EDIT-033: Duplicate Current Line"""
    new(app, "one\ntwo")
    app.select(1, 2)
    app.run("IDM_EDIT_DUP_LINE")
    assert app.text() == "one\none\ntwo"
    assert rc(app) == (1, 2)
    app.keys("cmd+down")
    app.keys("cmd+d")
    assert app.text() == "one\none\ntwo\ntwo"
    assert app.menu_item("IDM_EDIT_DUP_LINE")["key"] == "cmd+d"


@pytest.mark.case("EDIT-034")
def test_edit_034_remove_duplicate_lines_keeps_the_first_of_each(app, tmp):
    """EDIT-034: Remove Duplicate Lines keeps the first of each"""
    new(app, "a\nb\na\nc\nb\n")
    app.run("IDM_EDIT_REMOVE_ANY_DUP_LINES")
    assert app.text() == "a\nb\nc\n"
    new(app, "A\na\n")
    app.run("IDM_EDIT_REMOVE_ANY_DUP_LINES")
    assert app.text() == "A\na\n"
    app.open(write(tmp / "d.txt", b"x\r\ny\r\nx\r\n"))
    app.run("IDM_EDIT_REMOVE_ANY_DUP_LINES")
    assert app.text() == "x\r\ny\r\n"


@pytest.mark.case("EDIT-035")
def test_edit_035_remove_consecutive_duplicate_lines_collapses_only_neighbours(app):
    """EDIT-035: Remove Consecutive Duplicate Lines collapses only neighbours"""
    new(app, "a\na\nb\na\na\na\n")
    app.run("IDM_EDIT_REMOVE_CONSECUTIVE_DUP_LINES")
    assert app.text() == "a\nb\na\n"


@pytest.mark.case("EDIT-036")
def test_edit_036_line_removals_act_only_on_the_selected_lines(app):
    """EDIT-036: Line removals act only on the selected lines"""
    new(app, "a\nb\nb\na\nb\n")
    app.select(2, 1, 4, 2)
    app.run("IDM_EDIT_REMOVE_ANY_DUP_LINES")
    assert app.text() == "a\nb\na\nb\n"
    new(app, "x\n\ny\n\nz\n")
    app.select(1, 1, 3, 2)
    app.run("IDM_EDIT_REMOVEEMPTYLINES")
    assert app.text() == "x\ny\n\nz\n"


@pytest.mark.case("EDIT-037")
def test_edit_037_split_lines_breaks_long_lines_at_the_edge_column(app):
    """EDIT-037: Split Lines breaks long lines at the edge column"""
    with prefs(app, edgeMode=1, edgeColumns="8"):
        new(app, "aaa bbb ccc ddd eee fff\nshort\n")
        select_all(app)
        app.run("IDM_EDIT_SPLIT_LINES")
        assert app.text() == "aaa bbb\nccc ddd\neee fff\nshort\n"


@pytest.mark.case("EDIT-038")
def test_edit_038_join_lines_joins_with_single_spaces(app):
    """EDIT-038: Join Lines joins with single spaces"""
    new(app, "a\nb\nc")
    app.select(1, 1, 2, 2)
    app.run("IDM_EDIT_JOIN_LINES")
    assert app.text() == "a b\nc"
    new(app, "a\nb\nc\n")
    app.run("IDM_EDIT_JOIN_LINES")
    assert app.text() == "a b c\n"
    new(app, "x\n")
    app.run("IDM_EDIT_JOIN_LINES")
    assert app.text() == "x\n"


@pytest.mark.case("EDIT-039")
def test_edit_039_move_up_and_move_down_current_line(app):
    """EDIT-039: Move Up and Move Down Current Line"""
    new(app, "line1\nline2\nline3\n")
    app.select(3, 2)
    app.run("IDM_EDIT_LINE_UP")
    assert app.text() == "line1\nline3\nline2\n"
    assert rc(app)[0] == 2
    app.run("IDM_EDIT_LINE_DOWN")
    assert app.text() == "line1\nline2\nline3\n"
    app.select(1, 1)
    app.run("IDM_EDIT_LINE_UP")
    assert app.text() == "line1\nline2\nline3\n"
    app.select(1, 1, 2, 3)
    app.run("IDM_EDIT_LINE_DOWN")
    assert app.text() == "line3\nline1\nline2\n"
    # SCI_MOVESELECTEDLINESDOWN (what Notepad++ runs) leaves the moved lines selected whole, up to
    # the start of the line after them.
    s = app.selection()
    assert s["start"]["line"] == 2 and s["start"]["column"] == 1 and s["text"] == "line1\nline2\n"


@pytest.mark.case("EDIT-040")
def test_edit_040_remove_empty_lines_and_remove_empty_lines_containing_blank_c(app):
    """EDIT-040: Remove Empty Lines and Remove Empty Lines (Containing Blank characters)"""
    src = "a\n\n   \n\t\nb\n\n"
    new(app, src)
    app.run("IDM_EDIT_REMOVEEMPTYLINES")
    assert app.text() == "a\n   \n\t\nb\n"
    new(app, src)
    app.run("IDM_EDIT_REMOVEEMPTYLINESWITHBLANK")
    assert app.text() == "a\nb\n"


@pytest.mark.case("EDIT-041")
def test_edit_041_insert_blank_line_above_and_below_current(app, tmp):
    """EDIT-041: Insert Blank Line Above and Below Current"""
    new(app, "x\ny\n")
    app.select(2, 1)
    app.run("IDM_EDIT_BLANKLINEABOVECURRENT")
    assert app.text() == "x\n\ny\n"
    assert rc(app) == (2, 1)
    app.select(1, 1)
    app.run("IDM_EDIT_BLANKLINEBELOWCURRENT")
    assert app.text() == "x\n\n\ny\n"
    assert rc(app) == (2, 1)
    app.open(write(tmp / "crlf.txt", b"a\r\nb\r\n"))
    app.select(1, 1)
    app.run("IDM_EDIT_BLANKLINEBELOWCURRENT")
    assert app.text() == "a\r\n\r\nb\r\n"


@pytest.mark.case("EDIT-042")
def test_edit_042_reverse_line_order(app):
    """EDIT-042: Reverse Line Order"""
    new(app, "a\nb\nc\n")
    app.run("IDM_EDIT_SORTLINES_REVERSE_ORDER")
    assert app.text() == "c\nb\na\n"
    new(app, "1\n2\n3\n4\n")
    app.select(2, 1, 3, 2)
    app.run("IDM_EDIT_SORTLINES_REVERSE_ORDER")
    assert app.text() == "1\n3\n2\n4\n"
    new(app, "x\ny")
    app.run("IDM_EDIT_SORTLINES_REVERSE_ORDER")
    assert app.text() == "y\nx"


@pytest.mark.case("EDIT-043")
def test_edit_043_randomize_line_order_keeps_every_line(app):
    """EDIT-043: Randomize Line Order keeps every line"""
    lines = [f"l{i:02d}\n" for i in range(1, 21)]
    src = "".join(lines)
    changed = False
    for _ in range(5):
        new(app, src)
        app.run("IDM_EDIT_SORTLINES_RANDOMLY")
        t = app.text()
        assert sorted(t.splitlines(keepends=True)) == sorted(lines)
        if t != src:
            changed = True
            break
    assert changed


SORTS = [
    ("IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING", "B\na\nb\nA\n", "A\nB\na\nb\n"),
    ("IDM_EDIT_SORTLINES_LEXICOGRAPHIC_DESCENDING", "B\na\nb\nA\n", "b\na\nB\nA\n"),
    ("IDM_EDIT_SORTLINES_LEXICO_CASE_INSENS_ASCENDING", "B\na\nC\n", "a\nB\nC\n"),
    ("IDM_EDIT_SORTLINES_LEXICO_CASE_INSENS_DESCENDING", "B\na\nC\n", "C\nB\na\n"),
    ("IDM_EDIT_SORTLINES_LOCALE_ASCENDING", "é\nz\ne\nf\n", "e\né\nf\nz\n"),
    ("IDM_EDIT_SORTLINES_LOCALE_DESCENDING", "é\nz\ne\nf\n", "z\nf\né\ne\n"),
    ("IDM_EDIT_SORTLINES_INTEGER_ASCENDING", "10\n9\n-3\n2\n", "-3\n2\n9\n10\n"),
    ("IDM_EDIT_SORTLINES_INTEGER_DESCENDING", "10\n9\n-3\n2\n", "10\n9\n2\n-3\n"),
    ("IDM_EDIT_SORTLINES_DECIMALCOMMA_ASCENDING", "1,5\n-2,25\n10\n", "-2,25\n1,5\n10\n"),
    ("IDM_EDIT_SORTLINES_DECIMALCOMMA_DESCENDING", "1,5\n-2,25\n10\n", "10\n1,5\n-2,25\n"),
    ("IDM_EDIT_SORTLINES_DECIMALDOT_ASCENDING", "1.5\n1.25\n-0.5\n", "-0.5\n1.25\n1.5\n"),
    ("IDM_EDIT_SORTLINES_DECIMALDOT_DESCENDING", "1.5\n1.25\n-0.5\n", "1.5\n1.25\n-0.5\n"),
    ("IDM_EDIT_SORTLINES_LENGTH_ASCENDING", "ccc\na\nbb\n", "a\nbb\nccc\n"),
    ("IDM_EDIT_SORTLINES_LENGTH_DESCENDING", "ccc\na\nbb\n", "ccc\nbb\na\n"),
]


@pytest.mark.case("EDIT-044")
def test_edit_044_each_sort_command_orders_the_lines_as_notepad_does(app):
    """EDIT-044: Each sort command orders the lines as Notepad++ does"""
    for cmd, before, after in SORTS:
        new(app, before)
        app.run(cmd)
        assert app.text() == after, cmd
    assert app.modal_log() == []


@pytest.mark.case("EDIT-045")
def test_edit_045_integer_sort_compares_digit_runs_as_numbers_natural_order(app):
    """EDIT-045: Integer sort compares digit runs as numbers (natural order)"""
    for cmd, before, after in [
        ("IDM_EDIT_SORTLINES_INTEGER_ASCENDING", "item10\nitem9\nitem2\n", "item2\nitem9\nitem10\n"),
        ("IDM_EDIT_SORTLINES_INTEGER_ASCENDING", "x007\nx7\nx07\n", "x007\nx07\nx7\n"),
        ("IDM_EDIT_SORTLINES_INTEGER_ASCENDING", "a100000000000000000000\na99\n", "a99\na100000000000000000000\n"),
        ("IDM_EDIT_SORTLINES_INTEGER_DESCENDING", "item9\nitem2\nitem10\n", "item10\nitem9\nitem2\n"),
    ]:
        new(app, before)
        app.run(cmd)
        assert app.text() == after, before


@pytest.mark.case("EDIT-046")
def test_edit_046_a_decimal_sort_refuses_a_line_it_cannot_read_and_names_it(app):
    """EDIT-046: A decimal sort refuses a line it cannot read and names it"""
    new(app, "2.5\n-\n1.5\n")
    app.modal_log()
    app.answers(alerts=[1])
    app.run("IDM_EDIT_SORTLINES_DECIMALDOT_ASCENDING")
    log = app.modal_log()
    assert any(e.get("message") == "Sorting Error" and "line 2." in e.get("informative", "") for e in log), log
    assert app.text() == "2.5\n-\n1.5\n"
    new(app, "3,5\n1,5\n-\n")
    app.answers(alerts=[1])
    app.run("IDM_EDIT_SORTLINES_DECIMALCOMMA_ASCENDING")
    log = app.modal_log()
    assert any(e.get("message") == "Sorting Error" and "line 3." in e.get("informative", "") for e in log), log
    assert app.text() == "3,5\n1,5\n-\n"
    new(app, "2.5\nplain\n1.5\n")
    app.run("IDM_EDIT_SORTLINES_DECIMALDOT_ASCENDING")
    assert app.text() == "plain\n1.5\n2.5\n"
    new(app, "2.5\nplain\n1.5\n")
    app.run("IDM_EDIT_SORTLINES_DECIMALDOT_DESCENDING")
    assert app.text() == "2.5\n1.5\nplain\n"
    assert app.modal_log() == []


@pytest.mark.case("EDIT-047")
def test_edit_047_sorting_is_stable_and_keeps_line_endings(app, tmp):
    """EDIT-047: Sorting is stable and keeps line endings"""
    new(app, "b 1\na 1\nc 0\n")
    app.run("IDM_EDIT_SORTLINES_LENGTH_DESCENDING")
    assert app.text() == "b 1\na 1\nc 0\n"
    new(app, "b\nA\na\nB\n")
    app.run("IDM_EDIT_SORTLINES_LEXICO_CASE_INSENS_ASCENDING")
    assert app.text() == "A\na\nb\nB\n"
    app.open(write(tmp / "s.txt", b"b\r\na\r\nc"))
    app.run("IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING")
    assert app.text() == "a\r\nb\r\nc"
    app.open(write(tmp / "cr.txt", b"A\rC\rB\r"))
    app.run("IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING")
    assert app.text() == "A\rB\rC\r"


@pytest.mark.case("EDIT-048")
def test_edit_048_sorting_only_the_selected_lines(app):
    """EDIT-048: Sorting only the selected lines"""
    new(app, "d\nc\nb\na\n")
    app.select(2, 1, 3, 2)
    app.run("IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING")
    assert app.text() == "d\nb\nc\na\n"
    app.select(2, 1, 4, 1)
    app.run("IDM_EDIT_SORTLINES_REVERSE_ORDER")
    assert app.text() == "d\nc\nb\na\n"


@pytest.mark.case("EDIT-049")
def test_edit_049_a_rectangular_selection_sorts_whole_lines_by_the_text_in_its(app):
    """EDIT-049: A rectangular selection sorts whole lines by the text in its columns"""
    new(app, "c 2\nb 3\na 1\n")
    column_rect(app, 1, 3, 3, 4)
    app.run("IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING")
    assert app.text() == "a 1\nc 2\nb 3\n"
    table = "a\t2.5\tx\nb\t10\ty\nc\t-1\tz\nd\t2.5\tw\n"
    for cmd, want in [("IDM_EDIT_SORTLINES_DECIMALDOT_ASCENDING", "c\t-1\tz\na\t2.5\tx\nd\t2.5\tw\nb\t10\ty\n"),
                      ("IDM_EDIT_SORTLINES_DECIMALDOT_DESCENDING", "b\t10\ty\na\t2.5\tx\nd\t2.5\tw\nc\t-1\tz\n")]:
        new(app, table)
        column_rect(app, 1, 3, 4, 3)
        app.run(cmd)
        assert app.text() == want, cmd


@pytest.mark.case("EDIT-050")
def test_edit_050_line_operations_on_an_empty_document_and_a_single_line(app):
    """EDIT-050: Line operations on an empty document and a single line"""
    cmds = ["IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING", "IDM_EDIT_SORTLINES_RANDOMLY",
            "IDM_EDIT_REMOVE_ANY_DUP_LINES", "IDM_EDIT_JOIN_LINES", "IDM_EDIT_SPLIT_LINES",
            "IDM_EDIT_REMOVEEMPTYLINES"]
    for text in ("", "only"):
        for cmd in cmds:
            new(app, text)
            assert app.run(cmd)["ran"]
            assert app.text() == text, (cmd, text)
    assert app.modal_log() == []


# ---- comments ------------------------------------------------------------------------------------

LINE_TOKENS = [("cpp", "//"), ("python", "#"), ("sql", "--"), ("ini", ";"), ("vb", "'"), ("batch", "REM"),
               ("bash", "#")]


@pytest.mark.case("EDIT-051")
def test_edit_051_toggle_single_line_comment_comments_and_uncomments_per_langu(app):
    """EDIT-051: Toggle Single Line Comment comments and uncomments per language"""
    src = "x = 1\n  y = 2\n\n"
    for lang, tok in LINE_TOKENS:
        new(app, src, language=lang)
        select_all(app)
        app.run("IDM_EDIT_BLOCK_COMMENT")
        assert app.text() == f"{tok} x = 1\n  {tok} y = 2\n\n", lang
        select_all(app)
        app.run("IDM_EDIT_BLOCK_COMMENT")
        assert app.text() == src, lang
    new(app, "int a;\n", language="cpp")
    select_all(app)
    app.keys("cmd+/")
    assert app.text() == "// int a;\n"


@pytest.mark.case("EDIT-052")
def test_edit_052_toggling_keeps_the_lines_selected_so_toggling_twice_restores(app):
    """EDIT-052: Toggling keeps the lines selected, so toggling twice restores"""
    src = "x = 1\n  y = 2\n"
    new(app, src, language="python")
    select_all(app)
    app.run("IDM_EDIT_BLOCK_COMMENT")
    assert app.text() == "# x = 1\n  # y = 2\n"
    app.run("IDM_EDIT_BLOCK_COMMENT")
    assert app.text() == src


@pytest.mark.case("EDIT-053")
def test_edit_053_mixed_commented_and_uncommented_lines_are_all_commented(app):
    """EDIT-053: Mixed commented and uncommented lines are all commented"""
    new(app, "// a\nb\n", language="cpp")
    select_all(app)
    app.run("IDM_EDIT_BLOCK_COMMENT")
    assert app.text() == "// // a\n// b\n"


@pytest.mark.case("EDIT-054")
def test_edit_054_single_line_comment_always_adds_a_comment(app):
    """EDIT-054: Single Line Comment always adds a comment"""
    new(app, "// a\nb\n", language="cpp")
    select_all(app)
    assert app.run("IDM_EDIT_BLOCK_COMMENT_SET")["ran"]
    assert app.text() == "// // a\n// b\n"
    new(app, "a\n", language="cpp")
    select_all(app)
    app.run("IDM_EDIT_BLOCK_COMMENT_SET")
    assert app.text() == "// a\n"


@pytest.mark.case("EDIT-055")
def test_edit_055_single_line_uncomment_strips_one_comment_level(app):
    """EDIT-055: Single Line Uncomment strips one comment level"""
    new(app, "// x\n  //y\nz\n// // w\n", language="cpp")
    select_all(app)
    app.run("IDM_EDIT_BLOCK_UNCOMMENT")
    assert app.text() == "x\n  y\nz\n// w\n"


@pytest.mark.case("EDIT-056")
def test_edit_056_single_line_commands_in_a_language_with_no_line_comment(app):
    """EDIT-056: Single-line commands in a language with no line comment"""
    new(app, "text\n")
    select_all(app)
    app.run("IDM_EDIT_BLOCK_COMMENT")
    assert app.text() == "text\n"
    new(app, "<p>hi</p>\n", language="html")
    select_all(app)
    app.run("IDM_EDIT_BLOCK_COMMENT")
    assert app.text() == "<!-- <p>hi</p> -->\n"
    select_all(app)
    app.run("IDM_EDIT_BLOCK_UNCOMMENT")
    assert app.text() == "<p>hi</p>\n"


@pytest.mark.case("EDIT-057")
def test_edit_057_block_comment_wraps_the_selection_in_the_language_s_stream_c(app):
    """EDIT-057: Block Comment wraps the selection in the language's stream comment"""
    new(app, "int value;\n", language="cpp")
    app.select(1, 5, 1, 10)
    app.run("IDM_EDIT_STREAM_COMMENT")
    assert app.text() == "int /*value*/;\n"
    assert app.selection()["text"] == "/*value*/"
    # Option+Cmd+/: Shift+Cmd+/ is Cmd+?, which macOS keeps for the Help menu's search
    assert app.menu_item("IDM_EDIT_STREAM_COMMENT")["key"] == "alt+cmd+/"
    app.keys("cmd+z")
    app.select(1, 5, 1, 10)
    app.keys("alt+cmd+/")
    assert app.text() == "int /*value*/;\n"   # the key works, and keeps working after a press
    new(app, "<p>hi</p>\n", language="html")
    app.select(1, 1, 1, 10)
    app.run("IDM_EDIT_STREAM_COMMENT")
    assert app.text() == "<!--<p>hi</p>-->\n"
    new(app, "a{}\n", language="css")
    app.select(1, 1, 1, 4)
    app.run("IDM_EDIT_STREAM_COMMENT")
    assert app.text() == "/*a{}*/\n"


@pytest.mark.case("EDIT-058")
def test_edit_058_block_uncomment_removes_the_stream_comment_around_the_select(app):
    """EDIT-058: Block Uncomment removes the stream comment around the selection"""
    new(app, "int /*value*/;\n", language="cpp")
    app.select(1, 5, 1, 14)
    app.run("IDM_EDIT_STREAM_UNCOMMENT")
    assert app.text() == "int value;\n"
    new(app, "<!--<p>hi</p>-->\n", language="html")
    app.select(1, 1, 1, 17)
    app.run("IDM_EDIT_STREAM_UNCOMMENT")
    assert app.text() == "<p>hi</p>\n"


@pytest.mark.case("EDIT-059")
def test_edit_059_block_comment_in_a_language_without_stream_comments_changes(app):
    """EDIT-059: Block Comment in a language without stream comments changes nothing"""
    for lang, text in (("python", "x = 1\n"), (None, "text\n")):
        new(app, text, language=lang)
        select_all(app)
        app.run("IDM_EDIT_STREAM_COMMENT")
        app.run("IDM_EDIT_STREAM_UNCOMMENT")
        assert app.text() == text
    assert app.modal_log() == []


# ---- auto-completion ---------------------------------------------------------------------------

@pytest.mark.case("EDIT-060")
def test_edit_060_function_completion_lists_the_language_s_functions(app):
    """EDIT-060: Function Completion lists the language's functions"""
    with prefs(app, autoCompleteOnInput=False):
        for via_key in (False, True):
            new(app, "int main() { pri", language="c")
            app.keys("cmd+down")
            if via_key:
                app.keys("ctrl+space")
            else:
                app.run("IDM_EDIT_AUTOCOMPLETE")
            assert ac_active(app)
            cur = ac_current(app)
            assert cur.startswith("pri"), cur
            assert "printf" in ac_list(app)
            app.keys("return")
            assert app.text() == "int main() { " + cur


@pytest.mark.case("EDIT-061")
def test_edit_061_word_completion_offers_the_document_s_words_and_types_a_lone(app):
    """EDIT-061: Word Completion offers the document's words and types a lone one"""
    with prefs(app, autoCompleteOnInput=False):
        new(app, "alphabet alpine Alpha\nalp")
        app.keys("cmd+down")
        app.run("IDM_EDIT_AUTOCOMPLETE_CURRENTFILE")
        assert ac_active(app)
        assert sorted(ac_list(app)) == ["alphabet", "alpine"]
        app.keys("escape")
        new(app, "alphabet beta\nalp")
        app.keys("cmd+down", "cmd+return")
        assert not ac_active(app)
        assert app.text() == "alphabet beta\nalphabet"


@pytest.mark.case("EDIT-062")
def test_edit_062_word_completion_ignores_case_where_the_language_s_api_file_s(app):
    """EDIT-062: Word Completion ignores case where the language's API file says so"""
    with prefs(app, autoCompleteOnInput=False):
        new(app, "alphabet Alpine\nalp", language="sql")
        app.keys("cmd+down")
        app.run("IDM_EDIT_AUTOCOMPLETE_CURRENTFILE")
        assert ac_active(app)
        lst = ac_list(app)
        assert "alphabet" in lst and "Alpine" in lst
        ac_cancel(app)


@pytest.mark.case("EDIT-063")
def test_edit_063_function_parameters_hint_shows_the_shipped_signature(app):
    """EDIT-063: Function Parameters Hint shows the shipped signature"""
    with prefs(app, functionHintOnInput=False, autoCompleteOnInput=False):
        new(app, "x = abs(1);\n", language="c")
        app.select(1, 10)
        app.run("IDM_EDIT_FUNCCALLTIP")
        assert calltip_active(app)
        st = app.invoke("editor", "apiCallTipState")
        assert st and st["name"] == "abs"
        # The tip shown is built from the API entry's overload (return value, name, parameters in
        # the language's start/stop/separator), as Notepad++'s FunctionCallTip does; the editor's
        # callTipCandidates is a fallback keyed on the word under the caret, not what is shown.
        o = st["overload"]
        ret = app.get("editor", "apiCallTipState.entry.overloads.returnValue")[o]
        params = app.get("editor", "apiCallTipState.entry.overloads.params")[o]
        env = st["env"]
        shown = f"{ret} {st['name']} {env['start']}" + f"{env['param']} ".join(params) + env["stop"]
        assert shown == "int abs (int i)"
        app.keys("escape")
        assert not calltip_active(app)
        # Ctrl+Shift+Space: shifted chords from e2e_keys are not matched by the menu; checked on the item.
        assert app.menu_item("IDM_EDIT_FUNCCALLTIP")["key"] == "ctrl+shift+ "


@pytest.mark.case("EDIT-064")
def test_edit_064_previous_and_next_hint_step_between_overloads(app):
    """EDIT-064: Previous and Next Hint step between overloads"""
    with prefs(app, functionHintOnInput=False, autoCompleteOnInput=False):
        new(app, "$x = abs($y);\n", language="perl")
        app.select(1, 10)
        app.run("IDM_EDIT_FUNCCALLTIP")
        assert calltip_active(app)
        assert app.invoke("editor", "apiCallTipState")["overload"] == 0
        app.run("IDM_EDIT_FUNCCALLTIP_NEXT")
        assert app.invoke("editor", "apiCallTipState")["overload"] == 1
        app.run("IDM_EDIT_FUNCCALLTIP_PREVIOUS")
        assert app.invoke("editor", "apiCallTipState")["overload"] == 0
        calltip_cancel(app)
        new(app, "x = abs(1);\n", language="c")
        app.select(1, 10)
        app.run("IDM_EDIT_FUNCCALLTIP")
        app.run("IDM_EDIT_FUNCCALLTIP_NEXT")
        assert calltip_active(app)
        assert app.invoke("editor", "apiCallTipState")["overload"] == 0
        calltip_cancel(app)


@pytest.mark.case("EDIT-065")
def test_edit_065_path_completion_lists_folder_entries(app, tmp):
    """EDIT-065: Path Completion lists folder entries"""
    write(tmp / "pc" / "target.txt", "x")
    (tmp / "pc" / "my dir" / "Sub").mkdir(parents=True)
    with prefs(app, autoCompleteOnInput=False):
        new(app, f'cat "{tmp}/pc/my dir/su')
        app.keys("cmd+down")
        app.run("IDM_EDIT_AUTOCOMPLETE_PATH")
        assert ac_active(app)
        assert ac_current(app) == f"{tmp}/pc/my dir/Sub/"
        app.keys("return")
        assert app.text() == f'cat "{tmp}/pc/my dir/Sub/'
        new(app, f"{tmp}/pc/tar")
        app.keys("cmd+down", "ctrl+alt+space")
        assert ac_active(app)
        assert ac_current(app) == f"{tmp}/pc/target.txt"
        ac_cancel(app)
        new(app, "no path here")
        app.keys("cmd+down")
        app.run("IDM_EDIT_AUTOCOMPLETE_PATH")
        assert not ac_active(app)
        assert app.text() == "no path here"


# ---- EOL conversion ---------------------------------------------------------------------------------

@pytest.mark.case("EDIT-066")
def test_edit_066_eol_conversion_rewrites_every_line_ending(app, tmp):
    """EDIT-066: EOL Conversion rewrites every line ending"""
    p = write(tmp / "mixed.txt", b"a\nb\r\nc\rd")
    app.open(p)
    app.run("IDM_FORMAT_TODOS")
    assert app.text() == "a\r\nb\r\nc\r\nd" and app.doc()["eol"] == "CRLF"
    app.run("IDM_FORMAT_TOMAC")
    assert app.text() == "a\rb\rc\rd" and app.doc()["eol"] == "CR"
    app.run("IDM_FORMAT_TOUNIX")
    assert app.text() == "a\nb\nc\nd" and app.doc()["eol"] == "LF"
    app.keys("cmd+z")
    assert app.text() == "a\rb\rc\rd"
    app.run("IDM_EDIT_REDO")
    assert app.text() == "a\nb\nc\nd"
    app.run("IDM_FILE_SAVE")
    app.wait(lambda: p.read_bytes() == b"a\nb\nc\nd")


@pytest.mark.case("EDIT-067")
def test_edit_067_the_current_format_s_conversion_is_disabled(app):
    """EDIT-067: The current format's conversion is disabled"""
    ids = ["IDM_FORMAT_TODOS", "IDM_FORMAT_TOUNIX", "IDM_FORMAT_TOMAC"]
    new(app, "a\nb\n")
    m = app.menu(*ids)
    assert [m[i]["enabled"] for i in ids] == [True, False, True]
    app.run("IDM_FORMAT_TODOS")
    m = app.menu(*ids)
    assert [m[i]["enabled"] for i in ids] == [False, True, True]


@pytest.mark.case("EDIT-068")
def test_edit_068_new_typing_after_a_conversion_uses_the_new_eol(app):
    """EDIT-068: New typing after a conversion uses the new EOL"""
    new(app, "a")
    app.run("IDM_FORMAT_TODOS")
    app.keys("cmd+down", "return")
    app.type("b")
    assert app.text() == "a\r\nb"


# ---- blank operations -----------------------------------------------------------------------------

@pytest.mark.case("EDIT-069")
def test_edit_069_trim_trailing_trim_leading_and_trim_both(app):
    """EDIT-069: Trim Trailing, Trim Leading and Trim Both"""
    src = "  a  \n\tb\t\n c \n"
    for cmd, want in [("IDM_EDIT_TRIMTRAILING", "  a\n\tb\n c \n"),
                      ("IDM_EDIT_TRIMLINEHEAD", "a  \nb\t\n c \n"),
                      ("IDM_EDIT_TRIM_BOTH", "a\nb\n c \n")]:
        new(app, src)
        app.run(cmd)
        assert app.text() == want, cmd


@pytest.mark.case("EDIT-070")
def test_edit_070_blank_operations_limited_to_the_selected_lines(app):
    """EDIT-070: Blank operations limited to the selected lines"""
    new(app, "a  \nb  \nc  \n")
    app.select(2, 1, 2, 2)
    app.run("IDM_EDIT_TRIMTRAILING")
    assert app.text() == "a  \nb\nc  \n"
    new(app, "  a\n  b\n")
    app.select(2, 1, 2, 4)
    app.run("IDM_EDIT_TRIMLINEHEAD")
    assert app.text() == "  a\nb\n"


@pytest.mark.case("EDIT-071")
def test_edit_071_eol_to_space_and_trim_both_and_eol_to_space(app):
    """EDIT-071: EOL to Space and Trim both and EOL to Space"""
    new(app, "a\nb\r\nc\n")
    app.run("IDM_EDIT_EOL2WS")
    assert app.text() == "a b c\n"
    new(app, "1\n2\n3\n4\n")
    app.select(2, 1, 3, 2)
    app.run("IDM_EDIT_EOL2WS")
    assert app.text() == "1\n2 3\n4\n"
    new(app, "  a  \n\tb\t\n  c\n")
    app.run("IDM_EDIT_TRIMALL")
    assert app.text() == "a b c\n"


@pytest.mark.case("EDIT-072")
def test_edit_072_tab_to_space_fills_to_the_next_tab_stop(app):
    """EDIT-072: TAB to Space fills to the next tab stop"""
    with prefs(app, tabWidth=4, useSpaces=False):
        for src, want in [("\tx\n", "    x\n"), ("a\tb\n", "a   b\n"), ("abcd\te\n", "abcd    e\n"),
                          ("ab\t\tc\n", "ab      c\n")]:
            new(app, src)
            app.run("IDM_EDIT_TAB2SW")
            assert app.text() == want, repr(src)


@pytest.mark.case("EDIT-073")
def test_edit_073_space_to_tab_all_and_leading(app):
    """EDIT-073: Space to TAB (All) and (Leading)"""
    src = "        a    b\nab  cd\n"
    with prefs(app, tabWidth=4, useSpaces=False):
        new(app, src)
        app.run("IDM_EDIT_SW2TAB_LEADING")
        assert app.text() == "\t\ta    b\nab  cd\n"
        new(app, src)
        app.run("IDM_EDIT_SW2TAB_ALL")
        # upstream wsTabConvert: the tab reaches column 12, one space more keeps "b" at column 13
        assert app.text() == "\t\ta\t b\nab\tcd\n"


@pytest.mark.case("EDIT-074")
def test_edit_074_blank_operations_are_one_undo_step_and_ignore_a_rectangle(app):
    """EDIT-074: Blank operations are one undo step and ignore a rectangle"""
    new(app, "  a  \n  b  \n")
    app.run("IDM_EDIT_TRIM_BOTH")
    assert app.text() == "a\nb\n"
    app.keys("cmd+z")
    assert app.text() == "  a  \n  b  \n"
    with prefs(app, tabWidth=4, useSpaces=False):
        new(app, "\ta\n\tb\n")
        column_rect(app, 1, 1, 2, 2)
        assert app.selection()["rectangular"]
        app.run("IDM_EDIT_TAB2SW")
        assert app.text() == "\ta\n\tb\n"


# ---- paste special ----------------------------------------------------------------------------------

@pytest.mark.case("EDIT-075")
def test_edit_075_paste_html_content_pastes_the_html_source(app):
    """EDIT-075: Paste HTML Content pastes the HTML source"""
    new(app, "<b>bold</b> text", language="html")
    select_all(app)
    app.run("Plugins|Export|Copy HTML to clipboard")
    assert "public.html" in app.clipboard_info()["types"]
    new(app)
    app.run("IDM_EDIT_PASTE_AS_HTML")
    t = app.text()
    assert t.startswith("<!DOCTYPE html>")
    assert "bold" in t
    assert pos(app) == len(t.encode())


@pytest.mark.case("EDIT-076")
def test_edit_076_paste_rtf_content_pastes_the_rtf_source(app):
    """EDIT-076: Paste RTF Content pastes the RTF source"""
    new(app, "rich")
    select_all(app)
    app.run("Plugins|Export|Copy RTF to clipboard")
    new(app)
    app.run("IDM_EDIT_PASTE_AS_RTF")
    t = app.text()
    assert t.startswith("{\\rtf1")
    assert "rich" in t


@pytest.mark.case("EDIT-077")
def test_edit_077_paste_html_rtf_with_plain_text_on_the_clipboard_does_nothing(app):
    """EDIT-077: Paste HTML/RTF with plain text on the clipboard does nothing"""
    app.clipboard(set="plain")
    new(app, "x")
    app.run("IDM_EDIT_PASTE_AS_HTML")
    app.run("IDM_EDIT_PASTE_AS_RTF")
    assert app.text() == "x"


@pytest.mark.case("EDIT-078")
def test_edit_078_copy_cut_and_paste_binary_content_round_trip_bytes(app):
    """EDIT-078: Copy, Cut and Paste Binary Content round-trip bytes"""
    new(app, "ab é")
    app.select(1, 1, 1, 3)
    app.run("IDM_EDIT_COPY_BINARY")
    assert app.clipboard() == "61 62"
    app.select(1, 4, 1, 5)
    app.run("IDM_EDIT_CUT_BINARY")
    assert app.clipboard() == "C3 A9"
    assert app.text() == "ab "
    app.keys("cmd+down")
    app.run("IDM_EDIT_PASTE_BINARY")
    assert app.text() == "ab é"
    app.clipboard(set="C3 A9 zz 41")
    new(app, "[]")
    app.keys("right")
    app.run("IDM_EDIT_PASTE_BINARY")
    assert app.text() == "[éA]"


@pytest.mark.case("EDIT-079")
def test_edit_079_binary_copy_keeps_a_nul_byte(app, tmp):
    """EDIT-079: Binary copy keeps a NUL byte"""
    app.open(write(tmp / "nul.bin", b"a\x00b"))
    select_all(app)
    app.run("IDM_EDIT_COPY_BINARY")
    assert app.clipboard() == "61 00 62"
    new(app)
    app.run("IDM_EDIT_PASTE_BINARY")
    out = tmp / "out.bin"
    app.answers(panels=[str(out)])
    app.run("IDM_FILE_SAVEAS")
    app.wait(lambda: out.exists())
    assert out.read_bytes() == b"a\x00b"


@pytest.mark.case("EDIT-080")
def test_edit_080_binary_commands_with_nothing_selected(app):
    """EDIT-080: Binary commands with nothing selected"""
    app.clipboard(set="keep")
    new(app, "abc")
    app.run("IDM_EDIT_COPY_BINARY")
    app.run("IDM_EDIT_CUT_BINARY")
    assert app.clipboard() == "keep"
    assert app.text() == "abc"
    app.clipboard(set="")
    app.run("IDM_EDIT_PASTE_BINARY", expect_ran=False)
    assert app.text() == "abc"


# ---- on selection ------------------------------------------------------------------------------------

def select_line(app, n):
    app.select(n, 1, n)


@pytest.mark.case("EDIT-081")
def test_edit_081_open_file_opens_the_file_the_selection_names(app, tmp):
    """EDIT-081: Open File opens the file the selection names"""
    target = write(tmp / "target.txt", "target\n")
    homefile = write(app.home / "home.txt", "home\n")
    holder = write(tmp / "holder.txt", f"{target}\ntarget.txt\n\"{target}\"\n~/home.txt\n")
    app.open(holder)
    for line, want in [(1, target), (2, target), (3, target), (4, homefile)]:
        goto_doc(app, next(d["index"] for d in app.docs() if d.get("path") and app.same_path(d["path"], holder)))
        select_line(app, line)
        app.run("IDM_EDIT_OPENSELECTEDFILETOEDIT")
        cur = app.doc()
        assert cur.get("path") and app.same_path(cur["path"], want), (line, cur.get("path"))
        app.call("close_document", discard_changes=True)


@pytest.mark.case("EDIT-082")
def test_edit_082_open_file_on_a_word_under_the_caret_and_on_a_name_that_does(app, tmp):
    """EDIT-082: Open File on a word under the caret and on a name that does not exist"""
    notes = write(tmp / "notes.md", "n\n")
    holder = write(tmp / "holder.txt", "see notes.md and missing.txt")
    app.open(holder)
    app.select(1, 5, 1, 13)
    app.run("IDM_EDIT_OPENSELECTEDFILETOEDIT")
    assert app.same_path(app.doc()["path"], notes)
    app.call("close_document", discard_changes=True)
    goto_doc(app, next(d["index"] for d in app.docs() if d.get("path") and app.same_path(d["path"], holder)))
    count = len(app.docs())
    app.select(1, 18, 1, 29)
    app.run("IDM_EDIT_OPENSELECTEDFILETOEDIT")
    app.select(1, 2)
    app.run("IDM_EDIT_OPENSELECTEDFILETOEDIT")
    assert len(app.docs()) == count
    assert app.same_path(app.doc()["path"], holder)
    assert app.modal_log() == []


@pytest.mark.case("EDIT-083")
def test_edit_083_open_containing_folder_is_reachable_and_refuses_a_missing_fi(app):
    """EDIT-083: Open Containing Folder is reachable and refuses a missing file"""
    new(app, "no/such/file.txt")
    select_all(app)
    count = len(app.docs())
    assert invoke_menu(app, "Edit|On Selection|Open Containing Folder in Finder")["ran"]
    assert not log_kinds(app.modal_log(), "reveal")
    r = app.run("IDM_EDIT_OPENSELECTEDFILEFOLDERINEXPLORER", expect_ran=False)
    assert r.get("command") == 42074
    assert len(app.docs()) == count
    assert not log_kinds(app.modal_log(), "reveal")


@pytest.mark.case("EDIT-084")
def test_edit_084_redact_selection_replaces_each_character_with_a_block(app):
    """EDIT-084: Redact Selection replaces each character with a block"""
    new(app, "secret é👍 ok")
    app.keys(*["shift+right"] * 9)
    assert app.selection()["text"] == "secret é👍"
    app.run("IDM_EDIT_REDACT_SELECTION")
    assert app.text() == "█" * 9 + " ok"
    app.keys("cmd+z")
    assert app.text() == "secret é👍 ok"
    new(app, "ab x ab")
    app.keys("shift+right", "shift+right")
    app.run("IDM_EDIT_MULTISELECTALL")
    app.run("IDM_EDIT_REDACT_SELECTION")
    assert app.text() == "██ x ██"
    new(app, "plain")
    app.run("IDM_EDIT_REDACT_SELECTION")
    assert app.text() == "plain"


@pytest.mark.case("EDIT-085")
def test_edit_085_redact_with_shift_uses_bullets(app):
    """EDIT-085: Redact with Shift uses bullets"""
    new(app, "pin 1234")
    app.select(1, 5, 1, 9)
    assert invoke_menu(app, "Edit|On Selection|Redact Selection", modifiers=["shift"])["ran"]
    assert app.text() == "pin ●●●●"


@pytest.mark.case("EDIT-086")
def test_edit_086_search_on_internet_with_nothing_to_search_does_nothing(app):
    """EDIT-086: Search on Internet with nothing to search does nothing"""
    app.modal_log()
    count = len(app.docs())
    new(app)
    app.run("IDM_EDIT_SEARCHONINTERNET")
    new(app, "   ")
    app.select(1, 2)
    app.run("IDM_EDIT_SEARCHONINTERNET")
    assert not log_kinds(app.modal_log(), "open_url")
    assert app.text() == "   "
    assert len(app.docs()) == count + 2
    new(app, "hello wörld")
    app.select(1, 7, 1, 12)
    app.run("IDM_EDIT_SEARCHONINTERNET")
    opened = log_kinds(app.modal_log(), "open_url")
    assert len(opened) == 1
    url = json.dumps(opened[0])
    assert "w%C3%B6rld" in url or "wörld" in url


@pytest.mark.case("EDIT-087")
def test_edit_087_change_search_engine_stores_a_custom_engine(app):
    """EDIT-087: Change Search Engine stores a custom engine"""
    url = "https://example.invalid/?q=$(CURRENT_WORD)"
    with prefs(app, searchEngine=1, searchEngineCustom=""):
        app.modal_log()
        app.answers(alerts=[{"button": 1, "field": url}])
        app.run("IDM_EDIT_CHANGESEARCHENGINE")
        log = app.modal_log()
        prompt = next(e for e in log if e.get("kind") == "alert")
        assert "$(CURRENT_WORD)" in (prompt.get("fields") or [""])[0]
        assert app.pref("searchEngine") == 4
        assert app.pref("searchEngineCustom") == url
        app.answers(alerts=[2])
        app.run("IDM_EDIT_CHANGESEARCHENGINE")
        assert app.pref("searchEngineCustom") == url
        assert app.pref("searchEngine") == 4


# ---- multi-select ------------------------------------------------------------------------------------

@pytest.mark.case("EDIT-088")
def test_edit_088_multi_select_all_with_each_matching_mode(app):
    """EDIT-088: Multi-select All with each matching mode"""
    for cmd, want in [("IDM_EDIT_MULTISELECTALL", [(0, 3), (4, 7), (8, 11)]),
                      ("IDM_EDIT_MULTISELECTALLMATCHCASE", [(4, 7), (8, 11)]),
                      ("IDM_EDIT_MULTISELECTALLWHOLEWORD", [(0, 3), (4, 7)]),
                      ("IDM_EDIT_MULTISELECTALLMATCHCASEWHOLEWORD", [(4, 7)])]:
        new(app, "Cat cat catalog\n")
        app.select(1, 5, 1, 8)
        app.run(cmd)
        assert sorted_ranges(app) == want, cmd


@pytest.mark.case("EDIT-089")
def test_edit_089_typing_over_a_multi_selection_edits_every_occurrence(app):
    """EDIT-089: Typing over a multi-selection edits every occurrence"""
    new(app, "foo Foo foo\n")
    app.select(1, 1, 1, 4)
    app.run("IDM_EDIT_MULTISELECTALLMATCHCASE")
    app.type("bar")
    assert app.text() == "bar Foo bar\n"
    # With several selections Scintilla makes each keystroke its own undo step (Editor::InsertCharacter
    # opens an UndoGroup, and EndUndoAction stops it coalescing with the next), so Notepad++ takes
    # the typed word back a letter at a time.
    app.keys("cmd+z")
    assert app.text() == "ba Foo ba\n"
    app.keys("cmd+z")
    app.keys("cmd+z")
    assert app.text() == "foo Foo foo\n"


@pytest.mark.case("EDIT-090")
def test_edit_090_multi_select_all_uses_the_word_under_the_caret(app):
    """EDIT-090: Multi-select All uses the word under the caret"""
    new(app, "one two one")
    app.select(1, 2)
    app.run("IDM_EDIT_MULTISELECTALLWHOLEWORD")
    assert sorted_ranges(app) == [(0, 3), (8, 11)]


@pytest.mark.case("EDIT-091")
def test_edit_091_multi_select_next_adds_the_next_occurrence_under_each_mode(app):
    """EDIT-091: Multi-select Next adds the next occurrence under each mode"""
    for cmd, want in [("IDM_EDIT_MULTISELECTNEXT", [(4, 7), (8, 11)]),
                      ("IDM_EDIT_MULTISELECTNEXTMATCHCASE", [(4, 7), (8, 11)]),
                      ("IDM_EDIT_MULTISELECTNEXTWHOLEWORD", [(0, 3), (4, 7)]),
                      ("IDM_EDIT_MULTISELECTNEXTMATCHCASEWHOLEWORD", [(4, 7)])]:
        new(app, "Cat cat catalog\n")
        app.select(1, 5, 1, 8)
        app.run(cmd)
        assert sorted_ranges(app) == want, cmd


@pytest.mark.case("EDIT-092")
def test_edit_092_undo_the_latest_added_multi_select_and_skip_current(app):
    """EDIT-092: Undo the Latest Added Multi-Select and Skip Current"""
    new(app, "foo foo foo\n")
    app.select(1, 1, 1, 4)
    app.run("IDM_EDIT_MULTISELECTNEXT")
    app.run("IDM_EDIT_MULTISELECTNEXT")
    assert sorted_ranges(app) == [(0, 3), (4, 7), (8, 11)]
    app.run("IDM_EDIT_MULTISELECTUNDO")
    assert sorted_ranges(app) == [(0, 3), (4, 7)]
    app.run("IDM_EDIT_MULTISELECTSSKIP")
    assert sorted_ranges(app) == [(0, 3), (8, 11)]


@pytest.mark.case("EDIT-093")
def test_edit_093_multi_select_commands_with_nothing_to_find(app):
    """EDIT-093: Multi-select commands with nothing to find"""
    new(app)
    app.run("IDM_EDIT_MULTISELECTALL")
    app.run("IDM_EDIT_MULTISELECTNEXT")
    assert app.sci(SCI_GETSELECTIONS) == 1 and app.text() == ""
    new(app, "foo bar")
    app.select(1, 1, 1, 4)
    app.run("IDM_EDIT_MULTISELECTNEXT")
    assert ranges(app) == [(0, 3)]
    app.run("IDM_EDIT_MULTISELECTUNDO")
    assert ranges(app) == [(0, 3)]
    assert app.text() == "foo bar"


# ---- column mode / editor ----------------------------------------------------------------------

@pytest.mark.case("EDIT-094")
def test_edit_094_column_mode_explains_column_selection(app):
    """EDIT-094: Column Mode… explains column selection"""
    new(app, "abc")
    app.modal_log()
    app.answers(alerts=[1])
    app.run("IDM_EDIT_COLUMNMODETIP")
    log = [e for e in app.modal_log() if e.get("kind") == "alert"]
    assert len(log) == 1 and log[0]["message"] == "Column mode"
    assert "Option" in log[0]["informative"] and "Begin/End Select in Column Mode" in log[0]["informative"]
    assert app.text() == "abc"


def column_editor(app, *fields, cancel_at=None):
    answers = [{"button": 1, "field": f} for f in fields]
    if cancel_at is not None:
        answers = answers[:cancel_at] + [2]
    app.answers(alerts=answers)
    app.run("IDM_EDIT_COLUMNMODE")


@pytest.mark.case("EDIT-095")
def test_edit_095_column_editor_inserts_text_into_every_row_of_a_zero_width_co(app):
    """EDIT-095: Column Editor inserts text into every row of a zero-width column"""
    new(app, "a\nb\nc\n")
    column_rect(app, 1, 1, 3, 1)
    app.modal_log()
    column_editor(app, "text", ">")
    msgs = [e["message"] for e in app.modal_log() if e.get("kind") == "alert"]
    assert msgs == ['Column Editor - "text" or "number"?', "Text to insert"]
    assert app.text() == ">a\n>b\n>c\n"
    app.keys("cmd+z")
    assert app.text() == "a\nb\nc\n"


@pytest.mark.case("EDIT-096")
def test_edit_096_column_editor_replaces_a_selected_block_and_pads_short_lines(app):
    """EDIT-096: Column Editor replaces a selected block and pads short lines"""
    new(app, "abcd\nab\nabcd\n")
    column_rect(app, 1, 3, 3, 5)
    column_editor(app, "text", "XY")
    assert app.text() == "abXY\nabXY\nabXY\n"


@pytest.mark.case("EDIT-097")
def test_edit_097_column_editor_with_no_selection_works_from_the_caret_line_to(app):
    """EDIT-097: Column Editor with no selection works from the caret line to the end"""
    new(app, "12345\n1\n12345")
    app.select(1, 4)
    column_editor(app, "text", "|")
    assert app.text() == "123|45\n1  |\n123|45"


@pytest.mark.case("EDIT-098")
def test_edit_098_column_editor_numbers_initial_increase_repeat_zeros_and_base(app):
    """EDIT-098: Column Editor numbers: initial, increase, repeat, zeros and base"""
    for answers, want in [(("9", "1", "1", "yes", "dec"), "09x\n10x\n11x\n12x"),
                          (("1", "1", "2", "no", "dec"), "1x\n1x\n2x\n2x"),
                          (("8", "2", "1", "no", "hex"), "8x\nAx\nCx\nEx"),
                          (("5", "1", "1", "yes", "bin"), "0101x\n0110x\n0111x\n1000x"),
                          (("7", "1", "1", "no", "oct"), "7x\n10x\n11x\n12x")]:
        new(app, "x\nx\nx\nx")
        column_rect(app, 1, 1, 4, 1)
        app.modal_log()
        column_editor(app, "number", *answers)
        assert len([e for e in app.modal_log() if e.get("kind") == "alert"]) == 6
        assert app.text() == want, answers


@pytest.mark.case("EDIT-099")
def test_edit_099_cancelling_the_column_editor_changes_nothing(app):
    """EDIT-099: Cancelling the Column Editor changes nothing"""
    for fields, cancel_at in [((), 0), (("text",), 1), (("number", "1"), 2)]:
        new(app, "a\nb\n")
        column_rect(app, 1, 1, 2, 1)
        column_editor(app, *fields, cancel_at=cancel_at)
        assert app.text() == "a\nb\n", fields


# ---- panels ---------------------------------------------------------------------------------------

CHAR_COLUMNS = ["Value", "Hex", "Character", "HTML Name", "HTML Decimal", "HTML Hexadecimal"]


def char_table(app):
    for c in app.ui()["controls"]:
        if c.get("columns") == CHAR_COLUMNS:
            return c
    return None


@pytest.mark.case("EDIT-100")
def test_edit_100_character_panel_shows_256_characters_and_inserts_one_on_doub(app):
    """EDIT-100: Character Panel shows 256 characters and inserts one on double click"""
    new(app)
    app.run("IDM_EDIT_CHAR_PANEL")
    try:
        t = app.wait(lambda: char_table(app))
        assert t["rows"] == 256
        cells = t["cells"]
        assert cells[10][2] == "LF"
        assert cells[38][3] == "&amp;"
        assert cells[128][2] == "€" and cells[128][5] == "&#x20ac;"
        assert cells[255][1] == "FF"
        # A double click inserts the text of the column clicked, the character itself only in the
        # Character column (AnsiCharPanel NM_DBLCLK: insertChar for column 2, the cell's text otherwise).
        for row in (65, 233):
            app.call("e2e_act", window="main", action="double_click", value=row, target={"path": t["path"]}, column=2)
        assert app.text() == "Aé"
    finally:
        if char_table(app):
            app.run("IDM_EDIT_CHAR_PANEL")


@pytest.mark.case("EDIT-101")
def test_edit_101_character_panel_toggles_and_inserts_html_forms_from_their_co(app):
    """EDIT-101: Character Panel toggles and inserts HTML forms from their columns"""
    new(app)
    app.run("IDM_EDIT_CHAR_PANEL")
    try:
        t = app.wait(lambda: char_table(app))
        app.act("main", "double_click", 233, path=t["path"], column=3)
        app.act("main", "double_click", 147, path=t["path"], column=4)
        assert app.text() == "&eacute;&#8220;"
        assert app.checked("IDM_EDIT_CHAR_PANEL")
    finally:
        if char_table(app):
            app.run("IDM_EDIT_CHAR_PANEL")
    app.wait(lambda: char_table(app) is None)
    assert not app.checked("IDM_EDIT_CHAR_PANEL")


def clip_table(app):
    for c in app.ui()["controls"]:
        if c.get("class") == "NSTableView" and c.get("columns") and c.get("rows", 0) >= 0 \
                and any("history" in (row[0] if row else "") for row in c.get("cells", [])):
            return c
    return None


@pytest.mark.case("EDIT-102")
def test_edit_102_clipboard_history_keeps_copies_and_pastes_an_earlier_one(app):
    """EDIT-102: Clipboard History keeps copies and pastes an earlier one"""
    app.run("IDM_EDIT_CLIPBOARDHISTORY_PANEL")
    try:
        new(app, "history one\nhistory two\n")
        app.select(1, 1, 1, 12)
        app.keys("cmd+c")
        app.select(2, 1, 2, 12)
        app.keys("cmd+c")
        t = app.wait(lambda: (lambda c: c if c and len(c["cells"]) >= 2 else None)(clip_table(app)))
        firsts = [row[0] for row in t["cells"]]
        assert firsts[:2] == ["history two", "history one"]
        new(app)
        app.act("main", "double_click", 1, path=t["path"])
        assert app.text() == "history one"
    finally:
        app.run("IDM_EDIT_CLIPBOARDHISTORY_PANEL")
    app.wait(lambda: clip_table(app) is None)


# ---- read-only -------------------------------------------------------------------------------------

@pytest.mark.case("EDIT-103")
def test_edit_103_read_only_on_current_document_blocks_editing_and_is_checked(app):
    """EDIT-103: Read-Only on Current Document blocks editing and is checked"""
    new(app, "ro\n")
    app.run("IDM_EDIT_TOGGLEREADONLY")
    try:
        app.type("zz")
        app.keys("return", "backspace")
        assert app.text() == "ro\n"
        assert app.doc()["read_only"] is True
        assert app.checked("IDM_EDIT_TOGGLEREADONLY")
    finally:
        app.run("IDM_EDIT_TOGGLEREADONLY")
    assert app.doc()["read_only"] is False
    assert not app.checked("IDM_EDIT_TOGGLEREADONLY")
    app.keys("cmd+up")
    app.type("x")
    assert app.text() == "xro\n"


READ_ONLY_CMDS = ["IDM_EDIT_UPPERCASE", "IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING", "IDM_EDIT_JOIN_LINES",
                  "IDM_EDIT_TRIMTRAILING", "IDM_EDIT_REMOVE_ANY_DUP_LINES", "IDM_EDIT_DUP_LINE", "IDM_EDIT_INS_TAB",
                  "IDM_EDIT_INSERT_DATETIME_SHORT", "IDM_EDIT_BLOCK_COMMENT", "IDM_FORMAT_TODOS",
                  "IDM_EDIT_REDACT_SELECTION", "IDM_EDIT_COLUMNMODE"]


@pytest.mark.case("EDIT-104")
def test_edit_104_commands_do_not_change_a_read_only_document(app):
    """EDIT-104: Commands do not change a read-only document"""
    src = "b  \na\na\n"
    new(app, src, language="cpp")
    app.run("IDM_EDIT_TOGGLEREADONLY")
    changed = []
    try:
        for cmd in READ_ONLY_CMDS:
            select_all(app)
            if cmd == "IDM_EDIT_COLUMNMODE":
                app.answers(alerts=[{"button": 1, "field": "text"}, {"button": 1, "field": "X"}])
            app.run(cmd, expect_ran=False)
            if app.text() != src or app.doc()["eol"] != "LF":
                changed.append(cmd)
                app.run("IDM_EDIT_TOGGLEREADONLY")
                app.set_text(src)
                app.run("IDM_FORMAT_TOUNIX")
                app.run("IDM_EDIT_TOGGLEREADONLY")
    finally:
        if app.doc()["read_only"]:
            app.run("IDM_EDIT_TOGGLEREADONLY")
    assert changed == []


@pytest.mark.case("EDIT-105")
def test_edit_105_read_only_for_all_documents_and_clear_read_only_for_all_docu(app):
    """EDIT-105: Read-Only for All Documents and Clear Read-Only for All Documents"""
    app.new("one")
    app.new("two")
    app.new("three")
    docs = app.docs()
    second = docs[-2]["index"]
    goto_doc(app, second)
    app.run("IDM_EDIT_SETREADONLYFORALLDOCS")
    try:
        docs = app.docs()
        assert all(d["read_only"] for d in docs)
        assert current_doc(app)["index"] == second
        for d in docs:
            goto_doc(app, d["index"])
            before = app.text()
            app.type("Z")
            assert app.text() == before
    finally:
        app.run("IDM_EDIT_CLEARREADONLYFORALLDOCS")
    assert not any(d["read_only"] for d in app.docs())


@pytest.mark.case("EDIT-106")
def test_edit_106_read_only_attribute_on_disk_toggles_the_file_s_write_permiss(app, tmp):
    """EDIT-106: Read-Only Attribute on disk toggles the file's write permission"""
    p = write(tmp / "perm.txt", "x\n")
    os.chmod(p, 0o644)
    app.open(p)
    try:
        app.run("IDM_EDIT_TOGGLESYSTEMREADONLY")
        assert stat.S_IMODE(os.stat(p).st_mode) & 0o222 == 0
        app.run("IDM_EDIT_TOGGLESYSTEMREADONLY")
        assert stat.S_IMODE(os.stat(p).st_mode) & 0o200
    finally:
        os.chmod(p, 0o644)
    new(app, "u")
    app.modal_log()
    app.run("IDM_EDIT_TOGGLESYSTEMREADONLY")
    assert app.modal_log() == []


@pytest.mark.case("EDIT-107")
def test_edit_107_read_only_state_survives_switching_tabs(app):
    """EDIT-107: Read-only state survives switching tabs"""
    app.new("A")
    a = app.docs()[-1]["index"]
    app.run("IDM_EDIT_TOGGLEREADONLY")
    try:
        app.new("B")
        app.keys("cmd+down")
        app.type("b")
        assert app.text() == "Bb"
        goto_doc(app, a)
        app.keys("cmd+down")
        app.type("a")
        assert app.text() == "A"
        assert app.doc()["read_only"] is True
    finally:
        goto_doc(app, a)
        app.run("IDM_EDIT_TOGGLEREADONLY")
