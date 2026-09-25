"""SESSION: end-to-end tests (plan: plan/SESSION.md)."""
import os
import xml.etree.ElementTree as ET
import re
import time

import pytest

from harness.sci import *  # noqa: F401,F403
from _util_session import (App, alerts, backup_dir, backups, caret_anchor, doc_named, file_entry, files_of,
                           find_doc, front, kill_app, load_session, marks, names, parse, quit_app, relaunch,
                           save_session, session_xml, support, with_session, write)

A_PY = "import os\nx = 1\ny = 2\nprint(x)\n"
B_CPP = "int f() {\n  return 1;\n}\n"


def _rect_height(value) -> float:
    """'NSRect: {{x, y}, {w, h}}' -> h."""
    nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", str(value))]
    return nums[3]


def _rect_extent(value, along_width: bool) -> float:
    """'NSRect: {{x, y}, {w, h}}' -> w or h."""
    nums = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", str(value))]
    return nums[2] if along_width else nums[3]


def _main_share(app) -> float:
    """The first view's share along the split's axis: the views sit side by side (a vertical
    divider, NSSplitView.vertical) as upstream's POS_VERTICAL, or one above the other."""
    side = bool(app.get("editor", "editorSplit.vertical"))
    return (_rect_extent(app.get("editor", "sciView.frame"), side) /
            _rect_extent(app.get("editor", "editorSplit.frame"), side))


def _bookmarks(app, document=None) -> list:
    args = {} if document is None else {"document": document}
    return app.call("bookmarks", **args)["bookmarked_lines"]


def _close(app, path):
    d = find_doc(app, path)
    assert d, f"{path} is not open"
    app.call("close_document", document=d["index"], discard_changes=True)


def _build_001(app, tmp):
    """The state of SESSION-001: a.py with a selection and bookmarks; b.cpp folded, pinned,
    coloured and read-only; a.py in front."""
    a = write(tmp / "a.py", A_PY)
    b = write(tmp / "b.cpp", B_CPP)
    app.open(a)
    app.select(2, 3, 2, 6)
    app.call("bookmarks", add=[1, 3])
    app.open(b)
    app.sci(SCI_FOLDLINE, 0, 0)   # SC_FOLDACTION_CONTRACT
    app.run("File|Pin Tab")
    app.run("IDM_VIEW_TAB_COLOUR_3")
    app.run("IDM_EDIT_TOGGLEREADONLY")
    front(app, a)
    return a, b


def _untitled(app, text) -> str:
    """A new tab typed into as a user would (the MCP's open_document text makes a clean tab)."""
    app.run("IDM_FILE_NEW")
    app.type(text)
    app.wait(lambda: app.text() == text and app.doc()["modified"], 5, message="the typed untitled tab")
    return app.doc()["title"]


# ---- Save Session and Load Session ------------------------------------------------------------

@pytest.mark.case("SESSION-001")
def test_session_001_save_session_writes_notepad_s_session_xml(app, tmp):
    """SESSION-001: Save Session writes Notepad++'s session.xml"""
    a, b = _build_001(app, tmp)
    anchor, caret = caret_anchor(app)
    assert (anchor, caret) == (len("import os\n") + 2, len("import os\n") + 5)
    log = save_session(app, tmp / "s.xml")
    assert [e["kind"] for e in log] == ["save"]
    root = parse(tmp / "s.xml")
    assert root.tag == "NotepadPlus"
    sess = root.find("Session")
    assert sess.get("activeView") == "0"
    main = sess.find("mainView")
    files = files_of(root)
    paths = [f.get("filename") for f in files]
    # One File per open file, in tab order; the clean untitled tab is left out.
    open_paths = [d["path"] for d in app.docs() if d["path"]]
    assert len(paths) == len(open_paths) == 2
    assert all(App.same_path(p, q) for p, q in zip(paths, open_paths))
    ia = next(i for i, p in enumerate(paths) if App.same_path(p, a))
    assert main.get("activeIndex") == str(ia)
    sub = sess.find("subView")
    assert sub is not None and sub.get("activeIndex") == "0" and not sub.findall("File")
    fa, fb = file_entry(root, a), file_entry(root, b)
    assert fa.get("lang") == "Python"
    assert (fa.get("startPos"), fa.get("endPos")) == (str(anchor), str(caret))
    assert fa.get("encoding") == "-1"
    assert (fa.get("userReadOnly"), fa.get("tabPinned"), fa.get("tabColourId")) == ("no", "no", "-1")
    assert marks(fa) == [0, 2]
    assert fb.get("lang") == "C++"
    assert (fb.get("tabPinned"), fb.get("tabColourId"), fb.get("userReadOnly")) == ("yes", "2", "yes")
    assert marks(fb, "Fold") == [0]
    for f in (fa, fb):
        for attr in ("macLanguage", "macEncoding", "macBOM", "macEOL", "macMonitoring"):
            assert f.get(attr) is not None, attr


