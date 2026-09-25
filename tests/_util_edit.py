"""Helpers shared by the EDIT, TYPING and MACRO tests."""
from __future__ import annotations

import contextlib
import os
from pathlib import Path

from harness.sci import (SCI_GETSELECTIONS, SCI_GETSELECTIONNSTART, SCI_GETSELECTIONNEND,
                         SCI_AUTOCACTIVE, SCI_AUTOCGETCURRENTTEXT, SCI_CALLTIPACTIVE,
                         SCI_GETLINEINDENTATION, SCI_GETCURRENTPOS, SCI_GETANCHOR,
                         SCI_AUTOCCANCEL, SCI_CALLTIPCANCEL)

SCI_INDICATORVALUEAT = 2507



@contextlib.contextmanager
def prefs(app, **values):
    """Sets preferences for the block and puts the old values back."""
    old = app.prefs(*values.keys())
    app.set_prefs(**values)
    try:
        yield
    finally:
        back = {k: v for k, v in old.items() if v is not None}
        if back:
            app.set_prefs(**back)


def caret(app, line, column=1):
    """Puts the caret at line:column the way a user would end up there: go_to,
    then an arrow away and back, so Scintilla's remembered column is real."""
    app.select(line, column)
    s = app.selection()
    pos = s["caret"]["position"]
    length = app.sci(2006)
    if pos < length:
        app.keys("right", "left")
    elif pos > 0:
        app.keys("left", "right")


def pos(app):
    return app.sci(SCI_GETCURRENTPOS)


def anchor(app):
    return app.sci(SCI_GETANCHOR)


def ranges(app):
    """Every selection as (start, end) byte offsets, in Scintilla's order."""
    n = app.sci(SCI_GETSELECTIONS)
    return [(app.sci(SCI_GETSELECTIONNSTART, i), app.sci(SCI_GETSELECTIONNEND, i)) for i in range(n)]


def sorted_ranges(app):
    return sorted(ranges(app))


def indicator(app, number, length=None):
    """A string of 0/1 per byte: whether indicator `number` is set there."""
    if length is None:
        length = app.sci(2006)
    return "".join("1" if app.sci(SCI_INDICATORVALUEAT, number, p) else "0" for p in range(length))


def ac_active(app):
    return app.sci(SCI_AUTOCACTIVE) != 0


def ac_current(app):
    return app.sci(SCI_AUTOCGETCURRENTTEXT, 0, 0, returns="string")


def ac_list(app):
    return app.get("editor", "lastCompletionList") or []


def ac_cancel(app):
    app.sci(SCI_AUTOCCANCEL)


def calltip_active(app):
    return app.sci(SCI_CALLTIPACTIVE) != 0


def calltip_cancel(app):
    app.sci(SCI_CALLTIPCANCEL)


def indent(app, line):
    """Indentation (columns) of a 1-based line."""
    return app.sci(SCI_GETLINEINDENTATION, line - 1)


def column_rect(app, l1, c1, l2, c2):
    """A rectangular selection made with Begin/End Select in Column Mode."""
    caret(app, l1, c1)
    app.run("IDM_EDIT_BEGINENDSELECT_COLUMNMODE")
    caret(app, l2, c2)
    app.run("IDM_EDIT_BEGINENDSELECT_COLUMNMODE")


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8")
    path.write_bytes(data)
    return path


def home_dir(app):
    return app.home / "Library/Application Support/NotepadMac"


def new_doc(app, text="", language=None):
    """A new document that is current, with the caret at its start."""
    app.new(text, language=language)
    app.keys("cmd+up")


def type_keys(app, text):
    app.type(text)


def invoke_menu(app, path, modifiers=None):
    args = {"path": path}
    if modifiers:
        args["modifiers"] = list(modifiers)
    return app.call("e2e_menu_invoke", **args)


def log_kinds(entries, kind):
    return [e for e in entries if e.get("kind") == kind]
