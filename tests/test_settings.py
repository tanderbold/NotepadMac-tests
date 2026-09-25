"""SETTINGS: end-to-end tests (plan: plan/SETTINGS.md)."""
import os
import re
import subprocess
import time
from pathlib import Path

import pytest

from harness.sci import *  # noqa: F401,F403
import _util_set as U  # noqa: E402
from _util_set import (PAGES, fresh, indicator_runs_upto, PREFS, apply, check, close_prefs, control_for, controls, field, indicator_runs,  # noqa: F401
                       keep_prefs, light, open_prefs, page, panel_shown, papp, popup, prefs_visible, set_options, state,
                       status_text, stored, support, value, window_visible)

SMART_HIGHLIGHT = 19   # smart highlighting's own indicator (was 12, shared with Mark style 5)


# The in-app suite's shortcuts.xml as Notepad++ on Windows writes it: a menu key, a macro
# with its actions, a Run command, a plugin's command, a Scintilla key with a second key.
WINDOWS_SHORTCUTS = (
    '<?xml version="1.0" encoding="UTF-8" ?>\n<NotepadPlus>\n'
    '<InternalCommands><Shortcut id="41001" Ctrl="yes" Alt="yes" Shift="no" Key="78" /></InternalCommands>\n'
    '<Macros><Macro name="From Windows" Ctrl="no" Alt="yes" Shift="no" Key="117">'
    '<Action type="1" message="2170" wParam="0" lParam="0" sParam="hi hi" />'
    '<Action type="3" message="1700" wParam="0" lParam="0" sParam="" />'
    '<Action type="3" message="1601" wParam="0" lParam="0" sParam="hi" />'
    '<Action type="3" message="1625" wParam="0" lParam="0" sParam="" />'
    '<Action type="3" message="1602" wParam="0" lParam="0" sParam="yo" />'
    '<Action type="3" message="1702" wParam="0" lParam="768" sParam="" />'
    '<Action type="3" message="1701" wParam="0" lParam="1609" sParam="" />'
    '<Action type="2" message="0" wParam="42007" lParam="0" sParam="" /></Macro></Macros>\n'
    '<UserDefinedCommands><Command name="Say hello" Ctrl="no" Alt="no" Shift="no" Key="0">echo hello</Command></UserDefinedCommands>\n'
    '<PluginCommands><PluginCommand moduleName="x.dll" internalID="1" Ctrl="no" Alt="no" Shift="no" Key="0" /></PluginCommands>\n'
    '<ScintillaKeys><ScintKey ScintID="2338" menuCmdID="0" Ctrl="yes" Alt="no" Shift="yes" Key="68">'
    '<NextKey Ctrl="no" Alt="yes" Shift="no" Key="68" /></ScintKey></ScintillaKeys>\n'
    '</NotepadPlus>\n')


# The in-app suite's contextMenu.xml: by menu and item name, renamed, separators (duplicates
# collapse), a command this build lacks, a folder by id and by name, an empty folder, a plugin folder.
CONTEXT_MENU_SAMPLE = (
    '<?xml version="1.0" encoding="UTF-8" ?>\n<NotepadPlus><ScintillaContextMenu>\n'
    '<Item id="0"/>\n'
    '<Item MenuEntryName="Edit" MenuItemName="Copy"/>\n'
    '<Item MenuEntryName="edit" MenuItemName="&amp;Paste" ItemNameAs="Put it here"/>\n'
    '<Item id="0"/><Item id="0"/>\n'
    '<Item MenuEntryName="Edit" MenuItemName="No Such Command"/>\n'
    '<Item FolderName="Case" id="42016"/>\n'
    '<Item FolderName="Case" MenuEntryName="Edit" MenuItemName="lowercase"/>\n'
    '<Item FolderName="Nothing here" MenuEntryName="Edit" MenuItemName="Nor This"/>\n'
    '<Item FolderName="Plugin commands" PluginEntryName="JSON" PluginCommandItemName="Format"/>\n'
    '<Item id="0"/>\n'
    '</ScintillaContextMenu></NotepadPlus>\n')

# A theme file as Notepad++ writes one: Default Style ABCDEF on 222222, C++ DEFAULT 123456/654321.
TEST_THEME = (
    '<?xml version="1.0" encoding="UTF-8" ?>\n<NotepadPlus>\n<LexerStyles>\n'
    '<LexerType name="cpp" desc="C++" ext="">\n'
    '<WordsStyle name="DEFAULT" styleID="11" fgColor="123456" bgColor="654321" fontName="" fontStyle="0" fontSize="" />\n'
    '</LexerType>\n</LexerStyles>\n<GlobalStyles>\n'
    '<WidgetStyle name="Default Style" styleID="32" fgColor="ABCDEF" bgColor="222222" fontName="" fontStyle="0" fontSize="10" />\n'
    '</GlobalStyles>\n</NotepadPlus>\n')


@pytest.mark.case("SETTINGS-001")
def test_settings_001_preferences_opens_with_notepad_s_23_pages_in_order(app):
    """SETTINGS-001: Preferences opens with Notepad++'s 23 pages in order

    Covers: IDM_SETTING_PREFERENCE
    Channel: menu, ui
    Steps: Run IDM_SETTING_PREFERENCE; read the category table of the "Preferences" window; select each row in turn.
    Expect: the window "Preferences" is visible; the rows are exactly General, Toolbar, Editing 1, Editing 2, Dark Mode, Margins/Border/Edge, New Document, Indentation, Language, Highlighting, Print, Backup, Auto-Completion, Multi-Instance & Date, Delimiter, Performance, Tab Bar, Recent Files History, Default Directory, Searching, Cloud & Link, MISC., Search Engine; selecting a row shows that page (its first control changes); the buttons Apply, Cancel and Reset are present.
    """
    open_prefs(app)
    assert window_visible(app, PREFS)
    table = U.category_table(app)
    assert [r[0] for r in table["cells"]] == PAGES
    firsts = []
    for name in PAGES:
        page(app, name)
        cs = [c for c in controls(app) if c["class"] != "NSTableView" and c["path"].count(".") > 3]
        firsts.append((cs[0].get("title"), cs[0].get("value")) if cs else None)
    assert len(set(firsts)) == len(PAGES), firsts
    titles = {c.get("title") for c in controls(app) if c["class"] == "NSButton"}
    assert {"Apply", "Cancel", "Reset"} <= titles


@pytest.mark.case("SETTINGS-002")
def test_settings_002_the_menu_command_and_cmd_toggle_the_dialog(app):
    """SETTINGS-002: The menu command and Cmd+, toggle the dialog

    Covers: IDM_SETTING_PREFERENCE
    Channel: menu, keys, ui
    Steps: Read the key of IDM_SETTING_PREFERENCE with `menu_item`; press cmd+, with `keys`; run IDM_SETTING_PREFERENCE again.
    Expect: the menu item's key is "cmd+,"; cmd+, shows the Preferences window; running the command while it is shown hides it (toggle).
    """
    assert app.menu_item("IDM_SETTING_PREFERENCE").get("key") == "cmd+,"
    app.keys("cmd+,")
    app.wait(lambda: prefs_visible(app), message="Preferences shown by cmd+,")
    app.run("IDM_SETTING_PREFERENCE")
    app.wait(lambda: not prefs_visible(app), message="Preferences hidden again")


@pytest.mark.case("SETTINGS-003")
def test_settings_003_cancel_keeps_nothing_of_what_was_changed(papp):
    """SETTINGS-003: Cancel keeps nothing of what was changed

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, prefs
    Steps: On Editing 2 tick "Word wrap" and on General tick "Status Bar: Hide", then click Cancel; open the dialog again.
    Expect: the window closes; SCI_GETWRAPMODE stays SC_WRAP_NONE and the status bar is still shown; prefs wordWrap/statusBarHidden unchanged; reopened, both checkboxes are unticked again.
    """
    app = papp
    before = stored(app)
    page(app, "Editing 2")
    check(app, "Word wrap", True)
    page(app, "General")
    check(app, "Status Bar: Hide", True)
    app.click(PREFS, "Cancel")
    app.wait(lambda: not prefs_visible(app))
    assert app.sci(SCI_GETWRAPMODE) == SC_WRAP_NONE
    assert status_text(app)
    after = stored(app)
    assert after.get("wordWrap") == before.get("wordWrap")
    assert after.get("statusBarHidden") == before.get("statusBarHidden")
    page(app, "Editing 2")
    assert state(app, "Word wrap") == 0
    page(app, "General")
    assert state(app, "Status Bar: Hide") == 0


@pytest.mark.case("SETTINGS-004")
def test_settings_004_apply_keeps_the_dialog_open_and_the_dialog_shows_settings_ch(papp):
    """SETTINGS-004: Apply keeps the dialog open and the dialog shows settings changed elsewhere

    Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_WRAP
    Channel: ui, menu
    Steps: Open Preferences, click Apply without changes; close it; run IDM_VIEW_WRAP; open Preferences on Editing 2.
    Expect: after Apply the window is still visible and nothing changes in the editor; after View > Word wrap the "Word wrap" checkbox is ticked (the pages are rebuilt from current settings on opening); Apply then does not turn wrap back off.
    """
    app = papp
    open_prefs(app)
    apply(app)
    assert prefs_visible(app)
    assert app.sci(SCI_GETWRAPMODE) == SC_WRAP_NONE
    close_prefs(app)
    app.run("IDM_VIEW_WRAP")
    try:
        page(app, "Editing 2")
        assert state(app, "Word wrap") == 1
        apply(app)
        assert app.sci(SCI_GETWRAPMODE) != SC_WRAP_NONE
    finally:
        close_prefs(app)
        if app.checked("IDM_VIEW_WRAP"):
            app.run("IDM_VIEW_WRAP")


@pytest.mark.case("SETTINGS-005")
def test_settings_005_reset_puts_every_preference_back_to_its_default(fresh):
    """SETTINGS-005: Reset puts every preference back to its default

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, prefs
    Steps: With `fresh_app`, set Editing 1 "Enable virtual space" and Tab Bar "Vertical" and Apply; open the dialog and click Reset; afterwards write autoUpdateMode=0 again with `set_prefs`.
    Expect: the dialog closes; SCI_GETVIRTUALSPACEOPTIONS has no SCVS_USERACCESSIBLE; prefs virtualSpace and tabBarVertical read back as their defaults (false / absent); reopened, both checkboxes are unticked.
    """
    app = fresh
    set_options(app, "Editing 1", checks={"Enable virtual space": True}, close=False)
    set_options(app, "Tab Bar", checks={"Vertical": True}, close=False)
    assert app.sci(SCI_GETVIRTUALSPACEOPTIONS) & SCVS_USERACCESSIBLE
    app.click(PREFS, "Reset")
    app.wait(lambda: not prefs_visible(app))
    app.set_prefs(autoUpdateMode=0)
    assert not app.sci(SCI_GETVIRTUALSPACEOPTIONS) & SCVS_USERACCESSIBLE
    s = stored(app)
    assert not s.get("virtualSpace") and not s.get("tabBarVertical")
    page(app, "Editing 1")
    assert state(app, "Enable virtual space") == 0
    page(app, "Tab Bar")
    assert state(app, "Vertical") == 0


@pytest.mark.case("SETTINGS-006")
def test_settings_006_every_option_applied_from_the_dialog_survives_a_restart(fresh):
    """SETTINGS-006: Every option applied from the dialog survives a restart

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, prefs, launch
    Steps: With `fresh_app`, for each of (Editing 1 "Enable virtual space" on, Editing 2 "Show Indent Guide" off, Margins "Padding: Left" 5, New Document "Format (Line ending)" "Windows (CR LF)", Tab Bar "Max. tab label length:" 8, Searching "Confirm Replace All" off, Auto-Completion "Characters before it opens" 3) set the control and Apply; restart; open each page.
    Expect: every control shows the value set; the matching preference keys (virtualSpace, showIndentGuides, paddingLeft, defaultEOL=0, tabMaxLabelLength=8, confirmReplaceAll, autoCompleteThreshold=3) are stored in the test domain (`e2e_prefs all`).
    """
    app = fresh
    set_options(app, "Editing 1", checks={"Enable virtual space": True}, close=False)
    set_options(app, "Editing 2", checks={"Show Indent Guide": False}, close=False)
    set_options(app, "Margins/Border/Edge", fields={"Padding: Left": 5}, close=False)
    set_options(app, "New Document", popups={"Format (Line ending)": "Windows (CR LF)"}, close=False)
    set_options(app, "Tab Bar", fields={"Max. tab label length:": 8}, close=False)
    set_options(app, "Searching", checks={"Confirm Replace All": False}, close=False)
    set_options(app, "Auto-Completion", fields={"Characters before it opens": 3})
    app.restart()
    page(app, "Editing 1")
    assert state(app, "Enable virtual space") == 1
    page(app, "Editing 2")
    assert state(app, "Show Indent Guide") == 0
    page(app, "Margins/Border/Edge")
    assert value(app, "Padding: Left") == "5"
    page(app, "New Document")
    assert value(app, "Format (Line ending)") == "Windows (CR LF)"
    page(app, "Tab Bar")
    assert value(app, "Max. tab label length:") == "8"
    page(app, "Searching")
    assert state(app, "Confirm Replace All") == 0
    page(app, "Auto-Completion")
    assert value(app, "Characters before it opens") == "3"
    s = stored(app)
    assert s["virtualSpace"] in (True, 1) and s["showIndentGuides"] in (False, 0)
    assert s["paddingLeft"] == 5 and s["defaultEOL"] == 0 and s["tabMaxLabelLength"] == 8
    assert s["confirmReplaceAll"] in (False, 0) and s["autoCompleteThreshold"] == 3
    assert app.sci(SCI_GETVIRTUALSPACEOPTIONS) & SCVS_USERACCESSIBLE
    assert app.sci(SCI_GETMARGINLEFT) == 5


@pytest.mark.case("SETTINGS-007")
@pytest.mark.slow
@pytest.mark.timeout(300)   # every checkbox of every page, one Apply each: over two minutes
def test_settings_007_every_checkbox_in_the_dialog_is_written_by_apply(fresh):
    """SETTINGS-007: Every checkbox in the dialog is written by Apply

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, prefs
    Steps: With `fresh_app`, for every page, for every checkbox on it: flip its state, click Apply, read the persistent domain with `e2e_prefs all`, flip it back and Apply. Skip "Let AI agents drive the editor (MCP)" when it would turn the server off (checked separately in SETTINGS-089).
    Expect: each flip changes exactly one stored key to the new value; known failures: "Work the language out from the contents when the name does not say" (detectLanguageFromContent) and "Git: mark lines changed since the last commit in the margin" (gitMarginMarks) are never written by Apply (xfail, BUG).
    """
    app = fresh
    skip = {"Let AI agents drive the editor (MCP)", "Default (mono-instance)", "Always in multi-instance mode",
            "Open session in a new instance (and save session automatically on exit)", "Apply", "Cancel", "Reset",
            "Add", "→", "←", "Use default value"}
    unwritten = []
    for name in PAGES:
        page(app, name)
        apply(app)                       # the first Apply writes the page as it is
        boxes = [c["title"] for c in controls(app) if c["class"] == "NSButton" and c.get("title")
                 and c["title"] not in skip and "state" in c]
        for title in boxes:
            before = stored(app)
            was = state(app, title)
            check(app, title, not was)
            apply(app)
            after = stored(app)
            changed = [k for k in set(before) | set(after) if before.get(k) != after.get(k)]
            if not changed:
                unwritten.append(f"{name}: {title}")
            page(app, name)
            check(app, title, bool(was))
            apply(app)
    assert unwritten == [], unwritten


@pytest.mark.case("SETTINGS-008")
def test_settings_008_localization_changes_the_interface_language_and_persists(fresh):
    """SETTINGS-008: Localization changes the interface language and persists

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, menu, launch
    Steps: With `fresh_app`, on General select "Français" in the Localization pop-up and Apply; read the main menu's top titles; restart; then select "English (english)" and Apply.
    Expect: after Apply the top menus are French (e.g. "Fichier", "Édition"), the dialog's page names are translated; after restart they are still French and pref localizationFile is "french.xml"; back to English, the menus read "File", "Edit" and the pref is empty.
    """
    app = fresh
    page(app, "General")
    pop = [c for c in controls(app) if c["class"] == "NSPopUpButton"][0]
    app.act(PREFS, "select", "Français", path=pop["path"])
    apply(app)
    close_prefs(app)

    def tops():
        # the menu bar shows each top item's submenu title
        return app.get("nsapp", "mainMenu.itemArray.submenu.title")
    app.wait(lambda: "Fichier" in tops(), message="French menus")
    assert "Fichier" in tops() and "File" not in tops()
    app.restart()
    assert "Fichier" in tops()
    assert stored(app).get("localizationFile") == "french.xml"
    U.PREFS = "Préférences"          # the helpers find the dialog by its (now French) title
    try:
        page(app, "General")
        assert U.category_table(app)["cells"][0][0] != "General"      # the page names are translated
        pop = [c for c in controls(app) if c["class"] == "NSPopUpButton"][0]
        app.act(U.PREFS, "select", "English (english)", path=pop["path"])
        app.click(U.PREFS, "Appliquer")
        app.wait(lambda: "File" in tops(), message="English menus")
        for w in app.windows():
            if w["title"] in ("Préférences", "Preferences") and w["visible"]:
                app.close_window(w["number"])
    finally:
        U.PREFS = PREFS
    assert "Edit" in tops()
    assert not stored(app).get("localizationFile")


@pytest.mark.case("SETTINGS-009")
def test_settings_009_remember_current_session_for_next_launch(fresh, tmp):
    """SETTINGS-009: Remember current session for next launch

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, files, launch
    Steps: With `fresh_app`, tick "Remember current session for next launch", Apply; open two files from `tmp`; restart with `session=True`; then untick it, Apply, restart with `session=True`.
    Expect: after the first restart both files are open again; after the second restart they are not (only an empty document); session.xml in the home is written only while the option is on.
    """
    app = fresh
    a, b = tmp / "one.txt", tmp / "two.txt"
    a.write_text("one\n")
    b.write_text("two\n")
    set_options(app, "General", checks={"Remember current session for next launch": True})
    app.restart(session=True)
    app.open(a)
    app.open(b)
    app.restart(session=True)
    paths = [d["path"] for d in app.docs() if d["path"]]
    assert any(app.same_path(p, a) for p in paths) and any(app.same_path(p, b) for p in paths)
    set_options(app, "General", checks={"Remember current session for next launch": False})
    app.restart(session=True)
    paths = [d["path"] for d in app.docs() if d["path"]]
    assert not any(app.same_path(p, a) for p in paths)


@pytest.mark.case("SETTINGS-010")
def test_settings_010_remember_which_panels_were_open_panel_by_panel(fresh):
    """SETTINGS-010: Remember which panels were open, panel by panel

    Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_DOC_MAP, IDM_VIEW_FUNC_LIST
    Channel: ui, launch
    Steps: With `fresh_app`, tick "Remember which panels were open", untick "    Document Map", keep "    Function List" ticked, Apply; show Document Map and Function List; restart.
    Expect: after restart Function List is shown (IDM_VIEW_FUNC_LIST checked) and Document Map is not (IDM_VIEW_DOC_MAP unchecked); pref panelStateKeep has documentMap false.
    """
    app = fresh
    set_options(app, "General", checks={"Remember which panels were open": True, "    Document Map": False,
                                       "    Function List": True})
    app.run("IDM_VIEW_DOC_MAP")
    app.run("IDM_VIEW_FUNC_LIST")
    # the View menu carries no checkmark for panels (a VIEW finding): the dock says what is shown
    app.wait(lambda: panel_shown(app, "documentMap") and panel_shown(app, "functionList"))
    app.restart()
    app.wait(lambda: panel_shown(app, "functionList"), message="Function List restored")
    assert not panel_shown(app, "documentMap")
    assert stored(app).get("panelStateKeep", {}).get("documentMap") in (False, 0)


@pytest.mark.case("SETTINGS-011")
def test_settings_011_multi_instance_radio_buttons_store_the_mode(fresh):
    """SETTINGS-011: Multi-instance radio buttons store the mode

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, prefs, launch
    Steps: With `fresh_app`, click the radio "Always in multi-instance mode", Apply; restart; open General.
    Expect: exactly one of the three radios is on and it is "Always in multi-instance mode" after restart; pref multiInstanceMode is 1; clicking "Default (mono-instance)" and Apply sets it back to 0.
    """
    app = fresh
    page(app, "General")
    app.click(PREFS, "Always in multi-instance mode")
    apply(app)
    close_prefs(app)
    app.restart()
    page(app, "General")
    radios = ["Default (mono-instance)", "Always in multi-instance mode",
              "Open session in a new instance (and save session automatically on exit)"]
    assert [state(app, r) for r in radios] == [0, 1, 0]
    assert stored(app).get("multiInstanceMode") == 1
    app.click(PREFS, "Default (mono-instance)")
    apply(app)
    assert stored(app).get("multiInstanceMode") == 0


def come_back_to(app):
    """What a user does after another program changed a file: switch away and back.
    The app looks at its files on disk when it becomes active (applicationDidBecomeActive:),
    as Notepad++ does on WM_ACTIVATEAPP."""
    # Hidden (Cmd+H) rather than deactivate: with no other application in front
    # (the VM), deactivate has nothing to hand the focus to and does nothing.
    app.invoke("nsapp", "hide:", [None])
    app.wait(lambda: not app.get("nsapp", "active"), timeout=5, message="the app inactive")
    app.invoke("nsapp", "unhide:", [None])
    app.invoke("nsapp", "activateIgnoringOtherApps:", [True])
    app.wait(lambda: app.get("nsapp", "active"), timeout=5, message="the app active again")


@pytest.mark.case("SETTINGS-012")
def test_settings_012_file_status_auto_detection_asks_updates_silently_scrolls_to(papp, tmp):
    """SETTINGS-012: File Status Auto-Detection asks, updates silently, scrolls to the end

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, files, modal, mcp
    Steps: Open a file from `tmp`; append a line to it on disk; with "File Status Auto-Detection" on and "    Update silently" off, queue alert answer 1 and bring the app to idle; then tick "    Update silently" and "    Scroll to the last line after update", Apply, append again; finally untick "File Status Auto-Detection", Apply, append again.
    Expect: first change: an alert about the file being modified by another program is logged and the text is reloaded; second: no alert, text reloaded, caret/first visible line at the end (SCI_GETCURRENTPOS == length); third: no alert and the text is not reloaded.
    """
    app = papp
    f = tmp / "watched.txt"
    f.write_text("one\n")
    app.open(f)
    app.answers(alerts=[1])
    with open(f, "a") as h:
        h.write("two\n")
    come_back_to(app)
    app.wait(lambda: (app.idle(0.2), app.text())[1] == "one\ntwo\n", timeout=15, message="reload after asking")
    log = app.modal_log()
    assert any(e["kind"] == "alert" for e in log), log
    set_options(app, "General", checks={"    Update silently": True, "    Scroll to the last line after update": True})
    with open(f, "a") as h:
        h.write("three\n")
    come_back_to(app)
    app.wait(lambda: (app.idle(0.2), app.text())[1] == "one\ntwo\nthree\n", timeout=15, message="silent reload")
    assert not [e for e in app.modal_log() if e["kind"] == "alert"]
    app.wait(lambda: app.sci(SCI_GETCURRENTPOS) == app.sci(SCI_GETLENGTH), message="caret at the end")
    set_options(app, "General", checks={"File Status Auto-Detection": False})
    with open(f, "a") as h:
        h.write("four\n")
    come_back_to(app)
    for _ in range(10):
        app.idle(0.2)
    assert app.text() == "one\ntwo\nthree\n"
    assert not [e for e in app.modal_log() if e["kind"] == "alert"]


@pytest.mark.case("SETTINGS-013")
def test_settings_013_autodetect_character_encoding_on_and_off(papp, tmp):
    """SETTINGS-013: Autodetect character encoding on and off

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, files, mcp
    Steps: Write a Windows-1251 Russian text file into `tmp`; open it with "Autodetect character encoding" on; close it, untick the option, Apply, open it again.
    Expect: with the option on the document's encoding (file_encoding tool) is windows-1251 and the text reads as Russian; with it off the file opens as ANSI/Latin and the text is not the Russian original.
    """
    app = papp
    text = "Привет, мир! Это проверка автоматического определения кодировки текста.\n"
    f = tmp / "ru.txt"
    f.write_bytes(text.encode("cp1251"))
    app.open(f)
    assert "1251" in app.doc()["encoding"], app.doc()
    assert app.text() == text
    app.close_all()
    set_options(app, "General", checks={"Autodetect character encoding": False})
    app.open(f)
    assert "1251" not in app.doc()["encoding"]
    assert app.text() != text


@pytest.mark.case("SETTINGS-014")
def test_settings_014_status_bar_hide_hides_and_shows_the_status_bar(papp):
    """SETTINGS-014: Status Bar: Hide hides and shows the status bar

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, launch
    Steps: Tick "Status Bar: Hide", Apply; read the main window's controls; restart; untick, Apply.
    Expect: while ticked, the status bar fields (NppStatusPathField and the "length: … Ln: …" field) are not listed as visible; still hidden after restart; unticked, they are visible again.
    """
    app = papp
    app.new("abc")
    assert status_text(app)
    set_options(app, "General", checks={"Status Bar: Hide": True})
    assert status_text(app) == ""
    app.restart()
    app.new("abc")
    assert status_text(app) == ""
    set_options(app, "General", checks={"Status Bar: Hide": False})
    assert status_text(app)


@pytest.mark.case("SETTINGS-015")
def test_settings_015_show_the_toolbar(papp):
    """SETTINGS-015: Show the toolbar

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, launch
    Steps: On Toolbar untick "Show the toolbar", Apply; read `ui(main)["toolbar"]["visible"]`; restart; tick it again.
    Expect: the toolbar is not visible while unticked, including after restart; visible again when ticked.
    """
    app = papp
    def toolbar_visible():
        tb = app.ui("main").get("toolbar") or {}
        return bool(tb.get("visible"))
    assert toolbar_visible()
    set_options(app, "Toolbar", checks={"Show the toolbar": False})
    assert not toolbar_visible()
    app.restart()
    assert not toolbar_visible()
    set_options(app, "Toolbar", checks={"Show the toolbar": True})
    assert toolbar_visible()


