"""GIT: end-to-end tests (plan: plan/GIT.md)."""
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from harness.sci import *  # noqa: F401,F403
from tests._util_set import page as prefs_page
from tests._util_git import (
    ADDED, CHANGED, REMOVED, COMPARE_MASK, NOT_IN_REPO, SCI_MARKERGET,
    click_commit, commit_all, commit_enabled, commit_summary, commit_window, console_text,
    console_visible, cw_get, git, hide_panel, line_count, make_repo, margin_width, markers,
    open_commit_window, panel_button, panel_label, panel_rows, panel_visible, porcelain,
    run_git, set_message, show_panel, status_text, table_act, wait_console_end, wait_markers,
    _ui_ok,
)

HEAD4 = "one\ntwo\nthree\nfour\n"


@pytest.fixture(autouse=True)
def _git_clean(app_session):
    """The Git panel is docked in the main window and outlives a test: hide it after each."""
    yield
    if app_session.running:
        hide_panel(app_session)
        try:
            if app_session.get("editor", "secondaryViewVisible"):
                app_session.run("Plugins|Compare|Clear All Compares", expect_ran=False)
        except Exception:  # noqa: BLE001
            pass


def outside_file(tmp, name="outside.txt", text="x\n"):
    d = tmp / "plain"
    d.mkdir(exist_ok=True)
    p = d / name
    p.write_text(text)
    return p


def row_of(rows, name):
    for i, r in enumerate(rows):
        if r[2] == name or r[2].startswith(name + " "):
            return i
    raise AssertionError(f"no row for {name} in {rows}")


def text_of_sub(app):
    n = app.sci(2006, view="sub")
    return app.sci(2182, n + 1, 0, view="sub", returns="string")


# ---- Menu and reachability ------------------------------------------------

@pytest.mark.case("GIT-001")
def test_git_001_plugins_git_lists_its_sixteen_commands_in_upstream_style_ord(app):
    """GIT-001: Plugins > Git lists its sixteen commands in upstream-style order"""
    tree = app.menu_tree("Plugins|Git", 1)
    shape = ["-" if i.get("separator") else i["title"] for i in tree]
    assert shape == ["Git Panel", "-", "Compare with HEAD", "Clear Active Compare", "Blame", "File History", "-",
                     "Stage File", "Unstage File", "Revert Change at Caret to HEAD", "Discard Changes in File…",
                     "Commit…", "-", "Switch Branch", "New Branch…", "-", "Fetch", "Pull", "Push", "-",
                     "Refresh Git Status"]
    items = [i for i in tree if not i.get("separator")]
    assert all(i["enabled"] for i in items)
    switch = next(i for i in items if i["title"] == "Switch Branch")
    assert "items" in switch or switch.get("submenu_items") is not None or switch.get("action") == "submenuAction:"


@pytest.mark.case("GIT-002")
def test_git_002_every_git_command_outside_a_repository_declines_with_the_rea(app, tmp):
    """GIT-002: Every Git command outside a repository declines with the reason in the console"""
    p = outside_file(tmp)
    app.open(p)
    docs_before = len(app.docs())
    since = len(console_text(app))
    app.modal_log()
    items = ["Compare with HEAD", "Blame", "File History", "Stage File", "Unstage File",
             "Revert Change at Caret to HEAD", "Discard Changes in File..."]
    for item in items:
        run_git(app, item)
    app.answers(alerts=[{"button": 1, "field": "x"}])
    run_git(app, "New Branch...")
    added = console_text(app)[since:]
    assert added.count(f"[git] {NOT_IN_REPO}") == 8, added
    assert console_visible(app)
    assert len(app.docs()) == docs_before
    log = app.modal_log()
    assert [e.get("message") for e in log] == ["New branch name:"], log
    assert app.text() == "x\n"
    assert "⎇" not in status_text(app)
    assert margin_width(app) == 0


@pytest.mark.case("GIT-003")
def test_git_003_fetch_pull_push_outside_a_repository_say_so_in_the_console(app, tmp):
    """GIT-003: Fetch/Pull/Push outside a repository say so in the console"""
    app.open(outside_file(tmp))
    since = len(console_text(app))
    for item in ("Fetch", "Pull", "Push"):
        run_git(app, item)
    added = console_text(app)[since:]
    assert console_visible(app)
    assert added.count(NOT_IN_REPO) == 3, added
    assert "$ git" not in added
    assert app.text() == "x\n"


@pytest.mark.case("GIT-004")
def test_git_004_an_unsaved_new_document_is_treated_as_outside_a_repository(app):
    """GIT-004: An unsaved new document is treated as outside a repository"""
    app.new("text\n")
    assert "⎇" not in status_text(app)
    since = len(console_text(app))
    run_git(app, "Blame")
    assert f"[git] {NOT_IN_REPO}" in console_text(app)[since:]
    show_panel(app)
    assert panel_label(app) == ""
    assert panel_rows(app) == []


# ---- Margin markers ---------------------------------------------------------

@pytest.mark.case("GIT-005")
def test_git_005_changed_added_and_removed_lines_carry_markers_7_6_and_8(app, tmp):
    """GIT-005: Changed, added and removed lines carry markers 7, 6 and 8"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.wait(lambda: margin_width(app) == 6, 6, message="the git margin (worked out off the main thread)")
    app.set_text("one\nTWO\nthree\nfour\nfive\n")
    assert wait_markers(app, range(5), [0, CHANGED, 0, 0, ADDED]) == [0, CHANGED, 0, 0, ADDED]
    app.set_text("one\nthree\nfour\n")
    assert wait_markers(app, range(3), [0, REMOVED, 0]) == [0, REMOVED, 0]
    assert margin_width(app) == 6


@pytest.mark.case("GIT-006")
def test_git_006_lines_removed_at_the_end_put_the_removed_marker_on_the_last(app, tmp):
    """GIT-006: Lines removed at the end put the removed marker on the last line"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\ntwo\n")
    assert line_count(app) == 3
    assert wait_markers(app, range(3), [0, 0, REMOVED]) == [0, 0, REMOVED]


