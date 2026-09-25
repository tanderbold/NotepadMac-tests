# SETTINGS — Settings menu: Preferences, Style Configurator, Shortcut Mapper, context menu, imports

The Settings menu: the Preferences dialog (23 pages, every option that has an observable effect, set through the dialog's own controls and checked in the editor, the UI or on disk, and again after a restart), the Style Configurator (themes, a style's colour and font, user keywords and extensions, saving the theme), the Shortcut Mapper (listing, filtering, conflicts, removing and assigning keys, shortcuts.xml in the scratch home), Edit Popup ContextMenu (contextMenu.xml), Import plugin(s) / style theme(s) through queued open-panel answers, and the settings folder (Cloud & Link). Conventions for every Preferences case: open the dialog with `run IDM_SETTING_PREFERENCE` (window "Preferences"), show a page by selecting its row in the category table (`act select`, the rows are the page names), find a checkbox by its exact title (leading spaces and the "Group: Field" form included, e.g. "Status Bar: Hide", "    Update silently"), a text field or pop-up as the control on the same row right of its caption label (by frame), change it (`set_state`, `set_value`, `select`), then click "Apply". "Persists" means: `app.restart()` (home and preferences kept), the effect is observed again, and the dialog's control shows the value. Every test that changes a preference uses `fresh_app` or sets it back; tests that depend on colours first set Dark Mode > Appearance to "Light mode" (the machine may be in dark mode). Out of scope here: the Edit menu's EOL/encoding commands (ENCODING/EDIT), what the Language menu does (LANG), the session file itself (SESSION), the toolbar's command buttons (UI), the -settingsDir switch (CLI).

## Preferences dialog

### SETTINGS-001: Preferences opens with Notepad++'s 23 pages in order
- Covers: IDM_SETTING_PREFERENCE
- Channel: menu, ui
- Steps: Run IDM_SETTING_PREFERENCE; read the category table of the "Preferences" window; select each row in turn.
- Expect: the window "Preferences" is visible; the rows are exactly General, Toolbar, Editing 1, Editing 2, Dark Mode, Margins/Border/Edge, New Document, Indentation, Language, Highlighting, Print, Backup, Auto-Completion, Multi-Instance & Date, Delimiter, Performance, Tab Bar, Recent Files History, Default Directory, Searching, Cloud & Link, MISC., Search Engine; selecting a row shows that page (its first control changes); the buttons Apply, Cancel and Reset are present.

### SETTINGS-002: The menu command and Cmd+, toggle the dialog
- Covers: IDM_SETTING_PREFERENCE
- Channel: menu, keys, ui
- Steps: Read the key of IDM_SETTING_PREFERENCE with `menu_item`; press cmd+, with `keys`; run IDM_SETTING_PREFERENCE again.
- Expect: the menu item's key is "cmd+,"; cmd+, shows the Preferences window; running the command while it is shown hides it (toggle).

### SETTINGS-003: Cancel keeps nothing of what was changed
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, prefs
- Steps: On Editing 2 tick "Word wrap" and on General tick "Status Bar: Hide", then click Cancel; open the dialog again.
- Expect: the window closes; SCI_GETWRAPMODE stays SC_WRAP_NONE and the status bar is still shown; prefs wordWrap/statusBarHidden unchanged; reopened, both checkboxes are unticked again.

### SETTINGS-004: Apply keeps the dialog open and the dialog shows settings changed elsewhere
- Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_WRAP
- Channel: ui, menu
- Steps: Open Preferences, click Apply without changes; close it; run IDM_VIEW_WRAP; open Preferences on Editing 2.
- Expect: after Apply the window is still visible and nothing changes in the editor; after View > Word wrap the "Word wrap" checkbox is ticked (the pages are rebuilt from current settings on opening); Apply then does not turn wrap back off.

### SETTINGS-005: Reset puts every preference back to its default
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, prefs
- Steps: With `fresh_app`, set Editing 1 "Enable virtual space" and Tab Bar "Vertical" and Apply; open the dialog and click Reset; afterwards write autoUpdateMode=0 again with `set_prefs`.
- Expect: the dialog closes; SCI_GETVIRTUALSPACEOPTIONS has no SCVS_USERACCESSIBLE; prefs virtualSpace and tabBarVertical read back as their defaults (false / absent); reopened, both checkboxes are unticked.

### SETTINGS-006: Every option applied from the dialog survives a restart
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, prefs, launch
- Steps: With `fresh_app`, for each of (Editing 1 "Enable virtual space" on, Editing 2 "Show Indent Guide" off, Margins "Padding: Left" 5, New Document "Format (Line ending)" "Windows (CR LF)", Tab Bar "Max. tab label length:" 8, Searching "Confirm Replace All" off, Auto-Completion "Characters before it opens" 3) set the control and Apply; restart; open each page.
- Expect: every control shows the value set; the matching preference keys (virtualSpace, showIndentGuides, paddingLeft, defaultEOL=0, tabMaxLabelLength=8, confirmReplaceAll, autoCompleteThreshold=3) are stored in the test domain (`e2e_prefs all`).

### SETTINGS-007: Every checkbox in the dialog is written by Apply
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, prefs
- Steps: With `fresh_app`, for every page, for every checkbox on it: flip its state, click Apply, read the persistent domain with `e2e_prefs all`, flip it back and Apply. Skip "Let AI agents drive the editor (MCP)" when it would turn the server off (checked separately in SETTINGS-089).
- Expect: each flip changes exactly one stored key to the new value; known failures: "Work the language out from the contents when the name does not say" (detectLanguageFromContent) and "Git: mark lines changed since the last commit in the margin" (gitMarginMarks) are never written by Apply (xfail, BUG).

## General

### SETTINGS-008: Localization changes the interface language and persists
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, menu, launch
- Steps: With `fresh_app`, on General select "Français" in the Localization pop-up and Apply; read the main menu's top titles; restart; then select "English (english)" and Apply.
- Expect: after Apply the top menus are French (e.g. "Fichier", "Édition"), the dialog's page names are translated; after restart they are still French and pref localizationFile is "french.xml"; back to English, the menus read "File", "Edit" and the pref is empty.

### SETTINGS-009: Remember current session for next launch
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, files, launch
- Steps: With `fresh_app`, tick "Remember current session for next launch", Apply; open two files from `tmp`; restart with `session=True`; then untick it, Apply, restart with `session=True`.
- Expect: after the first restart both files are open again; after the second restart they are not (only an empty document); session.xml in the home is written only while the option is on.

### SETTINGS-010: Remember which panels were open, panel by panel
- Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_DOC_MAP, IDM_VIEW_FUNC_LIST
- Channel: ui, launch
- Steps: With `fresh_app`, tick "Remember which panels were open", untick "    Document Map", keep "    Function List" ticked, Apply; show Document Map and Function List; restart.
- Expect: after restart Function List is shown (IDM_VIEW_FUNC_LIST checked) and Document Map is not (IDM_VIEW_DOC_MAP unchecked); pref panelStateKeep has documentMap false.

### SETTINGS-011: Multi-instance radio buttons store the mode
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, prefs, launch
- Steps: With `fresh_app`, click the radio "Always in multi-instance mode", Apply; restart; open General.
- Expect: exactly one of the three radios is on and it is "Always in multi-instance mode" after restart; pref multiInstanceMode is 1; clicking "Default (mono-instance)" and Apply sets it back to 0.

### SETTINGS-012: File Status Auto-Detection asks, updates silently, scrolls to the end
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, files, modal, mcp
- Steps: Open a file from `tmp`; append a line to it on disk; with "File Status Auto-Detection" on and "    Update silently" off, queue alert answer 1 and bring the app to idle; then tick "    Update silently" and "    Scroll to the last line after update", Apply, append again; finally untick "File Status Auto-Detection", Apply, append again.
- Expect: first change: an alert about the file being modified by another program is logged and the text is reloaded; second: no alert, text reloaded, caret/first visible line at the end (SCI_GETCURRENTPOS == length); third: no alert and the text is not reloaded.

