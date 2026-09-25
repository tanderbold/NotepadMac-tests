"""TYPING: end-to-end tests (plan: plan/TYPING.md)."""
import os

import pytest

from harness.sci import *  # noqa: F401,F403
from _util_edit import (prefs, caret, pos, anchor, ranges, sorted_ranges, indicator, ac_active, ac_list,
                        ac_cancel, calltip_active, calltip_cancel, indent, write)

SMART_HIGHLIGHT = 19   # smart highlighting's own indicator (was 12, shared with Mark style 5)

SCI_GETSELECTIONNCARETVIRTUALSPACE = 2581


def new(app, text="", language=None):
    app.new(text, language=language)
    app.keys("cmd+up")


def rc(app):
    """Caret as (line, column), 1-based."""
    c = app.selection()["caret"]
    return c["line"], c["column"]


# ---- plain typing ---------------------------------------------------------

@pytest.mark.case("TYPING-001")
def test_typing_001_typed_text_goes_in_at_the_caret(app):
    """TYPING-001: Typed text goes in at the caret"""
    new(app, "ac")
    app.keys("right")
    app.type("b")
    app.keys("cmd+down")
    app.type(" done")
    assert app.text() == "abc done"
    assert rc(app) == (1, 9)
    assert app.doc()["modified"] is True


@pytest.mark.case("TYPING-002")
def test_typing_002_typing_replaces_the_selection(app):
    """TYPING-002: Typing replaces the selection"""
    new(app, "hello world")
    app.select(1, 7, 1, 12)
    app.type("there")
    assert app.text() == "hello there"
    assert app.selection()["text"] == ""
    assert pos(app) == len("hello there")


@pytest.mark.case("TYPING-003")
def test_typing_003_return_inserts_the_document_s_line_ending(app, tmp):
    """TYPING-003: Return inserts the document's line ending"""
    p = write(tmp / "crlf.txt", b"a\r\nb\r\n")
    app.open(p)
    app.keys("cmd+up", "end", "return")
    app.type("x")
    assert app.text() == "a\r\nx\r\nb\r\n"
    new(app, "a\nb\n")
    app.keys("end", "return")
    app.type("x")
    assert app.text() == "a\nx\nb\n"
    new(app, "a\nb\n")
    app.run("IDM_FORMAT_TOMAC")
    app.keys("cmd+up", "end", "return")
    app.type("x")
    assert app.text() == "a\rx\rb\r"


@pytest.mark.case("TYPING-004")
def test_typing_004_backspace_and_delete_remove_whole_characters_and_join_lines(app):
    """TYPING-004: Backspace and Delete remove whole characters and join lines"""
    new(app, "aé👍")
    app.keys("cmd+down", "backspace")
    assert app.text() == "aé"
    app.keys("backspace")
    assert app.text() == "a"
    new(app, "a\nb")
    app.keys("forwarddelete")
    assert app.text() == "\nb"
    app.keys("end", "forwarddelete")
    assert app.text() == "b"
    new(app, "x\n")
    app.keys("cmd+down", "backspace")
    assert app.text() == "x"


@pytest.mark.case("TYPING-005")
def test_typing_005_consecutive_typing_is_undone_as_one_step(app):
    """TYPING-005: Consecutive typing is undone as one step"""
    new(app, "hello world")
    app.keys("cmd+down")
    app.type(" again")
    app.keys("cmd+z")
    assert app.text() == "hello world"
    # (Shift+Cmd+Z through e2e_keys arrives as an unshifted "z" and undoes; the menu command redoes)
    app.run("IDM_EDIT_REDO")
    assert app.text() == "hello world again"
    app.keys("cmd+up")
    app.type("b")
    app.keys("cmd+z")
    assert app.text() == "hello world again"


@pytest.mark.case("TYPING-006")
def test_typing_006_non_ascii_input_accents_cjk_emoji_and_combining_marks(app, tmp):
    """TYPING-006: Non-ASCII input: accents, CJK, emoji and combining marks"""
    s = "héllo 日本語 👍 e\u0301"
    new(app)
    app.type(s)
    assert app.text() == s
    assert app.doc()["bytes"] == len(s.encode("utf-8"))
    assert pos(app) == len(s.encode("utf-8"))
    out = tmp / "u.txt"
    app.answers(panels=[str(out)])
    app.run("IDM_FILE_SAVEAS")
    app.wait(lambda: out.exists() and out.read_bytes() == s.encode("utf-8"))