@pytest.mark.case("GIT-007")
def test_git_007_markers_follow_typing_about_0_6_s_after_it_stops_without_a_s(app, tmp):
    """GIT-007: Markers follow typing about 0.6 s after it stops, without a save"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.select(5, 1)
    app.type("six\n")
    assert app.text() == HEAD4 + "six\n"
    assert wait_markers(app, range(6), [0, 0, 0, 0, ADDED, 0]) == [0, 0, 0, 0, ADDED, 0]
    assert app.doc()["modified"] is True
    assert (repo / "a.txt").read_text() == HEAD4


@pytest.mark.case("GIT-008")
def test_git_008_markers_return_to_none_when_the_text_is_typed_back_to_head_s(app, tmp):
    """GIT-008: Markers return to none when the text is typed back to HEAD's"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nTWO\nthree\nfour\n")
    assert wait_markers(app, range(5), [0, CHANGED, 0, 0, 0])[1] == CHANGED
    app.set_text(HEAD4)
    assert wait_markers(app, range(5), [0] * 5) == [0] * 5
    assert margin_width(app) == 6


@pytest.mark.case("GIT-009")
def test_git_009_a_file_never_committed_has_every_line_marked_added(app, tmp):
    """GIT-009: A file never committed has every line marked added"""
    repo = make_repo(tmp)
    (repo / "new.txt").write_text("a\nb\n")
    app.open(repo / "new.txt")
    assert wait_markers(app, range(2), [ADDED, ADDED]) == [ADDED, ADDED]
    assert status_text(app).endswith("⎇ main")
    empty = make_repo(tmp, "empty", files={}, commit=False)
    (empty / "f.txt").write_text("a\nb\n")
    app.open(empty / "f.txt")
    assert wait_markers(app, range(2), [ADDED, ADDED]) == [ADDED, ADDED]
    assert status_text(app).endswith("⎇ main")


@pytest.mark.case("GIT-010")
def test_git_010_the_misc_preference_switches_the_git_margin_off_and_on(app, tmp):
    """GIT-010: The MISC. preference switches the git margin off and on"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nTWO\nthree\nfour\n")
    assert wait_markers(app, range(4), [0, CHANGED, 0, 0])[1] == CHANGED
    try:
        app.set_prefs(gitMarginMarks=False)
        app.run("Plugins|Git|Refresh Git Status")
        assert wait_markers(app, range(5), [0] * 5) == [0] * 5
        assert margin_width(app) == 0
        # The Preferences window shows the setting as it is.
        # On the MISC. page: the window opens on whichever page it showed last.
        prefs_page(app, "MISC.")
        pw = app.wait(lambda: app.window("Preferences"), 5, message="Preferences")["number"]
        box = app.act(pw, "focus", **{"title": "Git: mark lines changed since the last commit in the margin"})
        assert box["control"].get("state") == 0
        app.close_window(pw)
        app.set_prefs(gitMarginMarks=True)
        app.run("Plugins|Git|Refresh Git Status")
        assert wait_markers(app, range(4), [0, CHANGED, 0, 0]) == [0, CHANGED, 0, 0]
        assert margin_width(app) == 6
    finally:
        app.set_prefs(gitMarginMarks=True)
    assert app.pref("gitMarginMarks") in (True, 1, "1", "YES")


@pytest.mark.case("GIT-010")
def test_git_010_the_misc_checkbox_in_preferences_switches_the_margin(app, tmp):
    """GIT-010 (the user's path): unticking the checkbox and applying hides the markers"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nTWO\nthree\nfour\n")
    assert wait_markers(app, range(4), [0, CHANGED, 0, 0])[1] == CHANGED
    try:
        app.run("IDM_SETTING_PREFERENCE")
        pw = app.wait(lambda: app.window("Preferences"), 5, message="Preferences")["number"]
        title = "Git: mark lines changed since the last commit in the margin"
        app.act(pw, "set_state", 0, **{"title": title})
        app.act(pw, "click", **{"class": "NSButton", "title": "Apply"})
        app.close_window(pw)
        app.idle(0.3)
        assert app.pref("gitMarginMarks") in (False, 0, "0", "NO")
        assert wait_markers(app, range(4), [0] * 4) == [0] * 4
        assert margin_width(app) == 0
    finally:
        app.set_prefs(gitMarginMarks=True)


@pytest.mark.case("GIT-011")
def test_git_011_markers_are_recomputed_per_document_when_switching_tabs(app, tmp):
    """GIT-011: Markers are recomputed per document when switching tabs"""
    repo = make_repo(tmp)
    tracked = app.open(repo / "a.txt")["index"]
    app.set_text("one\nTWO\nthree\nfour\n")
    assert wait_markers(app, range(4), [0, CHANGED, 0, 0])[1] == CHANGED
    outside = app.open(outside_file(tmp, text="a\nb\nc\nd\n"))["index"]
    app.call("go_to", document=outside, line=1)
    assert margin_width(app) == 0
    assert markers(app, range(4)) == [0] * 4
    app.call("go_to", document=tracked, line=1)
    assert wait_markers(app, range(4), [0, CHANGED, 0, 0]) == [0, CHANGED, 0, 0]
    assert margin_width(app) == 6


@pytest.mark.case("GIT-012")
def test_git_012_a_repository_reached_through_var_instead_of_private_var_stil(app):
    """GIT-012: A repository reached through /var instead of /private/var still gets markers"""
    base = tempfile.mkdtemp(prefix="npgit", dir=tempfile.gettempdir())
    try:
        assert base.startswith("/var/"), base
        repo = make_repo(Path(base))
        doc = app.open(os.path.join(str(repo), "a.txt"))
        assert doc["path"].startswith("/var/")
        app.wait(lambda: "⎇ main" in status_text(app), 6, message="the branch in the status bar")
        app.set_text("ONE\ntwo\nthree\nfour\n")
        assert wait_markers(app, range(4), [CHANGED, 0, 0, 0]) == [CHANGED, 0, 0, 0]
    finally:
        app.close_all()
        shutil.rmtree(os.path.realpath(base), ignore_errors=True)


@pytest.mark.case("GIT-013")
def test_git_013_big_files_are_not_diffed_while_typing_but_are_on_save(app, tmp):
    """GIT-013: Big files are not diffed while typing but are on save"""
    try:
        _git_013(app, tmp)
    except BaseException:
        # The app may still be busy in the diff: a new one for the next test, not a frozen one.
        app.stop(graceful=False)
        raise


def _git_013(app, tmp):
    line = "x" * 49 + "\n"
    repo = make_repo(tmp, files={"big.txt": line * 50000})
    app.open(repo / "big.txt")
    assert app.doc()["bytes"] == 2_500_000
    app.select(50001, 1)
    app.type("new line\n")
    new = 50000
    assert app.call("get_document", first_line=50001, last_line=50001)["text"] == "new line\n"
    app.idle(1.5)
    assert app.sci(SCI_MARKERGET, new) & ADDED == 0
    app.run("IDM_FILE_SAVE")
    app.wait(lambda: app.sci(SCI_MARKERGET, new) & ADDED, 6, message="the added marker after saving")


# ---- Status bar -------------------------------------------------------------

@pytest.mark.case("GIT-014")
def test_git_014_the_status_bar_ends_with_the_branch_inside_a_repository(app, tmp):
    """GIT-014: The status bar ends with the branch inside a repository"""
    repo = make_repo(tmp)
    git(repo, "checkout", "-q", "-b", "topic")
    app.open(repo / "a.txt")
    branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    # The branch is read off the main thread and shown a moment after the tab.
    app.wait(lambda: status_text(app).endswith(f"    ⎇ {branch}"), 6, message="the branch in the status bar")
    text = status_text(app)
    assert text.endswith(f"    ⎇ {branch}"), text
    assert text.index("INS") < text.index("⎇")


@pytest.mark.case("GIT-015")
def test_git_015_ahead_and_behind_counts_appear_after_local_commits_and_fetch(app, tmp):
    """GIT-015: Ahead and behind counts appear after local commits and Fetch"""
    repo = make_repo(tmp)
    bare = tmp / "bare.git"
    git(tmp, "init", "-q", "--bare", "-b", "main", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "-u", "origin", "main")
    other = tmp / "other"
    git(tmp, "clone", "-q", str(bare), str(other))
    git(other, "config", "user.name", "O")
    git(other, "config", "user.email", "o@example.invalid")
    app.open(repo / "a.txt")
    (repo / "b.txt").write_text("b\n")
    commit_all(repo, "local")
    run_git(app, "Refresh Git Status")
    assert status_text(app).endswith("⎇ main ↑1"), status_text(app)
    (other / "c.txt").write_text("c\n")
    commit_all(other, "remote")
    git(other, "push", "-q")
    since = len(console_text(app))
    run_git(app, "Fetch")
    out = wait_console_end(app, since)
    assert "- done" in out, out
    app.wait(lambda: status_text(app).endswith("⎇ main ↑1 ↓1"), 5, message="↑1 ↓1 in the status bar")
    show_panel(app)
    label = panel_label(app)
    assert "↑1" in label and "↓1" in label, label


@pytest.mark.case("GIT-016")
def test_git_016_a_detached_head_shows_as_head(app, tmp):
    """GIT-016: A detached HEAD shows as HEAD"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    git(repo, "checkout", "-q", "--detach")
    run_git(app, "Refresh Git Status")
    assert status_text(app).endswith("⎇ HEAD"), status_text(app)
    show_panel(app)
    assert panel_label(app).startswith("HEAD  ·  "), panel_label(app)


@pytest.mark.case("GIT-017")
def test_git_017_refresh_git_status_picks_up_a_commit_made_outside_the_editor(app, tmp):
    """GIT-017: Refresh Git Status picks up a commit made outside the editor"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nTWO\nthree\nfour\n")
    app.run("IDM_FILE_SAVE")
    assert wait_markers(app, range(4), [0, CHANGED, 0, 0]) == [0, CHANGED, 0, 0]
    show_panel(app)
    commit_all(repo, "outside")
    run_git(app, "Refresh Git Status")
    assert wait_markers(app, range(5), [0] * 5) == [0] * 5
    assert all(r[2] != "a.txt" for r in panel_rows(app))
    assert status_text(app).endswith("⎇ main")