@pytest.mark.case("SESSION-002")
def test_session_002_load_session_brings_every_file_back_as_it_was(app, tmp):
    """SESSION-002: Load Session brings every file back as it was"""
    a, b = _build_001(app, tmp)
    save_session(app, tmp / "s.xml")
    saved_order = [f.get("filename") for f in files_of(parse(tmp / "s.xml"))]
    app.close_all()
    load_session(app, tmp / "s.xml")
    opened = [d["path"] for d in app.docs() if d["path"]]
    assert len(opened) == 2 and all(App.same_path(p, q) for p, q in zip(opened, saved_order))
    cur = app.doc()
    assert App.same_path(cur["path"], a)
    assert cur["language"] == "python" and not cur["modified"]
    line2 = len("import os\n")
    assert caret_anchor(app) == (line2 + 2, line2 + 5)
    assert _bookmarks(app) == [1, 3]
    front(app, b)
    d = app.doc()
    assert d["language"] == "cpp" and not d["modified"]
    assert d.get("pinned") is True
    assert app.get("document", "tabColour") == 3
    assert app.sci(SCI_GETREADONLY) == 1
    assert app.sci(SCI_GETFOLDEXPANDED, 0) == 0
    assert app.sci(SCI_GETLINEVISIBLE, 1) == 0 and app.sci(SCI_GETLINEVISIBLE, 2) == 0


@pytest.mark.case("SESSION-003")
def test_session_003_the_active_tab_is_found_by_path_whatever_is_open_before(app, tmp):
    """SESSION-003: The active tab is found by path, whatever is open before"""
    u1 = app.new("scratch one")
    s1, s2 = write(tmp / "s1.txt", "one\n"), write(tmp / "s2.txt", "two\n")
    app.open(s1)
    app.open(s2)
    front(app, s1)
    save_session(app, tmp / "s.xml")
    _close(app, s1)
    _close(app, s2)
    app.new("scratch two")
    app.new("scratch three")
    before = {d["title"]: app.text(d["index"]) for d in app.docs() if not d["path"]}
    load_session(app, tmp / "s.xml")
    assert App.same_path(app.doc()["path"], s1)
    after = {d["title"]: app.text(d["index"]) for d in app.docs() if not d["path"]}
    assert after == before
    assert "scratch one" in before.values() and u1 is not None


@pytest.mark.case("SESSION-004")
def test_session_004_loading_a_session_skips_files_that_no_longer_exist(app, tmp):
    """SESSION-004: Loading a session skips files that no longer exist"""
    ks = [write(tmp / f"k{i}.txt", f"k{i}\n") for i in (1, 2, 3)]
    for k in ks:
        app.open(k)
    save_session(app, tmp / "s.xml")
    app.close_all()
    ks[1].unlink()
    log = load_session(app, tmp / "s.xml")
    assert find_doc(app, ks[0]) and find_doc(app, ks[2])
    assert find_doc(app, ks[1]) is None and "k2.txt" not in names(app)
    assert not alerts(log)
    assert not ks[1].exists()


