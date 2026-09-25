# GIT — Git integration (margin, status bar, panel, commit window, branches, remotes)

The port's own Git support (`macos/app/GitCommands.mm`, menu Plugins > Git), which drives the real `git` executable: the margin markers 6-8 in margin 4 for lines added, changed and removed since HEAD, the branch (with ahead/behind) at the end of the status bar, the Git panel (status list with Staged/Status/File columns, a branch label, Stage/Unstage/Discard/Commit/Refresh buttons), the Commit window, blame and file history as read-only documents, Compare with HEAD (through the Compare engine), Revert Change at Caret to HEAD, branches (Switch Branch submenu, New Branch prompt), and Fetch/Pull/Push streamed into the console window. Every test makes its own repository under `tmp` (`git init`, `user.name`/`user.email`/`commit.gpgsign=false` in the repository config, commits made with the `git` CLI), plus a local bare repository and a second clone where remotes are needed. None of the sixteen Git commands has an IDM id, so `Covers` is `-`; the tests reach them by menu path with `app.run("Plugins|Git|<item>")` (run_command's path resolution; `…` may be written `...`) or `e2e_menu_invoke`, and read the console with `app.get("editor", "console.text")` or `app.ui("Console")` when it is shown. Destructive commands ask through NSAlert and are answered with queued answers (`Discard`/`Save` = button 1, `Cancel` = button 2); the New Branch prompt is answered with `{button: 1, field: name}`. Out of scope: the Compare engine itself (COMPARE), the NppExec console's own commands (RUN), a Mac without git (cannot be simulated: the executable is looked up once through `xcode-select -p`).

## Menu and reachability

### GIT-001: Plugins > Git lists its sixteen commands in upstream-style order
- Covers: -
- Channel: menu
- Steps: Read `app.menu_tree("Plugins|Git", 1)`.
- Expect: the non-separator titles are, in order, Git Panel, Compare with HEAD, Clear Active Compare, Blame, File History, Stage File, Unstage File, Revert Change at Caret to HEAD, Discard Changes in File…, Commit…, Switch Branch, New Branch…, Fetch, Pull, Push, Refresh Git Status; separators after Git Panel, File History, Commit…, New Branch… and Push; Switch Branch has a submenu; every item is enabled (the commands explain themselves instead of greying out).

### GIT-002: Every Git command outside a repository declines with the reason in the console
- Covers: -
- Channel: menu, ui, mcp
- Steps: Open a file in `tmp` that is not in any repository; for each of Compare with HEAD, Blame, File History, Stage File, Unstage File, Revert Change at Caret to HEAD, Discard Changes in File…, New Branch… (answered `{button:1, field:"x"}`) run it by menu path; read the console text.
- Expect: each run appends `[git] The file is not in a Git repository` to the console and shows the console window; no new document is opened; no alert is logged except the New Branch prompt; the document text is unchanged; the status bar has no `⎇` field and `SCI_GETMARGINWIDTHN(4)` is 0.

### GIT-003: Fetch/Pull/Push outside a repository say so in the console
- Covers: -
- Channel: menu, ui
- Steps: With a non-repository file in front, run Plugins|Git|Fetch, then Pull, then Push.
- Expect: the console window is visible and gets `The file is not in a Git repository` three times; no `$ git` line is written; nothing else changes.

### GIT-004: An unsaved new document is treated as outside a repository
- Covers: -
- Channel: menu, mcp, ui
- Steps: `app.new("text\n")`; read the status bar field (`e2e_ui` main, the NSTextField whose value holds `Ln:`); run Plugins|Git|Blame and open Plugins|Git|Git Panel.
- Expect: the status bar has no `⎇`; the console says `[git] The file is not in a Git repository`; the panel's branch label is empty and its table has 0 rows.

## Margin markers

### GIT-005: Changed, added and removed lines carry markers 7, 6 and 8
- Covers: -
- Channel: mcp
- Steps: Commit `a.txt` = `one\ntwo\nthree\nfour\n`; open it; `set_text("one\nTWO\nthree\nfour\nfive\n")`; poll `SCI_MARKERGET` (2046) on lines 0-4 masked with 0x1C0; then `set_text("one\nthree\nfour\n")` and poll again.
- Expect: first text: line 1 = 1<<7 (changed), line 4 = 1<<6 (added), lines 0, 2, 3 = 0; second text: line 1 (`three`) = 1<<8 (removed arrow), the others 0; `SCI_GETMARGINWIDTHN(4)` is 6 while the document is in a repository.

