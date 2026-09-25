"""Helpers shared by the VIEW, UI and L10N tests."""
from __future__ import annotations

import contextlib
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from harness.app import ToolError
from harness.sci import *  # noqa: F401,F403

ROOT = Path(__file__).resolve().parent.parent
NPP = ROOT.parent / "npp"
NATIVE = NPP / "PowerEditor" / "installer" / "nativeLang"
EXTRA = NPP / "macos" / "resources" / "nativeLang-extra"
COMMANDS = [l.split("\t") for l in (ROOT / "plan" / "commands.tsv").read_text().splitlines()[1:]]
VIEW_COMMANDS = [c[1] for c in COMMANDS if c[0] == "View"]
DOCK = "class:NppDockingManager"
FULLSCREEN_BIT = 1 << 14


# ---- the main window's chrome, read where a user reads it ------------------

def status(app) -> str:
    """The status bar's text (the field right of the path)."""
    return app.get("editor", "statusField.stringValue")


def path_field(app) -> tuple[str, str | None]:
    return app.get("editor", "pathField.stringValue"), app.get("editor", "pathField.toolTip")


def tab_titles(app) -> list[str]:
    return app.get("editor", "tabBar.items.title")


def tab_attr(app, attr: str) -> list:
    return app.get("editor", f"tabBar.items.{attr}")


def parse_rect(s: str) -> tuple[float, float, float, float]:
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", s)]
    return nums[0], nums[1], nums[2], nums[3]


def tab_frames(app) -> list[tuple]:
    return [parse_rect(s) for s in app.get("editor", "tabBar.tabFrames")]


def click_tab(app, index: int, clicks: int = 1, button: str = "left", at: str = "middle", **kw):
    x, y, w, h = tab_frames(app)[index]
    if at == "close":           # TabBarView's close rect: 12 px, 6 px from the right edge
        point = [x + w - 12, y + h / 2]
    elif at == "left":
        point = [x + 10, y + h / 2]
    else:
        point = [x + w / 2, y + h / 2]
    return app.mouse(**{"class": "NppTabBarView"}, point=point, clicks=clicks, button=button, **kw)


def current(app) -> dict:
    return next(d for d in app.docs() if d["current"])


def current_title(app) -> str:
    return current(app)["title"]


def main_window(app) -> dict:
    return next(w for w in app.windows() if w["main_window"])


def level(app) -> int:
    return main_window(app)["level"]


def view_frame(app, key="sciView.frame"):
    return parse_rect(app.get("editor", key))


def toolbar_items(app) -> list[dict]:
    ids = app.get("window", "toolbar.items.itemIdentifier")
    labels = app.get("window", "toolbar.items.label")
    enabled = app.get("window", "toolbar.items.enabled")
    return [{"id": i, "label": l, "enabled": e} for i, l, e in zip(ids, labels, enabled)]


def toolbar_press(app, label: str):
    return app.act("main", "toolbar", value=label)


def dock(app, selector: str, *args):
    return app.invoke(DOCK, selector, list(args))


def ui(app, window="main", timeout: float = 15.0) -> dict:
    """e2e_ui with a guard: a window whose description never comes back skips the test."""
    try:
        return app.call("e2e_ui", window=window, timeout=timeout)
    except TimeoutError:
        pytest.skip(f"needs hook: e2e_ui does not answer for window {window!r}")


def controls(app, window="main", **match) -> list[dict]:
    return [c for c in ui(app, window)["controls"] if all(c.get(k) == v for k, v in match.items())]


def other_windows(app) -> list[dict]:
    return [w for w in app.windows() if not w["main_window"] and w["visible"]]


def window_titled(app, text: str):
    for w in app.windows():
        if w["visible"] and text.lower() in (w["title"] or "").lower():
            return w
    return None


# ---- documents -------------------------------------------------------------

def write(folder: Path, name: str, text: str | bytes) -> Path:
    p = Path(folder) / name
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_bytes(text.encode("utf-8"))
    return p


