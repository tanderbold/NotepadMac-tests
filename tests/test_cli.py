"""CLI: end-to-end tests (plan: plan/CLI.md)."""
import json
import os
import stat
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from harness.sci import *  # noqa: F401,F403
from _util_cli import (App, PRINT_GUARD, alerts, caret, current, find_doc, front, mcp_lines, nppmac,
                       raw_env, read_only, run_executable, support, titles, wait_open, write)
from _util_file import pdf_text


@pytest.fixture
def launch(app):
    """Starts the app with switches; afterwards a plain app runs again for the next test."""
    def go(args=(), **kwargs):
        return app.start(args=[str(a) for a in args], **kwargs)
    yield go
    try:
        app.start()
    except Exception:  # noqa: BLE001
        app.stop(graceful=False)
        app.start()


@pytest.fixture
def ltmp(app, request):
    """A scratch folder for launch arguments under the worker's folder: a plain path, not one
    through the /var -> /private/var link (the app would open such a file twice)."""
    import shutil
    path = app.work / "cl" / request.node.name[:48]
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def settle(app, pred, timeout=10.0, message="the launch to settle"):
    """The launch keeps opening files after the socket answers. The command line is applied
    before the main window is ordered front (applicationDidFinishLaunching:), so poll for both."""
    app.wait(lambda: app.get("window", "visible") in (True, 1), timeout=timeout, message="the main window shown")
    got = app.wait(lambda: pred(app.docs()), timeout=timeout, message=message)
    app.idle(0.3)
    return got


def named(docs, *names):
    return all(any(d["title"] == n for d in docs) for n in names)


# ---- nppmac ------------------------------------------------------------------

@pytest.mark.case("CLI-001")
def test_cli_001_nppmac_opens_a_file_in_the_running_application(app, tmp):
    """CLI-001: nppmac opens a file in the running application"""
    f = write(tmp / "cli.txt", "one\ntwo\n")
    r = nppmac(app, f)
    assert r.returncode == 0 and r.stdout == b"" and r.stderr == b""
    app.wait(lambda: (d := find_doc(app, f)) and d["current"], 10, message="cli.txt current")
    app.wait(lambda: app.text() == "one\ntwo\n", 5, message="cli.txt's text")
    assert alerts(app.modal_log()) == []


@pytest.mark.case("CLI-002")
def test_cli_002_nppmac_n_opens_the_file_that_follows_at_line_n(app, tmp):
    """CLI-002: nppmac +N opens the file that follows at line N"""
    lines = write(tmp / "lines.txt", "".join(f"line {i}\n" for i in range(1, 101)))
    other = write(tmp / "other.txt", "other\nfile\n")
    r = nppmac(app, "+42", lines, other)
    assert r.returncode == 0
    app.wait(lambda: (d := find_doc(app, other)) and d["current"], 10, message="other.txt current")
    assert caret(app)[:2] == (1, 1)
    front(app, lines)
    line, col, _ = caret(app)
    assert (line, col) == (42, 1)
    first = app.sci(SCI_GETFIRSTVISIBLELINE)
    assert first <= 41 < first + app.sci(SCI_LINESONSCREEN)
    front(app, other)
    count = len(app.docs())
    r = nppmac(app, "+7", lines)
    assert r.returncode == 0
    app.wait(lambda: (d := find_doc(app, lines)) and d["current"] and caret(app)[0] == 7, 10,
             message="lines.txt forward at line 7")
    assert len(app.docs()) == count


@pytest.mark.case("CLI-003")
def test_cli_003_nppmac_opens_several_files_and_a_folder_as_a_workspace_root(app, tmp):
    """CLI-003: nppmac opens several files and a folder as a workspace root"""
    proj = tmp / "proj"
    x = write(proj / "x.py", "x = 1\n")
    f1, f2 = write(tmp / "f1.txt", "1"), write(tmp / "f2.txt", "2")
    try:
        assert nppmac(app, f1, proj, f2).returncode == 0
        wait_open(app, f1, f2)
        app.wait(lambda: current(app)["title"] == "f2.txt", 5, message="f2.txt current")
        roots = app.call("list_documents")["workspace_roots"]
        assert any(App.same_path(r, proj) for r in roots), roots
        assert app.invoke("editor", "workspaceVisible") in (True, 1)
        assert find_doc(app, x) is None
    finally:
        app.invoke("editor", "openFolderAsWorkspace:", [None])


