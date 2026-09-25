"""LANG: end-to-end tests (plan: plan/LANG.md)."""
import json
import os
import re
import shutil
import xml.etree.ElementTree as ET

import pytest

from harness.app import ToolError, wait_for
from harness.sci import *  # noqa: F401,F403
from _util_lang import (  # noqa: E402
    NON_LANGUAGE, PY_SCRIPT, SAMPLES, after_label, bgr, by_menu_id, close_udl_dialog, colourise, fold_headers,
    language_commands, langs_model, lexer_language, open_udl_dialog, resources, settings_dir, status,
    status_language, style_at, style_of, stylers_model, udl_check, udl_controls, udl_create, udl_file,
    udl_select, udl_selected, udl_set_field, udl_set_keywords, udl_tab, udl_window, udl_xml, wait_xml, write,
)


def light(app):
    """Light appearance: the theme is Default, i.e. stylers.model.xml."""
    app.set_prefs(appearanceMode=1)


def back_to_system(app):
    app.set_prefs(appearanceMode=0)


def tokens(app, **kw):
    return app.call("tokens", **kw)


def token_pairs(app):
    return [(t[2], t[3]) for t in tokens(app)["tokens"]]


def header_lines(app):
    return [f[0] for f in tokens(app, include_folds=True)["folds"] if f[2]]


def new_in(app, text, language):
    return app.new(text, language=language)


# ============================================================================ the menu

@pytest.mark.case("LANG-001")
def test_lang_001_the_language_menu_has_upstream_s_structure_and_titles(app):
    """LANG-001: The Language menu has upstream's structure and titles"""
    tree = app.menu_tree("Language", 3)
    assert tree[0]["title"] == "None (Normal Text)"
    assert tree[1].get("separator")
    i = 2
    letters, titles = [], ["None (Normal Text)"]
    while not tree[i].get("separator"):
        holder = tree[i]
        letters.append(holder["title"])
        names = [it["title"] for it in holder["items"] if not it.get("separator")]
        assert all(n[0].upper() == holder["title"] for n in names), (holder["title"], names)
        assert names == sorted(names, key=str.lower), names
        titles += names
        i += 1
    assert letters == sorted(letters) and letters[0] == "A" and letters[-1] == "Y", letters
    i += 1
    udl = tree[i]
    assert udl["title"] == "User Defined Language"
    assert [it["title"] for it in udl["items"]] == [
        "Define your language…", "Open User Defined Language folder…", "Notepad++ User Defined Languages Collection"]
    assert tree[i + 1].get("separator")
    user = [it["title"] for it in tree[i + 2:]]
    assert "Markdown (preinstalled)" in user and "Markdown (preinstalled dark mode)" in user
    labels = [label for cid, label in language_commands() if cid not in NON_LANGUAGE]
    for label in labels:
        assert titles.count(label) == 1, f"{label!r} appears {titles.count(label)} times"
    for internal in ("javascript", "javascript.js", "searchResult", "ext", "udf"):
        assert internal not in titles


@pytest.mark.case("LANG-002")
def test_lang_002_every_language_command_applies_its_language_and_a_working_le(app):
    """LANG-002: Every language command applies its language and a working lexer.

    IDM_LANG_JS is checked by LANG-009 (its internal mapping is the known JavaScript defect)."""
    table = by_menu_id()
    app.new("x\n")
    previous = "IDM_LANG_TEXT"
    wrong = []
    for cid, label in language_commands():
        if cid in NON_LANGUAGE or cid == "IDM_LANG_JS":
            continue
        name, lexer = table[cid]
        r = app.run(cid)
        assert r["ran"]
        d = app.doc()
        got_lexer = tokens(app)["lexer"]
        sci_lexer = lexer_language(app)
        # Lexilla's own spelling ("D" for d); PHP is the hypertext lexer, as upstream's setXmlLexer(L_PHP).
        want_sci = {lexer.lower()} | ({"", "null"} if lexer == "null" else set()) | ({"hypertext"} if name == "php" else set())
        sci_lexer = sci_lexer.lower()
        states = app.menu(cid, previous)
        problems = []
        if d["language"] != name:
            problems.append(f"language {d['language']}")
        if d["language_title"] != label:
            problems.append(f"title {d['language_title']}")
        if got_lexer != lexer:
            problems.append(f"lexer {got_lexer}")
        if sci_lexer not in want_sci:
            problems.append(f"SCI lexer {sci_lexer!r}")
        if not states[cid]["checked"]:
            problems.append("not checked")
        if previous != cid and states[previous]["checked"]:
            problems.append(f"{previous} still checked")
        if problems:
            wrong.append(f"{cid}: {', '.join(problems)}")
        previous = cid
    assert not wrong, "\n".join(wrong)


PROBES = {
    "html": '<a href="x">text</a>\n', "xml": '<root attr="1">text</root>\n',
    "asp": '<% Response.Write "hi" %>\n', "jsp": '<% out.print("hi"); %>\n',
    "php": '<?php\necho "hi";\n?>\n', "kix": "; comment\n$a = 1\n",
    "inno": "[Setup]\nAppName=Test\n", "yaml": "key: value\n# comment\n",
}


@pytest.mark.case("LANG-003")
def test_lang_003_every_language_colours_its_own_first_keyword(app):
    """LANG-003: Every language colours its own first keyword"""
    menu_of = {name: cid for cid, (name, lexer) in by_menu_id().items()}
    app.new("")
    unstyled, checked = [], 0
    for lang in langs_model(app).iter("Language"):
        name = lang.get("name")
        cid = menu_of.get(name)
        if not cid or cid in NON_LANGUAGE:
            continue
        kws = [k.text for k in lang.findall("Keywords") if (k.text or "").strip()]
        probe = PROBES.get(name) or (kws[0].split()[0] + "\n" if kws else None)
        if not probe:
            continue
        app.run(cid)
        app.set_text(probe)
        colourise(app)
        checked += 1
        n = len(probe.encode())
        if not any(style_at(app, p) != 0 for p in range(n)):
            unstyled.append(name)
    assert checked > 70
    assert not unstyled, f"unstyled: {unstyled}"


@pytest.mark.case("LANG-004")
def test_lang_004_styles_of_the_theme_are_applied_to_every_language_s_lexer(app):
    """LANG-004: Styles of the theme are applied to every language's lexer"""
    light(app)
    try:
        menu_of = {name: cid for cid, (name, lexer) in by_menu_id().items()}
        root = stylers_model(app)
        default = next(s for s in root.iter("WidgetStyle") if s.get("styleID") == "32") \
            if any(True for _ in root.iter("WidgetStyle") if _.get("styleID") == "32") else None
        app.new("x\n")
        wrong, compared = [], 0
        for lexer in root.find("LexerStyles"):
            name = lexer.get("name")
            cid = menu_of.get(name)
            if not cid or cid in NON_LANGUAGE:
                continue
            app.run(cid)
            for ws in lexer.findall("WordsStyle"):
                sid = int(ws.get("styleID"))
                fg, bg, fs = ws.get("fgColor"), ws.get("bgColor"), ws.get("fontStyle")
                if fg:
                    got = app.sci(SCI_STYLEGETFORE, sid)
                    compared += 1
                    if got != bgr(fg):
                        wrong.append(f"{name}/{ws.get('name')}({sid}) fore {got:06X} != {bgr(fg):06X}")
                if bg:
                    got = app.sci(SCI_STYLEGETBACK, sid)
                    if got != bgr(bg):
                        wrong.append(f"{name}/{ws.get('name')}({sid}) back {got:06X} != {bgr(bg):06X}")
                if fs not in (None, ""):
                    bits = int(fs)
                    if bool(app.sci(SCI_STYLEGETBOLD, sid)) != bool(bits & 1):
                        wrong.append(f"{name}/{ws.get('name')}({sid}) bold")
                    if bool(app.sci(SCI_STYLEGETITALIC, sid)) != bool(bits & 2):
                        wrong.append(f"{name}/{ws.get('name')}({sid}) italic")
        assert compared > 500
        assert not wrong, f"{len(wrong)} mismatches:\n" + "\n".join(wrong[:60])
        app.run("IDM_LANG_PYTHON")
        assert app.sci(SCI_STYLEGETFORE, 5) != app.sci(SCI_STYLEGETFORE, STYLE_DEFAULT)
        app.run("IDM_LANG_CPP")
        assert app.sci(SCI_STYLEGETFORE, 5) != app.sci(SCI_STYLEGETFORE, STYLE_DEFAULT)
    finally:
        back_to_system(app)


