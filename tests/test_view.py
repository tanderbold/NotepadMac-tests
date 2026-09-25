"""VIEW: end-to-end tests (plan: plan/VIEW.md)."""
import os
import subprocess
import time

import re

import pytest

from harness.app import ToolError
from harness.sci import *  # noqa: F401,F403
from _util_view import (CPP2, FULLSCREEN_BIT, VIEW_COMMANDS, cleanup, click_tab, current, current_title,
                              depth, dock, expanded, fresh_doc, headers, level, main_window, nested_cpp, only,
                              parse_rect, prefs, representation, responsive, snap, status, summary, tab_attr,
                              tab_titles, toolbar_press, ui, view_frame, visible, write)


@pytest.fixture(autouse=True)
def _tidy(app_session):
    yield
    cleanup(app_session)


def _run_all(app, *cmds):
    for c in cmds:
        app.run(c)


def _clone_long(app, lines=400, width=0):
    body = "\n".join(f"line {i} " + ("w " * width) for i in range(lines)) + "\n"
    fresh_doc(app, body, language="normal")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    app.wait(lambda: app.get("editor", "secondaryViewVisible"), timeout=5)
    return body


def _toolbar_ids(app):
    return app.get("window", "toolbar.items.itemIdentifier")


# ---------------------------------------------------------------- menu structure

TOGGLES_RUN_TWICE = {"IDM_VIEW_ALWAYSONTOP", "IDM_VIEW_POSTIT", "IDM_VIEW_DISTRACTIONFREE", "IDM_VIEW_TAB_SPACE",
                     "IDM_VIEW_EOL", "IDM_VIEW_NPC", "IDM_VIEW_NPC_CCUNIEOL", "IDM_VIEW_ALL_CHARACTERS",
                     "IDM_VIEW_INDENT_GUIDE", "IDM_VIEW_WRAP_SYMBOL", "IDM_VIEW_WRAP", "IDM_VIEW_SYNSCROLLV",
                     "IDM_VIEW_ZOOM_SYNC", "IDM_VIEW_DOC_MAP", "IDM_VIEW_DOCLIST",
                     "IDM_VIEW_FUNC_LIST", "IDM_VIEW_FILEBROWSER", "IDM_VIEW_PROJECT_PANEL_1",
                     "IDM_VIEW_PROJECT_PANEL_2", "IDM_VIEW_PROJECT_PANEL_3", "IDM_VIEW_MONITORING"}


@pytest.mark.case("VIEW-001")
def test_view_001_every_view_command_is_in_the_menu_and_runs_by_its_id(app):
    fresh_doc(app, "abc")
    items = app.menu(*VIEW_COMMANDS)
    missing = [c for c in VIEW_COMMANDS if items.get(c) is None]
    disabled = [c for c in VIEW_COMMANDS if items.get(c) and not items[c]["enabled"]]
    refused = []
    for c in VIEW_COMMANDS:
        # Full screen animates; horizontal sync is exercised on its own (VIEW-072).
        if c in ("IDM_VIEW_FULLSCREENTOGGLE", "IDM_VIEW_SYNSCROLLH"):
            continue
        for _ in range(2 if c in TOGGLES_RUN_TWICE else 1):
            try:
                r = app.call("run_command", command=c)
                if not r.get("ran"):
                    refused.append(c)
            except ToolError as e:
                refused.append(f"{c}: {e}")
    cleanup(app)
    assert responsive(app)
    assert "abc" in [app.text(d["index"]) for d in app.docs()]
    assert not missing and not disabled and not refused, (missing, disabled, refused)


@pytest.mark.case("VIEW-002")
def test_view_002_view_shortcuts_are_the_documented_key_equivalents_and_work_f(app):
    keys = {c: app.menu_item(c).get("key") for c in
            ["IDM_VIEW_ZOOMIN", "IDM_VIEW_ZOOMOUT", "IDM_VIEW_ZOOMRESTORE", "IDM_VIEW_FOLDALL", "IDM_VIEW_UNFOLDALL",
             "IDM_VIEW_TAB_SPACE", "IDM_VIEW_FULLSCREENTOGGLE", "IDM_VIEW_TAB1"]}
    assert keys == {"IDM_VIEW_ZOOMIN": "cmd++", "IDM_VIEW_ZOOMOUT": "cmd+-", "IDM_VIEW_ZOOMRESTORE": "cmd+0",
                    "IDM_VIEW_FOLDALL": "alt+cmd+.", "IDM_VIEW_UNFOLDALL": "shift+cmd+.",
                    "IDM_VIEW_TAB_SPACE": "shift+cmd+i", "IDM_VIEW_FULLSCREENTOGGLE": "ctrl+cmd+f",
                    "IDM_VIEW_TAB1": "cmd+1"}
    fresh_doc(app, "int f() {\n  x;\n}\n", language="cpp")
    app.sci(SCI_COLOURISE, 0, -1)
    # Zoom In's key (cmd++) is checked above; "+" is shifted punctuation, which e2e_keys sends without
    # the shift (the WINDOW-008 gap), so it runs from its menu. cmd+= is Edit > Calculate.
    app.run("IDM_VIEW_ZOOMIN")
    assert app.sci(SCI_GETZOOM) == 1
    app.keys("cmd+-")
    assert app.sci(SCI_GETZOOM) == 0
    app.run("IDM_VIEW_ZOOMIN")
    app.keys("cmd+0")
    assert app.sci(SCI_GETZOOM) == 0
    app.keys("alt+cmd+.")
    assert not visible(app, 1)
    # Unfold All's key is checked above (shift+cmd+.); e2e_keys sends shifted punctuation without the
    # shift in charactersIgnoringModifiers (the WINDOW-008 gap), so the command runs from its menu here.
    app.call("e2e_menu_invoke", path="View|Unfold All")
    assert visible(app, 1)
    # shift+cmd+i (checked above) has the same gap for a letter with Shift (it arrives as cmd+i).
    app.run("IDM_VIEW_TAB_SPACE")
    assert app.sci(SCI_GETVIEWWS) == 1
    app.run("IDM_VIEW_TAB_SPACE")
    assert app.sci(SCI_GETVIEWWS) == 0


@pytest.mark.case("VIEW-003")
def test_view_003_the_view_menu_lists_each_command_once(app):
    tree = app.menu_tree("View", 2)
    dups = []

    def walk(items, where):
        seen = set()
        for i in items:
            # AppKit adds a hidden twin of the full-screen item (not made by the app); it is never shown.
            if i.get("separator") or i.get("hidden"):
                continue
            k = (i.get("title"), i.get("action"))
            if k in seen:
                dups.append((where, k))
            seen.add(k)
            if "items" in i:
                walk(i["items"], where + "|" + str(i.get("title")))
    walk(tree, "View")
    fs = [i for i in tree if i.get("title") == "Toggle Full Screen Mode" and not i.get("hidden")]
    symbols = next(i for i in tree if i.get("title") == "Show Symbol")["items"]
    names = [i["title"] for i in symbols if not i.get("separator")]
    assert not dups, dups
    assert len(fs) == 1 and fs[0]["action"] == "toggleFullScreenMode:"
    assert names == ["Show Space and Tab", "Show End of Line", "Show Non-Printing Characters",
                     "Show Control Characters & Unicode EOL", "Show All Characters", "Show Indent Guide",
                     "Show Wrap Symbol"]


TOGGLES = [pytest.param(c, id=c)
           for c in ["IDM_VIEW_ALWAYSONTOP", "IDM_VIEW_POSTIT", "IDM_VIEW_DISTRACTIONFREE", "IDM_VIEW_TAB_SPACE",
                     "IDM_VIEW_EOL", "IDM_VIEW_NPC", "IDM_VIEW_NPC_CCUNIEOL", "IDM_VIEW_ALL_CHARACTERS",
                     "IDM_VIEW_INDENT_GUIDE", "IDM_VIEW_WRAP_SYMBOL", "IDM_VIEW_WRAP", "IDM_VIEW_SYNSCROLLV",
                     "IDM_VIEW_SYNSCROLLH", "IDM_VIEW_ZOOM_SYNC", "IDM_VIEW_DOC_MAP", "IDM_VIEW_DOCLIST",
                     "IDM_VIEW_FUNC_LIST", "IDM_VIEW_FILEBROWSER", "IDM_VIEW_PROJECT_PANEL_1",
                     "IDM_VIEW_PROJECT_PANEL_2", "IDM_VIEW_PROJECT_PANEL_3", "IDM_VIEW_MONITORING", "RTL/LTR"]]


@pytest.mark.case("VIEW-004")
@pytest.mark.parametrize("command", TOGGLES)
def test_view_004_toggle_commands_carry_a_checkmark_that_follows_their_state(app, tmp, command):
    p = write(tmp, "m.txt", "a\tb\n")
    only(app, p)
    if command == "RTL/LTR":
        app.run("IDM_EDIT_RTL")
        after_rtl = (app.checked("IDM_EDIT_RTL"), app.checked("IDM_EDIT_LTR"))
        app.run("IDM_EDIT_LTR")
        after_ltr = (app.checked("IDM_EDIT_RTL"), app.checked("IDM_EDIT_LTR"))
        assert after_rtl == (True, False) and after_ltr == (False, True)
        return
    if command in ("IDM_VIEW_SYNSCROLLH",):
        pass    # a short document: horizontal sync does not hang with it
    if command.startswith("IDM_VIEW_SYN") or command == "IDM_VIEW_ZOOM_SYNC":
        app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    start = app.checked(command)
    app.run(command)
    mid = app.checked(command)
    app.run(command)
    end = app.checked(command)
    default_on = command in ("IDM_VIEW_NPC_CCUNIEOL", "IDM_VIEW_INDENT_GUIDE")
    assert (start, mid, end) == ((True, False, True) if default_on else (False, True, False))


