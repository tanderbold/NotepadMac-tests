"""AGENT: end-to-end tests (plan: plan/AGENT.md).

The product's MCP interface: the protocol, the socket, the nppmac bridge and the 21 tools.
"""
import json
import os
import plistlib
import socket
import stat
import subprocess
import threading
import time
from pathlib import Path

import pytest

from harness.app import ToolError, wait_for
from harness.sci import *  # noqa: F401,F403
from _util_agent import (INIT, Raw, bridge, call_raw, err, product_tools, raw, read_json_line,
                         restart_default, short_dir)

TOOL_ORDER = ["list_documents", "get_document", "get_selection", "open_document", "close_document", "go_to",
              "edit_document", "save_document", "bookmarks", "list_commands", "run_command", "detect_language",
              "tokens", "function_list", "find", "replace", "compare", "file_encoding", "ocr", "read_qr",
              "spell_check"]


def _ping(ident):
    return {"jsonrpc": "2.0", "id": ident, "method": "ping"}


# ---------------------------------------------------------------- Protocol


@pytest.mark.case("AGENT-001")
def test_agent_001_initialize_names_the_server_and_negotiates_the_protocol_vers(app):
    """AGENT-001: initialize names the server and negotiates the protocol version"""
    with open(app.bundle / "Contents/Info.plist", "rb") as f:
        version = plistlib.load(f)["CFBundleShortVersionString"]
    with raw(app) as c:
        for ident, asked, want in [(1, "2024-11-05", "2024-11-05"), (2, "2025-03-26", "2025-03-26"),
                                   (3, "2025-06-18", "2025-06-18"), (4, "1999-01-01", "2025-06-18")]:
            r = c.request(ident, "initialize", {"protocolVersion": asked, "capabilities": {},
                                                "clientInfo": {"name": "t", "version": "1"}})
            assert r["id"] == ident
            res = r["result"]
            assert res["protocolVersion"] == want
            assert res["serverInfo"]["name"] == "NotepadMac"
            assert res["serverInfo"]["title"] == "NotepadMac (Notepad++ for macOS)"
            assert res["serverInfo"]["version"] == version
            assert res["capabilities"]["tools"]["listChanged"] is False
            assert "one-based" in res["instructions"]


@pytest.mark.case("AGENT-002")
def test_agent_002_ping_answers_with_an_empty_result_and_ids_come_back_exactly(app):
    """AGENT-002: ping answers with an empty result and ids come back exactly as sent"""
    ids = [0, "abc", 9007199254740991, -5]
    with raw(app) as c:
        for i in ids:
            c.send_json(_ping(i))
        got = [c.line() for _ in ids]
    for i, r in zip(ids, got):
        assert r == {"jsonrpc": "2.0", "id": i, "result": {}}
        assert type(r["id"]) is type(i)


@pytest.mark.case("AGENT-003")
def test_agent_003_tools_list_describes_exactly_the_21_product_tools_with_usabl(app):
    """AGENT-003: tools/list describes exactly the 21 product tools with usable schemas"""
    tools = product_tools(app)
    assert [t["name"] for t in tools] == TOOL_ORDER
    required = {"go_to": ["line"], "run_command": ["command"], "find": ["what"],
                "replace": ["what", "replacement"], "compare": ["left", "right"], "file_encoding": ["path"],
                "ocr": ["path"], "read_qr": ["path"], "detect_language": ["text"]}
    for t in tools:
        assert t["description"].strip()
        s = t["inputSchema"]
        assert s["type"] == "object" and s["additionalProperties"] is False
        assert sorted(s["required"]) == sorted(required.get(t["name"], [])), t["name"]
        if "document" in s["properties"]:
            assert set(s["properties"]["document"]["type"]) == {"string", "integer"}


@pytest.mark.case("AGENT-004")
def test_agent_004_an_unknown_method_is_a_json_rpc_error_not_a_crash(app):
    """AGENT-004: An unknown method is a JSON-RPC error, not a crash"""
    with raw(app) as c:
        r = c.request(3, "resources/list")
        assert r["id"] == 3
        assert r["error"]["code"] == -32601
        assert r["error"]["message"] == "Method not found: resources/list"
        assert c.request(4, "ping") == {"jsonrpc": "2.0", "id": 4, "result": {}}


@pytest.mark.case("AGENT-005")
def test_agent_005_notifications_never_get_a_reply(app):
    """AGENT-005: Notifications never get a reply"""
    with raw(app) as c:
        for m in [{"jsonrpc": "2.0", "method": "notifications/initialized"},
                  {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}},
                  {"jsonrpc": "2.0", "method": "foo/bar"},
                  {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "nope"}}]:
            c.send_json(m)
        c.send_json(_ping(9))
        got = c.lines_for(1.0)
    assert got == [{"jsonrpc": "2.0", "id": 9, "result": {}}]


@pytest.mark.case("AGENT-006")
def test_agent_006_a_line_that_is_not_json_gets_a_parse_error_and_the_connectio(app):
    """AGENT-006: A line that is not JSON gets a parse error and the connection goes on"""
    with raw(app) as c:
        c.send(b"not json\n")
        c.send(b'{"a":"\xff\xfe"}\n')
        c.send_json(_ping(7))
        a, b, p = c.line(), c.line(), c.line()
    for e in (a, b):
        assert e["id"] is None and e["error"]["code"] == -32700 and e["error"]["message"] == "Parse error"
    assert p == {"jsonrpc": "2.0", "id": 7, "result": {}}


