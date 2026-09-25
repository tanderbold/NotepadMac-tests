"""L10N: end-to-end tests (plan: plan/L10N.md)."""
import re
import xml.etree.ElementTree as ET

import pytest

from harness.sci import *  # noqa: F401,F403
from _util_view import (cut_controls_measured as _cut, NATIVE, cleanup, command_ids, dock, extra_items, flat, fresh_doc, main_window,
                        native_commands, native_menus, native_submenus, path_field, snap, status, strip_keys, ui,
                        window_titled, write)


@pytest.fixture
def lang(app_session):
    """Starts the application in an interface language; plain English again afterwards."""
    started = []

    def start(fname):
        args = ["-NppMac.localizationFile", fname] if fname else []
        app_session.start(args=args)
        app_session.wait(lambda: app_session.docs(), timeout=10)
        started.append(fname)
        return app_session
    yield start
    if started:
        app_session.start()


def norm(s):
    s = strip_keys(s or "")
    return re.sub(r"\s+", " ", s).strip()


def windows_title(s):
    """A Windows menu label as a Mac menu shows it: "&&" is a literal "&", a lone "&" marks the
    mnemonic and goes; "..." is an ellipsis; a tab starts the shortcut."""
    s = re.sub(r"&(&)?", lambda m: "&" if m.group(1) else "", s or "")
    s = s.replace("...", "…").split("\t")[0]
    return re.sub(r"\s+", " ", s).strip()


def mac_title(s):
    """A Mac menu title has no mnemonics: every "&" in it is shown."""
    s = (s or "").replace("...", "…").split("\t")[0]
    return re.sub(r"\s+", " ", s).strip()


def by_action(tree):
    """(action, tag) -> title, for the items where that pair is unique."""
    seen, out = {}, {}
    for _, i in flat(tree):
        if not i.get("action") or i.get("action") == "submenuAction:":
            continue
        k = (i["action"], i.get("tag"))
        seen[k] = seen.get(k, 0) + 1
        out[k] = i["title"]
    return {k: v for k, v in out.items() if seen[k] == 1}


def main_tree(app, depth=3):
    return app.menu_tree("main", depth)


# ---------------------------------------------------------------- choosing the language

@pytest.mark.case("L10N-001")
def test_l10n_001_launching_in_russian_translates_the_menu_bar(lang):
    app = lang("russian.xml")
    tops = [i["title"] for i in app.menu_tree("main", 0)]
    menus = native_menus("russian.xml")
    expected = [norm(menus[k]) for k in ("file", "edit", "search", "view", "encoding", "language", "settings",
                                          "tools", "macro", "run", "Plugins", "Window")]
    assert tops[0] == "NotepadMac"
    for e in expected:
        assert e in [norm(t) for t in tops], (e, tops)
    assert app.modal_log() == [], app.modal_log()


ROOT = __import__('pathlib').Path(__file__).resolve().parent.parent


def _upstream_labels():
    """IDM name -> the label of upstream's menu (the port's generated CommandIDs.h)."""
    import re as _re
    src = (ROOT.parent / "npp" / "macos" / "app" / "CommandIDs.h").read_text()
    return {m.group(1): m.group(2) for m in _re.finditer(r'\{\d+, "(IDM_[A-Z0-9_]+)", "[^"]*", "([^"]*)"\}', src)}


def norm_label(t):
    t = t.split(" › ")[-1].split("\t")[0].replace("&", "")   # commands.tsv writes the submenu path first
    if t.endswith(")") and " (" in t:
        t = t[:t.rindex(" (")]
    return t.rstrip(".…: ").strip().lower()


UPSTREAM_LABELS = _upstream_labels()