@pytest.mark.case("VIEW-005")
def test_view_005_show_all_characters_shows_spaces_tabs_line_ends_and_invisibl(app):
    fresh_doc(app, "a\tb c\u00a0d\n")
    app.run("IDM_VIEW_ALL_CHARACTERS")
    on = (app.sci(SCI_GETVIEWWS), app.sci(SCI_GETVIEWEOL), app.pref("npcShow"))
    checks = [app.checked(c) for c in ("IDM_VIEW_TAB_SPACE", "IDM_VIEW_EOL", "IDM_VIEW_NPC")]
    app.run("IDM_VIEW_ALL_CHARACTERS")
    off = (app.sci(SCI_GETVIEWWS), app.sci(SCI_GETVIEWEOL), app.pref("npcShow"))
    assert on == (1, 1, True) and checks == [True, True, True] and off == (0, 0, False)
    toolbar_press(app, "All Characters")
    assert (app.sci(SCI_GETVIEWWS), app.sci(SCI_GETVIEWEOL), app.pref("npcShow")) == (1, 1, True)
    toolbar_press(app, "All Characters")
    assert (app.sci(SCI_GETVIEWWS), app.sci(SCI_GETVIEWEOL)) == (0, 0)
    assert app.text() == "a\tb c\u00a0d\n" and not app.doc()["modified"]


@pytest.mark.case("VIEW-006")
def test_view_006_the_browser_commands_are_reachable_by_their_notepad_ids_safa(app):
    tree = app.menu_tree("View", 1)
    sub = next(i for i in tree if i.get("title") == "View Current File in")["items"]
    assert [i["title"] for i in sub] == ["Firefox", "Chrome", "Edge", "Safari"]
    items = app.menu("IDM_VIEW_IN_FIREFOX", "IDM_VIEW_IN_CHROME", "IDM_VIEW_IN_EDGE", "IDM_VIEW_IN_IE")
    assert {k: (v or {}).get("title") for k, v in items.items()} == {
        "IDM_VIEW_IN_FIREFOX": "Firefox", "IDM_VIEW_IN_CHROME": "Chrome", "IDM_VIEW_IN_EDGE": "Edge",
        "IDM_VIEW_IN_IE": "Safari"}


# ---------------------------------------------------------------- window modes

@pytest.mark.case("VIEW-007")
def test_view_007_always_on_top_floats_the_window_and_puts_it_back(app):
    fresh_doc(app, "keep")
    levels = [level(app)]
    app.run("IDM_VIEW_ALWAYSONTOP")
    levels.append(level(app))
    chrome = app.get("editor", "chromeVisible") and not app.get("editor", "statusField.hidden")
    app.run("IDM_VIEW_ALWAYSONTOP")
    levels.append(level(app))
    assert levels == [0, 3, 0] and chrome and app.text() == "keep"


@pytest.mark.case("VIEW-008")
def test_view_008_the_alwaysontop_launch_switch_starts_the_window_on_top(app):
    try:
        app.start(args=["-alwaysOnTop"])
        app.wait(lambda: level(app) == 3, timeout=5)
        on = (level(app), app.checked("IDM_VIEW_ALWAYSONTOP"))
        app.run("IDM_VIEW_ALWAYSONTOP")
        off = (level(app), app.checked("IDM_VIEW_ALWAYSONTOP"))
    finally:
        app.start()
    assert on == (3, True) and off == (0, False)


def _settled(app, timeout=5.0):
    """Until the window's frame stops moving: a full-screen transition is animated, and a toggle sent
    while it runs is ignored by AppKit."""
    last = None
    def still():
        nonlocal last
        app.idle(0.25)
        f = main_window(app)["frame"]
        same, last = f == last, f
        return same
    app.wait(still, timeout=timeout)


@pytest.mark.case("VIEW-009")
@pytest.mark.slow
def test_view_009_toggle_full_screen_mode_enters_and_leaves_full_screen(app):
    fresh_doc(app, "full")
    app.select(1, 3)
    before = main_window(app)["frame"]
    fs = lambda: bool(app.get("window", "styleMask") & FULLSCREEN_BIT)   # noqa: E731
    app.run("IDM_VIEW_FULLSCREENTOGGLE")
    app.wait(fs, timeout=10)
    app.wait(lambda: main_window(app)["frame"] != before, timeout=5)
    _settled(app)
    screen = parse_rect(app.get("window", "screen.frame"))
    # On a display with a camera housing a full-screen window stops below it (the safe area).
    # The whole width, from the screen's bottom edge up to at least what a normal window may use: the
    # system keeps a band at the top in full screen on some displays (a camera housing, or the menu bar
    # left showing - 38 pt on the VM's 1728x1117 screen, which reports no safe-area inset).
    # (In full screen the screen's visibleFrame is the whole screen, so the band is bounded by the
    # height of a menu bar with a camera housing instead: at most 40 pt.)
    frame = main_window(app)["frame"]
    assert abs(frame[2] - screen[2]) <= 2 and abs(frame[0] - screen[0]) <= 2 and abs(frame[1] - screen[1]) <= 2, (frame, screen)
    assert screen[3] - 40 <= frame[3] <= screen[3] + 2, (frame, screen)
    assert app.text() == "full" and app.selection()["caret"]["line"] == 1
    app.run("IDM_VIEW_FULLSCREENTOGGLE")
    app.wait(lambda: not fs(), timeout=10)
    app.wait(lambda: all(abs(a - b) <= 2 for a, b in zip(main_window(app)["frame"], before)), timeout=5)
    _settled(app)
    app.keys("ctrl+cmd+f")
    app.wait(fs, timeout=10)
    _settled(app)
    app.keys("ctrl+cmd+f")
    app.wait(lambda: not fs(), timeout=10)


@pytest.mark.case("VIEW-010")
def test_view_010_post_it_hides_the_chrome_and_floats_the_window_and_toggles_b(app, tmp):
    only(app, write(tmp, "p.txt", "note\n"))
    app.run("IDM_VIEW_POSTIT")
    state = (app.get("editor", "chromeVisible"), app.get("editor", "statusField.hidden"),
             app.get("editor", "pathField.hidden"), app.get("editor", "tabBar.hidden"), level(app))
    app.select(1, 1)
    app.type("x")
    typed = app.text()
    app.run("IDM_VIEW_POSTIT")
    back = (app.get("editor", "chromeVisible"), app.get("editor", "statusField.hidden"), level(app))
    assert state == (False, True, True, True, 3)
    assert typed == "xnote\n"
    assert back == (True, False, 0)


@pytest.mark.case("VIEW-011")
def test_view_011_leaving_post_it_keeps_a_previous_always_on_top(app):
    app.run("IDM_VIEW_ALWAYSONTOP")
    app.run("IDM_VIEW_POSTIT")
    app.run("IDM_VIEW_POSTIT")
    kept = level(app)
    assert kept == 3
    app.run("IDM_VIEW_ALWAYSONTOP")
    assert level(app) == 0


@pytest.mark.case("VIEW-012")
def test_view_012_post_it_does_nothing_while_distraction_free_is_on(app):
    app.run("IDM_VIEW_DISTRACTIONFREE")
    app.run("IDM_VIEW_POSTIT")
    during = (app.get("editor", "chromeVisible"), level(app))
    app.run("IDM_VIEW_DISTRACTIONFREE")
    after = (app.get("editor", "chromeVisible"), level(app))
    assert during == (False, 0) and after == (True, 0)


def _df_margin(app):
    width = view_frame(app)[2]
    return app.sci(SCI_GETMARGINLEFT), width


@pytest.mark.case("VIEW-013")
def test_view_013_distraction_free_hides_the_chrome_and_centres_the_text(app):
    with prefs(app, distractionFreeDivPart=4):
        fresh_doc(app, "word " * 60 + "\n")
        app.run("IDM_VIEW_DISTRACTIONFREE")
        hidden = (app.get("editor", "chromeVisible"), app.get("editor", "statusField.hidden"),
                  app.get("editor", "pathField.hidden"))
        left, width = _df_margin(app)
        app.run("IDM_VIEW_DISTRACTIONFREE")
        back = (app.get("editor", "chromeVisible"), app.get("editor", "statusField.hidden"))
        assert hidden == (False, True, True)
        assert abs(left - width / 4) <= 1, (left, width)
        assert back == (True, False) and app.sci(SCI_GETMARGINLEFT) <= 9


@pytest.mark.case("VIEW-014")
@pytest.mark.parametrize("part", [3, 5, 6])
def test_view_014_the_distraction_free_width_follows_preferences(app, part):
    with prefs(app, distractionFreeDivPart=part):
        fresh_doc(app, "text\n")
        app.run("IDM_VIEW_DISTRACTIONFREE")
        left, width = _df_margin(app)
        app.run("IDM_VIEW_DISTRACTIONFREE")
    assert abs(left - width / part) <= 1, (left, width, part)


@pytest.mark.case("VIEW-015")
def test_view_015_distraction_free_stays_on_across_tab_changes(app):
    fresh_doc(app, "one\n")
    app.new("two\n")
    app.run("IDM_VIEW_DISTRACTIONFREE")
    left = app.sci(SCI_GETMARGINLEFT)
    app.run("IDM_VIEW_TAB_NEXT")
    after_switch = (app.get("editor", "chromeVisible"), app.get("editor", "tabBar.hidden"),
                    app.get("editor", "statusField.hidden"))
    app.new("z")
    after_new = (app.get("editor", "chromeVisible"), app.get("editor", "tabBar.hidden"),
                 app.get("editor", "statusField.hidden"), app.sci(SCI_GETMARGINLEFT))
    app.run("IDM_VIEW_DISTRACTIONFREE")
    assert after_switch == (False, True, True)
    assert after_new == (False, True, True, left)
    assert app.get("editor", "chromeVisible") and not app.get("editor", "statusField.hidden")


# ---------------------------------------------------------------- show symbol