### GIT-006: Lines removed at the end put the removed marker on the last line
- Covers: -
- Channel: mcp
- Steps: HEAD `one\ntwo\nthree\nfour\n`; `set_text("one\ntwo\n")`; poll markers.
- Expect: exactly one line carries 1<<8 and it is the last line (line index 2, the empty line after the final newline); lines 0-1 carry none of 6-8.

### GIT-007: Markers follow typing about 0.6 s after it stops, without a save
- Covers: -
- Channel: keys, mcp
- Steps: Open the committed file, put the caret at the end (`go_to` last line), type `six\n` with `app.type`; immediately read `SCI_MARKERGET` on the new line, then poll up to 5 s.
- Expect: the typed line ends up with 1<<6; the document is still modified (`get_document.modified` true) — markers are against the text as it is, not the file on disk; unchanged lines carry none.

### GIT-008: Markers return to none when the text is typed back to HEAD's
- Covers: -
- Channel: mcp
- Steps: `set_text` a changed text, wait for a marker, then `set_text` HEAD's exact text; poll.
- Expect: no line carries any of markers 6-8; the margin stays 6 px wide (still in a repository).

### GIT-009: A file never committed has every line marked added
- Covers: -
- Channel: mcp
- Steps: In a repository with one commit, create untracked `new.txt` = `a\nb\n` and open it; also make a fresh repository with no commit at all and open a file in it.
- Expect: in both cases lines 0 and 1 carry 1<<6 and none of 7/8; status bar shows `⎇ <branch>` for the committed repo and `⎇ main`/`⎇ master` (the unborn branch name) for the empty one.

### GIT-010: The MISC. preference switches the git margin off and on
- Covers: -
- Channel: prefs, mcp, ui
- Steps: With a changed tracked file open, `set_prefs(gitMarginMarks=False)` (and apply), read markers and margin 4 width; also open Preferences > MISC. and check the checkbox "Git: mark lines changed since the last commit in the margin" is off; set it back on.
- Expect: off: no markers 6-8 anywhere and `SCI_GETMARGINWIDTHN(4)` = 0; the checkbox state matches; on again: the markers are back and the width is 6; the preference ends as it started.

### GIT-011: Markers are recomputed per document when switching tabs
- Covers: -
- Channel: mcp
- Steps: Open a changed tracked file (marker on line 1) and a file outside any repository; switch to the outside file, read margin 4 width and markers; switch back.
- Expect: the outside file shows width 0 and no markers 6-8; back on the tracked file the changed marker is on line 1 again and the width is 6.

### GIT-012: A repository reached through /var instead of /private/var still gets markers
- Covers: -
- Channel: mcp
- Steps: Build the repository under the unresolved temporary folder (`tempfile.gettempdir()`, a `/var/folders/...` path) and open the file by its `/var/...` path; change line 0 with `set_text`.
- Expect: `get_document.path` starts with `/var/`; the status bar shows `⎇ <branch>`; the changed line carries 1<<7 (the relative path is worked out through the symlink).

### GIT-013: Big files are not diffed while typing but are on save
- Covers: -
- Channel: keys, mcp, files
- Steps: Commit a 2.5 MB text file (50 000 lines); open it; append a line by typing at the end; wait 1.5 s and read the marker of the new line; then save with IDM_FILE_SAVE and read it again.
- Expect: before saving the new line has no marker 6 (over 2 MB the live refresh is skipped); after the save it carries 1<<6.

## Status bar

### GIT-014: The status bar ends with the branch inside a repository
- Covers: -
- Channel: ui
- Steps: Open a tracked file; read the status field (the NSTextField whose value contains `Ln:`).
- Expect: its value ends with `    ⎇ <branch>` where `<branch>` is `git rev-parse --abbrev-ref HEAD`; it comes after the `INS` field.

### GIT-015: Ahead and behind counts appear after local commits and Fetch
- Covers: -
- Channel: ui, menu
- Steps: Push the first commit to a bare repository with `-u`; commit locally with the CLI, run Plugins|Git|Refresh Git Status; then commit and push from a second clone of the bare repository and run Plugins|Git|Fetch, waiting for `- done` in the console.
- Expect: after the refresh the status bar ends `⎇ main ↑1`; after the fetch it ends `⎇ main ↑1 ↓1`; the Git panel label contains `↑1` and `↓1` likewise.

