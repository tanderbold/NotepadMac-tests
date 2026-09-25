"""Helpers shared by the FILE, SESSION, CLI and WINDOW tests."""
import os
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

from harness.app import App, ToolError  # noqa: F401


def write(path, data, mode=None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    path.write_bytes(data)
    if mode is not None:
        os.chmod(path, mode)
    return path


def titles(app) -> list:
    return [d["title"] for d in app.docs()]


def current(app) -> dict:
    return next(d for d in app.docs() if d["current"])


def find_doc(app, path):
    for d in app.docs():
        if d["path"] and App.same_path(d["path"], path):
            return d
    return None


def front(app, path):
    """Brings an open document to the front, keeping its caret."""
    d = find_doc(app, path)
    assert d, f"{path} is not open"
    app.open(path)  # an open file is brought to front
    return d


def log(app) -> list:
    return app.modal_log()


def alerts(entries) -> list:
    return [e for e in entries if e.get("kind") == "alert"]


def panels(entries) -> list:
    return [e for e in entries if e.get("kind") in ("open", "save")]


def support(app) -> Path:
    return app.home / "Library/Application Support/NotepadMac"


def quit_app(app, alerts_=None, timeout=15.0) -> int:
    """Quits through NSApp terminate: with the given alert answers; returns the exit status."""
    app.answers(alerts=alerts_ or [], clear=True)
    try:
        app.invoke("nsapp", "terminate:", [None], timeout=5)
    except Exception:  # noqa: BLE001 - the connection goes with the app
        pass
    rc = app.proc.wait(timeout)
    if app.conn:
        app.conn.close()
    app.conn = None
    app.proc = None
    if os.path.exists(app.socket_path):
        os.unlink(app.socket_path)
    return rc


@contextmanager
def relaunched(app, **kwargs):
    """Runs the body in an app started with kwargs; afterwards a plain app runs again."""
    try:
        app.start(**kwargs)
        yield app
    finally:
        try:
            app.start()
        except Exception:  # noqa: BLE001
            app.stop(graceful=False)
            app.start()


def wait_docs(app, pred, timeout=10.0, message="documents"):
    return app.wait(lambda: pred(app.docs()), timeout=timeout, message=message)


def reactivate(app):
    """The application comes back to the front. Hiding and activating it from a test does
    not reliably deliver NSApplicationDidBecomeActive while another application is in
    front, so the delegate's activation handler is called as AppKit calls it."""
    app.invoke("app", "applicationDidBecomeActive:", [None])
    app.idle(0.2)


def wait_log(app, pred, timeout=10.0):
    """Collects log entries until pred(entries) holds; returns them."""
    got = []

    def check():
        got.extend(app.modal_log())
        return pred(got)
    app.wait(check, timeout=timeout, message="modal log")
    return got


def defaults_read(app, key):
    r = subprocess.run(["defaults", "read", app.bundle_id, key], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def defaults_write(app, key, value: str):
    subprocess.run(["defaults", "write", app.bundle_id, key, "-string", value], check=True)


def defaults_delete(app, key):
    subprocess.run(["defaults", "delete", app.bundle_id, key], capture_output=True)


def mtime(path):
    return os.stat(path).st_mtime_ns


def rewrite(path, data):
    """Another program rewrites a file: new contents and a clearly newer modification time."""
    before = os.stat(path).st_mtime if os.path.exists(path) else time.time()
    write(path, data)
    t = max(time.time(), before) + 5
    os.utime(path, (t, t))


def pdf_text(path) -> str:
    """The text of a PDF, read with PDFKit."""
    r = subprocess.run(["osascript", "-l", "JavaScript", "-e",
                        'ObjC.import("Quartz"); function run(a){ var d=$.PDFDocument.alloc.initWithURL('
                        '$.NSURL.fileURLWithPath(a[0])); return d.isNil() ? "" : d.string.js; }', str(path)],
                       capture_output=True, text=True, timeout=30)
    return r.stdout
