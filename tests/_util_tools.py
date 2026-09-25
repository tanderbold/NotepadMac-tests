"""Helpers for the TOOLS tests: the Tools windows driven through their controls,
and the local HTTP test server."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT.parent / "npp" / "macos" / "test-http-server.py"

DIGESTS = ["MD5", "SHA-1", "SHA-256", "SHA-512", "SHA-224", "SHA-384", "SHA3-256", "SHA3-512", "BLAKE2b", "CRC-32"]
KINDS = ["bcrypt", "scrypt", "Argon2", "PBKDF2"]
THREE = ["Generate…", "Generate from files…", "Generate from selection into clipboard"]


def tool_windows(app):
    return [w for w in app.windows() if not w["main_window"] and w["visible"] and not w.get("sheet")]


def open_tool(app, command, title=None, timeout=5.0):
    """Runs a Tools command and returns the number of the window it shows."""
    app.run(command)

    def found():
        for w in tool_windows(app):
            if title is None or w["title"] == title:
                return w["number"]
        return None
    return app.wait(found, timeout, f"window {title or command}")


def controls(app, w):
    return app.ui(w)["controls"]


def by_title(app, w, title):
    for c in controls(app, w):
        if c.get("title") == title:
            return c
    return None


def after_label(app, w, label, offset=1):
    """The control that follows a label (a field or popup beside it)."""
    cs = controls(app, w)
    for i, c in enumerate(cs):
        if c.get("value") == label and c.get("editable") is False:
            return cs[i + offset]
    raise AssertionError(f"no label {label!r}")


def text_views(app, w):
    return [c for c in controls(app, w) if c["class"] == "NSTextView"]


def input_view(app, w):
    return [c for c in text_views(app, w) if c.get("editable")][0]


def output_views(app, w):
    return [c for c in text_views(app, w) if not c.get("editable")]


def set_input(app, w, text, index=0):
    view = [c for c in text_views(app, w) if c.get("editable")][index]
    app.act(w, "set_text", text, path=view["path"])


def result(app, w, index=0):
    outs = output_views(app, w)
    return outs[index]["value"] if len(outs) > index else None


def set_field(app, w, label, value):
    c = after_label(app, w, label)
    if c["class"] == "NSPopUpButton":
        app.act(w, "select", value, path=c["path"])
    else:
        app.act(w, "set_value", value, path=c["path"])


def field(app, w, label):
    return after_label(app, w, label).get("value")


def state(app, w, title):
    c = by_title(app, w, title)
    return None if c is None else c.get("state")


def set_state(app, w, title, on):
    c = by_title(app, w, title)
    assert c is not None, title
    if bool(c.get("state")) != bool(on):
        app.act(w, "set_state", 1 if on else 0, path=c["path"])


def click(app, w, title):
    return app.act(w, "click", title=title)


def static_texts(app, w):
    return [c.get("value") for c in controls(app, w) if c["class"] == "NSTextField" and c.get("editable") is False]


# ---- digest window ----------------------------------------------------------

def digest_window(app, name, files=False):
    cmd = f"Tools|Hashes|{name}|" + ("Generate from files…" if files else "Generate…")
    title = f"Generate {name} digest" + (" from files" if files else "")
    return open_tool(app, cmd, title)


def digest_of(app, w, text, each_line=False, key=None):
    set_state(app, w, "Treat each line as a separate string", each_line)
    if key is not None:
        set_field(app, w, "HMAC key (optional):", key)
    set_input(app, w, text)
    app.idle(0.05)
    return result(app, w)


# ---- password-hash window ---------------------------------------------------

def hash_window(app, kind, files=False):
    cmd = f"Tools|Hashes|{kind}|" + ("Generate from files…" if files else "Generate…")
    title = f"Generate {kind} digest" + (" from files" if files else "")
    return open_tool(app, cmd, title)


def problem_line(app, w):
    """The password-hash window's problem line: the label right after the bare-key row."""
    cs = controls(app, w)
    for i, c in enumerate(cs):
        if c.get("title") == "Show the bare key in hexadecimal":
            for d in cs[i + 1:]:
                if d["class"] == "NSTextField" and d.get("editable") is False:
                    return d.get("value")
    return None


def verdict_line(app, w):
    cs = controls(app, w)
    for i, c in enumerate(cs):
        if c.get("title") == "Verify":
            nxt = cs[i + 1]
            if nxt["class"] == "NSTextField":
                return nxt.get("value")
    return None