TOKEN_TABLE = [
    ("c", 'int main(void) { /* c */ return 42; } // x\nchar *s = "str";\n',
     [("TYPE WORD", "int"), ("COMMENT", "/* c */"), ("INSTRUCTION WORD", "return"), ("NUMBER", "42"), ("COMMENT LINE", "// x")]),
    ("cpp", 'class A { public: int f() { return 1; } }; // c\n', [("INSTRUCTION WORD", "return"), ("TYPE WORD", "int")]),
    ("cs", 'public class A { void F() { string s = "x"; return; } } // c\n',
     [("INSTRUCTION WORD", "public"), ("TYPE WORD", "class"), ("STRING", '"x"')]),
    ("java", 'public class A { int f() { return 1; } } // c\n', [("INSTRUCTION WORD", "return"), ("TYPE WORD", "int")]),
    ("typescript", 'function f(): number { return 42; } // c\n', [("TYPE WORD", "number"), ("INSTRUCTION WORD", "return")]),
    ("python", 'def f():\n    # c\n    return "s", 42\n',
     [("KEYWORDS", "def"), ("DEF NAME", "f"), ("COMMENT LINE", "# c"), ("STRING", '"s"'), ("NUMBER", "42")]),
    ("ruby", 'def f\n  # c\n  return "s", 42\nend\n', [("INSTRUCTION", "def"), ("DEF NAME", "f")]),
    ("perl", 'sub f { # c\n  return "s";\n}\n', [("STRING DOUBLEQUOTE", '"s"'), ("INSTRUCTION WORD", "return")]),
    ("php", '<?php\nfunction f() { // c\n  return "s";\n}\n?>\n', [("QUESTION MARK", "<?php"), ("WORD", "function")]),
    ("html", '<html><body class="a"><!-- c --></body></html>\n',
     [("ATTRIBUTE", "class"), ("DOUBLE STRING", '"a"'), ("COMMENT", "<!-- c -->")]),
    ("xml", '<?xml version="1.0"?>\n<root a="1"><!-- c --></root>\n', [("XMLSTART", "<?"), ("XMLEND", "?>")]),
    ("css", 'body { color: red; } /* c */\n', [("VALUE", " red"), ("COMMENT", "/* c */")]),
    ("sql", "SELECT a FROM t WHERE b = 'x'; -- c\n", [("KEYWORD", "SELECT"), ("STRING2", "'x'"), ("COMMENT LINE", "-- c")]),
    ("bash", 'if [ -f x ]; then echo "s"; fi # c\n', [("INSTRUCTION WORD", "if"), ("COMMENT LINE", "# c")]),
    ("batch", 'REM c\necho hello\nset X=1\n', [("COMMENT", "REM c"), ("KEYWORDS", "echo")]),
    ("lua", 'function f() return "s" end -- c\n', [("INSTRUCTION WORD", "return"), ("COMMENT LINE", "-- c")]),
    ("go", 'package main\nfunc f() int { return 42 } // c\n', [("INSTRUCTION WORD", "func")]),
    ("rust", 'fn f() -> i32 { return 42; } // c\n', [("KEYWORDS 1", "fn"), ("KEYWORDS 2", "i32"), ("LINE COMMENT", "// c")]),
    ("json", '{"a": "s", "b": 42, "c": true}\n',
     [("PROPERTY NAME", '"a"'), ("STRING", '"s"'), ("NUMBER", "42"), ("KEYWORD", "true")]),
    ("ini", '[section]\n; c\nkey=value\n', [("SECTION", "[section]"), ("COMMENT", "; c"), ("KEY", "key"), ("ASSIGNMENT", "=")]),
    ("makefile", '# c\nall:\n\techo hi\n', [("TARGET", "all")]),
    ("diff", '--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new\n',
     [("HEADER", "--- a"), ("POSITION", "@@ -1 +1 @@"), ("DELETED", "-old"), ("ADDED", "+new")]),
    ("pascal", "begin { c } writeln('s'); end.\n", [("INSTRUCTION WORD", "begin"), ("COMMENT", "{ c }")]),
    ("vb", 'Dim x As Integer \' c\nx = "s"\n', [("WORD", "Dim"), ("COMMENT", "' c")]),
    ("powershell", 'function F { # c\n  return "s" }\n', [("INSTRUCTION WORD", "return")]),
    ("tcl", 'proc f {} { return "s" } ;# c\n', [("TCL KEYWORD", "proc")]),
    ("lisp", '(defun f () "s") ; c\n', [("FUNCTION WORD", "defun")]),
    ("haskell", 'module Main where -- c\nmain = putStrLn "s"\n', [("KEYWORD", "module"), ("MODULE", "Main")]),
    ("fortran", 'program p ! c\n  print *, "s"\nend program p\n', [("INSTRUCTION WORD", "program"), ("COMMENT", "! c")]),
    ("asm", 'mov eax, 42 ; c\n', [("CPU INSTRUCTION", "mov"), ("REGISTER", "eax")]),
    ("toml", '[t] # c\na = "s"\nb = 42\n', [("TABLE", "[t]"), ("STRING DQ", '"s"')]),
    ("latex", '\\begin{document} % c\n\\end{document}\n', [("COMMAND", "\\begin"), ("TAG OPENING", "{document}")]),
    ("cmake", 'project(x) # c\nset(A "s")\n', [("COMMAND", "project")]),
    ("nsis", 'Section "s" ; c\nSectionEnd\n', [("SECTION", "Section")]),
    ("objc", '@interface A : NSObject // c\n@end\n', [("QUALIFIER", "@interface")]),
]


@pytest.mark.case("LANG-005")
def test_lang_005_keywords_comments_strings_and_numbers_get_their_own_styles_p(app):
    """LANG-005: Keywords, comments, strings and numbers get their own styles per language"""
    # The names are the theme's (Style Configurator's): the table is DarkModeDefault's, which names
    # some styles otherwise than the light Default ("WORD"/"KEYWORDS", "XMLSTART"/"XML START").
    before = app.prefs("appearanceMode", "darkThemeName")
    app.set_prefs(appearanceMode=2, darkThemeName="DarkModeDefault")
    try:
        _lang_005_tokens(app)
    finally:
        app.set_prefs(**{k: v for k, v in before.items()})


def _lang_005_tokens(app):
    wrong = []
    for lang, text, want in TOKEN_TABLE:
        new_in(app, text, lang)
        r = tokens(app)
        assert r["language"] == lang
        pairs = [(t[2], t[3]) for t in r["tokens"]]
        missing = [w for w in want if w not in pairs]
        if missing:
            wrong.append(f"{lang}: missing {missing} in {pairs[:14]}")
    assert not wrong, "\n".join(wrong)


@pytest.mark.case("LANG-006")
def test_lang_006_none_normal_text_takes_the_lexer_off(app):
    """LANG-006: None (Normal Text) takes the lexer off"""
    text = "def f(): return 1\n"
    new_in(app, text, "python")
    assert style_of(app, text, "def") != 0
    app.run("IDM_LANG_TEXT")
    d = app.doc()
    assert d["language"] == "normal" and d["language_title"] == "None (Normal Text)"
    assert lexer_language(app) in ("null", "")
    colourise(app)
    assert all(style_at(app, p) == 0 for p in range(len(text)))
    assert fold_headers(app, 2) == []
    st = app.menu("IDM_LANG_TEXT", "IDM_LANG_PYTHON")
    assert st["IDM_LANG_TEXT"]["checked"] and not st["IDM_LANG_PYTHON"]["checked"]
    app.run("IDM_FILE_NEW")
    assert app.doc()["language"] == "normal"
    assert app.checked("IDM_LANG_TEXT")


@pytest.mark.case("LANG-007")
def test_lang_007_the_check_mark_and_status_bar_follow_the_document_in_front(app):
    """LANG-007: The check mark and status bar follow the document in front"""
    a = app.new("a\n")["index"]
    app.run("IDM_LANG_PYTHON")
    b = app.new("b\n")["index"]
    app.run("IDM_LANG_CPP")
    c = app.new("c\n")["index"]
    cmds = ["IDM_LANG_PYTHON", "IDM_LANG_CPP", "IDM_LANG_TEXT"]
    for index, want, title in [(a, "IDM_LANG_PYTHON", "Python"), (b, "IDM_LANG_CPP", "C++"),
                               (c, "IDM_LANG_TEXT", "None (Normal Text)"), (a, "IDM_LANG_PYTHON", "Python")]:
        app.select(1, document=index)
        app.wait(lambda: app.doc()["index"] == index)
        states = app.menu(*cmds)
        assert [k for k in cmds if states[k]["checked"]] == [want]
        assert status(app).startswith(title + "    ")
    app.select(1, document=b)
    app.run("IDM_LANG_RUBY")
    langs = {d["index"]: d["language"] for d in app.docs()}
    assert langs[a] == "python" and langs[b] == "ruby" and langs[c] == "normal"


@pytest.mark.case("LANG-008")
def test_lang_008_the_status_bar_and_the_document_list_show_the_language_title(app):
    """LANG-008: The status bar and the document list show the language title"""
    rows = [("IDM_LANG_ASCII", "MS-DOS Style", "nfo"), ("IDM_LANG_CS", "C#", "cs"),
            ("IDM_LANG_FORTRAN_77", "Fortran (fixed form)", "fortran77"), ("IDM_LANG_INI", "INI file", "ini"),
            ("IDM_LANG_BASH", "Shell", "bash"), ("IDM_LANG_MSSQL", "Microsoft Transact-SQL", "mssql")]
    for cid, title, name in rows:
        index = app.new("x\n")["index"]
        app.run(cid)
        assert status_language(app) == title
        doc = next(d for d in app.docs() if d["index"] == index)
        assert doc["language_title"] == title and doc["language"] == name


@pytest.mark.case("LANG-009")
def test_lang_009_javascript_is_one_menu_entry_that_applies_javascript_js_know(app, tmp):
    """LANG-009: JavaScript is one menu entry that applies javascript.js (known defect)"""
    tree = app.menu_tree("Language", 3)
    j = next(h for h in tree if h.get("title") == "J")
    titles = [it["title"] for it in j["items"]]
    assert titles.count("JavaScript") == 1 and "javascript" not in titles and "javascript.js" not in titles
    p = write(tmp / "s.js", "function f() { return 1; }\n")
    app.open(p)
    assert app.doc()["language"] == "javascript.js"
    assert app.checked("IDM_LANG_JS")
    assert status_language(app) == "JavaScript"
    app.new("function g() { return 2; }\n")
    app.run("IDM_LANG_JS")
    assert app.doc()["language"] == "javascript.js"


