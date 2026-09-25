"""Shared helpers for tests/test_search.py (the Search menu and the Find dialog).

The Find dialog is read through key paths on the AppDelegate's outlets
(findField, matchCaseBox, findStatus...) and driven through e2e_act (fields,
buttons, segments, radio groups) and e2e_mouse (check boxes: e2e_ui and
e2e_act never answer for a check box in this build, see the report).
"""
from __future__ import annotations

import os
from pathlib import Path

from harness.app import ToolError
from harness.sci import (SCI_GETCURRENTPOS, SCI_GETLENGTH, SCI_GETSELECTIONEND, SCI_GETSELECTIONSTART,
                         SCI_INDICATOREND, SCI_INDICATORVALUEAT, SCI_LINEFROMPOSITION, SCI_SETSEL)

FIND_MARK = 13            # the Find Mark style's indicator
BOOKMARK_MARKER = 1

FIELDS = {"what": ("findField", "0.1.2"), "with": ("replaceField", "0.1.4"),
          "filters": ("filtersField", "0.1.7"), "dir": ("directoryField", "0.1.9")}
BOXES = {"recursive": ("recursiveBox", "In all sub-folders"), "hidden": ("hiddenBox", "In hidden folders"),
         "dotnl": ("dotNewlineBox", ". matches newline"), "case": ("matchCaseBox", "Match case"),
         "word": ("wholeWordBox", "Match whole word only"), "wrap": ("wrapBox", "Wrap around"),
         "backward": ("backwardBox", "Backward direction"), "insel": ("inSelectionBox", "In selection"),
         "bookmark": ("bookmarkLineBox", "Bookmark line"), "purge": ("purgeBox", "Purge for each search"),
         "transparency": ("transparencyBox", "Transparency")}
DEFAULTS = {"recursive": 1, "hidden": 0, "dotnl": 0, "case": 0, "word": 0, "wrap": 1, "backward": 0,
            "insel": 0, "bookmark": 0, "purge": 0}
TABS = ["Find", "Replace", "Find in Files", "Find in Projects", "Mark"]
SAVED_PREFS = ["findHistory", "replaceHistory", "filterHistory", "directoryHistory", "findMatchCase",
               "findWholeWord", "findWrap", "findMode", "findTransparencyMode", "findTransparencyLevel",
               "searchResultsPurge", "markAllCaseSensitive", "markAllWordOnly", "confirmReplaceAllOpenDocs",
               "findDialogStaysOpen", "fillDirectoryFromActiveDocument", "inSelectionThreshold",
               "fillFindWhatThreshold"]


class Dlg:
    """The Find dialog of a running app."""

    def __init__(self, app):
        self.app = app

    # ---- reading
    def get(self, keypath):
        return self.app.get("app", keypath)

    @property
    def built(self):
        return self.get("findPanel") is not None

    @property
    def visible(self):
        return bool(self.built and self.get("findPanel.visible"))

    @property
    def number(self):
        return self.get("findPanel.windowNumber")

    @property
    def title(self):
        return self.get("findPanel.title")

    @property
    def tab_index(self):
        return self.get("findTabs.selectedSegment")

    def value(self, field):
        return self.get(FIELDS[field][0] + ".stringValue")

    def items(self, field):
        return self.get(FIELDS[field][0] + ".objectValues")

    def hidden(self, outlet):
        return bool(self.get(outlet + ".hidden"))

    def state(self, box):
        return self.get(BOXES[box][0] + ".state")

    def enabled(self, box):
        return bool(self.get(BOXES[box][0] + ".enabled"))

    def status(self):
        return self.get("findStatus.stringValue")

    def mode(self):
        return self.get("modeRadios.selectedRow")

    # ---- acting as a user
    def set(self, field, text):
        self.app.act(self.number, "set_value", text, path=FIELDS[field][1])
        assert self.value(field) == text

    def press(self, title):
        r = self.app.act(self.number, "click", title=title, **{"class": "NSButton"})
        assert r.get("acted"), r
        return r

    def box(self, box, on):
        """Ticks or unticks a check box as a click would.

        e2e_mouse cannot click an NSButton check box (its tracking loop waits for a real
        mouse-up) and e2e_act's reply for a check box never comes back in this build, so the
        state is set by key path; the box must be visible and enabled, as for a user, and the
        one box with an action of its own (Transparency) gets it sent.
        """
        outlet = BOXES[box][0]
        want = 1 if on else 0
        assert not self.hidden(outlet), f"{box} is hidden"
        assert self.enabled(box), f"{box} is disabled"
        if self.state(box) != want:
            self.app.invoke("app", "setValue:forKeyPath:", [want, outlet + ".state"])
            if box == "transparency":
                self.app.invoke("app", "findTransparencyChanged:", [None])
        assert self.state(box) == want, f"{box} did not become {want}"

    def set_mode(self, row):
        self.app.act(self.number, "select", row, path="0.1.14")
        assert self.mode() == row

    def select_tab(self, name):
        self.app.act(self.number, "select", name, path="0.1.0")
        assert self.title == name

    def force(self, box, on):
        """Sets a box without the user path (for resetting the dialog between tests)."""
        self.app.invoke("app", "setValue:forKeyPath:", [1 if on else 0, BOXES[box][0] + ".state"])

    def reset(self):
        if not self.built:
            return
        for f in FIELDS:
            self.app.invoke("app", "setValue:forKeyPath:", ["", FIELDS[f][0] + ".stringValue"])
        for b, v in DEFAULTS.items():
            self.force(b, v)
        self.app.invoke("app", "setValue:forKeyPath:", ["", "findStatus.stringValue"])

    def close(self):
        if self.visible:
            self.app.close_window(self.number)


