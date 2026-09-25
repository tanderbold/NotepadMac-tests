"""FTP: end-to-end tests (plan: plan/FTP.md)."""
import json
import os
import shutil
import time

import pytest

from harness.app import App
from harness.sci import *  # noqa: F401,F403
from _util_ftp import (BROWSE, CONNECT, CONNECTIONS, DISCONNECT, HOST, PASSWORD, PROMPTS, UPLOAD,  # noqa: F401
                             USER, delete_keychain_items, free_port, ftp, keychain_has, realpath, remote_windows,
                             standard_tree)

pytestmark = pytest.mark.network


@pytest.mark.case("FTP-001")
def test_ftp_001_connections_with_nothing_saved_says_so_and_close_saves_nothi(app, ftp):
    """FTP-001: Connections… with nothing saved says so and Close saves nothing

    Covers: -
    Channel: mcp, modal, prefs
    Steps: On a fresh app queue alert answer 2 (Close) and run "Plugins|FTP|Connections…".
    Expect: one alert logged, message "FTP connections", informative "No connections saved yet.", buttons ["Add…", "Close"]; preference `ftpProfiles` is still `[]`; no further prompt is shown.
    """
    app.answers(alerts=[2])
    ftp.run(CONNECTIONS)
    log = app.modal_log()
    assert len(log) == 1
    assert log[0]["message"] == "FTP connections"
    assert log[0]["informative"] == "No connections saved yet."
    assert log[0]["buttons"] == ["Add…", "Close"]
    assert app.pref("ftpProfiles") in ([], None)


@pytest.mark.case("FTP-002")
def test_ftp_002_add_a_connection_through_the_prompt_chain(app, ftp):
    """FTP-002: Add a connection through the prompt chain

    Covers: -
    Channel: mcp, modal, prefs
    Steps: Queue answers 1 (Add…), then fields "local", "127.0.0.1", "ftp", "<port>", "tester", "/", "secret" (each button 1) and run "Plugins|FTP|Connections…".
    Expect: the log shows, in order, the prompts "Connection name" (default "server"), "Host" (default ""), "Protocol: ftp, ftps or sftp" (default "ftp"), "Port (0 for the default)" (default "0"), "User name", "Initial directory" (default "/"), "Password (stored in the Keychain; leave empty for an SSH key)"; `ftpProfiles` is `[{name: "local", host: "127.0.0.1", protocol: 0, port: <port>, username: "tester", initialDirectory: "/"}]`; the password is not in the preferences; `security find-internet-password -s 127.0.0.1 -a tester` finds an item.
    """
    log = ftp.add()
    prompts = [e for e in log if e.get("fields") is not None]
    assert [e["message"] for e in prompts] == PROMPTS
    defaults = [e["fields"][0] for e in prompts]
    assert defaults[0] == "server" and defaults[1] == "" and defaults[2] == "ftp" and defaults[3] == "0"
    assert defaults[5] == "/"
    profiles = app.pref("ftpProfiles")
    assert len(profiles) == 1
    p = profiles[0]
    assert (p["name"], p["host"], int(p["protocol"]), int(p["port"]), p["username"], p["initialDirectory"]) == \
        ("local", HOST, 0, ftp.port, USER, "/")
    assert PASSWORD not in json.dumps(profiles)
    assert keychain_has(USER, HOST, ftp.port)


@pytest.mark.case("FTP-003")
def test_ftp_003_the_connections_list_shows_each_saved_profile(app, ftp):
    """FTP-003: The connections list shows each saved profile

    Covers: -
    Channel: mcp, modal
    Steps: Add profiles "local" (user tester) and "other" (user bob, host 127.0.0.2) as in FTP-002, then queue answer 2 and run "Plugins|FTP|Connections…" again.
    Expect: the alert's informative text is "local (tester@127.0.0.1)\\nother (bob@127.0.0.2)".
    """
    ftp.add("local")
    ftp.add("other", host="127.0.0.2", user="bob", password="")
    app.answers(alerts=[2])
    ftp.run(CONNECTIONS)
    log = app.modal_log()
    assert log[0]["informative"] == "local (tester@127.0.0.1)\nother (bob@127.0.0.2)"


