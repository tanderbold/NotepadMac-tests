"""WINDOW: end-to-end tests (plan: plan/WINDOW.md)."""
import json
import os
import platform
import plistlib
import re
import time

import pytest

from harness.app import wait_for
from harness.sci import *  # noqa: F401,F403
from _util_window import (PROXY_KEY, alerts, bring, current_title, day, delete_raw_default, kinds,
                          names_by_path, read_raw_default, repository, text_of, titles, urls, write,
                          write_raw_default)


def info_plist(app) -> dict:
    with open(app.bundle / "Contents/Info.plist", "rb") as f:
        return plistlib.load(f)


def stays(condition, seconds):
    """True when condition() holds for the whole period (polled)."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not condition():
            return False
        time.sleep(0.2)
    return True


def open_all(app, paths):
    for p in paths:
        app.open(p)


def sort(app, command):
    app.run(command)
    return titles(app)


def wait_alert(app, timeout=25.0):
    """Collects the log until an alert has been shown; returns every entry seen."""
    seen = []

    def got():
        seen.extend(app.modal_log())
        return alerts(seen)
    wait_for(got, timeout=timeout, interval=0.2, message="an alert")
    seen.extend(app.modal_log())
    return seen


def set_proxy(app, value):
    """Through Help > Set Updater Proxy…, as a user would."""
    app.answers(alerts=[{"button": 1, "field": value}])
    app.run("IDM_CONFUPDATERPROXY")
    app.modal_log()


# ---- Sort By ------------------------------------------------------------------

@pytest.mark.case("WINDOW-001")
def test_window_001_sort_by_name_a_to_z_and_z_to_a_numbers_as_numbers_and_withou(app, tmp):
    """WINDOW-001: Sort by name, A to Z and Z to A, numbers as numbers and without case"""
    open_all(app, [write(tmp / n, "x\n") for n in ("file10.txt", "File2.txt", "beta.md", "alpha.py")])
    bring(app, "File2.txt")
    asc = sort(app, "IDM_WINDOW_SORT_FN_ASC")
    assert current_title(app) == "File2.txt"
    dsc = sort(app, "IDM_WINDOW_SORT_FN_DSC")
    assert current_title(app) == "File2.txt"
    # The first file took the lone clean "new 1"'s place when it was opened (FILE-007).
    assert asc == ["alpha.py", "beta.md", "File2.txt", "file10.txt"]
    assert dsc == list(reversed(asc))


@pytest.mark.case("WINDOW-002")
def test_window_002_sort_by_path_a_to_z_and_z_to_a(app, tmp):
    """WINDOW-002: Sort by path, A to Z and Z to A"""
    open_all(app, [write(tmp / p, "x\n") for p in ("b/x.txt", "a/z.txt", "a/y.txt")])
    app.run("IDM_WINDOW_SORT_FP_ASC")
    asc = names_by_path(app, tmp)
    app.run("IDM_WINDOW_SORT_FP_DSC")
    dsc = names_by_path(app, tmp)
    # The first file took the lone clean "new 1"'s place when it was opened (FILE-007).
    assert len(asc) == 3
    assert asc == ["a/y.txt", "a/z.txt", "b/x.txt"]
    assert dsc == list(reversed(asc))


@pytest.mark.case("WINDOW-003")
def test_window_003_sort_by_type_orders_by_language(app, tmp):
    """WINDOW-003: Sort by type orders by language"""
    open_all(app, [write(tmp / n, "x\n") for n in ("a.py", "c.txt", "b.cxx", "d.cpp")])
    langs = {d["title"]: d["language"] for d in app.docs()}
    assert langs["b.cxx"] == langs["d.cpp"] == "cpp" and langs["a.py"] == "python" and langs["c.txt"] == "normal"
    asc = sort(app, "IDM_WINDOW_SORT_FT_ASC")
    dsc = sort(app, "IDM_WINDOW_SORT_FT_DSC")
    # The first file took the lone clean "new 1"'s place when it was opened (FILE-007).
    assert asc == ["b.cxx", "d.cpp", "c.txt", "a.py"]
    assert dsc == list(reversed(asc))


@pytest.mark.case("WINDOW-004")
def test_window_004_sort_by_content_length_uses_the_text_as_it_is_now(app, tmp):
    """WINDOW-004: Sort by content length uses the text as it is now"""
    open_all(app, [write(tmp / "s3.txt", "abc"), write(tmp / "s10.txt", "0123456789")])
    bring(app, "s3.txt")
    app.set_text("x" * 20)
    app.new("12345")
    five = current_title(app)
    asc = sort(app, "IDM_WINDOW_SORT_FS_ASC")
    dsc = sort(app, "IDM_WINDOW_SORT_FS_DSC")
    # The first file took the lone clean "new 1"'s place when it was opened (FILE-007).
    assert asc == [five, "s10.txt", "s3.txt"]
    assert dsc == list(reversed(asc))


@pytest.mark.case("WINDOW-005")
def test_window_005_sort_by_modified_time(app, tmp):
    """WINDOW-005: Sort by modified time"""
    times = {"t1.txt": 2020, "t2.txt": 2022, "t3.txt": 2024}
    for name, year in times.items():
        p = write(tmp / name, name)
        t = time.mktime((year, 6, 1, 12, 0, 0, 0, 0, -1))
        os.utime(p, (t, t))
    open_all(app, [tmp / "t2.txt", tmp / "t3.txt", tmp / "t1.txt"])
    # t2.txt took the lone clean "new 1"'s place when it was opened (FILE-007).
    assert sort(app, "IDM_WINDOW_SORT_FD_ASC") == ["t1.txt", "t2.txt", "t3.txt"]
    assert sort(app, "IDM_WINDOW_SORT_FD_DSC") == ["t3.txt", "t2.txt", "t1.txt"]


# ---- Windows list, droplist, tab switching --------------------------------------

@pytest.mark.case("WINDOW-006")
def test_window_006_windows_lists_every_open_document_in_tab_order(app, tmp):
    """WINDOW-006: Windows… lists every open document in tab order"""
    w1, w2 = write(tmp / "w1.txt", "1\n"), write(tmp / "sub/w2.md", "2\n")
    open_all(app, [w1, w2])
    app.new("")
    before = (titles(app), current_title(app))
    # w1 takes the place of the lone clean "new 1" (Notepad_plus::loadBufferIntoView), so the
    # untitled tab made after it is "new 1" again.
    expected = [str(w1), str(w2), "new 1"]

    def lines_ok(text):
        lines = text.split("\n")
        return len(lines) == len(expected) and all(a == b or os.path.realpath(a) == os.path.realpath(b)
                                       for a, b in zip(lines, expected))

    app.answers(alerts=["Copy"])
    app.run("IDM_WINDOW_WINDOWS")
    al = alerts(app.modal_log())
    assert len(al) == 1 and al[0]["message"] == "Windows" and al[0]["buttons"] == ["OK", "Copy"]
    assert al[0]["answered"] == "Copy"
    listing = al[0]["informative"]
    assert lines_ok(listing), listing
    assert app.clipboard() == listing

    app.answers(alerts=["OK"])
    app.run("IDM_WINDOW_WINDOWS")
    al = alerts(app.modal_log())
    assert len(al) == 1 and al[0]["answered"] == "OK" and al[0]["informative"] == listing
    assert (titles(app), current_title(app)) == before

    app.answers(alerts=["OK"])
    r = app.call("run_command", command=14001)
    assert r.get("ran"), r
    al = alerts(app.modal_log())
    assert len(al) == 1 and al[0]["informative"] == listing


@pytest.mark.case("WINDOW-007")
def test_window_007_recent_window_steps_back_to_the_previously_active_tab(app, tmp):
    """WINDOW-007: Recent Window steps back to the previously active tab"""
    open_all(app, [write(tmp / f"r{i}.txt", f"{i}\n") for i in (1, 2, 3)])
    bring(app, "r1.txt")
    bring(app, "r3.txt")
    app.run("IDM_WINDOW_MRU_FIRST")
    assert current_title(app) == "r1.txt"
    app.run("IDM_WINDOW_MRU_FIRST")
    assert current_title(app) == "r3.txt"

    bring(app, "r2.txt")
    bring(app, "r3.txt")
    r1 = next(d for d in app.docs() if d["title"] == "r1.txt")
    app.call("close_document", document=r1["index"], discard_changes=True)
    assert current_title(app) == "r3.txt"
    app.run("IDM_WINDOW_MRU_FIRST")
    assert current_title(app) == "r2.txt"

    r2 = next(d for d in app.docs() if d["title"] == "r2.txt")
    app.call("close_document", document=r2["index"], discard_changes=True)
    state = (titles(app), current_title(app))
    app.run("IDM_WINDOW_MRU_FIRST")
    assert (titles(app), current_title(app)) == state

    app.close_all()
    app.modal_log()
    app.run("IDM_WINDOW_MRU_FIRST")
    assert titles(app) == ["new 1"]
    assert not alerts(app.modal_log())


@pytest.mark.case("WINDOW-008")
def test_window_008_next_tab_and_previous_tab_cycle_through_the_tabs(app):
    """WINDOW-008: Next Tab and Previous Tab cycle through the tabs"""
    # shift+cmd+] on a keyboard gives the characters "}" (and "{" for [): sent as such.
    nxt, prv = "shift+cmd+}", "shift+cmd+{"
    for name in ("n1", "n2", "n3"):
        app.new("", title=name)
    assert titles(app) == ["new 1", "n1", "n2", "n3"]
    bring(app, "n2")
    seen = []
    for _ in range(3):
        app.keys(nxt)
        seen.append(current_title(app))
    for _ in range(2):
        app.keys(prv)
        seen.append(current_title(app))
    assert seen == ["n3", "new 1", "n1", "new 1", "n3"]

    app.close_all()
    for chord in (nxt, prv):
        app.keys(chord)
        assert titles(app) == ["new 1"] and current_title(app) == "new 1"


@pytest.mark.case("WINDOW-009")
def test_window_009_the_window_menu_has_notepad_s_items_in_order(app):
    """WINDOW-009: The Window menu has Notepad++'s items in order"""
    # Hidden items (IDM_DROPLIST_LIST, which upstream has on the tab bar's ▼) are never shown.
    # AppKit puts its tiling and Stage Manager items (private "_" actions) and a separator on top
    # once the menu has been updated for a key press; they are the system's, not the app's.
    app.new("")
    app.keys("shift+cmd+]")
    tree = [i for i in app.menu_tree("Window", 2) if not i.get("hidden")]
    while tree and (tree[0].get("separator") or (tree[0].get("action") or "").startswith("_")):
        tree.pop(0)
    # AppKit's window tabs are off: the documents are the editor's tabs (Ctrl+Tab is Notepad++'s).
    assert not {"Show Next Tab", "Show Previous Tab", "Merge All Windows", "Move Tab to New Window"} & \
        {i.get("title") for i in tree}
    head = [(i.get("title"), i.get("key")) if not i.get("separator") else "-" for i in tree[:6]]
    assert head == [("Next Tab", "shift+cmd+]"), ("Previous Tab", "shift+cmd+["), "-",
                    ("Sort By", None), ("Windows…", None), ("Recent Window", None)]
    sort_by = tree[3]["submenu"] if "submenu" in tree[3] else tree[3].get("items")
    assert [i["title"] for i in sort_by] == [
        "Name A to Z", "Name Z to A", "Path A to Z", "Path Z to A", "Type A to Z", "Type Z to A",
        "Content Length Ascending", "Content Length Descending",
        "Modified Time Ascending", "Modified Time Descending"]
    assert all(i["enabled"] for i in tree[:6] + sort_by if not i.get("separator"))
    # What follows is AppKit's own list of windows (NSApp.windowsMenu), after a separator.
    rest = tree[6:]
    if rest:
        assert rest[0].get("separator")
        assert all(i.get("action") == "makeKeyAndOrderFront:" for i in rest[1:] if not i.get("separator"))