# ---- Git panel ---------------------------------------------------------------

@pytest.mark.case("GIT-018")
def test_git_018_git_panel_toggles_the_docked_panel(app, tmp):
    """GIT-018: Git Panel toggles the docked panel"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    hide_panel(app)
    run_git(app, "Git Panel")
    assert panel_visible(app)
    titles = app.get("editor", "gitPanel.buttons.items.title")
    assert titles == ["Stage", "Unstage", "Discard", "Commit", "Refresh"]
    cols = app.get("editor", "gitPanel.table.tableColumns.title")
    assert cols == ["Staged", "Status", "File"]
    assert panel_label(app).startswith("main  ·  ")
    run_git(app, "Git Panel")
    assert not panel_visible(app)


@pytest.mark.case("GIT-019")
def test_git_019_the_panel_lists_modified_renamed_staged_and_untracked_files(app, tmp):
    """GIT-019: The panel lists modified, renamed, staged and untracked files in order"""
    repo = make_repo(tmp, files={"src/tracked.txt": "t\n", "other.txt": "o\n"})
    (repo / "src/tracked.txt").write_text("t changed\n")
    git(repo, "mv", "other.txt", "renamed.txt")
    (repo / "fresh.txt").write_text("f\n")
    app.open(repo / "src/tracked.txt")
    show_panel(app)
    assert panel_rows(app) == [["✓", "R", "renamed.txt ← other.txt"], ["", "M", "src/tracked.txt"],
                               ["", "??", "fresh.txt"]]
    assert panel_label(app) == "main  ·  repo  ·  3 changed, 1 staged"


@pytest.mark.case("GIT-020")
def test_git_020_stage_file_and_unstage_file_move_the_current_file_between_in(app, tmp):
    """GIT-020: Stage File and Unstage File move the current file between index and worktree"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nTWO\nthree\nfour\n")
    app.run("IDM_FILE_SAVE")
    show_panel(app)
    run_git(app, "Stage File")
    assert panel_rows(app) == [["✓", "M", "a.txt"]]
    assert porcelain(repo) == "M  a.txt"
    assert panel_label(app).endswith("1 staged")
    run_git(app, "Unstage File")
    assert panel_rows(app) == [["", "M", "a.txt"]]
    assert porcelain(repo) == " M a.txt"