@pytest.mark.case("FTP-004")
def test_ftp_004_protocol_answers_map_to_plain_ftps_and_sftp(app, ftp):
    """FTP-004: Protocol answers map to plain, FTPS and SFTP

    Covers: -
    Channel: mcp, modal, prefs
    Steps: For each of the protocol answers "ftp", "ftps", "sftp", "FTP-anything-else" add a profile named after it (host 127.0.0.1, empty password).
    Expect: the stored `protocol` is 0, 1, 2 and 0 respectively (only the "ftps"/"sftp" prefixes select TLS/SSH; anything else is plain FTP); an empty password answer stores no Keychain item.
    """
    for proto in ("ftp", "ftps", "sftp", "FTP-anything-else"):
        ftp.add(proto, protocol=proto, password="")
    by_name = {p["name"]: int(p["protocol"]) for p in app.pref("ftpProfiles")}
    assert by_name == {"ftp": 0, "ftps": 1, "sftp": 2, "FTP-anything-else": 0}
    assert not keychain_has(USER, HOST)


@pytest.mark.case("FTP-005")
def test_ftp_005_saving_a_profile_under_an_existing_name_replaces_it(app, ftp):
    """FTP-005: Saving a profile under an existing name replaces it

    Covers: -
    Channel: mcp, modal, prefs
    Steps: Add profile "local" with port 2121, then add "local" again with port <port> and initial directory "/sub".
    Expect: `ftpProfiles` holds exactly one "local", with port <port> and initialDirectory "/sub".
    """
    ftp.add("local", port=2121, password="")
    ftp.add("local", directory="/sub", password="")
    profiles = app.pref("ftpProfiles")
    assert len(profiles) == 1
    assert int(profiles[0]["port"]) == ftp.port and profiles[0]["initialDirectory"] == "/sub"


@pytest.mark.case("FTP-006")
def test_ftp_006_cancelling_or_leaving_the_name_or_host_empty_saves_nothing(app, ftp):
    """FTP-006: Cancelling or leaving the name or host empty saves nothing

    Covers: -
    Channel: mcp, modal, prefs
    Steps: For each of: Cancel on "Connection name"; empty field on "Connection name"; Cancel on "Host"; empty field on "Host" — queue Add… plus that answer and run Connections….
    Expect: the chain stops at that prompt (no later prompt in the log); `ftpProfiles` stays `[]`.
    """
    cases = [
        ([{"button": 2}], "Connection name"),
        ([{"button": 1, "field": ""}], "Connection name"),
        ([{"button": 1, "field": "n"}, {"button": 2}], "Host"),
        ([{"button": 1, "field": "n"}, {"button": 1, "field": ""}], "Host"),
    ]
    for answers, last in cases:
        app.answers(alerts=[1] + answers, clear=True)
        ftp.run(CONNECTIONS)
        log = app.modal_log()
        assert log[-1]["message"] == last, log
        assert app.pref("ftpProfiles") in ([], None)


@pytest.mark.restart
@pytest.mark.case("FTP-007")
def test_ftp_007_profiles_survive_a_restart(app, ftp):
    """FTP-007: Profiles survive a restart

    Covers: -
    Channel: mcp, modal, prefs, launch
    Steps: Add profile "local"; `app.restart()`; queue answer 2 and run Connections….
    Expect: the list still reads "local (tester@127.0.0.1)"; `ftpProfiles` is unchanged; connecting (FTP-009 steps) works without asking for the password again.
    """
    standard_tree(ftp)
    ftp.add("local")
    before = app.pref("ftpProfiles")
    app.restart()
    app.answers(alerts=[2])
    ftp.run(CONNECTIONS)
    assert app.modal_log()[0]["informative"] == "local (tester@127.0.0.1)"
    assert app.pref("ftpProfiles") == before
    log = ftp.connect("local")
    assert [e["message"] for e in log] == ["Connect to which? (local)"]
    assert app.wait(ftp.panel)["title"] == "Remote Files — /"


@pytest.mark.case("FTP-008")
def test_ftp_008_connect_with_no_profile_goes_to_connections(app, ftp):
    """FTP-008: Connect… with no profile goes to Connections

    Covers: -
    Channel: mcp, modal
    Steps: On a fresh app queue answer 2 and run "Plugins|FTP|Connect…".
    Expect: the logged alert is "FTP connections" / "No connections saved yet." (not a "Connect to which?" prompt); no "Remote Files" window appears.
    """
    app.answers(alerts=[2])
    ftp.run(CONNECT)
    log = app.modal_log()
    assert [e["message"] for e in log] == ["FTP connections"]
    assert log[0]["informative"] == "No connections saved yet."
    assert not remote_windows(app)