# ---- Help: About and Debug Info ---------------------------------------------------

def about_panel(app):
    return app.wait(lambda: app.window("About Notepad++"), message="the About panel")


@pytest.mark.case("WINDOW-010")
def test_window_010_about_shows_the_version_the_build_the_licence_and_this_port(app):
    """WINDOW-010: About shows the version, the build, the licence and this port's links"""
    info = info_plist(app)
    repo = repository(app)
    app.run("IDM_ABOUT")
    w = about_panel(app)
    assert w["title"] == "About Notepad++"
    controls = app.ui(w["number"])["controls"]
    values = [c.get("value") for c in controls if isinstance(c.get("value"), str)]
    bits = "(ARM 64-bit)" if platform.machine() == "arm64" else "(64-bit)"
    assert f"Notepad++ v{info['NppUpstreamVersion']}   {bits}" in values
    assert f"macOS port {info['CFBundleShortVersionString']} (build {info['CFBundleVersion']})" in values
    assert any(v.startswith("Build time: ") and len(v) > len("Build time: ") for v in values)
    assert any(v.startswith("This program is free software") for v in values)
    links = [c["id"] for c in controls if c.get("class") == "NSButton" and (c.get("id") or "").startswith("https://")]
    assert links == [f"https://github.com/{repo}", f"https://github.com/{repo}/issues"]
    assert "notepad-plus-plus.org" not in json.dumps(controls)
    app.click(w["number"], "OK")
    app.wait(lambda: not app.window("About Notepad++"), message="About closed")

    app.call("e2e_menu_invoke", path="NotepadMac|About NotepadMac")
    w2 = about_panel(app)
    assert w2["number"] == w["number"]   # the same panel
    app.close_window(w2["number"])
    app.wait(lambda: not app.window("About Notepad++"), message="About closed")