@pytest.mark.case("SESSION-005")
def test_session_005_a_session_xml_written_by_notepad_on_windows_is_read(app, tmp):
    """SESSION-005: A session.xml written by Notepad++ on Windows is read"""
    real = write(tmp / "real.cpp", "int main() {\n  return 0;\n}\n")
    common = ('firstVisibleLine="0" xOffset="0" scrollWidth="1" selMode="0" offset="0" wrapCount="1" '
              'RTL="no" untitleTabRenamed="no" backupFilePath="" originalFileLastModifTimestamp="0" '
              'originalFileLastModifTimestampHigh="0"')
    xml = f'''<?xml version="1.0" encoding="UTF-8" ?>
<NotepadPlus>
    <Session activeView="0">
        <mainView activeIndex="1">
            <File {common} startPos="0" endPos="0" lang="Python" encoding="-1" userReadOnly="no" filename="C:\\Users\\someone\\gone.py" tabColourId="-1" tabPinned="no" />
            <File {common} startPos="3" endPos="7" lang="C++" encoding="-1" userReadOnly="yes" filename="{real}" tabColourId="2" tabPinned="yes">
                <Mark line="1" />
            </File>
        </mainView>
        <subView activeIndex="0" />
    </Session>
</NotepadPlus>
'''
    write(tmp / "win.xml", xml.replace("\n", "\r\n"))
    log = load_session(app, tmp / "win.xml")
    assert not alerts(log)
    assert [d for d in app.docs() if d["path"] and "gone" in d["path"]] == []
    assert "gone.py" not in names(app)
    d = app.doc()
    assert App.same_path(d["path"], real)
    assert d["language"] == "cpp"
    assert caret_anchor(app) == (3, 7)
    assert d.get("pinned") is True
    assert app.get("document", "tabColour") == 3
    assert app.sci(SCI_GETREADONLY) == 1
    assert _bookmarks(app) == [2]


@pytest.mark.case("SESSION-006")
def test_session_006_a_cancelled_load_session_and_a_file_that_is_not_a_session_ch(app, tmp):
    """SESSION-006: A cancelled Load Session and a file that is not a session change nothing"""
    f = write(tmp / "keep.txt", "keep\n")
    app.open(f)
    before = [(d["title"], d["path"]) for d in app.docs()]
    app.answers(panels=[None], clear=True)
    app.run("IDM_FILE_LOADSESSION")
    log = app.modal_log()
    assert [(e["kind"], e["answered"]) for e in log] == [("open", "cancel")]
    assert [(d["title"], d["path"]) for d in app.docs()] == before
    ns = write(tmp / "not_session.txt", "hello")
    log = load_session(app, ns, alerts_=[1])
    assert [(d["title"], d["path"]) for d in app.docs()] == before
    assert find_doc(app, ns) is None
    assert len(alerts(log)) == 1


@pytest.mark.case("SESSION-007")
def test_session_007_the_session_keeps_the_second_view_and_the_folder_as_workspac(app, tmp):
    """SESSION-007: The session keeps the second view and the Folder as Workspace roots"""
    v = write(tmp / "v.txt", "".join(f"line {i}\n" for i in range(1, 201)))   # longer than a full-height view
    ra, rb = tmp / "rootA", tmp / "rootB"
    write(ra / "a.txt", "a")
    write(rb / "b.txt", "b")
    app.open(v)
    try:
        app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
        app.wait(lambda: app.get("editor", "secondaryViewVisible"), 5, message="the second view")
        app.sci(SCI_SETFIRSTVISIBLELINE, 19, view="sub")
        app.wait(lambda: app.sci(SCI_GETFIRSTVISIBLELINE, view="sub") == 19, 5, message="the sub view scrolled")
        share = _main_share(app)
        app.call("open_document", path=str(ra))
        app.call("open_document", path=str(rb))
        save_session(app, tmp / "s.xml")
        root = parse(tmp / "s.xml")
        sub = root.find("Session").find("subView")
        sf = file_entry(root, v, view="subView")
        assert sf is not None and sf.get("firstVisibleLine") == "19"
        assert abs(float(sub.get("macSplit")) - share) <= 0.02
        folders = [r.get("foldername") for r in root.find("Session").find("FileBrowser").findall("root")]
        assert len(folders) == 2 and App.same_path(folders[0], ra) and App.same_path(folders[1], rb)

        app.invoke("editor", "setSecondaryViewVisible:", [False])
        app.invoke("editor", "openFolderAsWorkspace:", [None])
        app.close_all()
        assert not app.get("editor", "secondaryViewVisible")
        load_session(app, tmp / "s.xml")
        app.wait(lambda: app.get("editor", "secondaryViewVisible"), 5, message="the second view back")
        assert App.same_path(app.get("editor", "secondaryDocument.path"), v)
        assert abs(_main_share(app) - share) <= 0.05
        roots = app.call("list_documents")["workspace_roots"]
        assert len(roots) == 2 and App.same_path(roots[0], ra) and App.same_path(roots[1], rb)
    finally:
        app.invoke("editor", "setSecondaryViewVisible:", [False])
        app.invoke("editor", "openFolderAsWorkspace:", [None])