def _menu_mismatches(app, fname):
    ids = command_ids()
    native = native_commands(fname)
    from _util_view import COMMANDS
    wanted = {ids[c[1]]: c[1] for c in COMMANDS if c[1] in ids}
    # Quit and About live in the application menu with the Mac's own words ("Quit NotepadMac",
    # "About NotepadMac", translated from nativeLang-extra), by the port's design.
    check = [i for i in native if i in wanted and wanted[i] not in ("IDM_FILE_EXIT", "IDM_ABOUT")]
    # A command the port words itself ("Move to Trash" for upstream's "Move to Recycle Bin",
    # "... in Finder") shows nativeLang-extra's translation of its own words (L10N-008 checks
    # those); only the commands named as upstream names them carry upstream's translation.
    items = app.call("e2e_menu", commands=check)["items"]
    # the item's English title (what the port calls it) against upstream's label
    check = [i for i in check if not (items.get(str(i)) and wanted[i] in UPSTREAM_LABELS and
             norm_label(items[str(i)].get("english", "")) != norm_label(UPSTREAM_LABELS[wanted[i]]))]
    bad = []
    for i in check:
        item = items.get(str(i))
        if not item:
            continue
        if mac_title(item["title"]) != windows_title(native[i]):
            bad.append((wanted[i], item["title"], native[i]))
    return bad, len(check)


@pytest.mark.case("L10N-002")
@pytest.mark.parametrize("fname", ["russian.xml", "german.xml", "french.xml", "japanese.xml",
                                   "chineseSimplified.xml", "finnish.xml"])
def test_l10n_002_menu_commands_are_translated_by_their_command_id(lang, fname):
    app = lang(fname)
    bad, n = _menu_mismatches(app, fname)
    assert n > 250   # finnish.xml translates 273 of the commands; the others more
    assert not bad, bad[:20]


@pytest.mark.case("L10N-003")
def test_l10n_003_submenus_are_translated_by_their_submenuid(lang):
    app = lang("german.xml")
    subs = native_submenus("german.xml")
    tree = main_tree(app, 2)
    names = {norm(i["title"]) for _, i in flat(tree) if "items" in i}
    wanted = ["view-showSymbol", "view-zoom", "view-moveCloneDocument", "view-currentFileIn", "view-tab",
              "view-collapseLevel", "view-uncollapseLevel", "view-project", "edit-copyToClipboard",
              "edit-lineOperations", "edit-convertCaseTo", "edit-eolConversion"]
    missing = [(k, subs.get(k)) for k in wanted if norm(subs.get(k)) not in names]
    assert not missing, missing


def _prefs_window(app):
    shown = lambda: next((w for w in app.windows() if w["class"] == "NppPanel" and w["visible"]), None)
    # Already open: the same window (the command hides a shown Preferences window in the port).
    if not shown():
        app.run("IDM_SETTING_PREFERENCE")
    w = app.wait(shown, timeout=5)
    # The window opens on whichever page it showed last; the Localization popup is on General, the
    # first row of the category table (the rows keep their order in every language).
    tables = sorted((c for c in ui(app, w["number"])["controls"] if c["class"] == "NSTableView"),
                    key=lambda c: c["frame"][0])
    app.act(w["number"], "select", 0, path=tables[0]["path"])
    return w


def _language_popup(app, w):
    for c in ui(app, w["number"])["controls"]:
        if c["class"] == "NSPopUpButton" and ENGLISH in (c.get("items") or []):
            return c
    raise AssertionError("no Localization popup")


def _language_names() -> set[str]:
    """The popup's items: each file's Native-Langue name; a name two files share ("English" for
    english.xml and english_customizable.xml) carries the file's name, since an NSPopUpButton keeps
    one item per title (SettingsPanels.mm)."""
    by_file = {}
    for f in NATIVE.glob("*.xml"):
        m = re.search(r'<Native-Langue[^>]*\bname="([^"]*)"', f.read_text(encoding="utf-8", errors="replace"))
        if m:
            by_file[f.stem] = m.group(1)
    counts = {}
    for n in by_file.values():
        counts[n] = counts.get(n, 0) + 1
    return {f"{n} ({stem})" if counts[n] > 1 else n for stem, n in by_file.items()}


ENGLISH = "English (english)"


def _choose_language(app, name):
    w = _prefs_window(app)
    popup = _language_popup(app, w)
    app.act(w["number"], "select", value=name, path=popup["path"])
    apply = next(c for c in ui(app, w["number"])["controls"]
                 if c["class"] == "NSButton" and c.get("title") in ("Apply", "Применить", "Übernehmen"))
    app.act(w["number"], "click", path=apply["path"])
    app.idle(0.3)
    return w