@pytest.mark.case("GIT-021")
def test_git_021_stage_file_on_an_unsaved_document_asks_to_save_first(app, tmp):
    """GIT-021: Stage File on an unsaved document asks to save first"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nTWO\nthree\nfour\n")
    app.modal_log()
    app.answers(alerts=[2])
    run_git(app, "Stage File")
    log = app.modal_log()
    assert len(log) == 1 and log[0]["message"] == "Save the file before staging it?", log
    assert log[0]["buttons"] == ["Save", "Cancel"]
    assert app.doc()["modified"] is True
    assert not any(l[:1] not in (" ", "?") for l in porcelain(repo).splitlines() if l)
    app.answers(alerts=[1])
    run_git(app, "Stage File")
    assert app.doc()["modified"] is False
    assert (repo / "a.txt").read_text() == "one\nTWO\nthree\nfour\n"
    assert porcelain(repo) == "M  a.txt"


@pytest.mark.case("GIT-022")
def test_git_022_the_panel_s_stage_and_unstage_buttons_act_on_the_selected_ro(app, tmp):
    """GIT-022: The panel's Stage and Unstage buttons act on the selected rows"""
    repo = make_repo(tmp)
    (repo / "a.txt").write_text("changed\n")
    (repo / "fresh.txt").write_text("f\n")
    app.open(repo / "a.txt")
    show_panel(app)
    rows = panel_rows(app)
    assert rows == [["", "M", "a.txt"], ["", "??", "fresh.txt"]]
    table_act(app, "select", row_of(rows, "fresh.txt"))
    panel_button(app, "Stage")
    rows = panel_rows(app)
    assert ["✓", "A", "fresh.txt"] in rows, rows
    table_act(app, "select", row_of(rows, "fresh.txt"))
    panel_button(app, "Unstage")
    rows = panel_rows(app)
    assert ["", "??", "fresh.txt"] in rows, rows
    table_act(app, "select", 0)
    table_act(app, "select", 1, extend=True)
    panel_button(app, "Stage")
    rows = panel_rows(app)
    assert all(r[0] == "✓" for r in rows) and len(rows) == 2, rows
    assert panel_label(app).endswith("2 staged"), panel_label(app)


@pytest.mark.case("GIT-023")
def test_git_023_stage_before_the_first_commit_and_unstage_back_to_untracked(app, tmp):
    """GIT-023: Stage before the first commit and unstage back to untracked"""
    repo = make_repo(tmp, files={}, commit=False)
    (repo / "a.txt").write_text("a\n")
    app.open(repo / "a.txt")
    since = len(console_text(app))
    run_git(app, "Stage File")
    assert porcelain(repo) == "A  a.txt"
    run_git(app, "Unstage File")
    assert porcelain(repo) == "?? a.txt"
    assert "[git]" not in console_text(app)[since:]


@pytest.mark.case("GIT-024")
def test_git_024_the_panel_s_discard_asks_and_restores_the_selected_files(app, tmp):
    """GIT-024: The panel's Discard asks and restores the selected files"""
    repo = make_repo(tmp, files={"a.txt": "a\n", "b.txt": "b\n"})
    (repo / "a.txt").write_text("a changed\n")
    (repo / "b.txt").write_text("b changed\n")
    app.open(repo / "a.txt")
    show_panel(app)
    assert [r[2] for r in panel_rows(app)] == ["a.txt", "b.txt"]
    table_act(app, "select", 0)
    table_act(app, "select", 1, extend=True)
    app.modal_log()
    app.answers(alerts=[2])
    panel_button(app, "Discard")
    log = app.modal_log()
    assert len(log) == 1, log
    assert log[0]["message"] == 'Discard the changes in "2 files"?'
    assert log[0]["informative"] == "The file goes back to the last committed version. This cannot be undone."
    assert log[0]["buttons"] == ["Discard", "Cancel"]
    assert (repo / "a.txt").read_text() == "a changed\n" and (repo / "b.txt").read_text() == "b changed\n"
    table_act(app, "select", 0)
    table_act(app, "select", 1, extend=True)
    app.answers(alerts=[1])
    panel_button(app, "Discard")
    assert (repo / "a.txt").read_text() == "a\n" and (repo / "b.txt").read_text() == "b\n"
    app.wait(lambda: app.text() == "a\n", 5, message="the tab reloaded")
    assert app.doc()["modified"] is False
    assert panel_rows(app) == []


@pytest.mark.case("GIT-025")
def test_git_025_the_panel_s_discard_with_nothing_selected_does_nothing(app, tmp):
    """GIT-025: The panel's Discard with nothing selected does nothing"""
    repo = make_repo(tmp)
    (repo / "a.txt").write_text("changed\n")
    app.open(repo / "a.txt")
    show_panel(app)
    if app.get("editor", "gitPanel.table.numberOfSelectedRows"):
        # A selection left from an earlier test: the panel is shown afresh with none.
        app.act("main", "focus", **{"class": "NSTableView"})
        app.invoke("first_responder", "deselectAll:", [None])
    assert app.get("editor", "gitPanel.table.numberOfSelectedRows") == 0
    app.modal_log()
    panel_button(app, "Discard")
    assert app.modal_log() == []
    assert (repo / "a.txt").read_text() == "changed\n"


@pytest.mark.case("GIT-026")
def test_git_026_the_panel_s_refresh_button_and_double_click_on_a_row(app, tmp):
    """GIT-026: The panel's Refresh button and double-click on a row"""
    repo = make_repo(tmp, files={"a.txt": "a\n", "b.txt": "b\n"})
    app.open(repo / "a.txt")
    show_panel(app)
    (repo / "later.txt").write_text("later\n")
    panel_button(app, "Refresh")
    rows = panel_rows(app)
    assert ["", "??", "later.txt"] in rows, rows
    table_act(app, "double_click", row_of(rows, "later.txt"))
    app.wait(lambda: (app.doc().get("path") or "").endswith("later.txt"), 5, message="later.txt in front")
    (repo / "b.txt").unlink()
    panel_button(app, "Refresh")
    rows = panel_rows(app)
    assert ["", "D", "b.txt"] in rows, rows
    count = len(app.docs())
    table_act(app, "double_click", row_of(rows, "b.txt"))
    app.idle(0.2)
    assert len(app.docs()) == count
    assert app.doc()["path"].endswith("later.txt")


