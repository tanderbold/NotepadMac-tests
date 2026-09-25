"""FILE: end-to-end tests (plan: plan/FILE.md)."""
import os
import unicodedata
import uuid
from pathlib import Path

import pytest

from harness.sci import *  # noqa: F401,F403
from harness.app import ToolError
from _util_file import (App, alerts, current, find_doc, front, mtime, panels, pdf_text, reactivate,
                              relaunched, rewrite, titles, wait_log, write)


def same(a, b):
    return App.same_path(a, b)


def new_tab(app, text=None):
    """A new untitled tab made as the user makes it (File > New), optionally with unsaved text."""
    app.run("IDM_FILE_NEW")
    if text is not None:
        app.set_text(text)
    return app.doc()


def wait_alert(app, timeout=10.0, message=None):
    got = wait_log(app, lambda es: any(e.get("kind") == "alert" and (message is None or message in e.get("message", ""))
                                       for e in es), timeout=timeout)
    return got


# ---- New -------------------------------------------------------------------

@pytest.mark.case("FILE-001")
def test_file_001_new_adds_an_empty_untitled_tab_in_front(app):
    """FILE-001: New adds an empty untitled tab in front"""
    steps = [lambda: app.run("IDM_FILE_NEW"), lambda: app.keys("cmd+n"), lambda: app.run(41001)]
    for n, step in enumerate(steps, start=2):
        step()
        d = app.doc()
        assert d["title"] == f"new {n}" and d["current"]
        assert d["path"] is None and not d["modified"] and app.text() == ""
        assert (d["encoding"], d["eol"], d["language"]) == ("UTF-8", "LF", "normal")
        assert app.get("window", "title") == f"new {n}"
    assert len(app.docs()) == 4
    assert app.menu_item("IDM_FILE_NEW")["key"] == "cmd+n"


@pytest.mark.case("FILE-002")
def test_file_002_new_takes_the_lowest_free_new_n_number(app):
    """FILE-002: New takes the lowest free "new N" number"""
    app.run("IDM_FILE_NEW")
    app.run("IDM_FILE_NEW")
    assert titles(app) == ["new 1", "new 2", "new 3"]
    app.call("close_document", document=1, discard_changes=True)
    app.run("IDM_FILE_NEW")
    assert sorted(titles(app)) == ["new 1", "new 2", "new 3"]
    assert app.doc()["title"] == "new 2"
    app.run("IDM_FILE_CLOSEALL")
    assert titles(app) == ["new 1"]
    app.run("IDM_FILE_NEW")
    assert titles(app) == ["new 1", "new 2"]


# ---- Open ------------------------------------------------------------------

@pytest.mark.case("FILE-003")
def test_file_003_open_a_file_through_the_open_panel(app, tmp):
    """FILE-003: Open a file through the Open panel"""
    one = write(tmp / "a/one.py", "import os\nx = 1\n")
    other = write(tmp / "a/other.txt", "o\n")
    app.open(other)
    app.answers(panels=[str(one)])
    app.run("IDM_FILE_OPEN")
    entries = app.modal_log()
    ps = panels(entries)
    assert len(ps) == 1 and ps[0]["kind"] == "open" and same(ps[0]["answered"][0], one)
    assert same(ps[0]["directory"], tmp / "a")
    assert not alerts(entries)
    d = app.doc()
    assert d["title"] == "one.py" and same(d["path"], one) and d["current"]
    assert app.text() == "import os\nx = 1\n" and d["language"] == "python" and not d["modified"]
    caret = app.selection()["caret"]
    assert (caret["line"], caret["column"]) == (1, 1)
    title = app.get("window", "title")
    assert title.startswith("one.py — ") and same(title.split(" — ", 1)[1], tmp / "a")


@pytest.mark.case("FILE-004")
def test_file_004_open_several_files_at_once(app, tmp):
    """FILE-004: Open several files at once"""
    files = [write(tmp / "m1.txt", "one\n"), write(tmp / "m2.md", "# two\n"), write(tmp / "m3.json", '{"a": 1}\n')]
    app.answers(panels=[[str(f) for f in files]])
    app.run("IDM_FILE_OPEN")
    docs = app.docs()
    # The first file takes the lone clean "new 1"'s place (FILE-007, loadBufferIntoView).
    assert [d["title"] for d in docs] == ["m1.txt", "m2.md", "m3.json"]
    langs = [d["language"] for d in docs]
    assert langs[0] == "normal" and langs[1].lower().startswith("markdown") and langs[2] == "json"
    for d, f in zip(docs, files):
        assert app.text(d["index"]) == f.read_text()
    assert docs[2]["current"]
    entries = app.modal_log()
    assert len(entries) == 1 and entries[0]["kind"] == "open"


@pytest.mark.case("FILE-005")
def test_file_005_a_cancelled_open_panel_changes_nothing(app, tmp):
    """FILE-005: A cancelled Open panel changes nothing"""
    app.open(write(tmp / "c.txt", "keep\n"))
    before = app.docs()
    app.answers(panels=[None])
    app.keys("cmd+o")
    entries = app.modal_log()
    assert [(e["kind"], e["answered"]) for e in entries] == [("open", "cancel")]
    assert app.docs() == before and app.text() == "keep\n"


@pytest.mark.case("FILE-006")
def test_file_006_opening_a_file_that_is_already_open_brings_its_tab_forward(app, tmp):
    """FILE-006: Opening a file that is already open brings its tab forward"""
    dup = write(tmp / "dup.txt", "text\n")
    other = write(tmp / "other.txt", "other\n")
    app.open(dup)
    app.select(1, 1)
    app.type("edit ")
    app.open(other)
    n = len(app.docs())
    shown = find_doc(app, dup)["path"]          # the path as the app spells it
    app.answers(panels=[shown])
    app.run("IDM_FILE_OPEN")
    assert len(app.docs()) == n and same(app.doc()["path"], dup)
    assert app.text() == "edit text\n" and app.doc()["modified"]
    app.open(other)
    app.open(dup)
    assert len(app.docs()) == n and same(app.doc()["path"], dup) and app.text() == "edit text\n"


@pytest.mark.case("FILE-006")
def test_file_006_the_same_file_under_another_spelling_is_not_opened_twice(app, tmp):
    """FILE-006 (variant): a file already open, chosen in the panel through the other spelling of a symlinked folder"""
    dup = write(tmp / "dup.txt", "text\n")
    app.open(dup)
    shown = find_doc(app, dup)["path"]
    other_spelling = shown[len("/private"):] if shown.startswith("/private/") else "/private" + shown
    assert os.path.exists(other_spelling)
    n = len(app.docs())
    app.answers(panels=[other_spelling])
    app.run("IDM_FILE_OPEN")
    assert len(app.docs()) == n


@pytest.mark.case("FILE-007")
def test_file_007_opening_a_file_replaces_a_lone_clean_untitled_tab(app, tmp):
    """FILE-007: Opening a file replaces a lone, clean untitled tab"""
    x = write(tmp / "x.txt", "x\n")
    y = write(tmp / "y.txt", "y\n")
    app.answers(panels=[str(x)])
    app.run("IDM_FILE_OPEN")
    assert titles(app) == ["x.txt"]
    new_tab(app, "keep")
    app.answers(panels=[str(y)])
    app.run("IDM_FILE_OPEN")
    assert len(app.docs()) == 3 and "y.txt" in titles(app)


