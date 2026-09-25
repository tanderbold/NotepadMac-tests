"""PERF: how NotepadMac copes with large inputs (wall time and memory).

Each test builds its input on the fly (nothing large is stored in the repository), drives the
application the way a user would (the Find dialog, the menus, key presses) and measures wall time
through the agent socket and the application's resident memory (RSS, from ps) while it works.

The limits are generous on purpose (several times what a run in the test VM measures): they are
there to catch a pathological regression - an O(n^2) step, a whole-document copy per keystroke -
not to grade a machine. Every number is printed (run with -s to see them) and appended to
.work/<worker>/perf.jsonl.

All tests are marked slow.
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import threading
import time
from pathlib import Path

import pytest

from harness.app import Connection
from harness.sci import (SCI_COLOURISE, SCI_DOCUMENTEND, SCI_GETENDSTYLED, SCI_GETLENGTH, SCI_GETLEXER,
                         SCI_GETLINE, SCI_GETLINECOUNT, SCI_GETWRAPMODE, SCI_GOTOPOS, SCI_LINEEND)
from _util_search import fresh_dlg, wait_search_done

pytestmark = [pytest.mark.slow, pytest.mark.timeout(1800)]

MB = 1024 * 1024

# Limits in seconds (and MB for memory): about ten times what a run in the test VM measured
# (4 cores, 6 GB), with a floor for the quick ones; the numbers of that run are in the comments.
LIMITS = {
    "open_10mb_cpp": 7,               # 0.7
    "colourise_10mb_cpp": 3,          # 0.31
    "goto_end_10mb_cpp": 2,           # 0.06
    "open_100mb_cpp": 60,             # 6.2
    "goto_end_100mb_cpp": 5,          # 0.09
    "rss_100mb_cpp_mb": 2500,         # 690
    "open_5mb_line": 8,               # 0.8
    "line_end_5mb_line": 5,           # 0.46
    "type_5mb_line": 6,               # 0.63 (three characters)
    "wrap_5mb_line": 5,               # 0.25
    "open_1gb": 70,                   # 6.7
    "rss_1gb_mb": 4500,               # 1840
    "goto_end_1gb": 5,                # 0.09
    "count_1gb": 60,                  # 6.3
    "open_100_tabs": 70,              # 6.8
    "cycle_100_tabs": 40,             # 4.5
    "close_100_tabs": 5,              # 0.2
    "session_load_100": 50,           # 4.6
    "session_close_100": 5,           # 0.5
    "find_all_100mb": 10,             # 0.73
    "regex_replace_1m": 120,          # 10.1 (linear since the text around a match is built only for $` and $')
    "find_in_files_20k": 20,          # 1.8
    "compare_50k_lines": 5,           # 0.47
    "doc_map_10mb": 3,                # 0.2
    "doc_map_end_10mb": 5,            # 0.49, 0.3 of it waiting
    "function_list_10mb": 25,         # 2.35
    "function_list_tool_10mb": 25,    # 2.5
    "keystroke_10mb_median": 0.2,     # 0.018
    "keystroke_10mb_max": 1.0,        # 0.037
}


# ---- measuring --------------------------------------------------------------

def rss_mb(app) -> float:
    r = subprocess.run(["ps", "-o", "rss=", "-p", str(app.proc.pid)], capture_output=True, text=True)
    try:
        return int(r.stdout.strip()) / 1024.0
    except ValueError:
        return 0.0


class Peak:
    """The application's highest RSS while a block runs (sampled every 50 ms)."""

    def __init__(self, app):
        self.app, self.peak, self._stop = app, 0.0, threading.Event()

    def __enter__(self):
        self.peak = rss_mb(self.app)
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
        return self

    def _run(self):
        while not self._stop.wait(0.05):
            self.peak = max(self.peak, rss_mb(self.app))

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join()
        self.peak = max(self.peak, rss_mb(self.app))


def record(app, name, seconds=None, **extra):
    row = {"name": name, **({"seconds": round(seconds, 3)} if seconds is not None else {}), **extra}
    print(f"PERF {json.dumps(row)}")
    with open(app.work / "perf.jsonl", "a") as f:
        f.write(json.dumps(row) + "\n")
    return row


LONG = 900.0


