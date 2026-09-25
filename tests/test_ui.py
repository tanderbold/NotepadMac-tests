"""UI: end-to-end tests (plan: plan/UI.md)."""
import os
import subprocess
import xml.etree.ElementTree as ET

import pytest

from harness.sci import *  # noqa: F401,F403
from _util_view import (cut_controls_measured, cleanup, click_tab, current, current_title, dock, flat, fresh_doc, luminance, main_window,
                        only, other_windows, parse_rect, path_field, prefs, region_median_luminance, snap, status,
                        tab_attr, tab_frames, tab_titles, titles, toolbar_items, toolbar_press, ui, view_frame,
                        window_titled, write)


@pytest.fixture(autouse=True)
def _tidy(app_session):
    yield
    cleanup(app_session)


def title(app):
    return main_window(app)["title"]


def support(app):
    return app.home / "Library" / "Application Support" / "NotepadMac"


# ---------------------------------------------------------------- window title

@pytest.mark.case("UI-001")
def test_ui_001_the_title_of_an_unsaved_document_is_its_tab_name(app):
    seen = [title(app)]
    app.run("IDM_FILE_NEW")
    seen.append(title(app))
    app.run("IDM_VIEW_TAB1")
    seen.append(title(app))
    assert seen == ["new 1", "new 2", "new 1"]
    assert not app.get("window", "representedFilename")


@pytest.mark.case("UI-002")
def test_ui_002_the_title_of_a_saved_file_is_its_name_and_folder(app, tmp):
    p = write(tmp / "dir", "a.txt", "a\n")
    app.open(p)
    name, folder = title(app).split(" — ")
    assert name == "a.txt" and app.same_path(folder, tmp / "dir")
    assert app.same_path(app.get("window", "representedFilename"), p)


@pytest.mark.case("UI-003")
def test_ui_003_file_name_only_in_the_title_bar(app, tmp):
    app.open(write(tmp, "a.txt", "a\n"))
    with prefs(app, titleBarFileNameOnly=True):
        only_name = title(app)
    assert only_name == "a.txt"
    assert title(app).startswith("a.txt — ")


@pytest.mark.case("UI-004")
def test_ui_004_the_window_says_when_the_document_has_unsaved_changes(app, tmp):
    only(app, write(tmp, "a.txt", "a\n"))
    seen = [app.get("window", "documentEdited")]
    app.type("x")
    seen.append(app.get("window", "documentEdited"))
    app.run("IDM_FILE_SAVE")
    seen.append(app.get("window", "documentEdited"))
    assert seen == [False, True, False]


@pytest.mark.case("UI-005")
@pytest.mark.restart
def test_ui_005_titleadd_adds_a_suffix_to_the_title(app, tmp):
    p = write(tmp, "a.txt", "a\n")
    try:
        app.start(args=["-titleAdd=Work"])
        app.wait(lambda: title(app) == "new 1 - Work", timeout=5)
        app.open(p)
        assert title(app).startswith("a.txt — ") and title(app).endswith(" - Work")
    finally:
        app.start()


@pytest.mark.case("UI-006")
def test_ui_006_the_title_follows_the_tab_in_front_and_a_rename(app, tmp):
    a, b = write(tmp, "a.txt", "a\n"), write(tmp, "b.txt", "b\n")
    only(app, a, b)
    assert title(app).startswith("b.txt — ")
    app.run("IDM_VIEW_TAB_PREV")
    assert title(app).startswith("a.txt — ")
    app.answers(panels=[str(tmp / "c.txt")])
    app.run("IDM_FILE_SAVEAS")
    app.wait(lambda: title(app).startswith("c.txt — "), timeout=5)


# ---------------------------------------------------------------- tab bar

@pytest.mark.case("UI-007")
def test_ui_007_one_tab_per_document_in_order_with_its_name(app, tmp):
    # a.txt takes the place of the lone clean "new 1" (FILE-007), then New numbers from 1 again.
    app.open(write(tmp, "a.txt", "a\n"))
    app.run("IDM_FILE_NEW")
    app.run("IDM_FILE_NEW")
    app.open(write(tmp, "b.py", "b\n"))
    assert tab_titles(app) == ["a.txt", "new 1", "new 2", "b.py"]
    assert app.get("editor", "tabBar.selectedIndex") == 3
    app.call("close_document", document=1, discard_changes=True)
    assert tab_titles(app) == ["a.txt", "new 2", "b.py"]


@pytest.mark.case("UI-008")
def test_ui_008_the_modified_marker_follows_the_save_point(app, tmp):
    only(app, write(tmp, "a.txt", "a\n"))
    clean = snap(app, tmp / "clean.png")
    app.type("x")
    assert tab_attr(app, "modified") == [True]
    dirty = snap(app, tmp / "dirty.png")
    top = (0, 0, clean.size[0], 56)
    assert list(clean.crop(top).get_flattened_data()) != list(dirty.crop(top).get_flattened_data())
    app.run("IDM_EDIT_UNDO")
    assert tab_attr(app, "modified") == [False]
    app.type("y")
    app.run("IDM_FILE_SAVE")
    assert tab_attr(app, "modified") == [False]


@pytest.mark.case("UI-009")
def test_ui_009_a_new_document_can_be_named_after_its_first_line(app, tmp):
    with prefs(app, untitledFromFirstLine=True):
        fresh_doc(app, "")
        app.type("Shopping list\nmilk")
        first = tab_titles(app)[-1]
        app.new("")
        app.type("x" * 40)
        long = tab_titles(app)[-1]
        app.open(write(tmp, "saved.txt", "Some first line\n"))
        saved = tab_titles(app)[-1]
    assert first == "Shopping list" and long == "x" * 32 and saved == "saved.txt"


@pytest.mark.case("UI-010")
def test_ui_010_tab_labels_are_cut_to_the_length_set(app, tmp):
    only(app, write(tmp, "a_long_file_name.txt", "x\n"))

    def labels():
        bar = next(c for c in ui(app)["controls"] if c["class"] == "NppTabBarView")
        return [t["label"] for t in bar["tabs"]], [t["title"] for t in bar["tabs"]]

    with prefs(app, tabMaxLabelLength=4):
        cut, whole = labels()
        app.set_prefs(tabMaxLabelLength=0)
        full, _ = labels()
    assert cut == ["a_lo\u2026"] and whole == ["a_long_file_name.txt"]
    assert full == ["a_long_file_name.txt"]


@pytest.mark.case("UI-011")
def test_ui_011_a_pinned_tab_shows_the_pin_and_stays_among_the_pinned(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "ABC"])
    click_tab(app, 2, button="right", menu_path="Pin Tab")
    assert tab_titles(app)[0] == "C.txt" and tab_attr(app, "pinned") == [True, False, False]
    item = next(i for _, i in flat(app.call("e2e_menu", context="tab")["tree"]) if i.get("action") == "togglePin:")
    assert item["checked"] or item["title"] == "Unpin Tab"
    app.run("IDM_FILE_CLOSEALL_BUT_PINNED")
    assert tab_titles(app) == ["C.txt"]
    app.call("e2e_menu_invoke", context="tab", path=item["title"])
    assert tab_attr(app, "pinned") == [False]


@pytest.mark.case("UI-012")
def test_ui_012_a_click_on_a_tab_brings_it_to_the_front(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "ABC"])
    click_tab(app, 0)
    assert current_title(app) == "A.txt" and app.get("editor", "tabBar.selectedIndex") == 0