@pytest.mark.case("FILE-008")
def test_file_008_a_file_with_a_unicode_name_and_spaces_opens_and_saves_back_to_itself(app, tmp):
    """FILE-008: A file with a Unicode name and spaces opens and saves back to itself"""
    name = "тест файл ☃ 文件.txt"
    f = write(tmp / name, "héllo\n")
    app.answers(panels=[str(f)])
    app.run("IDM_FILE_OPEN")
    nfc = lambda x: unicodedata.normalize("NFC", os.path.realpath(str(x)))  # noqa: E731
    assert unicodedata.normalize("NFC", app.doc()["title"]) == name and nfc(app.doc()["path"]) == nfc(f)
    app.select(1, 6)
    app.type("!")
    app.run("IDM_FILE_SAVE")
    assert f.read_bytes() == "héllo!\n".encode()
    assert sorted(p.name for p in tmp.iterdir()) == [name]


@pytest.mark.case("FILE-009")
def test_file_009_an_empty_file_opens_as_an_empty_utf8_document_and_saves_as_zero_bytes(app, tmp):
    """FILE-009: An empty file opens as an empty UTF-8 document and saves as zero bytes"""
    e = write(tmp / "empty.txt", b"")
    d = app.open(e)
    assert app.text() == "" and (d["encoding"], d["eol"], d["modified"]) == ("UTF-8", "LF", False)
    # Unmodified: Save is off and does nothing (Notepad_plus::checkDocState), as upstream.
    app.run("IDM_FILE_SAVE", expect_ran=False)
    assert e.stat().st_size == 0
    app.type("a")
    app.keys("backspace")
    app.run("IDM_FILE_SAVE")
    assert e.stat().st_size == 0


@pytest.mark.case("FILE-010")
def test_file_010_a_file_that_is_gone_by_the_time_it_is_opened_gives_an_error_and_no_tab(app, tmp):
    """FILE-010: A file that is gone by the time it is opened gives an error and no tab"""
    before = app.docs()
    app.answers(panels=[str(tmp / "missing.txt")], alerts=[1])
    app.run("IDM_FILE_OPEN")
    al = alerts(app.modal_log())
    assert len(al) == 1 and "missing.txt" in al[0]["message"] and "no such file" in al[0]["message"]
    assert app.docs() == before


@pytest.mark.case("FILE-011")
def test_file_011_a_file_without_read_permission_gives_an_error_and_no_tab(app, tmp):
    """FILE-011: A file without read permission gives an error and no tab"""
    f = write(tmp / "noread.txt", "secret", mode=0)
    try:
        n = len(app.docs())
        app.answers(panels=[str(f)], alerts=[1])
        app.run("IDM_FILE_OPEN")
        al = alerts(app.modal_log())
        assert len(al) == 1 and "noread.txt" in al[0]["message"] and "permission" in al[0]["message"]
        assert len(app.docs()) == n
    finally:
        os.chmod(f, 0o644)


@pytest.mark.case("FILE-012")
def test_file_012_a_read_only_file_opens_read_only_in_the_editor(app, tmp):
    """FILE-012: A read-only file opens read-only in the editor"""
    f = write(tmp / "ro.txt", "locked\n", mode=0o444)
    try:
        app.open(f)
        assert app.sci(SCI_GETREADONLY) == 1
        app.select(1, 1)
        app.type("X")
        app.keys("backspace")
        assert app.text() == "locked\n" and not app.doc()["modified"]
        app.run("IDM_FILE_SAVE", expect_ran=False)   # nothing to save: Save is off, as upstream
        assert f.read_text() == "locked\n" and (f.stat().st_mode & 0o777) == 0o444
    finally:
        os.chmod(f, 0o644)


# ---- Save ------------------------------------------------------------------

@pytest.mark.case("FILE-013")
def test_file_013_save_writes_the_document_and_clears_the_modified_state(app, tmp):
    """FILE-013: Save writes the document and clears the modified state"""
    f = write(tmp / "s.txt", "one\n")
    app.open(f)
    app.select(1, 1)
    app.type("two ")
    assert app.doc()["modified"] and app.get("window", "documentEdited") in (True, 1)
    app.keys("cmd+s")
    assert f.read_text() == "two one\n"
    assert not app.doc()["modified"] and app.get("window", "documentEdited") in (False, 0)
    assert app.sci(SCI_CANUNDO) == 1


SAVE_CASES = {
    "utf8": (b"a\nb\n", "utf-8", b"", "\n"),
    "utf8bom": (b"\xef\xbb\xbfa\nb\n", "utf-8", b"\xef\xbb\xbf", "\n"),
    "utf16le": (b"\xff\xfe" + "a\nb\n".encode("utf-16-le"), "utf-16-le", b"\xff\xfe", "\n"),
    "utf16be": (b"\xfe\xff" + "a\nb\n".encode("utf-16-be"), "utf-16-be", b"\xfe\xff", "\n"),
    "latin1": (b"caf\xe9\nx\n", "latin-1", b"", "\n"),
    "crlf": (b"a\r\nb\r\n", "utf-8", b"", "\r\n"),
    "cr": (b"a\rb\r", "utf-8", b"", "\r"),
}


@pytest.mark.case("FILE-014")
@pytest.mark.parametrize("kind", list(SAVE_CASES))
def test_file_014_save_keeps_the_file_s_encoding_byte_order_mark_and_line_endings(app, tmp, kind):
    """FILE-014: Save keeps the file's encoding, byte order mark and line endings"""
    raw, codec, bom, eol = SAVE_CASES[kind]
    f = write(tmp / f"{kind}.txt", raw)
    d0 = app.open(f)
    text = raw[len(bom):].decode(codec)
    first = text.split(eol, 1)[0]
    app.select(1, len(first) + 1)
    app.type("Z")
    app.keys("escape", "return")
    app.run("IDM_FILE_SAVE")
    expected = first + "Z" + eol + text[len(first):]
    assert f.read_bytes() == bom + expected.encode(codec)
    d1 = app.doc()
    assert (d1["encoding"], d1["eol"]) == (d0["encoding"], d0["eol"])


@pytest.mark.case("FILE-015")
def test_file_015_saving_an_untitled_document_asks_where_then_the_tab_becomes_that_file(app, tmp):
    """FILE-015: Saving an untitled document asks where, then the tab becomes that file"""
    new_tab(app, "print(1)\n")
    target = tmp / "new.py"
    app.answers(panels=[str(target)])
    app.run("IDM_FILE_SAVE")
    ps = panels(app.modal_log())
    assert len(ps) == 1 and ps[0]["kind"] == "save" and ps[0]["name"] == "new 2"
    assert target.read_text() == "print(1)\n"
    d = app.doc()
    assert d["title"] == "new.py" and same(d["path"], target) and d["language"] == "python" and not d["modified"]


@pytest.mark.case("FILE-016")
def test_file_016_cancelling_the_save_panel_of_an_untitled_document_keeps_it_untitled(app, tmp):
    """FILE-016: Cancelling the Save panel of an untitled document keeps it untitled"""
    new_tab(app, "draft")
    app.answers(panels=[None])
    app.run("IDM_FILE_SAVE")
    assert [e["answered"] for e in panels(app.modal_log())] == ["cancel"]
    d = app.doc()
    assert d["title"] == "new 2" and d["path"] is None and d["modified"] and app.text() == "draft"
    assert list(tmp.iterdir()) == []


@pytest.mark.case("FILE-017")
def test_file_017_save_and_save_all_are_disabled_when_there_is_nothing_to_save(app, tmp):
    """FILE-017: Save and Save All are disabled when there is nothing to save"""
    f = write(tmp / "clean.txt", "clean\n")
    os.utime(f, (1_600_000_000, 1_600_000_000))
    app.open(f)
    before = mtime(f)
    states = app.menu("IDM_FILE_SAVE", "IDM_FILE_SAVEALL")
    app.run("IDM_FILE_SAVE", expect_ran=False)
    assert mtime(f) == before
    assert not states["IDM_FILE_SAVE"]["enabled"] and not states["IDM_FILE_SAVEALL"]["enabled"]
    app.type("x")
    assert app.enabled("IDM_FILE_SAVE") and app.enabled("IDM_FILE_SAVEALL")


