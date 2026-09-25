# UI — The window's chrome and panels

What surrounds the text: the window title, the tab bar (titles, modified marker, pin, close,
colours, its right-click menu and its preferences), the toolbar (items, enabled state, the
Toolbar preferences), the status bar (language, length/lines, Ln/Col/Pos/Sel, EOL, encoding,
INS/OVR, the path field and its click-to-copy, the Git branch), the editor's right-click menu
built from `contextMenu.xml`, the docking manager (docked, tabbed, floating panels, their
persistence), the document switcher (Ctrl+Tab), light and dark rendering, and dialogs whose
text must not be cut off. Out of scope: what each View command does (VIEW), the interface
language (L10N), the Preferences dialog's other settings (SETTINGS). The tab bar is a custom
view: its items are read with `e2e_invoke editor key=tabBar.items.title` (and `.modified`,
`.pinned`, `.colour`); panels are located with `e2e_invoke class:NppDockingManager`
(`isPanelVisible:`, `placeOfPanel:`, `panelsIn:`, `frontPanelIn:`).

## Window title

### UI-001: The title of an unsaved document is its tab name
- Covers: IDM_FILE_NEW
- Channel: ui, mcp
- Steps: After the reset read the main window title; run IDM_FILE_NEW; read it; switch back to the first tab (IDM_VIEW_TAB1).
- Expect: "new 1", then "new 2", then "new 1" again; `window.representedFilename` is empty.

### UI-002: The title of a saved file is its name and folder
- Covers: IDM_FILE_OPEN
- Channel: ui, files
- Steps: Open `<tmp>/dir/a.txt`; read the title and `window.representedFilename`.
- Expect: title "a.txt — <tmp>/dir"; representedFilename "<tmp>/dir/a.txt".

### UI-003: "File name only" in the title bar
- Covers: -
- Channel: prefs, ui
- Steps: Open `a.txt`; set pref `titleBarFileNameOnly` true; read the title; set it false.
- Expect: "a.txt" while on; "a.txt — <folder>" again after.

### UI-004: The window says when the document has unsaved changes
- Covers: IDM_FILE_SAVE
- Channel: ui, mcp
- Steps: Open `a.txt`; read `window.documentEdited`; type "x"; read; run IDM_FILE_SAVE; read.
- Expect: false, true, false.

### UI-005: -titleAdd adds a suffix to the title
- Covers: -
- Channel: launch, ui
- Steps: `app.start(args=["-titleAdd=Work"])`; read the title; open `a.txt`; read it.
- Expect: "new 1 - Work", then "a.txt — <folder> - Work".

### UI-006: The title follows the tab in front and a rename
- Covers: IDM_VIEW_TAB_NEXT, IDM_FILE_SAVEAS
- Channel: ui, modal, files
- Steps: Open `a.txt` and `b.txt`; switch tabs; then Save As `c.txt` (queued panel answer).
- Expect: the title names the tab in front after each switch; after Save As it is "c.txt — <folder>".

## Tab bar

### UI-007: One tab per document, in order, with its name
- Covers: IDM_FILE_NEW, IDM_FILE_CLOSE
- Channel: ui, mcp
- Steps: Open `a.txt`, run IDM_FILE_NEW twice, open `b.py`; read `tabBar.items.title` and `tabBar.selectedIndex`; close the second tab.
- Expect: titles in opening order with the new documents numbered ("new 2", "new 3"); the selected index is the document in front; after the close the list loses exactly that title.

### UI-008: The modified marker follows the save point
- Covers: IDM_EDIT_UNDO, IDM_FILE_SAVE
- Channel: ui, mcp, snapshot
- Steps: Open `a.txt`; type "x"; read `tabBar.items.modified`; snapshot the window; undo; read; type "y"; save; read.
- Expect: modified true after typing and the tab's label is drawn with a trailing "•" (snapshot differs from the unmodified one in the tab area); false after the undo back to the save point; false after saving.

### UI-009: A new document can be named after its first line
- Covers: -
- Channel: prefs, ui
- Steps: Set pref `untitledFromFirstLine` true; new document; type "Shopping list\nmilk"; read the tab title; type a 40-character first line in another new document; restore the pref.
- Expect: the tab reads "Shopping list"; the long first line is cut to 32 characters; a saved file keeps its file name.