@pytest.mark.case("TYPING-007")
def test_typing_007_composing_text_with_an_input_method_marked_text(app):
    """TYPING-007: Composing text with an input method (marked text)"""
    new(app)
    app.call("e2e_keys", marked={"stages": ["に", "にほ"]})
    app.call("e2e_keys", marked={"stages": [], "commit": "日本"})
    assert app.text() == "日本"
    app.keys("cmd+z")
    assert app.text() == ""


@pytest.mark.case("TYPING-008")
def test_typing_008_typing_into_a_read_only_document_changes_nothing(app):
    """TYPING-008: Typing into a read-only document changes nothing"""
    new(app, "ro\n")
    app.run("IDM_EDIT_TOGGLEREADONLY")
    try:
        app.type("zz")
        app.keys("return", "backspace", "forwarddelete", "tab")
        assert app.text() == "ro\n"
        assert app.doc()["modified"] is False
    finally:
        app.run("IDM_EDIT_TOGGLEREADONLY")


# ---- auto-close ---------------------------------------------------------------

@pytest.mark.case("TYPING-009")
def test_typing_009_each_auto_insert_preference_closes_its_own_pair(app):
    """TYPING-009: Each auto-insert preference closes its own pair"""
    cases = [("autoInsertParenthesis", "(", "()"), ("autoInsertBracket", "[", "[]"),
             ("autoInsertBrace", "{", "{}"), ("autoInsertSingleQuote", "'", "''"),
             ("autoInsertDoubleQuote", '"', '""')]
    for pref, typed, result in cases:
        with prefs(app, **{pref: True}):
            new(app, language="cpp")
            app.type(typed)
            assert app.text() == result, pref
            assert rc(app) == (1, 2)
        with prefs(app, **{pref: False}):
            new(app, language="cpp")
            app.type(typed)
            assert app.text() == typed, pref


@pytest.mark.case("TYPING-010")
def test_typing_010_typing_the_closer_steps_over_the_one_put_in(app):
    """TYPING-010: Typing the closer steps over the one put in"""
    with prefs(app, autoInsertParenthesis=True):
        new(app, language="cpp")
        app.type("f(x)")
        assert app.text() == "f(x)"
        assert pos(app) == 4
        app.type("g(")
        assert app.text() == "f(x)g()"
        app.keys("left", "right")
        app.type(")")
        assert app.text() == "f(x)g()"
        assert pos(app) == 7


@pytest.mark.case("TYPING-011")
def test_typing_011_a_bracket_is_closed_only_before_a_blank_the_end_or_a_closer(app):
    """TYPING-011: A bracket is closed only before a blank, the end or a closer"""
    with prefs(app, autoInsertBracket=True, autoInsertParenthesis=True):
        new(app, "x", language="cpp")
        app.type("[")
        assert app.text() == "[x"
        new(app, "a )", language="cpp")
        app.keys("right", "right")
        app.type("(")
        assert app.text() == "a ())"


@pytest.mark.case("TYPING-012")
def test_typing_012_quotes_are_closed_between_blanks_and_after_an_opening_bracke(app):
    """TYPING-012: Quotes are closed between blanks and after an opening bracket only"""
    with prefs(app, autoInsertDoubleQuote=True):
        new(app, language="cpp")
        app.type('"')
        assert app.text() == '""'
        new(app, "ab", language="cpp")
        app.keys("cmd+down")
        app.type('"')
        assert app.text() == 'ab"'
        new(app, "f(", language="cpp")
        app.keys("cmd+down")
        app.type('"')
        assert app.text() == 'f(""'
        new(app, "x y", language="cpp")
        app.keys("right", "right")
        app.type('"')
        assert app.text() == 'x "y'


