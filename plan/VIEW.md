# VIEW — The View menu

Every command of the View menu (82 commands in `plan/commands.tsv`, menu "View"): the window
modes (Always on Top, Full Screen, Post-It, Distraction Free), Show Symbol, Zoom, Word Wrap,
folding and fold levels, Hide Lines, Summary, Monitoring (tail -f), the panels (Folder as
Workspace, Document Map, Document List, Function List, Project Panels 1-3), the second view
(move/clone, focus, synchronized scrolling and zoom), new instances, View Current File in a
browser, the Tab submenu (go to, move, colours) and text direction. Out of scope here: how the
panels dock and float, the toolbar, tab bar and status bar as such (UI), the interface language
(L10N), the contents of Folder as Workspace / Project panels beyond showing them (FILE/SESSION).
Scintilla state is read with `e2e_sci` on `main` or `sub`; menu state with `e2e_menu`.

## Menu structure and state

### VIEW-001: Every View command is in the menu and runs by its id
- Covers: IDM_VIEW_*, IDM_EDIT_RTL, IDM_EDIT_LTR
- Channel: menu, mcp
- Steps: For each of the 82 View commands of commands.tsv: look the item up with `e2e_menu` by IDM name, then (on a fresh unsaved `new 1` holding "abc") `run_command` it, except IDM_VIEW_FULLSCREENTOGGLE, which is only looked up; toggles are run twice so the state comes back.
- Expect: every id resolves to a menu item (not null) that is enabled; every `run_command` answers `ran: true` and never "is not in this build's menus"; the application still answers `list_documents` afterwards; the document text is still "abc".

### VIEW-002: View shortcuts are the documented key equivalents and work from the keyboard
- Covers: IDM_VIEW_ZOOMIN, IDM_VIEW_ZOOMOUT, IDM_VIEW_ZOOMRESTORE, IDM_VIEW_FOLDALL, IDM_VIEW_UNFOLDALL, IDM_VIEW_TAB_SPACE, IDM_VIEW_FULLSCREENTOGGLE, IDM_VIEW_TAB1
- Channel: menu, keys
- Steps: Read the `key` of each item with `e2e_menu`. Then with a C++ document `int f() {\n  x;\n}\n` press `cmd+=`, `cmd+-`, `cmd+0`, `alt+cmd+.`, `shift+cmd+.`, `shift+cmd+i` (twice) through `e2e_keys`.
- Expect: keys are zoom in `cmd++`, zoom out `cmd+-`, restore `cmd+0`, fold all `alt+cmd+.`, unfold all `shift+cmd+.`, show space and tab `shift+cmd+i`, full screen `ctrl+cmd+f`, 1st Tab `cmd+1`; after `cmd+=` SCI_GETZOOM is 1, after `cmd+-` 0, after `cmd+0` 0; after `alt+cmd+.` line 2 is invisible, after `shift+cmd+.` visible; `shift+cmd+i` sets SCI_GETVIEWWS to 1 and the second press back to 0.

### VIEW-003: The View menu lists each command once
- Covers: IDM_VIEW_FULLSCREENTOGGLE
- Channel: menu
- Steps: Dump `e2e_menu tree="View" depth=2`.
- Expect: no two non-separator items of one (sub)menu have the same title and action (in particular exactly one "Toggle Full Screen Mode" item with action `toggleFullScreenMode:`); the Show Symbol submenu lists Show Space and Tab, Show End of Line, Show Non-Printing Characters, Show Control Characters & Unicode EOL, Show All Characters, Show Indent Guide, Show Wrap Symbol.

### VIEW-004: Toggle commands carry a checkmark that follows their state
- Covers: IDM_VIEW_ALWAYSONTOP, IDM_VIEW_POSTIT, IDM_VIEW_DISTRACTIONFREE, IDM_VIEW_TAB_SPACE, IDM_VIEW_EOL, IDM_VIEW_NPC, IDM_VIEW_NPC_CCUNIEOL, IDM_VIEW_ALL_CHARACTERS, IDM_VIEW_INDENT_GUIDE, IDM_VIEW_WRAP_SYMBOL, IDM_VIEW_WRAP, IDM_VIEW_SYNSCROLLV, IDM_VIEW_SYNSCROLLH, IDM_VIEW_ZOOM_SYNC, IDM_VIEW_DOC_MAP, IDM_VIEW_DOCLIST, IDM_VIEW_FUNC_LIST, IDM_VIEW_FILEBROWSER, IDM_VIEW_PROJECT_PANEL_1, IDM_VIEW_PROJECT_PANEL_2, IDM_VIEW_PROJECT_PANEL_3, IDM_VIEW_MONITORING, IDM_EDIT_RTL, IDM_EDIT_LTR
- Channel: menu, mcp
- Steps: For each toggle command (Monitoring on a saved file `m.txt`, the sync commands with a cloned view): read `checked`, run it, read `checked`, run it again, read `checked`. For RTL/LTR: run IDM_EDIT_RTL, read both items, run IDM_EDIT_LTR, read both.
- Expect: `checked` is false, then true, then false for every toggle (Show Control Characters & Unicode EOL and Show Indent Guide start true, as their defaults are on, and go false then true); after RTL the RTL item is checked and LTR not, after LTR the reverse.

### VIEW-005: Show All Characters shows spaces, tabs, line ends and invisible characters at once
- Covers: IDM_VIEW_ALL_CHARACTERS, IDM_VIEW_TAB_SPACE, IDM_VIEW_EOL, IDM_VIEW_NPC
- Channel: mcp, menu
- Steps: New document "a\tb c\u00a0d\n". Run IDM_VIEW_ALL_CHARACTERS; read SCI_GETVIEWWS, SCI_GETVIEWEOL and SCI_GETREPRESENTATION of U+00A0; run it again; read them again. Also press the toolbar item "All Characters" (`e2e_act action=toolbar`) twice.
- Expect: after the first run whitespace is visible (1), EOL visible (1), U+00A0 has a representation ("NBSP"), and Show Space and Tab, Show End of Line, Show Non-Printing Characters are all checked; after the second run all three are off; the toolbar button does exactly the same as the menu command; the text is unchanged and not modified.