### GIT-016: A detached HEAD shows as HEAD
- Covers: -
- Channel: ui, menu
- Steps: With the CLI run `git checkout -q --detach`; run Plugins|Git|Refresh Git Status.
- Expect: the status bar ends with `⎇ HEAD`; the panel label begins `HEAD  ·  `.

### GIT-017: Refresh Git Status picks up a commit made outside the editor
- Covers: -
- Channel: menu, mcp, ui
- Steps: Open a tracked file, edit and save it (changed marker on line 1); commit it with the git CLI; run Plugins|Git|Refresh Git Status.
- Expect: markers 6-8 are all gone (HEAD moved and was fetched again); the panel, if visible, lists no row for the file; the status bar keeps `⎇ <branch>`.

## Git panel

### GIT-018: Git Panel toggles the docked panel
- Covers: -
- Channel: menu, ui
- Steps: Run Plugins|Git|Git Panel twice, reading the main window's controls after each.
- Expect: after the first run buttons Stage, Unstage, Discard, Commit, Refresh, a branch label and a table with columns Staged/Status/File are visible in the main window; after the second they are gone (hidden).

### GIT-019: The panel lists modified, renamed, staged and untracked files in order
- Covers: -
- Channel: ui, files
- Steps: In a repository with `src/tracked.txt` and `other.txt` committed: modify `src/tracked.txt` on disk, `git mv other.txt renamed.txt`, create untracked `fresh.txt`; open `src/tracked.txt`; show the panel.
- Expect: the table cells are, in order, `["✓","R","renamed.txt ← other.txt"]`, `["","M","src/tracked.txt"]`, `["","??","fresh.txt"]` (staged first, then changed, then untracked); the label is `<branch>  ·  <repo folder name>  ·  3 changed, 1 staged`.

### GIT-020: Stage File and Unstage File move the current file between index and worktree
- Covers: -
- Channel: menu, ui, files
- Steps: Modify and save a tracked file; show the panel; run Plugins|Git|Stage File, read the table and `git status --porcelain`; run Plugins|Git|Unstage File and read them again.
- Expect: after Stage the row is `["✓","M",path]`, porcelain `M  path`, label ends `1 staged`; after Unstage the row is `["","M",path]` and porcelain ` M path`.

### GIT-021: Stage File on an unsaved document asks to save first
- Covers: -
- Channel: menu, modal, files
- Steps: Change a tracked document without saving; queue `alerts=[2]` and run Plugins|Git|Stage File; then queue `alerts=[1]` and run it again.
- Expect: the first run logs an alert `Save the file before staging it?` with buttons Save/Cancel answered Cancel, the document stays modified and nothing is staged; the second saves the document (modified false, file on disk has the new text) and `git status --porcelain` shows `M  path`.

### GIT-022: The panel's Stage and Unstage buttons act on the selected rows
- Covers: -
- Channel: ui, files
- Steps: With an untracked `fresh.txt` and a modified tracked file listed, select the `fresh.txt` row (`e2e_act select` on the table) and click Stage; select it again and click Unstage; then select both rows (`select` row 0, then row 1 with `extend: true`) and click Stage.
- Expect: after the first Stage its row reads `["✓","A","fresh.txt"]`; after Unstage it is `["","??","fresh.txt"]` again; after staging both, both rows carry `✓` and the label says `2 staged`.

### GIT-023: Stage before the first commit and unstage back to untracked
- Covers: -
- Channel: menu, files
- Steps: `git init` a repository with no commits; open a new file `a.txt` saved in it; run Plugins|Git|Stage File then Plugins|Git|Unstage File, reading `git status --porcelain` after each.
- Expect: after Stage `A  a.txt`; after Unstage `?? a.txt` (taken out of the index with `rm --cached`, as there is no HEAD); no `[git]` error in the console.

### GIT-024: The panel's Discard asks and restores the selected files
- Covers: -
- Channel: ui, modal, files, mcp
- Steps: Modify two tracked files on disk (one open in a tab, one not); select both rows (`select` with `extend: true`); queue `alerts=[2]`, click Discard; then queue `alerts=[1]` and click Discard again.
- Expect: the first alert says `Discard the changes in "2 files"?` with informative text `The file goes back to the last committed version. This cannot be undone.` and buttons Discard/Cancel, and nothing changes; after the second both files on disk equal HEAD, the open tab's text is HEAD's and unmodified, and the table has no rows for them.

