"""RUN: end-to-end tests (plan: plan/RUN.md)."""
import re
import time
from pathlib import Path

import pytest

from harness.app import App
from _util_run import *  # noqa: F401,F403

from harness.sci import *  # noqa: F401,F403


@pytest.mark.case("RUN-001")
def test_run_001_run_runs_a_command_and_shows_it_and_its_output_in_the_consol(app):
    """RUN-001: Run… runs a command and shows it and its output in the Console

    Covers: IDM_EXECUTE
    Channel: modal, ui
    Steps: Open a new document; queue the answer `{button: 1, field: "echo hello-run"}` and run `IDM_EXECUTE`; wait until the Console window's text contains `hello-run`.
    Expect: the modal log has one alert with message `Run (variables such as $(FULL_CURRENT_PATH) are substituted)` and buttons `OK`, `Cancel`; a visible window titled `Console` (class `NppPanel`) exists; its text view is not editable; its text contains the line `> echo hello-run` followed by the line `hello-run`; no `exit status` line is written for a zero status.
    """
    app.new("x")
    m = Mark(app)
    run_prompt(app, "echo hello-run")
    text = m.wait("hello-run\n")
    log = app.modal_log()
    assert len(log) == 1
    assert log[0]["message"] == "Run (variables such as $(FULL_CURRENT_PATH) are substituted)"
    assert log[0]["buttons"] == ["OK", "Cancel"]
    cw = app.window("Console")
    assert cw and cw["class"] == "NppPanel" and cw["visible"]
    tv = app.controls(cw["number"], **{"class": "NSTextView"})[0]
    assert tv["editable"] is False
    assert "> echo hello-run\nhello-run\n" in text
    app.idle(0.3)
    assert "exit status" not in m.text()


@pytest.mark.case("RUN-002")
def test_run_002_run_has_shift_cmd_r_and_opens_from_the_keyboard(app):
    """RUN-002: Run… has Shift+Cmd+R and opens from the keyboard

    Covers: IDM_EXECUTE
    Channel: keys, menu, modal
    Steps: Read the menu item of `IDM_EXECUTE`; queue the answer `{button: 1, field: "echo from-keys"}` and press `shift+cmd+r` in the main window.
    Expect: the item's title is `Run…`, it is enabled and its key is `shift+cmd+r`; the modal log shows the Run prompt answered `OK`; the Console receives `from-keys`.
    """
    item = app.menu_item("IDM_EXECUTE")
    assert item["title"] == "Run…" and item["enabled"] and item["key"] == "shift+cmd+r"
    app.new("x")
    app.modal_log()
    m = Mark(app)
    app.answers(alerts=[{"button": 1, "field": "echo from-keys"}])
    app.keys("shift+cmd+r", window="main")
    assert any(e.get("kind") == "alert" for e in app.modal_log())
    m.wait("from-keys\n")


@pytest.mark.case("RUN-003")
def test_run_003_cancel_runs_nothing_the_prompt_offers_the_last_command(app):
    """RUN-003: Cancel runs nothing; the prompt offers the last command

    Covers: IDM_EXECUTE
    Channel: modal, ui
    Steps: Run `echo first-cmd` through `IDM_EXECUTE`; wait for it in the Console. Queue answer `2` (Cancel) with field `echo must-not-run` and run `IDM_EXECUTE` again; then queue `2` once more and run it a third time.
    Expect: after the cancel the Console text has no `must-not-run`; the third prompt's `fields` in the modal log are `["echo first-cmd"]` (the last command that ran, not the cancelled text); an empty field answered `OK` runs nothing either (no new `> ` line).
    """
    app.new("x")
    run_and_wait(app, "echo first-cmd", "first-cmd\n")
    m = Mark(app)
    app.answers(alerts=[{"button": 2, "field": "echo must-not-run"}])
    app.run("IDM_EXECUTE")
    app.modal_log()
    app.answers(alerts=[2])
    app.run("IDM_EXECUTE")
    log = app.modal_log()
    assert log[0]["fields"] == ["echo first-cmd"]
    app.answers(alerts=[{"button": 1, "field": ""}])
    app.run("IDM_EXECUTE")
    app.idle(1.0)
    assert "must-not-run" not in m.text()
    assert "> " not in m.text()


@pytest.mark.case("RUN-004")
def test_run_004_the_file_variables_of_a_saved_document(app, tmp):
    """RUN-004: The file variables of a saved document

    Covers: IDM_EXECUTE
    Channel: modal, ui, files
    Steps: Write `tmp/my file.txt` (`alpha beta\\nsecond line\\n`) and open it; for each of `FULL_CURRENT_PATH`, `CURRENT_DIRECTORY`, `FILE_NAME`, `NAME_PART`, `EXT_PART` run `printf '[%s]\\n' $(NAME)` through the Run prompt.
    Expect: the Console shows exactly one bracketed line per command (a value with a space is passed as one word): `[<tmp>/my file.txt]`, `[<tmp>]`, `[my file.txt]`, `[my file]`, `[.txt]`; the echoed command line (`> …`) shows the value single-quoted where it holds a space.
    """
    f = write(tmp / "my file.txt", "alpha beta\nsecond line\n")
    app.open(f)
    want = {"FULL_CURRENT_PATH": str(f), "CURRENT_DIRECTORY": str(tmp), "FILE_NAME": "my file.txt",
            "NAME_PART": "my file", "EXT_PART": ".txt"}
    for name, value in want.items():
        out = run_to_end(app, f"printf '[%s]\\n' $({name})")
        brackets = [l for l in out.splitlines() if l.startswith("[")]
        assert len(brackets) == 1, (name, out)
        got = brackets[0][1:-1]
        if name in ("FULL_CURRENT_PATH", "CURRENT_DIRECTORY"):
            assert App.same_path(got, value), (name, got)
        else:
            assert got == value, (name, got)
        echoed = [l for l in out.splitlines() if l.startswith("> ")][0]
        if " " in value:
            assert "'" in echoed and value.split("/")[-1] in echoed, echoed


@pytest.mark.case("RUN-005")
def test_run_005_ext_part_keeps_the_dot_and_is_empty_without_an_extension(app, tmp):
    """RUN-005: EXT_PART keeps the dot and is empty without an extension

    Covers: IDM_EXECUTE
    Channel: modal, ui, files
    Steps: For each of the files `tmp/Makefile` and `tmp/a.tar.gz`, open it and run `printf '<%s|%s>\\n' "$(NAME_PART)" "$(EXT_PART)"`.
    Expect: `Makefile` gives `<Makefile|>`; `a.tar.gz` gives `<a.tar|.gz>`.
    """
    for fname, want in (("Makefile", "<Makefile|>"), ("a.tar.gz", "<a.tar|.gz>")):
        app.open(write(tmp / fname, "x\n"))
        out = run_to_end(app, "printf '<%s|%s>\\n' \"$(NAME_PART)\" \"$(EXT_PART)\"")
        assert want in out.splitlines(), (fname, out)


