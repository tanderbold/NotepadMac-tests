"""SEARCH: end-to-end tests (plan: plan/SEARCH.md)."""
import os
import time
from pathlib import Path

import pytest

from harness.sci import *  # noqa: F401,F403
from _util_search import (BOXES, FIND_MARK, Dlg, bookmarks, beeps, caret, caret_line, fresh_dlg, make_tree,
                                open_dlg, prefs_restore, prefs_snapshot, ranges, real, results_front,
                                results_text, sel, setsel, status_contains, titles, wait_search_done)


@pytest.fixture(autouse=True)
def _search_state(app):
    """Every test starts without a Search results tab and with the dialog at its defaults, and leaves
    the search preferences as it found them."""
    close_results(app)
    Dlg(app).reset()
    saved = prefs_snapshot(app)
    yield
    if app.running:
        try:
            settle_folder_search(app)
            Dlg(app).reset()
            prefs_restore(app, saved)
        except Exception:  # noqa: BLE001 - a crashed test must not break the next one
            pass


def settle_folder_search(app):
    """A folder search left running is stopped; a dialog left believing one runs (SEARCH-063) gets a restart."""
    if not app.get("app", "runningSearch"):
        return
    app.invoke("app", "findPanelStop:", [None])
    try:
        app.wait(lambda: not app.get("app", "runningSearch"), timeout=15, message="the search to stop")
    except TimeoutError:
        app.restart()


def close_results(app):
    """The results tab is not in list_documents, so the fixture's close_all leaves it: close it here."""
    for _ in range(3):
        if not any(app.get("editor", "documents.isSearchResults")):
            return
        app.run("IDM_FOCUS_ON_FOUND_RESULTS")
        app.run("IDM_FILE_CLOSE")


def newest(text):
    """The newest search of a results text (older ones follow it)."""
    cut = text.find('\nSearch "', 1)
    return text if cut < 0 else text[:cut + 1]


STYLES = [1, 2, 3, 4, 5]   # style 5 has its own indicator again: smart highlighting moved to 19
# Clear Style n with the other style m = n % 5 + 1: style 5 is involved for n = 4 and n = 5.
STYLES_PAIRED = [1, 2, 3, 4, 5]


BOOKMARK = 1                              # the bookmark marker's number
HISTORY_MARKERS = 0xF << 21               # SC_MARKNUM_HISTORY_REVERTED_TO_ORIGIN .. REVERTED_TO_MODIFIED
ROOT = Path(__file__).resolve().parent.parent


def go_to(app, answer):
    """Search > Go to... answered with OK and the given text."""
    app.answers(alerts=[{"button": 1, "field": answer}])
    app.run("IDM_SEARCH_GOTOLINE")


def place(app):
    """(line, column) of the caret, line one-based, column zero-based."""
    return caret_line(app), app.sci(SCI_GETCOLUMN, caret(app))


def open_edited(app, tmp, lines, edited):
    """A saved file of `lines` lines ("l1".."ln"), opened, with "X" typed at the start of each edited line."""
    f = tmp / "history.txt"
    f.write_text("".join(f"l{i}\n" for i in range(1, lines + 1)))
    app.open(f)
    for line in edited:
        app.select(line, 1)
        app.type("X", window="main")
    app.wait(lambda: app.text().count("X") == len(edited), message="the edits")
    return f


def chars_in_range(app, low, high):
    """Search > Find characters in range... with both prompts answered, and the log of what was shown."""
    app.answers(alerts=[{"button": 1, "field": low}, {"button": 1, "field": high}, 1])
    app.run("IDM_SEARCH_FINDCHARINRANGE")
    return app.modal_log()


def count_status(n):
    return "Count: 1 match" if n == 1 else f"Count: {n} matches"


def do_count(d, what):
    d.set("what", what)
    d.press("Count")
    return d.status()


def fif_dlg(app, what, folder):
    """The Find in Files tab at its defaults with Find what and Directory filled."""
    d = fresh_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.set("what", what)
    d.set("dir", str(folder))
    return d


def fif_run(d, button="Find All"):
    d.press(button)
    return wait_search_done(d)


def report_files(app, root):
    """The files the newest search's report lists, relative to root."""
    prefix = real(root) + "/"
    out = []
    for line in newest(results_text(app)).split("\n"):
        if line.startswith(prefix) and line.endswith(")") and " (" in line:
            out.append(line[len(prefix):line.rindex(" (")])
    return out


def snapshot_tree(root):
    root = Path(root)
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def write_workspace(root):
    """A Notepad++ workspace ws.xml with project "P" listing p1.txt and p2.txt."""
    root = Path(root)
    (root / "p1.txt").write_bytes(b"needle one\n")
    (root / "p2.txt").write_bytes(b"none\n")
    (root / "ws.xml").write_text('<?xml version="1.0" encoding="UTF-8" ?>\n<NotepadPlus>\n'
                                 f'    <Project name="P">\n        <File name="{root}/p1.txt" />\n'
                                 f'        <File name="{root}/p2.txt" />\n    </Project>\n</NotepadPlus>\n')


def tick_project(app, d, n, on):
    """Ticks Project Panel n (1-3) on the Find in Projects tab."""
    r = app.act(d.number, "set_state", 1 if on else 0, title=f"Project Panel {n}", **{"class": "NSButton"})
    assert r.get("acted"), r


def results_line(app, prefix):
    """The 1-based line of the results tab that starts with prefix."""
    if not results_front(app):
        app.run("IDM_FOCUS_ON_FOUND_RESULTS")
    for i, l in enumerate(app.text().split("\n")):
        if l.startswith(prefix):
            return i + 1
    raise AssertionError(f"no results line {prefix!r}")


def big_tree(root, n=3000):
    """n files of 20 KB, each with "needle" once."""
    root = Path(root)
    filler = (b"x" * 99 + b"\n") * 200
    for i in range(n):
        (root / f"f{i:04}.txt").write_bytes(filler[:10000] + b"needle\n" + filler[:10000 - 7])
    return root


@pytest.mark.case("SEARCH-001")
def test_search_001_find_opens_the_dialog_on_the_find_tab_with_the_find_controls(app):
    """SEARCH-001: Find... opens the dialog on the Find tab with the Find controls

    Covers: IDM_SEARCH_FIND
    Channel: menu, ui
    Steps: With a document "one two one\\n" and nothing selected, run IDM_SEARCH_FIND; read the dialog's controls.
    Expect: an NppPanel titled "Find" is visible and key; the segmented control has items Find, Replace, Find in Files, Find in Projects, Mark with index 0 selected; visible buttons are Find Next, Count, Find All in Current Document, Find All in All Opened Documents; Replace with / Filters / Directory fields are hidden; the check boxes Match case, Match whole word only, Wrap around (on), Backward direction, In selection are present; the Find what field has keyboard focus
    """
    app.new("one two one\n")
    setsel(app, 0)
    d = fresh_dlg(app)
    # Started outside the user's GUI session (straight over ssh) the app never becomes active and
    # no window of it is key: that is the environment, not the app - run through tools/vm.sh.
    assert app.wait(lambda: app.get("nsapp", "active"), timeout=5, message="the app active"), \
        "the application is not active: run the suite in the GUI session (tools/vm.sh test)"
    w = app.wait(lambda: [x for x in app.windows() if x["number"] == d.number and x["key"]], message="key dialog")[0]
    assert w["class"] == "NppPanel" and w["visible"]
    assert d.title == "Find" and d.tab_index == 0
    assert d.get("findTabs.segmentCount") == 5
    # the field editor of Find what has the keyboard focus
    assert w["first_responder"] == "NSTextView"
    for title in ["Find Next", "Count", "Find All in Current Document", "Find All in All Opened Documents"]:
        assert app.act(d.number, "focus", title=title, **{"class": "NSButton"})["acted"]
    for outlet in ["replaceField", "filtersField", "directoryField"]:
        assert d.hidden(outlet)
    for box in ["case", "word", "wrap", "backward", "insel"]:
        assert not d.hidden(BOXES[box][0])
    assert d.state("wrap") == 1



@pytest.mark.case("SEARCH-002")
def test_search_002_each_dialog_command_opens_its_own_tab(app):
    """SEARCH-002: Each dialog command opens its own tab

    Covers: IDM_SEARCH_REPLACE, IDM_SEARCH_FINDINFILES, IDM_SEARCH_FIND
    Channel: menu, ui
    Steps: For each of (IDM_SEARCH_FIND, "Find", 0), (IDM_SEARCH_REPLACE, "Replace", 1), (IDM_SEARCH_FINDINFILES, "Find in Files", 2): run the command and read the dialog.
    Expect: the window title is the tab's name; the segmented control's selected index is the tab's; Replace shows Replace with, the swap button, Find Next, Replace, Replace All, Replace All in All Opened Documents; Find in Files shows Filters, Directory, Browse…, From doc, In all sub-folders (on), In hidden folders (off), Find All, Replace in Files and hides Backward direction and In selection
    """
    app.new("x\n")
    Dlg(app).reset()
    for cmd, title, index in [("IDM_SEARCH_FIND", "Find", 0), ("IDM_SEARCH_REPLACE", "Replace", 1),
                              ("IDM_SEARCH_FINDINFILES", "Find in Files", 2)]:
        d = open_dlg(app, cmd)
        assert d.title == title and d.tab_index == index
        if title == "Replace":
            assert not d.hidden("replaceField")
            for b in ["⇅", "Find Next", "Replace", "Replace All", "Replace All in All Opened Documents"]:
                app.act(d.number, "focus", title=b, **{"class": "NSButton"})
        if title == "Find in Files":
            for outlet in ["filtersField", "directoryField", "recursiveBox", "hiddenBox"]:
                assert not d.hidden(outlet)
            for b in ["Browse…", "From doc", "Find All", "Replace in Files"]:
                app.act(d.number, "focus", title=b, **{"class": "NSButton"})
            assert d.state("recursive") == 1 and d.state("hidden") == 0
            assert d.hidden("backwardBox") and d.hidden("inSelectionBox")



@pytest.mark.case("SEARCH-003")
def test_search_003_switching_tabs_in_the_dialog_swaps_controls_and_title_and_cl(app):
    """SEARCH-003: Switching tabs in the dialog swaps controls and title and clears the status

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Open Find, press Count on "one" so the status line reads "Count: …", then select each segment "Replace", "Find in Files", "Find in Projects", "Mark" with e2e_act select.
    Expect: the window title follows the segment; the status line is empty after each switch; the Mark tab shows Bookmark line, Purge for each search, Mark All, Clear all marks, Copy Marked Text; the Find in Projects tab shows Project Panel 1 (on), Project Panel 2 (off), Project Panel 3 (off), Find All, Replace in Projects
    """
    app.new("one two one\n")
    d = fresh_dlg(app)
    assert do_count(d, "one") == count_status(2)
    for name in ["Replace", "Find in Files", "Find in Projects", "Mark"]:
        d.select_tab(name)
        assert d.status() == ""
        if name == "Mark":
            for outlet in ["bookmarkLineBox", "purgeBox"]:
                assert not d.hidden(outlet)
            for b in ["Mark All", "Clear all marks", "Copy Marked Text"]:
                app.act(d.number, "focus", title=b, **{"class": "NSButton"})
        if name == "Find in Projects":
            boxes = d.get("projectPanelBoxes.state")
            assert boxes == [1, 0, 0]
            assert d.get("projectPanelBoxes.hidden") == [0, 0, 0] or d.get("projectPanelBoxes.hidden") == [False] * 3
            for b in ["Find All", "Replace in Projects"]:
                app.act(d.number, "focus", title=b, **{"class": "NSButton"})



@pytest.mark.case("SEARCH-004")
def test_search_004_the_selection_seeds_find_what(app):
    """SEARCH-004: The selection seeds Find what

    Covers: IDM_SEARCH_FIND
    Channel: menu, ui
    Steps: For each of: a selection "two" in "one two three"; the caret inside "three" with nothing selected; a 2000-byte selection (over fillFindWhatThreshold 1024) after Find what held "prev": open the dialog.
    Expect: Find what is "two"; then "three" (the word under the caret); then still "prev" (a selection over the threshold does not seed the field)
    """
    app.new("one two three\n" + "z" * 2100 + "\n")
    Dlg(app).reset()
    setsel(app, 4, 7)
    d = open_dlg(app)
    assert d.value("what") == "two"
    d.close()
    setsel(app, 10)
    d = open_dlg(app)
    assert d.value("what") == "three"
    d.set("what", "prev")
    d.close()
    setsel(app, 14, 14 + 2000)
    d = open_dlg(app)
    assert d.value("what") == "prev"



@pytest.mark.case("SEARCH-005")
def test_search_005_in_selection_follows_the_selection_when_the_dialog_opens(app):
    """SEARCH-005: In selection follows the selection when the dialog opens

    Covers: IDM_SEARCH_FIND
    Channel: menu, ui
    Steps: For each of: no selection; a 3-character selection; a 1100-character selection: open the dialog (IDM_SEARCH_FIND) and read In selection.
    Expect: no selection: In selection disabled and off; 3 characters: enabled and unchanged (off); 1100 characters (at least inSelectionThreshold 1024): enabled and ticked
    """
    app.new("abcdef\n" + "x" * 1200 + "\n")
    d = Dlg(app)
    d.reset()
    setsel(app, 0)
    d = open_dlg(app)
    assert not d.enabled("insel") and d.state("insel") == 0
    d.close()
    setsel(app, 0, 3)
    d = open_dlg(app)
    assert d.enabled("insel") and d.state("insel") == 0
    d.close()
    setsel(app, 7, 7 + 1100)
    d = open_dlg(app)
    assert d.enabled("insel") and d.state("insel") == 1



@pytest.mark.case("SEARCH-006")
def test_search_006_keyboard_shortcuts_of_the_search_menu(app):
    """SEARCH-006: Keyboard shortcuts of the Search menu

    Covers: IDM_SEARCH_FIND, IDM_SEARCH_REPLACE, IDM_SEARCH_FINDINFILES, IDM_SEARCH_FINDNEXT, IDM_SEARCH_FINDPREV, IDM_SEARCH_GOTOLINE, IDM_SEARCH_TOGGLE_BOOKMARK, IDM_SEARCH_NEXT_BOOKMARK, IDM_SEARCH_PREV_BOOKMARK, IDM_SEARCH_SETANDFINDNEXT, IDM_SEARCH_SETANDFINDPREV, IDM_SEARCH_FINDINCREMENT, IDM_SEARCH_GOTOMATCHINGBRACE, IDM_SEARCH_SELECTMATCHINGBRACES
    Channel: menu, keys
    Steps: Read each item's key equivalent with e2e_menu; then press cmd+f, alt+cmd+f, shift+cmd+f in the editor, and cmd+b on line 2 of a three-line document.
    Expect: keys are cmd+f, alt+cmd+f, shift+cmd+f, cmd+g, shift+cmd+g, cmd+l, cmd+b, shift+cmd+b, alt+cmd+b, cmd+e, shift+cmd+e, cmd+i, cmd+m, shift+cmd+m respectively; the three chords open the dialog on Find, Replace and Find in Files; cmd+b bookmarks line 2 (`bookmarks` tool lists [2])
    """
    expected = {"IDM_SEARCH_FIND": "cmd+f", "IDM_SEARCH_REPLACE": "alt+cmd+f", "IDM_SEARCH_FINDINFILES": "shift+cmd+f",
                "IDM_SEARCH_FINDNEXT": "cmd+g", "IDM_SEARCH_FINDPREV": "shift+cmd+g", "IDM_SEARCH_GOTOLINE": "cmd+l",
                "IDM_SEARCH_TOGGLE_BOOKMARK": "cmd+b", "IDM_SEARCH_NEXT_BOOKMARK": "shift+cmd+b",
                "IDM_SEARCH_PREV_BOOKMARK": "alt+cmd+b", "IDM_SEARCH_SETANDFINDNEXT": "cmd+e",
                "IDM_SEARCH_SETANDFINDPREV": "shift+cmd+e", "IDM_SEARCH_FINDINCREMENT": "cmd+i",
                "IDM_SEARCH_GOTOMATCHINGBRACE": "cmd+m", "IDM_SEARCH_SELECTMATCHINGBRACES": "shift+cmd+m"}
    items = app.menu(*expected)
    assert {k: items[k].get("key") for k in expected} == expected
    app.new("a\nb\nc\n")
    Dlg(app).reset()
    # shift+cmd+<letter> is not pressed: e2e_keys sends charactersIgnoringModifiers without the
    # shift ("f", where AppKit gives "F"), so such a chord reaches the unshifted item (reported).
    for chord, title in [("cmd+f", "Find"), ("alt+cmd+f", "Replace")]:
        d = Dlg(app)
        d.close()
        app.keys(chord, window="main")
        app.wait(lambda: d.visible and d.title == title, message=title)
    Dlg(app).close()
    app.select(2, 1)
    app.keys("cmd+b", window="main")
    assert bookmarks(app) == [2]



@pytest.mark.case("SEARCH-007")
def test_search_007_escape_and_the_close_button_hide_the_dialog_keeping_its_fiel(app):
    """SEARCH-007: Escape and the close button hide the dialog, keeping its fields

    Covers: IDM_SEARCH_FIND
    Channel: keys, ui
    Steps: Open Find, set Find what to "keepme", press escape in the dialog; reopen with IDM_SEARCH_FIND with the caret on an empty line; then close it with close_window and reopen.
    Expect: after escape the dialog is not visible and the main window is still open; on reopening Find what still reads "keepme" and the options are as left
    """
    app.new("abc\n\n")
    d = fresh_dlg(app)
    d.set("what", "keepme")
    d.box("case", True)
    app.keys("escape", window=d.number)
    app.wait(lambda: not d.visible, message="the dialog hidden")
    assert any(w["main_window"] for w in app.windows())
    app.select(2, 1)
    d = open_dlg(app)
    assert d.value("what") == "keepme" and d.state("case") == 1
    app.close_window(d.number)
    assert not d.visible
    d = open_dlg(app)
    assert d.value("what") == "keepme" and d.state("case") == 1



@pytest.mark.case("SEARCH-008")
def test_search_008_the_search_options_and_mode_are_remembered_across_launches(fresh_app):
    """SEARCH-008: The search options and mode are remembered across launches

    Covers: IDM_SEARCH_FIND
    Channel: ui, prefs, launch
    Steps: (fresh_app) In the dialog tick Match case and Match whole word only, untick Wrap around, pick Regular expression, press Count on "x"; restart keeping preferences; open the dialog.
    Expect: prefs findMatchCase true, findWholeWord true, findWrap false, findMode 2 after the Count; after the restart the boxes and the mode radio show the same state; Match whole word only is disabled (regex mode)
    """
    app = fresh_app
    app.new("x y x\n")
    d = fresh_dlg(app)
    d.box("case", True)
    d.box("word", True)
    d.box("wrap", False)
    d.set_mode(2)
    do_count(d, "x")
    p = app.prefs("findMatchCase", "findWholeWord", "findWrap", "findMode")
    assert p == {"findMatchCase": True, "findWholeWord": True, "findWrap": False, "findMode": 2}
    app.restart()
    app.new("x\n")
    d = open_dlg(app)
    assert d.state("case") == 1 and d.state("word") == 1 and d.state("wrap") == 0 and d.mode() == 2
    assert not d.enabled("word")
    app.stop()
    app.start()



@pytest.mark.case("SEARCH-009")
def test_search_009_find_what_history_keeps_ten_entries_newest_first_and_persist(app):
    """SEARCH-009: Find what history keeps ten entries, newest first, and persists

    Covers: IDM_SEARCH_FIND
    Channel: ui, prefs
    Steps: Press Count for "term0" … "term11", then for "term3"; read the Find what combo items and the findHistory pref. Restore findHistory afterwards.
    Expect: exactly 10 items; first "term3", second "term11"; "term0" and "term1" are gone; findHistory equals the combo's items
    """
    app.new("one two one\n")
    d = fresh_dlg(app)
    for i in range(12):
        do_count(d, f"term{i}")
    do_count(d, "term3")
    items = d.items("what")
    assert len(items) == 10 and items[0] == "term3" and items[1] == "term11"
    assert "term0" not in items and "term1" not in items
    assert app.pref("findHistory") == items