@pytest.mark.case("TYPING-013")
def test_typing_013_user_defined_matched_pairs_close_before_a_blank_only(app):
    """TYPING-013: User-defined matched pairs close before a blank only"""
    with prefs(app, userMatchedPairs=["<>", "*~"]):
        new(app)
        app.type("<")
        assert app.text() == "<>"
        assert pos(app) == 1
        new(app, "a ")
        app.keys("cmd+down")
        app.type("*")
        assert app.text() == "a *~"
        new(app, "x")
        app.type("<")
        assert app.text() == "<x"


@pytest.mark.case("TYPING-014")
def test_typing_014_html_and_xml_close_the_tag_just_opened(app):
    """TYPING-014: HTML and XML close the tag just opened"""
    with prefs(app, autoInsertCloseTag=True):
        new(app, language="html")
        app.type('<div class="a">')
        assert app.text() == '<div class="a"></div>'
        assert pos(app) == len('<div class="a">')
        new(app, language="html")
        app.type("<br>")
        assert app.text() == "<br>"
        new(app, language="html")
        app.type("<img/>")
        assert app.text() == "<img/>"
        new(app, language="xml")
        app.type("<item>")
        assert app.text() == "<item></item>"
        new(app)
        app.type("<div>")
        assert app.text() == "<div>"


@pytest.mark.case("TYPING-015")
def test_typing_015_return_between_braces_opens_an_indented_block(app):
    """TYPING-015: Return between braces opens an indented block"""
    with prefs(app, autoInsertBrace=True, autoIndentMode=2, useSpaces=False, tabWidth=4):
        new(app, language="cpp")
        app.type("int f() {")
        app.keys("return")
        assert app.text() == "int f() {\n\t\n}"
        assert rc(app)[0] == 2
        assert pos(app) == len("int f() {\n\t")


@pytest.mark.case("TYPING-016")
def test_typing_016_nothing_is_auto_closed_with_several_carets(app):
    """TYPING-016: Nothing is auto-closed with several carets"""
    with prefs(app, autoInsertParenthesis=True):
        new(app, "a\nb\n", language="cpp")
        app.sci(SCI_ADDSELECTION, 2, 2)
        assert app.sci(SCI_GETSELECTIONS) == 2
        app.type("(")
        assert app.text() == "(a\n(b\n"


# ---- auto-indent -------------------------------------------------------------------

@pytest.mark.case("TYPING-017")
def test_typing_017_basic_auto_indent_keeps_the_previous_line_s_indentation(app):
    """TYPING-017: Basic auto-indent keeps the previous line's indentation"""
    with prefs(app, autoIndentMode=1):
        new(app, "    x")
        app.keys("cmd+down", "return")
        app.type("y")
        assert indent(app, 2) == 4
        assert app.text().split("\n")[1].strip() == "y"
        app.keys("return", "return")
        app.type("z")
        assert indent(app, 4) == 4
        assert app.text().split("\n")[3].strip() == "z"


@pytest.mark.case("TYPING-018")
def test_typing_018_with_auto_indent_off_return_starts_at_column_1(app):
    """TYPING-018: With auto-indent off Return starts at column 1"""
    with prefs(app, autoIndentMode=0):
        new(app, "    x")
        app.keys("cmd+down", "return")
        assert app.text() == "    x\n"
        assert rc(app) == (2, 1)


@pytest.mark.case("TYPING-019")
def test_typing_019_advanced_auto_indent_for_c_like_languages(app):
    """TYPING-019: Advanced auto-indent for C-like languages"""
    with prefs(app, autoIndentMode=2, useSpaces=False, tabWidth=4):
        new(app, language="cpp")
        app.type("if (x)\ny();\n")
        assert app.text() == "if (x)\n\ty();\n"
        assert rc(app) == (3, 1)
        new(app, language="cpp")
        app.type("while (a) {\n")
        assert indent(app, 2) == 4
        app.type("b;\n}")
        assert indent(app, 3) == 0
        assert app.text().endswith("\n}")
        new(app, "    {\n        x;\n        ", language="cpp")
        app.keys("cmd+down")
        app.type("}")
        assert indent(app, 3) == 4
        new(app, language="perl")
        app.type("if (x)\n")
        assert indent(app, 2) == 0