def only(app, *paths):
    """Opens the files and closes the leftover empty `new 1`."""
    for p in paths:
        app.open(p)
    for d in app.docs():
        if d["title"] == "new 1" and not d["path"] and d["bytes"] == 0 and len(app.docs()) > 1:
            app.call("close_document", document=d["index"], discard_changes=True)
            break
    return app.docs()


def fresh_doc(app, text="", language=None):
    """A new document in front, the leftover `new 1` closed."""
    app.new(text, language=language)
    docs = app.docs()
    if len(docs) > 1 and docs[0]["title"] == "new 1" and docs[0]["bytes"] == 0:
        app.call("close_document", document=0, discard_changes=True)
    return current(app)


def nested_cpp(depth: int = 8) -> str:
    lines = []
    for i in range(depth):
        lines.append("  " * i + f"if (a{i}) {{")
    lines.append("  " * depth + "x();")
    for i in reversed(range(depth)):
        lines.append("  " * i + "}")
    return "\n".join(lines) + "\n"


CPP2 = "int f() {\n  if (x) {\n    y();\n  }\n}\nint g() {\n  z();\n}\n"


def headers(app, view="main") -> list[int]:
    app.sci(SCI_COLOURISE, 0, -1, view=view)
    n = app.sci(SCI_GETLINECOUNT, view=view)
    return [ln for ln in range(n) if app.sci(SCI_GETFOLDLEVEL, ln, view=view) & SC_FOLDLEVELHEADERFLAG]


def depth(app, line, view="main") -> int:
    return (app.sci(SCI_GETFOLDLEVEL, line, view=view) & SC_FOLDLEVELNUMBERMASK) - SC_FOLDLEVELBASE


def visible(app, line, view="main") -> bool:
    return bool(app.sci(SCI_GETLINEVISIBLE, line, view=view))


def expanded(app, line, view="main") -> bool:
    return bool(app.sci(SCI_GETFOLDEXPANDED, line, view=view))


def representation(app, ch: str, view="main") -> str:
    """SCI_GETREPRESENTATION of a character (the character goes in wParam, as a C string)."""
    return app.sci(SCI_GETREPRESENTATION, ch, view=view, returns="string")


def summary(app) -> dict:
    app.modal_log(clear=True)
    app.answers(alerts=[1])
    app.run("IDM_VIEW_SUMMARY")
    log = [e for e in app.modal_log() if e.get("kind") == "alert"]
    assert log, "no Summary alert"
    e = log[-1]
    values = {}
    for line in (e.get("informative") or "").splitlines():
        if ":" in line:
            k, v = line.rsplit(":", 1)
            values[k.strip()] = v.strip()
    # Upstream's last line: "N selected characters (M bytes) in K ranges".
    m = re.search(r"^(\d+) selected characters \((\d+) bytes\) in (\d+) ranges?$", e.get("informative") or "", re.M)
    if m:
        values["Selected characters"], values["Selected bytes"], values["Ranges"] = m.groups()
    values["_title"] = e.get("message")
    values["_text"] = e.get("informative")
    return values


# ---- preferences ------------------------------------------------------------

@contextlib.contextmanager
def prefs(app, **values):
    before = app.prefs(*values)
    app.set_prefs(**values)
    try:
        yield
    finally:
        app.set_prefs(**{k: before.get(k) for k in values})


# ---- pictures ----------------------------------------------------------------

def snap(app, path, window="main", frame=False):
    args = {"window": window, "path": str(path)}
    if frame:
        args["frame"] = True
    app.call("e2e_snapshot", **args)
    from PIL import Image
    return Image.open(path).convert("RGB")