### UI-010: Tab labels are cut to the length set
- Covers: -
- Channel: prefs, ui
- Steps: Open `a_long_file_name.txt`; set pref `tabMaxLabelLength` 4; read the label the tab shows (hook: `e2e_ui` listing the tab bar's tabs with their displayed title, frame and close-button rect); set it to 0.
- Expect: "a_lo…" while limited; the full name with 0.

### UI-011: A pinned tab shows the pin and stays among the pinned
- Covers: IDM_FILE_CLOSEALL_BUT_PINNED
- Channel: menu, ui
- Steps: Open A, B, C; with C in front choose "Pin Tab" in the tab menu (`e2e_menu_invoke context=tab path="Pin Tab"`); read titles and `tabBar.items.pinned`; run IDM_FILE_CLOSEALL_BUT_PINNED; choose "Pin Tab" again (unpin).
- Expect: C moves to the front of the bar and is the only pinned item; Close All but Pinned leaves only C; the menu item for a pinned tab reads as checked or "Unpin Tab"; unpinning clears `pinned`.

### UI-012: A click on a tab brings it to the front
- Covers: -
- Channel: ui
- Steps: Open A, B, C with C in front; click the first tab (hook: `e2e_act` click at a tab index or point of the NppTabBarView).
- Expect: A is the current document and the tab bar's selected index is 0.

### UI-013: The close button on a tab closes that tab
- Covers: IDM_FILE_CLOSE
- Channel: prefs, ui
- Steps: Set pref `tabShowCloseButton` true; open A and B (B in front); click the close button of B's tab (hook: click at a tab's close rect); then, with `tabCloseButtonOnInactive` true, click the close button of an inactive tab.
- Expect: B closes (no prompt, not modified); the inactive tab closes and the current one stays; with `tabShowCloseButton` false a click at the same place only selects the tab.

### UI-014: Double-click on a tab closes it when Preferences says so
- Covers: IDM_FILE_CLOSE
- Channel: prefs, ui
- Steps: Pref `tabDoubleClickCloses` true; double-click tab B (hook: click with clickCount 2 on a tab); then with the pref false double-click again.
- Expect: B closes the first time; with the pref off the tab only becomes current.

### UI-015: Closing a modified tab from the tab bar asks first
- Covers: IDM_FILE_CLOSE
- Channel: modal, ui
- Steps: Modify B; queue alert answer "Cancel" (or the third button); click B's close button (hook); then queue "No" (do not save) and click again.
- Expect: the first time an alert asks to save and B stays open, modified; the second time B closes and the file on disk is unchanged.

### UI-016: Hiding the tab bar gives its room to the editor
- Covers: -
- Channel: prefs, ui
- Steps: Read the ScintillaView height; set pref `hideTabBar` true; read the height and whether the tab bar is hidden; set it false.
- Expect: the tab bar is hidden and the editor is about 28 px taller; restored after.

### UI-017: Vertical and multi-line tab bars
- Covers: -
- Channel: prefs, ui, snapshot
- Steps: Open 12 files; set pref `tabBarVertical` true; read the tabs' frames (hook: tab bar tabs in `e2e_ui`, as in UI-010); snapshot; set it false and `tabBarMultiLine` true with a narrow window (800 px); read the frames; reset both.
- Expect: vertical: tabs stacked (same x, increasing y) down the side, the editor to their right; multi-line: tabs on more than one row, none cut off the right edge.

### UI-018: The tab's right-click menu has Notepad++'s items
- Covers: -
- Channel: menu
- Steps: Open a saved `a.txt`; dump `e2e_menu context=tab`.
- Expect: in order: Close; Close Multiple Tabs ▸ (Close All BUT This, Close All BUT Pinned, Close All to the Left, Close All to the Right, Close All Unchanged); Pin Tab; Save; Save As...; Open into ▸ (Open Containing Folder in Finder, in Terminal, as Workspace, Open in Default Viewer); Rename; Move to Trash; Reload; Print; Read-Only in Notepad++; Read-Only Attribute on Disk; Copy to Clipboard ▸ (Copy Full File Path, Copy Filename, Copy Current Dir. Path); Move Document ▸ (Move to Start, Move to End, Move to Other View, Clone to Other View, Move to New Instance, Open in New Instance); Apply Color to Tab ▸ (Apply Color 1-5, Remove Color); every item enabled.