@pytest.mark.case("SETTINGS-016")
def test_settings_016_toolbar_buttons_and_size_reach_the_window_s_toolbar(papp):
    """SETTINGS-016: Toolbar buttons and size reach the window's toolbar

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui
    Steps: For each of "Icons only", "Icons and labels", "Labels only" in "Toolbar buttons", and each of "Regular", "Small" in "Toolbar size": select, Apply, read the window's toolbar display mode and style (`e2e_invoke get window toolbar.displayMode`, `toolbarStyle`).
    Expect: display mode is icon-only (2), icon-and-label (1), label-only (3) respectively; "Icons and labels" or "Regular" gives the expanded toolbar style, "Small" with icons only the unified-compact style.
    """
    app = papp
    seen = {}
    for item in ("Icons only", "Icons and labels", "Labels only"):
        set_options(app, "Toolbar", popups={"Toolbar buttons": item}, close=False)
        seen[item] = (app.get("window", "toolbar.displayMode"), app.get("window", "toolbarStyle"))
    assert seen["Icons only"][0] == 2 and seen["Icons and labels"][0] == 1 and seen["Labels only"][0] == 3, seen
    assert seen["Icons and labels"][1] == 1, seen          # NSWindowToolbarStyleExpanded
    set_options(app, "Toolbar", popups={"Toolbar buttons": "Icons only", "Toolbar size": "Regular"}, close=False)
    assert app.get("window", "toolbarStyle") == 1
    set_options(app, "Toolbar", popups={"Toolbar size": "Small"})
    assert app.get("window", "toolbarStyle") == 4           # NSWindowToolbarStyleUnifiedCompact


@pytest.mark.case("SETTINGS-017")
def test_settings_017_icon_set_colour_and_colorization_change_the_toolbar_icons(papp, tmp):
    """SETTINGS-017: Icon set, colour and colorization change the toolbar icons

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, snapshot
    Steps: Set "Color choice" to "Green" and "Colorization" to "Complete", Apply, take a toolbar snapshot; set "Default"/"Partial", Apply, snapshot; select "Filled Fluent UI", Apply, snapshot; set "Custom" with "Color choice: Custom" field "FF00FF", Apply, snapshot.
    Expect: with Green/Complete more than 90% of the New button's opaque pixels are green; with Default under 10%; the filled set differs from the outline set; Custom gives magenta pixels; the preferences toolbarIconColour, toolbarColorizeComplete, toolbarFilledIcons and toolbarIconCustomColour are stored. (Needs a toolbar image hook if the window snapshot does not include the toolbar, see report.)
    """
    app = papp

    def shares(img):
        # the toolbar's icons: the strip right of the window buttons and the title
        # (the green window button would count otherwise); colored = clearly not grey
        w, h = img.size
        scale = app.get("window", "backingScaleFactor") or 1
        strip = img.crop((int(220 * scale), 0, w, int(52 * scale)))
        green = magenta = colored = 0
        for r, g, b in strip.get_flattened_data():
            if max(r, g, b) - min(r, g, b) < 40:
                continue
            colored += 1
            green += g > r + 40 and g > b + 40
            magenta += r > 150 and b > 150 and g < 110
        return colored, green / max(colored, 1), magenta / max(colored, 1)

    set_options(app, "Toolbar", popups={"Color choice": "Green", "Colorization": "Complete"})
    col_g, green_g, _ = shares(U.frame_snapshot(app, tmp / "green.png"))
    set_options(app, "Toolbar", popups={"Color choice": "Default", "Colorization": "Partial"})
    outline = U.frame_snapshot(app, tmp / "default.png")
    _, green_d, magenta_d = shares(outline)
    set_options(app, "Toolbar", popups={"Icons": "Filled Fluent UI"})
    filled = U.frame_snapshot(app, tmp / "filled.png")
    set_options(app, "Toolbar", popups={"Color choice": "Custom"}, fields={"Color choice: Custom": "FF00FF"})
    _, _, magenta_c = shares(U.frame_snapshot(app, tmp / "custom.png"))
    assert col_g > 200 and green_g > 0.9, (col_g, green_g)
    assert green_d < 0.1, green_d
    assert list(filled.get_flattened_data()) != list(outline.get_flattened_data())
    # Partial colorization tints part of each icon: magenta is there, where Default has none
    assert magenta_c > 0.2 and magenta_d < 0.02, (magenta_c, magenta_d)
    s = stored(app)
    assert {"toolbarIconColour", "toolbarColorizeComplete", "toolbarFilledIcons", "toolbarIconCustomColour"} <= set(s), sorted(s)


@pytest.mark.case("SETTINGS-018")
def test_settings_018_font_name_and_size_apply_to_the_editor(papp):
    """SETTINGS-018: Font name and size apply to the editor

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp, launch
    Steps: On Editing 1 set "Font name:" to "Courier" and "Font size" to 17, Apply; read SCI_STYLEGETFONT and SCI_STYLEGETSIZE of STYLE_DEFAULT; restart.
    Expect: STYLE_DEFAULT uses "Courier" at size 17, and so does a style of the current lexer that has no font of its own; unchanged after restart.
    """
    app = papp
    app.new("int x; // c\n", language="cpp")
    set_options(app, "Editing 1", fields={"Font name:": "Courier", "Font size": 17})

    def font(style):
        return app.sci(SCI_STYLEGETFONT, style, returns="string"), app.sci(SCI_STYLEGETSIZE, style)
    assert stored(app).get("fontName") == "Courier" and stored(app).get("fontSize") == 17
    assert font(STYLE_DEFAULT) == ("Courier", 17)
    assert font(SCE_C_WORD) == ("Courier", 17)
    app.restart()
    app.new("int x;\n", language="cpp")
    assert font(STYLE_DEFAULT) == ("Courier", 17)
    assert font(SCE_C_WORD) == ("Courier", 17)


@pytest.mark.case("SETTINGS-019")
def test_settings_019_caret_width_and_blink_rate(papp):
    """SETTINGS-019: Caret width and blink rate

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: For each "Caret Settings: Width" item (Hidden, 1 pixel, 2 pixels, 3 pixels) select and Apply; set "Caret Settings: Blink rate" to 0 then 530, Apply.
    Expect: SCI_GETCARETWIDTH is 0, 1, 2, 3 respectively; SCI_GETCARETPERIOD is 0 then 530.
    """
    app = papp
    app.new("text")
    widths = []
    for item in ("Hidden", "1 pixel", "2 pixels", "3 pixels"):
        set_options(app, "Editing 1", popups={"Caret Settings: Width": item}, close=False)
        widths.append(app.sci(SCI_GETCARETWIDTH))
    assert widths == [0, 1, 2, 3]
    set_options(app, "Editing 1", fields={"Caret Settings: Blink rate": 0}, close=False)
    assert app.sci(SCI_GETCARETPERIOD) == 0
    set_options(app, "Editing 1", fields={"Caret Settings: Blink rate": 530})
    assert app.sci(SCI_GETCARETPERIOD) == 530


@pytest.mark.case("SETTINGS-020")
def test_settings_020_current_line_indicator_none_background_frame_with_width(papp):
    """SETTINGS-020: Current line indicator: none, background, frame with width

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Select "None", Apply; select "Frame" with "Frame: Width" 3, Apply; select "Highlight Background", Apply.
    Expect: None: SCI_GETCARETLINEVISIBLE 0; Frame: visible and SCI_GETCARETLINEFRAME 3; Background: visible and SCI_GETCARETLINEFRAME 0; a frame width of 9 is stored as 6 (clamped 1..6).
    """
    app = papp
    app.new("one\ntwo\n")
    set_options(app, "Editing 1", popups={"Current Line Indicator": "Frame"}, fields={"Frame: Width": 3}, close=False)
    assert app.sci(SCI_GETCARETLINEVISIBLE) and app.sci(SCI_GETCARETLINEFRAME) == 3
    set_options(app, "Editing 1", popups={"Current Line Indicator": "Highlight Background"}, close=False)
    assert app.sci(SCI_GETCARETLINEVISIBLE) and app.sci(SCI_GETCARETLINEFRAME) == 0
    before = stored(app)
    set_options(app, "Editing 1", popups={"Current Line Indicator": "Frame"}, fields={"Frame: Width": 9})
    changed = U.diff(before, stored(app))
    assert app.sci(SCI_GETCARETLINEFRAME) == 6
    assert changed.get("currentLineFrameWidth") == 6, changed


@pytest.mark.case("SETTINGS-020")
def test_settings_020_none_leaves_the_current_line_alone(papp):
    """SETTINGS-020 (None): no current-line indicator at all"""
    app = papp
    app.new("one\ntwo\n")
    set_options(app, "Editing 1", popups={"Current Line Indicator": "None"})
    assert stored(app).get("currentLineHighlightMode") == 0
    assert app.sci(SCI_GETCARETLINEVISIBLE) == 0


@pytest.mark.case("SETTINGS-021")
def test_settings_021_scrolling_beyond_the_last_line_and_virtual_space(papp):
    """SETTINGS-021: Scrolling beyond the last line and virtual space

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Untick "Enable scrolling beyond last line" and "Enable virtual space", Apply; tick both, Apply; with virtual space on press `right` three times at the end of a short line.
    Expect: off: SCI_GETENDATLASTLINE != 0 and SCI_GETVIRTUALSPACEOPTIONS lacks SCVS_USERACCESSIBLE; on: SCI_GETENDATLASTLINE == 0, the flag is set and the caret's virtual space (SCI_GETSELECTIONNCARETVIRTUALSPACE 0) is 3.
    """
    app = papp
    app.new("ab\ncd\n")
    set_options(app, "Editing 1", checks={"Enable scrolling beyond last line": False, "Enable virtual space": False}, close=False)
    assert app.sci(SCI_GETENDATLASTLINE) != 0
    assert not app.sci(SCI_GETVIRTUALSPACEOPTIONS) & SCVS_USERACCESSIBLE
    set_options(app, "Editing 1", checks={"Enable scrolling beyond last line": True, "Enable virtual space": True})
    assert app.sci(SCI_GETENDATLASTLINE) == 0
    assert app.sci(SCI_GETVIRTUALSPACEOPTIONS) & SCVS_USERACCESSIBLE
    app.select(1, 3)
    app.keys("right", "right", "right")
    assert app.sci(SCI_GETSELECTIONNCARETVIRTUALSPACE, 0) == 3


@pytest.mark.case("SETTINGS-022")
def test_settings_022_copy_cut_line_without_selection(papp):
    """SETTINGS-022: Copy/Cut line without selection

    Covers: IDM_SETTING_PREFERENCE, IDM_EDIT_COPY, IDM_EDIT_CUT
    Channel: ui, clipboard, mcp
    Steps: Text "first\\nsecond\\nthird\\n", caret on line 2 with no selection; with the option ticked run IDM_EDIT_COPY and IDM_EDIT_CUT; untick it, Apply, put the caret in "first" and run IDM_EDIT_COPY with the clipboard set to "kept".
    Expect: ticked: the clipboard holds "second\\n" and Cut leaves "first\\nthird\\n"; unticked: the clipboard still reads "kept" and the text is unchanged.
    """
    app = papp
    app.new("first\nsecond\nthird\n")
    app.select(2, 3)
    app.run("IDM_EDIT_COPY")
    assert app.clipboard() == "second\n"
    app.run("IDM_EDIT_CUT")
    assert app.text() == "first\nthird\n"
    set_options(app, "Editing 1", checks={"Enable Copy/Cut Line without selection": False})
    app.clipboard(set="kept")
    app.select(1, 2)
    app.run("IDM_EDIT_COPY", expect_ran=False)
    assert app.clipboard() == "kept"
    assert app.text() == "first\nthird\n"


@pytest.mark.case("SETTINGS-023")
def test_settings_023_dragging_selected_text_and_keeping_the_selection_on_a_right(papp):
    """SETTINGS-023: Dragging selected text and keeping the selection on a right click

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp, prefs
    Steps: Untick "Selected text can be dragged", Apply, read SCI_GETDRAGDROPENABLED; tick it, Apply; tick "Keep selection when right-click outside of selection", Apply, select "abc" in "abc def" and right-click at "def" (needs an editor right-click hook, see report); untick and repeat.
    Expect: SCI_GETDRAGDROPENABLED 0 while unticked, 1 while ticked; with "Keep selection" ticked the selection is still 0..3 after the right click, unticked the caret moves to the click and the selection is empty. (rightClickKeepsSelection is stored but used nowhere in the port: xfail, BUG.)
    """
    app = papp
    app.new("abc def")
    set_options(app, "Editing 1", checks={"Selected text can be dragged": False}, close=False)
    assert app.sci(SCI_GETDRAGDROPENABLED) == 0
    set_options(app, "Editing 1", checks={"Selected text can be dragged": True}, close=False)
    assert app.sci(SCI_GETDRAGDROPENABLED) == 1
    set_options(app, "Editing 1", checks={"Keep selection when right-click outside of selection": True})
    app.select(1, 1, 1, 4)
    app.mouse(view="main", point={"line": 1, "column": 6}, button="right")
    kept = (app.sci(SCI_GETSELECTIONSTART), app.sci(SCI_GETSELECTIONEND))
    set_options(app, "Editing 1", checks={"Keep selection when right-click outside of selection": False})
    app.select(1, 1, 1, 4)
    app.mouse(view="main", point={"line": 1, "column": 6}, button="right")
    moved = (app.sci(SCI_GETSELECTIONSTART), app.sci(SCI_GETSELECTIONEND))
    assert kept == (0, 3), kept
    assert moved[0] == moved[1] == 5, moved


@pytest.mark.case("SETTINGS-024")
def test_settings_024_word_wrap_and_the_line_wrap_method(papp):
    """SETTINGS-024: Word wrap and the line wrap method

    Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_WRAP
    Channel: ui, mcp, menu
    Steps: Tick "Word wrap", Apply; for each "Line Wrap" item (Default, Aligned, Indent) select and Apply.
    Expect: SCI_GETWRAPMODE != SC_WRAP_NONE and IDM_VIEW_WRAP is checked; SCI_GETWRAPINDENTMODE is SC_WRAPINDENT_FIXED, SC_WRAPINDENT_SAME, SC_WRAPINDENT_INDENT respectively.
    """
    app = papp
    app.new("a long line " * 40)
    modes = []
    for item in ("Default", "Aligned", "Indent"):
        set_options(app, "Editing 2", checks={"Word wrap": True}, popups={"Line Wrap": item}, close=False)
        assert app.sci(SCI_GETWRAPMODE) != SC_WRAP_NONE and app.checked("IDM_VIEW_WRAP")
        modes.append(app.sci(SCI_GETWRAPINDENTMODE))
    set_options(app, "Editing 2", checks={"Word wrap": False}, popups={"Line Wrap": "Aligned"})
    assert modes == [SC_WRAPINDENT_FIXED, SC_WRAPINDENT_SAME, SC_WRAPINDENT_INDENT]


@pytest.mark.case("SETTINGS-025")
def test_settings_025_show_space_and_tab_show_indent_guide(papp):
    """SETTINGS-025: Show Space and Tab, Show Indent Guide

    Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_TAB_SPACE, IDM_VIEW_INDENT_GUIDE
    Channel: ui, mcp, menu
    Steps: Tick "Show Space and Tab" and untick "Show Indent Guide", Apply; then the reverse.
    Expect: SCI_GETVIEWWS != SCWS_INVISIBLE and IDM_VIEW_TAB_SPACE checked, SCI_GETINDENTATIONGUIDES == SC_IV_NONE and IDM_VIEW_INDENT_GUIDE unchecked; then the opposite.
    """
    app = papp
    app.new("\tx\n")
    set_options(app, "Editing 2", checks={"Show Space and Tab": True, "Show Indent Guide": False}, close=False)
    assert app.sci(SCI_GETVIEWWS) != SCWS_INVISIBLE and app.checked("IDM_VIEW_TAB_SPACE")
    assert app.sci(SCI_GETINDENTATIONGUIDES) == SC_IV_NONE
    set_options(app, "Editing 2", checks={"Show Space and Tab": False, "Show Indent Guide": True})
    assert app.sci(SCI_GETVIEWWS) == SCWS_INVISIBLE and not app.checked("IDM_VIEW_TAB_SPACE")
    assert app.sci(SCI_GETINDENTATIONGUIDES) != SC_IV_NONE


@pytest.mark.case("SETTINGS-025")
def test_settings_025_the_indent_guide_menu_item_follows_the_option(papp):
    """SETTINGS-025 (menu): IDM_VIEW_INDENT_GUIDE is checked while the guides are shown"""
    app = papp
    app.new("\tx\n")
    set_options(app, "Editing 2", checks={"Show Indent Guide": True})
    assert app.sci(SCI_GETINDENTATIONGUIDES) != SC_IV_NONE
    assert app.checked("IDM_VIEW_INDENT_GUIDE")


@pytest.mark.case("SETTINGS-026")
def test_settings_026_smooth_font_custom_selected_text_foreground_multi_editing(papp):
    """SETTINGS-026: Smooth font, custom selected-text foreground, Multi-Editing

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Tick "Enable smooth font", "Apply custom color to selected text foreground", untick "Enable Multi-Editing (Cmd+click/selection)", Apply; then the reverse, Apply.
    Expect: first: SCI_GETFONTQUALITY is SC_EFF_QUALITY_LCD_OPTIMIZED, SCI_GETELEMENTISSET(SC_ELEMENT_SELECTION_TEXT) is 1, SCI_GETMULTIPLESELECTION 0; reversed: font quality default, the selection text element not set, SCI_GETMULTIPLESELECTION 1.
    """
    app = papp
    app.new("text")
    set_options(app, "Editing 2", checks={"Enable smooth font": True, "Apply custom color to selected text foreground": True,
                                          "Enable Multi-Editing (Cmd+click/selection)": False}, close=False)
    assert app.sci(SCI_GETFONTQUALITY) == SC_EFF_QUALITY_LCD_OPTIMIZED
    assert app.sci(SCI_GETELEMENTISSET, SC_ELEMENT_SELECTION_TEXT) == 1
    assert app.sci(SCI_GETMULTIPLESELECTION) == 0
    set_options(app, "Editing 2", checks={"Enable smooth font": False, "Apply custom color to selected text foreground": False,
                                          "Enable Multi-Editing (Cmd+click/selection)": True})
    assert app.sci(SCI_GETFONTQUALITY) != SC_EFF_QUALITY_LCD_OPTIMIZED
    assert app.sci(SCI_GETELEMENTISSET, SC_ELEMENT_SELECTION_TEXT) == 0
    assert app.sci(SCI_GETMULTIPLESELECTION) == 1


@pytest.mark.case("SETTINGS-027")
def test_settings_027_folding_commands_toggle_when_asked(papp):
    """SETTINGS-027: Folding commands toggle when asked

    Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_FOLD_CURRENT
    Channel: ui, mcp
    Steps: C++ text "int f() {\\n    return 0;\\n}\\n", caret on line 2; tick "Make current level folding/unfolding commands toggleable", Apply; run IDM_VIEW_FOLD_CURRENT twice; untick, Apply, run it twice.
    Expect: toggleable: first run folds (SCI_GETFOLDEXPANDED(0)==0), second unfolds; not toggleable: both runs leave it folded.
    """
    app = papp
    app.new("int f() {\n    return 0;\n}\n", language="cpp")
    U.wait_folds(app)
    set_options(app, "Editing 2", checks={"Make current level folding/unfolding commands toggleable": True})
    app.select(2, 5)
    app.run("IDM_VIEW_FOLD_CURRENT")
    assert app.sci(SCI_GETFOLDEXPANDED, 0) == 0
    app.run("IDM_VIEW_FOLD_CURRENT")
    assert app.sci(SCI_GETFOLDEXPANDED, 0) == 1
    set_options(app, "Editing 2", checks={"Make current level folding/unfolding commands toggleable": False})
    app.select(2, 5)
    app.run("IDM_VIEW_FOLD_CURRENT")
    app.run("IDM_VIEW_FOLD_CURRENT")
    assert app.sci(SCI_GETFOLDEXPANDED, 0) == 0


@pytest.mark.case("SETTINGS-028")
def test_settings_028_eol_and_non_printing_character_appearance(papp, tmp):
    """SETTINGS-028: EOL and non-printing character appearance

    Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_NPC, IDM_VIEW_NPC_CCUNIEOL
    Channel: ui, mcp
    Steps: Text with a no-break space and U+0001; show non-printing characters (IDM_VIEW_NPC on); select "Non-Printing Characters" "Abbreviation", Apply, read SCI_GETREPRESENTATION of "\\xC2\\xA0"; select "Codepoint", Apply; select "EOL (CRLF)" "Plain Text", Apply, read SCI_GETREPRESENTATIONAPPEARANCE of "\\n" with EOL shown.
    Expect: "NBSP", then "U+00A0"; the EOL representation appearance is SC_REPRESENTATION_PLAIN with Plain Text and not with Default.
    """
    app = papp
    # e2e_sci passes wParam as a number only, so SCI_GETREPRESENTATION (key in wParam) cannot be asked:
    # the representation is checked as it is drawn (the caret hidden, so its blink does not count).
    app.new("a b\u0001c\nnext\n")
    if not app.checked("IDM_VIEW_NPC"):
        app.run("IDM_VIEW_NPC")
    try:
        set_options(app, "Editing 2", popups={"Non-Printing Characters": "Abbreviation"})
        abbr = U.still_snapshot(app, tmp / "abbr.png")
        assert list(U.still_snapshot(app, tmp / "abbr2.png").get_flattened_data()) == list(abbr.get_flattened_data())
        set_options(app, "Editing 2", popups={"Non-Printing Characters": "Codepoint"})
        code = U.still_snapshot(app, tmp / "code.png")
        assert list(abbr.get_flattened_data()) != list(code.get_flattened_data())
        if not app.checked("IDM_VIEW_EOL"):
            app.run("IDM_VIEW_EOL")
        set_options(app, "Editing 2", popups={"EOL (CRLF)": "Default"})
        eol_default = U.still_snapshot(app, tmp / "eol-default.png")
        set_options(app, "Editing 2", popups={"EOL (CRLF)": "Plain Text"})
        eol_plain = U.still_snapshot(app, tmp / "eol-plain.png")
        assert list(eol_default.get_flattened_data()) != list(eol_plain.get_flattened_data())
    finally:
        for cmd in ("IDM_VIEW_NPC", "IDM_VIEW_EOL"):
            if app.checked(cmd):
                app.run(cmd)


@pytest.mark.case("SETTINGS-029")
def test_settings_029_custom_colours_for_eol_and_non_printing_characters_c0_c1_app(papp, tmp):
    """SETTINGS-029: Custom colours for EOL and non-printing characters, C0/C1 appearance

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Tick "    EOL (CRLF): Custom Color", "    Non-Printing Characters: Custom Color" and "    Apply Appearance settings to C0, C1 & Unicode EOL", Apply; read SCI_GETREPRESENTATIONCOLOUR for "\\n", the NBSP and U+0001 with IDM_VIEW_NPC and IDM_VIEW_NPC_CCUNIEOL on; untick all, Apply.
    Expect: with the boxes ticked the representations carry a colour (SCI_GETREPRESENTATIONAPPEARANCE has SC_REPRESENTATION_COLOUR) and U+0001 uses the non-printing appearance; unticked, no colour flag; prefs eolCustomColour, npcCustomColour, npcIncludeCcUniEol follow.
    """
    app = papp
    app.new("a b\u0001c\nnext\n")
    for cmd in ("IDM_VIEW_NPC", "IDM_VIEW_NPC_CCUNIEOL", "IDM_VIEW_EOL"):
        if not app.checked(cmd):
            app.run(cmd)
    try:
        plain = U.still_snapshot(app, tmp / "plain.png")
        boxes = {"    EOL (CRLF): Custom Color": True, "    Non-Printing Characters: Custom Color": True,
                 "    Apply Appearance settings to C0, C1 & Unicode EOL": True}
        set_options(app, "Editing 2", checks=boxes)
        s = stored(app)
        assert s.get("eolCustomColour") in (True, 1) and s.get("npcCustomColour") in (True, 1)
        assert s.get("npcIncludeCcUniEol") in (True, 1)
        coloured = U.still_snapshot(app, tmp / "coloured.png")
        assert list(plain.get_flattened_data()) != list(coloured.get_flattened_data())
        set_options(app, "Editing 2", checks={k: False for k in boxes})
        s = stored(app)
        assert s.get("eolCustomColour") in (False, 0) and s.get("npcCustomColour") in (False, 0)
        assert s.get("npcIncludeCcUniEol") in (False, 0)
        assert list(U.still_snapshot(app, tmp / "again.png").get_flattened_data()) == list(plain.get_flattened_data())
    finally:
        for cmd in ("IDM_VIEW_NPC", "IDM_VIEW_NPC_CCUNIEOL", "IDM_VIEW_EOL"):
            if app.checked(cmd):
                app.run(cmd)


@pytest.mark.case("SETTINGS-030")
def test_settings_030_prevent_control_character_typing(papp):
    """SETTINGS-030: Prevent control character typing

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: Text "ab", caret at the end; with "Prevent control character (C0 code) typing into document" ticked press ctrl+b (inserts U+0002 by default); untick, Apply, press ctrl+b again.
    Expect: ticked: text stays "ab"; unticked: text is "ab\\x02".
    """
    app = papp
    # On a Mac ctrl+B is "move back"; a C0 character arrives the way an input method delivers it.
    app.new("ab")
    app.select(1, 3)
    app.type("\x02")
    assert app.text() == "ab"
    set_options(app, "Editing 2", checks={"Prevent control character (C0 code) typing into document": False})
    app.select(1, 3)
    app.type("\x02")
    assert app.text() == "ab\x02"