### SETTINGS-013: Autodetect character encoding on and off
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, files, mcp
- Steps: Write a Windows-1251 Russian text file into `tmp`; open it with "Autodetect character encoding" on; close it, untick the option, Apply, open it again.
- Expect: with the option on the document's encoding (file_encoding tool) is windows-1251 and the text reads as Russian; with it off the file opens as ANSI/Latin and the text is not the Russian original.

### SETTINGS-014: Status Bar: Hide hides and shows the status bar
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, launch
- Steps: Tick "Status Bar: Hide", Apply; read the main window's controls; restart; untick, Apply.
- Expect: while ticked, the status bar fields (NppStatusPathField and the "length: … Ln: …" field) are not listed as visible; still hidden after restart; unticked, they are visible again.

## Toolbar

### SETTINGS-015: Show the toolbar
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, launch
- Steps: On Toolbar untick "Show the toolbar", Apply; read `ui(main)["toolbar"]["visible"]`; restart; tick it again.
- Expect: the toolbar is not visible while unticked, including after restart; visible again when ticked.

### SETTINGS-016: Toolbar buttons and size reach the window's toolbar
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui
- Steps: For each of "Icons only", "Icons and labels", "Labels only" in "Toolbar buttons", and each of "Regular", "Small" in "Toolbar size": select, Apply, read the window's toolbar display mode and style (`e2e_invoke get window toolbar.displayMode`, `toolbarStyle`).
- Expect: display mode is icon-only (2), icon-and-label (1), label-only (3) respectively; "Icons and labels" or "Regular" gives the expanded toolbar style, "Small" with icons only the unified-compact style.

### SETTINGS-017: Icon set, colour and colorization change the toolbar icons
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, snapshot
- Steps: Set "Color choice" to "Green" and "Colorization" to "Complete", Apply, take a toolbar snapshot; set "Default"/"Partial", Apply, snapshot; select "Filled Fluent UI", Apply, snapshot; set "Custom" with "Color choice: Custom" field "FF00FF", Apply, snapshot.
- Expect: with Green/Complete more than 90% of the New button's opaque pixels are green; with Default under 10%; the filled set differs from the outline set; Custom gives magenta pixels; the preferences toolbarIconColour, toolbarColorizeComplete, toolbarFilledIcons and toolbarIconCustomColour are stored. (Needs a toolbar image hook if the window snapshot does not include the toolbar, see report.)

## Editing 1

### SETTINGS-018: Font name and size apply to the editor
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp, launch
- Steps: On Editing 1 set "Font name:" to "Courier" and "Font size" to 17, Apply; read SCI_STYLEGETFONT and SCI_STYLEGETSIZE of STYLE_DEFAULT; restart.
- Expect: STYLE_DEFAULT uses "Courier" at size 17, and so does a style of the current lexer that has no font of its own; unchanged after restart.

### SETTINGS-019: Caret width and blink rate
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: For each "Caret Settings: Width" item (Hidden, 1 pixel, 2 pixels, 3 pixels) select and Apply; set "Caret Settings: Blink rate" to 0 then 530, Apply.
- Expect: SCI_GETCARETWIDTH is 0, 1, 2, 3 respectively; SCI_GETCARETPERIOD is 0 then 530.

### SETTINGS-020: Current line indicator: none, background, frame with width
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Select "None", Apply; select "Frame" with "Frame: Width" 3, Apply; select "Highlight Background", Apply.
- Expect: None: SCI_GETCARETLINEVISIBLE 0; Frame: visible and SCI_GETCARETLINEFRAME 3; Background: visible and SCI_GETCARETLINEFRAME 0; a frame width of 9 is stored as 6 (clamped 1..6).

### SETTINGS-021: Scrolling beyond the last line and virtual space
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Untick "Enable scrolling beyond last line" and "Enable virtual space", Apply; tick both, Apply; with virtual space on press `right` three times at the end of a short line.
- Expect: off: SCI_GETENDATLASTLINE != 0 and SCI_GETVIRTUALSPACEOPTIONS lacks SCVS_USERACCESSIBLE; on: SCI_GETENDATLASTLINE == 0, the flag is set and the caret's virtual space (SCI_GETSELECTIONNCARETVIRTUALSPACE 0) is 3.

### SETTINGS-022: Copy/Cut line without selection
- Covers: IDM_SETTING_PREFERENCE, IDM_EDIT_COPY, IDM_EDIT_CUT
- Channel: ui, clipboard, mcp
- Steps: Text "first\nsecond\nthird\n", caret on line 2 with no selection; with the option ticked run IDM_EDIT_COPY and IDM_EDIT_CUT; untick it, Apply, put the caret in "first" and run IDM_EDIT_COPY with the clipboard set to "kept".
- Expect: ticked: the clipboard holds "second\n" and Cut leaves "first\nthird\n"; unticked: the clipboard still reads "kept" and the text is unchanged.

### SETTINGS-023: Dragging selected text and keeping the selection on a right click
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp, prefs
- Steps: Untick "Selected text can be dragged", Apply, read SCI_GETDRAGDROPENABLED; tick it, Apply; tick "Keep selection when right-click outside of selection", Apply, select "abc" in "abc def" and right-click at "def" (needs an editor right-click hook, see report); untick and repeat.
- Expect: SCI_GETDRAGDROPENABLED 0 while unticked, 1 while ticked; with "Keep selection" ticked the selection is still 0..3 after the right click, unticked the caret moves to the click and the selection is empty. (rightClickKeepsSelection is stored but used nowhere in the port: xfail, BUG.)

## Editing 2

### SETTINGS-024: Word wrap and the line wrap method
- Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_WRAP
- Channel: ui, mcp, menu
- Steps: Tick "Word wrap", Apply; for each "Line Wrap" item (Default, Aligned, Indent) select and Apply.
- Expect: SCI_GETWRAPMODE != SC_WRAP_NONE and IDM_VIEW_WRAP is checked; SCI_GETWRAPINDENTMODE is SC_WRAPINDENT_FIXED, SC_WRAPINDENT_SAME, SC_WRAPINDENT_INDENT respectively.

### SETTINGS-025: Show Space and Tab, Show Indent Guide
- Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_TAB_SPACE, IDM_VIEW_INDENT_GUIDE
- Channel: ui, mcp, menu
- Steps: Tick "Show Space and Tab" and untick "Show Indent Guide", Apply; then the reverse.
- Expect: SCI_GETVIEWWS != SCWS_INVISIBLE and IDM_VIEW_TAB_SPACE checked, SCI_GETINDENTATIONGUIDES == SC_IV_NONE and IDM_VIEW_INDENT_GUIDE unchecked; then the opposite.

### SETTINGS-026: Smooth font, custom selected-text foreground, Multi-Editing
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Tick "Enable smooth font", "Apply custom color to selected text foreground", untick "Enable Multi-Editing (Cmd+click/selection)", Apply; then the reverse, Apply.
- Expect: first: SCI_GETFONTQUALITY is SC_EFF_QUALITY_LCD_OPTIMIZED, SCI_GETELEMENTISSET(SC_ELEMENT_SELECTION_TEXT) is 1, SCI_GETMULTIPLESELECTION 0; reversed: font quality default, the selection text element not set, SCI_GETMULTIPLESELECTION 1.

### SETTINGS-027: Folding commands toggle when asked
- Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_FOLD_CURRENT
- Channel: ui, mcp
- Steps: C++ text "int f() {\n    return 0;\n}\n", caret on line 2; tick "Make current level folding/unfolding commands toggleable", Apply; run IDM_VIEW_FOLD_CURRENT twice; untick, Apply, run it twice.
- Expect: toggleable: first run folds (SCI_GETFOLDEXPANDED(0)==0), second unfolds; not toggleable: both runs leave it folded.

### SETTINGS-028: EOL and non-printing character appearance
- Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_NPC, IDM_VIEW_NPC_CCUNIEOL
- Channel: ui, mcp
- Steps: Text with a no-break space and U+0001; show non-printing characters (IDM_VIEW_NPC on); select "Non-Printing Characters" "Abbreviation", Apply, read SCI_GETREPRESENTATION of "\xC2\xA0"; select "Codepoint", Apply; select "EOL (CRLF)" "Plain Text", Apply, read SCI_GETREPRESENTATIONAPPEARANCE of "\n" with EOL shown.
- Expect: "NBSP", then "U+00A0"; the EOL representation appearance is SC_REPRESENTATION_PLAIN with Plain Text and not with Default.