### GIT-025: The panel's Discard with nothing selected does nothing
- Covers: -
- Channel: ui, modal
- Steps: Show the panel freshly (no row selected yet) with one modified file listed; click Discard.
- Expect: no alert is logged (`modal_log()` empty); the file on disk is unchanged.

### GIT-026: The panel's Refresh button and double-click on a row
- Covers: -
- Channel: ui, mcp
- Steps: Show the panel; create `later.txt` in the repository with Python; click Refresh; then `e2e_act double_click` the `later.txt` row.
- Expect: after Refresh a row `["","??","later.txt"]` is present; the double-click opens `later.txt` as the document in front (`get_document.path` ends `later.txt`); double-clicking a row whose file was deleted (a `D` row) opens nothing.

### GIT-027: The panel says when the file is outside a repository
- Covers: -
- Channel: ui
- Steps: Show the panel with a tracked file in front, then switch to a file outside any repository.
- Expect: the table has 0 rows and the branch label reads `The file is not in a Git repository`; switching back lists the repository's rows again.

## Discard and revert

### GIT-028: Discard Changes in File asks, then puts the committed text back on disk and in the tab
- Covers: -
- Channel: menu, modal, files, mcp
- Steps: Change and save a tracked `a.txt`; queue `alerts=[2]`, run Plugins|Git|Discard Changes in File…; queue `alerts=[1]` and run it again.
- Expect: first: alert `Discard the changes in "a.txt"?`, buttons Discard/Cancel, answered Cancel, file and tab unchanged; second: the file on disk equals HEAD, the tab's text equals HEAD, `modified` is false and the margin carries no markers.

### GIT-029: Revert Change at Caret restores a changed line in one undo step
- Covers: -
- Channel: menu, mcp, keys
- Steps: HEAD `one\ntwo\nthree\nfour\n`; `set_text("one\nTWO\nthree\nfour\nfive\n")`; `go_to(line=2)`; run Plugins|Git|Revert Change at Caret to HEAD; then `go_to(line=5)` and run it again; then undo once (IDM_EDIT_UNDO).
- Expect: after the first run the text is `one\ntwo\nthree\nfour\nfive\n` and the caret is at the start of line 2; after the second `one\ntwo\nthree\nfour\n`; one undo gives back `one\ntwo\nthree\nfour\nfive\n`; the markers follow each step.

### GIT-030: Revert Change at Caret puts removed lines back and handles a last line without ending
- Covers: -
- Channel: menu, mcp
- Steps: `set_text("one\nthree\nfour\n")`, `go_to(line=2)` (the line after the removal) and run the revert; then `set_text("one\ntwo\nthree\nfour\nfive")` (no final newline), `go_to(line=5)` and run it again.
- Expect: first: `one\ntwo\nthree\nfour\n`; second: `one\ntwo\nthree\nfour\n`.

### GIT-031: Revert Change at Caret on an unchanged line or an uncommitted file reports why
- Covers: -
- Channel: menu, mcp
- Steps: With a change on line 2 only, `go_to(line=1)` and run the revert; then open an untracked file in the repository and run it.
- Expect: the text is unchanged both times; the console gets `[git] The caret is on no change since the last commit`, then `[git] The file is not in HEAD yet`.

## Compare with HEAD, blame, history

### GIT-032: Compare with HEAD shows HEAD's text in the second view and Clear Active Compare ends it
- Covers: -
- Channel: menu, mcp, ui
- Steps: HEAD `one\ntwo\nthree\nfour\n`, document `one\nTWO\nthree\nfour\n` (unsaved); run Plugins|Git|Compare with HEAD; read the sub view's text (`SCI_GETTEXT`, view `sub`) and the compare markers on main line 1; run Plugins|Git|Clear Active Compare.
- Expect: the sub view holds `one\ntwo\nthree\nfour\n`; main line 1 carries a compare marker (any of bits 0/2/3/4 of `SCI_MARKERGET`) and the compare bar is shown; after Clear the second view is hidden, markers 0/2/3/4 are gone, and the document text is untouched.