@pytest.mark.case("SESSION-007")
def test_session_007_the_second_view_comes_back_at_its_first_visible_line(app, tmp):
    """SESSION-007: after loading, the second view shows v.txt from line 20 (first visible line 19)."""
    v = write(tmp / "v.txt", "".join(f"line {i}\n" for i in range(1, 201)))   # longer than a full-height view
    app.open(v)
    try:
        app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
        app.wait(lambda: app.get("editor", "secondaryViewVisible"), 5, message="the second view")
        app.sci(SCI_SETFIRSTVISIBLELINE, 19, view="sub")
        app.wait(lambda: app.sci(SCI_GETFIRSTVISIBLELINE, view="sub") == 19, 5, message="the sub view scrolled")
        save_session(app, tmp / "s.xml")
        assert file_entry(parse(tmp / "s.xml"), v, view="subView").get("firstVisibleLine") == "19"
        app.invoke("editor", "setSecondaryViewVisible:", [False])
        app.close_all()
        load_session(app, tmp / "s.xml")
        app.wait(lambda: app.get("editor", "secondaryViewVisible"), 5, message="the second view back")
        app.wait(lambda: app.sci(SCI_GETFIRSTVISIBLELINE, view="sub") == 19, 3,
                 message="the second view at first visible line 19")
    finally:
        app.invoke("editor", "setSecondaryViewVisible:", [False])


@pytest.mark.case("SESSION-008")
def test_session_008_the_session_keeps_a_chosen_code_page_and_monitoring(app, tmp):
    """SESSION-008: The session keeps a chosen code page and monitoring"""
    koi = write(tmp / "koi.txt", "Привет, мир\n".encode("koi8_r"))
    tail = write(tmp / "tail.log", "start\n")
    app.open(koi)
    app.run("IDM_FORMAT_KOI8R_CYRILLIC")
    app.open(tail)
    app.run("IDM_VIEW_MONITORING")
    try:
        save_session(app, tmp / "s.xml")
        root = parse(tmp / "s.xml")
        assert file_entry(root, koi).get("encoding") == "20866"
        assert file_entry(root, tail).get("macMonitoring") == "yes"
        app.close_all()
        load_session(app, tmp / "s.xml")
        front(app, koi)
        d = app.doc()
        assert app.text() == "Привет, мир\n"
        assert d["encoding"].lower() in ("cp20866", "koi8-r") and not d["modified"]
        front(app, tail)
        assert app.get("document", "monitoring") in (True, 1)
        assert app.doc()["read_only"]
        with open(tail, "a") as h:
            h.write("more\n")
        app.wait(lambda: "more" in app.text(), timeout=10, message="the monitored file's new line")
    finally:
        d = find_doc(app, tail)
        if d:
            front(app, tail)
            if app.get("document", "monitoring"):
                app.run("IDM_VIEW_MONITORING")


@pytest.mark.case("SESSION-009")
def test_session_009_loading_a_session_adds_to_the_open_tabs_without_duplicating(app, tmp):
    """SESSION-009: Loading a session adds to the open tabs without duplicating"""
    l1, l2, l3 = (write(tmp / f"l{i}.txt", f"l{i}\n") for i in (1, 2, 3))
    app.open(l1)
    app.open(l2)
    save_session(app, tmp / "s.xml")
    _close(app, l2)
    app.open(l3)
    load_session(app, tmp / "s.xml")
    t = names(app)
    assert t.count("l1.txt") == 1 and t.count("l2.txt") == 1 and t.count("l3.txt") == 1