### SETTINGS-029: Custom colours for EOL and non-printing characters, C0/C1 appearance
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Tick "    EOL (CRLF): Custom Color", "    Non-Printing Characters: Custom Color" and "    Apply Appearance settings to C0, C1 & Unicode EOL", Apply; read SCI_GETREPRESENTATIONCOLOUR for "\n", the NBSP and U+0001 with IDM_VIEW_NPC and IDM_VIEW_NPC_CCUNIEOL on; untick all, Apply.
- Expect: with the boxes ticked the representations carry a colour (SCI_GETREPRESENTATIONAPPEARANCE has SC_REPRESENTATION_COLOUR) and U+0001 uses the non-printing appearance; unticked, no colour flag; prefs eolCustomColour, npcCustomColour, npcIncludeCcUniEol follow.

### SETTINGS-030: Prevent control character typing
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: Text "ab", caret at the end; with "Prevent control character (C0 code) typing into document" ticked press ctrl+b (inserts U+0002 by default); untick, Apply, press ctrl+b again.
- Expect: ticked: text stays "ab"; unticked: text is "ab\x02".

## Dark Mode

### SETTINGS-031: Appearance light / dark picks the light / dark theme
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp, launch
- Steps: On Dark Mode select Appearance "Light mode", Apply, read SCI_STYLEGETBACK(STYLE_DEFAULT); select "Dark mode", Apply, read it and the app's effective appearance (`e2e_invoke get nsapp effectiveAppearance.name`); restart; set "Follow the system" at the end.
- Expect: light: 0xFFFFFF (Default theme); dark: 0x3F3F3F (DarkModeDefault) and an appearance name containing "Dark"; still dark after restart; pref appearanceMode 1 / 2.

### SETTINGS-032: The light and dark theme pop-ups list every theme and choose the one used
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: With Appearance "Light mode", select "Monokai" in "Light theme", Apply; select Appearance "Dark mode" and "Dark theme" "Deep Black", Apply; read STYLE_DEFAULT colours each time; for each item of the pop-up, select it and Apply.
- Expect: the pop-ups list at least 22 themes including Default, DarkModeDefault, Monokai; Monokai gives back 0x222827 (272822 in BGR) and fore 0xF2F8F8; every theme applied gives a default background and at least 5 styled C++ styles differing from Default; prefs lightThemeName / darkThemeName hold the chosen names.

## Margins/Border/Edge

### SETTINGS-033: Bookmark and fold margins, padding
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Untick "Display bookmark" and "Show the fold margin", set "Padding: Left" 5 and "Padding: Right" 7, Apply; set padding 12, Apply; restore.
- Expect: SCI_GETMARGINWIDTHN(1) == 0 and (2) == 0; SCI_GETMARGINLEFT 5, SCI_GETMARGINRIGHT 7; a padding of 12 is stored as 9 (clamped 0..9); restored, margin 2 width > 0.

### SETTINGS-034: Vertical edge: one line, several lines, background
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Select "A line" with columns "80", Apply; columns "80 100 120", Apply; "Background mode" with "72", Apply; "None", Apply.
- Expect: EDGE_LINE with SCI_GETEDGECOLUMN 80; EDGE_MULTILINE with SCI_GETMULTIEDGECOLUMN(1) 100; EDGE_BACKGROUND with column 72; EDGE_NONE.

### SETTINGS-035: Fold margin style
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: C++ document; for each "Fold Margin Style" item (Simple, Arrow, Circle tree, Box tree, None) select and Apply.
- Expect: SCI_MARKERSYMBOLDEFINED(SC_MARKNUM_FOLDER) is SC_MARK_MINUS/PLUS family for Simple, SC_MARK_ARROW for Arrow, SC_MARKNUM_FOLDEROPEN SC_MARK_CIRCLEMINUS for Circle tree, SC_MARK_BOXPLUS for Box tree; None makes SCI_GETMARGINWIDTHN(2) 0.

### SETTINGS-036: Line number display and width
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp, menu
- Steps: Document of 120000 lines, scrolled to the top; "    Width" "Dynamic width", Apply, read SCI_GETMARGINWIDTHN(0); "Constant width", Apply, read it; untick "Line Number: Display", Apply.
- Expect: constant width > dynamic width > 0; unticked, margin 0 width is 0; persists across restart.

### SETTINGS-037: Change history in the margin and in the text
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Tick "Change History: Show in the text", Apply; untick "Change History: Show in the margin", Apply; edit a line.
- Expect: SCI_GETCHANGEHISTORY has SC_CHANGE_HISTORY_INDICATORS when "in the text" is on and SC_CHANGE_HISTORY_MARKERS only while "in the margin" is on; margin 3 is 6 px wide with the margin option and 0 without; both off gives SC_CHANGE_HISTORY_DISABLED.

### SETTINGS-038: Distraction Free width
- Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_DISTRACTIONFREE
- Channel: ui, mcp
- Steps: Select "Distraction Free" "4 parts", Apply; run IDM_VIEW_DISTRACTIONFREE; read SCI_GETMARGINLEFT and the editor width (SCI_GETSCROLLWIDTH or `ui` frame of the ScintillaView); run it again.
- Expect: inside distraction-free mode the left margin is a quarter of the editor's width (±1 px); leaving it restores the padding (≤ 9).

## New Document

### SETTINGS-039: Default encoding of a new document
- Covers: IDM_SETTING_PREFERENCE, IDM_FILE_NEW
- Channel: ui, files, mcp
- Steps: For each of "ANSI", "UTF-8", "UTF-8-BOM", "UTF-16 BE BOM", "UTF-16 LE BOM" typed into the "Encoding" field: Apply, run IDM_FILE_NEW, type "é", save to `tmp` with a queued save-panel answer.
- Expect: the Encoding menu checks the matching item (IDM_FORMAT_ANSI, IDM_FORMAT_AS_UTF_8, IDM_FORMAT_UTF_8, IDM_FORMAT_UTF_16BE, IDM_FORMAT_UTF_16LE); the saved bytes are E9 / C3 A9 / EF BB BF C3 A9 / FE FF 00 E9 / FF FE E9 00.

### SETTINGS-040: Apply to opened ANSI files
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, files, menu
- Steps: A seven-bit file "plain text\n" in `tmp`; with Encoding "UTF-8" and "    Apply to opened ANSI files" ticked open it; close, untick, Apply, open again.
- Expect: ticked: the document is UTF-8 (IDM_FORMAT_AS_UTF_8 checked); unticked: ANSI (IDM_FORMAT_ANSI checked).

### SETTINGS-041: Default line ending of a new document
- Covers: IDM_SETTING_PREFERENCE, IDM_FILE_NEW
- Channel: ui, files, mcp
- Steps: For each "Format (Line ending)" item: Apply, IDM_FILE_NEW, type "a" return "b", save to `tmp`.
- Expect: SCI_GETEOLMODE is SC_EOL_CRLF / SC_EOL_CR / SC_EOL_LF; the file's bytes contain "\r\n" / "\r" / "\n" between a and b; the matching Edit > EOL Conversion item is checked.

### SETTINGS-042: Default language of a new document
- Covers: IDM_SETTING_PREFERENCE, IDM_FILE_NEW
- Channel: ui, menu, mcp
- Steps: Type "python" into "Default language:", Apply; run IDM_FILE_NEW; clear the field, Apply, IDM_FILE_NEW.
- Expect: the first new document's language is Python (IDM_LANG_PYTHON checked, status bar starts "Python"); the second is Normal text.

### SETTINGS-043: Language from contents when the name says nothing
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp, prefs
- Steps: Untick "Work the language out from the contents when the name does not say", Apply; open an extensionless file "script" whose first line is "#!/usr/bin/env python3"; then tick it, Apply, open it again.
- Expect: unticked: the document stays Normal text and pref detectLanguageFromContent is false; ticked: it opens as Python. (Currently Apply does not write this option: xfail, BUG.)