@pytest.mark.case("GIT-027")
def test_git_027_the_panel_says_when_the_file_is_outside_a_repository(app, tmp):
    """GIT-027: The panel says when the file is outside a repository"""
    repo = make_repo(tmp)
    (repo / "a.txt").write_text("changed\n")
    tracked = app.open(repo / "a.txt")["index"]
    show_panel(app)
    assert panel_rows(app) == [["", "M", "a.txt"]]
    app.open(outside_file(tmp))
    app.wait(lambda: panel_rows(app) == [], 5, message="no rows outside")
    assert panel_label(app) == NOT_IN_REPO
    app.call("go_to", document=tracked, line=1)
    app.wait(lambda: panel_rows(app) == [["", "M", "a.txt"]], 5, message="the rows again")


# ---- Discard and revert --------------------------------------------------------

@pytest.mark.case("GIT-028")
def test_git_028_discard_changes_in_file_asks_then_puts_the_committed_text_ba(app, tmp):
    """GIT-028: Discard Changes in File asks, then puts the committed text back on disk and in the tab"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("changed\n")
    app.run("IDM_FILE_SAVE")
    app.modal_log()
    app.answers(alerts=[2])
    run_git(app, "Discard Changes in File...")
    log = app.modal_log()
    assert len(log) == 1 and log[0]["message"] == 'Discard the changes in "a.txt"?', log
    assert log[0]["buttons"] == ["Discard", "Cancel"]
    assert (repo / "a.txt").read_text() == "changed\n" and app.text() == "changed\n"
    app.answers(alerts=[1])
    run_git(app, "Discard Changes in File...")
    assert (repo / "a.txt").read_text() == HEAD4
    app.wait(lambda: app.text() == HEAD4, 5, message="the tab reloaded")
    assert app.doc()["modified"] is False
    assert wait_markers(app, range(5), [0] * 5) == [0] * 5


@pytest.mark.case("GIT-029")
def test_git_029_revert_change_at_caret_restores_a_changed_line_in_one_undo_s(app, tmp):
    """GIT-029: Revert Change at Caret restores a changed line in one undo step"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nTWO\nthree\nfour\nfive\n")
    app.select(2, 1)
    run_git(app, "Revert Change at Caret to HEAD")
    assert app.text() == "one\ntwo\nthree\nfour\nfive\n"
    assert app.selection()["caret"]["line"] == 2 and app.selection()["caret"]["column"] == 1
    assert wait_markers(app, range(6), [0, 0, 0, 0, ADDED, 0]) == [0, 0, 0, 0, ADDED, 0]
    app.select(5, 1)
    run_git(app, "Revert Change at Caret to HEAD")
    assert app.text() == HEAD4
    assert wait_markers(app, range(5), [0] * 5) == [0] * 5
    app.run("IDM_EDIT_UNDO")
    assert app.text() == "one\ntwo\nthree\nfour\nfive\n"


@pytest.mark.case("GIT-030")
def test_git_030_revert_change_at_caret_puts_removed_lines_back_and_handles_a(app, tmp):
    """GIT-030: Revert Change at Caret puts removed lines back and handles a last line without ending"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nthree\nfour\n")
    app.select(2, 1)
    run_git(app, "Revert Change at Caret to HEAD")
    assert app.text() == HEAD4
    app.set_text("one\ntwo\nthree\nfour\nfive")
    app.select(5, 1)
    run_git(app, "Revert Change at Caret to HEAD")
    assert app.text() == HEAD4


@pytest.mark.case("GIT-031")
def test_git_031_revert_change_at_caret_on_an_unchanged_line_or_an_uncommitte(app, tmp):
    """GIT-031: Revert Change at Caret on an unchanged line or an uncommitted file reports why"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nTWO\nthree\nfour\n")
    app.select(1, 1)
    since = len(console_text(app))
    run_git(app, "Revert Change at Caret to HEAD")
    assert app.text() == "one\nTWO\nthree\nfour\n"
    (repo / "new.txt").write_text("n\n")
    app.open(repo / "new.txt")
    run_git(app, "Revert Change at Caret to HEAD")
    assert app.text() == "n\n"
    added = console_text(app)[since:]
    assert "[git] The caret is on no change since the last commit\n[git] The file is not in HEAD yet\n" in added, added


# ---- Compare with HEAD, blame, history ------------------------------------------

@pytest.mark.case("GIT-032")
def test_git_032_compare_with_head_shows_head_s_text_in_the_second_view_and_c(app, tmp):
    """GIT-032: Compare with HEAD shows HEAD's text in the second view and Clear Active Compare ends it"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nTWO\nthree\nfour\n")
    run_git(app, "Compare with HEAD")
    app.wait(lambda: app.get("editor", "secondaryViewVisible"), 5, message="the second view")
    assert text_of_sub(app) == HEAD4
    app.wait(lambda: app.sci(SCI_MARKERGET, 1) & COMPARE_MASK, 5, message="a compare marker on line 2")
    run_git(app, "Clear Active Compare")
    app.wait(lambda: not app.get("editor", "secondaryViewVisible"), 5, message="the second view hidden")
    assert all(app.sci(SCI_MARKERGET, i) & COMPARE_MASK == 0 for i in range(5))
    assert app.text() == "one\nTWO\nthree\nfour\n"


@pytest.mark.case("GIT-033")
def test_git_033_compare_with_head_for_a_file_not_yet_committed_is_refused(app, tmp):
    """GIT-033: Compare with HEAD for a file not yet committed is refused"""
    repo = make_repo(tmp)
    (repo / "new.txt").write_text("n\n")
    app.open(repo / "new.txt")
    since = len(console_text(app))
    run_git(app, "Compare with HEAD")
    assert not app.get("editor", "secondaryViewVisible")
    assert "[git] The file is not in HEAD yet" in console_text(app)[since:]


@pytest.mark.case("GIT-034")
def test_git_034_blame_opens_a_read_only_document_named_file_blame(app, tmp):
    """GIT-034: Blame opens a read-only document named "<file> (blame)\""""
    repo = make_repo(tmp)
    short = git(repo, "rev-parse", "--short=7", "HEAD")
    orig = app.open(repo / "a.txt")["index"]
    app.set_text("one\nTWO\nthree\nfour\n")
    run_git(app, "Blame")
    d = app.doc()
    assert d["title"] == "a.txt (blame)" and d["read_only"] is True and d["modified"] is False and d["path"] is None
    lines = [l for l in app.text().splitlines() if l]
    assert len(lines) == 4
    assert all("T Runner" in l and short in l for l in lines), lines
    assert app.text(orig) == "one\nTWO\nthree\nfour\n"
    app.call("close_document")
    assert all(x["title"] != "a.txt (blame)" for x in app.docs())