@pytest.mark.case("FILE-018")
def test_file_018_saving_into_a_folder_without_write_permission_fails_with_an_alert(app, tmp):
    """FILE-018: Saving into a folder without write permission fails with an alert"""
    ro = tmp / "rodir"
    ro.mkdir()
    os.chmod(ro, 0o555)
    try:
        new_tab(app, "text")
        app.answers(panels=[str(ro / "x.txt")], alerts=[1])
        app.run("IDM_FILE_SAVE")
        al = alerts(app.modal_log())
        assert len(al) == 1 and "permission" in al[0]["message"] and "x.txt" in al[0]["message"]
        assert not (ro / "x.txt").exists()
        assert app.doc()["path"] is None and app.doc()["modified"]
    finally:
        os.chmod(ro, 0o755)


@pytest.mark.case("FILE-019")
def test_file_019_saving_a_file_opened_through_a_symbolic_link_writes_the_target_and_keeps_the_link(app, tmp):
    """FILE-019: Saving a file opened through a symbolic link writes the target and keeps the link"""
    target = write(tmp / "target.txt", "t\n")
    link = tmp / "link.txt"
    link.symlink_to(target)
    app.open(link)
    app.set_text("changed\n")
    app.run("IDM_FILE_SAVE")
    assert link.is_symlink() and os.readlink(link) == str(target)
    assert target.read_text() == "changed\n"


@pytest.mark.case("FILE-020")
def test_file_020_saving_keeps_the_file_s_permissions(app, tmp):
    """FILE-020: Saving keeps the file's permissions"""
    f = write(tmp / "run.sh", "#!/bin/sh\necho hi\n", mode=0o755)
    app.open(f)
    app.set_text("#!/bin/sh\necho bye\n")
    app.run("IDM_FILE_SAVE")
    assert f.read_text() == "#!/bin/sh\necho bye\n" and (f.stat().st_mode & 0o777) == 0o755


# ---- Save As, Save a Copy As, Rename ------------------------------------------

@pytest.mark.case("FILE-021")
def test_file_021_save_as_writes_a_new_file_and_the_tab_follows_it(app, tmp):
    """FILE-021: Save As writes a new file and the tab follows it"""
    orig = write(tmp / "orig.txt", "x = 1\n")
    app.open(orig)
    app.set_text("x = 1\ny = 2\n")
    target = tmp / "copy.py"
    app.answers(panels=[str(target)])
    app.run("IDM_FILE_SAVEAS")
    ps = panels(app.modal_log())
    assert len(ps) == 1 and ps[0]["kind"] == "save" and ps[0]["name"] == "orig.txt"
    assert target.read_text() == "x = 1\ny = 2\n" and orig.read_text() == "x = 1\n"
    d = app.doc()
    assert d["title"] == "copy.py" and same(d["path"], target) and d["language"] == "python" and not d["modified"]


@pytest.mark.case("FILE-022")
def test_file_022_save_as_and_save_a_copy_as_start_in_the_document_s_folder(app, tmp):
    """FILE-022: Save As and Save a Copy As start in the document's folder"""
    f = write(tmp / "deep/dir/f.txt", "f\n")
    app.open(f)
    app.answers(panels=[None, None])
    app.run("IDM_FILE_SAVEAS")
    app.run("IDM_FILE_SAVECOPYAS")
    ps = panels(app.modal_log())
    assert len(ps) == 2
    for p in ps:
        assert p["name"] == "f.txt"
        assert same(p["directory"], tmp / "deep/dir")


@pytest.mark.case("FILE-023")
def test_file_023_save_as_onto_a_file_open_in_another_tab_is_refused(app, tmp):
    """FILE-023: Save As onto a file open in another tab is refused"""
    busy = write(tmp / "busy.txt", "busy\n")
    app.open(busy)
    shown = find_doc(app, busy)["path"]
    new_tab(app, "other")
    app.answers(panels=[shown], alerts=[1])
    app.run("IDM_FILE_SAVEAS")
    al = alerts(app.modal_log())
    assert len(al) == 1 and al[0]["message"] == "That file is open in another tab."
    assert al[0]["informative"] == "Close it first, or choose another name."
    assert busy.read_text() == "busy\n"
    assert app.doc()["path"] is None and app.doc()["modified"]


@pytest.mark.case("FILE-024")
def test_file_024_save_as_over_an_existing_file_that_is_not_open_replaces_its_content(app, tmp):
    """FILE-024: Save As over an existing file that is not open replaces its content"""
    old = write(tmp / "old.txt", "old contents\n")
    new_tab(app, "new contents")
    app.answers(panels=[str(old)])
    app.run("IDM_FILE_SAVEAS")
    assert old.read_text() == "new contents"
    assert app.doc()["title"] == "old.txt" and not app.doc()["modified"]


@pytest.mark.case("FILE-025")
def test_file_025_a_cancelled_save_as_changes_nothing(app, tmp):
    """FILE-025: A cancelled Save As changes nothing"""
    f = write(tmp / "keep.txt", "keep\n")
    app.open(f)
    app.select(1, 1)
    app.type("z")
    app.answers(panels=[None])
    app.run("IDM_FILE_SAVEAS")
    d = app.doc()
    assert same(d["path"], f) and d["title"] == "keep.txt" and d["modified"]
    assert f.read_text() == "keep\n" and [p.name for p in tmp.iterdir()] == ["keep.txt"]


@pytest.mark.case("FILE-026")
def test_file_026_save_a_copy_as_writes_a_copy_and_leaves_the_tab_on_its_own_file(app, tmp):
    """FILE-026: Save a Copy As writes a copy and leaves the tab on its own file"""
    raw = b"\xff\xfe" + "first\n".encode("utf-16-le")
    src = write(tmp / "src.txt", raw)
    app.open(src)
    app.set_text("first\nsecond\n")
    dst = tmp / "dst.txt"
    app.answers(panels=[str(dst)])
    app.run("IDM_FILE_SAVECOPYAS")
    assert dst.read_bytes() == b"\xff\xfe" + "first\nsecond\n".encode("utf-16-le")
    assert src.read_bytes() == raw
    d = app.doc()
    assert d["title"] == "src.txt" and same(d["path"], src) and d["modified"]


@pytest.mark.case("FILE-027")
def test_file_027_rename_moves_the_file_on_disk_and_the_tab_follows(app, tmp):
    """FILE-027: Rename moves the file on disk and the tab follows"""
    a = write(tmp / "a.txt", "var x = 1;\n")
    app.open(a)
    app.select(1, 1)
    app.type("// ")
    b = tmp / "b.js"
    app.answers(panels=[str(b)])
    app.run("IDM_FILE_RENAME")
    ps = panels(app.modal_log())
    assert len(ps) == 1 and ps[0]["title"] == "Rename" and ps[0]["name"] == "a.txt" and same(ps[0]["directory"], tmp)
    assert not a.exists() and b.read_text() == "var x = 1;\n"
    d = app.doc()
    assert d["title"] == "b.js" and same(d["path"], b) and d["language"] in ("javascript", "javascript.js")
    assert app.text() == "// var x = 1;\n" and d["modified"]


@pytest.mark.case("FILE-028")
def test_file_028_rename_keeps_a_language_the_user_chose(app, tmp):
    """FILE-028: Rename keeps a language the user chose"""
    f = write(tmp / "notes.txt", "x = 1\n")
    app.open(f)
    app.run("IDM_LANG_PYTHON")
    app.answers(panels=[str(tmp / "notes.md")])
    app.run("IDM_FILE_RENAME")
    assert app.doc()["title"] == "notes.md" and app.doc()["language"] == "python"