@pytest.mark.case("LANG-010")
def test_lang_010_user_defined_applies_the_plain_user_defined_lexer_known_gap(app):
    """LANG-010: User-Defined applies the plain user-defined lexer (known gap)"""
    app.new("alpha 12\n")
    r = app.run("IDM_LANG_USER")
    assert r["ran"]
    assert tokens(app)["lexer"] == "user"
    assert status_language(app) != "None (Normal Text)"


@pytest.mark.case("LANG-011")
def test_lang_011_a_language_picked_by_hand_survives_save_as_under_another_nam(app, tmp):
    """LANG-011: A language picked by hand survives Save As under another name (known defect)"""
    app.new("hello\n")
    app.run("IDM_LANG_PYTHON")
    target = tmp / "t.txt"
    app.answers(panels=[str(target)])
    app.run("IDM_FILE_SAVEAS")
    app.wait(lambda: target.exists())
    app.wait(lambda: app.doc()["path"] is not None)
    second = tmp / "u.cpp"
    app.new("puts 1\n")
    app.run("IDM_LANG_RUBY")
    app.answers(panels=[str(second)])
    app.run("IDM_FILE_SAVEAS")
    app.wait(lambda: second.exists())
    langs = {os.path.basename(d["path"] or ""): d["language"] for d in app.docs()}
    assert langs["t.txt"] == "python"
    assert langs["u.cpp"] == "ruby"


@pytest.mark.case("LANG-012")
def test_lang_012_a_language_not_picked_by_hand_follows_the_new_name_on_save_a(app, tmp):
    """LANG-012: A language not picked by hand follows the new name on Save As and Rename"""
    app.new("x = 1\n")
    assert app.doc()["language"] == "normal"
    a = tmp / "a.py"
    app.answers(panels=[str(a)])
    app.run("IDM_FILE_SAVEAS")
    app.wait(lambda: a.exists() and app.doc()["language"] == "python")
    rb = tmp / "a.rb"
    app.answers(panels=[str(rb)])
    app.run("IDM_FILE_RENAME")
    app.wait(lambda: rb.exists())
    assert app.doc()["language"] == "ruby"
    lua = write(tmp / "b.txt", "x = 1\n")
    app.open(lua)
    app.run("IDM_LANG_LUA")
    bpy = tmp / "b.py"
    app.answers(panels=[str(bpy)])
    app.run("IDM_FILE_RENAME")
    app.wait(lambda: bpy.exists())
    assert app.doc()["language"] == "lua"


@pytest.mark.case("LANG-013")
@pytest.mark.restart
def test_lang_013_the_language_chosen_for_a_document_is_kept_by_the_session_ac(app, tmp):
    """LANG-013: The language chosen for a document is kept by the session across a restart"""
    p = write(tmp / "notes.txt", "print 1;\n")
    try:
        app.restart(session=True, defaults={"restoreSession": True})
        app.open(p)
        app.run("IDM_LANG_PERL")
        # Choosing a language does not modify the document, so Save is off (as upstream);
        # the session written at quit keeps the language all the same.
        app.restart(session=True)
        session = (settings_dir(app) / "session.xml").read_text()
        entry = [l for l in session.splitlines() if "notes.txt" in l]
        assert entry and re.search(r'lang="Perl"', entry[0]), entry
        app.wait(lambda: any(d["path"] and d["path"].endswith("notes.txt") for d in app.docs()), timeout=10)
        doc = next(d for d in app.docs() if d["path"] and d["path"].endswith("notes.txt"))
        app.select(1, document=doc["index"])
        assert app.doc()["language"] == "perl"
        assert app.checked("IDM_LANG_PERL")
    finally:
        app.start()


@pytest.mark.case("LANG-014")
@pytest.mark.restart
def test_lang_014_launch_options_l_and_udl_set_the_language_of_the_files_opene(app, tmp):
    """LANG-014: Launch options -l and -udl= set the language of the files opened"""
    a = write(tmp / "a.txt", "x = 1\n")
    b = write(tmp / "b.txt", "alpha\n")
    try:
        app.start(args=["-lpython", str(a)])
        # Launch-time work settles after the socket answers (AppKit opens the file first, CLI-009,
        # then the command line's -l applies): poll for the language, do not read it once.
        def opened(name):
            return next((d for d in app.docs() if d["path"] and d["path"].endswith(name)), None)
        app.wait(lambda: (opened("a.txt") or {}).get("language") == "python", timeout=5, message="a.txt as python")
        doc = opened("a.txt")
        app.select(1, document=doc["index"])
        assert app.checked("IDM_LANG_PYTHON")
        app.stop()
        write(settings_dir(app) / "userDefineLang.xml", udl_file("MyLang", "myl", "alpha beta"))
        app.start(clean_home=False, args=["-udl=MyLang", str(b)])
        app.wait(lambda: (opened("b.txt") or {}).get("language") == "MyLang", message="b.txt as MyLang")
        doc = opened("b.txt")
        app.select(1, document=doc["index"])
        assert status_language(app) == "MyLang"
    finally:
        app.start()


# ============================================================================ by file name

@pytest.mark.case("LANG-015")
def test_lang_015_every_extension_in_langs_model_xml_opens_in_its_language(app, tmp):
    """LANG-015: Every extension in langs.model.xml opens in its language"""
    owner = {}
    for lang in langs_model(app).iter("Language"):
        for e in (lang.get("ext") or "").split():
            owner[e.lower()] = lang.get("name")      # the later definition wins (.tex -> tex)
    wrong = []
    for ext, name in sorted(owner.items()):
        if ext in ("md", "markdown"):
            continue
        by_name = app.call("detect_language", text="x", filename=f"sample.{ext}")["by_filename"]
        p = write(tmp / ext / f"sample.{ext}", "x\n")
        info = app.open(p)
        got = app.doc()["language"]
        app.call("close_document", document=info["index"], discard_changes=True)
        if got != name or by_name != name:
            wrong.append(f".{ext}: opened {got}, by_filename {by_name}, want {name}")
    assert owner["tex"] == "tex"
    assert not wrong, "\n".join(wrong)


@pytest.mark.case("LANG-016")
def test_lang_016_extensions_are_matched_without_regard_to_case(app, tmp):
    """LANG-016: Extensions are matched without regard to case"""
    for name, want in [("A.PY", "python"), ("B.Cpp", "cpp"), ("C.HTML", "html")]:
        app.open(write(tmp / name, "x\n"))
        assert app.doc()["language"] == want, name


@pytest.mark.case("LANG-017")
def test_lang_017_files_known_by_their_whole_name_get_upstream_s_language(app, tmp):
    """LANG-017: Files known by their whole name get upstream's language"""
    want = {"Makefile": "makefile", "GNUmakefile": "makefile", "CMakeLists.txt": "cmake", "SConstruct": "python",
            "SConscript": "python", "wscript": "python", "Rakefile": "ruby", "Vagrantfile": "ruby",
            "crontab": "bash", "PKGBUILD": "bash", "APKBUILD": "bash", "makefile": "makefile", "rakefile": "ruby"}
    wrong = []
    for name, lang in want.items():
        by_name = app.call("detect_language", text="x", filename=name)["by_filename"]
        app.open(write(tmp / name.lower() / name, "x\n"))
        got = app.doc()["language"]
        if got != lang or by_name != lang:
            wrong.append(f"{name}: opened {got}, by_filename {by_name}, want {lang}")
    assert not wrong, "\n".join(wrong)


@pytest.mark.case("LANG-018")
def test_lang_018_a_user_language_s_extension_comes_before_a_built_in_one(fresh_app, tmp):
    """LANG-018: A user language's extension comes before a built-in one"""
    app = fresh_app
    w = udl_create(app, "PyLike")
    udl_set_field(app, w, None, "Ext.:", "py")
    wait_xml(app, r'name="PyLike" ext="py"')
    app.open(write(tmp / "a.py", "x = 1\n"))
    assert app.doc()["language"] == "PyLike"
    udl_select(app, w, "PyLike")
    app.answers(alerts=["Yes"])
    app.click(w, "Remove")
    app.wait(lambda: "PyLike" not in udl_xml(app))
    app.open(write(tmp / "b.py", "x = 1\n"))
    assert app.doc()["language"] == "python"


# ============================================================================ from contents

def open_bare(app, tmp, name, text, answer=None):
    """Opens `text` as an extension-less file; answers a choice sheet if one comes."""
    app.answers(clear=True, alerts=[answer] if answer else None)
    p = write(tmp / f"d{len(list(tmp.iterdir()))}" / name, text)
    info = app.open(p)
    app.idle(0.05)
    return app.doc()


@pytest.mark.case("LANG-019")
def test_lang_019_a_shebang_line_settles_the_language_of_a_file_without_extens(app, tmp):
    """LANG-019: A shebang line settles the language of a file without extension"""
    rows = [("#!/usr/bin/env python3", "python"), ("#!/usr/bin/python3.11", "python"),
            ("#!/usr/bin/env -S python3 -u", "python"), ("#!/bin/sh", "bash"), ("#!/bin/bash", "bash"),
            ("#!/bin/zsh", "bash"), ("#!/usr/bin/perl", "perl"), ("#!/usr/bin/env ruby", "ruby"),
            ("#!/usr/bin/env node", "javascript"), ("#!/usr/bin/lua", "lua"), ("#!/usr/bin/tclsh", "tcl"),
            ("#!/usr/bin/env Rscript", "r"), ("#!/usr/bin/env pwsh", "powershell"), ("#!/usr/bin/php", "php")]
    wrong = []
    for line, lang in rows:
        text = line + "\nx = 1\n"
        r = app.call("detect_language", text=text)
        d = open_bare(app, tmp, "script", text)
        if d["language"] != lang or r["declared"] != lang or r["offered"] != [lang]:
            wrong.append(f"{line}: opened {d['language']}, declared {r['declared']}, offered {r['offered']}")
    assert not wrong, "\n".join(wrong)
    assert not [e for e in app.modal_log() if e.get("kind") == "alert"]