@pytest.mark.case("UI-013")
def test_ui_013_the_close_button_on_a_tab_closes_that_tab(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "ABC"])
    with prefs(app, tabShowCloseButton=False):
        click_tab(app, 0, at="close")
        assert tab_titles(app) == ["A.txt", "B.txt", "C.txt"] and current_title(app) == "A.txt"
    with prefs(app, tabShowCloseButton=True):
        click_tab(app, 0, at="close")
        assert tab_titles(app) == ["B.txt", "C.txt"]
        with prefs(app, tabCloseButtonOnInactive=True):
            click_tab(app, 1)
            click_tab(app, 0, at="close")
            assert tab_titles(app) == ["C.txt"] and current_title(app) == "C.txt"
    assert app.modal_log() == []


@pytest.mark.case("UI-014")
def test_ui_014_double_click_on_a_tab_closes_it_when_preferences_says_so(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "AB"])
    with prefs(app, tabDoubleClickCloses=True):
        click_tab(app, 1, clicks=2)
        assert tab_titles(app) == ["A.txt"]
    app.open(tmp / "B.txt")
    with prefs(app, tabDoubleClickCloses=False):
        click_tab(app, 0, clicks=2)
        assert tab_titles(app) == ["A.txt", "B.txt"] and current_title(app) == "A.txt"


@pytest.mark.case("UI-015")
def test_ui_015_closing_a_modified_tab_from_the_tab_bar_asks_first(app, tmp):
    a, b = write(tmp, "A.txt", "a\n"), write(tmp, "B.txt", "b\n")
    only(app, a, b)
    app.type("x")
    with prefs(app, tabShowCloseButton=True):
        app.answers(alerts=["Cancel"])
        click_tab(app, 1, at="close")
        log = app.modal_log()
        assert log and log[0]["kind"] == "alert"
        assert tab_titles(app) == ["A.txt", "B.txt"] and tab_attr(app, "modified")[1]
        app.answers(alerts=["No"])
        click_tab(app, 1, at="close")
    assert tab_titles(app) == ["A.txt"] and b.read_text() == "b\n"


@pytest.mark.case("UI-016")
def test_ui_016_hiding_the_tab_bar_gives_its_room_to_the_editor(app):
    h = view_frame(app)[3]
    with prefs(app, hideTabBar=True):
        hidden = app.get("editor", "tabBar.hidden")
        grown = view_frame(app)[3]
    assert hidden and 20 <= grown - h <= 32, (h, grown)
    assert view_frame(app)[3] == h and not app.get("editor", "tabBar.hidden")


@pytest.mark.case("UI-017")
def test_ui_017_vertical_and_multi_line_tab_bars(app, tmp):
    only(app, *[write(tmp, f"file{i:02}.txt", str(i)) for i in range(12)])
    with prefs(app, tabBarVertical=True):
        frames = tab_frames(app)
        vertical = all(f[0] == frames[0][0] for f in frames) and all(b[1] > a[1] for a, b in zip(frames, frames[1:]))
        bar = parse_rect(app.get("editor", "tabBar.frame"))
        editor = view_frame(app, "editorSplit.frame")   # the panes' split, the bar's sibling
    assert vertical and editor[0] >= bar[0] + bar[2] - 1
    before = main_window(app)["frame"]
    try:
        app.act("main", "resize_window", value=[800, 600])
        with prefs(app, tabBarMultiLine=True):
            frames = tab_frames(app)
            rows = {f[1] for f in frames}
            width = parse_rect(app.get("editor", "tabBar.frame"))[2]
        assert len(rows) > 1 and all(f[0] + f[2] <= width + 1 for f in frames)
    finally:
        app.act("main", "resize_window", value=[before[2], before[3] - 22])


TAB_MENU = [
    "Close", ("Close Multiple Tabs", ["Close All BUT This", "Close All BUT Pinned", "Close All to the Left",
                                      "Close All to the Right", "Close All Unchanged"]),
    "Pin Tab", "Save", "Save As...",
    ("Open into", ["Open Containing Folder in Finder", "Open Containing Folder in Terminal",
                   "Open Containing Folder as Workspace", None, "Open in Default Viewer"]),
    "Rename", "Move to Trash", "Reload", "Print", None, "Read-Only in Notepad++", "Read-Only Attribute on Disk", None,
    ("Copy to Clipboard", ["Copy Full File Path", "Copy Filename", "Copy Current Dir. Path"]),
    ("Move Document", ["Move to Start", "Move to End", None, "Move to Other View", "Clone to Other View",
                       "Move to New Instance", "Open in New Instance"]),
    ("Apply Color to Tab", ["Apply Color 1", "Apply Color 2", "Apply Color 3", "Apply Color 4", "Apply Color 5",
                            "Remove Color"]),
]


@pytest.mark.case("UI-018")
def test_ui_018_the_tab_s_right_click_menu_has_notepad_s_items(app, tmp):
    only(app, write(tmp, "a.txt", "a\n"))
    tree = app.call("e2e_menu", context="tab")["tree"]
    got = []
    for i in tree:
        if i.get("separator"):
            got.append(None)
        elif "items" in i:
            got.append((i["title"], titles(i["items"])))
        else:
            got.append(i["title"])
    assert got == TAB_MENU
    # Save is greyed while the document is saved, as the main menu's is (NppNotification: the tab
    # menu's IDM_FILE_SAVE follows the main menu's state); everything else is on for a file on disk.
    assert all(i["enabled"] for _, i in flat(tree) if i.get("title") != "Save")
    save = lambda t: next(i for _, i in flat(t) if i.get("title") == "Save")
    assert not save(tree)["enabled"]
    app.type("x")
    assert save(app.call("e2e_menu", context="tab")["tree"])["enabled"]


TAB_ACTIONS = ["Close", "Close Multiple Tabs|Close All BUT This", "Close Multiple Tabs|Close All to the Left",
               "Close Multiple Tabs|Close All to the Right", "Close Multiple Tabs|Close All Unchanged", "Save",
               "Reload", "Read-Only in Notepad++", "Copy to Clipboard|Copy Full File Path",
               "Copy to Clipboard|Copy Filename", "Copy to Clipboard|Copy Current Dir. Path",
               "Move Document|Move to Start", "Move Document|Move to End", "Move Document|Move to Other View",
               "Move Document|Clone to Other View", "Apply Color to Tab|Apply Color 1",
               "Apply Color to Tab|Remove Color"]


@pytest.mark.case("UI-019")
@pytest.mark.parametrize("path", TAB_ACTIONS)
def test_ui_019_tab_menu_commands_act_on_the_document(app, tmp, path):
    files = [write(tmp, f"{c}.txt", c.lower() + "\n") for c in "ABC"]
    only(app, *files)
    click_tab(app, 1)
    app.type("x")                      # B modified
    app.answers(alerts=[1])
    r = click_tab(app, 1, button="right", menu_path=path)
    assert r.get("menu") is not None or r
    names = tab_titles(app)
    b = files[1]
    if path == "Close":
        assert names == ["A.txt", "C.txt"]
    elif path.endswith("BUT This"):
        assert names == ["B.txt"]
    elif path.endswith("to the Left"):
        assert names == ["B.txt", "C.txt"]
    elif path.endswith("to the Right"):
        assert names == ["A.txt", "B.txt"]
    elif path.endswith("Unchanged"):
        assert names == ["B.txt"]
    elif path == "Save":
        assert b.read_text() == "xb\n"
    elif path == "Reload":
        app.wait(lambda: app.text() == "b\n", timeout=5)
    elif path.startswith("Read-Only"):
        assert app.sci(SCI_GETREADONLY) == 1
        app.run("IDM_EDIT_TOGGLEREADONLY")
    elif path.endswith("Full File Path"):
        assert app.same_path(app.clipboard(), b)
    elif path.endswith("Copy Filename"):
        assert app.clipboard() == "B.txt"
    elif path.endswith("Dir. Path"):
        assert app.same_path(app.clipboard(), tmp)
    elif path.endswith("Move to Start"):
        assert names == ["B.txt", "A.txt", "C.txt"]
    elif path.endswith("Move to End"):
        assert names == ["A.txt", "C.txt", "B.txt"]
    elif path.endswith("Other View"):
        assert app.get("editor", "secondaryViewVisible")
        assert app.sci(SCI_GETTEXT, 0, 0, view="sub", returns="string") == "xb\n"
    elif path.endswith("Apply Color 1"):
        assert tab_attr(app, "colour")[names.index("B.txt")] == 1
    elif path.endswith("Remove Color"):
        assert tab_attr(app, "colour") == [0, 0, 0]


