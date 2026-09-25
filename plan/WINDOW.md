# WINDOW — Window menu, the "▼" and "(root)" entries, and the Help ("?") menu

The Window menu (Sort By with its ten orders, Windows…, Recent Window, and the port's Next Tab / Previous Tab), the "▼" droplist entry (IDM_DROPLIST_LIST, the list of open documents), the "(root)" ＋ / ✕ entries (IDM_FILE_NEW / IDM_FILE_CLOSE, planned in FILE-001 and FILE-033), and the Help menu: the four links (which lead to this port's repository and to upstream's manual, never to Notepad++'s site or forum), Command Line Arguments, Debug Info, Check for Updates and its schedule, Set Updater Proxy, and About (also in the application menu). The Settings menu is entirely SETTINGS'. Sort orders follow Notepad++'s WindowsDlg (BufferEquivalent::compare): the name numerically and without case (numstrcmp), the full path, the language name for "Type", the document's length in memory for "Content Length", the file's time for "Modified Time", ties broken by the full path. Conventions: the tab order is the order of `app.docs()`; Windows…, Command Line Arguments and Set Updater Proxy end in NSAlerts read from `app.modal_log()` (informative text holds the content) and answered with `app.answers(alerts=[...])`; About and Debug Info are panels read with `app.ui(window)`; the Help links, About's link buttons and the update check's "open the page" answers go to NSWorkspace and need the workspace hook (recording instead of opening a browser, see report); the update check never reaches the network: a proxy pointing at a closed local port (`defaults write <bundle id> NppMacUpdaterProxy 127.0.0.1:1`, the key has no NppMac. prefix) makes it fail at once, and a local release file needs the release-URL hook.

## Sort By

### WINDOW-001: Sort by name, A to Z and Z to A, numbers as numbers and without case
- Covers: IDM_WINDOW_SORT_FN_ASC, IDM_WINDOW_SORT_FN_DSC
- Channel: mcp, menu
- Steps: Open `tmp/file10.txt`, `tmp/File2.txt`, `tmp/beta.md`, `tmp/alpha.py`; select File2.txt; run IDM_WINDOW_SORT_FN_ASC; read the tab order; run IDM_WINDOW_SORT_FN_DSC.
- Expect: A to Z gives alpha.py, beta.md, File2.txt, file10.txt, new 1 (2 before 10, case ignored); Z to A gives exactly the reverse; File2.txt stays the current tab after each sort; no tab was added or lost.