@pytest.mark.case("LANG-020")
def test_lang_020_opening_tags_and_doctypes_declare_xml_php_and_html(app, tmp):
    """LANG-020: Opening tags and doctypes declare XML, PHP and HTML"""
    for text, lang in [('<?xml version="1.0"?><a/>', "xml"), ("  <?php echo 1; ?>", "php"),
                       ("<!DOCTYPE html><html></html>", "html"), ("<html><body>x</body></html>", "html")]:
        assert app.call("detect_language", text=text)["declared"] == lang
        assert open_bare(app, tmp, "page", text)["language"] == lang, text


@pytest.mark.case("LANG-021")
def test_lang_021_emacs_and_vim_modelines_declare_the_language(app, tmp):
    """LANG-021: Emacs and vim modelines declare the language"""
    filler = "".join(f"value {i}\n" for i in range(19))
    rows = [("# -*- mode: ruby -*-\nx = 1\n", "ruby"), ("-- vim: set ft=lua:\nx = 1\n", "lua"),
            ("// -*- c++ -*-\nint x;\n", "cpp"), (filler + "# vim: filetype=sh\n", "bash"),
            ("key: 1\n# vim: syntax=yml\n", "yaml")]
    for text, lang in rows:
        assert app.call("detect_language", text=text)["declared"] == lang, text
        assert open_bare(app, tmp, "conf", text)["language"] == lang, text
    lines = [f"value {i}" for i in range(20)]
    lines[9] = "# vim: ft=ruby"
    assert app.call("detect_language", text="\n".join(lines) + "\n")["declared"] is None


@pytest.mark.case("LANG-022")
def test_lang_022_json_is_recognised_only_when_it_parses(app, tmp):
    """LANG-022: JSON is recognised only when it parses"""
    for text in ['{"a": [1, 2, 3]}', '[{"k": true}]']:
        assert app.call("detect_language", text=text)["declared"] == "json"
        assert open_bare(app, tmp, "data", text)["language"] == "json"
    assert app.call("detect_language", text="{ not json at all")["declared"] != "json"
    assert open_bare(app, tmp, "data", "{ not json at all")["language"] != "json"


@pytest.mark.case("LANG-023")
def test_lang_023_too_little_text_is_left_as_normal_text(app, tmp):
    """LANG-023: Too little text is left as Normal Text"""
    for text in ["", "hello\n", "one two three four\n", "...\n...\n"]:
        assert app.call("detect_language", text=text)["offered"] == []
        assert open_bare(app, tmp, "note", text)["language"] == "normal"
    assert not [e for e in app.modal_log() if e.get("kind") == "alert"]


@pytest.mark.case("LANG-024")
def test_lang_024_the_trained_model_names_the_language_of_each_written_sample(app, tmp):
    """LANG-024: The trained model names the language of each written sample"""
    files = sorted((lang.name, f) for lang in SAMPLES.iterdir() if lang.is_dir() for f in lang.iterdir())
    # The samples in the repository (56 when this was written; the plan counted 58).
    assert len(files) >= 56
    # Known misses, by name, so that any other miss fails: the plan's (jsp pages that begin with <html
    # are declared html; gui4cli/filelist.gui is below the offering level) and the model's JSON5 one,
    # tracked by test_lang_024_the_first_choice_for_each_sample_is_its_language.
    known = {"gui4cli/filelist.gui", "jsp/error.jsp", "jsp/index.jsp", "json5/settings.jsonc"}
    first_wrong, not_offered, not_opened = [], [], []
    for lang, f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        r = app.call("detect_language", text=text)
        if not r["guesses"] or r["guesses"][0]["language"] != lang:
            first_wrong.append(f"{lang}/{f.name}: {r['guesses'][:2]}")
        if lang not in r["offered"]:
            not_offered.append(f"{lang}/{f.name}: {r['offered']}")
        d = open_bare(app, tmp, f.stem, text, answer="Use this one")
        if d["language"] != lang:
            not_opened.append(f"{lang}/{f.name}: {d['language']}")
        app.call("close_document", document=d["index"], discard_changes=True)
    # The first choice for every sample is test_lang_024_the_first_choice_...: a known model miss.
    assert {m.split(":")[0] for m in not_offered} <= known, not_offered
    assert {m.split(":")[0] for m in not_opened} <= known, not_opened


@pytest.mark.case("LANG-024")
def test_lang_024_the_first_choice_for_each_sample_is_its_language(app):
    """LANG-024 (first choice): guesses[0] is the sample's own language for every written sample"""
    files = sorted((lang.name, f) for lang in SAMPLES.iterdir() if lang.is_dir() for f in lang.iterdir())
    wrong = []
    for lang, f in files:
        r = app.call("detect_language", text=f.read_text(encoding="utf-8", errors="replace"))
        if not r["guesses"] or r["guesses"][0]["language"] != lang:
            wrong.append(f"{lang}/{f.name}: {r['guesses'][:2]}")
    assert not wrong, wrong


@pytest.mark.case("LANG-025")
def test_lang_025_the_upstream_function_list_corpus_is_recognised_from_its_con(app):
    """LANG-025: The upstream function-list corpus is recognised from its contents"""
    corpus = resources(app) / "functionListCorpus"
    total = offered = first = 0
    longest, missed = 0, []
    for folder in sorted(corpus.iterdir()):
        unit = folder / "unitTest"
        if not unit.exists():
            continue
        want = folder.name[4:] if folder.name.startswith("udl-") else folder.name
        r = app.call("detect_language", text=unit.read_text(encoding="utf-8", errors="replace"))
        names = r["offered"]
        longest = max(longest, len(names))
        total += 1
        ok = [n for n in names if n == want or (want.startswith("javascript") and n.startswith("javascript"))]
        if not ok:
            missed.append(want)
            continue
        offered += 1
        if names.index(ok[0]) == 0:
            first += 1
    assert total >= 40
    assert offered >= 36, missed
    assert first >= 35
    assert longest <= 10


@pytest.mark.case("LANG-026")
def test_lang_026_when_several_languages_fit_the_user_is_asked_and_the_answer(app, tmp):
    """LANG-026: When several languages fit, the user is asked and the answer applies"""
    text = (SAMPLES / "fortran77" / "sort.f77").read_text()
    assert app.call("detect_language", text=text)["offered"][:2] == ["fortran77", "fortran"]
    app.modal_log()
    open_bare(app, tmp, "roots", text, answer="Use this one")
    app.wait(lambda: app.doc()["language"] == "fortran77")
    log = [e for e in app.modal_log() if e.get("kind") == "alert"]
    assert log and log[0]["message"] == "Which language is this?"
    assert log[0]["buttons"] == ["Use this one", "Leave as text"]
    d = open_bare(app, tmp, "roots2", text, answer="Leave as text")
    app.wait(lambda: any(e.get("kind") == "alert" for e in app.modal_log(clear=False)))
    app.idle(0.2)
    assert app.doc()["language"] == "normal"


@pytest.mark.case("LANG-027")
def test_lang_027_pasting_into_an_empty_document_works_out_its_language_pastin(app):
    """LANG-027: Pasting into an empty document works out its language; pasting into text does not"""
    app.clipboard(set=PY_SCRIPT)
    app.new("")
    app.run("IDM_EDIT_PASTE")
    app.wait(lambda: app.doc()["language"] == "python")
    assert "def read_config" in app.text()
    app.new("notes\n")
    app.select(2, 1)
    app.run("IDM_EDIT_PASTE")
    app.wait(lambda: "def read_config" in app.text())
    assert app.doc()["language"] == "normal"


@pytest.mark.case("LANG-028")
def test_lang_028_detection_only_where_the_name_says_nothing_and_the_user_has(app, tmp):
    """LANG-028: Detection only where the name says nothing and the user has not chosen"""
    app.open(write(tmp / "script.txt", PY_SCRIPT))
    assert app.doc()["language"] == "normal"
    app.clipboard(set=PY_SCRIPT)
    app.new("")
    app.run("IDM_LANG_CPP")
    app.run("IDM_EDIT_PASTE")
    app.wait(lambda: "def read_config" in app.text())
    assert app.doc()["language"] == "cpp"
    app.set_prefs(detectLanguageFromContent=False)
    try:
        app.open(write(tmp / "a" / "script", PY_SCRIPT))
        assert app.doc()["language"] == "normal"
    finally:
        app.set_prefs(detectLanguageFromContent=True)
    app.open(write(tmp / "b" / "script2", PY_SCRIPT))
    assert app.doc()["language"] == "python"