@pytest.mark.case("UI-020")
def test_ui_020_a_tabcontextmenu_xml_of_one_s_own_replaces_the_tab_menu(app, tmp):
    p = write(tmp, "a.txt", "a\n")
    only(app, p)
    f = support(app) / "tabContextMenu.xml"
    f.write_text('<?xml version="1.0" encoding="UTF-8" ?>\n<NotepadPlus>\n<TabContextMenu>\n'
                 '<Item MenuEntryName="File" MenuItemName="Close"/>\n<Item id="0"/>\n'
                 '<Item id="42029" ItemNameAs="Path please"/>\n</TabContextMenu>\n</NotepadPlus>\n')
    try:
        tree = app.call("e2e_menu", context="tab")["tree"]
        # An item named by MenuItemName shows the main menu's name for it (getContextMenuFromXmlTree);
        # the port's File menu calls IDM_FILE_CLOSE "Close Tab".
        assert titles(tree) == ["Close Tab", None, "Path please"]
        app.call("e2e_menu_invoke", context="tab", path="Path please")
        assert app.same_path(app.clipboard(), p)
    finally:
        f.unlink()
    assert titles(app.call("e2e_menu", context="tab")["tree"])[0] == "Close"
    assert len(app.call("e2e_menu", context="tab")["tree"]) > 5