### UI-019: Tab menu commands act on the document
- Covers: IDM_FILE_CLOSE, IDM_FILE_CLOSEALL_BUT_CURRENT, IDM_FILE_CLOSEALL_TOLEFT, IDM_FILE_CLOSEALL_TORIGHT, IDM_FILE_CLOSEALL_UNCHANGED, IDM_FILE_SAVE, IDM_FILE_RELOAD, IDM_EDIT_TOGGLEREADONLY, IDM_EDIT_FULLPATHTOCLIP, IDM_EDIT_FILENAMETOCLIP, IDM_EDIT_CURRENTDIRTOCLIP, IDM_VIEW_GOTO_START, IDM_VIEW_GOTO_END, IDM_VIEW_GOTO_ANOTHER_VIEW, IDM_VIEW_CLONE_TO_ANOTHER_VIEW, IDM_VIEW_TAB_COLOUR_1, IDM_VIEW_TAB_COLOUR_NONE
- Channel: menu, clipboard, files, modal
- Steps: For each tab-menu entry: set up A, B, C (saved files, B in front, B modified where it matters) and invoke it with `e2e_menu_invoke context=tab`.
- Expect: Close closes B; Close All BUT This leaves B; to the Left leaves B, C; to the Right leaves A, B; Close All Unchanged keeps only modified B; Save writes B; Reload (answer Yes) restores B from disk; Read-Only makes B read-only (SCI_GETREADONLY 1); the three copy items put B's full path, file name and folder on the clipboard; Move to Start/End reorder; Move/Clone to Other View put B in the second view; Apply Color 1 / Remove Color set `tabBar.items.colour` of B to 1 / 0.

### UI-020: A tabContextMenu.xml of one's own replaces the tab menu
- Covers: -
- Channel: files, menu
- Steps: Write `<home>/Library/Application Support/NotepadMac/tabContextMenu.xml` with root TabContextMenu and items `<Item MenuEntryName="File" MenuItemName="Close"/>`, `<Item id="0"/>`, `<Item id="42029" ItemNameAs="Path please"/>`; dump the tab menu; invoke "Path please"; delete the file.
- Expect: the menu is exactly Close, a separator, "Path please"; the renamed item copies the full path; after the file is removed the default menu is back.

### UI-021: Tab bar colours in light and dark appearance
- Covers: -
- Channel: prefs, snapshot
- Steps: For appearanceMode 1 (light) and 2 (dark): two tabs, snapshot the window, sample the active tab's label pixels against its background.
- Expect: the tab bar background is light in light mode and dark in dark mode; the label text contrasts with its background (luminance difference > 0.3) in both; the active tab's indicator bar is drawn.

## Toolbar

### UI-022: The toolbar has Notepad++'s buttons in its order
- Covers: -
- Channel: ui
- Steps: Read `e2e_ui toolbar=true` items; read `Contents/Resources/toolbar/order.txt` of the app bundle.
- Expect: the item identifiers are `npp.<command>` in order.txt's order with a space item for each "-"; every button has a non-empty label equal to its tooltip (New, Open, Save, Save All, Close, Close All, Print, Cut, Copy, Paste, Undo, Redo, Find, Replace, Zoom In, Zoom Out, Sync Vertical, Sync Horizontal, Word Wrap, All Characters, Indent Guide, User Language, Document Map, Document List, Function List, Folder as Workspace, Monitoring, Start Recording, Stop Recording, Play, Run Multiple, Save Macro).

### UI-023: Toolbar buttons are enabled only when they can act
- Covers: IDM_FILE_SAVE, IDM_EDIT_UNDO, IDM_EDIT_REDO, IDM_EDIT_CUT, IDM_EDIT_COPY, IDM_EDIT_PASTE, IDM_MACRO_STOPRECORDINGMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO
- Channel: ui, clipboard, mcp
- Steps: Open a saved file, clipboard empty; read the toolbar items' `enabled` (after an `e2e_idle`); type "x"; read; undo; read; select a word; read; copy; read; start macro recording; read.
- Expect: unmodified: Save, Undo, Redo, Paste, Stop Recording, Play disabled, Cut and Copy enabled (checkClipboard leaves them while copy/cut of the line without a selection is on, the default); after typing: Save and Undo enabled; after undo: Redo enabled, Save disabled; with a selection: Cut and Copy enabled; with text on the clipboard: Paste enabled; while recording: Stop Recording enabled, Start Recording disabled — the same enabled states as the matching menu items.