### VIEW-006: The browser commands are reachable by their Notepad++ ids, Safari under IDM_VIEW_IN_IE
- Covers: IDM_VIEW_IN_FIREFOX, IDM_VIEW_IN_CHROME, IDM_VIEW_IN_EDGE, IDM_VIEW_IN_IE
- Channel: menu, mcp
- Steps: `e2e_menu` each of the four ids; `e2e_menu` path "View|View Current File in" tree.
- Expect: the submenu lists Firefox, Chrome, Edge, Safari; IDM_VIEW_IN_FIREFOX is "Firefox", IDM_VIEW_IN_CHROME "Chrome", IDM_VIEW_IN_EDGE "Edge", IDM_VIEW_IN_IE "Safari" (the port's stand-in for IE); no id resolves to null and no two ids resolve to the same item.

## Window modes

### VIEW-007: Always on Top floats the window and puts it back
- Covers: IDM_VIEW_ALWAYSONTOP
- Channel: mcp, ui
- Steps: Read the main window's `level` (`e2e_windows`); run IDM_VIEW_ALWAYSONTOP; read it; run it again; read it.
- Expect: level 0, then 3 (floating), then 0; the tab bar and status bar stay visible throughout; the document is untouched.

### VIEW-008: The -alwaysOnTop launch switch starts the window on top
- Covers: IDM_VIEW_ALWAYSONTOP
- Channel: launch, menu
- Steps: `app.start(args=["-alwaysOnTop"])`; read the window level and the menu checkmark; run IDM_VIEW_ALWAYSONTOP.
- Expect: level 3 at start and the item checked; after the command level 0 and unchecked.

### VIEW-009: Toggle Full Screen Mode enters and leaves full screen
- Covers: IDM_VIEW_FULLSCREENTOGGLE
- Channel: mcp, keys, ui
- Steps: Run IDM_VIEW_FULLSCREENTOGGLE; wait (poll up to 5 s) until `window.styleMask` has bit 1<<14; read the window frame; run it again (then once more with `ctrl+cmd+f` pairs) and wait until the bit is gone.
- Expect: in full screen the frame covers the whole screen and the document text/caret are unchanged; afterwards the style mask has no full-screen bit and the frame is the one from before (within 2 px); the key chord does the same as the command.

### VIEW-010: Post-It hides the chrome and floats the window, and toggles back
- Covers: IDM_VIEW_POSTIT
- Channel: mcp, ui
- Steps: Open a saved file; run IDM_VIEW_POSTIT; read `e2e_ui` of the main window and its level; type "x"; run IDM_VIEW_POSTIT again.
- Expect: in Post-It no NppStatusPathField / status NSTextField is visible, `editor.chromeVisible` is false, the window level is 3, typing still edits the document; after the second run the status bar is back, `chromeVisible` true, level 0.

### VIEW-011: Leaving Post-It keeps a previous Always on Top
- Covers: IDM_VIEW_POSTIT, IDM_VIEW_ALWAYSONTOP
- Channel: mcp, ui
- Steps: Run IDM_VIEW_ALWAYSONTOP; run IDM_VIEW_POSTIT twice; read level and the Always on Top checkmark; run IDM_VIEW_ALWAYSONTOP.
- Expect: after the Post-It round trip the window is still at level 3 (Always on Top was on before Post-It, as Notepad++ restores `_beforeSpecialView._isAlwaysOnTop`); the final command lowers it to 0.

### VIEW-012: Post-It does nothing while Distraction Free is on
- Covers: IDM_VIEW_POSTIT, IDM_VIEW_DISTRACTIONFREE
- Channel: mcp, ui
- Steps: Run IDM_VIEW_DISTRACTIONFREE; run IDM_VIEW_POSTIT; read chrome and level; run IDM_VIEW_DISTRACTIONFREE.
- Expect: after Post-It the chrome is still hidden and the level still 0 (the command is ignored in Distraction Free, as upstream's IDM_VIEW_POSTIT checks `_isDistractionFree`); leaving Distraction Free shows tab bar and status bar again with level 0.

### VIEW-013: Distraction Free hides the chrome and centres the text
- Covers: IDM_VIEW_DISTRACTIONFREE
- Channel: mcp, ui, prefs
- Steps: Set pref `distractionFreeDivPart` 4; new document with a 300-character line; run IDM_VIEW_DISTRACTIONFREE; read SCI_GETMARGINLEFT, SCI_GETMARGINRIGHT and the ScintillaView width from `e2e_ui`; run it again; read the margins.
- Expect: in the mode the status bar and path field are gone and `editor.chromeVisible` is false; the left margin is a quarter of the view's width (±1 px); after leaving, the chrome is back and SCI_GETMARGINLEFT is at most 9.

### VIEW-014: The Distraction Free width follows Preferences
- Covers: IDM_VIEW_DISTRACTIONFREE
- Channel: prefs, mcp
- Steps: For each of `distractionFreeDivPart` 3, 5, 6: set the pref, enter Distraction Free, read SCI_GETMARGINLEFT and the view width, leave.
- Expect: the left margin is the width divided by the value (±1 px) each time; the pref is restored at the end.

### VIEW-015: Distraction Free stays on across tab changes
- Covers: IDM_VIEW_DISTRACTIONFREE, IDM_VIEW_TAB_NEXT
- Channel: mcp, ui
- Steps: With two documents enter Distraction Free; run IDM_VIEW_TAB_NEXT; open a new document (`open_document` text "z"); read the chrome.
- Expect: the tab bar and status bar stay hidden after the tab change and the new document; the margins are still the centred ones; leaving restores everything.

## Show Symbol

### VIEW-016: Show Space and Tab shows whitespace in both views and is remembered
- Covers: IDM_VIEW_TAB_SPACE
- Channel: mcp, prefs, snapshot
- Steps: New document "a\tb  c\n", clone it to the other view; snapshot; run IDM_VIEW_TAB_SPACE; read SCI_GETVIEWWS on main and sub and pref `showWhitespace`; snapshot; run it again.
- Expect: SCI_GETVIEWWS is 1 on both views and `showWhitespace` true after the first run; the second snapshot differs from the first in the text area (dots/arrows drawn); after the second run both views are 0 and the pref false; text unchanged, document not modified.

### VIEW-017: Show Space and Tab survives a restart
- Covers: IDM_VIEW_TAB_SPACE
- Channel: mcp, launch, prefs
- Steps: Run IDM_VIEW_TAB_SPACE; `app.restart()`; open a new document; read SCI_GETVIEWWS; turn it off again.
- Expect: whitespace is visible (1) in the restarted application's new document.

### VIEW-018: Show End of Line shows line ends in both views, for later documents and after a restart
- Covers: IDM_VIEW_EOL
- Channel: mcp, launch
- Steps: Clone a document "a\r\nb\n" to the other view; run IDM_VIEW_EOL; read SCI_GETVIEWEOL on main and sub; open another document; read it; restart; read it on a new document; run IDM_VIEW_EOL to turn it off.
- Expect: 1 on main and on sub, 1 for the later document, 1 after the restart (Notepad++ keeps the setting and applies it to both views); 0 after turning it off.

### VIEW-019: Show Indent Guide in both views and from the toolbar
- Covers: IDM_VIEW_INDENT_GUIDE
- Channel: mcp, ui
- Steps: Clone a Python document "if x:\n    y = 1\n"; read SCI_GETINDENTATIONGUIDES on main and sub; run IDM_VIEW_INDENT_GUIDE; read; press toolbar item "Indent Guide"; read.
- Expect: the default is on (SC_IV_LOOKBOTH = 3) on both views; after the command 0 on both views; after the toolbar button 3 on both again.

### VIEW-020: Show Wrap Symbol marks wrapped lines
- Covers: IDM_VIEW_WRAP_SYMBOL, IDM_VIEW_WRAP
- Channel: mcp, snapshot
- Steps: New document with one 400-character line; run IDM_VIEW_WRAP; snapshot; run IDM_VIEW_WRAP_SYMBOL; read SCI_GETWRAPVISUALFLAGS on main (and on sub after cloning); snapshot; run both commands again.
- Expect: flags are SC_WRAPVISUALFLAG_END (1) on both views after the command and 0 after the second; the second snapshot differs from the first near the right edge of the wrapped rows; text unchanged.

### VIEW-021: Show Non-Printing Characters shows invisible characters by name
- Covers: IDM_VIEW_NPC
- Channel: mcp, prefs
- Steps: New document "a\u00a0b\u200bc\n"; read SCI_GETREPRESENTATION of U+00A0 and U+200B; run IDM_VIEW_NPC; read them; set pref `npcCodepoint` true (apply) and read again; set it back; run IDM_VIEW_NPC.
- Expect: no representation before; "NBSP" and "ZWSP" after the command; "U+00A0" and "U+200B" with the code-point preference; none after turning it off; pref `npcShow` follows the toggle; text unchanged.

### VIEW-022: Show Control Characters & Unicode EOL shows or hides C0 controls
- Covers: IDM_VIEW_NPC_CCUNIEOL
- Channel: mcp, prefs
- Steps: New document "a\u0001b\u2028c\n"; read SCI_GETREPRESENTATION of U+0001 and U+2028; run IDM_VIEW_NPC_CCUNIEOL; read them; run it again.
- Expect: on by default: U+0001 shown as "SOH" and U+2028 as "LS"; after the command the control character is hidden (its representation is a zero-width space) and pref `ccUniEolShow` is false; after the second run "SOH" is back.

### VIEW-023: Symbols apply to the second view and to documents opened later
- Covers: IDM_VIEW_TAB_SPACE, IDM_VIEW_NPC, IDM_VIEW_NPC_CCUNIEOL, IDM_VIEW_INDENT_GUIDE, IDM_VIEW_WRAP_SYMBOL, IDM_VIEW_EOL
- Channel: mcp
- Steps: For each of the six commands: with a document cloned to the second view, run the command, then open a new document in the main view and move it to the other view (IDM_VIEW_GOTO_ANOTHER_VIEW); read the symbol's Scintilla state on `sub`; run the command again.
- Expect: the second view shows the same symbol state as the main view in every case.

### VIEW-024: Showing symbols never changes the text
- Covers: IDM_VIEW_TAB_SPACE, IDM_VIEW_EOL, IDM_VIEW_NPC, IDM_VIEW_NPC_CCUNIEOL, IDM_VIEW_ALL_CHARACTERS, IDM_VIEW_INDENT_GUIDE, IDM_VIEW_WRAP_SYMBOL
- Channel: mcp
- Steps: Open a saved file with tabs, CRLF, U+00A0 and U+0001; run each symbol command twice; save; compare the file on disk.
- Expect: the document is not marked modified at any point; SCI_CANUNDO stays 0; the bytes on disk are unchanged.

## Zoom

### VIEW-025: Zoom In, Zoom Out and Restore Default Zoom
- Covers: IDM_VIEW_ZOOMIN, IDM_VIEW_ZOOMOUT, IDM_VIEW_ZOOMRESTORE
- Channel: mcp
- Steps: Run IDM_VIEW_ZOOMIN three times, IDM_VIEW_ZOOMOUT once, IDM_VIEW_ZOOMRESTORE; read SCI_GETZOOM after each.
- Expect: 1, 2, 3, then 2, then 0; the text and caret position are unchanged.

### VIEW-026: Zoom stops at its limits
- Covers: IDM_VIEW_ZOOMIN, IDM_VIEW_ZOOMOUT, IDM_VIEW_ZOOMRESTORE
- Channel: mcp
- Steps: Run IDM_VIEW_ZOOMOUT 20 times; read SCI_GETZOOM; run IDM_VIEW_ZOOMIN 80 times; read it twice (after 79 and 80); run IDM_VIEW_ZOOMRESTORE.
- Expect: zoom out stops at -10; zoom in stops at a maximum (the value after 79 and 80 runs is the same and positive); restore gives 0; no error from any run.

### VIEW-027: Zoom buttons on the toolbar
- Covers: IDM_VIEW_ZOOMIN, IDM_VIEW_ZOOMOUT
- Channel: ui
- Steps: `e2e_act action=toolbar value="Zoom In"` twice, then "Zoom Out" once.
- Expect: SCI_GETZOOM goes 1, 2, 1.

### VIEW-028: Zoom belongs to the view, not the document
- Covers: IDM_VIEW_ZOOMIN, IDM_VIEW_ZOOMRESTORE, IDM_VIEW_CLONE_TO_ANOTHER_VIEW
- Channel: mcp
- Steps: With two documents zoom in twice; switch to the other tab (IDM_VIEW_TAB_NEXT); read SCI_GETZOOM; clone to the other view; read zoom on `sub`.
- Expect: the zoom is still 2 after the tab change; the second view keeps its own zoom (0) while synchronization is off.

### VIEW-029: Synchronize Zoom Across Views mirrors zoom both ways
- Covers: IDM_VIEW_ZOOM_SYNC, IDM_VIEW_ZOOMIN, IDM_VIEW_ZOOMOUT
- Channel: mcp
- Steps: Clone a document to the other view; run IDM_VIEW_ZOOM_SYNC; zoom in on main (IDM_VIEW_ZOOMIN); read zoom on both; set zoom 4 on `sub` with SCI_SETZOOM, let the run loop turn; read main; run IDM_VIEW_ZOOM_SYNC to switch off; zoom in on main.
- Expect: both 1 after the zoom in; main follows the second view to 4; after switching off only main changes (5 vs 4).

### VIEW-030: Zoom still works with zoom and vertical synchronization both on
- Covers: IDM_VIEW_ZOOM_SYNC, IDM_VIEW_SYNSCROLLV, IDM_VIEW_ZOOMIN
- Channel: mcp
- Steps: Clone a 400-line document to the other view; run IDM_VIEW_ZOOM_SYNC and IDM_VIEW_SYNSCROLLV; run IDM_VIEW_ZOOMIN; let the run loop turn; read SCI_GETZOOM on both views.
- Expect: both views are at zoom 1 (the zoom-in is not undone by the mirror of the other view).

## Word wrap

### VIEW-031: Word wrap wraps long lines in both views without touching the text
- Covers: IDM_VIEW_WRAP
- Channel: mcp, prefs, menu
- Steps: New document with a 500-character line of words, cloned to the other view; run IDM_VIEW_WRAP; read SCI_GETWRAPMODE on both, SCI_WRAPCOUNT of line 0, pref `wordWrap`, the checkmark; run it again.
- Expect: wrap mode SC_WRAP_WORD (1) on both views, line 0 takes more than one visual row, `wordWrap` true, item checked; afterwards mode 0 on both, one row, pref false, unchecked; the text is unchanged and the document not modified.

### VIEW-032: Word wrap from the toolbar button
- Covers: IDM_VIEW_WRAP
- Channel: ui
- Steps: `e2e_act action=toolbar value="Word Wrap"`; read SCI_GETWRAPMODE; press it again.
- Expect: 1 then 0, the same as the menu command.

### VIEW-033: Word wrap is remembered and applies to files opened later
- Covers: IDM_VIEW_WRAP
- Channel: mcp, launch
- Steps: Run IDM_VIEW_WRAP; open a saved file; read SCI_GETWRAPMODE; `app.restart()`; open a new document; read it; turn wrap off.
- Expect: 1 for the later file and 1 after the restart.

## Folding

### VIEW-034: Fold All and Unfold All
- Covers: IDM_VIEW_FOLDALL, IDM_VIEW_UNFOLDALL
- Channel: mcp
- Steps: C++ document "int f() {\n  if (x) {\n    y();\n  }\n}\nint g() {\n  z();\n}\n"; run IDM_VIEW_FOLDALL; read SCI_GETLINEVISIBLE of lines 1-4 and 6 and SCI_GETFOLDEXPANDED of lines 0 and 5; run IDM_VIEW_UNFOLDALL; read them again.
- Expect: after Fold All (0-based) lines 1-4 and 6-7 are hidden, lines 0 and 5 visible and contracted; after Unfold All every line is visible and every header expanded; the text is unchanged.

### VIEW-035: Folding commands on a document without folding do nothing
- Covers: IDM_VIEW_FOLDALL, IDM_VIEW_UNFOLDALL, IDM_VIEW_FOLD_CURRENT, IDM_VIEW_UNFOLD_CURRENT, IDM_VIEW_FOLD_1
- Channel: mcp
- Steps: Plain-text document of 5 lines; run each command.
- Expect: every command answers `ran: true`; every line stays visible; text unchanged.

### VIEW-036: Fold Current Level folds the block the caret is in
- Covers: IDM_VIEW_FOLD_CURRENT, IDM_VIEW_UNFOLD_CURRENT
- Channel: mcp
- Steps: The C++ document of VIEW-034; caret on 1-based line 3 (`y();`, inside the `if` block); run IDM_VIEW_FOLD_CURRENT; read visibility; run IDM_VIEW_UNFOLD_CURRENT; then caret on 1-based line 1 (`int f() {`, a header) and run IDM_VIEW_FOLD_CURRENT again.
- Expect: only the `if` header (0-based line 1) is contracted: 0-based lines 2-3 hidden, lines 0, 1, 4-7 visible, line 0 and line 5 still expanded; Unfold Current Level shows lines 2-3 again; with the caret on the header line `int f() {` that header is the one folded (lines 1-4 hidden, `g` untouched).

### VIEW-037: Fold/Unfold Current Level toggle when Preferences makes them toggleable
- Covers: IDM_VIEW_FOLD_CURRENT, IDM_VIEW_UNFOLD_CURRENT
- Channel: prefs, mcp
- Steps: Set pref `foldCommandsToggle` true; caret inside the `if` block; run IDM_VIEW_FOLD_CURRENT twice; run IDM_VIEW_UNFOLD_CURRENT twice; restore the pref.
- Expect: the first run folds, the second unfolds; Unfold Current Level likewise folds then unfolds.

### VIEW-038: Fold Level N folds exactly the headers of level N
- Covers: IDM_VIEW_FOLD_1, IDM_VIEW_FOLD_2, IDM_VIEW_FOLD_3, IDM_VIEW_FOLD_4, IDM_VIEW_FOLD_5, IDM_VIEW_FOLD_6, IDM_VIEW_FOLD_7, IDM_VIEW_FOLD_8
- Channel: mcp
- Steps: For each N in 1..8: a C++ document with blocks nested 8 deep (one `{` per line, each on its own line, closed in reverse); run IDM_VIEW_UNFOLDALL, then IDM_VIEW_FOLD_N; read SCI_GETFOLDEXPANDED of every header line.
- Expect: exactly the header whose depth is N-1 (0-based fold level) is contracted, every other header expanded; lines inside it hidden, lines above it visible.

### VIEW-039: Unfold Level N expands exactly the headers of level N
- Covers: IDM_VIEW_UNFOLD_1, IDM_VIEW_UNFOLD_2, IDM_VIEW_UNFOLD_3, IDM_VIEW_UNFOLD_4, IDM_VIEW_UNFOLD_5, IDM_VIEW_UNFOLD_6, IDM_VIEW_UNFOLD_7, IDM_VIEW_UNFOLD_8
- Channel: mcp
- Steps: For each N in 1..8: the 8-deep document; run IDM_VIEW_FOLDALL (which contracts every header), then IDM_VIEW_UNFOLD_N; read SCI_GETFOLDEXPANDED of every header.
- Expect: the headers of depth 0..N-1 are expanded (the level-N header is opened, and Scintilla shows its hidden parents first, as upstream), the deeper ones still contracted.

### VIEW-040: Fold levels deeper than the document change nothing
- Covers: IDM_VIEW_FOLD_5, IDM_VIEW_FOLD_8, IDM_VIEW_UNFOLD_5, IDM_VIEW_UNFOLD_8
- Channel: mcp
- Steps: The two-level C++ document of VIEW-034 fully expanded; run IDM_VIEW_FOLD_5 and IDM_VIEW_FOLD_8; then fold all and run IDM_VIEW_UNFOLD_5 and IDM_VIEW_UNFOLD_8.
- Expect: the fold state is exactly what it was before each pair of commands.

### VIEW-041: Folding in other lexers
- Covers: IDM_VIEW_FOLDALL, IDM_VIEW_UNFOLDALL, IDM_VIEW_FOLD_1
- Channel: mcp
- Steps: For each of Python ("def f():\n    if x:\n        y()\n"), HTML ("<div>\n<p>\nx\n</p>\n</div>\n"), XML ("<a>\n <b>\n  c\n </b>\n</a>\n"), JSON ("{\n \"a\": [\n  1\n ]\n}\n"): run IDM_VIEW_FOLDALL, read visibility of line 1; run IDM_VIEW_UNFOLDALL; run IDM_VIEW_FOLD_1.
- Expect: Fold All hides line 1 in each; Unfold All shows it; Fold Level 1 contracts the outermost header (line 0) and hides line 1.

### VIEW-042: Folds belong to the document
- Covers: IDM_VIEW_FOLDALL, IDM_VIEW_TAB_NEXT, IDM_VIEW_TAB_PREV
- Channel: mcp
- Steps: Saved C++ file with two functions; contract the second function only (fold level via IDM_VIEW_FOLD_CURRENT with the caret in it); switch to another tab and back.
- Expect: the second function is still contracted and the first expanded.

## Hide lines

### VIEW-043: Hide Lines hides the selected lines until Show All Hidden Lines
- Covers: IDM_VIEW_HIDELINES
- Channel: mcp, menu
- Steps: Document "1\n2\n3\n4\n5\n6\n"; select from line 2 column 1 to line 4 column 2; run IDM_VIEW_HIDELINES; read SCI_GETLINEVISIBLE of lines 0-5; `e2e_menu_invoke` "View|Show All Hidden Lines".
- Expect: lines 1-3 (0-based) hidden, 0, 4, 5 visible; the text and length are unchanged; after Show All Hidden Lines every line is visible.

### VIEW-044: Hide Lines with no selection hides the caret line
- Covers: IDM_VIEW_HIDELINES
- Channel: mcp
- Steps: Caret on line 3 of a 6-line document, empty selection; run IDM_VIEW_HIDELINES.
- Expect: only line 2 (0-based) is hidden.

### VIEW-045: Hidden lines are still part of the document
- Covers: IDM_VIEW_HIDELINES
- Channel: mcp, files, clipboard
- Steps: Saved file of 6 lines; hide lines 2-4; select all and copy; save as another file (queued panel answer).
- Expect: the clipboard holds all 6 lines; the saved file has all 6 lines; `get_document` returns them.

## Summary

### VIEW-046: Summary reports the document's counts
- Covers: IDM_VIEW_SUMMARY
- Channel: modal, mcp
- Steps: New document "foo_bar a#b 1,000 O'Connel\n"; queue alert answer 1; run IDM_VIEW_SUMMARY; read the modal log.
- Expect: one alert titled "Summary" whose text is "Characters: 27\nBytes: 27\nWords: 6\nLines: 2\nSelected bytes: 0".

### VIEW-047: Summary counts words the way Notepad++ does
- Covers: IDM_VIEW_SUMMARY
- Channel: modal
- Steps: For each text: "" → 0 words; "one" → 1; "a-b c.d e/f" → 6; "x=1;y=2" → 4; "tab\tsep\nnew line" → 4; "   " → 0: set the text, run IDM_VIEW_SUMMARY with a queued answer, parse "Words: N".
- Expect: the word counts listed; no alert is left open.

### VIEW-048: Summary counts characters and bytes of multi-byte text
- Covers: IDM_VIEW_SUMMARY
- Channel: modal
- Steps: Document "héllo wörld\n" (UTF-8); run Summary; then select "héllo" and run it again.
- Expect: Characters 12, Bytes 14, Words 2, Lines 2; with the selection "Selected bytes: 6".

### VIEW-049: Summary of an empty and of a CRLF document
- Covers: IDM_VIEW_SUMMARY
- Channel: modal, files
- Steps: Empty new document → Summary; then open a saved file "a\r\nb\r\n" → Summary.
- Expect: empty: Characters 0, Bytes 0, Words 0, Lines 1, Selected bytes 0; CRLF file: Bytes 6, Lines 3, Words 2.

## Monitoring (tail -f)

### VIEW-050: Monitoring follows a growing file and keeps it read-only
- Covers: IDM_VIEW_MONITORING
- Channel: mcp, files
- Steps: Save "one\n" to `log.txt` and open it; run IDM_VIEW_MONITORING; append "two\n" to the file from the test; poll `get_document` up to 5 s; read SCI_GETREADONLY and the caret; try typing "x"; run IDM_VIEW_MONITORING again; type "x".
- Expect: while monitored the document is read-only (SCI_GETREADONLY 1, `read_only` true), the text becomes "one\ntwo\n" without any alert, the caret is at the end (position 8), typing changes nothing; after switching off the document is writable and typing inserts "x".

### VIEW-051: Monitoring is refused for an unsaved document
- Covers: IDM_VIEW_MONITORING
- Channel: mcp, menu
- Steps: New unsaved document "abc"; run IDM_VIEW_MONITORING.
- Expect: the document stays writable (SCI_GETREADONLY 0), `editor.monitoringEnabled` false, the item not checked; typing still works.

### VIEW-052: Monitoring is refused for a document with unsaved changes
- Covers: IDM_VIEW_MONITORING
- Channel: mcp
- Steps: Open a saved file, type "x" (modified); run IDM_VIEW_MONITORING; append a line to the file on disk and wait 1 s.
- Expect: not monitored, still writable; the typed "x" is still in the document and no reload happened.

### VIEW-053: A rotated log is followed under its name
- Covers: IDM_VIEW_MONITORING
- Channel: mcp, files
- Steps: Monitor `log.txt` ("old\n"); rename it to `log.txt.1` and write a new `log.txt` "fresh\n"; poll the text; append "more\n".
- Expect: the document becomes "fresh\n" then "fresh\nmore\n" within 5 s each; it stays monitored.

### VIEW-054: A change while another tab is in front is caught up on return
- Covers: IDM_VIEW_MONITORING, IDM_VIEW_TAB_NEXT, IDM_VIEW_TAB_PREV
- Channel: mcp, files
- Steps: Monitor `a.log`; open `b.txt` in front; append "late\n" to `a.log`; wait 1 s; read `a.log`'s text through `get_document document=0`; switch back to it.
- Expect: after switching back the text contains "late" and the caret is at the end; `b.txt` is untouched.

### VIEW-055: Monitoring from the toolbar and in the session
- Covers: IDM_VIEW_MONITORING
- Channel: ui, launch, files
- Steps: Open a saved file; press toolbar item "Monitoring"; restart with `session=True` (the session kept); read the reopened document's state; append to the file.
- Expect: the toolbar button starts monitoring like the menu command; after the restart the file is still monitored (read-only, appended text shows up within 5 s).

### VIEW-056: Closing a monitored document stops watching it
- Covers: IDM_VIEW_MONITORING, IDM_FILE_CLOSE
- Channel: mcp, files
- Steps: Monitor `log.txt`; close its tab; append to the file; reopen it.
- Expect: no document is reopened by the change and no alert appears; the reopened document is writable and not monitored.

## Panels

### VIEW-057: Folder as Workspace shows the current file's folder
- Covers: IDM_VIEW_FILEBROWSER
- Channel: mcp, ui
- Steps: Create a folder with `a.py` and `b.txt`; open `a.py`; run IDM_VIEW_FILEBROWSER; read the workspace outline in `e2e_ui` (NSOutlineView cells) and `isPanelVisible: workspace`; run it again.
- Expect: the panel is visible on the left with the folder as root and `a.py`, `b.txt` below it (after expanding the root); the second run hides it.

### VIEW-058: Folder as Workspace for an unsaved document asks for the folder
- Covers: IDM_VIEW_FILEBROWSER
- Channel: modal, ui
- Steps: New unsaved document; queue a panel answer with a folder path; run IDM_VIEW_FILEBROWSER; then hide it, queue `None` (cancel) and run it again.
- Expect: the first time an open panel was shown (modal log) and the panel shows that folder; after the cancel no workspace panel is visible.

### VIEW-059: Document Map shows a mirror of the document on the right
- Covers: IDM_VIEW_DOC_MAP
- Channel: mcp, ui, snapshot
- Steps: Open a 200-line C file; run IDM_VIEW_DOC_MAP; read `isPanelVisible:`/`placeOfPanel: documentMap` (NppDockingManager) and the map's text through `e2e_sci view=map` (hook); snapshot; run it again.
- Expect: visible, place 1 (right); the map holds the same text as the editor - it is a view on the editor's own document (read-only is the document's, not the map's); the snapshot shows the map column right of the editor; the second run hides it.

### VIEW-060: Document Map follows the tab in front
- Covers: IDM_VIEW_DOC_MAP, IDM_VIEW_TAB_NEXT
- Channel: mcp
- Steps: Map visible; open a second document "second"; switch tabs with IDM_VIEW_TAB_NEXT; read the map's text (hook `e2e_sci view=map`, SCI_GETTEXT) after each switch.
- Expect: the map always shows the text of the document in front.

### VIEW-061: A click in the Document Map scrolls the editor there
- Covers: IDM_VIEW_DOC_MAP
- Channel: ui, mcp
- Steps: A 3000-line document, first visible line 0; show the map; `e2e_act click` on the map's zone view (class NppMapZoneView, clicked in its middle).
- Expect: the map line under the click (its first visible line plus half its lines on screen) comes into the editor's view (DocumentMap::scrollMap: the map shows its own window on a long text, not the whole of it); the caret line is unchanged.

### VIEW-062: Document List lists the open documents and switches to one
- Covers: IDM_VIEW_DOCLIST
- Channel: ui, mcp
- Steps: Open `zeta.txt`, `alpha.py` and a new document; run IDM_VIEW_DOCLIST; read the panel's table cells; `e2e_act double_click` the row of `zeta.txt`; close `alpha.py`; read the table; run IDM_VIEW_DOCLIST again.
- Expect: one row per open document with its name; the double click brings `zeta.txt` to the front; after the close its row is gone; the panel is on the left and the second run hides it.

### VIEW-063: Function List lists the functions and jumps to one
- Covers: IDM_VIEW_FUNC_LIST
- Channel: ui, mcp
- Steps: Open `m.py` = "def alpha():\n    pass\n\nclass Beta:\n    def gamma(self):\n        pass\n"; run IDM_VIEW_FUNC_LIST; read the table cells; `e2e_act double_click` the row of gamma; type "def delta():\n    pass\n" at the end and save (upstream parses the list again on save and activation, not while typing); switch to a plain-text tab.
- Expect: rows "alpha()  (line 1)", "Beta  (line 4)", "Beta::gamma(self)  (line 5)"; the double click puts the caret on line 5; after the edit a delta row appears; for the plain-text tab the list is empty; the panel is on the right.

### VIEW-064: Project Panels 1, 2 and 3 show and hide on their own
- Covers: IDM_VIEW_PROJECT_PANEL_1, IDM_VIEW_PROJECT_PANEL_2, IDM_VIEW_PROJECT_PANEL_3
- Channel: mcp, ui
- Steps: For each N in 1..3: run IDM_VIEW_PROJECT_PANEL_N; read `isPanelVisible: projectN` and the panel's title label; run it again. Then show 1 and 2 together.
- Expect: the panel appears (on the left) with a title starting "Project Panel N" and an empty tree whose root is "Workspace"; the same command again hides it; panels 1 and 2 can be shown at once as two tabs of the left dock.

### VIEW-065: Panel buttons on the toolbar do what the menu commands do
- Covers: IDM_VIEW_DOC_MAP, IDM_VIEW_DOCLIST, IDM_VIEW_FUNC_LIST, IDM_VIEW_FILEBROWSER
- Channel: ui
- Steps: With a saved file open, for each toolbar item "Document Map", "Document List", "Function List", "Folder as Workspace": press it, read the panel's visibility, press it again.
- Expect: visible after the first press, hidden after the second, exactly as the menu commands.

## Two views

### VIEW-066: Clone to Other View shows the same buffer in both views
- Covers: IDM_VIEW_CLONE_TO_ANOTHER_VIEW
- Channel: mcp, ui
- Steps: Open `a.txt` ("one\n") and `b.txt`; with `b.txt` in front run IDM_VIEW_CLONE_TO_ANOTHER_VIEW; type "X" in the main view; read `sub`'s text (SCI_GETTEXT); read `list_documents`.
- Expect: two ScintillaViews in `e2e_ui`; the second view shows `b.txt` and has "X" too; `list_documents` still has one entry for `b.txt`, now with `in_second_view: true`; styles of both views match (SCI_STYLEGETFORE of styles 0-10 equal).

### VIEW-067: Move to Other View takes the tab out of the main view
- Covers: IDM_VIEW_GOTO_ANOTHER_VIEW
- Channel: mcp
- Steps: Open `a.txt` and `b.txt`, modify `b.txt` ("changed"); run IDM_VIEW_GOTO_ANOTHER_VIEW; read the main tab bar titles (`editor.tabBar.items.title`) and `sub`'s text.
- Expect: the main tab bar has only `a.txt`; the second view shows "changed"; the change is kept (the document is still modified when brought back).

### VIEW-068: Move to Other View with a single document clones it
- Covers: IDM_VIEW_GOTO_ANOTHER_VIEW
- Channel: mcp
- Steps: Close all; open `a.txt` only; run IDM_VIEW_GOTO_ANOTHER_VIEW.
- Expect: the main view keeps `a.txt` (never an empty main view) and the second view shows it too.

### VIEW-069: Focus on Another View moves the keyboard focus between views
- Covers: IDM_VIEW_SWITCHTO_OTHER_VIEW
- Channel: mcp, keys, ui
- Steps: Clone a document "ab" to the other view, caret at 0 in main and 2 in sub; run IDM_VIEW_SWITCHTO_OTHER_VIEW; read `editor.otherViewHasFocus`; type "Z"; run it again; type "Y".
- Expect: focus is on the second view after the first run and "Z" is typed at its caret; after the second run focus is back and "Y" goes in at the main caret.

### VIEW-070: Focus on Another View with one view does nothing
- Covers: IDM_VIEW_SWITCHTO_OTHER_VIEW
- Channel: mcp, ui
- Steps: No second view; run IDM_VIEW_SWITCHTO_OTHER_VIEW; read the first responder.
- Expect: the main editor keeps the focus; no second view appears.

### VIEW-071: Synchronize Vertical Scrolling scrolls both views together
- Covers: IDM_VIEW_SYNSCROLLV
- Channel: mcp
- Steps: Clone a 400-line document; run IDM_VIEW_SYNSCROLLV; SCI_SETFIRSTVISIBLELINE 100 on main, let the run loop turn, read `sub`; SCI_SETFIRSTVISIBLELINE 200 on `sub`, read main; switch it off; scroll main to 50.
- Expect: sub at 100; main at 200; after switching off sub stays at 200.

### VIEW-072: Synchronize Horizontal Scrolling scrolls both views sideways and the application stays responsive
- Covers: IDM_VIEW_SYNSCROLLH
- Channel: mcp
- Steps: Clone a 400-line document of 300-character lines; run IDM_VIEW_SYNSCROLLH (with a 10 s call timeout); SCI_SETXOFFSET 50 on main; read `sub`'s x offset; run IDM_VIEW_SYNSCROLLH again.
- Expect: every call returns within 10 s; sub's offset is 50; after switching off an offset change on main leaves sub alone.

### VIEW-073: Synchronization commands without a second view are harmless
- Covers: IDM_VIEW_SYNSCROLLV, IDM_VIEW_SYNSCROLLH, IDM_VIEW_ZOOM_SYNC
- Channel: mcp
- Steps: One view only; run each sync command, scroll and zoom the main view, run each again.
- Expect: all run, no second view appears, zoom and scroll of the main view work normally.

### VIEW-074: Move / Open in New Instance decline for an unsaved document
- Covers: IDM_VIEW_GOTO_NEW_INSTANCE, IDM_VIEW_LOAD_IN_NEW_INSTANCE
- Channel: mcp
- Steps: New unsaved document "keep"; run IDM_VIEW_GOTO_NEW_INSTANCE, then IDM_VIEW_LOAD_IN_NEW_INSTANCE.
- Expect: the document is still open with "keep"; the number of documents is unchanged; no process was launched (hook `e2e_launches` empty).

### VIEW-075: Open in New Instance hands the file to a new instance and keeps it here
- Covers: IDM_VIEW_LOAD_IN_NEW_INSTANCE
- Channel: mcp, files
- Steps: Open saved `a.txt`; run IDM_VIEW_LOAD_IN_NEW_INSTANCE with the launch intercepted (hook `e2e_launches`: records NSWorkspace open requests instead of performing them).
- Expect: one request: the application's own bundle, the file URL of `a.txt`, "creates new instance" set; `a.txt` is still open here.

### VIEW-076: Move to New Instance hands the file over and closes it here
- Covers: IDM_VIEW_GOTO_NEW_INSTANCE
- Channel: mcp, files
- Steps: Open saved `a.txt` and `b.txt`, `a.txt` in front; run IDM_VIEW_GOTO_NEW_INSTANCE with the launch intercepted (hook `e2e_launches`).
- Expect: one request for `a.txt` with a new instance; `a.txt` is no longer among the open documents; `b.txt` is in front.

### VIEW-077: View Current File in a browser
- Covers: IDM_VIEW_IN_FIREFOX, IDM_VIEW_IN_CHROME, IDM_VIEW_IN_EDGE, IDM_VIEW_IN_IE
- Channel: mcp, files
- Steps: For each of the four commands: first with an unsaved document, then with saved `page.html`, the opening intercepted (hook `e2e_launches`).
- Expect: unsaved: nothing requested and the document is unchanged; saved: one request to open `page.html` with the browser's bundle id (org.mozilla.firefox, com.google.Chrome, com.microsoft.edgemac, com.apple.Safari) when the browser is installed, none otherwise; the document stays open in either case.

## Tabs

### VIEW-078: Go to the Nth tab
- Covers: IDM_VIEW_TAB1, IDM_VIEW_TAB2, IDM_VIEW_TAB3, IDM_VIEW_TAB4, IDM_VIEW_TAB5, IDM_VIEW_TAB6, IDM_VIEW_TAB7, IDM_VIEW_TAB8, IDM_VIEW_TAB9
- Channel: mcp
- Steps: Open files `t1.txt`..`t9.txt` (close the empty `new 1` first); for each N in 1..9 run IDM_VIEW_TABN.
- Expect: the current document is `tN.txt` (list_documents `current`) and the tab bar's selected index is N-1.

### VIEW-079: Cmd+1 to Cmd+9 go to the tabs from the keyboard
- Covers: IDM_VIEW_TAB1, IDM_VIEW_TAB2, IDM_VIEW_TAB3, IDM_VIEW_TAB4, IDM_VIEW_TAB5, IDM_VIEW_TAB6, IDM_VIEW_TAB7, IDM_VIEW_TAB8, IDM_VIEW_TAB9
- Channel: keys
- Steps: The nine files of VIEW-078; for each N press `cmd+N` in the editor.
- Expect: the current document is `tN.txt` each time.

### VIEW-080: Going to a tab that does not exist changes nothing
- Covers: IDM_VIEW_TAB4, IDM_VIEW_TAB9
- Channel: mcp, keys
- Steps: Three documents, the second in front; run IDM_VIEW_TAB4, IDM_VIEW_TAB9 and press `cmd+9`.
- Expect: the second document stays in front; the tab order is unchanged.

### VIEW-081: First Tab and Last Tab
- Covers: IDM_VIEW_TAB_START, IDM_VIEW_TAB_END
- Channel: mcp
- Steps: Five documents, the third in front; run IDM_VIEW_TAB_START; run IDM_VIEW_TAB_END.
- Expect: the first document, then the fifth, is current.

### VIEW-082: Next and Previous Tab wrap around the ends
- Covers: IDM_VIEW_TAB_NEXT, IDM_VIEW_TAB_PREV
- Channel: mcp
- Steps: Three documents, the last in front; run IDM_VIEW_TAB_NEXT; run IDM_VIEW_TAB_PREV twice. Then with a single document run both.
- Expect: Next from the last goes to the first; Previous from the first goes to the last, then to the second; with one document nothing changes and no error.

### VIEW-083: Each tab gets its caret and selection back
- Covers: IDM_VIEW_TAB_NEXT, IDM_VIEW_TAB_PREV
- Channel: mcp
- Steps: In document A select line 2 columns 3-6; switch to B, put its caret at line 1 column 2; IDM_VIEW_TAB_PREV; read the selection; IDM_VIEW_TAB_NEXT; read the caret.
- Expect: A's selection is line 2 columns 3-6 again; B's caret is line 1 column 2.

### VIEW-084: Move Tab Forward and Backward
- Covers: IDM_VIEW_TAB_MOVEFORWARD, IDM_VIEW_TAB_MOVEBACKWARD
- Channel: mcp
- Steps: Documents A, B, C with A in front; run IDM_VIEW_TAB_MOVEFORWARD twice; read the tab titles; run IDM_VIEW_TAB_MOVEBACKWARD once.
- Expect: order B, C, A with A still current; then B, A, C; the document contents are unchanged.

### VIEW-085: Moving a tab past either end changes nothing
- Covers: IDM_VIEW_TAB_MOVEFORWARD, IDM_VIEW_TAB_MOVEBACKWARD
- Channel: mcp
- Steps: A, B, C; with A in front run IDM_VIEW_TAB_MOVEBACKWARD; with C in front run IDM_VIEW_TAB_MOVEFORWARD.
- Expect: the order stays A, B, C both times and the current tab stays.

### VIEW-086: Move to Start and Move to End
- Covers: IDM_VIEW_GOTO_START, IDM_VIEW_GOTO_END
- Channel: mcp
- Steps: Documents A-E, C in front; run IDM_VIEW_GOTO_START; run IDM_VIEW_GOTO_END.
- Expect: order C, A, B, D, E, then A, B, D, E, C; C current throughout.

### VIEW-087: Moving tabs keeps pinned tabs first
- Covers: IDM_VIEW_GOTO_START, IDM_VIEW_TAB_MOVEBACKWARD
- Channel: mcp
- Steps: A, B, C; pin A (tab menu "Pin Tab", `e2e_menu_invoke context=tab`, with A in front); bring C in front; run IDM_VIEW_GOTO_START; then with B second run IDM_VIEW_TAB_MOVEBACKWARD.
- Expect: after Move to Start the order is A, C, B (C goes to the start of the unpinned run, A stays first); moving B backward does not put it before A.

### VIEW-088: Tab colours 1 to 5 and Remove Color
- Covers: IDM_VIEW_TAB_COLOUR_1, IDM_VIEW_TAB_COLOUR_2, IDM_VIEW_TAB_COLOUR_3, IDM_VIEW_TAB_COLOUR_4, IDM_VIEW_TAB_COLOUR_5, IDM_VIEW_TAB_COLOUR_NONE
- Channel: mcp, snapshot
- Steps: Two documents, the second in front; for each C in 1..5 run IDM_VIEW_TAB_COLOUR_C, read `editor.tabBar.items.colour`, snapshot and sample the tab's strip; then IDM_VIEW_TAB_COLOUR_NONE.
- Expect: the colour list is [0, C] each time (only the current tab); the strip's dominant hue is red, orange, yellow, green, blue for 1..5; after Remove Color [0, 0] and no coloured strip.

### VIEW-089: Tab colours come back with the session
- Covers: IDM_VIEW_TAB_COLOUR_2
- Channel: launch, mcp
- Steps: Open saved `a.txt`, apply Color 2; restart with `session=True`.
- Expect: `a.txt` is reopened with tab colour 2.

## Text direction

### VIEW-090: Text Direction RTL and LTR
- Covers: IDM_EDIT_RTL, IDM_EDIT_LTR
- Channel: mcp, snapshot
- Steps: Document "abc\n"; snapshot; run IDM_EDIT_RTL; read SCI_GETBIDIRECTIONAL; snapshot; run IDM_EDIT_LTR; read it.
- Expect: 2 (SC_BIDIRECTIONAL_R2L) after RTL and 1 (L2R) after LTR; in the RTL snapshot the text's ink is at the right edge of the editor, in the first at the left; the text is unchanged and not modified.

### VIEW-091: Asking for the direction already in force changes nothing
- Covers: IDM_EDIT_RTL, IDM_EDIT_LTR
- Channel: mcp
- Steps: Run IDM_EDIT_LTR on a left-to-right view; run IDM_EDIT_RTL twice.
- Expect: the direction stays 1, then is 2 after both RTL runs; wrap mode and text are unchanged.

### VIEW-092: Text direction applies to the view in front only
- Covers: IDM_EDIT_RTL, IDM_EDIT_LTR, IDM_VIEW_CLONE_TO_ANOTHER_VIEW
- Channel: mcp
- Steps: Clone a document to the other view; run IDM_EDIT_RTL with the main view focused; read SCI_GETBIDIRECTIONAL on main and sub; run IDM_EDIT_LTR.
- Expect: main is 2, sub stays 1; after LTR main is 1.