@pytest.mark.case("UI-021")
@pytest.mark.parametrize("mode,dark", [(1, False), (2, True)])
def test_ui_021_tab_bar_colours_in_light_and_dark_appearance(app, tmp, mode, dark):
    fresh_doc(app, "one")
    app.new("two")
    with prefs(app, appearanceMode=mode):
        app.idle(0.3)
        img = snap(app, tmp / "tabs.png")
    scale = img.size[0] / main_window(app)["frame"][2]
    frames = tab_frames(app)
    x, y, w, h = [v * scale for v in frames[1]]
    band = img.crop((int(x), int(y), int(x + w), int(y + h)))
    lums = sorted(luminance(p) for p in band.get_flattened_data())
    bg, ink = lums[len(lums) // 2], (lums[0] if not dark else lums[-1])
    empty = region_median_luminance(img, (int(frames[-1][0] * scale + frames[-1][2] * scale + 20), 2,
                                          img.size[0] - 5, int(h) - 2))
    assert (empty < 0.35) if dark else (empty > 0.65), empty
    assert abs(ink - bg) > 0.3, (ink, bg)


# ---------------------------------------------------------------- toolbar

def _order(app):
    rows = []
    for line in (app.bundle / "Contents/Resources/toolbar/order.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rows.append("NSToolbarSpaceItem" if line == "-" else "npp." + line.split("\t")[0])
    return rows


@pytest.mark.case("UI-022")
def test_ui_022_the_toolbar_has_notepad_s_buttons_in_its_order(app):
    items = toolbar_items(app)
    assert [i["id"] for i in items] == _order(app)
    tips = app.get("window", "toolbar.items.toolTip")
    buttons = [(i["label"], t) for i, t in zip(items, tips) if i["id"] != "NSToolbarSpaceItem"]
    assert all(lbl and lbl == tip for lbl, tip in buttons)
    assert [lbl for lbl, _ in buttons] == [
        "New", "Open", "Save", "Save All", "Close", "Close All", "Print", "Cut", "Copy", "Paste", "Undo", "Redo",
        "Find", "Replace", "Zoom In", "Zoom Out", "Sync Vertical", "Sync Horizontal", "Word Wrap", "All Characters",
        "Indent Guide", "User Language", "Document Map", "Document List", "Function List", "Folder as Workspace",
        "Monitoring", "Start Recording", "Stop Recording", "Play", "Run Multiple", "Save Macro"]


@pytest.mark.case("UI-023")
def test_ui_023_toolbar_buttons_are_enabled_only_when_they_can_act(app, tmp):
    only(app, write(tmp, "a.txt", "hello world\n"))
    app.clipboard(set="")
    app.call("e2e_clipboard", clear=True)
    app.idle(0.2)
    e = {i["label"]: i["enabled"] for i in toolbar_items(app) if i["label"]}
    on = [k for k in ("Save", "Undo", "Redo", "Paste", "Stop Recording", "Play") if e[k]]
    assert not on, on
    # Notepad_plus::checkClipboard leaves Cut and Copy alone while "copy/cut the line without a
    # selection" is on, as it is by default (_lineCopyCutWithoutSelection).
    assert e["Cut"] and e["Copy"], e
    app.type("x")
    app.idle(0.2)
    e = {i["label"]: i["enabled"] for i in toolbar_items(app) if i["label"]}
    assert e["Save"] and e["Undo"]
    app.run("IDM_EDIT_UNDO")
    app.idle(0.2)
    e = {i["label"]: i["enabled"] for i in toolbar_items(app) if i["label"]}
    assert e["Redo"] and not e["Save"]
    app.select(1, 1, 1, 6)
    app.idle(0.2)
    e = {i["label"]: i["enabled"] for i in toolbar_items(app) if i["label"]}
    assert e["Cut"] and e["Copy"]
    app.run("IDM_EDIT_COPY")
    app.idle(0.2)
    assert {i["label"]: i["enabled"] for i in toolbar_items(app)}["Paste"]


def _find_window(app):
    return next((w for w in other_windows(app) if w["class"] != "NSWindow" or "Find" in w["title"] or "Replace" in w["title"]), None)


BUTTONS = ["New", "Open", "Save", "Save All", "Close", "Close All", "Cut", "Copy", "Paste", "Undo", "Redo", "Find",
           "Replace", "User Language", "Sync Vertical", "Sync Horizontal", "Macro"]


@pytest.mark.case("UI-024")
@pytest.mark.parametrize("button", BUTTONS)
def test_ui_024_each_toolbar_button_runs_its_command(app, tmp, button):
    a = write(tmp, "a.txt", "alpha beta\n")
    only(app, a)
    n = len(app.docs())
    if button == "New":
        toolbar_press(app, "New")
        assert len(app.docs()) == n + 1
    elif button == "Open":
        app.answers(panels=[None])
        toolbar_press(app, "Open")
        assert [e for e in app.modal_log() if e.get("kind") != "alert"]
    elif button in ("Save", "Save All"):
        app.type("x")
        toolbar_press(app, button)
        assert a.read_text() == "xalpha beta\n"
    elif button == "Close":
        toolbar_press(app, "Close")
        assert not any(d["title"] == "a.txt" for d in app.docs())
    elif button == "Close All":
        app.new("z")
        app.answers(alerts=["No"])
        toolbar_press(app, "Close All")
        assert [d["title"] for d in app.docs()] == ["new 1"] or len(app.docs()) == 1
    elif button in ("Cut", "Copy"):
        app.select(1, 1, 1, 6)
        toolbar_press(app, button)
        assert app.clipboard() == "alpha"
        assert app.text() == (" beta\n" if button == "Cut" else "alpha beta\n")
    elif button == "Paste":
        app.clipboard(set="P")
        app.select(1, 1)
        toolbar_press(app, "Paste")
        assert app.text() == "Palpha beta\n"
    elif button in ("Undo", "Redo"):
        app.type("q")
        toolbar_press(app, "Undo")
        assert app.text() == "alpha beta\n"
        if button == "Redo":
            toolbar_press(app, "Redo")
            assert app.text() == "qalpha beta\n"
    elif button in ("Find", "Replace", "User Language"):
        toolbar_press(app, button)
        app.wait(lambda: other_windows(app), timeout=5)
        titles_ = [w["title"] for w in other_windows(app)]
        assert titles_, titles_
    elif button in ("Sync Vertical", "Sync Horizontal"):
        key = "syncVerticalScroll" if button == "Sync Vertical" else "syncHorizontalScroll"
        before = app.get("editor", key)
        toolbar_press(app, button)
        assert app.get("editor", key) != before
    elif button == "Macro":
        app.select(1, 1)
        toolbar_press(app, "Start Recording")
        app.type("ab")
        toolbar_press(app, "Stop Recording")
        toolbar_press(app, "Play")
        assert app.text() == "ababalpha beta\n"


@pytest.mark.case("UI-025")
def test_ui_025_start_recording_shows_as_active_while_recording(app):
    fresh_doc(app, "")
    toolbar_press(app, "Start Recording")
    active = "IDM_MACRO_STARTRECORDINGMACRO" in (app.get("app", "toolbar.activeCommands") or [])
    toolbar_press(app, "Stop Recording")
    after = "IDM_MACRO_STARTRECORDINGMACRO" in (app.get("app", "toolbar.activeCommands") or [])
    assert active and not after


@pytest.mark.case("UI-026")
def test_ui_026_the_toolbar_can_be_hidden(app):
    with prefs(app, showToolbar=False):
        hidden = app.get("window", "toolbar.visible")
        fresh_doc(app, "still works")
        assert app.text() == "still works"
    assert hidden is False and app.get("window", "toolbar.visible") is True


@pytest.mark.case("UI-027")
@pytest.mark.parametrize("mode,display,style", [(0, 2, None), (1, 1, 1), (2, 3, 1)])
def test_ui_027_toolbar_buttons_as_icons_icons_and_labels_or_labels(app, mode, display, style):
    with prefs(app, toolbarDisplayMode=mode):
        got = (app.get("window", "toolbar.displayMode"), app.get("window", "toolbarStyle"))
    assert got[0] == display
    if style is not None:
        assert got[1] == style


@pytest.mark.case("UI-028")
@pytest.mark.parametrize("size,style", [(0, 1), (1, 4)])
def test_ui_028_toolbar_size_regular_or_small(app, size, style):
    with prefs(app, toolbarDisplayMode=0, toolbarIconSize=size):
        got = app.get("window", "toolbarStyle")
    assert got == style


def _toolbar_band(app, tmp, name):
    img = snap(app, tmp / name, frame=True)
    scale = img.size[0] / main_window(app)["frame"][2]
    return img.crop((0, 0, img.size[0], int(52 * scale)))


@pytest.mark.case("UI-029")
def test_ui_029_toolbar_icon_set_and_colour(app, tmp):
    base = _toolbar_band(app, tmp, "base.png")
    with prefs(app, toolbarFilledIcons=True):
        filled = _toolbar_band(app, tmp, "filled.png")
    with prefs(app, toolbarIconColour=1, toolbarColorizeComplete=True):
        red = _toolbar_band(app, tmp, "red.png")
    with prefs(app, toolbarIconColour=2, toolbarColorizeComplete=True):
        green = _toolbar_band(app, tmp, "green.png")
    near = lambda img, c: sum(1 for p in img.get_flattened_data() if all(abs(a - b) <= 30 for a, b in zip(p, c)))  # noqa: E731
    assert list(base.get_flattened_data()) != list(filled.get_flattened_data())
    assert near(red, (0xE8, 0x11, 0x23)) > near(base, (0xE8, 0x11, 0x23)) + 50
    assert near(green, (0x00, 0x8B, 0x00)) > near(base, (0x00, 0x8B, 0x00)) + 50


@pytest.mark.case("UI-030")
@pytest.mark.restart
def test_ui_030_toolbar_preferences_survive_a_restart(app):
    app.set_prefs(showToolbar=False, toolbarDisplayMode=1)
    try:
        app.restart()
        hidden = app.get("window", "toolbar.visible")
        app.set_prefs(showToolbar=True)
        assert hidden is False and app.get("window", "toolbar.displayMode") == 1
    finally:
        app.start()


# ---------------------------------------------------------------- status bar

@pytest.mark.case("UI-031")
def test_ui_031_the_status_bar_of_a_new_document(app):
    assert status(app) == ("None (Normal Text)    length: 0    lines: 1    Ln: 1    Col: 1    Pos: 1    "
                           "Unix (LF)    UTF-8    INS")
    value, tip = path_field(app)
    assert value == "(unsaved)" and not tip


@pytest.mark.case("UI-032")
def test_ui_032_language_length_and_lines_follow_the_document(app, tmp):
    fresh_doc(app, "", language="normal")
    app.type("ab\ncd")
    assert "length: 5    lines: 2" in status(app)
    app.run("IDM_LANG_PYTHON")
    assert status(app).startswith("Python    ")
    app.open(write(tmp, "x.json", '{"a": 1}\n'))
    assert status(app).startswith("JSON    ")


@pytest.mark.case("UI-033")
def test_ui_033_ln_col_and_pos_follow_the_caret(app):
    fresh_doc(app, "ab\n\tcd\n")
    app.sci(SCI_SETTABWIDTH, 4)
    app.select(2, 2)
    assert "Ln: 2    Col: 5    Pos: 5" in status(app)
    app.select(1, 3)
    assert "Ln: 1    Col: 3    Pos: 3" in status(app)


@pytest.mark.case("UI-034")
def test_ui_034_the_selection_is_shown_as_characters_and_lines(app):
    fresh_doc(app, "héllo\nwörld\n")
    app.select(1, 2, 2, 3)
    assert "Sel: 7 | 2" in status(app) and "Pos:" not in status(app)
    app.run("IDM_EDIT_SELECTALL")
    assert "Sel: 12 | 3" in status(app)
    app.sci(SCI_SETSELECTION, 3, 0)
    app.sci(SCI_ADDSELECTION, 11, 8)
    app.idle(0.2)
    app.run("IDM_VIEW_TAB_NEXT")        # a refresh of the chrome, as any caret move gives
    # characters, as the single selection above (getSelectedCharNumber): "hé" and "ör"
    assert "Sel 2 : 4 | 2" in status(app), status(app)
    app.sci(SCI_SETRECTANGULARSELECTIONANCHOR, 0)
    app.sci(SCI_SETRECTANGULARSELECTIONCARET, 10)
    app.idle(0.2)
    app.run("IDM_VIEW_TAB_NEXT")
    assert "Sel 2 : " in status(app) or "Sel 3 : " in status(app), status(app)


@pytest.mark.case("UI-035")
def test_ui_035_the_line_ending_field_names_the_document_s_eol(app, tmp):
    for name, data, label in [("w.txt", b"a\r\nb\r\n", "Windows (CR LF)"), ("u.txt", b"a\nb\n", "Unix (LF)"),
                              ("m.txt", b"a\rb\r", "Macintosh (CR)")]:
        app.open(write(tmp, name, data))
        assert label in status(app), (name, status(app))
    for cmd, label in [("IDM_FORMAT_TODOS", "Windows (CR LF)"), ("IDM_FORMAT_TOMAC", "Macintosh (CR)"),
                       ("IDM_FORMAT_TOUNIX", "Unix (LF)")]:
        app.run(cmd)
        assert label in status(app)


@pytest.mark.case("UI-036")
@pytest.mark.parametrize("name,data,command,label", [
    ("u8.txt", "héllo\n".encode("utf-8"), None, "UTF-8"),
    ("bom.txt", b"\xef\xbb\xbfh\xc3\xa9llo\n", None, "UTF-8-BOM"),
    ("le.txt", b"\xff\xfe" + "héllo\n".encode("utf-16-le"), None, "UTF-16 LE BOM"),
    ("be.txt", b"\xfe\xff" + "héllo\n".encode("utf-16-be"), None, "UTF-16 BE BOM"),
    pytest.param("cyr.txt", "Привет мир\n".encode("cp1251"), "IDM_FORMAT_WIN_1251", "Windows-1251"),
    ("lat.txt", "café\n".encode("latin-1"), "IDM_FORMAT_ANSI", "ANSI"),
])
def test_ui_036_the_encoding_field_names_the_document_s_encoding(app, tmp, name, data, command, label):
    app.open(write(tmp, name, data))
    if command:
        app.run(command)
    fields = status(app).split("    ")
    assert fields[-2] == label or (fields[-1].startswith("⎇") and fields[-3] == label), status(app)


@pytest.mark.case("UI-037")
def test_ui_037_ins_and_ovr(app):
    fresh_doc(app, "abc")
    app.select(1, 2)
    app.call("e2e_menu_invoke", path="View|Toggle Insert/Overtype")
    assert status(app).endswith("OVR")
    app.type("X")
    assert app.text() == "aXc"
    app.call("e2e_menu_invoke", path="View|Toggle Insert/Overtype")
    assert status(app).endswith("INS")
    app.type("Y")
    assert app.text() == "aXYc"


@pytest.mark.case("UI-038")
def test_ui_038_the_path_field_shows_the_file_s_full_path(app, tmp):
    p = write(tmp / "dir", "a.txt", "a\n")
    app.open(p)
    value, tip = path_field(app)
    assert app.same_path(value, p) and tip == "Click to copy the full path"
    pf = parse_rect(app.get("editor", "pathField.frame"))
    sf = parse_rect(app.get("editor", "statusField.frame"))
    width = main_window(app)["frame"][2]
    assert pf[0] + pf[2] <= sf[0] and pf[2] <= width / 2 + 1


@pytest.mark.case("UI-039")
def test_ui_039_a_click_on_the_path_copies_it_and_says_so(app, tmp):
    p = write(tmp, "a.txt", "a\n")
    app.open(p)
    full = path_field(app)[0]
    app.clipboard(set="")
    app.mouse(**{"class": "NppStatusPathField"})
    assert app.same_path(app.clipboard(), p)
    shown = path_field(app)[0]
    assert shown == f"✓ Copied: {app.clipboard()}"
    app.wait(lambda: path_field(app)[0] == full, timeout=3)


@pytest.mark.case("UI-040")
def test_ui_040_clicking_the_path_of_an_unsaved_document_copies_nothing(app):
    app.clipboard(set="before")
    app.mouse(**{"class": "NppStatusPathField"})
    assert app.clipboard() == "before" and path_field(app)[0] == "(unsaved)"


@pytest.mark.case("UI-041")
def test_ui_041_the_git_branch_appears_inside_a_repository_only(app, tmp):
    repo = tmp / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "feature-x", str(repo)], check=True)
    app.open(write(repo, "f.txt", "x\n"))
    app.wait(lambda: status(app).endswith("    ⎇ feature-x"), timeout=5)
    app.open(write(tmp / "plain", "g.txt", "y\n"))
    app.wait(lambda: "⎇" not in status(app), timeout=5)