@pytest.mark.case("FILE-029")
def test_file_029_rename_onto_an_existing_file_fails_and_touches_neither_file(app, tmp):
    """FILE-029: Rename onto an existing file fails and touches neither file"""
    r1 = write(tmp / "r1.txt", "one")
    r2 = write(tmp / "r2.txt", "two")
    app.open(r1)
    app.answers(panels=[str(r2)], alerts=[1])
    app.run("IDM_FILE_RENAME")
    assert len(alerts(app.modal_log())) == 1
    assert r1.read_text() == "one" and r2.read_text() == "two"
    assert app.doc()["title"] == "r1.txt" and same(app.doc()["path"], r1)


@pytest.mark.case("FILE-030")
def test_file_030_rename_of_an_untitled_document_renames_only_its_tab(app, tmp):
    """FILE-030: Rename of an untitled document renames only its tab"""
    new_tab(app, "draft")
    app.answers(panels=[str(tmp / "named.txt")])
    app.run("IDM_FILE_RENAME")
    d = app.doc()
    assert d["title"] == "named.txt" and d["path"] is None and app.text() == "draft"
    assert list(tmp.iterdir()) == []
    app.answers(panels=[None])
    app.run("IDM_FILE_RENAME")
    assert app.doc()["title"] == "named.txt"


# ---- Save All -------------------------------------------------------------

@pytest.mark.case("FILE-031")
def test_file_031_save_all_saves_every_modified_document_after_confirmation(app, tmp):
    """FILE-031: Save All saves every modified document after confirmation"""
    p = write(tmp / "p.txt", "p\n")
    q = write(tmp / "q.txt", "q\n")
    untouched = write(tmp / "untouched.txt", "u\n")
    os.utime(untouched, (1_600_000_000, 1_600_000_000))
    app.open(p)
    app.set_text("p2\n")
    app.open(q)
    app.set_text("q2\n")
    app.open(untouched)
    new_tab(app, "fresh")
    app.open(q)
    fresh = tmp / "fresh.txt"
    app.answers(alerts=["Yes"], panels=[str(fresh)])
    app.keys("alt+cmd+s")
    entries = app.modal_log()
    assert [e["kind"] for e in entries] == ["alert", "save"]
    assert entries[0]["message"] == "Save All Confirmation" and entries[0]["buttons"] == ["Yes", "No", "Always Yes"]
    assert p.read_text() == "p2\n" and q.read_text() == "q2\n" and fresh.read_text() == "fresh"
    assert untouched.stat().st_mtime == 1_600_000_000
    assert not any(d["modified"] for d in app.docs())
    assert same(app.doc()["path"], q)


@pytest.mark.case("FILE-032")
def test_file_032_save_all_s_confirmation_no_saves_nothing_always_yes_stops_asking(app, tmp):
    """FILE-032: Save All's confirmation: No saves nothing, Always Yes stops asking"""
    f = write(tmp / "f.txt", "v1")
    app.open(f)
    try:
        app.set_text("v2")
        app.answers(alerts=["No"])
        app.run("IDM_FILE_SAVEALL")
        assert f.read_text() == "v1" and app.doc()["modified"]
        app.answers(alerts=["Always Yes"])
        app.run("IDM_FILE_SAVEALL")
        assert f.read_text() == "v2" and app.pref("confirmSaveAll") in (False, 0)
        app.modal_log()
        app.set_text("v3")
        app.run("IDM_FILE_SAVEALL")
        assert f.read_text() == "v3" and app.modal_log() == []
    finally:
        app.set_prefs(confirmSaveAll=True)


# ---- Close ------------------------------------------------------------------

@pytest.mark.case("FILE-033")
def test_file_033_close_removes_the_tab_in_front_and_the_neighbour_takes_its_place(app, tmp):
    """FILE-033: Close removes the tab in front and the neighbour takes its place"""
    cs = [write(tmp / f"c{i}.txt", f"c{i}\n") for i in (1, 2, 3)]
    for c in cs:
        app.open(c)
    app.open(cs[1])
    app.run("IDM_FILE_CLOSE")
    # c1.txt took the lone clean "new 1"'s place when it was opened (FILE-007).
    assert titles(app) == ["c1.txt", "c3.txt"] and app.doc()["title"] == "c3.txt"
    app.keys("cmd+w")
    assert titles(app) == ["c1.txt"]
    app.run(41003)
    assert titles(app) == ["new 1"]
    app.run("IDM_FILE_CLOSE")
    assert titles(app) == ["new 1"] and app.text() == "" and not app.doc()["modified"]
    assert app.running


@pytest.mark.case("FILE-034")
def test_file_034_closing_a_modified_document_asks_save_don_t_save_cancel(app, tmp):
    """FILE-034: Closing a modified document asks Save / Don't Save / Cancel"""
    f = write(tmp / "ask.txt", "v1")
    app.open(f)
    app.set_text("v2")

    def the_alert():
        al = alerts(app.modal_log())
        assert len(al) == 1 and al[0]["message"] == "Save" and al[0]["informative"] == 'Save file "ask.txt" ?'
        assert al[0]["buttons"] == ["Yes", "No", "Cancel"]
    app.answers(alerts=[3])
    app.run("IDM_FILE_CLOSE")
    the_alert()
    assert find_doc(app, f)["modified"]
    app.answers(alerts=[2])
    app.run("IDM_FILE_CLOSE")
    the_alert()
    assert find_doc(app, f) is None and f.read_text() == "v1"
    app.open(f)
    app.set_text("v3")
    app.answers(alerts=[1])
    app.run("IDM_FILE_CLOSE")
    the_alert()
    assert find_doc(app, f) is None and f.read_text() == "v3"


@pytest.mark.case("FILE-035")
def test_file_035_saving_an_untitled_document_while_closing_it_can_itself_be_cancelled(app):
    """FILE-035: Saving an untitled document while closing it can itself be cancelled"""
    new_tab(app, "unsaved")
    app.answers(alerts=[1], panels=[None])
    app.run("IDM_FILE_CLOSE")
    assert [e["kind"] for e in app.modal_log()] == ["alert", "save"]
    assert app.doc()["title"] == "new 2" and app.text() == "unsaved" and app.doc()["modified"]


@pytest.mark.case("FILE-036")
def test_file_036_close_all_closes_everything_and_leaves_one_fresh_tab(app, tmp):
    """FILE-036: Close All closes everything and leaves one fresh tab"""
    for i in range(3):
        app.open(write(tmp / f"f{i}.txt", "x"))
    app.run("IDM_FILE_NEW")
    app.run("IDM_FILE_NEW")
    app.keys("alt+cmd+w")
    assert app.modal_log() == []
    assert titles(app) == ["new 1"] and app.text() == "" and not app.doc()["modified"]


@pytest.mark.case("FILE-037")
def test_file_037_cancel_during_close_all_keeps_every_tab(app, tmp):
    """FILE-037: Cancel during Close All keeps every tab"""
    d1 = write(tmp / "d1.txt", "d1")
    d2 = write(tmp / "d2.txt", "d2")
    app.open(d1)
    app.set_text("d1!")
    app.open(d2)
    app.set_text("d2!")
    before = titles(app)
    app.answers(alerts=[2, 3])
    app.run("IDM_FILE_CLOSEALL")
    assert len(alerts(app.modal_log())) == 2
    assert titles(app) == before and find_doc(app, d1)["modified"] and find_doc(app, d2)["modified"]
    assert same(app.doc()["path"], d2)
    app.answers(alerts=[2, 2])
    app.run("IDM_FILE_CLOSEALL")
    assert titles(app) == ["new 1"] and d1.read_text() == "d1" and d2.read_text() == "d2"


