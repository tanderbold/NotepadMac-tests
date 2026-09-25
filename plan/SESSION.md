# SESSION — Session files, session restore, snapshot and periodic backup

Sessions as Notepad++ keeps them: File > Save Session / Load Session (session files in Notepad++'s own `session.xml` format, so a session moves between Windows and the Mac), the session written at quit and read at launch (`restoreSession`), and the session snapshot with periodic backup of unsaved documents (`autosaveEnabled`, `autosaveInterval`), which lets the application quit without asking and survive a crash. What a session holds is checked in the file and after loading: open files in tab order, the active tab, caret and selection, first visible line, bookmarks, folds, language, the code page chosen, pinned tabs, tab colour, the user's read-only, monitoring, untitled documents through their backups, the second view with its divider, and the Folder as Workspace roots. Out of scope: the Preferences controls for these options (SETTINGS-009, 062, 088), backup-on-save copies (SETTINGS-060), the `-openSession` and `-nosession` switches (CLI). Conventions: the session in the scratch home is `app.home/"Library/Application Support/NotepadMac/session.xml"` and backups are in its `backup` folder; tests about restore start with `app.start(session=True, defaults={"restoreSession": True, …})` (without `session=True` the harness passes `-nosession`, and then nothing is loaded or written) and restart with `app.restart(session=True)`; the application must be quit gracefully, by `terminate:` sent to `nsapp` (queued alert answers cover any question) — a kill is used only where a crash is meant. Session files for Save/Load Session go through queued panel answers. XML is checked with `xml.etree`; line numbers in `<Mark>`/`<Fold>` are 0-based, `startPos`/`endPos` are anchor and caret byte positions.

## Save Session and Load Session

### SESSION-001: Save Session writes Notepad++'s session.xml
- Covers: IDM_FILE_SAVESESSION
- Channel: modal, mcp, files
- Steps: Open `tmp/a.py` (4 lines), select line 2 columns 3-6 (anchor before caret), bookmark lines 1 and 3; open `tmp/b.cpp` ("int f() {\n  return 1;\n}\n"), fold line 1 (SCI_FOLDLINE), run "File|Pin Tab", IDM_VIEW_TAB_COLOUR_3 and IDM_EDIT_TOGGLEREADONLY; select a.py again; queue panel answer `tmp/s.xml`; run IDM_FILE_SAVESESSION.
- Expect: `tmp/s.xml` parses; root `NotepadPlus` > `Session activeView="0"` > `mainView` with `activeIndex` equal to a.py's position among the File entries, and an empty `subView activeIndex="0"`; one `File` per open file in tab order (untitled clean tabs are left out); a.py's File has `filename` = its path, `lang="Python"`, `startPos`/`endPos` = the selection's anchor/caret, `encoding="-1"`, `userReadOnly="no"`, `tabPinned="no"`, `tabColourId="-1"` and `<Mark line="0"/>`, `<Mark line="2"/>`; b.cpp's has `lang="C++"`, `tabPinned="yes"`, `tabColourId="2"`, `userReadOnly="yes"` and `<Fold line="0"/>`; the port's own attributes `macLanguage`, `macEncoding`, `macBOM`, `macEOL`, `macMonitoring` are present.

### SESSION-002: Load Session brings every file back as it was
- Covers: IDM_FILE_LOADSESSION
- Channel: modal, mcp
- Steps: Build the state of SESSION-001 and save it to `tmp/s.xml`; close all (discarding); queue panel answer `tmp/s.xml`; run IDM_FILE_LOADSESSION.
- Expect: a.py and b.cpp are open in that order and a.py is the current tab; a.py's selection is line 2 columns 3-6 with the caret at the end, its bookmarks are lines 1 and 3 (`bookmarks` tool); b.cpp is pinned, has tab colour 3, is read-only (SCI_GETREADONLY 1) and line 1 is folded (SCI_GETFOLDEXPANDED(0) = 0) with lines 2-3 hidden; languages are python and cpp; neither document is modified.

### SESSION-003: The active tab is found by path, whatever is open before
- Covers: IDM_FILE_LOADSESSION
- Channel: modal, mcp
- Steps: Make an untitled tab with text; open `tmp/s1.txt`, `tmp/s2.txt`, select s1.txt; save the session; close s1 and s2; make two more untitled tabs; load the session.
- Expect: after loading s1.txt is current (not the tab at the index that was saved); the untitled tabs are still there and unchanged.

### SESSION-004: Loading a session skips files that no longer exist
- Covers: IDM_FILE_LOADSESSION
- Channel: modal, mcp, files
- Steps: Open `tmp/k1.txt`, `tmp/k2.txt`, `tmp/k3.txt`; save the session; close all; delete k2.txt; load the session.
- Expect: k1.txt and k3.txt are open; no tab, no alert for k2.txt; k2.txt was not created.

### SESSION-005: A session.xml written by Notepad++ on Windows is read
- Covers: IDM_FILE_LOADSESSION
- Channel: modal, mcp, files
- Steps: Write `tmp/win.xml` as Windows Notepad++ writes it: mainView activeIndex="1" with a File for `C:\Users\someone\gone.py` (lang "Python") and a File for `tmp/real.cpp` with lang="C++", startPos="3", endPos="7", tabColourId="2", tabPinned="yes", userReadOnly="yes" and `<Mark line="1"/>`, none of the port's mac… attributes; load it.
- Expect: only real.cpp is opened (the Windows path is passed over without an alert); it is current, language cpp, selection anchor 3 caret 7, pinned, tab colour 3, read-only, with a bookmark on line 2.

### SESSION-006: A cancelled Load Session and a file that is not a session change nothing
- Covers: IDM_FILE_LOADSESSION
- Channel: modal, mcp
- Steps: Note the tabs; queue panel answer None and run IDM_FILE_LOADSESSION; write `tmp/not_session.txt` = "hello" and load it with alert answer 1 queued.
- Expect: the cancel shows no alert and changes nothing; the plain text file opens nothing (no tab for it, no tab closed) and an error alert is shown.

### SESSION-007: The session keeps the second view and the Folder as Workspace roots
- Covers: IDM_FILE_SAVESESSION, IDM_FILE_LOADSESSION
- Channel: modal, mcp, ui, files
- Steps: Open `tmp/v.txt` (50 lines); run IDM_VIEW_CLONE_TO_ANOTHER_VIEW; scroll the second view to line 20 (SCI_SETFIRSTVISIBLELINE on `sub`); note the height share of the main view (frames from `e2e_ui`); open folders `tmp/rootA` and `tmp/rootB` as workspace roots; save the session; hide the second view, close the workspace panel, close all; load the session.
- Expect: the file has a `subView` File for v.txt with `firstVisibleLine="19"` and a `macSplit` equal to the noted share (±0.02), and a `FileBrowser` element with `root foldername=` entries for rootA and rootB; after loading, the second view is shown with v.txt at first visible line 19, the main view's share is within 0.05 of the noted one, and `workspace_roots` is [rootA, rootB].

### SESSION-008: The session keeps a chosen code page and monitoring
- Covers: IDM_FILE_SAVESESSION, IDM_FILE_LOADSESSION
- Channel: modal, mcp, files
- Steps: Write `tmp/koi.txt` as KOI8-R bytes of "Привет, мир\n"; open it and run IDM_FORMAT_KOI8R_CYRILLIC; open `tmp/tail.log` and run IDM_VIEW_MONITORING; save the session; close all; load it; append "more\n" to tail.log.
- Expect: koi.txt's File has `encoding="20866"`; after loading its text is "Привет, мир\n", its encoding "cp20866", not modified; tail.log's File has `macMonitoring="yes"`, it is monitored again after loading (read-only) and shows "more" within a few seconds.

### SESSION-009: Loading a session adds to the open tabs without duplicating
- Covers: IDM_FILE_LOADSESSION
- Channel: modal, mcp
- Steps: Save a session with `tmp/l1.txt` and `tmp/l2.txt`; close l2.txt; open `tmp/l3.txt`; load the session.
- Expect: the tabs hold l1.txt once, l2.txt once and l3.txt (nothing that was open was closed).

### SESSION-010: The Save and Load Session panels speak of session files
- Covers: IDM_FILE_SAVESESSION, IDM_FILE_LOADSESSION
- Channel: modal, prefs
- Steps: Queue None and run IDM_FILE_SAVESESSION; set sessionFileExtension "npps", queue None, run it again; queue None and run IDM_FILE_LOADSESSION (the panel log with the panel's allowed types, see report); set the preference back to "".
- Expect: the proposed name does not claim a format the file is not in (no ".json" for an XML file; Notepad++ offers "Session file" with the defined extension): with the extension set it ends in ".npps"; the Load panel accepts .xml and .npps session files, not only .json.

## Session on restart

### SESSION-011: Quitting writes the session and the next launch restores it
- Covers: -
- Channel: launch, mcp, files
- Steps: Start with `session=True, defaults={"restoreSession": True}`; open `tmp/r1.py` and `tmp/r2.txt`; in r1.py put the caret on line 3 column 2 and bookmark line 2; select r2.txt then r1.py; quit gracefully; read session.xml; start again with `session=True` keeping home and preferences.
- Expect: session.xml exists in the home and lists r1.py and r2.txt with activeIndex pointing at r1.py; after the restart both files are open in the same order, r1.py is current with the caret at line 3 column 2 and a bookmark on line 2, language python; neither is modified.

### SESSION-012: Unsaved edits are asked about at quit when there is no snapshot
- Covers: -
- Channel: launch, modal, mcp, files
- Steps: Start with restoreSession on and autosaveEnabled off; open `tmp/e.txt` = "disk", change it to "edited"; make an untitled tab with "note"; queue alerts 2, 2; quit gracefully; restart with `session=True`.
- Expect: two "Save" alerts were shown (one per modified document); e.txt still holds "disk"; after the restart e.txt is open with "disk", not modified, and no tab holds "note".

### SESSION-013: Files removed between two launches are left out quietly
- Covers: -
- Channel: launch, mcp, files
- Steps: Start with restoreSession on; open `tmp/stay.txt` and `tmp/vanish.txt`; quit gracefully; delete vanish.txt; restart with `session=True`.
- Expect: stay.txt is open; there is no tab for vanish.txt and no alert in the modal log.

### SESSION-014: The second view and workspace roots come back after a restart
- Covers: -
- Channel: launch, mcp, ui
- Steps: Start with restoreSession on; open `tmp/w.txt`, clone it to the other view; open `tmp/wsroot` as workspace; quit gracefully; restart with `session=True`.
- Expect: the second view is visible and shows w.txt; `workspace_roots` is [`tmp/wsroot`] and the panel is visible.

### SESSION-015: A session.json from an earlier build is taken over once
- Covers: -
- Channel: launch, mcp, files
- Steps: Stop the app; in the home write `Library/Application Support/NotepadMac/session.json` = {"version": 2, "files": [{"path": "<tmp/old.txt>", "caret": 2, "language": "normal"}], "currentPath": "<tmp/old.txt>", "unsaved": []}; start with `session=True, clean_home=False, defaults={"restoreSession": True}`; quit gracefully.
- Expect: at launch old.txt is open with the caret at position 2; session.json is gone and session.xml exists (in XML, listing old.txt) after the quit.

## Snapshot and periodic backup

### SESSION-016: With the snapshot on, quitting asks nothing and unsaved text comes back
- Covers: -
- Channel: launch, modal, mcp, files
- Steps: Start with `session=True, defaults={"restoreSession": True, "autosaveEnabled": True}`; open `tmp/snap.txt` = "on disk\n" and change it to "unsaved change\n"; make an untitled tab and type "never saved"; quit gracefully with no alert answers queued; restart with `session=True`.
- Expect: the quit showed no alert (the modal log was empty before quitting); snap.txt on disk still holds "on disk\n"; after the restart snap.txt shows "unsaved change\n" and is modified; an untitled tab with its old name ("new 2") shows "never saved" and is modified; session.xml's File entries carry `backupFilePath` values that exist in the backup folder.

### SESSION-017: The periodic backup writes unsaved text at the interval
- Covers: -
- Channel: launch, mcp, files
- Steps: Start with `session=True, defaults={"restoreSession": True, "autosaveEnabled": True, "autosaveInterval": 5}`; open `tmp/pb.txt` = "orig\n" and change it to "changed\n"; make an untitled tab with "draft"; poll the backup folder for up to 15 s.
- Expect: two backup files appear, named "pb.txt@<yyyy-MM-dd_HHmmss>" and "new 2@<…>", holding "changed\n" and "draft"; pb.txt on disk still holds "orig\n"; session.xml has been rewritten and names both backups; the documents stay modified.

### SESSION-018: After a crash the unsaved text comes back from the backups
- Covers: -
- Channel: launch, mcp, files
- Steps: As SESSION-017, wait for the backups, then kill the process (SIGKILL, no quit); start with `session=True, clean_home=False, reset=False`.
- Expect: pb.txt is open with "changed\n", modified, and the untitled tab with "draft", modified; pb.txt on disk still holds "orig\n".

### SESSION-019: Saving or discarding a document removes its backup
- Covers: IDM_FILE_SAVE, IDM_FILE_CLOSE
- Channel: launch, modal, mcp, files
- Steps: With the snapshot on and interval 5, get backups for an edited `tmp/d1.txt`, an edited `tmp/d2.txt` and an untitled tab; save d1.txt; close d2.txt answering No (alert 2); empty the untitled tab's text; wait one more interval.
- Expect: d1.txt's backup file is gone right after the save; d2.txt's backup is gone after the close; the untitled tab's backup is gone after the next pass (an emptied untitled document keeps nothing); session.xml no longer names any of them.

### SESSION-020: A backup older than the file is not restored over newer content
- Covers: -
- Channel: launch, mcp, files
- Steps: With the snapshot on, edit `tmp/newer.txt` to "backup text" and wait for its backup; kill the process; write "changed elsewhere" to newer.txt (a newer mtime than the backup); start with `session=True, clean_home=False, reset=False`.
- Expect: newer.txt shows "changed elsewhere", not modified; its old backup file has been deleted.

### SESSION-021: A document too large to back up is still asked about at quit
- Covers: -
- Channel: launch, modal, mcp
- Steps: Start with the snapshot on and largeFileThresholdMB 1; open a 2 MB `tmp/large.txt`, type a character; make an untitled tab with "small"; queue alert 3 (Cancel); quit gracefully.
- Expect: one "Save" alert, for large.txt only (the untitled one is covered by its backup); after Cancel the application is still running with both tabs.

### SESSION-022: Without the snapshot nothing is backed up
- Covers: -
- Channel: launch, mcp, files
- Steps: Start with `session=True`, restoreSession on, autosaveEnabled off; edit an opened file and an untitled tab; wait 7 s.
- Expect: the backup folder is absent or empty; session.xml has not been written yet (it is written at quit).
