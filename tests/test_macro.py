"""MACRO: end-to-end tests (plan: plan/MACRO.md)."""
import json
import re

import pytest

from harness.sci import *  # noqa: F401,F403
from _util_edit import prefs, caret, ac_active, home_dir, invoke_menu, write

FIXED_ITEMS = ["Start Recording", "Stop Recording", "Playback", "Save Current Recorded Macro…",
               "Run a Macro Multiple Times…"]


def start(app):
    app.run("IDM_MACRO_STARTRECORDINGMACRO")


def stop(app):
    app.run("IDM_MACRO_STOPRECORDINGMACRO")


def play(app, expect_ran=True):
    # With nothing recorded Playback is disabled (Notepad_plus::checkMacroState) and does not run.
    r = app.run("IDM_MACRO_PLAYBACKRECORDEDMACRO", expect_ran=expect_ran)
    if not expect_ran:
        assert not r.get("ran"), r


def run_times(app, answer, expect_ran=True):
    app.answers(alerts=[answer])
    r = app.run("IDM_MACRO_RUNMULTIMACRODLG", expect_ran=expect_ran)
    if not expect_ran:
        assert not r.get("ran"), r
        app.answers(clear=True)   # the dialog never came up to take the answer


def save_as(app, name, expect_ran=True):
    app.answers(alerts=[{"button": 1, "field": name}])
    r = app.run("IDM_MACRO_SAVECURRENTMACRO", expect_ran=expect_ran)
    if not expect_ran:
        assert not r.get("ran"), r
        app.answers(clear=True)


def record_typing(app, text):
    app.new("")
    start(app)
    app.type(text)
    stop(app)


def macro_titles(app):
    return [i.get("title") for i in app.menu_tree("Macro", 1) if not i.get("separator")]


def saved_titles(app):
    return macro_titles(app)[len(FIXED_ITEMS):]


def record_cat2dog(app):
    """Records a Replace All of cat by dog made in the Replace dialog."""
    app.new("cat cat\n")
    start(app)
    app.run("IDM_SEARCH_REPLACE")
    fw = app.wait(lambda: next((w for w in app.windows() if not w["main_window"]), None))["number"]
    # (e2e_ui on the Find panel does not answer; the fields are found by class instead)
    app.act(fw, "set_value", "cat", **{"class": "NSComboBox", "index": 0})
    app.act(fw, "set_value", "dog", **{"class": "NSComboBox", "index": 1})
    app.click(fw, "Replace All")
    app.close_window(fw)
    stop(app)
    return app.text()


@pytest.mark.case("MACRO-001")
def test_macro_001_record_typed_text_and_play_it_back(app):
    """MACRO-001: Record typed text and play it back"""
    app.new("")
    start(app)
    app.type("ab")
    app.keys("return")
    stop(app)
    assert app.text() == "ab\n"
    app.new("x")
    app.keys("cmd+down")
    play(app)
    assert app.text() == "xab\n"


@pytest.mark.case("MACRO-002")
def test_macro_002_recorded_caret_movement_replays_relative_to_the_caret(app):
    """MACRO-002: Recorded caret movement replays relative to the caret"""
    app.new("abc\ndef\nghi\n")
    app.keys("cmd+up")
    start(app)
    app.keys("end")
    app.type(";")
    app.keys("down", "home")
    stop(app)
    assert app.text() == "abc;\ndef\nghi\n"
    assert app.selection()["caret"]["line"] == 2 and app.selection()["caret"]["column"] == 1
    play(app)
    play(app)
    assert app.text() == "abc;\ndef;\nghi;\n"


def record_semicolon_macro(app):
    app.new("abc\ndef\n")
    app.keys("cmd+up")
    start(app)
    app.keys("end")
    app.type(";")
    app.keys("down", "home")
    stop(app)