def open_dlg(app, command="IDM_SEARCH_FIND") -> Dlg:
    app.run(command)
    d = Dlg(app)
    app.wait(lambda: d.visible, message="the Find dialog")
    return d


def fresh_dlg(app, command="IDM_SEARCH_FIND", tab=None) -> Dlg:
    """Opens the dialog with every option back at its default, on the wanted tab."""
    d = Dlg(app)
    d.reset()
    d = open_dlg(app, command)
    for f in FIELDS:
        if d.value(f):
            d.set(f, "")
    if d.mode() != 0:
        d.set_mode(0)
    if tab:
        d.select_tab(tab)
    return d


def prefs_snapshot(app):
    return app.prefs(*SAVED_PREFS)


def prefs_restore(app, saved):
    app.set_prefs(**{k: v for k, v in saved.items() if v is not None})


# ---- the editor

def sel(app):
    return app.sci(SCI_GETSELECTIONSTART), app.sci(SCI_GETSELECTIONEND)


def setsel(app, a, b=None):
    app.sci(SCI_SETSEL, a, a if b is None else b)


def caret(app):
    return app.sci(SCI_GETCURRENTPOS)


def caret_line(app):
    return app.sci(SCI_LINEFROMPOSITION, caret(app)) + 1


def ranges(app, indicator, view="main"):
    """[(start, end)] byte ranges carrying the indicator."""
    length = app.sci(SCI_GETLENGTH, view=view)
    out, pos = [], 0
    while pos < length:
        value = app.sci(SCI_INDICATORVALUEAT, indicator, pos, view=view)
        end = app.sci(SCI_INDICATOREND, indicator, pos, view=view)
        if end <= pos:
            end = length
        if value:
            out.append((pos, end))
        pos = end
    return out


def bookmarks(app):
    return app.call("bookmarks")["bookmarked_lines"]


def beeps(app):
    return app.counters()["beeps"]


def titles(app):
    """Every tab's title, the Search results tab included."""
    return app.get("editor", "documents.displayName")


def results_front(app):
    return bool(app.get("editor", "currentDocument.isSearchResults"))


def results_text(app):
    if not results_front(app):
        app.run("IDM_FOCUS_ON_FOUND_RESULTS")
    assert results_front(app)
    return app.text()


def status_contains(d, text, timeout=30):
    return d.app.wait(lambda: text in (d.status() or ""), timeout=timeout, message=f"status with {text!r}")


def wait_search_done(d, timeout=60):
    """Waits for a folder search to end: its status says 'N found' / 'replaced in'."""
    def done():
        s = d.status() or ""
        return (s.endswith("found") or "found (stopped)" in s or " replaced in " in s or
                s.startswith("Choose") or s.startswith("The ticked")) and not d.get("runningSearch")
    d.app.wait(done, timeout=timeout, message="the folder search to end")
    return d.status()


def make_tree(root: Path):
    """The tree of SEARCH-058."""
    root = Path(root)
    (root / "sub").mkdir(parents=True, exist_ok=True)
    (root / ".hid").mkdir(exist_ok=True)
    (root / "a.txt").write_bytes(b"hello needle\nplain\n")
    (root / "b.log").write_bytes(b"needle again\r\nneedle twice\r\n")
    (root / "sub" / "c.txt").write_bytes(b"needle deep\n")
    (root / ".hid" / "d.txt").write_bytes(b"needle hidden\n")
    (root / "bin.dat").write_bytes(b"\x00\x01\x02needle\x00\xff\xfe")
    return root


def real(p) -> str:
    return os.path.realpath(str(p))