@pytest.mark.case("UI-042")
def test_ui_042_the_status_bar_follows_the_tab_in_front_and_the_focused_view(app, tmp):
    py = write(tmp, "p.py", "a = 1\nb = 2\n")
    tx = write(tmp, "w.txt", b"one\r\ntwo\r\nthree\r\n")
    only(app, py, tx)
    assert "Windows (CR LF)" in status(app) and app.same_path(path_field(app)[0], tx)
    app.run("IDM_VIEW_TAB_PREV")
    assert status(app).startswith("Python") and "Unix (LF)" in status(app) and app.same_path(path_field(app)[0], py)
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    app.sci(SCI_GOTOLINE, 0)
    app.run("IDM_VIEW_SWITCHTO_OTHER_VIEW")
    app.sci(SCI_GOTOLINE, 1, view="sub")
    app.run("IDM_VIEW_SWITCHTO_OTHER_VIEW")
    app.run("IDM_VIEW_SWITCHTO_OTHER_VIEW")
    assert "Ln: 2" in status(app), status(app)


@pytest.mark.case("UI-043")
def test_ui_043_the_status_bar_can_be_hidden(app):
    h = view_frame(app, "split.frame")[3] if app.get("editor", "split.frame") else None
    with prefs(app, statusBarHidden=True):
        hidden = (app.get("editor", "statusField.hidden"), app.get("editor", "pathField.hidden"))
        grown = view_frame(app, "split.frame")[3]
    assert hidden == (True, True) and 20 <= grown - h <= 24
    assert not app.get("editor", "statusField.hidden")


# ---------------------------------------------------------------- editor context menu

def _editor_menu(app):
    return app.call("e2e_menu", context="editor")["tree"]


@pytest.mark.case("UI-044")
def test_ui_044_the_right_click_menu_is_notepad_s_default_contextmenu_xml(fresh_app):
    app = fresh_app
    tree = _editor_menu(app)
    f = support(app) / "contextMenu.xml"
    assert f.exists()
    assert f.read_text() == (app.bundle / "Contents/Resources/contextMenu.xml").read_text() or "ScintillaContextMenu" in f.read_text()
    assert titles(tree)[:9] == ["Cut", "Copy", "Paste", "Delete", "Select All", "Begin/End Select",
                                "Begin/End Select in Column Mode", None, "Style all occurrences of token"]
    names = [t for t in titles(tree) if t]
    assert len(names) == len(set(names))


@pytest.mark.case("UI-045")
def test_ui_045_context_menu_commands_act_on_the_editor(app):
    fresh_doc(app, "x = 1\ny = 2\n", language="python")
    app.call("e2e_clipboard", clear=True)
    paste = next(i for i in _editor_menu(app) if i.get("title") == "Paste")
    assert not paste["enabled"]
    app.select(1, 1, 1, 2)
    app.call("e2e_menu_invoke", context="editor", path="Copy")
    app.sci(SCI_DOCUMENTEND)
    app.call("e2e_menu_invoke", context="editor", path="Paste")
    assert app.text() == "x = 1\ny = 2\nx"
    app.call("e2e_menu_invoke", context="editor", path="Select All")
    app.call("e2e_menu_invoke", context="editor", path="Cut")
    assert app.text() == ""
    app.call("e2e_menu_invoke", context="editor", path="Paste")
    assert app.text() == "x = 1\ny = 2\nx"
    toggle = [p for p, i in flat(_editor_menu(app)) if i.get("action") in ("toggleLineComment:", "blockComment:")
              or (p[-1] or "").startswith("Toggle Single Line Comment")]
    if toggle:
        app.select(1, 1)
        app.call("e2e_menu_invoke", context="editor", path="|".join(toggle[0]))
        assert app.text().startswith("#")