@pytest.mark.case("TYPING-020")
def test_typing_020_advanced_auto_indent_for_python(app):
    """TYPING-020: Advanced auto-indent for Python"""
    with prefs(app, autoIndentMode=2, useSpaces=False, tabWidth=4):
        new(app, language="python")
        app.type("def f(a):  # note\n")
        assert indent(app, 2) == 4
        new(app, language="python")
        app.type("s = 'a:'\n")
        assert indent(app, 2) == 0
        new(app, language="python")
        app.type("if x:\n")
        app.type("y = 1\n")
        assert indent(app, 3) == 4


# ---- completion ---------------------------------------------------------------------

@pytest.mark.case("TYPING-021")
def test_typing_021_word_completion_pops_up_while_typing_and_tab_or_return_accep(app):
    """TYPING-021: Word completion pops up while typing and Tab or Return accepts"""
    with prefs(app, autoCompleteOnInput=True, autoCompleteSource=2, autoCompleteThreshold=1):
        for key in ("tab", "return"):
            new(app, "alphabet alpine\n")
            app.keys("cmd+down")
            app.type("alph")
            assert ac_active(app)
            app.keys(key)
            assert app.text() == "alphabet alpine\nalphabet", key
            assert not ac_active(app)


@pytest.mark.case("TYPING-022")
def test_typing_022_escape_closes_the_list_and_keeps_what_was_typed(app):
    """TYPING-022: Escape closes the list and keeps what was typed"""
    with prefs(app, autoCompleteOnInput=True, autoCompleteThreshold=1):
        new(app, "alphabet\n")
        app.keys("cmd+down")
        app.type("alp")
        assert ac_active(app)
        app.keys("escape")
        assert not ac_active(app)
        assert app.text() == "alphabet\nalp"


@pytest.mark.case("TYPING-023")
def test_typing_023_the_completion_threshold(app):
    """TYPING-023: The completion threshold"""
    with prefs(app, autoCompleteOnInput=True, autoCompleteThreshold=3):
        new(app, "alphabet\n")
        app.keys("cmd+down")
        app.type("al")
        assert not ac_active(app)
        app.type("p")
        assert ac_active(app)
        ac_cancel(app)


@pytest.mark.case("TYPING-024")
def test_typing_024_completion_sources_words_functions_both(app):
    """TYPING-024: Completion sources: words, functions, both"""
    for source, has_return, has_retrieval in [(0, True, False), (1, False, True), (2, True, True)]:
        with prefs(app, autoCompleteOnInput=True, autoCompleteThreshold=1, autoCompleteSource=source,
                   autoCompleteBriefList=False):
            new(app, "retrieval\n", language="cpp")
            app.keys("cmd+down")
            app.type("ret")
            assert ac_active(app), source
            lst = ac_list(app)
            assert ("return" in lst) == has_return, (source, lst[:20])
            assert ("retrieval" in lst) == has_retrieval, (source, lst[:20])
            ac_cancel(app)


@pytest.mark.case("TYPING-025")
def test_typing_025_numbers_are_not_offered_when_ignore_numbers_is_on(app):
    """TYPING-025: Numbers are not offered when "ignore numbers" is on"""
    with prefs(app, autoCompleteOnInput=True, autoCompleteThreshold=1, autoCompleteSource=1,
               autoCompleteIgnoreNumbers=True):
        new(app, "12345 12abc\n")
        app.keys("cmd+down")
        app.type("12")
        assert ac_list(app) == ["12abc"]
        ac_cancel(app)
    with prefs(app, autoCompleteOnInput=True, autoCompleteThreshold=1, autoCompleteSource=1,
               autoCompleteIgnoreNumbers=False):
        new(app, "12345 12abc\n")
        app.keys("cmd+down")
        app.type("12")
        assert sorted(ac_list(app)) == ["12345", "12abc"]
        ac_cancel(app)