def timed(app, name, fn, limit_key=None, **extra):
    """Runs fn, records its wall time and the peak RSS, checks the limit; returns fn's result.

    A call that takes three times its limit is given up on (the connection times out), so a
    pathological case fails in bounded time; the fixture then restarts the application."""
    limit = LIMITS.get(limit_key or name)
    if limit is not None and app.conn:
        app.conn.sock.settimeout(max(60.0, min(3 * limit, 900.0)))
    try:
        with Peak(app) as p:
            t = time.monotonic()
            try:
                result = fn()
            except (TimeoutError, OSError):
                record(app, name, time.monotonic() - t, rss_peak_mb=round(p.peak), gave_up=True, **extra)
                raise
            dt = time.monotonic() - t
    finally:
        if app.conn:
            app.conn.sock.settimeout(LONG)
    record(app, name, dt, rss_peak_mb=round(p.peak), **extra)
    if limit is not None:
        assert dt < limit, f"{name}: {dt:.2f}s, the limit is {limit}s"
    return result


def responsive(app) -> bool:
    """Whether the application answers within a few seconds (not still busy with a call given up on)."""
    try:
        c = Connection(app.socket_path, timeout=15)
        try:
            c.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "npp-tests-perf", "version": "1"}})
            c.request("tools/call", {"name": "e2e_idle", "arguments": {"seconds": 0}})
        finally:
            c.close()
        return True
    except (OSError, TimeoutError, ConnectionError):
        return False


@pytest.fixture
def perf(app_session, app):
    """The app with a connection that waits long enough for a slow tool, put back afterwards.
    An application still busy with a call the test gave up on is quit, to start afresh."""
    short = app.conn
    app.conn = Connection(app.socket_path, timeout=LONG)
    app.conn.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                    "clientInfo": {"name": "npp-tests-perf", "version": "1"}})
    app.conn.notify("notifications/initialized")
    yield app
    if not app.running or not responsive(app):
        record(app, "restarted_after_test")
        app_session.stop()
        return
    try:
        app.answers(clear=True)
        app.close_all()
    finally:
        record(app, "rss_after_test", rss_mb=round(rss_mb(app)))
        app.conn.close()
        app.conn = short


def press(app, d, title):
    """A dialog button, through the long connection (Find All in 100 MB takes a while)."""
    r = app.call("e2e_act", window=d.number, action="click", target={"title": title, "class": "NSButton"})
    assert r.get("acted"), r


# ---- inputs -------------------------------------------------------------------

def cpp_block(i: int, needle: bool = False) -> str:
    """About 330 bytes of C++: a comment, a function, a loop, a string."""
    return (f"// block {i}{' needle' if needle else ''}\n"
            f"static int func_{i}(int a, int b)\n"
            "{\n"
            f"    int total_{i} = a * {i % 97} + b;   /* note {i} */\n"
            f"    for (int k = 0; k < {i % 13}; ++k) {{\n"
            f"        total_{i} += k ^ 0x{i & 0xffff:04x};\n"
            "    }\n"
            f"    if (total_{i} > 1000) return total_{i} - \"string {i}\"[0];\n"
            f"    return total_{i};\n"
            "}\n\n")


def write_cpp(path: Path, size: int, needle_every: int = 0) -> int:
    """A C++ file of about size bytes; returns the number of needle lines."""
    needles, written, i = 0, 0, 0
    with open(path, "w") as f:
        while written < size:
            parts = []
            for _ in range(2000):
                hit = bool(needle_every) and i % needle_every == 0
                needles += hit
                parts.append(cpp_block(i, hit))
                i += 1
            chunk = "".join(parts)
            f.write(chunk)
            written += len(chunk)
    return needles


@pytest.fixture(scope="module")
def inputs(tmp_path_factory):
    root = Path(os.path.realpath(tmp_path_factory.mktemp("perf")))
    return root


def cpp10(inputs) -> Path:
    p = inputs / "ten.cpp"
    if not p.exists():
        write_cpp(p, 10 * MB)
    return p


# ---- files --------------------------------------------------------------------

def test_perf_001_a_10mb_cpp_file_opens_styles_and_scrolls(perf, inputs):
    """PERF-001: a 10 MB C++ file opens, is styled to the end and scrolled to its end in bounded time."""
    app = perf
    path = cpp10(inputs)
    doc = timed(app, "open_10mb_cpp", lambda: app.open(path), size_mb=10)
    assert doc["language"].lower() in ("c++", "cpp"), doc
    assert app.sci(SCI_GETLEXER) != 1          # a real lexer, not SCLEX_NULL
    n = app.sci(SCI_GETLENGTH)
    timed(app, "colourise_10mb_cpp", lambda: app.sci(SCI_COLOURISE, 0, -1))
    assert app.sci(SCI_GETENDSTYLED) == n
    timed(app, "goto_end_10mb_cpp", lambda: (app.sci(SCI_DOCUMENTEND), app.idle(0.05)))