@pytest.mark.case("CLI-004")
def test_cli_004_nppmac_resolves_relative_paths_against_its_working_directory(app, tmp):
    """CLI-004: nppmac resolves relative paths against its working directory"""
    rel = write(tmp / "sub/rel.txt", "rel")
    r = nppmac(app, "sub/rel.txt", f"../{tmp.name}/sub/./rel.txt", cwd=tmp)
    assert r.returncode == 0
    wait_open(app, rel)
    app.idle(0.5)
    tabs = [d for d in app.docs() if d["title"] == "rel.txt"]
    assert len(tabs) == 1
    assert App.same_path(tabs[0]["path"], rel) and os.path.isabs(tabs[0]["path"])
    assert "/./" not in tabs[0]["path"] and "/../" not in tabs[0]["path"]


@pytest.mark.case("CLI-005")
def test_cli_005_nppmac_creates_a_file_that_does_not_exist(app, tmp):
    """CLI-005: nppmac creates a file that does not exist"""
    new = tmp / "brand_new.md"
    r = nppmac(app, new)
    assert r.returncode == 0
    assert new.exists() and new.stat().st_size == 0
    wait_open(app, new)
    app.wait(lambda: current(app)["title"] == "brand_new.md", 5)
    d = app.doc()
    assert app.text() == "" and not d["modified"] and d["language"].lower().startswith("markdown")
    locked = tmp / "locked"
    locked.mkdir()
    os.chmod(locked, 0o555)
    try:
        before = len(app.docs())
        target = locked / "x.txt"
        r = nppmac(app, target)
        assert r.returncode == 0
        assert r.stderr.decode() == f"nppmac: cannot create {target}\n"
        app.idle(0.5)
        assert len(app.docs()) == before and not target.exists()
    finally:
        os.chmod(locked, 0o755)


@pytest.mark.case("CLI-006")
def test_cli_006_nppmac_reads_standard_input_into_a_document(app, tmp):
    """CLI-006: nppmac - reads standard input into a document"""
    text = "piped ☃ text\nline 2\n"
    before = {d["title"] for d in app.docs()}
    r = nppmac(app, "-", input=text.encode("utf-8"))
    assert r.returncode == 0
    d = app.wait(lambda: next((d for d in app.docs() if d["title"] not in before and d["current"]), None), 10,
                 message="the stdin tab")
    assert d["title"].startswith("nppmac-stdin-") and d["title"].endswith(".txt")
    assert d["title"][len("nppmac-stdin-"):-4].isdigit()
    app.wait(lambda: app.text() == text, 5, message="the piped text")
    assert app.doc()["encoding"] == "UTF-8"
    assert os.path.realpath(os.path.dirname(d["path"])) == os.path.realpath(tempfile.gettempdir())
    try:
        os.unlink(d["path"])
    except OSError:
        pass


@pytest.mark.case("CLI-007")
def test_cli_007_nppmac_h_prints_its_usage_and_opens_nothing(app):
    """CLI-007: nppmac -h prints its usage and opens nothing"""
    before = app.docs()
    for flag in ("-h", "--help"):
        r = nppmac(app, flag)
        assert r.returncode == 0
        err = r.stderr.decode()
        assert err.startswith("usage: nppmac [+N] [file|folder ...] [-]")
        assert "+N" in err and "  -  " in err.replace("-      ", "  -  ") and "mcp" in err
    app.idle(0.5)
    assert app.docs() == before