def wait_result(app, w, timeout=30, previous=None):
    """Waits for the (asynchronous) password-hash result or a problem line."""
    def done():
        r = result(app, w) or ""
        p = problem_line(app, w) or ""
        if r and r != previous:
            return ("result", r)
        if p and not r:
            return ("problem", p)
        return None
    return app.wait(done, timeout, "password hash")


def wait_result_value(app, w, timeout=30):
    kind, value = wait_result(app, w, timeout)
    assert kind == "result", value
    return value


def verify(app, w, hash_text, timeout=30):
    """Types the hash to check, clicks Verify, and waits for the button to come back (it is off while checking)."""
    c = after_label(app, w, "Hash to check the password against:")
    app.act(w, "set_value", hash_text, path=c["path"])
    click(app, w, "Verify")
    app.wait(lambda: by_title(app, w, "Verify").get("enabled", True) is not False, timeout, "verify done")
    return verdict_line(app, w)


# ---- the HTTP test server ----------------------------------------------------

class HttpServer:
    def __init__(self):
        self.proc = subprocess.Popen([sys.executable, str(SERVER)], stdout=subprocess.PIPE, text=True)
        line = self.proc.stdout.readline()
        self.port = int(line.split()[1])
        self.base = f"http://127.0.0.1:{self.port}"

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


@pytest.fixture
def http_server():
    s = HttpServer()
    yield s
    s.stop()


def http_window(app):
    return open_tool(app, "Tools|HTTP Request", "HTTP Request")


def http_section(app, w, name):
    seg = [c for c in controls(app, w) if c["class"] == "NSSegmentedControl" and "Parameters" in (c.get("items") or [])][0]
    app.act(w, "select", name, path=seg["path"])


def http_answer_view(app, w, name):
    seg = [c for c in controls(app, w) if c["class"] == "NSSegmentedControl" and c.get("items") == ["Body", "Headers"]][0]
    app.act(w, "select", name, path=seg["path"])


def http_set(app, w, method=None, address=None, params=None, headers=None, body=None, content_type=None,
             user=None, password=None, timeout=None, follow=None, insecure=None, fmt=None):
    cs = controls(app, w)
    if method is not None:
        pop = [c for c in cs if c["class"] == "NSPopUpButton" and "OPTIONS" in (c.get("items") or [])][0]
        app.act(w, "select", method, path=pop["path"])
    if address is not None:
        f = [c for c in cs if c.get("placeholder") == "https://example.com/path"][0]
        app.act(w, "set_value", address, path=f["path"])
    for section, text in (("Parameters", params), ("Headers", headers), ("Body", body)):
        if text is not None:
            http_section(app, w, section)
            set_input(app, w, text)
    if content_type is not None:
        http_section(app, w, "Body")
        set_field(app, w, "Content type:", content_type)
    if any(v is not None for v in (user, password, timeout, follow, insecure)):
        http_section(app, w, "Options")
        if user is not None:
            set_field(app, w, "User name:", user)
        if password is not None:
            set_field(app, w, "Password:", password)
        if timeout is not None:
            set_field(app, w, "Timeout (seconds):", str(timeout))
        if follow is not None:
            set_state(app, w, "Follow redirects", follow)
        if insecure is not None:
            set_state(app, w, "Allow invalid certificates", insecure)
    if fmt is not None:
        set_state(app, w, "Format JSON", fmt)
    http_section(app, w, "Parameters")


def http_status(app, w):
    cs = controls(app, w)
    for i, c in enumerate(cs):
        if c["class"] == "NSSegmentedControl" and c.get("items") == ["Body", "Headers"]:
            prev = cs[i - 1]
            return prev.get("value") if prev["class"] == "NSTextField" else None
    return None


def http_answer(app, w):
    outs = output_views(app, w)
    return outs[-1]["value"] if outs else None


def http_send(app, w, timeout=15):
    """Clicks Send and waits for this request's answer. The window counts its requests
    (`generation`) and says when one is in flight (`sending`): read only to know that
    the answer on screen is the new one, not the previous request's."""
    before = app.get("class:NppHttpWindow", "generation")
    click(app, w, "Send")
    app.wait(lambda: app.get("class:NppHttpWindow", "generation") > before
             and not app.get("class:NppHttpWindow", "sending"), timeout, "HTTP answer")
    return app.wait(lambda: http_status(app, w) or None, 5, "status line")


def http_json(app, w):
    return json.loads(http_answer(app, w))
