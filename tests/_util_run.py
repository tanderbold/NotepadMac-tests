"""Helpers for the RUN tests (Run menu and NppExec)."""
from __future__ import annotations

import os
import time
from pathlib import Path

STOP = "Plugins|NppExec|Stop Running NppExec Script"
EXEC_DIALOG = "Execute NppExec Script"


def console(app) -> str:
    """The Console panel's whole text (it keeps its text while hidden)."""
    return app.get("editor", "console.text") or ""


class Mark:
    """What the Console gets after this point: the panel keeps text across tests."""

    def __init__(self, app):
        self.app = app
        self.offset = len(console(app))

    def text(self) -> str:
        return console(self.app)[self.offset:]

    def wait(self, needle: str, timeout: float = 10.0) -> str:
        self.app.wait(lambda: needle in self.text(), timeout, message=f"{needle!r} in the Console")
        return self.text()

    def lines(self) -> list[str]:
        return self.text().splitlines()


def run_prompt(app, command: str):
    """Run… with the prompt answered OK and the given command line."""
    app.answers(alerts=[{"button": 1, "field": command}])
    return app.run("IDM_EXECUTE")


def run_and_wait(app, command: str, needle: str, timeout: float = 10.0) -> str:
    m = Mark(app)
    run_prompt(app, command)
    return m.wait(needle, timeout)


def run_to_end(app, command: str, timeout: float = 10.0) -> str:
    """Runs a command with a trailing marker line; returns the Console text before that marker line
    (the echoed "> " command line included)."""
    token = f"END-RUN-{time.monotonic_ns()}"
    m = Mark(app)
    run_prompt(app, f"{command}; echo {token}")
    app.wait(lambda: token in m.lines(), timeout, message=f"{token} in the Console")
    lines = m.lines()
    return "\n".join(lines[: lines.index(token)]) + "\n"


def output_lines(text: str) -> list[str]:
    """The lines a command printed (without the echoed "> " command lines)."""
    return [l for l in text.splitlines() if not l.startswith("> ")]


def key_name(key: str | None) -> str:
    """Menu key equivalents as e2e_menu reports them, with F-keys given their names."""
    return (key or "").replace("\uf709", "f6")


def clear_saved_commands(app):
    app.set_prefs(savedRunCommands=[])
    app.invoke("app", "rebuildRunMenu")


def saved_scripts_file(app) -> Path:
    return app.home / "Library/Application Support/NotepadMac/npes_saved.txt"


def clear_saved_scripts(app):
    f = saved_scripts_file(app)
    if f.exists():
        f.unlink()
    app.invoke("app", "rebuildExecMenu")


def stop_enabled(app) -> bool:
    return app.enabled(STOP)


def open_exec_dialog(app, path: str = "Plugins|NppExec|Execute NppExec Script…"):
    """Runs a menu command that opens the Execute NppExec Script dialog (a real modal);
    returns (pending call, window)."""
    pending = app.run_async(path)
    # Workaround (harness): a request that reaches the app while the command is still
    # entering its modal loop is never answered (reproduced 1 in 1 without the pause,
    # 0 in 6 with it), so let the modal start before asking anything else.
    time.sleep(0.5)
    w = app.wait(lambda: app.window(EXEC_DIALOG), 5, message="the Execute dialog")
    return pending, w


def dialog_controls(app, w):
    return app.ui(w["number"])["controls"]


def dialog_text_view(app, w):
    return [c for c in dialog_controls(app, w) if c["class"] == "NSTextView"][0]


def dialog_popup(app, w):
    return [c for c in dialog_controls(app, w) if c["class"] == "NSPopUpButton"][0]


def set_dialog_text(app, w, text: str):
    app.act(w["number"], "set_text", text, path=dialog_text_view(app, w)["path"])


def close_dialog(app, pending, w, button: str):
    app.click(w["number"], button)
    app.wait(lambda: not app.window(EXEC_DIALOG), 5, message="the dialog to close")
    pending.wait(10)


def exec_script(app, text: str, wait_for: str | None = None, timeout: float = 15.0) -> str:
    """Runs a temporary script through the Execute dialog; waits until it has finished."""
    m = Mark(app)
    pending, w = open_exec_dialog(app)
    set_dialog_text(app, w, text)
    close_dialog(app, pending, w, "OK")
    if wait_for:
        m.wait(wait_for, timeout)
    wait_script_done(app, timeout)
    return m.text()


def wait_script_done(app, timeout: float = 15.0):
    # the engine runs on its own queue; Stop is enabled while it runs
    app.idle(0.2)
    app.wait(lambda: not stop_enabled(app), timeout, message="the script to finish")
    app.idle(0.2)


def luminance(rgb) -> float:
    r, g, b = [c / 255 for c in rgb[:3]]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def sleep_children_of(pid: int, pattern: str) -> list[int]:
    """Processes whose command line matches pattern and that descend from pid."""
    import subprocess
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True).stdout
    parent = {}
    cmd = {}
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        p, pp, c = int(parts[0]), int(parts[1]), parts[2]
        parent[p] = pp
        cmd[p] = c
    found = []
    for p, c in cmd.items():
        if pattern not in c:
            continue
        q = p
        while q in parent and q not in (0, 1):
            if parent[q] == pid:
                found.append(p)
                break
            q = parent[q]
    return found


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def real(p) -> str:
    return os.path.realpath(str(p))