@pytest.mark.case("RUN-006")
def test_run_006_the_caret_variables_zero_based_line_and_column_as_on_windows(app, tmp):
    """RUN-006: The caret variables (zero-based line and column, as on Windows)

    Covers: IDM_EXECUTE
    Channel: modal, ui, mcp
    Steps: Open a file with `alpha beta\\nsecond line\\n`; put the caret at line 1 column 8 (one-based, inside `beta`) and run `printf '[%s][%s][%s][%s]\\n' $(CURRENT_WORD) $(CURRENT_LINE) $(CURRENT_COLUMN) $(CURRENT_LINESTR)`; then select `second` on line 2 and run `printf '[%s]\\n' $(CURRENT_WORD)`.
    Expect: the first line is `[beta][0][7][alpha beta]` (line and column are Scintilla's zero-based numbers, not the status bar's); with a selection CURRENT_WORD is the selected text: `[second]`.
    """
    app.open(write(tmp / "c.txt", "alpha beta\nsecond line\n"))
    app.select(1, 8)
    out = run_to_end(app, "printf '[%s][%s][%s][%s]\\n' $(CURRENT_WORD) $(CURRENT_LINE) $(CURRENT_COLUMN) $(CURRENT_LINESTR)")
    assert "[beta][0][7][alpha beta]" in out.splitlines(), out
    app.select(2, 1, 2, 7)
    out = run_to_end(app, "printf '[%s]\\n' $(CURRENT_WORD)")
    assert "[second]" in out.splitlines(), out


@pytest.mark.case("RUN-007")
def test_run_007_the_application_s_own_variables(app):
    """RUN-007: The application's own variables

    Covers: IDM_EXECUTE
    Channel: modal, ui
    Steps: Run `printf '[%s][%s]\\n' $(NPP_DIRECTORY) $(NPP_FULL_FILE_PATH)`.
    Expect: the first value is the folder that contains the test copy's `.app` bundle (`app.bundle.parent`); the second is the copy's executable (`app.executable`, ending in `Contents/MacOS/NotepadMac`).
    """
    app.new("x")
    out = run_to_end(app, "printf '[%s][%s]\\n' $(NPP_DIRECTORY) $(NPP_FULL_FILE_PATH)")
    line = [l for l in out.splitlines() if l.startswith("[")][0]
    first, second = line[1:-1].split("][")
    assert App.same_path(first, str(app.bundle.parent)), first
    assert App.same_path(second, str(app.executable)) and second.endswith("Contents/MacOS/NotepadMac"), second


@pytest.mark.case("RUN-008")
def test_run_008_an_untitled_document_gives_its_tab_name(app):
    """RUN-008: An untitled document gives its tab name

    Covers: IDM_EXECUTE
    Channel: modal, ui, mcp
    Steps: With only an empty untitled document open (tab name from `list_documents`, e.g. `new 1`), run `printf '[%s][%s][%s]\\n' "$(FULL_CURRENT_PATH)" "$(FILE_NAME)" "$(CURRENT_DIRECTORY)"`.
    Expect: the Console shows `[new 1][new 1][]` (with the actual tab name); the command runs and exits 0.
    """
    title = app.docs()[0]["title"]
    m = Mark(app)
    run_prompt(app, "printf '[%s][%s][%s]\\n' \"$(FULL_CURRENT_PATH)\" \"$(FILE_NAME)\" \"$(CURRENT_DIRECTORY)\"; echo done-008")
    text = m.wait("done-008\n")
    assert f"[{title}][{title}][]" in text.splitlines(), text
    assert "exit status" not in text


@pytest.mark.case("RUN-009")
def test_run_009_unknown_and_unclosed_variables_are_left_for_the_shell(app):
    """RUN-009: Unknown and unclosed variables are left for the shell

    Covers: IDM_EXECUTE
    Channel: modal, ui
    Steps: Run in turn `echo $(echo sub-ok)`, `echo 'a $(unclosed'`, `echo 'cost is $5'` and `echo $(NOT_A_VAR_XYZ) tail`.
    Expect: the Console shows `sub-ok` (an unknown name is the shell's command substitution), `a $(unclosed`, `cost is $5`; for the last, the echoed command line still reads `$(NOT_A_VAR_XYZ)` and the shell's `NOT_A_VAR_XYZ: command not found` appears, followed by ` tail` output.
    """
    app.new("x")
    assert "sub-ok" in run_to_end(app, "echo $(echo sub-ok)").splitlines()
    assert "a $(unclosed" in run_to_end(app, "echo 'a $(unclosed'").splitlines()
    assert "cost is $5" in run_to_end(app, "echo 'cost is $5'").splitlines()
    out = run_to_end(app, "echo $(NOT_A_VAR_XYZ) tail")
    echoed = [l for l in out.splitlines() if l.startswith("> ")][0]
    assert "$(NOT_A_VAR_XYZ)" in echoed
    assert "NOT_A_VAR_XYZ: command not found" in out
    assert "tail" in [l.strip() for l in out.splitlines()]


@pytest.mark.case("RUN-010")
def test_run_010_text_from_the_document_never_becomes_a_command(app, tmp):
    """RUN-010: Text from the document never becomes a command

    Covers: IDM_EXECUTE
    Channel: modal, ui, files
    Steps: Open `tmp/inj.txt` whose first line is `a'b"c $HOME ` + "`touch PWNED1`" + `; touch PWNED2`; caret on line 1. For each of `echo $(CURRENT_LINESTR)`, `echo "$(CURRENT_LINESTR)"`, `echo '$(CURRENT_LINESTR)'`, `echo "$(printf %s $(CURRENT_LINESTR))"` and `echo ` + "`printf %s $(CURRENT_LINESTR)`" run it and wait for its output.
    Expect: no file `PWNED1` or `PWNED2` appears in `tmp` (nor in the app's working folder); every command prints the line literally, `$HOME` unexpanded.
    """
    lines = ["a'b\"c $HOME `touch PWNED1`; touch PWNED2", "x`; touch PWNED9; echo `y"]
    f = write(tmp / "inj.txt", "\n".join(lines) + "\n")
    app.open(f)
    for n, line in enumerate(lines, 1):
        app.select(n, 1)
        for cmd in ("echo $(CURRENT_LINESTR)", "echo \"$(CURRENT_LINESTR)\"", "echo '$(CURRENT_LINESTR)'",
                    "echo \"$(printf %s $(CURRENT_LINESTR))\"", "echo `printf %s $(CURRENT_LINESTR)`"):
            out = run_to_end(app, cmd)
            for place in (tmp, Path(app.executable).parent):
                made = [x for x in ("PWNED1", "PWNED2", "PWNED9") if (place / x).exists()]
                assert not made, (cmd, line, made)
            assert line in output_lines(out), (cmd, line, out)


@pytest.mark.case("RUN-011")
def test_run_011_the_command_runs_in_the_document_s_folder(app, tmp):
    """RUN-011: The command runs in the document's folder

    Covers: IDM_EXECUTE
    Channel: modal, ui, files
    Steps: Open `tmp/sub/w.txt` and run `pwd; ls`; also create `tmp/sub/marker.txt` beforehand.
    Expect: the Console shows `<tmp>/sub` (symlinks resolved) and lists `marker.txt` and `w.txt`.
    """
    write(tmp / "sub/marker.txt", "m\n")
    app.open(write(tmp / "sub/w.txt", "w\n"))
    out = run_to_end(app, "pwd; ls")
    lines = [l for l in out.splitlines() if not l.startswith("> ")]
    assert App.same_path(lines[0], str(tmp / "sub")), lines
    assert "marker.txt" in lines and "w.txt" in lines