@pytest.mark.case("WINDOW-011")
def test_window_011_about_s_link_buttons_open_the_port_s_pages(app):
    """WINDOW-011: About's link buttons open the port's pages"""
    repo = repository(app)
    app.run("IDM_ABOUT")
    w = about_panel(app)
    app.modal_log()
    for url in (f"https://github.com/{repo}", f"https://github.com/{repo}/issues"):
        app.click(w["number"], url)
    assert urls(app.modal_log()) == [f"https://github.com/{repo}", f"https://github.com/{repo}/issues"]
    app.close_window(w["number"])


@pytest.mark.case("WINDOW-012")
def test_window_012_debug_info_lists_upstream_s_fields_as_they_are_now(app):
    """WINDOW-012: Debug Info lists upstream's fields as they are now"""
    was = app.pref("autosaveEnabled")
    repo = repository(app)
    app.set_prefs(autosaveEnabled=True)
    try:
        app.run("IDM_DEBUGINFO")
        w = app.wait(lambda: app.window("Debug Info"), message="Debug Info")
        text = next(c["value"] for c in app.ui(w["number"])["controls"] if c.get("class") == "NSTextView")
        fields = ["Notepad++ v", "macOS port: ", "Build time: ", "Built with: Clang ", "Scintilla/Lexilla included: 5.",
                  f"Path: {app.executable}", "Command Line: ", "Admin mode: OFF", "Local Conf mode: OFF",
                  "Cloud Config: OFF", f"Auto-updater: disabled (GitHub Releases of {repo})", "Periodic Backup: ON",
                  "Multi-instance Mode: monoInst", "File Status Auto-Detection: cdEnabledNew", "Dark Mode: ",
                  "Display Info:", "OS Name: macOS", "OS Version: ", "Current ANSI codepage: ", "Plugins: none"]
        at = 0
        for f in fields:
            i = text.find(f, at)
            assert i >= 0, f"{f!r} missing or out of order in:\n{text}"
            at = i + len(f)
        cmdline = next(l for l in text.splitlines() if l.startswith("Command Line: "))
        assert "-nosession" in cmdline
        app.click(w["number"], "Copy debug info to clipboard")
        assert app.clipboard() == text
        app.click(w["number"], "OK")
        app.wait(lambda: not app.window("Debug Info"), message="Debug Info closed")
    finally:
        app.set_prefs(autosaveEnabled=was)