@pytest.mark.case("FTP-009")
def test_ftp_009_connect_lists_the_initial_directory_in_the_remote_files_pane(app, ftp):
    """FTP-009: Connect lists the initial directory in the Remote Files panel

    Covers: -
    Channel: mcp, modal, ui
    Steps: Server root holds `greeting.txt` ("remote hello\\n", 13 bytes) and folder `sub/`. Add profile "local", queue `{field: "local"}` and run "Plugins|FTP|Connect…".
    Expect: the prompt logged is "Connect to which? (local)" with default "local"; a visible `NppPanel` window titled "Remote Files — /" appears; its NSTableView cells are [[".."], ["greeting.txt   13 bytes"], ["sub/"]] (sorted as the server lists); no error alert.
    """
    ftp.write("greeting.txt", "remote hello\n")
    (ftp.root / "sub").mkdir()
    ftp.add("local")
    log = ftp.connect("local")
    assert [e["message"] for e in log] == ["Connect to which? (local)"]
    assert log[0]["fields"] == ["local"]
    w = app.wait(ftp.panel)
    assert w["title"] == "Remote Files — /"
    assert w["class"] == "NppPanel"
    assert ftp.cells() == [[".."], ["greeting.txt   13 bytes"], ["sub/"]]


@pytest.mark.case("FTP-010")
def test_ftp_010_the_profile_s_initial_directory_is_where_browsing_starts(app, ftp):
    """FTP-010: The profile's initial directory is where browsing starts

    Covers: -
    Channel: mcp, modal, ui
    Steps: Profile "local" with initial directory "/sub" (holding `inner.txt`, 6 bytes); connect.
    Expect: panel title "Remote Files — /sub"; cells [[".."], ["inner.txt   6 bytes"]].
    """
    ftp.write("sub/inner.txt", "inner\n")
    ftp.add("local", directory="/sub")
    ftp.connect("local")
    assert app.wait(ftp.title) == "Remote Files — /sub"
    assert ftp.cells() == [[".."], ["inner.txt   6 bytes"]]


@pytest.mark.case("FTP-011")
def test_ftp_011_choosing_among_several_profiles_an_unknown_name_or_cancel_do(app, ftp):
    """FTP-011: Choosing among several profiles; an unknown name or Cancel does nothing

    Covers: -
    Channel: mcp, modal, ui
    Steps: Profiles "local" and "other"; run Connect… with field "bogus", then with button 2 (Cancel), then with field "local".
    Expect: the prompt reads "Connect to which? (local, other)"; "bogus" and Cancel show no further alert and open no Remote Files window; "local" opens "Remote Files — /".
    """
    standard_tree(ftp)
    ftp.add("local")
    ftp.add("other", password="")
    log = ftp.connect("bogus")
    assert [e["message"] for e in log] == ["Connect to which? (local, other)"]
    assert not remote_windows(app)
    app.answers(alerts=[2])
    ftp.run(CONNECT)
    assert len(app.modal_log()) == 1
    assert not remote_windows(app)
    ftp.connect("local")
    assert app.wait(ftp.title) == "Remote Files — /"


@pytest.mark.case("FTP-012")
def test_ftp_012_wrong_credentials_are_refused_with_cannot_connect(app, ftp):
    """FTP-012: Wrong credentials are refused with "Cannot connect."

    Covers: -
    Channel: mcp, modal, ui
    Steps: For each of: user "nobody" with password "secret"; user "tester" with password "wrong" — add a profile and connect to it.
    Expect: an alert "Cannot connect." is logged whose informative text is not empty; no Remote Files window; Upload Current File afterwards shows no alert (not connected).
    """
    for user, pw in (("nobody", "secret"), ("tester", "wrong")):
        app.set_prefs(ftpProfiles=[])
        delete_keychain_items()
        ftp.add("bad", user=user, password=pw)
        log = ftp.connect("bad")
        refused = [e for e in log if e["message"] == "Cannot connect."]
        assert refused and refused[0]["informative"], log
        assert not remote_windows(app)
        ftp.run(UPLOAD)
        assert app.modal_log() == []