@pytest.mark.case("SESSION-010")
def test_session_010_the_save_and_load_session_panels_speak_of_session_files(app):
    """SESSION-010: The Save and Load Session panels speak of session files"""
    try:
        app.answers(panels=[None], clear=True)
        app.run("IDM_FILE_SAVESESSION")
        plain = [e for e in app.modal_log() if e["kind"] == "save"][0]
        app.set_prefs(sessionFileExtension="npps")
        app.answers(panels=[None], clear=True)
        app.run("IDM_FILE_SAVESESSION")
        with_ext = [e for e in app.modal_log() if e["kind"] == "save"][0]
        app.answers(panels=[None], clear=True)
        app.run("IDM_FILE_LOADSESSION")
        load = [e for e in app.modal_log() if e["kind"] == "open"][0]
    finally:
        app.set_prefs(sessionFileExtension="")
    assert not plain["name"].endswith(".json")
    assert with_ext["name"].endswith(".npps")
    types = [t.lower().lstrip(".") for t in (load.get("allowed_types") or [])]
    assert not types or ("xml" in types and "npps" in types)


# ---- Session on restart -----------------------------------------------------------------------

@pytest.mark.case("SESSION-011")
@pytest.mark.restart
def test_session_011_quitting_writes_the_session_and_the_next_launch_restores_it(app, tmp):
    """SESSION-011: Quitting writes the session and the next launch restores it"""
    r1 = write(tmp / "r1.py", "a = 1\nb = 2\nc = 3\nd = 4\n")
    r2 = write(tmp / "r2.txt", "two\n")
    with with_session(app):
        app.open(r1)
        app.open(r2)
        front(app, r1)
        app.select(3, 2)
        app.call("bookmarks", add=[2])
        front(app, r2)
        front(app, r1)
        assert quit_app(app) == 0
        sx = session_xml(app)
        assert sx.exists()
        root = parse(sx)
        paths = [f.get("filename") for f in files_of(root)]
        assert len(paths) == 2 and App.same_path(paths[0], r1) and App.same_path(paths[1], r2)
        assert root.find("Session").find("mainView").get("activeIndex") == "0"
        relaunch(app)
        opened = [d["path"] for d in app.docs() if d["path"]]
        assert len(opened) == 2 and App.same_path(opened[0], r1) and App.same_path(opened[1], r2)
        d = app.doc()
        assert App.same_path(d["path"], r1) and d["language"] == "python" and not d["modified"]
        sel = app.selection()
        assert (sel["start"], sel["end"]) == (sel["end"], sel["start"]) and \
            (sel["end"]["line"], sel["end"]["column"]) == (3, 2), sel
        assert _bookmarks(app) == [2]
        assert not doc_named(app, "r2.txt")["modified"]


@pytest.mark.case("SESSION-012")
@pytest.mark.restart
def test_session_012_unsaved_edits_are_asked_about_at_quit_when_there_is_no_snaps(app, tmp):
    """SESSION-012: Unsaved edits are asked about at quit when there is no snapshot"""
    e = write(tmp / "e.txt", "disk")
    with with_session(app, autosaveEnabled=False):
        app.open(e)
        app.set_text("edited")
        _untitled(app, "note")
        app.modal_log(clear=True)
        app.answers(alerts=[2, 2], clear=True)
        try:
            app.invoke("nsapp", "terminate:", [None], timeout=5)
        except Exception:  # noqa: BLE001 - the connection goes with the app
            pass
        # The log goes with the process; the next test counts the questions.
        rc = app.proc.wait(15)
        assert rc == 0
        app.conn = None
        app.proc = None
        assert e.read_text() == "disk"
        relaunch(app)
        d = find_doc(app, e)
        assert d and app.text(d["index"]) == "disk" and not d["modified"]
        assert all(app.text(x["index"]) != "note" for x in app.docs())


@pytest.mark.case("SESSION-012")
@pytest.mark.restart
def test_session_012_the_quit_asks_once_per_modified_document(app, tmp):
    """SESSION-012: two Save alerts, one per modified document (answered Cancel, then the log is read)."""
    e = write(tmp / "e.txt", "disk")
    with with_session(app, autosaveEnabled=False):
        app.open(e)
        app.set_text("edited")
        _untitled(app, "note")
        app.modal_log(clear=True)
        # Don't save the first, cancel at the second: the application stays and its log can be read.
        app.answers(alerts=[2, 3], clear=True)
        app.invoke("nsapp", "terminate:", [None], timeout=10)
        assert app.running
        shown = alerts(app.modal_log())
        assert len(shown) == 2, shown