@pytest.mark.case("MACRO-003")
def test_macro_003_run_a_macro_multiple_times_runs_it_the_number_of_times_asked(app):
    """MACRO-003: Run a Macro Multiple Times runs it the number of times asked"""
    record_semicolon_macro(app)
    app.set_text("l1\nl2\nl3\nl4\nl5\n")
    app.keys("cmd+up")
    app.modal_log()
    run_times(app, {"button": 1, "field": "4"})
    log = app.modal_log()
    assert any(e.get("message") == "Run how many times?" for e in log)
    assert app.text() == "l1;\nl2;\nl3;\nl4;\nl5\n"


@pytest.mark.case("MACRO-004")
def test_macro_004_cancelling_or_giving_no_count_runs_nothing_extra(app):
    """MACRO-004: Cancelling or giving no count runs nothing extra"""
    record_typing(app, "x")
    app.new("")
    run_times(app, 2)
    assert app.text() == ""
    run_times(app, {"button": 1, "field": "0"})
    assert app.text() == "x"
    run_times(app, {"button": 1, "field": "abc"})
    assert app.text() == "xx"


@pytest.mark.case("MACRO-005")
def test_macro_005_a_playback_is_one_undo_step(app):
    """MACRO-005: A playback is one undo step"""
    record_typing(app, "hello ")
    app.new("!")
    app.keys("cmd+up")
    play(app)
    assert app.text() == "hello !"
    run_times(app, {"button": 1, "field": "3"})
    assert app.text() == "hello hello hello hello !"
    app.keys("cmd+z")
    assert app.text() == "hello !"
    app.keys("cmd+z")
    assert app.text() == "!"


@pytest.mark.case("MACRO-006")
def test_macro_006_playback_with_nothing_recorded_does_nothing(fresh_app):
    """MACRO-006: Playback with nothing recorded does nothing"""
    app = fresh_app
    app.new("q")
    play(app, expect_ran=False)
    run_times(app, {"button": 1, "field": "3"}, expect_ran=False)
    assert app.text() == "q"


@pytest.mark.case("MACRO-007")
def test_macro_007_the_macro_menu_follows_the_recording_state(fresh_app):
    """MACRO-007: The Macro menu follows the recording state"""
    app = fresh_app
    ids = ["IDM_MACRO_STARTRECORDINGMACRO", "IDM_MACRO_STOPRECORDINGMACRO", "IDM_MACRO_PLAYBACKRECORDEDMACRO"]

    def state():
        items = app.menu(*ids)
        return [items[i]["enabled"] for i in ids]

    app.new("")
    assert state() == [True, False, False]
    start(app)
    try:
        assert state() == [False, True, False]
        app.type("a")
    finally:
        stop(app)
    assert state() == [True, False, True]


@pytest.mark.case("MACRO-008")
def test_macro_008_recording_a_new_macro_replaces_the_previous_one(app):
    """MACRO-008: Recording a new macro replaces the previous one"""
    record_typing(app, "1")
    record_typing(app, "2")
    app.new("")
    play(app)
    assert app.text() == "2"


@pytest.mark.case("MACRO-009")
def test_macro_009_a_menu_command_is_recorded_by_its_id_and_replays_as_the_comm(app):
    """MACRO-009: A menu command is recorded by its id and replays as the command"""
    app.new("abc\n")
    start(app)
    app.keys("cmd+a")
    assert invoke_menu(app, "Edit|Convert Case to|UPPERCASE")["ran"]
    app.keys("down")
    app.type("x")
    stop(app)
    assert app.text() == "ABC\nx"
    app.new("def\nghi\n")
    app.keys("cmd+up")
    play(app)
    assert app.text() == "DEF\nGHI\nx"
    save_as(app, "UpperMacro9")
    xml = (home_dir(app) / "shortcuts.xml").read_text()
    block = xml[xml.index('name="UpperMacro9"'):]
    block = block[:block.index("</Macro>")]
    assert re.search(r'type="2"[^>]*wParam="42016"', block)