@pytest.mark.case("AGENT-007")
def test_agent_007_invalid_requests_and_batches_are_refused_with_32600(app):
    """AGENT-007: Invalid requests and batches are refused with -32600"""
    with raw(app) as c:
        c.send('{"jsonrpc":"2.0","id":8}\n')
        r1 = c.line()
        c.send('{"jsonrpc":"2.0","id":10,"method":42}\n')
        r2 = c.line()
        c.send('[{"jsonrpc":"2.0","id":1,"method":"ping"}]\n')
        r3 = c.line()
    assert r1["id"] == 8 and r1["error"] == {"code": -32600, "message": "Invalid Request"}
    assert r2["id"] == 10 and r2["error"]["code"] == -32600
    assert r3["error"]["code"] == -32600


@pytest.mark.case("AGENT-008")
def test_agent_008_responses_sent_by_the_client_are_ignored(app):
    """AGENT-008: Responses sent by the client are ignored"""
    with raw(app) as c:
        c.send('{"jsonrpc":"2.0","id":5,"result":{}}\n')
        c.send('{"jsonrpc":"2.0","id":6,"error":{"code":1,"message":"x"}}\n')
        c.send_json(_ping(7))
        got = c.lines_for(1.0)
    assert got == [{"jsonrpc": "2.0", "id": 7, "result": {}}]


@pytest.mark.case("AGENT-009")
def test_agent_009_tools_call_with_an_unknown_or_missing_tool_name_is_a_32602_e(app):
    """AGENT-009: tools/call with an unknown or missing tool name is a -32602 error"""
    with raw(app) as c:
        r1 = c.request(1, "tools/call", {"name": "no_such_tool", "arguments": {}})
        r2 = c.request(2, "tools/call", {})
        r3 = c.request(3, "tools/call", {"name": "list_documents", "arguments": "x"})
    assert r1["error"]["code"] == -32602 and r1["error"]["message"] == "Unknown tool: no_such_tool"
    assert r2["error"]["code"] == -32602 and r2["error"]["message"].startswith("Unknown tool:")
    assert r3["result"]["isError"] is False
    assert isinstance(r3["result"]["structuredContent"]["documents"], list)


@pytest.mark.case("AGENT-010")
def test_agent_010_a_tool_s_failure_is_an_error_result_its_success_carries_text(app):
    """AGENT-010: A tool's failure is an error result, its success carries text and structured content"""
    bad = call_raw(app, "get_document", document="no-such.txt")
    assert bad["isError"] is True
    assert bad["content"][0] == {"type": "text", "text": "No open document is no-such.txt"}
    good = call_raw(app, "list_documents")
    assert good["isError"] is False
    assert good["content"][0]["type"] == "text"
    assert json.loads(good["content"][0]["text"]) == good["structuredContent"]
    assert isinstance(good["structuredContent"]["documents"], list)