### UI-024: Each toolbar button runs its command
- Covers: IDM_FILE_NEW, IDM_FILE_SAVEALL, IDM_FILE_CLOSEALL, IDM_SEARCH_FIND, IDM_SEARCH_REPLACE, IDM_LANG_USER_DLG, IDM_VIEW_SYNSCROLLV, IDM_VIEW_SYNSCROLLH, IDM_MACRO_STARTRECORDINGMACRO, IDM_MACRO_STOPRECORDINGMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO
- Channel: ui, modal
- Steps: For each button, from a known state, `e2e_act action=toolbar value=<label>`: New; Open (panel answer None); Save (saved file, modified); Save All; Close; Close All; Cut/Copy/Paste on a selection; Undo/Redo; Find; Replace; User Language; Sync Vertical/Horizontal with a clone; Start Recording, type "ab", Stop Recording, Play.
- Expect: each does what its menu command does: a new tab; an open panel shown then cancelled; the file written; all tabs saved/closed; the text cut/copied/pasted; undone/redone; the Find window (on its Find / Replace tab) and the User Defined Language window appear; the sync flags change; the recorded macro types "ab" again.

### UI-025: Start Recording shows as active while recording
- Covers: IDM_MACRO_STARTRECORDINGMACRO, IDM_MACRO_STOPRECORDINGMACRO
- Channel: ui
- Steps: Press "Start Recording"; read `e2e_invoke app key=toolbar` → `isActiveForCommand: IDM_MACRO_STARTRECORDINGMACRO`; press "Stop Recording"; read again.
- Expect: active while recording, not active after.

### UI-026: The toolbar can be hidden
- Covers: -
- Channel: prefs, ui
- Steps: Set pref `showToolbar` false; read `e2e_ui toolbar=true` → `toolbar.visible`; set it true.
- Expect: false, then true; the editor keeps working in between.

### UI-027: Toolbar buttons as icons, icons and labels, or labels
- Covers: -
- Channel: prefs, ui
- Steps: For `toolbarDisplayMode` 0, 1, 2: set it; read `window.toolbar.displayMode` and `window.toolbarStyle`.
- Expect: 0 → icon only (NSToolbarDisplayModeIconOnly = 2); 1 → icon and label (1) and the expanded style (1); 2 → label only (3) and expanded style.

### UI-028: Toolbar size Regular or Small
- Covers: -
- Channel: prefs, ui
- Steps: With icons only, set `toolbarIconSize` 0 then 1; read `window.toolbarStyle`.
- Expect: 0 (Regular) → expanded style (1); 1 (Small) → unified compact style (4).

### UI-029: Toolbar icon set and colour
- Covers: -
- Channel: prefs, snapshot
- Steps: For `toolbarFilledIcons` false/true and `toolbarIconColour` 0 (default), 1 (red), 2 (green) with `toolbarColorizeComplete` true: set the prefs; snapshot the window including its toolbar (hook: snapshot of the whole window frame, or of the toolbar); sample the "New" button's pixels.
- Expect: the filled set differs from the outline set; with complete colourization the icon's opaque pixels are red (E8 11 23) or green (00 8B 00) within tolerance; default leaves the icon's own colours.

### UI-030: Toolbar preferences survive a restart
- Covers: -
- Channel: prefs, launch, ui
- Steps: Set `showToolbar` false and `toolbarDisplayMode` 1; `app.restart()`; read the toolbar; set `showToolbar` true; read display mode.
- Expect: the toolbar is hidden after the restart; shown again it has labels.

## Status bar

### UI-031: The status bar of a new document
- Covers: IDM_FILE_NEW
- Channel: ui
- Steps: After the reset read the status field (the NSTextField after the NppStatusPathField) and the path field.
- Expect: exactly "None (Normal Text)    length: 0    lines: 1    Ln: 1    Col: 1    Pos: 1    Unix (LF)    UTF-8    INS"; path field "(unsaved)" with no tooltip.

### UI-032: Language, length and lines follow the document
- Covers: IDM_LANG_PYTHON
- Channel: ui, mcp, keys
- Steps: Type "ab\ncd" in a new document; read; set Python (IDM_LANG_PYTHON); read; open a saved `x.json`.
- Expect: "length: 5    lines: 2" after typing; the language field "Python", then "JSON"; each field separated by four spaces.