@pytest.mark.case("FILE-038")
def test_file_038_close_all_but_active_document_keeps_only_the_tab_in_front(app, tmp):
    """FILE-038: Close All but Active Document keeps only the tab in front"""
    fs = [write(tmp / f"k{i}.txt", f"k{i}") for i in range(5)]
    for f in fs:
        app.open(f)
    app.open(fs[0])
    app.set_text("changed")
    app.open(fs[2])
    app.answers(alerts=[2])
    app.run("IDM_FILE_CLOSEALL_BUT_CURRENT")
    al = alerts(app.modal_log())
    assert len(al) == 1 and "k0.txt" in al[0]["informative"]
    assert titles(app) == ["k2.txt"] and app.text() == "k2"


@pytest.mark.case("FILE-039")
def test_file_039_close_all_to_the_left_and_to_the_right(app, tmp):
    """FILE-039: Close All to the Left and to the Right"""
    fs = [write(tmp / f"t{i}.txt", f"t{i}") for i in range(5)]
    for f in fs:
        app.open(f)
    app.open(fs[2])
    app.run("IDM_FILE_CLOSEALL_TOLEFT")
    assert titles(app) == ["t2.txt", "t3.txt", "t4.txt"] and app.doc()["title"] == "t2.txt"
    app.run("IDM_FILE_CLOSEALL_TORIGHT")
    assert titles(app) == ["t2.txt"] and app.doc()["title"] == "t2.txt"
    app.run("IDM_FILE_CLOSEALL_TOLEFT")
    app.run("IDM_FILE_CLOSEALL_TORIGHT")
    assert titles(app) == ["t2.txt"]


@pytest.mark.case("FILE-040")
def test_file_040_close_all_unchanged_keeps_the_modified_documents_only(app, tmp):
    """FILE-040: Close All Unchanged keeps the modified documents only"""
    us = [write(tmp / f"u{i}.txt", f"u{i}") for i in (1, 2, 3)]
    for u in us:
        app.open(u)
    app.open(us[1])
    app.set_text("u2!")
    new_tab(app, "x")
    app.run("IDM_FILE_CLOSEALL_UNCHANGED")
    assert app.modal_log() == []
    # u1.txt took "new 1"'s place (FILE-007), so the new tab is the lowest free number, "new 1" (FILE-002).
    assert titles(app) == ["u2.txt", "new 1"] and all(d["modified"] for d in app.docs())
    assert us[1].read_text() == "u2"


@pytest.mark.case("FILE-041")
def test_file_041_close_all_but_pinned_documents_keeps_the_pinned_tabs(app, tmp):
    """FILE-041: Close All but Pinned Documents keeps the pinned tabs"""
    p1, p2, l1, l2 = (write(tmp / n, n) for n in ("p1.txt", "p2.txt", "loose1.txt", "loose2.txt"))
    for f in (p1, p2, l1, l2):
        app.open(f)
    app.open(p2)
    app.run("File|Pin Tab")
    app.open(p1)
    app.run("File|Pin Tab")
    assert titles(app)[:2] == ["p2.txt", "p1.txt"]
    app.open(l2)
    app.set_text("changed")
    app.answers(alerts=[2])
    app.run("IDM_FILE_CLOSEALL_BUT_PINNED")
    al = alerts(app.modal_log())
    assert len(al) == 1 and "loose2.txt" in al[0]["informative"]
    docs = app.docs()
    assert [d["title"] for d in docs] == ["p2.txt", "p1.txt"] and all(d.get("pinned") for d in docs)


@pytest.mark.case("FILE-042")
def test_file_042_the_tab_context_menu_s_close_commands_act_like_the_file_menu_s(app, tmp):
    """FILE-042: The tab context menu's close commands act like the File menu's"""
    fs = [write(tmp / f"t{i}.txt", f"t{i}") for i in range(4)]
    for f in fs:
        app.open(f)
    app.open(fs[1])
    tree = app.call("e2e_menu", context="tab")["tree"]
    tops = [i.get("title") for i in tree]
    assert tops[:12] == ["Close", "Close Multiple Tabs", "Pin Tab", "Save", "Save As...", "Open into", "Rename",
                         "Move to Trash", "Reload", "Print", None, "Read-Only in Notepad++"]
    multi = [i.get("title") for i in tree[1]["items"]]
    assert multi == ["Close All BUT This", "Close All BUT Pinned", "Close All to the Left", "Close All to the Right",
                     "Close All Unchanged"]
    into = [i.get("title") for i in tree[5]["items"] if i.get("title")]
    assert into == ["Open Containing Folder in Finder", "Open Containing Folder in Terminal",
                    "Open Containing Folder as Workspace", "Open in Default Viewer"]
    app.call("e2e_menu_invoke", context="tab", path="Close Multiple Tabs|Close All to the Right")
    # t0.txt took the lone clean "new 1"'s place when it was opened (FILE-007).
    assert titles(app) == ["t0.txt", "t1.txt"] and app.doc()["title"] == "t1.txt"
    app.call("e2e_menu_invoke", context="tab", path="Close")
    assert titles(app) == ["t0.txt"]


# ---- Recent files ---------------------------------------------------------

def recent_titles(app):
    return [i.get("title") for i in app.menu_tree("File|Open Recent", 1)]


@pytest.mark.case("FILE-043")
def test_file_043_a_closed_file_goes_to_the_top_of_open_recent_at_once(app, tmp):
    """FILE-043: A closed file goes to the top of Open Recent at once"""
    app.run("File|Open Recent|Clear Menu")
    r1 = write(tmp / "r1.txt", "1")
    r2 = write(tmp / "r2.txt", "2")
    app.open(r1)
    app.open(r2)
    assert recent_titles(app) == ["Open All Recent Files", "Clear Menu"]
    app.open(r1)
    app.run("IDM_FILE_CLOSE")
    assert recent_titles(app)[0] == "r1.txt"
    app.open(r2)
    app.run("IDM_FILE_CLOSE")
    tree = app.menu_tree("File|Open Recent", 1)
    assert [i.get("title") for i in tree] == ["r2.txt", "r1.txt", None, "Open All Recent Files", "Clear Menu"]
    assert [os.path.realpath(p) for p in app.pref("recentFiles")] == [str(r2), str(r1)]


@pytest.mark.case("FILE-044")
def test_file_044_choosing_a_recent_entry_reopens_the_file_and_takes_it_off_the_list(app, tmp):
    """FILE-044: Choosing a recent entry reopens the file and takes it off the list"""
    back = write(tmp / "back.txt", "back\n")
    app.open(back)
    app.run("IDM_FILE_CLOSE")
    app.call("e2e_menu_invoke", path="File|Open Recent|back.txt")
    assert same(app.doc()["path"], back) and app.text() == "back\n"
    assert not any(App.same_path(p, back) for p in app.pref("recentFiles"))
    assert "back.txt" not in recent_titles(app)


@pytest.mark.case("FILE-045")
def test_file_045_restore_last_closed_file_reopens_the_file_closed_last(app, tmp):
    """FILE-045: Restore Last Closed File reopens the file closed last"""
    x1 = write(tmp / "x1.txt", "1")
    x2 = write(tmp / "x2.txt", "2")
    for x in (x1, x2):
        app.open(x)
        app.run("IDM_FILE_CLOSE")
    app.keys("shift+cmd+t")
    assert same(app.doc()["path"], x2)
    app.keys("shift+cmd+t")
    assert same(app.doc()["path"], x1)
    app.run("File|Open Recent|Clear Menu")
    before = titles(app)
    app.keys("shift+cmd+t")
    assert titles(app) == before and app.modal_log() == []