def _write_context_menu(app, body):
    (support(app)).mkdir(parents=True, exist_ok=True)
    f = support(app) / "contextMenu.xml"
    f.write_text('<?xml version="1.0" encoding="UTF-8" ?>\n<NotepadPlus>\n<ScintillaContextMenu>\n'
                 + body + '\n</ScintillaContextMenu>\n</NotepadPlus>\n')
    return f


@pytest.mark.case("UI-046")
def test_ui_046_an_edited_contextmenu_xml_shows_at_the_next_right_click(app):
    f = support(app) / "contextMenu.xml"
    old = f.read_text() if f.exists() else None
    _write_context_menu(app, '<Item MenuEntryName="Edit" MenuItemName="Copy"/>\n<Item id="0"/>\n'
                             '<Item id="42016" ItemNameAs="Shout"/>\n'
                             '<Item FolderName="More" MenuEntryName="View" MenuItemName="Word wrap"/>')
    try:
        tree = _editor_menu(app)
        assert titles(tree) == ["Copy", None, "Shout", "More"]
        assert titles(tree[3]["items"]) == ["Word Wrap"]
        fresh_doc(app, "abc")
        app.select(1, 1, 1, 4)
        app.call("e2e_menu_invoke", context="editor", path="Shout")
        assert app.text() == "ABC"
    finally:
        if old is None:
            f.unlink()
        else:
            f.write_text(old)


@pytest.mark.case("UI-047")
def test_ui_047_unknown_entries_are_skipped_and_a_broken_file_does_not_break(app):
    f = support(app) / "contextMenu.xml"
    old = f.read_text() if f.exists() else None
    try:
        _write_context_menu(app, '<Item id="99999"/>\n<Item MenuEntryName="Nope" MenuItemName="Nothing"/>\n'
                                 '<Item MenuEntryName="Edit" MenuItemName="Copy"/>')
        assert titles(_editor_menu(app)) == ["Copy"]
        f.write_text("this is not XML <<<")
        assert len([t for t in titles(_editor_menu(app)) if t]) > 0
        assert app.docs()
    finally:
        if old is None:
            f.unlink(missing_ok=True)
        else:
            f.write_text(old)


@pytest.mark.case("UI-048")
def test_ui_048_edit_popup_contextmenu_opens_the_file_to_edit(app):
    app.answers(alerts=[1])
    app.run("IDM_SETTING_EDITCONTEXTMENU")
    log = app.modal_log()
    assert any(e.get("message") == "Editing contextMenu" for e in log), log
    assert app.same_path(current(app)["path"], support(app) / "contextMenu.xml")


# ---------------------------------------------------------------- docking

@pytest.mark.case("UI-049")
def test_ui_049_panels_open_where_notepad_puts_them_and_share_a_side_as_tabs(fresh_app, tmp):
    app = fresh_app
    only(app, write(tmp, "m.py", "def f():\n    pass\n"))
    before = view_frame(app)
    for c in ["IDM_VIEW_DOC_MAP", "IDM_VIEW_FUNC_LIST", "IDM_VIEW_DOCLIST", "IDM_VIEW_FILEBROWSER",
              "IDM_VIEW_PROJECT_PANEL_1"]:
        app.run(c)
    places = {p: dock(app, "placeOfPanel:", p) for p in
              ["documentMap", "functionList", "documentList", "workspace", "project1"]}
    assert places == {"documentMap": 1, "functionList": 1, "documentList": 0, "workspace": 0, "project1": 0}
    assert set(dock(app, "panelsIn:", 1)) == {"documentMap", "functionList"}
    assert set(dock(app, "panelsIn:", 0)) == {"documentList", "workspace", "project1"}
    assert dock(app, "frontPanelIn:", 1) == "functionList" and dock(app, "frontPanelIn:", 0) == "project1"
    assert view_frame(app)[2] < before[2] - 300


def _dock_menu(app, place, path=None):
    kw = {"menu_path": path} if path else {}
    return app.mouse(**{"class": "NppDockContainerView", "index": 0 if place == 0 else 0}, button="right",
                     point=[20, 10], **kw)


@pytest.mark.case("UI-050")
def test_ui_050_a_panel_moves_between_the_sides_and_floats_from_its_tab_s_me(app, tmp):
    only(app, write(tmp, "m.py", "def f():\n    pass\n"))
    app.run("IDM_VIEW_FUNC_LIST")
    width = view_frame(app)[2]
    r = app.mouse(**{"class": "NppDockContainerView"}, button="right", point=[20, 10])
    menu = r["menu"]
    assert titles(menu) == ["Dock Left", "Dock Right", "Dock Top", "Dock Bottom", "Float", None, "Close"]
    assert [i["checked"] for i in menu if i.get("title") == "Dock Right"] == [True]
    for path, place in [("Dock Bottom", 3), ("Dock Left", 0), ("Float", 4)]:
        app.mouse(**{"class": "NppDockContainerView"}, button="right", point=[20, 10], menu_path=path)
        assert dock(app, "placeOfPanel:", "functionList") == place
    app.wait(lambda: window_titled(app, "Function List"), timeout=5)
    assert view_frame(app)[2] > width
    dock(app, "movePanel:to:", "functionList", 1)


@pytest.mark.case("UI-051")
def test_ui_051_closing_a_floating_panel_s_window_hides_the_panel_until_it_i(app):
    app.run("IDM_VIEW_DOCLIST")
    app.mouse(**{"class": "NppDockContainerView"}, button="right", point=[20, 10], menu_path="Float")
    w = app.wait(lambda: window_titled(app, "Document List"), timeout=5)
    frame = w["frame"]
    app.close_window(w["number"])
    assert not dock(app, "isPanelVisible:", "documentList")
    app.run("IDM_VIEW_DOCLIST")
    w2 = app.wait(lambda: window_titled(app, "Document List"), timeout=5)
    assert dock(app, "placeOfPanel:", "documentList") == 4
    assert all(abs(a - b) <= 2 for a, b in zip(w2["frame"], frame))
    dock(app, "movePanel:to:", "documentList", 0)


@pytest.mark.case("UI-052")
def test_ui_052_the_close_button_on_a_dock_tab_hides_the_panel(app):
    app.run("IDM_VIEW_DOC_MAP")
    size = dock(app, "sizeOfPlace:", 1)
    app.mouse(**{"class": "NppDockContainerView"}, point=[size - 13, 11])
    assert not dock(app, "isPanelVisible:", "documentMap")
    app.run("IDM_VIEW_DOC_MAP")
    assert dock(app, "isPanelVisible:", "documentMap") and dock(app, "placeOfPanel:", "documentMap") == 1


