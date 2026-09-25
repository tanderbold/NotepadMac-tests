"""Helpers for the LANG tests (plan/LANG.md)."""
from __future__ import annotations

import csv
import os
import re
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from harness.app import ROOT, wait_for

NPP = ROOT.parent / "npp"
SAMPLES = NPP / "macos" / "resources" / "language-samples"

SCI_GETSTYLEAT = 2010
SCI_COLOURISE = 4003
SCI_GETFOLDLEVEL = 2223
SCI_GETLEXERLANGUAGE = 4012
SC_FOLDLEVELHEADERFLAG = 0x2000

UDL_DIALOG = "User Defined Language"


# ---- reference data --------------------------------------------------------

def resources(app) -> Path:
    return app.bundle / "Contents" / "Resources"


def settings_dir(app) -> Path:
    return app.home / "Library" / "Application Support" / "NotepadMac"


def language_commands() -> list[tuple[str, str]]:
    """(IDM id, label) of the Language menu's rows of commands.tsv, first occurrence, in order."""
    seen, out = set(), []
    with open(ROOT / "plan" / "commands.tsv", encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            if len(row) < 3 or row[0] != "Language" or row[1] in seen:
                continue
            seen.add(row[1])
            out.append((row[1], row[2].split(" › ")[-1]))
    return out


NON_LANGUAGE = {"IDM_LANG_USER_DLG", "IDM_LANG_OPENUDLDIR", "IDM_LANG_UDLCOLLECTION_PROJECT_SITE", "IDM_LANG_USER"}


def langmap() -> list[tuple[str, str, str]]:
    """(langName, lexerID, menuID) from the port's LangMap.h (generated from upstream)."""
    text = (NPP / "macos" / "app" / "LangMap.h").read_text()
    return re.findall(r'\{"([^"]*)", "([^"]*)", "([^"]*)"\}', text)


def by_menu_id() -> dict[str, tuple[str, str]]:
    return {m: (name, lexer) for name, lexer, m in langmap() if m}


def langs_model(app):
    return ET.parse(resources(app) / "langs.model.xml").getroot()


def stylers_model(app):
    return ET.parse(resources(app) / "stylers.model.xml").getroot()


def bgr(hex6: str) -> int:
    v = int(hex6, 16)
    return ((v & 0xFF) << 16) | (v & 0xFF00) | ((v >> 16) & 0xFF)


# ---- the editor ----------------------------------------------------------------

def status(app) -> str:
    # e2e_ui on the main window does not answer with the current build; the status
    # field's own text is read instead (the same string the user sees).
    try:
        v = app.get("editor", "statusField.stringValue")
        if isinstance(v, str) and "Ln:" in v:
            return v
    except Exception:  # noqa: BLE001
        pass
    for c in app.ui()["controls"]:
        v = c.get("value")
        if isinstance(v, str) and "Ln:" in v and "Col:" in v:
            return v
    raise AssertionError("no status bar field")


def status_language(app) -> str:
    return status(app).split("    ")[0]


def colourise(app):
    app.sci(SCI_COLOURISE, 0, -1)


def style_at(app, pos: int) -> int:
    return app.sci(SCI_GETSTYLEAT, pos)


def style_of(app, text: str, needle: str, offset: int = 0) -> int:
    """Style at the byte where `needle` starts (ASCII texts) plus offset."""
    i = text.index(needle)
    return style_at(app, len(text[:i].encode()) + offset)


def fold_headers(app, lines: int) -> list[int]:
    """One-based lines that head a fold."""
    colourise(app)
    return [n + 1 for n in range(lines) if app.sci(SCI_GETFOLDLEVEL, n) & SC_FOLDLEVELHEADERFLAG]


def lexer_language(app) -> str:
    return app.sci(SCI_GETLEXERLANGUAGE, 0, 0, returns="string")


def write(path: Path, text: str, encoding="utf-8") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)
    return path


def open_file(app, path) -> dict:
    app.open(path)
    return app.doc()


def modal_titles(entries) -> list[str]:
    return [e.get("message", "") for e in entries if e.get("kind") == "alert"]


# ---- User Defined Language dialog ------------------------------------------------

def udl_window(app):
    w = app.window(UDL_DIALOG)
    return w["number"] if w and w.get("visible", True) else None


def open_udl_dialog(app) -> int:
    if not udl_window(app):
        app.run("IDM_LANG_USER_DLG")
    return app.wait(lambda: udl_window(app), message="the UDL dialog")


def udl_controls(app, w) -> list[dict]:
    return app.ui(w)["controls"]


def after_label(ctrls, label: str, nth: int = 0, cls: str = "NSTextField", skip: int = 0) -> dict:
    """The (skip+1)th editable control of class `cls` after the nth label titled `label`."""
    seen = -1
    for i, c in enumerate(ctrls):
        if c.get("class") == "NSTextField" and not c.get("editable") and c.get("value") == label:
            seen += 1
            if seen == nth:
                k = skip
                for d in ctrls[i + 1:]:
                    if d.get("class") == cls and (cls != "NSTextField" or d.get("editable")):
                        if k == 0:
                            return d
                        k -= 1
    raise AssertionError(f"no control after label {label!r} #{nth}")


