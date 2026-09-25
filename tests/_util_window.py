"""Helpers shared by the WINDOW tests."""
import datetime
import os
import subprocess
from pathlib import Path

from harness.app import App, ToolError  # noqa: F401

PROXY_KEY = "NppMacUpdaterProxy"   # has no NppMac. prefix


def write(path, data) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
    return path


def titles(app) -> list:
    return [d["title"] for d in app.docs()]


def current_title(app) -> str:
    return next(d["title"] for d in app.docs() if d["current"])


def bring(app, title):
    """Makes the tab with this title current (by its index, as a tab click)."""
    d = next(d for d in app.docs() if d["title"] == title)
    app.call("go_to", document=d["index"], line=1)
    app.wait(lambda: current_title(app) == title, message=f"{title} current")


def names_by_path(app, root) -> list:
    """Tab order as paths relative to root, untitled tabs by their title."""
    out = []
    for d in app.docs():
        if d["path"]:
            out.append(os.path.relpath(os.path.realpath(d["path"]), os.path.realpath(root)))
        else:
            out.append(d["title"])
    return out


def kinds(entries, kind) -> list:
    return [e for e in entries if e.get("kind") == kind]


def alerts(entries) -> list:
    return kinds(entries, "alert")


def urls(entries) -> list:
    return [e["target"] for e in kinds(entries, "open_url")]


def repository(app) -> str:
    return app.pref("updateRepository")


def read_raw_default(app, key):
    r = subprocess.run(["defaults", "read", app.bundle_id, key], capture_output=True, text=True)
    return r.stdout.rstrip("\n") if r.returncode == 0 else None


def write_raw_default(app, key, value: str):
    subprocess.run(["defaults", "write", app.bundle_id, key, "-string", value], check=True)


def delete_raw_default(app, key):
    subprocess.run(["defaults", "delete", app.bundle_id, key], capture_output=True)


def day(offset: int = 0) -> str:
    return (datetime.date.today() + datetime.timedelta(days=offset)).strftime("%Y%m%d")


def text_of(controls) -> str:
    """All the visible text in a window's controls, one control per line."""
    parts = []
    for c in controls:
        for k in ("title", "value", "text", "string"):
            v = c.get(k)
            if isinstance(v, str) and v:
                parts.append(v)
    return "\n".join(parts)