def test_perf_002_a_100mb_cpp_file_opens_and_scrolls_to_its_end(perf, inputs):
    """PERF-002: a 100 MB C++ file (below the large-file threshold) opens and scrolls to its end."""
    app = perf
    path = inputs / "hundred.cpp"
    write_cpp(path, 100 * MB)
    timed(app, "open_100mb_cpp", lambda: app.open(path), size_mb=100)
    lines = app.sci(SCI_GETLINECOUNT)
    timed(app, "goto_end_100mb_cpp", lambda: (app.select(lines), app.idle(0.05)))
    mem = rss_mb(app)
    record(app, "rss_100mb_cpp", rss_mb=round(mem))
    assert mem < LIMITS["rss_100mb_cpp_mb"]
    app.close_all()
    path.unlink()


def test_perf_003_a_5mb_single_line_opens_edits_and_wraps(perf, inputs):
    """PERF-003: a file of one 5 MB line: open, End, typing at its end, word wrap on and off."""
    app = perf
    path = inputs / "oneline.js"
    word = "var x1 = [1, 2, 'three', {a: 4}]; "
    path.write_text(word * (5 * MB // len(word)) + "\n")
    timed(app, "open_5mb_line", lambda: app.open(path), size_mb=5)
    timed(app, "line_end_5mb_line", lambda: (app.sci(SCI_GOTOPOS, 0), app.sci(SCI_LINEEND), app.idle(0.05)))
    n = app.sci(SCI_GETLENGTH)
    timed(app, "type_5mb_line", lambda: app.type("abc"))
    assert app.sci(SCI_GETLENGTH) == n + 3
    wrap = app.sci(SCI_GETWRAPMODE)
    try:
        timed(app, "wrap_5mb_line", lambda: (app.run("IDM_VIEW_WRAP"), app.idle(0.05)))
        assert app.sci(SCI_GETWRAPMODE) != wrap
    finally:
        if app.sci(SCI_GETWRAPMODE) != wrap:
            app.run("IDM_VIEW_WRAP")


# The CI runner has about 7 GB of memory: a 1 GB file (written, then held by the application, which
# measures 1.8 GB) is more than it can spare beside the rest. The other cases run there.
@pytest.mark.skipif(bool(os.environ.get("CI")), reason="the CI runner (7 GB) cannot hold a 1 GB file beside the rest")
def test_perf_004_a_1gb_file_opens_on_the_large_file_path(perf, inputs):
    """PERF-004: a 1 GB file is above the large-file threshold (200 MB, as upstream): it opens without
    styling (SC_DOCUMENTOPTION_STYLES_NONE, no lexer), and scrolling and Count stay bounded."""
    app = perf
    path = inputs / "huge.cpp"          # a C++ name: a large file is Normal text all the same
    block = "".join(cpp_block(i, i % 1000 == 0) for i in range(30000)).encode()
    reps = (1024 * MB) // len(block) + 1
    with open(path, "wb") as f:
        for _ in range(reps):
            f.write(block)
    try:
        timed(app, "open_1gb", lambda: app.open(path), size_mb=round(path.stat().st_size / MB))
        mem = rss_mb(app)
        record(app, "rss_1gb", rss_mb=round(mem))
        assert mem < LIMITS["rss_1gb_mb"]
        assert app.sci(SCI_GETLEXER) in (0, 1), "no lexer on a large file"
        assert app.doc()["language"].lower() in ("normal text", "normal", "text"), app.doc()
        timed(app, "goto_end_1gb", lambda: (app.sci(SCI_DOCUMENTEND), app.idle(0.05)))
        d = fresh_dlg(app)
        d.set("what", "needle")
        timed(app, "count_1gb", lambda: press(app, d, "Count"))
        assert d.status() == f"Count: {30 * reps} matches"
        d.close()
    finally:
        app.close_all()
        path.unlink()


# ---- many documents -------------------------------------------------------------

def many_files(inputs, n=100, size=64 * 1024) -> list[Path]:
    folder = inputs / "many"
    folder.mkdir(exist_ok=True)
    out = []
    for i in range(n):
        p = folder / f"file{i:03d}.cpp"
        if not p.exists():
            write_cpp(p, size)
        out.append(p)
    return out


def test_perf_005_a_hundred_tabs_open_cycle_and_close(perf, inputs):
    """PERF-005: 100 files of 64 KB open as 100 tabs, Next Tab walks all of them, Close All closes them."""
    app = perf
    files = many_files(inputs)
    timed(app, "open_100_tabs", lambda: [app.open(p) for p in files])
    assert len(app.docs()) == 100
    # Through run_command, as an agent would: by the shortcut, AppKit throttles a key equivalent
    # repeated this fast (NSMENU_IS_THROTTLING_REPEATED_MENU_ITEM_INVOCATIONS, ~140 ms each), which
    # would be all that is measured. run_command's own look-up of the command is ~15 ms of each step.
    first = app.doc()["title"]
    timed(app, "cycle_100_tabs", lambda: [app.run("IDM_VIEW_TAB_NEXT") for _ in range(100)])
    assert app.doc()["title"] == first
    timed(app, "close_100_tabs", lambda: app.run("IDM_FILE_CLOSEALL"))
    assert len(app.docs()) == 1


def test_perf_006_a_session_of_a_hundred_documents_loads_and_closes(perf, inputs):
    """PERF-006: a session file naming 100 documents loads, and Close All closes them."""
    app = perf
    files = many_files(inputs)
    session = inputs / "hundred.session.xml"
    session.write_text('<?xml version="1.0" encoding="UTF-8" ?>\n<NotepadPlus>\n'
                       '    <Session activeView="0">\n        <mainView activeIndex="0">\n'
                       + "".join(f'            <File firstVisibleLine="0" xOffset="0" scrollWidth="1" '
                                 f'startPos="0" endPos="0" selMode="0" offset="0" wrapCount="1" '
                                 f'lang="C++" encoding="-1" userReadOnly="no" filename="{p}" '
                                 f'backupFilePath="" originalFileLastModifTimestamp="0" '
                                 f'originalFileLastModifTimestampHigh="0" tabColourId="-1" '
                                 f'mapFirstVisibleDisplayLine="-1" mapFirstVisibleDocLine="-1" '
                                 f'mapLastVisibleDocLine="-1" mapNbLine="-1" mapHigherPos="-1" '
                                 f'mapWidth="-1" mapHeight="-1" mapKByteInDoc="0" mapWrapIndentMode="-1" '
                                 f'mapIsWrap="no" />\n' for p in files)
                       + '        </mainView>\n        <subView activeIndex="0" />\n    </Session>\n</NotepadPlus>\n')

    def load():
        app.answers(panels=[str(session)], clear=True)
        app.run("IDM_FILE_LOADSESSION")
    timed(app, "session_load_100", load)
    assert len(app.docs()) == 100
    timed(app, "session_close_100", lambda: app.run("IDM_FILE_CLOSEALL"))
    assert len(app.docs()) == 1


# ---- search -------------------------------------------------------------------

def test_perf_007_find_all_in_a_100mb_file(perf, inputs):
    """PERF-007: Find All in Current Document in a 100 MB file lists every needle line."""
    app = perf
    path = inputs / "find100.cpp"
    hits = write_cpp(path, 100 * MB, needle_every=10)
    timed(app, "open_100mb_cpp_for_find", lambda: app.open(path), limit_key="open_100mb_cpp")
    d = fresh_dlg(app)
    d.set("what", "needle")
    timed(app, "find_all_100mb", lambda: press(app, d, "Find All in Current Document"), hits=hits)
    # The report is more than get_document returns (a million characters): its last line is read.
    last = app.sci(SCI_GETLINE, app.sci(SCI_GETLINECOUNT) - 2, 0, returns="string")
    assert last.strip() == f"{hits} hits", last
    path.unlink()


def test_perf_008_regex_replace_all_with_a_million_matches(perf, inputs):
    """PERF-008: Replace All of a regular expression that matches 1,000,000 times."""
    app = perf
    app.new("".join(f"value = {i};\n" for i in range(1_000_000)))
    d = fresh_dlg(app, "IDM_SEARCH_REPLACE")
    d.set("what", r"\d+")
    d.set("with", "N")
    d.set_mode(2)
    try:
        timed(app, "regex_replace_1m", lambda: press(app, d, "Replace All"), matches=1_000_000)
        assert d.status() == "Replace All: 1000000 occurrences were replaced"
        assert app.text()[:22] == "value = N;\nvalue = N;\n"
    finally:
        d.set_mode(0)
        d.close()


def test_perf_009_find_in_files_over_twenty_thousand_files(perf, inputs):
    """PERF-009: Find in Files over a tree of 20,000 files (200 folders of 100)."""
    app = perf
    root = inputs / "tree"
    expected = 0
    for f in range(200):
        folder = root / f"dir{f:03d}"
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(100):
            n = f * 100 + i
            hit = n % 10 == 0
            expected += hit
            (folder / f"src{i:03d}.c").write_text(cpp_block(n, hit) * 3)
    d = fresh_dlg(app, "IDM_SEARCH_FINDINFILES")
    d.set("what", "needle")
    d.set("dir", str(root))

    def run():
        press(app, d, "Find All")
        return wait_search_done(d, timeout=LIMITS["find_in_files_20k"] * 2)
    status = timed(app, "find_in_files_20k", run, files=20000)
    record(app, "find_in_files_20k_status", status=status)
    assert f"{expected * 3} " in status or str(expected * 3) in status, status


# ---- compare --------------------------------------------------------------------

def test_perf_010_compare_two_50k_line_files(perf, inputs):
    """PERF-010: Compare of two 50,000-line files with scattered differences (changed, added, removed)."""
    app = perf
    old = [f"line {i}: int value_{i} = {i * 7 % 1000};" for i in range(50000)]
    new = list(old)
    for i in range(250, 50000, 500):
        new[i] = new[i].replace("int", "long")          # 100 changed
    for i in range(49900, 0, -1000):
        new.insert(i, f"// added before {i}")          # 50 added
    for i in range(49700, 0, -2000):
        del new[i]                                     # 25 removed
    a, b = inputs / "cmp_old.txt", inputs / "cmp_new.txt"
    a.write_text("\n".join(old) + "\n")
    b.write_text("\n".join(new) + "\n")
    from _util_compare import CLEAR_ALL, WITH_FILE, restore_options
    restore_options(app)
    app.open(b)

    def run():
        app.answers(panels=[str(a)], clear=True)
        app.run(WITH_FILE)
        return app.modal_log()
    try:
        log = timed(app, "compare_50k_lines", run, lines=50000)
        summary = [e.get("informative") for e in log if e.get("kind") == "alert"]
        record(app, "compare_50k_summary", summary=summary)
    finally:
        app.run(CLEAR_ALL)
        app.modal_log(clear=True)


# ---- panels ---------------------------------------------------------------------

def panel_shown(app, name):
    return bool(app.invoke("class:NppDockingManager", "isPanelVisible:", [name]))


def test_perf_011_document_map_of_a_10mb_file(perf, inputs):
    """PERF-011: the Document Map shown over a 10 MB file, then following it to its end."""
    app = perf
    app.open(cpp10(inputs))
    assert not panel_shown(app, "documentMap")
    try:
        timed(app, "doc_map_10mb", lambda: (app.run("IDM_VIEW_DOC_MAP"), app.idle(0.05)))
        assert panel_shown(app, "documentMap")
        timed(app, "doc_map_end_10mb", lambda: (app.sci(SCI_DOCUMENTEND), app.idle(0.3)))
    finally:
        if panel_shown(app, "documentMap"):
            app.run("IDM_VIEW_DOC_MAP")


def test_perf_012_function_list_of_a_10mb_file(perf, inputs):
    """PERF-012: the Function List of a 10 MB C++ file (about 30,000 functions), panel and agent tool."""
    app = perf
    app.open(cpp10(inputs))
    assert not panel_shown(app, "functionList")
    try:
        timed(app, "function_list_10mb", lambda: app.run("IDM_VIEW_FUNC_LIST"))
        count = app.get("app", "funcList.entries.@count")
        record(app, "function_list_10mb_entries", entries=count)
        assert count > 25000, count
    finally:
        if panel_shown(app, "functionList"):
            app.run("IDM_VIEW_FUNC_LIST")
    r = timed(app, "function_list_tool_10mb", lambda: app.call("function_list"))
    assert len(r["entries"]) > 25000


# ---- typing -----------------------------------------------------------------------

def test_perf_013_a_keystroke_lands_quickly_in_a_10mb_document(perf, inputs):
    """PERF-013: time from a key press to its character in the document, in the middle of a 10 MB C++ file
    (styled, change history on): 40 keystrokes, median and worst."""
    app = perf
    app.open(cpp10(inputs))
    lines = app.sci(SCI_GETLINECOUNT)
    app.select(lines // 2, 5)
    app.idle(0.2)
    n = app.sci(SCI_GETLENGTH)
    times = []
    with Peak(app) as p:
        for i in range(40):
            t = time.monotonic()
            app.type("x")
            while app.sci(SCI_GETLENGTH) != n + i + 1:
                pass
            times.append(time.monotonic() - t)
    med, worst = statistics.median(times), max(times)
    record(app, "keystroke_10mb", median=round(med, 4), max=round(worst, 4), rss_peak_mb=round(p.peak))
    assert med < LIMITS["keystroke_10mb_median"]
    assert worst < LIMITS["keystroke_10mb_max"]