def _snapshot_ui(app):
    return {"menu": main_tree(app, 2), "status": status(app),
            "tab": [i.get("title") for i in app.call("e2e_menu", context="tab")["tree"]],
            "dock": dock(app, "titleOf:", "documentList")}


@pytest.mark.case("L10N-004")
def test_l10n_004_switching_the_language_in_preferences_applies_at_once_and_ba(fresh_app):
    app = fresh_app
    try:
        app.run("IDM_VIEW_DOCLIST")
        english = _snapshot_ui(app)
        w = _choose_language(app, "Русский")
        russian = _snapshot_ui(app)
        assert "длина:" in russian["status"] and russian["tab"][0] == "Закрыть"
        assert russian["dock"] == "Список Файлов"
        assert main_window(app) and window_titled(app, "Настройки")
        w = _choose_language(app, ENGLISH)
        # The first dump was taken with no Preferences window: close it, so that the Window menu's
        # list (AppKit's, with its mark on the main window) is compared in the same state.
        app.close_window(w["number"])
        app.wait(lambda: not any(x["number"] == w["number"] and x["visible"] for x in app.windows()), timeout=5)
        back = _snapshot_ui(app)
        assert back == english
    finally:
        cleanup(app)
        app.start()


@pytest.mark.case("L10N-005")
@pytest.mark.restart
def test_l10n_005_the_chosen_language_survives_a_restart(fresh_app):
    app = fresh_app
    try:
        _choose_language(app, "Deutsch")
        assert app.pref("localizationFile") == "german.xml"
        app.restart()
        tops = [i["title"] for i in app.menu_tree("main", 0)]
        new_name = native_commands("german.xml")[41001]
        assert norm(native_menus("german.xml")["file"]) in [norm(t) for t in tops]
        assert norm(app.menu_item("IDM_FILE_NEW")["title"]) == norm(new_name)
    finally:
        app.start()


@pytest.mark.case("L10N-006")
def test_l10n_006_the_language_list_names_each_language_in_itself(lang):
    app = lang("russian.xml")
    w = _prefs_window(app)
    popup = _language_popup(app, w)
    names = _language_names()
    assert set(popup["items"]) == names, set(popup["items"]) ^ names
    assert popup["value"] == "Русский"


@pytest.mark.case("L10N-007")
@pytest.mark.parametrize("fname", ["nosuch.xml", "english.xml"])
def test_l10n_007_an_unknown_language_file_leaves_the_interface_in_english(lang, fname):
    app = lang(fname)
    assert (app.menu("File|New")["File|New"] or {}).get("title") == "New"
    assert app.menu("Edit|Undo")["Edit|Undo"] is not None
    assert app.menu_item("IDM_FILE_NEW")["title"] == "New"
    fresh_doc(app, "")
    app.type("hello")
    assert app.text() == "hello" and "length: 5" in status(app)


# ---------------------------------------------------------------- what is translated

@pytest.mark.case("L10N-008")
@pytest.mark.parametrize("fname", ["russian.xml", "german.xml"])
def test_l10n_008_the_port_s_own_texts_are_translated_from_nativelang_extra(lang, tmp, fname):
    app = lang(None)
    english = by_action(main_tree(app, 3))
    app = lang(fname)
    translated = by_action(main_tree(app, 3))
    extra = extra_items(fname)
    bad = []
    for key, en in english.items():
        if en in extra and key in translated and translated[key] != extra[en]:
            bad.append((en, translated[key], extra[en]))
    assert not bad, bad[:20]
    if fname == "russian.xml":
        ins = app.call("e2e_menu", commands=["View|Переключить вставку/замену"])["items"]
        assert ins["View|Переключить вставку/замену"] is not None or \
            "Переключить вставку/замену" in {i["title"] for _, i in flat(main_tree(app, 2))}
        app.open(write(tmp, "a.txt", "a\n"))
        assert path_field(app)[1] == "Щёлкните, чтобы скопировать полный путь"


@pytest.mark.case("L10N-009")
def test_l10n_009_copied_feedback_in_the_interface_language(lang, tmp):
    app = lang("russian.xml")
    p = write(tmp, "a.txt", "a\n")
    app.open(p)
    app.mouse(**{"class": "NppStatusPathField"})
    assert app.same_path(app.clipboard(), p)
    assert path_field(app)[0] == f"✓ Скопировано: {app.clipboard()}"