### SETTINGS-044: Always open a new document at startup
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, launch, mcp
- Steps: Untick "Always open a new document in addition at startup", Apply; restart with a file of `tmp` as argument; tick it, Apply, restart the same way.
- Expect: unticked: the only document is the file; ticked: the file plus an untitled "new 1".

### SETTINGS-045: First line as untitled tab name
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: Tick "Use the first line of document as untitled tab name", Apply; in a new document type "Shopping list\nmilk"; untick, Apply.
- Expect: the tab title (list_documents) is "Shopping list" while ticked, "new N" after unticking; a first line longer than 32 characters is cut to 32.

## Indentation

### SETTINGS-046: Indent size and spaces
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: Set "Indent size:" 3 and tick "Indent using: Space character(s)", Apply; press tab in an empty document; set 8 and untick, Apply, press tab.
- Expect: SCI_GETTABWIDTH 3, SCI_GETUSETABS 0, the text is three spaces; then width 8, uses tabs, the text is "\t".

### SETTINGS-047: Auto-indent none, basic, advanced
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: For "None", "Auto-indent: Basic", "Auto-indent: Advanced": Apply; in C++ type "    if (x) {" then return.
- Expect: None: the new line has indentation 0; Basic: 4; Advanced: 8; with Advanced a "}" typed on the next line goes back under the opener (4).

### SETTINGS-048: Backspace unindents
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: Tick "Backspace key unindents instead of removing single space", Apply; text "        x" (8 spaces), caret before x, press backspace; untick, Apply, repeat.
- Expect: ticked: SCI_GETBACKSPACEUNINDENTS 1 and the line has 4 spaces; unticked: 7 spaces.

### SETTINGS-049: Indent settings per language
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp, launch
- Steps: Under "Indent Settings for" select "python", untick "Use default value", set its "Indent size:" 2 and "Space character(s)", Apply; open a .py and a .cpp document; restart.
- Expect: Python document: tab width 2, no tabs; C++ document: the default size; still so after restart; pref languageIndent has python {size 2, spaces true}.

## Language page

### SETTINGS-050: Hiding languages from the Language menu
- Covers: IDM_SETTING_PREFERENCE, IDM_LANG_PYTHON
- Channel: ui, menu, launch
- Steps: On Language select "Python" in "Available items", click "→", Apply; read the Language menu; restart; move it back with "←".
- Expect: Python is listed under "Disabled items" and absent from the Language menu (IDM_LANG_PYTHON not found) and from its "P" submenu; still hidden after restart; back after "←" and Apply.

### SETTINGS-051: Compact language menu
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, menu
- Steps: Tick "Make language menu compact", Apply, read the Language menu tree depth 2; untick, Apply.
- Expect: compact: first item "None (Normal Text)", letter submenus ("C" holding "C++"); flat: "C++" and "Python" are top-level items and "User Defined Language" is present.

### SETTINGS-052: SQL backslash escape
- Covers: IDM_SETTING_PREFERENCE, IDM_LANG_SQL
- Channel: ui, mcp
- Steps: SQL document "select 'a\\'b' from t"; with "Treat backslash as escape character for SQL" ticked read SCI_GETSTYLEAT at "from"; untick, Apply, recolour.
- Expect: ticked: the string ends after b' so "from" is a keyword (SCE_SQL_WORD); unticked: the string ends at the backslash's quote and the style at "b" is not a string.

## Highlighting

### SETTINGS-053: Brace matching on and off
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp, snapshot
- Steps: C++ text "value = (a + b);"; read SCI_STYLEGETFORE(STYLE_BRACELIGHT); with "Highlight matching braces" ticked put the caret after "(" and snapshot the main window; move the caret to "a" and snapshot; untick, Apply, and repeat both snapshots.
- Expect: ticked: in the first snapshot pixels of the brace-light colour appear at the two braces and not in the second; unticked: neither snapshot has them (the braces keep the operator colour).

### SETTINGS-054: Smart highlighting and its options
- Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_FIND
- Channel: ui, mcp
- Steps: Text "total = total + subtotal Total"; select the first "total" (go_to with end column); count runs of indicator 12 (smart highlight) with SCI_INDICATORVALUEAT; repeat with "Smart Highlighting: Match whole word only" off, then "Smart Highlighting: Match case" on, then "Smart highlighting" off.
- Expect: whole word, case-insensitive: 3 (total, total, Total); whole word off: 4; match case on: 2 without "Total"; smart highlighting off: 0; with "Smart Highlighting: Use Find dialog settings" ticked the Find window's Match case / Match whole word options decide instead (Find's Match case on gives 2, off gives 3).

### SETTINGS-055: Smart highlighting in the other view
- Covers: IDM_SETTING_PREFERENCE, IDM_VIEW_CLONE_TO_ANOTHER_VIEW
- Channel: ui, mcp
- Steps: Text "alpha beta alpha gamma alpha"; clone to the other view; tick "Smart Highlighting: Highlight another view", Apply; select the first "alpha" in the main view.
- Expect: the sub view (e2e_sci view=sub) has 3 runs of indicator 12; unticked, 0.

### SETTINGS-056: Mark style options: match case and whole word
- Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_MARKALLEXT1
- Channel: ui, mcp
- Steps: Text "cat cats CAT", select "cat"; for (case off, word on), (case on, word on), (case on, word off) set "Style All Occurrences of Token: Match case" / "…: Match whole word only", Apply, run IDM_SEARCH_UNMARKALLEXT1 then IDM_SEARCH_MARKALLEXT1, count runs of indicator 8.
- Expect: 2, 1, 2 runs respectively.

### SETTINGS-057: Matching tags, attributes, non-HTML zones
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: HTML "<div class=\"a\" id='b'><p>x</p></div>"; caret in "div"; read runs of indicators 15 (tag) and 16 (attributes); untick "    Highlight tag attributes", Apply; untick "Highlight Matching Tags", Apply.
- Expect: tag runs at 0..4, 21..22, 30..36 and attribute runs at 5..14, 15..21; without attributes indicator 16 is empty; without matching tags indicator 15 is empty; "    Highlight comment/php/asp zone" is stored (highlightNonHtmlZone) and, as upstream (which reads _enableHiliteNonHTMLZone nowhere but in its settings), tags inside "<!-- <b>x</b> -->" still do not match.

## Print

### SETTINGS-058: Print options reach the print job
- Covers: IDM_SETTING_PREFERENCE, IDM_FILE_PRINT
- Channel: ui, prefs, modal
- Steps: Tick "Print line number", select "Color Options" "Invert", set margins "11 33 22 44", header/footer parts, header font "Courier" size 12, Bold, "Print formfeed as page break", Apply; run IDM_FILE_PRINT with the print panel cancelled (queued answer / real modal closed).
- Expect: the stored preferences are printLineNumbers true, printColourMode 1, printMarginLeft 11, printMarginTop 33, printMarginRight 22, printMarginBottom 44, the six header/footer strings, printHeaderFontName "Courier", printHeaderFontSize 12, printHeaderBold true, printFormFeedPageBreak true; a margins text with three numbers leaves the margins unchanged; nothing reaches a printer. (Checking the rendered page needs a print-to-PDF hook, see report.)

### SETTINGS-059: Print Variable + Add inserts into the last header/footer field
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui
- Steps: On Print focus the "Footer: Left part" field (`act focus`), select "File name" in "Variable", click "Add"; with no field focused select "Page" and click "Add".
- Expect: "Footer: Left part" ends with "$(FILE_NAME)"; the second Add appends "$(CURRENT_PRINTING_PAGE)" to the last field used (or "Header: Middle part" when none was).

## Backup

### SETTINGS-060: Backup on save: none, simple, verbose
- Covers: IDM_SETTING_PREFERENCE, IDM_FILE_SAVE
- Channel: ui, files
- Steps: Open `tmp/b.txt` ("one"); with "None" edit to "two" and save; "Simple backup", Apply, edit "three", save; "Verbose backup", Apply, edit "four", save.
- Expect: None: no b.txt.bak; Simple: b.txt.bak holds "two"; Verbose: a file b.txt.<timestamp>.bak holding "three" in home/Library/Application Support/NotepadMac/backup.