@pytest.mark.case("RUN-012")
def test_run_012_failure_standard_error_and_non_ascii_output_reach_the_consol(app):
    """RUN-012: Failure, standard error and non-ASCII output reach the Console

    Covers: IDM_EXECUTE
    Channel: modal, ui
    Steps: Run `echo oops >&2; printf 'é✓ 日本\\n'; exit 3`; then run `/no/such/program`.
    Expect: the Console shows `oops`, `é✓ 日本` (decoded as UTF-8) and `(exit status 3)`; the second gives the shell's `not found` message and `(exit status 127)`.
    """
    app.new("x")
    m = Mark(app)
    run_prompt(app, "echo oops >&2; printf 'é✓ 日本\\n'; exit 3")
    text = m.wait("(exit status 3)\n")
    assert "oops" in text.splitlines() and "é✓ 日本" in text.splitlines()
    m = Mark(app)
    run_prompt(app, "/no/such/program")
    text = m.wait("(exit status 127)\n")
    assert "No such file or directory" in text or "not found" in text


@pytest.mark.case("RUN-013")
def test_run_013_a_command_runs_in_the_background_and_its_output_streams(app):
    """RUN-013: A command runs in the background and its output streams

    Covers: IDM_EXECUTE
    Channel: modal, ui, mcp
    Steps: Run `echo first-part; sleep 3; echo second-part`; immediately afterwards time a `get_document` call and poll the Console.
    Expect: `run_command` and `get_document` each come back in under 1 s while the command runs; `first-part` is in the Console while `second-part` is not yet; `second-part` arrives within 10 s.
    """
    app.new("x")
    m = Mark(app)
    app.answers(alerts=[{"button": 1, "field": "echo first-part; sleep 3; echo second-part"}])
    t = time.monotonic()
    app.run("IDM_EXECUTE")
    assert time.monotonic() - t < 1.0
    t = time.monotonic()
    app.call("get_document")
    assert time.monotonic() - t < 1.0
    m.wait("first-part\n", 3)
    assert "second-part" not in output_lines(m.text())
    app.wait(lambda: "second-part" in output_lines(m.text()), 10)


@pytest.mark.slow
@pytest.mark.case("RUN-014")
def test_run_014_a_run_command_is_not_ended_after_30_seconds(app):
    """RUN-014: A Run command is not ended after 30 seconds, and a child left in the background does not hold it

    Covers: IDM_EXECUTE
    Channel: modal, ui
    Steps: (slow, ~35 s) Run `sleep 33; echo still-here` and poll the Console for up to 45 s; then Run `(sleep 3; echo late-line) & exit 4`.
    Expect: `still-here` arrives (Command::run hands the program to ShellExecute, which sets no time limit) and the Console never says `timed out`; the second command's `(exit status 4)` comes at once, before `late-line` (its shell has ended; the child it left holds the output pipe), and `late-line` still reaches the Console afterwards.
    """
    app.new("x")
    m = Mark(app)
    run_prompt(app, "sleep 33; echo still-here")
    m.wait("still-here\n", 45)
    assert "timed out" not in m.text()
    m2 = Mark(app)
    run_prompt(app, "(sleep 3; echo late-line) & exit 4")
    m2.wait("(exit status 4)\n", 10)
    assert "late-line" not in m2.text().splitlines()   # the echoed command line has the words too
    m2.wait("late-line\n", 10)


@pytest.mark.case("RUN-015")
def test_run_015_save_current_command_adds_a_named_entry_to_the_run_menu(app, tmp):
    """RUN-015: Save Current Command… adds a named entry to the Run menu

    Covers: -
    Channel: menu, modal, prefs, ui
    Steps: Run `echo last-one` through `IDM_EXECUTE`; queue `{button: 1, field: "echo saved $(FILE_NAME)"}` and `{button: 1, field: "Say"}` and run `Run|Save Current Command…`; open `tmp/x.txt` and run `Run|Say`.
    Expect: the first prompt (`Command to save`) offered `echo last-one`; the second is `Name it`; the Run menu ends with a separator and an item `Say`; the preference `savedRunCommands` is `[{"name": "Say", "command": "echo saved $(FILE_NAME)"}]`; running it prints `saved x.txt` (variables are filled in when it runs, from the document in front).
    """
    try:
        app.new("x")
        run_and_wait(app, "echo last-one", "last-one\n")
        app.modal_log()
        app.answers(alerts=[{"button": 1, "field": "echo saved $(FILE_NAME)"}, {"button": 1, "field": "Say"}])
        app.run("Run|Save Current Command…")
        log = app.modal_log()
        assert log[0]["message"] == "Command to save" and log[0]["fields"] == ["echo last-one"]
        assert log[1]["message"] == "Name it"
        tree = app.menu_tree("Run", 1)
        assert tree[-2].get("separator") and tree[-1]["title"] == "Say"
        assert app.pref("savedRunCommands") == [{"name": "Say", "command": "echo saved $(FILE_NAME)"}]
        app.open(write(tmp / "x.txt", "x\n"))
        m = Mark(app)
        app.run("Run|Say")
        m.wait("saved x.txt\n")
    finally:
        clear_saved_commands(app)


@pytest.mark.case("RUN-016")
def test_run_016_saving_under_an_existing_name_replaces_a_cancelled_save_save(app):
    """RUN-016: Saving under an existing name replaces; a cancelled save saves nothing

    Covers: -
    Channel: menu, modal, prefs
    Steps: Save `make` as `Build`, then `make -j8` as `Build`; then run Save Current Command… answering the name prompt with Cancel; then answer the command prompt with Cancel.
    Expect: `savedRunCommands` holds one `Build` entry with command `make -j8` and the Run menu one `Build` item; the cancelled saves add nothing; when the command prompt is cancelled the name prompt is not shown (one alert in the log).
    """
    try:
        for cmd in ("make", "make -j8"):
            app.answers(alerts=[{"button": 1, "field": cmd}, {"button": 1, "field": "Build"}])
            app.run("Run|Save Current Command…")
        assert app.pref("savedRunCommands") == [{"name": "Build", "command": "make -j8"}]
        titles = [i.get("title") for i in app.menu_tree("Run", 1)]
        assert titles.count("Build") == 1
        app.modal_log()
        app.answers(alerts=[{"button": 1, "field": "echo other"}, 2])
        app.run("Run|Save Current Command…")
        assert len(app.modal_log()) == 2
        app.answers(alerts=[2])
        app.run("Run|Save Current Command…")
        assert len(app.modal_log()) == 1
        assert app.pref("savedRunCommands") == [{"name": "Build", "command": "make -j8"}]
    finally:
        clear_saved_commands(app)