@pytest.mark.case("SETTINGS-031")
def test_settings_031_appearance_light_dark_picks_the_light_dark_theme(papp):
    """SETTINGS-031: Appearance light / dark picks the light / dark theme

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp, launch
    Steps: On Dark Mode select Appearance "Light mode", Apply, read SCI_STYLEGETBACK(STYLE_DEFAULT); select "Dark mode", Apply, read it and the app's effective appearance (`e2e_invoke get nsapp effectiveAppearance.name`); restart; set "Follow the system" at the end.
    Expect: light: 0xFFFFFF (Default theme); dark: 0x3F3F3F (DarkModeDefault) and an appearance name containing "Dark"; still dark after restart; pref appearanceMode 1 / 2.
    """
    app = papp
    app.new("int x;\n", language="cpp")
    set_options(app, "Dark Mode", popups={"Appearance": "Light mode"}, close=False)
    assert app.sci(SCI_STYLEGETBACK, STYLE_DEFAULT) == 0xFFFFFF
    assert stored(app).get("appearanceMode") == 1
    set_options(app, "Dark Mode", popups={"Appearance": "Dark mode"})
    assert app.sci(SCI_STYLEGETBACK, STYLE_DEFAULT) == 0x3F3F3F
    assert "Dark" in str(app.get("nsapp", "effectiveAppearance.name"))
    assert stored(app).get("appearanceMode") == 2
    app.restart()
    app.new("int x;\n", language="cpp")
    assert app.sci(SCI_STYLEGETBACK, STYLE_DEFAULT) == 0x3F3F3F
    assert "Dark" in str(app.get("nsapp", "effectiveAppearance.name"))
    set_options(app, "Dark Mode", popups={"Appearance": "Follow the system"})
    assert stored(app).get("appearanceMode") == 0


@pytest.mark.case("SETTINGS-032")
def test_settings_032_the_light_and_dark_theme_pop_ups_list_every_theme_and_choose(papp):
    """SETTINGS-032: The light and dark theme pop-ups list every theme and choose the one used

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: With Appearance "Light mode", select "Monokai" in "Light theme", Apply; select Appearance "Dark mode" and "Dark theme" "Deep Black", Apply; read STYLE_DEFAULT colours each time; for each item of the pop-up, select it and Apply.
    Expect: the pop-ups list at least 22 themes including Default, DarkModeDefault, Monokai; Monokai gives back 0x222827 (272822 in BGR) and fore 0xF2F8F8; every theme applied gives a default background and at least 5 styled C++ styles differing from Default; prefs lightThemeName / darkThemeName hold the chosen names.
    """
    app = papp
    app.new("#include <x>\n// c\nint main() { return \"s\" + 1; }\n", language="cpp")
    page(app, "Dark Mode")
    themes = control_for(app, "Light theme", kinds=("NSPopUpButton",))["items"]
    assert len(themes) >= 22 and {"Default", "DarkModeDefault", "Monokai"} <= set(themes), themes
    assert control_for(app, "Dark theme", kinds=("NSPopUpButton",))["items"] == themes
    set_options(app, "Dark Mode", popups={"Appearance": "Light mode", "Light theme": "Monokai"}, close=False)
    assert app.sci(SCI_STYLEGETBACK, STYLE_DEFAULT) == 0x222827
    assert app.sci(SCI_STYLEGETFORE, STYLE_DEFAULT) == 0xF2F8F8
    set_options(app, "Dark Mode", popups={"Appearance": "Dark mode", "Dark theme": "Deep Black"}, close=False)
    deep = app.sci(SCI_STYLEGETBACK, STYLE_DEFAULT)
    s = stored(app)
    assert s.get("lightThemeName") == "Monokai" and s.get("darkThemeName") == "Deep Black"
    assert deep != 0x222827
    # every theme, applied as the light theme, colours the C++ styles its own way
    set_options(app, "Dark Mode", popups={"Appearance": "Light mode", "Light theme": "Default"}, close=False)
    def colours():
        return [(app.sci(SCI_STYLEGETFORE, st), app.sci(SCI_STYLEGETBACK, st)) for st in range(20)]
    base = colours()
    same = []
    for name in themes:
        if name == "Default":
            continue
        set_options(app, "Dark Mode", popups={"Light theme": name}, close=False)
        if sum(a != b for a, b in zip(base, colours())) < 5:
            same.append(name)
    close_prefs(app)
    assert same == [], same


@pytest.mark.case("SETTINGS-033")
def test_settings_033_bookmark_and_fold_margins_padding(papp):
    """SETTINGS-033: Bookmark and fold margins, padding

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Untick "Display bookmark" and "Show the fold margin", set "Padding: Left" 5 and "Padding: Right" 7, Apply; set padding 12, Apply; restore.
    Expect: SCI_GETMARGINWIDTHN(1) == 0 and (2) == 0; SCI_GETMARGINLEFT 5, SCI_GETMARGINRIGHT 7; a padding of 12 is stored as 9 (clamped 0..9); restored, margin 2 width > 0.
    """
    app = papp
    app.new("x\n")
    set_options(app, "Margins/Border/Edge", checks={"Display bookmark": False, "Show the fold margin": False},
                fields={"Padding: Left": 5, "Padding: Right": 7}, close=False)
    assert app.sci(SCI_GETMARGINWIDTHN, 1) == 0 and app.sci(SCI_GETMARGINWIDTHN, 2) == 0
    assert app.sci(SCI_GETMARGINLEFT) == 5 and app.sci(SCI_GETMARGINRIGHT) == 7
    set_options(app, "Margins/Border/Edge", fields={"Padding: Left": 12}, close=False)
    assert stored(app).get("paddingLeft") == 9 and app.sci(SCI_GETMARGINLEFT) == 9
    set_options(app, "Margins/Border/Edge", checks={"Display bookmark": True, "Show the fold margin": True},
                fields={"Padding: Left": 0, "Padding: Right": 0})
    assert app.sci(SCI_GETMARGINWIDTHN, 2) > 0 and app.sci(SCI_GETMARGINWIDTHN, 1) > 0


@pytest.mark.case("SETTINGS-034")
def test_settings_034_vertical_edge_one_line_several_lines_background(papp):
    """SETTINGS-034: Vertical edge: one line, several lines, background

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Select "A line" with columns "80", Apply; columns "80 100 120", Apply; "Background mode" with "72", Apply; "None", Apply.
    Expect: EDGE_LINE with SCI_GETEDGECOLUMN 80; EDGE_MULTILINE with SCI_GETMULTIEDGECOLUMN(1) 100; EDGE_BACKGROUND with column 72; EDGE_NONE.
    """
    app = papp
    app.new("x\n")
    edge = "Vertical Edge Settings"
    cols = "Columns (space separated)"
    set_options(app, "Margins/Border/Edge", popups={edge: "A line"}, fields={cols: "80"}, close=False)
    assert app.sci(SCI_GETEDGEMODE) == EDGE_LINE and app.sci(SCI_GETEDGECOLUMN) == 80
    set_options(app, "Margins/Border/Edge", fields={cols: "80 100 120"}, close=False)
    assert app.sci(SCI_GETEDGEMODE) == EDGE_MULTILINE and app.sci(SCI_GETMULTIEDGECOLUMN, 1) == 100
    set_options(app, "Margins/Border/Edge", popups={edge: "Background mode"}, fields={cols: "72"}, close=False)
    assert app.sci(SCI_GETEDGEMODE) == EDGE_BACKGROUND and app.sci(SCI_GETEDGECOLUMN) == 72
    set_options(app, "Margins/Border/Edge", popups={edge: "None"}, fields={cols: "80"})
    assert app.sci(SCI_GETEDGEMODE) == EDGE_NONE


@pytest.mark.case("SETTINGS-035")
def test_settings_035_fold_margin_style(papp):
    """SETTINGS-035: Fold margin style

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: C++ document; for each "Fold Margin Style" item (Simple, Arrow, Circle tree, Box tree, None) select and Apply.
    Expect: SCI_MARKERSYMBOLDEFINED(SC_MARKNUM_FOLDER) is SC_MARK_MINUS/PLUS family for Simple, SC_MARK_ARROW for Arrow, SC_MARKNUM_FOLDEROPEN SC_MARK_CIRCLEMINUS for Circle tree, SC_MARK_BOXPLUS for Box tree; None makes SCI_GETMARGINWIDTHN(2) 0.
    """
    app = papp
    app.new("int f() {\n    return 0;\n}\n", language="cpp")
    U.wait_folds(app)
    got = {}
    for item in ("Simple", "Arrow", "Circle tree", "Box tree"):
        set_options(app, "Margins/Border/Edge", popups={"Fold Margin Style": item}, close=False)
        got[item] = (app.sci(SCI_MARKERSYMBOLDEFINED, SC_MARKNUM_FOLDER), app.sci(SCI_MARKERSYMBOLDEFINED, SC_MARKNUM_FOLDEROPEN))
    set_options(app, "Margins/Border/Edge", popups={"Fold Margin Style": "None"}, close=False)
    none_width = app.sci(SCI_GETMARGINWIDTHN, 2)
    set_options(app, "Margins/Border/Edge", popups={"Fold Margin Style": "Box tree"})
    assert got["Simple"] == (SC_MARK_PLUS, SC_MARK_MINUS), got
    assert got["Arrow"][0] == SC_MARK_ARROW, got
    assert got["Circle tree"] == (SC_MARK_CIRCLEPLUS, SC_MARK_CIRCLEMINUS), got
    assert got["Box tree"] == (SC_MARK_BOXPLUS, SC_MARK_BOXMINUS), got
    assert none_width == 0
    assert app.sci(SCI_GETMARGINWIDTHN, 2) > 0


@pytest.mark.case("SETTINGS-036")
def test_settings_036_line_number_display_and_width(papp):
    """SETTINGS-036: Line number display and width

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp, menu
    Steps: Document of 120000 lines, scrolled to the top; "    Width" "Dynamic width", Apply, read SCI_GETMARGINWIDTHN(0); "Constant width", Apply, read it; untick "Line Number: Display", Apply.
    Expect: constant width > dynamic width > 0; unticked, margin 0 width is 0; persists across restart.
    """
    app = papp
    app.new("".join(f"line {i}\n" for i in range(120000)))
    app.select(1, 1)
    set_options(app, "Margins/Border/Edge", popups={"    Width": "Dynamic width"}, close=False)
    dynamic = app.sci(SCI_GETMARGINWIDTHN, 0)
    set_options(app, "Margins/Border/Edge", popups={"    Width": "Constant width"}, close=False)
    constant = app.sci(SCI_GETMARGINWIDTHN, 0)
    assert constant > dynamic > 0, (constant, dynamic)
    set_options(app, "Margins/Border/Edge", checks={"Line Number: Display": False})
    assert app.sci(SCI_GETMARGINWIDTHN, 0) == 0
    app.restart()
    app.new("x\n")
    assert app.sci(SCI_GETMARGINWIDTHN, 0) == 0
    page(app, "Margins/Border/Edge")
    assert state(app, "Line Number: Display") == 0 and value(app, "    Width") == "Constant width"


@pytest.mark.case("SETTINGS-037")
def test_settings_037_change_history_in_the_margin_and_in_the_text(papp):
    """SETTINGS-037: Change history in the margin and in the text

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Tick "Change History: Show in the text", Apply; untick "Change History: Show in the margin", Apply; edit a line.
    Expect: SCI_GETCHANGEHISTORY has SC_CHANGE_HISTORY_INDICATORS when "in the text" is on and SC_CHANGE_HISTORY_MARKERS only while "in the margin" is on; margin 3 is 6 px wide with the margin option and 0 without; both off gives SC_CHANGE_HISTORY_DISABLED.
    """
    app = papp
    app.new("one\ntwo\n")
    set_options(app, "Margins/Border/Edge", checks={"Change History: Show in the text": True}, close=False)
    h = app.sci(SCI_GETCHANGEHISTORY)
    assert h & SC_CHANGE_HISTORY_INDICATORS and h & SC_CHANGE_HISTORY_MARKERS, h
    assert app.sci(SCI_GETMARGINWIDTHN, 3) == 6
    set_options(app, "Margins/Border/Edge", checks={"Change History: Show in the margin": False}, close=False)
    h = app.sci(SCI_GETCHANGEHISTORY)
    assert h & SC_CHANGE_HISTORY_INDICATORS and not h & SC_CHANGE_HISTORY_MARKERS, h
    assert app.sci(SCI_GETMARGINWIDTHN, 3) == 0
    set_options(app, "Margins/Border/Edge", checks={"Change History: Show in the text": False}, close=False)
    assert app.sci(SCI_GETCHANGEHISTORY) == SC_CHANGE_HISTORY_DISABLED
    set_options(app, "Margins/Border/Edge", checks={"Change History: Show in the margin": True})
    app.new("fresh\n")
    app.select(1, 1)
    app.type("edit ")
    h = app.sci(SCI_GETCHANGEHISTORY)
    assert h & SC_CHANGE_HISTORY_MARKERS and not h & SC_CHANGE_HISTORY_INDICATORS, h


@pytest.mark.case("SETTINGS-038")
def test_settings_038_distraction_free_width(papp):
    """SETTINGS-038: Distraction Free width

    Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_DISTRACTIONFREE
    Channel: ui, mcp
    Steps: Select "Distraction Free" "4 parts", Apply; run IDM_VIEW_DISTRACTIONFREE; read SCI_GETMARGINLEFT and the editor width (SCI_GETSCROLLWIDTH or `ui` frame of the ScintillaView); run it again.
    Expect: inside distraction-free mode the left margin is a quarter of the editor's width (±1 px); leaving it restores the padding (≤ 9).
    """
    app = papp
    app.new("text\n")
    set_options(app, "Margins/Border/Edge", popups={"Distraction Free": "4 parts"})
    app.run("IDM_VIEW_DISTRACTIONFREE")
    try:
        width = U.rect(app.get("editor", "sciView.frame"))[2]
        app.wait(lambda: abs(app.sci(SCI_GETMARGINLEFT) - width / 4) <= 1, message="a quarter of the width as margin")
    finally:
        app.run("IDM_VIEW_DISTRACTIONFREE")
    app.wait(lambda: app.sci(SCI_GETMARGINLEFT) <= 9, message="the padding back")


@pytest.mark.case("SETTINGS-039")
def test_settings_039_default_encoding_of_a_new_document(papp, tmp):
    """SETTINGS-039: Default encoding of a new document

    Covers: IDM_SETTING_PREFERENCE, IDM_FILE_NEW
    Channel: ui, files, mcp
    Steps: For each of "ANSI", "UTF-8", "UTF-8-BOM", "UTF-16 BE BOM", "UTF-16 LE BOM" typed into the "Encoding" field: Apply, run IDM_FILE_NEW, type "é", save to `tmp` with a queued save-panel answer.
    Expect: the Encoding menu checks the matching item (IDM_FORMAT_ANSI, IDM_FORMAT_AS_UTF_8, IDM_FORMAT_UTF_8, IDM_FORMAT_UTF_16BE, IDM_FORMAT_UTF_16LE); the saved bytes are E9 / C3 A9 / EF BB BF C3 A9 / FE FF 00 E9 / FF FE E9 00.
    """
    app = papp
    cases = [("ANSI", "IDM_FORMAT_ANSI", b"\xe9"), ("UTF-8", "IDM_FORMAT_AS_UTF_8", b"\xc3\xa9"),
             ("UTF-8-BOM", "IDM_FORMAT_UTF_8", b"\xef\xbb\xbf\xc3\xa9"),
             ("UTF-16 BE BOM", "IDM_FORMAT_UTF_16BE", b"\xfe\xff\x00\xe9"),
             ("UTF-16 LE BOM", "IDM_FORMAT_UTF_16LE", b"\xff\xfe\xe9\x00")]
    for name, command, data in cases:
        set_options(app, "New Document", fields={"Encoding": name})
        app.run("IDM_FILE_NEW")
        app.type("é")
        assert app.checked(command), (name, app.doc())
        f = tmp / f"{command}.txt"
        U.save_new_as(app, f)
        assert f.read_bytes() == data, (name, f.read_bytes())
    set_options(app, "New Document", fields={"Encoding": "UTF-8"})


@pytest.mark.case("SETTINGS-040")
def test_settings_040_apply_to_opened_ansi_files(papp, tmp):
    """SETTINGS-040: Apply to opened ANSI files

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, files, menu
    Steps: A seven-bit file "plain text\\n" in `tmp`; with Encoding "UTF-8" and "    Apply to opened ANSI files" ticked open it; close, untick, Apply, open again.
    Expect: ticked: the document is UTF-8 (IDM_FORMAT_AS_UTF_8 checked); unticked: ANSI (IDM_FORMAT_ANSI checked).
    """
    app = papp
    f = tmp / "seven.txt"
    f.write_bytes(b"plain text\n")
    set_options(app, "New Document", fields={"Encoding": "UTF-8"}, checks={"    Apply to opened ANSI files": True})
    app.open(f)
    assert app.checked("IDM_FORMAT_AS_UTF_8")
    app.close_all()
    set_options(app, "New Document", checks={"    Apply to opened ANSI files": False})
    app.open(f)
    assert app.checked("IDM_FORMAT_ANSI")


@pytest.mark.case("SETTINGS-041")
def test_settings_041_default_line_ending_of_a_new_document(papp, tmp):
    """SETTINGS-041: Default line ending of a new document

    Covers: IDM_SETTING_PREFERENCE, IDM_FILE_NEW
    Channel: ui, files, mcp
    Steps: For each "Format (Line ending)" item: Apply, IDM_FILE_NEW, type "a" return "b", save to `tmp`.
    Expect: SCI_GETEOLMODE is SC_EOL_CRLF / SC_EOL_CR / SC_EOL_LF; the file's bytes contain "\\r\\n" / "\\r" / "\\n" between a and b; the matching Edit > EOL Conversion item is checked.
    """
    app = papp
    cases = [("Windows (CR LF)", SC_EOL_CRLF, b"a\r\nb", "IDM_FORMAT_TODOS"),
             ("Macintosh (CR)", SC_EOL_CR, b"a\rb", "IDM_FORMAT_TOMAC"),
             ("Unix (LF)", SC_EOL_LF, b"a\nb", "IDM_FORMAT_TOUNIX")]
    for item, mode, data, command in cases:
        set_options(app, "New Document", popups={"Format (Line ending)": item})
        app.run("IDM_FILE_NEW")
        app.type("a")
        app.keys("return")
        app.type("b")
        assert app.sci(SCI_GETEOLMODE) == mode
        # (the EOL Conversion menu marks the current format by disabling it: an EDIT finding)
        f = tmp / f"eol{mode}.txt"
        U.save_new_as(app, f)
        assert data in f.read_bytes(), (item, f.read_bytes())


@pytest.mark.case("SETTINGS-042")
def test_settings_042_default_language_of_a_new_document(papp):
    """SETTINGS-042: Default language of a new document

    Covers: IDM_SETTING_PREFERENCE, IDM_FILE_NEW
    Channel: ui, menu, mcp
    Steps: Type "python" into "Default language:", Apply; run IDM_FILE_NEW; clear the field, Apply, IDM_FILE_NEW.
    Expect: the first new document's language is Python (IDM_LANG_PYTHON checked, status bar starts "Python"); the second is Normal text.
    """
    app = papp
    set_options(app, "New Document", fields={"Default language:": "python"})
    app.run("IDM_FILE_NEW")
    assert app.doc()["language"] == "python"
    assert app.checked("IDM_LANG_PYTHON")
    assert any(str(c.get("value", "")).startswith("Python") for c in app.ui("main")["controls"])
    set_options(app, "New Document", fields={"Default language:": ""})
    app.run("IDM_FILE_NEW")
    assert app.doc()["language"] == "normal"


@pytest.mark.case("SETTINGS-043")
def test_settings_043_language_from_contents_when_the_name_says_nothing(papp, tmp):
    """SETTINGS-043: Language from contents when the name says nothing

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp, prefs
    Steps: Untick "Work the language out from the contents when the name does not say", Apply; open an extensionless file "script" whose first line is "#!/usr/bin/env python3"; then tick it, Apply, open it again.
    Expect: unticked: the document stays Normal text and pref detectLanguageFromContent is false; ticked: it opens as Python. (Currently Apply does not write this option: xfail, BUG.)
    """
    app = papp
    f = tmp / "script"
    f.write_text("#!/usr/bin/env python3\nprint('hi')\n")
    set_options(app, "New Document", checks={"Work the language out from the contents when the name does not say": False})
    assert stored(app).get("detectLanguageFromContent") in (False, 0)
    app.open(f)
    assert app.doc()["language"] == "normal"
    app.close_all()
    set_options(app, "New Document", checks={"Work the language out from the contents when the name does not say": True})
    app.open(f)
    assert app.doc()["language"] == "python"


@pytest.mark.case("SETTINGS-044")
def test_settings_044_always_open_a_new_document_at_startup(papp, tmp):
    """SETTINGS-044: Always open a new document at startup

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, launch, mcp
    Steps: Untick "Always open a new document in addition at startup", Apply; restart with a file of `tmp` as argument; tick it, Apply, restart the same way.
    Expect: unticked: the only document is the file; ticked: the file plus an untitled "new 1".
    """
    app = papp
    f = tmp / "only.txt"
    f.write_text("only\n")
    set_options(app, "New Document", checks={"Always open a new document in addition at startup": True})
    app.restart(args=[str(f)])
    app.wait(lambda: any(d["path"] and app.same_path(d["path"], f) for d in app.docs()), message="the file opened")
    app.idle(0.3)
    assert sorted(d["title"] for d in app.docs()) == ["new 1", "only.txt"]
    set_options(app, "New Document", checks={"Always open a new document in addition at startup": False})
    assert stored(app).get("openNewDocumentAtStartup") in (False, 0)
    app.restart(args=[str(f)])
    app.wait(lambda: any(d["path"] and app.same_path(d["path"], f) for d in app.docs()), message="the file opened")
    app.idle(0.3)
    assert [d["title"] for d in app.docs()] == ["only.txt"]


@pytest.mark.case("SETTINGS-045")
def test_settings_045_first_line_as_untitled_tab_name(papp):
    """SETTINGS-045: First line as untitled tab name

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: Tick "Use the first line of document as untitled tab name", Apply; in a new document type "Shopping list\\nmilk"; untick, Apply.
    Expect: the tab title (list_documents) is "Shopping list" while ticked, "new N" after unticking; a first line longer than 32 characters is cut to 32.
    """
    app = papp

    def tab_titles():
        for c in app.ui("main")["controls"]:
            if c["class"] == "NppTabBarView":
                return [t.get("title") for t in c.get("tabs", [])]
        return []
    set_options(app, "New Document", checks={"Use the first line of document as untitled tab name": True})
    app.run("IDM_FILE_NEW")
    app.type("Shopping list")
    app.keys("return")
    app.type("milk")
    app.wait(lambda: tab_titles()[-1] == "Shopping list", message="the first line as the tab name")
    app.run("IDM_FILE_NEW")
    long = "A first line that is much longer than thirty-two characters"
    app.type(long)
    app.wait(lambda: tab_titles()[-1] == long[:32], message="the name cut to 32")
    set_options(app, "New Document", checks={"Use the first line of document as untitled tab name": False})
    app.wait(lambda: re.fullmatch(r"new \d+", tab_titles()[-1]), message="new N again")


@pytest.mark.case("SETTINGS-045")
def test_settings_045_every_untitled_tab_keeps_its_first_line_name(papp):
    """SETTINGS-045 (background tabs): the first-line name stays when another tab is in front"""
    app = papp
    set_options(app, "New Document", checks={"Use the first line of document as untitled tab name": True})
    app.run("IDM_FILE_NEW")
    app.type("Shopping list")
    app.run("IDM_FILE_NEW")
    app.idle(0.2)
    titles = [d["title"] for d in app.docs()]
    tabs = next(c for c in app.ui("main")["controls"] if c["class"] == "NppTabBarView")["tabs"]
    assert "Shopping list" in titles, titles
    assert "Shopping list" in [t["title"] for t in tabs], tabs


@pytest.mark.case("SETTINGS-046")
def test_settings_046_indent_size_and_spaces(papp):
    """SETTINGS-046: Indent size and spaces

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: Set "Indent size:" 3 and tick "Indent using: Space character(s)", Apply; press tab in an empty document; set 8 and untick, Apply, press tab.
    Expect: SCI_GETTABWIDTH 3, SCI_GETUSETABS 0, the text is three spaces; then width 8, uses tabs, the text is "\\t".
    """
    app = papp
    set_options(app, "Indentation", fields={"Indent size:": 3}, checks={"Indent using: Space character(s)": True})
    app.new("")
    app.keys("tab")
    assert app.sci(SCI_GETTABWIDTH) == 3 and app.sci(SCI_GETUSETABS) == 0
    assert app.text() == "   "
    set_options(app, "Indentation", fields={"Indent size:": 8}, checks={"Indent using: Space character(s)": False})
    app.new("")
    app.keys("tab")
    assert app.sci(SCI_GETTABWIDTH) == 8 and app.sci(SCI_GETUSETABS) == 1
    assert app.text() == "\t"
    set_options(app, "Indentation", fields={"Indent size:": 4})


@pytest.mark.case("SETTINGS-047")
def test_settings_047_auto_indent_none_basic_advanced(papp):
    """SETTINGS-047: Auto-indent none, basic, advanced

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: For "None", "Auto-indent: Basic", "Auto-indent: Advanced": Apply; in C++ type "    if (x) {" then return.
    Expect: None: the new line has indentation 0; Basic: 4; Advanced: 8; with Advanced a "}" typed on the next line goes back under the opener (4).
    """
    app = papp
    got = {}
    for item in ("None", "Auto-indent: Basic", "Auto-indent: Advanced"):
        set_options(app, "Indentation", popups={"Auto-indent": item})
        app.new("", language="cpp")
        app.type("    if (x) {")
        app.keys("return")
        got[item] = app.sci(SCI_GETLINEINDENTATION, 1)
    app.type("}")
    closer = app.sci(SCI_GETLINEINDENTATION, 1)
    assert got == {"None": 0, "Auto-indent: Basic": 4, "Auto-indent: Advanced": 8}, got
    assert closer == 4


