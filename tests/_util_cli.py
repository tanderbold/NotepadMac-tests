"""Helpers for the CLI tests: running the copy's nppmac, launching with switches."""
import json
import os
import subprocess
import time
from pathlib import Path

from harness.app import App, wait_for  # noqa: F401
from harness.sci import SCI_GETCURRENTPOS, SCI_LINEFROMPOSITION, SCI_GETCOLUMN, SCI_GETREADONLY

# The print guard in the build (E2EHooks.mm): a job that is not a save-to-file job is refused.
PRINT_GUARD = b"refused a print job that would reach a printer"


def write(path, data="", mode=None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    if mode is not None:
        os.chmod(path, mode)
    return path


def nppmac(app, *args, cwd=None, input=None, env=None, timeout=30):
    """Runs the copy's nppmac (only while the test app runs: it would launch
    the copy without the harness's isolation otherwise)."""
    assert app.running, "nppmac is run only while the test app is running"
    full_env = dict(os.environ)
    full_env.update(env or {})
    return subprocess.run([str(app.cli), *[str(a) for a in args]], cwd=cwd, input=input, env=full_env,
                          capture_output=True, timeout=timeout)


def titles(app) -> list:
    return [d["title"] for d in app.docs()]


def current(app) -> dict:
    return next(d for d in app.docs() if d["current"])


def find_doc(app, path):
    for d in app.docs():
        if d["path"] and App.same_path(d["path"], path):
            return d
    return None


def wait_open(app, *paths, timeout=10.0):
    """Polls until every path is open (and its text read)."""
    def ok():
        return all(find_doc(app, p) for p in paths)
    app.wait(ok, timeout, message=f"{[Path(p).name for p in paths]} open")
    # the tab comes before its text: wait for the current one's bytes too
    app.idle(0.05)
    return app.docs()


def front(app, path):
    """Brings an open document forward without changing its caret."""
    d = find_doc(app, path)
    assert d, f"{path} is not open"
    app.open(path)
    return d


def caret(app, view="main"):
    """(line, column), 1-based, and the position of the caret."""
    pos = app.sci(SCI_GETCURRENTPOS, view=view)
    line = app.sci(SCI_LINEFROMPOSITION, pos, view=view)
    col = app.sci(SCI_GETCOLUMN, pos, view=view)
    return line + 1, col + 1, pos


def read_only(app) -> bool:
    return bool(app.sci(SCI_GETREADONLY))


def alerts(entries) -> list:
    return [e for e in entries if e.get("kind") == "alert"]


def support(app) -> Path:
    return app.home / "Library/Application Support/NotepadMac"


def raw_env(app) -> dict:
    """The environment App.start gives the copy, for launching its executable directly."""
    env = dict(os.environ)
    env.update({"CFFIXED_USER_HOME": str(app.home), "NPPMAC_AGENT_SOCKET": app.socket_path,
                "NPPMAC_E2E": "1", "NPPMAC_E2E_CLI_DIR": str(app.work / "bin"),
                "NPPMAC_E2E_PRINT_DIR": str(app.print_dir)})
    for k in ("NPPMAC_TEST", "NPPMAC_SNAPSHOT", "NPPMAC_SELFTEST"):
        env.pop(k, None)
    return env


def run_executable(app, args, timeout=10.0):
    """Launches the copy's executable (no -nosession, no agent flag) and waits for
    it to quit by itself; returns (returncode or None when it did not quit, seconds)."""
    app.stop()
    app.prepare()
    (app.work / "bin").mkdir(exist_ok=True)
    app.print_dir.mkdir(exist_ok=True)
    with open(app.log_path, "ab") as log:
        proc = subprocess.Popen([str(app.executable), *[str(a) for a in args]], env=raw_env(app),
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        start = time.monotonic()
        try:
            rc = proc.wait(timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            rc = None
    return rc, time.monotonic() - start


def mcp_lines(*messages) -> bytes:
    return b"".join(json.dumps(m).encode() + b"\n" for m in messages)