@pytest.mark.case("SESSION-013")
@pytest.mark.restart
def test_session_013_files_removed_between_two_launches_are_left_out_quietly(app, tmp):
    """SESSION-013: Files removed between two launches are left out quietly"""
    stay, vanish = write(tmp / "stay.txt", "stay\n"), write(tmp / "vanish.txt", "vanish\n")
    with with_session(app):
        app.open(stay)
        app.open(vanish)
        assert quit_app(app) == 0
        vanish.unlink()
        relaunch(app)
        assert find_doc(app, stay)
        assert find_doc(app, vanish) is None and "vanish.txt" not in names(app)
        assert not alerts(app.modal_log())
        assert not vanish.exists()


@pytest.mark.case("SESSION-014")
@pytest.mark.restart
def test_session_014_the_second_view_and_workspace_roots_come_back_after_a_restar(app, tmp):
    """SESSION-014: The second view and workspace roots come back after a restart"""
    w = write(tmp / "w.txt", "".join(f"w {i}\n" for i in range(20)))
    ws = tmp / "wsroot"
    write(ws / "x.txt", "x")
    with with_session(app):
        app.open(w)
        app.run("IDM_VIEW_CLONE_TO_ANOTHER_VIEW")
        app.wait(lambda: app.get("editor", "secondaryViewVisible"), 5, message="the second view")
        app.call("open_document", path=str(ws))
        assert quit_app(app) == 0
        relaunch(app)
        app.wait(lambda: app.get("editor", "secondaryViewVisible"), 5, message="the second view back")
        assert App.same_path(app.get("editor", "secondaryDocument.path"), w)
        roots = app.call("list_documents")["workspace_roots"]
        assert len(roots) == 1 and App.same_path(roots[0], ws)
        assert app.invoke("editor", "workspaceVisible") in (True, 1)


@pytest.mark.case("SESSION-015")
@pytest.mark.restart
def test_session_015_a_session_json_from_an_earlier_build_is_taken_over_once(app, tmp):
    """SESSION-015: A session.json from an earlier build is taken over once"""
    import json
    old = write(tmp / "old.txt", "hello world\n")
    with with_session(app):
        app.stop(graceful=False)
        js = support(app) / "session.json"
        js.write_text(json.dumps({"version": 2, "files": [{"path": str(old), "caret": 2, "language": "normal"}],
                                  "currentPath": str(old), "unsaved": []}))
        app.start(session=True, clean_home=False, defaults={"restoreSession": True})
        d = find_doc(app, old)
        assert d and d["current"]
        assert app.sci(SCI_GETCURRENTPOS) == 2
        assert quit_app(app) == 0
        assert not js.exists()
        sx = session_xml(app)
        assert sx.exists()
        root = parse(sx)
        assert root.tag == "NotepadPlus" and file_entry(root, old) is not None


# ---- Snapshot and periodic backup ---------------------------------------------------------------

BACKUP_NAME = r"@\d{4}-\d{2}-\d{2}_\d{6}(-\d+)?$"


def _backup_of(app, stem):
    for name, data in backups(app).items():
        if name.startswith(stem + "@") and re.search(BACKUP_NAME, name):
            return name, data
    return None


@pytest.mark.case("SESSION-016")
@pytest.mark.restart
def test_session_016_with_the_snapshot_on_quitting_asks_nothing_and_unsaved_text(app, tmp):
    """SESSION-016: With the snapshot on, quitting asks nothing and unsaved text comes back"""
    snap = write(tmp / "snap.txt", "on disk\n")
    with with_session(app, autosaveEnabled=True):
        app.open(snap)
        app.set_text("unsaved change\n")
        untitled = _untitled(app, "never saved")
        app.modal_log(clear=True)
        # No answers queued (the next test shows that nothing is asked: Cancel queued, the quit goes on).
        app.answers(clear=True)
        try:
            app.invoke("nsapp", "terminate:", [None], timeout=5)
        except Exception:  # noqa: BLE001
            pass
        assert app.proc.wait(15) == 0
        app.conn = None
        app.proc = None
        assert snap.read_text() == "on disk\n"
        root = parse(session_xml(app))
        bps = [f.get("backupFilePath") for f in files_of(root) if f.get("backupFilePath")]
        assert len(bps) == 2 and all(os.path.exists(p) and App.same_path(os.path.dirname(p), backup_dir(app))
                                     for p in bps)
        relaunch(app)
        d = find_doc(app, snap)
        assert d and app.text(d["index"]) == "unsaved change\n" and d["modified"]
        n = doc_named(app, untitled)
        assert n and app.text(n["index"]) == "never saved" and n["modified"] and n["path"] is None
        assert not alerts(app.modal_log())