@pytest.mark.case("TYPING-026")
def test_typing_026_automatic_completion_is_off_when_its_preference_is_off(app):
    """TYPING-026: Automatic completion is off when its preference is off"""
    with prefs(app, autoCompleteOnInput=False):
        new(app, "alphabet\n")
        app.keys("cmd+down")
        app.type("alp")
        assert not ac_active(app)
        app.keys("cmd+return")
        assert app.text() == "alphabet\nalphabet"


@pytest.mark.case("TYPING-027")
def test_typing_027_the_parameter_hint_follows_the_typing(app):
    """TYPING-027: The parameter hint follows the typing"""
    with prefs(app, functionHintOnInput=True, autoCompleteOnInput=False):
        new(app, "f = ", language="c")
        app.keys("cmd+down")
        app.type("fopen(")
        assert calltip_active(app)
        st = app.invoke("editor", "apiCallTipState")
        assert st["name"] == "fopen" and st["param"] == 0
        app.type("name, ")
        st = app.invoke("editor", "apiCallTipState")
        assert st["param"] == 1
        app.type('"r")')
        assert not calltip_active(app)


@pytest.mark.case("TYPING-028")
def test_typing_028_completion_shortcuts_work_from_the_keyboard(app, tmp):
    """TYPING-028: Completion shortcuts work from the keyboard"""
    with prefs(app, autoCompleteOnInput=False, functionHintOnInput=False):
        new(app, "int x = pri", language="c")
        app.keys("cmd+down", "ctrl+space")
        assert ac_active(app)
        ac_cancel(app)
        new(app, "alpha alpine\nal")
        app.keys("cmd+down", "cmd+return")
        assert ac_active(app)
        ac_cancel(app)
        # Ctrl+Shift+Space: e2e_keys sends shifted chords with unshifted characters, which the
        # menu does not match; the item's key is checked and the command run instead.
        assert app.menu_item("IDM_EDIT_FUNCCALLTIP")["key"] == "ctrl+shift+ "
        new(app, "x = abs()", language="c")
        app.keys("cmd+down", "left")
        app.run("IDM_EDIT_FUNCCALLTIP")
        assert calltip_active(app)
        calltip_cancel(app)
        write(tmp / "pc" / "f.txt", "x")
        new(app, f"{tmp}/pc/")
        app.keys("cmd+down", "ctrl+alt+space")
        assert ac_active(app)
        ac_cancel(app)


# ---- highlighting ----------------------------------------------------------------------

@pytest.mark.case("TYPING-029")
def test_typing_029_smart_highlighting_marks_the_other_whole_word_occurrences(app):
    """TYPING-029: Smart highlighting marks the other whole-word occurrences"""
    with prefs(app, smartHighlightEnabled=True, smartHighlightMatchCase=False, smartHighlightWholeWord=True,
               smartHighlightUseFindSettings=False):
        new(app, "foo bar foo foobar Foo\n")
        app.keys("shift+right", "shift+right", "shift+right")
        want = "1110000011100000000111" + "0"
        app.wait(lambda: indicator(app, SMART_HIGHLIGHT) == want)
        app.keys("right")
        app.wait(lambda: "1" not in indicator(app, SMART_HIGHLIGHT))


@pytest.mark.case("TYPING-030")
def test_typing_030_smart_highlighting_options(app):
    """TYPING-030: Smart highlighting options"""
    def mark(text):
        new(app, text)
        app.keys("shift+right", "shift+right", "shift+right")
        app.idle(0.2)
        return indicator(app, SMART_HIGHLIGHT)

    base = dict(smartHighlightEnabled=True, smartHighlightMatchCase=False, smartHighlightWholeWord=True,
                smartHighlightUseFindSettings=False)
    with prefs(app, **dict(base, smartHighlightMatchCase=True)):
        assert mark("foo Foo foo") == "11100000111"
    with prefs(app, **dict(base, smartHighlightWholeWord=False)):
        assert mark("foo foobar") == "1110111000"
    with prefs(app, **dict(base, smartHighlightEnabled=False)):
        assert "1" not in mark("foo x foo")
    with prefs(app, **dict(base, smartHighlightUseFindSettings=True, findMatchCase=True)):
        assert mark("foo Foo") == "1110000"