@pytest.mark.case("RUN-017")
def test_run_017_manage_saved_commands_lists_and_removes(app):
    """RUN-017: Manage Saved Commands… lists and removes

    Covers: -
    Channel: menu, modal, prefs, clipboard
    Steps: Save `A` = `echo a` and `B` = `echo b`; queue `2` (Copy) for the listing and `{button: 1, field: "A"}` for the removal prompt and run `Run|Manage Saved Commands…`; run it again answering the removal prompt with `nosuch`; remove `B`; run it once more.
    Expect: the listing alert is titled `Saved Commands` with informative text `A\\techo a\\nB\\techo b\\n`; Copy puts that text on the clipboard; after the removal only `B` is in the menu and the preference; an unknown name removes nothing; with nothing saved the only alert is `No commands have been saved.` (no removal prompt) and the Run menu has no trailing separator.
    """
    try:
        for name, cmd in (("A", "echo a"), ("B", "echo b")):
            app.answers(alerts=[{"button": 1, "field": cmd}, {"button": 1, "field": name}])
            app.run("Run|Save Current Command…")
        app.modal_log()
        app.answers(alerts=[2, {"button": 1, "field": "A"}])
        app.run("Run|Manage Saved Commands…")
        log = app.modal_log()
        assert log[0]["message"] == "Saved Commands"
        assert log[0]["informative"] == "A\techo a\nB\techo b\n"
        assert app.clipboard() == "A\techo a\nB\techo b\n"
        assert app.pref("savedRunCommands") == [{"name": "B", "command": "echo b"}]
        assert [i.get("title") for i in app.menu_tree("Run", 1)][-1] == "B"
        app.answers(alerts=[1, {"button": 1, "field": "nosuch"}])
        app.run("Run|Manage Saved Commands…")
        assert app.pref("savedRunCommands") == [{"name": "B", "command": "echo b"}]
        app.answers(alerts=[1, {"button": 1, "field": "B"}])
        app.run("Run|Manage Saved Commands…")
        assert app.pref("savedRunCommands") in ([], None)
        app.modal_log()
        app.answers(alerts=[1])
        app.run("Run|Manage Saved Commands…")
        log = app.modal_log()
        assert len(log) == 1 and "No commands have been saved." in (log[0]["informative"] + log[0]["message"])
        assert not app.menu_tree("Run", 1)[-1].get("separator")
    finally:
        clear_saved_commands(app)


@pytest.mark.case("RUN-018")
def test_run_018_saved_commands_survive_a_restart(app):
    """RUN-018: Saved commands survive a restart

    Covers: -
    Channel: launch, menu, prefs, ui
    Steps: Save `Keep` = `echo kept-across`; `app.restart()` (home and preferences kept); run `Run|Keep`.
    Expect: after the restart the Run menu still lists `Keep` and running it prints `kept-across`. (The test removes it afterwards.)
    """
    try:
        app.answers(alerts=[{"button": 1, "field": "echo kept-across"}, {"button": 1, "field": "Keep"}])
        app.run("Run|Save Current Command…")
        app.restart()
        assert "Keep" in [i.get("title") for i in app.menu_tree("Run", 1)]
        m = Mark(app)
        app.run("Run|Keep")
        m.wait("kept-across\n")
    finally:
        clear_saved_commands(app)


@pytest.mark.case("RUN-019")
def test_run_019_user_commands_from_shortcuts_xml_come_with_their_shortcut(app):
    """RUN-019: User commands from shortcuts.xml come with their shortcut

    Covers: -
    Channel: launch, files, keys, menu, ui
    Steps: Stop the app, write `home/Library/Application Support/NotepadMac/shortcuts.xml` with `<NotepadPlus><UserDefinedCommands><Command name="Hello" Ctrl="yes" Alt="yes" Shift="no" Key="72">echo hello-from-xml</Command></UserDefinedCommands></NotepadPlus>`, restart keeping the home; press `cmd+alt+h`.
    Expect: the Run menu has `Hello` with key `alt+cmd+h` (Windows Ctrl is Command); `savedRunCommands` now contains it; the key prints `hello-from-xml` in the Console.
    """
    app.stop()
    xml = (app.home / "Library/Application Support/NotepadMac/shortcuts.xml")
    try:
        write(xml, '<NotepadPlus><UserDefinedCommands><Command name="Hello" Ctrl="yes" Alt="yes" Shift="no" '
                   'Key="72">echo hello-from-xml</Command></UserDefinedCommands></NotepadPlus>\n')
        app.start(clean_home=False, reset=True)
        hello = [i for i in app.menu_tree("Run", 1) if i.get("title") == "Hello"]
        assert hello and hello[0]["key"] == "alt+cmd+h", hello
        assert {"name": "Hello", "command": "echo hello-from-xml"} in (app.pref("savedRunCommands") or [])
        app.new("x")
        m = Mark(app)
        app.keys("cmd+alt+h", window="main")
        m.wait("hello-from-xml\n")
    finally:
        app.stop()
        app.start()


@pytest.mark.case("RUN-020")
def test_run_020_show_console_and_show_nppexec_console_toggle_the_same_panel(app):
    """RUN-020: Show Console and Show NppExec Console toggle the same panel

    Covers: -
    Channel: menu, ui
    Steps: Run `Run|Show Console`, then `Run|Show Console`, then `Plugins|NppExec|Show NppExec Console` twice; after a Run command, hide the console and run another command.
    Expect: the `Console` window is visible, hidden, visible, hidden in turn (one panel for both menus); its earlier text is kept while hidden; a Run command shows it again.
    """
    before = console(app)
    def visible():
        return any(w["title"] == "Console" and w["visible"] for w in app.windows(all=True))
    states = []
    for path in ("Run|Show Console", "Run|Show Console",
                 "Plugins|NppExec|Show NppExec Console", "Plugins|NppExec|Show NppExec Console"):
        app.run(path)
        app.idle(0.1)
        states.append(visible())
    assert states == [True, False, True, False]
    assert console(app) == before
    app.new("x")
    m = Mark(app)
    run_prompt(app, "echo shown-again")
    m.wait("shown-again\n")
    assert visible()


@pytest.mark.case("RUN-021")
def test_run_021_the_console_is_readable_in_dark_appearance(app, tmp):
    """RUN-021: The Console is readable in dark appearance

    Covers: -
    Channel: prefs, snapshot, modal
    Steps: Switch the app to dark appearance (preference `appearanceMode` = 2, applied), run `printf 'XXXXXXXXXXXXXXXXXXXX\\n'`, and snapshot the Console window; restore the preference.
    Expect: the snapshot's background is dark (mean luminance of the text area < 0.3) and the pixels of the text row include light ones (luminance > 0.6): the text is not black on dark.
    """
    from PIL import Image
    try:
        app.set_prefs(appearanceMode=2)
        app.new("x")
        run_and_wait(app, "printf 'XXXXXXXXXXXXXXXXXXXX\\n'", "XXXXXXXXXXXXXXXXXXXX\n")
        app.idle(0.5)
        cw = app.window("Console")
        png = tmp / "console.png"
        app.snapshot(png, window=cw["number"])
        img = Image.open(png).convert("RGB")
        w, h = img.size
        px = [luminance(img.getpixel((x, y))) for x in range(0, w, 3) for y in range(int(h * 0.1), h, 3)]
        mean = sum(px) / len(px)
        assert mean < 0.3, mean
        assert max(px) > 0.6
    finally:
        app.set_prefs(appearanceMode=0)


@pytest.mark.case("RUN-022")
def test_run_022_validate_shortcuts_xml_is_reachable_by_its_notepad_id_known(app):
    """RUN-022: Validate shortcuts.xml is reachable by its Notepad++ id (known gap)

    Covers: IDM_EXECUTE_VALIDATE_SHORTCUTSXML
    Channel: mcp, menu
    Steps: Read `e2e_menu` for `IDM_EXECUTE_VALIDATE_SHORTCUTSXML`; `run_command` it by name and by id 49001; `list_commands` with query `Validate`.
    Expect: the id resolves to the Run menu's `Validate shortcuts` item and runs (FEATURES.md marks it implemented). Currently the item is labelled `Validate shortcuts` while the id's label is `Validate shortcuts.xml`, so no menu item carries the id and `run_command` answers `Command 49001 is not in this build's menus` - xfail(strict) BUG.
    """
    item = app.menu("IDM_EXECUTE_VALIDATE_SHORTCUTSXML")["IDM_EXECUTE_VALIDATE_SHORTCUTSXML"]
    assert item is not None and item["title"] == "Validate shortcuts"
    app.answers(alerts=[1, 1])
    assert app.call("run_command", command="IDM_EXECUTE_VALIDATE_SHORTCUTSXML")["ran"]
    assert app.call("run_command", command=49001)["ran"]
    names = [c["name"] for c in app.call("list_commands", query="Validate")["commands"]]
    assert "IDM_EXECUTE_VALIDATE_SHORTCUTSXML" in names