@pytest.mark.case("GIT-035")
def test_git_035_file_history_opens_a_read_only_document_with_the_commits(app, tmp):
    """GIT-035: File History opens a read-only document with the commits"""
    repo = make_repo(tmp, files={"a.txt": "1\n"}, commit=False)
    commit_all(repo, "first")
    (repo / "a.txt").write_text("2\n")
    commit_all(repo, "second")
    app.open(repo / "a.txt")
    run_git(app, "File History")
    d = app.doc()
    assert d["title"] == "a.txt (history)" and d["read_only"] is True
    text = app.text()
    head = r"[0-9a-f]{7,}  \d{4}-\d\d-\d\d  T Runner\n    "
    m2 = re.search(head + "second", text)
    m1 = re.search(head + "first", text)
    assert m1 and m2 and m2.start() < m1.start(), text
    (repo / "new.txt").write_text("n\n")
    app.open(repo / "new.txt")
    run_git(app, "File History")
    assert app.doc()["title"] == "new.txt (history)"
    assert app.text() == "The file is not in HEAD yet\n"


@pytest.mark.case("GIT-036")
def test_git_036_blame_of_an_untracked_file_reports_git_s_error(app, tmp):
    """GIT-036: Blame of an untracked file reports git's error"""
    repo = make_repo(tmp)
    (repo / "new.txt").write_text("n\n")
    app.open(repo / "new.txt")
    count = len(app.docs())
    since = len(console_text(app))
    run_git(app, "Blame")
    assert len(app.docs()) == count
    added = console_text(app)[since:]
    assert "[git] " in added and ("no such path" in added or "fatal" in added), added


# ---- Commit window -----------------------------------------------------------------

@pytest.mark.case("GIT-037")
def test_git_037_commit_opens_the_window_with_its_summary_and_a_disabled_comm(app, tmp):
    """GIT-037: Commit… opens the window with its summary and a disabled Commit button"""
    repo = make_repo(tmp, files={"a.txt": "a\n", "b.txt": "b\n"})
    (repo / "a.txt").write_text("a2\n")
    (repo / "b.txt").write_text("b2\n")
    git(repo, "add", "a.txt")
    app.open(repo / "a.txt")
    cw = open_commit_window(app)
    assert cw_get(app, "panel.title") == "Commit"
    assert cw_get(app, "messageLabel.stringValue") == "Commit message"
    assert cw_get(app, "message.string") == ""
    assert commit_summary(app) == "1 files staged: a.txt  ·  1 not staged"
    assert cw_get(app, "stageAll.title") == "Stage all changes first"
    assert cw_get(app, "stageAll.state") == 0
    assert not commit_enabled(app)
    app.close_window(cw)


@pytest.mark.case("GIT-038")
def test_git_038_typing_a_message_enables_commit_committing_closes_the_window(app, tmp):
    """GIT-038: Typing a message enables Commit; committing closes the window and names the commit"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.set_text("one\nTWO\nthree\nfour\n")
    app.run("IDM_FILE_SAVE")
    git(repo, "add", "a.txt")
    cw = open_commit_window(app)
    assert not commit_enabled(app)
    set_message(app, cw, "second commit\n\nwith a body")
    assert commit_enabled(app)
    since = len(console_text(app))
    click_commit(app, cw)
    app.wait(lambda: commit_window(app) is None, 5, message="the Commit window closed")
    assert git(repo, "log", "-1", "--format=%s") == "second commit"
    assert git(repo, "log", "-1", "--format=%b").strip() == "with a body"
    sha = git(repo, "rev-parse", "HEAD")
    assert f"[git] Committed {sha[:7]}" in console_text(app)[since:]
    assert wait_markers(app, range(5), [0] * 5) == [0] * 5
    assert status_text(app).endswith("⎇ main")


@pytest.mark.case("GIT-039")
def test_git_039_stage_all_changes_first_stages_and_commits_everything(app, tmp):
    """GIT-039: Stage all changes first stages and commits everything"""
    repo = make_repo(tmp)
    (repo / "a.txt").write_text("changed\n")
    (repo / "new.txt").write_text("new\n")
    app.open(repo / "a.txt")
    cw = open_commit_window(app)
    app.act(cw, "click", **{"class": "NSButton", "title": "Stage all changes first"})
    assert commit_summary(app) == "2 files will be staged and committed"
    set_message(app, cw, "everything")
    assert commit_enabled(app)
    click_commit(app, cw)
    app.wait(lambda: commit_window(app) is None, 5, message="the Commit window closed")
    assert porcelain(repo) == ""
    assert set(git(repo, "show", "--name-only", "--format=", "HEAD").split()) == {"a.txt", "new.txt"}
    open_commit_window(app)
    assert cw_get(app, "stageAll.state") == 0
    assert cw_get(app, "message.string") == ""


@pytest.mark.case("GIT-040")
def test_git_040_commit_is_disabled_with_nothing_staged_even_with_a_message_c(app, tmp):
    """GIT-040: Commit is disabled with nothing staged even with a message; Cancel and Escape close"""
    repo = make_repo(tmp)
    (repo / "a.txt").write_text("changed\n")
    head = git(repo, "rev-parse", "HEAD")
    app.open(repo / "a.txt")
    cw = open_commit_window(app)
    set_message(app, cw, "a message")
    assert not commit_enabled(app)
    app.keys("escape", window=cw)
    app.wait(lambda: commit_window(app) is None, 5, message="Escape closes the window")
    cw = open_commit_window(app)
    app.act(cw, "click", **{"class": "NSButton", "title": "Cancel"})
    app.wait(lambda: commit_window(app) is None, 5, message="Cancel closes the window")
    assert git(repo, "rev-parse", "HEAD") == head


@pytest.mark.case("GIT-041")
def test_git_041_a_failing_commit_keeps_the_window_open_with_git_s_message(app, tmp):
    """GIT-041: A failing commit keeps the window open with git's message"""
    repo = make_repo(tmp)
    hook = repo / ".git/hooks/pre-commit"
    hook.write_text("#!/bin/sh\necho 'hook says no' >&2\nexit 1\n")
    hook.chmod(0o755)
    (repo / "a.txt").write_text("changed\n")
    git(repo, "add", "a.txt")
    head = git(repo, "rev-parse", "HEAD")
    app.open(repo / "a.txt")
    cw = open_commit_window(app)
    set_message(app, cw, "blocked")
    click_commit(app, cw)
    assert commit_window(app) == cw
    assert "hook says no" in cw_get(app, "problem.stringValue")
    assert git(repo, "rev-parse", "HEAD") == head
    assert cw_get(app, "message.string") == "blocked"
    app.close_window(cw)