@pytest.mark.case("FILE-046")
def test_file_046_open_all_recent_files_and_clear_menu(app, tmp):
    """FILE-046: Open All Recent Files and Clear Menu"""
    app.run("File|Open Recent|Clear Menu")
    os_ = [write(tmp / f"o{i}.txt", f"o{i}") for i in (1, 2, 3)]
    for o in os_:
        app.open(o)
        app.run("IDM_FILE_CLOSE")
    os_[1].unlink()
    app.run("File|Open Recent|Open All Recent Files")
    t = titles(app)
    assert "o1.txt" in t and "o3.txt" in t and "o2.txt" not in t
    assert app.running
    app.close_all()
    app.run("File|Open Recent|Clear Menu")
    assert app.pref("recentFiles") == []
    assert recent_titles(app) == ["Open All Recent Files", "Clear Menu"]


@pytest.mark.case("FILE-047")
def test_file_047_a_recent_entry_whose_file_was_deleted_gives_an_error_not_a_tab(app, tmp):
    """FILE-047: A recent entry whose file was deleted gives an error, not a tab"""
    gone = write(tmp / "gone.txt", "g")
    app.open(gone)
    app.run("IDM_FILE_CLOSE")
    gone.unlink()
    n = len(app.docs())
    app.answers(alerts=[1])
    app.call("e2e_menu_invoke", path="File|Open Recent|gone.txt")
    al = alerts(app.modal_log())
    assert len(al) == 1 and "no such file" in al[0]["message"]
    assert len(app.docs()) == n


# ---- Reload ------------------------------------------------------------------

@pytest.mark.case("FILE-048")
def test_file_048_reload_from_disk_takes_the_file_as_it_now_is(app, tmp):
    """FILE-048: Reload from Disk takes the file as it now is"""
    f = write(tmp / "rl.txt", "line1\nline2\nline3\n")
    app.open(f)
    app.select(2, 3)
    rewrite(f, "LINE1\nLINE2\nLINE3\nLINE4\n")
    app.keys("cmd+r")
    assert app.text() == "LINE1\nLINE2\nLINE3\nLINE4\n" and not app.doc()["modified"]
    caret = app.selection()["caret"]
    assert (caret["line"], caret["column"]) == (2, 3)
    assert app.sci(SCI_CANUNDO) == 0
    assert alerts(app.modal_log()) == []


@pytest.mark.case("FILE-049")
def test_file_049_reloading_a_document_with_edits_asks_first(app, tmp):
    """FILE-049: Reloading a document with edits asks first"""
    f = write(tmp / "rl2.txt", "disk\n")
    app.open(f)
    app.set_text("mine\n")
    app.answers(alerts=[2])
    app.run("IDM_FILE_RELOAD")
    al = alerts(app.modal_log())
    assert len(al) == 1 and al[0]["message"] == "Reload" and al[0]["buttons"] == ["Yes", "No"]
    assert al[0]["informative"] == "Are you sure you want to reload the current file and lose the changes made in Notepad++?"
    assert app.text() == "mine\n" and app.doc()["modified"]
    app.answers(alerts=[1])
    app.run("IDM_FILE_RELOAD")
    assert app.text() == "disk\n" and not app.doc()["modified"]


FILE_ONLY = ["IDM_FILE_RELOAD", "IDM_FILE_DELETE", "IDM_FILE_OPEN_FOLDER", "IDM_FILE_OPEN_CMD",
             "IDM_FILE_CONTAININGFOLDERASWORKSPACE", "IDM_FILE_OPEN_DEFAULT_VIEWER"]


@pytest.mark.case("FILE-050")
def test_file_050_file_commands_that_need_a_file_are_unavailable_for_an_untitled_document(app, tmp):
    """FILE-050: File commands that need a file are unavailable for an untitled document"""
    new_tab(app, "text")
    roots = app.call("list_documents")["workspace_roots"]
    states = app.menu(*FILE_ONLY)
    app.run("IDM_FILE_RELOAD", expect_ran=False)
    app.run("IDM_FILE_CONTAININGFOLDERASWORKSPACE", expect_ran=False)
    assert app.modal_log() == []
    assert app.text() == "text" and app.call("list_documents")["workspace_roots"] == roots
    assert all(not states[c]["enabled"] for c in FILE_ONLY), states
    app.open(write(tmp / "saved.txt", "s"))
    assert all(app.menu(*FILE_ONLY)[c]["enabled"] for c in FILE_ONLY)


# ---- Files changed by other programs ---------------------------------------------

@pytest.mark.case("FILE-051")
def test_file_051_a_file_changed_on_disk_is_offered_for_reload_when_the_application_comes_back_to_the_front(app, tmp):
    """FILE-051: A file changed on disk is offered for reload when the application comes back to the front"""
    f = write(tmp / "ext.txt", "v1\n")
    app.open(f)
    rewrite(f, "v2\n")
    app.answers(alerts=[2])
    reactivate(app)
    got = wait_log(app, lambda es: alerts(es))
    al = alerts(got)
    assert al[0]["message"] == "Reload" and al[0]["buttons"] == ["Yes", "No"]
    assert "This file has been modified by another program.\nDo you want to reload it?" in al[0]["informative"]
    assert "ext.txt" in al[0]["informative"]
    assert app.text() == "v1\n"
    reactivate(app)
    app.idle(1.0)
    assert alerts(app.modal_log()) == []
    rewrite(f, "v3\n")
    app.answers(alerts=[1])
    reactivate(app)
    wait_log(app, lambda es: alerts(es))
    app.wait(lambda: app.text() == "v3\n")
    assert not app.doc()["modified"]


@pytest.mark.case("FILE-052")
def test_file_052_a_change_on_disk_to_a_document_with_edits_warns_that_the_edits_will_be_lost(app, tmp):
    """FILE-052: A change on disk to a document with edits warns that the edits will be lost"""
    f = write(tmp / "both.txt", "disk1\n")
    app.open(f)
    app.set_text("mine\n")
    rewrite(f, "disk2\n")
    app.answers(alerts=[2])
    reactivate(app)
    al = alerts(wait_log(app, lambda es: alerts(es)))
    assert "Do you want to reload it and lose the changes made in Notepad++?" in al[0]["informative"]
    assert app.text() == "mine\n" and app.doc()["modified"]


@pytest.mark.case("FILE-053")
def test_file_053_a_change_on_disk_to_a_tab_that_is_not_in_front_is_found_too_and_the_front_tab_stays(app, tmp):
    """FILE-053: A change on disk to a tab that is not in front is found too and the front tab stays"""
    bg = write(tmp / "bg.txt", "old\n")
    fg = write(tmp / "fg.txt", "fg\n")
    app.open(bg)
    app.open(fg)
    rewrite(bg, "new\n")
    app.answers(alerts=[1])
    reactivate(app)
    al = alerts(wait_log(app, lambda es: alerts(es)))
    assert len(al) == 1 and "bg.txt" in al[0]["informative"]
    assert app.text(find_doc(app, bg)["index"]) == "new\n"
    assert same(app.doc()["path"], fg)
    app.run("IDM_WINDOW_MRU_FIRST")
    assert same(app.doc()["path"], bg)


@pytest.mark.case("FILE-054")
def test_file_054_a_file_deleted_from_disk_can_be_kept_or_closed(app, tmp):
    """FILE-054: A file deleted from disk can be kept or closed"""
    d1 = write(tmp / "del1.txt", "one\n")
    d2 = write(tmp / "del2.txt", "two\n")
    app.open(d1)
    app.open(d2)
    d1.unlink()
    d2.unlink()
    app.answers(alerts=[1, 2])
    reactivate(app)
    al = alerts(wait_log(app, lambda es: len(alerts(es)) >= 2))
    assert [a["message"] for a in al] == ["Keep non existing file"] * 2
    assert "doesn't exist anymore.\nKeep this file in editor?" in al[0]["informative"]
    assert "del1.txt" in al[0]["informative"] and "del2.txt" in al[1]["informative"]
    k = find_doc(app, d1)
    assert k and k["modified"] and app.text(k["index"]) == "one\n"
    assert find_doc(app, d2) is None
    assert not any(App.same_path(p, d2) for p in app.pref("recentFiles") or [])
    reactivate(app)
    app.idle(1.0)
    assert alerts(app.modal_log()) == []