@pytest.mark.case("TYPING-031")
def test_typing_031_braces_are_highlighted_when_the_caret_is_next_to_one(app):
    """TYPING-031: Braces are highlighted when the caret is next to one"""
    def braces():
        # what the view was last told to show: (the two positions, sorted), style
        a, b, style = app.call("e2e_sci", braces=True)["braces"]
        return tuple(sorted((a, b))), style

    with prefs(app, braceMatchEnabled=True):
        new(app, "f(a[1])", language="cpp")
        caret(app, 1, 3)        # right after "(": it and ")" at 1:7
        app.wait(lambda: braces() == ((1, 6), STYLE_BRACELIGHT))
        caret(app, 1, 6)        # before "]": it and "["
        app.wait(lambda: braces() == ((3, 5), STYLE_BRACELIGHT))
        new(app, "g(x", language="cpp")
        caret(app, 1, 3)        # after an unmatched "("
        app.wait(lambda: braces() == ((-1, 1), STYLE_BRACEBAD))
    with prefs(app, braceMatchEnabled=False):
        new(app, "f(a[1])", language="cpp")
        caret(app, 1, 3)
        app.wait(lambda: braces()[0] == (-1, -1))


@pytest.mark.case("TYPING-032")
def test_typing_032_matching_html_tags_are_highlighted(app):
    """TYPING-032: Matching HTML tags are highlighted"""
    with prefs(app, highlightMatchingTags=True, highlightTagAttributes=True):
        new(app, "<div><span>x</span></div>", language="html")
        caret(app, 1, 8)
        # both span tags (opening and closing) are marked, the div tags are not
        app.wait(lambda: indicator(app, 15) == "0000011111101111111000000")
        new(app, "<a href='x'>t</a>", language="html")
        caret(app, 1, 2)
        app.wait(lambda: "1" in indicator(app, 16))
        attr = indicator(app, 16)
        assert app.text()[attr.index("1"):attr.rindex("1") + 1].strip() == "href='x'"
    with prefs(app, highlightMatchingTags=False):
        new(app, "<div><span>x</span></div>", language="html")
        caret(app, 1, 8)
        app.idle(0.3)
        assert "1" not in indicator(app, 15)
        assert "1" not in indicator(app, 16)


# ---- multi-caret / column ------------------------------------------------------------------

@pytest.mark.case("TYPING-033")
def test_typing_033_typing_and_deleting_at_several_carets(app):
    """TYPING-033: Typing and deleting at several carets"""
    new(app, "one\ntwo\nthree\n")
    app.sci(SCI_ADDSELECTION, 4, 4)
    app.type("-")
    assert app.text() == "-one\n-two\nthree\n"
    app.keys("backspace")
    assert app.text() == "one\ntwo\nthree\n"
    app.type("+")
    assert app.text() == "+one\n+two\nthree\n"
    app.keys("escape")
    assert app.sci(SCI_GETSELECTIONS) == 1


@pytest.mark.case("TYPING-034")
def test_typing_034_multi_editing_preference(app):
    """TYPING-034: Multi-editing preference"""
    with prefs(app, multiEditing=False):
        new(app, "x")
        assert app.sci(SCI_GETMULTIPLESELECTION) == 0
    with prefs(app, multiEditing=True):
        assert app.sci(SCI_GETMULTIPLESELECTION) == 1


@pytest.mark.case("TYPING-035")
def test_typing_035_alt_shift_arrows_make_a_rectangular_selection_and_typing_fil(app):
    """TYPING-035: Alt+Shift+arrows make a rectangular selection and typing fills every row"""
    new(app, "abcd\nabcd\nabcd\n")
    caret(app, 1, 2)
    app.keys("alt+shift+down", "alt+shift+down", "alt+shift+right", "alt+shift+right")
    assert app.selection()["rectangular"]
    assert sorted_ranges(app) == [(1, 3), (6, 8), (11, 13)]
    app.type("Z")
    assert app.text() == "aZd\naZd\naZd\n"
    assert app.sci(SCI_GETSELECTIONS) == 3