CSHARP_TOP_LEVEL = (
    "using System.Net.Http.Headers;\nusing System.Security.Cryptography;\nusing System.Text.Json;\n\n"
    "var builder = WebApplication.CreateBuilder(args);\n"
    "builder.Services.AddHttpClient(\"proxy\", c => c.Timeout = TimeSpan.FromMinutes(10));\n"
    "builder.Logging.SetMinimumLevel(LogLevel.Warning);\n\n"
    "var (cert, _) = await SetupCertificateAsync();\nvar app = builder.Build();\n\n"
    "var nugetOrg = \"https://api.nuget.org/v3\";\nConsole.WriteLine(\"NuGet Aggregating Proxy\");\n"
    "Console.Write(\"\\nNexus Username: \");\nvar username = Console.ReadLine()!;\n\n"
    "var factory = app.Services.GetRequiredService<IHttpClientFactory>();\n"
    "foreach (var src in nexusSources)\n{\n    var client = CreateAuthClient(factory, creds);\n"
    "    var r = await client.GetAsync($\"{src}/index.json\");\n"
    "    Console.WriteLine($\"  {(r.IsSuccessStatusCode ? \"ok\" : \"no\")} {src}\");\n}\n\n"
    "app.MapGet(\"/v3/search\", async (string? q, int? skip, IHttpClientFactory f) =>\n{\n"
    "    var results = new List<JsonElement>();\n    foreach (var src in nexusSources)\n    {\n"
    "        var content = await TryGetNexus(f, creds, $\"{src}/v3/search?q={Uri.EscapeDataString(q ?? \"\")}\");\n"
    "        if (content != null)\n        {\n            try\n            {\n"
    "                var json = JsonDocument.Parse(content);\n"
    "                if (json.RootElement.TryGetProperty(\"data\", out var data))\n"
    "                    foreach (var item in data.EnumerateArray())\n                        results.Add(item);\n"
    "            }\n            catch { }\n        }\n    }\n"
    "    return Results.Json(new { totalHits = results.Count, data = results });\n});\n\n"
    "static async Task<string?> TryGetNexus(IHttpClientFactory f, CredentialStore c, string url)\n{\n"
    "    try\n    {\n        var client = CreateAuthClient(f, c);\n        var r = await client.GetAsync(url);\n"
    "        if (r.IsSuccessStatusCode)\n            return await r.Content.ReadAsStringAsync();\n    }\n"
    "    catch { }\n    return null;\n}\n\n"
    "class CredentialStore\n{\n    char[] _p;\n    public string Username { get; private set; }\n"
    "    public string Password => new(_p);\n"
    "    public CredentialStore(string u, string p) { Username = u; _p = p.ToCharArray(); }\n"
    "    public void Clear() { Array.Clear(_p); Username = \"\"; }\n}\n\n"
)
SQL_QUERY = ("SELECT u.id, u.name, count(o.id) AS orders\nFROM users u\nLEFT JOIN orders o ON o.user_id = u.id\n"
             "WHERE u.active = 1\nGROUP BY u.id, u.name\nORDER BY orders DESC;\n")
RUBY_SNIPPET = ("require 'json'\n\nclass Loader\n  def initialize(path)\n    @path = path\n  end\n\n  def load\n"
                "    JSON.parse(File.read(@path))\n  end\nend\n")


@pytest.mark.case("LANG-029")
def test_lang_029_an_agent_s_new_document_is_detected_and_c_without_a_class_is(app):
    """LANG-029: An agent's new document is detected, and C# without a class is C#"""
    for text, lang in [(CSHARP_TOP_LEVEL, "cs"), (SQL_QUERY, "sql"), (RUBY_SNIPPET, "ruby")]:
        app.answers(clear=True, alerts=["Use this one"])
        app.new(text)
        app.wait(lambda: app.doc()["language"] == lang, message=lang)
    guesses = app.call("detect_language", text=CSHARP_TOP_LEVEL)
    assert guesses["offered"][0] == "cs"


# ============================================================================ lexers and folding

HTML_PAGE = ('<html>\n<body>\n<div class="a">\n  <p>one</p>\n  <p>two</p>\n</div>\n<!-- a comment\n     of two lines -->\n'
             '<script>\nfunction f() {\n  return 1;\n}\n</script>\n</body>\n</html>\n')
XML_DOC = '<?xml version="1.0"?>\n<root>\n  <item>\n    <name>a</name>\n  </item>\n</root>\n'
PHP_PAGE = "<html>\n<body>\n<?php\nfunction f() {\n  return 1;\n}\n?>\n</body>\n</html>\n"

FOLDS_EXACT = [
    ("python", "def f():\n    return 1\n\nx = 2\n", [1]),
    ("cpp", "int f() {\n  return 1;\n}\n", [1]),
    ("java", "class A {\n  void f() {\n  }\n}\n", [1, 2]),
    ("lua", "function f()\n  return 1\nend\n", [1]),
    ("yaml", "a:\n  b: 1\n  c: 2\n", [1]),
    ("json", '{\n "a": [\n  1\n ]\n}\n', [1, 2]),
    ("css", "a {\n  color: red;\n}\n", [1]),
    ("bash", "if true; then\n  echo 1\nfi\n", [1]),
    ("ruby", "def f\n  1\nend\n", [1]),
    ("ini", "[a]\nk=1\n[b]\nk=2\n", [1, 3]),
    ("pascal", "begin\n  x := 1;\nend.\n", [1]),
    ("sql", "BEGIN\n  SELECT 1;\nEND;\n", [1]),
    ("perl", "sub f {\n  1;\n}\n", [1]),
]


@pytest.mark.case("LANG-030")
def test_lang_030_each_lexer_folds_where_its_language_folds(app):
    """LANG-030: Each lexer folds where its language folds"""
    wrong = []
    for lang, text, want in FOLDS_EXACT:
        new_in(app, text, lang)
        got = header_lines(app)
        if got != want:
            wrong.append(f"{lang}: {got} != {want}")
    for lang, text, must in [("xml", XML_DOC, [2, 3]), ("html", HTML_PAGE, [1, 2, 3, 7, 10]), ("php", PHP_PAGE, [1, 4])]:
        new_in(app, text, lang)
        got = header_lines(app)
        if not set(must) <= set(got):
            wrong.append(f"{lang}: {got} lacks {must}")
    assert not wrong, "\n".join(wrong)


@pytest.mark.case("LANG-031")
def test_lang_031_a_fold_closes_and_opens_its_lines_and_a_language_change_keep(app):
    """LANG-031: A fold closes and opens its lines, and a language change keeps what was folded"""
    new_in(app, "int f(void) {\n    return 1;\n}\nint g;\n", "c")
    colourise(app)
    app.sci(SCI_TOGGLEFOLD, 0)
    assert [app.sci(SCI_GETLINEVISIBLE, n) for n in range(4)] == [1, 0, 0, 1]
    assert app.sci(SCI_GETFOLDEXPANDED, 0) == 0
    app.run("IDM_LANG_CPP")
    assert [app.sci(SCI_GETLINEVISIBLE, n) for n in range(4)] == [1, 0, 0, 1]
    app.sci(SCI_TOGGLEFOLD, 0)
    assert [app.sci(SCI_GETLINEVISIBLE, n) for n in range(4)] == [1, 1, 1, 1]
    assert app.sci(SCI_GETFOLDEXPANDED, 0) == 1


C_SOURCE = ("/** a comment\n *  @param x of three\n *  lines */\n#if DEBUG\nint f(void) {\n    return 1;\n}\n#endif\n"
            "#if 0\nint g(void) { return 2; }\n#endif\n")


@pytest.mark.case("LANG-032")
def test_lang_032_the_c_family_gets_comment_and_preprocessor_folding_and_its_w(app):
    """LANG-032: The C family gets comment and preprocessor folding and its word lists in the right slots"""
    new_in(app, C_SOURCE, "c")
    heads = fold_headers(app, C_SOURCE.count("\n"))
    assert {1, 4, 5} <= set(heads), heads
    assert style_of(app, C_SOURCE, "return 1") == SCE_C_WORD
    assert style_of(app, C_SOURCE, "int f") == SCE_C_WORD2
    assert style_of(app, C_SOURCE, "@param", 1) == SCE_C_COMMENTDOCKEYWORD
    assert style_of(app, C_SOURCE, "int g") == SCE_C_WORD2


MIXED_PAGE = ("<html>\n<script>\nvar x = function () { return 1; };\n</script>\n<?php\nforeach ($a as $b) { echo $b; }\n"
              "?>\n</html>\n")


@pytest.mark.case("LANG-033")
def test_lang_033_a_php_page_styles_html_embedded_javascript_and_php_each_in_i(app):
    """LANG-033: A PHP page styles HTML, embedded JavaScript and PHP each in its own language's styles"""
    light(app)
    try:
        new_in(app, MIXED_PAGE, "php")
        colourise(app)
        assert style_at(app, 1) == SCE_H_TAG
        assert style_of(app, MIXED_PAGE, "function") == SCE_HJ_KEYWORD
        assert style_of(app, MIXED_PAGE, "foreach") == SCE_HPHP_WORD
        root = stylers_model(app)

        def fg(lexer, sid):
            lt = next(l for l in root.find("LexerStyles") if l.get("name") == lexer)
            return bgr(next(w for w in lt.findall("WordsStyle") if w.get("styleID") == str(sid)).get("fgColor"))
        assert app.sci(SCI_STYLEGETFORE, SCE_H_TAG) == fg("html", SCE_H_TAG)
        assert app.sci(SCI_STYLEGETFORE, SCE_HJ_KEYWORD) == fg("javascript", SCE_HJ_KEYWORD)
        assert app.sci(SCI_STYLEGETFORE, SCE_HPHP_WORD) == fg("php", SCE_HPHP_WORD)
        assert app.sci(SCI_STYLEGETFORE, SCE_HPHP_WORD) != app.sci(SCI_STYLEGETFORE, STYLE_DEFAULT)
        for lang, text, needle in [("asp", '<% Response.Write "hi" %>\n', "Response"),
                                   ("jsp", '<% out.print("hi"); %>\n', "out")]:
            new_in(app, text, lang)
            colourise(app)
            assert style_of(app, text, needle) != 0, lang
    finally:
        back_to_system(app)


