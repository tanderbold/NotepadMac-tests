# VISUAL — What the window shows, in pixels

Every other area reads the application's state: text, selections, menus, controls, frames. A view that paints over another one leaves all of that right and the window wrong (the second view's tab bar once filled the whole pane below it with the window's colour, and only a screenshot showed it). This area looks at the window as the window server composites it (`e2e_snapshot screen=true`). Structural checks, which do not depend on how text is rendered, run for each key layout: every editor pane on screen shows its document (its line-number margin and its text area are, band by band from top to bottom, in the colours Scintilla was given for them — STYLE_LINENUMBER's and STYLE_DEFAULT's backgrounds — so nothing else is painted over them, and both carry ink: digits and text), no tab bar's frame lies over a pane, every tab the bar shows whole has its label drawn, and a docked panel's tab and content are not blank. Golden pictures cover a few windows that do not change from run to run: they are kept at 1x in `fixtures/golden/<name>.png`, compared after a light blur with a per-channel threshold and a largest share of differing pixels, and written again with `pytest --update-goldens`. Conditions are fixed for the whole area: the app is started with scroll bars always shown and window animations off, the main window is 860x560 points and centred (so it fits a 1024x768 screen), the Default themes, the caret hidden and no field editing when a golden is taken; texts that change by design (the version and build in About, the scratch folder's path in the title and status bar) are masked. Pictures are left in `.work/<worker>/visual`.

## Layouts

### VISUAL-001: One view shows its text, line numbers and tab labels
- Covers: -
- Channel: snapshot, mcp, prefs
- Steps: For each of light and dark appearance (appearanceMode 1, 2): open `stations.ts` and `forecast.py`; take the main window's picture.
- Expect: one pane and one tab bar on screen; the pane passes the pane checks (four bands of margin and text in their own colours, digits and text drawn at its top); both tabs show their labels; the bar does not overlap the pane.

### VISUAL-002: Two views side by side both show their documents
- Covers: IDM_VIEW_GOTO_ANOTHER_VIEW
- Channel: snapshot, mcp, prefs
- Steps: For each of light and dark appearance: open `stations.ts` and `forecast.py`; move `forecast.py` to the other view; take the picture.
- Expect: two panes and two tab bars; both panes pass the pane checks (the second view's bar does not paint over its pane); every tab label is drawn.

### VISUAL-003: Two views one above the other both show their documents
- Covers: IDM_VIEW_GOTO_ANOTHER_VIEW
- Channel: snapshot, mcp
- Steps: With the editors' split turned horizontal (NSSplitView.vertical NO: the port has no Rotate on the divider, upstream's SplitterContainer::rotateTo), move a document to the other view; take the picture.
- Expect: two panes, the second below the first, two tab bars; both panes pass the pane checks.

### VISUAL-004: Each panel docked on each side is drawn beside the editor
- Covers: IDM_VIEW_FUNC_LIST, IDM_VIEW_DOC_MAP, IDM_VIEW_DOCLIST, IDM_VIEW_FILEBROWSER
- Channel: snapshot, mcp
- Steps: For each side (left, right, top, bottom), with `forecast.py` of a repository with a change in front: show each of Function List, Document Map, Document List, Folder as Workspace and the Git panel in turn, move it to that side, take the picture, hide it.
- Expect: the pane passes the pane checks and its tab labels are drawn; the dock region between the editor and the content's edge has ink in its tab header (the panel's title) and in its content.

### VISUAL-005: A vertical tab bar shows every label beside the pane
- Covers: -
- Channel: snapshot, prefs
- Steps: Open six files; set tabBarVertical; take the picture.
- Expect: the bar is left of the pane, six tabs, every label drawn; the pane passes the pane checks.

### VISUAL-006: Multi-line tabs show every label above the pane
- Covers: -
- Channel: snapshot, prefs
- Steps: Open fourteen files; set tabBarMultiLine; take the picture.
- Expect: the tabs take more than one row; every label drawn; the pane below passes the pane checks.

### VISUAL-007: Compare shows both texts side by side
- Covers: -
- Channel: snapshot, modal
- Steps: Open `new.py` and compare it with `old.py` (Compare with File…); take the picture; clear the compare.
- Expect: two panes, both pass the pane checks (the changed lines' colours leave the background most of each band).

### VISUAL-008: Markdown Preview renders beside the text
- Covers: -
- Channel: snapshot, mcp
- Steps: Open `README.md`; show Markdown Preview; wait for its page; take the picture.
- Expect: the pane passes the pane checks; the preview's dock region has ink in its tab and its content (the rendered page).

### VISUAL-009: Search results are drawn with the document
- Covers: IDM_SEARCH_FINDINFILES
- Channel: snapshot, ui
- Steps: Find in Files "station" in a folder of two files; close the dialog; take the picture.
- Expect: every pane on screen (the document and the results) passes the pane checks; every tab label drawn.

### VISUAL-010: Distraction-free mode shows the text alone
- Covers: IDM_VIEW_DISTRACTIONFREE
- Channel: snapshot, mcp
- Steps: Open `forecast.py`; turn distraction-free mode on; take the picture; turn it off.
- Expect: one pane passing the pane checks; no tab bar on screen.

## Goldens

### VISUAL-011: Preferences pages look as recorded
- Covers: IDM_SETTING_PREFERENCE
- Channel: snapshot, ui
- Steps: For each of General, Editing 1, Margins/Border/Edge and Tab Bar: open Preferences on that page, no field editing; take the window's picture.
- Expect: it matches `fixtures/golden/prefs-<page>.png`.

### VISUAL-012: The Find dialog looks as recorded
- Covers: IDM_SEARCH_FIND
- Channel: snapshot, ui
- Steps: Open the Find dialog at its defaults on the Find tab, no field editing; take its picture.
- Expect: it matches `fixtures/golden/find.png`.

### VISUAL-013: About looks as recorded but for its version
- Covers: IDM_ABOUT
- Channel: snapshot, ui
- Steps: Open About; mask the version, build and build-time lines; take its picture.
- Expect: exactly three lines masked; the rest matches `fixtures/golden/about.png`.

### VISUAL-014: The main window on a demo file looks as recorded
- Covers: -
- Channel: snapshot, mcp, prefs
- Steps: For each of light and dark appearance: open `stations.ts` and `forecast.py`, caret at 12:5 and hidden; mask the title and the status bar's path; take the picture.
- Expect: it matches `fixtures/golden/main-<appearance>.png`.