@pytest.mark.case("SESSION-016")
@pytest.mark.restart
def test_session_016_the_snapshot_quit_shows_no_alert(app, tmp):
    """SESSION-016: the quit itself asks nothing (answer Cancel queued: an alert would stop the quit)."""
    snap = write(tmp / "snap.txt", "on disk\n")
    with with_session(app, autosaveEnabled=True):
        app.open(snap)
        app.set_text("unsaved change\n")
        _untitled(app, "never saved")
        app.modal_log(clear=True)
        app.answers(alerts=[3, 3], clear=True)
        try:
            app.invoke("nsapp", "terminate:", [None], timeout=5)
        except Exception:  # noqa: BLE001
            pass
        # With Cancel queued, any question would have kept the application running.
        assert app.proc.wait(15) == 0
        app.conn = None
        app.proc = None


def _start_backups(app, tmp, interval=5):
    pb = write(tmp / "pb.txt", "orig\n")
    app.open(pb)
    app.set_text("changed\n")
    return pb, _untitled(app, "draft")


@pytest.mark.case("SESSION-017")
@pytest.mark.restart
def test_session_017_the_periodic_backup_writes_unsaved_text_at_the_interval(app, tmp):
    """SESSION-017: The periodic backup writes unsaved text at the interval"""
    with with_session(app, autosaveEnabled=True, autosaveInterval=5):
        pb, title = _start_backups(app, tmp)
        app.wait(lambda: _backup_of(app, "pb.txt") and _backup_of(app, title), timeout=15, message="two backups")
        assert _backup_of(app, "pb.txt")[1] == b"changed\n"
        assert _backup_of(app, title)[1] == b"draft"
        assert pb.read_text() == "orig\n"
        root = parse(session_xml(app))
        named = {os.path.basename(f.get("backupFilePath") or "") for f in files_of(root)}
        assert {_backup_of(app, "pb.txt")[0], _backup_of(app, title)[0]} <= named
        assert find_doc(app, pb)["modified"] and doc_named(app, title)["modified"]


@pytest.mark.case("SESSION-018")
@pytest.mark.restart
def test_session_018_after_a_crash_the_unsaved_text_comes_back_from_the_backups(app, tmp):
    """SESSION-018: After a crash the unsaved text comes back from the backups"""
    with with_session(app, autosaveEnabled=True, autosaveInterval=5):
        pb, title = _start_backups(app, tmp)
        app.wait(lambda: _backup_of(app, "pb.txt") and _backup_of(app, title), timeout=15, message="two backups")
        # The crash must come after session.xml names both backups, or there is nothing to restore from.
        def session_names_backups():
            try:
                root = parse(session_xml(app))
            except (FileNotFoundError, ET.ParseError):   # not written yet, or being written
                return False
            named = {os.path.basename(f.get("backupFilePath") or "") for f in files_of(root)}
            return {_backup_of(app, "pb.txt")[0], _backup_of(app, title)[0]} <= named
        app.wait(session_names_backups, timeout=15, message="session.xml naming both backups")
        kill_app(app)
        relaunch(app)
        # The session is restored after the socket answers: wait for it.
        app.wait(lambda: find_doc(app, pb), timeout=15, message="pb.txt back after the crash")
        d = find_doc(app, pb)
        assert d and app.text(d["index"]) == "changed\n" and d["modified"]
        n = next((x for x in app.docs() if not x["path"] and app.text(x["index"]) == "draft"), None)
        assert n and n["modified"]
        assert pb.read_text() == "orig\n"


