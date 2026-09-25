"""Helpers for the SETTINGS tests: the Preferences dialog driven through its own controls."""
from __future__ import annotations

import contextlib
from pathlib import Path

import pytest

PREFS = "Preferences"
PAGES = ["General", "Toolbar", "Editing 1", "Editing 2", "Dark Mode", "Margins/Border/Edge", "New Document",
         "Indentation", "Language", "Highlighting", "Print", "Backup", "Auto-Completion", "Multi-Instance & Date",
         "Delimiter", "Performance", "Tab Bar", "Recent Files History", "Default Directory", "Searching",
         "Cloud & Link", "MISC.", "Search Engine"]

SUPPORT = "Library/Application Support/NotepadMac"


def support(app) -> Path:
    return app.home / SUPPORT


def prefs_visible(app) -> bool:
    return any(w["title"] == PREFS and w["visible"] for w in app.windows())


def open_prefs(app):
    if not prefs_visible(app):
        app.run("IDM_SETTING_PREFERENCE")
        app.wait(lambda: prefs_visible(app), message="the Preferences window")


def close_prefs(app):
    if prefs_visible(app):
        app.click(PREFS, "Cancel")
        app.wait(lambda: not prefs_visible(app), message="Preferences closed")


def category_table(app) -> dict:
    for c in app.ui(PREFS)["controls"]:
        if c["class"] == "NSTableView" and c.get("rows") == len(PAGES) and c["frame"][0] < 1e9:
            return c
    raise AssertionError("no category table")


def page(app, name: str):
    """Opens Preferences on a page (by its English name)."""
    open_prefs(app)
    table = category_table(app)
    row = PAGES.index(name)       # the rows keep this order in every interface language
    app.act(PREFS, "select", row, path=table["path"])


def controls(app) -> list[dict]:
    return app.ui(PREFS)["controls"]


def _centre_y(c):
    f = c["frame"]
    return f[1] + f[3] / 2


def control_for(app, caption: str, index: int = 0, kinds=("NSPopUpButton", "NSTextField")) -> dict:
    """The field or pop-up beside (or just below) a caption label on the page shown."""
    cs = controls(app)
    labels = [c for c in cs if c["class"] == "NSTextField" and not c.get("editable") and c.get("value") == caption]
    if len(labels) <= index:
        raise AssertionError(f"no caption {caption!r}")
    label = labels[index]
    lf = label["frame"]
    cands = [c for c in cs if c is not label and c["class"] in kinds
             and (c["class"] != "NSTextField" or c.get("editable"))]
    same_row = [c for c in cands if abs(_centre_y(c) - _centre_y(label)) < 12 and c["frame"][0] > lf[0] + 20]
    if same_row:
        return min(same_row, key=lambda c: c["frame"][0])
    below = [c for c in cands if c["frame"][1] + c["frame"][3] <= lf[1] + 2 and lf[1] - (c["frame"][1] + c["frame"][3]) < 40]
    if below:
        return max(below, key=lambda c: c["frame"][1])
    raise AssertionError(f"no control beside {caption!r}")


def check(app, title: str, on: bool = True):
    return app.act(PREFS, "set_state", 1 if on else 0, title=title)


def state(app, title: str) -> int:
    for c in controls(app):
        if c["class"] == "NSButton" and c.get("title") == title:
            return c["state"]
    raise AssertionError(f"no checkbox {title!r}")


def field(app, caption: str, value, index: int = 0):
    c = control_for(app, caption, index)
    return app.act(PREFS, "set_value", str(value), path=c["path"])


def popup(app, caption: str, item, index: int = 0):
    c = control_for(app, caption, index, kinds=("NSPopUpButton",))
    return app.act(PREFS, "select", item, path=c["path"])


def value(app, caption: str, index: int = 0):
    return control_for(app, caption, index).get("value")


def apply(app):
    app.click(PREFS, "Apply")
    app.idle(0.05)