### UI-033: Ln, Col and Pos follow the caret
- Covers: -
- Channel: ui, mcp
- Steps: Document "ab\n\tcd\n" (tab width 4); put the caret at line 2 column 2 (after the tab, `go_to`) and read; at line 1 column 3 and read.
- Expect: "Ln: 2    Col: 5    Pos: 5" (the tab counts as its width in Col); then "Ln: 1    Col: 3    Pos: 3".

### UI-034: The selection is shown as characters and lines
- Covers: IDM_EDIT_SELECTALL
- Channel: ui, mcp
- Steps: Document "héllo\nwörld\n"; select from line 1 col 2 to line 2 col 3; read; select all; read; make a two-caret multi-selection of 3 characters each (SCI_SETSELECTION/SCI_ADDSELECTION); read; make a 2x3 rectangular selection; read.
- Expect: "Sel: 7 | 2" (characters, not bytes); select all "Sel: 12 | 3"; multi-selection "Sel 2 : 4 | 2" (characters again: "hé" and "ör"); rectangular "Sel N : … | 2"; the Pos field is replaced by the Sel field while there is a selection.

### UI-035: The line-ending field names the document's EOL
- Covers: IDM_FORMAT_TODOS, IDM_FORMAT_TOUNIX, IDM_FORMAT_TOMAC
- Channel: ui, files
- Steps: Open files with CRLF, LF and CR endings; read each; then convert one with IDM_FORMAT_TODOS, IDM_FORMAT_TOMAC, IDM_FORMAT_TOUNIX.
- Expect: "Windows (CR LF)", "Unix (LF)", "Macintosh (CR)" for the files, and the field follows each conversion.