@pytest.mark.case("RUN-023")
def test_run_023_validate_shortcuts_reports_no_duplicates_on_a_clean_profile(fresh_app):
    """RUN-023: Validate shortcuts reports no duplicates on a clean profile

    Covers: IDM_EXECUTE_VALIDATE_SHORTCUTSXML
    Channel: menu, modal, clipboard
    Steps: With `fresh_app`, queue `2` (Copy) and run `Run|Validate shortcuts`.
    Expect: one alert titled `Shortcuts` with buttons `OK`, `Copy`; its text is `<N> shortcuts, no duplicates.` with N > 50; Copy puts the same text on the clipboard. Currently it reports `1 duplicate(s): Toggle Full Screen Mode clashes with Toggle Full Screen Mode (f)` - the hidden alternate View item is counted as a clash - xfail(strict) BUG.
    """
    app = fresh_app
    fresh = app
    fresh.answers(alerts=[2])
    fresh.run("Run|Validate shortcuts")
    log = fresh.modal_log()
    assert len(log) == 1
    assert log[0]["message"] == "Shortcuts" and log[0]["buttons"] == ["OK", "Copy"]
    text = log[0]["informative"]
    mm = re.fullmatch(r"(\d+) shortcuts, no duplicates\.", text.strip())
    assert mm and int(mm.group(1)) > 50, text
    assert fresh.clipboard().strip() == text.strip()


@pytest.mark.case("RUN-024")
def test_run_024_validate_shortcuts_names_a_real_clash(app):
    """RUN-024: Validate shortcuts names a real clash

    Covers: IDM_EXECUTE_VALIDATE_SHORTCUTSXML
    Channel: launch, files, menu, modal
    Steps: Before a restart, write a shortcuts.xml whose `UserDefinedCommands` give `One` and `Two` the same combination (`Ctrl="yes" Alt="yes" Key="75"`); restart keeping the home; run `Run|Validate shortcuts`.
    Expect: the report says `duplicate(s)` and has a line `Two clashes with One (k)`.
    """
    app.stop()
    xml = app.home / "Library/Application Support/NotepadMac/shortcuts.xml"
    try:
        write(xml, '<NotepadPlus><UserDefinedCommands>'
                   '<Command name="One" Ctrl="yes" Alt="yes" Shift="no" Key="75">echo one</Command>'
                   '<Command name="Two" Ctrl="yes" Alt="yes" Shift="no" Key="75">echo two</Command>'
                   '</UserDefinedCommands></NotepadPlus>\n')
        app.start(clean_home=False, reset=True)
        app.answers(alerts=[1])
        app.run("Run|Validate shortcuts")
        text = app.modal_log()[0]["informative"]
        assert "duplicate(s)" in text
        assert "Two clashes with One (k)" in text.splitlines() or "Two clashes with One (k)" in text, text
    finally:
        app.stop()
        app.start()


@pytest.mark.case("RUN-025")
def test_run_025_the_execute_nppexec_script_dialog_runs_a_temporary_script(app, tmp):
    """RUN-025: The Execute NppExec Script dialog runs a temporary script

    Covers: -
    Channel: ui, menu
    Steps: Open `tmp/e.txt`; open the dialog (deferred `executeScriptDialog:`); read its controls; set the text view to `ECHO hello $(FILE_NAME)\\nSET n ~ 6*7\\nECHO n=$(n)\\n/bin/echo out`; click `OK`.
    Expect: the window is titled `Execute NppExec Script` with a pop-up whose items start with `<temporary script>`, a text view, and buttons `Save…`, `Delete`, `Cancel`, `OK`; the menu item `Execute NppExec Script…` has key `f6`; after OK the dialog closes and the Console shows `hello e.txt`, `n=42`, `> /bin/echo out`, `out`, `<<< Process finished. (Exit code 0)` in that order; `Stop Running NppExec Script` is disabled once it has finished.
    """
    app.open(write(tmp / "e.txt", "e\n"))
    assert key_name(app.menu_item("Plugins|NppExec|Execute NppExec Script…")["key"]) == "f6"
    m = Mark(app)
    pending, w = open_exec_dialog(app)
    assert w["title"] == "Execute NppExec Script"
    ctr = dialog_controls(app, w)
    popup = dialog_popup(app, w)
    assert popup["items"][0] == "<temporary script>"
    assert dialog_text_view(app, w)
    buttons = [c["title"] for c in ctr if c["class"] == "NSButton"]
    for b in ("Save…", "Delete", "Cancel", "OK"):
        assert b in buttons
    set_dialog_text(app, w, "ECHO hello $(FILE_NAME)\nSET n ~ 6*7\nECHO n=$(n)\n/bin/echo out")
    close_dialog(app, pending, w, "OK")
    text = m.wait("<<< Process finished. (Exit code 0)")
    wait_script_done(app)
    lines = m.lines()
    order = ["hello e.txt", "n=42", "> /bin/echo out", "out", "<<< Process finished. (Exit code 0)"]
    idx = [lines.index(x) for x in order]
    assert idx == sorted(idx), lines
    assert not stop_enabled(app)


@pytest.mark.case("RUN-026")
def test_run_026_cancel_in_the_dialog_runs_nothing_the_dialog_opens_with_the(app):
    """RUN-026: Cancel in the dialog runs nothing; the dialog opens with the last script

    Covers: -
    Channel: ui
    Steps: Run a script `ECHO one-run` through the dialog; open the dialog again, read the text view, replace the text with `ECHO cancelled-run` and click `Cancel`; open it a third time.
    Expect: the second and third openings show `ECHO one-run`; `cancelled-run` never appears in the Console.
    """
    app.new("x")
    exec_script(app, "ECHO one-run", "one-run")
    m = Mark(app)
    pending, w = open_exec_dialog(app)
    assert dialog_text_view(app, w)["value"] == "ECHO one-run"
    set_dialog_text(app, w, "ECHO cancelled-run")
    close_dialog(app, pending, w, "Cancel")
    pending, w = open_exec_dialog(app)
    assert dialog_text_view(app, w)["value"] == "ECHO one-run"
    close_dialog(app, pending, w, "Cancel")
    app.idle(0.5)
    assert "cancelled-run" not in m.text()