@pytest.mark.case("MACRO-010")
def test_macro_010_a_replace_all_from_the_replace_dialog_is_recorded_and_replay(app):
    """MACRO-010: A Replace All from the Replace dialog is recorded and replays"""
    assert record_cat2dog(app) == "dog dog\n"
    app.new("a cat\n")
    play(app)
    assert app.text() == "a dog\n"


@pytest.mark.case("MACRO-011")
def test_macro_011_a_find_next_from_the_dialog_is_recorded_and_replays_as_a_sea(app):
    """MACRO-011: A Find Next from the dialog is recorded and replays as a search"""
    app.new("x foo y foo z foo\n")
    app.keys("cmd+up")
    start(app)
    app.run("IDM_SEARCH_FIND")
    fw = app.wait(lambda: next((w for w in app.windows() if not w["main_window"]), None))["number"]
    app.act(fw, "set_value", "foo", **{"class": "NSComboBox", "index": 0})
    app.click(fw, "Find Next")
    app.close_window(fw)
    app.type("!")
    stop(app)
    assert app.text() == "x ! y foo z foo\n"
    play(app)
    play(app)
    assert app.text() == "x ! y ! z !\n"


@pytest.mark.case("MACRO-012")
def test_macro_012_auto_close_and_auto_completion_are_left_out_of_recording_and(app):
    """MACRO-012: Auto-close and auto-completion are left out of recording and playback"""
    with prefs(app, autoInsertParenthesis=True, autoCompleteOnInput=True):
        app.new("alphabet\n")
        app.keys("cmd+down")
        start(app)
        app.type("f(al")
        assert not ac_active(app)
        stop(app)
        assert app.text() == "alphabet\nf(al"
        app.new("")
        play(app)
        assert app.text() == "f(al"
        assert not ac_active(app)


@pytest.mark.case("MACRO-013")
def test_macro_013_save_current_recorded_macro_lists_it_in_the_macro_menu_and_w(app):
    """MACRO-013: Save Current Recorded Macro lists it in the Macro menu and writes it to disk"""
    record_typing(app, "ab")
    app.modal_log()
    save_as(app, "MyMac")
    log = app.modal_log()
    prompt = next(e for e in log if e.get("message") == "Save macro as")
    assert prompt.get("fields") == ["macro"]
    tree = app.menu_tree("Macro", 1)
    titles = [i.get("title") for i in tree if not i.get("separator")]
    assert "MyMac" in titles
    idx = next(k for k, i in enumerate(tree) if i.get("title") == "MyMac")
    assert any(i.get("separator") for i in tree[len(FIXED_ITEMS):idx])
    data = json.loads((home_dir(app) / "macros.json").read_text())
    assert "MyMac" in data
    xml = (home_dir(app) / "shortcuts.xml").read_text()
    assert '<Macro name="MyMac" Ctrl="no" Alt="no" Shift="no" Key="0">' in xml
    block = xml[xml.index('<Macro name="MyMac"'):]
    block = block[:block.index("</Macro>")]
    assert re.search(r'type="1" message="2170" wParam="0" lParam="0" sParam="a"', block)
    assert re.search(r'type="1" message="2170" wParam="0" lParam="0" sParam="b"', block)


@pytest.mark.case("MACRO-014")
def test_macro_014_a_saved_macro_runs_from_the_macro_menu(app):
    """MACRO-014: A saved macro runs from the Macro menu"""
    record_cat2dog(app)
    save_as(app, "Cat2Dog")
    record_typing(app, "z")
    app.new("my cat\n")
    assert invoke_menu(app, "Macro|Cat2Dog")["ran"]
    assert app.text() == "my dog\n"