def set_options(app, pagename: str, checks: dict | None = None, fields: dict | None = None,
                popups: dict | None = None, close: bool = True):
    """Sets controls on one page and clicks Apply."""
    page(app, pagename)
    for t, on in (checks or {}).items():
        check(app, t, on)
    for cap, v in (fields or {}).items():
        field(app, cap, v)
    for cap, v in (popups or {}).items():
        popup(app, cap, v)
    apply(app)
    if close:
        close_prefs(app)


def stored(app) -> dict:
    """The preferences in the persistent domain (argument-domain values left out)."""
    return app.call("e2e_prefs", all=True)["values"].get("all", {})


@contextlib.contextmanager
def keep_prefs(app):
    """Puts the persistent preferences back as they were after the block."""
    before = stored(app)
    try:
        yield
    finally:
        if app.running:
            with contextlib.suppress(Exception):
                close_prefs(app)
            now = stored(app)
            changes = {k: None for k in now if k not in before}
            changes.update({k: v for k, v in before.items() if now.get(k) != v})
            if changes:
                app.set_prefs(**changes)


@pytest.fixture
def fresh(fresh_app):
    """A newly started app with empty preferences and home; stopped afterwards, so
    the next test starts from a clean domain again."""
    yield fresh_app
    fresh_app.stop()


@pytest.fixture
def papp(app):
    """The app, with its preferences restored after the test."""
    with keep_prefs(app):
        yield app


def light(app):
    """Colour checks assume the light appearance and the Default theme."""
    app.set_prefs(appearanceMode=1, lightThemeName="Default")
    app.run("IDM_LANG_TEXT", expect_ran=False)


def status_text(app) -> str:
    """The status bar's "length: … Ln: …" field as shown; "" when the status bar is hidden."""
    for c in app.ui("main")["controls"]:
        if c["class"] == "NSTextField" and "length:" in str(c.get("value")):
            return c["value"]
    return ""


def indicator_runs(app, indicator: int, view: str = "main") -> list[tuple[int, int]]:
    """The runs of an indicator, as (start, end)."""
    from harness.sci import SCI_GETLENGTH, SCI_INDICATOREND, SCI_INDICATORVALUEAT
    length = app.sci(SCI_GETLENGTH, view=view)
    runs, pos = [], 0
    while pos < length:
        end = app.sci(SCI_INDICATOREND, indicator, pos, view=view)
        if end <= pos:
            end = length
        if app.sci(SCI_INDICATORVALUEAT, indicator, pos, view=view):
            runs.append((pos, end))
        pos = end
    return runs


def window_visible(app, title: str) -> bool:
    return any(w["title"] == title and w["visible"] for w in app.windows())


def panel_shown(app, name: str) -> bool:
    """Whether a docked panel (documentMap, functionList, ...) is shown."""
    return bool(app.invoke("class:NppDockingManager", "isPanelVisible:", [name]))


def diff(before: dict, after: dict) -> dict:
    """The stored keys that changed, with their new values (None = removed)."""
    return {k: after.get(k) for k in set(before) | set(after) if before.get(k) != after.get(k)}


def frame_snapshot(app, path, window="main"):
    """The whole window, title bar and toolbar included."""
    app.call("e2e_snapshot", window=window, path=str(path), frame=True)
    from PIL import Image
    return Image.open(path).convert("RGB")


def plain_snapshot(app, path, window="main"):
    app.snapshot(path, window=window)
    from PIL import Image
    return Image.open(path).convert("RGB")


def wait_folds(app, line: int = 0):
    """Until the lexer has made `line` a fold header."""
    from harness.sci import SCI_GETFOLDLEVEL, SC_FOLDLEVELHEADERFLAG
    app.wait(lambda: app.sci(SCI_GETFOLDLEVEL, line) & SC_FOLDLEVELHEADERFLAG, message="fold levels")


def still_snapshot(app, path, window="main"):
    """A snapshot that does not depend on the caret's blink: the caret is hidden for it."""
    from harness.sci import SCI_GETCARETSTYLE, SCI_SETCARETSTYLE
    CARETSTYLE_INVISIBLE = 0      # Scintilla.h; not among the generated constants
    style = app.sci(SCI_GETCARETSTYLE)
    app.sci(SCI_SETCARETSTYLE, CARETSTYLE_INVISIBLE)
    try:
        return plain_snapshot(app, path, window)
    finally:
        app.sci(SCI_SETCARETSTYLE, style)


