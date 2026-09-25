"""Shared helpers for the COMPARE tests (plan/COMPARE.md)."""
import time

from harness.sci import (SCI_GETLENGTH, SCI_GETLINECOUNT, SCI_GETMARGINWIDTHN, SCI_GETTEXT,
                         SCI_INDICATORVALUEAT, SCI_MARKERGET, SCI_POSITIONFROMLINE)

OLD = "alpha\nbeta x\ngamma\n"
NEW = "alpha\nbetta x\ngamma\ndelta\n"
MOVED_OLD = "int a = 1;\nint b = 2;\nint c = 3;\nint d = 4;\nint e = 5;\nint moved = 9;\nint f = 6;\n"
MOVED_NEW = "int moved = 9;\nint a = 1;\nint B = 2;\nint c = 3;\nint added = 0;\nint added2 = 0;\nint d = 4;\nint f = 6;\n"

SUMMARY_NEW_OLD = "1 added, 0 removed, 1 changed, 2 unchanged."
SUMMARY_MOVED = "2 added, 1 removed, 1 moved, 1 changed, 4 unchanged."
IDENTICAL = "The files are identical."
NOTHING_TITLE = "Nothing to compare with."
NOTHING_INFO = 'Choose "Set as First to Compare" on one file, then run Compare on the other.'

P = "Plugins|Compare|"
SET_FIRST = P + "Set as First to Compare"
COMPARE = P + "Compare"
WITH_FILE = P + "Compare with File..."
NEXT = P + "Next Difference"
PREV = P + "Previous Difference"
FIRST = P + "First Difference"
LAST = P + "Last Difference"
SUMMARY = P + "Compare Summary"
IGNORE_CASE = P + "Ignore Case"
IGNORE_SPACES = P + "Ignore Spaces"
IGNORE_EMPTY = P + "Ignore Empty Lines"
DETECT_MOVES = P + "Detect Moves"
CHAR_DIFFS = P + "Detect Character Differences"
CLEAR = P + "Clear Active Compare"
CLEAR_ALL = P + "Clear All Compares"
GIT_HEAD = "Plugins|Git|Compare with HEAD"
GIT_CLEAR = "Plugins|Git|Clear Active Compare"

OPTION_PREFS = {
    IGNORE_CASE: "compareIgnoreCase",
    IGNORE_SPACES: "compareIgnoreSpaces",
    IGNORE_EMPTY: "compareIgnoreEmptyLines",
    DETECT_MOVES: "compareDetectMoves",
    CHAR_DIFFS: "compareCharDiffs",
}
DEFAULTS = {"compareIgnoreCase": False, "compareIgnoreSpaces": False, "compareIgnoreEmptyLines": False,
            "compareDetectMoves": True, "compareCharDiffs": True}

# markers written by the engine: backgrounds 0 (changed), 2 (added), 3 (removed), 4 (moved);
# 9 = the port's revert arrow; symbols 10-19 in margin 5
BACKGROUND_BITS = (1 << 0) | (1 << 2) | (1 << 3) | (1 << 4)
COMPARE_BITS = BACKGROUND_BITS | sum(1 << b for b in range(9, 20))


def write(tmp, name, text, encoding="utf-8"):
    p = tmp / name
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_bytes(text.encode(encoding))
    return p


def clear_all(app):
    app.run(CLEAR_ALL)
    app.modal_log(clear=True)


def restore_options(app):
    app.set_prefs(**DEFAULTS)


def marks(app, line, view="main"):
    return app.sci(SCI_MARKERGET, line, 0, view=view)


def has(app, line, bit, view="main"):
    return bool(marks(app, line, view) & (1 << bit))


def line_count(app, view="main"):
    return app.sci(SCI_GETLINECOUNT, view=view)


def all_marks(app, view="main"):
    return [marks(app, i, view) for i in range(line_count(app, view))]


def pane_text(app, view="sub"):
    n = app.sci(SCI_GETLENGTH, view=view)
    return app.sci(SCI_GETTEXT, n + 1, 0, view=view, returns="string")


def margin5(app):
    return app.sci(SCI_GETMARGINWIDTHN, 5)


def _bar_on_screen(app):
    return app.get("editor", "compareBar.window") is not None


def bar(app):
    """The bar's summary text, or None when the bar is not shown.

    The bar's own controls are read by key path: e2e_ui does not answer for them."""
    if not _bar_on_screen(app):
        return None
    ids = app.get("editor", "compareBar.subviews.identifier") or []
    values = app.get("editor", "compareBar.subviews.stringValue") or []
    return dict(zip(ids, values)).get("compareSummary")


def bar_buttons(app):
    """[{title, tooltip}] of the bar's buttons on screen."""
    if not _bar_on_screen(app):
        return []
    ids = app.get("editor", "compareBar.subviews.identifier") or []
    tips = app.get("editor", "compareBar.subviews.toolTip") or []
    return [{"title": i, "tooltip": t} for i, t in zip(ids, tips) if i in ("◀", "▶", "✕")]


def second_pane_shown(app):
    return bool(app.get("editor", "secondaryViewVisible"))


def alerts(log):
    return [e for e in log if e.get("kind") == "alert"]


def compare_with_file(app, path):
    """Compare with File... answering the panel with path; returns the modal log."""
    app.answers(panels=[str(path)])
    app.run(WITH_FILE)
    return app.modal_log()


def open_and_compare(app, doc_path, other_path):
    app.open(doc_path)
    log = compare_with_file(app, other_path)
    a = alerts(log)
    return a[-1].get("informative") if a else None


def ind18(app, line, count, view="main"):
    start = app.sci(SCI_POSITIONFROMLINE, line, view=view)
    return [app.sci(SCI_INDICATORVALUEAT, 18, start + i, view=view) for i in range(count)]


def caret_line(app):
    return app.selection()["caret"]["line"]


def wait_bar(app, text, timeout=5.0):
    return app.wait(lambda: bar(app) == text, timeout=timeout, message=f"bar says {text!r}")


def timed(fn):
    t = time.monotonic()
    fn()
    return time.monotonic() - t
