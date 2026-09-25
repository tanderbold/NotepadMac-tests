# FILE — File menu, opening and saving, closing, recent files, files on disk

The File menu of NotepadMac as `plan/commands.tsv` lists it (27 commands, plus the port's File > Pin Tab, Open Recent and Restore Last Closed File, and the "(root)" ＋ / ✕ entries, which are IDM_FILE_NEW / IDM_FILE_CLOSE): New, Open, the Open Containing Folder family, Open in Default Viewer, Open Folder as Workspace, Reload, Save / Save As / Save a Copy As / Save All / Rename, the Close family, Move to Trash, Print / Print Now and Exit; and around them: files kept byte-for-byte in their encoding and line endings on save, read-only and unreadable files, symlinks and permissions, big and huge files, files changed or deleted by other programs, monitoring (tail -f), and the recent files list. Out of scope: how an encoding is detected and the Encoding menu (ENCODING), the Preferences pages that steer these commands (SETTINGS: backup on save, auto-detection options, recent-files display, default directory, large-file options, print options), session files (SESSION), the command line (CLI). Conventions: files are written byte-exact with Python into `tmp`; documents are opened with `app.open(path)` unless the case is about File > Open; commands run with `app.run("IDM_…")` or by menu path (`app.run("File|Pin Tab")`); open and save panels are answered with `app.answers(panels=[path | [paths] | None])` and alerts with `app.answers(alerts=[n | "Title"])`, and what was shown is read from `app.modal_log()` (kind, message, informative, buttons, name, directory, answered). The MCP `run_command` refuses IDM_FILE_EXIT and IDM_FILE_DELETE ("left to the user"), so those two are invoked as a click would: `e2e_menu_invoke` with path "File|Move to Trash" / "NotepadMac|Quit NotepadMac", or `app.keys("cmd+q")`. Commands that hand a file to Finder, Terminal, the default viewer or a printer need the workspace and print hooks listed in the report; until they exist those cases are skipped, never run for real. "Modified" is `doc()["modified"]`; "the window shows it edited" is `app.get("window", "documentEdited")`. After `app.close_all()` one empty "new 1" remains.

## New

### FILE-001: New adds an empty untitled tab in front
- Covers: IDM_FILE_NEW
- Channel: mcp, keys, menu
- Steps: From the clean slate (one "new 1"), run IDM_FILE_NEW; press cmd+n; invoke the "(root)" ＋ equivalent by running command id 41001.
- Expect: after each step one more tab, named "new 2", "new 3", "new 4" in turn; the new tab is current, its text is "", `path` is null, not modified, encoding "UTF-8", eol "LF", language "normal"; the window title is the tab name; the menu item IDM_FILE_NEW carries the key "cmd+n".

### FILE-002: New takes the lowest free "new N" number
- Covers: IDM_FILE_NEW
- Channel: mcp
- Steps: Run IDM_FILE_NEW twice (tabs new 1, new 2, new 3); close "new 2" (close_document, discard); run IDM_FILE_NEW; then close all and run IDM_FILE_NEW once more.
- Expect: the tab made after closing "new 2" is named "new 2" (never a second "new 3"); no two tabs ever share a title; after Close All the fresh tab is "new 1" and the next New is "new 2".

## Open

### FILE-003: Open a file through the Open panel
- Covers: IDM_FILE_OPEN
- Channel: mcp, modal, files
- Steps: Write `tmp/a/one.py` = "import os\nx = 1\n"; open `tmp/a/other.txt` first so the current document lives in `tmp/a`; queue panel answer `tmp/a/one.py`; run IDM_FILE_OPEN.
- Expect: the modal log has one entry of kind "open" answered with that path whose `directory` is `tmp/a` (the current document's folder); a tab "one.py" is current with the file's exact text, language "python", not modified, caret at line 1 column 1; the window title is "one.py — <tmp/a>"; the status bar field shows the full path.

### FILE-004: Open several files at once
- Covers: IDM_FILE_OPEN
- Channel: mcp, modal
- Steps: Write `tmp/m1.txt`, `tmp/m2.md`, `tmp/m3.json`; queue one panel answer that is the list of the three paths; run IDM_FILE_OPEN.
- Expect: three new tabs in the order given (m1.txt, m2.md, m3.json), each with its file's text and language (normal, markdown, json); m3.json is current; nothing else was asked (the log has only the panel).

### FILE-005: A cancelled Open panel changes nothing
- Covers: IDM_FILE_OPEN
- Channel: mcp, modal, keys
- Steps: Note the documents; queue panel answer None; press cmd+o.
- Expect: the log has an "open" panel answered "cancel"; the documents, the current tab and its text are unchanged; no alert was shown.

### FILE-006: Opening a file that is already open brings its tab forward
- Covers: IDM_FILE_OPEN
- Channel: mcp, modal
- Steps: Open `tmp/dup.txt`, type "edit " at its start (modified), open `tmp/other.txt`; queue panel answer `tmp/dup.txt` and run IDM_FILE_OPEN; then `app.open(tmp/dup.txt)` again.
- Expect: the number of tabs does not grow; dup.txt becomes current both times; its unsaved text "edit …" is kept (not reloaded) and it stays modified.

### FILE-007: Opening a file replaces a lone, clean untitled tab
- Covers: IDM_FILE_OPEN
- Channel: mcp, modal
- Steps: From the clean slate (only an empty, unmodified "new 1"), open `tmp/x.txt` through the Open panel; then make a new tab, type "keep", and open `tmp/y.txt`.
- Expect: after the first open the only tab is "x.txt" ("new 1" was replaced, as Notepad++'s loadBufferIntoView does); after the second the modified untitled tab is kept beside y.txt.

### FILE-008: A file with a Unicode name and spaces opens and saves back to itself
- Covers: IDM_FILE_OPEN, IDM_FILE_SAVE
- Channel: mcp, modal, files
- Steps: Write `tmp/тест файл ☃ 文件.txt` = "héllo\n"; open it through the panel; type "!" at the end of line 1; run IDM_FILE_SAVE.
- Expect: the tab title is "тест файл ☃ 文件.txt"; `path` equals the file's path (NFC as written); after saving the same file holds "héllo!\n" in UTF-8 and no other file was created in `tmp`.

### FILE-009: An empty file opens as an empty UTF-8 document and saves as zero bytes
- Covers: IDM_FILE_OPEN, IDM_FILE_SAVE
- Channel: mcp, files
- Steps: Create a 0-byte `tmp/empty.txt`; open it; run IDM_FILE_SAVE; then type "a", delete it with backspace, save again.
- Expect: text "", encoding "UTF-8", eol "LF", not modified; after both saves the file is still 0 bytes (no BOM, no newline added).

### FILE-010: A file that is gone by the time it is opened gives an error and no tab
- Covers: IDM_FILE_OPEN
- Channel: modal, mcp
- Steps: Queue panel answer `tmp/missing.txt` (not on disk) and alert answer 1; run IDM_FILE_OPEN.
- Expect: an alert whose message says the file "missing.txt" couldn't be opened because there is no such file; no tab was added; the current document is unchanged.

### FILE-011: A file without read permission gives an error and no tab
- Covers: IDM_FILE_OPEN
- Channel: modal, mcp, files
- Steps: Write `tmp/noread.txt` and chmod it 000; queue its path and alert answer 1; run IDM_FILE_OPEN; restore the mode afterwards.
- Expect: an alert saying "noread.txt" couldn't be opened because of permission; no tab was added.

### FILE-012: A read-only file opens read-only in the editor
- Covers: IDM_FILE_OPEN, IDM_FILE_SAVE
- Channel: mcp, keys, files
- Steps: Write `tmp/ro.txt` = "locked\n" and chmod 444; open it; type "X" at line 1 and press backspace; run IDM_FILE_SAVE; restore the mode.
- Expect: SCI_GETREADONLY is 1; the text is still "locked\n" after typing; the document is not modified; the file on disk is unchanged in content and still mode 444.

## Save

### FILE-013: Save writes the document and clears the modified state
- Covers: IDM_FILE_SAVE
- Channel: mcp, keys, files
- Steps: Open `tmp/s.txt` = "one\n"; type "two " at its start; read modified and the window's documentEdited; press cmd+s.
- Expect: before saving the document is modified and documentEdited is true; after cmd+s the file holds "two one\n", modified is false, documentEdited is false, and SCI_CANUNDO is still 1 (saving keeps the undo history).

### FILE-014: Save keeps the file's encoding, byte order mark and line endings
- Covers: IDM_FILE_SAVE
- Channel: mcp, keys, files
- Steps: For each of: UTF-8 "a\nb\n"; UTF-8 with BOM; UTF-16 LE with BOM; UTF-16 BE with BOM; Latin-1 b"caf\xe9\nx\n"; UTF-8 with CRLF "a\r\nb\r\n"; UTF-8 with CR "a\rb\r": write the file, open it, put the caret at the end of line 1, type "Z" and press return, save.
- Expect: the bytes on disk are the original bytes with "Z" + the file's own line ending inserted after the first line, all in the file's encoding (same BOM, UTF-16 code units, é still byte E9); `doc()["encoding"]` and `doc()["eol"]` are what they were when the file was opened.

### FILE-015: Saving an untitled document asks where, then the tab becomes that file
- Covers: IDM_FILE_SAVE
- Channel: mcp, modal, files
- Steps: Run IDM_FILE_NEW, type "print(1)\n"; queue panel answer `tmp/new.py`; run IDM_FILE_SAVE.
- Expect: a "save" panel was shown proposing the name "new 2" (the tab's name); `tmp/new.py` holds "print(1)\n"; the tab is titled "new.py", `path` is that file, language "python", not modified.

### FILE-016: Cancelling the Save panel of an untitled document keeps it untitled
- Covers: IDM_FILE_SAVE
- Channel: mcp, modal
- Steps: Make a new tab, type "draft"; queue panel answer None; run IDM_FILE_SAVE.
- Expect: the panel was answered "cancel"; the tab keeps its "new N" name, `path` null, text "draft", still modified; no file was written.

### FILE-017: Save and Save All are disabled when there is nothing to save
- Covers: IDM_FILE_SAVE, IDM_FILE_SAVEALL
- Channel: menu, mcp, files
- Steps: Open `tmp/clean.txt` and note its modification time; read the enabled state of IDM_FILE_SAVE and IDM_FILE_SAVEALL; run IDM_FILE_SAVE; type a character and read both states again.
- Expect: as in Notepad++'s checkDocState: with no modified document both items are disabled and running Save does not touch the file (same mtime); once the document is modified both are enabled.

### FILE-018: Saving into a folder without write permission fails with an alert
- Covers: IDM_FILE_SAVE
- Channel: modal, mcp, files
- Steps: Create `tmp/rodir` and chmod it 555; make a new tab with "text"; queue panel answer `tmp/rodir/x.txt` and alert answer 1; run IDM_FILE_SAVE; restore the mode.
- Expect: an alert saying there is no permission to save "x.txt" in the folder "rodir"; no file exists there; the tab is still untitled and modified.

### FILE-019: Saving a file opened through a symbolic link writes the target and keeps the link
- Covers: IDM_FILE_SAVE
- Channel: mcp, files
- Steps: Write `tmp/target.txt` = "t\n" and make `tmp/link.txt` a symlink to it; open `tmp/link.txt`; replace the text with "changed\n"; run IDM_FILE_SAVE.
- Expect: `tmp/link.txt` is still a symbolic link to target.txt; `tmp/target.txt` holds "changed\n" (Notepad++ writes through the link).

### FILE-020: Saving keeps the file's permissions
- Covers: IDM_FILE_SAVE
- Channel: mcp, files
- Steps: Write `tmp/run.sh` = "#!/bin/sh\necho hi\n" with mode 0755; open it, change "hi" to "bye", save.
- Expect: the file holds the new text and its mode is still 0755.

## Save As, Save a Copy As, Rename

### FILE-021: Save As writes a new file and the tab follows it
- Covers: IDM_FILE_SAVEAS
- Channel: mcp, modal, keys, files
- Steps: Open `tmp/orig.txt` = "x = 1\n"; type "y = 2\n" at the end; queue panel answer `tmp/copy.py`; press shift+cmd+s.
- Expect: a "save" panel was shown proposing "orig.txt"; `tmp/copy.py` holds "x = 1\ny = 2\n"; `tmp/orig.txt` still holds "x = 1\n"; the tab is "copy.py", path the new file, language "python", not modified; File > Open Recent does not list copy.py (it is open).

### FILE-022: Save As and Save a Copy As start in the document's folder
- Covers: IDM_FILE_SAVEAS, IDM_FILE_SAVECOPYAS
- Channel: modal, mcp
- Steps: Open `tmp/deep/dir/f.txt`; queue two panel answers None; run IDM_FILE_SAVEAS, then IDM_FILE_SAVECOPYAS.
- Expect: both logged "save" panels propose the name "f.txt" and their `directory` is `tmp/deep/dir`, as Notepad++'s file dialog starts in the file's folder.

### FILE-023: Save As onto a file open in another tab is refused
- Covers: IDM_FILE_SAVEAS
- Channel: modal, mcp, files
- Steps: Open `tmp/busy.txt` = "busy\n"; make a new tab with "other"; queue panel answer `tmp/busy.txt` and alert answer 1; run IDM_FILE_SAVEAS.
- Expect: an alert "That file is open in another tab." with informative "Close it first, or choose another name."; `tmp/busy.txt` still holds "busy\n"; the new tab is still untitled and modified.

### FILE-024: Save As over an existing file that is not open replaces its content
- Covers: IDM_FILE_SAVEAS
- Channel: modal, mcp, files
- Steps: Write `tmp/old.txt` = "old contents\n"; make a new tab with "new contents"; queue panel answer `tmp/old.txt`; run IDM_FILE_SAVEAS.
- Expect: `tmp/old.txt` holds exactly "new contents"; the tab is "old.txt" and not modified.

### FILE-025: A cancelled Save As changes nothing
- Covers: IDM_FILE_SAVEAS
- Channel: modal, mcp
- Steps: Open `tmp/keep.txt`, type "z"; queue panel answer None; run IDM_FILE_SAVEAS.
- Expect: the tab keeps its path and title, stays modified; the file on disk is unchanged; no other file was written.

### FILE-026: Save a Copy As writes a copy and leaves the tab on its own file
- Covers: IDM_FILE_SAVECOPYAS
- Channel: modal, mcp, files
- Steps: Write `tmp/src.txt` as UTF-16 LE with BOM "first\n"; open it; type "second\n" at the end; queue panel answer `tmp/dst.txt`; run IDM_FILE_SAVECOPYAS.
- Expect: `tmp/dst.txt` is FF FE + "first\nsecond\n" in UTF-16 LE; `tmp/src.txt` is unchanged; the tab is still "src.txt" with its old path and is still modified.

### FILE-027: Rename moves the file on disk and the tab follows
- Covers: IDM_FILE_RENAME
- Channel: modal, mcp, files
- Steps: Open `tmp/a.txt` = "var x = 1;\n"; type "// " at its start (unsaved); queue panel answer `tmp/b.js`; run IDM_FILE_RENAME.
- Expect: the panel was titled "Rename", proposed "a.txt" and started in `tmp`; `tmp/a.txt` no longer exists and `tmp/b.js` holds the saved text "var x = 1;\n"; the tab is "b.js", its language is JavaScript (the new extension decides), and the unsaved "// " edit is still there, still modified.

### FILE-028: Rename keeps a language the user chose
- Covers: IDM_FILE_RENAME
- Channel: modal, mcp
- Steps: Open `tmp/notes.txt`; run IDM_LANG_PYTHON; rename it to `tmp/notes.md` through a queued panel answer.
- Expect: the tab is "notes.md" and its language is still "python".

### FILE-029: Rename onto an existing file fails and touches neither file
- Covers: IDM_FILE_RENAME
- Channel: modal, mcp, files
- Steps: Write `tmp/r1.txt` = "one" and `tmp/r2.txt` = "two"; open r1.txt; queue panel answer `tmp/r2.txt` and alert answer 1; run IDM_FILE_RENAME.
- Expect: an error alert was shown; both files still exist with "one" and "two"; the tab is still "r1.txt".

### FILE-030: Rename of an untitled document renames only its tab
- Covers: IDM_FILE_RENAME
- Channel: modal, mcp, files
- Steps: Make a new tab with "draft"; queue panel answer `tmp/named.txt`; run IDM_FILE_RENAME; then cancel a second Rename (panel answer None).
- Expect: the tab is titled "named.txt", `path` is still null, the text is "draft", nothing was written to `tmp`; the cancelled Rename changes nothing.

## Save All

### FILE-031: Save All saves every modified document after confirmation
- Covers: IDM_FILE_SAVEALL
- Channel: modal, mcp, keys, files
- Steps: Open `tmp/p.txt` and `tmp/q.txt`, modify both; open `tmp/untouched.txt` (note its mtime); make a new tab and type "fresh"; queue alert answer "Yes" and panel answer `tmp/fresh.txt`; press alt+cmd+s.
- Expect: the log shows the "Save All Confirmation" alert (buttons Yes, No, Always Yes) then one "save" panel for the untitled tab; p.txt and q.txt hold their new texts; `tmp/fresh.txt` holds "fresh"; untouched.txt keeps its mtime; no document is modified; the tab that was current before is current again.

### FILE-032: Save All's confirmation: No saves nothing, Always Yes stops asking
- Covers: IDM_FILE_SAVEALL
- Channel: modal, mcp, prefs
- Steps: Modify an opened file; queue alert "No" and run IDM_FILE_SAVEALL; queue alert "Always Yes" and run it; modify again and run it with nothing queued; set confirmSaveAll back to true.
- Expect: after No the file is unchanged and the document still modified; after Always Yes the file is saved and the preference confirmSaveAll is false; the third Save All saves without any alert (the log has no entry).

## Close

### FILE-033: Close removes the tab in front and the neighbour takes its place
- Covers: IDM_FILE_CLOSE
- Channel: mcp, keys
- Steps: Open `tmp/c1.txt`, `tmp/c2.txt`, `tmp/c3.txt`; select c2.txt; run IDM_FILE_CLOSE; press cmd+w; run command id 41003 (the "(root)" ✕ entry); run IDM_FILE_CLOSE once more.
- Expect: c2.txt goes first and c3.txt becomes current; then c3.txt goes; then the next; closing the very last tab leaves exactly one fresh empty "new 1" (the application keeps running).

### FILE-034: Closing a modified document asks Save / Don't Save / Cancel
- Covers: IDM_FILE_CLOSE
- Channel: modal, mcp, files
- Steps: Open `tmp/ask.txt` = "v1"; change it to "v2"; queue alert 3 and close; queue alert 2 and close; reopen, change to "v3", queue alert 1 and close.
- Expect: each time an alert with message "Save" and informative 'Save file "ask.txt" ?' and buttons Yes, No, Cancel; Cancel keeps the tab, still modified; No closes it and the file still holds "v1"; Yes saves "v3" and closes the tab.

### FILE-035: Saving an untitled document while closing it can itself be cancelled
- Covers: IDM_FILE_CLOSE
- Channel: modal, mcp
- Steps: Make a new tab with "unsaved"; queue alert 1 (Yes) and panel answer None; run IDM_FILE_CLOSE.
- Expect: the Save alert then a "save" panel were shown; the tab is still open with its text, still modified.

### FILE-036: Close All closes everything and leaves one fresh tab
- Covers: IDM_FILE_CLOSEALL
- Channel: mcp, keys
- Steps: Open three files and make two new tabs without changes; press alt+cmd+w.
- Expect: no alert was shown; exactly one tab remains, an empty unmodified "new 1".

### FILE-037: Cancel during Close All keeps every tab
- Covers: IDM_FILE_CLOSEALL
- Channel: modal, mcp
- Steps: Open `tmp/d1.txt` and `tmp/d2.txt`, modify both; queue alerts 2 (No for d1) then 3 (Cancel for d2); run IDM_FILE_CLOSEALL; then queue 2, 2 and run it again.
- Expect: the first run asked twice and closed nothing (d1 and d2 still open and modified, the current tab as before); the second closed both without saving (files unchanged) and left one "new 1".

### FILE-038: Close All but Active Document keeps only the tab in front
- Covers: IDM_FILE_CLOSEALL_BUT_CURRENT
- Channel: mcp, modal
- Steps: Open five files; modify the first; select the third; queue alert 2; run IDM_FILE_CLOSEALL_BUT_CURRENT.
- Expect: one "Save" alert, for the first file; the only tab left is the third file, current, with its text.

### FILE-039: Close All to the Left and to the Right
- Covers: IDM_FILE_CLOSEALL_TOLEFT, IDM_FILE_CLOSEALL_TORIGHT
- Channel: mcp
- Steps: Close all, then open t0..t4 (tabs: new 1, t0, t1, t2, t3, t4); select t2; run IDM_FILE_CLOSEALL_TOLEFT; then IDM_FILE_CLOSEALL_TORIGHT.
- Expect: after "to the Left" the tabs are t2, t3, t4 with t2 current; after "to the Right" only t2 remains, current; with t2 first and alone both commands change nothing.

### FILE-040: Close All Unchanged keeps the modified documents only
- Covers: IDM_FILE_CLOSEALL_UNCHANGED
- Channel: mcp, modal
- Steps: Open u1, u2, u3; modify u2; make a new tab and type "x"; run IDM_FILE_CLOSEALL_UNCHANGED.
- Expect: no alert; the remaining tabs are u2 and the modified untitled tab, both still modified; nothing was saved.

### FILE-041: Close All but Pinned Documents keeps the pinned tabs
- Covers: IDM_FILE_CLOSEALL_BUT_PINNED
- Channel: mcp, modal
- Steps: Open p1, p2, loose1, loose2; select p2 and run "File|Pin Tab", then p1 and pin it; modify loose2; queue alert 2; run IDM_FILE_CLOSEALL_BUT_PINNED.
- Expect: pinning moves each pinned tab to the end of the pinned run at the left (order p2, p1, …); one Save alert for loose2; the tabs left are exactly p2 and p1, both `pinned`.

### FILE-042: The tab context menu's close commands act like the File menu's
- Covers: IDM_FILE_CLOSE, IDM_FILE_CLOSEALL_TORIGHT
- Channel: menu, mcp
- Steps: Open t0..t3; select t1; read `e2e_menu(context="tab")`; invoke "Close Multiple Tabs|Close All to the Right" from the tab context menu; then invoke "Close".
- Expect: the tab menu starts with Close, Close Multiple Tabs (Close All BUT This, Close All BUT Pinned, Close All to the Left, Close All to the Right, Close All Unchanged), Pin Tab, Save, Save As..., Open into (Open Containing Folder in Finder, … in Terminal, … as Workspace, Open in Default Viewer), Rename, Move to Trash, Reload, Print; after the first invocation t2 and t3 are gone and t1 is current; after "Close" t1 is gone.

## Recent files

### FILE-043: A closed file goes to the top of Open Recent at once
- Covers: IDM_FILE_CLOSE
- Channel: menu, mcp
- Steps: Clear the recent list ("File|Open Recent|Clear Menu"); open `tmp/r1.txt` and `tmp/r2.txt`; read the File > Open Recent tree; close r1.txt, then r2.txt, reading the tree after each close.
- Expect: while a file is open it is not listed; right after each close the submenu lists it first (r2.txt above r1.txt after both), each entry's tooltip being the full path, followed by a separator, "Open All Recent Files" and "Clear Menu"; the preference recentFiles holds the same paths in the same order.

### FILE-044: Choosing a recent entry reopens the file and takes it off the list
- Covers: IDM_FILE_OPEN
- Channel: menu, mcp
- Steps: Open and close `tmp/back.txt`; invoke "File|Open Recent|back.txt" (e2e_menu_invoke).
- Expect: back.txt is open and current with its text; it is no longer in recentFiles nor in the submenu.

### FILE-045: Restore Last Closed File reopens the file closed last
- Covers: IDM_FILE_CLOSE
- Channel: keys, mcp
- Steps: Open and close `tmp/x1.txt` then `tmp/x2.txt`; press shift+cmd+t; press it again; with the recent list cleared press it a third time.
- Expect: the first press reopens x2.txt, the second x1.txt, each current; the third changes nothing (no tab, no alert).

### FILE-046: Open All Recent Files and Clear Menu
- Covers: -
- Channel: menu, mcp
- Steps: Open and close `tmp/o1.txt`, `tmp/o2.txt`, `tmp/o3.txt`; delete o2.txt from disk; run "File|Open Recent|Open All Recent Files"; close all again; run "File|Open Recent|Clear Menu".
- Expect: o1.txt and o3.txt are open, o2.txt is not and no tab or crash results from it; after Clear Menu recentFiles is [] and the submenu holds only "Open All Recent Files" and "Clear Menu".

### FILE-047: A recent entry whose file was deleted gives an error, not a tab
- Covers: -
- Channel: menu, modal, mcp
- Steps: Open and close `tmp/gone.txt`; delete the file; queue alert answer 1; invoke "File|Open Recent|gone.txt".
- Expect: an alert saying the file couldn't be opened because there is no such file; no tab was added.

## Reload from Disk

### FILE-048: Reload from Disk takes the file as it now is
- Covers: IDM_FILE_RELOAD
- Channel: mcp, keys, files
- Steps: Open `tmp/rl.txt` = "line1\nline2\nline3\n"; put the caret on line 2 column 3; rewrite the file externally as "LINE1\nLINE2\nLINE3\nLINE4\n"; press cmd+r.
- Expect: the text is the new file content; not modified; the caret is still at line 2 column 3; SCI_CANUNDO is 0 (undo history emptied); no alert was shown (the document had no edits).

### FILE-049: Reloading a document with edits asks first
- Covers: IDM_FILE_RELOAD
- Channel: modal, mcp
- Steps: Open `tmp/rl2.txt` = "disk\n"; replace the text with "mine\n"; queue alert 2 and run IDM_FILE_RELOAD; queue alert 1 and run it again.
- Expect: an alert titled "Reload" with "Are you sure you want to reload the current file and lose the changes made in Notepad++?" and buttons Yes, No; after No the text is "mine\n" and modified; after Yes it is "disk\n" and not modified.

### FILE-050: File commands that need a file are unavailable for an untitled document
- Covers: IDM_FILE_RELOAD, IDM_FILE_DELETE, IDM_FILE_OPEN_FOLDER, IDM_FILE_OPEN_CMD, IDM_FILE_CONTAININGFOLDERASWORKSPACE, IDM_FILE_OPEN_DEFAULT_VIEWER
- Channel: menu, modal, mcp
- Steps: With an untitled document in front read the enabled state of the six items; run IDM_FILE_RELOAD and IDM_FILE_CONTAININGFOLDERASWORKSPACE anyway.
- Expect: as in Notepad++'s checkDocState the items are disabled while the document has no file on disk (they are enabled again once a saved file is in front); running them shows no alert (no "This document has never been saved." error) and changes nothing: the text, the tabs and the workspace roots are as before.

## Files changed by other programs

### FILE-051: A file changed on disk is offered for reload when the application comes back to the front
- Covers: IDM_FILE_RELOAD
- Channel: modal, mcp, files
- Steps: Open `tmp/ext.txt` = "v1\n" (no edits); wait past one second and write "v2\n" to it; queue alert 2; deactivate and reactivate the application (`invoke nsapp hide:` then `activateIgnoringOtherApps:` YES) and poll the modal log; then write "v3\n", queue alert 1 and reactivate again.
- Expect: an alert titled "Reload" whose text holds the file's path and "This file has been modified by another program.\nDo you want to reload it?" (buttons Yes, No); after No the text is still "v1\n" and reactivating again without a new change asks nothing; after the "v3" change and Yes the text is "v3\n" and not modified.

### FILE-052: A change on disk to a document with edits warns that the edits will be lost
- Covers: -
- Channel: modal, mcp, files
- Steps: Open `tmp/both.txt` = "disk1\n"; replace the text with "mine\n"; write "disk2\n" to the file; queue alert 2; reactivate the application.
- Expect: the "Reload" alert's text says "Do you want to reload it and lose the changes made in Notepad++?"; after No the text is "mine\n", still modified.

### FILE-053: A change on disk to a tab that is not in front is found too and the front tab stays
- Covers: -
- Channel: modal, mcp, files
- Steps: Open `tmp/bg.txt` = "old\n" then `tmp/fg.txt`; write "new\n" to bg.txt; queue alert 1; reactivate the application.
- Expect: one "Reload" alert naming bg.txt; afterwards bg.txt's text is "new\n"; fg.txt is still the current tab; Window > Recent Window still leads back to bg.txt (the check did not disturb the tab history).

### FILE-054: A file deleted from disk can be kept or closed
- Covers: -
- Channel: modal, mcp, files
- Steps: Open `tmp/del1.txt` and `tmp/del2.txt`; delete both files; queue alerts 1 then 2; reactivate the application.
- Expect: two alerts titled "Keep non existing file" with 'The file "…" doesn't exist anymore.\nKeep this file in editor?'; del1.txt (Yes) stays open, marked modified, with its text; del2.txt (No) is closed and is not in recentFiles; reactivating again asks nothing more.

## Monitoring (tail -f)

### FILE-055: Monitoring follows a growing file to its end and keeps it read-only
- Covers: IDM_VIEW_MONITORING
- Channel: mcp, keys, files
- Steps: Open `tmp/app.log` = "one\n"; run IDM_VIEW_MONITORING; type "x"; append "two\n" to the file from Python and poll the text; run IDM_VIEW_MONITORING again and type "y".
- Expect: while monitoring the menu item is checked, SCI_GETREADONLY is 1, `doc()["read_only"]` is true and typing changes nothing; within a few seconds the text becomes "one\ntwo\n" with the caret at the end; after turning it off the item is unchecked, the document is editable and "y" is typed in.

### FILE-056: Monitoring refuses a modified or untitled document, waits in the background, survives rotation
- Covers: IDM_VIEW_MONITORING
- Channel: mcp, files
- Steps: (a) modify an opened file and run IDM_VIEW_MONITORING; (b) in an untitled tab run it; (c) monitor `tmp/a.log`, switch to another tab, append "late\n", wait a second, switch back; (d) move `tmp/a.log` to `tmp/a.log.1`, create a new `tmp/a.log` = "fresh\n", then append "more\n".
- Expect: (a) and (b) leave the item unchecked and the document editable; (c) the text of a.log does not change while it is behind, and holds "late" once it is in front again; (d) the tab follows the name: its text becomes "fresh\n" then "fresh\nmore\n" and monitoring stays on.

## Big files

### FILE-057: Files above the streaming threshold are read byte-exact
- Covers: IDM_FILE_OPEN, IDM_FILE_SAVE
- Channel: mcp, files
- Steps: Lower the streaming threshold for the test (`invoke class:EditorController setStreamingThreshold: [1024]`, put back with [0] afterwards); for each of: 400 lines "line N café\r\n" in UTF-8, the same in Latin-1, the same in UTF-8 with BOM: open the file, check, save it unchanged after typing and deleting one character, compare bytes.
- Expect: the text equals the original; encodings "UTF-8", "ISO-8859-1", "UTF-8-BOM" respectively; eol "CRLF"; the saved file is byte-identical to the original.

### FILE-058: A large file opens without styling
- Covers: IDM_FILE_OPEN
- Channel: mcp, prefs
- Steps: Set largeFileThresholdMB to 1; write a 2.5 MB `tmp/big.cpp` of "int x; // comment\n" lines; open it; put the preference back to 200.
- Expect: the document is open with the whole text (`lines` equals the number written); SCI_GETDOCUMENTOPTIONS has SC_DOCUMENTOPTION_STYLES_NONE and SC_DOCUMENTOPTION_TEXT_LARGE (257); a small .cpp opened next has neither.

### FILE-059: A huge file is only opened after a warning
- Covers: IDM_FILE_OPEN
- Channel: modal, mcp, files
- Steps: Create a sparse 2 GiB `tmp/huge.bin` (truncate); queue panel answer that path and alert "No"; run IDM_FILE_OPEN; delete the file.
- Expect: an alert "Opening huge file warning" with "Opening a huge file of 2GB+ could take several minutes.\nDo you want to open it?" and buttons Yes, No; after No no tab was added and no further alert was shown (no "The operation was cancelled." error).

## Containing folder, default viewer, Folder as Workspace

### FILE-060: Open Containing Folder in Finder selects the file
- Covers: IDM_FILE_OPEN_FOLDER
- Channel: menu, mcp
- Steps: With the workspace hook recording instead of performing, open `tmp/sub/f.txt` and run IDM_FILE_OPEN_FOLDER.
- Expect: exactly one recorded request: reveal (activateFileViewerSelectingURLs) of `tmp/sub/f.txt`; nothing else was opened.

### FILE-061: Open Containing Folder in Terminal (cmd and PowerShell)
- Covers: IDM_FILE_OPEN_CMD, IDM_FILE_OPEN_POWERSHELL
- Channel: menu, mcp
- Steps: With the workspace hook recording, open `tmp/sub/f.txt`; run IDM_FILE_OPEN_CMD; then run IDM_FILE_OPEN_POWERSHELL.
- Expect: IDM_FILE_OPEN_CMD records one request to open the folder `tmp/sub` with the application com.apple.Terminal; IDM_FILE_OPEN_POWERSHELL does the same (on macOS both of Notepad++'s shells are Terminal) — it must not answer "not in this build's menus".

### FILE-062: Open in Default Viewer hands the file to its application
- Covers: IDM_FILE_OPEN_DEFAULT_VIEWER
- Channel: menu, mcp
- Steps: With the workspace hook recording, open `tmp/page.html` and run IDM_FILE_OPEN_DEFAULT_VIEWER.
- Expect: one recorded openURL of the file URL of `tmp/page.html`; the document stays open and unchanged.

### FILE-063: Open Containing Folder as Workspace roots the panel at the file's folder
- Covers: IDM_FILE_CONTAININGFOLDERASWORKSPACE
- Channel: mcp, ui
- Steps: Write `tmp/ws/a.txt` and `tmp/ws/b.py`; open a.txt; run IDM_FILE_CONTAININGFOLDERASWORKSPACE; run it again.
- Expect: `list_documents()["workspace_roots"]` is [`tmp/ws`] (not twice after the second run); the Folder as Workspace panel is visible and lists a.txt and b.py.

### FILE-064: Open Folder as Workspace adds the chosen folders as roots
- Covers: IDM_FILE_OPENFOLDERASWORKSPACE
- Channel: modal, mcp, ui
- Steps: Create `tmp/r1` and `tmp/r2` with one file each; queue panel answer `tmp/r1` and run IDM_FILE_OPENFOLDERASWORKSPACE; the same with `tmp/r2`; then with None.
- Expect: each logged panel is an "open" panel; after the first run the roots are [r1], after the second [r1, r2]; the cancelled run changes nothing; the panel shows both roots.

## Move to Trash

### FILE-065: Move to Trash asks, then trashes the file and closes its tab
- Covers: IDM_FILE_DELETE
- Channel: modal, menu, mcp, files
- Steps: Open `tmp/trash_me.txt` and `tmp/stay.txt`, select trash_me.txt; run_command IDM_FILE_DELETE; queue alert "No" and invoke "File|Move to Trash"; queue alert "Yes" and invoke it again.
- Expect: run_command answers an error that the command is left to the user and nothing happens; the alert is titled "Delete file" with 'The file "<full path>"\nwill be moved to your Trash and this document will be closed.\nContinue?' (Yes, No); after No the file and tab remain; after Yes the file is no longer in `tmp`, its tab is closed, stay.txt is current, and the path is not in recentFiles.

## Print

### FILE-066: Print shows the print panel and Cancel prints nothing
- Covers: IDM_FILE_PRINT
- Channel: modal, keys, mcp
- Steps: With the print hook answering the print panel (queued "cancel"), open `tmp/print.txt` = "alpha\nbeta\n" and press cmd+p.
- Expect: the log records one print panel for a job titled "print.txt"; nothing was printed or written; the application keeps answering and the document is unchanged.

### FILE-067: Print Now prints the document with the print settings and no panel
- Covers: IDM_FILE_PRINTNOW
- Channel: keys, mcp, prefs, files
- Steps: With the print hook sending jobs to a PDF file, set printLineNumbers true and printHeaderLeft "$(FILE_NAME)"; open `tmp/pn.txt` = "alpha\nbeta\ngamma\n"; press shift+cmd+p; read the PDF's text; put the preferences back.
- Expect: no panel was shown; one job titled "pn.txt"; the PDF's text holds "1  alpha" and "3  gamma" and the header "pn.txt" (the print preferences reach the job, as SETTINGS-058 sets them).

## Exit

### FILE-068: Exit with unsaved changes asks, and Cancel keeps the application running
- Covers: IDM_FILE_EXIT
- Channel: modal, keys, mcp
- Steps: run_command IDM_FILE_EXIT; make a new tab with "dirty"; queue alert 3 and press cmd+q; queue alert 3 and invoke "NotepadMac|Quit NotepadMac".
- Expect: run_command answers that the command is left to the user; each quit attempt shows the "Save" alert for the untitled tab (Yes, No, Cancel); after Cancel the application still answers, the tab and its text are there.

### FILE-069: Exit quits, saving only what the user says
- Covers: IDM_FILE_EXIT
- Channel: modal, keys, files
- Steps: Open `tmp/exit.txt` = "v1", change it to "v2"; queue alert 2 (No); press cmd+q; wait for the process to end; then start again, open nothing, press cmd+q.
- Expect: the process exits with status 0; `tmp/exit.txt` still holds "v1"; the second quit, with nothing modified, asks nothing and exits with status 0.