@pytest.mark.case("FTP-013")
def test_ftp_013_a_server_that_is_not_there_is_reported_not_hung_on(app, ftp):
    """FTP-013: A server that is not there is reported, not hung on

    Covers: -
    Channel: mcp, modal
    Steps: Profile with host 127.0.0.1 and a port nothing listens on (bind a socket, take its port, close it); connect with a 20 s call timeout.
    Expect: the call returns within the timeout; alert "Cannot connect." logged; the connection state stays disconnected (Show Remote Files asks "Connect to which?" again).
    """
    dead = free_port()
    ftp.add("dead", port=dead, password="")
    t = time.monotonic()
    log = ftp.connect("dead", timeout=20)
    assert time.monotonic() - t < 20
    assert any(e["message"] == "Cannot connect." for e in log)
    app.answers(alerts=[2])
    ftp.run(BROWSE)
    assert app.modal_log()[0]["message"].startswith("Connect to which?")
    assert not remote_windows(app)


@pytest.mark.case("FTP-014")
def test_ftp_014_the_connect_error_names_the_cause_curl_s_message(app, ftp):
    """FTP-014: The connect error names the cause (curl's message)

    Covers: -
    Channel: mcp, modal
    Steps: Repeat FTP-013 (refused port) and a profile with protocol "ftps" against the plain test server (it answers 502 to AUTH TLS).
    Expect: the "Cannot connect." alert's informative text carries the transfer error (e.g. contains "connect" / "SSL"/"TLS"), not only the generic "The server did not answer, or the credentials were refused.".
    """
    ftp.add("dead", port=free_port(), password="")
    ftp.add("tls", protocol="ftps", password="")
    generic = "The server did not answer, or the credentials were refused."
    for name in ("dead", "tls"):
        log = ftp.connect(name, timeout=30)
        refused = [e for e in log if e["message"] == "Cannot connect."]
        assert refused
        assert refused[0]["informative"] != generic, refused[0]


@pytest.mark.case("FTP-015")
def test_ftp_015_sftp_to_a_non_ssh_port_fails_with_an_alert(app, ftp):
    """FTP-015: SFTP to a non-SSH port fails with an alert

    Covers: -
    Channel: mcp, modal
    Steps: Profile with protocol "sftp", host 127.0.0.1, port = the FTP test server's port, user tester; connect with a 60 s call timeout.
    Expect: alert "Cannot connect." logged; no Remote Files window; no password prompt or hang (the system sftp runs in BatchMode).
    """
    ftp.add("ssh", protocol="sftp", password="")
    app.answers(alerts=[{"button": 1, "field": "ssh"}])
    pending = app.call_async("run_command", command=CONNECT)
    # The connection is tried off the main thread: the command comes back at once
    # and the alert follows when the transfer gives up.
    log = []
    t = time.monotonic()
    while time.monotonic() - t < 30:
        log += app.modal_log()
        if pending.done and any(e["message"] == "Cannot connect." for e in log):
            break
        time.sleep(0.2)
    hung = not any(e["message"] == "Cannot connect." for e in log)
    if hung:
        ftp.kill()   # sftp then sees end of file and the application comes back
        pending.wait(60)
        log += app.modal_log()
    assert any(e["message"] == "Cannot connect." for e in log), log
    assert not any("assword" in e.get("message", "") for e in log[1:])
    assert not remote_windows(app)
    assert not hung, "the connect call did not come back within 30 s"


@pytest.mark.case("FTP-016")
def test_ftp_016_double_click_a_folder_descends_goes_back_up(app, ftp):
    """FTP-016: Double-click a folder descends, ".." goes back up

    Covers: -
    Channel: mcp, ui
    Steps: Connected at "/" (FTP-009); `e2e_act double_click` row of "sub/" in the Remote Files table; then double_click row 0 (".."); then row 0 again.
    Expect: after the first: title "Remote Files — /sub", cells [[".."], ["inner.txt   6 bytes"]]; after "..": title "Remote Files — /" and the root listing; ".." at the root stays at "Remote Files — /". (Needs `double_click` to set the table's clickedRow; see hooks.)
    """
    standard_tree(ftp)
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.activate_name("sub/")
    app.wait(lambda: ftp.title() == "Remote Files — /sub")
    assert ftp.cells() == [[".."], ["inner.txt   6 bytes"]]
    ftp.activate(0)
    app.wait(lambda: ftp.title() == "Remote Files — /")
    assert ["sub/"] in ftp.cells()
    ftp.activate(0)
    app.idle(0.2)
    assert ftp.title() == "Remote Files — /"