@pytest.mark.case("VIEW-016")
def test_view_016_show_space_and_tab_shows_whitespace_in_both_views_and_is_rem(app, tmp):
    fresh_doc(app, "a\tb  c\n")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    before = snap(app, tmp / "ws0.png")
    app.run("IDM_VIEW_TAB_SPACE")
    on = (app.sci(SCI_GETVIEWWS), app.sci(SCI_GETVIEWWS, view="sub"), app.pref("showWhitespace"))
    after = snap(app, tmp / "ws1.png")
    app.run("IDM_VIEW_TAB_SPACE")
    off = (app.sci(SCI_GETVIEWWS), app.sci(SCI_GETVIEWWS, view="sub"), app.pref("showWhitespace"))
    assert on == (1, 1, True) and off == (0, 0, False)
    assert list(before.get_flattened_data()) != list(after.get_flattened_data())
    assert app.text() == "a\tb  c\n" and not app.doc()["modified"]


@pytest.mark.case("VIEW-017")
@pytest.mark.restart
def test_view_017_show_space_and_tab_survives_a_restart(app):
    app.run("IDM_VIEW_TAB_SPACE")
    try:
        app.restart()
        app.new("x y")
        assert app.sci(SCI_GETVIEWWS) == 1
    finally:
        app.start()


@pytest.mark.case("VIEW-018")
@pytest.mark.restart
def test_view_018_show_end_of_line_shows_line_ends_in_both_views_for_later_doc(app):
    try:
        fresh_doc(app, "a\r\nb\n")
        app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
        app.run("IDM_VIEW_EOL")
        both = (app.sci(SCI_GETVIEWEOL), app.sci(SCI_GETVIEWEOL, view="sub"))
        app.new("later")
        later = app.sci(SCI_GETVIEWEOL)
        app.restart()
        app.new("again")
        restarted = app.sci(SCI_GETVIEWEOL)
        assert both == (1, 1) and later == 1 and restarted == 1
    finally:
        app.start()


@pytest.mark.case("VIEW-019")
def test_view_019_show_indent_guide_in_both_views_and_from_the_toolbar(app):
    fresh_doc(app, "if x:\n    y = 1\n", language="python")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    default = (app.sci(SCI_GETINDENTATIONGUIDES), app.sci(SCI_GETINDENTATIONGUIDES, view="sub"))
    app.run("IDM_VIEW_INDENT_GUIDE")
    off = (app.sci(SCI_GETINDENTATIONGUIDES), app.sci(SCI_GETINDENTATIONGUIDES, view="sub"))
    toolbar_press(app, "Indent Guide")
    on = (app.sci(SCI_GETINDENTATIONGUIDES), app.sci(SCI_GETINDENTATIONGUIDES, view="sub"))
    assert default == (SC_IV_LOOKBOTH, SC_IV_LOOKBOTH)
    assert off == (0, 0) and on == (SC_IV_LOOKBOTH, SC_IV_LOOKBOTH)


@pytest.mark.case("VIEW-020")
def test_view_020_show_wrap_symbol_marks_wrapped_lines(app, tmp):
    fresh_doc(app, "word " * 80 + "\n")
    app.run("IDM_VIEW_WRAP")
    plain = snap(app, tmp / "w0.png")
    app.run("IDM_VIEW_WRAP_SYMBOL")
    main_flags = app.sci(SCI_GETWRAPVISUALFLAGS)
    marked = snap(app, tmp / "w1.png")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    sub_flags = app.sci(SCI_GETWRAPVISUALFLAGS, view="sub")
    app.run("IDM_VIEW_WRAP_SYMBOL")
    off = (app.sci(SCI_GETWRAPVISUALFLAGS), app.sci(SCI_GETWRAPVISUALFLAGS, view="sub"))
    app.run("IDM_VIEW_WRAP")
    assert main_flags == SC_WRAPVISUALFLAG_END
    assert list(plain.get_flattened_data()) != list(marked.get_flattened_data())
    assert app.text() == "word " * 80 + "\n"
    assert sub_flags == SC_WRAPVISUALFLAG_END and off == (0, 0)


@pytest.mark.case("VIEW-021")
def test_view_021_show_non_printing_characters_shows_invisible_characters_by_n(app, tmp):
    fresh_doc(app, "a\u00a0b\u200bc\n")
    before = snap(app, tmp / "n0.png")
    app.run("IDM_VIEW_NPC")
    on = app.pref("npcShow")
    after = snap(app, tmp / "n1.png")
    names_on = [representation(app, c) for c in ("\u00a0", "\u200b")]
    app.run("IDM_VIEW_NPC")
    off = app.pref("npcShow")
    assert on is True and off is False
    assert list(before.get_flattened_data()) != list(after.get_flattened_data())
    assert app.text() == "a\u00a0b\u200bc\n"
    # Upstream's nonPrintChars names while shown; none once hidden again.
    assert names_on == ["NBSP", "ZWSP"]
    assert [representation(app, c) for c in ("\u00a0", "\u200b")] == ["", ""]


@pytest.mark.case("VIEW-022")
def test_view_022_show_control_characters_unicode_eol_shows_or_hides_c0_contro(app, tmp):
    fresh_doc(app, "a\u0001b\u2028c\n")
    assert app.pref("ccUniEolShow") in (True, None)
    shown = snap(app, tmp / "c0.png")
    shown_as = representation(app, "\u0001")
    app.run("IDM_VIEW_NPC_CCUNIEOL")
    off = app.pref("ccUniEolShow")
    hidden = snap(app, tmp / "c1.png")
    hidden_as = representation(app, "\u0001")
    app.run("IDM_VIEW_NPC_CCUNIEOL")
    assert off is False and app.pref("ccUniEolShow") is True
    assert list(shown.get_flattened_data()) != list(hidden.get_flattened_data())
    # Shown: its C0 mnemonic; hidden: upstream draws it as a zero-width space.
    assert shown_as == "SOH" and hidden_as == "\u200b"
    assert representation(app, "\u0001") == "SOH"




@pytest.mark.case("VIEW-023")
@pytest.mark.parametrize("command,message", [
    pytest.param("IDM_VIEW_TAB_SPACE", SCI_GETVIEWWS, id="space"),
    pytest.param("IDM_VIEW_EOL", SCI_GETVIEWEOL, id="eol"),
    pytest.param("IDM_VIEW_INDENT_GUIDE", SCI_GETINDENTATIONGUIDES, id="indent"),
    pytest.param("IDM_VIEW_WRAP_SYMBOL", SCI_GETWRAPVISUALFLAGS, id="wrapsymbol"),
    pytest.param("IDM_VIEW_NPC", None, id="npc"),
    pytest.param("IDM_VIEW_NPC_CCUNIEOL", None, id="cc"),
])
def test_view_023_symbols_apply_to_the_second_view_and_to_documents_opened_lat(app, command, message):
    # The two NPC commands show as the representation of a character they cover.
    ch = "\u0001" if command == "IDM_VIEW_NPC_CCUNIEOL" else "\u00a0"
    read = (lambda view: representation(app, ch, view=view)) if message is None else (lambda view: app.sci(message, view=view))
    fresh_doc(app, "a\tb\n    c\n")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    before = read("main")
    app.run(command)
    app.new("later\n")
    app.run("IDM_VIEW_GOTO_ANOTHER_VIEW")
    main, sub = read("main"), read("sub")
    app.run(command)
    assert main == sub, (main, sub)
    if message is None:
        assert main != before, (before, main)


@pytest.mark.case("VIEW-024")
def test_view_024_showing_symbols_never_changes_the_text(app, tmp):
    data = "a\tb\r\nc\u00a0d\u0001e\r\n".encode("utf-8")
    p = write(tmp, "s.txt", data)
    only(app, p)
    for c in ["IDM_VIEW_TAB_SPACE", "IDM_VIEW_EOL", "IDM_VIEW_NPC", "IDM_VIEW_NPC_CCUNIEOL",
              "IDM_VIEW_ALL_CHARACTERS", "IDM_VIEW_INDENT_GUIDE", "IDM_VIEW_WRAP_SYMBOL"]:
        for _ in range(2):
            try:
                app.run(c)
            except ToolError:
                pass      # IDM_VIEW_ALL_CHARACTERS is not in the menus (VIEW-005)
            assert not app.doc()["modified"], c
    assert app.sci(SCI_CANUNDO) == 0
    # Nothing to save: Save is greyed on an unmodified document (checkDocState), the file as it was.
    assert not app.enabled("IDM_FILE_SAVE")
    assert p.read_bytes() == data


# ---------------------------------------------------------------- zoom

@pytest.mark.case("VIEW-025")
def test_view_025_zoom_in_zoom_out_and_restore_default_zoom(app):
    fresh_doc(app, "zoom me\n")
    app.select(1, 3)
    seen = []
    for c in ["IDM_VIEW_ZOOMIN"] * 3 + ["IDM_VIEW_ZOOMOUT", "IDM_VIEW_ZOOMRESTORE"]:
        app.run(c)
        seen.append(app.sci(SCI_GETZOOM))
    assert seen == [1, 2, 3, 2, 0]
    assert app.text() == "zoom me\n" and app.sci(SCI_GETCURRENTPOS) == 2


@pytest.mark.case("VIEW-026")
def test_view_026_zoom_stops_at_its_limits(app):
    fresh_doc(app, "z")
    for _ in range(20):
        app.run("IDM_VIEW_ZOOMOUT")
    low = app.sci(SCI_GETZOOM)
    for _ in range(79):
        app.run("IDM_VIEW_ZOOMIN")
    high79 = app.sci(SCI_GETZOOM)
    app.run("IDM_VIEW_ZOOMIN")
    high80 = app.sci(SCI_GETZOOM)
    app.run("IDM_VIEW_ZOOMRESTORE")
    assert low == -10 and high79 == high80 > 0 and app.sci(SCI_GETZOOM) == 0


