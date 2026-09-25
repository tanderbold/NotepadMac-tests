"""Helpers for the PLUGINS tests."""
from __future__ import annotations

import contextlib
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SDK = ROOT.parent / "npp" / "macos" / "plugin-sdk"
SAMPLE = SDK / "sample" / "hellomac.c"
FIXTURES = ROOT / "fixtures" / "plugins"

SCI_UNDO = 2176
SCI_GOTOPOS = 2025
SCI_DOCUMENTEND = 2318
SCI_GETSTYLEAT = 2010
SCI_STYLEGETFORE = 2481
SCI_INDICATORVALUEAT = 2507
SCI_INDICGETSTYLE = 2081
SCI_INDICGETFORE = 2083
SCI_INDICGETUNDER = 2511
SPELL = 17


def plugins_menu(app, depth=2):
    """The Plugins menu's items (found by its content, not its title)."""
    for top in app.menu_tree("main", depth + 1):
        titles = [i.get("title") for i in top.get("items", [])]
        if "JSON" in titles and "Markdown Preview" in titles:
            return top["items"]
    raise AssertionError("no Plugins menu")


def titles(items):
    return ["-" if i.get("separator") else i.get("title") for i in items]


def submenu(items, title):
    for i in items:
        if i.get("title") == title:
            return i.get("items", [])
    raise AssertionError(f"no submenu {title}: {titles(items)}")


def others(app):
    return [w for w in app.windows() if not w["main_window"] and w["visible"]]


def window_titled(app, title, timeout=5):
    return app.wait(lambda: next((w for w in others(app) if w["title"] == title), None), timeout,
                    message=f"window {title}")


def textviews(app, window):
    return [c for c in app.controls(window) if c["class"] == "NSTextView"]


def alerts(app):
    return [e for e in app.modal_log() if e.get("kind") == "alert"]


def run_alert(app, command):
    """Runs a command and returns the alerts it showed."""
    app.modal_log(clear=True)
    app.run(command)
    return alerts(app)


def caret_line(app):
    return app.selection()["caret"]["line"]


def undo(app):
    app.sci(SCI_UNDO)


def select_all_run(app, text, command):
    app.set_text(text)
    app.select_all()
    app.modal_log(clear=True)
    app.run(command)
    return app.text()


# ---- plugins ---------------------------------------------------------------

def plugins_dir(app) -> Path:
    return app.home / "Library/Application Support/NotepadMac/plugins"


def build(source: Path, out: Path, name: str | None = None) -> Path:
    if not shutil.which("clang"):
        pytest.skip("no clang to build a plugin with")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["clang", "-dynamiclib", "-I", str(SDK), "-o", str(out), str(source)]
    if name:
        cmd[1:1] = [f'-DPLUGIN_NAME="{name}"']
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out


def plugin_names(app):
    return app.get("class:NppPluginHost", "plugins.name") or []


@contextlib.contextmanager
def installed(app, builder):
    """builder(plugins_dir) puts plugins in place; the app is restarted with
    them, and afterwards they are removed and the app restarted clean."""
    folder = plugins_dir(app)
    try:
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True, exist_ok=True)
        builder(folder)
        app.restart()
        yield folder
    finally:
        if not app.running:
            app.start(clean_home=False, reset=False)
        shutil.rmtree(folder, ignore_errors=True)
        app.restart()


# ---- spelling ----------------------------------------------------------------

def spell_available(app, word, language):
    r = app.call("spell_check", text=word, language=language)
    return any(m["word"] == word for m in r.get("misspelled", []))


def spell_at(app, pos):
    return app.sci(SCI_INDICATORVALUEAT, SPELL, pos)


@contextlib.contextmanager
def spelling(app, language="en", probe="helo"):
    """Spell checking on (by its menu toggle) in a language; set back after."""
    if language and not spell_available(app, probe, language):
        pytest.skip(f"the spelling engine offers no {language} here")
    app.set_prefs(spellCheckLanguage=language)
    try:
        if not app.pref("spellCheckEnabled"):
            app.run("Plugins|Spell Check|Spell Check Document Automatically")
        yield
    finally:
        if app.pref("spellCheckEnabled"):
            app.run("Plugins|Spell Check|Spell Check Document Automatically")
        app.set_prefs(spellCheckLanguage=None, spellCheckEnabled=None)


def textutil_text(path) -> str:
    """The plain text of an RTF/HTML file, as macOS's own reader sees it."""
    r = subprocess.run(["textutil", "-convert", "txt", "-stdout", str(path)], capture_output=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.decode("utf-8")


def right_click(app, line, column, menu_path=None):
    """A click to put the caret in the word, then the right click there (the
    menu's spelling items are those of the word at the caret)."""
    app.select(line, column)
    return app.mouse(view="main", button="right", point={"line": line, "column": column}, menu_path=menu_path)


def spelling_items(menu):
    return [i for i in menu if i.get("action") in ("spellReplaceWord:", "spellIgnoreWord:", "spellLearnWord:")]


def markdown_html(app):
    return app.get("app", "markdownPanel.lastHTML") or ""


def markdown_visible(app):
    return bool(app.get("app", "markdownPanel.visible"))