def page_tables(app) -> list[dict]:
    """The tables of the page shown (the category table left out), left to right."""
    return sorted((c for c in controls(app) if c["class"] == "NSTableView" and c is not category_table(app)
                   and c["path"] != category_table(app)["path"]), key=lambda c: c["frame"][0])


def rect(value) -> tuple[float, float, float, float]:
    """An NSRect as the hooks give it ("{{x, y}, {w, h}}" or a list) as numbers."""
    import re as _re
    if isinstance(value, (list, tuple)):
        flat = []
        for v in value:
            flat += list(v) if isinstance(v, (list, tuple)) else [v]
        return tuple(float(x) for x in flat[:4])
    return tuple(float(x) for x in _re.findall(r"-?\d+(?:\.\d+)?", str(value))[:4])


def save_new_as(app, path):
    """Saves the untitled document in front through the Save panel, answered with `path`."""
    app.answers(panels=[str(path)])
    app.run("IDM_FILE_SAVE")
    app.wait(lambda: app.doc().get("path") and app.same_path(app.doc()["path"], path), message=f"saved as {path}")


def indicator_runs_upto(app, indicator: int, end: int, view: str = "main") -> list[tuple[int, int]]:
    """The runs of an indicator that start before `end` (a big document need not be walked)."""
    from harness.sci import SCI_INDICATOREND, SCI_INDICATORVALUEAT
    runs, pos = [], 0
    while pos < end:
        stop = app.sci(SCI_INDICATOREND, indicator, pos, view=view)
        if stop <= pos:
            break
        if app.sci(SCI_INDICATORVALUEAT, indicator, pos, view=view):
            runs.append((pos, stop))
        pos = stop
    return runs


def tab_label(app, title: str) -> str:
    """What the tab of the document titled `title` shows (the tab bar may shorten it)."""
    for c in app.ui("main")["controls"]:
        if c["class"] == "NppTabBarView":
            tabs = c.get("tabs", [])
            for t in tabs:
                if t.get("title") == title:
                    return t.get("label", t.get("shown", t["title"]))
            return tabs[-1].get("label", tabs[-1].get("shown", tabs[-1]["title"])) if tabs else ""
    return ""


# ---- Shortcut Mapper ----------------------------------------------------------

MAPPER = "Shortcut Mapper"


def open_mapper(app):
    """Opens the mapper on Main menu with no filter (the window is kept between openings, and so is its state)."""
    if not window_visible(app, MAPPER):
        app.run("IDM_SETTING_SHORTCUT_MAPPER")
        app.wait(lambda: window_visible(app, MAPPER), message="the Shortcut Mapper")
    mapper_segment(app, "Main menu")
    mapper_filter(app, "")


def close_mapper(app):
    if window_visible(app, MAPPER):
        app.click(MAPPER, "Close")
        app.wait(lambda: not window_visible(app, MAPPER), message="the Shortcut Mapper closed")


def mapper_table(app) -> dict:
    return next(c for c in app.ui(MAPPER)["controls"] if c["class"] == "NSTableView")


def mapper_rows(app) -> list[list[str]]:
    return mapper_table(app)["cells"]


def mapper_filter(app, text: str):
    app.act(MAPPER, "set_value", text, placeholder="Filter", send_action=True)
    app.idle(0.05)


def mapper_segment(app, label: str):
    app.act(MAPPER, "select", label, **{"class": "NSSegmentedControl"})
    app.idle(0.05)


def mapper_select(app, name: str, where: str | None = None) -> int:
    """Selects the row named `name` (and in menu `where`), filtering by the name first."""
    mapper_filter(app, name)
    rows = mapper_rows(app)
    for i, r in enumerate(rows):
        if r[0] == name and (where is None or (len(r) > 2 and r[2] == where)):
            app.act(MAPPER, "select", i, path=mapper_table(app)["path"])
            app.idle(0.05)
            return i
    raise AssertionError(f"no mapper row {name!r} in {rows}")