@pytest.mark.case("SETTINGS-048")
def test_settings_048_backspace_unindents(papp):
    """SETTINGS-048: Backspace unindents

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: Tick "Backspace key unindents instead of removing single space", Apply; text "        x" (8 spaces), caret before x, press backspace; untick, Apply, repeat.
    Expect: ticked: SCI_GETBACKSPACEUNINDENTS 1 and the line has 4 spaces; unticked: 7 spaces.
    """
    app = papp
    set_options(app, "Indentation", checks={"Backspace key unindents instead of removing single space": True})
    app.new("        x")
    app.select(1, 9)
    app.keys("backspace")
    assert app.sci(SCI_GETBACKSPACEUNINDENTS) == 1
    assert app.sci(SCI_GETLINEINDENTATION, 0) == 4 and app.text().endswith("x")   # tabs or spaces, as Indent using says
    set_options(app, "Indentation", checks={"Backspace key unindents instead of removing single space": False})
    app.new("        x")
    app.select(1, 9)
    app.keys("backspace")
    assert app.text() == "       x" and app.sci(SCI_GETLINEINDENTATION, 0) == 7


@pytest.mark.case("SETTINGS-049")
def test_settings_049_indent_settings_per_language(papp, tmp):
    """SETTINGS-049: Indent settings per language

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp, launch
    Steps: Under "Indent Settings for" select "python", untick "Use default value", set its "Indent size:" 2 and "Space character(s)", Apply; open a .py and a .cpp document; restart.
    Expect: Python document: tab width 2, no tabs; C++ document: the default size; still so after restart; pref languageIndent has python {size 2, spaces true}.
    """
    app = papp
    page(app, "Indentation")
    popup(app, "Indent Settings for", "python")
    check(app, "Use default value", False)
    field(app, "Indent size:", 2, index=1)
    pops = [c for c in controls(app) if c["class"] == "NSPopUpButton" and "Space character(s)" in (c.get("items") or [])]
    app.act(PREFS, "select", "Space character(s)", path=pops[0]["path"])
    apply(app)
    close_prefs(app)
    py, cpp = tmp / "a.py", tmp / "b.cpp"
    py.write_text("x = 1\n")
    cpp.write_text("int x;\n")

    def check_docs():
        app.open(py)
        assert app.doc()["language"] == "python"
        assert (app.sci(SCI_GETTABWIDTH), app.sci(SCI_GETUSETABS)) == (2, 0)
        app.open(cpp)
        assert app.sci(SCI_GETTABWIDTH) == 4
    assert stored(app).get("languageIndent", {}).get("python") in ({"size": 2, "spaces": True}, {"size": 2, "spaces": 1})
    check_docs()
    app.close_all()
    app.restart()
    check_docs()


@pytest.mark.case("SETTINGS-050")
def test_settings_050_hiding_languages_from_the_language_menu(papp):
    """SETTINGS-050: Hiding languages from the Language menu

    Covers: IDM_SETTING_PREFERENCE, IDM_LANG_PYTHON
    Channel: ui, menu, launch
    Steps: On Language select "Python" in "Available items", click "→", Apply; read the Language menu; restart; move it back with "←".
    Expect: Python is listed under "Disabled items" and absent from the Language menu (IDM_LANG_PYTHON not found) and from its "P" submenu; still hidden after restart; back after "←" and Apply.
    """
    app = papp
    page(app, "Language")
    avail, disabled = U.page_tables(app)
    names = [r[0] for r in avail["cells"]]
    app.act(PREFS, "select", names.index("Python"), path=avail["path"])
    app.click(PREFS, "→")
    assert "Python" in [r[0] for r in U.page_tables(app)[1]["cells"]]
    apply(app)
    close_prefs(app)

    def in_menu():
        return app.menu("IDM_LANG_PYTHON").get("IDM_LANG_PYTHON") is not None
    assert not in_menu()
    app.restart()
    assert not in_menu()
    page(app, "Language")
    disabled = U.page_tables(app)[1]
    app.act(PREFS, "select", [r[0] for r in disabled["cells"]].index("Python"), path=disabled["path"])
    app.click(PREFS, "←")
    apply(app)
    close_prefs(app)
    assert in_menu()


@pytest.mark.case("SETTINGS-051")
def test_settings_051_compact_language_menu(papp):
    """SETTINGS-051: Compact language menu

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, menu
    Steps: Tick "Make language menu compact", Apply, read the Language menu tree depth 2; untick, Apply.
    Expect: compact: first item "None (Normal Text)", letter submenus ("C" holding "C++"); flat: "C++" and "Python" are top-level items and "User Defined Language" is present.
    """
    app = papp
    set_options(app, "Language", checks={"Make language menu compact": True})
    tree = app.menu_tree("Language", 2)
    titles = [i.get("title") for i in tree if not i.get("separator")]
    assert titles[0] == "None (Normal Text)"
    c = next(i for i in tree if i.get("title") == "C")
    assert "C++" in [i.get("title") for i in c.get("items", [])]
    assert "C++" not in titles
    set_options(app, "Language", checks={"Make language menu compact": False})
    titles = [i.get("title") for i in app.menu_tree("Language", 2) if not i.get("separator")]
    assert "C++" in titles and "Python" in titles and "User Defined Language" in titles, titles


@pytest.mark.case("SETTINGS-052")
def test_settings_052_sql_backslash_escape(papp):
    """SETTINGS-052: SQL backslash escape

    Covers: IDM_SETTING_PREFERENCE, IDM_LANG_SQL
    Channel: ui, mcp
    Steps: SQL document "select 'a\\\\'b' from t"; with "Treat backslash as escape character for SQL" ticked read SCI_GETSTYLEAT at "from"; untick, Apply, recolour.
    Expect: ticked: the string ends after b' so "from" is a keyword (SCE_SQL_WORD); unticked: the string ends at the backslash's quote and the style at "b" is not a string.
    """
    app = papp
    text = "select 'a\\'b' from t"
    app.new(text, language="sql")
    at_from, at_b = text.index("from"), text.index("b'")
    app.wait(lambda: app.sci(SCI_GETSTYLEAT, at_from) == SCE_SQL_WORD, message="from as a keyword")
    set_options(app, "Language", checks={"Treat backslash as escape character for SQL": False})
    app.sci(SCI_COLOURISE, 0, -1)
    app.wait(lambda: app.sci(SCI_GETSTYLEAT, at_b) not in (SCE_SQL_STRING, SCE_SQL_CHARACTER), message="the string ends at \\'")
    set_options(app, "Language", checks={"Treat backslash as escape character for SQL": True})
    app.sci(SCI_COLOURISE, 0, -1)
    app.wait(lambda: app.sci(SCI_GETSTYLEAT, at_from) == SCE_SQL_WORD, message="from as a keyword again")


@pytest.mark.case("SETTINGS-053")
def test_settings_053_brace_matching_on_and_off(papp, tmp):
    """SETTINGS-053: Brace matching on and off

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp, snapshot
    Steps: C++ text "value = (a + b);"; read SCI_STYLEGETFORE(STYLE_BRACELIGHT); with "Highlight matching braces" ticked put the caret after "(" and snapshot the main window; move the caret to "a" and snapshot; untick, Apply, and repeat both snapshots.
    Expect: ticked: in the first snapshot pixels of the brace-light colour appear at the two braces and not in the second; unticked: neither snapshot has them (the braces keep the operator colour).
    """
    app = papp
    light(app)
    text = "value = (a + b);"
    app.new(text, language="cpp")
    fore = app.sci(SCI_STYLEGETFORE, STYLE_BRACELIGHT)
    colour = (fore & 0xFF, (fore >> 8) & 0xFF, (fore >> 16) & 0xFF)

    def lit(name):
        img = U.still_snapshot(app, tmp / name)
        # the window is colour-managed: FF0000 is drawn as about (255, 38, 0)
        return sum(1 for p in img.get_flattened_data() if all(abs(p[i] - colour[i]) < 60 for i in range(3)))
    # a few pixels of that colour are elsewhere on the window: count what the braces add
    app.sci(SCI_GOTOPOS, 2)          # inside "value": no brace next to the caret
    app.idle(0.3)
    baseline = lit("off-brace.png")
    # Two bold parentheses: about 20 such pixels on a Retina screen, a quarter of that at 1x (CI runners).
    from PIL import Image
    scale = Image.open(tmp / "off-brace.png").size[0] / app.windows()[0]["frame"][2]
    enough = max(4, round(5 * scale * scale))
    app.sci(SCI_GOTOPOS, text.index("(") + 1)
    try:
        app.wait(lambda: lit("on-brace.png") > baseline + enough, message="the braces drawn in the brace-light colour")
    except TimeoutError:
        raise AssertionError(f"brace-light pixels: {lit('on-brace.png')} with the caret by the brace, {baseline} "
                             f"without, {enough} more wanted (snapshot scale {scale:.2f}, colour {colour})")
    set_options(app, "Highlighting", checks={"Highlight matching braces": False})
    app.sci(SCI_GOTOPOS, 2)
    app.sci(SCI_GOTOPOS, text.index("(") + 1)
    app.idle(0.3)
    assert lit("disabled.png") <= baseline


@pytest.mark.case("SETTINGS-054")
def test_settings_054_smart_highlighting_and_its_options(papp):
    """SETTINGS-054: Smart highlighting and its options

    Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_FIND
    Channel: ui, mcp
    Steps: Text "total = total + subtotal Total"; select the first "total" (go_to with end column); count runs of indicator 12 (smart highlight) with SCI_INDICATORVALUEAT; repeat with "Smart Highlighting: Match whole word only" off, then "Smart Highlighting: Match case" on, then "Smart highlighting" off.
    Expect: whole word, case-insensitive: 3 (total, total, Total); whole word off: 4; match case on: 2 without "Total"; smart highlighting off: 0; with "Smart Highlighting: Use Find dialog settings" ticked the Find window's Match case / Match whole word options decide instead (Find's Match case on gives 2, off gives 3).
    """
    app = papp
    text = "total = total + subtotal Total"

    def runs():
        app.new(text)
        app.select(1, 1, 1, 6)
        app.idle(0.3)
        return len(indicator_runs(app, SMART_HIGHLIGHT))
    set_options(app, "Highlighting", checks={"Smart highlighting": True, "Smart Highlighting: Match whole word only": True,
                                             "Smart Highlighting: Match case": False})
    app.wait(lambda: runs() == 3, message="3 whole-word matches")
    set_options(app, "Highlighting", checks={"Smart Highlighting: Match whole word only": False})
    app.wait(lambda: runs() == 4, message="4 with whole word off")
    set_options(app, "Highlighting", checks={"Smart Highlighting: Match whole word only": True,
                                             "Smart Highlighting: Match case": True})
    app.wait(lambda: runs() == 2, message="2 with match case")
    set_options(app, "Highlighting", checks={"Smart highlighting": False})
    app.wait(lambda: runs() == 0, message="none with smart highlighting off")
    set_options(app, "Highlighting", checks={"Smart highlighting": True, "Smart Highlighting: Match case": False,
                                             "Smart Highlighting: Use Find dialog settings": True})
    app.run("IDM_SEARCH_FIND")
    app.act("Find", "set_state", 1, title="Match whole word only")
    app.act("Find", "set_state", 1, title="Match case")
    app.click("Find", "Find Next")      # the port takes the Find options when a search runs (see below)
    app.wait(lambda: runs() == 2, message="Find's Match case decides")
    app.run("IDM_SEARCH_FIND")
    app.act("Find", "set_state", 0, title="Match case")
    app.click("Find", "Find Next")
    app.wait(lambda: runs() == 3, message="Find's Match case off")
    app.run("IDM_SEARCH_FIND")
    app.act("Find", "set_state", 0, title="Match whole word only")
    app.click("Find", "Find Next")
    app.close_window("Find")


@pytest.mark.case("SETTINGS-054")
def test_settings_054_find_options_apply_as_soon_as_ticked(papp):
    """SETTINGS-054 (Find settings): the Find window's Match case counts as soon as it is ticked"""
    app = papp
    set_options(app, "Highlighting", checks={"Smart Highlighting: Use Find dialog settings": True})
    app.new("total = total + subtotal Total")
    app.run("IDM_SEARCH_FIND")
    try:
        app.act("Find", "set_state", 1, title="Match whole word only")
        app.act("Find", "set_state", 1, title="Match case")
        app.select(1, 1, 1, 6)
        app.idle(0.3)
        assert len(indicator_runs(app, SMART_HIGHLIGHT)) == 2
    finally:
        app.act("Find", "set_state", 0, title="Match case")
        app.act("Find", "set_state", 0, title="Match whole word only")
        app.click("Find", "Find Next")
        app.close_window("Find")


@pytest.mark.case("SETTINGS-055")
def test_settings_055_smart_highlighting_in_the_other_view(papp):
    """SETTINGS-055: Smart highlighting in the other view

    Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_CLONE_TO_ANOTHER_VIEW
    Channel: ui, mcp
    Steps: Text "alpha beta alpha gamma alpha"; clone to the other view; tick "Smart Highlighting: Highlight another view", Apply; select the first "alpha" in the main view.
    Expect: the sub view (e2e_sci view=sub) has 3 runs of indicator 12; unticked, 0.
    """
    app = papp
    app.new("alpha beta alpha gamma alpha")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    try:
        set_options(app, "Highlighting", checks={"Smart Highlighting: Highlight another view": True})
        app.sci(SCI_SETSEL, 0, 5)
        app.wait(lambda: len(indicator_runs(app, SMART_HIGHLIGHT, view="sub")) == 3, message="3 matches in the other view")
        app.sci(SCI_SETSEL, 6, 10)      # "beta": its single match elsewhere
        app.wait(lambda: len(indicator_runs(app, SMART_HIGHLIGHT, view="sub")) == 1, message="1 beta in the other view")
    finally:
        app.close_all()


@pytest.mark.case("SETTINGS-055")
def test_settings_055_unticked_the_other_view_is_not_highlighted(papp):
    """SETTINGS-055 (off): unticked, the other view keeps none of the marks it was given

    A clone shows the same Scintilla document, and indicators belong to the document (upstream's
    clone shares the buffer the same way), so the main view's own highlight of the new word is
    necessarily seen in the clone too; what must go are the other view's marks of the old word."""
    app = papp
    app.new("alpha beta alpha gamma alpha")
    app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
    try:
        set_options(app, "Highlighting", checks={"Smart Highlighting: Highlight another view": True})
        app.sci(SCI_SETSEL, 0, 5)
        app.wait(lambda: len(indicator_runs(app, SMART_HIGHLIGHT, view="sub")) == 3, message="3 matches in the other view")
        set_options(app, "Highlighting", checks={"Smart Highlighting: Highlight another view": False})
        app.sci(SCI_SETSEL, 6, 10)
        app.idle(0.3)
        sub = indicator_runs(app, SMART_HIGHLIGHT, view="sub")
        assert sub == indicator_runs(app, SMART_HIGHLIGHT, view="main")
        assert not [r for r in sub if r in ((0, 5), (17, 22), (23, 28))], sub   # no "alpha" left
    finally:
        app.close_all()


@pytest.mark.case("SETTINGS-056")
def test_settings_056_mark_style_options_match_case_and_whole_word(papp):
    """SETTINGS-056: Mark style options: match case and whole word

    Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_MARKALLEXT1
    Channel: ui, mcp
    Steps: Text "cat cats CAT", select "cat"; for (case off, word on), (case on, word on), (case on, word off) set "Style All Occurrences of Token: Match case" / "…: Match whole word only", Apply, run IDM_SEARCH_UNMARKALLEXT1 then IDM_SEARCH_MARKALLEXT1, count runs of indicator 8.
    Expect: 2, 1, 2 runs respectively.
    """
    app = papp
    got = []
    for case, word in ((False, True), (True, True), (True, False)):
        set_options(app, "Highlighting", checks={"Style All Occurrences of Token: Match case": case,
                                                 "Style All Occurrences of Token: Match whole word only": word})
        app.new("cat cats CAT")
        app.sci(SCI_SETSEL, 0, 3)
        app.run("IDM_SEARCH_UNMARKALLEXT1")
        app.run("IDM_SEARCH_MARKALLEXT1")
        got.append(len(indicator_runs(app, 8)))
    assert got == [2, 1, 2], got


@pytest.mark.case("SETTINGS-057")
def test_settings_057_matching_tags_attributes_non_html_zones(papp):
    """SETTINGS-057: Matching tags, attributes, non-HTML zones

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: HTML "<div class=\\"a\\" id='b'><p>x</p></div>"; caret in "div"; read runs of indicators 15 (tag) and 16 (attributes); untick "    Highlight tag attributes", Apply; untick "Highlight Matching Tags", Apply.
    Expect: tag runs at 0..4, 21..22, 30..36 and attribute runs at 5..14, 15..21; without attributes indicator 16 is empty; without matching tags indicator 15 is empty; "    Highlight comment/php/asp zone" ticked makes tags inside "<!-- <b>x</b> -->" match (highlightNonHtmlZone is used nowhere in the port: xfail, BUG).
    """
    app = papp
    text = "<div class=\"a\" id='b'><p>x</p></div>"
    app.new(text, language="html")
    app.sci(SCI_GOTOPOS, 2)
    app.wait(lambda: indicator_runs(app, 15) == [(0, 4), (21, 22), (30, 36)], message="the tag pair")
    app.wait(lambda: indicator_runs(app, 16) == [(5, 14), (15, 21)], message="the attributes")
    set_options(app, "Highlighting", checks={"    Highlight tag attributes": False})
    app.sci(SCI_GOTOPOS, 3)
    app.sci(SCI_GOTOPOS, 2)
    app.idle(0.3)
    assert indicator_runs(app, 16) == []
    set_options(app, "Highlighting", checks={"Highlight Matching Tags": False, "    Highlight tag attributes": True})
    app.sci(SCI_GOTOPOS, 3)
    app.sci(SCI_GOTOPOS, 2)
    app.idle(0.3)
    assert indicator_runs(app, 15) == []


@pytest.mark.case("SETTINGS-057")
def test_settings_057_tags_inside_a_comment_match_with_the_zone_option(papp):
    """SETTINGS-057 (zones): "Highlight comment/php/asp zone" is stored, and tags in a comment still do not match

    Upstream reads _enableHiliteNonHTMLZone from config.xml and writes it back, and nothing else
    reads it (Parameters.cpp, preferenceDlg.cpp only); XmlMatchedTagsHighlighter skips a tag whose
    style is SCE_H_COMMENT whatever the option. The port does the same."""
    app = papp
    text = "<!-- <b>x</b> --><i>y</i>"
    set_options(app, "Highlighting", checks={"    Highlight comment/php/asp zone": True})
    try:
        assert stored(app).get("highlightNonHtmlZone") is True
        app.new(text, language="html")
        app.sci(SCI_GOTOPOS, text.index("i>"))     # a real tag first: the matcher is on
        app.wait(lambda: indicator_runs(app, 15), timeout=3, message="the tags outside the comment matched")
        app.sci(SCI_GOTOPOS, text.index("b>"))
        app.idle(0.3)
        assert indicator_runs(app, 15) == [], "a tag inside a comment matched"
    finally:
        set_options(app, "Highlighting", checks={"    Highlight comment/php/asp zone": False})


@pytest.mark.case("SETTINGS-058")
def test_settings_058_print_options_reach_the_print_job(papp):
    """SETTINGS-058: Print options reach the print job

    Covers: IDM_SETTING_PREFERENCE, IDM_FILE_PRINT
    Channel: ui, prefs, modal
    Steps: Tick "Print line number", select "Color Options" "Invert", set margins "11 33 22 44", header/footer parts, header font "Courier" size 12, Bold, "Print formfeed as page break", Apply; run IDM_FILE_PRINT with the print panel cancelled (queued answer / real modal closed).
    Expect: the stored preferences are printLineNumbers true, printColourMode 1, printMarginLeft 11, printMarginTop 33, printMarginRight 22, printMarginBottom 44, the six header/footer strings, printHeaderFontName "Courier", printHeaderFontSize 12, printHeaderBold true, printFormFeedPageBreak true; a margins text with three numbers leaves the margins unchanged; nothing reaches a printer. (Checking the rendered page needs a print-to-PDF hook, see report.)
    """
    app = papp
    app.new("page one\n\fpage two\n")
    set_options(app, "Print", checks={"Print line number": True, "Header and Footer: Bold": True,
                                      "Print formfeed as page break": True},
                popups={"Color Options": "Invert"},
                fields={"Margins: left, top, right, bottom (points)": "11 33 22 44", "Header: Left part": "HL",
                        "Header: Middle part": "HM", "Header: Right part": "HR", "Footer: Left part": "FL",
                        "Footer: Middle part": "FM", "Footer: Right part": "FR",
                        "Header font (blank for the editor's)": "Courier", "Header font size": 12})
    s = stored(app)
    want = {"printLineNumbers": True, "printColourMode": 1, "printMarginLeft": 11, "printMarginTop": 33,
            "printMarginRight": 22, "printMarginBottom": 44, "printHeaderFontName": "Courier",
            "printHeaderFontSize": 12, "printHeaderBold": True, "printFormFeedPageBreak": True}
    assert {k: s.get(k) for k in want} == want, {k: s.get(k) for k in want}
    parts = {s.get(k) for k in s if k.startswith("print") and isinstance(s.get(k), str)}
    assert {"HL", "HM", "HR", "FL", "FM", "FR"} <= parts, parts
    set_options(app, "Print", fields={"Margins: left, top, right, bottom (points)": "1 2 3"})
    s = stored(app)
    assert (s["printMarginLeft"], s["printMarginTop"], s["printMarginRight"], s["printMarginBottom"]) == (11, 33, 22, 44)
    # The job itself is printed into the PDF hook by the next test (SETTINGS-058 job).


@pytest.mark.case("SETTINGS-058")
def test_settings_058_the_print_job_uses_the_print_page(papp):
    """SETTINGS-058 (job): printed into the suite's PDF hook, the job has the Print page's margins, line numbers and header"""
    app = papp
    from test_file import no_printer_here
    from _util_file import pdf_text
    no_printer_here(app)
    app.new("page one\n")
    set_options(app, "Print", checks={"Print line number": True},
                fields={"Margins: left, top, right, bottom (points)": "11 33 22 44", "Header: Left part": "HL"})
    app.modal_log()
    app.run("IDM_FILE_PRINTNOW")
    jobs = [e for e in app.modal_log() if e["kind"] == "print"]
    assert len(jobs) == 1, jobs
    text = pdf_text(jobs[0]["path"])
    assert "page one" in text
    assert jobs[0]["margins"] == [11, 33, 22, 44], jobs[0]["margins"]
    # PDFKit reads the two spaces after the number back as one on a page of one line.
    assert re.search(r"^1\s+page one", text, re.M) and "HL" in text, text


@pytest.mark.case("SETTINGS-059")
def test_settings_059_print_variable_add_inserts_into_the_last_header_footer_field(papp):
    """SETTINGS-059: Print Variable + Add inserts into the last header/footer field

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui
    Steps: On Print focus the "Footer: Left part" field (`act focus`), select "File name" in "Variable", click "Add"; with no field focused select "Page" and click "Add".
    Expect: "Footer: Left part" ends with "$(FILE_NAME)"; the second Add appends "$(CURRENT_PRINTING_PAGE)" to the last field used (or "Header: Middle part" when none was).
    """
    app = papp
    page(app, "Print")
    footer = control_for(app, "Footer: Left part")
    field(app, "Footer: Left part", "")
    app.act(PREFS, "focus", path=footer["path"])
    popup(app, "Variable", "File name")
    app.click(PREFS, "Add")
    assert value(app, "Footer: Left part").endswith("$(FILE_NAME)")
    popup(app, "Variable", "Page")
    app.click(PREFS, "Add")
    assert value(app, "Footer: Left part").endswith("$(FILE_NAME)$(CURRENT_PRINTING_PAGE)")
    close_prefs(app)
    app.restart()                     # no field used yet: Header: Middle part takes it
    page(app, "Print")
    before = value(app, "Header: Middle part")
    popup(app, "Variable", "Page")
    app.click(PREFS, "Add")
    assert value(app, "Header: Middle part") == before + "$(CURRENT_PRINTING_PAGE)"
    close_prefs(app)


@pytest.mark.case("SETTINGS-060")
def test_settings_060_backup_on_save_none_simple_verbose(papp, tmp):
    """SETTINGS-060: Backup on save: none, simple, verbose

    Covers: IDM_SETTING_PREFERENCE, IDM_FILE_SAVE
    Channel: ui, files
    Steps: Open `tmp/b.txt` ("one"); with "None" edit to "two" and save; "Simple backup", Apply, edit "three", save; "Verbose backup", Apply, edit "four", save.
    Expect: None: no b.txt.bak; Simple: b.txt.bak holds "two"; Verbose: a file b.txt.<timestamp>.bak holding "three" in home/Library/Application Support/NotepadMac/backup.
    """
    app = papp
    f = tmp / "b.txt"
    f.write_text("one")
    backup = support(app) / "backup"
    app.open(f)

    def save(text):
        app.set_text(text)
        app.run("IDM_FILE_SAVE")
        app.wait(lambda: f.read_text() == text, message=f"saved {text}")
    set_options(app, "Backup", popups={"Backup on save": "None"})
    save("two")
    assert not (tmp / "b.txt.bak").exists() and not list(backup.glob("b.txt*")) if backup.exists() else True
    set_options(app, "Backup", popups={"Backup on save": "Simple backup"})
    save("three")
    simple = [p for p in [tmp / "b.txt.bak", backup / "b.txt.bak"] if p.exists()]
    assert simple and simple[0].read_text() == "two", simple
    set_options(app, "Backup", popups={"Backup on save": "Verbose backup"})
    save("four")
    verbose = [p for p in backup.glob("b.txt.*.bak")]
    assert len(verbose) == 1 and verbose[0].read_text() == "three", list(backup.iterdir()) if backup.exists() else None