### WINDOW-002: Sort by path, A to Z and Z to A
- Covers: IDM_WINDOW_SORT_FP_ASC, IDM_WINDOW_SORT_FP_DSC
- Channel: mcp, menu
- Steps: Open `tmp/b/x.txt`, `tmp/a/z.txt`, `tmp/a/y.txt` (the clean slate's "new 1" is kept); run IDM_WINDOW_SORT_FP_ASC, then IDM_WINDOW_SORT_FP_DSC.
- Expect: ascending: a/y.txt, a/z.txt, b/x.txt, then "new 1" (an untitled document's full name "new 1" sorts after the "/…" paths, as upstream compares full path names); descending is the reverse.

### WINDOW-003: Sort by type orders by language
- Covers: IDM_WINDOW_SORT_FT_ASC, IDM_WINDOW_SORT_FT_DSC
- Channel: mcp, menu
- Steps: Close all; open `tmp/a.py`, `tmp/c.txt`, `tmp/b.cxx`, `tmp/d.cpp`; run IDM_WINDOW_SORT_FT_ASC, then IDM_WINDOW_SORT_FT_DSC.
- Expect: ascending groups by language name — b.cxx and d.cpp (cpp, tie broken by path: b before d), then c.txt and "new 1" (normal, by path), then a.py (python) — not by extension; descending is the reverse.

### WINDOW-004: Sort by content length uses the text as it is now
- Covers: IDM_WINDOW_SORT_FS_ASC, IDM_WINDOW_SORT_FS_DSC
- Channel: mcp, menu
- Steps: Close all; open `tmp/s3.txt` (3 bytes) and `tmp/s10.txt` (10 bytes); replace s3.txt's text with 20 characters without saving; make an untitled tab with 5 characters; run IDM_WINDOW_SORT_FS_ASC, then IDM_WINDOW_SORT_FS_DSC.
- Expect: ascending by the documents' current lengths: the empty "new 1" (0), the 5-character untitled tab, s10.txt (10), s3.txt (20); descending the reverse.

### WINDOW-005: Sort by modified time
- Covers: IDM_WINDOW_SORT_FD_ASC, IDM_WINDOW_SORT_FD_DSC
- Channel: mcp, menu, files
- Steps: Close all; write `tmp/t1.txt`, `tmp/t2.txt`, `tmp/t3.txt` and set their mtimes (os.utime) to 2020, 2022 and 2024; open them in the order t2, t3, t1; run IDM_WINDOW_SORT_FD_ASC, then IDM_WINDOW_SORT_FD_DSC.
- Expect: ascending: "new 1" (no file time), t1, t2, t3; descending: t3, t2, t1, "new 1".

## Windows list, droplist, tab switching

### WINDOW-006: Windows… lists every open document in tab order
- Covers: IDM_WINDOW_WINDOWS, IDM_DROPLIST_LIST
- Channel: modal, mcp, clipboard
- Steps: Open `tmp/w1.txt` and `tmp/sub/w2.md` and make an untitled tab; queue alert "Copy" and run IDM_WINDOW_WINDOWS; queue alert "OK" and run it again; run command id 14001 (the "▼" droplist) with alert "OK" queued.
- Expect: an alert titled "Windows" with buttons OK and Copy whose informative text is one line per tab in tab order: the full path of w1.txt (it took the lone clean "new 1"'s place), the full path of w2.md, "new 1"; after Copy the clipboard holds exactly that text; OK changes nothing (current tab, tabs); the droplist command offers the same list (it must not answer that the command is not in the menus).

### WINDOW-007: Recent Window steps back to the previously active tab
- Covers: IDM_WINDOW_MRU_FIRST
- Channel: mcp, menu
- Steps: Open `tmp/r1.txt`, `tmp/r2.txt`, `tmp/r3.txt`; select r1.txt, then r3.txt; run IDM_WINDOW_MRU_FIRST twice; select r2.txt then r3.txt, close r1.txt (not in front), run it again; close r2.txt and run it once more; with a single tab run it.
- Expect: the first run makes r1.txt current, the second r3.txt again; after closing r1.txt it goes to r2.txt (the previous tab, not whatever now sits at its old index); after r2.txt is gone it changes nothing; with one tab nothing changes and no alert is shown.

### WINDOW-008: Next Tab and Previous Tab cycle through the tabs
- Covers: -
- Channel: keys, mcp
- Steps: Open n1, n2, n3 (tabs: new 1, n1, n2, n3); select n2; press shift+cmd+] three times, reading the current tab after each; press shift+cmd+[ twice.
- Expect: n3, new 1 (wraps to the first), n1; then new 1, n3 (wraps to the last); with a single tab both keys change nothing.

### WINDOW-009: The Window menu has Notepad++'s items in order
- Covers: -
- Channel: menu
- Steps: Read `app.menu_tree("Window", 2)`.
- Expect: Next Tab (shift+cmd+]), Previous Tab (shift+cmd+[), a separator, Sort By with the ten orders in Notepad++'s order (Name A to Z, Name Z to A, Path A to Z, Path Z to A, Type A to Z, Type Z to A, Content Length Ascending, Content Length Descending, Modified Time Ascending, Modified Time Descending), Windows…, Recent Window; every item is enabled.

## Help: About and Debug Info

### WINDOW-010: About shows the version, the build, the licence and this port's links
- Covers: IDM_ABOUT
- Channel: menu, ui, mcp
- Steps: Run IDM_ABOUT; read the panel's controls; click "OK"; invoke "NotepadMac|About NotepadMac" from the application menu and close it again.
- Expect: a panel titled "About Notepad++" with the line "Notepad++ v<upstream version>   (ARM 64-bit)" (or "64-bit" on Intel), "macOS port <version> (build <n>)", "Build time: …", the GPL text starting "This program is free software", and two link buttons whose ids are https://github.com/<updateRepository> and …/issues; no control mentions notepad-plus-plus.org; OK closes the panel; the application-menu item opens the same panel.

### WINDOW-011: About's link buttons open the port's pages
- Covers: IDM_ABOUT
- Channel: ui, mcp
- Steps: With the workspace hook recording, open About and click the repository button, then the issues button.
- Expect: two recorded openURL requests, exactly the buttons' addresses (https://github.com/<updateRepository> and its /issues); no browser was started.

### WINDOW-012: Debug Info lists upstream's fields as they are now
- Covers: IDM_DEBUGINFO
- Channel: menu, ui, clipboard, prefs
- Steps: Set autosaveEnabled true; run IDM_DEBUGINFO; read the text view; click "Copy debug info to clipboard"; click "OK"; set autosaveEnabled back.
- Expect: a panel "Debug Info" whose text holds, in this order, "Notepad++ v", "macOS port: ", "Build time: ", "Built with: Clang ", "Scintilla/Lexilla included: 5.", "Path: <the copy's executable>", "Command Line: " (containing "-nosession"), "Admin mode: OFF", "Local Conf mode: OFF", "Cloud Config: OFF", "Auto-updater: disabled (GitHub Releases of <updateRepository>)", "Periodic Backup: ON", "Multi-instance Mode: monoInst", "File Status Auto-Detection: cdEnabledNew", "Dark Mode: ", "Display Info:", "OS Name: macOS", "OS Version: ", "Current ANSI codepage: ", "Plugins: none"; the clipboard then equals the text exactly; OK closes the panel.

### WINDOW-013: Command Line Arguments documents every switch the application reads
- Covers: IDM_CMDLINEARGUMENTS
- Channel: modal, clipboard
- Steps: Queue alert "Copy"; run IDM_CMDLINEARGUMENTS.
- Expect: an alert titled "Command Line Arguments" (OK, Copy) whose text names each switch parseCommandLine takes: -n -c -p -l -udl= -ro -fullReadOnly -nosession -openSession -r -openFoldersAsWorkspace -monitor -alwaysOnTop -notabbar -titleAdd= -settingsDir= -qt= -qf= -notepadStyleCmdline -z -quickPrint -export=functionList -x -y, and the ignored -multiInst -noPlugin -systemtray -loadingTime -pluginMessage=; the clipboard holds the same text.

## Help: links and updates

### WINDOW-014: The Help links lead to this port's pages and upstream's manual
- Covers: IDM_HOMESWEETHOME, IDM_PROJECTPAGE, IDM_ONLINEDOCUMENT, IDM_FORUM
- Channel: menu, mcp
- Steps: With the workspace hook recording, run IDM_HOMESWEETHOME, IDM_PROJECTPAGE, IDM_ONLINEDOCUMENT and IDM_FORUM; read the Help menu tree.
- Expect: four recorded openURL requests, in order: https://github.com/<updateRepository>#readme, https://github.com/<updateRepository>, https://npp-user-manual.org/, https://github.com/<updateRepository>/discussions — all https, none on notepad-plus-plus.org or github.com/notepad-plus-plus; the Help menu reads Notepad++ Home, Notepad++ Project Page, Notepad++ Online User Manual, Notepad++ Community (Forum), a separator, Command Line Arguments…, Debug Info…, Check for Updates, Set Updater Proxy…, About NotepadMac.

### WINDOW-015: Set Updater Proxy asks for host:port and remembers it
- Covers: IDM_CONFUPDATERPROXY
- Channel: modal, prefs
- Steps: Queue {"button": 1, "field": "proxy.example:8080"} and run IDM_CONFUPDATERPROXY; run it again with alert 2 (Cancel) after filling "other:1"; run it once more with {"button": 1, "field": ""}; read the key NppMacUpdaterProxy with `defaults read` after each.
- Expect: the alert's message is "Updater proxy (host:port)" with OK and Cancel and one text field, prefilled with the stored value (empty the first time, "proxy.example:8080" the second); after OK the key is "proxy.example:8080"; Cancel leaves it; OK with an empty field stores "".

### WINDOW-016: Check for Updates reports a failure without the network
- Covers: IDM_UPDATE_NPP
- Channel: modal, mcp
- Steps: Set NppMacUpdaterProxy to "127.0.0.1:1"; with the workspace hook recording, queue alert "Open the Releases Page" and run IDM_UPDATE_NPP; poll the modal log (up to 25 s); then queue "OK" and run it again.
- Expect: an alert "Notepad++ update" whose informative text holds an error description and "https://api.github.com/repos/<updateRepository>/releases/latest", with buttons OK and "Open the Releases Page"; that button records an openURL of https://github.com/<updateRepository>/releases; OK records nothing; the application keeps answering while the check runs.

### WINDOW-017: Check for Updates offers a newer release and says when there is none
- Covers: IDM_UPDATE_NPP
- Channel: modal, mcp, files
- Steps: With the release-URL hook pointing at `tmp/latest.json` = {"tag_name": "v99.0.0", "name": "NotepadMac 99", "html_url": "https://github.com/o/r/releases/tag/v99.0.0"} and the workspace hook recording, queue "Yes" and run IDM_UPDATE_NPP; then rewrite the file with the current version's tag, queue "OK" and run it again.
- Expect: first an alert "Notepad++ update" saying "An update package is available, do you want to download it?" with "NotepadMac 99 (you have v<current>)", buttons Yes and No, and Yes records an openURL of the html_url; the second time an alert "No update is available." naming the current version and the latest release, with only OK, and nothing is opened.

### WINDOW-018: The automatic update check follows its schedule quietly
- Covers: IDM_UPDATE_NPP
- Channel: launch, prefs, modal
- Steps: Reset the preferences, write autoUpdateMode 1, nextUpdateDate "20200101", updateIntervalDays 15 and NppMacUpdaterProxy "127.0.0.1:1"; start with `reset=False`; wait until nextUpdateDate changes (up to 30 s); read the modal log. Then restart with nextUpdateDate 30 days ahead, wait 6 s; then with autoUpdateMode 0 and a past date, wait 6 s.
- Expect: with mode 1 and a past date, nextUpdateDate becomes today + 15 days (yyyyMMdd) and no alert is shown for the failed check; with a future date it is unchanged; with mode 0 it is unchanged.

### WINDOW-019: The update check on exit moves the schedule and opens nothing
- Covers: IDM_UPDATE_NPP
- Channel: launch, prefs
- Steps: Write autoUpdateMode 2, nextUpdateDate "20200101" and the closed-port proxy; start with `reset=False`; wait 5 s and check nextUpdateDate is still "20200101"; quit gracefully; read the domain with `defaults read`.
- Expect: nothing is checked at launch in mode 2; the process exits within 10 s with status 0 (the exit check gives up on the failed request); NppMac.nextUpdateDate is then today + updateIntervalDays (yyyyMMdd).