@pytest.mark.case("CLI-008")
def test_cli_008_nppmac_mcp_bridges_an_agent_to_the_running_application(app):
    """CLI-008: nppmac mcp bridges an agent to the running application"""
    env = dict(os.environ, NPPMAC_AGENT_SOCKET=app.socket_path)
    p = subprocess.Popen([str(app.cli), "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, env=env)
    try:
        def ask(message):
            p.stdin.write(mcp_lines(message))
            p.stdin.flush()
            if "id" not in message:
                return None
            return json.loads(p.stdout.readline())
        init = ask({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "cli-test", "version": "1"}}})
        assert init["id"] == 1
        assert init["result"]["serverInfo"]["name"] == "NotepadMac" and init["result"]["protocolVersion"]
        ask({"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools = ask({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = {t["name"] for t in tools["result"]["tools"]}
        product = {"open_document", "get_document", "edit_document", "get_selection", "go_to", "list_documents",
                   "close_document", "save_document", "bookmarks", "list_commands", "run_command",
                   "detect_language", "tokens", "function_list", "find", "replace", "compare",
                   "file_encoding", "ocr", "read_qr", "spell_check"}
        assert product <= names, product - names
        listed = ask({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                      "params": {"name": "list_documents", "arguments": {}}})
        assert listed["result"]["structuredContent"]["documents"] == app.docs()
        p.stdin.close()
        assert p.wait(10) == 0
    finally:
        if p.poll() is None:
            p.kill()
    assert app.running and app.docs()


# ---- Files on the application's command line ----------------------------------

@pytest.mark.case("CLI-009")
def test_cli_009_files_given_at_launch_open_in_the_given_order_the_last_in_fr(launch, app, ltmp):
    """CLI-009: Files given at launch open in the given order, the last in front"""
    tmp = ltmp
    files = [write(tmp / "a.txt", "A"), write(tmp / "b c.txt", "B C"), write(tmp / "z.md", "# Z")]
    launch(files)
    settle(app, lambda ds: named(ds, "a.txt", "b c.txt", "z.md"))
    # Files given at launch take the place of the empty "new 1" (FILE-007, upstream): none is made.
    assert titles(app) == ["a.txt", "b c.txt", "z.md"]
    assert current(app)["title"] == "z.md"
    for f, text in zip(files, ["A", "B C", "# Z"]):
        assert app.text(find_doc(app, f)["index"]) == text


@pytest.mark.case("CLI-010")
def test_cli_010_a_relative_file_argument_is_found_from_the_process_s_working(launch, app):
    """CLI-010: A relative file argument is found from the process's working directory"""
    rel = write(app.work / "cl/rel.txt", "relative")
    relative = os.path.relpath(rel, os.getcwd())
    assert not os.path.isabs(relative)
    launch([relative])
    settle(app, lambda ds: named(ds, "rel.txt"))
    d = find_doc(app, rel)
    assert d and os.path.isabs(d["path"])


@pytest.mark.case("CLI-011")
def test_cli_011_a_file_argument_that_does_not_exist_is_offered_for_creation(launch, app, ltmp):
    """CLI-011: A file argument that does not exist is offered for creation"""
    tmp = ltmp
    nothere, nodir = tmp / "nothere.txt", tmp / "nodir/x.txt"
    launch([nothere, nodir])
    app.idle(1.0)
    log = alerts(app.modal_log())
    create = [e for e in log if e.get("message") == "Create new file"]
    assert create, log
    assert f'"{nothere}" doesn\'t exist. Create it?' in create[0].get("informative", "")
    assert create[0]["buttons"] == ["Yes", "No"]
    assert nothere.exists() and nothere.stat().st_size == 0 and find_doc(app, nothere)
    assert any(e.get("message") == "Cannot open file" for e in log)
    assert find_doc(app, nodir) is None


@pytest.mark.case("CLI-012")
def test_cli_012_a_folder_argument_opens_the_files_under_it_r_and_wildcards(launch, app, ltmp):
    """CLI-012: A folder argument opens the files under it; -r and wildcards"""
    tmp = ltmp
    tree = tmp / "tree"
    a, b, c = write(tree / "a.txt", "a"), write(tree / "sub/b.txt", "b"), write(tree / "c.log", "c")
    launch([tree])
    app.idle(1.0)
    assert all(find_doc(app, f) for f in (a, b, c)), titles(app)
    launch(["-r", tree / "*.txt"])
    settle(app, lambda ds: named(ds, "a.txt", "b.txt"))
    assert find_doc(app, c) is None
    launch([tree / "*.txt"])
    settle(app, lambda ds: named(ds, "a.txt"))
    assert find_doc(app, b) is None and find_doc(app, c) is None
    many = tmp / "many"
    for i in range(201):
        write(many / f"f{i:03}.txt", str(i))
    launch(["-r", many])
    app.idle(1.0)
    log = alerts(app.modal_log())
    assert any(e.get("message") == "Amount of files to open is too large"
               and "201 files are about to be opened. Are you sure to open them?" in e.get("informative", "")
               for e in log), log


@pytest.mark.case("CLI-013")
def test_cli_013_openfoldersasworkspace_puts_the_folders_in_the_workspace_pan(launch, app, ltmp):
    """CLI-013: -openFoldersAsWorkspace puts the folders in the workspace panel"""
    tmp = ltmp
    w1, w2 = tmp / "w1", tmp / "w2"
    f1, f2 = write(w1 / "one.txt", "1"), write(w2 / "two.txt", "2")
    launch(["-openFoldersAsWorkspace", w1, w2])
    app.wait(lambda: len(app.call("list_documents")["workspace_roots"]) >= 2, 10, message="two roots")
    app.idle(0.3)
    roots = [r for r in app.call("list_documents")["workspace_roots"]]
    assert len(roots) == 2 and App.same_path(roots[0], w1) and App.same_path(roots[1], w2), roots
    assert app.invoke("editor", "workspaceVisible") in (True, 1)
    assert find_doc(app, f1) is None and find_doc(app, f2) is None
    assert alerts(app.modal_log()) == []


# ---- Position, language, read-only --------------------------------------------

@pytest.mark.case("CLI-014")
def test_cli_014_n_and_c_put_the_caret_on_a_line_and_column(launch, app, ltmp):
    """CLI-014: -n and -c put the caret on a line and column"""
    tmp = ltmp
    pos = write(tmp / "pos.txt", "one\ntwo\nthree\n")
    launch(["-n2", "-c3", pos])
    settle(app, lambda ds: named(ds, "pos.txt"))
    assert caret(app) == (2, 3, 6)
    launch(["-n99", pos])
    settle(app, lambda ds: named(ds, "pos.txt"))
    assert caret(app)[0] == app.sci(SCI_GETLINECOUNT)
    launch(["-n2", "-c99", pos])
    settle(app, lambda ds: named(ds, "pos.txt"))
    assert caret(app)[:2] == (2, 4)


@pytest.mark.case("CLI-015")
def test_cli_015_p_puts_the_caret_at_a_position(launch, app, ltmp):
    """CLI-015: -p puts the caret at a position"""
    tmp = ltmp
    pos = write(tmp / "pos.txt", "one\ntwo\nthree\n")
    for args in (["-p9", pos], ["-p9", "-n1", pos]):
        launch(args)
        settle(app, lambda ds: named(ds, "pos.txt"))
        assert caret(app) == (3, 2, 9), args


@pytest.mark.case("CLI-016")
def test_cli_016_l_sets_the_language_of_the_files_given(launch, app, ltmp):
    """CLI-016: -l sets the language of the files given"""
    tmp = ltmp
    l1, l2 = write(tmp / "l1.txt", "x = 1"), write(tmp / "l2.txt", "x = 1")
    launch(["-lpython", l1, l2])
    settle(app, lambda ds: named(ds, "l1.txt", "l2.txt"))
    assert find_doc(app, l1)["language"] == "python" and find_doc(app, l2)["language"] == "python"
    assert app.checked("IDM_LANG_PYTHON")
    launch(["-lnosuchlang", l1])
    settle(app, lambda ds: named(ds, "l1.txt"))
    assert find_doc(app, l1)["language"] == "normal"
    assert alerts(app.modal_log()) == []


UDL = """<?xml version="1.0" encoding="UTF-8" ?>
<NotepadPlus>
    <UserLang name="MyLang" ext="myl" udlVersion="2.1">
        <Settings>
            <Global caseIgnored="no" allowFoldOfComments="no" foldCompact="no" forcePureLC="0" decimalSeparator="0" />
            <Prefix Keywords1="no" Keywords2="no" Keywords3="no" Keywords4="no" Keywords5="no" Keywords6="no" Keywords7="no" Keywords8="no" />
        </Settings>
        <KeyWordsList>
            <Keywords name="Keywords1">alpha beta</Keywords>
        </KeyWordsList>
        <Styles>
            <WordsStyle name="DEFAULT" fgColor="000000" bgColor="FFFFFF" fontName="" fontStyle="0" nesting="0" />
            <WordsStyle name="KEYWORDS1" fgColor="0000FF" bgColor="FFFFFF" fontName="" fontStyle="1" nesting="0" />
        </Styles>
    </UserLang>
</NotepadPlus>
"""


@pytest.mark.case("CLI-017")
def test_cli_017_udl_picks_a_user_defined_language(launch, app, ltmp):
    """CLI-017: -udl= picks a user defined language"""
    tmp = ltmp
    u = write(tmp / "u.txt", "alpha gamma\n")
    app.stop()
    write(support(app) / "userDefineLang.xml", UDL)
    launch(["-udl=MyLang", u], clean_home=False)
    settle(app, lambda ds: named(ds, "u.txt"))
    d = find_doc(app, u)
    assert d["language"] == "MyLang" or d["language_title"] == "MyLang", d
    tree = app.menu_tree("Language", depth=2)

    def items(node):
        for it in node if isinstance(node, list) else node.get("items", []):
            yield it
            yield from items(it.get("items", []))
    mine = [it for it in items(tree) if it.get("title") == "MyLang"]
    assert mine and mine[0]["checked"], mine


@pytest.mark.case("CLI-018")
def test_cli_018_ro_and_the_full_read_only_switches_open_the_files_read_only(launch, app, ltmp):
    """CLI-018: -ro and the full read-only switches open the files read-only"""
    tmp = ltmp
    r1, r2 = write(tmp / "r1.txt", "first\n"), write(tmp / "r2.txt", "second\n")
    modes = {f: stat.S_IMODE(os.stat(f).st_mode) for f in (r1, r2)}
    for switch in ("-ro", "-fullReadOnly", "-fullReadOnlySavingForbidden"):
        launch([switch, r1, r2])
        settle(app, lambda ds: named(ds, "r1.txt", "r2.txt"))
        app.wait(lambda: current(app)["title"] == "r2.txt", 5)
        app.type("X")
        app.idle(0.2)
        assert app.text() == "second\n", switch
        for f in (r2, r1):
            front(app, f)
            assert read_only(app) and app.doc()["read_only"], (switch, f.name)
        assert r1.read_text() == "first\n" and r2.read_text() == "second\n"
        assert all(stat.S_IMODE(os.stat(f).st_mode) == m for f, m in modes.items())
        assert os.access(r1, os.W_OK) and os.access(r2, os.W_OK)


@pytest.mark.case("CLI-019")
def test_cli_019_monitor_watches_every_file_given(launch, app, ltmp):
    """CLI-019: -monitor watches every file given"""
    tmp = ltmp
    m1, m2 = write(tmp / "m1.log", "start 1\n"), write(tmp / "m2.log", "start 2\n")
    launch(["-monitor", m1, m2])
    settle(app, lambda ds: named(ds, "m1.log", "m2.log"))
    app.wait(lambda: current(app)["title"] == "m2.log", 5)
    for f in (m1, m2):
        assert find_doc(app, f)["read_only"], f.name
    checks = [app.checked("IDM_VIEW_MONITORING")]
    with open(m2, "a") as fh:
        fh.write("new\n")
    app.wait(lambda: app.text() == "start 2\nnew\n", 10, message="m2.log's appended line")
    app.wait(lambda: caret(app)[2] == app.sci(SCI_GETLENGTH), 5, message="caret at the end")
    front(app, m1)
    checks.append(app.checked("IDM_VIEW_MONITORING"))
    with open(m1, "a") as fh:
        fh.write("new\n")
    app.wait(lambda: app.text() == "start 1\nnew\n", 10, message="m1.log's appended line")
    app.wait(lambda: caret(app)[2] == app.sci(SCI_GETLENGTH), 5, message="caret at the end")
    assert checks == [True, True]


# ---- Sessions ----------------------------------------------------------------

@pytest.mark.case("CLI-020")
def test_cli_020_nosession_neither_restores_nor_overwrites_the_session(launch, app, ltmp):
    """CLI-020: -nosession neither restores nor overwrites the session"""
    tmp = ltmp
    s, t = write(tmp / "s.txt", "s"), write(tmp / "t.txt", "t")
    launch(session=True, defaults={"restoreSession": True})
    app.open(s)
    app.stop()
    session = support(app) / "session.xml"
    assert session.exists() and "s.txt" in session.read_text()
    before, mtime = session.read_bytes(), session.stat().st_mtime_ns
    launch(["-nosession"], session=True, clean_home=False, reset=False)
    app.idle(1.0)
    assert find_doc(app, s) is None, titles(app)
    app.open(t)
    app.stop()
    assert session.read_bytes() == before and session.stat().st_mtime_ns == mtime


def save_session(app, path):
    app.answers(panels=[str(path)])
    app.run("IDM_FILE_SAVESESSION")
    app.wait(lambda: Path(path).exists(), 5, message="the session file")


@pytest.mark.case("CLI-021")
def test_cli_021_opensession_loads_the_files_given_as_sessions(launch, app, ltmp):
    """CLI-021: -openSession loads the files given as sessions"""
    tmp = ltmp
    o1, o2 = write(tmp / "o1.txt", "first\n"), write(tmp / "o2.txt", "second\n")
    sess = tmp / "sess.xml"
    app.open(o1)
    app.open(o2)
    app.sci(SCI_GOTOPOS, 3)
    save_session(app, sess)
    launch(["-openSession", sess])
    settle(app, lambda ds: named(ds, "o1.txt", "o2.txt"))
    assert current(app)["title"] == "o2.txt"
    assert caret(app)[2] == 3
    assert find_doc(app, sess) is None, titles(app)


@pytest.mark.case("CLI-022")
def test_cli_022_files_given_at_launch_open_after_the_restored_session(launch, app, ltmp):
    """CLI-022: Files given at launch open after the restored session"""
    tmp = ltmp
    old, given = write(tmp / "old1.txt", "old"), write(tmp / "given.txt", "given")
    launch(session=True, defaults={"restoreSession": True})
    app.open(old)
    app.stop()
    launch([given], session=True, clean_home=False, reset=False)
    settle(app, lambda ds: named(ds, "old1.txt", "given.txt"))
    assert current(app)["title"] == "given.txt"


# ---- Window and new-text switches ------------------------------------------------

def rect(value):
    """NSRect: {{x, y}, {w, h}} -> (x, y, w, h)."""
    nums = [float(n) for n in value.replace("NSRect:", "").replace("{", " ").replace("}", " ").replace(",", " ").split()]
    return tuple(nums)


@pytest.mark.case("CLI-023")
def test_cli_023_titleadd_alwaysontop_x_and_y_shape_the_window(launch, app, ltmp):
    """CLI-023: -titleAdd=, -alwaysOnTop, -x and -y shape the window"""
    tmp = ltmp
    t = write(tmp / "t.txt", "t")
    launch(["-titleAdd=Here", "-alwaysOnTop", "-x40", "-y60", t])
    settle(app, lambda ds: named(ds, "t.txt"))
    app.wait(lambda: app.get("window", "title") == f"t.txt — {tmp} - Here", 5, message="the title")
    app.run("IDM_FILE_NEW")
    app.wait(lambda: app.get("window", "title").endswith(" - Here"), 5, message="the suffix kept")
    assert app.get("window", "level") == 3
    x, y, w, h = rect(app.get("window", "frame"))
    sx, sy, sw, sh = rect(app.get("window", "screen.frame"))
    assert x == sx + 40 and y + h == sy + sh - 60, (x, y, w, h, sx, sy, sw, sh)
    assert app.checked("IDM_VIEW_ALWAYSONTOP")


@pytest.mark.case("CLI-024")
def test_cli_024_notabbar_hides_the_tab_bar_only(launch, app, ltmp):
    """CLI-024: -notabbar hides the tab bar only"""
    tmp = ltmp
    # e2e_ui does not answer with this build (harness gap), so the views are read by key path.
    a, b = write(tmp / "a.txt", "a"), write(tmp / "b.txt", "b")
    launch(["-notabbar", a, b])
    settle(app, lambda ds: named(ds, "a.txt", "b.txt"))
    assert app.get("editor", "tabBar.hidden") in (True, 1)
    before = current(app)["title"]
    app.run("IDM_VIEW_TAB_NEXT")
    assert current(app)["title"] != before
    assert app.get("editor", "statusField.hidden") in (False, 0)


@pytest.mark.case("CLI-025")
def test_cli_025_qt_and_qf_open_a_new_document_holding_a_text(launch, app, ltmp):
    """CLI-025: -qt= and -qf= open a new document holding a text"""
    tmp = ltmp
    launch(["-qt=quoted ☃ text"])
    app.wait(lambda: app.text() == "quoted ☃ text", 10, message="the quoted text")
    d = app.doc()
    assert d["path"] is None and d["current"]
    assert app.sci(SCI_CANUNDO) == 0
    q = write(tmp / "q.txt", "from a file\nline 2\n")
    launch(["-qf=" + str(q)])
    app.wait(lambda: app.text() == "from a file\nline 2\n", 10, message="the file's text")
    assert app.doc()["path"] is None
    app.idle(0.3)
    assert find_doc(app, q) is None


@pytest.mark.case("CLI-026")
def test_cli_026_notepadstylecmdline_takes_the_rest_of_the_line_as_one_file_n(launch, app, ltmp):
    """CLI-026: -notepadStyleCmdline takes the rest of the line as one file name"""
    tmp = ltmp
    f = write(tmp / "my file name.txt", "spaced")
    write(tmp / "my", "decoy")
    launch(["-notepadStyleCmdline", tmp / "my", "file", "name.txt"])
    settle(app, lambda ds: named(ds, "my file name.txt"))
    assert app.text(find_doc(app, f)["index"]) == "spaced"
    assert titles(app) == ["my file name.txt"]
    assert alerts(app.modal_log()) == []


@pytest.mark.case("CLI-027")
def test_cli_027_z_skips_the_argument_that_follows_it(launch, app, ltmp):
    """CLI-027: -z skips the argument that follows it"""
    tmp = ltmp
    skipped, kept = write(tmp / "skipped.txt", "s"), write(tmp / "kept.txt", "k")
    launch(["-z", skipped, kept])
    settle(app, lambda ds: named(ds, "kept.txt"))
    assert find_doc(app, skipped) is None, titles(app)


@pytest.mark.case("CLI-028")
def test_cli_028_settingsdir_keeps_this_launch_s_settings_in_that_folder(launch, app, ltmp):
    """CLI-028: -settingsDir= keeps this launch's settings in that folder"""
    tmp = ltmp
    cfg = tmp / "cfg"
    launch(["-settingsDir=" + str(cfg)])
    home_menu = support(app) / "contextMenu.xml"
    assert not home_menu.exists()
    app.call("e2e_menu", context="editor")
    app.wait(lambda: (cfg / "contextMenu.xml").exists(), 5, message="contextMenu.xml in the settings folder")
    assert not home_menu.exists()
    app.run("IDM_DEBUGINFO")
    # The text the Debug Info window shows (e2e_ui does not answer with this build: harness gap).
    assert "Local Conf mode: ON" in app.invoke("editor", "debugInfo")


# ---- Switches that do one job and quit, and ignored ones -------------------------

@pytest.mark.case("CLI-029")
def test_cli_029_export_functionlist_writes_each_file_s_function_list_as_json(launch, app, ltmp):
    """CLI-029: -export=functionList writes each file's function list as JSON and quits"""
    tmp = ltmp
    f = write(tmp / "f.cpp", "class Shape {\npublic:\n  int area() { return 0; }\n};\nint helper(int a) { return a; }\n")
    old = write(tmp / "old.txt", "old")
    launch(session=True, defaults={"restoreSession": True})
    app.open(old)
    app.stop()
    session = support(app) / "session.xml"
    assert session.exists()
    before, mtime = session.read_bytes(), session.stat().st_mtime_ns
    rc, took = run_executable(app, ["-export=functionList", f])
    assert rc == 0 and took < 10
    result = tmp / "f.cpp.result.json"
    assert result.read_text() == '{"leaves":["helper"],"nodes":[{"leaves":["area"],"name":"Shape"}],"root":"f.cpp"}'
    assert session.read_bytes() == before and session.stat().st_mtime_ns == mtime


@pytest.mark.case("CLI-030")
def test_cli_030_quickprint_prints_the_files_given_and_quits(launch, app, ltmp):
    """CLI-030: -quickPrint prints the files given and quits"""
    tmp = ltmp
    # The print hook covers NSPrintOperation's concrete subclass too (E2EHookPrinting); the guard below
    # still refuses to run against a build without it.
    if subprocess.run(["lpstat", "-p"], capture_output=True, text=True).stdout.strip():
        pytest.skip("a printer is set up on this machine: print tests run only in the VM")
    assert PRINT_GUARD in app.executable.read_bytes(), "the build has no print guard: not printing"
    assert raw_env(app)["NPPMAC_E2E"] == "1"
    p = write(tmp / "p.txt", "quick print body\n")
    app.stop()
    for old in app.print_dir.glob("*.pdf"):
        old.unlink()
    session = support(app) / "session.xml"
    had_session = session.exists()
    rc, took = run_executable(app, ["-quickPrint", p])
    assert rc == 0 and took < 10
    pdfs = sorted(app.print_dir.glob("*.pdf"))
    assert len(pdfs) == 1, pdfs
    assert "quick print body" in pdf_text(pdfs[0])
    assert session.exists() == had_session


@pytest.mark.case("CLI-031")
def test_cli_031_switches_the_port_does_not_need_are_accepted_and_ignored(launch, app, ltmp):
    """CLI-031: Switches the port does not need are accepted and ignored"""
    tmp = ltmp
    i = write(tmp / "i.txt", "ignored switches")
    size = app.log_path.stat().st_size if app.log_path.exists() else 0
    launch(["-multiInst", "-noPlugin", "-systemtray", "-loadingTime", '-pluginMessage="hello"', i])
    settle(app, lambda ds: named(ds, "i.txt"))
    assert current(app)["title"] == "i.txt"
    assert titles(app) == ["i.txt"]   # it took the lone clean "new 1"'s place (FILE-007)
    assert alerts(app.modal_log()) == []
    with open(app.log_path, "rb") as fh:
        fh.seek(size)
        log = fh.read().decode("utf-8", "replace")
    assert "NotepadMac: -pluginMessage ignored, plugins are not supported: hello\n" in log