@pytest.mark.case("SETTINGS-061")
def test_settings_061_custom_backup_directory(papp, tmp):
    """SETTINGS-061: Custom backup directory

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, files, launch
    Steps: Set "Custom Backup Directory" to `tmp/bk`, "Verbose backup", Apply; save an edited file; restart and save again.
    Expect: the verbose backups land in `tmp/bk` both times, none in the home's backup folder.
    """
    app = papp
    f = tmp / "c.txt"
    f.write_text("zero")
    bk = tmp / "bk"
    bk.mkdir()
    set_options(app, "Backup", popups={"Backup on save": "Verbose backup"}, fields={"Custom Backup Directory": str(bk)})

    def save(text):
        app.open(f)
        app.set_text(text)
        app.run("IDM_FILE_SAVE")
        app.wait(lambda: f.read_text() == text, message=f"saved {text}")
    save("one")
    app.wait(lambda: len(list(bk.glob("c.txt.*.bak"))) == 1, message="a verbose backup in the custom folder")
    app.restart()
    save("two")
    app.wait(lambda: len(list(bk.glob("c.txt.*.bak"))) == 2, message="the second backup in the custom folder")
    home_backup = support(app) / "backup"
    assert not (home_backup.exists() and list(home_backup.glob("c.txt*")))


@pytest.mark.case("SETTINGS-062")
def test_settings_062_session_snapshot_and_periodic_backup(papp, tmp):
    """SETTINGS-062: Session snapshot and periodic backup

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, files, launch
    Steps: Tick "Enable session snapshot and periodic backup", set seconds to 5, Apply; type "never saved" in an untitled document and edit an opened file without saving; poll the backup folder up to 15 s; kill the app (stop with graceful=False) and start with `session=True`, clean_home=False.
    Expect: within the interval backup files with the unsaved texts appear in the home's backup folder and the opened file on disk is unchanged; after the restart the untitled document comes back with "never saved", marked modified; a value below 5 is stored as 5.
    """
    app = papp
    f = tmp / "kept.txt"
    f.write_text("on disk\n")
    backup = support(app) / "backup"
    # as on Windows, the snapshot goes with "Remember current session"
    set_options(app, "General", checks={"Remember current session for next launch": True})
    set_options(app, "Backup", checks={"Enable session snapshot and periodic backup": True},
                fields={"Trigger backup on modification in every: seconds": 2})
    assert stored(app).get("autosaveInterval") == 5, stored(app).get("autosaveInterval")
    app.restart(session=True)           # the suite's -nosession turns the snapshot off
    app.run("IDM_FILE_NEW")
    app.type("never saved")
    app.open(f)
    app.set_text("edited, not saved\n")

    def backed_up():
        texts = [p.read_bytes() for p in backup.glob("*")] if backup.exists() else []
        return any(b"never saved" in t for t in texts) and any(b"edited, not saved" in t for t in texts)
    app.wait(backed_up, timeout=15, message="both unsaved texts backed up")
    assert f.read_text() == "on disk\n"
    app.stop(graceful=False)
    app.start(session=True, clean_home=False, reset=False)
    app.wait(lambda: any(d["modified"] and not d["path"] and app.text(d["index"]) == "never saved" for d in app.docs()),
             timeout=15, message="the untitled text back after the crash")


@pytest.mark.case("SETTINGS-063")
def test_settings_063_auto_completion_on_input_source_and_threshold(papp):
    """SETTINGS-063: Auto-completion on input, source and threshold

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: C++ document with "retrieval retrospect\\n"; for "Function completion", "Word completion", "Function and word completion" with "Characters before it opens" 3: Apply, type "ret" on a new line, read SCI_AUTOCACTIVE and the list (SCI_AUTOCGETCURRENTTEXT after moving); untick "Enable auto-completion on each input", Apply, type "ret".
    Expect: the list opens after the third character only; Word: retrieval, retrospect and not return; Function: return; both: all three; unticked: SCI_AUTOCACTIVE stays 0.
    """
    app = papp

    def listed():
        items = []
        for _ in range(20):
            cur = app.sci(SCI_AUTOCGETCURRENTTEXT, 0, 0, returns="string")
            if items and cur == items[-1]:
                break
            items.append(cur)
            app.keys("down")
        return items

    def offer(source):
        set_options(app, "Auto-Completion", popups={"Auto-Completion": source}, fields={"Characters before it opens": 3},
                    checks={"Enable auto-completion on each input": True})
        app.new("retrieval retrospect\n", language="cpp")
        app.sci(SCI_DOCUMENTEND)
        app.type("re")
        app.idle(0.2)
        assert app.sci(SCI_AUTOCACTIVE) == 0
        app.type("t")
        app.wait(lambda: app.sci(SCI_AUTOCACTIVE), message="the list after the third character")
        items = listed()
        app.sci(SCI_AUTOCCANCEL)
        return set(items)
    words = offer("Word completion")
    assert {"retrieval", "retrospect"} <= words and "return" not in words, words
    functions = offer("Function completion")
    assert "return" in functions and "retrieval" not in functions, functions
    both = offer("Function and word completion")
    assert {"retrieval", "retrospect", "return"} <= both, both
    set_options(app, "Auto-Completion", checks={"Enable auto-completion on each input": False})
    app.new("retrieval retrospect\n", language="cpp")
    app.sci(SCI_DOCUMENTEND)
    app.type("ret")
    app.idle(0.3)
    assert app.sci(SCI_AUTOCACTIVE) == 0
    set_options(app, "Auto-Completion", fields={"Characters before it opens": 1}, checks={"Enable auto-completion on each input": True})


@pytest.mark.case("SETTINGS-064")
def test_settings_064_brief_list_ignore_numbers_tab_inserts(papp):
    """SETTINGS-064: Brief list, ignore numbers, Tab inserts

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: Tick "Make auto-completion list brief", type "ret" in C++; tick "Ignore numbers", document "12345 12399", type "123"; untick "Insert Selection: TAB", open a list and press tab.
    Expect: the brief list holds only names starting with "ret"; with Ignore numbers no list opens for "123" (and one does when unticked); without TAB insertion, tab does not insert the selected item (SCI_AUTOCGETOPTIONS / text unchanged apart from a tab).
    """
    app = papp
    set_options(app, "Auto-Completion", checks={"Make auto-completion list brief": True, "Ignore numbers": True},
                fields={"Characters before it opens": 1})
    app.new("retrieval retrospect other\n", language="cpp")
    app.sci(SCI_DOCUMENTEND)
    app.type("ret")
    app.wait(lambda: app.sci(SCI_AUTOCACTIVE), message="a list")
    items = []
    for _ in range(40):
        cur = app.sci(SCI_AUTOCGETCURRENTTEXT, 0, 0, returns="string")
        if items and cur == items[-1]:
            break
        items.append(cur)
        app.keys("down")
    app.sci(SCI_AUTOCCANCEL)
    assert items and all(i.lower().startswith("ret") for i in items), items
    app.new("12345 12399\n")
    app.sci(SCI_DOCUMENTEND)
    app.type("123")
    app.idle(0.3)
    assert app.sci(SCI_AUTOCACTIVE) == 0
    set_options(app, "Auto-Completion", checks={"Ignore numbers": False})
    app.new("12345 12399\n")
    app.sci(SCI_DOCUMENTEND)
    app.type("123")
    app.wait(lambda: app.sci(SCI_AUTOCACTIVE), message="a list of numbers")
    app.sci(SCI_AUTOCCANCEL)
    set_options(app, "Auto-Completion", checks={"Make auto-completion list brief": False, "Ignore numbers": True})


@pytest.mark.case("SETTINGS-064")
def test_settings_064_tab_does_not_insert_when_unticked(papp):
    """SETTINGS-064 (TAB): with "Insert Selection: TAB" unticked, Tab does not take the list's item"""
    app = papp
    set_options(app, "Auto-Completion", checks={"Insert Selection: TAB": False}, fields={"Characters before it opens": 1})
    app.new("retrieval\n")
    app.sci(SCI_DOCUMENTEND)
    app.type("retr")
    app.wait(lambda: app.sci(SCI_AUTOCACTIVE), message="a list")
    app.keys("tab")
    assert "retrieval\nretrieval" not in app.text(), repr(app.text())


@pytest.mark.case("SETTINGS-065")
def test_settings_065_function_parameters_hint_on_input(papp):
    """SETTINGS-065: Function parameters hint on input

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: C document; with "Function parameters hint on input" ticked type "fopen("; then "name, "; then "\\"r\\")"; untick, Apply, type "fopen(" again.
    Expect: SCI_CALLTIPACTIVE 1 after "(" and still after ","; 0 after ")"; unticked, no call tip.
    """
    app = papp
    app.new("", language="c")
    app.type("fopen(")
    app.wait(lambda: app.sci(SCI_CALLTIPACTIVE), message="a call tip")
    app.type("name, ")
    assert app.sci(SCI_CALLTIPACTIVE)
    app.type("\"r\")")
    app.wait(lambda: not app.sci(SCI_CALLTIPACTIVE), message="the call tip gone")
    set_options(app, "Auto-Completion", checks={"Function parameters hint on input": False})
    app.new("", language="c")
    app.type("fopen(")
    app.idle(0.3)
    assert not app.sci(SCI_CALLTIPACTIVE)


@pytest.mark.case("SETTINGS-066")
def test_settings_066_auto_insert_pairs_and_the_close_tag(papp):
    """SETTINGS-066: Auto-insert pairs and the close tag

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: For each of "Auto-Insert: ( )", "[ ]", "{ }", "' '", "\\" \\"": tick only it, Apply, type its opener in an empty C++ document; tick "Auto-Insert: html/xml close tag", HTML document, type "<div>"; untick all and repeat.
    Expect: "()", "[]", "{}", "''", "\\"\\"" with the caret between; "<div></div>" with the caret after "<div>"; "<img/>" gets nothing; unticked: only the typed characters.
    """
    app = papp
    pairs = {"Auto-Insert: ( )": ("(", "()"), "Auto-Insert: [ ]": ("[", "[]"), "Auto-Insert: { }": ("{", "{}"),
             "Auto-Insert: ' '": ("'", "''"), "Auto-Insert: \" \"": ("\"", "\"\"")}
    off = {k: False for k in pairs} | {"Auto-Insert: html/xml close tag": False}
    for box, (typed, want) in pairs.items():
        set_options(app, "Auto-Completion", checks=off | {box: True})
        app.new("", language="cpp")
        app.type(typed)
        assert app.text() == want, (box, app.text())
        assert app.sci(SCI_GETCURRENTPOS) == 1
    set_options(app, "Auto-Completion", checks=off | {"Auto-Insert: html/xml close tag": True})
    app.new("", language="html")
    app.type("<div>")
    assert app.text() == "<div></div>" and app.sci(SCI_GETCURRENTPOS) == 5
    app.new("", language="html")
    app.type("<img/>")
    assert app.text() == "<img/>"
    set_options(app, "Auto-Completion", checks=off)
    for typed, _ in pairs.values():
        app.new("", language="cpp")
        app.type(typed)
        assert app.text() == typed
    app.new("", language="html")
    app.type("<div>")
    assert app.text() == "<div>"


@pytest.mark.case("SETTINGS-067")
def test_settings_067_user_matched_pairs(papp):
    """SETTINGS-067: User matched pairs

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: Set "Matched pair 1:" "<>" and "Matched pair 2:" "ab" (invalid: letters), Apply; type "<" in an empty document; type "<" before "x".
    Expect: "<>" in the empty document; "<x" before text; pref userMatchedPairs is ["<>"] (the letter pair is dropped).
    """
    app = papp
    set_options(app, "Auto-Completion", fields={"Matched pair 1:": "<>", "Matched pair 2:": "ab"})
    assert stored(app).get("userMatchedPairs") == ["<>"]
    app.new("")
    app.type("<")
    assert app.text() == "<>"
    app.new("x")
    app.sci(SCI_GOTOPOS, 0)
    app.type("<")
    assert app.text() == "<x"
    set_options(app, "Auto-Completion", fields={"Matched pair 1:": "", "Matched pair 2:": ""})


@pytest.mark.case("SETTINGS-068")
def test_settings_068_custom_date_format_its_preview_and_the_reversed_order(papp):
    """SETTINGS-068: Custom date format, its preview, and the reversed order

    Covers: IDM_SETTING_PREFERENCE, IDM_EDIT_INSERT_DATETIME_CUSTOMIZED, IDM_EDIT_INSERT_DATETIME_SHORT
    Channel: ui, mcp
    Steps: Set "Custom format" to "yyyy/MM/dd" (set_value), read the preview label beside it; Apply; run IDM_EDIT_INSERT_DATETIME_CUSTOMIZED; tick "Reverse default date time order (short & long formats)", Apply, run IDM_EDIT_INSERT_DATETIME_SHORT and compare with the unticked result.
    Expect: the preview shows today's date as yyyy/MM/dd as soon as the field changes; the inserted text matches ^\\d{4}/\\d{2}/\\d{2}$ and is today; reversed short form starts with the time (differs from the default, which starts with the date).
    """
    app = papp
    import datetime
    page(app, "Multi-Instance & Date")
    field(app, "Custom format", "yyyy/MM/dd")
    today = datetime.date.today().strftime("%Y/%m/%d")
    preview = [c for c in controls(app) if c["class"] == "NSTextField" and not c.get("editable")
               and re.fullmatch(r"\d{4}/\d{2}/\d{2}", str(c.get("value")))]
    assert preview and preview[0]["value"] == today, [c.get("value") for c in controls(app)]
    apply(app)
    close_prefs(app)
    app.new("")
    app.run("IDM_EDIT_INSERT_DATETIME_CUSTOMIZED")
    assert re.fullmatch(r"\d{4}/\d{2}/\d{2}", app.text()) and app.text() == today
    app.new("")
    app.run("IDM_EDIT_INSERT_DATETIME_SHORT")
    plain = app.text()
    set_options(app, "Multi-Instance & Date", checks={"Reverse default date time order (short & long formats)": True})
    app.new("")
    app.run("IDM_EDIT_INSERT_DATETIME_SHORT")
    reversed_ = app.text()
    # as Windows writes it: time then date; reversed, date then time
    time_first = re.compile(r"\d{1,2}[:.]\d{2}(?:\s*[AP]M)?\s")
    assert time_first.match(plain), plain
    assert not time_first.match(reversed_) and reversed_ != plain, (plain, reversed_)
    set_options(app, "Multi-Instance & Date", checks={"Reverse default date time order (short & long formats)": False},
                fields={"Custom format": "yyyy-MM-dd HH:mm:ss"})


@pytest.mark.case("SETTINGS-069")
def test_settings_069_word_character_list_changes_what_a_word_is(papp):
    """SETTINGS-069: Word character list changes what a word is

    Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_SELECTMATCHINGBRACES
    Channel: ui, mcp
    Steps: Text "alpha-beta gamma"; read SCI_WORDENDPOSITION(2, 1); tick "Add characters to the word list", set "Word character list" to "-", Apply, read it again; untick, Apply.
    Expect: 5 without, 10 with "-", 5 again; SCI_GETWORDCHARS contains "-" only while ticked.
    """
    app = papp
    app.new("alpha-beta gamma")
    assert app.sci(SCI_WORDENDPOSITION, 2, 1) == 5
    set_options(app, "Delimiter", checks={"Add characters to the word list": True}, fields={"Word character list": "-"})
    assert app.sci(SCI_WORDENDPOSITION, 2, 1) == 10
    assert "-" in app.sci(SCI_GETWORDCHARS, 0, 0, returns="string")
    set_options(app, "Delimiter", checks={"Add characters to the word list": False})
    assert app.sci(SCI_WORDENDPOSITION, 2, 1) == 5
    assert "-" not in app.sci(SCI_GETWORDCHARS, 0, 0, returns="string")


@pytest.mark.case("SETTINGS-070")
def test_settings_070_selection_between_delimiters_known_gap(papp):
    """SETTINGS-070: Selection between delimiters (known gap)

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Set "Delimiter: Open" "[" and "Delimiter: Close" "]", tick "Allow on several lines", Apply; text "arr[42] rest"; Cmd+double-click inside "42" (needs an editor mouse hook, see report).
    Expect: the selection is 4..6 ("42"); prefs delimiterOpen "[", delimiterClose "]", delimiterMultiline true persist across restart. (The port stores these settings but no user action uses them.)
    """
    app = papp
    set_options(app, "Delimiter", fields={"Delimiter: Open": "[", "Delimiter: Close": "]"}, checks={"Allow on several lines": True})
    app.restart()
    s = stored(app)
    assert (s.get("delimiterOpen"), s.get("delimiterClose"), s.get("delimiterMultiline")) in (("[", "]", True), ("[", "]", 1)), s
    app.new("arr[42] rest")
    app.mouse(view="main", point={"line": 1, "column": 5}, clicks=2, modifiers=["cmd"])
    assert (app.sci(SCI_GETSELECTIONSTART), app.sci(SCI_GETSELECTIONEND)) == (4, 6)


@pytest.mark.case("SETTINGS-071")
def test_settings_071_large_file_restriction_and_what_it_allows(papp, tmp):
    """SETTINGS-071: Large file restriction and what it allows

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp, files
    Steps: Set "Define Large File Size:" 1 with "Enable Large File Restriction (no syntax highlighting)" ticked, "Allow Brace Match", "Allow URL Clickable Link", "Allow Auto-Completion", "Allow Smart Highlighting" unticked, "Deactivate Word Wrap globally" ticked, Apply; open a 1.5 MB C++ file with a comment and a URL on line 1 and word wrap on; then untick the restriction, Apply, reopen.
    Expect: restricted: SCI_GETSTYLEAT(0) is 0 (no highlighting), no link indicator (14) on the URL, no smart highlight, SCI_GETWRAPMODE none; unrestricted: line 1 is SCE_C_COMMENTLINE; a size of 5000 is stored as 2046.
    """
    app = papp
    f = tmp / "big.cpp"
    line1 = "// see https://example.org/page\n"
    f.write_text(line1 + "int value_name = 1; // filler text for size\n" * 36000)
    assert 1_400_000 < f.stat().st_size < 1_700_000
    allow = {"Allow Brace Match": False, "Allow URL Clickable Link": False, "Allow Auto-Completion": False,
             "Allow Smart Highlighting": False}
    set_options(app, "Performance", checks={"Enable Large File Restriction (no syntax highlighting)": True,
                                            "Deactivate Word Wrap globally": True} | allow,
                fields={"Define Large File Size:": 1})
    if not app.checked("IDM_VIEW_WRAP"):
        app.run("IDM_VIEW_WRAP")
    try:
        app.open(f)
        app.idle(0.5)
        assert app.sci(SCI_GETSTYLEAT, 0) == 0
        assert not indicator_runs_upto(app, 14, len(line1))
        assert app.sci(SCI_GETWRAPMODE) == SC_WRAP_NONE
        app.sci(SCI_SETSEL, len(line1) + 4, len(line1) + 9)       # "value"
        app.idle(0.3)
        assert not indicator_runs_upto(app, 12, 5000)
        app.close_all()
        set_options(app, "Performance", checks={"Enable Large File Restriction (no syntax highlighting)": False})
        app.open(f)
        app.wait(lambda: app.sci(SCI_GETSTYLEAT, 0) == SCE_C_COMMENTLINE, message="the comment highlighted")
        app.close_all()
        before = stored(app)
        set_options(app, "Performance", checks={"Enable Large File Restriction (no syntax highlighting)": True},
                    fields={"Define Large File Size:": 5000})
        assert 2046 in U.diff(before, stored(app)).values(), U.diff(before, stored(app))
    finally:
        app.close_all()
        if app.checked("IDM_VIEW_WRAP"):
            app.run("IDM_VIEW_WRAP")


@pytest.mark.case("SETTINGS-072")
def test_settings_072_tab_bar_options_reach_the_tab_bar(papp):
    """SETTINGS-072: Tab bar options reach the tab bar

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, snapshot, prefs
    Steps: For each of "Tab Bar: Hide", "Vertical", "Multi-line", "Show close button", "Show buttons on inactive tabs", "Reduce", "Change inactive tab color", "Draw a colored bar on active tab", "Lock (no drag and drop)": flip it, Apply, read the tab bar view (NppTabBarView in `ui`, hidden/frame) and its matching property (`e2e_invoke get editor tabBar.<property>`), flip back.
    Expect: Hide removes the tab bar from the visible controls; Vertical makes it taller than wide and left of the editor; each other property follows its checkbox; each preference key is stored.
    """
    app = papp
    boxes = {"Tab Bar: Hide": ("hideTabBar", "hidden"), "Multi-line": ("tabBarMultiLine", "multiLine"),
             "Show close button": ("tabShowCloseButton", "showCloseButtons"),
             "Show buttons on inactive tabs": ("tabCloseButtonOnInactive", "closeButtonsOnInactiveTabs"),
             "Reduce": ("tabReduced", "reduced"), "Change inactive tab color": ("tabColourInactive", "colourInactiveTabs"),
             "Draw a colored bar on active tab": ("tabDrawActiveBar", "drawActiveBar"),
             "Lock (no drag and drop)": ("tabBarLocked", "locked"), "Vertical": ("tabBarVertical", "vertical")}
    bars = lambda: [c for c in app.ui("main")["controls"] if c["class"] == "NppTabBarView"]
    for title, (key, prop) in boxes.items():
        page(app, "Tab Bar")
        was = state(app, title)
        check(app, title, not was)
        apply(app)
        assert bool(stored(app).get(key)) == (not was), title
        assert bool(app.get("editor", f"tabBar.{prop}")) == (not was), title
        if title == "Tab Bar: Hide":
            assert (not bars()) == (not was)
        check(app, title, bool(was))
        apply(app)
        assert bool(app.get("editor", f"tabBar.{prop}")) == bool(was), title
    close_prefs(app)
    # Last: a Vertical tab bar stands down the left of the panes (the split holding them is the
    # bar's sibling; sciView's own frame is inside that split).
    set_options(app, "Tab Bar", checks={"Vertical": True})
    try:
        app.idle(0.3)
        x, y, w, h = U.rect(app.get("editor", "tabBar.frame"))
        ex, ey, ew, eh = U.rect(app.get("editor", "editorSplit.frame"))
        assert h > w and x + w <= ex + 1, ((x, y, w, h), (ex, ey, ew, eh))
    finally:
        set_options(app, "Tab Bar", checks={"Vertical": False})


@pytest.mark.case("SETTINGS-073")
def test_settings_073_max_tab_label_length_and_double_click_to_close(papp, tmp):
    """SETTINGS-073: Max tab label length and double click to close

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Open `tmp/averylongfilename.txt`; set "Max. tab label length:" 4, Apply; read the tab's label in `ui`; tick "Double click to close document", Apply, double-click the tab (needs a tab double-click hook, see report); set the length back to 0.
    Expect: the label is at most 5 characters with an ellipsis; after the double click the document is closed; length 0 shows the full name.
    """
    app = papp
    f = tmp / "averylongfilename.txt"
    f.write_text("x\n")
    app.open(f)
    def label_ink():
        """How many pixel columns the label of the file's tab has ink in (the label itself is not exposed)."""
        from PIL import Image
        bar = next(c for c in app.ui("main")["controls"] if c["class"] == "NppTabBarView")
        tab = next(t for t in bar["tabs"] if t["title"] == "averylongfilename.txt")
        bh = U.rect(app.get("editor", "tabBar.frame"))[3]
        cw = U.rect(app.get("window", "contentView.frame"))[2]
        img = U.still_snapshot(app, tmp / "tabs.png")     # the tab bar is the top of the picture
        k = img.width / cw
        top = 0
        x0, x1 = (tab["frame"][0] + 4) * k, (tab["frame"][0] + tab["frame"][2] - 24) * k   # the close button left out
        crop = img.crop((int(x0), int(top + 3 * k), int(x1), int(top + (bh - 3) * k)))
        px = crop.load()
        back = px[1, 1]
        return sum(1 for cx in range(crop.width)
                   if any(sum(abs(a - b) for a, b in zip(px[cx, cy], back)) > 90 for cy in range(crop.height)))
    full = label_ink()
    set_options(app, "Tab Bar", fields={"Max. tab label length:": 4})
    assert stored(app).get("tabMaxLabelLength") == 4
    app.wait(lambda: label_ink() < full * 0.5, message="the label shortened to 4 characters and an ellipsis")
    set_options(app, "Tab Bar", fields={"Max. tab label length:": 0})
    app.wait(lambda: abs(label_ink() - full) <= 2, message="the full name again")
    set_options(app, "Tab Bar", checks={"Double click to close document": True})
    bar = next(c for c in app.ui("main")["controls"] if c["class"] == "NppTabBarView")
    t = next(t for t in bar["tabs"] if t["title"] == "averylongfilename.txt")
    app.mouse("main", point=[t["frame"][0] + t["frame"][2] / 2, t["frame"][1] + t["frame"][3] / 2], clicks=2,
              **{"class": "NppTabBarView"})
    app.wait(lambda: "averylongfilename.txt" not in [d["title"] for d in app.docs()], message="the double-clicked tab closed")


@pytest.mark.case("SETTINGS-074")
def test_settings_074_exit_on_close_the_last_tab_and_the_pin_feature(fresh):
    """SETTINGS-074: Exit on close the last tab and the pin feature

    Covers: IDM_SETTING_PREFERENCE, IDM_FILE_CLOSE
    Channel: ui, menu, launch
    Steps: Untick "Enable pin tab feature", Apply, read the tab context menu (`e2e_menu context=tab`) and File > Pin Tab; tick "Exit on close the last tab", Apply, run IDM_FILE_CLOSE on the only document.
    Expect: without the pin feature "Pin Tab" is absent or disabled in both menus (tabPinFeatureEnabled is used nowhere in the port: xfail, BUG); closing the last tab quits the app (the process exits); a restarted app still has exitOnClosingLastTab true.
    """
    app = fresh
    app.close_all()                  # before the option: with it, closing the last tab quits
    assert len(app.docs()) == 1
    set_options(app, "Tab Bar", checks={"Exit on close the last tab": True})
    assert stored(app).get("exitOnClosingLastTab") in (True, 1)
    proc = app.proc
    try:
        app.keys("cmd+w")            # the reply may never come: the app quits
    except Exception:  # noqa: BLE001
        pass
    app.wait(lambda: proc.poll() is not None, timeout=15, message="the app quit after its last tab closed")
    app.stop()                        # the harness lets go of the gone process
    app.start(clean_home=False, reset=False)
    assert app.pref("exitOnClosingLastTab") in (True, 1)