@pytest.mark.case("L10N-010")
@pytest.mark.parametrize("fname", ["russian.xml", "german.xml", "finnish.xml"])
def test_l10n_010_the_status_bar_speaks_the_language(lang, fname):
    app = lang(fname)
    fresh_doc(app, "ab\ncd\nef", language="normal")
    first = status(app)
    app.select(1, 1, 2, 3)
    second = status(app)
    assert "length:" not in first
    assert "Unix (LF)" in first and "UTF-8" in first
    if fname == "russian.xml":
        assert "длина: 8" in first and "Стр: 3" in first and first.startswith("Обычный Текст")
        assert "Выд: 5 | 2" in second
    elif fname == "german.xml":
        assert "Länge: 8" in first
    else:
        assert "pituus: 8    rivejä: 3" in first


@pytest.mark.case("L10N-011")
def test_l10n_011_the_tab_and_editor_context_menus_are_translated(lang, tmp):
    app = lang(None)
    app.open(write(tmp, "a.txt", "a\n"))
    english_tab = [t for p, t in [(p, i["title"]) for p, i in flat(app.call("e2e_menu", context="tab")["tree"])]]
    app = lang("russian.xml")
    app.open(tmp / "a.txt")
    tab = app.call("e2e_menu", context="tab")["tree"]
    tab_titles_ = [i["title"] for _, i in flat(tab)]
    assert tab[0]["title"] == "Закрыть"
    assert "Закрыть все Кроме Текущей" in tab_titles_ and "Закрепить Вкладку" in tab_titles_
    left_english = [t for t in tab_titles_ if t in english_tab and not t.startswith(("Apply Color", "Copy"))]
    assert not left_english, left_english
    main = by_action(main_tree(app, 3))
    editor = app.call("e2e_menu", context="editor")["tree"]
    bad = [(i["title"], main[(i["action"], i.get("tag"))]) for _, i in flat(editor)
           if (i.get("action"), i.get("tag")) in main and i["title"] != main[(i["action"], i.get("tag"))]]
    assert not bad, bad


@pytest.mark.case("L10N-012")
def test_l10n_012_panel_titles_are_translated_docked_and_floating(lang):
    app = lang("russian.xml")
    for c in ("IDM_VIEW_FUNC_LIST", "IDM_VIEW_DOC_MAP", "IDM_VIEW_DOCLIST"):
        app.run(c)
    got = [dock(app, "titleOf:", p) for p in ("functionList", "documentMap", "documentList")]
    assert got == ["Список Функций", "Карта Документа", "Список Файлов"]
    dock(app, "movePanel:to:", "functionList", 4)
    assert app.wait(lambda: window_titled(app, "Список Функций"), timeout=5)
    dock(app, "movePanel:to:", "functionList", 1)


@pytest.mark.case("L10N-013")
def test_l10n_013_messages_are_shown_in_the_interface_language(lang, tmp):
    app = lang("russian.xml")
    app.open(write(tmp, "r.txt", "r\n"))
    app.type("x")
    app.answers(alerts=[2])
    app.run("IDM_FILE_RELOAD")
    reload_ = [e for e in app.modal_log() if e.get("kind") == "alert"]
    assert reload_ and "Are you sure" not in (reload_[0].get("informative") or "")
    assert reload_[0].get("buttons", ["Да"])[0] != "Yes"
    app.answers(alerts=[1])
    app.run("IDM_VIEW_SUMMARY")
    s = [e for e in app.modal_log() if e.get("kind") == "alert"][-1]
    root = ET.parse(NATIVE / "russian.xml").getroot()
    title = root.find(".//summary").get("value")
    assert s["message"] == title
    assert "Characters" not in (s.get("informative") or "")


@pytest.mark.case("L10N-014")
def test_l10n_014_shortcuts_keep_working_in_another_language(lang):
    app = lang("german.xml")
    keys = [app.menu_item(c).get("key") for c in ("IDM_VIEW_ZOOMIN", "IDM_SEARCH_FIND", "IDM_EDIT_SELECTALL")]
    assert keys == ["cmd++", "cmd+f", "cmd+a"]
    fresh_doc(app, "abc def")
    # Zoom In's own key (cmd++, read above); cmd+= is Edit > Calculate since 2026-09-23.
    app.keys("cmd++")
    assert app.sci(SCI_GETZOOM) == 1
    app.sci(SCI_SETZOOM, 0)
    app.keys("cmd+a")
    assert app.selection()["text"] == "abc def"
    app.keys("cmd+f")
    app.wait(lambda: next((w for w in app.windows() if not w["main_window"] and w["visible"]), None), timeout=5)