@pytest.mark.case("TYPING-036")
def test_typing_036_typing_into_a_zero_width_column_inserts_on_every_line(app):
    """TYPING-036: Typing into a zero-width column inserts on every line"""
    new(app, "ab\ncd\nef\n")
    caret(app, 1, 2)
    app.keys("alt+shift+down", "alt+shift+down")
    app.type("|")
    assert app.text() == "a|b\nc|d\ne|f\n"
    app.keys("backspace")
    assert app.text() == "ab\ncd\nef\n"


@pytest.mark.case("TYPING-037")
def test_typing_037_the_caret_column_is_kept_when_moving_vertically_after_go_to(app):
    """TYPING-037: The caret column is kept when moving vertically after go_to"""
    new(app, "abcd\nabcd\nabcd\n")
    app.keys("cmd+down")
    app.select(1, 2)
    app.keys("down")
    assert pos(app) == 6
    app.select(1, 2)
    app.keys("alt+shift+down")
    assert sorted_ranges(app) == [(1, 1), (6, 6)]


@pytest.mark.case("TYPING-038")
def test_typing_038_virtual_space(app):
    """TYPING-038: Virtual space"""
    with prefs(app, virtualSpace=True):
        new(app, "ab\nabcdef\n")
        app.keys("end", "right", "right")
        assert app.sci(SCI_GETSELECTIONNCARETVIRTUALSPACE, 0) == 2
        app.type("Q")
        assert app.text() == "ab  Q\nabcdef\n"
    with prefs(app, virtualSpace=False):
        new(app, "ab\nabcdef\n")
        app.keys("end", "right")
        assert rc(app) == (2, 1)


@pytest.mark.case("TYPING-039")
def test_typing_039_a_rectangle_reaches_past_short_lines_even_without_virtual_sp(app):
    """TYPING-039: A rectangle reaches past short lines even without virtual space"""
    with prefs(app, virtualSpace=False):
        new(app, "abcdef\nab\nabcdef\n")
        caret(app, 1, 5)
        app.keys("alt+shift+down", "alt+shift+down")
        app.type("X")
        assert app.text() == "abcdXef\nab  X\nabcdXef\n"


# ---- indentation keys -------------------------------------------------------------------------

@pytest.mark.case("TYPING-040")
def test_typing_040_tab_inserts_indentation_according_to_the_settings(app):
    """TYPING-040: Tab inserts indentation according to the settings"""
    with prefs(app, useSpaces=False, tabWidth=4):
        new(app, "ab")
        app.keys("end", "tab")
        assert app.text() == "ab\t"
    with prefs(app, useSpaces=True, tabWidth=4):
        new(app, "ab")
        app.keys("end", "tab")
        assert app.text() == "ab  "
        new(app, "")
        app.keys("tab")
        assert app.text() == "    "


@pytest.mark.case("TYPING-041")
def test_typing_041_tab_and_shift_tab_on_a_multi_line_selection_indent_the_lines(app):
    """TYPING-041: Tab and Shift+Tab on a multi-line selection indent the lines"""
    with prefs(app, useSpaces=False, tabWidth=4):
        new(app, "a\nb\nc\n")
        app.select(1, 1, 3, 1)
        app.keys("tab")
        assert app.text() == "\ta\n\tb\nc\n"
        app.keys("shift+tab")
        assert app.text() == "a\nb\nc\n"
        new(app, "    x")
        caret(app, 1, 5)
        app.keys("shift+tab")
        assert app.text() == "x"


@pytest.mark.case("TYPING-042")
def test_typing_042_backspace_unindents_when_that_is_on(app):
    """TYPING-042: Backspace unindents when that is on"""
    with prefs(app, backspaceUnindents=True, useSpaces=False, tabWidth=4):
        new(app, "        x")
        caret(app, 1, 9)
        app.keys("backspace")
        assert indent(app, 1) == 4
        assert app.text().endswith("x")
    with prefs(app, backspaceUnindents=False, useSpaces=False, tabWidth=4):
        new(app, "        x")
        caret(app, 1, 9)
        app.keys("backspace")
        assert indent(app, 1) == 7


# ---- movement ----------------------------------------------------------------------------------