@pytest.mark.case("FTP-017")
def test_ftp_017_show_remote_files_refreshes_the_listing_from_the_server(app, ftp):
    """FTP-017: Show Remote Files refreshes the listing from the server

    Covers: -
    Channel: mcp, ui, files
    Steps: Connected at "/"; create `new.txt` (3 bytes) in the server root on disk; run "Plugins|FTP|Show Remote Files".
    Expect: the table now includes ["new.txt   3 bytes"]; the panel is key and still titled "Remote Files — /".
    """
    standard_tree(ftp)
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.write("new.txt", "abc")
    ftp.run(BROWSE)
    assert ["new.txt   3 bytes"] in ftp.cells()
    w = ftp.panel()
    assert w["title"] == "Remote Files — /"
    assert w["visible"]   # key-ness is not observable while the test app is in the background


@pytest.mark.case("FTP-018")
def test_ftp_018_show_remote_files_while_disconnected_asks_which_profile_to_c(app, ftp):
    """FTP-018: Show Remote Files while disconnected asks which profile to connect

    Covers: -
    Channel: mcp, modal, ui
    Steps: With profile "local" saved and not connected, queue `{field: "local"}` and run "Plugins|FTP|Show Remote Files".
    Expect: the "Connect to which? (local)" prompt is logged; then the Remote Files panel lists the root.
    """
    standard_tree(ftp)
    ftp.add("local")
    app.answers(alerts=[{"button": 1, "field": "local"}])
    ftp.run(BROWSE)
    log = app.modal_log()
    assert log[0]["message"] == "Connect to which? (local)"
    assert app.wait(ftp.title) == "Remote Files — /"
    assert ["sub/"] in ftp.cells()


@pytest.mark.case("FTP-019")
def test_ftp_019_losing_the_server_while_browsing_shows_the_transfer_error(app, ftp):
    """FTP-019: Losing the server while browsing shows the transfer error

    Covers: -
    Channel: mcp, modal
    Steps: Connect; kill the server process; queue answer 1 and run "Plugins|FTP|Show Remote Files".
    Expect: an alert titled "FTP" with buttons ["OK", "Copy"] and a non-empty informative text (curl's "Couldn't connect to server" or similar) is logged; the app keeps running.
    """
    standard_tree(ftp)
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.kill()
    app.answers(alerts=[1])
    ftp.run(BROWSE)
    # The listing is tried off the main thread; the alert follows its failure.
    log = []
    try:
        app.wait(lambda: log.extend(e for e in app.modal_log() if e["message"] == "FTP") or log, 20,
                 message="the FTP alert")
    except TimeoutError:
        pass
    assert log, "no FTP alert"
    assert log[0]["buttons"] == ["OK", "Copy"]
    assert log[0]["informative"].strip()
    assert app.running


@pytest.mark.case("FTP-020")
def test_ftp_020_closing_the_panel_and_showing_it_again(app, ftp):
    """FTP-020: Closing the panel and showing it again

    Covers: -
    Channel: mcp, ui
    Steps: Connect; close the Remote Files window with `close_window`; run Show Remote Files.
    Expect: the panel is hidden after closing, the connection is kept (no connect prompt logged), and it reappears with the same directory and listing.
    """
    standard_tree(ftp)
    ftp.add("local")
    ftp.connect("local")
    w = app.wait(ftp.panel)
    cells = ftp.cells()
    app.close_window(w["number"])
    app.wait(lambda: not remote_windows(app))
    ftp.run(BROWSE)
    assert app.modal_log() == []
    assert app.wait(ftp.title) == "Remote Files — /"
    assert ftp.cells() == cells


@pytest.mark.case("FTP-021")
def test_ftp_021_double_click_a_file_opens_it_from_the_cache(app, ftp):
    """FTP-021: Double-click a file opens it from the cache

    Covers: -
    Channel: mcp, ui, files
    Steps: Connected at "/"; double_click the "greeting.txt" row.
    Expect: a new tab "greeting.txt" is current with text "remote hello\\n", not modified; its path is `<home>/Library/Application Support/NotepadMac/ftp-cache/127.0.0.1/greeting.txt` and that file on disk has the same bytes.
    """
    ftp.write("greeting.txt", "remote hello\n")
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.activate_name("greeting.txt")
    app.wait(lambda: app.doc()["title"] == "greeting.txt")
    d = app.doc()
    assert d["current"] and not d["modified"]
    assert app.text() == "remote hello\n"
    assert App.same_path(d["path"], ftp.cache("greeting.txt"))
    assert ftp.cache("greeting.txt").read_bytes() == b"remote hello\n"