@pytest.mark.case("AGENT-011")
def test_agent_011_framing_crlf_blank_lines_pipelining_and_split_writes(app):
    """AGENT-011: Framing: CRLF, blank lines, pipelining and split writes"""
    with raw(app) as c:
        c.send(json.dumps(_ping(1)) + "\r\n")
        c.send("\n\n")
        c.send("".join(json.dumps(_ping(i)) + "\n" for i in (2, 3, 4)))
        msg = (json.dumps({"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                           "params": {"name": "list_documents", "arguments": {}}}) + "\n").encode()
        for b in msg:
            c.send(bytes([b]))
            time.sleep(0.001)
        lines = [c.raw_line() for _ in range(5)]
        extra = c.lines_for(0.5)
    assert all(ln is not None for ln in lines)
    assert [json.loads(ln)["id"] for ln in lines] == [1, 2, 3, 4, 5]
    assert extra == []


@pytest.mark.case("AGENT-012")
def test_agent_012_a_multi_megabyte_request_and_answer_travel_whole(app):
    """AGENT-012: A multi-megabyte request and answer travel whole"""
    line = "0123456789" * 9 + "012345678\n"          # 100 characters with the newline
    text = line * 50000                                # 5,000,000 characters
    app.new("")
    t = time.monotonic()
    r = app.call("edit_document", text=text)
    assert time.monotonic() - t < 10
    assert r["applied"] == 1 and r["document"]["bytes"] == 5_000_000
    part = app.call("get_document", first_line=1, last_line=9000)
    assert part["text"] == line * 9000 and part["truncated"] is False
    part = app.call("get_document", first_line=41001, last_line=50000)
    assert part["text"] == line * 9000


@pytest.mark.case("AGENT-013")
def test_agent_013_a_client_that_disconnects_before_reading_its_answer_does_not(fresh_app):
    """AGENT-013: A client that disconnects before reading its answer does not kill the application"""
    app = fresh_app
    for msg in (_ping(1), {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                           "params": {"name": "get_document", "arguments": {}}}):
        s = socket.socket(socket.AF_UNIX)
        s.connect(app.socket_path)
        s.sendall((json.dumps(msg) + "\n").encode())
        s.close()
    time.sleep(1.0)   # the answers are written (or fail) meanwhile; nothing to poll for
    alive = app.running
    if alive:
        with raw(app) as c:
            assert c.request(3, "ping")["result"] == {}
    else:
        restart_default(app)
    assert alive, "the application died when a client went away before its answer"


@pytest.mark.case("AGENT-014")
def test_agent_014_several_connections_at_once_are_each_served_correctly(app):
    """AGENT-014: Several connections at once are each served correctly"""
    app.new("x\ny\n", title="conc")
    errors = []

    def worker(k):
        c = app.connect()
        try:
            for i in range(40):
                name = "list_documents" if i % 2 else "get_document"
                args = {} if name == "list_documents" else {"document": "conc"}
                r = c.request("tools/call", {"name": name, "arguments": args})
                sc = r["structuredContent"]
                if r.get("isError") or (name == "get_document" and sc["text"] != "x\ny\n") or \
                        (name == "list_documents" and not sc["documents"]):
                    errors.append(r)
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))
        finally:
            c.close()
    t = time.monotonic()
    threads = [threading.Thread(target=worker, args=(k,)) for k in range(12)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(30)
    assert errors == []
    assert time.monotonic() - t < 10
    # A burst of 20 connections, more than listen()'s backlog of 8.
    conns, refused = [], 0
    for _ in range(20):
        try:
            conns.append(Raw(app.socket_path))
        except ConnectionRefusedError:
            refused += 1
    try:
        for i, c in enumerate(conns):
            c.send_json(_ping(i))
        for i, c in enumerate(conns):
            assert c.line() == {"jsonrpc": "2.0", "id": i, "result": {}}
    finally:
        for c in conns:
            c.close()
    assert refused == 0, f"{refused} of 20 simultaneous connections were refused"


@pytest.mark.case("AGENT-015")
def test_agent_015_concurrent_edits_from_two_connections_are_all_applied(app):
    """AGENT-015: Concurrent edits from two connections are all applied"""
    app.new("", title="edits")
    errors = []

    def worker(tag):
        c = app.connect()
        try:
            for i in range(1, 51):
                r = c.request("tools/call", {"name": "edit_document", "arguments": {
                    "document": "edits", "edits": [{"start_line": 1, "start_column": 1, "end_line": 1,
                                                    "end_column": 1, "text": f"{tag}{i}\n"}]}})
                if r.get("isError"):
                    errors.append(r)
        except Exception as e:  # noqa: BLE001
            errors.append(repr(e))
        finally:
            c.close()
    threads = [threading.Thread(target=worker, args=(t,)) for t in "AB"]
    for th in threads:
        th.start()
    for th in threads:
        th.join(60)
    assert errors == []
    lines = app.text("edits").splitlines()
    assert len(lines) == 100
    assert sorted(lines) == sorted([f"{t}{i}" for t in "AB" for i in range(1, 51)])
    assert app.doc("edits")["modified"] is True


@pytest.mark.case("AGENT-016")
def test_agent_016_while_a_modal_dialog_opened_by_a_tool_is_up_other_connection(app):
    """AGENT-016: While a modal dialog opened by a tool is up, other connections are still answered"""
    app.new("abc\n")
    app.answers(real_modals=True)
    pending = app.run_async("IDM_EDIT_COLUMNMODE")
    try:
        w = app.wait(lambda: app.window("_NSAlertPanel"), 5, "the Column Editor's first question")
        with raw(app, timeout=3) as c:
            assert c.request(1, "ping", timeout=3) == {"jsonrpc": "2.0", "id": 1, "result": {}}
        app.click(w["number"], "Cancel")
        r = pending.wait(10)
    finally:
        app.answers(real_modals=False)
    assert r["ran"] is True
    assert app.text() == "abc\n"


# ---------------------------------------------------- Socket, preference, bridge


def _launch_on(app, path, **kw):
    """Starts the session's copy listening on another socket path; connects there."""
    app.stop()
    app.start(env={"NPPMAC_AGENT_SOCKET": path}, wait_socket=False, **kw)
    wait_for(lambda: stat.S_ISSOCK(os.stat(path).st_mode) if os.path.exists(path) else False, 30,
             message="the socket at " + path)


@pytest.mark.case("AGENT-017")
def test_agent_017_the_socket_is_the_user_s_alone(app):
    """AGENT-017: The socket is the user's alone"""
    base = short_dir()
    path = os.path.join(base, "newdir", "s.sock")
    try:
        _launch_on(app, path)
        st = os.stat(path)
        assert stat.S_ISSOCK(st.st_mode)
        assert stat.S_IMODE(st.st_mode) == 0o600
        assert st.st_uid == os.getuid()
        assert stat.S_IMODE(os.stat(os.path.dirname(path)).st_mode) == 0o700
        with Raw(path) as c:
            assert c.request(1, "ping")["result"] == {}
    finally:
        restart_default(app)


@pytest.mark.case("AGENT-018")
def test_agent_018_the_agent_interface_is_off_by_default(app):
    """AGENT-018: The agent interface is off by default"""
    try:
        app.stop()
        app.start(agent_flag=False, wait_socket=False)
        # Up and running for a while: no socket appears.
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            assert app.running
            assert not os.path.exists(app.socket_path)
            time.sleep(0.2)
        b = bridge(app)
        b.stdin.write((json.dumps(INIT) + "\n" +
                       json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n").encode())
        b.stdin.flush()
        # The bridge waits up to 15 s for the socket after asking Launch Services for the app; in the
        # VM's GUI session that request itself takes some 13 s (it launches the copy), so 25 s is short.
        r = read_json_line(b.stdout, 45)
        assert r is not None, "the bridge said nothing"
        assert r["id"] == 1 and r["error"]["code"] == -32000
        assert "MISC." in r["error"]["message"] and "Let AI agents drive the editor" in r["error"]["message"]
        assert read_json_line(b.stdout, 1) is None     # nothing for the notification
        b.stdin.close()
        b.wait(10)
        assert not os.path.exists(app.socket_path)
    finally:
        if app.proc:
            app.proc.terminate()
            try:
                app.proc.wait(10)
            except subprocess.TimeoutExpired:
                app.proc.kill()
        app.proc = None
        restart_default(app)


def _prefs_window(app):
    app.run("IDM_SETTING_PREFERENCE")
    w = app.wait(lambda: app.window("Preferences"), 5, "Preferences")["number"]
    table = [c for c in app.ui(w)["controls"] if c.get("class") == "NSTableView"][0]
    row = [r[0] for r in table["cells"]].index("MISC.")
    app.act(w, "select", row, path=table["path"])
    return w


@pytest.mark.case("AGENT-019")
def test_agent_019_the_misc_preference_starts_and_stops_listening(app):
    """AGENT-019: The MISC. preference starts and stops listening"""
    label = "Let AI agents drive the editor (MCP)"
    try:
        app.stop()
        app.start(agent_flag=False, defaults={"agentServer": True})
        app.new("x\n")
        w = _prefs_window(app)
        box = app.controls(w, title=label)[0]
        assert box["state"] == 1
        with raw(app, timeout=5) as other:
            assert other.request(1, "ping")["result"] == {}
            app.click(w, label)
            try:
                app.click(w, "Apply")        # the answer may not come: this connection ends too
            except (ConnectionError, OSError, TimeoutError):
                pass
            wait_for(lambda: not os.path.exists(app.socket_path), 5, message="the socket to go")
            with pytest.raises(OSError):
                Raw(app.socket_path, 2)
            # Switched off, no agent keeps control: the connection made before is ended.
            other.sock.settimeout(5)
            assert other.sock.recv(1024) == b""
        assert app.running
        # Stored off: a launch that listens again (the flag) reads it back from the domain.
        app.stop(graceful=False)
        app.start(clean_home=False, reset=False)
        assert app.call("e2e_prefs", all=True)["values"]["all"].get("agentServer") in (False, 0, "NO", "0")
    finally:
        restart_default(app)


@pytest.mark.case("AGENT-020")
def test_agent_020_a_stale_socket_file_is_replaced_at_launch(app):
    """AGENT-020: A stale socket file is replaced at launch"""
    path = os.path.join(short_dir(), "st.sock")
    Path(path).write_text("stale")
    try:
        _launch_on(app, path)
        with Raw(path) as c:
            assert c.request(1, "ping")["result"] == {}
    finally:
        restart_default(app)


@pytest.mark.case("AGENT-021")
def test_agent_021_quitting_removes_the_socket_file(fresh_app):
    """AGENT-021: Quitting removes the socket file"""
    app = fresh_app
    try:
        assert os.path.exists(app.socket_path)
        app.answers(alerts=[2, 2, 2], clear=True)
        try:
            app.invoke("nsapp", "terminate:", [None], timeout=3)
        except Exception:  # noqa: BLE001 - the answer may not come back
            pass
        app.proc.wait(15)
        assert app.proc.returncode == 0
        assert not os.path.exists(app.socket_path)
    finally:
        restart_default(app)


@pytest.mark.case("AGENT-022")
def test_agent_022_nppmac_mcp_relays_requests_and_answers(app):
    """AGENT-022: nppmac mcp relays requests and answers"""
    b = bridge(app)
    b.stdin.write((json.dumps(INIT) + "\n" +
                   json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n" +
                   json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                               "params": {"name": "list_documents", "arguments": {}}}) + "\n").encode())
    b.stdin.flush()
    r1 = read_json_line(b.stdout)
    r2 = read_json_line(b.stdout)
    assert r1["id"] == 1 and r1["result"]["serverInfo"]["name"] == "NotepadMac"
    assert r2["id"] == 2 and isinstance(r2["result"]["structuredContent"]["documents"], list)
    b.stdin.close()
    assert b.wait(5) == 0
    assert app.running


@pytest.mark.case("AGENT-023")
def test_agent_023_nppmac_mcp_used_as_a_one_shot_pipe_prints_every_answer_befor(fresh_app):
    """AGENT-023: nppmac mcp used as a one-shot pipe prints every answer before it exits"""
    app = fresh_app
    inp = (json.dumps(INIT) + "\n" + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}) + "\n").encode()
    env = dict(os.environ, NPPMAC_AGENT_SOCKET=app.socket_path)
    r = subprocess.run([str(app.cli), "mcp"], input=inp, env=env, capture_output=True, timeout=30)
    time.sleep(0.5)
    alive = app.running
    if not alive:
        restart_default(app)
    assert alive, "the application died"
    lines = [json.loads(x) for x in r.stdout.splitlines() if x.strip()]
    assert [x["id"] for x in lines] == [1, 2]
    assert r.returncode == 0