### GIT-033: Compare with HEAD for a file not yet committed is refused
- Covers: -
- Channel: menu, ui
- Steps: Open an untracked file in a repository; run Plugins|Git|Compare with HEAD.
- Expect: no comparison starts (the second view stays hidden); the console gets `[git] The file is not in HEAD yet`.

### GIT-034: Blame opens a read-only document named "<file> (blame)"
- Covers: -
- Channel: menu, mcp
- Steps: Commit `a.txt` as author `T Runner`, change line 2 unsaved; run Plugins|Git|Blame.
- Expect: a new tab in front titled `a.txt (blame)`, `read_only` true, `modified` false, `path` null; its text has one line per line of the file on disk, committed lines containing `T Runner` and the short hash, and the original tab is unchanged; closing it needs no save prompt.

### GIT-035: File History opens a read-only document with the commits
- Covers: -
- Channel: menu, mcp
- Steps: Make two commits on `a.txt` (subjects `first`, `second`); run Plugins|Git|File History.
- Expect: a tab `a.txt (history)`, read-only; its text lists `second` before `first`, each under a line `<7-char hash>  <YYYY-MM-DD>  T Runner`; for an untracked file the history document says `The file is not in HEAD yet`.

### GIT-036: Blame of an untracked file reports git's error
- Covers: -
- Channel: menu, ui, mcp
- Steps: Open an untracked file in a repository; run Plugins|Git|Blame.
- Expect: no new tab opens (the document count is unchanged); the console gets a `[git] ` line with git's own message (contains `no such path` or `fatal`).

## Commit window

### GIT-037: Commit… opens the window with its summary and a disabled Commit button
- Covers: -
- Channel: menu, ui
- Steps: Stage `a.txt` and leave `b.txt` modified; run Plugins|Git|Commit…; read the `Commit` window's controls.
- Expect: a window titled `Commit` with the label `Commit message`, an empty NSTextView, the summary `1 files staged: a.txt  ·  1 not staged`, an unticked checkbox `Stage all changes first`, and buttons Cancel and Commit, Commit disabled (no message yet).

### GIT-038: Typing a message enables Commit; committing closes the window and names the commit
- Covers: -
- Channel: ui, files
- Steps: In the open Commit window `set_text` the NSTextView to `second commit\n\nwith a body`; click the NSButton `Commit`.
- Expect: Commit becomes enabled after the message is set; after the click the window is gone, `git log -1 --format=%s` is `second commit` and `%b` is `with a body`, the console text contains `[git] Committed <first 7 of the new HEAD>`, the margin carries no markers and the status bar still shows the branch.

### GIT-039: Stage all changes first stages and commits everything
- Covers: -
- Channel: ui, files
- Steps: With nothing staged, one modified tracked file and one untracked file, open the Commit window, tick `Stage all changes first`, set a message, click Commit.
- Expect: before the click the summary reads `2 files will be staged and committed` and Commit is enabled; after it `git status --porcelain` is empty and the new commit contains both files; reopening the window shows the checkbox unticked and the message empty.

### GIT-040: Commit is disabled with nothing staged even with a message; Cancel and Escape close
- Covers: -
- Channel: ui, keys
- Steps: With changes but nothing staged, open the window and set a message; read the button; press `escape` in the window; reopen and click Cancel.
- Expect: Commit stays disabled while the checkbox is unticked; Escape and Cancel both close the window without a commit (HEAD unchanged).

### GIT-041: A failing commit keeps the window open with git's message
- Covers: -
- Channel: ui, files
- Steps: Install an executable `.git/hooks/pre-commit` that prints `hook says no` to stderr and exits 1; stage a change, open the window, set a message, click Commit.
- Expect: the window stays open; the red problem label contains `hook says no`; HEAD is unchanged; the message text is kept.

### GIT-042: Cmd+Return in the message commits
- Covers: -
- Channel: keys, ui, files
- Steps: Stage a change, open the window, type `via keyboard` into the message (`app.type` with the window), press `cmd+return`.
- Expect: the window closes and `git log -1 --format=%s` is `via keyboard`.

### GIT-043: The Commit window outside a repository says so
- Covers: -
- Channel: menu, ui
- Steps: With a file outside any repository in front, run Plugins|Git|Commit….
- Expect: the summary reads `The file is not in a Git repository` and Commit is disabled even after a message is set.

## Branches