def luminance(rgb) -> float:
    r, g, b = rgb
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def region_median_luminance(img, box) -> float:
    crop = img.crop(tuple(int(v) for v in box))
    vals = sorted(luminance(p) for p in crop.get_flattened_data())
    return vals[len(vals) // 2] if vals else 0


def distinct_colours(img, box) -> int:
    return len(set(img.crop(tuple(int(v) for v in box)).get_flattened_data()))


# ---- menus -------------------------------------------------------------------

def flat(tree, prefix=()):
    for item in tree:
        if item.get("separator"):
            continue
        yield prefix + (item.get("title"),), item
        if "items" in item:
            yield from flat(item["items"], prefix + (item.get("title"),))


def titles(tree) -> list:
    return [None if i.get("separator") else i.get("title") for i in tree]


# ---- translations -----------------------------------------------------------

def strip_keys(s: str) -> str:
    s = re.sub(r"&(?!&)", "", s or "")
    s = s.replace("...", "…").split("\t")[0]
    return " ".join(s.split())


def native_commands(fname: str) -> dict[int, str]:
    root = ET.parse(NATIVE / fname).getroot()
    out = {}
    for item in root.iter("Item"):
        if item.get("id") and item.get("name") is not None:
            parent = item
            out.setdefault(int(item.get("id")), item.get("name"))
    main = root.find("Native-Langue/Menu/Main/Commands")
    if main is not None:
        out = {int(i.get("id")): i.get("name") for i in main.findall("Item") if i.get("id")}
    return out


def native_submenus(fname: str) -> dict[str, str]:
    sub = _main_menu(fname, "SubEntries")
    return {i.get("subMenuId"): i.get("name") for i in (sub if sub is not None else []) if i.get("subMenuId")}


def _main_menu(fname: str, part: str):
    """<NotepadPlus><Native-Langue><Menu><Main><part>, as the nativeLang files have it."""
    root = ET.parse(NATIVE / fname).getroot()
    return root.find(f"Native-Langue/Menu/Main/{part}")


def native_menus(fname: str) -> dict[str, str]:
    ent = _main_menu(fname, "Entries")
    return {i.get("menuId"): i.get("name") for i in (ent if ent is not None else []) if i.get("menuId")}


def extra_items(fname: str) -> dict[str, str]:
    p = EXTRA / fname
    if not p.exists():
        return {}
    return {i.get("english"): i.get("text") for i in ET.parse(p).getroot().findall("Item") if i.get("text")}


def command_ids() -> dict[str, int]:
    """IDM name -> id, from the port's generated table."""
    text = (NPP / "macos" / "app" / "CommandIDs.h").read_text()
    return {m.group(2): int(m.group(1)) for m in re.finditer(r'\{(\d+), "(IDM_[A-Z0-9_]+)"', text)}


def launch_in(app, lang_file: str | None):
    """Restarts the application in an interface language (empty preferences)."""
    args = ["-NppMac.localizationFile", lang_file] if lang_file else []
    app.start(args=args)
    app.wait(lambda: app.docs(), timeout=10)
    return app


def safe_call(app, name, timeout=15.0, **args):
    try:
        return app.call(name, timeout=timeout, **args)
    except (TimeoutError, ToolError) as e:
        return e


# ---- putting the window back the way the next test expects it -------------

PANELS = ["documentMap", "functionList", "documentList", "workspace", "project1", "project2", "project3",
          "clipboardHistory", "characterPanel", "git", "markdownPreview"]


def cleanup(app):
    """Leaves no window mode, panel, second view or view toggle behind (teardown only)."""
    if not app.running:
        return
    steps = [
        lambda: app.answers(clear=True, real_modals=False),
        lambda: app.get("editor", "chromeVisible") or app.invoke("editor", "setChromeVisible:", [True]),
        lambda: app.get("app", "alwaysOnTop") and app.run("IDM_VIEW_ALWAYSONTOP"),
        lambda: app.invoke("window", "setLevel:", [0]),
        lambda: app.invoke("editor", "setSyncVerticalScroll:", [False]),
        lambda: app.invoke("editor", "setSyncHorizontalScroll:", [False]),
        lambda: app.invoke("editor", "setSyncZoom:", [False]),
        lambda: app.invoke("editor", "setSecondaryViewVisible:", [False]),
        lambda: [dock(app, "hidePanel:", p) for p in PANELS if dock(app, "hasPanel:", p) and dock(app, "isPanelVisible:", p)],
        lambda: app.sci(SCI_SETZOOM, 0),
        lambda: app.sci(SCI_SETVIEWEOL, 0),
        lambda: app.sci(SCI_SETWRAPVISUALFLAGS, 0),
        lambda: app.sci(SCI_SETBIDIRECTIONAL, 1),
        lambda: app.set_prefs(wordWrap=False, showWhitespace=False, npcShow=False, ccUniEolShow=True),
    ]
    for s in steps:
        try:
            s()
        except Exception:  # noqa: BLE001 - best effort
            pass
    try:
        if app.get("window", "styleMask") & FULLSCREEN_BIT:
            app.invoke("window", "toggleFullScreen:", [None])
            app.wait(lambda: not app.get("window", "styleMask") & FULLSCREEN_BIT, timeout=10)
    except Exception:  # noqa: BLE001
        pass


def responsive(app, timeout=5.0) -> bool:
    try:
        app.call("list_documents", timeout=timeout)
        return True
    except Exception:  # noqa: BLE001
        return False


# ---- what does not fit in a window (shared by UI-065 and L10N-015)

_JXA_BUTTONS = r"""
ObjC.import('AppKit');
function run(argv) {
  var out = [];
  JSON.parse(argv[0]).forEach(function (q) {
    var r = $.NSMakeRect(0, 0, q[1], q[2]), b;
    if (q[3] === "popup") {
      b = $.NSPopUpButton.alloc.initWithFramePullsDown(r, false);
      b.addItemWithTitle($(q[0]));
    } else {
      b = $.NSButton.alloc.initWithFrame(r);
      b.bezelStyle = $.NSBezelStyleRounded;
      b.title = $(q[0]);
    }
    var attrs = $.NSDictionary.dictionaryWithObjectForKey(b.font, $.NSFontAttributeName);
    out.push([$(q[0]).sizeWithAttributes(attrs).width, b.cell.titleRectForBounds(b.bounds).size.width]);
  });
  return JSON.stringify(out);
}
"""


def _button_room(buttons):
    """For push buttons and pop-ups [(title, width, height, "button"|"popup")]: (width the title needs,
    width AppKit gives it) in a control of that size and kind, system font. The hook's cell_size is the
    preferred size - a rounded push button's bezel margins and all (26 pt high "needs" 32), a pop-up's
    widest item - not what the text shown needs."""
    if not buttons:
        return []
    import json, subprocess, tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
        fh.write(_JXA_BUTTONS)
    out = subprocess.run(["osascript", "-l", "JavaScript", fh.name, json.dumps(buttons)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def cut_controls_measured(app, number):
    """Controls whose text does not fit: push buttons and pop-ups by the room AppKit gives their title
    (their cell_size is the preferred size, bezel margins included), the rest by cell_size."""
    bad, buttons = [], []
    for c in ui(app, number)["controls"]:
        if c.get("hidden") or "fits" not in c or c.get("wraps") or c.get("editable"):
            continue
        text = c.get("title") or c.get("value")
        if not text:
            continue
        need, have = c["cell_size"], c["size"]
        # A push button (the hooks give no bezel; a check box or radio is 20 pt high or less, a rounded
        # push button 26-30): measured by its title below.
        if c["class"] == "NSButton" and have[1] >= 24:
            buttons.append((text, have[0], have[1], "button"))
            continue
        if c["class"] == "NSPopUpButton":
            buttons.append((text, have[0], have[1], "popup"))   # the item shown, not the widest one
            continue
        if need[0] > have[0] + 1.5 or need[1] > have[1] + 1.5:
            bad.append(f"{text!r} needs {need} has {have}")
    for (text, w, h, kind), (need, room) in zip(buttons, _button_room(buttons)):
        if need > room + 0.5:
            bad.append(f"{kind} {text!r} needs {need:.1f} for its title, has {room:.1f} (frame {w}x{h})")
    return bad