def udl_tab(app, w, title: str):
    app.act(w, "select", title, **{"class": "NSTabView"})


def udl_set_field(app, w, tab: str | None, label: str, value: str, nth: int = 0, skip: int = 0):
    if tab:
        udl_tab(app, w, tab)
    c = after_label(udl_controls(app, w), label, nth, skip=skip)
    app.act(w, "set_value", value, path=c["path"], end_editing=True)


def udl_set_keywords(app, w, group: int, words: str):
    udl_tab(app, w, "Keywords Lists")
    views = [c for c in udl_controls(app, w) if c.get("class") == "NSTextView"]
    app.act(w, "set_value", words, path=views[group - 1]["path"])
    # The text view commits a moment after the last change; ending editing commits at once.
    # "window:<spec>" takes a title or class; a window number is looked up only as a number,
    # and a spec is a string, so the dialog is named by its title.
    app.invoke(f"window:{UDL_DIALOG}", "makeFirstResponder:", [None])


def udl_check(app, w, title: str, on: bool, tab: str | None = None, index: int = 0):
    if tab:
        udl_tab(app, w, tab)
    app.act(w, "set_state", 1 if on else 0, title=title, index=index)


def udl_create(app, name: str) -> int:
    w = open_udl_dialog(app)
    app.answers(alerts=[{"button": "OK", "field": name}])
    app.click(w, "Create New…")
    app.wait(lambda: udl_selected(app, w) == name, message=f"UDL {name} selected")
    return w


def udl_selected(app, w) -> str | None:
    for c in udl_controls(app, w):
        if c.get("class") == "NSPopUpButton":
            return c.get("value")
    return None


def udl_select(app, w, name: str):
    pop = [c for c in udl_controls(app, w) if c.get("class") == "NSPopUpButton"][0]
    app.act(w, "select", name, path=pop["path"])


def udl_xml(app) -> str:
    p = settings_dir(app) / "userDefineLang.xml"
    return p.read_text() if p.exists() else ""


def wait_xml(app, pattern: str, timeout=5.0):
    return wait_for(lambda: re.search(pattern, udl_xml(app)), timeout=timeout, message=f"userDefineLang.xml ~ {pattern}")


def close_udl_dialog(app):
    w = udl_window(app)
    if w:
        app.close_window(w)


def udl_file(name: str, ext: str, keywords1: str = "", comments: str = "00 01 02 03 04",
             styles: str = "", extra_lists: dict | None = None, dark: bool = False) -> str:
    """A UDL file in Notepad++'s 2.1 format."""
    lists = {
        "Comments": comments, "Numbers, prefix1": "", "Numbers, prefix2": "", "Numbers, extras1": "",
        "Numbers, extras2": "", "Numbers, suffix1": "", "Numbers, suffix2": "", "Numbers, range": "",
        "Operators1": "", "Operators2": "", "Folders in code1, open": "", "Folders in code1, middle": "",
        "Folders in code1, close": "", "Folders in code2, open": "", "Folders in code2, middle": "",
        "Folders in code2, close": "", "Folders in comment, open": "", "Folders in comment, middle": "",
        "Folders in comment, close": "", "Keywords1": keywords1, "Keywords2": "", "Keywords3": "",
        "Keywords4": "", "Keywords5": "", "Keywords6": "", "Keywords7": "", "Keywords8": "",
        "Delimiters": "00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23",
    }
    lists.update(extra_lists or {})
    kw = "\n".join(f'            <Keywords name="{k}">{v}</Keywords>' for k, v in lists.items())
    dm = ' darkModeTheme="yes"' if dark else ""
    return f'''<?xml version="1.0" encoding="UTF-8" ?>
<NotepadPlus>
    <UserLang name="{name}" ext="{ext}" udlVersion="2.1"{dm}>
        <Settings>
            <Global caseIgnored="no" allowFoldOfComments="no" foldCompact="no" forcePureLC="0" decimalSeparator="0" />
            <Prefix Keywords1="no" Keywords2="no" Keywords3="no" Keywords4="no" Keywords5="no" Keywords6="no" Keywords7="no" Keywords8="no" />
        </Settings>
        <KeywordLists>
{kw}
        </KeywordLists>
        <Styles>
{styles}
        </Styles>
    </UserLang>
</NotepadPlus>
'''


PY_SCRIPT = (
    "import os\nimport sys\n\n"
    "def read_config(path):\n"
    "    with open(path) as handle:\n"
    "        for line in handle:\n"
    "            if line.startswith('#'):\n"
    "                continue\n"
    "            yield line.strip()\n\n"
    "class Runner:\n"
    "    def __init__(self, config):\n"
    "        self.config = config\n\n"
    "    def run(self):\n"
    "        for item in self.config:\n"
    "            print(item)\n\n"
    "if __name__ == '__main__':\n"
    "    Runner(list(read_config(sys.argv[1]))).run()\n"
)