### SETTINGS-061: Custom backup directory
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, files, launch
- Steps: Set "Custom Backup Directory" to `tmp/bk`, "Verbose backup", Apply; save an edited file; restart and save again.
- Expect: the verbose backups land in `tmp/bk` both times, none in the home's backup folder.

### SETTINGS-062: Session snapshot and periodic backup
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, files, launch
- Steps: Tick "Enable session snapshot and periodic backup", set seconds to 5, Apply; type "never saved" in an untitled document and edit an opened file without saving; poll the backup folder up to 15 s; kill the app (stop with graceful=False) and start with `session=True`, clean_home=False.
- Expect: within the interval backup files with the unsaved texts appear in the home's backup folder and the opened file on disk is unchanged; after the restart the untitled document comes back with "never saved", marked modified; a value below 5 is stored as 5.

## Auto-Completion

### SETTINGS-063: Auto-completion on input, source and threshold
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: C++ document with "retrieval retrospect\n"; for "Function completion", "Word completion", "Function and word completion" with "Characters before it opens" 3: Apply, type "ret" on a new line, read SCI_AUTOCACTIVE and the list (SCI_AUTOCGETCURRENTTEXT after moving); untick "Enable auto-completion on each input", Apply, type "ret".
- Expect: the list opens after the third character only; Word: retrieval, retrospect and not return; Function: return; both: all three; unticked: SCI_AUTOCACTIVE stays 0.

### SETTINGS-064: Brief list, ignore numbers, Tab inserts
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: Tick "Make auto-completion list brief", type "ret" in C++; tick "Ignore numbers", document "12345 12399", type "123"; untick "Insert Selection: TAB", open a list and press tab.
- Expect: the brief list holds only names starting with "ret"; with Ignore numbers no list opens for "123" (and one does when unticked); without TAB insertion, tab does not insert the selected item (SCI_AUTOCGETOPTIONS / text unchanged apart from a tab).

### SETTINGS-065: Function parameters hint on input
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: C document; with "Function parameters hint on input" ticked type "fopen("; then "name, "; then "\"r\")"; untick, Apply, type "fopen(" again.
- Expect: SCI_CALLTIPACTIVE 1 after "(" and still after ","; 0 after ")"; unticked, no call tip.

### SETTINGS-066: Auto-insert pairs and the close tag
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: For each of "Auto-Insert: ( )", "[ ]", "{ }", "' '", "\" \"": tick only it, Apply, type its opener in an empty C++ document; tick "Auto-Insert: html/xml close tag", HTML document, type "<div>"; untick all and repeat.
- Expect: "()", "[]", "{}", "''", "\"\"" with the caret between; "<div></div>" with the caret after "<div>"; "<img/>" gets nothing; unticked: only the typed characters.

### SETTINGS-067: User matched pairs
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: Set "Matched pair 1:" "<>" and "Matched pair 2:" "ab" (invalid: letters), Apply; type "<" in an empty document; type "<" before "x".
- Expect: "<>" in the empty document; "<x" before text; pref userMatchedPairs is ["<>"] (the letter pair is dropped).

## Multi-Instance & Date

### SETTINGS-068: Custom date format, its preview, and the reversed order
- Covers: IDM_SETTING_PREFERENCE, IDM_EDIT_INSERT_DATETIME_CUSTOMIZED, IDM_EDIT_INSERT_DATETIME_SHORT
- Channel: ui, mcp
- Steps: Set "Custom format" to "yyyy/MM/dd" (set_value), read the preview label beside it; Apply; run IDM_EDIT_INSERT_DATETIME_CUSTOMIZED; tick "Reverse default date time order (short & long formats)", Apply, run IDM_EDIT_INSERT_DATETIME_SHORT and compare with the unticked result.
- Expect: the preview shows today's date as yyyy/MM/dd as soon as the field changes; the inserted text matches ^\d{4}/\d{2}/\d{2}$ and is today; reversed short form starts with the time (differs from the default, which starts with the date).

## Delimiter

### SETTINGS-069: Word character list changes what a word is
- Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_SELECTMATCHINGBRACES
- Channel: ui, mcp
- Steps: Text "alpha-beta gamma"; read SCI_WORDENDPOSITION(2, 1); tick "Add characters to the word list", set "Word character list" to "-", Apply, read it again; untick, Apply.
- Expect: 5 without, 10 with "-", 5 again; SCI_GETWORDCHARS contains "-" only while ticked.

### SETTINGS-070: Selection between delimiters (known gap)
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Set "Delimiter: Open" "[" and "Delimiter: Close" "]", tick "Allow on several lines", Apply; text "arr[42] rest"; Cmd+double-click inside "42" (needs an editor mouse hook, see report).
- Expect: the selection is 4..6 ("42"); prefs delimiterOpen "[", delimiterClose "]", delimiterMultiline true persist across restart. (The port stores these settings but no user action uses them.)

## Performance

### SETTINGS-071: Large file restriction and what it allows
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp, files
- Steps: Set "Define Large File Size:" 1 with "Enable Large File Restriction (no syntax highlighting)" ticked, "Allow Brace Match", "Allow URL Clickable Link", "Allow Auto-Completion", "Allow Smart Highlighting" unticked, "Deactivate Word Wrap globally" ticked, Apply; open a 1.5 MB C++ file with a comment and a URL on line 1 and word wrap on; then untick the restriction, Apply, reopen.
- Expect: restricted: SCI_GETSTYLEAT(0) is 0 (no highlighting), no link indicator (14) on the URL, no smart highlight, SCI_GETWRAPMODE none; unrestricted: line 1 is SCE_C_COMMENTLINE; a size of 5000 is stored as 2046.

## Tab Bar

### SETTINGS-072: Tab bar options reach the tab bar
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, snapshot, prefs
- Steps: For each of "Tab Bar: Hide", "Vertical", "Multi-line", "Show close button", "Show buttons on inactive tabs", "Reduce", "Change inactive tab color", "Draw a colored bar on active tab", "Lock (no drag and drop)": flip it, Apply, read the tab bar view (NppTabBarView in `ui`, hidden/frame) and its matching property (`e2e_invoke get editor tabBar.<property>`), flip back.
- Expect: Hide removes the tab bar from the visible controls; Vertical makes it taller than wide and left of the editor; each other property follows its checkbox; each preference key is stored.

### SETTINGS-073: Max tab label length and double click to close
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Open `tmp/averylongfilename.txt`; set "Max. tab label length:" 4, Apply; read the tab's label in `ui`; tick "Double click to close document", Apply, double-click the tab (needs a tab double-click hook, see report); set the length back to 0.
- Expect: the label is at most 5 characters with an ellipsis; after the double click the document is closed; length 0 shows the full name.

### SETTINGS-074: Exit on close the last tab and the pin feature
- Covers: IDM_SETTING_PREFERENCE, IDM_FILE_CLOSE
- Channel: ui, menu, launch
- Steps: Untick "Enable pin tab feature", Apply, read the tab context menu (`e2e_menu context=tab`) and File > Pin Tab; tick "Exit on close the last tab", Apply, run IDM_FILE_CLOSE on the only document.
- Expect: without the pin feature "Pin Tab" is absent or disabled in both menus (tabPinFeatureEnabled is used nowhere in the port: xfail, BUG); closing the last tab quits the app (the process exits); a restarted app still has exitOnClosingLastTab true.

## Recent Files History

### SETTINGS-075: Number of entries, full path and length
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, menu, launch
- Steps: Set "Max. number of entries:" 3, Apply; open and close five files from `tmp`; read the File menu's recent entries; tick "Full File Name Path" and set "Customize Maximum Length:" 20, Apply; restart.
- Expect: three entries, the most recent first; with the full path they start with "…" and are 20 characters long, ending with the file name; the same after restart.

## Default Directory