# ---- Monitoring --------------------------------------------------------------

@pytest.mark.case("FILE-055")
def test_file_055_monitoring_follows_a_growing_file_to_its_end_and_keeps_it_read_only(app, tmp):
    """FILE-055: Monitoring follows a growing file to its end and keeps it read-only"""
    f = write(tmp / "app.log", "one\n")
    app.open(f)
    app.run("IDM_VIEW_MONITORING")
    try:
        assert app.sci(SCI_GETREADONLY) == 1 and app.doc()["read_only"]
        app.type("x")
        assert app.text() == "one\n"
        with open(f, "a") as h:
            h.write("two\n")
        app.wait(lambda: app.text() == "one\ntwo\n", timeout=10)
        assert app.sci(SCI_GETCURRENTPOS) == len("one\ntwo\n")
    finally:
        app.run("IDM_VIEW_MONITORING")
    app.type("y")
    assert "y" in app.text()


@pytest.mark.case("FILE-055")
def test_file_055_the_monitoring_item_is_checked_while_monitoring(app, tmp):
    """FILE-055 (menu state): the item is checked while on, unchecked after"""
    app.open(write(tmp / "app.log", "one\n"))
    app.run("IDM_VIEW_MONITORING")
    try:
        assert app.doc()["read_only"]
        assert app.checked("IDM_VIEW_MONITORING")
    finally:
        app.run("IDM_VIEW_MONITORING")
    assert not app.checked("IDM_VIEW_MONITORING")


@pytest.mark.case("FILE-056")
def test_file_056_monitoring_refuses_a_modified_or_untitled_document_waits_in_the_background_survives_rotation(app, tmp):
    """FILE-056: Monitoring refuses a modified or untitled document, waits in the background, survives rotation"""
    m = write(tmp / "m.txt", "m\n")
    app.open(m)
    app.set_text("dirty\n")
    app.run("IDM_VIEW_MONITORING")
    assert not app.doc()["read_only"] and app.sci(SCI_GETREADONLY) == 0
    new_tab(app)
    app.run("IDM_VIEW_MONITORING")
    assert not app.doc()["read_only"]
    a = write(tmp / "a.log", "start\n")
    app.open(a)
    app.run("IDM_VIEW_MONITORING")
    try:
        app.open(m)
        with open(a, "a") as h:
            h.write("late\n")
        app.idle(1.0)
        assert app.text(find_doc(app, a)["index"]) == "start\n"
        app.open(a)
        app.wait(lambda: "late" in app.text(), timeout=10)
        os.rename(a, tmp / "a.log.1")
        write(a, "fresh\n")
        app.wait(lambda: app.text() == "fresh\n", timeout=10)
        with open(a, "a") as h:
            h.write("more\n")
        app.wait(lambda: app.text() == "fresh\nmore\n", timeout=10)
        assert app.doc()["read_only"]
    finally:
        app.run("IDM_VIEW_MONITORING")


# ---- Big files ------------------------------------------------------------------

BIG = "".join(f"line {i} café\r\n" for i in range(400))


@pytest.mark.case("FILE-057")
@pytest.mark.parametrize("kind,raw,encoding", [
    ("utf8", BIG.encode("utf-8"), "UTF-8"),
    ("latin1", BIG.encode("latin-1"), "ISO-8859-1"),
    ("bom", b"\xef\xbb\xbf" + BIG.encode("utf-8"), "UTF-8-BOM"),
])
def test_file_057_files_above_the_streaming_threshold_are_read_byte_exact(app, tmp, kind, raw, encoding):
    """FILE-057: Files above the streaming threshold are read byte-exact"""
    f = write(tmp / f"big_{kind}.txt", raw)
    app.invoke("class:EditorController", "setStreamingThreshold:", [1024])
    try:
        d = app.open(f)
    finally:
        app.invoke("class:EditorController", "setStreamingThreshold:", [0])
    assert app.text() == BIG and d["encoding"] == encoding and d["eol"] == "CRLF"
    app.select(1, 1)
    app.type("x")
    app.keys("backspace")
    app.run("IDM_FILE_SAVE")
    assert f.read_bytes() == raw


@pytest.mark.case("FILE-058")
def test_file_058_a_large_file_opens_without_styling(app, tmp):
    """FILE-058: A large file opens without styling"""
    n = 2_500_000 // len("int x; // comment\n") + 1
    big = write(tmp / "big.cpp", "int x; // comment\n" * n)
    small = write(tmp / "small.cpp", "int x;\n")
    app.set_prefs(largeFileThresholdMB=1)
    try:
        d = app.open(big)
        assert d["lines"] == n + 1
        assert app.sci(SCI_GETDOCUMENTOPTIONS) == 257
        app.open(small)
        assert app.sci(SCI_GETDOCUMENTOPTIONS) == 0
    finally:
        app.set_prefs(largeFileThresholdMB=200)


@pytest.mark.case("FILE-059")
def test_file_059_a_huge_file_is_only_opened_after_a_warning(app, tmp):
    """FILE-059: A huge file is only opened after a warning"""
    h = tmp / "huge.bin"
    with open(h, "wb") as fh:
        fh.truncate(2 * 1024 ** 3)
    try:
        n = len(app.docs())
        app.answers(panels=[str(h)], alerts=["No", 1])
        app.run("IDM_FILE_OPEN")
        al = alerts(app.modal_log())
        assert al[0]["message"] == "Opening huge file warning" and al[0]["buttons"] == ["Yes", "No"]
        assert al[0]["informative"] == "Opening a huge file of 2GB+ could take several minutes.\nDo you want to open it?"
        assert len(app.docs()) == n
        assert len(al) == 1, [a["message"] for a in al]
    finally:
        h.unlink()


# ---- Containing folder, default viewer, workspace ----------------------------------

@pytest.mark.case("FILE-060")
def test_file_060_open_containing_folder_in_finder_selects_the_file(app, tmp):
    """FILE-060: Open Containing Folder in Finder selects the file"""
    f = write(tmp / "sub/f.txt", "f")
    app.open(f)
    app.run("IDM_FILE_OPEN_FOLDER")
    entries = app.modal_log()
    assert len(entries) == 1 and entries[0]["kind"] == "reveal" and same(entries[0]["target"], f)


@pytest.mark.case("FILE-061")
def test_file_061_open_containing_folder_in_terminal_cmd_and_powershell(app, tmp):
    """FILE-061: Open Containing Folder in Terminal (cmd and PowerShell)"""
    f = write(tmp / "sub/f.txt", "f")
    app.open(f)

    def check():
        entries = app.modal_log()
        assert len(entries) == 1 and entries[0]["kind"] == "open_url_with"
        folder, _, appl = entries[0]["target"].partition(" -> ")
        assert same(folder, tmp / "sub") and appl.endswith("Terminal.app")
    app.run("IDM_FILE_OPEN_CMD")
    check()
    app.run("IDM_FILE_OPEN_POWERSHELL")
    check()


@pytest.mark.case("FILE-062")
def test_file_062_open_in_default_viewer_hands_the_file_to_its_application(app, tmp):
    """FILE-062: Open in Default Viewer hands the file to its application"""
    f = write(tmp / "page.html", "<p>x</p>\n")
    app.open(f)
    app.run("IDM_FILE_OPEN_DEFAULT_VIEWER")
    entries = app.modal_log()
    assert len(entries) == 1 and entries[0]["kind"] in ("open_url", "open_file") and same(entries[0]["target"], f)
    assert same(app.doc()["path"], f) and app.text() == "<p>x</p>\n"