@pytest.mark.case("TYPING-043")
def test_typing_043_home_goes_to_the_first_non_blank_then_to_column_1_end_to_the(app):
    """TYPING-043: Home goes to the first non-blank, then to column 1; End to the line end"""
    new(app, "    indented line\nsecond")
    caret(app, 1, 10)
    app.keys("home")
    assert rc(app) == (1, 5)
    app.keys("home")
    assert rc(app) == (1, 1)
    app.keys("end")
    assert rc(app) == (1, 18)


@pytest.mark.case("TYPING-044")
def test_typing_044_cmd_and_alt_arrows_move_by_line_document_and_word(app):
    """TYPING-044: Cmd and Alt arrows move by line, document and word"""
    new(app, "    ab cd\nef")
    caret(app, 1, 8)
    app.keys("cmd+left")
    assert rc(app) == (1, 5)
    app.keys("cmd+right")
    assert rc(app) == (1, 10)
    app.keys("alt+left")
    assert rc(app) == (1, 8)
    app.keys("alt+right")
    assert rc(app) == (1, 10)
    app.keys("cmd+up")
    assert rc(app) == (1, 1)
    app.keys("cmd+down")
    assert rc(app) == (2, 3)


@pytest.mark.case("TYPING-045")
def test_typing_045_shift_with_the_movement_keys_extends_the_selection(app):
    """TYPING-045: Shift with the movement keys extends the selection"""
    new(app, "hello world\nnext")
    app.keys(*["shift+right"] * 5)
    assert app.selection()["text"] == "hello"
    app.keys("shift+cmd+right")
    assert app.selection()["text"] == "hello world"
    app.keys("shift+down")
    assert app.selection()["text"] == "hello world\nnext"
    app.keys("shift+cmd+up")
    assert app.selection()["text"] == ""
    assert pos(app) == 0


@pytest.mark.case("TYPING-046")
def test_typing_046_cmd_d_duplicates_the_line_and_keeps_the_caret_column(app):
    """TYPING-046: Cmd+D duplicates the line and keeps the caret column"""
    new(app, "abc\nxyz")
    caret(app, 1, 2)
    app.keys("cmd+d", "cmd+d")
    assert app.text() == "abc\nabc\nabc\nxyz"
    assert rc(app) == (1, 2)
    app.keys("cmd+z")
    assert app.text() == "abc\nabc\nxyz"


# ---- zoom and overtype ---------------------------------------------------------------------------

@pytest.mark.case("TYPING-047")
def test_typing_047_zoom_keys(app):
    """TYPING-047: Zoom keys"""
    new(app, "zoom text")
    try:
        assert app.sci(SCI_GETZOOM) == 0
        # Zoom In is Cmd++ (View > Zoom); Cmd+= is Edit > Calculate now (the user's choice, pending).
        app.keys("cmd++")
        assert app.sci(SCI_GETZOOM) == 1
        app.keys("cmd+-", "cmd+-")
        assert app.sci(SCI_GETZOOM) == -1
        app.keys("cmd+0")
        assert app.sci(SCI_GETZOOM) == 0
        app.keys(*["cmd++"] * 80)
        top = app.sci(SCI_GETZOOM)
        app.keys("cmd++")
        assert app.sci(SCI_GETZOOM) == top and 20 <= top <= 60
        assert app.text() == "zoom text"
    finally:
        app.keys("cmd+0")


@pytest.mark.case("TYPING-048")
def test_typing_048_overtype_replaces_characters_instead_of_inserting(app):
    """TYPING-048: Overtype replaces characters instead of inserting"""
    new(app, "abcdef\ncd")
    app.run("View|Toggle Insert/Overtype")
    try:
        assert app.sci(SCI_GETOVERTYPE) == 1
        app.type("XY")
        assert app.text() == "XYcdef\ncd"
        app.keys("end")
        app.type("Z")
        assert app.text() == "XYcdefZ\ncd"
    finally:
        app.run("View|Toggle Insert/Overtype")
    assert app.sci(SCI_GETOVERTYPE) == 0
    app.type("i")
    assert app.text() == "XYcdefZi\ncd"