@pytest.mark.case("L10N-014")
def test_l10n_014_the_find_window_opened_by_its_key_has_a_translated_title(lang):
    app = lang("german.xml")
    fresh_doc(app, "abc")
    shown = lambda: next((w for w in app.windows() if not w["main_window"] and w["visible"]), None)
    for _ in range(2):   # opened, then Cmd+F again with the window already up (the tab is chosen anew)
        app.keys("cmd+f")
        w = app.wait(shown, timeout=5)
        app.idle(0.2)
        w = shown()
        assert w["title"] == "Suchen", w["title"]   # german.xml: <Find titleFind="Suchen" ...>


# ---------------------------------------------------------------- dialogs

def _open(app, command):
    before = {w["number"] for w in app.windows()}
    pending = None
    if command in ("IDM_SEARCH_GOTOLINE", "IDM_EDIT_COLUMNMODE"):
        app.answers(real_modals=True)
        pending = app.run_async(command)
    else:
        app.run(command)
    w = app.wait(lambda: next((w for w in app.windows() if w["number"] not in before and w["visible"]), None), timeout=5)
    return w, pending


def _close(app, w, pending):
    app.close_window(w["number"])
    if pending:
        pending.wait(10)
    app.answers(real_modals=False)


def _pref_pages(app, w):
    table = next(c for c in ui(app, w["number"])["controls"] if c["class"] == "NSTableView")
    return table


# Go To and Column Editor are app-modal alerts: _open runs them for real (real_modals + run_async) and
# the agent server keeps answering while they are up (AGENT-016).
MODAL_COMMANDS = ["IDM_SEARCH_GOTOLINE", "IDM_EDIT_COLUMNMODE"]
DIALOG_COMMANDS = ["IDM_SEARCH_FIND", "IDM_SETTING_PREFERENCE", "IDM_LANGSTYLE_CONFIG_DLG",
                   "IDM_SETTING_SHORTCUT_MAPPER"] + MODAL_COMMANDS


def _cut_everywhere(app, tmp, tag):
    problems = {}
    fresh_doc(app, "text\n")
    for command in DIALOG_COMMANDS:
        w, pending = _open(app, command)
        try:
            snap(app, tmp / f"{tag}-{command}.png", window=w["number"])
            if command == "IDM_SETTING_PREFERENCE":
                table = _pref_pages(app, w)
                for row in range(table["rows"]):
                    app.act(w["number"], "select", value=row, path=table["path"], send_action=True)
                    bad = _cut(app, w["number"])
                    if bad:
                        problems[f"{command} page {row}"] = bad
            else:
                bad = _cut(app, w["number"])
                if bad:
                    problems[command] = bad
        finally:
            _close(app, w, pending)
    return problems


@pytest.mark.case("L10N-015")
@pytest.mark.slow
@pytest.mark.parametrize("fname", ["german.xml", "finnish.xml", "hungarian.xml", "russian.xml", "french.xml",
                                   "japanese.xml", "chineseSimplified.xml"])
def test_l10n_015_nothing_is_cut_off_in_dialogs_in_long_word_and_cjk_languages(lang, tmp, fname):
    app = lang(fname)
    problems = _cut_everywhere(app, tmp, fname)
    assert not problems, problems


def _flatten(fname):
    """(element path, attribute) -> text, for the Dialog section."""
    root = ET.parse(NATIVE / fname).getroot()
    dialog = root.find("Dialog")
    out = {}

    def walk(el, path):
        key = path + "/" + el.tag + ("[" + el.get("id") + "]" if el.get("id") else "")
        for attr in ("name", "title", "value"):
            if el.get(attr):
                out[(key, attr)] = el.get(attr)
        for ch in el:
            walk(ch, key)
    if dialog is not None:
        walk(dialog, "")
    return out