@pytest.mark.case("FTP-022")
def test_ftp_022_names_with_spaces_and_non_ascii_text_download_intact(app, ftp):
    """FTP-022: Names with spaces, '#' and non-ASCII text download intact

    Covers: -
    Channel: mcp, ui, files
    Steps: Server root has `a b#c.txt` ("odd\\n") and `cyr.txt` ("привет\\r\\n" in UTF-8); open each by double-click.
    Expect: the tabs read "odd\\n" and "привет\\r\\n" (EOL CRLF, encoding UTF-8); cache files `ftp-cache/127.0.0.1/a b#c.txt` and `.../cyr.txt` exist.
    """
    ftp.write("a b#c.txt", "odd\n")
    ftp.write("cyr.txt", "привет\r\n".encode())
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.activate_name("a b#c.txt")
    app.wait(lambda: app.doc()["title"] == "a b#c.txt")
    assert app.text() == "odd\n"
    ftp.activate_name("cyr.txt")
    app.wait(lambda: app.doc()["title"] == "cyr.txt")
    assert app.text() == "привет\r\n"
    d = app.doc()
    assert d["eol"] == "CRLF" and d["encoding"] == "UTF-8"
    assert ftp.cache("a b#c.txt").exists() and ftp.cache("cyr.txt").exists()


@pytest.mark.case("FTP-023")
def test_ftp_023_same_file_name_in_two_folders_gets_two_cache_files(app, ftp):
    """FTP-023: Same file name in two folders gets two cache files

    Covers: -
    Channel: mcp, ui, files
    Steps: Root `greeting.txt` ("remote hello\\n") and `sub/greeting.txt` ("inner\\n"); open the root one, then descend into sub/ and open that one.
    Expect: two tabs, both titled "greeting.txt", with their own texts; cache paths `.../127.0.0.1/greeting.txt` and `.../127.0.0.1/sub/greeting.txt`.
    """
    ftp.write("greeting.txt", "remote hello\n")
    ftp.write("sub/greeting.txt", "inner\n")
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.activate_name("greeting.txt")
    app.wait(lambda: app.doc()["title"] == "greeting.txt")
    ftp.activate_name("sub/")
    app.wait(lambda: ftp.title() == "Remote Files — /sub")
    ftp.activate_name("greeting.txt")
    app.wait(lambda: app.text() == "inner\n")
    docs = [d for d in app.docs() if d["title"] == "greeting.txt"]
    assert len(docs) == 2
    paths = sorted(os.path.realpath(d["path"]) for d in docs)
    assert paths == sorted([realpath(ftp.cache("greeting.txt")), realpath(ftp.cache("sub/greeting.txt"))])
    assert app.text(docs[0]["index"]) != app.text(docs[1]["index"])


@pytest.mark.case("FTP-024")
def test_ftp_024_a_file_that_vanished_from_the_server_reports_an_error_and_op(app, ftp):
    """FTP-024: A file that vanished from the server reports an error and opens nothing

    Covers: -
    Channel: mcp, ui, modal, files
    Steps: Connected, listing shows `gone.txt`; delete it on disk; queue answer 1 and double-click its row.
    Expect: an alert titled "FTP" with a non-empty informative text is logged; the document count and current tab are unchanged; no `ftp-cache/127.0.0.1/gone.txt` is written.
    """
    ftp.write("gone.txt", "bye\n")
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    before = app.docs()
    (ftp.root / "gone.txt").unlink()
    app.answers(alerts=[1])
    opened = ftp.activate_name("gone.txt")
    assert not opened
    # The download is tried off the main thread; the alert follows its failure.
    alerts = []
    app.wait(lambda: alerts.extend(e for e in app.modal_log() if e["message"] == "FTP") or alerts, 20,
             message="the FTP alert")
    assert alerts and alerts[0]["informative"].strip()
    after = app.docs()
    assert len(after) == len(before)
    assert [d["title"] for d in after if d["current"]] == [d["title"] for d in before if d["current"]]
    assert not ftp.cache("gone.txt").exists()