@pytest.mark.case("VIEW-027")
def test_view_027_zoom_buttons_on_the_toolbar(app):
    fresh_doc(app, "z")
    seen = []
    for label in ["Zoom In", "Zoom In", "Zoom Out"]:
        toolbar_press(app, label)
        seen.append(app.sci(SCI_GETZOOM))
    assert seen == [1, 2, 1]


@pytest.mark.case("VIEW-028")
def test_view_028_zoom_belongs_to_the_view_not_the_document(app):
    fresh_doc(app, "one")
    app.new("two")
    _run_all(app, "IDM_VIEW_ZOOMIN", "IDM_VIEW_ZOOMIN", "IDM_VIEW_TAB_NEXT")
    after_switch = app.sci(SCI_GETZOOM)
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    assert after_switch == 2 and app.sci(SCI_GETZOOM, view="sub") == 0


@pytest.mark.case("VIEW-029")
def test_view_029_synchronize_zoom_across_views_mirrors_zoom_both_ways(app):
    _clone_long(app, 50)
    app.run("IDM_VIEW_ZOOM_SYNC")
    app.run("IDM_VIEW_ZOOMIN")
    app.idle(0.2)
    both = (app.sci(SCI_GETZOOM), app.sci(SCI_GETZOOM, view="sub"))
    app.sci(SCI_SETZOOM, 4, view="sub")
    app.idle(0.3)
    followed = app.sci(SCI_GETZOOM)
    app.run("IDM_VIEW_ZOOM_SYNC")
    app.run("IDM_VIEW_ZOOMIN")
    app.idle(0.2)
    assert both == (1, 1) and followed == 4
    assert (app.sci(SCI_GETZOOM), app.sci(SCI_GETZOOM, view="sub")) == (5, 4)


@pytest.mark.case("VIEW-030")
def test_view_030_zoom_still_works_with_zoom_and_vertical_synchronization_both(app):
    _clone_long(app, 400)
    app.run("IDM_VIEW_ZOOM_SYNC")
    app.run("IDM_VIEW_SYNSCROLLV")
    app.run("IDM_VIEW_ZOOMIN")
    app.idle(0.3)
    assert (app.sci(SCI_GETZOOM), app.sci(SCI_GETZOOM, view="sub")) == (1, 1)


# ---------------------------------------------------------------- word wrap

@pytest.mark.case("VIEW-031")
def test_view_031_word_wrap_wraps_long_lines_in_both_views_without_touching_th(app):
    text = "word " * 100 + "\n"
    fresh_doc(app, text)
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    app.run("IDM_VIEW_WRAP")
    on = (app.sci(SCI_GETWRAPMODE), app.sci(SCI_GETWRAPMODE, view="sub"), app.pref("wordWrap"),
          app.checked("IDM_VIEW_WRAP"))
    rows = app.sci(SCI_WRAPCOUNT, 0)
    app.run("IDM_VIEW_WRAP")
    off = (app.sci(SCI_GETWRAPMODE), app.sci(SCI_GETWRAPMODE, view="sub"), app.pref("wordWrap"),
           app.checked("IDM_VIEW_WRAP"))
    assert on == (SC_WRAP_WORD, SC_WRAP_WORD, True, True) and rows > 1
    assert off == (0, 0, False, False) and app.sci(SCI_WRAPCOUNT, 0) == 1
    assert app.text() == text and not app.doc()["modified"]


@pytest.mark.case("VIEW-032")
def test_view_032_word_wrap_from_the_toolbar_button(app):
    fresh_doc(app, "x")
    toolbar_press(app, "Word Wrap")
    on = app.sci(SCI_GETWRAPMODE)
    toolbar_press(app, "Word Wrap")
    assert on == SC_WRAP_WORD and app.sci(SCI_GETWRAPMODE) == 0


@pytest.mark.case("VIEW-033")
@pytest.mark.restart
def test_view_033_word_wrap_is_remembered_and_applies_to_files_opened_later(app, tmp):
    app.run("IDM_VIEW_WRAP")
    try:
        app.open(write(tmp, "later.txt", "later\n"))
        later = app.sci(SCI_GETWRAPMODE)
        app.restart()
        app.new("again")
        assert later == SC_WRAP_WORD and app.sci(SCI_GETWRAPMODE) == SC_WRAP_WORD
    finally:
        app.start()


# ---------------------------------------------------------------- folding

def _cpp(app, text=CPP2):
    fresh_doc(app, text, language="cpp")
    app.sci(SCI_COLOURISE, 0, -1)


@pytest.mark.case("VIEW-034")
def test_view_034_fold_all_and_unfold_all(app):
    _cpp(app)
    app.run("IDM_VIEW_FOLDALL")
    hidden = [ln for ln in range(8) if not visible(app, ln)]
    heads = (expanded(app, 0), expanded(app, 5))
    app.run("IDM_VIEW_UNFOLDALL")
    assert hidden == [1, 2, 3, 4, 6, 7] and heads == (False, False)
    assert all(visible(app, ln) for ln in range(8)) and all(expanded(app, h) for h in headers(app))
    assert app.text() == CPP2


@pytest.mark.case("VIEW-035")
def test_view_035_folding_commands_on_a_document_without_folding_do_nothing(app):
    fresh_doc(app, "1\n2\n3\n4\n5\n", language="normal")
    for c in ["IDM_VIEW_FOLDALL", "IDM_VIEW_UNFOLDALL", "IDM_VIEW_FOLD_CURRENT", "IDM_VIEW_UNFOLD_CURRENT",
              "IDM_VIEW_FOLD_1"]:
        assert app.run(c)["ran"]
        assert all(visible(app, ln) for ln in range(5)), c
    assert app.text() == "1\n2\n3\n4\n5\n"


@pytest.mark.case("VIEW-036")
def test_view_036_fold_current_level_folds_the_block_the_caret_is_in(app):
    _cpp(app)
    app.select(3, 5)
    app.run("IDM_VIEW_FOLD_CURRENT")
    vis = [visible(app, ln) for ln in range(8)]
    state = (expanded(app, 0), expanded(app, 1), expanded(app, 5))
    app.run("IDM_VIEW_UNFOLD_CURRENT")
    reopened = visible(app, 2) and visible(app, 3)
    app.select(1, 1)
    app.run("IDM_VIEW_FOLD_CURRENT")
    assert vis == [True, True, False, False, True, True, True, True]
    assert state == (True, False, True) and reopened
    assert [visible(app, ln) for ln in range(8)] == [True, False, False, False, False, True, True, True]
    assert expanded(app, 5)


@pytest.mark.case("VIEW-037")
def test_view_037_fold_unfold_current_level_toggle_when_preferences_makes_them(app):
    with prefs(app, foldCommandsToggle=True):
        _cpp(app)
        app.select(3, 5)
        seen = []
        for c in ["IDM_VIEW_FOLD_CURRENT", "IDM_VIEW_FOLD_CURRENT", "IDM_VIEW_UNFOLD_CURRENT", "IDM_VIEW_UNFOLD_CURRENT"]:
            app.run(c)
            seen.append(expanded(app, 1))
    assert seen == [False, True, False, True]


@pytest.mark.case("VIEW-038")
@pytest.mark.parametrize("n", range(1, 9))
def test_view_038_fold_level_n_folds_exactly_the_headers_of_level_n(app, n):
    _cpp(app, nested_cpp(8))
    hs = headers(app)
    assert [depth(app, h) for h in hs] == list(range(8))
    app.run("IDM_VIEW_UNFOLDALL")
    app.run(f"IDM_VIEW_FOLD_{n}")
    state = {h: expanded(app, h) for h in hs}
    target = hs[n - 1]
    assert state == {h: h != target for h in hs}
    assert not visible(app, target + 1) and all(visible(app, ln) for ln in range(target + 1))


@pytest.mark.case("VIEW-039")
@pytest.mark.parametrize("n", range(1, 9))
def test_view_039_unfold_level_n_expands_exactly_the_headers_of_level_n(app, n):
    _cpp(app, nested_cpp(8))
    hs = headers(app)
    app.run("IDM_VIEW_FOLDALL")
    app.run(f"IDM_VIEW_UNFOLD_{n}")
    state = {h: expanded(app, h) for h in hs}
    # foldLevel toggles the level-N headers; Scintilla's FoldLine shows a hidden header's parents
    # first (EnsureLineVisible), so after Fold All levels 1..N are open and the deeper ones stay folded.
    assert state == {h: i < n for i, h in enumerate(hs)}


@pytest.mark.case("VIEW-040")
def test_view_040_fold_levels_deeper_than_the_document_change_nothing(app):
    _cpp(app)
    hs = headers(app)
    snapshot = lambda: {h: expanded(app, h) for h in hs}   # noqa: E731
    before = snapshot()
    _run_all(app, "IDM_VIEW_FOLD_5", "IDM_VIEW_FOLD_8")
    assert snapshot() == before
    app.run("IDM_VIEW_FOLDALL")
    folded = snapshot()
    _run_all(app, "IDM_VIEW_UNFOLD_5", "IDM_VIEW_UNFOLD_8")
    assert snapshot() == folded


@pytest.mark.case("VIEW-041")
@pytest.mark.parametrize("language,text", [
    ("python", "def f():\n    if x:\n        y()\n"),
    ("html", "<div>\n<p>\nx\n</p>\n</div>\n"),
    ("xml", "<a>\n <b>\n  c\n </b>\n</a>\n"),
    ("json", "{\n \"a\": [\n  1\n ]\n}\n"),
])
def test_view_041_folding_in_other_lexers(app, language, text):
    fresh_doc(app, text, language=language)
    app.sci(SCI_COLOURISE, 0, -1)
    app.run("IDM_VIEW_FOLDALL")
    folded = visible(app, 1)
    app.run("IDM_VIEW_UNFOLDALL")
    unfolded = visible(app, 1)
    app.run("IDM_VIEW_FOLD_1")
    assert not folded and unfolded
    assert not expanded(app, 0) and not visible(app, 1)