@pytest.mark.case("RUN-027")
def test_run_027_saved_scripts_save_the_pop_up_delete_the_menu_and_npes_saved(app):
    """RUN-027: Saved scripts: Save…, the pop-up, Delete, the menu and npes_saved.txt

    Covers: -
    Channel: ui, modal, files, menu
    Steps: In the dialog type `ECHO saved-one`, queue `{button: 1, field: "first"}` and click `Save…`; type `ECHO saved-two`, save as `second`; select `first` in the pop-up; then select `second` and click `Delete`; Cancel.
    Expect: after the saves `home/…/NotepadMac/npes_saved.txt` is `::first\\nECHO saved-one\\n::second\\nECHO saved-two\\n`, the pop-up lists both, the Plugins › NppExec menu ends with a separator and `first`, `second`; selecting `first` loads `ECHO saved-one` into the text view; after Delete the file holds only `first`, the pop-up is back on `<temporary script>`, and the menu lists only `first`.
    """
    clear_saved_scripts(app)
    try:
        pending, w = open_exec_dialog(app)
        for body, name in (("ECHO saved-one", "first"), ("ECHO saved-two", "second")):
            set_dialog_text(app, w, body)
            app.answers(alerts=[{"button": 1, "field": name}])
            app.click(w["number"], "Save…")
            w = app.wait(lambda: app.window(EXEC_DIALOG), 5)
        assert saved_scripts_file(app).read_text() == "::first\nECHO saved-one\n::second\nECHO saved-two\n"
        assert dialog_popup(app, w)["items"][:3] == ["<temporary script>", "first", "second"]
        tree = app.menu_tree("Plugins|NppExec", 1)
        assert [i.get("title") for i in tree[-2:]] == ["first", "second"] and tree[-3].get("separator")
        app.act(w["number"], "select", "first", path=dialog_popup(app, w)["path"])
        assert dialog_text_view(app, w)["value"] == "ECHO saved-one"
        app.act(w["number"], "select", "second", path=dialog_popup(app, w)["path"])
        app.click(w["number"], "Delete")
        w = app.wait(lambda: app.window(EXEC_DIALOG), 5)
        assert saved_scripts_file(app).read_text() == "::first\nECHO saved-one\n"
        assert dialog_popup(app, w)["value"] in ("<temporary script>", None) or \
            dialog_popup(app, w).get("title") == "<temporary script>"
        tree = app.menu_tree("Plugins|NppExec", 1)
        assert [i.get("title") for i in tree[-1:]] == ["first"]
        close_dialog(app, pending, w, "Cancel")
    finally:
        clear_saved_scripts(app)


@pytest.mark.case("RUN-028")
def test_run_028_a_saved_script_from_the_menu_execute_previous_and_its_keys(app, tmp):
    """RUN-028: A saved script from the menu; Execute Previous and its keys

    Covers: -
    Channel: menu, keys, ui, files
    Steps: Write `npes_saved.txt` through the dialog with a script `greet` = `ECHO greeting $(FILE_NAME)`; run `Plugins|NppExec|greet`; then run `Plugins|NppExec|Execute Previous NppExec Script` and press `ctrl+f6`. Separately, with `fresh_app` (no previous script), run Execute Previous deferred (`performSelector` with `executePreviousScript:`).
    Expect: the Console gets `greeting <name>` three times; the Execute Previous item's key is `ctrl+f6`; with no previous script the Execute NppExec Script dialog opens instead (Cancel closes it).
    """
    clear_saved_scripts(app)
    try:
        pending, w = open_exec_dialog(app)
        set_dialog_text(app, w, "ECHO greeting $(FILE_NAME)")
        app.answers(alerts=[{"button": 1, "field": "greet"}])
        app.click(w["number"], "Save…")
        w = app.wait(lambda: app.window(EXEC_DIALOG), 5)
        close_dialog(app, pending, w, "Cancel")
        app.open(write(tmp / "g.txt", "g\n"))
        m = Mark(app)
        app.run("Plugins|NppExec|greet")
        app.wait(lambda: m.text().count("greeting g.txt") == 1)
        wait_script_done(app)
        app.run("Plugins|NppExec|Execute Previous NppExec Script")
        app.wait(lambda: m.text().count("greeting g.txt") == 2)
        wait_script_done(app)
        assert key_name(app.menu_item("Plugins|NppExec|Execute Previous NppExec Script")["key"]) == "ctrl+f6"
        app.keys("ctrl+f6", window="main")
        app.wait(lambda: m.text().count("greeting g.txt") == 3)
        wait_script_done(app)
    finally:
        clear_saved_scripts(app)
    app.stop()
    app.start()
    pending, w = open_exec_dialog(app, "Plugins|NppExec|Execute Previous NppExec Script")
    close_dialog(app, pending, w, "Cancel")


@pytest.mark.case("RUN-029")
def test_run_029_script_flow_set_arithmetic_if_goto_block_if_then(app):
    """RUN-029: Script flow: SET, arithmetic, IF…GOTO, block IF, THEN

    Covers: -
    Channel: ui
    Steps: Run through the dialog: `SET n = 0`, `:again`, `SET n ~ $(n) + 1`, `ECHO pass $(n)`, `IF $(n) < 3 GOTO again`, `IF "$(n)" == "3"` / `ECHO three` / `ELSE IF $(n) == 4` / `ECHO four` / `ELSE` / `ECHO other` / `ENDIF`, `SET half ~ 7 / 2`, `ECHO half=$(half)`, `SET expr = a==b`, `IF "$(expr)" == "a==b" THEN` / `ECHO operator-inside` / `ENDIF`, `SET`.
    Expect: the Console shows `pass 1`, `pass 2`, `pass 3` and no `pass 4`; `three` and neither `four` nor `other`; `half=3.5`; `operator-inside`; the bare `SET` lists the script's variables sorted by name, among them `$(ARGC) = 0`, `$(EXPR) = a==b`, `$(HALF) = 3.5`, `$(N) = 3` in that order.
    """
    app.new("x")
    script = "\n".join([
        "SET n = 0", ":again", "SET n ~ $(n) + 1", "ECHO pass $(n)", "IF $(n) < 3 GOTO again",
        'IF "$(n)" == "3"', "ECHO three", "ELSE IF $(n) == 4", "ECHO four", "ELSE", "ECHO other", "ENDIF",
        "SET half ~ 7 / 2", "ECHO half=$(half)", "SET expr = a==b",
        'IF "$(expr)" == "a==b" THEN', "ECHO operator-inside", "ENDIF", "SET", "ECHO end-029"])
    text = exec_script(app, script, "end-029")
    lines = text.splitlines()
    for x in ("pass 1", "pass 2", "pass 3", "three", "half=3.5", "operator-inside"):
        assert x in lines, (x, lines)
    for x in ("pass 4", "four", "other"):
        assert x not in lines
    wanted = ["$(ARGC) = 0", "$(EXPR) = a==b", "$(HALF) = 3.5", "$(N) = 3"]
    idx = [lines.index(x) for x in wanted]
    assert idx == sorted(idx), lines


@pytest.mark.case("RUN-030")
def test_run_030_programs_their_output_variables_cd_and_the_environment(app, tmp):
    """RUN-030: Programs, their output variables, CD and the environment

    Covers: -
    Channel: ui, files
    Steps: Make `tmp/x/one.txt` and `tmp/x/two.txt`; open `tmp/doc.txt`; run a script: `/bin/pwd`, `CD <tmp>/x`, `ENV_SET GREETING = hello from env`, `/bin/echo "$(SYS.GREETING)"; exit 3`, `ECHO code=$(EXITCODE) out=$(OUTPUT)`, `ls *.txt`, `ECHO first=$(OUTPUT1) last=$(OUTPUTL)`, `CD`, `CD /no/such/dir`, `ECHO not-reached`.
    Expect: the first program prints `<tmp>` (a script starts in the document's folder); the Console shows `CD: <tmp>/x`, `code=3 out=hello from env`, `<<< Process finished. (Exit code 3)`, `first=one.txt last=two.txt`, `Current directory: <tmp>/x`, `- CD: no such folder: /no/such/dir`; `not-reached` is not shown (a failed command ends the script).
    """
    write(tmp / "x/one.txt", "1\n")
    write(tmp / "x/two.txt", "2\n")
    app.open(write(tmp / "doc.txt", "d\n"))
    x = str(tmp / "x")
    script = "\n".join([
        "/bin/pwd", f"CD {x}", "ENV_SET GREETING = hello from env", '/bin/echo "$(SYS.GREETING)"; exit 3',
        "ECHO code=$(EXITCODE) out=$(OUTPUT)", "ls *.txt", "ECHO first=$(OUTPUT1) last=$(OUTPUTL)",
        "CD", "CD /no/such/dir", "ECHO not-reached"])
    text = exec_script(app, script, "- CD: no such folder: /no/such/dir")
    lines = text.splitlines()
    pwd = lines[lines.index("> /bin/pwd") + 1]
    assert App.same_path(pwd, str(tmp)), pwd
    cd = [l for l in lines if l.startswith("CD: ")][0]
    assert App.same_path(cd[4:], x)
    assert "code=3 out=hello from env" in lines
    assert "<<< Process finished. (Exit code 3)" in lines
    assert "first=one.txt last=two.txt" in lines
    cur = [l for l in lines if l.startswith("Current directory: ")][0]
    assert App.same_path(cur[len("Current directory: "):], x)
    assert "not-reached" not in text