def mapper_row(app, name: str, where: str | None = None) -> list[str] | None:
    for r in mapper_rows(app):
        if r[0] == name and (where is None or (len(r) > 2 and r[2] == where)):
            return r
    return None


def mapper_status(app) -> str:
    """The line under the table (conflicts, notes)."""
    for c in app.ui(MAPPER)["controls"]:
        if c["class"] == "NSTextField" and c["path"] == "0.1.3":
            return c.get("value") or ""
    return ""


def mapper_button_enabled(app, title: str) -> bool:
    for c in app.ui(MAPPER)["controls"]:
        if c["class"] == "NSButton" and c.get("title") == title:
            return c.get("enabled", True) not in (False, 0)
    raise AssertionError(f"no button {title!r}")


def shortcuts_xml(app) -> Path:
    return support(app) / "shortcuts.xml"


# ---- Style Configurator ---------------------------------------------------------

STYLES = "Style Configurator"


def open_styles(app):
    if not window_visible(app, STYLES):
        app.run("IDM_LANGSTYLE_CONFIG_DLG")
        app.wait(lambda: window_visible(app, STYLES), message="the Style Configurator")


def styles_controls(app) -> list[dict]:
    return app.ui(STYLES)["controls"]


def styles_tables(app) -> tuple[dict, dict]:
    """(Language table, Style table)."""
    ts = sorted((c for c in styles_controls(app) if c["class"] == "NSTableView"), key=lambda c: c["frame"][0])
    return ts[0], ts[1]


def styles_select(app, language: str | None = None, style: str | None = None):
    if language is not None:
        lang = styles_tables(app)[0]
        row = [r[0] for r in lang["cells"]].index(language)
        app.act(STYLES, "select", row, path=lang["path"], send_action=True)
        app.idle(0.05)
    if style is not None:
        st = styles_tables(app)[1]
        row = [r[0] for r in st["cells"]].index(style)
        app.act(STYLES, "select", row, path=st["path"], send_action=True)
        app.idle(0.05)


def styles_control(app, cls: str, index: int = 0) -> dict:
    return [c for c in styles_controls(app) if c["class"] == cls][index]


def styles_after(app, caption: str, cls: str) -> dict:
    """The first control of a class after a caption label, in the window's order."""
    cs = styles_controls(app)
    i = next(k for k, c in enumerate(cs) if c["class"] == "NSTextField" and c.get("value") == caption)
    return next(c for c in cs[i + 1:] if c["class"] == cls)


def chord_of(shown: str) -> str:
    """The mapper's "⇧⌘D" (first key of a list) as an e2e_keys chord, "shift+cmd+d"."""
    shown = shown.split(",")[0].strip()
    mods = {"⌃": "ctrl", "⌥": "alt", "⇧": "shift", "⌘": "cmd"}
    names = {"↩": "return", "⌫": "delete", "⌦": "forwarddelete", "⇥": "tab", "⎋": "escape", "↑": "up", "↓": "down",
             "←": "left", "→": "right", "⇞": "pageup", "⇟": "pagedown", "↖": "home", "↘": "end", "Space": "space"}
    parts, i = [], 0
    while i < len(shown) and shown[i] in mods:
        parts.append(mods[shown[i]])
        i += 1
    key = shown[i:]
    parts.append(names.get(key, key.lower()))
    return "+".join(parts)


def mapper_capture(app, chord: str, shown: str, button: str = "OK"):
    """Modify… on the selected row for real: the keys are pressed into its alert, then `button`."""
    app.answers(real_modals=True)
    try:
        before = {w["number"] for w in app.windows()}
        pending = app.call_async("e2e_act", window=MAPPER, action="click", target={"title": "Modify…"})
        alert = app.wait(lambda: next((w for w in app.windows() if w["number"] not in before and w["visible"]), None),
                         timeout=5, message="the Modify alert")
        app.keys(chord, window=alert["number"])
        app.wait(lambda: any(c.get("value") == shown for c in app.ui(alert["number"])["controls"]), timeout=5,
                 message=f"{shown} shown in the alert")
        app.click(alert["number"], button)
        pending.wait(10)
    finally:
        app.answers(real_modals=False)