@pytest.mark.case("GIT-042")
def test_git_042_cmd_return_in_the_message_commits(app, tmp):
    """GIT-042: Cmd+Return in the message commits"""
    repo = make_repo(tmp)
    (repo / "a.txt").write_text("changed\n")
    git(repo, "add", "a.txt")
    app.open(repo / "a.txt")
    cw = open_commit_window(app)
    # The window keeps an unsent message (only a commit empties it), so a draft may be there: clear it.
    set_message(app, cw, "")
    app.type("via keyboard", window=cw)
    assert cw_get(app, "message.string") == "via keyboard"
    app.keys("cmd+return", window=cw)
    app.wait(lambda: commit_window(app) is None, 5, message="the window closed")
    assert git(repo, "log", "-1", "--format=%s") == "via keyboard"


@pytest.mark.case("GIT-043")
def test_git_043_the_commit_window_outside_a_repository_says_so(app, tmp):
    """GIT-043: The Commit window outside a repository says so"""
    app.open(outside_file(tmp))
    cw = open_commit_window(app)
    assert commit_summary(app) == NOT_IN_REPO
    assert not commit_enabled(app)
    set_message(app, cw, "a message")
    assert not commit_enabled(app)
    app.close_window(cw)


@pytest.mark.case("GIT-043")
def test_git_043_the_summary_keeps_saying_so_after_a_message_is_typed(app, tmp):
    """GIT-043 (continued): the summary still says why after a message is typed"""
    app.open(outside_file(tmp))
    cw = open_commit_window(app)
    try:
        set_message(app, cw, "a message")
        assert commit_summary(app) == NOT_IN_REPO
    finally:
        app.close_window(cw)


# ---- Branches ------------------------------------------------------------------------

@pytest.mark.case("GIT-044")
def test_git_044_new_branch_creates_and_checks_out_the_branch_a_blank_name_is(app, tmp):
    """GIT-044: New Branch… creates and checks out the branch; a blank name is refused"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.modal_log()
    app.answers(alerts=[{"button": 1, "field": "feature/x"}])
    run_git(app, "New Branch...")
    log = app.modal_log()
    assert len(log) == 1 and log[0]["message"] == "New branch name:", log
    assert log[0]["buttons"][:2] == ["OK", "Cancel"]
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "feature/x"
    app.wait(lambda: status_text(app).endswith("⎇ feature/x"), 5, message="the new branch in the status bar")
    since = len(console_text(app))
    app.answers(alerts=[{"button": 1, "field": "  "}])
    run_git(app, "New Branch...")
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "feature/x"
    assert "[git] A branch needs a name" in console_text(app)[since:]
    branches = git(repo, "branch", "--list")
    app.answers(alerts=[2])
    run_git(app, "New Branch...")
    assert git(repo, "branch", "--list") == branches


def _two_branches(tmp):
    repo = make_repo(tmp, files={"a.txt": "one\n"})
    git(repo, "checkout", "-q", "-b", "other")
    (repo / "a.txt").write_text("other\n")
    commit_all(repo, "other")
    git(repo, "checkout", "-q", "main")
    return repo


@pytest.mark.case("GIT-045")
def test_git_045_switch_branch_lists_the_branches_with_the_current_one_ticked(app, tmp):
    """GIT-045: Switch Branch lists the branches with the current one ticked and checks one out"""
    repo = _two_branches(tmp)
    app.open(repo / "a.txt")
    tree = app.menu_tree("Plugins|Git|Switch Branch", 1)
    assert [(i["title"], i["checked"]) for i in tree] == [("main", True), ("other", False)]
    app.answers(alerts=[1, 1])
    run_git(app, "Switch Branch|other")
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "other"
    app.wait(lambda: status_text(app).endswith("⎇ other"), 5, message="⎇ other")
    app.wait(lambda: app.text() == "other\n", 5, message="the tab reloaded")
    assert wait_markers(app, range(2), [0, 0]) == [0, 0]
    tree = app.menu_tree("Plugins|Git|Switch Branch", 1)
    assert [(i["title"], i["checked"]) for i in tree] == [("main", False), ("other", True)]
    run_git(app, "Switch Branch|main")
    app.wait(lambda: app.text() == "one\n", 5, message="back to main's text")
    assert status_text(app).endswith("⎇ main")
    app.open(outside_file(tmp))
    tree = app.menu_tree("Plugins|Git|Switch Branch", 1)
    assert [(i["title"], i["enabled"]) for i in tree] == [(NOT_IN_REPO, False)]


@pytest.mark.case("GIT-046")
def test_git_046_switching_to_a_branch_with_conflicting_local_changes_fails_w(app, tmp):
    """GIT-046: Switching to a branch with conflicting local changes fails with git's message"""
    repo = _two_branches(tmp)
    app.open(repo / "a.txt")
    app.set_text("local\n")
    app.run("IDM_FILE_SAVE")
    since = len(console_text(app))
    # The branch list is built when the submenu opens (menuNeedsUpdate:), as a user opens it first.
    assert [i["title"] for i in app.menu_tree("Plugins|Git|Switch Branch", 1)] == ["main", "other"]
    run_git(app, "Switch Branch|other")
    assert git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert status_text(app).endswith("⎇ main")
    added = console_text(app)[since:]
    assert "[git] " in added and "would be overwritten" in added, added
    assert (repo / "a.txt").read_text() == "local\n"