@pytest.mark.case("UI-053")
def test_ui_053_two_panels_can_float_together_in_one_window(app, tmp):
    only(app, write(tmp, "m.py", "def f():\n    pass\n"))
    app.run("IDM_VIEW_FUNC_LIST")
    app.mouse(**{"class": "NppDockContainerView"}, button="right", point=[20, 10], menu_path="Float")
    fx, fy, fw, fh = app.wait(lambda: window_titled(app, "Function List"), timeout=5)["frame"]
    app.run("IDM_VIEW_DOCLIST")
    if dock(app, "placeOfPanel:", "documentList") == 4:
        dock(app, "movePanel:to:", "documentList", 0)
    try:
        # Document List's tab, the only docked one, dragged by the mouse onto the floating window.
        app.mouse(**{"class": "NppDockContainerView"}, point=[20, 10], drag_to_screen=[fx + fw / 2, fy + fh / 2])
        assert sorted(dock(app, "panelsFloatingWith:", "functionList")) == ["documentList", "functionList"]
        assert dock(app, "placeOfPanel:", "documentList") == 4
        panels = [w for w in app.windows() if w["visible"] and w["title"] in ("Function List", "Document List")]
        assert len(panels) == 1
        app.close_window(panels[0]["number"])
        assert not dock(app, "isPanelVisible:", "functionList") and not dock(app, "isPanelVisible:", "documentList")
    finally:
        dock(app, "movePanel:to:", "documentList", 0)
        dock(app, "movePanel:to:", "functionList", 1)


@pytest.mark.case("UI-054")
@pytest.mark.restart
def test_ui_054_where_the_panels_are_is_remembered_across_a_restart(app, tmp):
    try:
        app.set_prefs(rememberPanelState=True)
        only(app, write(tmp, "m.py", "def f():\n    pass\n"))
        app.run("IDM_VIEW_FUNC_LIST")
        dock(app, "movePanel:to:", "functionList", 3)
        app.run("IDM_VIEW_DOCLIST")
        dock(app, "movePanel:to:", "documentList", 4)
        frame = app.wait(lambda: window_titled(app, "Document List"), timeout=5)["frame"]
        app.run("IDM_VIEW_DOC_MAP")
        app.restart()
        app.wait(lambda: dock(app, "isPanelVisible:", "documentList"), timeout=5)
        assert dock(app, "isPanelVisible:", "functionList")
        assert dock(app, "placeOfPanel:", "functionList") == 3 and dock(app, "placeOfPanel:", "documentList") == 4
        w = app.wait(lambda: window_titled(app, "Document List"), timeout=5)
        assert all(abs(a - b) <= 2 for a, b in zip(w["frame"], frame))
        places = app.pref("dockLayout")["places"]
        assert places["functionList"] == 3 and places["documentList"] == 4
    finally:
        app.start()


@pytest.mark.case("UI-055")
@pytest.mark.restart
@pytest.mark.parametrize("remember,keep,expect", [(False, None, set()), (True, None, {"documentList", "functionList"}),
                                                  (True, {"functionList": False}, {"documentList"})])
def test_ui_055_remember_panel_state_panel_by_panel(app, remember, keep, expect):
    try:
        app.set_prefs(rememberPanelState=remember)
        if keep is not None:
            app.set_prefs(panelStateKeep=keep)
        app.run("IDM_VIEW_DOCLIST")
        app.run("IDM_VIEW_FUNC_LIST")
        app.restart()
        app.idle(0.5)
        shown = {p for p in ("documentList", "functionList")
                 if dock(app, "hasPanel:", p) and dock(app, "isPanelVisible:", p)}
        assert shown == expect
    finally:
        app.start()


@pytest.mark.case("UI-056")
@pytest.mark.restart
def test_ui_056_a_dock_s_size_is_kept(app, tmp):
    def drag_to(size):
        # The divider before the right dock, dragged by the mouse: left makes the dock wider.
        now = dock(app, "sizeOfPlace:", 1)
        app.mouse(**{"class": "NppDockContainerView"}, divider="before", drag_by=[now - size, 0])
        return dock(app, "sizeOfPlace:", 1)

    try:
        app.set_prefs(rememberPanelState=True)
        only(app, write(tmp, "m.py", "def f():\n    pass\n"))
        app.run("IDM_VIEW_FUNC_LIST")
        dock(app, "movePanel:to:", "functionList", 1)
        assert abs(drag_to(260) - 260) <= 2
        assert abs(drag_to(320) - 320) <= 2
        assert abs(app.pref("dockLayout")["sizes"]["1"] - 320) <= 2
        app.restart()
        app.wait(lambda: dock(app, "isPanelVisible:", "functionList"), timeout=5)
        assert abs(dock(app, "sizeOfPlace:", 1) - 320) <= 2
        assert abs(app.pref("dockLayout")["sizes"]["1"] - 320) <= 2
    finally:
        app.start()


# ---------------------------------------------------------------- document switcher

def _switcher(app):
    ws = [w for w in app.windows() if w["class"] == "NSPanel" and w["visible"] and not w["title"]]
    return ws[0] if ws else None


def _abc_mru(app, tmp):
    only(app, *[write(tmp, f"{c}.txt", c) for c in "ABC"])
    app.run("IDM_VIEW_TAB1")        # visit order: A, B, C, then A: MRU = A, C, B


def _switcher_rows(app):
    w = _switcher(app)
    t = next(c for c in ui(app, w["number"])["controls"] if c["class"] == "NSTableView")
    return [r[0] for r in t["cells"]], t["selected"]


@pytest.mark.case("UI-057")
def test_ui_057_ctrl_tab_shows_the_switcher_with_the_most_recent_documents_f(app, tmp):
    with prefs(app, docSwitcherEnabled=True, docSwitcherMRU=True):
        _abc_mru(app, tmp)
        app.call("e2e_keys", keys=["ctrl+tab"], hold=["ctrl"], keep_held=True)
        try:
            assert _switcher(app)
            rows, sel = _switcher_rows(app)
            assert rows == ["A.txt", "C.txt", "B.txt"] and sel == [1]
            assert current_title(app) == "C.txt"
        finally:
            app.call("e2e_keys", keys=[], release=True)
        app.wait(lambda: not _switcher(app), timeout=3)
        assert current_title(app) == "C.txt"


@pytest.mark.case("UI-058")
def test_ui_058_ctrl_tab_repeated_and_ctrl_shift_tab_walk_the_list(app, tmp):
    with prefs(app, docSwitcherEnabled=True, docSwitcherMRU=True):
        _abc_mru(app, tmp)
        app.call("e2e_keys", keys=["ctrl+tab", "ctrl+tab"], hold=["ctrl"], keep_held=True)
        try:
            assert _switcher_rows(app)[1] == [2]
            app.call("e2e_keys", keys=["ctrl+shift+tab"], hold=["ctrl"], keep_held=True)
            assert _switcher_rows(app)[1] == [1]
        finally:
            app.call("e2e_keys", keys=[], release=True)
        assert current_title(app) == "C.txt"


@pytest.mark.case("UI-059")
def test_ui_059_without_mru_the_switcher_follows_the_tab_order(app, tmp):
    with prefs(app, docSwitcherEnabled=True, docSwitcherMRU=False):
        _abc_mru(app, tmp)
        app.call("e2e_keys", keys=["ctrl+tab"], hold=["ctrl"], keep_held=True)
        try:
            rows, _ = _switcher_rows(app)
        finally:
            app.call("e2e_keys", keys=[], release=True)
        assert rows == ["A.txt", "B.txt", "C.txt"] and current_title(app) == "B.txt"


@pytest.mark.case("UI-060")
def test_ui_060_with_the_switcher_off_ctrl_tab_steps_through_the_tabs(app, tmp):
    with prefs(app, docSwitcherEnabled=False):
        only(app, *[write(tmp, f"{c}.txt", c) for c in "ABC"])
        seen = []
        for k in ["ctrl+tab", "ctrl+shift+tab", "ctrl+shift+tab"]:
            app.call("e2e_keys", keys=[k], hold=["ctrl"], release=True)
            assert not _switcher(app)
            seen.append(current_title(app))
    assert seen == ["A.txt", "C.txt", "B.txt"]