@pytest.mark.case("FTP-025")
def test_ftp_025_edit_save_and_upload_a_remote_file_back_to_where_it_came_fro(app, ftp):
    """FTP-025: Edit, save and upload a remote file back to where it came from

    Covers: IDM_FILE_SAVE
    Channel: mcp, modal, files
    Steps: Open `greeting.txt` from the panel; replace the text with "changed here\\n"; run IDM_FILE_SAVE; check the server file; queue answer 1 and run "Plugins|FTP|Upload Current File".
    Expect: after Save the cache file holds "changed here\\n" and the server root's `greeting.txt` still holds "remote hello\\n" (saving does not upload); after Upload an alert "FTP" / "Uploaded to /greeting.txt" (buttons ["OK", "Copy"]) is logged and the server file holds "changed here\\n".
    """
    ftp.write("greeting.txt", "remote hello\n")
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.activate_name("greeting.txt")
    app.wait(lambda: app.doc()["title"] == "greeting.txt")
    app.set_text("changed here\n")
    app.run("IDM_FILE_SAVE")
    assert ftp.cache("greeting.txt").read_bytes() == b"changed here\n"
    assert ftp.read("greeting.txt") == b"remote hello\n"
    log = ftp.upload()
    up = [e for e in log if e["message"] == "FTP"]
    assert up and up[0]["informative"] == "Uploaded to /greeting.txt"
    assert up[0]["buttons"] == ["OK", "Copy"]
    assert ftp.read("greeting.txt") == b"changed here\n"


@pytest.mark.case("FTP-026")
def test_ftp_026_a_file_from_a_subfolder_goes_back_to_its_subfolder_even_afte(app, ftp):
    """FTP-026: A file from a subfolder goes back to its subfolder even after browsing elsewhere

    Covers: -
    Channel: mcp, modal, files, ui
    Steps: Open `sub/greeting.txt` from the panel, go ".." back to "/", edit to "inner 2\\n", Upload.
    Expect: "Uploaded to /sub/greeting.txt"; `sub/greeting.txt` on the server is "inner 2\\n"; root `greeting.txt` is untouched.
    """
    ftp.write("greeting.txt", "remote hello\n")
    ftp.write("sub/greeting.txt", "inner\n")
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.activate_name("sub/")
    app.wait(lambda: ftp.title() == "Remote Files — /sub")
    ftp.activate_name("greeting.txt")
    app.wait(lambda: app.text() == "inner\n")
    ftp.activate(0)
    app.wait(lambda: ftp.title() == "Remote Files — /")
    app.set_text("inner 2\n")
    log = ftp.upload()
    assert [e["informative"] for e in log if e["message"] == "FTP"] == ["Uploaded to /sub/greeting.txt"]
    assert ftp.read("sub/greeting.txt") == b"inner 2\n"
    assert ftp.read("greeting.txt") == b"remote hello\n"


@pytest.mark.case("FTP-027")
def test_ftp_027_upload_recreates_a_missing_remote_folder(app, ftp):
    """FTP-027: Upload recreates a missing remote folder

    Covers: -
    Channel: mcp, modal, files
    Steps: Open `sub/greeting.txt`; delete the whole `sub` folder on the server's disk; edit and Upload.
    Expect: "Uploaded to /sub/greeting.txt"; the server root has `sub/greeting.txt` again with the new text (missing directories are created with MKD).
    """
    ftp.write("sub/greeting.txt", "inner\n")
    ftp.add("local", directory="/sub")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.activate_name("greeting.txt")
    app.wait(lambda: app.text() == "inner\n")
    shutil.rmtree(ftp.root / "sub")
    app.set_text("recreated\n")
    log = ftp.upload()
    assert [e["informative"] for e in log if e["message"] == "FTP"] == ["Uploaded to /sub/greeting.txt"]
    assert ftp.read("sub/greeting.txt") == b"recreated\n"