# ---- Remotes in the console ----------------------------------------------------------

@pytest.mark.case("GIT-047")
def test_git_047_push_to_a_local_bare_repository_streams_into_the_console_and(app, tmp):
    """GIT-047: Push to a local bare repository streams into the console and ends done"""
    repo = make_repo(tmp)
    bare = tmp / "bare.git"
    git(tmp, "init", "-q", "--bare", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "config", "push.default", "current")
    app.open(repo / "a.txt")
    since = len(console_text(app))
    run_git(app, "Push")
    out = wait_console_end(app, since, timeout=20)
    assert console_visible(app)
    assert "$ git push" in out and "[new branch]" in out, out
    assert out.rstrip("\n").endswith("- done"), out
    assert git(bare, "rev-parse", "main") == git(repo, "rev-parse", "HEAD")


@pytest.mark.case("GIT-048")
def test_git_048_fetch_from_a_missing_remote_ends_failed_with_git_s_complaint(app, tmp):
    """GIT-048: Fetch from a missing remote ends failed with git's complaint"""
    repo = make_repo(tmp)
    git(repo, "remote", "add", "origin", "/nonexistent/remote")
    app.open(repo / "a.txt")
    app.wait(lambda: status_text(app).endswith("⎇ main"), 6, message="the branch in the status bar")
    before = status_text(app)
    since = len(console_text(app))
    run_git(app, "Fetch")
    assert app.call("get_document")["text"] == HEAD4   # the editor answers while git runs
    out = wait_console_end(app, since, timeout=20)
    assert "$ git fetch --all --prune" in out
    assert "fatal" in out or "does not appear" in out, out
    assert out.rstrip("\n").endswith("- git failed"), out
    assert status_text(app).endswith("⎇ main") and before.endswith("⎇ main")


@pytest.mark.case("GIT-049")
def test_git_049_pull_brings_a_remote_commit_in_and_the_open_document_follows(app, tmp):
    """GIT-049: Pull brings a remote commit in and the open document follows"""
    repo = make_repo(tmp)
    bare = tmp / "bare.git"
    git(tmp, "init", "-q", "--bare", "-b", "main", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-q", "-u", "origin", "main")
    git(repo, "config", "pull.rebase", "false")
    other = tmp / "other"
    git(tmp, "clone", "-q", str(bare), str(other))
    git(other, "config", "user.name", "O")
    git(other, "config", "user.email", "o@example.invalid")
    (other / "a.txt").write_text(HEAD4 + "pulled\n")
    commit_all(other, "remote change")
    git(other, "push", "-q")
    app.open(repo / "a.txt")
    app.answers(alerts=[1, 1, 1])
    since = len(console_text(app))
    run_git(app, "Pull")
    out = wait_console_end(app, since, timeout=20)
    assert "$ git pull" in out and out.rstrip("\n").endswith("- done"), out
    assert (repo / "a.txt").read_text() == HEAD4 + "pulled\n"
    app.wait(lambda: app.text() == HEAD4 + "pulled\n", 5, message="the tab follows the pull")
    assert wait_markers(app, range(6), [0] * 6) == [0] * 6
    assert "↓" not in status_text(app)


@pytest.mark.case("GIT-050")
def test_git_050_push_without_a_remote_fails_in_the_console_without_hanging(app, tmp):
    """GIT-050: Push without a remote fails in the console without hanging"""
    repo = make_repo(tmp)
    app.open(repo / "a.txt")
    app.modal_log()
    since = len(console_text(app))
    run_git(app, "Push")
    out = wait_console_end(app, since, timeout=20)
    assert out.rstrip("\n").endswith("- git failed"), out
    assert "No configured push destination" in out or "fatal" in out, out
    assert app.modal_log() == []


# ---- Localisation ------------------------------------------------------------------------

def _size(v):
    """An NSSize/NSRect as e2e_invoke hands it back: a dict, a list or '{w, h}'."""
    if isinstance(v, dict):
        if "width" in v:
            return float(v["width"]), float(v["height"])
        if "size" in v:
            return _size(v["size"])
    if isinstance(v, (list, tuple)):
        return float(v[-2]), float(v[-1])
    nums = re.findall(r"-?[\d.]+", str(v))
    return float(nums[-2]), float(nums[-1])


@pytest.mark.case("GIT-051")
def test_git_051_the_commit_window_and_the_panel_are_translated_and_nothing_i(app_session, tmp):
    """GIT-051: The Commit window and the panel are translated and nothing is cut in German"""
    app = app_session
    try:
        app.start(args=["-NppMac.localizationFile", "german.xml"])
        repo = make_repo(tmp)
        (repo / "a.txt").write_text("changed\n")
        app.open(repo / "a.txt")
        show_panel(app)
        titles = app.get("editor", "gitPanel.buttons.items.title")
        assert titles[0] == "In den Index" and titles[1] == "Aus dem Index", titles
        cw = open_commit_window(app)
        assert cw_get(app, "panel.title") == "Commit"
        assert cw_get(app, "messageLabel.stringValue") == "Commit-Nachricht"
        assert cw_get(app, "stageAll.title") == "Zuerst alle Änderungen zum Index hinzufügen"
        assert cw_get(app, "commitButton.title") == "Commit"
        # Nothing cut: every button is at least as wide as its text needs.
        for key in ("commitButton", "stageAll"):
            need = _size(cw_get(app, f"{key}.fittingSize"))
            have = _size(cw_get(app, f"{key}.frame"))
            assert have[0] + 0.5 >= need[0], (key, need, have)
        widths = app.get("editor", "gitPanel.buttons.items.frame")
        fits = app.get("editor", "gitPanel.buttons.items.fittingSize")
        for have, need in zip(widths, fits):
            assert _size(have)[0] + 0.5 >= _size(need)[0], (have, need)
        app.snapshot(tmp / "commit-de.png", window=cw)
        app.snapshot(tmp / "main-de.png")
        assert (tmp / "commit-de.png").stat().st_size > 0
        app.close_window(cw)
    finally:
        hide_panel(app)
        app.stop()
        app.start()
