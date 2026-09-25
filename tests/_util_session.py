"""Helpers for the SESSION tests: session files, restarts, backups."""
import os
import signal
import time
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path

from harness.app import App, ToolError  # noqa: F401
from harness.sci import SCI_GETANCHOR, SCI_GETCURRENTPOS

from _util_file import alerts, find_doc, write  # noqa: F401


def support(app) -> Path:
    return app.home / "Library/Application Support/NotepadMac"


def session_xml(app) -> Path:
    return support(app) / "session.xml"


def backup_dir(app) -> Path:
    return support(app) / "backup"


def backups(app) -> dict:
    """Backup file name -> its bytes."""
    d = backup_dir(app)
    if not d.is_dir():
        return {}
    out = {}
    for p in d.iterdir():
        if p.is_file():
            try:
                out[p.name] = p.read_bytes()
            except OSError:
                pass
    return out


def parse(path) -> ET.Element:
    return ET.parse(str(path)).getroot()


def files_of(root, view="mainView") -> list:
    return root.find("Session").find(view).findall("File")


def file_entry(root, path, view="mainView"):
    for f in files_of(root, view):
        if App.same_path(f.get("filename"), path):
            return f
    return None


def marks(entry, kind="Mark") -> list:
    return [int(m.get("line")) for m in entry.findall(kind)]


def save_session(app, path):
    app.answers(panels=[str(path)], clear=True)
    app.run("IDM_FILE_SAVESESSION")
    return app.modal_log()


def load_session(app, path, alerts_=None):
    app.answers(panels=[str(path)], alerts=alerts_ or [], clear=True)
    app.run("IDM_FILE_LOADSESSION")
    return app.modal_log()


def caret_anchor(app):
    return app.sci(SCI_GETANCHOR), app.sci(SCI_GETCURRENTPOS)


def front(app, path):
    d = find_doc(app, path)
    assert d, f"{path} is not open"
    app.open(path)   # an open file is brought to the front
    return d


def names(app) -> list:
    return [d["title"] for d in app.docs()]


def doc_named(app, title):
    return next((d for d in app.docs() if d["title"] == title), None)


def tab_colour(app, title):
    """The tab bar's own record of a tab's colour (0 = none)."""
    bars = [c for c in app.ui()["controls"] if c.get("class") == "NppTabBarView" and c.get("tabs")]
    for bar in bars:
        for t in bar["tabs"]:
            if t.get("title") == title:
                return t.get("colour")
    return None


def quit_app(app, answers=None, timeout=15.0) -> int:
    """Quits through NSApp terminate: (as Quit does) with only the given alert answers
    queued; returns the exit status. Raises TimeoutError when the app stays up."""
    app.answers(alerts=answers or [], clear=True)
    app.modal_log(clear=True)
    try:
        app.invoke("nsapp", "terminate:", [None], timeout=5)
    except Exception:  # noqa: BLE001 - the connection goes with the app
        pass
    rc = app.proc.wait(timeout)
    _forget(app)
    return rc


def kill_app(app):
    """A crash: SIGKILL, nothing written at quit."""
    app.proc.send_signal(signal.SIGKILL)
    app.proc.wait(10)
    _forget(app)


def _forget(app):
    if app.conn:
        app.conn.close()
    app.conn = None
    app.proc = None
    if os.path.exists(app.socket_path):
        os.unlink(app.socket_path)


def relaunch(app, **kwargs):
    """Starts again keeping home and preferences, with the session."""
    kwargs.setdefault("session", True)
    kwargs.setdefault("clean_home", False)
    kwargs.setdefault("reset", False)
    app.start(**kwargs)
    # Launch-time work (the session) settles on the main thread before the socket is served,
    # but give the run loop a turn for delayed refreshes.
    app.idle(0.2)
    return app


@contextmanager
def with_session(app, **defaults):
    """An app started with the session kept (restoreSession on unless told) and a clean
    home; afterwards the plain -nosession app of the suite runs again."""
    defaults.setdefault("restoreSession", True)
    try:
        app.start(session=True, defaults=defaults)
        app.idle(0.2)
        yield app
    finally:
        try:
            if app.running:
                app.stop(graceful=False)
            app.start()
        except Exception:  # noqa: BLE001
            app.stop(graceful=False)
            app.start()


def wait_file(path, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if Path(path).exists():
            return True
        time.sleep(0.1)
    raise TimeoutError(f"{path} did not appear")
