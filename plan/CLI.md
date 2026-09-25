# CLI — The nppmac tool and the application's command-line switches

Two ways in from the command line. `nppmac` (the copy's `app.cli`, `Contents/Helpers/nppmac`) opens files, a file at a line (`+N`), folders (as workspace roots) and standard input (`-`) in the running application over a distributed notification named after the copy's bundle id, creates a file that does not exist, and bridges MCP over stdio (`nppmac mcp`). The application itself reads Notepad++'s switches (`parseCommandLine` / `applyCommandLine` in AppDelegate.mm, after upstream's winmain.cpp and its "Command Line Arguments" help): -n -c -p -l -udl= -ro -fullReadOnly -nosession -openSession -r -openFoldersAsWorkspace -monitor -alwaysOnTop -notabbar -titleAdd= -settingsDir= -qt= -qf= -notepadStyleCmdline -z -x -y -export=functionList -quickPrint, and accepts -multiInst -noPlugin -systemtray -loadingTime -pluginMessage= without effect. Out of scope: the MCP tools themselves (AGENT), Help > Command Line Arguments (WINDOW), multi-instance mode (it would start a second, unisolated copy). Conventions: switches are given with `app.start(args=[...])` (the harness adds `-NppMac.agentServer YES` and, without `session=True`, `-nosession`); the launch keeps opening files after the agent socket answers, so every launch case first polls (`app.wait`) until the expected tab count or window title is there. `nppmac` is run with `subprocess.run([app.cli, ...], cwd=..., input=..., timeout=30)` only while the test app is running — with no app running it would launch the copy without the harness's isolation, so that path is not tested. "Files" are written into `tmp`.

## nppmac

### CLI-001: nppmac opens a file in the running application
- Covers: -
- Channel: cli, mcp
- Steps: Write `tmp/cli.txt` = "one\ntwo\n"; run `nppmac <tmp/cli.txt>`; poll the documents.
- Expect: nppmac exits with status 0 and prints nothing; within 10 s cli.txt is open and current with its text in the test application (not in any other NotepadMac); no alert was shown.

### CLI-002: nppmac +N opens the file that follows at line N
- Covers: -
- Channel: cli, mcp
- Steps: Write `tmp/lines.txt` with 100 numbered lines and `tmp/other.txt`; run `nppmac +42 <lines.txt> <other.txt>`; then run `nppmac +7 <lines.txt>` again.
- Expect: lines.txt's caret is at line 42 column 1 and line 42 is within the visible lines (SCI_GETFIRSTVISIBLELINE .. + SCI_LINESONSCREEN); other.txt, which followed without +N, opens with its caret at line 1 and is current; the second call brings lines.txt forward (no second tab) with the caret on line 7.

### CLI-003: nppmac opens several files and a folder as a workspace root
- Covers: -
- Channel: cli, mcp, ui
- Steps: Create `tmp/proj` holding `x.py`, and `tmp/f1.txt`, `tmp/f2.txt`; run `nppmac <f1.txt> <tmp/proj> <f2.txt>`.
- Expect: f1.txt and f2.txt are open, f2.txt current; `list_documents()["workspace_roots"]` contains `tmp/proj` and the Folder as Workspace panel is visible; x.py was not opened as a tab.

### CLI-004: nppmac resolves relative paths against its working directory
- Covers: -
- Channel: cli, mcp
- Steps: Create `tmp/sub/rel.txt`; run `nppmac sub/rel.txt ../<tmp name>/sub/./rel.txt` with `cwd=tmp`.
- Expect: exactly one tab for rel.txt whose `path` is the absolute, standardized `tmp/sub/rel.txt`.

### CLI-005: nppmac creates a file that does not exist
- Covers: -
- Channel: cli, mcp, files
- Steps: Run `nppmac <tmp/brand_new.md>`; make `tmp/locked` mode 555 and run `nppmac <tmp/locked/x.txt>`; restore the mode.
- Expect: `tmp/brand_new.md` exists with 0 bytes and is open, empty, not modified, language markdown; for the locked folder nppmac writes "nppmac: cannot create <path>" to stderr, still exits 0, and no tab is added.