@pytest.mark.case("AGENT-024")
def test_agent_024_nppmac_mcp_forwards_a_last_line_without_a_newline(app):
    """AGENT-024: nppmac mcp forwards a last line without a newline"""
    b = bridge(app)
    b.stdin.write(json.dumps(_ping(1)).encode())
    b.stdin.flush()
    got = read_json_line(b.stdout, 3)
    b.stdin.close()
    if got is None:
        got = read_json_line(b.stdout, 3)
    b.wait(5)
    assert got == {"jsonrpc": "2.0", "id": 1, "result": {}}


@pytest.mark.case("AGENT-025")
def test_agent_025_nppmac_mcp_ends_when_the_application_goes_away(fresh_app):
    """AGENT-025: nppmac mcp ends when the application goes away"""
    app = fresh_app
    b = bridge(app)
    try:
        b.stdin.write((json.dumps(_ping(1)) + "\n").encode())
        b.stdin.flush()
        assert read_json_line(b.stdout)["id"] == 1
        app.stop()
        assert b.wait(5) == 0
    finally:
        if b.poll() is None:
            b.kill()
        restart_default(app)


@pytest.mark.case("AGENT-026")
def test_agent_026_tool_descriptions_errors_and_english_menu_paths_stay_english(app):
    """AGENT-026: Tool descriptions, errors and English menu paths stay English in a localized interface"""
    english = {t["name"]: t["description"] for t in product_tools(app)}
    try:
        app.restart(args=["-NppMac.localizationFile", "russian.xml"])
        assert {t["name"]: t["description"] for t in product_tools(app)} == english
        assert err(app, "get_document", document="nope.txt") == "No open document is nope.txt"
        app.new("abc")
        app.select_all()
        r = app.call("run_command", command="Edit|Convert Case to|UPPERCASE")
        assert r["ran"] is True
        assert app.text() == "ABC"
        names = [c["name"] for c in app.call("list_commands", query="uppercase")["commands"]]
        assert "IDM_EDIT_UPPERCASE" in names
    finally:
        app.restart()


# ------------------------------------------------------ Documents and addressing


def _titles(app):
    return [d["title"] for d in app.docs()]


