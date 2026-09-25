"""Launching an isolated copy of NotepadMac and talking to it.

The copy lives in .work/<worker>/NotepadMacE2E.app under its own bundle id, so
its preferences are a domain of its own (the user's org.notepad-plus-plus.mac is
never read or written); CFFIXED_USER_HOME moves its Application Support folder
(session, plugins, user languages, macros, the agent socket's default place)
into a scratch home; NPPMAC_E2E=1 turns on the e2e_* tools and the queued answers
for alerts and file panels; the clipboard is private to the process.
"""
from __future__ import annotations

import json
import os
import plistlib
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUILD = ROOT.parent / "npp" / "macos" / "build" / "NotepadMac.app"
BASE_BUNDLE_ID = "org.notepad-plus-plus.mac.e2e"


class ToolError(Exception):
    """A tool answered with isError, or the protocol answered with an error."""


def wait_for(condition, timeout=10.0, interval=0.05, message="condition"):
    """Polls until condition() is truthy; returns its value."""
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = condition()
        if last:
            return last
        time.sleep(interval)
    raise TimeoutError(f"timed out after {timeout}s waiting for {message} (last: {last!r})")


class Connection:
    """One JSON-RPC connection to the agent socket."""

    def __init__(self, path: str, timeout: float = 60.0):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect(path)
        self.file = self.sock.makefile("rwb")
        self.next_id = 1
        self.lock = threading.Lock()

    def request(self, method: str, params: dict | None = None) -> dict:
        with self.lock:
            ident = self.next_id
            self.next_id += 1
            line = json.dumps({"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}})
            self.file.write(line.encode() + b"\n")
            self.file.flush()
            # Answers carry their request's id. One whose request timed out earlier (a tool
            # that froze the app for a while) may still arrive first: it is not this one's,
            # and taking it would hand every later call the answer before it.
            while True:
                raw = self.file.readline()
                if not raw:
                    break
                reply = json.loads(raw)
                if reply.get("id") in (ident, None):
                    break
        if not raw:
            raise ConnectionError("the application closed the connection")
        if "error" in reply:
            raise ToolError(reply["error"].get("message", str(reply["error"])))
        return reply["result"]

    def notify(self, method: str, params: dict | None = None):
        with self.lock:
            self.file.write(json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}}).encode() + b"\n")
            self.file.flush()

    def close(self):
        try:
            self.file.close()
            self.sock.close()
        except OSError:
            pass


class Pending:
    """A tool call running on its own connection (it may be held up by a modal)."""

    def __init__(self, app: "App", name: str, args: dict):
        self.result = None
        self.error = None
        self.conn = app.connect()
        self.thread = threading.Thread(target=self._run, args=(name, args), daemon=True)
        self.thread.start()

    def _run(self, name, args):
        try:
            self.result = App._unwrap(self.conn.request("tools/call", {"name": name, "arguments": args}))
        except Exception as e:  # noqa: BLE001 - handed to the waiter
            self.error = e

    @property
    def done(self) -> bool:
        return not self.thread.is_alive()

    def wait(self, timeout: float = 30.0):
        self.thread.join(timeout)
        if self.thread.is_alive():
            raise TimeoutError("the call did not come back")
        self.conn.close()
        if self.error:
            raise self.error
        return self.result