@pytest.mark.case("RUN-031")
def test_run_031_editor_commands_from_a_script(app, tmp):
    """RUN-031: Editor commands from a script

    Covers: -
    Channel: ui, files, mcp
    Steps: Write `tmp/y/one.txt` = `alpha\\n`, `tmp/y/two.txt` = `beta\\n`; with the script folder `CD <tmp>/y`, run `NPP_OPEN *.txt`, `NPP_SWITCH one.txt`, `ECHO line=$(CURRENT_LINESTR)`, `SCI_SENDMSG 2013`, `SEL_SETTEXT+ gamma\\tdelta\\n`, `NPP_SAVE`, `NPP_SAVEAS copy.txt`, `NPP_CLOSE copy.txt`, `NPP_CLOSE two.txt`, `NPP_SENDMSG 1234`, then in a second script with an untitled document in front `NPP_SAVE`.
    Expect: `line=alpha`; `one.txt` on disk is `gamma\\tdelta\\n` and `copy.txt` the same; afterwards neither `copy.txt` nor `two.txt` is open (`list_documents`); the Console shows `NPP_SENDMSG is not available on macOS`; the untitled `NPP_SAVE` prints `NPP_SAVE: new N - failed` and opens no Save panel (the modal log is empty).
    """
    y = tmp / "y"
    write(y / "one.txt", "alpha\n")
    write(y / "two.txt", "beta\n")
    app.new("front")
    script = "\n".join([
        f"CD {y}", "NPP_OPEN *.txt", "NPP_SWITCH one.txt", "ECHO line=$(CURRENT_LINESTR)", "SCI_SENDMSG 2013",
        "SEL_SETTEXT+ gamma\\tdelta\\n", "NPP_SAVE", "NPP_SAVEAS copy.txt", "NPP_CLOSE copy.txt",
        "NPP_CLOSE two.txt", "NPP_SENDMSG 1234", "ECHO end-031"])
    text = exec_script(app, script, "end-031")
    assert "line=alpha" in text.splitlines()
    assert (y / "one.txt").read_text() == "gamma\tdelta\n"
    assert (y / "copy.txt").read_text() == "gamma\tdelta\n"
    titles = [d["title"] for d in app.docs()]
    assert "copy.txt" not in titles and "two.txt" not in titles
    assert "NPP_SENDMSG is not available on macOS" in text
    app.new("")
    title = app.doc()["title"]
    app.modal_log()
    text = exec_script(app, "NPP_SAVE\nECHO end-031b", "NPP_SAVE:")
    assert f"NPP_SAVE: {title} - failed" in text.splitlines(), text
    assert app.modal_log() == []


@pytest.mark.case("RUN-032")
def test_run_032_npp_exec_with_arguments_exit_inputbox_and_npp_menucommand(app):
    """RUN-032: NPP_EXEC with arguments, EXIT, INPUTBOX and NPP_MENUCOMMAND

    Covers: -
    Channel: ui, modal, mcp
    Steps: Save scripts `t_greet` = `ECHO hi $(ARGV[1]) of $(ARGC)` and `t_inner` = `ECHO inner-start\\nEXIT $(ARGV[1])\\nECHO inner-not-reached`; with a document `abc` in front and the answer `{button: 1, field: "Hello World"}` queued, run: `INPUTBOX "Who?" : Hello`, `NPP_EXEC t_greet "$(INPUT[2])" two`, `ECHO argc now [$(ARGC)]`, `NPP_MENUCOMMAND Edit|Select All`, `NPP_MENUCOMMAND Edit|No Such Command`, then a second script `NPP_EXEC t_inner 0`, `ECHO outer-goes-on`, `NPP_EXEC t_inner 1`, `ECHO outer-not-reached`; a third script `INPUTBOX "Again?"`, `ECHO after-cancel` with the answer `2` queued.
    Expect: the INPUTBOX alert's message is `NppExec` and informative text `Who?` with field `Hello`; the Console shows `hi World of 2` and `argc now [0]`; the whole document `abc` is selected (`get_selection`); `NPP_MENUCOMMAND: Edit|No Such Command - no such command` ends the first script; `outer-goes-on` appears, `inner-start` twice, neither `inner-not-reached` nor `outer-not-reached`; the cancelled INPUTBOX prints `- INPUTBOX: cancelled` and not `after-cancel`.
    """
    f = saved_scripts_file(app)
    try:
        write(f, "::t_greet\nECHO hi $(ARGV[1]) of $(ARGC)\n"
                 "::t_inner\nECHO inner-start\nEXIT $(ARGV[1])\nECHO inner-not-reached\n")
        app.invoke("app", "rebuildExecMenu")
        app.new("abc")
        app.modal_log()
        app.answers(alerts=[{"button": 1, "field": "Hello World"}])
        text = exec_script(app, "\n".join([
            'INPUTBOX "Who?" : Hello', 'NPP_EXEC t_greet "$(INPUT[2])" two', "ECHO argc now [$(ARGC)]",
            "NPP_MENUCOMMAND Edit|Select All", "NPP_MENUCOMMAND Edit|No Such Command", "ECHO not-shown"]),
            "no such command")
        log = app.modal_log()
        assert log[0]["message"] == "NppExec" and log[0]["informative"] == "Who?" and log[0]["fields"] == ["Hello"]
        lines = text.splitlines()
        assert "hi World of 2" in lines and "argc now [0]" in lines
        assert app.selection()["text"] == "abc"
        assert "NPP_MENUCOMMAND: Edit|No Such Command - no such command" in lines
        assert "not-shown" not in text
        text = exec_script(app, "NPP_EXEC t_inner 0\nECHO outer-goes-on\nNPP_EXEC t_inner 1\nECHO outer-not-reached",
                           "inner-start")
        app.wait(lambda: True)
        assert "outer-goes-on" in text.splitlines()
        assert text.count("inner-start") == 2
        assert "inner-not-reached" not in text and "outer-not-reached" not in text
        app.answers(alerts=[2])
        text = exec_script(app, 'INPUTBOX "Again?"\nECHO after-cancel', "- INPUTBOX: cancelled")
        assert "after-cancel" not in text
    finally:
        clear_saved_scripts(app)