### UI-036: The encoding field names the document's encoding
- Covers: IDM_FORMAT_AS_UTF_8, IDM_FORMAT_UTF_8, IDM_FORMAT_UTF_16LE, IDM_FORMAT_UTF_16BE, IDM_FORMAT_ANSI, IDM_FORMAT_WIN_1251
- Channel: ui, files
- Steps: Open files written as UTF-8, UTF-8 with BOM, UTF-16 LE with BOM, UTF-16 BE with BOM; then a Windows-1251 file with IDM_FORMAT_WIN_1251 applied, and a Latin-1 file with IDM_FORMAT_ANSI.
- Expect: "UTF-8", "UTF-8-BOM", "UTF-16 LE BOM", "UTF-16 BE BOM", "Windows-1251" (the character set's name, as Notepad++ shows it), "ANSI".

### UI-037: INS and OVR
- Covers: -
- Channel: ui, menu, keys
- Steps: Document "abc", caret at 1; `e2e_menu_invoke` "View|Toggle Insert/Overtype"; read; type "X"; toggle again; type "Y".
- Expect: "OVR" at the end of the status after the toggle and "X" replaces "b" ("aXc"); "INS" after the second toggle and "Y" is inserted.

### UI-038: The path field shows the file's full path
- Covers: -
- Channel: ui
- Steps: Open `<tmp>/dir/a.txt`; read the path field's value, tooltip and frame and the status field's frame.
- Expect: value is the full path; tooltip "Click to copy the full path"; the path field is left of the status field and does not overlap it; it is no wider than half the window.

### UI-039: A click on the path copies it and says so
- Covers: -
- Channel: ui, clipboard
- Steps: Open `<tmp>/a.txt`; clipboard empty; click the path field (hook: a click delivered as mouse down/up to a control without an action); read the field; poll until it changes back (≤ 3 s).
- Expect: the clipboard holds the full path; the field reads "✓ Copied: <full path>" right after the click; within 3 s it shows the path again.

### UI-040: Clicking the path of an unsaved document copies nothing
- Covers: -
- Channel: ui, clipboard
- Steps: New document; clipboard "before"; click the path field (hook as in UI-039).
- Expect: the clipboard still holds "before"; the field still reads "(unsaved)".

### UI-041: The Git branch appears inside a repository only
- Covers: -
- Channel: ui, files
- Steps: `git init -b feature-x` a folder with `f.txt`; open it; poll the status field up to 3 s; open a file outside any repository (in a folder with no `.git` above it, e.g. under `$TMPDIR`).
- Expect: the status ends with "    ⎇ feature-x" for `f.txt`; no "⎇" for the file outside a repository.

### UI-042: The status bar follows the tab in front and the focused view
- Covers: IDM_VIEW_TAB_NEXT, IDM_VIEW_SWITCHTO_OTHER_VIEW
- Channel: ui, mcp
- Steps: A Python file (LF) and a CRLF text file; switch between them; clone one to the other view and move the caret there to line 2 after IDM_VIEW_SWITCHTO_OTHER_VIEW.
- Expect: language, EOL, path and Ln follow the tab in front; with the second view focused the Ln field shows its caret line.

### UI-043: The status bar can be hidden
- Covers: -
- Channel: prefs, ui
- Steps: Read the editor height; set pref `statusBarHidden` true; read the status fields' `hidden` and the editor height; set it false.
- Expect: both fields hidden, the editor 22 px taller; everything back afterwards.

## Editor context menu

### UI-044: The right-click menu is Notepad++'s default contextMenu.xml
- Covers: -
- Channel: menu, files
- Steps: With a fresh home dump `e2e_menu context=editor`; read `<home>/Library/Application Support/NotepadMac/contextMenu.xml`.
- Expect: the file exists afterwards with upstream's default content; the menu starts Cut, Copy, Paste, Delete, Select All, Begin/End Select, Begin/End Select in Column Mode, separator, "Style all occurrences of token" ▸ (Using 1st..5th Style), "Style one token" ▸ ...; every item named in the file whose command exists appears once, in file order, with separators where the file has id 0.

### UI-045: Context-menu commands act on the editor
- Covers: IDM_EDIT_CUT, IDM_EDIT_COPY, IDM_EDIT_PASTE, IDM_EDIT_SELECTALL, IDM_EDIT_BLOCK_COMMENT
- Channel: menu, clipboard, mcp
- Steps: Python document "x = 1\ny = 2\n"; select "x"; `e2e_menu_invoke context=editor` Copy; move to the end; Paste; Select All; Cut; Paste; then Toggle Single Line Comment on line 1 (if listed by the default file); read the Paste item's `enabled` with an empty clipboard.
- Expect: the text changes exactly as the menu commands would (copy/paste appends "x", cut empties, paste restores, the line gets "# "); Paste is disabled while the clipboard is empty.

### UI-046: An edited contextMenu.xml shows at the next right click
- Covers: IDM_EDIT_UPPERCASE
- Channel: files, menu
- Steps: Write contextMenu.xml: `<Item MenuEntryName="Edit" MenuItemName="Copy"/>`, `<Item id="0"/>`, `<Item id="42016" ItemNameAs="Shout"/>` (IDM_EDIT_UPPERCASE), a `FolderName="More"` group holding `<Item MenuEntryName="View" MenuItemName="Word wrap"/>`; dump the menu (no restart); invoke "Shout" on a selection "abc".
- Expect: the menu is Copy, separator, Shout, More ▸ (Word Wrap); "Shout" makes "ABC".

### UI-047: Unknown entries are skipped and a broken file does not break the menu
- Covers: -
- Channel: files, menu
- Steps: Write contextMenu.xml with `<Item id="99999"/>`, `<Item MenuEntryName="Nope" MenuItemName="Nothing"/>` and one valid Copy item; dump; then write text that is not XML; dump.
- Expect: the first menu is only Copy; with the broken file the menu still has items (the Preferences list) and the application answers normally.

### UI-048: Edit Popup ContextMenu opens the file to edit
- Covers: IDM_SETTING_EDITCONTEXTMENU
- Channel: mcp, modal
- Steps: Queue alert answer 1; run IDM_SETTING_EDITCONTEXTMENU; read the current document's path.
- Expect: an alert "Editing contextMenu" was shown; the document in front is `<home>/Library/Application Support/NotepadMac/contextMenu.xml`; editing and saving it changes the next right-click menu (as UI-046).

## Docking

### UI-049: Panels open where Notepad++ puts them and share a side as tabs
- Covers: IDM_VIEW_DOC_MAP, IDM_VIEW_FUNC_LIST, IDM_VIEW_DOCLIST, IDM_VIEW_FILEBROWSER, IDM_VIEW_PROJECT_PANEL_1
- Channel: mcp, ui
- Steps: With a fresh app open a saved `m.py`; show Document Map, Function List, Document List, Folder as Workspace, Project Panel 1; read `placeOfPanel:` for each, `panelsIn:` 0 and 1, `frontPanelIn:` 0 and 1; read the ScintillaView frame before and after.
- Expect: documentMap and functionList on the right (1), documentList, workspace and project1 on the left (0); each side lists its panels as tabs, the last shown in front; the editor got narrower on both sides and no panel overlaps it.

### UI-050: A panel moves between the sides and floats from its tab's menu
- Covers: IDM_VIEW_FUNC_LIST
- Channel: ui, menu
- Steps: Show Function List; from its dock tab's right-click menu (hook: `e2e_menu context=dock:functionList` / `e2e_menu_invoke`) choose Dock Bottom, then Dock Left, then Float; read the place and the windows after each.
- Expect: the menu lists Dock Left, Dock Right, Dock Top, Dock Bottom, Float (the current place checked), separator, Close; the place becomes 3, 0, 4; floating, an NSPanel titled "Function List" is visible and holds the list; the editor gets its width back.

### UI-051: Closing a floating panel's window hides the panel until it is asked for again
- Covers: IDM_VIEW_DOCLIST
- Channel: ui
- Steps: Float Document List; close its window (`e2e_act close_window`); read visibility; run IDM_VIEW_DOCLIST; read place and window frame.
- Expect: hidden after the close; shown again floating in a window at the same frame.

### UI-052: The close button on a dock tab hides the panel
- Covers: IDM_VIEW_DOC_MAP
- Channel: ui
- Steps: Show Document Map; click the dock tab's close box (hook: click at a point of the NppDockContainerView tab); read visibility; run IDM_VIEW_DOC_MAP.
- Expect: hidden after the click; the command shows it again on the right.

### UI-053: Two panels can float together in one window
- Covers: IDM_VIEW_FUNC_LIST, IDM_VIEW_DOCLIST
- Channel: ui
- Steps: Float Function List; drag Document List's dock tab onto the floating window (hook: drag of a dock tab to a screen point); read `panelsFloatingWith: functionList` and the windows.
- Expect: one floating window holding both as tabs; closing it hides both.

### UI-054: Where the panels are is remembered across a restart
- Covers: IDM_VIEW_FUNC_LIST, IDM_VIEW_DOCLIST, IDM_VIEW_DOC_MAP
- Channel: prefs, launch, ui
- Steps: Pref `rememberPanelState` true; move Function List to the bottom, float Document List, show Document Map; `app.restart()`; read places, visibility and the floating window frame; read pref `dockLayout`.
- Expect: after the restart Function List and Document List are visible again, at the bottom and floating (same frame ±2 px); `dockLayout.places` records 3 and 4.

### UI-055: Remember panel state, panel by panel
- Covers: IDM_VIEW_DOCLIST, IDM_VIEW_FUNC_LIST
- Channel: prefs, launch, ui
- Steps: Show Document List and Function List; for (`rememberPanelState` false), (true), (true with `panelStateKeep` {functionList: false}): restart and read which are visible.
- Expect: none reopen when off; both reopen when on; only Document List reopens when Function List is excluded.

### UI-056: A dock's size is kept
- Covers: IDM_VIEW_FUNC_LIST
- Channel: ui, prefs, launch
- Steps: Show Function List on the right; drag the divider so the right dock is 320 px (hook: move a split view divider, or `e2e_invoke` the split's `setPosition:ofDividerAtIndex:`); restart with panels remembered.
- Expect: `sizeOfPlace: 1` is 320 (±2) before and after the restart; `dockLayout.sizes.1` is 320.

## Document switcher

### UI-057: Ctrl+Tab shows the switcher with the most recent documents first
- Covers: -
- Channel: keys, ui
- Steps: Prefs `docSwitcherEnabled` and `docSwitcherMRU` true; open A, B, C, then bring A in front; press `ctrl+tab` (Control kept held: hook to hold/release a modifier); read the windows and the switcher table's cells and selection; release Control.
- Expect: while held, a borderless panel is visible listing A, C, B (most recent first) with row 1 (C) selected and C already in front; after the release the panel is gone and C stays in front.

### UI-058: Ctrl+Tab repeated and Ctrl+Shift+Tab walk the list
- Covers: -
- Channel: keys, ui
- Steps: As UI-057; press `ctrl+tab` twice while holding Control, then `ctrl+shift+tab`; release.
- Expect: the selection goes to row 2 (B), then back to row 1 (C); C is in front at the end.

### UI-059: Without MRU the switcher follows the tab order
- Covers: -
- Channel: keys, prefs
- Steps: `docSwitcherMRU` false; A, B, C with A in front after visiting C; `ctrl+tab`.
- Expect: the list is A, B, C and B comes to the front.

### UI-060: With the switcher off Ctrl+Tab steps through the tabs
- Covers: -
- Channel: keys, prefs, ui
- Steps: `docSwitcherEnabled` false; A, B, C with C in front; press `ctrl+tab`, then `ctrl+shift+tab` twice.
- Expect: no switcher window appears; the document in front goes A, then C, then B.

### UI-061: Ctrl+Tab with a single document does nothing
- Covers: -
- Channel: keys, ui
- Steps: One document; press `ctrl+tab`.
- Expect: no switcher window; the document stays; no error.

## Rendering, themes and dialogs

### UI-062: Light and dark appearance
- Covers: -
- Channel: prefs, snapshot, mcp
- Steps: For appearanceMode 1 and 2: set the pref; read SCI_STYLEGETBACK of STYLE_DEFAULT (32) on main (and on sub with a clone, and on the Document Map view via hook `e2e_sci view=map`); snapshot the window and take the editor area's median luminance; read `window.effectiveAppearance.name`.
- Expect: light: background luminance > 0.7 and appearance Aqua; dark: < 0.3 and DarkAqua; both views and the map agree; the change applies at once without a restart and the text stays unchanged.

### UI-063: Following the system appearance
- Covers: -
- Channel: prefs, ui
- Steps: Set appearanceMode 0; read the window's effective appearance and the editor background.
- Expect: the effective appearance is the system's (read `nsapp.effectiveAppearance.name`), and the editor background is dark exactly when it is DarkAqua.

### UI-064: The window renders its chrome in a snapshot
- Covers: -
- Channel: snapshot
- Steps: Snapshot the main window with a saved file open in light and in dark mode; check the regions of the tab bar, the editor, the line-number margin and the status bar.
- Expect: each region is non-uniform (text drawn): the tab label, line numbers, text and the status bar's words are visible (the status bar strip is not blank white); the snapshot is as large as the window's content.

### UI-065: Nothing is cut off in the main dialogs
- Covers: IDM_SEARCH_FIND, IDM_SEARCH_REPLACE, IDM_SEARCH_FINDINFILES, IDM_SEARCH_MARK, IDM_SETTING_PREFERENCE, IDM_LANGSTYLE_CONFIG_DLG, IDM_SETTING_SHORTCUT_MAPPER, IDM_SEARCH_GOTOLINE, IDM_EDIT_COLUMNMODE, IDM_LANG_USER_DLG, IDM_ABOUT
- Channel: ui, snapshot
- Steps: For each dialog (Find on each of its tabs, Preferences on each page selected in its list, Style Configurator, Shortcut Mapper, Go To, Column Editor, User Defined Language, About): open it, read every visible label and button with its frame and needed size (hook: `cell_size` and `wraps` in `e2e_ui`), snapshot it, close it.
- Expect: for every non-wrapping label and button the needed width and height fit in its frame (+1.5 px); no two visible controls of one page overlap; no control lies outside its window; the snapshot is saved as an artefact.

### UI-066: The main window's chrome at a small size
- Covers: -
- Channel: ui
- Steps: Resize the main window to 640x400 (hook: `e2e_act action=resize_window`, as a drag of the window's corner would); open a file with a long path; read the toolbar items, the path field and the status field; resize back.
- Expect: the toolbar shows its overflow indicator (NSToolbarClippedItemsIndicator) instead of overlapping buttons; the path field takes at most half the width and the status field starts after it; the editor still has a positive size.

### UI-067: The two views lie side by side without overlap
- Covers: IDM_VIEW_CLONE_TO_ANOTHER_VIEW
- Channel: ui
- Steps: Clone a document to the other view; read both ScintillaView frames and the tab bar's.
- Expect: two ScintillaViews whose frames do not overlap and together fill the editor area; each has a positive size; closing the second view's content (Move it back with IDM_VIEW_GOTO_ANOTHER_VIEW from there) leaves one view filling the area.
