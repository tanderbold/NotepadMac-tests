"""Helpers for the FTP tests: the repository's test server, profiles made through
the Connections… prompts, the Remote Files panel, and Keychain clean-up."""
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parent.parent.parent / "npp" / "macos" / "test-ftp-server.py"
HOST = "127.0.0.1"
USER = "tester"
PASSWORD = "secret"

CONNECTIONS = "Plugins|FTP|Connections…"
CONNECT = "Plugins|FTP|Connect…"
DISCONNECT = "Plugins|FTP|Disconnect"
BROWSE = "Plugins|FTP|Show Remote Files"
UPLOAD = "Plugins|FTP|Upload Current File"

PROMPTS = ["Connection name", "Host", "Protocol: ftp, ftps or sftp", "Port (0 for the default)",
           "User name", "Initial directory", "Password (stored in the Keychain; leave empty for an SSH key)"]


def free_port() -> int:
    s = socket.socket()
    s.bind((HOST, 0))
    port = s.getsockname()[1]
    s.close()
    return port


def delete_keychain_items(users=(USER, "nobody", "bob")):
    """Removes every internet password the tests could have stored (test hosts only)."""
    for host in (HOST, "127.0.0.2"):
        for user in users:
            for _ in range(30):
                r = subprocess.run(["security", "delete-internet-password", "-s", host, "-a", user],
                                   capture_output=True)
                if r.returncode != 0:
                    break


def keychain_has(user=USER, host=HOST, port=None) -> bool:
    args = ["security", "find-internet-password", "-s", host, "-a", user]
    if port:
        args += ["-P", str(port)]
    return subprocess.run(args, capture_output=True).returncode == 0


class Ftp:
    def __init__(self, app, root: Path):
        self.app = app
        self.root = root
        self.proc = None
        self.port = None

    # ---- the server ---------------------------------------------------------
    def start(self):
        self.proc = subprocess.Popen([sys.executable, str(SERVER), str(self.root)],
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        line = self.proc.stdout.readline()
        assert line.startswith("PORT "), line
        self.port = int(line.split()[1])
        return self

    def kill(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()

    def write(self, rel: str, data, binary=False):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            p.write_bytes(data)
        else:
            p.write_text(data)
        return p

    def read(self, rel: str) -> bytes:
        return (self.root / rel).read_bytes()

    # ---- the app ------------------------------------------------------------
    def run(self, path):
        return self.app.run(path)

    def add(self, name="local", host=HOST, protocol="ftp", port=None, user=USER, directory="/",
            password=PASSWORD):
        answers = [1] + [{"button": 1, "field": str(v)} for v in
                         (name, host, protocol, self.port if port is None else port, user, directory, password)]
        self.app.answers(alerts=answers)
        self.run(CONNECTIONS)
        return self.app.modal_log()

    def connect(self, name="local", timeout=None):
        self.app.answers(alerts=[{"button": 1, "field": name}])
        if timeout:
            self.app.call("run_command", timeout=timeout, command=CONNECT)
        else:
            self.run(CONNECT)
        return self.app.modal_log()

    def panel(self):
        for w in self.app.windows():
            if w["title"].startswith("Remote Files") and w["visible"]:
                return w
        return None

    def table(self):
        w = self.panel()
        assert w, "no Remote Files window"
        t = [c for c in self.app.ui(w["number"])["controls"] if c["class"] == "NSTableView"][0]
        return w, t

    def cells(self):
        return self.table()[1]["cells"]

    def title(self):
        w = self.panel()
        return w["title"] if w else None

    def row_of(self, text_prefix: str) -> int:
        for i, c in enumerate(self.cells()):
            if c[0].startswith(text_prefix):
                return i
        raise AssertionError(f"no row {text_prefix!r} in {self.cells()}")

    def activate(self, row):
        """Double-clicks a row of the Remote Files table (AppDelegate ftpRowActivated:):
        ".." and folders change directory and list again, files are downloaded and opened.
        Returns True when the row was a folder or its file opened as the current tab."""
        w, t = self.table()
        name = t["cells"][row][0]
        before = self.app.doc()
        self.app.act(w["number"], "double_click", row, path=t["path"])
        if row == 0 or name.endswith("/"):
            return True
        d = self.app.doc()
        return d["title"] == name.split("   ")[0] and d != before

    def activate_name(self, prefix):
        return self.activate(self.row_of(prefix))

    def cache(self, rel="") -> Path:
        return self.app.home / "Library/Application Support/NotepadMac/ftp-cache" / HOST / rel

    def upload(self, answer=1):
        self.app.answers(alerts=[answer])
        self.run(UPLOAD)
        return self.app.modal_log()

    def cleanup(self):
        try:
            if self.app.running:
                self.app.answers(clear=True)
                self.run(DISCONNECT)
                self.app.set_prefs(ftpProfiles=[])
                self.app.modal_log()
        except Exception:  # noqa: BLE001 - best effort
            pass
        self.kill()
        delete_keychain_items()
        shutil.rmtree(self.app.home / "Library/Application Support/NotepadMac/ftp-cache", ignore_errors=True)


@pytest.fixture
def ftp(app, tmp):
    delete_keychain_items()
    root = tmp / "ftproot"
    root.mkdir()
    f = Ftp(app, root)
    app.answers(clear=True)
    app.run(DISCONNECT)
    app.set_prefs(ftpProfiles=[])
    shutil.rmtree(app.home / "Library/Application Support/NotepadMac/ftp-cache", ignore_errors=True)
    app.modal_log()
    f.start()
    yield f
    f.cleanup()


def standard_tree(f: Ftp):
    f.write("greeting.txt", "remote hello\n")
    f.write("sub/inner.txt", "inner\n")


def remote_windows(app):
    return [w for w in app.windows() if w["title"].startswith("Remote Files") and w["visible"]]


def alerts(log, message=None):
    return [e for e in log if message is None or e.get("message") == message]


def realpath(p):
    return os.path.realpath(str(p))