@pytest.mark.case("VIEW-042")
def test_view_042_folds_belong_to_the_document(app, tmp):
    p = write(tmp, "f.cpp", "int f() {\n    return 1;\n}\nint g() {\n    return 2;\n}\n")
    q = write(tmp, "o.txt", "other\n")
    only(app, p, q)
    app.run("IDM_VIEW_TAB_PREV")
    app.sci(SCI_COLOURISE, 0, -1)
    app.select(5, 3)
    app.run("IDM_VIEW_FOLD_CURRENT")
    app.run("IDM_VIEW_TAB_NEXT")
    app.run("IDM_VIEW_TAB_PREV")
    assert current_title(app) == "f.cpp"
    assert not expanded(app, 3) and expanded(app, 0)


# ---------------------------------------------------------------- hide lines

@pytest.mark.case("VIEW-043")
def test_view_043_hide_lines_hides_the_selected_lines_until_show_all_hidden_li(app):
    fresh_doc(app, "1\n2\n3\n4\n5\n6\n")
    app.select(2, 1, 4, 2)
    app.run("IDM_VIEW_HIDELINES")
    vis = [visible(app, ln) for ln in range(6)]
    assert vis == [True, False, False, False, True, True]
    assert app.text() == "1\n2\n3\n4\n5\n6\n"
    r = app.call("e2e_menu_invoke", path="View|Show All Hidden Lines")
    assert r["ran"]
    assert all(visible(app, ln) for ln in range(6))


@pytest.mark.case("VIEW-044")
def test_view_044_hide_lines_with_no_selection_hides_the_caret_line(app):
    fresh_doc(app, "1\n2\n3\n4\n5\n6\n")
    app.select(3, 1)
    app.run("IDM_VIEW_HIDELINES")
    assert [visible(app, ln) for ln in range(6)] == [True, True, False, True, True, True]


@pytest.mark.case("VIEW-045")
def test_view_045_hidden_lines_are_still_part_of_the_document(app, tmp):
    text = "1\n2\n3\n4\n5\n6\n"
    only(app, write(tmp, "h.txt", text))
    app.select(2, 1, 4, 1)
    app.run("IDM_VIEW_HIDELINES")
    app.run("IDM_EDIT_SELECTALL")
    app.run("IDM_EDIT_COPY")
    assert app.clipboard() == text
    out = tmp / "copy.txt"
    app.answers(panels=[str(out)])
    app.run("IDM_FILE_SAVEAS")
    app.wait(lambda: out.exists(), timeout=5)
    assert out.read_text() == text and app.text() == text


# ---------------------------------------------------------------- summary

@pytest.mark.case("VIEW-046")
def test_view_046_summary_reports_the_document_s_counts(app):
    fresh_doc(app, "foo_bar a#b 1,000 O'Connel\n")
    s = summary(app)
    assert s["_title"] == "Summary"
    # Upstream's IDM_VIEW_SUMMARY lines, for an unsaved document (no path or dates).
    assert s["_text"] == ("Characters (without line endings): 26\nWords: 6\nLines: 2\nDocument length: 27\n"
                          "0 selected characters (0 bytes) in 0 ranges")


@pytest.mark.case("VIEW-047")
@pytest.mark.parametrize("text,words", [("", 0), ("one", 1), ("a-b c.d e/f", 6), ("x=1;y=2", 4),
                                        ("tab\tsep\nnew line", 4), ("   ", 0)])
def test_view_047_summary_counts_words_the_way_notepad_does(app, text, words):
    fresh_doc(app, text)
    s = summary(app)
    assert int(s["Words"]) == words
    assert not [w for w in app.windows() if w.get("modal")]


@pytest.mark.case("VIEW-048")
def test_view_048_summary_counts_characters_and_bytes_of_multi_byte_text(app):
    fresh_doc(app, "héllo wörld\n")
    s = summary(app)
    assert (s["Characters (without line endings)"], s["Document length"], s["Words"], s["Lines"]) == ("11", "14", "2", "2")
    app.select(1, 1, 1, 6)
    s = summary(app)
    assert (s["Selected characters"], s["Selected bytes"], s["Ranges"]) == ("5", "6", "1")


@pytest.mark.case("VIEW-049")
def test_view_049_summary_of_an_empty_and_of_a_crlf_document(app, tmp):
    fresh_doc(app, "")
    s = summary(app)
    assert (s["Characters (without line endings)"], s["Document length"], s["Words"], s["Lines"], s["Selected bytes"]) == ("0", "0", "0", "1", "0")
    only(app, write(tmp, "crlf.txt", b"a\r\nb\r\n"))
    s = summary(app)
    assert (s["Document length"], s["Lines"], s["Words"], s["Characters (without line endings)"]) == ("6", "3", "2", "2")


# ---------------------------------------------------------------- monitoring

@pytest.mark.case("VIEW-050")
def test_view_050_monitoring_follows_a_growing_file_and_keeps_it_read_only(app, tmp):
    p = write(tmp, "log.txt", "one\n")
    only(app, p)
    app.run("IDM_VIEW_MONITORING")
    assert app.sci(SCI_GETREADONLY) == 1 and app.doc()["read_only"]
    with open(p, "a") as f:
        f.write("two\n")
    app.wait(lambda: app.text() == "one\ntwo\n", timeout=5)
    assert app.sci(SCI_GETCURRENTPOS) == 8
    assert app.modal_log() == []
    app.type("x")
    assert app.text() == "one\ntwo\n"
    app.run("IDM_VIEW_MONITORING")
    assert app.sci(SCI_GETREADONLY) == 0
    app.type("x")
    assert app.text() == "one\ntwo\nx"


@pytest.mark.case("VIEW-051")
def test_view_051_monitoring_is_refused_for_an_unsaved_document(app):
    fresh_doc(app, "abc")
    app.modal_log(clear=True)
    app.run("IDM_VIEW_MONITORING")
    # Upstream's DocNoExistToMonitor box says why, not a bare beep.
    boxes = [e for e in app.modal_log() if e.get("kind") == "alert"]
    assert [(b["message"], b["informative"]) for b in boxes] == [
        ("Monitoring problem", "The file should exist to be monitored.")]
    assert app.sci(SCI_GETREADONLY) == 0 and not app.get("editor", "monitoringEnabled")
    assert not app.checked("IDM_VIEW_MONITORING")
    app.select(1, 4)
    app.type("d")
    assert app.text() == "abcd"


@pytest.mark.case("VIEW-052")
def test_view_052_monitoring_is_refused_for_a_document_with_unsaved_changes(app, tmp):
    p = write(tmp, "m.txt", "base\n")
    only(app, p)
    app.type("x")
    app.modal_log(clear=True)
    app.run("IDM_VIEW_MONITORING")
    # DocTooDirtyToMonitor.
    boxes = [e for e in app.modal_log() if e.get("kind") == "alert"]
    assert [(b["message"], b["informative"]) for b in boxes] == [
        ("Monitoring problem", "The document is dirty. Please save the modification before monitoring it.")]
    assert not app.get("editor", "monitoringEnabled") and app.sci(SCI_GETREADONLY) == 0
    with open(p, "a") as f:
        f.write("more\n")
    app.idle(1.0)
    assert app.text() == "xbase\n"


@pytest.mark.case("VIEW-053")
def test_view_053_a_rotated_log_is_followed_under_its_name(app, tmp):
    p = write(tmp, "log.txt", "old\n")
    only(app, p)
    app.run("IDM_VIEW_MONITORING")
    os.rename(p, str(p) + ".1")
    p.write_text("fresh\n")
    app.wait(lambda: app.text() == "fresh\n", timeout=5)
    with open(p, "a") as f:
        f.write("more\n")
    app.wait(lambda: app.text() == "fresh\nmore\n", timeout=5)
    assert app.get("editor", "monitoringEnabled")


@pytest.mark.case("VIEW-054")
def test_view_054_a_change_while_another_tab_is_in_front_is_caught_up_on_retur(app, tmp):
    a = write(tmp, "a.log", "first\n")
    b = write(tmp, "b.txt", "bee\n")
    only(app, a)
    app.run("IDM_VIEW_MONITORING")
    app.open(b)
    with open(a, "a") as f:
        f.write("late\n")
    app.idle(1.0)
    app.run("IDM_VIEW_TAB_PREV")
    app.wait(lambda: "late" in app.text(), timeout=5)
    assert app.sci(SCI_GETCURRENTPOS) == app.sci(SCI_GETLENGTH)
    assert app.text(1) == "bee\n"


@pytest.mark.case("VIEW-055")
@pytest.mark.restart
def test_view_055_monitoring_from_the_toolbar_and_in_the_session(app, tmp):
    p = write(tmp, "s.log", "start\n")
    try:
        # Remember the session (MISC.), as the SESSION tests do: the port's default leaves it off.
        app.restart(session=True, defaults={"restoreSession": True})
        app.open(p)
        toolbar_press(app, "Monitoring")
        assert app.get("editor", "monitoringEnabled") and app.sci(SCI_GETREADONLY) == 1
        app.restart(session=True)
        app.wait(lambda: any(d["path"] and app.same_path(d["path"], p) for d in app.docs()), timeout=10)
        idx = next(d["index"] for d in app.docs() if d["path"] and app.same_path(d["path"], p))
        app.call("go_to", document=idx, line=1)
        assert app.get("editor", "monitoringEnabled") and app.sci(SCI_GETREADONLY) == 1
        with open(p, "a") as f:
            f.write("after\n")
        app.wait(lambda: "after" in app.text(), timeout=5)
    finally:
        app.start()


@pytest.mark.case("VIEW-056")
def test_view_056_closing_a_monitored_document_stops_watching_it(app, tmp):
    p = write(tmp, "c.log", "x\n")
    only(app, p)
    app.run("IDM_VIEW_MONITORING")
    app.run("IDM_FILE_CLOSE")
    n = len(app.docs())
    with open(p, "a") as f:
        f.write("y\n")
    app.idle(1.0)
    assert len(app.docs()) == n and app.modal_log() == []
    app.open(p)
    assert app.sci(SCI_GETREADONLY) == 0 and not app.get("editor", "monitoringEnabled")