def _doc_named(app, title):
    return [d for d in app.docs() if d["title"] == title][0]


@pytest.mark.case("AGENT-027")
def test_agent_027_list_documents_reports_what_the_tabs_and_the_status_bar_show(app, tmp):
    """AGENT-027: list_documents reports what the tabs and the status bar show"""
    (tmp / "a.py").write_text("x = 1\n")
    (tmp / "b.txt").write_bytes(b"\xef\xbb\xbfbom\n")
    (tmp / "c.txt").write_bytes("﻿hé\r\nx\r\n".encode("utf-16-le"))
    for n in ("a.py", "b.txt", "c.txt"):
        app.open(tmp / n)
    app.call("edit_document", document=str(tmp / "a.py"), text="x = 2\n")
    app.new("x", title="x")
    r = app.call("list_documents")
    docs = r["documents"]
    assert [d["index"] for d in docs] == list(range(len(docs)))
    by = {d["title"]: d for d in docs}
    assert by["a.py"]["language"] == "python" and by["a.py"]["language_title"] == "Python"
    assert by["b.txt"]["language"] == "normal"
    assert by["a.py"]["modified"] is True
    assert [t for t, d in by.items() if d["modified"]] == ["a.py"]
    assert [t for t, d in by.items() if d["current"]] == ["x"]
    assert by["x"]["path"] is None
    for n in ("a.py", "b.txt", "c.txt"):
        assert app.same_path(by[n]["path"], tmp / n)
    assert (by["a.py"]["encoding"], by["b.txt"]["encoding"], by["c.txt"]["encoding"], by["x"]["encoding"]) == \
        ("UTF-8", "UTF-8-BOM", "UTF-16LE", "UTF-8")
    assert (by["a.py"]["eol"], by["b.txt"]["eol"], by["c.txt"]["eol"], by["x"]["eol"]) == ("LF", "LF", "CRLF", "LF")
    assert all(d["read_only"] is False for d in docs)
    for t in ("a.py", "c.txt", "x"):
        app.call("go_to", document=t, line=1)
        assert by[t]["lines"] == app.sci(SCI_GETLINECOUNT)
        assert by[t]["bytes"] == app.sci(SCI_GETLENGTH)
    assert r["workspace_roots"] == []


@pytest.mark.case("AGENT-028")
def test_agent_028_pinned_tabs_and_workspace_roots_appear_in_the_list(app, tmp):
    """AGENT-028: Pinned tabs and workspace roots appear in the list"""
    app.new("p\n", title="pinme")
    app.new("q\n", title="other")
    app.call("go_to", document="pinme", line=1)
    app.run("File|Pin Tab")
    try:
        (tmp / "ws").mkdir()
        r = app.call("open_document", path=str(tmp / "ws"))
        assert len(r["workspace_roots"]) == 1 and app.same_path(r["workspace_roots"][0], tmp / "ws")
        lst = app.call("list_documents")
        assert _doc_named(app, "pinme").get("pinned") is True
        assert "pinned" not in _doc_named(app, "other")
        assert any(app.same_path(p, tmp / "ws") for p in lst["workspace_roots"])
    finally:
        app.call("go_to", document="pinme", line=1)
        app.run("File|Pin Tab")
        try:
            app.invoke("editor", "closeWorkspaceRoots") if False else None
        except ToolError:
            pass


@pytest.mark.case("AGENT-029")
def test_agent_029_the_search_results_tab_is_neither_listed_nor_addressable(app):
    """AGENT-029: The Search results tab is neither listed nor addressable"""
    app.new("foo\nfoo\n", title="one")
    assert app.call("find", what="foo", show_results=True)["hits"] == 2
    app.new("two\n", title="two")
    docs = app.docs()
    idx = [d["index"] for d in docs]
    missing = [i for i in range(max(idx) + 1) if i not in idx]
    assert missing, f"no gap in {idx}: where did the Search results tab go?"
    e = err(app, "get_document", document=missing[0])
    assert e.startswith(f"No document at index {missing[0]}")


@pytest.mark.case("AGENT-030")
def test_agent_030_a_document_is_found_by_index_path_name_title_or_current(app, tmp):
    """AGENT-030: A document is found by index, path, name, title or "current\""""
    (tmp / "dir1").mkdir()
    f = tmp / "dir1" / "same.txt"
    f.write_text("one\n")
    app.open(f)
    h = app.home / "h.txt"
    h.write_text("home\n")
    app.open(h)
    app.new("notes text\n", title="notes")
    idx = _doc_named(app, "same.txt")["index"]
    real = os.path.realpath(f)
    for spec in (idx, str(idx), real, real.replace("/private/var/", "/var/"),
                 str(tmp / "dir1" / ".." / "dir1" / "same.txt"), "same.txt"):
        assert app.text(spec) == "one\n", spec
    assert app.text("~/h.txt") == "home\n"
    assert app.text("notes") == "notes text\n"
    assert app.text("current") == "notes text\n"
    n = len(app.docs())
    assert err(app, "get_document", document=7) == f"No document at index 7 (list_documents shows {n})"
    assert err(app, "get_document", document=-1) == f"No document at index -1 (list_documents shows {n})"
    assert err(app, "get_document", document="nope.txt") == "No open document is nope.txt"
    assert err(app, "get_document", document=[1]) == "document must be an index, a path or a name"
    assert err(app, "get_document", document={"a": 1}) == "document must be an index, a path or a name"


@pytest.mark.case("AGENT-031")
def test_agent_031_same_named_files_and_number_like_titles_are_addressable(app, tmp):
    """AGENT-031: Same-named files and number-like titles are addressable"""
    for d, t in (("dir1", "first\n"), ("dir2", "second\n")):
        (tmp / d).mkdir()
        (tmp / d / "same.txt").write_text(t)
        app.open(tmp / d / "same.txt")
    assert app.text(str(tmp / "dir1" / "same.txt")) == "first\n"
    assert app.text(str(tmp / "dir2" / "same.txt")) == "second\n"
    assert app.text("same.txt") == "first\n"
    app.new("year\n", title="2024")
    assert app.text("2024") == "year\n"


