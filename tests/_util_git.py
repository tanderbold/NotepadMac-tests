"""Helpers for the Git tests (tests/test_git.py): repositories made with the git CLI,
and reading what the editor shows about them."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from harness.app import ToolError

SCI_MARKERGET = 2046
SCI_GETMARGINWIDTHN = 2243
SCI_GETLENGTH = 2006
SCI_GETTEXT = 2182
SCI_LINEFROMPOSITION = 2166
SCI_GETCURRENTPOS = 2008
SCI_GETLINECOUNT = 2154

GIT_MASK = (1 << 6) | (1 << 7) | (1 << 8)
ADDED, CHANGED, REMOVED = 1 << 6, 1 << 7, 1 << 8
COMPARE_MASK = (1 << 0) | (1 << 2) | (1 << 3) | (1 << 4)

NOT_IN_REPO = "The file is not in a Git repository"


# ---- the git CLI ----------------------------------------------------------

def git(repo, *args, check=True) -> str:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="en_US.UTF-8")
    r = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {r.stderr}")
    return r.stdout.rstrip("\n")


def configure(repo):
    git(repo, "config", "user.name", "T Runner")
    git(repo, "config", "user.email", "t@example.invalid")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "config", "core.autocrlf", "false")


def make_repo(parent: Path, name: str = "repo", files: dict | None = None, commit: bool = True,
              branch: str = "main") -> Path:
    """A repository with an identity in its config and, unless told otherwise, one commit."""
    repo = Path(parent) / name
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q", "-b", branch)
    configure(repo)
    for rel, text in (files if files is not None else {"a.txt": "one\ntwo\nthree\nfour\n"}).items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    if commit and (files is None or files):
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", "first")
    return repo


def commit_all(repo, message: str):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def porcelain(repo) -> str:
    return git(repo, "status", "--porcelain")


# ---- what the editor shows --------------------------------------------------

def markers(app, lines) -> list[int]:
    return [app.sci(SCI_MARKERGET, i) & GIT_MASK for i in lines]


def line_count(app) -> int:
    return app.sci(SCI_GETLINECOUNT)


def margin_width(app) -> int:
    return app.sci(SCI_GETMARGINWIDTHN, 4)


def wait_markers(app, lines, expected, timeout=6.0):
    """Polls until the git markers on `lines` are `expected`; returns them."""
    last = []

    def ok():
        nonlocal last
        last = markers(app, lines)
        return last == list(expected)
    try:
        app.wait(ok, timeout, message=f"git markers {expected}")
    except TimeoutError:
        pass
    return last


def _ui_ok(app) -> bool:
    """Whether e2e_ui answers in this app run (it can hang on some builds)."""
    key = getattr(app.proc, "pid", None)
    cache = getattr(app, "_git_ui_ok", None)
    if cache and cache[0] == key:
        return cache[1]
    try:
        app.call("e2e_ui", window="main", timeout=6)
        ok = True
    except Exception:  # noqa: BLE001 - a timeout or an error: fall back
        ok = False
    app._git_ui_ok = (key, ok)
    return ok


def status_text(app) -> str:
    """The status bar field that carries Ln:/Col: and, in a repository, the branch."""
    if _ui_ok(app):
        for c in app.ui("main")["controls"]:
            v = c.get("value")
            if isinstance(v, str) and "Ln:" in v:
                return v
    return app.get("editor", "statusField.stringValue") or ""


def console_text(app) -> str:
    return app.get("editor", "console.text") or ""


def console_visible(app) -> bool:
    return bool(app.get("editor", "console.visible"))


def panel_visible(app) -> bool:
    return bool(app.get("editor", "gitPanel.visible"))


def show_panel(app):
    if not panel_visible(app):
        app.run("Plugins|Git|Git Panel")
    app.wait(lambda: panel_visible(app), 5, message="the Git panel")


def hide_panel(app):
    try:
        if panel_visible(app):
            app.run("Plugins|Git|Git Panel")
    except Exception:  # noqa: BLE001 - teardown
        pass


def _panel_table(app):
    for c in app.ui("main")["controls"]:
        if c.get("class") == "NSTableView" and c.get("columns") == ["Staged", "Status", "File"]:
            return c
    return None


def panel_rows(app) -> list[list[str]]:
    """The Git panel's table cells, row by row: [staged, status, file]."""
    if _ui_ok(app):
        t = _panel_table(app)
        if t is not None:
            return [list(r) for r in t.get("cells", [])]
    paths = app.get("editor", "gitPanel.rows.path") or []
    status = app.get("editor", "gitPanel.rows.shortStatus") or []
    staged = app.get("editor", "gitPanel.rows.staged") or []
    renamed = app.get("editor", "gitPanel.rows.renamedFrom") or [None] * len(paths)
    out = []
    for p, s, st, r in zip(paths, status, staged, renamed):
        out.append(["✓" if st else "", s, f"{p} ← {r}" if r else p])
    return out


def panel_label(app) -> str:
    return app.get("editor", "gitPanel.branchLabel.stringValue") or ""


def table_act(app, action, row, extend=False):
    args = {"window": "main", "action": action, "value": row, "target": {"class": "NSTableView"}}
    if extend:
        args["extend"] = True
    return app.call("e2e_act", **args)


def panel_button(app, title):
    return app.act("main", "click", **{"class": "NSButton", "title": title})


# ---- the Commit window -------------------------------------------------------

CW = "class:NppCommitWindow"


def commit_window(app):
    for w in app.windows():
        if w["title"] == "Commit" and w["visible"]:
            return w["number"]
    return None


def cw_get(app, key):
    return app.get(CW, key)


def commit_summary(app) -> str:
    return cw_get(app, "stagedSummary.stringValue") or ""


def commit_enabled(app) -> bool:
    return bool(cw_get(app, "commitButton.isEnabled"))


def open_commit_window(app):
    app.run("Plugins|Git|Commit...")
    return app.wait(lambda: commit_window(app), 5, message="the Commit window")


def set_message(app, cw, text):
    app.act(cw, "set_text", text, **{"class": "NSTextView"})


def click_commit(app, cw):
    app.act(cw, "click", **{"class": "NSButton", "title": "Commit"})


def run_git(app, item):
    """Runs a Plugins > Git command by its menu path."""
    return app.run(f"Plugins|Git|{item}")


def wait_console_end(app, since: int, count: int = 1, timeout=25.0) -> str:
    """Polls until `count` of '- done' / '- git failed' appear after offset `since`."""
    def ended():
        t = console_text(app)[since:]
        return t if t.count("- done") + t.count("- git failed") >= count else None
    return app.wait(ended, timeout, message="the git command to end in the console")


def safe(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except (ToolError, Exception):  # noqa: BLE001
        return None