### CLI-006: nppmac - reads standard input into a document
- Covers: -
- Channel: cli, mcp
- Steps: Run `nppmac -` with input "piped ☃ text\nline 2\n" (UTF-8).
- Expect: a new current tab holds exactly "piped ☃ text\nline 2\n", encoding UTF-8; its title is "nppmac-stdin-<pid>.txt" and its path is in the temporary folder; nppmac exited 0.

### CLI-007: nppmac -h prints its usage and opens nothing
- Covers: -
- Channel: cli, mcp
- Steps: Note the documents; run `nppmac -h` and `nppmac --help`.
- Expect: both exit 0 and write to stderr a usage starting "usage: nppmac [+N] [file|folder ...] [-]" that mentions "+N", "-" and "mcp"; the documents are unchanged.

### CLI-008: nppmac mcp bridges an agent to the running application
- Covers: -
- Channel: cli, mcp
- Steps: Run `nppmac mcp` with `NPPMAC_AGENT_SOCKET` set to the app's socket; write "initialize", "notifications/initialized", "tools/list" and "tools/call list_documents" as JSON-RPC lines; read the answers; close stdin.
- Expect: the initialize answer has serverInfo.name "NotepadMac" and a protocolVersion; tools/list includes open_document, get_document, edit_document, run_command and the other product tools; list_documents answers the same documents as the harness sees; after stdin closes the bridge exits with status 0 and the application keeps running.

## Files on the application's command line

### CLI-009: Files given at launch open in the given order, the last in front
- Covers: -
- Channel: launch, mcp
- Steps: Start with args [`tmp/a.txt`, `tmp/b c.txt`, `tmp/z.md`].
- Expect: after the launch settles the tabs after "new 1" are a.txt, "b c.txt", z.md in that order (a name with a space is one file), z.md is current, each with its text.

### CLI-010: A relative file argument is found from the process's working directory
- Covers: -
- Channel: launch, mcp
- Steps: Create a file under the test project root, e.g. `.work/<worker>/cl/rel.txt`; start with args [".work/<worker>/cl/rel.txt"] (the harness starts the app in the project root).
- Expect: rel.txt is open with the absolute path of that file.