def _translations(fname):
    en, tr = _flatten("english.xml"), _flatten(fname)
    table = {}
    for k, v in en.items():
        if k in tr and norm(tr[k]) and norm(tr[k]) != norm(v):
            table.setdefault(_key(v), norm(tr[k]))
    for e, t in extra_items(fname).items():
        table.setdefault(_key(e), norm(t))
    return table


def _key(s):
    s = norm(s)
    while s.endswith((":", "…", ".")):
        s = s[:-1].strip()
    return s.lower()


def _texts(app, number):
    return {c["path"]: (c.get("title") or c.get("value")) for c in ui(app, number)["controls"]
            if not c.get("editable") and (c.get("title") or c.get("value")) and c["class"] in ("NSButton", "NSTextField", "NSBox")}


@pytest.mark.case("L10N-016")
@pytest.mark.parametrize("fname", ["russian.xml", "german.xml"])
def test_l10n_016_no_english_left_where_the_translation_has_the_text(lang, fname):
    commands = ["IDM_SETTING_PREFERENCE", "IDM_SEARCH_FIND"] + MODAL_COMMANDS
    english = {}
    app = lang(None)
    for c in commands:
        w, pending = _open(app, c)
        try:
            english[c] = (w["title"], _texts(app, w["number"]))
        finally:
            _close(app, w, pending)
    app = lang(fname)
    table = _translations(fname)
    left = []
    for c in commands:
        w, pending = _open(app, c)
        try:
            shown = _texts(app, w["number"])
            wt, texts = english[c]
            if _key(wt) in table and w["title"] == wt:
                left.append((c, "window title", wt))
            for path, en in texts.items():
                if path in shown and shown[path] == en and _key(en) in table and table[_key(en)].lower() != _key(en):
                    left.append((c, en))
        finally:
            _close(app, w, pending)
    assert not left, left


@pytest.mark.case("L10N-017")
@pytest.mark.slow
@pytest.mark.parametrize("fname", ["arabic.xml", "hebrew.xml", "farsi.xml", "urdu.xml"])
def test_l10n_017_right_to_left_languages(lang, tmp, fname):
    app = lang(fname)
    native = native_commands(fname)
    ids = command_ids()
    view = [ids[c] for c in ids if c.startswith("IDM_VIEW_") and ids[c] in native][:20]
    items = app.call("e2e_menu", commands=view)["items"]
    wrong = [(i, items[str(i)]["title"], native[i]) for i in view
             if items.get(str(i)) and norm(items[str(i)]["title"]) != norm(native[i])]
    assert not wrong, wrong
    fresh_doc(app, "")
    text = "abc שלום مرحبا"
    app.type(text)
    assert app.text() == text
    assert "length:" not in status(app)
    img = snap(app, tmp / "rtl.png")
    w, h = img.size
    assert len(set(img.crop((int(w * 0.05), int(h * 0.05), int(w * 0.5), int(h * 0.15))).get_flattened_data())) > 3
    problems = {}
    for command in ("IDM_SEARCH_FIND", "IDM_SETTING_PREFERENCE"):
        win, pending = _open(app, command)
        try:
            snap(app, tmp / f"{command}.png", window=win["number"])
            bad = _cut(app, win["number"])
            if bad:
                problems[command] = bad
        finally:
            _close(app, win, pending)
    assert not problems, problems


@pytest.mark.case("L10N-018")
@pytest.mark.slow
def test_l10n_018_every_translation_loads_and_yields_a_usable_interface(lang):
    failures = []
    for f in sorted(NATIVE.glob("*.xml")):
        app = lang(f.name)
        tops = app.menu_tree("main", 0)
        new_title = app.menu_item("IDM_FILE_NEW")["title"]
        about = app.menu_tree("main", 1)[0]
        problems = []
        if any(not (t.get("title") or "").strip() for t in tops):
            problems.append("empty top menu")
        if not new_title.strip():
            problems.append("empty New")
        if about["title"] != "NotepadMac" or "NotepadMac" not in (about["items"][0]["title"] or ""):
            problems.append(f"app menu {about['title']!r} / {about['items'][0]['title']!r}")
        if not status(app):
            problems.append("no status")
        if problems:
            failures.append((f.name, problems))
    assert not failures, failures