class App:
    """A running, isolated NotepadMac driven over MCP."""

    def __init__(self, worker: str = "main", build: Path | None = None, work: Path | None = None):
        self.worker = worker
        self.build = Path(build or os.environ.get("NPPMAC_E2E_APP") or DEFAULT_BUILD)
        self.work = Path(work or ROOT / ".work" / worker)
        self.bundle_id = f"{BASE_BUNDLE_ID}.{worker}"
        self.bundle = self.work / "NotepadMacE2E.app"
        self.home = self.work / "home"
        # A socket path has 104 bytes; the temporary folder is short enough.
        self.socket_path = os.path.join(tempfile.gettempdir(), f"npe2e-{worker}.sock")
        self.proc: subprocess.Popen | None = None
        self.conn: Connection | None = None
        self.log_path = self.work / "app.log"
        self.extra_args: list[str] = []
        self.print_dir = self.work / "print"

    # ---- the copy -------------------------------------------------------

    def prepare(self):
        """Copies the build under the test bundle id when the build is newer."""
        if not self.build.exists():
            raise FileNotFoundError(f"no build at {self.build}; run macos/build.sh in the npp clone")
        self.work.mkdir(parents=True, exist_ok=True)
        stamp = self.work / ".copied-from"
        src_time = str(max(p.stat().st_mtime for p in [self.build / "Contents/MacOS/NotepadMac",
                                                        self.build / "Contents/Info.plist"]))
        if self.bundle.exists() and stamp.exists() and stamp.read_text() == src_time:
            return
        if self.bundle.exists():
            shutil.rmtree(self.bundle)
        subprocess.run(["ditto", str(self.build), str(self.bundle)], check=True)
        info_path = self.bundle / "Contents/Info.plist"
        with open(info_path, "rb") as f:
            info = plistlib.load(f)
        info["CFBundleIdentifier"] = self.bundle_id
        info["CFBundleName"] = "NotepadMacE2E"
        with open(info_path, "wb") as f:
            plistlib.dump(info, f)
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(self.bundle)],
                       check=True, capture_output=True)
        stamp.write_text(src_time)

    @property
    def executable(self) -> Path:
        return self.bundle / "Contents/MacOS/NotepadMac"

    @property
    def cli(self) -> Path:
        return self.bundle / "Contents/Helpers/nppmac"

    # ---- preferences (the test domain only) ------------------------------

    def reset_defaults(self, initial: dict | None = None):
        """Empties the test bundle's preference domain, then writes initial values."""
        subprocess.run(["defaults", "delete", self.bundle_id], capture_output=True)
        values = {"autoUpdateMode": 0}
        values.update(initial or {})
        for key, value in values.items():
            self.write_default(key, value)

    def write_default(self, key: str, value):
        full = f"NppMac.{key}"
        if isinstance(value, bool):
            args = ["-bool", "YES" if value else "NO"]
        elif isinstance(value, int):
            args = ["-int", str(value)]
        elif isinstance(value, float):
            args = ["-float", str(value)]
        elif isinstance(value, str):
            args = ["-string", value]
        else:
            raise TypeError(f"cannot write {type(value)} with defaults")
        subprocess.run(["defaults", "write", self.bundle_id, full, *args], check=True)

    def read_default(self, key: str):
        r = subprocess.run(["defaults", "read", self.bundle_id, f"NppMac.{key}"], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else None

    # ---- life ------------------------------------------------------------

    def start(self, args: list[str] | None = None, env: dict | None = None, clean_home: bool = True,
              defaults: dict | None = None, reset: bool = True, session: bool = False, timeout: float = 30.0,
              agent_flag: bool = True, wait_socket: bool = True):
        """Starts the copy. agent_flag=False leaves out -NppMac.agentServer YES (the
        preference domain then decides); wait_socket=False does not wait for the
        socket nor connect (for launches whose agent interface is off)."""
        self.prepare()
        if self.running:
            self.stop()
        if clean_home and self.home.exists():
            shutil.rmtree(self.home)
        (self.home / "Library/Application Support/NotepadMac").mkdir(parents=True, exist_ok=True)
        if reset:
            self.reset_defaults(defaults)
        elif defaults:
            for k, v in defaults.items():
                self.write_default(k, v)
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
        full_env = dict(os.environ)
        full_env.update({"CFFIXED_USER_HOME": str(self.home), "NPPMAC_AGENT_SOCKET": self.socket_path,
                         "NPPMAC_E2E": "1", "NPPMAC_E2E_CLI_DIR": str(self.work / "bin"),
                         "NPPMAC_E2E_PRINT_DIR": str(self.print_dir)})
        (self.work / "bin").mkdir(exist_ok=True)
        self.print_dir.mkdir(exist_ok=True)
        for k in ("NPPMAC_TEST", "NPPMAC_SNAPSHOT", "NPPMAC_SELFTEST"):
            full_env.pop(k, None)
        full_env.update(env or {})
        argv = [str(self.executable)] + (["-NppMac.agentServer", "YES"] if agent_flag else [])
        if not session:
            argv.append("-nosession")
        argv += self.extra_args + (args or [])
        self.log = open(self.log_path, "ab")
        self.proc = subprocess.Popen(argv, env=full_env, stdout=self.log, stderr=subprocess.STDOUT,
                                     start_new_session=True)
        if not wait_socket:
            return self
        wait_for(lambda: os.path.exists(self.socket_path) or self.proc.poll() is not None, timeout,
                 message="the agent socket")
        if self.proc.poll() is not None:
            raise RuntimeError(f"the application exited with {self.proc.returncode}; see {self.log_path}")
        self.conn = self.connect()
        self.conn.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                         "clientInfo": {"name": "npp-tests", "version": "1"}})
        self.conn.notify("notifications/initialized")
        if os.environ.get("NPPMAC_E2E_ACTIVATE"):
            # In the VM (tools/vm.sh sets it) the app comes to the front as a launch from the
            # Finder does; started with exec it stays behind whatever had the focus. Never set on
            # a Mac someone is working at: it would take their focus.
            self.invoke("nsapp", "activateIgnoringOtherApps:", [True])
            try:
                wait_for(lambda: self.get("nsapp", "active"), 30, message="the app active")
            except TimeoutError:
                # A launch still opening hundreds of files, or asking about them, may not be in front
                # yet; a test that needs the focus finds out from its own checks.
                pass
        return self

    def connect(self) -> Connection:
        return Connection(self.socket_path)

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def stop(self, timeout: float = 10.0, graceful: bool = True):
        """Quits: terminate: through the app (so it saves what it saves on quit), then signals."""
        if not self.proc:
            return
        if self.running and graceful and self.conn:
            try:
                self.answers(alerts=[2, 2, 2], clear=True)   # "don't save" style answers if it asks
                # NSApp's terminate: runs applicationShouldTerminate: and
                # applicationWillTerminate: (session.xml, backups), as Quit does.
                self.invoke("nsapp", "terminate:", [None], timeout=3)
            except Exception:  # noqa: BLE001 - it may be gone already
                pass
        try:
            self.proc.wait(timeout)
        except subprocess.TimeoutExpired:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        if self.conn:
            self.conn.close()
        self.conn = None
        self.proc = None
        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

    def restart(self, **kwargs):
        """Quits and starts again, keeping home and preferences unless told otherwise."""
        self.stop()
        kwargs.setdefault("clean_home", False)
        kwargs.setdefault("reset", False)
        return self.start(**kwargs)

    # ---- calls -------------------------------------------------------------

    @staticmethod
    def _unwrap(result: dict):
        if result.get("isError"):
            text = " ".join(c.get("text", "") for c in result.get("content", []))
            raise ToolError(text)
        if "structuredContent" in result:
            return result["structuredContent"]
        texts = [c.get("text", "") for c in result.get("content", [])]
        return {"text": "\n".join(texts)}

    def call(self, name: str, timeout: float | None = None, **args):
        if not self.conn:
            raise RuntimeError("the application is not running")
        if timeout is not None:
            p = Pending(self, name, args)
            return p.wait(timeout)
        try:
            return self._unwrap(self.conn.request("tools/call", {"name": name, "arguments": args}))
        except (TimeoutError, OSError) as e:
            # A socket file that timed out is broken for good ("cannot read from timed out
            # object"): every later call would fail the same way. Connect afresh, so one frozen
            # call fails one test, not the rest of the run; the late answer goes with the old one.
            if self.running and not isinstance(e, ConnectionError):
                try:
                    self.conn.close()
                except Exception:  # noqa: BLE001
                    pass
                self.conn = self.connect()
                self.conn.request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                                 "clientInfo": {"name": "npp-tests", "version": "1"}})
                self.conn.notify("notifications/initialized")
            raise

    def call_async(self, name: str, **args) -> Pending:
        """For a call that opens a modal: it comes back when the modal ends."""
        return Pending(self, name, args)

    def tools(self) -> list[dict]:
        return self.conn.request("tools/list")["tools"]

    # conveniences over the product's own tools
    def new(self, text: str = "", language: str | None = None, title: str | None = None) -> dict:
        args = {"text": text}
        if language:
            args["language"] = language
        if title:
            args["title"] = title
        return self.call("open_document", **args)

    def open(self, path, line: int | None = None) -> dict:
        args = {"path": str(path)}
        if line:
            args["line"] = line
        return self.call("open_document", **args)

    def text(self, document=None) -> str:
        args = {} if document is None else {"document": document}
        return self.call("get_document", **args)["text"]

    def set_text(self, text: str, document=None):
        args = {"text": text}
        if document is not None:
            args["document"] = document
        return self.call("edit_document", **args)

    def doc(self, document=None) -> dict:
        args = {} if document is None else {"document": document}
        d = self.call("get_document", **args)
        d.pop("text", None)
        return d

    def docs(self) -> list[dict]:
        return self.call("list_documents")["documents"]

    def selection(self) -> dict:
        return self.call("get_selection")

    def select(self, line: int, column: int = 1, end_line: int | None = None, end_column: int | None = None, document=None):
        args = {"line": line, "column": column}
        if end_line is not None:
            args["end_line"] = end_line
        if end_column is not None:
            args["end_column"] = end_column
        if document is not None:
            args["document"] = document
        return self.call("go_to", **args)

    def select_all(self):
        return self.sci(2013)  # SCI_SELECTALL

    def run(self, command, expect_ran: bool = True) -> dict:
        r = self.call("run_command", command=command)
        if expect_ran and not r.get("ran"):
            raise AssertionError(f"{command} did not run: {r}")
        return r

    def run_async(self, command) -> Pending:
        return self.call_async("run_command", command=command)

    def close_all(self):
        for d in reversed(self.docs()):
            try:
                self.call("close_document", document=d["index"], discard_changes=True)
            except ToolError:
                pass

    # e2e hooks
    def sci(self, message: int, wparam: int = 0, lparam=0, view: str = "main", returns: str | None = None):
        args = {"message": message, "wparam": wparam, "lparam": lparam, "view": view}
        if returns:
            args["returns"] = returns
            return self.call("e2e_sci", **args)["text"]
        return self.call("e2e_sci", **args)["result"]

    def menu(self, *commands) -> dict:
        return self.call("e2e_menu", commands=list(commands))["items"]

    def menu_item(self, command) -> dict:
        item = self.menu(command)[str(command)]
        if item is None:
            raise AssertionError(f"no menu item {command}")
        return item

    def checked(self, command) -> bool:
        return self.menu_item(command)["checked"]

    def enabled(self, command) -> bool:
        return self.menu_item(command)["enabled"]

    def menu_tree(self, top: str = "main", depth: int = 1):
        return self.call("e2e_menu", tree=top, depth=depth)["tree"]

    def windows(self, all: bool = False) -> list[dict]:
        return self.call("e2e_windows", all=all)["windows"]

    def window(self, spec) -> dict | None:
        for w in self.windows():
            if spec in (w["title"], w["class"], w["number"]):
                return w
        for w in self.windows():
            if isinstance(spec, str) and spec.lower() in w["title"].lower():
                return w
        return None

    def ui(self, window="main", include_hidden: bool = False) -> dict:
        return self.call("e2e_ui", window=window, include_hidden=include_hidden)

    def controls(self, window="main", **match) -> list[dict]:
        out = []
        for c in self.ui(window)["controls"]:
            if all(c.get(k) == v for k, v in match.items()):
                out.append(c)
        return out

    def act(self, window, action: str = "click", value=None, **target):
        args = {"window": window, "action": action, "target": target}
        if value is not None:
            args["value"] = value
        return self.call("e2e_act", **args)

    def click(self, window, title: str | None = None, **target):
        if title is not None:
            target["title"] = title
        return self.act(window, "click", **target)

    def close_window(self, window):
        return self.call("e2e_act", window=window, action="close_window")

    def keys(self, *keys, window=None):
        args = {"keys": list(keys)}
        if window is not None:
            args["window"] = window
        return self.call("e2e_keys", **args)

    def type(self, text: str, window=None):
        args = {"text": text}
        if window is not None:
            args["window"] = window
        return self.call("e2e_keys", **args)

    def snapshot(self, path, window="main") -> dict:
        return self.call("e2e_snapshot", window=window, path=str(path))

    def prefs(self, *names) -> dict:
        return self.call("e2e_prefs", get=list(names))["values"]

    def pref(self, name):
        return self.prefs(name)[name]

    def set_prefs(self, **values):
        return self.call("e2e_prefs", set=values)

    def clipboard(self, set: str | None = None, clear: bool = False) -> str | None:
        """The private clipboard's text; set= puts a string on it (set="" is an empty string,
        which a paste can still take), clear=True leaves nothing on it at all."""
        args = {} if set is None else {"set": set}
        if clear:
            args["clear"] = True
        return self.call("e2e_clipboard", **args)["text"]

    def clipboard_info(self, type: str | None = None, image=None, files=None) -> dict:
        """Types on the clipboard (and one type's data, base64); image= puts an
        image file's picture on it, files= file URLs."""
        args = {}
        if type:
            args["type"] = type
        if image is not None:
            args["image"] = str(image)
        if files is not None:
            args["files"] = [str(f) for f in files]
        return self.call("e2e_clipboard", **args)

    def answers(self, alerts=None, panels=None, real_modals=None, clear=False):
        args = {"clear": clear}
        if alerts is not None:
            args["alerts"] = alerts
        if panels is not None:
            args["panels"] = panels
        if real_modals is not None:
            args["real_modals"] = real_modals
        return self.call("e2e_answers", **args)

    def modal_log(self, clear: bool = True) -> list[dict]:
        return self.call("e2e_log", clear=clear)["entries"]

    def invoke(self, target: str, selector: str, arguments=None, timeout: float | None = None):
        args = {"target": target, "selector": selector, "arguments": arguments or []}
        if timeout is not None:
            return self.call("e2e_invoke", timeout=timeout, **args)["value"]
        return self.call("e2e_invoke", **args)["value"]

    def get(self, target: str, key: str):
        return self.call("e2e_invoke", target=target, key=key)["value"]

    def mouse(self, window=None, view: str | None = None, point=None, clicks: int = 1, modifiers=(),
              button: str = "left", menu_path: str | None = None, drag_to=None, drag_by=None,
              drag_to_screen=None, divider=None, **target):
        """A click on a control (window + target) or an editor (view='main'|'sub', point={'line','column'}).

        drag_to (view coordinates), drag_by [dx, dy] or drag_to_screen (screen coordinates) make it a
        drag from point; divider (an index, or 'before'/'after' the target) starts it on a split
        view's divider."""
        args = {"clicks": clicks, "modifiers": list(modifiers), "button": button}
        for key, value in (("drag_to", drag_to), ("drag_by", drag_by), ("drag_to_screen", drag_to_screen),
                           ("divider", divider)):
            if value is not None:
                args[key] = list(value) if isinstance(value, tuple) else value
        if view:
            args["view"] = view
        else:
            args["window"] = window if window is not None else "main"
            args["target"] = target
        if point is not None:
            args["point"] = point
        if menu_path:
            args["menu_path"] = menu_path
        return self.call("e2e_mouse", **args)

    def counters(self, reset: bool = False) -> dict:
        return self.call("e2e_counters", reset=reset)

    def idle(self, seconds: float = 0.1):
        return self.call("e2e_idle", seconds=seconds)

    @staticmethod
    def same_path(a, b) -> bool:
        """The app reports /var/..., pytest's tmp is /private/var/...: compare resolved."""
        return os.path.realpath(str(a)) == os.path.realpath(str(b))

    def wait(self, condition, timeout: float = 10.0, message: str = "condition"):
        return wait_for(condition, timeout=timeout, message=message)

    # a clean slate between tests, without a restart
    def reset(self):
        self.answers(clear=True, real_modals=False)
        # An auto-completion list or call tip is a window of Scintilla's own: closing it from
        # outside frees it under Scintilla, which then crashes on its next cancel. Cancel them
        # as Escape would first, then close the other windows.
        for view in ("main", "sub"):
            try:
                self.sci(2101, view=view)   # SCI_AUTOCCANCEL
                self.sci(2201, view=view)   # SCI_CALLTIPCANCEL
            except ToolError:
                pass
        # Windows other than the main one: close them.
        for w in self.windows():
            if not w["main_window"] and w["visible"] and not w.get("sheet"):
                try:
                    self.close_window(w["number"])
                except ToolError:
                    pass
        # The Search results tab is not in list_documents, so close_all does not see it, and while it
        # is open the agent's indexes and the editor's differ by one (AGENT-029): close it by its place
        # in the editor's own list first.
        try:
            flags = self.get("editor", "documents.isSearchResults") or []
            for i in reversed([i for i, f in enumerate(flags) if f]):
                self.invoke("editor", "closeDocumentAtIndex:discardChanges:", [i, True])
        except ToolError:
            pass
        self.close_all()
        if os.environ.get("NPPMAC_E2E_ACTIVATE") and not self.get("nsapp", "active"):
            # A test may leave the app behind (a window of another program, a hidden app): each test
            # starts with it in front, as for someone working in it. VM only, as at start.
            self.invoke("nsapp", "activateIgnoringOtherApps:", [True])
            wait_for(lambda: self.get("nsapp", "active"), 10, message="the app active")
        self.modal_log(clear=True)
        self.clipboard(clear=True)   # nothing on it: not even an empty string