@pytest.mark.case("LANG-034")
def test_lang_034_backquoted_strings_in_go_javascript_and_typescript_span_line(app):
    """LANG-034: Backquoted strings in Go, JavaScript and TypeScript span lines"""
    for lang, text, needles in [("go", "package main\n\nvar s = `raw\nstring`\n", ["raw", "string`"]),
                                ("javascript.js", "const s = `a ${b}\nc`;\n", ["a $", "c`"]),
                                ("typescript", "const s: string = `raw\ntext`;\n", ["raw", "text"])]:
        new_in(app, text, lang)
        colourise(app)
        for n in needles:
            assert style_of(app, text, n) == SCE_C_STRINGRAW, (lang, n)


@pytest.mark.case("LANG-035")
def test_lang_035_json_escapes_and_json5_comments(app):
    """LANG-035: JSON escapes and JSON5 comments"""
    text = '{"a": "x\\ny"}\n'
    new_in(app, text, "json")
    colourise(app)
    assert style_of(app, text, "\\n") == SCE_JSON_ESCAPESEQUENCE
    text5 = "{\n  // a comment\n  a: 1\n}\n"
    new_in(app, text5, "json5")
    colourise(app)
    assert style_of(app, text5, "// a", 3) == SCE_JSON_LINECOMMENT


# ============================================================================ function list

@pytest.mark.case("LANG-036")
def test_lang_036_function_list_parsers_give_notepad_s_expected_results_on_its(app):
    """LANG-036: Function List parsers give Notepad++'s expected results on its own corpus"""
    corpus = resources(app) / "functionListCorpus"
    checked, failures = 0, []
    for folder in sorted(corpus.iterdir()):
        if folder.name in ("javascript", "typescript") or folder.name.startswith("udl-"):
            continue
        unit, exp = folder / "unitTest", folder / "unitTest.expected.result"
        if not unit.exists() or not exp.exists():
            continue
        expected = json.loads(exp.read_text(encoding="utf-8"))
        r = app.call("function_list", text=unit.read_text(encoding="utf-8"), language=folder.name)
        assert r["parser"], folder.name
        checked += 1
        leaves, nodes, order = [], {}, []
        for e in r["entries"]:
            if e["container"]:
                if e["container"] not in nodes:
                    nodes[e["container"]] = []
                    order.append(e["container"])
                nodes[e["container"]].append(e["name"])
            else:
                leaves.append(e["name"])
        classes = {n.strip() for n in order}
        plain = [l for l in leaves if l.strip() not in classes]
        ok = plain == expected.get("leaves", []) and len(expected.get("nodes", [])) == len(order) and all(
            nodes.get(n["name"]) == n.get("leaves", []) for n in expected.get("nodes", []))
        if not ok:
            failures.append(folder.name)
    assert checked >= 38
    assert checked - len(failures) >= 35, failures


BATTERY = [
    ("c", "c", "int add(int a, int b)\n{\n    return 0;\n}\n", "add(int a, int b)"),
    ("cpp", "cpp", "class Thing {\npublic:\n    void run() {}\n};\n", "Thing::run"),
    ("cs", "cs", "class Store\n{\n    public void Clear() { }\n}\n", "Store::Clear"),
    ("java", "java", "public class G {\n  public void hello(String w) { }\n}\n", "G::hello"),
    ("php", "php", "<?php\nfunction helper($x) { return $x; }\n", "helper($x) "),
    ("python", "py", "def alpha(x):\n    pass\n", "alpha(x)"),
    ("ruby", "rb", "def alpha(x)\n  x\nend\n", "alpha"),
    ("perl", "pl", "sub alpha {\n  1;\n}\n", "alpha"),
    ("lua", "lua", "function alpha(x)\n  return x\nend\n", "alpha"),
    ("bash", "sh", "alpha() {\n  echo hi\n}\n", "alpha"),
    ("pascal", "pas", "procedure Alpha(x: Integer);\nbegin\nend;\n", "Alpha"),
    ("vb", "vb", "Public Sub Alpha(x As Integer)\nEnd Sub\n", "Alpha"),
    ("rust", "rs", "fn alpha(x: i32) -> i32 {\n    x\n}\n", "alpha"),
    ("javascript.js", "js", "function alpha(x) { return x; }\n", "alpha"),
    ("typescript", "ts", "function alpha(x) {\n  return x;\n}\n", "alpha"),
    ("powershell", "ps1", "function Get-Thing {\n    param($x)\n}\n", "Get-Thing"),
    ("haskell", "hs", "alpha :: Int -> Int\nalpha x = x\n", "alpha"),
    ("nim", "nim", "proc alpha(x: int): int =\n  x\n", "alpha(x: int): int"),
    ("css", "css", ".alpha { color: red; }\n", ".alpha "),
    ("makefile", "mak", "alpha:\n\techo hi\n", "alpha"),
    ("batch", "bat", ":alpha\necho hi\n", "alpha"),
    ("ini", "ini", "[Section]\nkey=1\n", "Section"),
    ("fortran", "f90", "      SUBROUTINE ALPHA(X)\n      END\n", "ALPHA"),
    ("d", "d", "int add(int a, int b)\n{\n    return 0;\n}\n", "add"),
    ("sql", "sql", "CREATE OR REPLACE PROCEDURE alpha IS\nBEGIN\nNULL;\nEND alpha;\n", "PROCEDURE alpha"),
    ("rust", "rs", "pub fn alpha(x: i32) -> i32 { x }\n", "alpha"),
    ("rust", "rs", "impl Thing {\n    pub fn delta(&self) {}\n}\n", "Thing::delta"),
    ("javascript.js", "js", "const beta = (x) => x;\n", "beta"),
]


@pytest.mark.case("LANG-037")
def test_lang_037_the_function_list_finds_each_language_s_declarations_in_an_o(app, tmp):
    """LANG-037: The Function List finds each language's declarations in an open document"""
    missing = []
    for i, (lang, ext, text, want) in enumerate(BATTERY):
        info = app.open(write(tmp / str(i) / f"f.{ext}", text))
        r = app.call("function_list", document=info["index"])
        shown = [f"{e['container']}::{e['name']}" if e["container"] else e["name"] for e in r["entries"]]
        if want not in shown or r["language"] != lang:
            missing.append(f"{lang}: wanted {want!r}, got {shown} ({r['language']})")
        app.call("close_document", document=info["index"], discard_changes=True)
    assert not missing, "\n".join(missing)


def panel_texts(app):
    """The names the Function List panel shows (its rows; e2e_ui on the main window does not answer)."""
    return " | ".join(app.get("app", "funcList.functionNames") or [])


@pytest.mark.case("LANG-038")
def test_lang_038_the_function_list_panel_follows_the_language_of_the_document(app):
    """LANG-038: The Function List panel follows the language of the document"""
    new_in(app, "def alpha(x):\n    pass\n\ndef beta():\n    pass\n", "python")
    shown_before = app.checked("IDM_VIEW_FUNC_LIST")
    if not shown_before:
        app.run("IDM_VIEW_FUNC_LIST")
    try:
        app.wait(lambda: "alpha(x)" in panel_texts(app) and "beta()" in panel_texts(app), message="panel rows")
        t = panel_texts(app)
        assert t.index("alpha(x)") < t.index("beta()")
        app.run("IDM_LANG_TEXT")
        app.wait(lambda: "alpha(x)" not in panel_texts(app), message="panel emptied")
        app.run("IDM_LANG_PYTHON")
        app.wait(lambda: "alpha(x)" in panel_texts(app), message="panel refilled")
    finally:
        if not shown_before and app.checked("IDM_VIEW_FUNC_LIST"):
            app.run("IDM_VIEW_FUNC_LIST")


# ============================================================================ user defined languages

@pytest.mark.case("LANG-039")
def test_lang_039_define_your_language_opens_the_dialog_and_toggles_it(app):
    """LANG-039: Define your language opens the dialog and toggles it"""
    close_udl_dialog(app)
    w = open_udl_dialog(app)
    ctrls = udl_controls(app, w)
    pop = [c for c in ctrls if c.get("class") == "NSPopUpButton"][0]
    assert pop["items"][:2] == ["Markdown (preinstalled)", "Markdown (preinstalled dark mode)"]
    titles = [c.get("title") for c in ctrls if c.get("class") == "NSButton"]
    for b in ["Create New…", "Save As…", "Rename…", "Remove", "Import…", "Export…"]:
        assert b in titles
    udl_select(app, w, "Markdown (preinstalled)")
    assert after_label(udl_controls(app, w), "Ext.:")["value"] == "md markdown"
    tabs = [c for c in app.ui(w, include_hidden=True)["controls"] if c.get("class") == "NSTabView"][0]
    for t in ["Folder & Default", "Keywords Lists", "Comment & Number", "Operators & Delimiters"]:
        udl_tab(app, w, t)
    app.run("IDM_LANG_USER_DLG")
    app.wait(lambda: not udl_window(app), message="dialog hidden")


def udl_with_mylang(app, tmp):
    """MyLang: ext myl, keywords alpha beta gamma, # line comments, /* */ block comments."""
    w = udl_create(app, "MyLang")
    udl_set_field(app, w, None, "Ext.:", "myl")
    udl_set_keywords(app, w, 1, "alpha beta")
    udl_set_field(app, w, "Comment & Number", "Open:", "#", nth=0)
    udl_set_field(app, w, None, "Open:", "/*", nth=1)
    udl_set_field(app, w, None, "Close:", "*/", nth=1)
    wait_xml(app, r'name="MyLang" ext="myl"')
    wait_xml(app, r'<Keywords name="Keywords1">alpha beta</Keywords>')
    wait_xml(app, r'<Keywords name="Comments">00# 01 02 03/\* 04\*/</Keywords>')
    return w


MY_TEXT = "alpha x 12 # note\nbeta /* c */ gamma\n"