# ---------------------------------------------------------------- panels

@pytest.mark.case("VIEW-057")
def test_view_057_folder_as_workspace_shows_the_current_file_s_folder(app, tmp):
    folder = tmp / "ws"
    a = write(folder, "a.py", "x = 1\n")
    write(folder, "b.txt", "b\n")
    only(app, a)
    app.run("IDM_VIEW_FILEBROWSER")
    assert dock(app, "isPanelVisible:", "workspace") and dock(app, "placeOfPanel:", "workspace") == 0
    roots = app.get("editor", "workspaceRootPaths")
    assert any(app.same_path(r, folder) for r in roots), roots
    app.run("IDM_VIEW_FILEBROWSER")
    assert not dock(app, "isPanelVisible:", "workspace")


@pytest.mark.case("VIEW-058")
def test_view_058_folder_as_workspace_for_an_unsaved_document_asks_for_the_fol(app, tmp):
    folder = tmp / "pick"
    write(folder, "z.txt", "z\n")
    fresh_doc(app, "unsaved")
    app.answers(panels=[str(folder)])
    app.run("IDM_VIEW_FILEBROWSER")
    log = app.modal_log()
    assert any(e.get("kind") != "alert" for e in log), log
    app.wait(lambda: dock(app, "isPanelVisible:", "workspace"), timeout=5)
    assert any(app.same_path(r, folder) for r in app.get("editor", "workspaceRootPaths"))
    app.run("IDM_VIEW_FILEBROWSER")
    assert not dock(app, "isPanelVisible:", "workspace")
    app.answers(panels=[None])
    app.run("IDM_VIEW_FILEBROWSER")
    assert not dock(app, "isPanelVisible:", "workspace")


def _map_text(app):
    return app.sci(SCI_GETTEXT, 0, 0, view="docMapView", returns="string")


@pytest.mark.case("VIEW-059")
def test_view_059_document_map_shows_a_mirror_of_the_document_on_the_right(app, tmp):
    body = "".join(f"int v{i} = {i};\n" for i in range(200))
    only(app, write(tmp, "m.c", body))
    app.run("IDM_VIEW_DOC_MAP")
    assert dock(app, "isPanelVisible:", "documentMap") and dock(app, "placeOfPanel:", "documentMap") == 1
    assert _map_text(app) == body
    # The map is a second view on the editor's own document (DocumentMap::reloadMap: SCI_SETDOCPOINTER);
    # read-only is the document's, so it is not the map's to have - it is kept out of editing by not
    # taking the keyboard, as upstream's map window.
    assert app.sci(SCI_GETDOCPOINTER, view="docMapView") == app.sci(SCI_GETDOCPOINTER)
    img = snap(app, tmp / "map.png")
    # The map's own column, right of the editor: its text is there at its left edge (short lines at the
    # map's zoom), so the crop is taken from the map view's frame, not a share of the window.
    win = main_window(app)["frame"]
    scale = img.size[0] / win[2]
    views = sorted((c["frame"] for c in ui(app)["controls"] if c["class"] == "ScintillaView"), key=lambda f: f[0])
    mx, my, mw, mh = views[-1]
    assert mx > views[0][0] + views[0][2] - 2                       # right of the editor
    left = int((mx - win[0]) * scale)
    assert len(set(img.crop((left, 20, left + int(40 * scale), int(160 * scale))).get_flattened_data())) > 2
    app.run("IDM_VIEW_DOC_MAP")
    assert not dock(app, "isPanelVisible:", "documentMap")


@pytest.mark.case("VIEW-060")
def test_view_060_document_map_follows_the_tab_in_front(app):
    fresh_doc(app, "first\n")
    app.run("IDM_VIEW_DOC_MAP")
    app.new("second")
    assert _map_text(app) == "second"
    app.run("IDM_VIEW_TAB_NEXT")
    assert _map_text(app) == "first\n"
    app.run("IDM_VIEW_TAB_NEXT")
    assert _map_text(app) == "second"


@pytest.mark.case("VIEW-061")
def test_view_061_a_click_in_the_document_map_scrolls_the_editor_there(app):
    fresh_doc(app, "".join(f"int line{i} = {i};\n" for i in range(3000)))
    app.select(1, 1)
    app.sci(SCI_SETFIRSTVISIBLELINE, 0)
    app.run("IDM_VIEW_DOC_MAP")
    app.idle(0.3)
    # The map shows its own window on the text (a few hundred lines at its zoom); a click in its middle
    # brings the map line there into the editor's view (DocumentMap::scrollMap), whatever the length.
    map_first = app.sci(SCI_GETFIRSTVISIBLELINE, view="docMapView")
    clicked = map_first + app.sci(SCI_LINESONSCREEN, view="docMapView") // 2
    app.mouse(**{"class": "NppMapZoneView"})
    app.idle(0.3)
    first = app.sci(SCI_GETFIRSTVISIBLELINE)
    shown = app.sci(SCI_LINESONSCREEN)
    assert first > 0 and first - 2 <= clicked <= first + shown + 2, (first, shown, clicked)
    assert app.selection()["caret"]["line"] == 1


def _table_with(app, text):
    for c in ui(app)["controls"]:
        if c["class"] in ("NSTableView", "NSOutlineView") and any(text in " ".join(map(str, r)) for r in c.get("cells", [])):
            return c
    return None


@pytest.mark.case("VIEW-062")
def test_view_062_document_list_lists_the_open_documents_and_switches_to_one(app, tmp):
    z, a = write(tmp, "zeta.txt", "z\n"), write(tmp, "alpha.py", "a\n")
    only(app, z, a)
    app.new("")
    app.run("IDM_VIEW_DOCLIST")
    assert dock(app, "placeOfPanel:", "documentList") == 0
    table = _table_with(app, "zeta")
    assert table and table["rows"] == 3
    row = next(i for i, r in enumerate(table["cells"]) if "zeta" in " ".join(r))
    app.act("main", "double_click", value=row, path=table["path"])
    assert current_title(app) == "zeta.txt"
    idx = next(d["index"] for d in app.docs() if d["title"] == "alpha.py")
    app.call("close_document", document=idx, discard_changes=True)
    app.idle(0.2)
    assert not _table_with(app, "alpha")
    app.run("IDM_VIEW_DOCLIST")
    assert not dock(app, "isPanelVisible:", "documentList")


@pytest.mark.case("VIEW-063")
def test_view_063_function_list_lists_the_functions_and_jumps_to_one(app, tmp):
    p = write(tmp, "m.py", "def alpha():\n    pass\n\nclass Beta:\n    def gamma(self):\n        pass\n")
    only(app, p)
    app.run("IDM_VIEW_FUNC_LIST")
    assert dock(app, "placeOfPanel:", "functionList") == 1
    table = _table_with(app, "alpha")
    cells = [" ".join(r) for r in table["cells"]]
    assert cells == ["alpha()  (line 1)", "Beta  (line 4)", "Beta::gamma(self)  (line 5)"]
    app.act("main", "double_click", value=2, path=table["path"])
    assert app.selection()["caret"]["line"] == 5
    app.sci(SCI_DOCUMENTEND)
    app.type("\ndef delta():\n    pass\n")
    # The list is parsed again when the file is saved (and on activation), not while typing (NppIO).
    app.run("IDM_FILE_SAVE")
    app.wait(lambda: _table_with(app, "delta"), timeout=5)
    app.new("plain text", language="normal")
    app.idle(0.3)
    assert not _table_with(app, "alpha")


@pytest.mark.case("VIEW-064")
def test_view_064_project_panels_1_2_and_3_show_and_hide_on_their_own(app):
    for n in (1, 2, 3):
        app.run(f"IDM_VIEW_PROJECT_PANEL_{n}")
        assert dock(app, "isPanelVisible:", f"project{n}") and dock(app, "placeOfPanel:", f"project{n}") == 0
        title = app.get("editor", "projects.title.stringValue")[n - 1]
        assert title.startswith(f"Project Panel {n}"), title
        app.run(f"IDM_VIEW_PROJECT_PANEL_{n}")
        assert not dock(app, "isPanelVisible:", f"project{n}")
    app.run("IDM_VIEW_PROJECT_PANEL_1")
    app.run("IDM_VIEW_PROJECT_PANEL_2")
    assert {"project1", "project2"} <= set(dock(app, "panelsIn:", 0))


@pytest.mark.case("VIEW-065")
@pytest.mark.parametrize("label,panel", [("Document Map", "documentMap"), ("Document List", "documentList"),
                                         ("Function List", "functionList"), ("Folder as Workspace", "workspace")])
def test_view_065_panel_buttons_on_the_toolbar_do_what_the_menu_commands_do(app, tmp, label, panel):
    only(app, write(tmp, "t.py", "def f():\n    pass\n"))
    toolbar_press(app, label)
    on = dock(app, "isPanelVisible:", panel)
    toolbar_press(app, label)
    assert on and not dock(app, "isPanelVisible:", panel)


# ---------------------------------------------------------------- two views

@pytest.mark.case("VIEW-066")
def test_view_066_clone_to_other_view_shows_the_same_buffer_in_both_views(app, tmp):
    a, b = write(tmp, "a.txt", "one\n"), write(tmp, "b.txt", "bee\n")
    only(app, a, b)
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    assert app.get("editor", "secondaryViewVisible")
    app.select(1, 1)
    app.type("X")
    assert app.sci(SCI_GETTEXT, 0, 0, view="sub", returns="string") == "Xbee\n"
    docs = app.docs()
    assert [d["title"] for d in docs].count("b.txt") == 1
    assert next(d for d in docs if d["title"] == "b.txt").get("in_second_view") is True
    assert [app.sci(SCI_STYLEGETFORE, s) for s in range(11)] == [app.sci(SCI_STYLEGETFORE, s, view="sub") for s in range(11)]