@pytest.mark.case("SETTINGS-074")
def test_settings_074_without_the_pin_feature_pin_tab_is_not_offered(papp):
    """SETTINGS-074 (pin): unticked, Pin Tab is absent or disabled in the tab menu and File menu"""
    app = papp
    set_options(app, "Tab Bar", checks={"Enable pin tab feature": False})
    item = app.menu("File|Pin Tab").get("File|Pin Tab")
    tab_menu = app.call("e2e_menu", context="tab").get("items") or app.call("e2e_menu", context="tab").get("tree") or []
    pins = [i for i in tab_menu if "Pin" in str(i.get("title"))]
    assert (item is None or not item["enabled"]) and all(not i.get("enabled") for i in pins), (item, pins)


@pytest.mark.case("SETTINGS-075")
def test_settings_075_number_of_entries_full_path_and_length(papp, tmp):
    """SETTINGS-075: Number of entries, full path and length

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, menu, launch
    Steps: Set "Max. number of entries:" 3, Apply; open and close five files from `tmp`; read the File menu's recent entries; tick "Full File Name Path" and set "Customize Maximum Length:" 20, Apply; restart.
    Expect: three entries, the most recent first; with the full path they start with "…" and are 20 characters long, ending with the file name; the same after restart.
    """
    app = papp
    recent = lambda: [i.get("title") for i in app.menu_tree("File|Open Recent", 1) if i.get("action") == "openRecentFile:"]
    set_options(app, "Recent Files History", fields={"Max. number of entries:": 3})
    names = [f"recent_{i}.txt" for i in range(5)]
    for n in names:
        f = tmp / n
        f.write_text(n)
        app.open(f)
        app.run("IDM_FILE_CLOSE")
    app.restart()                   # Open Recent is not rebuilt when a tab closes (FILE-043)
    assert recent() == ["recent_4.txt", "recent_3.txt", "recent_2.txt"], recent()
    set_options(app, "Recent Files History", checks={"Full File Name Path": True}, fields={"Customize Maximum Length:": 20})
    app.restart()
    shown = recent()
    assert len(shown) == 3 and all(e.startswith("…") and len(e) == 20 for e in shown), shown
    assert [e[-len("recent_4.txt"):] for e in shown] == ["recent_4.txt", "recent_3.txt", "recent_2.txt"]


@pytest.mark.case("SETTINGS-076")
def test_settings_076_open_save_dialogs_start_in_the_configured_folder(papp, tmp):
    """SETTINGS-076: Open/Save dialogs start in the configured folder

    Covers: IDM_SETTING_PREFERENCE, IDM_FILE_OPEN
    Channel: ui, modal
    Steps: Open `tmp/a/x.txt`; with "Follow current document" run IDM_FILE_OPEN with a cancelled panel and read the logged panel's directory; "A fixed folder" with "Fixed folder" `tmp/b`, Apply, again; "Remember last used directory", open a file from `tmp/c` through the panel, then run IDM_FILE_OPEN again.
    Expect: the logged directories are `tmp/a`, `tmp/b`, `tmp/c` respectively.
    """
    app = papp
    for d in "abc":
        (tmp / d).mkdir()
    x = tmp / "a" / "x.txt"
    x.write_text("x")
    y = tmp / "c" / "y.txt"
    y.write_text("y")
    app.open(x)

    def panel_dir():
        app.answers(panels=[None])
        app.run("IDM_FILE_OPEN")
        entry = [e for e in app.modal_log() if e["kind"] == "open"][-1]
        return entry["directory"]
    set_options(app, "Default Directory", popups={"Default Open/Save file Directory": "Follow current document"})
    assert app.same_path(panel_dir(), tmp / "a")
    set_options(app, "Default Directory", popups={"Default Open/Save file Directory": "A fixed folder"},
                fields={"Fixed folder": str(tmp / "b")})
    assert app.same_path(panel_dir(), tmp / "b")
    set_options(app, "Default Directory", popups={"Default Open/Save file Directory": "Remember last used directory"})
    app.answers(panels=[str(y)])
    app.run("IDM_FILE_OPEN")
    app.wait(lambda: any(d["path"] and app.same_path(d["path"], y) for d in app.docs()), message="y.txt opened")
    app.select(1, 1)
    app.open(x)
    assert app.same_path(panel_dir(), tmp / "c")
    set_options(app, "Default Directory", popups={"Default Open/Save file Directory": "Follow current document"})


@pytest.mark.case("SETTINGS-077")
def test_settings_077_filling_the_find_field(papp):
    """SETTINGS-077: Filling the Find field

    Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_FIND
    Channel: ui, mcp
    Steps: Select "needle" and run IDM_SEARCH_FIND, read the Find window's field; with nothing selected and the caret in "word", run it again; set "Max Characters to Auto-Fill Find Field" 3, Apply, select "abcdef", run it; untick "Fill Find Field with Selected Text" and "Select Word Under Caret when Nothing Selected", Apply, repeat.
    Expect: "needle"; "word"; not "abcdef" when over the limit; with the options off the field keeps its previous text; with 'Minimum Size for Auto-Checking "In selection"' 10, a 12-character two-line selection opens Find with "In selection" ticked and a 5-character one without.
    """
    app = papp
    import _util_search as S
    def opened_with():
        d = S.open_dlg(app)
        v = d.value("what")
        d.close()
        return v
    app.new("needle word abcdef\n")
    app.select(1, 1, 1, 7)
    assert opened_with() == "needle"
    app.call("go_to", line=1, column=10)
    assert opened_with() == "word"
    set_options(app, "Searching", fields={"Max Characters to Auto-Fill Find Field": 3})
    app.select(1, 13, 1, 19)
    assert opened_with() != "abcdef"
    set_options(app, "Searching", checks={"Fill Find Field with Selected Text": False,
                                          "Select Word Under Caret when Nothing Selected": False},
                fields={"Max Characters to Auto-Fill Find Field": 1024})
    before = opened_with()
    app.select(1, 1, 1, 7)
    assert opened_with() == before
    app.call("go_to", line=1, column=10)
    assert opened_with() == before


@pytest.mark.case("SETTINGS-077")
def test_settings_077_in_selection_follows_the_selection_size(papp):
    """SETTINGS-077 (In selection): a 12-character two-line selection over a threshold of 10 ticks it, a 5-character one does not"""
    app = papp
    import _util_search as S
    set_options(app, "Searching", fields={'Minimum Size for Auto-Checking "In selection"': 10})
    app.new("abcdef\nghijkl\n")
    app.select(1, 1, 2, 6)
    d = S.open_dlg(app)
    assert d.state("insel") == 1
    d.close()
    app.select(1, 1, 1, 6)
    d = S.open_dlg(app)
    try:
        assert d.state("insel") == 0
    finally:
        d.close()


@pytest.mark.case("SETTINGS-078")
def test_settings_078_confirm_replace_all_and_replace_staying_on_the_occurrence(papp):
    """SETTINGS-078: Confirm Replace All and Replace staying on the occurrence

    Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_REPLACE
    Channel: ui, modal, mcp
    Steps: Text "cat cat cat"; in the Replace window find "cat" replace "dog" and click Replace All with "Confirm Replace All" ticked and alert answer "Cancel"-equivalent (button 2); then answer 1; untick it and repeat on fresh text; tick "Replace: Don't move to the following occurrence", click Replace once.
    Expect: an alert is logged and cancelling leaves the text; confirming gives "dog dog dog"; unticked, no alert; with "Replace: Don't move to the following occurrence" on, Replace changes the first match and the selection stays on the replaced text instead of moving to the next "cat" (replaceStaysOnOccurrence is used nowhere in the port: xfail, BUG).
    """
    app = papp

    def replace_all(answer):
        app.new("cat cat cat")
        app.run("IDM_SEARCH_REPLACE")
        w = "Replace"
        combos = [c for c in app.ui(w)["controls"] if c["class"] == "NSComboBox"]
        app.act(w, "set_value", "cat", path=combos[0]["path"])
        app.act(w, "set_value", "dog", path=combos[1]["path"])
        if answer is not None:
            app.answers(alerts=[answer])
        app.click(w, "Replace All")
        app.close_window(w)
        return [e for e in app.modal_log() if e["kind"] == "alert"], app.text()
    # The port's own box, off by default (upstream's Replace All does not ask).
    assert stored(app).get("confirmReplaceAll") in (False, 0, None)
    set_options(app, "Searching", checks={"Confirm Replace All": True})
    alerts, text = replace_all(2)
    assert alerts and text == "cat cat cat", (alerts, text)
    alerts, text = replace_all(1)
    assert alerts and text == "dog dog dog"
    set_options(app, "Searching", checks={"Confirm Replace All": False})
    alerts, text = replace_all(None)
    assert not alerts and text == "dog dog dog"


@pytest.mark.case("SETTINGS-078")
def test_settings_078_replace_stays_on_the_replaced_text(papp):
    """SETTINGS-078 (stay): with the option on, Replace does not go on to the next occurrence

    Upstream's processReplace (_replaceStopsWithoutFindingNext) leaves the caret right after
    the replacement, SCI_SETSEL(start + len, start + len), and finds nothing further."""
    app = papp
    set_options(app, "Searching", checks={"Replace: Don't move to the following occurrence": True})
    app.new("cat cat cat")
    app.run("IDM_SEARCH_REPLACE")
    w = "Replace"
    combos = [c for c in app.ui(w)["controls"] if c["class"] == "NSComboBox"]
    app.act(w, "set_value", "cat", path=combos[0]["path"])
    app.act(w, "set_value", "dog", path=combos[1]["path"])
    app.sci(SCI_SETSEL, 0, 3)
    app.click(w, "Replace", **{"class": "NSButton"})   # the button, not the window titled Replace
    app.close_window(w)
    assert app.text().startswith("dog cat")
    assert (app.sci(SCI_GETSELECTIONSTART), app.sci(SCI_GETSELECTIONEND)) == (3, 3)


@pytest.mark.case("SETTINGS-079")
def test_settings_079_compare_options_from_searching(papp, tmp):
    """SETTINGS-079: Compare options from Searching

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Two documents "Alpha\\n\\nbeta" and "alpha\\nbeta  "; tick "Compare: ignore case", "Compare: ignore spaces", "Compare: ignore empty lines", Apply; call the compare tool; untick, Apply, compare again.
    Expect: with the options on the documents compare as identical; off, differences are reported.
    """
    app = papp
    from _util_compare import IDENTICAL, alerts as compare_alerts, clear_all
    a, b = tmp / "a.txt", tmp / "b.txt"
    a.write_text("Alpha\n\nbeta\n")
    b.write_text("alpha\nbeta  \n")

    def compare():
        clear_all(app)
        app.open(a)
        app.answers(panels=[str(b)])
        app.run("Plugins|Compare|Compare with File...")
        found = compare_alerts(app.modal_log())
        clear_all(app)
        return found[-1].get("informative") if found else None
    set_options(app, "Searching", checks={"Compare: ignore case": True, "Compare: ignore spaces": True,
                                          "Compare: ignore empty lines": True})
    assert compare() == IDENTICAL
    set_options(app, "Searching", checks={"Compare: ignore case": False, "Compare: ignore spaces": False,
                                          "Compare: ignore empty lines": False})
    assert compare() != IDENTICAL


@pytest.mark.case("SETTINGS-080")
def test_settings_080_find_dialog_remains_open_after_a_results_window_search(papp):
    """SETTINGS-080: Find dialog remains open after a results-window search

    Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_FIND
    Channel: ui
    Steps: Open Find, type "x", click "Find All in Current Document" with "Find dialog remains open after search that outputs to results window" unticked; tick it, Apply, repeat.
    Expect: unticked: the Find window is hidden after the search; ticked: it stays visible.
    """
    app = papp
    app.new("x y x")

    def find_all_shown():
        app.run("IDM_SEARCH_FIND")
        combo = next(c for c in app.ui("Find")["controls"] if c["class"] == "NSComboBox")
        app.act("Find", "set_value", "x", path=combo["path"])
        app.click("Find", "Find All in Current Document")
        app.idle(0.3)
        shown = window_visible(app, "Find")
        if shown:
            app.close_window("Find")
        return shown
    assert find_all_shown() is False
    set_options(app, "Searching", checks={"Find dialog remains open after search that outputs to results window": True})
    assert find_all_shown() is True
    set_options(app, "Searching", checks={"Find dialog remains open after search that outputs to results window": False})
    app.close_all()


@pytest.mark.case("SETTINGS-081")
def test_settings_081_clickable_links_underline_and_custom_schemes(papp):
    """SETTINGS-081: Clickable links, underline and custom schemes

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, mcp
    Steps: Text "see https://example.org/page and obsidian://open?vault=x"; count runs of indicator 14 with "Clickable Link Settings: Enable" ticked and "URI customized schemes:" empty; set the schemes to "obsidian", Apply; tick "No underline", Apply, read SCI_INDICGETSTYLE(14); tick Searching > "Enable fullbox mode", Apply, read it again; untick Enable, Apply.
    Expect: 1 link, then 2; the indicator style is INDIC_PLAIN normally, INDIC_HIDDEN with No underline, INDIC_ROUNDBOX with fullbox mode; disabled: 0 runs.
    """
    app = papp
    app.new("see https://example.org/page and obsidian://open?vault=x\n")
    def links():
        app.idle(0.1)
        return len(indicator_runs(app, 14))
    set_options(app, "Cloud & Link", checks={"Clickable Link Settings: Enable": True, "No underline": False},
                fields={"URI customized schemes:": ""})
    app.wait(lambda: links() == 1, message="one link (https)")
    assert app.sci(SCI_INDICGETSTYLE, 14) == INDIC_PLAIN
    set_options(app, "Cloud & Link", fields={"URI customized schemes:": "obsidian"})
    app.wait(lambda: links() == 2, message="two links with the obsidian scheme")
    set_options(app, "Cloud & Link", checks={"No underline": True})
    app.wait(lambda: app.sci(SCI_INDICGETSTYLE, 14) == INDIC_HIDDEN, message="no underline")
    set_options(app, "Searching", checks={"Enable fullbox mode": True})
    app.wait(lambda: app.sci(SCI_INDICGETSTYLE, 14) == INDIC_ROUNDBOX, message="fullbox")
    set_options(app, "Cloud & Link", checks={"Clickable Link Settings: Enable": False})
    app.wait(lambda: links() == 0, message="no links when disabled")


@pytest.mark.case("SETTINGS-082")
def test_settings_082_the_settings_folder_moves_the_settings_files(fresh, tmp):
    """SETTINGS-082: The settings folder moves the settings files

    Covers: IDM_SETTING_PREFERENCE, IDM_SETTING_EDITCONTEXTMENU, IDM_SETTING_SHORTCUT_MAPPER
    Channel: ui, files, launch, modal
    Steps: With `fresh_app`, set "Set your cloud location path here:" to `tmp/cloud`, Apply; remove a shortcut in the Shortcut Mapper (Modify… with alert answer "Remove"); run IDM_SETTING_EDITCONTEXTMENU (alert answered 1); restart; run IDM_SETTING_EDITCONTEXTMENU again; clear the field, Apply.
    Expect: shortcuts.xml and contextMenu.xml are written in `tmp/cloud`, not in the home's NotepadMac folder; the opened contextMenu.xml's path (get_document) is in `tmp/cloud` before and after the restart; the removed shortcut is still removed after the restart (read from the cloud folder).
    """
    app = fresh
    cloud = tmp / "cloud"
    cloud.mkdir()
    home_dir = support(app)
    home_menu = home_dir / "contextMenu.xml"
    home_before = home_menu.read_bytes() if home_menu.exists() else None   # the app writes a default at start
    set_options(app, "Cloud & Link", fields={"Set your cloud location path here:": str(cloud)})
    assert stored(app).get("settingsDirectory") == str(cloud)
    U.open_mapper(app)
    U.mapper_select(app, "Find Next", "Search")
    app.answers(alerts=["Remove"])
    app.click(U.MAPPER, "Modify…")
    U.close_mapper(app)
    app.wait(lambda: (cloud / "shortcuts.xml").exists(), message="shortcuts.xml in the cloud folder")
    assert not (home_dir / "shortcuts.xml").exists()
    def open_context_menu_file():
        app.answers(alerts=[1])
        app.run("IDM_SETTING_EDITCONTEXTMENU")
        app.wait(lambda: (app.doc().get("path") or "").endswith("contextMenu.xml"), message="contextMenu.xml opened")
        return app.doc()["path"]
    assert app.same_path(open_context_menu_file(), cloud / "contextMenu.xml")
    assert (cloud / "contextMenu.xml").exists()
    assert (home_menu.read_bytes() if home_menu.exists() else None) == home_before
    app.restart()
    assert app.same_path(open_context_menu_file(), cloud / "contextMenu.xml")
    assert not app.menu_item("IDM_SEARCH_FINDNEXT").get("key")
    assert 'id="43002"' in (cloud / "shortcuts.xml").read_text()
    set_options(app, "Cloud & Link", fields={"Set your cloud location path here:": ""})
    assert not stored(app).get("settingsDirectory")


@pytest.mark.case("SETTINGS-083")
def test_settings_083_show_only_filename_in_title_bar(papp, tmp):
    """SETTINGS-083: Show only filename in title bar

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, launch
    Steps: Open `tmp/t_title.txt`; tick "Show only filename in title bar", Apply, read the main window's title; untick, Apply.
    Expect: "t_title.txt" exactly while ticked; with the full path otherwise; persists across restart.
    """
    app = papp
    f = tmp / "t_title.txt"
    f.write_text("title\n")
    app.open(f)
    title = lambda: app.get("window", "title")
    set_options(app, "MISC.", checks={"Show only filename in title bar": True})
    app.wait(lambda: title() == "t_title.txt", message="only the file name")
    app.restart()
    app.open(f)
    app.wait(lambda: title() == "t_title.txt", message="only the file name after a restart")
    set_options(app, "MISC.", checks={"Show only filename in title bar": False})
    app.wait(lambda: str(tmp) in title() or str(tmp).replace("/private", "") in title(), message="the path back in the title")
    assert title().startswith("t_title.txt")


@pytest.mark.case("SETTINGS-084")
def test_settings_084_document_switcher_and_mru_order(papp, tmp):
    """SETTINGS-084: Document Switcher and MRU order

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, keys, mcp
    Steps: Documents A, B, C; activate A then C; with "Document Switcher (Ctrl+TAB): Enable" and "    Enable MRU behaviour" ticked press ctrl+tab; untick Enable, Apply, activate B and press ctrl+tab.
    Expect: MRU: A becomes current and the switcher window is shown while Control is held; disabled: C (the next tab) becomes current and no switcher window appears.
    """
    app = papp
    files = []
    for c in "ABC":
        f = tmp / f"{c}.txt"
        f.write_text(c)
        files.append(f)
    app.close_all()
    for f in files:
        app.open(f)
    app.open(files[0])          # visit A, then C: most recent first is C, A, B
    app.open(files[2])
    current = lambda: app.doc()["title"]
    def switcher():
        return [w for w in app.windows() if w["class"] == "NSPanel" and w["visible"] and not w["title"]]
    set_options(app, "MISC.", checks={"Document Switcher (Ctrl+TAB): Enable": True, "    Enable MRU behaviour": True})
    app.call("e2e_keys", keys=["ctrl+tab"], hold=["ctrl"], keep_held=True)
    try:
        assert current() == "A.txt"
        assert switcher(), "the switcher shows while Control is held"
    finally:
        app.call("e2e_keys", keys=[], release=True)
    app.wait(lambda: not switcher(), timeout=3, message="the switcher gone")
    set_options(app, "MISC.", checks={"Document Switcher (Ctrl+TAB): Enable": False})
    app.open(files[1])
    app.call("e2e_keys", keys=["ctrl+tab"], hold=["ctrl"], keep_held=True)
    try:
        assert current() == "C.txt", "disabled: the next tab"
        assert not switcher()
    finally:
        app.call("e2e_keys", keys=[], release=True)


@pytest.mark.case("SETTINGS-085")
def test_settings_085_save_all_confirmation(papp, tmp):
    """SETTINGS-085: Save All confirmation

    Covers: IDM_SETTING_PREFERENCE, IDM_FILE_SAVEALL
    Channel: ui, modal, files
    Steps: Two modified files from `tmp`; with "Enable Save All confirm dialog" ticked run IDM_FILE_SAVEALL with alert answer "Yes"/1; modify again, untick, Apply, run it again.
    Expect: ticked: one confirmation alert is logged and both files are written; unticked: no alert and both files are written.
    """
    app = papp
    a, b = tmp / "sa.txt", tmp / "sb.txt"
    a.write_text("a\n"); b.write_text("b\n")
    app.close_all()
    def edit_both(mark):
        for f in (a, b):
            app.open(f)
            app.call("edit_document", edits=[{"start_line": 1, "start_column": 1, "end_line": 1, "end_column": 1, "text": mark}])
            assert app.doc()["modified"]
    set_options(app, "MISC.", checks={"Enable Save All confirm dialog": True})
    edit_both("1")
    app.modal_log()
    app.answers(alerts=[1])
    app.run("IDM_FILE_SAVEALL")
    alerts = [e for e in app.modal_log() if e["kind"] == "alert"]
    assert len(alerts) == 1, alerts
    assert a.read_text() == "1a\n" and b.read_text() == "1b\n"
    set_options(app, "MISC.", checks={"Enable Save All confirm dialog": False})
    edit_both("2")
    app.modal_log()
    app.run("IDM_FILE_SAVEALL")
    assert not [e for e in app.modal_log() if e["kind"] == "alert"]
    assert a.read_text() == "21a\n" and b.read_text() == "21b\n"


@pytest.mark.case("SETTINGS-086")
def test_settings_086_mute_all_sounds(papp):
    """SETTINGS-086: Mute all sounds

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, prefs
    Steps: Tick "Mute all sounds", Apply; run a command that beeps (Find Next with no match) — needs a beep counter hook, see report.
    Expect: pref muteSounds true and no beep is recorded; unticked, one beep.
    """
    app = papp
    app.new("just words")
    def calculate_nothing():
        app.call("go_to", line=1, column=11)
        app.run("Edit|Calculate")          # no formula at the caret: it beeps
    set_options(app, "MISC.", checks={"Mute all sounds": True})
    assert stored(app).get("muteSounds") in (True, 1)
    app.call("e2e_counters", reset=True)
    calculate_nothing()
    c = app.call("e2e_counters")
    assert c["beeps"] == 0 and c["muted_beeps"] == 1, c
    set_options(app, "MISC.", checks={"Mute all sounds": False})
    app.call("e2e_counters", reset=True)
    calculate_nothing()
    c = app.call("e2e_counters")
    assert c["beeps"] == 1 and c["muted_beeps"] == 0, c


@pytest.mark.case("SETTINGS-087")
def test_settings_087_folder_as_workspace_symlinks(papp, tmp):
    """SETTINGS-087: Folder as Workspace symlinks

    Covers: IDM_SETTING_PREFERENCE, IDM_FILE_OPENFOLDERASWORKSPACE
    Channel: ui, modal
    Steps: Folder `tmp/ws` with real.txt and a symlink link.txt; with "Allow loading symlinks in Folder as Workspace panel" unticked open it as workspace (panel answer); read the workspace panel's outline; tick, Apply, open it again.
    Expect: only real.txt without the option; real.txt and link.txt with it.
    """
    app = papp
    ws = tmp / "ws"
    ws.mkdir()
    (ws / "real.txt").write_text("r")
    os.symlink(ws / "real.txt", ws / "link.txt")
    def names():
        app.answers(panels=[str(ws)])
        app.run("IDM_FILE_OPENFOLDERASWORKSPACE")
        try:
            return sorted(app.invoke("editor", "workspaceTopLevelNames"))
        finally:
            app.invoke("editor", "openFolderAsWorkspace:", [None])
    set_options(app, "MISC.", checks={"Allow loading symlinks in Folder as Workspace panel": False})
    assert names() == ["real.txt"]
    set_options(app, "MISC.", checks={"Allow loading symlinks in Folder as Workspace panel": True})
    assert names() == ["link.txt", "real.txt"]


@pytest.mark.case("SETTINGS-088")
def test_settings_088_session_and_workspace_file_extensions(papp, tmp):
    """SETTINGS-088: Session and workspace file extensions

    Covers: IDM_SETTING_PREFERENCE, IDM_FILE_SAVESESSION
    Channel: ui, files, modal
    Steps: Set "Session file ext." "npps" and "Workspace file ext." ".nppw", Apply; save a session with one file to `tmp/s.npps` (panel answer); close all; open `tmp/s.npps`; open a project file `tmp/p.nppw`.
    Expect: opening s.npps loads the session (the file is open again, the session file itself is not shown as text); p.nppw opens in Project Panel 1, not as a text document.
    """
    app = papp
    f = tmp / "in_session.txt"
    f.write_text("kept\n")
    set_options(app, "MISC.", fields={"Session file ext.": "npps", "Workspace file ext.": ".nppw"})
    app.close_all()
    app.open(f)
    s = tmp / "s.npps"
    app.answers(panels=[str(s)])
    app.run("IDM_FILE_SAVESESSION")
    app.wait(lambda: s.exists(), message="the session file written")
    app.close_all()
    app.open(s)
    titles = lambda: [d["title"] for d in app.docs()]
    app.wait(lambda: "in_session.txt" in titles(), message="the session loaded")
    assert "s.npps" not in titles()
    p = tmp / "p.nppw"
    p.write_text('<NotepadPlus><Project name="P"><File name="in_session.txt"/></Project></NotepadPlus>\n')
    app.open(p)
    app.wait(lambda: panel_shown(app, "project1"), message="Project Panel 1 shown")
    assert "p.nppw" not in titles()