@pytest.mark.case("LANG-040")
def test_lang_040_create_new_makes_a_language_writes_userdefinelang_xml_and_ad(fresh_app):
    """LANG-040: Create New makes a language, writes userDefineLang.xml and adds it to the menu"""
    app = fresh_app
    w = open_udl_dialog(app)
    app.modal_log()
    app.answers(alerts=[{"button": "OK", "field": "MyLang"}])
    app.click(w, "Create New…")
    app.wait(lambda: udl_selected(app, w) == "MyLang")
    assert "Name of the new language:" in [e.get("message") for e in app.modal_log()]
    assert re.search(r'<UserLang name="MyLang"[^>]*udlVersion="2.1"', udl_xml(app))
    tree = app.menu_tree("Language", 1)
    titles = [t.get("title") for t in tree]
    # Among the user languages, in the order Notepad++ loads them (NppParameters::load): those of
    # userDefineLang.xml first, then the userDefineLangs folder's (the preinstalled Markdown ones).
    # The plan said "after the Markdown ones"; upstream's in-session insert (UserDefineDialog,
    # IDC_ADD_BUTTON: InsertMenu before IDM_LANG_USER + newIndex) does not give that either.
    assert titles.index("User Defined Language") < titles.index("MyLang") < titles.index("Markdown (preinstalled)")
    app.new("x\n")
    r = app.call("e2e_menu_invoke", path="Language|MyLang")
    assert r["ran"]
    assert app.doc()["language"] == "MyLang"
    assert app.menu_item("Language|MyLang")["checked"]
    assert status_language(app) == "MyLang"


@pytest.mark.case("LANG-041")
def test_lang_041_a_user_language_defined_in_the_dialog_colours_a_file_with_it(fresh_app, tmp):
    """LANG-041: A user language defined in the dialog colours a file with its extension"""
    app = fresh_app
    udl_with_mylang(app, tmp)
    app.open(write(tmp / "x.myl", MY_TEXT))
    assert app.doc()["language"] == "MyLang"
    colourise(app)
    assert style_of(app, MY_TEXT, "alpha") == 4
    assert style_of(app, MY_TEXT, "beta") == 4
    assert style_of(app, MY_TEXT, "12") == 3
    assert style_of(app, MY_TEXT, "# note") == 2
    assert style_of(app, MY_TEXT, "/* c */") == 1
    assert style_of(app, MY_TEXT, "x ") == 0
    pairs = token_pairs(app)
    assert ("STYLE_4", "alpha") in pairs or any(t == "alpha" and s != "DEFAULT" for s, t in pairs)


@pytest.mark.case("LANG-042")
def test_lang_042_edits_in_the_dialog_restyle_open_documents_of_that_language(fresh_app, tmp):
    """LANG-042: Edits in the dialog restyle open documents of that language at once"""
    app = fresh_app
    w = udl_with_mylang(app, tmp)
    second = app.open(write(tmp / "y.myl", "gamma\n"))["index"]
    first = app.open(write(tmp / "x.myl", MY_TEXT))["index"]
    assert style_of(app, MY_TEXT, "gamma") == 0
    udl_set_keywords(app, w, 1, "alpha beta gamma")
    app.wait(lambda: style_of(app, MY_TEXT, "gamma") == 4, timeout=3, message="gamma restyled")
    app.select(1, document=second)
    colourise(app)
    app.wait(lambda: style_at(app, 0) == 4, timeout=3)


@pytest.mark.case("LANG-043")
def test_lang_043_ignore_case_and_prefix_mode_change_how_keywords_match(fresh_app, tmp):
    """LANG-043: Ignore case and prefix mode change how keywords match"""
    app = fresh_app
    w = udl_create(app, "MyLang")
    udl_set_field(app, w, None, "Ext.:", "myl")
    udl_set_keywords(app, w, 1, "alpha")
    wait_xml(app, r">alpha</Keywords>")
    text = "ALPHA alphabet alpha\n"
    app.open(write(tmp / "c.myl", text))

    def styles():
        colourise(app)
        # " alpha\n": the last word (" alpha" alone is first found in " alphabet").
        return [style_of(app, text, "ALPHA"), style_of(app, text, "alphabet"), style_of(app, text, " alpha\n", 1)]
    assert styles() == [0, 0, 4]
    udl_check(app, w, "Ignore case", True)
    wait_xml(app, r'caseIgnored="yes"')
    app.wait(lambda: styles() == [4, 0, 4], timeout=3)
    udl_check(app, w, "Prefix mode", True, tab="Keywords Lists", index=0)
    wait_xml(app, r'Keywords1="yes"')
    app.wait(lambda: styles() == [4, 4, 4], timeout=3)


@pytest.mark.case("LANG-044")
def test_lang_044_folding_in_code_operators_and_delimiters_of_a_user_language(fresh_app, tmp):
    """LANG-044: Folding in code, operators and delimiters of a user language"""
    app = fresh_app
    w = udl_create(app, "MyLang")
    udl_set_field(app, w, None, "Ext.:", "myl")
    udl_set_field(app, w, "Folder & Default", "Open:", "{", nth=0)
    udl_set_field(app, w, None, "Close:", "}", nth=0)
    udl_set_field(app, w, "Operators & Delimiters", "Operators 1:", "+ =")
    udl_set_field(app, w, None, "Delimiter 1", '"', skip=0)
    udl_set_field(app, w, None, "Delimiter 1", "\\", skip=1)
    udl_set_field(app, w, None, "Delimiter 1", '"', skip=2)
    wait_xml(app, r'Folders in code1, open">\{<')
    wait_xml(app, r'Operators1">\+ =<')
    text = 'x = 1 + 2\n{\n  s = "a\\"b"\n}\n'
    app.open(write(tmp / "f.myl", text))
    colourise(app)
    assert 2 in fold_headers(app, 4)
    assert style_of(app, text, "=") == SCE_USER_STYLE_OPERATOR
    assert style_of(app, text, "+") == SCE_USER_STYLE_OPERATOR
    start = text.index('"a')
    assert all(style_at(app, p) == SCE_USER_STYLE_DELIMITER1 for p in range(start, start + 6))
    assert style_of(app, text, "{") == SCE_USER_STYLE_FOLDER_IN_CODE1
    app.sci(SCI_TOGGLEFOLD, 1)
    assert [app.sci(SCI_GETLINEVISIBLE, n) for n in range(4)] == [1, 1, 0, 0]


@pytest.mark.case("LANG-045")
def test_lang_045_the_styler_of_a_user_language_style_sets_its_look(fresh_app, tmp):
    """LANG-045: The Styler of a user-language style sets its look"""
    app = fresh_app
    w = udl_create(app, "MyLang")
    udl_set_field(app, w, None, "Ext.:", "myl")
    udl_set_keywords(app, w, 1, "alpha")
    wait_xml(app, r">alpha</Keywords>")
    app.open(write(tmp / "s.myl", "alpha\n"))
    udl_tab(app, w, "Keywords Lists")
    app.answers(alerts=[{"button": "OK", "states": {"Bold": 1, "Italic": 1}}])
    app.act(w, "click", title="Styler", index=0)
    wait_xml(app, r'name="KEYWORDS1"[^>]*fontStyle="3"')
    app.wait(lambda: app.sci(SCI_STYLEGETBOLD, 4) == 1 and app.sci(SCI_STYLEGETITALIC, 4) == 1, timeout=3)
    app.answers(alerts=[{"button": "Cancel", "states": {"Underline": 1}}])
    app.act(w, "click", title="Styler", index=0)
    app.idle(0.3)
    assert app.sci(SCI_STYLEGETUNDERLINE, 4) == 0
    assert re.search(r'name="KEYWORDS1"[^>]*fontStyle="3"', udl_xml(app))


TINY_STYLES = '            <WordsStyle name="KEYWORDS1" styleID="4" fgColor="FF0000" bgColor="FFFFFF" fontStyle="1" nesting="0" />'


@pytest.mark.case("LANG-046")
def test_lang_046_import_reads_a_windows_udl_file_a_name_already_taken_is_refu(fresh_app, tmp):
    """LANG-046: Import reads a Windows UDL file; a name already taken is refused"""
    app = fresh_app
    src = write(tmp / "tiny.xml", udl_file("Tiny", "tiny", "foo bar", styles=TINY_STYLES))
    w = open_udl_dialog(app)
    app.answers(panels=[str(src)])
    app.click(w, "Import…")
    app.wait(lambda: udl_selected(app, w) == "Tiny")
    assert "Tiny" in [t.get("title") for t in app.menu_tree("Language", 1)]
    text = "foo baz\n"
    app.open(write(tmp / "a.tiny", text))
    assert app.doc()["language"] == "Tiny"
    colourise(app)
    assert style_at(app, 0) == 4
    assert app.sci(SCI_STYLEGETFORE, 4) == 0x0000FF
    assert app.sci(SCI_STYLEGETBOLD, 4) == 1
    app.modal_log()
    app.answers(panels=[str(src)], alerts=[1])
    app.click(w, "Import…")
    app.wait(lambda: any(e.get("kind") == "alert" for e in app.modal_log(clear=False)))
    msgs = [e.get("message") for e in app.modal_log()]
    assert "Nothing was imported: the file holds no language, or only names already taken." in msgs
    assert udl_xml(app).count('name="Tiny"') == 1