@pytest.mark.case("UI-061")
def test_ui_061_ctrl_tab_with_a_single_document_does_nothing(app):
    app.call("e2e_keys", keys=["ctrl+tab"], hold=["ctrl"], release=True)
    assert not _switcher(app) and len(app.docs()) == 1 and current_title(app) == "new 1"


# ---------------------------------------------------------------- rendering

@pytest.mark.case("UI-062")
@pytest.mark.parametrize("mode,dark", [(1, False), (2, True)])
def test_ui_062_light_and_dark_appearance(app, tmp, mode, dark):
    fresh_doc(app, "int x = 1;\n", language="cpp")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    app.run("IDM_VIEW_DOC_MAP")
    with prefs(app, appearanceMode=mode):
        app.idle(0.3)
        backs = [app.sci(SCI_STYLEGETBACK, 32, view=v) for v in ("main", "sub", "docMapView")]
        img = snap(app, tmp / "look.png")
        appearance = app.get("window", "effectiveAppearance.name")
        w, h = img.size
        lum = region_median_luminance(img, (int(w * 0.3), int(h * 0.2), int(w * 0.6), int(h * 0.4)))
    assert len(set(backs)) == 1
    bgr = backs[0]
    back_lum = luminance(((bgr & 0xFF), (bgr >> 8) & 0xFF, (bgr >> 16) & 0xFF))
    if dark:
        assert back_lum < 0.3 and lum < 0.3 and "Dark" in appearance
    else:
        assert back_lum > 0.7 and lum > 0.7 and "Dark" not in appearance
    assert app.text() == "int x = 1;\n"


@pytest.mark.case("UI-063")
def test_ui_063_following_the_system_appearance(app):
    with prefs(app, appearanceMode=0):
        system = app.get("nsapp", "effectiveAppearance.name")
        win = app.get("window", "effectiveAppearance.name")
        bgr = app.sci(SCI_STYLEGETBACK, 32)
    dark_bg = luminance(((bgr & 0xFF), (bgr >> 8) & 0xFF, (bgr >> 16) & 0xFF)) < 0.5
    assert ("Dark" in win) == ("Dark" in system)
    assert dark_bg == ("Dark" in system)


@pytest.mark.case("UI-064")
@pytest.mark.parametrize("mode", [1, 2])
def test_ui_064_the_window_renders_its_chrome_in_a_snapshot(app, tmp, mode):
    only(app, write(tmp, "a.txt", "".join(f"line {i}\n" for i in range(40))))
    with prefs(app, appearanceMode=mode):
        app.idle(0.3)
        img = snap(app, tmp / "chrome.png")
    w, h = img.size
    frame = main_window(app)["frame"]
    scale = w / frame[2]
    # The status bar's line: the bottom 60 pt. The document's 40 lines end well above the editor's
    # bottom, so nothing but the status bar draws there (the snapshot is the window's content, less the
    # title and toolbar strip, so a field's frame does not map onto it directly).
    assert 40 * 14 < frame[3] - 140, "the window must be tall enough for the editor's bottom to stay empty"
    status_band = (int(10 * scale), h - int(60 * scale), int(w * 0.6), h - int(2 * scale))
    regions = {"tabs": (0, 0, int(w * 0.3), int(26 * scale)), "margin": (0, int(40 * scale), int(40 * scale), int(h * 0.5)),
               "text": (int(60 * scale), int(40 * scale), int(w * 0.4), int(h * 0.5)), "status": status_band}
    blank = [k for k, box in regions.items() if len(set(img.crop(box).get_flattened_data())) <= 2]
    assert not blank, blank


DIALOGS = [("IDM_SEARCH_FIND", "Find"), ("IDM_SEARCH_REPLACE", "Replace"), ("IDM_SEARCH_FINDINFILES", "Find in Files"),
           ("IDM_SEARCH_MARK", "Mark"), ("IDM_SETTING_PREFERENCE", "Preferences"),
           ("IDM_LANGSTYLE_CONFIG_DLG", "Style Configurator"), ("IDM_SETTING_SHORTCUT_MAPPER", "Shortcut Mapper"),
           ("IDM_SEARCH_GOTOLINE", "Go To"), ("IDM_EDIT_COLUMNMODE", "Column Editor"),
           ("IDM_LANG_USER_DLG", "User Defined Language"), ("IDM_ABOUT", "About")]


cut_controls = cut_controls_measured


def open_dialog(app, command):
    before = {w["number"] for w in app.windows()}
    r = app.call_async("run_command", command=command) if command in ("IDM_SEARCH_GOTOLINE", "IDM_EDIT_COLUMNMODE", "IDM_ABOUT") else None
    if r is None:
        app.run(command)
    w = app.wait(lambda: next((w for w in app.windows() if w["number"] not in before and w["visible"]), None), timeout=5)
    return w, r


@pytest.mark.case("UI-065")
@pytest.mark.parametrize("command,name", DIALOGS, ids=[d[1] for d in DIALOGS])
def test_ui_065_nothing_is_cut_off_in_the_main_dialogs(app, tmp, command, name):
    fresh_doc(app, "text\n")
    app.answers(real_modals=True)
    w, pending = open_dialog(app, command)
    try:
        snap(app, tmp / f"{name}.png", window=w["number"])
        bad = cut_controls(app, w["number"])
        assert not bad, bad
    finally:
        app.close_window(w["number"])
        if pending:
            pending.wait(10)
        app.answers(real_modals=False)


@pytest.mark.case("UI-066")
def test_ui_066_the_main_window_s_chrome_at_a_small_size(app, tmp):
    before = main_window(app)["frame"]
    app.open(write(tmp / ("deep/" * 6), "a_file_with_a_long_name.txt", "x\n"))
    try:
        app.act("main", "resize_window", value=[640, 400])
        visible_items = app.get("window", "toolbar.visibleItems.itemIdentifier") or []
        assert len(visible_items) < len(app.get("window", "toolbar.items"))
        pf = parse_rect(app.get("editor", "pathField.frame"))
        sf = parse_rect(app.get("editor", "statusField.frame"))
        assert pf[2] <= 320 + 1 and sf[0] >= pf[0] + pf[2]
        ed = view_frame(app)
        assert ed[2] > 0 and ed[3] > 0
    finally:
        app.act("main", "resize_window", value=[before[2], before[3] - 22])


@pytest.mark.case("UI-067")
def test_ui_067_the_two_views_lie_side_by_side_without_overlap(app):
    fresh_doc(app, "x\n")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    a = view_frame(app, "sciView.frame")
    host = parse_rect(app.get("editor", "secondaryHost.frame"))
    area = parse_rect(app.get("editor", "editorSplit.frame"))
    assert a[2] > 0 and a[3] > 0 and host[2] > 0 and host[3] > 0
    # Frames in the split's coordinates: the main view and the second view's host side by side
    # (NppGUI::_splitterPos = POS_VERTICAL), no overlap. editorArea is the whole area, not a pane.
    main_host = a
    assert host[0] >= a[0] + a[2] - 1
    overlap_x = min(main_host[0] + main_host[2], host[0] + host[2]) - max(main_host[0], host[0])
    overlap_y = min(main_host[1] + main_host[3], host[1] + host[3]) - max(main_host[1], host[1])
    assert overlap_x <= 0 or overlap_y <= 0
    assert abs((main_host[2] * main_host[3] + host[2] * host[3]) - area[2] * area[3]) < area[2] * 12
    app.run("IDM_VIEW_SWITCHTO_OTHER_VIEW")
    app.run("IDM_VIEW_GOTO_ANOTHER_VIEW")