### GIT-044: New Branch… creates and checks out the branch; a blank name is refused
- Covers: -
- Channel: menu, modal, ui
- Steps: Queue `alerts=[{"button":1,"field":"feature/x"}]` and run Plugins|Git|New Branch…; then queue `{"button":1,"field":"  "}` and run it again; then queue `alerts=[2]` (Cancel) and run it once more.
- Expect: the prompt `New branch name:` with OK/Cancel is logged; after the first run `git rev-parse --abbrev-ref HEAD` is `feature/x` and the status bar ends `⎇ feature/x`; the second leaves the branch as is and the console gets `[git] A branch needs a name`; the cancelled prompt creates nothing (`git branch --list` unchanged).

### GIT-045: Switch Branch lists the branches with the current one ticked and checks one out
- Covers: -
- Channel: menu, ui, mcp, files
- Steps: Branch `other` has `a.txt` = `other\n` committed, the current branch has `one\n`; with `a.txt` open, read `app.menu_tree("Plugins|Git|Switch Branch", 1)`; invoke `Plugins|Git|Switch Branch|other`; then switch back the same way.
- Expect: the submenu lists both branches, the current one checked; after switching to `other` the status bar ends `⎇ other`, the open unmodified tab reloads to `other\n`, and the markers are recomputed against the new HEAD; switching back restores `one\n`. Outside a repository the submenu holds one disabled item `The file is not in a Git repository`. (Needs hook: the submenu is filled by its delegate's `menuNeedsUpdate:`, which `e2e_menu`/`e2e_menu_invoke` do not call — they see 0 items; until then the checkout step falls back to `app.invoke("editor", "gitCheckoutBranch:", ["other"])`.)

### GIT-046: Switching to a branch with conflicting local changes fails with git's message
- Covers: -
- Channel: menu, ui
- Steps: Modify and save `a.txt` so that `git checkout other` would overwrite it; switch to `other` (as in GIT-045).
- Expect: the branch stays the same (status bar unchanged); the console gets a `[git] ` line containing `would be overwritten`; the file keeps the local change.

## Remotes in the console

### GIT-047: Push to a local bare repository streams into the console and ends done
- Covers: -
- Channel: menu, ui, files
- Steps: Add `origin` = a bare repository in `tmp`, set `push.default=current`; run Plugins|Git|Push; poll the console for `- done` or `- git failed` (20 s).
- Expect: the console window is shown; its text contains `$ git push`, git's `[new branch]` line and ends `- done`; `git rev-parse <branch>` in the bare repository equals the local HEAD.

### GIT-048: Fetch from a missing remote ends failed with git's complaint
- Covers: -
- Channel: menu, ui
- Steps: Set `origin` to `/nonexistent/remote`; run Plugins|Git|Fetch; poll the console.
- Expect: the console contains `$ git fetch --all --prune`, a line with `fatal` or `does not appear`, and ends `- git failed`; the editor stays responsive (a `get_document` call answers while it runs) and the status bar branch is unchanged.

### GIT-049: Pull brings a remote commit in and the open document follows
- Covers: -
- Channel: menu, ui, mcp, files
- Steps: From a second clone of the bare repository, commit a change to `a.txt` and push; in the app (with `a.txt` open, unmodified, `pull.rebase=false`) run Plugins|Git|Pull, answering any reload alert with button 1; poll the console for the second `- done`.
- Expect: the console shows `$ git pull` and ends `- done`; `a.txt` on disk and the tab's text both hold the pushed change; the markers are recomputed (none on the pulled lines); the status bar shows no `↓`.

### GIT-050: Push without a remote fails in the console without hanging
- Covers: -
- Channel: menu, ui
- Steps: In a repository with no remote, run Plugins|Git|Push; poll the console up to 20 s.
- Expect: the console ends `- git failed` with git's message (contains `No configured push destination` or `fatal`); no prompt or alert appears (`GIT_TERMINAL_PROMPT=0`).

## Localisation

### GIT-051: The Commit window and the panel are translated and nothing is cut in German
- Covers: -
- Channel: launch, ui, snapshot
- Steps: Start with `-NppMac.localizationFile german.xml` (fresh_app); open a tracked file, show the Git panel and open the Commit window; read their controls and take snapshots.
- Expect: the window title, the Commit button, the `Commit message` label, the `Stage all changes first` checkbox and the panel's Stage button show the texts german.xml's nativeLang-extra gives for them; each button's frame is at least as wide as needed (no button text truncated in the snapshot); the English settings are restored afterwards.