@pytest.mark.case("MACRO-015")
def test_macro_015_saved_macros_survive_a_restart(app):
    """MACRO-015: Saved macros survive a restart"""
    record_cat2dog(app)
    save_as(app, "Cat2Dog")
    app.restart()
    try:
        assert "Cat2Dog" in saved_titles(app)
        app.new("my cat\n")
        assert invoke_menu(app, "Macro|Cat2Dog")["ran"]
        assert app.text() == "my dog\n"
        app.new("q")
        play(app, expect_ran=False)   # nothing recorded in this run of the app
        assert app.text() == "q"
    finally:
        app.stop()
        app.start()


@pytest.mark.case("MACRO-016")
def test_macro_016_cancelling_the_save_or_saving_with_nothing_recorded_saves_no(fresh_app):
    """MACRO-016: Cancelling the save, or saving with nothing recorded, saves nothing"""
    app = fresh_app
    app.new("")
    save_as(app, "Empty", expect_ran=False)
    record_typing(app, "a")
    app.answers(alerts=[2])
    app.run("IDM_MACRO_SAVECURRENTMACRO")
    assert saved_titles(app) == []
    mj = home_dir(app) / "macros.json"
    if mj.exists():
        assert json.loads(mj.read_text() or "{}") == {}
    sx = home_dir(app) / "shortcuts.xml"
    if sx.exists():
        assert "<Macro " not in sx.read_text()


@pytest.mark.case("MACRO-017")
def test_macro_017_saving_under_an_existing_name_replaces_that_macro(app):
    """MACRO-017: Saving under an existing name replaces that macro"""
    record_typing(app, "1")
    save_as(app, "M")
    record_typing(app, "2")
    save_as(app, "M")
    assert saved_titles(app).count("M") == 1
    app.new("")
    invoke_menu(app, "Macro|M")
    assert app.text() == "2"


SHORTCUTS = """<?xml version="1.0" encoding="UTF-8"?>
<NotepadPlus>
    <InternalCommands/>
    <Macros>
        <Macro name="From Windows" Ctrl="yes" Alt="yes" Shift="no" Key="77">
            <Action type="1" message="2170" wParam="0" lParam="0" sParam="hi"/>
            <Action type="0" message="2013" wParam="0" lParam="0" sParam=""/>
            <Action type="2" message="0" wParam="42016" lParam="0" sParam=""/>
        </Macro>
    </Macros>
    <UserDefinedCommands/>
    <PluginCommands/>
    <ScintillaKeys/>
</NotepadPlus>
"""


@pytest.mark.case("MACRO-018")
def test_macro_018_a_macro_from_a_windows_shortcuts_xml_is_brought_in_with_its(app):
    """MACRO-018: A macro from a Windows shortcuts.xml is brought in with its key"""
    app.stop()
    try:
        home = home_dir(app)
        (home / "macros.json").unlink(missing_ok=True)
        write(home / "shortcuts.xml", SHORTCUTS)
        app.start(clean_home=False, reset=False)
        tree = app.menu_tree("Macro", 1)
        item = next(i for i in tree if i.get("title") == "From Windows")
        assert item.get("key") == "alt+cmd+m"
        app.new("")
        invoke_menu(app, "Macro|From Windows")
        assert app.text() == "HI"
        app.new("")
        app.keys("alt+cmd+m")
        assert app.text() == "HI"
        assert "From Windows" in json.loads((home / "macros.json").read_text())
    finally:
        app.stop()
        app.start()


@pytest.mark.case("MACRO-019")
def test_macro_019_several_saved_macros_are_listed_in_name_order(fresh_app):
    """MACRO-019: Several saved macros are listed in name order"""
    app = fresh_app
    for name, text in [("b macro", "b"), ("A macro", "A"), ("c macro", "c")]:
        record_typing(app, text)
        save_as(app, name)
    assert saved_titles(app) == ["A macro", "b macro", "c macro"]
    for name, text in [("A macro", "A"), ("b macro", "b"), ("c macro", "c")]:
        app.new("")
        invoke_menu(app, "Macro|" + name)
        assert app.text() == text
