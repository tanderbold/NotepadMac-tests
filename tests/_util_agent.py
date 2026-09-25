"""Helpers for the AGENT tests: raw protocol connections, error texts, the stdio bridge."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import tempfile
import time

from harness.app import ToolError


class Raw:
    """A bare connection to the agent socket: bytes in, lines out."""

    def __init__(self, path: str, timeout: float = 10.0):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect(path)
        self.buf = b""

    def send(self, data):
        if isinstance(data, str):
            data = data.encode()
        self.sock.sendall(data)

    def send_json(self, obj):
        self.send(json.dumps(obj) + "\n")

    def line(self, timeout: float = 10.0):
        """The next line as parsed JSON, or None when none comes in time."""
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buf:
            left = deadline - time.monotonic()
            if left <= 0:
                return None
            self.sock.settimeout(left)
            try:
                chunk = self.sock.recv(1 << 20)
            except socket.timeout:
                return None
            if not chunk:
                return None
            self.buf += chunk
        raw, self.buf = self.buf.split(b"\n", 1)
        return json.loads(raw)

    def raw_line(self, timeout: float = 10.0) -> bytes | None:
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buf:
            left = deadline - time.monotonic()
            if left <= 0:
                return None
            self.sock.settimeout(left)
            try:
                chunk = self.sock.recv(1 << 20)
            except socket.timeout:
                return None
            if not chunk:
                return None
            self.buf += chunk
        raw, self.buf = self.buf.split(b"\n", 1)
        return raw

    def lines_for(self, seconds: float) -> list:
        """Every line that arrives within the given time."""
        out = []
        deadline = time.monotonic() + seconds
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                break
            got = self.line(left)
            if got is None:
                break
            out.append(got)
        return out

    def request(self, ident, method, params=None, timeout=10.0):
        msg = {"jsonrpc": "2.0", "id": ident, "method": method}
        if params is not None:
            msg["params"] = params
        self.send_json(msg)
        return self.line(timeout)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def raw(app, timeout: float = 10.0) -> Raw:
    return Raw(app.socket_path, timeout)


def err(app, name, **args) -> str:
    """The error text of a tool call that must fail."""
    try:
        r = app.call(name, **args)
    except ToolError as e:
        return str(e)
    raise AssertionError(f"{name}({args}) did not fail: {str(r)[:300]}")


def call_raw(app, name, **args) -> dict:
    """tools/call without unwrapping: the result object as sent."""
    return app.conn.request("tools/call", {"name": name, "arguments": args})


def short_dir() -> str:
    """A folder with a short path (sockets have 104 bytes)."""
    return os.path.realpath(tempfile.mkdtemp(prefix="npa", dir=tempfile.gettempdir()))


INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "t", "version": "1"}}}


def bridge(app, socket_path=None) -> subprocess.Popen:
    env = dict(os.environ, NPPMAC_AGENT_SOCKET=socket_path or app.socket_path)
    return subprocess.Popen([str(app.cli), "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=env)


def read_json_line(stream, timeout: float = 10.0):
    """One line from a pipe with a timeout (os.read on the fd)."""
    import select
    data = b""
    deadline = time.monotonic() + timeout
    fd = stream.fileno()
    while b"\n" not in data:
        left = deadline - time.monotonic()
        if left <= 0:
            return None
        r, _, _ = select.select([fd], [], [], left)
        if not r:
            return None
        chunk = os.read(fd, 1)
        if not chunk:
            return None
        data += chunk
    return json.loads(data)


def product_tools(app) -> list[dict]:
    return [t for t in app.tools() if not t["name"].startswith("e2e_")]


def restart_default(app):
    """Back to the session's usual launch (agent flag on, fresh home)."""
    try:
        app.stop()
    except Exception:  # noqa: BLE001
        pass
    app.start()