# ---------------------------------------------------------------- get_document


@pytest.mark.case("AGENT-032")
def test_agent_032_the_whole_text_comes_back_unsaved_changes_included(app, tmp):
    """AGENT-032: The whole text comes back, unsaved changes included"""
    f = tmp / "w.txt"
    f.write_text("a\nb\n")
    app.open(f)
    app.call("edit_document", text="a\nB\nc\n")
    g = app.call("get_document")
    assert g["text"] == "a\nB\nc\n"
    assert f.read_text() == "a\nb\n"
    assert (g["first_line"], g["last_line"], g["truncated"]) == (1, 4, False)
    assert g["modified"] is True and g["title"] == "w.txt" and g["lines"] == 4


@pytest.mark.case("AGENT-033")
def test_agent_033_a_line_range_returns_exactly_those_lines(app, tmp):
    """AGENT-033: A line range returns exactly those lines"""
    f = tmp / "crlf.txt"
    f.write_bytes(b"l1\r\nl2\r\nl3\r\nl4\r\nl5")
    app.open(f)

    def get(a, b):
        g = app.call("get_document", first_line=a, last_line=b)
        return g["text"], g["first_line"], g["last_line"]
    assert get(2, 3) == ("l2\r\nl3\r\n", 2, 3)
    assert get(0, 1) == ("l1\r\n", 1, 1)
    assert get(4, 99) == ("l4\r\nl5", 4, 5)
    assert get(3, 2) == ("l3\r\n", 3, 3)
    assert get(5, 5) == ("l5", 5, 5)


@pytest.mark.case("AGENT-034")
def test_agent_034_a_range_past_the_end_returns_no_text_not_garbage(app):
    """AGENT-034: A range past the end returns no text, not garbage"""
    app.new("one\ntwo\nthree\n")
    for a, b in ((99, None), (5, 7)):
        args = {"first_line": a} if b is None else {"first_line": a, "last_line": b}
        try:
            g = app.call("get_document", **args)
        except ToolError as e:
            assert "outside" in str(e)
            continue
        assert "\x00" not in g["text"]
        assert g["text"] == ""
        assert g["first_line"] <= 4 and g["last_line"] <= 4


@pytest.mark.case("AGENT-035")
def test_agent_035_truncation_at_a_million_characters_loses_nothing_on_continua(app, tmp):
    """AGENT-035: Truncation at a million characters loses nothing on continuation"""
    content = "".join(f"{i:09d}" + "y" * 90 + "\n" for i in range(12000))
    f = tmp / "big.txt"
    f.write_text(content)
    app.open(f)
    g = app.call("get_document")
    assert g["truncated"] is True and len(g["text"]) <= 1_000_000
    pieces, text, last = [g["text"]], g["text"], g["last_line"]
    while g["truncated"]:
        nxt = last if not text.endswith("\n") else last + 1
        if not text.endswith("\n"):
            # a partial line: take it again from its start and drop what we have of it
            pieces[-1] = text[: text.rfind("\n") + 1]
        g = app.call("get_document", first_line=nxt)
        text, last = g["text"], g["last_line"]
        pieces.append(text)
    assert "".join(pieces) == content


@pytest.mark.case("AGENT-036")
def test_agent_036_the_truncation_limit_counts_characters_not_bytes(app):
    """AGENT-036: The truncation limit counts characters, not bytes"""
    app.new("é" * 600000 + "\n")
    g = app.call("get_document")
    assert g["truncated"] is False
    assert len(g["text"]) == 600001


@pytest.mark.case("AGENT-037")
def test_agent_037_a_cut_never_splits_a_character(app):
    """AGENT-037: A cut never splits a character

    The cut counts characters and falls on a whole line (AGENT-035/036), so it takes more than
    a million characters of four-byte emoji to reach it: 1,200 lines of 1,000."""
    app.new(("😀" * 1000 + "\n") * 1200)
    g = app.call("get_document")
    assert g["truncated"] is True
    assert 0 < len(g["text"]) <= 1_000_000
    assert set(g["text"]) == {"😀", "\n"} and g["text"].endswith("\n")
    assert g["first_line"] == 1 and g["text"].count("\n") == g["last_line"]


@pytest.mark.case("AGENT-038")
def test_agent_038_reading_a_document_behind_the_front_one_disturbs_nothing(app):
    """AGENT-038: Reading a document behind the front one disturbs nothing"""
    a = app.new("".join(f"line {i} # comment\n" for i in range(1, 1001)), language="python", title="A")
    app.call("go_to", document="A", line=500, column=3, end_line=500, end_column=6)
    before = app.selection()
    app.new("front\n", title="B")
    g = app.call("get_document", document="A")
    assert g["text"].count("\n") == 1000
    assert app.call("tokens", document="A", first_line=1, last_line=2)["tokens"]
    app.call("spell_check", document="A", language="en")
    assert _doc_named(app, "B")["current"] is True
    app.run("IDM_VIEW_TAB_PREV")
    assert _doc_named(app, "A")["current"] is True
    after = app.selection()
    for k in ("start", "end", "caret", "first_visible_line", "text"):
        assert after[k] == before[k], k
    assert a["index"] == _doc_named(app, "A")["index"]


@pytest.mark.case("AGENT-039")
def test_agent_039_unusual_characters_survive_the_round_trip(app):
    """AGENT-039: Unusual characters survive the round trip"""
    text = "a\u0000b\té字😀é‍\n"
    d = app.new(text)
    assert app.text() == text
    assert d["bytes"] == len(text.encode("utf-8"))
    m = app.call("find", what="b")["matches"]
    assert [(x["line"], x["column"]) for x in m] == [(1, 3)]