@pytest.mark.case("SETTINGS-089")
def test_settings_089_git_margin_marks_and_the_mcp_switch_are_applied(fresh):
    """SETTINGS-089: Git margin marks and the MCP switch are applied

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, prefs
    Steps: With `fresh_app`, untick "Git: mark lines changed since the last commit in the margin", Apply, read the persistent domain; tick "Let AI agents drive the editor (MCP)" (already on through the launch argument) and Apply, read the persistent domain.
    Expect: gitMarginMarks false and agentServer true are stored (README says MCP is turned on in Preferences). Currently Apply writes neither (xfail, BUG).
    """
    app = fresh
    set_options(app, "MISC.", checks={"Git: mark lines changed since the last commit in the margin": False,
                                      "Let AI agents drive the editor (MCP)": True})
    s = stored(app)
    assert s.get("gitMarginMarks") in (False, 0), s
    assert s.get("agentServer") in (True, 1), s


@pytest.mark.case("SETTINGS-090")
def test_settings_090_auto_updater_mode_and_releases_repository(papp):
    """SETTINGS-090: Auto-updater mode and releases repository

    Covers: IDM_SETTING_PREFERENCE
    Channel: ui, prefs
    Steps: Select "Enable on Notepad++ exit" in "Auto-updater:", set "Releases repository" to "someone/Fork", Apply; set the repository to "not-a-repo", Apply; select "Disable", Apply.
    Expect: autoUpdateMode 2 then 0; updateRepository "someone/Fork", and "not-a-repo" (no single slash) is refused, leaving "someone/Fork".
    """
    app = papp
    set_options(app, "MISC.", popups={"Auto-updater:": "Enable on Notepad++ exit"}, fields={"Releases repository": "someone/Fork"})
    s = stored(app)
    assert s.get("autoUpdateMode") == 2 and s.get("updateRepository") == "someone/Fork", s
    set_options(app, "MISC.", fields={"Releases repository": "not-a-repo"})
    assert stored(app).get("updateRepository") == "someone/Fork"
    set_options(app, "MISC.", popups={"Auto-updater:": "Disable"})
    assert stored(app).get("autoUpdateMode") == 0


@pytest.mark.case("SETTINGS-091")
def test_settings_091_the_chosen_engine_is_what_search_on_internet_opens(papp):
    """SETTINGS-091: The chosen engine is what Search on Internet opens

    Covers: IDM_SETTING_PREFERENCE, IDM_EDIT_SEARCHONINTERNET
    Channel: ui, mcp
    Steps: Select "word" in the document; for each of DuckDuckGo, Google, Bing, Yahoo! and "Set your search engine here:" with "https://example.org/find?w=$(CURRENT_WORD)&x=1": Apply, run IDM_EDIT_SEARCHONINTERNET (needs a hook capturing opened URLs instead of launching the browser, see report).
    Expect: the opened URLs start with https://duckduckgo.com/, https://www.google.com/, https://www.bing.com/, https://search.yahoo.com/ and equal "https://example.org/find?w=word&x=1"; pref searchEngine 0..4 persists.
    """
    app = papp
    app.new("a word here")
    app.select(1, 3, 1, 7)
    expected = [("DuckDuckGo", "https://duckduckgo.com/"), ("Google", "https://www.google.com/"),
                ("Bing", "https://www.bing.com/"), ("Yahoo!", "https://search.yahoo.com/")]
    for i, (engine, prefix) in enumerate(expected):
        set_options(app, "Search Engine", popups={"Search Engine (for command \"Search on Internet\")": engine})
        assert stored(app).get("searchEngine") == i
        app.modal_log()
        app.run("IDM_EDIT_SEARCHONINTERNET")
        urls = [e.get("target") or e.get("url") for e in app.modal_log() if e["kind"] == "open_url"]
        assert len(urls) == 1 and urls[0].startswith(prefix) and "word" in urls[0], (engine, urls)
    set_options(app, "Search Engine", popups={"Search Engine (for command \"Search on Internet\")": "Set your search engine here:"},
                fields={"Set your search engine here:": "https://example.org/find?w=$(CURRENT_WORD)&x=1"})
    assert stored(app).get("searchEngine") == 4
    app.modal_log()
    app.run("IDM_EDIT_SEARCHONINTERNET")
    urls = [e.get("target") or e.get("url") for e in app.modal_log() if e["kind"] == "open_url"]
    assert urls == ["https://example.org/find?w=word&x=1"], urls


@pytest.mark.case("SETTINGS-092")
def test_settings_092_the_style_configurator_opens_on_the_current_language(papp):
    """SETTINGS-092: The Style Configurator opens on the current language

    Covers: IDM_LANGSTYLE_CONFIG_DLG
    Channel: menu, ui
    Steps: Open a C++ document; run IDM_LANGSTYLE_CONFIG_DLG; read the window's theme pop-up, Language table, Style table and the "Default ext.:" label; run it on a Normal text document after closing.
    Expect: the window "Style Configurator" is shown; the Language table's first row is "Global Styles" and the selected row is "C++"; the Style table lists PREPROCESSOR, DEFAULT, INSTRUCTION WORD, … COMMENT LINE; "Default ext.:" shows "cpp cxx cc h hh hpp hxx ino"; for Normal text the selected row is Global Styles.
    """
    app = papp
    light(app)
    app.new("int x;\n", language="cpp")
    U.open_styles(app)
    lang, style = U.styles_tables(app)
    names = [r[0] for r in lang["cells"]]
    assert names[0] == "Global Styles"
    assert lang["selected"] == [names.index("C++")]
    styles = [r[0] for r in style["cells"]]
    assert styles[:3] == ["PREPROCESSOR", "DEFAULT", "INSTRUCTION WORD"] and "COMMENT LINE" in styles, styles
    assert U.styles_after(app, "Default ext.:", "NSTextField")["value"] == "cpp cxx cc h hh hpp hxx ino"
    app.click(U.STYLES, "Cancel")
    app.wait(lambda: not window_visible(app, U.STYLES))
    app.new("plain\n")
    U.open_styles(app)
    assert U.styles_tables(app)[0]["selected"] == [0]
    app.click(U.STYLES, "Cancel")


@pytest.mark.case("SETTINGS-093")
def test_settings_093_choosing_a_theme_previews_it_cancel_reverts_save_close_keeps(papp):
    """SETTINGS-093: Choosing a theme previews it, Cancel reverts, Save & Close keeps it

    Covers: IDM_LANGSTYLE_CONFIG_DLG
    Channel: ui, mcp, launch
    Steps: With Appearance "Light mode", open the configurator, select "Monokai" in "Select theme:"; read STYLE_DEFAULT back; click Cancel; open again, select "Monokai", click "Save & Close"; restart.
    Expect: after choosing, back is 0x222827 at once; Cancel restores 0xFFFFFF and pref lightThemeName stays "Default"; after Save & Close and restart the editor is Monokai and lightThemeName is "Monokai"; the Dark Mode page's "Light theme" shows Monokai.
    """
    app = papp
    light(app)
    app.new("int x;\n", language="cpp")
    back = lambda: app.sci(SCI_STYLEGETBACK, STYLE_DEFAULT)
    assert back() == 0xFFFFFF
    theme = lambda: U.styles_control(app, "NSPopUpButton", 0)
    U.open_styles(app)
    app.act(U.STYLES, "select", "Monokai", path=theme()["path"])
    app.wait(lambda: back() == 0x222827, message="Monokai previewed")
    app.click(U.STYLES, "Cancel")
    app.wait(lambda: back() == 0xFFFFFF, message="Cancel back to Default")
    assert app.pref("lightThemeName") == "Default"
    U.open_styles(app)
    app.act(U.STYLES, "select", "Monokai", path=theme()["path"])
    app.click(U.STYLES, "Save & Close")
    app.wait(lambda: not window_visible(app, U.STYLES))
    assert app.pref("lightThemeName") == "Monokai"
    app.restart()
    app.new("int x;\n", language="cpp")
    app.wait(lambda: back() == 0x222827, message="Monokai after a restart")
    page(app, "Dark Mode")
    assert any(c["class"] == "NSPopUpButton" and c.get("value") == "Monokai" for c in controls(app))
    close_prefs(app)


@pytest.mark.case("SETTINGS-094")
def test_settings_094_font_size_bold_italic_and_underline_of_a_style_apply_at_once(fresh):
    """SETTINGS-094: Font, size, bold, italic and underline of a style apply at once and are saved

    Covers: IDM_LANGSTYLE_CONFIG_DLG
    Channel: ui, mcp, files, launch
    Steps: C++ document "// note\\nint x;"; open the configurator, select Style "COMMENT LINE", select "Courier New" in "Font name:", "20" in "Size:", tick Bold, Italic, Underline; read style 2 (SCE_C_COMMENTLINE); click "Save & Close"; restart.
    Expect: SCI_STYLEGETFONT(2) "Courier New", SCI_STYLEGETSIZE(2) 20, bold, italic, underline all 1 before saving; home/…/NotepadMac/stylers.xml exists with COMMENT LINE fontName="Courier New" fontSize="20" fontStyle="7"; after restart style 2 still has them; other styles are unchanged.
    """
    app = fresh
    light(app)
    app.new("// note\nint x;\n", language="cpp")
    U.open_styles(app)
    U.styles_select(app, "C++", "COMMENT LINE")
    font = U.styles_after(app, "Font name:", "NSPopUpButton")
    app.act(U.STYLES, "select", "Courier New", path=font["path"])
    size = U.styles_after(app, "Size:", "NSPopUpButton")
    app.act(U.STYLES, "select", "20", path=size["path"])
    for box in ("Bold", "Italic", "Underline"):
        app.act(U.STYLES, "set_state", 1, title=box)
    def comment_line():
        return (app.sci(SCI_STYLEGETFONT, 2, returns="string"), app.sci(SCI_STYLEGETSIZE, 2),
                app.sci(SCI_STYLEGETBOLD, 2), app.sci(SCI_STYLEGETITALIC, 2), app.sci(SCI_STYLEGETUNDERLINE, 2))
    word_font = app.sci(SCI_STYLEGETFONT, 5, returns="string")
    app.wait(lambda: comment_line() == ("Courier New", 20, 1, 1, 1), message="the style applied at once")
    app.click(U.STYLES, "Save & Close")
    xml = (support(app) / "stylers.xml").read_text()
    m = re.search(r'<WordsStyle name="COMMENT LINE"[^>]*>', xml[xml.index('<LexerType name="cpp"'):])
    assert m and 'fontName="Courier New"' in m.group(0) and 'fontSize="20"' in m.group(0) and 'fontStyle="7"' in m.group(0), m
    app.restart()
    app.new("// note\nint x;\n", language="cpp")
    app.wait(lambda: comment_line() == ("Courier New", 20, 1, 1, 1), message="the style after a restart")
    assert app.sci(SCI_STYLEGETFONT, 5, returns="string") == word_font


@pytest.mark.case("SETTINGS-095")
def test_settings_095_changing_a_style_s_colours(fresh):
    """SETTINGS-095: Changing a style's colours

    Covers: IDM_LANGSTYLE_CONFIG_DLG
    Channel: ui, mcp, files
    Steps: C++ document; configurator, Style "COMMENT LINE"; set the "Foreground color" well to FF0000 and "Background color" to 00FF00 (needs e2e_act set_value on NSColorWell, see report); Save && Close.
    Expect: SCI_STYLEGETFORE(2) 0x0000FF and SCI_STYLEGETBACK(2) 0x00FF00 at once; the saved stylers.xml has fgColor="FF0000" bgColor="00FF00" for COMMENT LINE.
    """
    app = fresh
    light(app)
    app.new("// note\nint x;\n", language="cpp")
    U.open_styles(app)
    U.styles_select(app, "C++", "COMMENT LINE")
    app.act(U.STYLES, "set_value", "#FF0000", path=U.styles_control(app, "NSColorWell", 0)["path"])
    app.act(U.STYLES, "set_value", "#00FF00", path=U.styles_control(app, "NSColorWell", 1)["path"])
    app.wait(lambda: (app.sci(SCI_STYLEGETFORE, 2), app.sci(SCI_STYLEGETBACK, 2)) == (0x0000FF, 0x00FF00),
             message="the colours applied at once")
    app.click(U.STYLES, "Save & Close")
    xml = (support(app) / "stylers.xml").read_text()
    m = re.search(r'<WordsStyle name="COMMENT LINE"[^>]*>', xml[xml.index('<LexerType name="cpp"'):])
    assert m and 'fgColor="FF0000"' in m.group(0) and 'bgColor="00FF00"' in m.group(0), m


@pytest.mark.case("SETTINGS-096")
def test_settings_096_global_override_switches(papp):
    """SETTINGS-096: Global override switches

    Covers: IDM_LANGSTYLE_CONFIG_DLG
    Channel: ui, mcp
    Steps: C++ document; configurator, Language "Global Styles", Style "Global override"; tick "Enable global foreground colour" and "Enable global bold font style"; read SCI_STYLEGETFORE of SCE_C_WORD and STYLE_DEFAULT; click Cancel.
    Expect: both styles take Global override's foreground and bold follows its font style while ticked; after Cancel the keyword colour is back to the theme's (0xFF0000 for 0000FF) and pref globalOverride has no fg.
    """
    app = papp
    light(app)
    app.new("int x;\n", language="cpp")
    U.open_styles(app)
    U.styles_select(app, "Global Styles", "Global override")
    fg = U.styles_control(app, "NSColorWell", 0)["value"].lstrip("#")
    override_fg = int(fg[4:6] + fg[2:4] + fg[0:2], 16)        # RRGGBB as Scintilla's BGR
    override_bold = U.styles_controls(app) and next(c["state"] for c in U.styles_controls(app) if c.get("title") == "Bold")
    word_fore = app.sci(SCI_STYLEGETFORE, 5)
    for box in ("Enable global foreground colour", "Enable global bold font style"):
        app.act(U.STYLES, "set_state", 1, title=box)
    app.wait(lambda: app.sci(SCI_STYLEGETFORE, 5) == override_fg and app.sci(SCI_STYLEGETFORE, STYLE_DEFAULT) == override_fg,
             message="the global foreground on every style")
    assert app.sci(SCI_STYLEGETBOLD, 5) == override_bold and app.sci(SCI_STYLEGETBOLD, STYLE_DEFAULT) == override_bold
    app.click(U.STYLES, "Cancel")
    app.wait(lambda: app.sci(SCI_STYLEGETFORE, 5) == word_fore == 0xFF0000, message="back to the theme's keyword colour")
    assert not (app.pref("globalOverride") or {}).get("fg")


@pytest.mark.case("SETTINGS-097")
def test_settings_097_user_extensions_and_user_keywords(fresh, tmp):
    """SETTINGS-097: User extensions and user keywords

    Covers: IDM_LANGSTYLE_CONFIG_DLG
    Channel: ui, mcp, files
    Steps: Configurator, Language "C++", Style "INSTRUCTION WORD"; set "User ext.:" to " nppx  NPPY " (set_value, end_editing); set the "User-defined keywords" text view to "nppmacword" (set_text); Save && Close; open `tmp/a.nppx` containing "nppmacword x;".
    Expect: the file opens as C++; SCI_GETSTYLEAT(0) is SCE_C_WORD (5); stylers.xml holds ext="nppx nppy" (lower-cased) and the keyword; b.NPPY also opens as C++.
    """
    app = fresh
    light(app)
    U.open_styles(app)
    U.styles_select(app, "C++", "INSTRUCTION WORD")
    ext = next(c for c in U.styles_controls(app) if c.get("placeholder") == "ext1 ext2")
    app.act(U.STYLES, "set_value", " nppx  NPPY ", path=ext["path"])
    kw = U.styles_after(app, "User-defined keywords", "NSTextView")
    app.act(U.STYLES, "set_text", "nppmacword", path=kw["path"])
    app.click(U.STYLES, "Save & Close")
    a = tmp / "a.nppx"
    a.write_text("nppmacword x;\n")
    app.open(a)
    assert app.doc()["language"] == "cpp"
    app.wait(lambda: app.sci(SCI_GETSTYLEAT, 0) == 5, message="the user keyword styled as INSTRUCTION WORD")
    b = tmp / "b.NPPY"
    b.write_text("int y;\n")
    app.open(b)
    assert app.doc()["language"] == "cpp"
    xml = (support(app) / "stylers.xml").read_text()
    lexer = re.search(r'<LexerType name="cpp"[^>]*ext="([^"]*)"', xml)
    # Kept as typed, as upstream's WordStyleDlg does (setLexerUserExt with the field's text);
    # the plan's lower-casing is not upstream's.
    assert lexer and lexer.group(1).split() == ["nppx", "NPPY"], lexer
    assert "nppmacword" in xml[xml.index('<LexerType name="cpp"'):]


@pytest.mark.case("SETTINGS-098")
def test_settings_098_transparency_and_closing_the_configurator_s_window_cancels(papp):
    """SETTINGS-098: Transparency, and closing the configurator's window cancels

    Covers: IDM_LANGSTYLE_CONFIG_DLG
    Channel: ui
    Steps: Tick "Transparency", set the slider to 0.5 (set_value), read the window's alphaValue (`e2e_invoke get window:Style Configurator alphaValue`); untick; select "Monokai" as theme, then close the window with `close_window`.
    Expect: 0.5 while ticked, 1.0 unticked; closing the window acts as Cancel: STYLE_DEFAULT back returns to 0xFFFFFF and lightThemeName is unchanged.
    """
    app = papp
    light(app)
    app.new("int x;\n", language="cpp")
    U.open_styles(app)
    alpha = lambda: float(app.get("window:Style Configurator", "alphaValue"))
    app.act(U.STYLES, "set_state", 1, title="Transparency")
    app.act(U.STYLES, "set_value", 0.5, path=U.styles_control(app, "NSSlider")["path"])
    app.wait(lambda: abs(alpha() - 0.5) < 0.01, message="half transparent")
    app.act(U.STYLES, "set_state", 0, title="Transparency")
    app.wait(lambda: alpha() == 1.0, message="opaque again")
    app.act(U.STYLES, "select", "Monokai", path=U.styles_control(app, "NSPopUpButton", 0)["path"])
    app.wait(lambda: app.sci(SCI_STYLEGETBACK, STYLE_DEFAULT) == 0x222827, message="Monokai previewed")
    app.close_window(U.STYLES)
    app.wait(lambda: not window_visible(app, U.STYLES), message="the configurator closed")
    app.wait(lambda: app.sci(SCI_STYLEGETBACK, STYLE_DEFAULT) == 0xFFFFFF, message="closing cancels")
    assert app.pref("lightThemeName") == "Default"


@pytest.mark.case("SETTINGS-099")
def test_settings_099_the_mapper_lists_every_command_with_its_key_and_place(papp):
    """SETTINGS-099: The mapper lists every command with its key and place

    Covers: IDM_SETTING_SHORTCUT_MAPPER
    Channel: menu, ui
    Steps: Run IDM_SETTING_SHORTCUT_MAPPER; read the segmented control, the table and its columns; select each segment.
    Expect: segments Main menu, Macros, Run commands, Plugin commands, Scintilla commands; Main menu has more than 400 rows with columns Name, Shortcut, Where, e.g. ["New", "⌘N", "File"] and ["Find Next", "⌘G", "Search"]; Scintilla commands has more than 80 rows; on Plugin commands the line under the table explains that plugins' commands cannot be assigned, and Modify… / Clear there show no alert and change nothing; Delete is enabled only on Macros and Run commands.
    """
    app = papp
    U.open_mapper(app)
    seg = next(c for c in app.ui(U.MAPPER)["controls"] if c["class"] == "NSSegmentedControl")
    assert seg["items"] == ["Main menu", "Macros", "Run commands", "Plugin commands", "Scintilla commands"]
    t = U.mapper_table(app)
    assert t["columns"] == ["Name", "Shortcut", "Where"] and t["rows"] > 400
    assert ["New", "⌘N", "File"] in t["cells"] and ["Find Next", "⌘G", "Search"] in t["cells"]
    assert not U.mapper_button_enabled(app, "Delete")
    for label, deletable in [("Macros", True), ("Run commands", True), ("Plugin commands", False), ("Scintilla commands", False)]:
        U.mapper_segment(app, label)
        assert U.mapper_button_enabled(app, "Delete") == deletable, label
    U.mapper_segment(app, "Scintilla commands")
    assert U.mapper_table(app)["rows"] > 80
    U.mapper_segment(app, "Plugin commands")
    texts = [c.get("value") or "" for c in app.ui(U.MAPPER)["controls"] if c["class"] == "NSTextField"]
    assert any("plugin" in t.lower() and ("assign" in t.lower() or "not loaded" in t.lower()) for t in texts), texts
    before = U.mapper_rows(app)
    app.modal_log()
    app.click(U.MAPPER, "Modify…")
    app.click(U.MAPPER, "Clear")
    assert not [e for e in app.modal_log() if e["kind"] == "alert"]
    assert U.mapper_rows(app) == before
    U.close_mapper(app)


@pytest.mark.case("SETTINGS-100")
def test_settings_100_the_filter_narrows_by_name_place_or_key(papp):
    """SETTINGS-100: The filter narrows by name, place or key

    Covers: IDM_SETTING_SHORTCUT_MAPPER
    Channel: ui
    Steps: Set the search field (placeholder "Filter") to "Find Next", then "⌘G", then "search", then empty.
    Expect: "Find Next" gives the rows Find Next and Select and Find Next; "⌘G" includes Find Next; "search" gives the Search menu's commands; empty gives the full list back.
    """
    app = papp
    U.open_mapper(app)
    full = U.mapper_table(app)["rows"]
    U.mapper_filter(app, "Find Next")
    assert [r[0] for r in U.mapper_rows(app)] == ["Find Next", "Select and Find Next"]
    U.mapper_filter(app, "⌘G")
    assert "Find Next" in [r[0] for r in U.mapper_rows(app)]
    U.mapper_filter(app, "search")
    rows = U.mapper_rows(app)
    assert rows and all("search" in (r[0] + " " + r[2]).lower() for r in rows), rows
    assert {"Find…", "Find Next", "Replace…"} <= {r[0] for r in rows if r[2] == "Search"}
    U.mapper_filter(app, "")
    assert U.mapper_table(app)["rows"] == full
    U.close_mapper(app)


@pytest.mark.case("SETTINGS-101")
def test_settings_101_remove_a_shortcut_menu_keys_and_shortcuts_xml(fresh):
    """SETTINGS-101: Remove a shortcut: menu, keys and shortcuts.xml

    Covers: IDM_SETTING_SHORTCUT_MAPPER, IDM_SEARCH_FINDNEXT
    Channel: ui, modal, keys, files, launch
    Steps: Filter "Find Next", select its row, queue alert answer "Remove", click "Modify…"; press cmd+g in a document with a search term set; restart.
    Expect: the alert 'Shortcut for "Find Next"' with buttons OK, Cancel, Remove is logged; the row's shortcut is empty; IDM_SEARCH_FINDNEXT has no key; cmd+g does not move the selection; shortcuts.xml in the home has <Shortcut id="43002" Ctrl="no" Alt="no" Shift="no" Key="0"/>; after restart the key is still gone.
    """
    app = fresh
    U.open_mapper(app)
    U.mapper_select(app, "Find Next", "Search")
    app.modal_log()
    app.answers(alerts=["Remove"])
    app.click(U.MAPPER, "Modify…")
    log = [e for e in app.modal_log() if e["kind"] == "alert"]
    assert len(log) == 1 and log[0]["message"] == 'Shortcut for "Find Next"' and log[0]["buttons"] == ["OK", "Cancel", "Remove"], log
    assert U.mapper_row(app, "Find Next", "Search")[1] == ""
    U.close_mapper(app)
    assert not app.menu_item("IDM_SEARCH_FINDNEXT").get("key")
    app.new("one one one\n")
    app.select(1, 1, 1, 4)
    app.run("IDM_SEARCH_SETANDFINDNEXT")
    sel = app.selection()
    app.keys("cmd+g")
    app.idle(0.2)
    assert app.selection() == sel, "cmd+g no longer finds the next one"
    xml = U.shortcuts_xml(app).read_text()
    assert re.search(r'<Shortcut id="43002" Ctrl="no" Alt="no" Shift="no" Key="0"\s*/>', xml), xml
    app.restart()
    assert not app.menu_item("IDM_SEARCH_FINDNEXT").get("key")


@pytest.mark.case("SETTINGS-102")
def test_settings_102_modify_cancelled_or_confirmed_unchanged_leaves_everything_as(papp):
    """SETTINGS-102: Modify… cancelled or confirmed unchanged leaves everything as it was

    Covers: IDM_SETTING_SHORTCUT_MAPPER
    Channel: ui, modal, files
    Steps: Select "Find Next"; Modify… answered "Cancel"; then Modify… answered "OK" without a key.
    Expect: the row still shows ⌘G and IDM_SEARCH_FINDNEXT's key is "cmd+g" both times; no conflict alert is logged.
    """
    app = papp
    U.open_mapper(app)
    U.mapper_select(app, "Find Next", "Search")
    app.modal_log()
    for answer in ("Cancel", "OK"):
        app.answers(alerts=[answer])
        app.click(U.MAPPER, "Modify…")
        assert U.mapper_row(app, "Find Next", "Search")[1] == "⌘G"
        assert app.menu_item("IDM_SEARCH_FINDNEXT").get("key") == "cmd+g"
    alerts = [e for e in app.modal_log() if e["kind"] == "alert"]
    assert [e["message"] for e in alerts] == ['Shortcut for "Find Next"'] * 2, alerts
    U.close_mapper(app)