SWITCHES = ["-n", "-c", "-p", "-l", "-udl=", "-ro", "-fullReadOnly", "-nosession", "-openSession", "-r",
            "-openFoldersAsWorkspace", "-monitor", "-alwaysOnTop", "-notabbar", "-titleAdd=", "-settingsDir=",
            "-qt=", "-qf=", "-notepadStyleCmdline", "-z", "-quickPrint", "-export=functionList", "-x", "-y",
            "-multiInst", "-noPlugin", "-systemtray", "-loadingTime", "-pluginMessage="]


@pytest.mark.case("WINDOW-013")
def test_window_013_command_line_arguments_documents_every_switch_the_applicatio(app):
    """WINDOW-013: Command Line Arguments documents every switch the application reads"""
    app.answers(alerts=["Copy"])
    app.run("IDM_CMDLINEARGUMENTS")
    al = alerts(app.modal_log())
    assert len(al) == 1 and al[0]["message"] == "Command Line Arguments" and al[0]["buttons"] == ["OK", "Copy"]
    text = al[0]["informative"]
    # NSAlert shows the text with each line's leading blanks dropped; the copy keeps them.
    assert [l.strip() for l in app.clipboard().splitlines()] == [l.strip() for l in text.splitlines()]
    missing = [s for s in SWITCHES if not re.search(r"(?<![\w-])" + re.escape(s) + ("" if s.endswith("=") else r"(?![A-Za-z])"), text)]
    assert not missing, missing