### SETTINGS-076: Open/Save dialogs start in the configured folder
- Covers: IDM_SETTING_PREFERENCE, IDM_FILE_OPEN
- Channel: ui, modal
- Steps: Open `tmp/a/x.txt`; with "Follow current document" run IDM_FILE_OPEN with a cancelled panel and read the logged panel's directory; "A fixed folder" with "Fixed folder" `tmp/b`, Apply, again; "Remember last used directory", open a file from `tmp/c` through the panel, then run IDM_FILE_OPEN again.
- Expect: the logged directories are `tmp/a`, `tmp/b`, `tmp/c` respectively.

## Searching

### SETTINGS-077: Filling the Find field
- Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_FIND
- Channel: ui, mcp
- Steps: Select "needle" and run IDM_SEARCH_FIND, read the Find window's field; with nothing selected and the caret in "word", run it again; set "Max Characters to Auto-Fill Find Field" 3, Apply, select "abcdef", run it; untick "Fill Find Field with Selected Text" and "Select Word Under Caret when Nothing Selected", Apply, repeat.
- Expect: "needle"; "word"; not "abcdef" when over the limit; with the options off the field keeps its previous text; with "Minimum Size for Auto-Checking \"In selection\"" 10, a 12-character two-line selection opens Find with "In selection" ticked and a 5-character one without.