@pytest.mark.case("SETTINGS-103")
def test_settings_103_clear_removes_the_key_of_the_selected_command(fresh):
    """SETTINGS-103: Clear removes the key of the selected command

    Covers: IDM_SETTING_SHORTCUT_MAPPER, IDM_FILE_NEW
    Channel: ui, keys, mcp
    Steps: Select the row "New"; click "Clear"; press cmd+n.
    Expect: the row's shortcut is empty, IDM_FILE_NEW has no key, cmd+n opens no new document (list_documents count unchanged); shortcuts.xml has id="41001" Key="0".
    """
    app = fresh
    U.open_mapper(app)
    U.mapper_select(app, "New", "File")
    app.click(U.MAPPER, "Clear")
    assert U.mapper_row(app, "New", "File")[1] == ""
    U.close_mapper(app)
    assert not app.menu_item("IDM_FILE_NEW").get("key")
    count = len(app.docs())
    app.keys("cmd+n")
    app.idle(0.2)
    assert len(app.docs()) == count
    xml = U.shortcuts_xml(app).read_text()
    assert re.search(r'<Shortcut id="41001"[^>]*Key="0"', xml), xml


@pytest.mark.case("SETTINGS-104")
def test_settings_104_assign_a_new_key_through_the_key_capture(fresh):
    """SETTINGS-104: Assign a new key through the key capture

    Covers: IDM_SETTING_SHORTCUT_MAPPER, IDM_EDIT_UPPERCASE
    Channel: ui, modal, keys, files
    Steps: Select "UPPERCASE"; Modify… with an alert answer that presses cmd+alt+ctrl+u before answering OK (needs a hook: keys delivered to a queued alert, see report); select "abc" and press cmd+alt+ctrl+u.
    Expect: the row shows ⌃⌥⌘U; IDM_EDIT_UPPERCASE's key is "ctrl+alt+cmd+u"; the text becomes "ABC"; shortcuts.xml has id="42016" Ctrl="yes" Alt="yes" Shift="no" Key="85" MacCtrl="yes".
    """
    app = fresh
    U.open_mapper(app)
    U.mapper_select(app, "UPPERCASE")
    U.mapper_capture(app, "ctrl+alt+cmd+u", "⌃⌥⌘U")
    assert U.mapper_row(app, "UPPERCASE")[1] == "⌃⌥⌘U"
    U.close_mapper(app)
    assert set(app.menu_item("IDM_EDIT_UPPERCASE").get("key", "").split("+")) == {"ctrl", "alt", "cmd", "u"}
    app.new("abc")
    app.select(1, 1, 1, 4)
    app.keys("ctrl+alt+cmd+u")
    app.wait(lambda: app.text() == "ABC", message="the new key upper-cases")
    xml = U.shortcuts_xml(app).read_text()
    assert re.search(r'id="42016" Ctrl="yes" Alt="yes" Shift="no" Key="85" MacCtrl="yes"', xml), xml


@pytest.mark.case("SETTINGS-105")
def test_settings_105_conflicts_are_shown_and_resolved_take_share_cancel(fresh):
    """SETTINGS-105: Conflicts are shown and resolved: take, share, cancel

    Covers: IDM_SETTING_SHORTCUT_MAPPER
    Channel: files, launch, ui, modal
    Steps: Write shortcuts.xml into the home giving IDM_EDIT_UPPERCASE (42016) and IDM_EDIT_LOWERCASE (42017) the same key Ctrl+Alt+U; start; select the UPPERCASE row; Modify… answered "OK" then the clash alert answered "Cancel"; again answered "Share it"; again answered "Take it from them".
    Expect: selecting the row shows "⌥⌘U is also used by: lowercase" in the red line and both rows are drawn as conflicting; the clash alert says "⌥⌘U is already used by lowercase."; Cancel and Share leave both keys; Take leaves lowercase without a key and UPPERCASE with ⌥⌘U, written to shortcuts.xml.
    """
    app = fresh
    app.stop()
    U.shortcuts_xml(app).parent.mkdir(parents=True, exist_ok=True)
    U.shortcuts_xml(app).write_text('<?xml version="1.0" encoding="UTF-8" ?>\n<NotepadPlus><InternalCommands>'
        '<Shortcut id="42016" Ctrl="yes" Alt="yes" Shift="no" Key="85" />'
        '<Shortcut id="42017" Ctrl="yes" Alt="yes" Shift="no" Key="85" />'
        '</InternalCommands></NotepadPlus>\n')
    app.start(clean_home=False)
    U.open_mapper(app)
    U.mapper_select(app, "UPPERCASE")
    assert U.mapper_status(app) == "⌥⌘U is also used by: lowercase"
    def modify(clash_answer):
        app.modal_log()
        app.answers(alerts=["OK", clash_answer])
        U.mapper_select(app, "UPPERCASE")
        app.click(U.MAPPER, "Modify…")
        return [e["message"] for e in app.modal_log() if e["kind"] == "alert"]
    for answer in ("Cancel", "Share it"):
        assert modify(answer) == ['Shortcut for "UPPERCASE"', "⌥⌘U is already used by lowercase."]
        U.mapper_filter(app, "case")
        assert U.mapper_row(app, "UPPERCASE")[1] == "⌥⌘U" and U.mapper_row(app, "lowercase")[1] == "⌥⌘U", answer
    modify("Take it from them")
    U.mapper_filter(app, "case")
    assert U.mapper_row(app, "UPPERCASE")[1] == "⌥⌘U" and U.mapper_row(app, "lowercase")[1] == ""
    U.close_mapper(app)
    assert not app.menu_item("IDM_EDIT_LOWERCASE").get("key")
    xml = U.shortcuts_xml(app).read_text()
    assert re.search(r'id="42016" Ctrl="yes" Alt="yes" Shift="no" Key="85"', xml)
    assert not re.search(r'id="42017" Ctrl="yes" Alt="yes" Shift="no" Key="85"', xml), xml


@pytest.mark.case("SETTINGS-106")
def test_settings_106_a_shortcuts_xml_from_windows_is_read_menu_macro_run_scintill(fresh):
    """SETTINGS-106: A shortcuts.xml from Windows is read: menu, macro, Run, Scintilla keys

    Covers: IDM_SETTING_SHORTCUT_MAPPER, IDM_FILE_NEW
    Channel: files, launch, keys, ui, menu
    Steps: Write the Windows-format shortcuts.xml of the in-app suite (41001 Ctrl+Alt+N, macro "From Windows" Alt+F6 typing "hi hi" then a Replace hi→yo, Run command "Say hello", ScintKey 2338 Ctrl+Shift+D with NextKey Alt+D, a PluginCommand of x.dll) into the home; start; press cmd+alt+n; in "one\\ntwo\\n" at line 1 press cmd+shift+d; in a new document press alt+f6.
    Expect: IDM_FILE_NEW's key is "alt+cmd+n" and it opens a document; cmd+shift+d deletes the line leaving "two\\n"; alt+f6 plays the macro giving "yo yo"; the Macros tab lists "From Windows" with ⌥F6, the Macro menu lists it, the Run commands tab and Run menu list "Say hello"; after any change is saved the PluginCommand element of x.dll is still in the file.
    """
    app = fresh
    app.stop()
    U.shortcuts_xml(app).parent.mkdir(parents=True, exist_ok=True)
    U.shortcuts_xml(app).write_text(WINDOWS_SHORTCUTS)
    app.start(clean_home=False)
    assert set(app.menu_item("IDM_FILE_NEW").get("key", "").split("+")) == {"alt", "cmd", "n"}
    count = len(app.docs())
    app.keys("cmd+alt+n")
    app.wait(lambda: len(app.docs()) == count + 1, message="the Windows key opens a document")
    app.new("one\ntwo\n")
    app.call("go_to", line=1, column=1)
    # The ScintKey's second key (NextKey Alt+D): e2e_keys cannot send Shift with a letter, so the
    # first key (Ctrl+Shift+D, shown ⇧⌘D) is checked in the mapper instead.
    app.keys("alt+d")
    app.wait(lambda: app.text() == "two\n", message="the Scintilla key deletes the line")
    U.open_mapper(app)
    U.mapper_segment(app, "Scintilla commands")
    U.mapper_filter(app, "SCI_LINEDELETE")
    assert U.mapper_rows(app)[0][1] == "⇧⌘D  ⌥D"
    U.mapper_segment(app, "Macros")
    U.mapper_filter(app, "")
    assert U.mapper_row(app, "From Windows")[1] == "⌥F6"
    U.mapper_segment(app, "Run commands")
    assert U.mapper_row(app, "Say hello") is not None
    U.mapper_segment(app, "Main menu")
    U.mapper_select(app, "Find Next", "Search")
    app.answers(alerts=["Remove"])
    app.click(U.MAPPER, "Modify…")
    U.close_mapper(app)
    assert 'moduleName="x.dll"' in U.shortcuts_xml(app).read_text()
    app.restart()
    # Read back from the preferences, the menus list them, and the macro's key plays it.
    assert "Say hello" in [i.get("title") for i in app.menu_tree("Run", 1)]
    assert "From Windows" in [i.get("title") for i in app.menu_tree("Macro", 1)]
    app.new("")
    app.keys("alt+f6")
    app.wait(lambda: app.text() == "yo yo", message="the macro played")
    # Last, the defect: on the launch that reads the file, the menus were built before it was read.
    app.stop()
    U.shortcuts_xml(app).write_text(WINDOWS_SHORTCUTS.replace("From Windows", "From Windows 2").replace("Say hello", "Say hi"))
    app.start(clean_home=False)
    macro_titles = [i.get("title") for i in app.menu_tree("Macro", 1)]
    run_titles = [i.get("title") for i in app.menu_tree("Run", 1)]
    assert "From Windows 2" in macro_titles and "Say hi" in run_titles, (macro_titles, run_titles)


@pytest.mark.case("SETTINGS-107")
def test_settings_107_scintilla_command_keys_can_be_removed_and_given(fresh):
    """SETTINGS-107: Scintilla command keys can be removed and given

    Covers: IDM_SETTING_SHORTCUT_MAPPER
    Channel: ui, modal, keys, mcp
    Steps: On Scintilla commands filter "SCI_LINEDELETE" (or its name), select it, Modify… answered "Remove"; press its old key in "one\\ntwo\\n".
    Expect: the row has no key and the key no longer deletes the line; shortcuts.xml has a ScintKey ScintID="2338" entry with Key="0".
    """
    app = fresh
    def rows():
        U.open_mapper(app)
        U.mapper_segment(app, "Scintilla commands")
        U.mapper_filter(app, "SCI_LINEDELETE")
        r = U.mapper_rows(app)
        assert len(r) == 1, r
        app.act(U.MAPPER, "select", 0, path=U.mapper_table(app)["path"])
        return r
    def deletes_line():
        U.close_mapper(app)
        app.new("one\ntwo\n")
        app.call("go_to", line=1, column=1)
        app.keys("ctrl+alt+cmd+k")
        app.idle(0.2)
        return app.text() == "two\n"
    assert rows()[0][1]                     # its own key to begin with
    # Given: a key without Shift (e2e_keys cannot send Shift with a letter, which the default ⇧⌘L has).
    U.mapper_capture(app, "ctrl+alt+cmd+k", "⌃⌥⌘K")
    assert rows()[0][1].startswith("⌃⌥⌘K")
    assert deletes_line()
    # Removed.
    rows()
    app.answers(alerts=["Remove"])
    app.click(U.MAPPER, "Modify…")
    assert rows()[0][1] == ""
    assert not deletes_line(), "the removed key no longer deletes the line"
    xml = U.shortcuts_xml(app).read_text()
    assert re.search(r'<ScintKey ScintID="2338"[^>]*Key="0"', xml), xml

@pytest.mark.case("SETTINGS-108")
def test_settings_108_deleting_a_macro_and_a_run_command_from_the_mapper(fresh):
    """SETTINGS-108: Deleting a macro and a Run command from the mapper

    Covers: IDM_SETTING_SHORTCUT_MAPPER, IDM_MACRO_SAVECURRENTMACRO
    Channel: ui, menu, files
    Steps: Record a macro typing "x" and save it as "Mine" (IDM_MACRO_SAVECURRENTMACRO with a prompt answer {"button":1,"field":"Mine"}); save a Run command "Echo" through the Run dialog or shortcuts.xml; in the mapper select Macros > "Mine", click Delete; Run commands > "Echo", click Delete.
    Expect: both rows disappear; the Macro menu no longer lists "Mine" and the Run menu no longer lists "Echo"; shortcuts.xml has neither; on the Main menu segment Delete is disabled and clicking it changes nothing.
    """
    app = fresh
    app.stop()
    U.shortcuts_xml(app).parent.mkdir(parents=True, exist_ok=True)
    U.shortcuts_xml(app).write_text('<?xml version="1.0" encoding="UTF-8" ?>\n<NotepadPlus><UserDefinedCommands>'
        '<Command name="Echo" Ctrl="no" Alt="no" Shift="no" Key="0">echo hi</Command></UserDefinedCommands></NotepadPlus>\n')
    app.start(clean_home=False)
    app.restart()          # the launch that reads shortcuts.xml does not list its Run commands yet (SETTINGS-106)
    app.new("")
    app.run("IDM_MACRO_STARTRECORDINGMACRO")
    app.type("x")
    app.run("IDM_MACRO_STOPRECORDINGMACRO")
    app.answers(alerts=[{"button": 1, "field": "Mine"}])
    app.run("IDM_MACRO_SAVECURRENTMACRO")
    def menu_titles(top):
        return [i.get("title") for i in app.menu_tree(top, 1)]
    assert "Mine" in menu_titles("Macro") and "Echo" in menu_titles("Run")
    U.open_mapper(app)
    U.mapper_segment(app, "Macros")
    U.mapper_select(app, "Mine")
    app.click(U.MAPPER, "Delete")
    assert U.mapper_row(app, "Mine") is None
    U.mapper_segment(app, "Run commands")
    U.mapper_select(app, "Echo")
    app.click(U.MAPPER, "Delete")
    assert U.mapper_row(app, "Echo") is None
    U.mapper_segment(app, "Main menu")
    U.mapper_filter(app, "")
    assert not U.mapper_button_enabled(app, "Delete")
    U.close_mapper(app)
    assert "Mine" not in menu_titles("Macro") and "Echo" not in menu_titles("Run")
    xml = U.shortcuts_xml(app).read_text()
    assert 'name="Mine"' not in xml and 'name="Echo"' not in xml


@pytest.mark.case("SETTINGS-109")
def test_settings_109_edit_popup_contextmenu_opens_contextmenu_xml_with_upstream_s(fresh):
    """SETTINGS-109: Edit Popup ContextMenu opens contextMenu.xml with upstream's default

    Covers: IDM_SETTING_EDITCONTEXTMENU
    Channel: menu, modal, files, mcp
    Steps: With `fresh_app`, queue alert answer 1, run IDM_SETTING_EDITCONTEXTMENU; read the modal log, the current document's path and text; read the editor context menu (`e2e_menu context=editor`).
    Expect: an alert "Editing contextMenu" is logged; the document opened is home/Library/Application Support/NotepadMac/contextMenu.xml, created with a <ScintillaContextMenu> root; the context menu has at least 12 items, starts with "Cut", and "Style all occurrences of token" has a submenu of 5 items.
    """
    app = fresh
    f = support(app) / "contextMenu.xml"
    app.modal_log()
    app.answers(alerts=[1])
    app.run("IDM_SETTING_EDITCONTEXTMENU")
    alerts = [e for e in app.modal_log() if e["kind"] == "alert"]
    assert [e["message"] for e in alerts] == ["Editing contextMenu"], alerts
    app.wait(lambda: app.same_path(app.doc().get("path") or "/", f), message="contextMenu.xml opened")
    assert "<ScintillaContextMenu>" in app.text() and f.exists()
    tree = app.call("e2e_menu", context="editor")["tree"]
    assert len([i for i in tree if i.get("title")]) >= 12
    assert tree[0].get("title") == "Cut"
    token = next(i for i in tree if i.get("title") == "Style all occurrences of token")
    assert len(token.get("items", [])) == 5


@pytest.mark.case("SETTINGS-110")
def test_settings_110_an_edited_contextmenu_xml_is_the_right_click_menu_at_the_nex(fresh):
    """SETTINGS-110: An edited contextMenu.xml is the right-click menu at the next click

    Covers: IDM_SETTING_EDITCONTEXTMENU, IDM_EDIT_UPPERCASE, IDM_EDIT_PASTE
    Channel: menu, files, mcp, clipboard
    Steps: Open contextMenu.xml through the command, replace its text with the in-app suite's sample (Copy by name, Paste renamed "Put it here", separators, a missing command, a "Case" folder with id 42016 and lowercase, an empty folder, a plugin folder) and save; read the context menu; set the clipboard to "pasted" and invoke "Put it here" (`e2e_menu_invoke context=editor`); invoke Case > UPPERCASE on a selection.
    Expect: the menu is exactly Copy, Put it here, separator, Case, Plugin commands (duplicate separators collapsed, the missing command and the empty folder left out); Case has 2 items; "Put it here" pastes "pasted"; Case > UPPERCASE upper-cases the selection.
    """
    app = fresh
    app.answers(alerts=[1])
    app.run("IDM_SETTING_EDITCONTEXTMENU")
    f = support(app) / "contextMenu.xml"
    app.wait(lambda: app.same_path(app.doc().get("path") or "/", f), message="contextMenu.xml opened")
    app.call("edit_document", text=CONTEXT_MENU_SAMPLE)
    app.run("IDM_FILE_SAVE")
    app.wait(lambda: f.read_text() == CONTEXT_MENU_SAMPLE, message="the edited file saved")
    tree = app.call("e2e_menu", context="editor")["tree"]
    assert [i.get("title") for i in tree] == ["Copy", "Put it here", None, "Case", "Plugin commands"], tree
    case = next(i for i in tree if i.get("title") == "Case")
    assert [i.get("title") for i in case.get("items", [])] == ["UPPERCASE", "lowercase"]
    app.new("")
    app.clipboard("pasted")
    app.call("e2e_menu_invoke", context="editor", path="Put it here")
    assert app.text() == "pasted"
    app.select(1, 1, 1, 7)
    app.call("e2e_menu_invoke", context="editor", path="Case|UPPERCASE")
    assert app.text() == "PASTED"


@pytest.mark.case("SETTINGS-111")
def test_settings_111_without_a_scintillacontextmenu_the_preferences_list_is_used(papp):
    """SETTINGS-111: Without a ScintillaContextMenu the Preferences list is used

    Covers: IDM_SETTING_EDITCONTEXTMENU
    Channel: files, prefs, mcp
    Steps: Write "<NotepadPlus></NotepadPlus>" into contextMenu.xml; set pref contextMenuCommands to ["Copy", "Paste", "Toggle Line Comment"]; read the context menu; restore the file.
    Expect: the context menu is exactly Copy, Paste, Toggle Line Comment (named in English whatever the interface language).
    """
    app = papp
    f = support(app) / "contextMenu.xml"
    app.call("e2e_menu", context="editor")            # the default is written the first time
    was = f.read_bytes() if f.exists() else None
    try:
        f.write_text("<NotepadPlus></NotepadPlus>\n")
        app.set_prefs(contextMenuCommands=["Copy", "Paste", "Toggle Line Comment"])
        tree = app.call("e2e_menu", context="editor")["tree"]
        assert [i.get("title") for i in tree] == ["Copy", "Paste", "Toggle Line Comment"], tree
    finally:
        if was is None:
            f.unlink(missing_ok=True)
        else:
            f.write_bytes(was)


@pytest.mark.case("SETTINGS-112")
def test_settings_112_import_style_theme_s_copies_the_theme_and_makes_it_usable(fresh, tmp):
    """SETTINGS-112: Import style theme(s) copies the theme and makes it usable

    Covers: IDM_SETTING_IMPORTSTYLETHEMES
    Channel: menu, modal, files, ui, mcp
    Steps: Write `tmp/TestTheme.xml` (Default Style fg ABCDEF bg 222222, cpp DEFAULT 123456/654321); queue panel answer [that path] and alert answer 1; run IDM_SETTING_IMPORTSTYLETHEMES; open Dark Mode > Light theme; with Appearance "Light mode" choose "TestTheme", Apply; restart.
    Expect: the open panel titled "Import style theme(s)" is logged; an alert "Import style theme(s)" says "1 file(s) imported into themes"; home/…/NotepadMac/themes/TestTheme.xml exists; the Light theme pop-up and the Style Configurator's theme list include TestTheme; applied, STYLE_DEFAULT back is 0x222222 and fore 0xEFCDAB; still so after restart.
    """
    app = fresh
    theme = tmp / "TestTheme.xml"
    theme.write_text(TEST_THEME)
    app.modal_log()
    app.answers(panels=[[str(theme)]], alerts=[1])
    app.run("IDM_SETTING_IMPORTSTYLETHEMES")
    log = app.modal_log()
    assert any(e["kind"] == "open" and e.get("title") == "Import style theme(s)" for e in log), log
    told = [e for e in log if e["kind"] == "alert"]
    assert told and told[0]["message"] == "Import style theme(s)" and "1 file(s) imported into themes" in (told[0].get("informative") or ""), told
    assert (support(app) / "themes" / "TestTheme.xml").exists()
    page(app, "Dark Mode")
    light_popup = control_for(app, "Light theme", kinds=("NSPopUpButton",))
    assert "TestTheme" in light_popup["items"]
    close_prefs(app)
    U.open_styles(app)
    assert "TestTheme" in U.styles_control(app, "NSPopUpButton", 0)["items"]
    app.click(U.STYLES, "Cancel")
    set_options(app, "Dark Mode", popups={"Appearance": "Light mode", "Light theme": "TestTheme"})
    app.new("plain\n")
    colours = lambda: (app.sci(SCI_STYLEGETBACK, STYLE_DEFAULT), app.sci(SCI_STYLEGETFORE, STYLE_DEFAULT))
    app.wait(lambda: colours() == (0x222222, 0xEFCDAB), message="the imported theme applied")
    app.restart()
    app.new("plain\n")
    app.wait(lambda: colours() == (0x222222, 0xEFCDAB), message="the imported theme after a restart")


@pytest.mark.case("SETTINGS-113")
def test_settings_113_importing_several_themes_again_or_cancelling(fresh, tmp):
    """SETTINGS-113: Importing several themes, again, or cancelling

    Covers: IDM_SETTING_IMPORTSTYLETHEMES
    Channel: modal, files
    Steps: Import two theme files in one panel answer; import one of them again with changed contents; run the command with a cancelled panel (panel answer None).
    Expect: "2 file(s) imported into themes" then "1 file(s) …"; the second import replaces the file's contents; the cancelled run shows no alert and copies nothing.
    """
    app = fresh
    one, two = tmp / "One.xml", tmp / "Two.xml"
    one.write_text(TEST_THEME)
    two.write_text(TEST_THEME.replace("ABCDEF", "111111"))
    def imported(paths):
        app.modal_log()
        app.answers(panels=[paths], alerts=[1])
        app.run("IDM_SETTING_IMPORTSTYLETHEMES")
        return [e.get("informative") or "" for e in app.modal_log() if e["kind"] == "alert"]
    assert any("2 file(s) imported into themes" in t for t in imported([str(one), str(two)]))
    one.write_text(TEST_THEME.replace("ABCDEF", "999999"))
    assert any("1 file(s) imported into themes" in t for t in imported([str(one)]))
    assert "999999" in (support(app) / "themes" / "One.xml").read_text()
    before = sorted(p.name for p in (support(app) / "themes").iterdir())
    assert imported(None) == []
    assert sorted(p.name for p in (support(app) / "themes").iterdir()) == before


@pytest.mark.case("SETTINGS-114")
def test_settings_114_import_plugin_s_copies_a_plugin_that_loads_at_the_next_start(fresh, tmp):
    """SETTINGS-114: Import plugin(s) copies a plugin that loads at the next start

    Covers: IDM_SETTING_IMPORTPLUGIN
    Channel: menu, modal, files, launch
    Steps: Build ../npp/macos/plugin-sdk/sample/hellomac.c into `tmp/HelloMac.dylib` with `clang -dynamiclib`; queue the panel answer and alert answer 1; run IDM_SETTING_IMPORTPLUGIN; restart; run Plugins > HelloMac > Insert Greeting (e2e_menu_invoke) in an empty document.
    Expect: the alert "Import plugin(s)" says "1 file(s) imported into plugins"; home/…/NotepadMac/plugins/HelloMac.dylib exists; after restart the Plugins menu has a "HelloMac" submenu; the document reads "hello from the sample plugin"; a text file imported as junk.dylib is copied too, the app still starts, and app.log reports that plugin junk.dylib could not be loaded.
    """
    app = fresh
    sample = Path(__file__).resolve().parent.parent.parent / "npp" / "macos" / "plugin-sdk" / "sample" / "hellomac.c"
    dylib = tmp / "HelloMac.dylib"
    subprocess.run(["clang", "-dynamiclib", "-o", str(dylib), str(sample)], check=True)
    junk = tmp / "junk.dylib"
    junk.write_text("not a library\n")
    app.modal_log()
    app.answers(panels=[[str(dylib), str(junk)]], alerts=[1])
    app.run("IDM_SETTING_IMPORTPLUGIN")
    told = [e for e in app.modal_log() if e["kind"] == "alert"]
    assert told and told[0]["message"] == "Import plugin(s)" and "2 file(s) imported into plugins" in (told[0].get("informative") or ""), told
    plugins = support(app) / "plugins"
    assert (plugins / "HelloMac.dylib").exists() or (plugins / "HelloMac" / "HelloMac.dylib").exists()
    app.restart()
    assert "HelloMac" in [i.get("title") for i in app.menu_tree("Plugins", 1)]
    app.new("")
    greeting = next(i for i in app.menu_tree("Plugins", 2) if i.get("title") == "HelloMac")["items"][0]["title"]
    assert app.call("e2e_menu_invoke", path=f"Plugins|HelloMac|{greeting}")["ran"]
    app.wait(lambda: "hello" in app.text().lower(), message="the plugin's command wrote its greeting")
    assert "junk.dylib" in app.log_path.read_text(errors="replace")