# ---- Help: links and updates --------------------------------------------------------

@pytest.mark.case("WINDOW-014")
def test_window_014_the_help_links_lead_to_this_port_s_pages_and_upstream_s_manu(app):
    """WINDOW-014: The Help links lead to this port's pages and upstream's manual"""
    repo = repository(app)
    for cmd in ("IDM_HOMESWEETHOME", "IDM_PROJECTPAGE", "IDM_ONLINEDOCUMENT", "IDM_FORUM"):
        app.run(cmd)
    got = urls(app.modal_log())
    assert got == [f"https://github.com/{repo}#readme", f"https://github.com/{repo}",
                   "https://npp-user-manual.org/", f"https://github.com/{repo}/discussions"]
    for u in got:
        assert u.startswith("https://") and "notepad-plus-plus.org" not in u and "github.com/notepad-plus-plus" not in u
    tree = app.menu_tree("Help", 1)
    items = ["-" if i.get("separator") else i["title"] for i in tree]
    assert items == ["Notepad++ Home", "Notepad++ Project Page", "Notepad++ Online User Manual",
                     "Notepad++ Community (Forum)", "-", "Command Line Arguments…", "Debug Info…",
                     "Check for Updates", "Set Updater Proxy…", "About NotepadMac"]


@pytest.mark.case("WINDOW-015")
def test_window_015_set_updater_proxy_asks_for_host_port_and_remembers_it(app):
    """WINDOW-015: Set Updater Proxy asks for host:port and remembers it"""
    delete_raw_default(app, PROXY_KEY)
    try:
        app.answers(alerts=[{"button": 1, "field": "proxy.example:8080"}])
        app.run("IDM_CONFUPDATERPROXY")
        al = alerts(app.modal_log())
        assert len(al) == 1 and al[0]["message"] == "Updater proxy (host:port)"
        assert al[0]["buttons"] == ["OK", "Cancel"] and al[0]["fields"] == [""]
        app.wait(lambda: read_raw_default(app, PROXY_KEY) == "proxy.example:8080", message="the proxy stored")

        app.answers(alerts=[{"button": 2, "field": "other:1"}])
        app.run("IDM_CONFUPDATERPROXY")
        al = alerts(app.modal_log())
        assert len(al) == 1 and al[0]["fields"] == ["proxy.example:8080"] and al[0]["answered"] == "Cancel"
        assert stays(lambda: read_raw_default(app, PROXY_KEY) == "proxy.example:8080", 1.0)

        app.answers(alerts=[{"button": 1, "field": ""}])
        app.run("IDM_CONFUPDATERPROXY")
        assert len(alerts(app.modal_log())) == 1
        app.wait(lambda: read_raw_default(app, PROXY_KEY) == "", message="the proxy emptied")
    finally:
        delete_raw_default(app, PROXY_KEY)


@pytest.mark.case("WINDOW-016")
def test_window_016_check_for_updates_reports_a_failure_without_the_network(app):
    """WINDOW-016: Check for Updates reports a failure without the network"""
    repo = repository(app)
    set_proxy(app, "127.0.0.1:1")
    try:
        app.answers(alerts=["Open the Releases Page"])
        app.run("IDM_UPDATE_NPP")
        seen = wait_alert(app)     # the application answers while the check runs: this polls it
        al = alerts(seen)
        assert len(al) == 1 and al[0]["message"] == "Notepad++ update"
        assert al[0]["buttons"] == ["OK", "Open the Releases Page"]
        info = al[0]["informative"]
        assert f"https://api.github.com/repos/{repo}/releases/latest" in info
        assert info.split("\n")[0].strip(), info   # an error description comes first
        assert urls(seen) == [f"https://github.com/{repo}/releases"]

        app.answers(alerts=["OK"])
        app.run("IDM_UPDATE_NPP")
        seen = wait_alert(app)
        assert alerts(seen)[0]["answered"] == "OK" and not urls(seen)
    finally:
        delete_raw_default(app, PROXY_KEY)