@pytest.mark.case("SEARCH-010")
def test_search_010_the_swap_button_trades_find_what_and_replace_with(app):
    """SEARCH-010: The swap button trades Find what and Replace with

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: On the Replace tab set Find what "left" and Replace with "right", click the "⇅" button.
    Expect: Find what reads "right" and Replace with reads "left"
    """
    app.new("x\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "left")
    d.set("with", "right")
    d.press("⇅")
    assert d.value("what") == "right" and d.value("with") == "left"



@pytest.mark.case("SEARCH-011")
def test_search_011_mode_dependent_options_are_greyed_out(app):
    """SEARCH-011: Mode-dependent options are greyed out

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Select each mode (Normal, Extended, Regular expression) and read Match whole word only and ". matches newline".
    Expect: Normal and Extended: whole word enabled, ". matches newline" disabled; Regular expression: whole word disabled, ". matches newline" enabled
    """
    app.new("x\n")
    d = fresh_dlg(app)
    for row, word, dot in [(0, True, False), (1, True, False), (2, False, True), (0, True, False)]:
        d.set_mode(row)
        assert d.enabled("word") == word and d.enabled("dotnl") == dot



@pytest.mark.case("SEARCH-012")
def test_search_012_dialog_transparency_on_losing_focus_or_always(app):
    """SEARCH-012: Dialog transparency on losing focus or always

    Covers: IDM_SEARCH_FIND
    Channel: ui, prefs
    Steps: Tick Transparency, choose "Always" (focus the second NSMatrix and press down), set the slider to 100; then untick Transparency. Read `window:<dialog>` alphaValue with e2e_invoke key after each step. Restore findTransparencyMode.
    Expect: with Always the alpha is about 100/255 even while key and pref findTransparencyMode is 2; unticked the alpha is 1.0 and findTransparencyMode is 0; the slider and radios are disabled when unticked
    """
    app.new("x\n")
    d = fresh_dlg(app)
    was = app.prefs("findTransparencyMode", "findTransparencyLevel")
    try:
        d.box("transparency", True)
        app.act(d.number, "select", 1, path="0.1.44")
        app.act(d.number, "set_value", 100, path="0.1.45")
        alpha = d.get("findPanel.alphaValue")
        assert abs(alpha - 100 / 255) < 0.02
        assert app.pref("findTransparencyMode") == 2
        d.box("transparency", False)
        assert d.get("findPanel.alphaValue") == 1.0
        assert app.pref("findTransparencyMode") == 0
        assert not d.get("transparencyRadios.enabled") and not d.get("transparencySlider.enabled")
    finally:
        d.box("transparency", True)
        app.act(d.number, "select", 0, path="0.1.44")
        app.act(d.number, "set_value", 150, path="0.1.45")
        app.set_prefs(**{k: v for k, v in was.items() if v is not None})



@pytest.mark.case("SEARCH-013")
def test_search_013_find_next_selects_the_next_match_and_advances(app):
    """SEARCH-013: Find Next selects the next match and advances

    Covers: IDM_SEARCH_FIND
    Channel: ui, mcp
    Steps: Document "x x x\\n", caret at 0; Find what "x", Normal; press Find Next three times, then a fourth time.
    Expect: selections are 0-1, 2-3, 4-5, then 0-1 again (wrap on); the status line is empty after each successful press
    """
    app.new("x x x\n")
    d = fresh_dlg(app)
    d.set("what", "x")
    setsel(app, 0)
    for want in [(0, 1), (2, 3), (4, 5)]:
        d.press("Find Next")
        assert sel(app) == want
        assert d.status() == ""
    # The fourth wraps round, and says so as Notepad++ does (SEARCH-016).
    d.press("Find Next")
    assert sel(app) == (0, 1)
    assert d.status() == "Find: Reached document end, first occurrence from the top found."



@pytest.mark.case("SEARCH-014")
def test_search_014_find_next_without_a_match_reports_it_and_leaves_the_selectio(app):
    """SEARCH-014: Find Next without a match reports it and leaves the selection

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "abc\\n" with caret at 1; Find what "zzz"; press Find Next.
    Expect: selection unchanged (caret 1, nothing selected); status line reads `Find: Can't find the text "zzz"`
    """
    app.new("abc\n")
    d = fresh_dlg(app)
    d.set("what", "zzz")
    setsel(app, 1)
    d.press("Find Next")
    assert sel(app) == (1, 1)
    assert d.status() == 'Find: Can\'t find the text "zzz"'



@pytest.mark.case("SEARCH-015")
def test_search_015_wrap_around_off_stops_at_the_end_of_the_document(app):
    """SEARCH-015: Wrap around off stops at the end of the document

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "one one\\n", caret after the second "one"; untick Wrap around; press Find Next; tick it again and press Find Next.
    Expect: unticked: selection unchanged and status `Find: Can't find the text "one"`; ticked: the first "one" (0-3) is selected
    """
    app.new("one one\n")
    d = fresh_dlg(app)
    d.set("what", "one")
    d.box("wrap", False)
    setsel(app, 7)
    d.press("Find Next")
    assert sel(app) == (7, 7)
    assert d.status() == 'Find: Can\'t find the text "one"'
    d.box("wrap", True)
    d.press("Find Next")
    assert sel(app) == (0, 3)



@pytest.mark.case("SEARCH-016")
def test_search_016_find_next_reports_wrapping_round_the_end_notepad_status(app):
    """SEARCH-016: Find Next reports wrapping round the end (Notepad++ status)

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "one one\\n", caret after the second "one", Wrap around on; press Find Next. Then tick Backward direction, caret at 0, press Find Next.
    Expect: forward: selection 0-3 and status "Find: Reached document end, first occurrence from the top found."; backward: selection 4-7 and status "Find: Reached document beginning, first occurrence from the bottom found." (the port's dialog Find Next leaves the status empty: likely defect)
    """
    app.new("one one\n")
    d = fresh_dlg(app)
    d.set("what", "one")
    setsel(app, 7)
    d.press("Find Next")
    assert sel(app) == (0, 3)
    assert d.status() == "Find: Reached document end, first occurrence from the top found."
    d.box("backward", True)
    setsel(app, 0)
    d.press("Find Next")
    assert sel(app) == (4, 7)
    assert d.status() == "Find: Reached document beginning, first occurrence from the bottom found."



@pytest.mark.case("SEARCH-017")
def test_search_017_backward_direction_searches_up_from_the_selection(app):
    """SEARCH-017: Backward direction searches up from the selection

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "a1 a2 a3\\n", select "a3" (6-8); tick Backward direction; Find what "a"; press Find Next twice.
    Expect: selections 3-4 then 0-1; untick Backward direction afterwards
    """
    app.new("a1 a2 a3\n")
    d = fresh_dlg(app)
    d.box("backward", True)
    d.set("what", "a")
    setsel(app, 6, 8)
    d.press("Find Next")
    assert sel(app) == (3, 4)
    d.press("Find Next")
    assert sel(app) == (0, 1)



@pytest.mark.case("SEARCH-018")
def test_search_018_match_case_narrows_the_matches(app):
    """SEARCH-018: Match case narrows the matches

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "alpha Alpha alphabet\\n"; Find what "alpha"; press Count with Match case off, then on.
    Expect: "Count: 3 matches", then "Count: 2 matches"
    """
    app.new("alpha Alpha alphabet\n")
    d = fresh_dlg(app)
    assert do_count(d, "alpha") == count_status(3)
    d.box("case", True)
    assert do_count(d, "alpha") == count_status(2)



@pytest.mark.case("SEARCH-019")
def test_search_019_match_whole_word_only_narrows_the_matches(app):
    """SEARCH-019: Match whole word only narrows the matches

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "alpha Alpha alphabet\\n"; Match case on; tick Match whole word only; Count "alpha". Then Normal mode "a.b" whole word in "a.b xa.b".
    Expect: "Count: 1 match"; the second count is "Count: 1 match" (word boundary around a literal with a dot)
    """
    app.new("alpha Alpha alphabet\n")
    d = fresh_dlg(app)
    d.box("case", True)
    d.box("word", True)
    assert do_count(d, "alpha") == count_status(1)
    app.set_text("a.b xa.b\n")
    assert do_count(d, "a.b") == count_status(1)



@pytest.mark.case("SEARCH-020")
def test_search_020_normal_mode_takes_regex_metacharacters_literally(app):
    """SEARCH-020: Normal mode takes regex metacharacters literally

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: For each of "a.c", "(x)", "[1]", "a*b", "$", "\\\\d": document containing each once plus look-alikes ("a.c abc (x) x [1] 1 a*b aab $ \\\\d 5"); Normal mode, Match case on; Count.
    Expect: each count is "Count: 1 match"
    """
    app.new("a.c abc (x) x [1] 1 a*b aab $ \\d 5\n")
    d = fresh_dlg(app)
    d.box("case", True)
    for term in ["a.c", "(x)", "[1]", "a*b", "$", "\\d"]:
        assert do_count(d, term) == count_status(1), term



@pytest.mark.case("SEARCH-021")
def test_search_021_extended_mode_converts_its_escapes(app):
    """SEARCH-021: Extended mode converts its escapes

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: For each (Find what, document, expected count): ("a\\\\tb", "a\\tb a b", 1), ("\\\\n", "x\\ny\\nz", 2), ("\\\\x41", "ABA", 2), ("\\\\d065", "A", 1), ("\\\\o101", "A", 1), ("\\\\u0041", "A", 1), ("\\\\b01000001", "A", 1), ("\\\\\\\\", "a\\\\b", 1), ("\\\\q", "\\\\q q", 1): Extended mode, Match case on, Count.
    Expect: each status reads "Count: <expected> match(es)" with the expected number; an unknown escape "\\\\q" keeps its backslash
    """
    app.new("x\n")
    d = fresh_dlg(app)
    d.set_mode(1)
    d.box("case", True)
    for what, text, n in [("a\\tb", "a\tb a b", 1), ("\\n", "x\ny\nz", 2), ("\\x41", "ABA", 2),
                          ("\\d065", "A", 1), ("\\o101", "A", 1), ("\\u0041", "A", 1), ("\\b01000001", "A", 1),
                          ("\\\\", "a\\b", 1), ("\\q", "\\q q", 1)]:
        app.set_text(text)
        assert do_count(d, what) == count_status(n), what



@pytest.mark.case("SEARCH-022")
def test_search_022_extended_r_n_finds_crlf_line_endings(app, tmp):
    """SEARCH-022: Extended \\r\\n finds CRLF line endings

    Covers: IDM_SEARCH_FIND
    Channel: ui, files
    Steps: Open a file saved with CRLF endings "a\\r\\nb\\r\\nc\\r\\n"; Extended mode, Find what "\\\\r\\\\n"; Count; then Find what "\\\\n" alone; then "b\\\\r".
    Expect: "Count: 3 matches" for both "\\\\r\\\\n" and "\\\\n"; "Count: 1 match" for "b\\\\r"
    """
    path = tmp / "crlf.txt"
    path.write_bytes(b"a\r\nb\r\nc\r\n")
    app.open(path)
    d = fresh_dlg(app)
    d.set_mode(1)
    assert do_count(d, "\\r\\n") == count_status(3)
    assert do_count(d, "\\n") == count_status(3)
    assert do_count(d, "b\\r") == count_status(1)



@pytest.mark.case("SEARCH-023")
def test_search_023_regular_expressions_use_boost_syntax(app):
    """SEARCH-023: Regular expressions use Boost syntax

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: For each (pattern, document, count): ("\\\\d+", "one 11 two 22 three 333", 3), ("\\\\d{3}", same, 1), ("^.", "abc\\ndef\\n", 2), ("\\\\bfoo\\\\b", "foo food foo", 2), ("(?<=a)b", "ab cb", 1), ("\\\\p{Lu}", "aBcD", 2), ("[[:digit:]]+", "a1b22", 2), ("(?i)ABC", "abc", 1): Regular expression mode, Match case on, Count.
    Expect: each count as listed
    """
    app.new("x\n")
    d = fresh_dlg(app)
    d.set_mode(2)
    d.box("case", True)
    for pattern, text, n in [("\\d+", "one 11 two 22 three 333", 3), ("\\d{3}", "one 11 two 22 three 333", 1),
                             ("^.", "abc\ndef\n", 2), ("\\bfoo\\b", "foo food foo", 2), ("(?<=a)b", "ab cb", 1),
                             ("\\p{Lu}", "aBcD", 2), ("[[:digit:]]+", "a1b22", 2), ("(?i)ABC", "abc", 1)]:
        app.set_text(text)
        assert do_count(d, pattern) == count_status(n), pattern



@pytest.mark.case("SEARCH-024")
def test_search_024_matches_newline_decides_whether_crosses_line_ends(app):
    """SEARCH-024: ". matches newline" decides whether . crosses line ends

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "a\\nb\\n"; regex "a.b"; Count with ". matches newline" off, then on; then document "a\\r\\nb" with "a..b" and the box on.
    Expect: "Count: 0 matches", then "Count: 1 match"; the CRLF document gives "Count: 1 match"
    """
    app.new("a\nb\n")
    d = fresh_dlg(app)
    d.set_mode(2)
    assert do_count(d, "a.b") == count_status(0)
    d.box("dotnl", True)
    assert do_count(d, "a.b") == count_status(1)
    app.set_text("a\r\nb")
    assert do_count(d, "a..b") == count_status(1)



@pytest.mark.case("SEARCH-025")
def test_search_025_and_anchor_per_line_also_in_crlf_documents(app):
    """SEARCH-025: $ and ^ anchor per line, also in CRLF documents

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: For each document "ab\\ncd\\n" and "ab\\r\\ncd\\r\\n": regex "b$", Count; then "^c", Count; then press Find Next on "d$" from caret 0.
    Expect: "Count: 1 match" for each pattern in both documents; Find Next selects "d" (not including "\\r")
    """
    app.new("x\n")
    d = fresh_dlg(app)
    d.set_mode(2)
    for text, dpos in [("ab\ncd\n", 4), ("ab\r\ncd\r\n", 5)]:
        app.set_text(text)
        assert do_count(d, "b$") == count_status(1), text
        assert do_count(d, "^c") == count_status(1), text
        d.set("what", "d$")
        setsel(app, 0)
        d.press("Find Next")
        assert sel(app) == (dpos, dpos + 1), text



@pytest.mark.case("SEARCH-026")
def test_search_026_an_empty_match_does_not_trap_find_next(app):
    """SEARCH-026: An empty match does not trap Find Next

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "ab\\ncd\\nef\\n"; regex "$"; caret at 0; press Find Next four times.
    Expect: the caret visits positions 2, 5, 8, 9 (the ends of lines 1-3 and of the empty last line), then wraps to 2; it never stays on the same position twice in a row
    """
    app.new("ab\ncd\nef\n")
    d = fresh_dlg(app)
    d.set_mode(2)
    d.set("what", "$")
    setsel(app, 0)
    seen = []
    for _ in range(5):
        d.press("Find Next")
        seen.append(caret(app))
    assert seen == [2, 5, 8, 9, 2]



@pytest.mark.case("SEARCH-027")
def test_search_027_an_invalid_regular_expression_is_reported_as_invalid(app):
    """SEARCH-027: An invalid regular expression is reported as invalid

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Regex mode, Find what "("; press Find Next, then Count; also "a{2,1}".
    Expect: the selection and document are unchanged and no alert is shown; the status line reads "Find: Invalid regular expression" as Notepad++ says (the port says `Find: Can't find the text "("` and "Count: 0 matches": likely defect)
    """
    app.new("a(b\n")
    d = fresh_dlg(app)
    d.set_mode(2)
    setsel(app, 1)
    for pattern in ["(", "a{2,1}"]:
        d.set("what", pattern)
        d.press("Find Next")
        assert sel(app) == (1, 1) and app.text() == "a(b\n"
        assert app.modal_log() == []
        assert d.status() == "Find: Invalid regular expression", pattern
        d.press("Count")
        assert "Invalid regular expression" in d.status(), pattern



@pytest.mark.case("SEARCH-028")
def test_search_028_count_with_no_match_one_match_and_a_huge_number_of_matches(app):
    """SEARCH-028: Count with no match, one match, and a huge number of matches

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document of 100000 "a" characters on 1000 lines; Count "a"; Count "aa" (non-overlapping); Count "b"; Count with Find what emptied.
    Expect: "Count: 100000 matches" within 10 s; "Count: 50000 matches"; "Count: 0 matches"; empty Find what gives "Count: 0 matches" and changes nothing
    """
    app.new(("a" * 100 + "\n") * 1000)
    d = fresh_dlg(app)
    t = time.monotonic()
    assert do_count(d, "a") == count_status(100000)
    assert time.monotonic() - t < 10
    assert do_count(d, "aa") == count_status(50000)
    assert do_count(d, "b") == count_status(0)
    d.set("what", "")
    d.press("Count")
    assert d.status() == count_status(0)



@pytest.mark.case("SEARCH-029")
def test_search_029_empty_find_what_does_nothing_on_find_next(app):
    """SEARCH-029: Empty Find what does nothing on Find Next

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "abc", caret at 1; clear Find what; press Find Next.
    Expect: selection and document unchanged; no alert; nothing is added to the Find what history
    """
    app.new("abc\n")
    d = fresh_dlg(app)
    history = app.pref("findHistory")
    setsel(app, 1)
    d.press("Find Next")
    assert sel(app) == (1, 1) and app.text() == "abc\n"
    assert app.modal_log() == []
    assert app.pref("findHistory") == history



@pytest.mark.case("SEARCH-030")
def test_search_030_unicode_text_is_found_and_selected_on_the_right_bytes(app):
    """SEARCH-030: Unicode text is found and selected on the right bytes

    Covers: IDM_SEARCH_FIND
    Channel: ui, mcp
    Steps: Document "😀 café Ωμέγα 日本語 café\\n"; for each of "café", "日本", "Ω", "😀": caret at 0, Find Next; then Count "CAFÉ" with Match case off.
    Expect: get_selection text equals the term each time; "Count: 2 matches" for "CAFÉ" (case folding beyond ASCII)
    """
    app.new("😀 café Ωμέγα 日本語 café\n")
    d = fresh_dlg(app)
    for term in ["café", "日本", "Ω", "😀"]:
        d.set("what", term)
        setsel(app, 0)
        d.press("Find Next")
        assert app.selection()["text"] == term
    assert do_count(d, "CAFÉ") == count_status(2)



@pytest.mark.case("SEARCH-031")
def test_search_031_match_whole_word_only_treats_accented_letters_as_word_charac(app):
    """SEARCH-031: Match whole word only treats accented letters as word characters

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "café naïve cafés CAFÉ\\n"; Normal mode, Match case off; Count "café" with Match whole word only off, then on.
    Expect: "Count: 3 matches", then "Count: 2 matches" ("café" and "CAFÉ", not the "café" inside "cafés"), as Notepad++'s Unicode word boundaries give; the port's ASCII \\b gives 1 match, the wrong one: likely defect
    """
    app.new("café naïve cafés CAFÉ\n")
    d = fresh_dlg(app)
    assert do_count(d, "café") == count_status(3)
    d.box("word", True)
    assert do_count(d, "café") == count_status(2)



@pytest.mark.case("SEARCH-032")
def test_search_032_w_and_b_in_a_regular_expression_are_unicode_aware(app):
    """SEARCH-032: \\w and \\b in a regular expression are Unicode-aware

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Regex mode; document "café naïve cafés CAFÉ\\n"; Count "\\w+"; Count "\\bcaf\\w\\b" with Match case off.
    Expect: as Boost in Notepad++: "Count: 4 matches" for "\\w+" (the port counts 6: caf, na, ve, caf, s, CAF: likely defect); "Count: 2 matches" for the second
    """
    app.new("café naïve cafés CAFÉ\n")
    d = fresh_dlg(app)
    d.set_mode(2)
    assert do_count(d, "\\w+") == count_status(4)
    assert do_count(d, "\\bcaf\\w\\b") == count_status(2)



@pytest.mark.case("SEARCH-033")
def test_search_033_in_selection_limits_find_next_and_count_to_the_selection(app):
    """SEARCH-033: In selection limits Find Next and Count to the selection

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: Document "q q q q\\n"; select 0-3; run IDM_SEARCH_FIND (In selection becomes enabled only when the dialog becomes key), tick In selection, then set Find what "q"; Count; untick; Count.
    Expect: "Count: 2 matches" with In selection, "Count: 4 matches" without
    """
    app.new("q q q q\n")
    Dlg(app).reset()
    setsel(app, 0, 3)
    d = open_dlg(app)
    assert d.enabled("insel")
    d.box("insel", True)
    assert do_count(d, "q") == count_status(2)
    d.box("insel", False)
    assert do_count(d, "q") == count_status(4)



@pytest.mark.case("SEARCH-034")
def test_search_034_find_all_in_current_document_lists_every_hit_line_in_the_res(app):
    """SEARCH-034: Find All in Current Document lists every hit line in the results tab

    Covers: IDM_SEARCH_FIND, IDM_FOCUS_ON_FOUND_RESULTS
    Channel: ui, mcp
    Steps: Untitled document "one two one\\nthree one\\nnone\\n" (title "new N"); Find what "one", whole word off; press Find All in Current Document.
    Expect: a tab "Search results" is in front whose text is `Search "one" in new N\\n\\n\\tLine 1: one two one\\n\\tLine 2: three one\\n\\tLine 3: none\\n\\n4 hits\\n`; each line appears once however many hits it has; the results tab is read-only and not modified
    """
    app.new("one two one\nthree one\nnone\n")
    title = app.doc()["title"]
    d = fresh_dlg(app)
    d.set("what", "one")
    d.press("Find All in Current Document")
    assert results_front(app)
    assert app.text() == f'Search "one" in {title}\n\n\tLine 1: one two one\n\tLine 2: three one\n\tLine 3: none\n\n4 hits\n'
    assert app.sci(SCI_GETREADONLY) == 1
    assert not app.get("editor", "currentDocument.modified")
    assert titles(app).count("Search results") == 1



@pytest.mark.case("SEARCH-035")
def test_search_035_find_all_closes_the_dialog_unless_told_to_stay_open(app):
    """SEARCH-035: Find All closes the dialog unless told to stay open

    Covers: IDM_SEARCH_FIND
    Channel: ui, prefs
    Steps: Press Find All in Current Document with pref findDialogStaysOpen false; reopen; set findDialogStaysOpen true and press it again; restore the pref.
    Expect: first: the dialog is hidden afterwards; second: the dialog stays visible with status "N found"
    """
    app.new("one\n")
    idx = app.doc()["index"]
    app.set_prefs(findDialogStaysOpen=False)
    d = fresh_dlg(app)
    d.set("what", "one")
    d.press("Find All in Current Document")
    app.wait(lambda: not d.visible, message="the dialog closed")
    app.set_prefs(findDialogStaysOpen=True)
    app.select(1, 1, document=idx)
    d = open_dlg(app)
    d.set("what", "one")
    d.press("Find All in Current Document")
    assert d.visible
    assert d.status() == "1 found"



@pytest.mark.case("SEARCH-036")
def test_search_036_find_all_for_a_saved_file_names_its_path_and_a_crlf_file_rep(app, tmp):
    """SEARCH-036: Find All for a saved file names its path, and a CRLF file reports clean lines

    Covers: IDM_SEARCH_FIND
    Channel: ui, files
    Steps: Save "alpha\\r\\nbeta alpha\\r\\n" to tmp/crlf.txt and open it; Find All in Current Document for "alpha".
    Expect: the report's first line is `Search "alpha" in <tmp>/crlf.txt`; hit lines are "\\tLine 1: alpha" and "\\tLine 2: beta alpha" with no "\\r"; last line "2 hits"
    """
    path = tmp / "crlf.txt"
    path.write_bytes(b"alpha\r\nbeta alpha\r\n")
    app.open(path)
    d = fresh_dlg(app)
    d.set("what", "alpha")
    d.press("Find All in Current Document")
    lines = app.text().split("\n")
    assert lines[0].startswith('Search "alpha" in ')
    assert app.same_path(lines[0][len('Search "alpha" in '):], path)
    assert lines[2:4] == ["\tLine 1: alpha", "\tLine 2: beta alpha"]
    assert "\r" not in app.text()
    assert lines[-2] == "2 hits"



@pytest.mark.case("SEARCH-037")
def test_search_037_find_all_in_all_opened_documents_searches_every_tab(app):
    """SEARCH-037: Find All in All Opened Documents searches every tab

    Covers: IDM_SEARCH_FIND
    Channel: ui, mcp
    Steps: Open three documents: "zqx first\\nzqx again zqx\\n", "second zqx\\n", "nothing\\n" (plus the initial empty new 1); make the second one current; press Find All in All Opened Documents for "zqx".
    Expect: the results text starts `Search "zqx" (4 hits in 2 files of 4 searched)`; it contains "(3 hits)\\n\\tLine 1: zqx first\\n\\tLine 2: zqx again zqx\\n" under the first document's title and "(1 hit)" under the second's; the dialog status (if kept open) reads "4 found in all opened documents"; closing the results tab brings back the second document as it was
    """
    app.new("zqx first\nzqx again zqx\n")
    ta, ia = app.doc()["title"], app.doc()["index"]
    app.new("second zqx\n")
    tb, ib = app.doc()["title"], app.doc()["index"]
    app.new("nothing\n")
    app.select(1, 1, document=ib)
    assert app.doc()["title"] == tb
    d = fresh_dlg(app)
    d.set("what", "zqx")
    d.press("Find All in All Opened Documents")
    text = results_text(app)
    assert text.startswith(f'Search "zqx" (4 hits in 2 files of {len(app.docs())} searched)')
    assert f"{ta} (3 hits)\n\tLine 1: zqx first\n\tLine 2: zqx again zqx\n" in text
    assert f"{tb} (1 hit)\n\tLine 1: second zqx\n" in text
    assert d.status() == "4 found in all opened documents"
    assert app.text(ib) == "second zqx\n" and app.text(ia) == "zqx first\nzqx again zqx\n"



@pytest.mark.case("SEARCH-038")
def test_search_038_find_all_in_all_opened_documents_ignores_in_selection_and_th(app):
    """SEARCH-038: Find All in All Opened Documents ignores In selection and the results tab itself

    Covers: IDM_SEARCH_FIND
    Channel: ui
    Steps: With an earlier results tab open containing "zqx" text, and a small selection ticked In selection in one document, run Find All in All Opened Documents for "zqx" twice.
    Expect: the second report's hit counts equal the first's (the results tab is not searched); every match in every document is counted, not only the selected part
    """
    app.new("zqx zqx\n")
    app.new("zqx\n")
    Dlg(app).reset()
    setsel(app, 0, 3)
    d = open_dlg(app)
    d.box("insel", True)
    d.set("what", "zqx")
    d.press("Find All in All Opened Documents")
    first = results_text(app).split("\n")[0]
    assert "(3 hits in 2 files" in first
    d = open_dlg(app)
    d.set("what", "zqx")
    d.press("Find All in All Opened Documents")
    assert results_text(app).split("\n")[0] == first



@pytest.mark.case("SEARCH-039")
def test_search_039_replace_first_selects_a_match_then_replaces_it_and_moves_on(app):
    """SEARCH-039: Replace first selects a match, then replaces it and moves on

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Document "one one one\\n", caret at 0; Find what "one", Replace with "1"; press Replace four times.
    Expect: after 1: text unchanged, selection 0-3; after 2: "1 one one\\n" with the next "one" selected; after 3: "1 1 one\\n"; after 4: "1 1 1\\n" and status "Replace: no occurrence was found"
    """
    app.new("one one one\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "one")
    d.set("with", "1")
    setsel(app, 0)
    d.press("Replace")
    assert app.text() == "one one one\n" and sel(app) == (0, 3)
    d.press("Replace")
    assert app.text() == "1 one one\n" and sel(app) == (2, 5)
    d.press("Replace")
    assert app.text() == "1 1 one\n" and sel(app) == (4, 7)
    d.press("Replace")
    assert app.text() == "1 1 1\n"
    assert d.status() == "Replace: no occurrence was found"



@pytest.mark.case("SEARCH-040")
def test_search_040_replace_does_not_touch_a_selection_that_is_not_a_match(app):
    """SEARCH-040: Replace does not touch a selection that is not a match

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Document "abc one\\n"; select "abc"; Find what "one", Replace with "X"; press Replace.
    Expect: text unchanged "abc one\\n"; "one" (4-7) is selected
    """
    app.new("abc one\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "one")
    d.set("with", "X")
    setsel(app, 0, 3)
    d.press("Replace")
    assert app.text() == "abc one\n"
    assert sel(app) == (4, 7)



@pytest.mark.case("SEARCH-041")
def test_search_041_replace_all_replaces_every_match_as_one_undo_step(app):
    """SEARCH-041: Replace All replaces every match as one undo step

    Covers: IDM_SEARCH_REPLACE
    Channel: ui, mcp, keys
    Steps: Document "cat dog cat cat\\n"; Replace All "cat" → "bird"; then IDM_EDIT_UNDO once.
    Expect: text "bird dog bird bird\\n"; status "Replace All: 3 occurrences were replaced"; one undo restores "cat dog cat cat\\n"
    """
    app.new("cat dog cat cat\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "cat")
    d.set("with", "bird")
    d.press("Replace All")
    assert app.text() == "bird dog bird bird\n"
    assert d.status() == "Replace All: 3 occurrences were replaced"
    app.run("IDM_EDIT_UNDO")
    assert app.text() == "cat dog cat cat\n"



@pytest.mark.case("SEARCH-042")
def test_search_042_replace_all_status_forms_for_one_and_none(app):
    """SEARCH-042: Replace All status forms for one and none

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Replace All "dog" → "x" in "cat dog\\n"; then Replace All "zzz" → "y".
    Expect: "Replace All: 1 occurrence was replaced"; then "Replace All: 0 occurrences were replaced" and the text unchanged
    """
    app.new("cat dog\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "dog")
    d.set("with", "x")
    d.press("Replace All")
    assert d.status() == "Replace All: 1 occurrence was replaced"
    d.set("what", "zzz")
    d.set("with", "y")
    d.press("Replace All")
    assert d.status() == "Replace All: 0 occurrences were replaced"
    assert app.text() == "cat x\n"



@pytest.mark.case("SEARCH-043")
def test_search_043_replace_all_does_not_re_search_its_own_output(app):
    """SEARCH-043: Replace All does not re-search its own output

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Document "aaa\\n"; Replace All "a" → "aa".
    Expect: text "aaaaaa\\n"; status "Replace All: 3 occurrences were replaced"
    """
    app.new("aaa\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "a")
    d.set("with", "aa")
    d.press("Replace All")
    assert app.text() == "aaaaaa\n"
    assert d.status() == "Replace All: 3 occurrences were replaced"



@pytest.mark.case("SEARCH-044")
def test_search_044_replace_all_in_selection_only_changes_the_selection(app):
    """SEARCH-044: Replace All in selection only changes the selection

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Document "q q q q\\n"; select 0-3; run IDM_SEARCH_REPLACE so the dialog becomes key; tick In selection; set Find what "q", Replace with "Z"; Replace All.
    Expect: text "Z Z q q\\n"; status "Replace All: 2 occurrences were replaced"
    """
    app.new("q q q q\n")
    Dlg(app).reset()
    setsel(app, 0, 3)
    d = open_dlg(app, "IDM_SEARCH_REPLACE")
    d.box("insel", True)
    d.set("what", "q")
    d.set("with", "Z")
    d.press("Replace All")
    assert app.text() == "Z Z q q\n"
    assert d.status() == "Replace All: 2 occurrences were replaced"



@pytest.mark.case("SEARCH-045")
def test_search_045_replace_with_an_empty_replacement_deletes_the_matches(app):
    """SEARCH-045: Replace with an empty replacement deletes the matches

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Document "a-b-c\\n"; Replace with empty; Replace All "-".
    Expect: text "abc\\n"; status "Replace All: 2 occurrences were replaced"
    """
    app.new("a-b-c\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "-")
    d.press("Replace All")
    assert app.text() == "abc\n"
    assert d.status() == "Replace All: 2 occurrences were replaced"



@pytest.mark.case("SEARCH-046")
def test_search_046_extended_replacement_escapes(app):
    """SEARCH-046: Extended replacement escapes

    Covers: IDM_SEARCH_REPLACE
    Channel: ui, mcp
    Steps: Extended mode. For each (document, find, replace, result): ("a,b", ",", "\\\\n", "a\\nb"), ("a,b", ",", "\\\\t", "a\\tb"), ("a,b", ",", "\\\\x41", "aAb"), ("a\\nb", "\\\\n", " ", "a b"), ("a-b", "-", "\\\\0", "a<NUL>b"): Replace All.
    Expect: document text equals the result; the NUL case leaves a 3-character document whose middle character is U+0000
    """
    app.new("x\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set_mode(1)
    for text, what, with_, result in [("a,b", ",", "\\n", "a\nb"), ("a,b", ",", "\\t", "a\tb"),
                                      ("a,b", ",", "\\x41", "aAb"), ("a\nb", "\\n", " ", "a b"),
                                      ("a-b", "-", "\\0", "a\x00b")]:
        app.set_text(text)
        d.set("what", what)
        d.set("with", with_)
        d.press("Replace All")
        assert app.text() == result, (what, with_)



@pytest.mark.case("SEARCH-047")
def test_search_047_normal_mode_replacement_is_literal_text(app):
    """SEARCH-047: Normal-mode replacement is literal text

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Normal mode; document "x\\n"; Replace All "x" → "$1\\\\n\\\\2".
    Expect: text "$1\\\\n\\\\2\\n" exactly (no escapes or groups interpreted)
    """
    app.new("x\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "x")
    d.set("with", "$1\\n\\2")
    d.press("Replace All")
    assert app.text() == "$1\\n\\2\n"



@pytest.mark.case("SEARCH-048")
def test_search_048_regex_back_references_in_n_and_n_form(app):
    """SEARCH-048: Regex back-references in \\n and $n form

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Regex mode. "john smith\\njane doe\\n" with "(\\\\w+) (\\\\w+)" → "\\\\2, \\\\1"; "ab\\n" with "(a)(b)(c)?" → "$2$1$3"; "abcdefghij" with "(a)(b)(c)(d)(e)(f)(g)(h)(i)(j)" → "\\\\10|$10|${1}0".
    Expect: "smith, john\\ndoe, jane\\n" with status "Replace All: 2 occurrences were replaced"; "ba\\n" (an unmatched group adds nothing); "a0|j|a0"
    """
    app.new("x\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set_mode(2)
    app.set_text("john smith\njane doe\n")
    d.set("what", "(\\w+) (\\w+)")
    d.set("with", "\\2, \\1")
    d.press("Replace All")
    assert app.text() == "smith, john\ndoe, jane\n"
    assert d.status() == "Replace All: 2 occurrences were replaced"
    for text, what, with_, result in [("ab\n", "(a)(b)(c)?", "$2$1$3", "ba\n"),
                                      ("abcdefghij", "(a)(b)(c)(d)(e)(f)(g)(h)(i)(j)", "\\10|$10|${1}0", "a0|j|a0")]:
        app.set_text(text)
        d.set("what", what)
        d.set("with", with_)
        d.press("Replace All")
        assert app.text() == result, with_



@pytest.mark.case("SEARCH-049")
def test_search_049_boost_format_features_in_the_replacement(app):
    """SEARCH-049: Boost format features in the replacement

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Regex mode, Match case on. For each (document, pattern, replacement, result): ("xx ab-12 yy", "(?<w>[a-z]+)-(\\\\d+)", "[$+{w}|$2|$&|$$|$`|$']", "xx [ab|12|ab-12|$|xx | yy] yy"), ("a1 b", "([a-z])(\\\\d)?", "(?2<$1$2>:[$1])", "<a1> [b]"), ("q", "q", "\\\\x41\\\\x{263A}\\\\\\\\", "A☺\\\\"), ("x", "x", "\\\\d+", "d+"): Replace All.
    Expect: each document equals its result
    """
    app.new("x\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set_mode(2)
    d.box("case", True)
    for text, what, with_, result in [
            ("xx ab-12 yy", "(?<w>[a-z]+)-(\\d+)", "[$+{w}|$2|$&|$$|$`|$']", "xx [ab|12|ab-12|$|xx | yy] yy"),
            ("a1 b", "([a-z])(\\d)?", "(?2<$1$2>:[$1])", "<a1> [b]"),
            ("q", "q", "\\x41\\x{263A}\\\\", "A☺\\"),
            ("x", "x", "\\d+", "d+")]:
        app.set_text(text)
        d.set("what", what)
        d.set("with", with_)
        d.press("Replace All")
        assert app.text() == result, with_



@pytest.mark.case("SEARCH-050")
def test_search_050_case_changing_escapes_in_a_regex_replacement(app):
    """SEARCH-050: Case-changing escapes in a regex replacement

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Regex mode. "hello world" with "(\\\\w+) (\\\\w+)" → "\\\\U\\\\1\\\\E \\\\2"; "HELLO WORLD" → "\\\\L\\\\1 \\\\2"; "hello world" → "\\\\u\\\\1 \\\\u\\\\2"; "john smith\\n" with "^(\\\\w)" → "\\\\U$1".
    Expect: "HELLO world", "hello world", "Hello World", "John smith\\n"
    """
    app.new("x\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set_mode(2)
    for text, what, with_, result in [("hello world", "(\\w+) (\\w+)", "\\U\\1\\E \\2", "HELLO world"),
                                      ("HELLO WORLD", "(\\w+) (\\w+)", "\\L\\1 \\2", "hello world"),
                                      ("hello world", "(\\w+) (\\w+)", "\\u\\1 \\u\\2", "Hello World"),
                                      ("john smith\n", "^(\\w)", "\\U$1", "John smith\n")]:
        app.set_text(text)
        d.set("what", what)
        d.set("with", with_)
        d.press("Replace All")
        assert app.text() == result, with_



@pytest.mark.case("SEARCH-051")
def test_search_051_a_lookahead_match_survives_replace(app):
    """SEARCH-051: A lookahead match survives Replace

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Regex mode; document "foobar foobaz foobar\\n"; Find what "foo(?=bar)", Replace with "X"; caret at 0; press Replace three times.
    Expect: text "Xbar foobaz Xbar\\n"; the "foo" of "foobaz" is never replaced
    """
    app.new("foobar foobaz foobar\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set_mode(2)
    d.set("what", "foo(?=bar)")
    d.set("with", "X")
    setsel(app, 0)
    for _ in range(3):
        d.press("Replace")
    assert app.text() == "Xbar foobaz Xbar\n"



@pytest.mark.case("SEARCH-052")
def test_search_052_regex_replace_with_matches_newline_joins_lines(app):
    """SEARCH-052: Regex replace with . matches newline joins lines

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Regex mode, document "a\\nb\\n"; Replace All "a.b" → "X" with ". matches newline" off, then on.
    Expect: off: "Replace All: 0 occurrences were replaced", text unchanged; on: text "X\\n", "Replace All: 1 occurrence was replaced"
    """
    app.new("a\nb\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set_mode(2)
    d.set("what", "a.b")
    d.set("with", "X")
    d.press("Replace All")
    assert d.status() == "Replace All: 0 occurrences were replaced" and app.text() == "a\nb\n"
    d.box("dotnl", True)
    d.press("Replace All")
    assert app.text() == "X\n"
    assert d.status() == "Replace All: 1 occurrence was replaced"



@pytest.mark.case("SEARCH-053")
def test_search_053_replace_all_with_an_invalid_regex_changes_nothing_and_says_w(app):
    """SEARCH-053: Replace All with an invalid regex changes nothing and says why

    Covers: IDM_SEARCH_REPLACE
    Channel: ui
    Steps: Regex mode; document "a(b\\n"; Replace All "(" → "x".
    Expect: text unchanged; status reports an invalid regular expression (Notepad++ "Find: Invalid regular expression"; the port says "Replace All: 0 occurrences were replaced": likely defect)
    """
    app.new("a(b\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set_mode(2)
    d.set("what", "(")
    d.set("with", "x")
    d.press("Replace All")
    assert app.text() == "a(b\n"
    assert "Invalid regular expression" in d.status()



@pytest.mark.case("SEARCH-054")
def test_search_054_replace_all_on_a_read_only_document_changes_nothing(app):
    """SEARCH-054: Replace All on a read-only document changes nothing

    Covers: IDM_SEARCH_REPLACE
    Channel: ui, menu
    Steps: Document "cat\\n"; IDM_EDIT_TOGGLEREADONLY on; Replace All "cat" → "dog"; turn read-only off again.
    Expect: text still "cat\\n"; the document is not modified
    """
    app.new("cat\n")
    modified = app.doc()["modified"]
    app.run("IDM_EDIT_TOGGLEREADONLY")
    try:
        d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
        d.set("what", "cat")
        d.set("with", "dog")
        d.press("Replace All")
        assert app.text() == "cat\n"
        assert app.doc()["modified"] == modified
    finally:
        app.run("IDM_EDIT_TOGGLEREADONLY")



@pytest.mark.case("SEARCH-055")
def test_search_055_replace_all_in_all_opened_documents_asks_then_replaces_every(app):
    """SEARCH-055: Replace All in All Opened Documents asks, then replaces everywhere

    Covers: IDM_SEARCH_REPLACE
    Channel: ui, modal
    Steps: Documents "cat dog cat\\n" and "cat\\n"; Replace tab "cat" → "CAT"; queue alert answer 2 (Cancel) and press Replace All in All Opened Documents; then queue 1 and press it again.
    Expect: the alert logged has message "Replace All in All Opened Documents", informative "Are you sure you want to replace all occurrences in all open documents?", buttons Replace, Cancel; after Cancel both texts unchanged; after Replace "CAT dog CAT\\n" and "CAT\\n", status "Replace in Opened Files: 3 occurrences were replaced"
    """
    a = app.new("cat dog cat\n")
    ia = app.doc()["index"]
    app.new("cat\n")
    ib = app.doc()["index"]
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "cat")
    d.set("with", "CAT")
    app.modal_log()
    app.answers(alerts=[2])
    d.press("Replace All in All Opened Documents")
    log = app.modal_log()
    assert len(log) == 1
    assert log[0]["message"] == "Replace All in All Opened Documents"
    assert log[0]["informative"] == "Are you sure you want to replace all occurrences in all open documents?"
    assert log[0]["buttons"] == ["Replace", "Cancel"]
    assert app.text(ia) == "cat dog cat\n" and app.text(ib) == "cat\n"
    app.answers(alerts=[1])
    d.press("Replace All in All Opened Documents")
    assert app.text(ia) == "CAT dog CAT\n" and app.text(ib) == "CAT\n"
    assert d.status() == "Replace in Opened Files: 3 occurrences were replaced"



@pytest.mark.case("SEARCH-056")
def test_search_056_replace_all_in_all_opened_documents_without_the_confirmation(app):
    """SEARCH-056: Replace All in All Opened Documents without the confirmation

    Covers: IDM_SEARCH_REPLACE
    Channel: ui, prefs, modal
    Steps: Set pref confirmReplaceAllOpenDocs false; with two documents containing "a", press Replace All in All Opened Documents "a" → "b"; restore the pref.
    Expect: no alert in the modal log; both documents replaced; status "Replace in Opened Files: 2 occurrences were replaced" (or the count in upstream's form)
    """
    app.new("a\n")
    ia = app.doc()["index"]
    app.new("a\n")
    ib = app.doc()["index"]
    app.set_prefs(confirmReplaceAllOpenDocs=False)
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "a")
    d.set("with", "b")
    app.modal_log()
    d.press("Replace All in All Opened Documents")
    assert app.modal_log() == []
    assert app.text(ia) == "b\n" and app.text(ib) == "b\n"
    assert d.status() == "Replace in Opened Files: 2 occurrences were replaced"



@pytest.mark.case("SEARCH-057")
def test_search_057_replace_history_keeps_the_replacements(app):
    """SEARCH-057: Replace history keeps the replacements

    Covers: IDM_SEARCH_REPLACE
    Channel: ui, prefs
    Steps: Press Replace All with Replace with "r1", then "r2"; read the Replace with combo items and pref replaceHistory; restore it.
    Expect: items start ["r2", "r1"]; replaceHistory matches
    """
    app.new("x\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", "x")
    for r in ["r1", "r2"]:
        d.set("with", r)
        d.press("Replace All")
    assert d.items("with")[:2] == ["r2", "r1"]
    assert app.pref("replaceHistory")[:2] == ["r2", "r1"]



@pytest.mark.case("SEARCH-058")
def test_search_058_find_in_files_over_a_folder_lists_every_hit_with_its_file_an(app, tmp):
    """SEARCH-058: Find in Files over a folder lists every hit with its file and line

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, files
    Steps: tmp tree: a.txt "hello needle\\nplain\\n", b.log "needle again\\r\\nneedle twice\\r\\n", sub/c.txt "needle deep\\n", .hid/d.txt "needle hidden\\n", bin.dat with NUL bytes and "needle". Find in Files tab: Find what "needle", Directory tmp, Filters empty, sub-folders on, hidden off; press Find All; wait for the status to end in "found".
    Expect: status "4 found"; the results tab starts `Search "needle" (<tmp>)`, holds "<tmp>/a.txt (1 hit)\\n\\tLine 1: hello needle", "<tmp>/b.log (2 hits)\\n\\tLine 1: needle again\\n\\tLine 2: needle twice" (no "\\r"), "<tmp>/sub/c.txt (1 hit)"; it does not mention .hid or bin.dat; it ends "4 hits in 3 files"
    """
    make_tree(tmp)
    d = fif_dlg(app, "needle", tmp)
    assert fif_run(d) == "4 found"
    text = results_text(app)
    assert text.startswith(f'Search "needle" ({real(tmp)})')
    assert f"{real(tmp)}/a.txt (1 hit)\n\tLine 1: hello needle" in text
    assert f"{real(tmp)}/b.log (2 hits)\n\tLine 1: needle again\n\tLine 2: needle twice" in text
    assert f"{real(tmp)}/sub/c.txt (1 hit)" in text
    assert "\r" not in text and ".hid" not in text and "bin.dat" not in text
    assert text.rstrip("\n").endswith("4 hits in 3 files")



@pytest.mark.case("SEARCH-059")
def test_search_059_filters_include_and_exclude_files_and_folders(app, tmp):
    """SEARCH-059: Filters include and exclude files and folders

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, files
    Steps: Same tree as SEARCH-058. For each filter: "*.txt", "*.log", "*.txt *.log", "!*.log", "*.* !\\\\sub", "*.TXT": Find All and read the report.
    Expect: "*.txt": a.txt and sub/c.txt only; "*.log": b.log only; both: all three; "!*.log": a.txt and sub/c.txt; "!\\\\sub": a.txt and b.log; "*.TXT": matches case-insensitively (a.txt, sub/c.txt)
    """
    make_tree(tmp)
    d = fif_dlg(app, "needle", tmp)
    for flt, want in [("*.txt", {"a.txt", "sub/c.txt"}), ("*.log", {"b.log"}),
                      ("*.txt *.log", {"a.txt", "b.log", "sub/c.txt"}), ("!*.log", {"a.txt", "sub/c.txt"}),
                      ("*.* !\\sub", {"a.txt", "b.log"}), ("*.TXT", {"a.txt", "sub/c.txt"})]:
        d.set("filters", flt)
        fif_run(d)
        assert set(report_files(app, tmp)) == want, flt



@pytest.mark.case("SEARCH-060")
def test_search_060_in_all_sub_folders_and_in_hidden_folders(app, tmp):
    """SEARCH-060: In all sub-folders and In hidden folders

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, files
    Steps: Same tree. Find All with sub-folders off; then sub-folders on and hidden on.
    Expect: off: only a.txt and b.log files ("3 hits in 2 files"); with hidden: .hid/d.txt appears too ("5 hits in 4 files")
    """
    make_tree(tmp)
    d = fif_dlg(app, "needle", tmp)
    d.box("recursive", False)
    fif_run(d)
    text = newest(results_text(app))
    assert set(report_files(app, tmp)) == {"a.txt", "b.log"}
    assert "3 hits in 2 files" in text
    d = open_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.box("recursive", True)
    d.box("hidden", True)
    fif_run(d)
    assert set(report_files(app, tmp)) == {"a.txt", "b.log", "sub/c.txt", ".hid/d.txt"}
    assert "5 hits in 4 files" in newest(results_text(app))



@pytest.mark.case("SEARCH-061")
def test_search_061_find_in_files_honours_the_mode_and_options(app, tmp):
    """SEARCH-061: Find in Files honours the mode and options

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, files
    Steps: Folder with x.txt "Needle\\nneedle\\nneedles\\n". Find All "needle" with Match case on; then whole word on; then regex "^need.e$" with case off.
    Expect: "2 found" then "1 found" (line 2) then "2 found" (lines 1 and 2)
    """
    (tmp / "x.txt").write_bytes(b"Needle\nneedle\nneedles\n")
    d = fif_dlg(app, "needle", tmp)
    d.box("case", True)
    assert fif_run(d) == "2 found"
    d = open_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.box("word", True)
    assert fif_run(d) == "1 found"
    assert "\tLine 2: needle\n" in newest(results_text(app))
    d = open_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.box("case", False)
    d.box("word", False)
    d.set_mode(2)
    d.set("what", "^need.e$")
    assert fif_run(d) == "2 found"
    text = newest(results_text(app))
    assert "\tLine 1: Needle\n" in text and "\tLine 2: needle\n" in text



@pytest.mark.case("SEARCH-062")
def test_search_062_find_in_files_reads_other_encodings(app, tmp):
    """SEARCH-062: Find in Files reads other encodings

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, files
    Steps: Folder with u16.txt (UTF-16 LE with BOM) "héllo needle\\n", latin.txt (ISO-8859-1 bytes) "caf\\xe9 needle\\n", utf8bom.txt (UTF-8 BOM) "needle\\n"; Find All "needle"; then Find All "café".
    Expect: "3 found" listing all three files; "café" is found in latin.txt ("1 found")
    """
    (tmp / "u16.txt").write_bytes(b"\xff\xfe" + "héllo needle\n".encode("utf-16-le"))
    (tmp / "latin.txt").write_bytes(b"caf\xe9 needle\n")
    (tmp / "utf8bom.txt").write_bytes(b"\xef\xbb\xbfneedle\n")
    d = fif_dlg(app, "needle", tmp)
    assert fif_run(d) == "3 found"
    assert set(report_files(app, tmp)) == {"u16.txt", "latin.txt", "utf8bom.txt"}
    d = open_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.set("what", "café")
    assert fif_run(d) == "1 found"
    assert set(report_files(app, tmp)) == {"latin.txt"}



@pytest.mark.case("SEARCH-063")
def test_search_063_find_in_files_with_no_directory_a_missing_folder_or_an_empty(app, tmp):
    """SEARCH-063: Find in Files with no directory, a missing folder, or an empty term

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui
    Steps: Directory empty → Find All; Directory "/nonexistent/folder" → Find All; Directory tmp with Find what empty → Find All.
    Expect: first: status "Choose a folder first" and no results tab created; second: status "0 found" and a report ending "0 hits in 0 files"; third: no hits, nothing replaced or opened, no crash
    """
    (tmp / "a.txt").write_bytes(b"abc\n")
    d = fresh_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.set("what", "abc")
    d.press("Find All")
    assert d.status() == "Choose a folder first"
    assert not any(app.get("editor", "documents.isSearchResults"))
    d.set("dir", "/nonexistent/folder")
    assert fif_run(d) == "0 found"
    assert newest(results_text(app)).rstrip("\n").endswith("0 hits in 0 files")
    close_results(app)
    d = open_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.set("dir", str(tmp))
    d.set("what", "")
    before = [x["title"] for x in app.docs()]
    d.press("Find All")
    wait_search_done(d)
    assert app.running
    assert d.status() == "0 found"
    assert [x["title"] for x in app.docs()] == before
    assert (tmp / "a.txt").read_bytes() == b"abc\n"
    # ...and the dialog still works: the next search runs
    d.set("what", "abc")
    d.press("Find All")
    app.wait(lambda: d.status() == "1 found", timeout=10, message="the next search")



@pytest.mark.case("SEARCH-064")
def test_search_064_from_doc_and_browse_fill_the_directory(app, tmp):
    """SEARCH-064: From doc and Browse… fill the Directory

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, modal
    Steps: Open tmp/sub/c.txt; on the Find in Files tab click "From doc"; then with an untitled document in front click "From doc"; then queue a panel answer tmp and click "Browse…"; then queue None and click it again.
    Expect: Directory becomes "<tmp>/sub"; the untitled case leaves it and sets status "This document has no folder"; Browse sets Directory to tmp; the cancelled panel leaves Directory at tmp
    """
    make_tree(tmp)
    app.open(tmp / "sub" / "c.txt")
    d = fresh_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.press("From doc")
    assert app.same_path(d.value("dir"), tmp / "sub")
    app.new("untitled\n")
    d = open_dlg(app, "IDM_SEARCH_FINDINFILES")
    kept = d.value("dir")
    d.press("From doc")
    assert d.value("dir") == kept
    assert d.status() == "This document has no folder"
    app.answers(panels=[str(tmp)])
    d.press("Browse…")
    assert app.same_path(d.value("dir"), tmp)
    app.answers(panels=[None])
    d.press("Browse…")
    assert app.same_path(d.value("dir"), tmp)
    log = [e for e in app.modal_log() if e["kind"] == "open"]
    assert len(log) == 2 and log[1]["answered"] == "cancel"



@pytest.mark.case("SEARCH-065")
def test_search_065_the_directory_fills_from_the_active_document_when_asked(app, tmp):
    """SEARCH-065: The Directory fills from the active document when asked

    Covers: IDM_SEARCH_FINDINFILES
    Channel: menu, ui, prefs
    Steps: With pref fillDirectoryFromActiveDocument false and Directory already "/tmp", open tmp/sub/c.txt and run IDM_SEARCH_FINDINFILES; then set the pref true and run it again; restore.
    Expect: first Directory stays "/tmp"; second Directory is "<tmp>/sub"
    """
    make_tree(tmp)
    app.set_prefs(fillDirectoryFromActiveDocument=False)
    d = fresh_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.set("dir", "/tmp")
    d.close()
    app.open(tmp / "sub" / "c.txt")
    d = open_dlg(app, "IDM_SEARCH_FINDINFILES")
    assert d.value("dir") == "/tmp"
    d.close()
    app.set_prefs(fillDirectoryFromActiveDocument=True)
    d = open_dlg(app, "IDM_SEARCH_FINDINFILES")
    assert app.same_path(d.value("dir"), tmp / "sub")



@pytest.mark.case("SEARCH-066")
def test_search_066_filters_and_directory_histories_are_kept(app, tmp):
    """SEARCH-066: Filters and Directory histories are kept

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, prefs
    Steps: Find All with Filters "*.txt" in tmp, then Filters "*.log" in tmp/sub; read the two combos' items and prefs filterHistory, directoryHistory; restore them.
    Expect: Filters items start ["*.log", "*.txt"]; Directory items start ["<tmp>/sub", "<tmp>"]
    """
    make_tree(tmp)
    d = fif_dlg(app, "needle", tmp)
    d.set("filters", "*.txt")
    fif_run(d)
    d = open_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.set("filters", "*.log")
    d.set("dir", str(tmp / "sub"))
    fif_run(d)
    assert d.items("filters")[:2] == ["*.log", "*.txt"]
    assert d.items("dir")[:2] == [str(tmp / "sub"), str(tmp)]
    assert app.pref("filterHistory")[:2] == ["*.log", "*.txt"]
    assert app.pref("directoryHistory")[:2] == [str(tmp / "sub"), str(tmp)]



@pytest.mark.case("SEARCH-067")
def test_search_067_find_in_files_does_not_block_and_can_be_stopped(app, tmp):
    """SEARCH-067: Find in Files does not block and can be stopped

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, files
    Steps: Create 3000 files of 20 KB each containing "needle" once; Find All; while the Stop button is visible click it; wait for the status.
    Expect: while running, Stop is visible, Find All and Replace in Files are disabled and get_document still answers; after Stop the status ends "(stopped)", the report ends " - search stopped", Stop is hidden and the buttons are enabled again
    """
    big_tree(tmp)
    d = fif_dlg(app, "needle", tmp)
    d.press("Find All")
    app.wait(lambda: not d.hidden("findStopButton"), message="Stop shown")
    assert not d.get("findSearchButtons.enabled")[0] or not all(d.get("findSearchButtons.enabled"))
    assert not any(d.get("findSearchButtons.enabled"))
    assert "text" in app.call("get_document")
    assert app.act(d.number, "click", title="Stop", **{"class": "NSButton"})["acted"]
    status = wait_search_done(d)
    assert status.endswith("(stopped)"), status
    assert newest(results_text(app)).rstrip("\n").endswith(" - search stopped")
    assert d.hidden("findStopButton")
    assert all(d.get("findSearchButtons.enabled"))



@pytest.mark.case("SEARCH-068")
def test_search_068_find_in_files_shows_progress_while_it_runs(app, tmp):
    """SEARCH-068: Find in Files shows progress while it runs

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui
    Steps: With the 3000-file tree, press Find All and poll the status line and the results tab.
    Expect: at some point the status reads "<n> files searched, <m> found" with n > 0 before the final "3000 found"; the results tab grows while the search runs
    """
    big_tree(tmp)
    d = fif_dlg(app, "needle", tmp)
    d.press("Find All")
    seen, sizes, gaps = [], [], []
    import re as _re
    last = time.monotonic()
    while True:
        now = time.monotonic()
        gaps.append(now - last)
        last = now
        s = d.status() or ""
        seen.append(s)
        if not d.get("runningSearch") and s.endswith("found") and not _re.match(r"\d+ files? searched", s):
            break
        if results_front(app):
            sizes.append(app.sci(SCI_GETLENGTH))
        app.idle(0.02)
        assert len(seen) < 20000
    assert any(_re.match(r"[1-9]\d* files? searched, \d+ found", s) for s in seen), seen[:20]
    assert seen[-1] == "3000 found"
    assert len(set(sizes)) > 1, "the results tab never grew while the search ran"
    assert max(gaps) < 2, f"the application did not answer for {max(gaps):.1f} s"



@pytest.mark.case("SEARCH-069")
def test_search_069_replace_in_files_asks_first_cancel_leaves_the_files_alone(app, tmp):
    """SEARCH-069: Replace in Files asks first; Cancel leaves the files alone

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, modal, files
    Steps: Tree of SEARCH-058; Find what "needle", Replace with "PIN", Filters empty; queue alert 2; press Replace in Files.
    Expect: an alert "Are you sure?" whose informative text contains "Are you sure you want to replace all occurrences in:", the folder path, "For file type:" and "*.*"; after Cancel every file on disk is byte-identical
    """
    make_tree(tmp)
    before = snapshot_tree(tmp)
    d = fif_dlg(app, "needle", tmp)
    d.set("with", "PIN")
    app.modal_log()
    app.answers(alerts=[2])
    d.press("Replace in Files")
    log = app.modal_log()
    assert len(log) == 1 and log[0]["message"] == "Are you sure?"
    info = log[0]["informative"]
    assert "Are you sure you want to replace all occurrences in:" in info and str(tmp) in info
    assert "For file type:" in info and "*.*" in info
    assert snapshot_tree(tmp) == before



@pytest.mark.case("SEARCH-070")
def test_search_070_replace_in_files_rewrites_matching_files_on_disk(app, tmp):
    """SEARCH-070: Replace in Files rewrites matching files on disk

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, modal, files
    Steps: Same tree; Filters "*.txt"; queue alert 1; press Replace in Files; wait for the status.
    Expect: status "2 replaced in 2 files"; a.txt reads "hello PIN\\nplain\\n", sub/c.txt "PIN deep\\n"; b.log, .hid/d.txt and bin.dat are unchanged; the alert's informative text names "*.txt"
    """
    make_tree(tmp)
    before = snapshot_tree(tmp)
    d = fif_dlg(app, "needle", tmp)
    d.set("with", "PIN")
    d.set("filters", "*.txt")
    app.modal_log()
    app.answers(alerts=[1])
    d.press("Replace in Files")
    assert wait_search_done(d) == "2 replaced in 2 files"
    assert "*.txt" in app.modal_log()[0]["informative"]
    assert (tmp / "a.txt").read_bytes() == b"hello PIN\nplain\n"
    assert (tmp / "sub" / "c.txt").read_bytes() == b"PIN deep\n"
    for f in ["b.log", ".hid/d.txt", "bin.dat"]:
        assert (tmp / f).read_bytes() == before[f], f



@pytest.mark.case("SEARCH-071")
def test_search_071_replace_in_files_keeps_encodings_bom_and_line_endings(app, tmp):
    """SEARCH-071: Replace in Files keeps encodings, BOM and line endings

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, modal, files
    Steps: Folder with u16.txt (UTF-16 LE BOM, CRLF) "one needle\\r\\n", bom.txt (UTF-8 BOM) "needle\\n", latin.txt (Latin-1) "caf\\xe9 needle\\n"; Replace in Files "needle" → "pin" (confirm with 1).
    Expect: u16.txt still starts FF FE and decodes to "one pin\\r\\n"; bom.txt starts EF BB BF and reads "pin\\n"; latin.txt bytes are "caf\\xe9 pin\\n"; status "3 replaced in 3 files"
    """
    (tmp / "u16.txt").write_bytes(b"\xff\xfe" + "one needle\r\n".encode("utf-16-le"))
    (tmp / "bom.txt").write_bytes(b"\xef\xbb\xbfneedle\n")
    (tmp / "latin.txt").write_bytes(b"caf\xe9 needle\n")
    d = fif_dlg(app, "needle", tmp)
    d.set("with", "pin")
    app.answers(alerts=[1])
    d.press("Replace in Files")
    assert wait_search_done(d) == "3 replaced in 3 files"
    u16 = (tmp / "u16.txt").read_bytes()
    assert u16[:2] == b"\xff\xfe" and u16[2:].decode("utf-16-le") == "one pin\r\n"
    assert (tmp / "bom.txt").read_bytes() == b"\xef\xbb\xbfpin\n"
    assert (tmp / "latin.txt").read_bytes() == b"caf\xe9 pin\n"



@pytest.mark.case("SEARCH-072")
def test_search_072_replace_in_files_with_regex_back_references(app, tmp):
    """SEARCH-072: Replace in Files with regex back-references

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, modal, files
    Steps: Folder with names.txt "john smith\\njane doe\\n"; regex "(\\\\w+) (\\\\w+)" → "\\\\2 \\\\1"; Replace in Files (confirm).
    Expect: names.txt reads "smith john\\ndoe jane\\n"; status "2 replaced in 1 file"
    """
    (tmp / "names.txt").write_bytes(b"john smith\njane doe\n")
    d = fif_dlg(app, "(\\w+) (\\w+)", tmp)
    d.set_mode(2)
    d.set("with", "\\2 \\1")
    app.answers(alerts=[1])
    d.press("Replace in Files")
    assert wait_search_done(d) == "2 replaced in 1 file"
    assert (tmp / "names.txt").read_bytes() == b"smith john\ndoe jane\n"



@pytest.mark.case("SEARCH-073")
def test_search_073_replace_in_files_with_no_directory(app):
    """SEARCH-073: Replace in Files with no directory

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, modal
    Steps: Directory empty; press Replace in Files.
    Expect: no alert is shown; status "Choose a folder first"
    """
    app.new("x\n")
    d = fresh_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.set("what", "x")
    d.set("with", "y")
    app.modal_log()
    d.press("Replace in Files")
    assert app.modal_log() == []
    assert d.status() == "Choose a folder first"



@pytest.mark.case("SEARCH-074")
def test_search_074_find_in_projects_searches_the_files_of_the_ticked_project_pa(fresh_app, tmp):
    """SEARCH-074: Find in Projects searches the files of the ticked project panels

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, prefs, files
    Steps: Write tmp/ws.xml, a Notepad++ workspace with project "P" listing tmp/p1.txt ("needle one\\n") and tmp/p2.txt ("none\\n"); set pref projectWorkspaces {"1": "<tmp>/ws.xml"} (or load it into Project Panel 1); open the dialog, select "Find in Projects", Project Panel 1 ticked; Find All "needle".
    Expect: status "1 found"; the results tab starts `Search "needle" (the projects)` and lists "<tmp>/p1.txt (1 hit)\\n\\tLine 1: needle one"; p2.txt is not listed
    """
    app = fresh_app
    write_workspace(tmp)
    app.set_prefs(projectWorkspaces={"1": str(tmp / "ws.xml")})
    d = fresh_dlg(app, tab="Find in Projects")
    assert d.get("projectPanelBoxes.state") == [1, 0, 0]
    d.set("what", "needle")
    assert fif_run(d) == "1 found"
    text = newest(results_text(app))
    assert text.startswith('Search "needle" (the projects)')
    head = [l for l in text.split("\n") if l.endswith("/p1.txt (1 hit)")]
    assert len(head) == 1 and app.same_path(head[0][:-len(" (1 hit)")], tmp / "p1.txt")
    assert head[0] + "\n\tLine 1: needle one\n" in text
    assert "p2.txt" not in text



@pytest.mark.case("SEARCH-075")
def test_search_075_find_in_projects_with_no_files_in_the_ticked_panels(app):
    """SEARCH-075: Find in Projects with no files in the ticked panels

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui
    Steps: No workspace loaded; untick Project Panel 1, tick Project Panel 3; press Find All on the Find in Projects tab.
    Expect: status "The ticked project panels have no files"; no results tab is created
    """
    app.new("x\n")
    d = fresh_dlg(app, tab="Find in Projects")
    tick_project(app, d, 1, False)
    tick_project(app, d, 3, True)
    assert d.get("projectPanelBoxes.state") == [0, 0, 1]
    d.set("what", "x")
    d.press("Find All")
    assert d.status() == "The ticked project panels have no files"
    assert not any(app.get("editor", "documents.isSearchResults"))



@pytest.mark.case("SEARCH-076")
def test_search_076_replace_in_projects_asks_and_rewrites_the_project_files(fresh_app, tmp):
    """SEARCH-076: Replace in Projects asks and rewrites the project files

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, modal, files
    Steps: Workspace of SEARCH-074; Replace with "pin"; queue alert 1; press Replace in Projects; wait for the status.
    Expect: alert "Are you sure?" with informative "Do you want to replace all occurrences in all documents in the selected Project Panel(s)?"; p1.txt reads "pin one\\n"; status "1 replaced in 1 file"; with alert answer 2 instead nothing changes on disk
    """
    app = fresh_app
    write_workspace(tmp)
    app.set_prefs(projectWorkspaces={"1": str(tmp / "ws.xml")})
    d = fresh_dlg(app, tab="Find in Projects")
    d.set("what", "needle")
    d.set("with", "pin")
    app.modal_log()
    app.answers(alerts=[2])
    d.press("Replace in Projects")
    log = app.modal_log()
    assert len(log) == 1 and log[0]["message"] == "Are you sure?"
    assert log[0]["informative"] == "Do you want to replace all occurrences in all documents in the selected Project Panel(s)?"
    assert (tmp / "p1.txt").read_bytes() == b"needle one\n"
    app.answers(alerts=[1])
    d.press("Replace in Projects")
    assert wait_search_done(d) == "1 replaced in 1 file"
    assert (tmp / "p1.txt").read_bytes() == b"pin one\n"
    assert (tmp / "p2.txt").read_bytes() == b"none\n"



@pytest.mark.case("SEARCH-077")
def test_search_077_search_results_window_brings_the_results_tab_to_the_front(app):
    """SEARCH-077: Search Results Window brings the results tab to the front

    Covers: IDM_FOCUS_ON_FOUND_RESULTS
    Channel: menu, mcp
    Steps: Run Find All in Current Document, switch back to the searched document, run IDM_FOCUS_ON_FOUND_RESULTS; then close the results tab and run it again.
    Expect: first: the current tab is "Search results" and its text is the report; second: nothing changes (the current document stays), no new tab is created
    """
    app.new("one\n")
    idx = app.doc()["index"]
    d = fresh_dlg(app)
    d.set("what", "one")
    d.press("Find All in Current Document")
    report = app.text()
    app.select(1, 1, document=idx)
    assert not results_front(app)
    app.run("IDM_FOCUS_ON_FOUND_RESULTS")
    assert results_front(app) and app.text() == report
    assert app.get("editor", "currentDocument.displayName") == "Search results"
    close_results(app)
    app.select(1, 1, document=idx)
    before = titles(app)
    app.run("IDM_FOCUS_ON_FOUND_RESULTS", expect_ran=False)
    assert titles(app) == before
    assert app.doc()["index"] == idx and not results_front(app)



@pytest.mark.case("SEARCH-078")
def test_search_078_only_one_results_tab_reused_by_every_search(app, tmp):
    """SEARCH-078: Only one results tab, reused by every search

    Covers: IDM_SEARCH_FINDINFILES, IDM_FOCUS_ON_FOUND_RESULTS
    Channel: ui, mcp
    Steps: Run Find All in Current Document three times with different terms, and Find in Files once; count tabs titled "Search results" (via tab titles in e2e_ui of the main window or the window list).
    Expect: exactly one "Search results" tab; a user document that happens to be named "Search results" is left alone
    """
    make_tree(tmp)
    app.new("user doc\n", title="Search results")
    app.new("one two three\n")
    idx = app.doc()["index"]
    for term in ["one", "two", "three"]:
        app.select(1, 1, document=idx)
        d = fresh_dlg(app)
        d.set("what", term)
        d.press("Find All in Current Document")
    d = fif_dlg(app, "needle", tmp)
    fif_run(d)
    flags = app.get("editor", "documents.isSearchResults")
    assert sum(1 for f in flags if f) == 1
    user = [x for x in app.docs() if x["title"] == "Search results"]
    assert len(user) == 1 and app.text(user[0]["index"]) == "user doc\n"



@pytest.mark.case("SEARCH-079")
def test_search_079_newer_searches_go_on_top_and_older_ones_fold_away(app):
    """SEARCH-079: Newer searches go on top and older ones fold away

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, mcp
    Steps: Find All "one" then Find All "two" in the same document (purge off); read the results text and e2e_sci SCI_GETFOLDLEVEL / SCI_GETFOLDEXPANDED for the "Search \\"" header lines.
    Expect: the text starts with the "two" search and ends with the "one" search; header lines carry SC_FOLDLEVELHEADERFLAG; file lines are one level deeper, hit lines two; the newest header is expanded, the older one contracted
    """
    app.new("one\ntwo\n")
    idx = app.doc()["index"]
    title = app.doc()["title"]
    app.set_prefs(searchResultsPurge=False)
    for term in ["one", "two"]:
        app.select(1, 1, document=idx)
        d = fresh_dlg(app)
        d.set("what", term)
        d.press("Find All in Current Document")
    text = results_text(app)
    assert text.startswith('Search "two"')
    headers = [i for i, l in enumerate(text.split("\n")) if l.startswith('Search "')]
    assert len(headers) == 2 and text.split("\n")[headers[1]].startswith('Search "one"')
    for h in headers:
        assert app.sci(SCI_GETFOLDLEVEL, h) & SC_FOLDLEVELHEADERFLAG
    lines = text.split("\n")
    base = app.sci(SCI_GETFOLDLEVEL, headers[0]) & SC_FOLDLEVELNUMBERMASK
    for i, l in enumerate(lines[:-1]):
        if l.startswith("\tLine "):
            assert app.sci(SCI_GETFOLDLEVEL, i) & SC_FOLDLEVELNUMBERMASK == base + 2, (i, l)
        elif l.startswith(title + " ("):
            assert app.sci(SCI_GETFOLDLEVEL, i) & SC_FOLDLEVELNUMBERMASK == base + 1, (i, l)
    assert app.sci(SCI_GETFOLDEXPANDED, headers[0]) == 1
    assert app.sci(SCI_GETFOLDEXPANDED, headers[1]) == 0



@pytest.mark.case("SEARCH-080")
def test_search_080_purge_for_every_search_keeps_only_the_newest_search(app):
    """SEARCH-080: Purge for every search keeps only the newest search

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, prefs
    Steps: Set pref searchResultsPurge true; run two Find All searches; restore the pref.
    Expect: the results text contains only the second search
    """
    app.new("one\ntwo\n")
    idx = app.doc()["index"]
    app.set_prefs(searchResultsPurge=True)
    for term in ["one", "two"]:
        app.select(1, 1, document=idx)
        d = fresh_dlg(app)
        d.set("what", term)
        d.press("Find All in Current Document")
    text = results_text(app)
    assert text.startswith('Search "two"') and 'Search "one"' not in text



@pytest.mark.case("SEARCH-081")
def test_search_081_next_and_previous_search_result_step_through_hit_lines(app, tmp):
    """SEARCH-081: Next and Previous Search Result step through hit lines

    Covers: IDM_SEARCH_GOTONEXTFOUND, IDM_SEARCH_GOTOPREVFOUND
    Channel: menu, mcp
    Steps: After the Find in Files of SEARCH-058 (4 hit lines), put the caret on line 1 of the results; run IDM_SEARCH_GOTONEXTFOUND five times, then IDM_SEARCH_GOTOPREVFOUND once.
    Expect: the caret moves to each "\\tLine " line in turn, skipping file headers and blank lines; after the last hit the fifth Next leaves it on the last hit; Previous moves back one hit line; the results tab is in front throughout
    """
    make_tree(tmp)
    fif_run(fif_dlg(app, "needle", tmp))
    assert results_front(app)
    lines = app.text().split("\n")
    hits = [i + 1 for i, l in enumerate(lines) if l.startswith("\tLine ")]
    assert len(hits) == 4
    app.select(1, 1)
    got = []
    for _ in range(5):
        app.run("IDM_SEARCH_GOTONEXTFOUND")
        assert results_front(app)
        got.append(caret_line(app))
    assert got == hits + [hits[-1]]
    app.run("IDM_SEARCH_GOTOPREVFOUND")
    assert results_front(app) and caret_line(app) == hits[-2]



@pytest.mark.case("SEARCH-082")
def test_search_082_next_search_result_with_no_results_does_nothing(app):
    """SEARCH-082: Next Search Result with no results does nothing

    Covers: IDM_SEARCH_GOTONEXTFOUND, IDM_SEARCH_GOTOPREVFOUND
    Channel: menu, mcp
    Steps: With no results tab, in document "abc", run IDM_SEARCH_GOTONEXTFOUND and IDM_SEARCH_GOTOPREVFOUND.
    Expect: the current document, its text and caret are unchanged; no tab is created
    """
    app.new("abc")
    setsel(app, 1)
    idx, before = app.doc()["index"], titles(app)
    for cmd in ["IDM_SEARCH_GOTONEXTFOUND", "IDM_SEARCH_GOTOPREVFOUND"]:
        app.run(cmd, expect_ran=False)
        assert app.doc()["index"] == idx and app.text() == "abc" and sel(app) == (1, 1)
    assert titles(app) == before



@pytest.mark.case("SEARCH-083")
def test_search_083_going_to_a_result_opens_the_file_on_that_line(app, tmp):
    """SEARCH-083: Going to a result opens the file on that line

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, mcp
    Steps: tmp/target.txt "one\\ntwo\\nthree needle\\nfour\\n" not open; Find in Files "needle" in tmp; in the results put the caret on the "\\tLine 3:" line and double-click it (requested hook; until then `invoke("editor", "openSearchResultAtCaret")`).
    Expect: target.txt is opened and current; line 3 is selected whole ("three needle"); a second open of the same result does not open a second tab
    """
    target = tmp / "target.txt"
    target.write_bytes(b"one\ntwo\nthree needle\nfour\n")
    fif_run(fif_dlg(app, "needle", tmp))
    line = results_line(app, "\tLine 3:")
    app.mouse(view="main", point={"line": line, "column": 3}, clicks=2)
    app.wait(lambda: not results_front(app), message="the file opened")
    assert app.same_path(app.doc()["path"], target)
    app.wait(lambda: app.call("get_selection")["text"].rstrip("\n") == "three needle", timeout=3,
             message="line 3 selected")
    n = len(app.docs())
    app.run("IDM_FOCUS_ON_FOUND_RESULTS")
    app.mouse(view="main", point={"line": line, "column": 8}, clicks=2)
    app.wait(lambda: not results_front(app), message="the file again")
    assert len(app.docs()) == n and app.same_path(app.doc()["path"], target)
    app.wait(lambda: app.call("get_selection")["text"].rstrip("\n") == "three needle", timeout=3,
             message="line 3 selected again")



@pytest.mark.case("SEARCH-084")
def test_search_084_going_to_a_result_of_an_untitled_document_selects_that_tab(app):
    """SEARCH-084: Going to a result of an untitled document selects that tab

    Covers: IDM_SEARCH_FIND
    Channel: ui, mcp
    Steps: Untitled "a\\nb needle\\n" plus another tab; Find All in Current Document "needle"; go to the "\\tLine 2:" result (as SEARCH-083).
    Expect: the untitled tab becomes current with line 2 selected
    """
    app.new("a\nb needle\n")
    idx = app.doc()["index"]
    app.new("other\n")
    app.select(1, 1, document=idx)
    d = fresh_dlg(app)
    d.set("what", "needle")
    d.press("Find All in Current Document")
    app.select(1, 1, document=app.docs()[-1]["index"])
    app.run("IDM_FOCUS_ON_FOUND_RESULTS")
    line = results_line(app, "\tLine 2:")
    app.mouse(view="main", point={"line": line, "column": 3}, clicks=2)
    app.wait(lambda: not results_front(app), message="the tab selected")
    assert app.doc()["index"] == idx
    app.wait(lambda: app.call("get_selection")["text"].rstrip("\n") == "b needle", timeout=3,
             message="line 2 selected")
    assert caret_line(app) in (2, 3)



@pytest.mark.case("SEARCH-085")
def test_search_085_a_file_heading_or_the_search_header_goes_to_line_1_the_folde(app, tmp):
    """SEARCH-085: A file heading or the search header goes to line 1, the folder is not a result

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, mcp
    Steps: After Find in Files, go to the result on a file heading line "<path> (1 hit)"; then on the `Search "needle" (<tmp>)` header line; then on the summary line.
    Expect: the heading opens the file with line 1 selected; the header and summary open nothing (no new tab, results tab stays current)
    """
    (tmp / "a.txt").write_bytes(b"x\nneedle\n")
    fif_run(fif_dlg(app, "needle", tmp))
    line = results_line(app, f"{real(tmp)}/a.txt (1 hit)")
    app.mouse(view="main", point={"line": line, "column": 3}, clicks=2)
    app.wait(lambda: not results_front(app), message="the file opened")
    assert app.same_path(app.doc()["path"], tmp / "a.txt") and caret_line(app) == 1
    n = len(app.docs())
    app.run("IDM_FOCUS_ON_FOUND_RESULTS")
    lines = app.text().split("\n")
    summary = [i + 1 for i, l in enumerate(lines) if l.endswith(" files") or l.endswith(" file")][0]
    for line in [1, summary]:
        app.mouse(view="main", point={"line": line, "column": 2}, clicks=2)
        app.idle(0.3)
        assert results_front(app) and len(app.docs()) == n



@pytest.mark.case("SEARCH-086")
def test_search_086_results_tab_menu_copy_lines_and_pathnames(app, tmp):
    """SEARCH-086: Results tab menu: copy lines and pathnames

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, clipboard
    Steps: After Find in Files over a.txt ("alpha one", "alpha two" on lines 1-2), select from the file heading to the second hit in the results; use the results tab's "Copy Selected Line(s)" then "Copy Selected Pathname(s)" (results context menu; requested hook, until then invoke editor resultsCopyLines:/resultsCopyPaths:).
    Expect: clipboard "alpha one\\nalpha two" (without "Line n:"); then "<tmp>/a.txt"
    """
    (tmp / "a.txt").write_bytes(b"alpha one\nalpha two\n")
    fif_run(fif_dlg(app, "alpha", tmp))
    head = results_line(app, f"{real(tmp)}/a.txt (2 hits)")
    app.select(head, 1, head + 2, 5)
    assert app.mouse(view="main", point={"line": head + 1, "column": 3}, button="right",
                     menu_path="Copy Selected Line(s)")["ran"]
    assert app.clipboard() == "alpha one\nalpha two"
    app.select(head, 1, head + 2, 5)
    assert app.mouse(view="main", point={"line": head + 1, "column": 3}, button="right",
                     menu_path="Copy Selected Pathname(s)")["ran"]
    assert app.same_path(app.clipboard(), tmp / "a.txt")



@pytest.mark.case("SEARCH-087")
def test_search_087_results_tab_menu_fold_all_unfold_all_delete_this_search_clea(app):
    """SEARCH-087: Results tab menu: fold all, unfold all, delete this search, clear all

    Covers: IDM_SEARCH_FINDINFILES
    Channel: ui, mcp
    Steps: With two stacked searches: Fold all, Unfold all (read SCI_GETFOLDEXPANDED of both headers); caret in the newer search, Delete This Search; then Clear all.
    Expect: fold all contracts both headers, unfold all expands both; delete leaves exactly the older search's text; clear all leaves an empty results tab that is not modified
    """
    app.new("one\ntwo\n")
    idx = app.doc()["index"]
    app.set_prefs(searchResultsPurge=False)
    for term in ["one", "two"]:
        app.select(1, 1, document=idx)
        d = fresh_dlg(app)
        d.set("what", term)
        d.press("Find All in Current Document")
    app.run("IDM_FOCUS_ON_FOUND_RESULTS")
    text = app.text()
    older = text[text.index('Search "one"'):]
    headers = [i for i, l in enumerate(text.split("\n")) if l.startswith('Search "')]
    ctx = lambda item: app.mouse(view="main", point={"line": 1, "column": 1}, button="right", menu_path=item)
    assert ctx("Fold all")["ran"]
    assert [app.sci(SCI_GETFOLDEXPANDED, h) for h in headers] == [0, 0]
    assert ctx("Unfold all")["ran"]
    assert [app.sci(SCI_GETFOLDEXPANDED, h) for h in headers] == [1, 1]
    app.select(2, 1)
    assert app.mouse(view="main", point={"line": 2, "column": 1}, button="right", menu_path="Delete This Search")["ran"]
    assert app.text() == older
    assert ctx("Clear all")["ran"]
    assert app.text() == "" and results_front(app)
    assert not app.get("editor", "currentDocument.modified")



@pytest.mark.case("SEARCH-088")
def test_search_088_the_results_tab_is_read_only(app):
    """SEARCH-088: The results tab is read-only

    Covers: IDM_FOCUS_ON_FOUND_RESULTS
    Channel: keys, mcp
    Steps: Bring the results tab to the front and type "xyz"; press delete.
    Expect: the results text is unchanged; the tab is not marked modified
    """
    app.new("one\n")
    d = fresh_dlg(app)
    d.set("what", "one")
    d.press("Find All in Current Document")
    app.run("IDM_FOCUS_ON_FOUND_RESULTS")
    before = app.text()
    app.select(1, 1)
    app.type("xyz")
    app.keys("delete")
    assert app.text() == before
    assert not app.get("editor", "currentDocument.modified")



@pytest.mark.case("SEARCH-089")
def test_search_089_mark_all_marks_every_match_with_the_find_mark_style(app):
    """SEARCH-089: Mark All marks every match with the Find Mark style

    Covers: IDM_SEARCH_FIND
    Channel: ui, mcp
    Steps: Document "one two one\\nthree one\\n"; Mark tab, Find what "one", Purge on; press Mark All; read indicator 13 with SCI_INDICATORVALUEAT at each position.
    Expect: status "Mark: 3 matches"; indicator 13 covers exactly 0-3, 8-11, 18-21 and nothing else
    """
    app.new("one two one\nthree one\n")
    d = fresh_dlg(app, tab="Mark")
    d.set("what", "one")
    d.box("purge", True)
    d.press("Mark All")
    assert d.status() == "Mark: 3 matches"
    assert ranges(app, FIND_MARK) == [(0, 3), (8, 11), (18, 21)]



@pytest.mark.case("SEARCH-090")
def test_search_090_mark_all_with_bookmark_line_bookmarks_the_matching_lines(app):
    """SEARCH-090: Mark All with Bookmark line bookmarks the matching lines

    Covers: IDM_SEARCH_FIND
    Channel: ui, mcp
    Steps: Document "a x\\nb\\nc x\\nd x x\\n"; tick Bookmark line and Purge; Mark All "x"; read the `bookmarks` tool.
    Expect: bookmarked lines [1, 3, 4]; status "Mark: 4 matches"
    """
    app.new("a x\nb\nc x\nd x x\n")
    d = fresh_dlg(app, tab="Mark")
    d.box("bookmark", True)
    d.box("purge", True)
    d.set("what", "x")
    d.press("Mark All")
    assert bookmarks(app) == [1, 3, 4]
    assert d.status() == "Mark: 4 matches"



@pytest.mark.case("SEARCH-091")
def test_search_091_without_purge_marks_and_bookmarks_of_earlier_searches_stay(app):
    """SEARCH-091: Without Purge, marks and bookmarks of earlier searches stay

    Covers: IDM_SEARCH_FIND
    Channel: ui, mcp
    Steps: Document "one\\ntwo one\\ntwo\\n"; Purge off, Bookmark line on: Mark All "one", then Mark All "two"; then Purge on and Mark All "two".
    Expect: after the second: indicator 13 covers both "one"s and both "two"s, bookmarks [1, 2, 3]; after the purged one: only the "two"s are marked and bookmarks are [2, 3] (line 1, bookmarked only for "one", loses its bookmark)
    """
    app.new("one\ntwo one\ntwo\n")
    d = fresh_dlg(app, tab="Mark")
    d.box("bookmark", True)
    d.set("what", "one")
    d.press("Mark All")
    d.set("what", "two")
    d.press("Mark All")
    assert ranges(app, FIND_MARK) == [(0, 3), (4, 7), (8, 11), (12, 15)]
    assert bookmarks(app) == [1, 2, 3]
    d.box("purge", True)
    d.press("Mark All")
    assert ranges(app, FIND_MARK) == [(4, 7), (12, 15)]
    assert bookmarks(app) == [2, 3]



@pytest.mark.case("SEARCH-092")
def test_search_092_clear_all_marks_and_copy_marked_text(app):
    """SEARCH-092: Clear all marks and Copy Marked Text

    Covers: IDM_SEARCH_FIND
    Channel: ui, clipboard
    Steps: Mark All "two" in "one two one two\\n"; press Copy Marked Text; press Clear all marks; press Copy Marked Text again.
    Expect: clipboard "two\\ntwo" and status "Marked text copied"; after clearing, status "Marks cleared" and no indicator 13 remains; the last copy leaves the clipboard as it was and says "Nothing is marked"
    """
    app.new("one two one two\n")
    d = fresh_dlg(app, tab="Mark")
    d.set("what", "two")
    d.press("Mark All")
    d.press("Copy Marked Text")
    assert app.clipboard() == "two\ntwo"
    assert d.status() == "Marked text copied"
    d.press("Clear all marks")
    assert d.status() == "Marks cleared"
    assert ranges(app, FIND_MARK) == []
    d.press("Copy Marked Text")
    assert app.clipboard() == "two\ntwo"
    assert d.status() == "Nothing is marked"



@pytest.mark.case("SEARCH-093")
def test_search_093_mark_all_with_regex_and_in_selection(app):
    """SEARCH-093: Mark All with regex and In selection

    Covers: IDM_SEARCH_FIND
    Channel: ui, mcp
    Steps: Document "a1 b22 c333\\n"; regex "\\\\d+" Mark All; then select "b22 " (3-7), bring the dialog back to key with IDM_SEARCH_FIND and the Mark segment, set Find what "\\\\d+" again, tick In selection and Purge, Mark All.
    Expect: "Mark: 3 matches" marking 1-2, 4-6, 8-11; then "Mark: 1 match" marking only 4-6
    """
    app.new("a1 b22 c333\n")
    d = fresh_dlg(app, tab="Mark")
    d.set_mode(2)
    d.set("what", "\\d+")
    d.press("Mark All")
    assert d.status() == "Mark: 3 matches"
    assert ranges(app, FIND_MARK) == [(1, 2), (4, 6), (8, 11)]
    setsel(app, 3, 7)
    d = open_dlg(app)
    d.select_tab("Mark")
    d.set("what", "\\d+")
    d.box("insel", True)
    d.box("purge", True)
    d.press("Mark All")
    assert d.status() == "Mark: 1 match"
    assert ranges(app, FIND_MARK) == [(4, 6)]



@pytest.mark.case("SEARCH-094")
def test_search_094_find_next_and_find_previous_repeat_the_dialog_s_last_search(app):
    """SEARCH-094: Find Next and Find Previous repeat the dialog's last search

    Covers: IDM_SEARCH_FINDNEXT, IDM_SEARCH_FINDPREV
    Channel: menu, keys, mcp
    Steps: Document "x1 x2 x3\\n"; in the dialog Find Next "x" once (selects 0-1) and close it; run IDM_SEARCH_FINDNEXT twice, IDM_SEARCH_FINDPREV once; press cmd+g once.
    Expect: selections 3-4, 6-7, then 3-4 (Previous), then 6-7; the dialog stays closed
    """
    app.new("x1 x2 x3\n")
    setsel(app, 0)
    d = fresh_dlg(app)
    d.set("what", "x")
    d.press("Find Next")
    assert sel(app) == (0, 1)
    d.close()
    got = []
    for cmd in ["IDM_SEARCH_FINDNEXT", "IDM_SEARCH_FINDNEXT", "IDM_SEARCH_FINDPREV"]:
        app.run(cmd)
        got.append(sel(app))
    app.keys("cmd+g")
    got.append(sel(app))
    assert got == [(3, 4), (6, 7), (3, 4), (6, 7)]
    assert not d.visible



@pytest.mark.case("SEARCH-095")
def test_search_095_find_next_previous_ignore_the_dialog_s_backward_box(app):
    """SEARCH-095: Find Next / Previous ignore the dialog's Backward box

    Covers: IDM_SEARCH_FINDNEXT, IDM_SEARCH_FINDPREV
    Channel: menu, ui
    Steps: In the dialog tick Backward direction and Find Next "x" in "x x x\\n" from the end; close it; run IDM_SEARCH_FINDNEXT from caret 0, then IDM_SEARCH_FINDPREV.
    Expect: Find Next moves forward (0-1 then onward), Find Previous backward, whatever the box says
    """
    app.new("x x x\n")
    setsel(app, 5)
    d = fresh_dlg(app)
    d.box("backward", True)
    d.set("what", "x")
    d.press("Find Next")
    assert sel(app) == (4, 5)
    d.close()
    setsel(app, 0)
    app.run("IDM_SEARCH_FINDNEXT")
    assert sel(app) == (0, 1)
    app.run("IDM_SEARCH_FINDNEXT")
    assert sel(app) == (2, 3)
    app.run("IDM_SEARCH_FINDPREV")
    assert sel(app) == (0, 1)



@pytest.mark.case("SEARCH-096")
def test_search_096_find_next_with_nothing_searched_yet_opens_the_dialog(fresh_app):
    """SEARCH-096: Find Next with nothing searched yet opens the dialog

    Covers: IDM_SEARCH_FINDNEXT, IDM_SEARCH_FINDPREV
    Channel: menu, ui
    Steps: (fresh_app) Document "abc"; run IDM_SEARCH_FINDNEXT; close the dialog; run IDM_SEARCH_FINDPREV.
    Expect: each time the dialog opens on the Find tab; the selection is unchanged
    """
    app = fresh_app
    app.new("abc")
    setsel(app, 1)
    d = Dlg(app)
    for cmd in ["IDM_SEARCH_FINDNEXT", "IDM_SEARCH_FINDPREV"]:
        app.run(cmd)
        app.wait(lambda: d.visible, message="the Find dialog")
        assert d.title == "Find" and d.tab_index == 0
        assert sel(app) == (1, 1)
        d.close()
        app.wait(lambda: not d.visible, message="the dialog closed")



@pytest.mark.case("SEARCH-097")
def test_search_097_find_next_without_a_match_leaves_the_selection(app):
    """SEARCH-097: Find Next without a match leaves the selection

    Covers: IDM_SEARCH_FINDNEXT
    Channel: menu, mcp
    Steps: Search "zzz" once in the dialog on "abc" (no match); close; run IDM_SEARCH_FINDNEXT with caret at 1.
    Expect: selection unchanged, document unchanged, no alert
    """
    app.new("abc")
    setsel(app, 0)
    d = fresh_dlg(app)
    d.set("what", "zzz")
    d.press("Find Next")
    d.close()
    setsel(app, 1)
    app.modal_log()
    app.run("IDM_SEARCH_FINDNEXT")
    assert sel(app) == (1, 1) and app.text() == "abc"
    assert [e for e in app.modal_log() if e["kind"] == "alert"] == []



@pytest.mark.case("SEARCH-098")
def test_search_098_select_and_find_next_previous_use_the_selection_and_the_dial(app):
    """SEARCH-098: Select and Find Next / Previous use the selection and the dialog's options

    Covers: IDM_SEARCH_SETANDFINDNEXT, IDM_SEARCH_SETANDFINDPREV
    Channel: menu, ui, mcp
    Steps: Document "Word word Word\\n"; Match case ticked in the dialog; select 0-4 ("Word"); run IDM_SEARCH_SETANDFINDNEXT; then IDM_SEARCH_SETANDFINDPREV.
    Expect: selection 10-14 (the lowercase "word" is skipped); Find what reads "Word" and heads the Find what history; Previous goes back to 0-4
    """
    app.new("Word word Word\n")
    d = fresh_dlg(app)
    d.box("case", True)
    d.close()
    setsel(app, 0, 4)
    app.run("IDM_SEARCH_SETANDFINDNEXT")
    assert sel(app) == (10, 14)
    assert d.value("what") == "Word" and d.items("what")[0] == "Word"
    app.run("IDM_SEARCH_SETANDFINDPREV")
    assert sel(app) == (0, 4)



@pytest.mark.case("SEARCH-099")
def test_search_099_select_and_find_next_takes_the_word_under_the_caret(app):
    """SEARCH-099: Select and Find Next takes the word under the caret

    Covers: IDM_SEARCH_SETANDFINDNEXT
    Channel: menu, mcp
    Steps: Document "foo bar foo\\n"; caret inside the first "foo" (column 2) with nothing selected; run IDM_SEARCH_SETANDFINDNEXT; then at the last "foo" run it again.
    Expect: selection 8-11; then wraps to 0-3 (Wrap around on)
    """
    app.new("foo bar foo\n")
    Dlg(app).reset()
    setsel(app, 1)
    app.run("IDM_SEARCH_SETANDFINDNEXT")
    assert sel(app) == (8, 11)
    app.run("IDM_SEARCH_SETANDFINDNEXT")
    assert sel(app) == (0, 3)



@pytest.mark.case("SEARCH-100")
def test_search_100_select_and_find_next_with_no_word_at_the_caret_does_nothing(app):
    """SEARCH-100: Select and Find Next with no word at the caret does nothing

    Covers: IDM_SEARCH_SETANDFINDNEXT, IDM_SEARCH_SETANDFINDPREV
    Channel: menu, mcp
    Steps: Document "   \\n" with the caret at 1; run both commands.
    Expect: selection and Find what unchanged
    """
    app.new("   \n")
    d = fresh_dlg(app)
    d.set("what", "keep")
    d.close()
    setsel(app, 1)
    for cmd in ["IDM_SEARCH_SETANDFINDNEXT", "IDM_SEARCH_SETANDFINDPREV"]:
        app.run(cmd)
        assert sel(app) == (1, 1)
        assert d.value("what") == "keep"



@pytest.mark.case("SEARCH-101")
def test_search_101_find_next_continues_what_select_and_find_next_started(fresh_app):
    """SEARCH-101: Find Next continues what Select and Find Next started

    Covers: IDM_SEARCH_SETANDFINDNEXT, IDM_SEARCH_FINDNEXT
    Channel: menu, mcp
    Steps: (fresh_app, no dialog search yet) Document "foo a foo b foo\\n"; select the first "foo"; run IDM_SEARCH_SETANDFINDNEXT, then IDM_SEARCH_FINDNEXT.
    Expect: selections 6-9 then 12-15 as in Notepad++ (F3 continues with Find what); the port opens the Find dialog instead: likely defect
    """
    app = fresh_app
    app.new("foo a foo b foo\n")
    setsel(app, 0, 3)
    app.run("IDM_SEARCH_SETANDFINDNEXT")
    assert sel(app) == (6, 9)
    app.run("IDM_SEARCH_FINDNEXT")
    assert sel(app) == (12, 15)
    assert not Dlg(app).visible



@pytest.mark.case("SEARCH-102")
def test_search_102_volatile_find_next_previous_use_the_selection_any_case_wrapp(app):
    """SEARCH-102: Volatile Find Next / Previous use the selection, any case, wrapping

    Covers: IDM_SEARCH_VOLATILE_FINDNEXT, IDM_SEARCH_VOLATILE_FINDPREV
    Channel: menu, ui, mcp
    Steps: With the dialog open, Match case ticked and Find what "untouched"; document "Word word Word\\n"; select 10-14; run IDM_SEARCH_VOLATILE_FINDNEXT; then select 0-4 and run it; then IDM_SEARCH_VOLATILE_FINDPREV.
    Expect: first wraps to 0-4 and the dialog status reads "Find: Reached document end, first occurrence from the top found."; second selects 5-9 (case ignored) with an empty status; Previous selects 0-4; Find what still reads "untouched"
    """
    app.new("Word word Word\n")
    d = fresh_dlg(app)
    d.box("case", True)
    d.set("what", "untouched")
    setsel(app, 10, 14)
    app.run("IDM_SEARCH_VOLATILE_FINDNEXT")
    assert sel(app) == (0, 4)
    assert d.status() == "Find: Reached document end, first occurrence from the top found."
    setsel(app, 0, 4)
    app.run("IDM_SEARCH_VOLATILE_FINDNEXT")
    assert sel(app) == (5, 9) and d.status() == ""
    app.run("IDM_SEARCH_VOLATILE_FINDPREV")
    assert sel(app) == (0, 4)
    assert d.value("what") == "untouched"



@pytest.mark.case("SEARCH-103")
def test_search_103_volatile_find_with_no_selection_does_nothing(app):
    """SEARCH-103: Volatile Find with no selection does nothing

    Covers: IDM_SEARCH_VOLATILE_FINDNEXT, IDM_SEARCH_VOLATILE_FINDPREV
    Channel: menu, mcp
    Steps: Document "foo foo\\n", caret inside the first "foo" with nothing selected; run both commands.
    Expect: the caret and selection are unchanged (the word under the caret is not used)
    """
    app.new("foo foo\n")
    setsel(app, 1)
    for cmd in ["IDM_SEARCH_VOLATILE_FINDNEXT", "IDM_SEARCH_VOLATILE_FINDPREV"]:
        app.run(cmd)
        assert sel(app) == (1, 1)



@pytest.mark.case("SEARCH-104")
def test_search_104_incremental_search_finds_the_typed_term_from_the_caret_wrapp(app):
    """SEARCH-104: Incremental Search finds the typed term from the caret, wrapping

    Covers: IDM_SEARCH_FINDINCREMENT
    Channel: menu, modal, mcp
    Steps: Document "aa bb aa cc aa\\n", caret at 7; queue alert {button 1, field "CC"}; run IDM_SEARCH_FINDINCREMENT; then caret at 13, queue {1, "aa"} and run it.
    Expect: the prompt "Incremental search" was shown; "cc" (9-11) is selected (case ignored); the second selects 0-2 after wrapping
    """
    app.new("aa bb aa cc aa\n")
    setsel(app, 7)
    app.modal_log()
    app.answers(alerts=[{"button": 1, "field": "CC"}])
    app.run("IDM_SEARCH_FINDINCREMENT")
    log = app.modal_log()
    assert [e["message"] for e in log] == ["Incremental search"]
    assert sel(app) == (9, 11)
    setsel(app, 13)
    app.answers(alerts=[{"button": 1, "field": "aa"}])
    app.run("IDM_SEARCH_FINDINCREMENT")
    assert sel(app) == (0, 2)



@pytest.mark.case("SEARCH-105")
def test_search_105_incremental_search_remembers_the_term_and_can_be_cancelled(app):
    """SEARCH-105: Incremental Search remembers the term and can be cancelled

    Covers: IDM_SEARCH_FINDINCREMENT
    Channel: menu, modal, mcp
    Steps: Document "aa bb aa\\n", caret at 0; run IDM_SEARCH_FINDINCREMENT answering {1, "bb"}; then queue alert 2 (Cancel) and run it again with the caret at 0; then queue {1, "zzz"} and run it.
    Expect: the second prompt's field (in the modal log) held "bb"; Cancel leaves the caret at 0 with nothing selected; "zzz" (absent) leaves the selection unchanged
    """
    app.new("aa bb aa\n")
    setsel(app, 0)
    app.answers(alerts=[{"button": 1, "field": "bb"}])
    app.run("IDM_SEARCH_FINDINCREMENT")
    assert sel(app) == (3, 5)
    setsel(app, 0)
    app.modal_log()
    app.answers(alerts=[2])
    app.run("IDM_SEARCH_FINDINCREMENT")
    log = app.modal_log()
    assert log[0]["fields"] == ["bb"] and log[0]["answered"] == "Cancel"
    assert sel(app) == (0, 0)
    app.answers(alerts=[{"button": 1, "field": "zzz"}])
    app.run("IDM_SEARCH_FINDINCREMENT")
    assert sel(app) == (0, 0)



@pytest.mark.case("SEARCH-106")
def test_search_106_mark_marks_every_whole_word_occurrence_with_the_find_mark_st(app):
    """SEARCH-106: Mark... marks every whole-word occurrence with the Find Mark style

    Covers: IDM_SEARCH_MARK
    Channel: menu, ui, mcp
    Steps: Document "foo bar foo foobar Foo\\n"; run IDM_SEARCH_MARK (it opens the Find dialog on its
    Mark tab, upstream's MARK_DLG); Find what "foo", Match whole word only on, Match case off, Purge on;
    press Mark All; read indicator 13.
    Expect: indicator 13 covers 0-3, 8-11 and 19-22 (whole word, any case) but not "foobar"
    """
    app.new("foo bar foo foobar Foo\n")
    app.run("IDM_SEARCH_MARK")
    d = Dlg(app)
    app.wait(lambda: d.visible, timeout=3, message="the Find dialog")
    assert d.tab_index == 4
    d.set("what", "foo")
    d.box("word", True)
    d.box("case", False)
    d.box("purge", True)
    try:
        d.press("Mark All")
        assert ranges(app, FIND_MARK) == [(0, 3), (8, 11), (19, 22)]
    finally:
        d.box("word", False)
        d.box("purge", False)



@pytest.mark.case("SEARCH-107")
def test_search_107_mark_with_a_term_that_is_not_in_the_document_marks_nothing(app):
    """SEARCH-107: Mark... with a term that is not in the document marks nothing

    Covers: IDM_SEARCH_MARK
    Channel: menu, modal, mcp
    Steps: Document "foo bar foo\\n"; queue {1, "zzz"}; run IDM_SEARCH_MARK; read indicator 13.
    Expect: no position carries indicator 13 (the port marks the word at the start of the document, "foo": likely defect)
    """
    app.new("foo bar foo\n")
    app.answers(alerts=[{"button": 1, "field": "zzz"}])
    app.run("IDM_SEARCH_MARK")
    assert ranges(app, FIND_MARK) == []



@pytest.mark.case("SEARCH-108")
def test_search_108_mark_opens_the_find_dialog_on_its_mark_tab_known_gap(app):
    """SEARCH-108: Mark... opens the Find dialog on its Mark tab (known gap)

    Covers: IDM_SEARCH_MARK
    Channel: menu, ui
    Steps: Run IDM_SEARCH_MARK.
    Expect: as in Notepad++ (and README's "Mark"), the dialog opens with the Mark segment selected and title "Mark"; the port shows a one-field prompt instead
    """
    app.new("foo\n")
    app.answers(alerts=[2])
    app.run("IDM_SEARCH_MARK")
    d = Dlg(app)
    app.wait(lambda: d.visible, timeout=3, message="the Find dialog")
    assert d.title == "Mark" and d.tab_index == 4



@pytest.mark.case("SEARCH-109")
@pytest.mark.parametrize("n", STYLES)
def test_search_109_style_all_occurrences_of_token_marks_each_style_s_own_token(app, n):
    """SEARCH-109: Style All Occurrences of Token marks each style's own token

    Covers: IDM_SEARCH_MARKALLEXT1, IDM_SEARCH_MARKALLEXT2, IDM_SEARCH_MARKALLEXT3, IDM_SEARCH_MARKALLEXT4, IDM_SEARCH_MARKALLEXT5
    Channel: menu, mcp
    Steps: For each style n in 1..5: document "foo bar foo foobar Foo\\nbar foo\\n"; select 0-3; run IDM_SEARCH_MARKALLEXTn; then click away (caret to 2:1) and read indicator 7+n.
    Expect: indicator 7+n covers 0-3, 8-11, 19-22, 27-30 (whole word, any case); "foobar" is not styled; no other style's indicator is set (for style 5 the marks must survive the caret move: the port's smart highlighting reuses indicator 12 and wipes them: likely defect)
    """
    app.new("foo bar foo foobar Foo\nbar foo\n")
    setsel(app, 0, 3)
    app.run(f"IDM_SEARCH_MARKALLEXT{n}")
    app.select(2, 1)
    assert ranges(app, 7 + n) == [(0, 3), (8, 11), (19, 22), (27, 30)]
    for other in range(8, 13):
        if other != 7 + n:
            assert ranges(app, other) == [], other



@pytest.mark.case("SEARCH-110")
def test_search_110_style_all_occurrences_uses_the_word_under_the_caret_and_resp(app):
    """SEARCH-110: Style All Occurrences uses the word under the caret and respects its settings

    Covers: IDM_SEARCH_MARKALLEXT1
    Channel: menu, prefs, mcp
    Steps: Caret inside "foo" with no selection, run IDM_SEARCH_MARKALLEXT1; then set markAllCaseSensitive true and run again; then markAllWordOnly false and run again; restore both prefs.
    Expect: 4 styled ranges; then 3 (not "Foo"); then 4 including the "foo" of "foobar" but not "Foo"
    """
    app.new("foo bar foo foobar Foo\nbar foo\n")
    setsel(app, 1)
    app.run("IDM_SEARCH_MARKALLEXT1")
    assert ranges(app, 8) == [(0, 3), (8, 11), (19, 22), (27, 30)]
    app.set_prefs(markAllCaseSensitive=True)
    setsel(app, 1)
    app.run("IDM_SEARCH_MARKALLEXT1")
    assert ranges(app, 8) == [(0, 3), (8, 11), (27, 30)]
    app.set_prefs(markAllWordOnly=False)
    setsel(app, 1)
    app.run("IDM_SEARCH_MARKALLEXT1")
    assert ranges(app, 8) == [(0, 3), (8, 11), (12, 15), (27, 30)]



@pytest.mark.case("SEARCH-111")
def test_search_111_styling_again_replaces_the_style_s_previous_token_styles_coe(app):
    """SEARCH-111: Styling again replaces the style's previous token; styles coexist

    Covers: IDM_SEARCH_MARKALLEXT1, IDM_SEARCH_MARKALLEXT2
    Channel: menu, mcp
    Steps: Style 1 on "foo", then style 1 on "bar", then style 2 on "foo".
    Expect: indicator 8 covers only the "bar"s; indicator 9 covers the "foo"s
    """
    app.new("foo bar foo foobar Foo\nbar foo\n")
    for a, b, cmd in [(0, 3, "IDM_SEARCH_MARKALLEXT1"), (4, 7, "IDM_SEARCH_MARKALLEXT1"), (0, 3, "IDM_SEARCH_MARKALLEXT2")]:
        setsel(app, a, b)
        app.run(cmd)
    assert ranges(app, 8) == [(4, 7), (23, 26)]
    assert ranges(app, 9) == [(0, 3), (8, 11), (19, 22), (27, 30)]



@pytest.mark.case("SEARCH-112")
def test_search_112_style_all_with_nothing_under_the_caret_does_nothing(app):
    """SEARCH-112: Style All with nothing under the caret does nothing

    Covers: IDM_SEARCH_MARKALLEXT1
    Channel: menu, mcp
    Steps: Document "   \\n", caret at 1; run IDM_SEARCH_MARKALLEXT1.
    Expect: no indicator 8 anywhere; document unchanged
    """
    app.new("   \n")
    setsel(app, 1)
    app.run("IDM_SEARCH_MARKALLEXT1")
    assert ranges(app, 8) == [] and app.text() == "   \n"



@pytest.mark.case("SEARCH-113")
@pytest.mark.parametrize("n", STYLES)
def test_search_113_style_one_token_styles_only_the_selection(app, n):
    """SEARCH-113: Style One Token styles only the selection

    Covers: IDM_SEARCH_MARKONEEXT1, IDM_SEARCH_MARKONEEXT2, IDM_SEARCH_MARKONEEXT3, IDM_SEARCH_MARKONEEXT4, IDM_SEARCH_MARKONEEXT5
    Channel: menu, mcp
    Steps: For each style n: document "foo bar foo\\n"; select 4-7 ("bar") and run IDM_SEARCH_MARKONEEXTn; then select 8-11 and run it again; move the caret.
    Expect: indicator 7+n covers 4-7 and 8-11 only (One Token adds, it does not purge); the first "foo" is not styled
    """
    app.new("foo bar foo\n")
    setsel(app, 4, 7)
    app.run(f"IDM_SEARCH_MARKONEEXT{n}")
    setsel(app, 8, 11)
    app.run(f"IDM_SEARCH_MARKONEEXT{n}")
    setsel(app, 0)
    assert ranges(app, 7 + n) == [(4, 7), (8, 11)]



@pytest.mark.case("SEARCH-114")
def test_search_114_style_one_token_without_a_selection_does_nothing(app):
    """SEARCH-114: Style One Token without a selection does nothing

    Covers: IDM_SEARCH_MARKONEEXT1
    Channel: menu, mcp
    Steps: Caret inside "foo" with nothing selected; run IDM_SEARCH_MARKONEEXT1.
    Expect: no indicator 8 anywhere
    """
    app.new("foo bar foo\n")
    setsel(app, 1)
    app.run("IDM_SEARCH_MARKONEEXT1")
    assert ranges(app, 8) == []



@pytest.mark.case("SEARCH-115")
@pytest.mark.parametrize("n", STYLES_PAIRED)
def test_search_115_clear_style_removes_one_style_and_leaves_the_others(app, n):
    """SEARCH-115: Clear Style removes one style and leaves the others

    Covers: IDM_SEARCH_UNMARKALLEXT1, IDM_SEARCH_UNMARKALLEXT2, IDM_SEARCH_UNMARKALLEXT3, IDM_SEARCH_UNMARKALLEXT4, IDM_SEARCH_UNMARKALLEXT5
    Channel: menu, mcp
    Steps: For each n: style "foo" with style n and "bar" with another style m ≠ n (One Token); run IDM_SEARCH_UNMARKALLEXTn.
    Expect: indicator 7+n is gone everywhere; indicator 7+m is untouched
    """
    m = n % 5 + 1
    app.new("foo bar\n")
    setsel(app, 0, 3)
    app.run(f"IDM_SEARCH_MARKONEEXT{n}")
    setsel(app, 4, 7)
    app.run(f"IDM_SEARCH_MARKONEEXT{m}")
    setsel(app, 0)
    assert ranges(app, 7 + n) == [(0, 3)] and ranges(app, 7 + m) == [(4, 7)]
    app.run(f"IDM_SEARCH_UNMARKALLEXT{n}")
    assert ranges(app, 7 + n) == []
    assert ranges(app, 7 + m) == [(4, 7)]



@pytest.mark.case("SEARCH-116")
def test_search_116_clear_all_styles_removes_the_five_styles_and_the_find_mark_s(app):
    """SEARCH-116: Clear all Styles removes the five styles and the Find Mark style

    Covers: IDM_SEARCH_CLEARALLMARKS
    Channel: menu, mcp
    Steps: Style tokens with all five styles and Mark All with the dialog; run IDM_SEARCH_CLEARALLMARKS.
    Expect: indicators 8-13 are clear over the whole document; bookmarks are not touched
    """
    app.new("aa bb cc dd ee ff\n")
    for n, a in zip(range(1, 6), [0, 3, 6, 9, 12]):
        setsel(app, a, a + 2)
        app.run(f"IDM_SEARCH_MARKONEEXT{n}")
    setsel(app, 0)
    d = fresh_dlg(app, tab="Mark")
    d.set("what", "ff")
    d.press("Mark All")
    app.run("IDM_SEARCH_TOGGLE_BOOKMARK")
    assert ranges(app, FIND_MARK) == [(15, 17)]
    app.run("IDM_SEARCH_CLEARALLMARKS")
    for ind in range(8, 14):
        assert ranges(app, ind) == [], ind
    assert bookmarks(app) == [1]



@pytest.mark.case("SEARCH-117")
@pytest.mark.parametrize("n", STYLES)
def test_search_117_jump_down_jump_up_move_between_a_style_s_ranges_and_wrap(app, n):
    """SEARCH-117: Jump Down / Jump Up move between a style's ranges and wrap

    Covers: IDM_SEARCH_GONEXTMARKER1, IDM_SEARCH_GONEXTMARKER2, IDM_SEARCH_GONEXTMARKER3, IDM_SEARCH_GONEXTMARKER4, IDM_SEARCH_GONEXTMARKER5, IDM_SEARCH_GOPREVMARKER1, IDM_SEARCH_GOPREVMARKER2, IDM_SEARCH_GOPREVMARKER3, IDM_SEARCH_GOPREVMARKER4, IDM_SEARCH_GOPREVMARKER5
    Channel: menu, mcp
    Steps: For each n: "foo bar foo foobar Foo\\nbar foo\\n" styled with style n on "foo" (Style All); caret at 1:1 (before, not inside, a selection); run IDM_SEARCH_GONEXTMARKERn four times, then IDM_SEARCH_GOPREVMARKERn twice.
    Expect: Jump Down selects 8-11, 19-22, 27-30, then wraps to 0-3; Jump Up from 0-3 wraps to 27-30, then 19-22
    """
    app.new("foo bar foo foobar Foo\nbar foo\n")
    setsel(app, 0, 3)
    app.run(f"IDM_SEARCH_MARKALLEXT{n}")
    setsel(app, 0)
    got = []
    for _ in range(4):
        app.run(f"IDM_SEARCH_GONEXTMARKER{n}")
        got.append(sel(app))
    assert got == [(8, 11), (19, 22), (27, 30), (0, 3)]
    got = []
    for _ in range(2):
        app.run(f"IDM_SEARCH_GOPREVMARKER{n}")
        got.append(sel(app))
    assert got == [(27, 30), (19, 22)]



@pytest.mark.case("SEARCH-118")
def test_search_118_jump_up_down_on_a_style_with_no_ranges_does_nothing(app):
    """SEARCH-118: Jump Up / Down on a style with no ranges does nothing

    Covers: IDM_SEARCH_GONEXTMARKER3, IDM_SEARCH_GOPREVMARKER3
    Channel: menu, mcp
    Steps: No style 3 anywhere; caret at 5; run both commands.
    Expect: caret and selection unchanged
    """
    app.new("foo bar foo\n")
    setsel(app, 5)
    for cmd in ["IDM_SEARCH_GONEXTMARKER3", "IDM_SEARCH_GOPREVMARKER3"]:
        app.run(cmd)
        assert sel(app) == (5, 5)



@pytest.mark.case("SEARCH-119")
def test_search_119_jump_down_up_over_the_find_mark_style(app):
    """SEARCH-119: Jump Down / Up over the Find Mark style

    Covers: IDM_SEARCH_GONEXTMARKER_DEF, IDM_SEARCH_GOPREVMARKER_DEF
    Channel: menu, ui, mcp
    Steps: Mark All "find" in "find me find\\nfind\\n" (dialog, Mark tab); caret at end; run IDM_SEARCH_GONEXTMARKER_DEF, then IDM_SEARCH_GOPREVMARKER_DEF twice.
    Expect: Jump Down wraps to 0-4; Jump Up wraps to 13-17 then 8-12
    """
    app.new("find me find\nfind\n")
    d = fresh_dlg(app, tab="Mark")
    d.set("what", "find")
    d.press("Mark All")
    setsel(app, 18)
    app.run("IDM_SEARCH_GONEXTMARKER_DEF")
    assert sel(app) == (0, 4)
    app.run("IDM_SEARCH_GOPREVMARKER_DEF")
    assert sel(app) == (13, 17)
    app.run("IDM_SEARCH_GOPREVMARKER_DEF")
    assert sel(app) == (8, 12)



@pytest.mark.case("SEARCH-120")
@pytest.mark.parametrize("n", STYLES)
def test_search_120_copy_styled_text_copies_a_style_s_text_one_range_per_line(app, n):
    """SEARCH-120: Copy Styled Text copies a style's text, one range per line

    Covers: IDM_SEARCH_STYLE1TOCLIP, IDM_SEARCH_STYLE2TOCLIP, IDM_SEARCH_STYLE3TOCLIP, IDM_SEARCH_STYLE4TOCLIP, IDM_SEARCH_STYLE5TOCLIP
    Channel: menu, clipboard
    Steps: For each n: "foo bar foo foobar Foo\\nbar foo\\n", Style All "foo" with style n, move the caret to 2:1 without selecting; run IDM_SEARCH_STYLEnTOCLIP.
    Expect: clipboard "foo\\nfoo\\nFoo\\nfoo"; for style 5 this requires the style to survive the caret move (see SEARCH-109)
    """
    app.new("foo bar foo foobar Foo\nbar foo\n")
    setsel(app, 0, 3)
    app.run(f"IDM_SEARCH_MARKALLEXT{n}")
    app.select(2, 1)
    app.run(f"IDM_SEARCH_STYLE{n}TOCLIP")
    assert app.clipboard() == "foo\nfoo\nFoo\nfoo"



@pytest.mark.case("SEARCH-121")
def test_search_121_copy_styled_text_of_an_unused_style_empties_the_clipboard_te(app):
    """SEARCH-121: Copy Styled Text of an unused style empties the clipboard text

    Covers: IDM_SEARCH_STYLE2TOCLIP
    Channel: menu, clipboard
    Steps: Clipboard "before"; nothing styled with style 2; run IDM_SEARCH_STYLE2TOCLIP.
    Expect: clipboard text is "" (the port writes an empty string)
    """
    app.new("foo\n")
    app.clipboard(set="before")
    app.run("IDM_SEARCH_STYLE2TOCLIP")
    assert app.clipboard() == ""



@pytest.mark.case("SEARCH-122")
def test_search_122_copy_styled_text_all_styles_gathers_the_five_styles_in_order(app):
    """SEARCH-122: Copy Styled Text › All Styles gathers the five styles in order and nothing else

    Covers: IDM_SEARCH_ALLSTYLESTOCLIP
    Channel: menu, clipboard
    Steps: "foo bar baz\\n": Style One Token "baz" with style 3, "foo" with style 1; select "bar" and leave it selected (smart highlighting active); Mark All "bar" with the dialog; run IDM_SEARCH_ALLSTYLESTOCLIP.
    Expect: clipboard "foo\\nbaz" (style 1 before style 3); neither the Find Mark text nor smart-highlighted "bar" is included (the port includes smart highlights through indicator 12: likely defect)
    """
    app.new("foo bar baz\n")
    setsel(app, 8, 11)
    app.run("IDM_SEARCH_MARKONEEXT3")
    setsel(app, 0, 3)
    app.run("IDM_SEARCH_MARKONEEXT1")
    setsel(app, 4, 7)
    d = fresh_dlg(app, tab="Mark")
    d.set("what", "bar")
    d.press("Mark All")
    assert ranges(app, FIND_MARK) == [(4, 7)]
    app.run("IDM_SEARCH_ALLSTYLESTOCLIP")
    assert app.clipboard() == "foo\nbaz"



@pytest.mark.case("SEARCH-123")
def test_search_123_copy_styled_text_find_mark_style_copies_the_marked_text(app):
    """SEARCH-123: Copy Styled Text › Find Mark Style copies the marked text

    Covers: IDM_SEARCH_MARKEDTOCLIP
    Channel: menu, ui, clipboard
    Steps: Mark All "find" in "find me find\\n" with the dialog; run IDM_SEARCH_MARKEDTOCLIP.
    Expect: clipboard "find\\nfind"
    """
    app.new("find me find\n")
    d = fresh_dlg(app, tab="Mark")
    d.set("what", "find")
    d.press("Mark All")
    app.run("IDM_SEARCH_MARKEDTOCLIP")
    assert app.clipboard() == "find\nfind"



@pytest.mark.case("SEARCH-124")
def test_search_124_toggle_bookmark_adds_and_removes_the_caret_line_s_bookmark(app):
    """SEARCH-124: Toggle Bookmark adds and removes the caret line's bookmark

    Covers: IDM_SEARCH_TOGGLE_BOOKMARK
    Channel: menu, mcp
    Steps: "l1\\nl2\\nl3\\nl4\\n"; caret on line 2; run IDM_SEARCH_TOGGLE_BOOKMARK; caret on line 4, run it; run it again on line 4.
    Expect: `bookmarks` lists [2, 4] after the second, [2] after the third; SCI_MARKERGET of line index 1 has bit 1 set
    """
    app.new("l1\nl2\nl3\nl4\n")
    app.select(2)
    app.run("IDM_SEARCH_TOGGLE_BOOKMARK")
    app.select(4)
    app.run("IDM_SEARCH_TOGGLE_BOOKMARK")
    assert bookmarks(app) == [2, 4]
    assert app.sci(SCI_MARKERGET, 1) & (1 << BOOKMARK)
    app.run("IDM_SEARCH_TOGGLE_BOOKMARK")
    assert bookmarks(app) == [2]


@pytest.mark.case("SEARCH-125")
def test_search_125_next_and_previous_bookmark_move_and_wrap(app):
    """SEARCH-125: Next and Previous Bookmark move and wrap

    Covers: IDM_SEARCH_NEXT_BOOKMARK, IDM_SEARCH_PREV_BOOKMARK
    Channel: menu, mcp
    Steps: Bookmarks on lines 2 and 4 of a five-line document; caret line 1: Next three times; then Previous three times.
    Expect: Next: lines 2, 4, 2 (wraps); Previous from 2: 4 (wraps), 2, 4
    """
    app.new("l1\nl2\nl3\nl4\nl5")
    app.call("bookmarks", add=[2, 4])
    app.select(1)
    seen = []
    for _ in range(3):
        app.run("IDM_SEARCH_NEXT_BOOKMARK")
        seen.append(caret_line(app))
    assert seen == [2, 4, 2]
    seen = []
    for _ in range(3):
        app.run("IDM_SEARCH_PREV_BOOKMARK")
        seen.append(caret_line(app))
    assert seen == [4, 2, 4]


@pytest.mark.case("SEARCH-126")
def test_search_126_next_previous_bookmark_with_no_bookmarks_does_nothing(app):
    """SEARCH-126: Next / Previous Bookmark with no bookmarks does nothing

    Covers: IDM_SEARCH_NEXT_BOOKMARK, IDM_SEARCH_PREV_BOOKMARK
    Channel: menu, mcp
    Steps: Caret at line 3 column 2 of a document without bookmarks; run both.
    Expect: caret unchanged
    """
    app.new("l1\nl2\nabc\nl4\n")
    app.select(3, 2)
    before = caret(app)
    app.run("IDM_SEARCH_NEXT_BOOKMARK")
    assert caret(app) == before
    app.run("IDM_SEARCH_PREV_BOOKMARK")
    assert caret(app) == before


@pytest.mark.case("SEARCH-127")
def test_search_127_clear_all_bookmarks_removes_every_bookmark(app):
    """SEARCH-127: Clear All Bookmarks removes every bookmark

    Covers: IDM_SEARCH_CLEAR_BOOKMARKS
    Channel: menu, mcp
    Steps: Bookmarks on lines 1 and 3; run IDM_SEARCH_CLEAR_BOOKMARKS (and look for Search › Bookmark › Clear All Bookmarks with e2e_menu).
    Expect: the menu item exists and runs; `bookmarks` lists []; text unchanged (the port's menus lack the item: run_command answers "Command 43008 is not in this build's menus": defect)
    """
    app.new("l1\nl2\nl3\n")
    app.call("bookmarks", add=[1, 3])
    assert app.menu("IDM_SEARCH_CLEAR_BOOKMARKS")["IDM_SEARCH_CLEAR_BOOKMARKS"], "Search > Bookmark > Clear All Bookmarks is missing"
    app.run("IDM_SEARCH_CLEAR_BOOKMARKS")
    assert bookmarks(app) == []
    assert app.text() == "l1\nl2\nl3\n"


@pytest.mark.case("SEARCH-128")
def test_search_128_copy_bookmarked_lines_copies_each_line_with_its_ending(app, tmp):
    """SEARCH-128: Copy Bookmarked Lines copies each line with its ending

    Covers: IDM_SEARCH_COPYMARKEDLINES
    Channel: menu, clipboard
    Steps: For each document "l1\\nl2\\nl3\\nl4\\n" and CRLF file "l1\\r\\nl2\\r\\nl3\\r\\n": bookmark lines 2 and 4 (2 and 3 for CRLF); run IDM_SEARCH_COPYMARKEDLINES.
    Expect: clipboard "l2\\nl4\\n"; for CRLF "l2\\r\\nl3\\r\\n"; the document is unchanged
    """
    app.new("l1\nl2\nl3\nl4\n")
    app.call("bookmarks", add=[2, 4])
    app.run("IDM_SEARCH_COPYMARKEDLINES")
    assert app.clipboard() == "l2\nl4\n"
    assert app.text() == "l1\nl2\nl3\nl4\n"
    crlf = tmp / "crlf.txt"
    crlf.write_bytes(b"l1\r\nl2\r\nl3\r\n")
    app.open(crlf)
    app.call("bookmarks", add=[2, 3])
    app.run("IDM_SEARCH_COPYMARKEDLINES")
    assert app.clipboard() == "l2\r\nl3\r\n"
    assert app.text() == "l1\r\nl2\r\nl3\r\n"


@pytest.mark.case("SEARCH-129")
def test_search_129_cut_bookmarked_lines_copies_then_removes_them_as_one_undo(app):
    """SEARCH-129: Cut Bookmarked Lines copies then removes them, as one undo

    Covers: IDM_SEARCH_CUTMARKEDLINES
    Channel: menu, clipboard, mcp
    Steps: "keep1\\ndrop1\\nkeep2\\ndrop2\\n", bookmark lines 2 and 4; run IDM_SEARCH_CUTMARKEDLINES; then IDM_EDIT_UNDO.
    Expect: clipboard "drop1\\ndrop2\\n"; text "keep1\\nkeep2\\n"; one undo restores the original text
    """
    app.new("keep1\ndrop1\nkeep2\ndrop2\n")
    app.call("bookmarks", add=[2, 4])
    app.run("IDM_SEARCH_CUTMARKEDLINES")
    assert app.clipboard() == "drop1\ndrop2\n"
    assert app.text() == "keep1\nkeep2\n"
    app.run("IDM_EDIT_UNDO")
    assert app.text() == "keep1\ndrop1\nkeep2\ndrop2\n"


@pytest.mark.case("SEARCH-130")
def test_search_130_remove_bookmarked_lines_and_remove_non_bookmarked_lines(app):
    """SEARCH-130: Remove Bookmarked Lines and Remove Non-Bookmarked Lines

    Covers: IDM_SEARCH_DELETEMARKEDLINES, IDM_SEARCH_DELETEUNMARKEDLINES
    Channel: menu, mcp
    Steps: "keep1\\ndrop1\\nkeep2\\ndrop2\\n" with lines 1 and 3 bookmarked: run IDM_SEARCH_DELETEUNMARKEDLINES; restore the text and bookmarks, run IDM_SEARCH_DELETEMARKEDLINES; also run both on a document with no bookmarks.
    Expect: "keep1\\nkeep2\\n" with bookmarks still on the kept lines; then "drop1\\ndrop2\\n"; without bookmarks, Remove Bookmarked changes nothing and Remove Non-Bookmarked empties the document; the clipboard is untouched
    """
    original = "keep1\ndrop1\nkeep2\ndrop2\n"
    app.clipboard(set="clip")
    app.new(original)
    app.call("bookmarks", add=[1, 3])
    app.run("IDM_SEARCH_DELETEUNMARKEDLINES")
    assert app.text() == "keep1\nkeep2\n"
    assert bookmarks(app) == [1, 2]
    app.new(original)
    app.call("bookmarks", add=[1, 3])
    app.run("IDM_SEARCH_DELETEMARKEDLINES")
    assert app.text() == "drop1\ndrop2\n"
    app.new(original)
    app.run("IDM_SEARCH_DELETEMARKEDLINES")
    assert app.text() == original
    app.run("IDM_SEARCH_DELETEUNMARKEDLINES")
    assert app.text() == ""
    assert app.clipboard() == "clip"


@pytest.mark.case("SEARCH-131")
def test_search_131_paste_to_replace_bookmarked_lines_puts_the_clipboard_into_ea(app):
    """SEARCH-131: Paste to (Replace) Bookmarked Lines puts the clipboard into each

    Covers: IDM_SEARCH_PASTEMARKEDLINES
    Channel: menu, clipboard, mcp
    Steps: "a\\nb\\nc\\n" with lines 1 and 3 bookmarked; clipboard "X\\nY"; run IDM_SEARCH_PASTEMARKEDLINES; then with no bookmarks run it again.
    Expect: text "X\\nY\\nb\\nX\\nY\\n"; with no bookmarks nothing changes
    """
    app.new("a\nb\nc\n")
    app.call("bookmarks", add=[1, 3])
    app.clipboard(set="X\nY")
    app.run("IDM_SEARCH_PASTEMARKEDLINES")
    assert app.text() == "X\nY\nb\nX\nY\n"
    app.call("bookmarks", clear=True)
    app.run("IDM_SEARCH_PASTEMARKEDLINES")
    assert app.text() == "X\nY\nb\nX\nY\n"


@pytest.mark.case("SEARCH-132")
def test_search_132_inverse_bookmarks_flips_every_line(app):
    """SEARCH-132: Inverse Bookmarks flips every line

    Covers: IDM_SEARCH_INVERSEMARKS
    Channel: menu, mcp
    Steps: "l1\\nl2\\nl3\\nl4\\n" (5 lines with the empty last) with bookmarks on 2 and 4; run IDM_SEARCH_INVERSEMARKS twice.
    Expect: after one: [1, 3, 5]; after two: [2, 4]
    """
    app.new("l1\nl2\nl3\nl4\n")
    app.call("bookmarks", add=[2, 4])
    app.run("IDM_SEARCH_INVERSEMARKS")
    assert bookmarks(app) == [1, 3, 5]
    app.run("IDM_SEARCH_INVERSEMARKS")
    assert bookmarks(app) == [2, 4]


@pytest.mark.case("SEARCH-133")
def test_search_133_bookmarks_move_with_their_lines_when_text_is_inserted_above(app):
    """SEARCH-133: Bookmarks move with their lines when text is inserted above

    Covers: IDM_SEARCH_TOGGLE_BOOKMARK
    Channel: menu, keys, mcp
    Steps: Bookmark line 3 of "a\\nb\\nc\\n"; at line 1 type "new\\n".
    Expect: `bookmarks` lists [4]; the bookmarked line's text is still "c"
    """
    app.new("a\nb\nc\n")
    app.call("bookmarks", add=[3])
    app.select(1, 1)
    app.type("new", window="main")
    app.keys("return", window="main")
    app.wait(lambda: app.text().startswith("new\n"), message="the typed line")
    assert bookmarks(app) == [4]
    assert app.text().split("\n")[3] == "c"


@pytest.mark.case("SEARCH-134")
def test_search_134_go_to_moves_the_caret_to_a_line(app):
    """SEARCH-134: Go to... moves the caret to a line

    Covers: IDM_SEARCH_GOTOLINE
    Channel: menu, modal, mcp
    Steps: "abc 123\\nfoo(bar)\\nline3\\n"; queue alert {button 1, field "3"}; run IDM_SEARCH_GOTOLINE.
    Expect: the logged prompt reads "Go to line (1 to 4), or @offset (0 to 23)" with an empty field and buttons OK, Cancel; the caret is at line 3 column 1
    """
    app.new("abc 123\nfoo(bar)\nline3\n")
    go_to(app, "3")
    log = app.modal_log()
    assert [(e["message"], e.get("fields"), e["buttons"]) for e in log] == [
        ("Go to line (1 to 4), or @offset (0 to 23)", [""], ["OK", "Cancel"])]
    assert (caret_line(app), app.sci(SCI_GETCOLUMN, caret(app))) == (3, 0)


@pytest.mark.case("SEARCH-135")
def test_search_135_go_to_an_offset_with(app):
    """SEARCH-135: Go to an offset with @

    Covers: IDM_SEARCH_GOTOLINE
    Channel: menu, modal, mcp
    Steps: Same document; answers {1, "@5"}; then {1, "@0"}; then {1, "@23"}.
    Expect: caret positions 5 (line 1 column 6), 0, 23 (end)
    """
    app.new("abc 123\nfoo(bar)\nline3\n")
    go_to(app, "@5")
    assert caret(app) == 5 and (caret_line(app), app.sci(SCI_GETCOLUMN, caret(app))) == (1, 5)
    go_to(app, "@0")
    assert caret(app) == 0
    go_to(app, "@23")
    assert caret(app) == 23


@pytest.mark.case("SEARCH-136")
def test_search_136_an_offset_inside_a_crlf_pair_or_a_multi_byte_character_is_mo(app, tmp):
    """SEARCH-136: An offset inside a CRLF pair or a multi-byte character is moved to a boundary

    Covers: IDM_SEARCH_GOTOLINE
    Channel: menu, modal, mcp
    Steps: CRLF file "ab\\r\\ncd\\r\\n": go to "@3" (between \\r and \\n); document "é!" : go to "@1" (inside é).
    Expect: first caret at 2 (end of line 1, before \\r); second caret at 0 (never inside the é)
    """
    crlf = tmp / "crlf.txt"
    crlf.write_bytes(b"ab\r\ncd\r\n")
    app.open(crlf)
    # GoToLineDlg (IDOK): posToGoto = POSITIONAFTER(POSITIONBEFORE(offset)) - the boundary after.
    go_to(app, "@3")
    assert caret(app) == 4
    app.new("\u00e9!")
    go_to(app, "@1")
    assert caret(app) == 2


@pytest.mark.case("SEARCH-137")
def test_search_137_a_line_past_the_end_goes_to_the_last_line(app):
    """SEARCH-137: A line past the end goes to the last line

    Covers: IDM_SEARCH_GOTOLINE
    Channel: menu, modal, mcp
    Steps: Four-line document, caret at 1:1; answer {1, "99"}.
    Expect: as Notepad++ (SCI_GOTOLINE clamps): caret on the last line (4); the port beeps and leaves the caret: likely defect
    """
    app.new("l1\nl2\nl3\nl4")
    app.select(1, 1)
    go_to(app, "99")
    assert caret_line(app) == 4


@pytest.mark.case("SEARCH-138")
def test_search_138_go_to_refuses_nonsense_and_can_be_cancelled(app):
    """SEARCH-138: Go to... refuses nonsense and can be cancelled

    Covers: IDM_SEARCH_GOTOLINE
    Channel: menu, modal, mcp
    Steps: Caret at 2:3; answers in turn: 2 (Cancel), {1, ""}, {1, "abc"}, {1, "0"}, {1, "@-1"}, {1, "@9999"}.
    Expect: the caret stays at 2:3 after each; no text changes
    """
    text = "l1\nabcd\nl3\n"
    app.new(text)
    app.select(2, 3)
    before = caret(app)
    for answer in [2, {"button": 1, "field": ""}, {"button": 1, "field": "abc"}, {"button": 1, "field": "0"},
                   {"button": 1, "field": "@-1"}]:
        app.answers(alerts=[answer])
        app.run("IDM_SEARCH_GOTOLINE")
        assert caret(app) == before, answer
        assert app.text() == text
    # An offset past the end is not refused: POSITIONBEFORE/POSITIONAFTER clamp it, so the caret
    # goes to the end, as GoToLineDlg does.
    app.answers(alerts=[{"button": 1, "field": "@9999"}])
    app.run("IDM_SEARCH_GOTOLINE")
    assert caret(app) == len(text.encode()) and app.text() == text


@pytest.mark.case("SEARCH-139")
def test_search_139_go_to_matching_brace_jumps_between_brace_pairs(app):
    """SEARCH-139: Go to Matching Brace jumps between brace pairs

    Covers: IDM_SEARCH_GOTOMATCHINGBRACE
    Channel: menu, keys, mcp
    Steps: "f(a[1], {b})\\n": caret before "(" (1) → run; run again; caret after "]" (6) → run; caret before "{" → press cmd+m.
    Expect: caret 11 (at ")"), then back to 1; from after "]" to 3 ("["); from "{" to 10 ("}")
    """
    app.new("f(a[1], {b})\n")
    app.sci(SCI_GOTOPOS, 1)
    app.run("IDM_SEARCH_GOTOMATCHINGBRACE")
    assert caret(app) == 11
    app.run("IDM_SEARCH_GOTOMATCHINGBRACE")
    assert caret(app) == 1
    app.sci(SCI_GOTOPOS, 6)
    app.run("IDM_SEARCH_GOTOMATCHINGBRACE")
    assert caret(app) == 3
    app.sci(SCI_GOTOPOS, 8)
    app.keys("cmd+m", window="main")
    assert caret(app) == 10


@pytest.mark.case("SEARCH-140")
def test_search_140_go_to_matching_brace_off_a_brace_or_with_an_unmatched_brace(app):
    """SEARCH-140: Go to Matching Brace off a brace, or with an unmatched brace, does nothing

    Covers: IDM_SEARCH_GOTOMATCHINGBRACE
    Channel: menu, mcp
    Steps: "f(a\\nxyz\\n": caret at 1 (before the unmatched "("); caret at 5 (inside "xyz").
    Expect: caret unchanged both times
    """
    app.new("f(a\nxyz\n")
    for pos in (1, 5):
        app.sci(SCI_GOTOPOS, pos)
        app.run("IDM_SEARCH_GOTOMATCHINGBRACE")
        assert caret(app) == pos


@pytest.mark.case("SEARCH-141")
def test_search_141_select_all_in_between_selects_the_pair_with_its_braces(app):
    """SEARCH-141: Select All In-between selects the pair with its braces

    Covers: IDM_SEARCH_SELECTMATCHINGBRACES
    Channel: menu, keys, mcp
    Steps: "f(a[1], {b})\\n": caret at 9 (just after "{") run IDM_SEARCH_SELECTMATCHINGBRACES; caret at 1 (before "(") press shift+cmd+m; across lines "{\\n  x\\n}\\n" with caret at 0 run the command.
    Expect: selected text "{b}"; then "(a[1], {b})"; then "{\\n  x\\n}"
    """
    app.new("f(a[1], {b})\n")
    app.sci(SCI_GOTOPOS, 9)
    app.run("IDM_SEARCH_SELECTMATCHINGBRACES")
    assert sel(app) == (8, 11)
    # shift+cmd+m is not pressed: e2e_keys sends charactersIgnoringModifiers without the shift
    # ("m", where AppKit gives "M"), so the chord reaches cmd+m's item (see SEARCH-006); the key
    # equivalent itself is checked there.
    app.sci(SCI_GOTOPOS, 1)
    app.run("IDM_SEARCH_SELECTMATCHINGBRACES")
    assert sel(app) == (1, 12)
    app.new("{\n  x\n}\n")
    app.sci(SCI_GOTOPOS, 0)
    app.run("IDM_SEARCH_SELECTMATCHINGBRACES")
    assert sel(app) == (0, 7)


@pytest.mark.case("SEARCH-142")
def test_search_142_select_all_in_between_without_a_brace_does_nothing(app):
    """SEARCH-142: Select All In-between without a brace does nothing

    Covers: IDM_SEARCH_SELECTMATCHINGBRACES
    Channel: menu, mcp
    Steps: "abc\\n", caret at 1.
    Expect: nothing selected; caret at 1
    """
    app.new("abc\n")
    app.sci(SCI_GOTOPOS, 1)
    app.run("IDM_SEARCH_SELECTMATCHINGBRACES")
    assert sel(app) == (1, 1)


@pytest.mark.case("SEARCH-143")
def test_search_143_go_to_next_previous_change_reach_edited_lines(app, tmp):
    """SEARCH-143: Go to Next / Previous Change reach edited lines

    Covers: IDM_SEARCH_CHANGED_NEXT, IDM_SEARCH_CHANGED_PREV
    Channel: menu, keys, mcp
    Steps: Open a saved file "a\\nb\\nc\\nd\\ne\\n"; type "X" at the start of line 3; caret at 1:1, run IDM_SEARCH_CHANGED_NEXT; caret at line 5, run IDM_SEARCH_CHANGED_PREV.
    Expect: both land on line 3 (column 1)
    """
    open_edited(app, tmp, 5, [3])
    app.select(1, 1)
    app.run("IDM_SEARCH_CHANGED_NEXT")
    assert place(app) == (3, 0)
    app.select(5, 1)
    app.run("IDM_SEARCH_CHANGED_PREV")
    assert place(app) == (3, 0)


@pytest.mark.case("SEARCH-144")
def test_search_144_change_navigation_wraps_around(app, tmp):
    """SEARCH-144: Change navigation wraps around

    Covers: IDM_SEARCH_CHANGED_NEXT, IDM_SEARCH_CHANGED_PREV
    Channel: menu, keys, mcp
    Steps: Saved file of 6 lines; edit line 2 only; caret at line 5; run Next; caret at line 1, run Previous.
    Expect: as Notepad++ (changedHistoryGoTo wraps): Next lands on line 2, Previous lands on line 2; the port does not wrap: likely defect
    """
    open_edited(app, tmp, 6, [2])
    app.select(5, 1)
    app.run("IDM_SEARCH_CHANGED_NEXT")
    assert place(app)[0] == 2
    app.select(1, 1)
    app.run("IDM_SEARCH_CHANGED_PREV")
    assert place(app)[0] == 2


@pytest.mark.case("SEARCH-145")
def test_search_145_change_navigation_skips_over_a_block_of_changed_lines(app, tmp):
    """SEARCH-145: Change navigation skips over a block of changed lines

    Covers: IDM_SEARCH_CHANGED_NEXT, IDM_SEARCH_CHANGED_PREV
    Channel: menu, keys, mcp
    Steps: Saved 10-line file; edit lines 2, 3, 4 and 7; caret at line 2; run Next; then Previous from line 7.
    Expect: as Notepad++ (changedHistoryGoTo skips the block the caret is in): Next goes to line 7, not 3; Previous from line 7 goes to line 4; the port steps line by line: likely defect
    """
    open_edited(app, tmp, 10, [2, 3, 4, 7])
    app.select(2, 1)
    app.run("IDM_SEARCH_CHANGED_NEXT")
    assert place(app)[0] == 7
    app.select(7, 1)
    app.run("IDM_SEARCH_CHANGED_PREV")
    assert place(app)[0] == 4


@pytest.mark.case("SEARCH-146")
def test_search_146_saved_changes_are_change_history_stops_too(app, tmp):
    """SEARCH-146: Saved changes are change-history stops too

    Covers: IDM_SEARCH_CHANGED_NEXT
    Channel: menu, keys, files, mcp
    Steps: Open a file, edit line 3, save (IDM_FILE_SAVE), caret at line 1; run IDM_SEARCH_CHANGED_NEXT.
    Expect: as Notepad++ (mask includes SC_MARKNUM_HISTORY_SAVED): the caret moves to line 3; the port ignores saved-change markers: likely defect
    """
    open_edited(app, tmp, 5, [3])
    app.run("IDM_FILE_SAVE")
    app.wait(lambda: not app.doc()["modified"], message="the save")
    app.select(1, 1)
    app.run("IDM_SEARCH_CHANGED_NEXT")
    assert place(app)[0] == 3


@pytest.mark.case("SEARCH-147")
def test_search_147_clear_change_history_removes_the_markers_and_the_stops(app, tmp):
    """SEARCH-147: Clear Change History removes the markers and the stops

    Covers: IDM_SEARCH_CLEAR_CHANGE_HISTORY, IDM_SEARCH_CHANGED_NEXT
    Channel: menu, keys, mcp
    Steps: Edit line 3 of a file; run IDM_SEARCH_CLEAR_CHANGE_HISTORY; caret at 1:1; run IDM_SEARCH_CHANGED_NEXT; read SCI_MARKERGET on line 3.
    Expect: no change-history marker bits on any line; the caret stays at 1:1; the text and its undo history are kept (IDM_EDIT_UNDO still undoes the edit)
    """
    f = open_edited(app, tmp, 5, [3])
    app.run("IDM_SEARCH_CLEAR_CHANGE_HISTORY")
    for line in range(app.sci(SCI_GETLINECOUNT)):
        assert not app.sci(SCI_MARKERGET, line) & HISTORY_MARKERS, line
    app.select(1, 1)
    app.run("IDM_SEARCH_CHANGED_NEXT")
    assert place(app) == (1, 0)
    app.run("IDM_EDIT_UNDO")
    assert app.text() == f.read_text()


@pytest.mark.case("SEARCH-148")
def test_search_148_with_no_changes_change_navigation_does_nothing(app, tmp):
    """SEARCH-148: With no changes, change navigation does nothing

    Covers: IDM_SEARCH_CHANGED_NEXT, IDM_SEARCH_CHANGED_PREV
    Channel: menu, mcp
    Steps: Freshly opened unmodified file; caret at 2:1; run both commands.
    Expect: caret unchanged
    """
    f = tmp / "plain.txt"
    f.write_text("a\nb\nc\n")
    app.open(f)
    app.select(2, 1)
    before = caret(app)
    app.run("IDM_SEARCH_CHANGED_NEXT")
    assert caret(app) == before
    app.run("IDM_SEARCH_CHANGED_PREV")
    assert caret(app) == before


@pytest.mark.case("SEARCH-149")
def test_search_149_find_characters_in_range_marks_the_characters_in_a_code_poin(app):
    """SEARCH-149: Find characters in range marks the characters in a code-point range

    Covers: IDM_SEARCH_FINDCHARINRANGE
    Channel: menu, modal, mcp
    Steps: "ascii é è\\n"; queue alerts {1, "128"}, {1, "255"}, 1; run IDM_SEARCH_FINDCHARINRANGE; read indicator 13.
    Expect: prompts "Mark characters from (decimal code point)" (default 128) and "…to (decimal code point)" (default 65535) were shown, then an alert "2 characters marked"; indicator 13 covers exactly the bytes of "é" and "è"
    """
    app.new("ascii \u00e9 \u00e8\n")
    log = chars_in_range(app, "128", "255")
    assert [(e["message"], e.get("fields")) for e in log] == [
        ("Mark characters from (decimal code point)", ["128"]), ("\u2026to (decimal code point)", ["65535"]),
        ("2 characters marked", None)]
    assert ranges(app, FIND_MARK) == [(6, 8), (9, 11)]


@pytest.mark.case("SEARCH-150")
def test_search_150_find_characters_in_range_counts_by_code_point_after_an_emoji(app):
    """SEARCH-150: Find characters in range counts by code point after an emoji

    Covers: IDM_SEARCH_FINDCHARINRANGE
    Channel: menu, modal, mcp
    Steps: "😀 é\\n"; range 233..233.
    Expect: "1 character marked"; indicator 13 covers bytes 5-7 (the é) and not the emoji's bytes 0-4
    """
    app.new("\U0001F600 \u00e9\n")
    log = chars_in_range(app, "233", "233")
    assert log[-1]["message"] == "1 character marked"
    assert ranges(app, FIND_MARK) == [(5, 7)]


@pytest.mark.case("SEARCH-151")
def test_search_151_find_characters_in_range_reaches_beyond_the_bmp(app):
    """SEARCH-151: Find characters in range reaches beyond the BMP

    Covers: IDM_SEARCH_FINDCHARINRANGE
    Channel: menu, modal, mcp
    Steps: "a 😀 b\\n"; range 128..1114111.
    Expect: "1 character marked" covering the 4 bytes of 😀 (the port casts the bounds to 16 bits, so 1114111 becomes 65535 and the emoji is missed: likely defect)
    """
    app.new("a \U0001F600 b\n")
    log = chars_in_range(app, "128", "1114111")
    assert log[-1]["message"] == "1 character marked"
    assert ranges(app, FIND_MARK) == [(2, 6)]


@pytest.mark.case("SEARCH-152")
def test_search_152_find_characters_in_range_nothing_found_or_cancelled(app):
    """SEARCH-152: Find characters in range: nothing found, or cancelled

    Covers: IDM_SEARCH_FINDCHARINRANGE
    Channel: menu, modal, mcp
    Steps: Pure ASCII "abc\\n" with range 128..65535; then run again answering 2 (Cancel) on the first prompt.
    Expect: "0 characters marked" and no indicator 13; the cancelled run shows only the first prompt and leaves the marks as they were
    """
    app.new("abc\n")
    log = chars_in_range(app, "128", "65535")
    assert log[-1]["message"] == "0 characters marked"
    assert ranges(app, FIND_MARK) == []
    # Cancel on the first prompt: nothing else is asked and marks already made stay.
    app.new("\u00e9 abc\n")
    chars_in_range(app, "128", "65535")
    assert ranges(app, FIND_MARK) == [(0, 2)]
    app.answers(alerts=[2])
    app.run("IDM_SEARCH_FINDCHARINRANGE")
    log = app.modal_log()
    assert [(e["message"], e["answered"]) for e in log] == [("Mark characters from (decimal code point)", "Cancel")]
    assert ranges(app, FIND_MARK) == [(0, 2)]


@pytest.mark.case("SEARCH-153")
def test_search_153_the_search_menu_carries_every_command_enabled(app):
    """SEARCH-153: The Search menu carries every command, enabled

    Covers: IDM_SEARCH_*, IDM_FOCUS_ON_FOUND_RESULTS
    Channel: menu
    Steps: e2e_menu for every Search command id of plan/commands.tsv; e2e_menu tree "Search" depth 3.
    Expect: every id resolves to an enabled item whose title matches commands.tsv (with "…" for "..."), under the submenus Style All Occurrences of Token, Style One Token, Clear Style, Jump Up, Jump Down, Copy Styled Text, Bookmark, Change History; IDM_SEARCH_CLEAR_BOOKMARKS must be among them (see SEARCH-127)
    """
    rows = [line.split("\t") for line in (ROOT / "plan" / "commands.tsv").read_text().splitlines()
            if line.startswith("Search\t")]
    app.new("text\n")
    items = app.menu(*[r[1] for r in rows])
    missing = [cid for _, cid, _ in rows if not items.get(cid)]
    wrong = {cid: (items[cid]["title"], label) for _, cid, label in rows if items.get(cid) and
             items[cid]["title"] != label.split(" \u203a ")[-1].replace("...", "\u2026")}
    disabled = [cid for _, cid, _ in rows if items.get(cid) and not items[cid]["enabled"]]
    tree = app.menu_tree("Search", 3)
    subs = {i["title"] for i in tree if i.get("items") is not None or i.get("submenu")}
    wanted = {"Style All Occurrences of Token", "Style One Token", "Clear Style", "Jump Up", "Jump Down",
              "Copy Styled Text", "Bookmark", "Change History"}
    assert (missing, wrong, disabled, wanted - subs) == ([], {}, [], set())



@pytest.mark.case("SEARCH-154")
def test_search_154_anchors_and_replace_all_on_crlf_text_as_boost_does(app):
    """SEARCH-154: '^', '$', \\s+$ and \\R on CRLF text replace as Boost does

    Covers: IDM_SEARCH_REPLACE, IDM_SEARCH_FIND
    Channel: ui
    Steps: Regular expression mode. Replace All "$" → ";" in "a\\r\\nb\\r\\n"; "^" → ">" in "a\\r\\nb\\r\\n"; "\\s+$" → "" in "a \\r\\nb\\t\\r\\nc"; "\\R" → "|" in "a\\r\\nb\\nc\\rd"; "a*" → "-" in "baac"; then Count "$" in "ab\\r\\ncd\\r\\n".
    Expect: "a;\\r\\nb;\\r\\n;", ">a\\r\\n>b\\r\\n>", "a\\r\\nb\\r\\nc", "a|b|c|d", "-b-c-" (Boost's '^' and '$' never stand between CR and LF, '^' also starts the empty last line, and Replace All takes no empty match right after the previous match: SCFIND_REGEXP_EMPTYMATCH_NOTAFTERMATCH); Count "$" reads "Count: 0 matches" (Count takes no empty match, EMPTYMATCH_NONE)
    """
    app.new("x\n")
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set_mode(2)
    for doc, what, with_, want in [("a\r\nb\r\n", "$", ";", "a;\r\nb;\r\n;"),
                                   ("a\r\nb\r\n", "^", ">", ">a\r\n>b\r\n>"),
                                   ("a \r\nb\t\r\nc", r"\s+$", "", "a\r\nb\r\nc"),
                                   ("a\r\nb\nc\rd", r"\R", "|", "a|b|c|d"),
                                   ("baac", "a*", "-", "-b-c-")]:
        app.set_text(doc)
        d.set("what", what)
        d.set("with", with_)
        d.press("Replace All")
        assert app.text() == want, (doc, what)
    d = fresh_dlg(app)
    d.set_mode(2)
    app.set_text("ab\r\ncd\r\n")
    assert do_count(d, "$") == count_status(0)
