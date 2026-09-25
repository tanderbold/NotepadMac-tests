# LANG — Languages, lexers, folding, detection, User Defined Languages

The Language menu (194 commands: None (Normal Text), the letter submenus with every built-in language, the User Defined Language submenu, the user languages appended at the end) and everything that decides and shows a document's language: the lexer and its properties, the styles of the active theme applied to it, the status bar field, the menu check mark, the language given by a file's name (extensions of `langs.model.xml`, user-language extensions, whole file names), the language worked out from the contents (declarations: shebang, `<?xml`, `<?php`, doctype, modelines, JSON; then the trained model), folding per lexer, keyword colouring (checked with `e2e_sci` SCI_GETSTYLEAT and the MCP `tokens` tool), the Function List parsers per language (MCP `function_list`), and User Defined Languages (the dialog, files in the settings folder, import/export, persistence, dark-mode variants). Out of scope: the Style Configurator and the Preferences > Language page (SETTINGS), comment toggling and auto-completion as editing commands (EDIT/TYPING), the View > Fold commands themselves (VIEW), `-l` as a general command-line switch (CLI). Unless a case says otherwise, a case that compares colours runs with `appearanceMode = 1` (light, theme Default = the bundle's `stylers.model.xml`); reference data (`langs.model.xml`, `stylers.model.xml`, `functionListCorpus/`) is read from the test copy's `Contents/Resources`, samples from `../npp/macos/resources/language-samples/`.

## The Language menu

### LANG-001: The Language menu has upstream's structure and titles
- Covers: IDM_LANG_TEXT, IDM_LANG_USER_DLG, IDM_LANG_OPENUDLDIR, IDM_LANG_UDLCOLLECTION_PROJECT_SITE
- Channel: menu
- Steps: Dump `app.menu_tree("Language", 3)` on a fresh app. Collect every `pickLanguage:` item title from the letter submenus and compare with the labels of the Language rows of `plan/commands.tsv` (the part after the last " › ").
- Expect: the first item is "None (Normal Text)", then a separator, then letter submenus "A".."Y" in alphabetical order, each holding the languages whose title starts with that letter, sorted case-insensitively; then a separator and the "User Defined Language" submenu holding "Define your language…", "Open User Defined Language folder…", "Notepad++ User Defined Languages Collection" in that order; then a separator and the user languages ("Markdown (preinstalled)", "Markdown (preinstalled dark mode)"); every built-in label of commands.tsv (other than "User-Defined" and the three UDL-submenu items) is present exactly once; no title is an internal name ("javascript", "javascript.js", "searchResult", "ext", "udf" must not appear) — currently fails: J holds "javascript" and "javascript.js" instead of one "JavaScript" (xfail, see LANG-009).

### LANG-002: Every language command applies its language and a working lexer
- Covers: IDM_LANG_*
- Channel: mcp, menu
- Steps: For each Language row of commands.tsv whose id is a language (all IDM_LANG_* except IDM_LANG_USER_DLG, IDM_LANG_OPENUDLDIR, IDM_LANG_UDLCOLLECTION_PROJECT_SITE, IDM_LANG_USER), make a new document with `x\n`, run the command with `app.run(id)`. The expected internal name and lexer come from the table `LangMap.h` mirrors (e.g. IDM_LANG_CPP → cpp/cpp, IDM_LANG_ASCII → nfo/null, IDM_LANG_INI → ini/props, IDM_LANG_NIM → nim/nimrod, IDM_LANG_JSON5 → json5/json, IDM_LANG_GOLANG → go/cpp, IDM_LANG_PHP → php/phpscript).
- Expect: `run_command` reports ran=true; `app.doc()["language"]` is the expected name and `language_title` equals the command's label; `tokens` reports the expected lexer; `e2e_sci` SCI_GETLEXERLANGUAGE (4012, returns=string) is the same lexer name (or "null" for Normal Text and MS-DOS Style); `app.checked(id)` is true and the previously checked language item is now unchecked.

### LANG-003: Every language colours its own first keyword
- Covers: IDM_LANG_*
- Channel: mcp
- Steps: For each built-in language in langs.model.xml that has a menu command, take the first word of its first `<Keywords>` list (for html, xml, asp, jsp, php, kix, inno, yaml use the probe lines `<a href="x">text</a>`, `<root attr="1">text</root>`, `<% Response.Write "hi" %>`, `<% out.print("hi"); %>`, `<?php\necho "hi";\n?>`, `; comment\n$a = 1`, `[Setup]\nAppName=Test`, `key: value\n# comment`), put it on a line of its own in a new document, run the language's command.
- Expect: for every language at least one byte of the document has SCI_GETSTYLEAT (2010) ≠ 0 after SCI_COLOURISE (4003, 0, -1): no language is attached "in name only"; the test prints the list of languages that stay unstyled when it fails.

### LANG-004: Styles of the theme are applied to every language's lexer
- Covers: IDM_LANG_*
- Channel: mcp, prefs
- Steps: With appearanceMode=1 (theme Default), for each `<LexerType name=…>` of stylers.model.xml that belongs to a menu language, run the language's command on a new document and, for each `<WordsStyle styleID=… fgColor=… bgColor=… fontStyle=…>`, read SCI_STYLEGETFORE (2481), SCI_STYLEGETBACK (2482), SCI_STYLEGETBOLD (2483), SCI_STYLEGETITALIC (2484) for that style id.
- Expect: fore/back equal the style's fgColor/bgColor converted to Scintilla's BGR integer (a style without a colour inherits the Default style's); bold is set exactly when fontStyle has bit 1, italic exactly when it has bit 2; in particular python style 5 (KEYWORDS) and cpp style 5 (INSTRUCTION WORD) are not the Default style's colour.

### LANG-005: Keywords, comments, strings and numbers get their own styles per language
- Covers: IDM_LANG_C, IDM_LANG_CPP, IDM_LANG_CS, IDM_LANG_JAVA, IDM_LANG_TYPESCRIPT, IDM_LANG_PYTHON, IDM_LANG_RUBY, IDM_LANG_PERL, IDM_LANG_PHP, IDM_LANG_HTML, IDM_LANG_XML, IDM_LANG_CSS, IDM_LANG_SQL, IDM_LANG_BASH, IDM_LANG_BATCH, IDM_LANG_LUA, IDM_LANG_GOLANG, IDM_LANG_RUST, IDM_LANG_JSON, IDM_LANG_INI, IDM_LANG_MAKEFILE, IDM_LANG_DIFF, IDM_LANG_PASCAL, IDM_LANG_VB, IDM_LANG_POWERSHELL, IDM_LANG_TCL, IDM_LANG_LISP, IDM_LANG_HASKELL, IDM_LANG_FORTRAN, IDM_LANG_ASM, IDM_LANG_TOML, IDM_LANG_LATEX, IDM_LANG_CMAKE, IDM_LANG_NSIS, IDM_LANG_OBJC
- Channel: mcp
- Steps: For each row of a table (language, snippet, expected [style name, text] pairs), open the snippet with `open_document(text, language)` and call `tokens`. Rows: c `int main(void) { /* c */ return 42; } // x` → TYPE WORD "int", COMMENT "/* c */", INSTRUCTION WORD "return", NUMBER "42", COMMENT LINE "// x"; python `def f():\n    # c\n    return "s", 42` → KEYWORDS "def", DEF NAME "f", COMMENT LINE "# c", STRING "\"s\"", NUMBER "42"; ruby `def f` → INSTRUCTION "def", DEF NAME "f"; perl `"s"` → STRING DOUBLEQUOTE; php `<?php\nfunction f() {…}` → QUESTION MARK "<?php", WORD "function"; html `<body class="a"><!-- c -->` → TAG, ATTRIBUTE "class", DOUBLE STRING "\"a\"", COMMENT; xml `<?xml version="1.0"?>` → XMLSTART "<?", XMLEND "?>"; css `body { color: red; } /* c */` → TAG, VALUE " red", COMMENT; sql `SELECT … 'x'; -- c` → KEYWORD "SELECT", STRING2 "'x'", COMMENT LINE; batch `REM c` → COMMENT, `echo` → KEYWORDS; go `func` → INSTRUCTION WORD; rust `fn`/`i32` → KEYWORDS 1 / KEYWORDS 2, `// c` → LINE COMMENT; json `{"a": "s", "b": 42, "c": true}` → PROPERTY NAME, STRING, NUMBER, KEYWORD "true"; ini `[section]`, `; c`, `key=value` → SECTION, COMMENT, KEY, ASSIGNMENT; makefile `all:` → TARGET; diff → HEADER, POSITION, DELETED, ADDED; pascal `begin` → INSTRUCTION WORD, `{ c }` → COMMENT; vb `Dim` → WORD, `' c` → COMMENT; tcl `proc` → TCL KEYWORD; lisp `defun` → FUNCTION WORD; haskell `module Main` → KEYWORD, MODULE; fortran `program` → INSTRUCTION WORD, `! c` → COMMENT; asm `mov eax` → CPU INSTRUCTION, REGISTER; toml `[t]`, `"s"` → TABLE, STRING DQ; latex `\begin{document}` → COMMAND, TAG OPENING; cmake `project(x)` → COMMAND; nsis `Section` → SECTION; objc `@interface` → QUALIFIER; cs `public class` → INSTRUCTION WORD, TYPE WORD; typescript `number` → TYPE WORD; java/cpp/bash/lua/powershell `return` → INSTRUCTION WORD.
- Expect: each expected [style, text] pair occurs in the token list at the position of that text; `tokens.language` is the language asked for.

### LANG-006: None (Normal Text) takes the lexer off
- Covers: IDM_LANG_TEXT
- Channel: mcp, menu
- Steps: Open `def f(): return 1` as python, then run IDM_LANG_TEXT.
- Expect: language "normal", language_title "None (Normal Text)"; SCI_GETLEXERLANGUAGE is "null"; every byte has style 0; no line has SC_FOLDLEVELHEADERFLAG (0x2000) in SCI_GETFOLDLEVEL (2223); IDM_LANG_TEXT is checked, IDM_LANG_PYTHON is not; a new document (IDM_FILE_NEW) starts in None (Normal Text).

### LANG-007: The check mark and status bar follow the document in front
- Covers: IDM_LANG_PYTHON, IDM_LANG_CPP, IDM_LANG_TEXT
- Channel: mcp, menu, ui
- Steps: Make three documents: A set to Python, B to C++, C left as Normal Text. Switch between them with `go_to`/IDM_VIEW_TAB1..3 (or `select` on the tab) and read the menu and the status bar (the main window's NSTextField whose value contains "Ln:").
- Expect: with A in front only IDM_LANG_PYTHON is checked and the status bar value starts with "Python    "; with B only IDM_LANG_CPP and "C++    "; with C only IDM_LANG_TEXT and "None (Normal Text)    "; choosing a language for B does not change A's or C's language (`list_documents`).

### LANG-008: The status bar and the document list show the language title
- Covers: IDM_LANG_ASCII, IDM_LANG_CS, IDM_LANG_FORTRAN_77, IDM_LANG_INI, IDM_LANG_BASH, IDM_LANG_MSSQL
- Channel: ui, mcp
- Steps: For each of MS-DOS Style, C#, Fortran (fixed form), INI file, Shell, Microsoft Transact-SQL: run the command on a new document and read the status bar field and `list_documents`.
- Expect: the status bar's first field and `language_title` equal the menu label ("MS-DOS Style", "C#", "Fortran (fixed form)", "INI file", "Shell", "Microsoft Transact-SQL"); the internal names are nfo, cs, fortran77, ini, bash, mssql.

### LANG-009: JavaScript is one menu entry that applies javascript.js (known defect)
- Covers: IDM_LANG_JS
- Channel: menu, mcp, files
- Steps: Look at the J submenu; open a file `s.js` (`function f() { return 1; }`); read `app.menu_item("IDM_LANG_JS")` and the status bar; then on a new document run IDM_LANG_JS.
- Expect: Upstream: IDM_LANG_JS → L_JAVASCRIPT, the "javascript.js" definition, titled "JavaScript". The J submenu holds exactly one "JavaScript" item; for the .js file the item is checked and the status bar starts with "JavaScript"; after IDM_LANG_JS the document's language is javascript.js and function_list uses the javascript.js parser. Currently the submenu shows "javascript" and "javascript.js", IDM_LANG_JS resolves to the legacy "javascript" item and is not checked for a .js file — mark xfail with that reason.

### LANG-010: User-Defined applies the plain user-defined lexer (known gap)
- Covers: IDM_LANG_USER
- Channel: mcp, menu
- Steps: On a new document with `alpha 12`, `app.run("IDM_LANG_USER")`.
- Expect: FEATURES.md claims IDM_LANG_USER; upstream has a "User-Defined" item at the end of the Language menu that sets L_USER. The command runs, the lexer is "user" and the status bar names the user-defined language. Currently `run_command` answers "Command 46180 is not in this build's menus" — xfail.

### LANG-011: A language picked by hand survives Save As under another name (known defect)
- Covers: IDM_LANG_PYTHON
- Channel: mcp, modal, files
- Steps: New document `hello`, run IDM_LANG_PYTHON, queue a save panel answer `<tmp>/t.txt` and run IDM_FILE_SAVEAS; then open `<tmp>/u.cpp` saved from a document set to Ruby by hand.
- Expect: Upstream Buffer::setFileName keeps a language set from the menu, `_hasLangBeenSetFromMenu`. After the save the document is still python, and the u.cpp document still ruby. Currently the language falls back to what the name gives (normal) — xfail.

### LANG-012: A language not picked by hand follows the new name on Save As and Rename
- Covers: IDM_LANG_TEXT
- Channel: mcp, modal, files
- Steps: New document `x = 1` (stays Normal Text: too short to detect), save it as `<tmp>/a.py` with a queued panel; then IDM_FILE_RENAME to `<tmp>/a.rb` (queued answer); then rename a hand-set document (IDM_LANG_LUA) to `<tmp>/b.py`.
- Expect: after Save As the language is python; after the rename ruby; the hand-set document stays lua after its rename (renameCurrentTo keeps a chosen language).

### LANG-013: The language chosen for a document is kept by the session across a restart
- Covers: IDM_LANG_PERL
- Channel: launch, files, mcp
- Steps: Open `<tmp>/notes.txt`, run IDM_LANG_PERL, save; quit through `invoke("nsapp", "terminate:")` (the helper's `app` terminate does not write session.xml) and start again with `session=True`, `defaults={"restoreSession": True}`, keeping home and preferences.
- Expect: session.xml in the settings folder has a File entry for notes.txt with a `lang` attribute naming Perl; after the restart notes.txt is open again with language perl and IDM_LANG_PERL checked.

### LANG-014: Launch options -l and -udl= set the language of the files opened
- Covers: IDM_LANG_PYTHON
- Channel: launch, mcp
- Steps: Start with `args=["-lpython", "<tmp>/a.txt"]`; then with a UDL "MyLang" in the home's userDefineLang.xml, start with `args=['-udl=MyLang', "<tmp>/b.txt"]`.
- Expect: a.txt opens as python (IDM_LANG_PYTHON checked); b.txt opens as MyLang, status bar "MyLang".

## Language by file name

### LANG-015: Every extension in langs.model.xml opens in its language
- Covers: IDM_LANG_*
- Channel: files, mcp
- Steps: For each (language, extension) in the bundle's langs.model.xml (244 extensions; skip the ones a shipped user language claims: md, markdown), write `<tmp>/sample.<ext>` with `x\n` and open it; also call `detect_language(text="x", filename="sample.<ext>")`.
- Expect: the document's language is that language, except that where two languages claim an extension the later definition wins (`.tex` → tex, not latex); `by_filename` agrees; the menu item of the language is checked.

### LANG-016: Extensions are matched without regard to case
- Covers: IDM_LANG_PYTHON, IDM_LANG_CPP, IDM_LANG_HTML
- Channel: files, mcp
- Steps: Open `<tmp>/A.PY`, `<tmp>/B.Cpp`, `<tmp>/C.HTML`.
- Expect: python, cpp, html respectively.

### LANG-017: Files known by their whole name get upstream's language
- Covers: IDM_LANG_MAKEFILE, IDM_LANG_CMAKE, IDM_LANG_PYTHON, IDM_LANG_RUBY, IDM_LANG_BASH
- Channel: files, mcp
- Steps: For each of Makefile, GNUmakefile, CMakeLists.txt, SConstruct, SConscript, wscript, Rakefile, Vagrantfile, crontab, PKGBUILD, APKBUILD: write a one-line file (`x`, so the contents cannot decide) and open it; also `detect_language(text="x", filename=name)`.
- Expect: Upstream Buffer::setFileName: Makefile/GNUmakefile → makefile, CMakeLists.txt → cmake, SConstruct/SConscript/wscript → python, Rakefile/Vagrantfile → ruby, crontab/PKGBUILD/APKBUILD → bash, case-insensitively. Currently `by_filename` is normal for all of them and CMakeLists.txt opens as Normal Text (Makefile only gets makefile when its contents are detected) — xfail.

### LANG-018: A user language's extension comes before a built-in one
- Covers: IDM_LANG_USER_DLG
- Channel: files, mcp, ui, modal
- Steps: Through the UDL dialog create "PyLike" with Ext. `py`; open `<tmp>/a.py`; remove PyLike again (Remove, queued "Yes") and reopen a fresh `<tmp>/b.py`.
- Expect: a.py opens as PyLike (getUserDefinedLangNameFromExt is asked first); after the removal b.py opens as python.

## Language from the contents

### LANG-019: A shebang line settles the language of a file without extension
- Covers: IDM_LANG_PYTHON, IDM_LANG_BASH, IDM_LANG_PERL, IDM_LANG_RUBY, IDM_LANG_JS, IDM_LANG_LUA, IDM_LANG_TCL, IDM_LANG_R, IDM_LANG_POWERSHELL, IDM_LANG_PHP
- Channel: files, mcp
- Steps: For each first line: `#!/usr/bin/env python3`, `#!/usr/bin/python3.11`, `#!/usr/bin/env -S python3 -u`, `#!/bin/sh`, `#!/bin/bash`, `#!/bin/zsh`, `#!/usr/bin/perl`, `#!/usr/bin/env ruby`, `#!/usr/bin/env node`, `#!/usr/bin/lua`, `#!/usr/bin/tclsh`, `#!/usr/bin/env Rscript`, `#!/usr/bin/env pwsh`, `#!/usr/bin/php` — write `<tmp>/script` (no extension) with that line and `x = 1`, open it; also `detect_language`.
- Expect: languages python, python, python, bash, bash, bash, perl, ruby, javascript, lua, tcl, r, powershell, php; `declared` equals the language and `offered` is exactly [it]; no choice sheet is shown (modal log empty).

### LANG-020: Opening tags and doctypes declare XML, PHP and HTML
- Covers: IDM_LANG_XML, IDM_LANG_PHP, IDM_LANG_HTML
- Channel: files, mcp
- Steps: Open extension-less files starting `<?xml version="1.0"?><a/>`, `  <?php echo 1; ?>`, `<!DOCTYPE html><html></html>`, `<html><body>x</body></html>`.
- Expect: xml, php, html, html; `detect_language.declared` the same.

### LANG-021: Emacs and vim modelines declare the language
- Covers: IDM_LANG_RUBY, IDM_LANG_LUA, IDM_LANG_CPP, IDM_LANG_BASH, IDM_LANG_YAML
- Channel: files, mcp
- Steps: Open extension-less files with: first line `# -*- mode: ruby -*-`; first line `-- vim: set ft=lua:`; first line `// -*- c++ -*-`; last of 20 lines `# vim: filetype=sh`; second line `# vim: syntax=yml`; and a modeline on line 10 of 20 (neither the first two nor the last five lines).
- Expect: ruby, lua, cpp, bash, yaml; the file with the modeline in the middle is not declared by it (`declared` is null).

### LANG-022: JSON is recognised only when it parses
- Covers: IDM_LANG_JSON
- Channel: files, mcp
- Steps: Open extension-less files `{"a": [1, 2, 3]}`, `[{"k": true}]` and `{ not json at all`.
- Expect: the first two are json (`declared` json); the third is not declared json.

### LANG-023: Too little text is left as Normal Text
- Covers: IDM_LANG_TEXT
- Channel: files, mcp
- Steps: Open extension-less files containing ``, `hello\n`, `one two three four\n`, `...\n...\n`.
- Expect: all stay "normal"; `detect_language` gives `offered` = [] for each; no choice sheet appears.

### LANG-024: The trained model names the language of each written sample
- Covers: IDM_LANG_ASN1, IDM_LANG_AVS, IDM_LANG_ESCRIPT, IDM_LANG_FORTRAN_77, IDM_LANG_GUI4CLI, IDM_LANG_HOLLYWOOD, IDM_LANG_JSON5, IDM_LANG_JSP, IDM_LANG_KIX, IDM_LANG_ASCII, IDM_LANG_OSCRIPT, IDM_LANG_REGISTRY, IDM_LANG_SPICE, IDM_LANG_TXT2TAGS
- Channel: mcp, files, modal
- Steps: For each of the 56 files in `../npp/macos/resources/language-samples/<language>/`: call `detect_language(text)`; copy it to `<tmp>/<stem>` (no extension), queue the alert answer "Use this one" and open it.
- Expect: for every file `guesses[0].language` is the folder's language (nfo for the nfo folder); `offered` contains it for all but at most 3 (known misses: jsp pages beginning with `<html` are declared html; gui4cli/filelist.gui is below the offering level); the opened document's language equals the folder's language for all but at most 3.

### LANG-025: The upstream function-list corpus is recognised from its contents
- Covers: IDM_LANG_*
- Channel: mcp
- Steps: For each `functionListCorpus/<lang>/unitTest` in the bundle (41 folders; `udl-X` means X; javascript may be answered by javascript or javascript.js), call `detect_language(text)`.
- Expect: at least 36 of the files have their language in `offered`, at least 35 have it first; no `offered` list is longer than 10.

### LANG-026: When several languages fit, the user is asked and the answer applies
- Covers: IDM_LANG_FORTRAN_77, IDM_LANG_TEXT
- Channel: files, modal, mcp
- Steps: Copy language-samples/fortran77/roots.f77 to `<tmp>/roots` (its offered list is [fortran77, fortran]). Queue alert answer "Use this one" and open it; then copy it to `<tmp>/roots2`, queue "Leave as text" and open that.
- Expect: the modal log has an alert "Which language is this?" with buttons ["Use this one", "Leave as text"]; the first document becomes fortran77 (the likeliest, preselected); the second stays normal.

### LANG-027: Pasting into an empty document works out its language; pasting into text does not
- Covers: IDM_LANG_PYTHON
- Channel: clipboard, mcp
- Steps: Put the 20-line Python script from the in-app suite (`import os`, `def read_config(path):`, `class Runner:` …) on the private clipboard; on an empty new document run IDM_EDIT_PASTE; on another new document with `notes\n` in it, move to the end and paste the same.
- Expect: the first document becomes python; the second stays normal.

### LANG-028: Detection only where the name says nothing and the user has not chosen
- Covers: IDM_LANG_TEXT, IDM_LANG_CPP
- Channel: files, mcp, prefs
- Steps: (a) Open `<tmp>/script.txt` holding the Python script. (b) New document, run IDM_LANG_CPP, then paste the script into it while empty. (c) Set preference `detectLanguageFromContent = false`, open `<tmp>/script` (no extension, same text); restore the preference.
- Expect: (a) stays normal (the extension decides); (b) stays cpp; (c) stays normal; with the preference back on, reopening a copy `<tmp>/script2` gives python.

### LANG-029: An agent's new document is detected, and C# without a class is C#
- Covers: IDM_LANG_CS, IDM_LANG_SQL, IDM_LANG_RUBY
- Channel: mcp
- Steps: `open_document(text=…)` without a language for: the top-level C# program from the in-app suite (`using System.Net.Http.Headers;` … `var builder = WebApplication.CreateBuilder(args);` …), the SQL query `SELECT u.id, u.name, count(o.id) AS orders FROM users u LEFT JOIN …`, the Ruby `require 'json'` / `class Loader` snippet.
- Expect: the documents get cs, sql and ruby (or, when a sheet asks, cs/sql/ruby is the preselected first choice); `detect_language` on the C# text has cs first, not javascript.

## Lexer set-up and folding

### LANG-030: Each lexer folds where its language folds
- Covers: IDM_LANG_PYTHON, IDM_LANG_CPP, IDM_LANG_JAVA, IDM_LANG_LUA, IDM_LANG_YAML, IDM_LANG_JSON, IDM_LANG_CSS, IDM_LANG_BASH, IDM_LANG_RUBY, IDM_LANG_INI, IDM_LANG_PASCAL, IDM_LANG_SQL, IDM_LANG_PERL, IDM_LANG_XML, IDM_LANG_HTML, IDM_LANG_PHP
- Channel: mcp
- Steps: For each (language, text) open the text in that language and call `tokens(include_folds=true)` (and cross-check with SCI_GETFOLDLEVEL & 0x2000): python `def f():\n    return 1\n\nx = 2`; cpp `int f() {\n  return 1;\n}`; java `class A {\n  void f() {\n  }\n}`; lua `function f()\n  return 1\nend`; yaml `a:\n  b: 1\n  c: 2`; json `{\n "a": [\n  1\n ]\n}`; css `a {\n  color: red;\n}`; bash `if true; then\n  echo 1\nfi`; ruby `def f\n  1\nend`; ini `[a]\nk=1\n[b]\nk=2`; pascal `begin\n  x := 1;\nend.`; sql `BEGIN\n  SELECT 1;\nEND;`; perl `sub f {\n  1;\n}`; xml `<?xml version="1.0"?>\n<root>\n  <item>\n    <name>a</name>\n  </item>\n</root>`; html page and php page from the in-app suite.
- Expect: fold headers exactly at: python [1], cpp [1], java [1, 2], lua [1], yaml [1], json [1, 2], css [1], bash [1], ruby [1], ini [1, 3], pascal [1], sql [1], perl [1]; xml has headers at lines 2 and 3; html at 1, 2, 3, 7 and 10 (elements, a two-line comment, the function inside `<script>`); php at 1 and 4.

### LANG-031: A fold closes and opens its lines, and a language change keeps what was folded
- Covers: IDM_LANG_C, IDM_LANG_CPP
- Channel: mcp
- Steps: Open `int f(void) {\n    return 1;\n}\nint g;\n` as C; SCI_TOGGLEFOLD (2231) on line 0; then run IDM_LANG_CPP; then SCI_TOGGLEFOLD line 0 again.
- Expect: after the fold, SCI_GETLINEVISIBLE (2228) is 0 for lines 1-2 and 1 for line 3, SCI_GETFOLDEXPANDED (2230) of line 0 is 0; after switching to C++ lines 1-2 are still hidden; after the second toggle they are visible and line 0 is expanded.

### LANG-032: The C family gets comment and preprocessor folding and its word lists in the right slots
- Covers: IDM_LANG_C
- Channel: mcp
- Steps: Open the in-app suite's C source (`/** a comment\n *  @param x of three\n *  lines */\n#if DEBUG\nint f(void) {\n    return 1;\n}\n#endif\n#if 0\nint g(void) { return 2; }\n#endif\n`) as C.
- Expect: fold headers at lines 1 (block comment), 4 (`#if`) and 5 (brace); SCI_GETSTYLEAT at "return" is SCE_C_WORD (5), at "int f" SCE_C_WORD2 (16), inside "@param" SCE_C_COMMENTDOCKEYWORD (17); "int g" under `#if 0` is still SCE_C_WORD2 (lexer.cpp.track.preprocessor=0, not greyed out).

### LANG-033: A PHP page styles HTML, embedded JavaScript and PHP each in its own language's styles
- Covers: IDM_LANG_PHP, IDM_LANG_HTML, IDM_LANG_ASP, IDM_LANG_JSP
- Channel: mcp
- Steps: Open `<html>\n<script>\nvar x = function () { return 1; };\n</script>\n<?php\nforeach ($a as $b) { echo $b; }\n?>\n</html>\n` as php; read SCI_GETSTYLEAT at offset 1, at "function", at "foreach", and the fore colours of those styles; repeat the tag check for ASP (`<% Response.Write "hi" %>`) and JSP (`<% out.print("hi"); %>`).
- Expect: offset 1 is SCE_H_TAG (1), "function" SCE_HJ_KEYWORD (47), "foreach" SCE_HPHP_WORD (121); SCI_STYLEGETFORE of 1, 47 and 121 equal the fgColor of html TAG, javascript KEYWORD and php WORD in stylers.model.xml, and style 121's colour differs from STYLE_DEFAULT's; the ASP/JSP server blocks are not style 0.

### LANG-034: Backquoted strings in Go, JavaScript and TypeScript span lines
- Covers: IDM_LANG_GOLANG, IDM_LANG_JS, IDM_LANG_TYPESCRIPT
- Channel: mcp
- Steps: Open ``package main\n\nvar s = `raw\nstring`\n`` as go, ``const s = `a ${b}\nc`;\n`` as javascript.js, ``const s: string = `raw\ntext`;\n`` as typescript.
- Expect: SCI_GETSTYLEAT at "raw"/"a $"/"c`"/"text" is SCE_C_STRINGRAW (20) in each, including on the second line.

### LANG-035: JSON escapes and JSON5 comments
- Covers: IDM_LANG_JSON, IDM_LANG_JSON5
- Channel: mcp
- Steps: Open `{"a": "x\ny"}` (a literal backslash-n) as json and `{\n  // a comment\n  a: 1\n}` as json5.
- Expect: the `\n` escape has SCE_JSON_ESCAPESEQUENCE (5); the `//` comment has SCE_JSON_LINECOMMENT (6) in JSON5.

## Function List per language

### LANG-036: Function List parsers give Notepad++'s expected results on its own corpus
- Covers: IDM_LANG_*
- Channel: mcp
- Steps: For each folder of the bundle's `functionListCorpus` except javascript, typescript (deliberate corrections) and udl-* : call `function_list(text=unitTest, language=<folder>)`; turn entries into leaves (no container, minus rows that only repeat a class name) and nodes (container → names); compare with `unitTest.expected.result` (JSON: leaves, nodes[name, leaves]).
- Expect: `parser` is non-null for each; at least 35 of the 38 languages match exactly (the failing ones are printed).

### LANG-037: The Function List finds each language's declarations in an open document
- Covers: IDM_LANG_C, IDM_LANG_CPP, IDM_LANG_CS, IDM_LANG_JAVA, IDM_LANG_PHP, IDM_LANG_PYTHON, IDM_LANG_RUBY, IDM_LANG_PERL, IDM_LANG_LUA, IDM_LANG_BASH, IDM_LANG_PASCAL, IDM_LANG_VB, IDM_LANG_RUST, IDM_LANG_JS, IDM_LANG_TYPESCRIPT, IDM_LANG_POWERSHELL, IDM_LANG_HASKELL, IDM_LANG_NIM, IDM_LANG_CSS, IDM_LANG_MAKEFILE, IDM_LANG_BATCH, IDM_LANG_INI, IDM_LANG_FORTRAN, IDM_LANG_D, IDM_LANG_SQL
- Channel: files, mcp
- Steps: For each row of the in-app battery (language, extension, snippet, wanted entry), write `<tmp>/f.<ext>`, open it and call `function_list(document=…)`: c `int add(int a, int b)\n{…}` → "add(int a, int b)"; cpp `class Thing {\npublic:\n    void run() {}\n};` → Thing::run; cs `class Store { public void Clear() { } }` → Store::Clear; java → G::hello; php `<?php\nfunction helper($x) …` → "helper($x) "; python `def alpha(x):` → "alpha(x)"; ruby, perl, lua, bash, pascal, vb, rust, javascript, typescript, powershell (Get-Thing), haskell, nim ("alpha(x: int): int"), css (".alpha "), makefile, batch, ini (Section), fortran (ALPHA), d, sql ("PROCEDURE alpha"); plus the corrected rows `pub fn alpha`, `impl Thing { pub fn delta }` → Thing::delta, `const beta = (x) => x;` → beta.
- Expect: each wanted entry (name, or container::name) is in the result; `language` is the document's language.

### LANG-038: The Function List panel follows the language of the document
- Covers: IDM_LANG_PYTHON, IDM_LANG_TEXT, IDM_VIEW_FUNC_LIST
- Channel: ui, mcp, menu
- Steps: Open `def alpha(x):\n    pass\n\ndef beta():\n    pass\n` as python, show the panel with IDM_VIEW_FUNC_LIST and read its outline rows with `app.ui()`; then run IDM_LANG_TEXT and read the panel again.
- Expect: the panel lists "alpha(x)" and "beta()" in file order; after switching to Normal Text it is empty; switching back to Python fills it again.

## User Defined Languages

### LANG-039: Define your language opens the dialog and toggles it
- Covers: IDM_LANG_USER_DLG
- Channel: menu, ui
- Steps: Run IDM_LANG_USER_DLG; read the window "User Defined Language" with `app.ui`; run the command again.
- Expect: a window titled "User Defined Language" appears with the "User language:" popup listing "Markdown (preinstalled)" and "Markdown (preinstalled dark mode)", buttons Create New…, Save As…, Rename…, Remove, Import…, Export…, the Ext. field showing "md markdown" for the first, and tabs "Folder & Default", "Keywords Lists", "Comment & Number", "Operators & Delimiters"; the second run hides the window.

### LANG-040: Create New makes a language, writes userDefineLang.xml and adds it to the menu
- Covers: IDM_LANG_USER_DLG, IDM_LANG_USER
- Channel: ui, modal, files, menu
- Steps: Open the dialog, queue alert `{"button": "OK", "field": "MyLang"}`, click "Create New…".
- Expect: the modal log has the alert "Name of the new language:"; the popup now shows "MyLang"; `<home>/Library/Application Support/NotepadMac/userDefineLang.xml` exists and holds `<UserLang name="MyLang" … udlVersion="2.1">`; the Language menu has a "MyLang" item among the user languages, before the userDefineLangs folder's (the Markdown ones), as Notepad++ loads userDefineLang.xml first; running that item (`e2e_menu_invoke` path `Language|MyLang`) sets the document's language to MyLang, checks the item and shows "MyLang" in the status bar.

### LANG-041: A user language defined in the dialog colours a file with its extension
- Covers: IDM_LANG_USER_DLG
- Channel: ui, modal, files, mcp
- Steps: Create "MyLang"; set Ext. to `myl` (set_value, end_editing); on "Keywords Lists" set the 1st group to `alpha beta`; on "Comment & Number" set Comment line Open to `#` and Comment Open/Close to `/*` `*/`; wait past the 0.35 s commit (poll the XML file); open `<tmp>/x.myl` with `alpha x 12 # note\nbeta /* c */\n`.
- Expect: the document's language is MyLang; SCI_GETSTYLEAT is SCE_USER_STYLE_KEYWORD1 (4) on "alpha" and "beta", SCE_USER_STYLE_NUMBER (3) on "12", SCE_USER_STYLE_COMMENTLINE (2) on "# note", SCE_USER_STYLE_COMMENT (1) on "/* c */", 0 on "x"; `tokens` shows the same runs (as STYLE_4, STYLE_3 …); the XML has `ext="myl"`, Keywords1 `alpha beta` and Comments `00# 01 02 03/* 04*/`.

### LANG-042: Edits in the dialog restyle open documents of that language at once
- Covers: IDM_LANG_USER_DLG
- Channel: ui, mcp
- Steps: With x.myl from LANG-041 open in front, add `gamma` to the 1st keyword group in the dialog (and `gamma` in the document), poll.
- Expect: within 2 s "gamma" has style 4 without reopening the file; a second open document in MyLang shows the change when brought to front.

### LANG-043: Ignore case and prefix mode change how keywords match
- Covers: IDM_LANG_USER_DLG
- Channel: ui, mcp
- Steps: MyLang with keywords `alpha`; document `ALPHA alphabet alpha`; toggle "Ignore case" on, then "Prefix mode" of the 1st group on.
- Expect: before: only the last word has style 4; with Ignore case: "ALPHA" too; with Prefix mode as well: "alphabet" too; the XML reflects `caseIgnored="yes"` and `Keywords1="yes"`.

### LANG-044: Folding in code, operators and delimiters of a user language
- Covers: IDM_LANG_USER_DLG
- Channel: ui, mcp
- Steps: In MyLang set Folding in code 1 Open `{`, Close `}` (Folder & Default), Operators 1 `+ =`, Delimiter 1 Open `"` Escape `\` Close `"` (Operators & Delimiters); document `x = 1 + 2\n{\n  s = "a\"b"\n}\n`.
- Expect: line 2 is a fold header (SCI_GETFOLDLEVEL & 0x2000) and folds lines 3-4 away; "=" and "+" have SCE_USER_STYLE_OPERATOR (12); the whole `"a\"b"` including the escaped quote has SCE_USER_STYLE_DELIMITER1 (16); "{" has SCE_USER_STYLE_FOLDER_IN_CODE1 (13).

### LANG-045: The Styler of a user-language style sets its look
- Covers: IDM_LANG_USER_DLG
- Channel: ui, modal, mcp
- Steps: Click the Styler button of the 1st keyword group; the sheet "Style: …" is an NSAlert whose accessory holds the check boxes, so it needs a hook that sets accessory controls from a queued answer (e.g. `{"button": "OK", "states": {"Bold": 1, "Italic": 1}}`) - a real modal cannot be driven from a second connection because the agent server serves requests synchronously on the main queue.
- Expect: in an open MyLang document SCI_STYLEGETBOLD (2483) and SCI_STYLEGETITALIC (2484) of style 4 are 1; the XML's WordsStyle KEYWORDS1 has fontStyle 3; Cancel instead leaves them unchanged.

### LANG-046: Import reads a Windows UDL file; a name already taken is refused
- Covers: IDM_LANG_USER_DLG
- Channel: ui, modal, files, mcp
- Steps: Write `<tmp>/tiny.xml` in Notepad++'s format (`<NotepadPlus><UserLang name="Tiny" ext="tiny" udlVersion="2.1">` with Keywords1 `foo bar` and `<WordsStyle name="KEYWORDS1" styleID="4" fgColor="FF0000" bgColor="FFFFFF" fontStyle="1"/>`); in the dialog queue the panel answer and click "Import…"; open `<tmp>/a.tiny` with `foo baz`; then import the same file again.
- Expect: the popup selects "Tiny", the menu has "Tiny"; a.tiny is Tiny, "foo" has style 4 with SCI_STYLEGETFORE 0x0000FF and bold 1; the second import shows the alert "Nothing was imported: the file holds no language, or only names already taken." and adds nothing.

### LANG-047: Export writes the language to a file that imports back the same
- Covers: IDM_LANG_USER_DLG
- Channel: ui, modal, files
- Steps: Select MyLang (from LANG-041), queue save panel `<tmp>/out/MyLang.xml`, click "Export…"; check the panel's proposed name; remove MyLang (queued "Yes") and import the exported file.
- Expect: the save panel was offered "MyLang.xml"; the file parses as XML with one `UserLang name="MyLang" ext="myl"` and the keyword and comment lists; after re-import a new x.myl document is styled as in LANG-041.

### LANG-048: Rename, Save As and Remove in the dialog
- Covers: IDM_LANG_USER_DLG, IDM_LANG_USER
- Channel: ui, modal, mcp, menu
- Steps: With a document open in MyLang: Rename… (queued field "OurLang"); Save As… (queued field "OurCopy"); Remove with queued "No", then Remove with queued "Yes" on OurLang; finally Create New… with the name "OurCopy".
- Expect: after the rename the document's language and status bar are "OurLang" and the menu item is renamed; after Save As both OurLang and OurCopy are in the menu and the popup shows OurCopy; "No" keeps OurLang; "Yes" removes it from the menu and popup and the document falls back to None (Normal Text); the duplicate name is refused with the alert "That name is taken.".

### LANG-049: User languages persist across a restart and files in userDefineLangs are loaded
- Covers: IDM_LANG_USER_DLG, IDM_LANG_USER
- Channel: launch, files, menu, mcp
- Steps: Create MyLang with ext `myl`; write `<home>/…/NotepadMac/userDefineLangs/extra.xml` holding a UDL "Extra" with ext `ext1`; restart keeping home and preferences; open `<tmp>/a.myl` and `<tmp>/b.ext1`.
- Expect: the menu lists MyLang and Extra (and the Markdown ones); a.myl is MyLang and b.ext1 is Extra, keyword styles as defined.

### LANG-050: Editing a shipped user language shadows it in the user's folder
- Covers: IDM_LANG_USER_DLG
- Channel: ui, files
- Steps: In the dialog select "Markdown (preinstalled)" and add ` mdx` to its Ext.; then Remove it (queued "Yes"); restart.
- Expect: after the edit `<settings>/userDefineLangs/markdown._preinstalled.udl.xml` exists with `ext="md markdown mdx"` while the bundle's file is unchanged; after removal the shadow file stays (empty of that language) and after the restart "Markdown (preinstalled)" is not in the menu while the dark-mode variant still is.

### LANG-051: The dark-mode variant of a user language is chosen by appearance
- Covers: IDM_LANG_USER
- Channel: launch, prefs, files, mcp
- Steps: Start with `appearanceMode = 1` (light) and open `<tmp>/r.md`; restart with `appearanceMode = 2` (dark) and open `<tmp>/s.md`.
- Expect: in light mode r.md is "Markdown (preinstalled)"; in dark mode s.md is "Markdown (preinstalled dark mode)"; the "Dark mode variant" check box in the dialog is on only for the latter.

### LANG-052: Comment toggling uses the user language's comment tokens
- Covers: IDM_LANG_USER_DLG, IDM_EDIT_BLOCK_COMMENT, IDM_EDIT_STREAM_COMMENT
- Channel: ui, mcp
- Steps: MyLang with comment line `#` and block `/*` `*/`; document `alpha\nbeta\n` in MyLang; select line 1 and run IDM_EDIT_BLOCK_COMMENT; select "beta" and run IDM_EDIT_STREAM_COMMENT.
- Expect: line 1 becomes `#alpha` (upstream inserts the token without a space for a UDL unless configured otherwise — accept `#alpha` or `# alpha`, as the port writes it) and has style 2; "beta" becomes `/*beta*/` (or `/* beta */`) with style 1.

### LANG-053: Open User Defined Language folder reveals the settings folder
- Covers: IDM_LANG_OPENUDLDIR
- Channel: menu, files
- Steps: Create MyLang (so userDefineLang.xml exists); run IDM_LANG_OPENUDLDIR. Needs a hook that records NSWorkspace `activateFileViewerSelectingURLs:` / `openURL:` calls in `e2e_log` instead of performing them.
- Expect: the command runs (enabled); the recorded reveal is exactly `<home>/Library/Application Support/NotepadMac/userDefineLang.xml` (the settings folder's user-language file); Finder is not actually activated during the test.

### LANG-054: The User Defined Languages Collection item opens the project's site
- Covers: IDM_LANG_UDLCOLLECTION_PROJECT_SITE
- Channel: menu
- Steps: Run IDM_LANG_UDLCOLLECTION_PROJECT_SITE with the same NSWorkspace-recording hook as LANG-053.
- Expect: the command is enabled and runs; the one URL recorded is `https://github.com/notepad-plus-plus/userDefinedLanguages`; no browser is opened.