@pytest.mark.case("VIEW-067")
def test_view_067_move_to_other_view_takes_the_tab_out_of_the_main_view(app, tmp):
    a, b = write(tmp, "a.txt", "one\n"), write(tmp, "b.txt", "bee\n")
    only(app, a, b)
    app.set_text("changed")
    app.run("IDM_VIEW_GOTO_ANOTHER_VIEW")
    assert tab_titles(app) == ["a.txt"]
    assert app.sci(SCI_GETTEXT, 0, 0, view="sub", returns="string") == "changed"
    moved = [d for d in app.docs() if d["title"] == "b.txt"]
    assert moved and moved[0]["modified"]


@pytest.mark.case("VIEW-068")
def test_view_068_move_to_other_view_with_a_single_document_clones_it(app, tmp):
    only(app, write(tmp, "a.txt", "one\n"))
    app.run("IDM_VIEW_GOTO_ANOTHER_VIEW")
    assert tab_titles(app) == ["a.txt"]
    assert app.get("editor", "secondaryViewVisible")
    assert app.sci(SCI_GETTEXT, 0, 0, view="sub", returns="string") == "one\n"


@pytest.mark.case("VIEW-069")
def test_view_069_focus_on_another_view_moves_the_keyboard_focus_between_views(app):
    fresh_doc(app, "ab")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    app.sci(SCI_GOTOPOS, 0)
    app.sci(SCI_GOTOPOS, 2, view="sub")
    app.run("IDM_VIEW_SWITCHTO_OTHER_VIEW")
    assert app.get("editor", "otherViewHasFocus")
    app.type("Z")
    assert app.text() == "abZ"
    app.run("IDM_VIEW_SWITCHTO_OTHER_VIEW")
    assert not app.get("editor", "otherViewHasFocus")
    app.type("Y")
    assert app.text() == "YabZ"


@pytest.mark.case("VIEW-070")
def test_view_070_focus_on_another_view_with_one_view_does_nothing(app):
    fresh_doc(app, "x")
    app.run("IDM_VIEW_SWITCHTO_OTHER_VIEW")
    assert main_window(app)["first_responder"] in ("SCIContentView", "ScintillaView")
    assert not app.get("editor", "secondaryViewVisible")


@pytest.mark.case("VIEW-071")
def test_view_071_synchronize_vertical_scrolling_scrolls_both_views_together(app):
    _clone_long(app, 400)
    app.run("IDM_VIEW_SYNSCROLLV")
    app.sci(SCI_SETFIRSTVISIBLELINE, 100)
    app.wait(lambda: app.sci(SCI_GETFIRSTVISIBLELINE, view="sub") == 100, timeout=3)
    app.sci(SCI_SETFIRSTVISIBLELINE, 200, view="sub")
    app.wait(lambda: app.sci(SCI_GETFIRSTVISIBLELINE) == 200, timeout=3)
    app.run("IDM_VIEW_SYNSCROLLV")
    app.sci(SCI_SETFIRSTVISIBLELINE, 50)
    app.idle(0.3)
    assert app.sci(SCI_GETFIRSTVISIBLELINE, view="sub") == 200


@pytest.mark.case("VIEW-072")
@pytest.mark.slow
def test_view_072_synchronize_horizontal_scrolling_scrolls_both_views_sideways(fresh_app):
    app = fresh_app
    try:
        _clone_long(app, 400, width=150)
        r = app.call("run_command", command="IDM_VIEW_SYNSCROLLH", timeout=10)
        assert r["ran"]
        app.call("e2e_sci", message=SCI_SETXOFFSET, wparam=50, timeout=10)
        app.call("e2e_idle", seconds=0.3, timeout=10)
        assert app.call("e2e_sci", message=SCI_GETXOFFSET, view="sub", timeout=10)["result"] == 50
        app.call("run_command", command="IDM_VIEW_SYNSCROLLH", timeout=10)
        app.call("e2e_sci", message=SCI_SETXOFFSET, wparam=90, timeout=10)
        assert app.call("e2e_sci", message=SCI_GETXOFFSET, view="sub", timeout=10)["result"] == 50
    finally:
        if not responsive(app):
            app.stop(graceful=False)
            app.start()


@pytest.mark.case("VIEW-073")
def test_view_073_synchronization_commands_without_a_second_view_are_harmless(app):
    # long enough that line 30 at the top is a scroll position at any window height (with 200 lines
    # a tall screen clamps the top line to lines - lines on screen once the zoom grows)
    fresh_doc(app, "\n".join("x" * 50 for _ in range(2000)))
    # What a zoom does to the scroll with no synchronisation at all (Scintilla re-lays out the view)...
    app.sci(SCI_SETFIRSTVISIBLELINE, 30)
    app.run("IDM_VIEW_ZOOMIN")
    plain = app.sci(SCI_GETFIRSTVISIBLELINE)
    app.run("IDM_VIEW_ZOOMRESTORE")
    # ...is what it does with all three on and no second view: they change nothing.
    for c in ["IDM_VIEW_SYNSCROLLV", "IDM_VIEW_SYNSCROLLH", "IDM_VIEW_ZOOM_SYNC"]:
        assert app.run(c)["ran"]
    app.sci(SCI_SETFIRSTVISIBLELINE, 30)
    app.run("IDM_VIEW_ZOOMIN")
    assert app.sci(SCI_GETFIRSTVISIBLELINE) == plain and app.sci(SCI_GETZOOM) == 1
    assert not app.get("editor", "secondaryViewVisible")
    for c in ["IDM_VIEW_SYNSCROLLV", "IDM_VIEW_SYNSCROLLH", "IDM_VIEW_ZOOM_SYNC"]:
        assert app.run(c)["ran"]


def _launches(app):
    return [e for e in app.modal_log() if e.get("kind") in ("open_url_with", "open_url", "open_file")]


@pytest.mark.case("VIEW-074")
def test_view_074_move_open_in_new_instance_decline_for_an_unsaved_document(app):
    fresh_doc(app, "keep")
    n = len(app.docs())
    app.run("IDM_VIEW_GOTO_NEW_INSTANCE")
    app.run("IDM_VIEW_LOAD_IN_NEW_INSTANCE")
    assert len(app.docs()) == n and app.text() == "keep"
    assert _launches(app) == []


@pytest.mark.case("VIEW-075")
def test_view_075_open_in_new_instance_hands_the_file_to_a_new_instance_and_ke(app, tmp):
    p = write(tmp, "a.txt", "a\n")
    only(app, p)
    app.run("IDM_VIEW_LOAD_IN_NEW_INSTANCE")
    log = _launches(app)
    assert len(log) == 1 and log[0]["kind"] == "open_url_with"
    target, bundle = log[0]["target"].split(" -> ")
    assert app.same_path(target, p) and bundle.endswith("NotepadMacE2E.app")
    assert any(d["path"] and app.same_path(d["path"], p) for d in app.docs())


@pytest.mark.case("VIEW-076")
def test_view_076_move_to_new_instance_hands_the_file_over_and_closes_it_here(app, tmp):
    a, b = write(tmp, "a.txt", "a\n"), write(tmp, "b.txt", "b\n")
    only(app, a, b)
    app.run("IDM_VIEW_TAB_PREV")
    app.run("IDM_VIEW_GOTO_NEW_INSTANCE")
    log = _launches(app)
    assert len(log) == 1 and app.same_path(log[0]["target"].split(" -> ")[0], a)
    assert [d["title"] for d in app.docs()] == ["b.txt"] and current_title(app) == "b.txt"


def _installed(bundle_id):
    r = subprocess.run(["mdfind", f"kMDItemCFBundleIdentifier == '{bundle_id}'"], capture_output=True, text=True)
    return bool(r.stdout.strip())


@pytest.mark.case("VIEW-077")
@pytest.mark.parametrize("command,bundle", [
    ("IDM_VIEW_IN_FIREFOX", "org.mozilla.firefox"), ("IDM_VIEW_IN_CHROME", "com.google.Chrome"),
    ("IDM_VIEW_IN_EDGE", "com.microsoft.edgemac"),
    pytest.param("IDM_VIEW_IN_IE", "com.apple.Safari"),
])
def test_view_077_view_current_file_in_a_browser(app, tmp, command, bundle):
    fresh_doc(app, "<p>unsaved</p>")
    app.run(command)
    assert _launches(app) == [] and app.text() == "<p>unsaved</p>"
    page = write(tmp, "page.html", "<p>x</p>\n")
    app.open(page)
    app.run(command)
    log = _launches(app)
    if _installed(bundle):
        assert len(log) == 1 and app.same_path(log[0]["target"].split(" -> ")[0], page)
    else:
        assert log == []
    assert any(d["path"] and app.same_path(d["path"], page) for d in app.docs())


# ---------------------------------------------------------------- tabs

def _nine(app, tmp):
    return only(app, *[write(tmp, f"t{i}.txt", f"tab {i}\n") for i in range(1, 10)])


@pytest.mark.case("VIEW-078")
@pytest.mark.parametrize("n", range(1, 10))
def test_view_078_go_to_the_nth_tab(app, tmp, n):
    _nine(app, tmp)
    app.run(f"IDM_VIEW_TAB{n}")
    assert current_title(app) == f"t{n}.txt"
    assert app.get("editor", "tabBar.selectedIndex") == n - 1


@pytest.mark.case("VIEW-079")
def test_view_079_cmd_1_to_cmd_9_go_to_the_tabs_from_the_keyboard(app, tmp):
    _nine(app, tmp)
    for n in range(1, 10):
        app.keys(f"cmd+{n}")
        assert current_title(app) == f"t{n}.txt"