@pytest.mark.case("LANG-047")
def test_lang_047_export_writes_the_language_to_a_file_that_imports_back_the_s(fresh_app, tmp):
    """LANG-047: Export writes the language to a file that imports back the same"""
    app = fresh_app
    w = udl_with_mylang(app, tmp)
    out = tmp / "out" / "MyLang.xml"
    out.parent.mkdir()
    app.modal_log()
    app.answers(panels=[str(out)])
    app.click(w, "Export…")
    app.wait(lambda: out.exists())
    save = [e for e in app.modal_log() if e.get("kind") == "save"]
    assert save and save[0]["name"] == "MyLang.xml"
    root = ET.parse(out).getroot()
    langs = root.findall("UserLang")
    assert len(langs) == 1 and langs[0].get("name") == "MyLang" and langs[0].get("ext") == "myl"
    kws = {k.get("name"): k.text or "" for k in langs[0].iter("Keywords")}
    assert kws["Keywords1"] == "alpha beta" and kws["Comments"] == "00# 01 02 03/* 04*/"
    udl_select(app, w, "MyLang")
    app.answers(alerts=["Yes"])
    app.click(w, "Remove")
    app.wait(lambda: 'name="MyLang"' not in udl_xml(app))
    app.answers(panels=[str(out)])
    app.click(w, "Import…")
    app.wait(lambda: udl_selected(app, w) == "MyLang")
    app.open(write(tmp / "x.myl", MY_TEXT))
    colourise(app)
    assert style_of(app, MY_TEXT, "alpha") == 4 and style_of(app, MY_TEXT, "# note") == 2


@pytest.mark.case("LANG-048")
def test_lang_048_rename_save_as_and_remove_in_the_dialog(fresh_app, tmp):
    """LANG-048: Rename, Save As and Remove in the dialog"""
    app = fresh_app
    w = udl_with_mylang(app, tmp)
    app.open(write(tmp / "x.myl", MY_TEXT))
    app.answers(alerts=[{"button": "OK", "field": "OurLang"}])
    app.click(w, "Rename…")
    app.wait(lambda: udl_selected(app, w) == "OurLang")
    assert app.doc()["language"] == "OurLang"
    assert status_language(app) == "OurLang"
    titles = [t.get("title") for t in app.menu_tree("Language", 1)]
    assert "OurLang" in titles and "MyLang" not in titles
    app.answers(alerts=[{"button": "OK", "field": "OurCopy"}])
    app.click(w, "Save As…")
    app.wait(lambda: udl_selected(app, w) == "OurCopy")
    titles = [t.get("title") for t in app.menu_tree("Language", 1)]
    assert "OurLang" in titles and "OurCopy" in titles
    udl_select(app, w, "OurLang")
    app.answers(alerts=["No"])
    app.click(w, "Remove")
    app.idle(0.2)
    assert "OurLang" in [t.get("title") for t in app.menu_tree("Language", 1)]
    app.answers(alerts=["Yes"])
    app.click(w, "Remove")
    app.wait(lambda: "OurLang" not in [t.get("title") for t in app.menu_tree("Language", 1)])
    pop = [c for c in udl_controls(app, w) if c.get("class") == "NSPopUpButton"][0]
    assert "OurLang" not in pop["items"]
    assert app.doc()["language"] == "normal"


@pytest.mark.case("LANG-048")
def test_lang_048_create_new_refuses_a_taken_name(fresh_app):
    """LANG-048 (the name check): Create New with a name in use is refused and the language is kept"""
    app = fresh_app
    w = udl_create(app, "OurCopy")
    udl_set_keywords(app, w, 1, "keepme")
    wait_xml(app, r">keepme</Keywords>")
    app.modal_log()
    app.answers(alerts=[{"button": "OK", "field": "OurCopy"}, 1])
    app.click(w, "Create New…")
    app.wait(lambda: "That name is taken." in [e.get("message") for e in app.modal_log(clear=False)], timeout=5)
    assert ">keepme</Keywords>" in udl_xml(app)


@pytest.mark.case("LANG-049")
@pytest.mark.restart
def test_lang_049_user_languages_persist_across_a_restart_and_files_in_userdef(fresh_app, tmp):
    """LANG-049: User languages persist across a restart and files in userDefineLangs are loaded"""
    app = fresh_app
    udl_with_mylang(app, tmp)
    write(settings_dir(app) / "userDefineLangs" / "extra.xml", udl_file("Extra", "ext1", "zeta"))
    app.restart()
    titles = [t.get("title") for t in app.menu_tree("Language", 1)]
    for name in ["MyLang", "Extra", "Markdown (preinstalled)", "Markdown (preinstalled dark mode)"]:
        assert name in titles, name
    app.open(write(tmp / "a.myl", MY_TEXT))
    assert app.doc()["language"] == "MyLang"
    colourise(app)
    assert style_of(app, MY_TEXT, "alpha") == 4
    text = "zeta eta\n"
    app.open(write(tmp / "b.ext1", text))
    assert app.doc()["language"] == "Extra"
    colourise(app)
    assert style_at(app, 0) == 4


@pytest.mark.case("LANG-050")
@pytest.mark.restart
def test_lang_050_editing_a_shipped_user_language_shadows_it_in_the_user_s_fol(fresh_app, tmp):
    """LANG-050: Editing a shipped user language shadows it in the user's folder"""
    app = fresh_app
    shipped = resources(app) / "userDefineLangs" / "markdown._preinstalled.udl.xml"
    before = shipped.read_bytes()
    w = open_udl_dialog(app)
    udl_select(app, w, "Markdown (preinstalled)")
    udl_set_field(app, w, None, "Ext.:", "md markdown mdx")
    shadow = settings_dir(app) / "userDefineLangs" / "markdown._preinstalled.udl.xml"
    app.wait(lambda: shadow.exists() and 'ext="md markdown mdx"' in shadow.read_text())
    assert shipped.read_bytes() == before
    udl_select(app, w, "Markdown (preinstalled)")
    app.answers(alerts=["Yes"])
    app.click(w, "Remove")
    app.wait(lambda: "Markdown (preinstalled)" not in [t.get("title") for t in app.menu_tree("Language", 1)])
    assert shadow.exists()
    app.restart()
    titles = [t.get("title") for t in app.menu_tree("Language", 1)]
    assert "Markdown (preinstalled)" not in titles
    assert "Markdown (preinstalled dark mode)" in titles


@pytest.mark.case("LANG-051")
@pytest.mark.restart
def test_lang_051_the_dark_mode_variant_of_a_user_language_is_chosen_by_appear(app, tmp):
    """LANG-051: The dark-mode variant of a user language is chosen by appearance"""
    try:
        app.start(defaults={"appearanceMode": 1})
        app.open(write(tmp / "r.md", "# title\n"))
        assert app.doc()["language"] == "Markdown (preinstalled)"
        w = open_udl_dialog(app)
        udl_select(app, w, "Markdown (preinstalled)")
        box = [c for c in udl_controls(app, w) if c.get("title") == "Dark mode variant"][0]
        assert box["state"] == 0
        app.restart(defaults={"appearanceMode": 2})
        app.open(write(tmp / "s.md", "# title\n"))
        assert app.doc()["language"] == "Markdown (preinstalled dark mode)"
        w = open_udl_dialog(app)
        udl_select(app, w, "Markdown (preinstalled dark mode)")
        box = [c for c in udl_controls(app, w) if c.get("title") == "Dark mode variant"][0]
        assert box["state"] == 1
    finally:
        app.start()


@pytest.mark.case("LANG-052")
def test_lang_052_comment_toggling_uses_the_user_language_s_comment_tokens(fresh_app, tmp):
    """LANG-052: Comment toggling uses the user language's comment tokens"""
    app = fresh_app
    udl_with_mylang(app, tmp)
    close_udl_dialog(app)
    app.open(write(tmp / "c.myl", "alpha\nbeta\n"))
    app.select(1, 1)
    app.run("IDM_EDIT_BLOCK_COMMENT")
    first = app.text().split("\n")[0]
    assert first in ("#alpha", "# alpha"), first
    colourise(app)
    assert style_at(app, 0) == 2
    app.select(2, 1, 2, 5)
    app.run("IDM_EDIT_STREAM_COMMENT")
    second = app.text().split("\n")[1]
    assert second in ("/*beta*/", "/* beta */"), second
    colourise(app)
    assert style_of(app, app.text(), "/*") == 1


@pytest.mark.case("LANG-053")
def test_lang_053_open_user_defined_language_folder_reveals_the_settings_folde(fresh_app):
    """LANG-053: Open User Defined Language folder reveals the settings folder"""
    app = fresh_app
    udl_create(app, "MyLang")
    close_udl_dialog(app)
    app.modal_log()
    assert app.enabled("IDM_LANG_OPENUDLDIR")
    app.run("IDM_LANG_OPENUDLDIR")
    log = app.wait(lambda: [e for e in app.modal_log(clear=False) if e.get("kind") in ("reveal", "open_file", "open_url")])
    assert len(log) == 1 and log[0]["kind"] == "reveal", log
    # The NSWorkspace hook records what was opened or revealed as "target".
    want = settings_dir(app) / "userDefineLang.xml"
    assert app.same_path(log[0]["target"].replace("file://", ""), str(want)), log


@pytest.mark.case("LANG-054")
def test_lang_054_the_user_defined_languages_collection_item_opens_the_project(app):
    """LANG-054: The User Defined Languages Collection item opens the project's site"""
    app.modal_log()
    assert app.enabled("IDM_LANG_UDLCOLLECTION_PROJECT_SITE")
    app.run("IDM_LANG_UDLCOLLECTION_PROJECT_SITE")
    log = app.wait(lambda: [e for e in app.modal_log(clear=False) if e.get("kind") in ("open_url", "reveal", "open_file")])
    assert len(log) == 1 and log[0]["kind"] == "open_url", log
    assert log[0]["target"] == "https://github.com/notepad-plus-plus/userDefinedLanguages", log