# ------------------------------------------------------ get_selection and go_to


@pytest.mark.case("AGENT-040")
def test_agent_040_a_caret_without_a_selection(app):
    """AGENT-040: A caret without a selection"""
    app.new("hello\nworld\n")
    app.call("go_to", line=2, column=3)
    s = app.selection()
    here = {"line": 2, "column": 3, "position": 8}
    assert s["text"] == "" and s["start"] == here and s["end"] == here and s["caret"] == here
    assert s["selections"] == 1 and s["rectangular"] is False and s["first_visible_line"] == 1
    assert s["document"]["current"] is True


@pytest.mark.case("AGENT-041")
def test_agent_041_a_stream_selection_across_lines_with_unicode_columns(app):
    """AGENT-041: A stream selection across lines with Unicode columns"""
    app.new("😀é字x\nline2\n")
    app.call("go_to", line=1, column=2, end_line=2, end_column=3)
    s = app.selection()
    assert s["text"] == "é字x\nli"
    assert s["start"] == {"line": 1, "column": 2, "position": 4}
    assert s["end"] == {"line": 2, "column": 3, "position": 13}
    app.keys("shift+right")
    s = app.selection()
    assert s["text"].endswith("lin") and s["caret"]["column"] == 4


@pytest.mark.case("AGENT-042")
def test_agent_042_multiple_selections_are_counted_the_main_one_reported(app):
    """AGENT-042: Multiple selections are counted, the main one reported"""
    app.new("abc\ndef\n")
    app.sci(SCI_SETSELECTION, 1, 0)
    app.sci(SCI_ADDSELECTION, 6, 5)
    s = app.selection()
    assert s["selections"] == 2 and s["rectangular"] is False
    assert s["text"] == "e"


@pytest.mark.case("AGENT-043")
def test_agent_043_a_rectangular_selection_reports_the_block_s_text(app):
    """AGENT-043: A rectangular selection reports the block's text"""
    app.new("abc\ndef\nghi\n")
    app.call("go_to", line=1, column=1)
    app.keys("alt+shift+down", "alt+shift+down", "alt+shift+right")
    s = app.selection()
    assert s["rectangular"] is True and s["selections"] == 3
    app.run("IDM_EDIT_COPY")
    assert app.clipboard().replace("\r\n", "\n").rstrip("\n") == "a\nd\ng"
    assert s["text"].replace("\r\n", "\n") == "a\nd\ng"


@pytest.mark.case("AGENT-044")
def test_agent_044_go_to_puts_the_caret_centres_the_line_and_gives_the_editor_t(app):
    """AGENT-044: go_to puts the caret, centres the line and gives the editor the keys"""
    app.new("".join(f"line {i}\n" for i in range(1, 1001)))
    r = app.call("go_to", line=500, column=3)
    assert r["start"]["line"] == 500 and r["start"]["column"] == 3 and r["end"] == r["start"]
    first = app.selection()["first_visible_line"]
    assert 450 <= first <= 500
    app.type("X")
    assert app.text().splitlines()[499] == "liXne 500"


@pytest.mark.case("AGENT-045")
def test_agent_045_go_to_selects_a_range_end_column_is_exclusive_and_clamped(app):
    """AGENT-045: go_to selects a range; end_column is exclusive and clamped"""
    app.new("abcdef\nghij\nkl\n")
    app.call("go_to", line=1, column=2, end_line=2, end_column=3)
    assert app.selection()["text"] == "bcdef\ngh"
    app.call("go_to", line=2, column=1, end_line=2)
    assert app.selection()["text"] == "ghij"
    r = app.call("go_to", line=1, column=99)
    assert r["start"]["line"] == 1 and r["start"]["column"] == 7
    app.call("go_to", line=3, column=1, end_line=99)
    assert app.selection()["text"] == "kl\n"
    app.call("go_to", line=2, column=3, end_line=1, end_column=2)
    s = app.selection()
    assert s["text"] == "bcdef\ngh"
    assert s["caret"]["line"] == 1 and s["caret"]["column"] == 2
    assert app.sci(SCI_GETANCHOR) == 9    # line 2 column 3


@pytest.mark.case("AGENT-046")
def test_agent_046_go_to_refuses_lines_outside_the_document_and_a_missing_line(app):
    """AGENT-046: go_to refuses lines outside the document and a missing line"""
    app.new("a\nb\nc")
    assert err(app, "go_to", line=0) == "Line 0 is outside 1..3"
    assert err(app, "go_to", line=5) == "Line 5 is outside 1..3"
    assert err(app, "go_to", line=-2) == "Line -2 is outside 1..3"
    assert "line" in err(app, "go_to")
    assert "line" in err(app, "go_to", line="2")


@pytest.mark.case("AGENT-047")
def test_agent_047_go_to_brings_a_background_document_to_front(app):
    """AGENT-047: go_to brings a background document to front"""
    app.new("a1\na2\n", title="A")
    app.new("b1\n", title="B")
    app.call("go_to", document="A", line=2)
    assert _doc_named(app, "A")["current"] is True
    assert app.get("editor", "currentDocument.displayName") == "A"
    assert app.selection()["caret"]["line"] == 2
    assert app.text("B") == "b1\n"


# ----------------------------------------------- open_document and close_document


@pytest.mark.case("AGENT-048")
def test_agent_048_opening_a_file_and_again_when_it_is_already_open(app, tmp):
    """AGENT-048: Opening a file, and again when it is already open"""
    f = tmp / "f.py"
    f.write_text("1\n2\n3\n4\n5\n")
    r1 = app.call("open_document", path=str(f), line=4)
    assert app.same_path(r1["path"], f) and r1["language"] == "python"
    assert app.selection()["caret"]["line"] == 4
    app.new("x\n")
    n = len(app.docs())
    r2 = app.call("open_document", path=str(f), line=2)
    assert r2["index"] == r1["index"]
    assert len(app.docs()) == n
    assert _doc_named(app, "f.py")["current"] is True
    assert app.selection()["caret"]["line"] == 2