@pytest.mark.case("VIEW-080")
def test_view_080_going_to_a_tab_that_does_not_exist_changes_nothing(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "abc"])
    app.run("IDM_VIEW_TAB2")
    order = tab_titles(app)
    app.run("IDM_VIEW_TAB4")
    app.run("IDM_VIEW_TAB9")
    app.keys("cmd+9")
    assert current_title(app) == "b.txt" and tab_titles(app) == order


@pytest.mark.case("VIEW-081")
def test_view_081_first_tab_and_last_tab(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "abcde"])
    app.run("IDM_VIEW_TAB3")
    app.run("IDM_VIEW_TAB_START")
    first = current_title(app)
    app.run("IDM_VIEW_TAB_END")
    assert first == "a.txt" and current_title(app) == "e.txt"


@pytest.mark.case("VIEW-082")
def test_view_082_next_and_previous_tab_wrap_around_the_ends(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "abc"])
    app.run("IDM_VIEW_TAB_END")
    seen = []
    for c in ["IDM_VIEW_TAB_NEXT", "IDM_VIEW_TAB_PREV", "IDM_VIEW_TAB_PREV"]:
        app.run(c)
        seen.append(current_title(app))
    assert seen == ["a.txt", "c.txt", "b.txt"]
    app.close_all()
    for c in ["IDM_VIEW_TAB_NEXT", "IDM_VIEW_TAB_PREV"]:
        assert app.run(c)["ran"]
    assert len(app.docs()) == 1


@pytest.mark.case("VIEW-083")
def test_view_083_each_tab_gets_its_caret_and_selection_back(app, tmp):
    a = write(tmp, "a.txt", "first line\nsecond line\n")
    b = write(tmp, "b.txt", "bee line\n")
    only(app, a, b)
    app.run("IDM_VIEW_TAB_PREV")
    app.select(2, 3, 2, 6)
    app.run("IDM_VIEW_TAB_NEXT")
    app.select(1, 2)
    app.run("IDM_VIEW_TAB_PREV")
    s = app.selection()
    # get_selection answers places {line, column, position}: start and end of the selection, the caret
    assert (s["start"]["line"], s["start"]["column"], s["end"]["line"], s["end"]["column"]) == (2, 3, 2, 6)
    app.run("IDM_VIEW_TAB_NEXT")
    s = app.selection()
    assert (s["caret"]["line"], s["caret"]["column"]) == (1, 2)


@pytest.mark.case("VIEW-084")
def test_view_084_move_tab_forward_and_backward(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "ABC"])
    app.run("IDM_VIEW_TAB1")
    _run_all(app, "IDM_VIEW_TAB_MOVEFORWARD", "IDM_VIEW_TAB_MOVEFORWARD")
    assert tab_titles(app) == ["B.txt", "C.txt", "A.txt"] and current_title(app) == "A.txt"
    app.run("IDM_VIEW_TAB_MOVEBACKWARD")
    assert tab_titles(app) == ["B.txt", "A.txt", "C.txt"]
    assert app.text() == "A"


@pytest.mark.case("VIEW-085")
def test_view_085_moving_a_tab_past_either_end_changes_nothing(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "ABC"])
    app.run("IDM_VIEW_TAB1")
    app.run("IDM_VIEW_TAB_MOVEBACKWARD")
    assert tab_titles(app) == ["A.txt", "B.txt", "C.txt"] and current_title(app) == "A.txt"
    app.run("IDM_VIEW_TAB3")
    app.run("IDM_VIEW_TAB_MOVEFORWARD")
    assert tab_titles(app) == ["A.txt", "B.txt", "C.txt"] and current_title(app) == "C.txt"


@pytest.mark.case("VIEW-086")
def test_view_086_move_to_start_and_move_to_end(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "ABCDE"])
    app.run("IDM_VIEW_TAB3")
    app.run("IDM_VIEW_GOTO_START")
    assert tab_titles(app) == ["C.txt", "A.txt", "B.txt", "D.txt", "E.txt"] and current_title(app) == "C.txt"
    app.run("IDM_VIEW_GOTO_END")
    assert tab_titles(app) == ["A.txt", "B.txt", "D.txt", "E.txt", "C.txt"] and current_title(app) == "C.txt"


@pytest.mark.case("VIEW-087")
def test_view_087_moving_tabs_keeps_pinned_tabs_first(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "ABC"])
    app.run("IDM_VIEW_TAB1")
    assert app.call("e2e_menu_invoke", context="tab", path="Pin Tab")["ran"]
    assert tab_attr(app, "pinned")[0]
    app.run("IDM_VIEW_TAB3")
    app.run("IDM_VIEW_GOTO_START")
    after_start = tab_titles(app)
    app.run("IDM_VIEW_TAB3")      # B, second of the unpinned run after the move
    b_index = tab_titles(app).index("B.txt")
    app.call("go_to", document=next(d["index"] for d in app.docs() if d["title"] == "B.txt"), line=1)
    app.run("IDM_VIEW_TAB_MOVEBACKWARD")
    app.run("IDM_VIEW_TAB_MOVEBACKWARD")
    assert after_start == ["A.txt", "C.txt", "B.txt"], after_start
    assert b_index >= 1 and tab_titles(app)[0] == "A.txt"


def _strip_hue(img, frame, bar_y):
    x, y, w, h = frame
    pixels = [img.getpixel((int(x + w * f), int(bar_y))) for f in (0.3, 0.5, 0.7)]
    r = sum(p[0] for p in pixels) / 3
    g = sum(p[1] for p in pixels) / 3
    b = sum(p[2] for p in pixels) / 3
    return r, g, b


@pytest.mark.case("VIEW-088")
def test_view_088_tab_colours_1_to_5_and_remove_color(app, tmp):
    fresh_doc(app, "one")
    app.new("two")
    for c in range(1, 6):
        app.run(f"IDM_VIEW_TAB_COLOUR_{c}")
        assert tab_attr(app, "colour") == [0, c]
    app.run("IDM_VIEW_TAB_COLOUR_NONE")
    assert tab_attr(app, "colour") == [0, 0]
    # The strip's hue, colour 1 (red) against colour 5 (blue), in the snapshot.
    app.run("IDM_VIEW_TAB_COLOUR_1")
    red = snap(app, tmp / "red.png")
    app.run("IDM_VIEW_TAB_COLOUR_5")
    blue = snap(app, tmp / "blue.png")
    app.run("IDM_VIEW_TAB_COLOUR_NONE")
    none = snap(app, tmp / "none.png")
    diff_red = [p for p, q in zip(red.get_flattened_data(), none.get_flattened_data()) if p != q]
    diff_blue = [p for p, q in zip(blue.get_flattened_data(), none.get_flattened_data()) if p != q]
    assert diff_red and diff_blue
    assert sum(p[0] - p[2] for p in diff_red) > 0 and sum(p[2] - p[0] for p in diff_blue) > 0


@pytest.mark.case("VIEW-089")
@pytest.mark.restart
def test_view_089_tab_colours_come_back_with_the_session(app, tmp):
    p = write(tmp, "a.txt", "a\n")
    try:
        # Remember the session (MISC.), as the SESSION tests do: the port's default leaves it off.
        app.restart(session=True, defaults={"restoreSession": True})
        app.open(p)
        app.run("IDM_VIEW_TAB_COLOUR_2")
        app.restart(session=True)
        app.wait(lambda: any(d["path"] and app.same_path(d["path"], p) for d in app.docs()), timeout=10)
        titles = tab_titles(app)
        assert tab_attr(app, "colour")[titles.index("a.txt")] == 2
    finally:
        app.start()


# ---------------------------------------------------------------- text direction

def _ink_side(img, top=60):
    w, h = img.size
    bg = img.getpixel((w // 2, h // 2))
    xs = [x for x in range(0, w, 2) for y in range(top, top + 30, 3) if sum(abs(a - b) for a, b in zip(img.getpixel((x, y)), bg)) > 120]
    return xs


@pytest.mark.case("VIEW-090")
def test_view_090_text_direction_rtl_and_ltr(app, tmp):
    fresh_doc(app, "abc\n")
    app.run("IDM_EDIT_RTL")
    rtl = app.sci(SCI_GETBIDIRECTIONAL)
    app.run("IDM_EDIT_LTR")
    ltr = app.sci(SCI_GETBIDIRECTIONAL)
    assert rtl == SC_BIDIRECTIONAL_R2L and ltr == SC_BIDIRECTIONAL_L2R
    assert app.text() == "abc\n" and not app.doc()["modified"]


@pytest.mark.case("VIEW-091")
def test_view_091_asking_for_the_direction_already_in_force_changes_nothing(app):
    fresh_doc(app, "abc\n")
    wrap = app.sci(SCI_GETWRAPMODE)
    app.run("IDM_EDIT_LTR")
    assert app.sci(SCI_GETBIDIRECTIONAL) == SC_BIDIRECTIONAL_L2R
    app.run("IDM_EDIT_RTL")
    app.run("IDM_EDIT_RTL")
    assert app.sci(SCI_GETBIDIRECTIONAL) == SC_BIDIRECTIONAL_R2L
    assert app.sci(SCI_GETWRAPMODE) == wrap and app.text() == "abc\n"


@pytest.mark.case("VIEW-092")
def test_view_092_text_direction_applies_to_the_view_in_front_only(app):
    fresh_doc(app, "abc\n")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    app.call("e2e_act", window="main", action="focus", target={"class": "ScintillaView", "index": 0})
    app.run("IDM_EDIT_RTL")
    both = (app.sci(SCI_GETBIDIRECTIONAL), app.sci(SCI_GETBIDIRECTIONAL, view="sub"))
    app.run("IDM_EDIT_LTR")
    # the view in front turns right to left, the other is left as it was (Scintilla's default
    # "disabled" is left to right too; upstream's changeTextDirection sets one window only)
    assert both[0] == SC_BIDIRECTIONAL_R2L and both[1] != SC_BIDIRECTIONAL_R2L, both
    assert app.sci(SCI_GETBIDIRECTIONAL) == SC_BIDIRECTIONAL_L2R