### CLI-011: A file argument that does not exist is offered for creation
- Covers: -
- Channel: launch, modal, mcp, files
- Steps: Queue nothing; start with args [`tmp/nothere.txt`, `tmp/nodir/x.txt`]; read the modal log (the launch's alerts take their first button).
- Expect: as Notepad++ does: an alert "Create new file" with '"<tmp/nothere.txt>" doesn't exist. Create it?' (Yes, No) — answered Yes, the empty file is created and opened; for the missing folder an alert "Cannot open file" saying the folder doesn't exist, and no tab.

### CLI-012: A folder argument opens the files under it; -r and wildcards
- Covers: -
- Channel: launch, mcp, modal
- Steps: Create `tmp/tree/a.txt`, `tmp/tree/sub/b.txt`, `tmp/tree/c.log`; start with args [`tmp/tree`]; then with ["-r", `tmp/tree/*.txt`]; then with [`tmp/tree/*.txt`]; then create `tmp/many` with 201 files and start with ["-r", `tmp/many`].
- Expect: a folder alone opens every file below it (a.txt, sub/b.txt, c.log), as upstream's doOpen does; "-r" with "*.txt" opens a.txt and sub/b.txt but not c.log; "*.txt" without -r opens a.txt only; for 201 files an alert "Amount of files to open is too large" asks first ("201 files are about to be opened. Are you sure to open them?").

### CLI-013: -openFoldersAsWorkspace puts the folders in the workspace panel
- Covers: -
- Channel: launch, mcp, ui
- Steps: Create `tmp/w1` and `tmp/w2` with a file each; start with ["-openFoldersAsWorkspace", `tmp/w1`, `tmp/w2`].
- Expect: `workspace_roots` is [w1, w2]; the Folder as Workspace panel is visible; no file of theirs is open in a tab.

## Position, language, read-only

### CLI-014: -n and -c put the caret on a line and column
- Covers: -
- Channel: launch, mcp
- Steps: `tmp/pos.txt` = "one\ntwo\nthree\n"; start with ["-n2", "-c3", pos.txt]; then with ["-n99", pos.txt]; then with ["-n2", "-c99", pos.txt].
- Expect: caret at line 2 column 3 (position 6); with -n99 the caret is on the last line; with -c99 at the end of line 2 (column 4).

### CLI-015: -p puts the caret at a position
- Covers: -
- Channel: launch, mcp
- Steps: Start with ["-p9", `tmp/pos.txt`]; then ["-p9", "-n1", `tmp/pos.txt`].
- Expect: the caret position is 9 (line 3 column 2) both times (-p wins over -n).

### CLI-016: -l sets the language of the files given
- Covers: -
- Channel: launch, mcp
- Steps: `tmp/l1.txt` and `tmp/l2.txt` hold "x = 1"; start with ["-lpython", l1.txt, l2.txt]; then with ["-lnosuchlang", l1.txt].
- Expect: both documents have language "python" and the Python menu item is checked for the one in front; with an unknown name the language stays "normal" and the application starts normally.

### CLI-017: -udl= picks a user defined language
- Covers: -
- Channel: launch, mcp, files
- Steps: Stop the app, write a userDefineLang.xml defining "MyLang" into the home's `Library/Application Support/NotepadMac`; start with `clean_home=False`, args ["-udl=MyLang", `tmp/u.txt`].
- Expect: u.txt's language is "MyLang" and the Language menu shows MyLang checked.

### CLI-018: -ro and the full read-only switches open the files read-only
- Covers: -
- Channel: launch, mcp, keys, files
- Steps: For each of "-ro", "-fullReadOnly", "-fullReadOnlySavingForbidden": start with [switch, `tmp/r1.txt`, `tmp/r2.txt`]; type "X" in the front document; read SCI_GETREADONLY of both (switching tabs).
- Expect: both documents are read-only (SCI_GETREADONLY 1, `read_only` true in `doc()`), typing changes nothing, the files on disk are unchanged and still writable (mode not changed).

### CLI-019: -monitor watches every file given
- Covers: IDM_VIEW_MONITORING
- Channel: launch, mcp, files
- Steps: Start with ["-monitor", `tmp/m1.log`, `tmp/m2.log`]; append "new\n" to m2.log; poll; select m1.log, append to it, poll.
- Expect: both documents are monitored (read_only true, View > Monitoring checked when in front); each shows its appended line within a few seconds with the caret at the end.

## Sessions

### CLI-020: -nosession neither restores nor overwrites the session
- Covers: -
- Channel: launch, mcp, files
- Steps: Start with `session=True, defaults={"restoreSession": True}`, open `tmp/s.txt`, quit gracefully (session.xml now lists s.txt, note its bytes and mtime); start with `session=True, clean_home=False, reset=False, args=["-nosession"]`; open `tmp/t.txt`; quit gracefully.
- Expect: with -nosession s.txt is not reopened (only "new 1" and what the test opened); after that quit session.xml is byte-identical with the same mtime (t.txt is not in it).

### CLI-021: -openSession loads the files given as sessions
- Covers: -
- Channel: launch, mcp
- Steps: Save a session of `tmp/o1.txt` and `tmp/o2.txt` (o2 current, caret at 3) to `tmp/sess.xml` with File > Save Session; restart with ["-openSession", `tmp/sess.xml`].
- Expect: o1.txt and o2.txt are open, o2.txt current with the caret at 3; there is no tab for sess.xml itself.

### CLI-022: Files given at launch open after the restored session
- Covers: -
- Channel: launch, mcp
- Steps: Start with restoreSession on and `session=True`; open `tmp/old1.txt`; quit gracefully; start with `session=True, clean_home=False, reset=False, args=[tmp/given.txt]`.
- Expect: old1.txt (from the session) and given.txt are both open; given.txt is the current tab.

## Window and new-text switches

### CLI-023: -titleAdd=, -alwaysOnTop, -x and -y shape the window
- Covers: IDM_VIEW_ALWAYSONTOP
- Channel: launch, mcp, menu
- Steps: Start with ["-titleAdd=Here", "-alwaysOnTop", "-x40", "-y60", `tmp/t.txt`].
- Expect: the window title is "t.txt — <tmp> - Here" and keeps the suffix after switching to another tab; the main window's level is the floating level (3) and View > Always on Top is checked; the window's top-left corner is 40 pt right of and 60 pt below the screen's top-left (frame x = screen x + 40, frame top = screen top − 60).

### CLI-024: -notabbar hides the tab bar only
- Covers: -
- Channel: launch, ui, mcp
- Steps: Start with ["-notabbar", `tmp/a.txt`, `tmp/b.txt`]; read the main window's controls with hidden ones included.
- Expect: the tab bar view is hidden; the status bar is still visible (upstream hides only the tab bar); both documents are open and switching with IDM_VIEW_TAB_NEXT works.

### CLI-025: -qt= and -qf= open a new document holding a text
- Covers: -
- Channel: launch, mcp
- Steps: Start with ["-qt=quoted ☃ text"]; then write `tmp/q.txt` = "from a file\nline 2\n" and start with ["-qf=" + q.txt].
- Expect: a new untitled tab in front holds exactly "quoted ☃ text"; SCI_CANUNDO is 0; the second launch's new tab holds "from a file\nline 2\n" and q.txt itself is not opened as a file.

### CLI-026: -notepadStyleCmdline takes the rest of the line as one file name
- Covers: -
- Channel: launch, mcp
- Steps: Write `tmp/my file name.txt`; start with ["-notepadStyleCmdline", `tmp/my`, "file", "name.txt"].
- Expect: one tab "my file name.txt" with that file's text; nothing else opened, no alert.

### CLI-027: -z skips the argument that follows it
- Covers: -
- Channel: launch, mcp
- Steps: Write `tmp/skipped.txt` and `tmp/kept.txt`; start with ["-z", skipped.txt, kept.txt].
- Expect: kept.txt is open; there is no tab for skipped.txt.

### CLI-028: -settingsDir= keeps this launch's settings in that folder
- Covers: -
- Channel: launch, mcp, files
- Steps: Start with ["-settingsDir=" + `tmp/cfg`]; read the editor context menu (`e2e_menu context=editor`, which writes the default contextMenu.xml); open Help > Debug Info and read its text.
- Expect: `tmp/cfg/contextMenu.xml` exists and the home's Application Support has no new contextMenu.xml; Debug Info says "Local Conf mode: ON".

## Switches that do one job and quit, and ignored ones

### CLI-029: -export=functionList writes each file's function list as JSON and quits
- Covers: -
- Channel: launch, files
- Steps: Write `tmp/f.cpp` = "class Shape {\npublic:\n  int area() { return 0; }\n};\nint helper(int a) { return a; }\n"; with restoreSession on and an existing session.xml in the home, launch the copy's executable (`app.executable`, with the environment `App.start` gives it: CFFIXED_USER_HOME, NPPMAC_E2E, no -nosession) with ["-export=functionList", f.cpp] and wait for the process to exit.
- Expect: the process exits by itself with status 0 within 10 s; `tmp/f.cpp.result.json` is exactly {"leaves":["helper"],"nodes":[{"leaves":["area"],"name":"Shape"}],"root":"f.cpp"}; session.xml is unchanged (the export runs as -nosession).

### CLI-030: -quickPrint prints the files given and quits
- Covers: IDM_FILE_PRINTNOW
- Channel: launch, files
- Steps: With the print hook sending jobs to a PDF file, launch the copy's executable as in CLI-029 with ["-quickPrint", `tmp/p.txt`] and wait for the process to exit.
- Expect: one print job titled "p.txt" without a print panel; its PDF holds p.txt's text; the process exits with status 0 by itself; no session is written.

### CLI-031: Switches the port does not need are accepted and ignored
- Covers: -
- Channel: launch, mcp, files
- Steps: Start with ["-multiInst", "-noPlugin", "-systemtray", "-loadingTime", "-pluginMessage=\"hello\"", `tmp/i.txt`].
- Expect: the application starts normally with i.txt open and current; none of the switches became a tab or an alert; app.log contains "NotepadMac: -pluginMessage ignored, plugins are not supported: hello" (quotes stripped).