@pytest.mark.case("RUN-033")
def test_run_033_script_errors_and_a_runaway_loop_are_reported_not_hung_on(app):
    """RUN-033: Script errors and a runaway loop are reported, not hung on

    Covers: -
    Channel: ui, mcp
    Steps: Run separately: `GOTO nowhere`; `IF abc` / `ECHO x` / `ENDIF`; `SET v ~ 2 + evil()`; `:top` / `GOTO top`.
    Expect: the Console shows `- GOTO: no label "nowhere"`, `- IF: no comparison in "abc"`, `- SET: cannot calculate "2 + evil()"` and `- the script was stopped: too many steps (an endless loop?)`; the runaway script ends within 20 s, the Stop item is disabled again, and the editor answers `get_document` meanwhile.
    """
    app.new("x")
    assert "- GOTO: no label \"nowhere\"" in exec_script(app, "GOTO nowhere", "GOTO")
    assert "- IF: no comparison in \"abc\"" in exec_script(app, "IF abc\nECHO x\nENDIF", "IF:")
    assert "- SET: cannot calculate \"2 + evil()\"" in exec_script(app, "SET v ~ 2 + evil()", "SET:")
    m = Mark(app)
    pending, w = open_exec_dialog(app)
    set_dialog_text(app, w, ":top\nGOTO top")
    close_dialog(app, pending, w, "OK")
    t = time.monotonic()
    app.call("get_document")
    assert time.monotonic() - t < 2
    m.wait("- the script was stopped: too many steps (an endless loop?)", 20)
    wait_script_done(app, 5)


@pytest.mark.case("RUN-034")
def test_run_034_stop_running_nppexec_script_ends_the_program_and_the_script(app):
    """RUN-034: Stop Running NppExec Script ends the program and the script

    Covers: -
    Channel: menu, ui
    Steps: Check `Plugins|NppExec|Stop Running NppExec Script` is disabled; run a script `ECHO start` / `/bin/sh -c "/bin/sleep 20; true"` / `ECHO after`; wait until Stop is enabled; run Stop and time it.
    Expect: Stop is enabled only while the script runs; within 5 s it is disabled again; the Console shows `- the script was stopped` and `<<< Process finished. (Exit code 15)` and no `after`; the `> /bin/sh -c …` line comes before `- the script was stopped`.
    """
    app.new("x")
    assert not stop_enabled(app)
    m = Mark(app)
    pending, w = open_exec_dialog(app)
    set_dialog_text(app, w, 'ECHO start\n/bin/sh -c "/bin/sleep 20; true"\nECHO after')
    close_dialog(app, pending, w, "OK")
    app.wait(lambda: stop_enabled(app), 5)
    m.wait("> /bin/sh", 5)
    t = time.monotonic()
    app.run(STOP)
    app.wait(lambda: not stop_enabled(app), 5)
    assert time.monotonic() - t < 5
    m.wait("<<< Process finished. (Exit code 15)", 5)
    app.idle(0.5)
    lines = m.lines()
    assert "- the script was stopped" in lines and "after" not in lines
    cmd = [i for i, l in enumerate(lines) if l.startswith("> /bin/sh -c")][0]
    assert cmd < lines.index("- the script was stopped"), lines


@pytest.mark.case("RUN-035")
def test_run_035_a_new_script_stops_the_one_running_cls_and_npp_console(app):
    """RUN-035: A new script stops the one running; CLS and NPP_CONSOLE

    Covers: -
    Channel: ui
    Steps: Start `/bin/sleep 20` / `ECHO old-after` from the dialog; at once run a second script `ECHO new-one`; then run `ECHO before-cls` / `CLS` / `ECHO after-cls`; then `NPP_CONSOLE 0` and later `NPP_CONSOLE 1`.
    Expect: within 5 s `new-one` is shown and `old-after` never; after the second script the Console text is exactly `after-cls\\n`; `NPP_CONSOLE 0` hides the Console window and `NPP_CONSOLE 1` shows it without making it key.
    """
    app.new("x")
    m = Mark(app)
    pending, w = open_exec_dialog(app)
    set_dialog_text(app, w, "/bin/sleep 20\nECHO old-after")
    close_dialog(app, pending, w, "OK")
    app.wait(lambda: stop_enabled(app), 5)
    pending, w = open_exec_dialog(app)
    set_dialog_text(app, w, "ECHO new-one")
    close_dialog(app, pending, w, "OK")
    m.wait("new-one", 5)
    wait_script_done(app, 10)
    app.idle(0.5)
    assert "old-after" not in m.text()
    exec_script(app, "ECHO before-cls\nCLS\nECHO after-cls", None)
    app.wait(lambda: console(app) == "after-cls\n", 5)
    exec_script(app, "NPP_CONSOLE 0")
    assert not any(x["title"] == "Console" and x["visible"] for x in app.windows(all=True))
    exec_script(app, "NPP_CONSOLE 1")
    cw = [x for x in app.windows(all=True) if x["title"] == "Console"][0]
    assert cw["visible"] and not cw["key"]


@pytest.mark.case("RUN-036")
def test_run_036_nppexec_s_own_variables_and_quoting_of_document_text(app, tmp):
    """RUN-036: NppExec's own variables and quoting of document text

    Covers: -
    Channel: ui, clipboard, mcp, files
    Steps: Open `tmp/q.txt` containing `x; touch PWNED3` and select all; set the clipboard to `clip-text`; run `ECHO [$(#1)] [$(#0)]`, `ECHO clip=$(CLIPBOARD_TEXT) cwd=$(CWD)`, `ECHO cfg=$(PLUGINS_CONFIG_DIR)`, `SET sel = $(SELECTED_TEXT)`, `/bin/echo $(sel)`, `SET flags = a b`, `/usr/bin/printf '%s|' $(flags) tail`, `ECHO $(output)`.
    Expect: `$(#1)` is the first open document's path and `$(#0)` the app's executable; `clip=clip-text`, `cwd=<tmp>`; `cfg=` is the Application Support folder under the test home; the selected text is printed literally as one word and `PWNED3` is not created; the author's own `$(flags)` splits into words: `a|b|tail|`; variable names are case-insensitive (`$(output)` = `$(OUTPUT)`).
    """
    q = write(tmp / "q.txt", "x; touch PWNED3\n")
    app.open(q)
    app.select_all()
    app.clipboard(set="clip-text")
    script = "\n".join([
        "ECHO [$(#1)] [$(#0)]", "ECHO clip=$(CLIPBOARD_TEXT) cwd=$(CWD)", "ECHO cfg=$(PLUGINS_CONFIG_DIR)",
        "SET sel = $(SELECTED_TEXT)", "/bin/echo $(sel)", "SET flags = a b", "/usr/bin/printf '%s|' $(flags) tail",
        "ECHO $(output)", "ECHO end-036"])
    text = exec_script(app, script, "end-036")
    lines = text.splitlines()
    first = [l for l in lines if l.startswith("[")][0]
    doc1, exe = first[1:-1].split("] [")
    assert App.same_path(doc1, str(q)), doc1
    assert App.same_path(exe, str(app.executable)), exe
    clip = [l for l in lines if l.startswith("clip=")][0]
    assert clip.startswith("clip=clip-text cwd=") and App.same_path(clip.split(" cwd=")[1], str(tmp))
    cfg = [l for l in lines if l.startswith("cfg=")][0][4:]
    assert App.same_path(cfg, str(app.home / "Library/Application Support/NotepadMac")), cfg
    assert "x; touch PWNED3" in lines
    assert not (tmp / "PWNED3").exists()
    assert "a|b|tail|" in lines
    assert lines.count("a|b|tail|") == 2