@pytest.mark.case("SESSION-019")
@pytest.mark.restart
def test_session_019_saving_or_discarding_a_document_removes_its_backup(app, tmp):
    """SESSION-019: Saving or discarding a document removes its backup"""
    with with_session(app, autosaveEnabled=True, autosaveInterval=5):
        d1, d2 = write(tmp / "d1.txt", "one\n"), write(tmp / "d2.txt", "two\n")
        app.open(d1)
        app.set_text("one edited\n")
        app.open(d2)
        app.set_text("two edited\n")
        title = _untitled(app, "draft")
        app.wait(lambda: all(_backup_of(app, s) for s in ("d1.txt", "d2.txt", title)), timeout=15,
                 message="three backups")
        b1, b2, bu = (_backup_of(app, s)[0] for s in ("d1.txt", "d2.txt", title))
        front(app, d1)
        app.run("IDM_FILE_SAVE")
        assert d1.read_text() == "one edited\n"
        assert b1 not in backups(app)
        front(app, d2)
        app.answers(alerts=[2], clear=True)
        app.run("IDM_FILE_CLOSE")
        assert find_doc(app, d2) is None
        assert b2 not in backups(app)
        app.call("go_to", document=title, line=1)
        app.set_text("")
        app.wait(lambda: bu not in backups(app), timeout=12, message="the emptied tab's backup gone")
        app.wait(lambda: not ({b1, b2, bu} & {os.path.basename(f.get("backupFilePath") or "")
                                             for f in files_of(parse(session_xml(app)))}),
                 timeout=12, message="session.xml without the backups")


@pytest.mark.case("SESSION-020")
@pytest.mark.restart
def test_session_020_a_backup_older_than_the_file_is_not_restored_over_newer_cont(app, tmp):
    """SESSION-020: A backup older than the file is not restored over newer content"""
    newer = write(tmp / "newer.txt", "original\n")
    with with_session(app, autosaveEnabled=True, autosaveInterval=5):
        app.open(newer)
        app.set_text("backup text")
        app.wait(lambda: _backup_of(app, "newer.txt"), timeout=15, message="the backup")
        name = _backup_of(app, "newer.txt")[0]
        kill_app(app)
        write(newer, "changed elsewhere")
        t = time.time() + 5
        os.utime(newer, (t, t))
        relaunch(app)
        d = find_doc(app, newer)
        assert d and app.text(d["index"]) == "changed elsewhere" and not d["modified"]
        assert name not in backups(app)


@pytest.mark.case("SESSION-021")
@pytest.mark.restart
def test_session_021_a_document_too_large_to_back_up_is_still_asked_about_at_quit(app, tmp):
    """SESSION-021: A document too large to back up is still asked about at quit"""
    large = write(tmp / "large.txt", ("0123456789" * 7 + "\n") * 29000)   # ~2 MB
    with with_session(app, autosaveEnabled=True, largeFileThresholdMB=1):
        app.open(large)
        app.sci(SCI_GOTOPOS, 0)
        app.type("x")
        app.wait(lambda: app.doc()["modified"], 5, message="large.txt modified")
        _untitled(app, "small")
        app.modal_log(clear=True)
        # One Cancel is the answer; the second only keeps a wrong second round from saving anything.
        app.answers(alerts=[3, 3], clear=True)
        app.invoke("nsapp", "terminate:", [None], timeout=20)
        assert app.running
        shown = alerts(app.modal_log())
        assert len(shown) == 1, shown
        text = " ".join(str(shown[0].get(k, "")) for k in ("message", "informative"))
        assert "large.txt" in text, shown
        assert find_doc(app, large) and any(app.text(x["index"]) == "small" for x in app.docs() if not x["path"])


@pytest.mark.case("SESSION-022")
@pytest.mark.restart
def test_session_022_without_the_snapshot_nothing_is_backed_up(app, tmp):
    """SESSION-022: Without the snapshot nothing is backed up"""
    f = write(tmp / "f.txt", "f\n")
    with with_session(app, autosaveEnabled=False, autosaveInterval=5):
        app.open(f)
        app.set_text("edited\n")
        _untitled(app, "draft")
        app.idle(7)
        assert backups(app) == {}
        assert not session_xml(app).exists()