@pytest.mark.restart
@pytest.mark.case("WINDOW-017")
def test_window_017_check_for_updates_offers_a_newer_release_and_says_when_there(app, tmp):
    """WINDOW-017: Check for Updates offers a newer release and says when there is none"""
    current = info_plist(app)["NppUpstreamVersion"]
    latest = write(tmp / "latest.json", json.dumps({"tag_name": "v99.0.0", "name": "NotepadMac 99",
                                                    "html_url": "https://github.com/o/r/releases/tag/v99.0.0"}))
    try:
        app.start(env={"NPPMAC_E2E_RELEASE_URL": str(latest)})
        app.answers(alerts=["Yes"])
        app.run("IDM_UPDATE_NPP")
        seen = wait_alert(app)
        al = alerts(seen)
        assert len(al) == 1 and al[0]["message"] == "Notepad++ update" and al[0]["buttons"] == ["Yes", "No"]
        assert "An update package is available, do you want to download it?" in al[0]["informative"]
        assert f"NotepadMac 99 (you have v{current})" in al[0]["informative"]
        assert urls(seen) == ["https://github.com/o/r/releases/tag/v99.0.0"]

        write(latest, json.dumps({"tag_name": f"v{current}", "name": f"NotepadMac {current}",
                                  "html_url": f"https://github.com/o/r/releases/tag/v{current}"}))
        app.answers(alerts=["OK"])
        app.run("IDM_UPDATE_NPP")
        seen = wait_alert(app)
        al = alerts(seen)
        assert len(al) == 1 and al[0]["buttons"] == ["OK"]
        assert "No update is available." in al[0]["informative"]
        assert f"v{current}" in al[0]["informative"] and f"NotepadMac {current}" in al[0]["informative"]
        assert not urls(seen)
    finally:
        app.start()


@pytest.mark.restart
@pytest.mark.slow
@pytest.mark.case("WINDOW-018")
def test_window_018_the_automatic_update_check_follows_its_schedule_quietly(app):
    """WINDOW-018: The automatic update check follows its schedule quietly"""
    try:
        app.stop()
        app.reset_defaults({"autoUpdateMode": 1, "nextUpdateDate": "20200101", "updateIntervalDays": 15})
        write_raw_default(app, PROXY_KEY, "127.0.0.1:1")
        app.start(reset=False)
        app.wait(lambda: app.read_default("nextUpdateDate") != "20200101", timeout=30, message="the schedule moved")
        assert app.read_default("nextUpdateDate") == day(15)
        # the failed check stays quiet
        assert stays(lambda: not alerts(app.modal_log(clear=False)), 3)

        app.stop()
        app.write_default("nextUpdateDate", day(30))
        app.start(reset=False)
        assert stays(lambda: app.read_default("nextUpdateDate") == day(30), 6)

        app.stop()
        app.write_default("autoUpdateMode", 0)
        app.write_default("nextUpdateDate", "20200101")
        app.start(reset=False)
        assert stays(lambda: app.read_default("nextUpdateDate") == "20200101", 6)
        assert not alerts(app.modal_log())
    finally:
        app.start()


@pytest.mark.restart
@pytest.mark.slow
@pytest.mark.case("WINDOW-019")
def test_window_019_the_update_check_on_exit_moves_the_schedule_and_opens_nothin(app):
    """WINDOW-019: The update check on exit moves the schedule and opens nothing"""
    try:
        app.stop()
        app.reset_defaults({"autoUpdateMode": 2, "nextUpdateDate": "20200101", "updateIntervalDays": 15})
        write_raw_default(app, PROXY_KEY, "127.0.0.1:1")
        app.start(reset=False)
        assert stays(lambda: app.read_default("nextUpdateDate") == "20200101", 5)
        proc = app.proc
        app.answers(clear=True)
        t0 = time.monotonic()
        try:
            app.invoke("nsapp", "terminate:", [None], timeout=3)
        except Exception:  # noqa: BLE001 - the process may go before it answers
            pass
        status = proc.wait(10)
        assert time.monotonic() - t0 < 10
        assert status == 0
        app.stop()
        assert app.read_default("nextUpdateDate") == day(15)
    finally:
        app.start()