@pytest.mark.case("FILE-063")
def test_file_063_open_containing_folder_as_workspace_roots_the_panel_at_the_file_s_folder(app, tmp):
    """FILE-063: Open Containing Folder as Workspace roots the panel at the file's folder"""
    a = write(tmp / "ws/a.txt", "a")
    write(tmp / "ws/b.py", "b")
    app.open(a)
    try:
        app.run("IDM_FILE_CONTAININGFOLDERASWORKSPACE")
        app.run("IDM_FILE_CONTAININGFOLDERASWORKSPACE")
        roots = app.call("list_documents")["workspace_roots"]
        assert len(roots) == 1 and same(roots[0], tmp / "ws")
        assert app.invoke("editor", "workspaceVisible") in (True, 1)
        names = app.invoke("editor", "workspaceTopLevelNames")
        assert sorted(names) == ["a.txt", "b.py"]
    finally:
        app.invoke("editor", "openFolderAsWorkspace:", [None])


@pytest.mark.case("FILE-064")
def test_file_064_open_folder_as_workspace_adds_the_chosen_folders_as_roots(app, tmp):
    """FILE-064: Open Folder as Workspace adds the chosen folders as roots"""
    r1, r2 = tmp / "r1", tmp / "r2"
    write(r1 / "one.txt", "1")
    write(r2 / "two.txt", "2")
    try:
        app.answers(panels=[str(r1)])
        app.run("IDM_FILE_OPENFOLDERASWORKSPACE")
        p = panels(app.modal_log())
        assert len(p) == 1 and p[0]["kind"] == "open" and p[0].get("can_choose_directories") in (True, 1)
        roots = app.call("list_documents")["workspace_roots"]
        assert [os.path.realpath(r) for r in roots] == [str(r1)]
        app.answers(panels=[str(r2)])
        app.run("IDM_FILE_OPENFOLDERASWORKSPACE")
        app.answers(panels=[None])
        app.run("IDM_FILE_OPENFOLDERASWORKSPACE")
        roots = app.call("list_documents")["workspace_roots"]
        assert [os.path.realpath(r) for r in roots] == [str(r1), str(r2)]
        assert app.invoke("editor", "workspaceVisible") in (True, 1)
    finally:
        app.invoke("editor", "openFolderAsWorkspace:", [None])


# ---- Move to Trash ---------------------------------------------------------------

@pytest.mark.case("FILE-065")
def test_file_065_move_to_trash_asks_then_trashes_the_file_and_closes_its_tab(app, tmp):
    """FILE-065: Move to Trash asks, then trashes the file and closes its tab"""
    name = f"trash_me_{uuid.uuid4().hex[:8]}.txt"
    victim = write(tmp / name, "bye")
    stay = write(tmp / "stay.txt", "stay")
    app.open(stay)
    app.open(victim)
    with pytest.raises(ToolError, match="left to the user"):
        app.run("IDM_FILE_DELETE")
    assert victim.exists()
    try:
        app.answers(alerts=["No"])
        app.call("e2e_menu_invoke", path="File|Move to Trash")
        al = alerts(app.modal_log())
        assert len(al) == 1 and al[0]["message"] == "Delete file" and al[0]["buttons"] == ["Yes", "No"]
        assert "will be moved to your Trash and this document will be closed.\nContinue?" in al[0]["informative"]
        assert name in al[0]["informative"]
        assert victim.exists() and find_doc(app, victim)
        app.answers(alerts=["Yes"])
        app.call("e2e_menu_invoke", path="File|Move to Trash")
        assert not victim.exists() and find_doc(app, victim) is None
        assert same(app.doc()["path"], stay)
        assert not any(name in p for p in app.pref("recentFiles") or [])
    finally:
        trashed = Path.home() / ".Trash" / name
        if trashed.exists():
            trashed.unlink()


# ---- Print -----------------------------------------------------------------------

def print_entries(entries):
    return [e for e in entries if e.get("kind") == "print"]


def no_printer_here(app):
    """Printing runs only where no printer is set up (the test VM) and only against a build
    whose print hook turns every job into a PDF and refuses anything else."""
    import subprocess
    printers = subprocess.run(["lpstat", "-p"], capture_output=True, text=True).stdout.strip()
    if printers:
        pytest.skip("a printer is set up on this machine: print tests run only in the VM")
    assert b"refused a print job that would reach a printer" in app.executable.read_bytes(), \
        "the build has no print guard: not printing"


@pytest.mark.case("FILE-066")
def test_file_066_print_shows_the_print_panel_and_cancel_prints_nothing(app, tmp):
    """FILE-066: Print shows the print panel (the hook saves the job as a PDF instead of printing)"""
    no_printer_here(app)
    f = write(tmp / "print.txt", "alpha\nbeta\n")
    app.open(f)
    app.keys("cmd+p")
    pe = print_entries(app.modal_log())
    assert len(pe) == 1 and pe[0]["job_title"] == "print.txt" and pe[0]["shows_panel"] in (True, 1)
    assert os.path.exists(pe[0]["path"])
    assert "alpha" in pdf_text(pe[0]["path"])
    assert app.text() == "alpha\nbeta\n" and not app.doc()["modified"]


@pytest.mark.case("FILE-067")
def test_file_067_print_now_prints_the_document_with_the_print_settings_and_no_panel(app, tmp):
    """FILE-067: Print Now prints the document with the print settings and no panel"""
    no_printer_here(app)
    f = write(tmp / "pn.txt", "alpha\nbeta\ngamma\n")
    app.open(f)
    app.set_prefs(printLineNumbers=True, printHeaderLeft="$(FILE_NAME)")
    try:
        app.keys("shift+cmd+p")
        pe = print_entries(app.modal_log())
        assert len(pe) == 1 and pe[0]["job_title"] == "pn.txt" and pe[0]["shows_panel"] in (False, 0)
        text = pdf_text(pe[0]["path"])
        assert "gamma" in text
        assert "1  alpha" in text and "3  gamma" in text and "pn.txt" in text
    finally:
        app.set_prefs(printLineNumbers=False, printHeaderLeft="$(FULL_CURRENT_PATH)")


# ---- Exit -------------------------------------------------------------------------

@pytest.mark.case("FILE-068")
def test_file_068_exit_with_unsaved_changes_asks_and_cancel_keeps_the_application_running(app):
    """FILE-068: Exit with unsaved changes asks, and Cancel keeps the application running"""
    with pytest.raises(ToolError, match="left to the user"):
        app.run("IDM_FILE_EXIT")
    new_tab(app, "dirty")
    app.answers(alerts=[3])
    app.keys("cmd+q")
    al = alerts(app.modal_log())
    assert len(al) == 1 and al[0]["message"] == "Save" and al[0]["buttons"] == ["Yes", "No", "Cancel"]
    assert app.running and app.text() == "dirty"
    app.answers(alerts=[3])
    app.call("e2e_menu_invoke", path="NotepadMac|Quit NotepadMac")
    assert len(alerts(app.modal_log())) == 1
    assert app.running and app.text() == "dirty" and app.doc()["title"] == "new 2"


@pytest.mark.case("FILE-069")
def test_file_069_exit_quits_saving_only_what_the_user_says(app, tmp):
    """FILE-069: Exit quits, saving only what the user says"""
    f = write(tmp / "exit.txt", "v1")
    app.open(f)
    app.set_text("v2")
    try:
        app.answers(alerts=[2])
        try:
            app.keys("cmd+q")
        except Exception:  # noqa: BLE001 - the connection may close under the call
            pass
        assert app.proc.wait(15) == 0
        assert f.read_text() == "v1"
        app.stop()
        app.start()
        try:
            app.keys("cmd+q")
        except Exception:  # noqa: BLE001
            pass
        assert app.proc.wait(15) == 0
        app.stop()
    finally:
        if not app.running:
            app.start()