@pytest.mark.case("FTP-028")
def test_ftp_028_a_local_file_is_uploaded_into_the_directory_being_browsed_co(app, ftp, tmp):
    """FTP-028: A local file is uploaded into the directory being browsed; Copy copies the message

    Covers: -
    Channel: mcp, modal, files, clipboard
    Steps: Connected, browsing "/sub"; open a local file `<tmp>/local.txt` ("from local\\n"); queue answer 2 (Copy) and run Upload Current File; then edit it and Upload again.
    Expect: alert "Uploaded to /sub/local.txt"; the clipboard is "Uploaded to /sub/local.txt"; `sub/local.txt` on the server holds "from local\\n", and after the second upload the edited text (the remembered remote path is reused).
    """
    ftp.write("sub/inner.txt", "inner\n")
    ftp.add("local", directory="/sub")
    ftp.connect("local")
    app.wait(ftp.panel)
    local = tmp / "local.txt"
    local.write_text("from local\n")
    app.open(local)
    log = ftp.upload(answer=2)
    assert [e["informative"] for e in log if e["message"] == "FTP"] == ["Uploaded to /sub/local.txt"]
    assert app.clipboard() == "Uploaded to /sub/local.txt"
    assert ftp.read("sub/local.txt") == b"from local\n"
    app.set_text("edited local\n")
    log = ftp.upload()
    assert [e["informative"] for e in log if e["message"] == "FTP"] == ["Uploaded to /sub/local.txt"]
    assert ftp.read("sub/local.txt") == b"edited local\n"


@pytest.mark.case("FTP-029")
def test_ftp_029_upload_sends_the_bytes_save_writes_encoding_and_bom_kept(app, ftp):
    """FTP-029: Upload sends the bytes Save writes (encoding and BOM kept)

    Covers: IDM_FORMAT_CONV2_UTF_8, IDM_FORMAT_CONV2_AS_UTF_8
    Channel: mcp, modal, files
    Steps: Open `cyr.txt` ("привет\\r\\n" UTF-8) from the panel; for each of IDM_FORMAT_CONV2_UTF_8 (UTF-8-BOM) and IDM_FORMAT_CONV2_AS_UTF_8 (back to UTF-8): convert, IDM_FILE_SAVE, Upload Current File.
    Expect: after each upload the server file's bytes equal the cache file's bytes (EF BB BF + the UTF-8 text for UTF-8-BOM; the plain UTF-8 text afterwards).
    """
    ftp.write("cyr.txt", "привет\r\n".encode())
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.activate_name("cyr.txt")
    app.wait(lambda: app.doc()["title"] == "cyr.txt")
    for cmd, bom in (("IDM_FORMAT_CONV2_UTF_8", True), ("IDM_FORMAT_CONV2_AS_UTF_8", False)):
        app.run(cmd)
        app.run("IDM_FILE_SAVE")
        ftp.upload()
        cached = ftp.cache("cyr.txt").read_bytes()
        assert cached.startswith(b"\xef\xbb\xbf") == bom
        assert ftp.read("cyr.txt") == cached, (cmd, ftp.read("cyr.txt"), cached)


@pytest.mark.case("FTP-030")
def test_ftp_030_upload_and_disconnect_without_a_connection_disconnect_hides(app, ftp):
    """FTP-030: Upload and Disconnect without a connection; Disconnect hides the panel

    Covers: -
    Channel: mcp, modal, ui
    Steps: Connect, open `greeting.txt`, run "Plugins|FTP|Disconnect"; then run Upload Current File; then queue answer 2 and run Show Remote Files.
    Expect: after Disconnect no Remote Files window is visible; Upload shows no alert and the server file is unchanged (it only beeps); Show Remote Files logs the "Connect to which?" prompt (answered Cancel) and opens no panel; the opened tab stays open with its cache path.
    """
    ftp.write("greeting.txt", "remote hello\n")
    ftp.add("local")
    ftp.connect("local")
    app.wait(ftp.panel)
    ftp.activate_name("greeting.txt")
    app.wait(lambda: app.doc()["title"] == "greeting.txt")
    ftp.run(DISCONNECT)
    app.wait(lambda: not remote_windows(app))
    app.set_text("not sent\n")
    app.call("e2e_counters", reset=True)
    ftp.run(UPLOAD)
    assert app.modal_log() == []
    assert app.call("e2e_counters")["beeps"] >= 1
    assert ftp.read("greeting.txt") == b"remote hello\n"
    app.answers(alerts=[2])
    ftp.run(BROWSE)
    log = app.modal_log()
    assert log[0]["message"] == "Connect to which? (local)"
    assert not remote_windows(app)
    d = app.doc()
    assert d["title"] == "greeting.txt" and App.same_path(d["path"], ftp.cache("greeting.txt"))