### SETTINGS-078: Confirm Replace All and Replace staying on the occurrence
- Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_REPLACE
- Channel: ui, modal, mcp
- Steps: Text "cat cat cat"; in the Replace window find "cat" replace "dog" and click Replace All with "Confirm Replace All" ticked and alert answer "Cancel"-equivalent (button 2); then answer 1; untick it and repeat on fresh text; tick "Replace: Don't move to the following occurrence", click Replace once.
- Expect: an alert is logged and cancelling leaves the text; confirming gives "dog dog dog"; unticked, no alert; with "Replace: Don't move to the following occurrence" on, Replace changes the first match and the caret stays right after it (3..3, upstream's processReplace) instead of moving to the next "cat".

### SETTINGS-079: Compare options from Searching
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Two documents "Alpha\n\nbeta" and "alpha\nbeta  "; tick "Compare: ignore case", "Compare: ignore spaces", "Compare: ignore empty lines", Apply; call the compare tool; untick, Apply, compare again.
- Expect: with the options on the documents compare as identical; off, differences are reported.

### SETTINGS-080: Find dialog remains open after a results-window search
- Covers: IDM_SETTING_PREFERENCE, IDM_SEARCH_FIND
- Channel: ui
- Steps: Open Find, type "x", click "Find All in Current Document" with "Find dialog remains open after search that outputs to results window" unticked; tick it, Apply, repeat.
- Expect: unticked: the Find window is hidden after the search; ticked: it stays visible.

## Cloud & Link

### SETTINGS-081: Clickable links, underline and custom schemes
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, mcp
- Steps: Text "see https://example.org/page and obsidian://open?vault=x"; count runs of indicator 14 with "Clickable Link Settings: Enable" ticked and "URI customized schemes:" empty; set the schemes to "obsidian", Apply; tick "No underline", Apply, read SCI_INDICGETSTYLE(14); tick Searching > "Enable fullbox mode", Apply, read it again; untick Enable, Apply.
- Expect: 1 link, then 2; the indicator style is INDIC_PLAIN normally, INDIC_HIDDEN with No underline, INDIC_ROUNDBOX with fullbox mode; disabled: 0 runs.

### SETTINGS-082: The settings folder moves the settings files
- Covers: IDM_SETTING_PREFERENCE, IDM_SETTING_EDITCONTEXTMENU, IDM_SETTING_SHORTCUT_MAPPER
- Channel: ui, files, launch, modal
- Steps: With `fresh_app`, set "Set your cloud location path here:" to `tmp/cloud`, Apply; remove a shortcut in the Shortcut Mapper (Modify… with alert answer "Remove"); run IDM_SETTING_EDITCONTEXTMENU (alert answered 1); restart; run IDM_SETTING_EDITCONTEXTMENU again; clear the field, Apply.
- Expect: shortcuts.xml and contextMenu.xml are written in `tmp/cloud`, not in the home's NotepadMac folder; the opened contextMenu.xml's path (get_document) is in `tmp/cloud` before and after the restart; the removed shortcut is still removed after the restart (read from the cloud folder).

## MISC.

### SETTINGS-083: Show only filename in title bar
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, launch
- Steps: Open `tmp/t_title.txt`; tick "Show only filename in title bar", Apply, read the main window's title; untick, Apply.
- Expect: "t_title.txt" exactly while ticked; with the full path otherwise; persists across restart.

### SETTINGS-084: Document Switcher and MRU order
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, keys, mcp
- Steps: Documents A, B, C; activate A then C; with "Document Switcher (Ctrl+TAB): Enable" and "    Enable MRU behaviour" ticked press ctrl+tab; untick Enable, Apply, activate B and press ctrl+tab.
- Expect: MRU: A becomes current and the switcher window is shown while Control is held; disabled: C (the next tab) becomes current and no switcher window appears.

### SETTINGS-085: Save All confirmation
- Covers: IDM_SETTING_PREFERENCE, IDM_FILE_SAVEALL
- Channel: ui, modal, files
- Steps: Two modified files from `tmp`; with "Enable Save All confirm dialog" ticked run IDM_FILE_SAVEALL with alert answer "Yes"/1; modify again, untick, Apply, run it again.
- Expect: ticked: one confirmation alert is logged and both files are written; unticked: no alert and both files are written.

### SETTINGS-086: Mute all sounds
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, prefs
- Steps: Tick "Mute all sounds", Apply; run a command that beeps (Find Next with no match) — needs a beep counter hook, see report.
- Expect: pref muteSounds true and no beep is recorded; unticked, one beep.

### SETTINGS-087: Folder as Workspace symlinks
- Covers: IDM_SETTING_PREFERENCE, IDM_FILE_OPENFOLDERASWORKSPACE
- Channel: ui, modal
- Steps: Folder `tmp/ws` with real.txt and a symlink link.txt; with "Allow loading symlinks in Folder as Workspace panel" unticked open it as workspace (panel answer); read the workspace panel's outline; tick, Apply, open it again.
- Expect: only real.txt without the option; real.txt and link.txt with it.

### SETTINGS-088: Session and workspace file extensions
- Covers: IDM_SETTING_PREFERENCE, IDM_FILE_SAVESESSION
- Channel: ui, files, modal
- Steps: Set "Session file ext." "npps" and "Workspace file ext." ".nppw", Apply; save a session with one file to `tmp/s.npps` (panel answer); close all; open `tmp/s.npps`; open a project file `tmp/p.nppw`.
- Expect: opening s.npps loads the session (the file is open again, the session file itself is not shown as text); p.nppw opens in Project Panel 1, not as a text document.

### SETTINGS-089: Git margin marks and the MCP switch are applied
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, prefs
- Steps: With `fresh_app`, untick "Git: mark lines changed since the last commit in the margin", Apply, read the persistent domain; tick "Let AI agents drive the editor (MCP)" (already on through the launch argument) and Apply, read the persistent domain.
- Expect: gitMarginMarks false and agentServer true are stored (README says MCP is turned on in Preferences). Currently Apply writes neither (xfail, BUG).

### SETTINGS-090: Auto-updater mode and releases repository
- Covers: IDM_SETTING_PREFERENCE
- Channel: ui, prefs
- Steps: Select "Enable on Notepad++ exit" in "Auto-updater:", set "Releases repository" to "someone/Fork", Apply; set the repository to "not-a-repo", Apply; select "Disable", Apply.
- Expect: autoUpdateMode 2 then 0; updateRepository "someone/Fork", and "not-a-repo" (no single slash) is refused, leaving "someone/Fork".

## Search Engine

### SETTINGS-091: The chosen engine is what Search on Internet opens
- Covers: IDM_SETTING_PREFERENCE, IDM_EDIT_SEARCHONINTERNET
- Channel: ui, mcp
- Steps: Select "word" in the document; for each of DuckDuckGo, Google, Bing, Yahoo! and "Set your search engine here:" with "https://example.org/find?w=$(CURRENT_WORD)&x=1": Apply, run IDM_EDIT_SEARCHONINTERNET (needs a hook capturing opened URLs instead of launching the browser, see report).
- Expect: the opened URLs start with https://duckduckgo.com/, https://www.google.com/, https://www.bing.com/, https://search.yahoo.com/ and equal "https://example.org/find?w=word&x=1"; pref searchEngine 0..4 persists.

## Style Configurator

### SETTINGS-092: The Style Configurator opens on the current language
- Covers: IDM_LANGSTYLE_CONFIG_DLG
- Channel: menu, ui
- Steps: Open a C++ document; run IDM_LANGSTYLE_CONFIG_DLG; read the window's theme pop-up, Language table, Style table and the "Default ext.:" label; run it on a Normal text document after closing.
- Expect: the window "Style Configurator" is shown; the Language table's first row is "Global Styles" and the selected row is "C++"; the Style table lists PREPROCESSOR, DEFAULT, INSTRUCTION WORD, … COMMENT LINE; "Default ext.:" shows "cpp cxx cc h hh hpp hxx ino"; for Normal text the selected row is Global Styles.

### SETTINGS-093: Choosing a theme previews it, Cancel reverts, Save & Close keeps it
- Covers: IDM_LANGSTYLE_CONFIG_DLG
- Channel: ui, mcp, launch
- Steps: With Appearance "Light mode", open the configurator, select "Monokai" in "Select theme:"; read STYLE_DEFAULT back; click Cancel; open again, select "Monokai", click "Save && Close"; restart.
- Expect: after choosing, back is 0x222827 at once; Cancel restores 0xFFFFFF and pref lightThemeName stays "Default"; after Save & Close and restart the editor is Monokai and lightThemeName is "Monokai"; the Dark Mode page's "Light theme" shows Monokai.

### SETTINGS-094: Font, size, bold, italic and underline of a style apply at once and are saved
- Covers: IDM_LANGSTYLE_CONFIG_DLG
- Channel: ui, mcp, files, launch
- Steps: C++ document "// note\nint x;"; open the configurator, select Style "COMMENT LINE", select "Courier New" in "Font name:", "20" in "Size:", tick Bold, Italic, Underline; read style 2 (SCE_C_COMMENTLINE); click "Save && Close"; restart.
- Expect: SCI_STYLEGETFONT(2) "Courier New", SCI_STYLEGETSIZE(2) 20, bold, italic, underline all 1 before saving; home/…/NotepadMac/stylers.xml exists with COMMENT LINE fontName="Courier New" fontSize="20" fontStyle="7"; after restart style 2 still has them; other styles are unchanged.

### SETTINGS-095: Changing a style's colours
- Covers: IDM_LANGSTYLE_CONFIG_DLG
- Channel: ui, mcp, files
- Steps: C++ document; configurator, Style "COMMENT LINE"; set the "Foreground color" well to FF0000 and "Background color" to 00FF00 (needs e2e_act set_value on NSColorWell, see report); Save && Close.
- Expect: SCI_STYLEGETFORE(2) 0x0000FF and SCI_STYLEGETBACK(2) 0x00FF00 at once; the saved stylers.xml has fgColor="FF0000" bgColor="00FF00" for COMMENT LINE.

### SETTINGS-096: Global override switches
- Covers: IDM_LANGSTYLE_CONFIG_DLG
- Channel: ui, mcp
- Steps: C++ document; configurator, Language "Global Styles", Style "Global override"; tick "Enable global foreground colour" and "Enable global bold font style"; read SCI_STYLEGETFORE of SCE_C_WORD and STYLE_DEFAULT; click Cancel.
- Expect: both styles take Global override's foreground and bold follows its font style while ticked; after Cancel the keyword colour is back to the theme's (0xFF0000 for 0000FF) and pref globalOverride has no fg.

### SETTINGS-097: User extensions and user keywords
- Covers: IDM_LANGSTYLE_CONFIG_DLG
- Channel: ui, mcp, files
- Steps: Configurator, Language "C++", Style "INSTRUCTION WORD"; set "User ext.:" to " nppx  NPPY " (set_value, end_editing); set the "User-defined keywords" text view to "nppmacword" (set_text); Save && Close; open `tmp/a.nppx` containing "nppmacword x;".
- Expect: the file opens as C++; SCI_GETSTYLEAT(0) is SCE_C_WORD (5); stylers.xml holds ext="nppx nppy" (lower-cased) and the keyword; b.NPPY also opens as C++.

### SETTINGS-098: Transparency, and closing the configurator's window cancels
- Covers: IDM_LANGSTYLE_CONFIG_DLG
- Channel: ui
- Steps: Tick "Transparency", set the slider to 0.5 (set_value), read the window's alphaValue (`e2e_invoke get window:Style Configurator alphaValue`); untick; select "Monokai" as theme, then close the window with `close_window`.
- Expect: 0.5 while ticked, 1.0 unticked; closing the window acts as Cancel: STYLE_DEFAULT back returns to 0xFFFFFF and lightThemeName is unchanged.

## Shortcut Mapper

### SETTINGS-099: The mapper lists every command with its key and place
- Covers: IDM_SETTING_SHORTCUT_MAPPER
- Channel: menu, ui
- Steps: Run IDM_SETTING_SHORTCUT_MAPPER; read the segmented control, the table and its columns; select each segment.
- Expect: segments Main menu, Macros, Run commands, Plugin commands, Scintilla commands; Main menu has more than 400 rows with columns Name, Shortcut, Where, e.g. ["New", "⌘N", "File"] and ["Find Next", "⌘G", "Search"]; Scintilla commands has more than 80 rows; on Plugin commands the line under the table explains that plugins' commands cannot be assigned, and Modify… / Clear there show no alert and change nothing; Delete is enabled only on Macros and Run commands.

### SETTINGS-100: The filter narrows by name, place or key
- Covers: IDM_SETTING_SHORTCUT_MAPPER
- Channel: ui
- Steps: Set the search field (placeholder "Filter") to "Find Next", then "⌘G", then "search", then empty.
- Expect: "Find Next" gives the rows Find Next and Select and Find Next; "⌘G" includes Find Next; "search" gives the Search menu's commands; empty gives the full list back.

### SETTINGS-101: Remove a shortcut: menu, keys and shortcuts.xml
- Covers: IDM_SETTING_SHORTCUT_MAPPER, IDM_SEARCH_FINDNEXT
- Channel: ui, modal, keys, files, launch
- Steps: Filter "Find Next", select its row, queue alert answer "Remove", click "Modify…"; press cmd+g in a document with a search term set; restart.
- Expect: the alert 'Shortcut for "Find Next"' with buttons OK, Cancel, Remove is logged; the row's shortcut is empty; IDM_SEARCH_FINDNEXT has no key; cmd+g does not move the selection; shortcuts.xml in the home has <Shortcut id="43002" Ctrl="no" Alt="no" Shift="no" Key="0"/>; after restart the key is still gone.

### SETTINGS-102: Modify… cancelled or confirmed unchanged leaves everything as it was
- Covers: IDM_SETTING_SHORTCUT_MAPPER
- Channel: ui, modal, files
- Steps: Select "Find Next"; Modify… answered "Cancel"; then Modify… answered "OK" without a key.
- Expect: the row still shows ⌘G and IDM_SEARCH_FINDNEXT's key is "cmd+g" both times; no conflict alert is logged.

### SETTINGS-103: Clear removes the key of the selected command
- Covers: IDM_SETTING_SHORTCUT_MAPPER, IDM_FILE_NEW
- Channel: ui, keys, mcp
- Steps: Select the row "New"; click "Clear"; press cmd+n.
- Expect: the row's shortcut is empty, IDM_FILE_NEW has no key, cmd+n opens no new document (list_documents count unchanged); shortcuts.xml has id="41001" Key="0".

### SETTINGS-104: Assign a new key through the key capture
- Covers: IDM_SETTING_SHORTCUT_MAPPER, IDM_EDIT_UPPERCASE
- Channel: ui, modal, keys, files
- Steps: Select "UPPERCASE"; Modify… with an alert answer that presses cmd+alt+ctrl+u before answering OK (needs a hook: keys delivered to a queued alert, see report); select "abc" and press cmd+alt+ctrl+u.
- Expect: the row shows ⌃⌥⌘U; IDM_EDIT_UPPERCASE's key is "ctrl+alt+cmd+u"; the text becomes "ABC"; shortcuts.xml has id="42016" Ctrl="yes" Alt="yes" Shift="no" Key="85" MacCtrl="yes".

### SETTINGS-105: Conflicts are shown and resolved: take, share, cancel
- Covers: IDM_SETTING_SHORTCUT_MAPPER
- Channel: files, launch, ui, modal
- Steps: Write shortcuts.xml into the home giving IDM_EDIT_UPPERCASE (42016) and IDM_EDIT_LOWERCASE (42017) the same key Ctrl+Alt+U; start; select the UPPERCASE row; Modify… answered "OK" then the clash alert answered "Cancel"; again answered "Share it"; again answered "Take it from them".
- Expect: selecting the row shows "⌥⌘U is also used by: lowercase" in the red line and both rows are drawn as conflicting; the clash alert says "⌥⌘U is already used by lowercase."; Cancel and Share leave both keys; Take leaves lowercase without a key and UPPERCASE with ⌥⌘U, written to shortcuts.xml.

### SETTINGS-106: A shortcuts.xml from Windows is read: menu, macro, Run, Scintilla keys
- Covers: IDM_SETTING_SHORTCUT_MAPPER, IDM_FILE_NEW
- Channel: files, launch, keys, ui, menu
- Steps: Write the Windows-format shortcuts.xml of the in-app suite (41001 Ctrl+Alt+N, macro "From Windows" Alt+F6 typing "hi hi" then a Replace hi→yo, Run command "Say hello", ScintKey 2338 Ctrl+Shift+D with NextKey Alt+D, a PluginCommand of x.dll) into the home; start; press cmd+alt+n; in "one\ntwo\n" at line 1 press cmd+shift+d; in a new document press alt+f6.
- Expect: IDM_FILE_NEW's key is "alt+cmd+n" and it opens a document; cmd+shift+d deletes the line leaving "two\n"; alt+f6 plays the macro giving "yo yo"; the Macros tab lists "From Windows" with ⌥F6, the Macro menu lists it, the Run commands tab and Run menu list "Say hello"; after any change is saved the PluginCommand element of x.dll is still in the file.

### SETTINGS-107: Scintilla command keys can be removed and given
- Covers: IDM_SETTING_SHORTCUT_MAPPER
- Channel: ui, modal, keys, mcp
- Steps: On Scintilla commands filter "SCI_LINEDELETE" (or its name), select it, Modify… answered "Remove"; press its old key in "one\ntwo\n".
- Expect: the row has no key and the key no longer deletes the line; shortcuts.xml has a ScintKey ScintID="2338" entry with Key="0".

### SETTINGS-108: Deleting a macro and a Run command from the mapper
- Covers: IDM_SETTING_SHORTCUT_MAPPER, IDM_MACRO_SAVECURRENTMACRO
- Channel: ui, menu, files
- Steps: Record a macro typing "x" and save it as "Mine" (IDM_MACRO_SAVECURRENTMACRO with a prompt answer {"button":1,"field":"Mine"}); save a Run command "Echo" through the Run dialog or shortcuts.xml; in the mapper select Macros > "Mine", click Delete; Run commands > "Echo", click Delete.
- Expect: both rows disappear; the Macro menu no longer lists "Mine" and the Run menu no longer lists "Echo"; shortcuts.xml has neither; on the Main menu segment Delete is disabled and clicking it changes nothing.

## Edit Popup ContextMenu

### SETTINGS-109: Edit Popup ContextMenu opens contextMenu.xml with upstream's default
- Covers: IDM_SETTING_EDITCONTEXTMENU
- Channel: menu, modal, files, mcp
- Steps: With `fresh_app`, queue alert answer 1, run IDM_SETTING_EDITCONTEXTMENU; read the modal log, the current document's path and text; read the editor context menu (`e2e_menu context=editor`).
- Expect: an alert "Editing contextMenu" is logged; the document opened is home/Library/Application Support/NotepadMac/contextMenu.xml, created with a <ScintillaContextMenu> root; the context menu has at least 12 items, starts with "Cut", and "Style all occurrences of token" has a submenu of 5 items.

### SETTINGS-110: An edited contextMenu.xml is the right-click menu at the next click
- Covers: IDM_SETTING_EDITCONTEXTMENU, IDM_EDIT_UPPERCASE, IDM_EDIT_PASTE
- Channel: menu, files, mcp, clipboard
- Steps: Open contextMenu.xml through the command, replace its text with the in-app suite's sample (Copy by name, Paste renamed "Put it here", separators, a missing command, a "Case" folder with id 42016 and lowercase, an empty folder, a plugin folder) and save; read the context menu; set the clipboard to "pasted" and invoke "Put it here" (`e2e_menu_invoke context=editor`); invoke Case > UPPERCASE on a selection.
- Expect: the menu is exactly Copy, Put it here, separator, Case, Plugin commands (duplicate separators collapsed, the missing command and the empty folder left out); Case has 2 items; "Put it here" pastes "pasted"; Case > UPPERCASE upper-cases the selection.

### SETTINGS-111: Without a ScintillaContextMenu the Preferences list is used
- Covers: IDM_SETTING_EDITCONTEXTMENU
- Channel: files, prefs, mcp
- Steps: Write "<NotepadPlus></NotepadPlus>" into contextMenu.xml; set pref contextMenuCommands to ["Copy", "Paste", "Toggle Line Comment"]; read the context menu; restore the file.
- Expect: the context menu is exactly Copy, Paste, Toggle Line Comment (named in English whatever the interface language).

## Import

### SETTINGS-112: Import style theme(s) copies the theme and makes it usable
- Covers: IDM_SETTING_IMPORTSTYLETHEMES
- Channel: menu, modal, files, ui, mcp
- Steps: Write `tmp/TestTheme.xml` (Default Style fg ABCDEF bg 222222, cpp DEFAULT 123456/654321); queue panel answer [that path] and alert answer 1; run IDM_SETTING_IMPORTSTYLETHEMES; open Dark Mode > Light theme; with Appearance "Light mode" choose "TestTheme", Apply; restart.
- Expect: the open panel titled "Import style theme(s)" is logged; an alert "Import style theme(s)" says "1 file(s) imported into themes"; home/…/NotepadMac/themes/TestTheme.xml exists; the Light theme pop-up and the Style Configurator's theme list include TestTheme; applied, STYLE_DEFAULT back is 0x222222 and fore 0xEFCDAB; still so after restart.

### SETTINGS-113: Importing several themes, again, or cancelling
- Covers: IDM_SETTING_IMPORTSTYLETHEMES
- Channel: modal, files
- Steps: Import two theme files in one panel answer; import one of them again with changed contents; run the command with a cancelled panel (panel answer None).
- Expect: "2 file(s) imported into themes" then "1 file(s) …"; the second import replaces the file's contents; the cancelled run shows no alert and copies nothing.

### SETTINGS-114: Import plugin(s) copies a plugin that loads at the next start
- Covers: IDM_SETTING_IMPORTPLUGIN
- Channel: menu, modal, files, launch
- Steps: Build ../npp/macos/plugin-sdk/sample/hellomac.c into `tmp/HelloMac.dylib` with `clang -dynamiclib`; queue the panel answer and alert answer 1; run IDM_SETTING_IMPORTPLUGIN; restart; run Plugins > HelloMac > Insert Greeting (e2e_menu_invoke) in an empty document.
- Expect: the alert "Import plugin(s)" says "1 file(s) imported into plugins"; home/…/NotepadMac/plugins/HelloMac.dylib exists; after restart the Plugins menu has a "HelloMac" submenu; the document reads "hello from the sample plugin"; a text file imported as junk.dylib is copied too, the app still starts, and app.log reports that plugin junk.dylib could not be loaded.