@pytest.mark.case("AGENT-049")
def test_agent_049_a_new_document_from_text_with_title_and_language(app):
    """AGENT-049: A new document from text, with title and language"""
    r = app.call("open_document", text="int main(){}\n", title="demo.cpp", language="cpp")
    assert r["title"] == "demo.cpp" and r["language"] == "cpp" and r["path"] is None and r["modified"] is False
    assert app.enabled("IDM_EDIT_UNDO") is False
    r = app.call("open_document", text="#!/usr/bin/env python3\nprint(1)\n")
    assert r["language"] == "python"


@pytest.mark.case("AGENT-050")
def test_agent_050_open_document_refuses_before_it_makes_a_tab(app, tmp):
    """AGENT-050: open_document refuses before it makes a tab"""
    n = len(app.docs())
    assert err(app, "open_document", path="/nonexistent/x.txt") == "No such file: /nonexistent/x.txt"
    assert err(app, "open_document", text="x", language="klingon") == "No language named klingon"
    assert err(app, "open_document") == "Give a path or a text"
    assert err(app, "open_document", text=42) == "Give a path or a text"
    assert len(app.docs()) == n
    f = tmp / "e.txt"
    f.write_text("file\n")
    r = app.call("open_document", path=str(f), text="zzz")
    assert app.same_path(r["path"], f)
    for d in app.docs():
        assert "zzz" not in app.text(d["index"])


@pytest.mark.case("AGENT-051")
def test_agent_051_the_eol_of_a_new_document_agrees_with_the_status_bar(app, tmp):
    """AGENT-051: The eol of a new document agrees with the status bar"""
    def status():
        return app.get("editor", "statusField.stringValue")

    r = app.call("open_document", text="a\r\nb\r\n")
    assert r["eol"] == "LF"
    assert "Unix (LF)" in status()
    assert app.sci(SCI_GETEOLMODE) == SC_EOL_LF
    assert app.text() == "a\r\nb\r\n"
    f = tmp / "w.txt"
    f.write_bytes(b"a\r\nb\r\n")
    r = app.open(f)
    assert r["eol"] == "CRLF"
    assert "Windows (CR LF)" in status()


@pytest.mark.case("AGENT-052")
def test_agent_052_close_document_keeps_the_user_s_unsaved_work_unless_told(app, tmp):
    """AGENT-052: close_document keeps the user's unsaved work unless told"""
    f = tmp / "a.txt"
    f.write_text("a\n")
    app.open(f)
    app.new("", title="B")
    app.set_text("changed\n")
    assert err(app, "close_document", document="B") == \
        "B has unsaved changes; pass discard_changes to close it anyway"
    assert app.text("B") == "changed\n"
    r = app.call("close_document", document="B", discard_changes=True)
    assert r["closed"] is True
    r = app.call("close_document", document=str(f))
    assert r["closed"] is True
    while len(app.docs()) > 1:
        app.call("close_document", document=0, discard_changes=True)
    r = app.call("close_document", discard_changes=True)
    assert r == {"closed": True, "open_documents": 1}
    docs = app.docs()
    assert len(docs) == 1 and docs[0]["title"] == "new 1" and docs[0]["bytes"] == 0


# ------------------------------------------------ What stays the user's


@pytest.mark.case("AGENT-106")
def test_agent_106_an_agent_closing_the_last_tab_never_quits_the_editor(app):
    """AGENT-106: An agent closing the last tab never quits the editor, whatever "Exit on close the last tab" says"""
    app.close_all()
    app.set_prefs(exitOnClosingLastTab=True)
    try:
        app.new("one\n")
        app.new("two\n")
        proc = app.proc
        r = app.run("IDM_FILE_CLOSEALL")
        assert r["ran"] is True
        assert proc.poll() is None
        assert len(app.docs()) == 1
        r = app.call("close_document")
        assert r == {"closed": True, "open_documents": 1}
        assert proc.poll() is None
        docs = app.docs()
        assert len(docs) == 1 and docs[0]["bytes"] == 0 and docs[0]["modified"] is False
    finally:
        app.set_prefs(exitOnClosingLastTab=False)


@pytest.mark.case("AGENT-107")
def test_agent_107_while_the_user_answers_a_dialog_only_reading_tools_run(app):
    """AGENT-107: While an app-modal dialog waits for the user, tools that change the editor are refused"""
    app.new("abc\n", title="asked")
    app.answers(real_modals=True)
    pending = app.run_async("IDM_EDIT_COLUMNMODE")
    try:
        w = app.wait(lambda: app.window("_NSAlertPanel"), 5, "the Column Editor's first question")
        with raw(app, timeout=5) as c:
            c.request(1, "initialize", INIT["params"])
            edit = c.request(2, "tools/call", {"name": "edit_document", "arguments": {"text": "changed\n"}})["result"]
            went = c.request(3, "tools/call", {"name": "open_document", "arguments": {"text": "new\n"}})["result"]
            read = c.request(4, "tools/call", {"name": "get_document", "arguments": {}})["result"]
        app.click(w["number"], "Cancel")
        r = pending.wait(10)
    finally:
        app.answers(real_modals=False)
    assert r["ran"] is True
    for refused, name in [(edit, "edit_document"), (went, "open_document")]:
        assert refused["isError"] is True
        assert refused["content"][0]["text"] == \
            f"NotepadMac is waiting for the user to answer a dialog; {name} can run once it is closed"
    assert read["isError"] is False and read["structuredContent"]["text"] == "abc\n"
    assert app.text() == "abc\n" and [d["title"] for d in app.docs()].count("asked") == 1
    app.set_text("changed\n")
    assert app.text() == "changed\n"

