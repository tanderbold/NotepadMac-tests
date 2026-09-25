# RUN — Run menu and NppExec

The Run menu (Run… with Notepad++'s `$(…)` variables, Save Current Command…, Manage Saved Commands…, Show Console, Validate shortcuts, the saved commands listed under it) and the NppExec stand-in under Plugins › NppExec (the Execute dialog, saved scripts in `npes_saved.txt`, Execute Previous, Stop, the console, the script language: variables, flow, programs, editor commands). What is observed: the Console panel's text (`e2e_ui` on the window titled "Console", its `NSTextView` value), the prompts in the modal log, files the commands and scripts write, the menus, and `savedRunCommands` in the preferences. Commands without an `IDM_*` id are reached with `run_command` by menu path (`Run|Save Current Command…`, `Plugins|NppExec|Stop Running NppExec Script`). The Run prompts are NSAlerts answered with queued `{button, field}` answers. The NppExec dialog runs its own modal loop (`runModalForWindow:`), which cannot be started from inside a tool call: the test opens it with `e2e_invoke` on `app`, `performSelector:withObject:afterDelay:` with `["executeScriptDialog:", null, 0.05]`, so the call returns first, and then drives the dialog with `e2e_ui`/`e2e_act`. Open Plugins Folder… (also in the Run menu) belongs to PLUGINS. Shortcut Mapper editing belongs to SETTINGS.

## Run dialog

### RUN-001: Run… runs a command and shows it and its output in the Console
- Covers: IDM_EXECUTE
- Channel: modal, ui
- Steps: Open a new document; queue the answer `{button: 1, field: "echo hello-run"}` and run `IDM_EXECUTE`; wait until the Console window's text contains `hello-run`.
- Expect: the modal log has one alert with message `Run (variables such as $(FULL_CURRENT_PATH) are substituted)` and buttons `OK`, `Cancel`; a visible window titled `Console` (class `NppPanel`) exists; its text view is not editable; its text contains the line `> echo hello-run` followed by the line `hello-run`; no `exit status` line is written for a zero status.

### RUN-002: Run… has Shift+Cmd+R and opens from the keyboard
- Covers: IDM_EXECUTE
- Channel: keys, menu, modal
- Steps: Read the menu item of `IDM_EXECUTE`; queue the answer `{button: 1, field: "echo from-keys"}` and press `shift+cmd+r` in the main window.
- Expect: the item's title is `Run…`, it is enabled and its key is `shift+cmd+r`; the modal log shows the Run prompt answered `OK`; the Console receives `from-keys`.

### RUN-003: Cancel runs nothing; the prompt offers the last command
- Covers: IDM_EXECUTE
- Channel: modal, ui
- Steps: Run `echo first-cmd` through `IDM_EXECUTE`; wait for it in the Console. Queue answer `2` (Cancel) with field `echo must-not-run` and run `IDM_EXECUTE` again; then queue `2` once more and run it a third time.
- Expect: after the cancel the Console text has no `must-not-run`; the third prompt's `fields` in the modal log are `["echo first-cmd"]` (the last command that ran, not the cancelled text); an empty field answered `OK` runs nothing either (no new `> ` line).

### RUN-004: The file variables of a saved document
- Covers: IDM_EXECUTE
- Channel: modal, ui, files
- Steps: Write `tmp/my file.txt` (`alpha beta\nsecond line\n`) and open it; for each of `FULL_CURRENT_PATH`, `CURRENT_DIRECTORY`, `FILE_NAME`, `NAME_PART`, `EXT_PART` run `printf '[%s]\n' $(NAME)` through the Run prompt.
- Expect: the Console shows exactly one bracketed line per command (a value with a space is passed as one word): `[<tmp>/my file.txt]`, `[<tmp>]`, `[my file.txt]`, `[my file]`, `[.txt]`; the echoed command line (`> …`) shows the value single-quoted where it holds a space.

### RUN-005: EXT_PART keeps the dot and is empty without an extension
- Covers: IDM_EXECUTE
- Channel: modal, ui, files
- Steps: For each of the files `tmp/Makefile` and `tmp/a.tar.gz`, open it and run `printf '<%s|%s>\n' "$(NAME_PART)" "$(EXT_PART)"`.
- Expect: `Makefile` gives `<Makefile|>`; `a.tar.gz` gives `<a.tar|.gz>`.

### RUN-006: The caret variables (zero-based line and column, as on Windows)
- Covers: IDM_EXECUTE
- Channel: modal, ui, mcp
- Steps: Open a file with `alpha beta\nsecond line\n`; put the caret at line 1 column 8 (one-based, inside `beta`) and run `printf '[%s][%s][%s][%s]\n' $(CURRENT_WORD) $(CURRENT_LINE) $(CURRENT_COLUMN) $(CURRENT_LINESTR)`; then select `second` on line 2 and run `printf '[%s]\n' $(CURRENT_WORD)`.
- Expect: the first line is `[beta][0][7][alpha beta]` (line and column are Scintilla's zero-based numbers, not the status bar's); with a selection CURRENT_WORD is the selected text: `[second]`.

### RUN-007: The application's own variables
- Covers: IDM_EXECUTE
- Channel: modal, ui
- Steps: Run `printf '[%s][%s]\n' $(NPP_DIRECTORY) $(NPP_FULL_FILE_PATH)`.
- Expect: the first value is the folder that contains the test copy's `.app` bundle (`app.bundle.parent`); the second is the copy's executable (`app.executable`, ending in `Contents/MacOS/NotepadMac`).

### RUN-008: An untitled document gives its tab name
- Covers: IDM_EXECUTE
- Channel: modal, ui, mcp
- Steps: With only an empty untitled document open (tab name from `list_documents`, e.g. `new 1`), run `printf '[%s][%s][%s]\n' "$(FULL_CURRENT_PATH)" "$(FILE_NAME)" "$(CURRENT_DIRECTORY)"`.
- Expect: the Console shows `[new 1][new 1][]` (with the actual tab name); the command runs and exits 0.

### RUN-009: Unknown and unclosed variables are left for the shell
- Covers: IDM_EXECUTE
- Channel: modal, ui
- Steps: Run in turn `echo $(echo sub-ok)`, `echo 'a $(unclosed'`, `echo 'cost is $5'` and `echo $(NOT_A_VAR_XYZ) tail`.
- Expect: the Console shows `sub-ok` (an unknown name is the shell's command substitution), `a $(unclosed`, `cost is $5`; for the last, the echoed command line still reads `$(NOT_A_VAR_XYZ)` and the shell's `NOT_A_VAR_XYZ: command not found` appears, followed by ` tail` output.

### RUN-010: Text from the document never becomes a command
- Covers: IDM_EXECUTE
- Channel: modal, ui, files
- Steps: Open `tmp/inj.txt` whose first line is `a'b"c $HOME ` + "`touch PWNED1`" + `; touch PWNED2`; caret on line 1. For each of `echo $(CURRENT_LINESTR)`, `echo "$(CURRENT_LINESTR)"`, `echo '$(CURRENT_LINESTR)'`, `echo "$(printf %s $(CURRENT_LINESTR))"` and `echo ` + "`printf %s $(CURRENT_LINESTR)`" run it and wait for its output.
- Expect: no file `PWNED1` or `PWNED2` appears in `tmp` (nor in the app's working folder); every command prints the line literally, `$HOME` unexpanded.

### RUN-011: The command runs in the document's folder
- Covers: IDM_EXECUTE
- Channel: modal, ui, files
- Steps: Open `tmp/sub/w.txt` and run `pwd; ls`; also create `tmp/sub/marker.txt` beforehand.
- Expect: the Console shows `<tmp>/sub` (symlinks resolved) and lists `marker.txt` and `w.txt`.

### RUN-012: Failure, standard error and non-ASCII output reach the Console
- Covers: IDM_EXECUTE
- Channel: modal, ui
- Steps: Run `echo oops >&2; printf 'é✓ 日本\n'; exit 3`; then run `/no/such/program`.
- Expect: the Console shows `oops`, `é✓ 日本` (decoded as UTF-8) and `(exit status 3)`; the second gives the shell's `not found` message and `(exit status 127)`.

### RUN-013: A command runs in the background and its output streams
- Covers: IDM_EXECUTE
- Channel: modal, ui, mcp
- Steps: Run `echo first-part; sleep 3; echo second-part`; immediately afterwards time a `get_document` call and poll the Console.
- Expect: `run_command` and `get_document` each come back in under 1 s while the command runs; `first-part` is in the Console while `second-part` is not yet; `second-part` arrives within 10 s.

### RUN-014: A Run command is not ended after 30 seconds, and a child left in the background does not hold it
- Covers: IDM_EXECUTE
- Channel: modal, ui
- Steps: (slow, ~35 s) Run `sleep 33; echo still-here` and poll the Console for up to 45 s; then Run `(sleep 3; echo late-line) & exit 4`.
- Expect: `still-here` arrives (Command::run hands the program to ShellExecute, which sets no time limit) and the Console never says `timed out`; the second command's `(exit status 4)` comes at once, before `late-line` (its shell has ended; the child it left holds the output pipe), and `late-line` still reaches the Console afterwards.

## Saved commands

### RUN-015: Save Current Command… adds a named entry to the Run menu
- Covers: -
- Channel: menu, modal, prefs, ui
- Steps: Run `echo last-one` through `IDM_EXECUTE`; queue `{button: 1, field: "echo saved $(FILE_NAME)"}` and `{button: 1, field: "Say"}` and run `Run|Save Current Command…`; open `tmp/x.txt` and run `Run|Say`.
- Expect: the first prompt (`Command to save`) offered `echo last-one`; the second is `Name it`; the Run menu ends with a separator and an item `Say`; the preference `savedRunCommands` is `[{"name": "Say", "command": "echo saved $(FILE_NAME)"}]`; running it prints `saved x.txt` (variables are filled in when it runs, from the document in front).

### RUN-016: Saving under an existing name replaces; a cancelled save saves nothing
- Covers: -
- Channel: menu, modal, prefs
- Steps: Save `make` as `Build`, then `make -j8` as `Build`; then run Save Current Command… answering the name prompt with Cancel; then answer the command prompt with Cancel.
- Expect: `savedRunCommands` holds one `Build` entry with command `make -j8` and the Run menu one `Build` item; the cancelled saves add nothing; when the command prompt is cancelled the name prompt is not shown (one alert in the log).

### RUN-017: Manage Saved Commands… lists and removes
- Covers: -
- Channel: menu, modal, prefs, clipboard
- Steps: Save `A` = `echo a` and `B` = `echo b`; queue `2` (Copy) for the listing and `{button: 1, field: "A"}` for the removal prompt and run `Run|Manage Saved Commands…`; run it again answering the removal prompt with `nosuch`; remove `B`; run it once more.
- Expect: the listing alert is titled `Saved Commands` with informative text `A\techo a\nB\techo b\n`; Copy puts that text on the clipboard; after the removal only `B` is in the menu and the preference; an unknown name removes nothing; with nothing saved the only alert is `No commands have been saved.` (no removal prompt) and the Run menu has no trailing separator.

### RUN-018: Saved commands survive a restart
- Covers: -
- Channel: launch, menu, prefs, ui
- Steps: Save `Keep` = `echo kept-across`; `app.restart()` (home and preferences kept); run `Run|Keep`.
- Expect: after the restart the Run menu still lists `Keep` and running it prints `kept-across`. (The test removes it afterwards.)

### RUN-019: User commands from shortcuts.xml come with their shortcut
- Covers: -
- Channel: launch, files, keys, menu, ui
- Steps: Stop the app, write `home/Library/Application Support/NotepadMac/shortcuts.xml` with `<NotepadPlus><UserDefinedCommands><Command name="Hello" Ctrl="yes" Alt="yes" Shift="no" Key="72">echo hello-from-xml</Command></UserDefinedCommands></NotepadPlus>`, restart keeping the home; press `cmd+alt+h`.
- Expect: the Run menu has `Hello` with key `alt+cmd+h` (Windows Ctrl is Command); `savedRunCommands` now contains it; the key prints `hello-from-xml` in the Console.

## Console

### RUN-020: Show Console and Show NppExec Console toggle the same panel
- Covers: -
- Channel: menu, ui
- Steps: Run `Run|Show Console`, then `Run|Show Console`, then `Plugins|NppExec|Show NppExec Console` twice; after a Run command, hide the console and run another command.
- Expect: the `Console` window is visible, hidden, visible, hidden in turn (one panel for both menus); its earlier text is kept while hidden; a Run command shows it again.

### RUN-021: The Console is readable in dark appearance
- Covers: -
- Channel: prefs, snapshot, modal
- Steps: Switch the app to dark appearance (preference `appearanceMode` = 2, applied), run `printf 'XXXXXXXXXXXXXXXXXXXX\n'`, and snapshot the Console window; restore the preference.
- Expect: the snapshot's background is dark (mean luminance of the text area < 0.3) and the pixels of the text row include light ones (luminance > 0.6): the text is not black on dark.

## Validate shortcuts

### RUN-022: Validate shortcuts.xml is reachable by its Notepad++ id (known gap)
- Covers: IDM_EXECUTE_VALIDATE_SHORTCUTSXML
- Channel: mcp, menu
- Steps: Read `e2e_menu` for `IDM_EXECUTE_VALIDATE_SHORTCUTSXML`; `run_command` it by name and by id 49001; `list_commands` with query `Validate`.
- Expect: the id resolves to the Run menu's `Validate shortcuts` item and runs (FEATURES.md marks it implemented). Currently the item is labelled `Validate shortcuts` while the id's label is `Validate shortcuts.xml`, so no menu item carries the id and `run_command` answers `Command 49001 is not in this build's menus` - xfail(strict) BUG.

### RUN-023: Validate shortcuts reports no duplicates on a clean profile
- Covers: IDM_EXECUTE_VALIDATE_SHORTCUTSXML
- Channel: menu, modal, clipboard
- Steps: With `fresh_app`, queue `2` (Copy) and run `Run|Validate shortcuts`.
- Expect: one alert titled `Shortcuts` with buttons `OK`, `Copy`; its text is `<N> shortcuts, no duplicates.` with N > 50; Copy puts the same text on the clipboard. Currently it reports `1 duplicate(s): Toggle Full Screen Mode clashes with Toggle Full Screen Mode (f)` - the hidden alternate View item is counted as a clash - xfail(strict) BUG.

### RUN-024: Validate shortcuts names a real clash
- Covers: IDM_EXECUTE_VALIDATE_SHORTCUTSXML
- Channel: launch, files, menu, modal
- Steps: Before a restart, write a shortcuts.xml whose `UserDefinedCommands` give `One` and `Two` the same combination (`Ctrl="yes" Alt="yes" Key="75"`); restart keeping the home; run `Run|Validate shortcuts`.
- Expect: the report says `duplicate(s)` and has a line `Two clashes with One (k)`.

## NppExec

### RUN-025: The Execute NppExec Script dialog runs a temporary script
- Covers: -
- Channel: ui, menu
- Steps: Open `tmp/e.txt`; open the dialog (deferred `executeScriptDialog:`); read its controls; set the text view to `ECHO hello $(FILE_NAME)\nSET n ~ 6*7\nECHO n=$(n)\n/bin/echo out`; click `OK`.
- Expect: the window is titled `Execute NppExec Script` with a pop-up whose items start with `<temporary script>`, a text view, and buttons `Save…`, `Delete`, `Cancel`, `OK`; the menu item `Execute NppExec Script…` has key `f6`; after OK the dialog closes and the Console shows `hello e.txt`, `n=42`, `> /bin/echo out`, `out`, `<<< Process finished. (Exit code 0)` in that order; `Stop Running NppExec Script` is disabled once it has finished.

### RUN-026: Cancel in the dialog runs nothing; the dialog opens with the last script
- Covers: -
- Channel: ui
- Steps: Run a script `ECHO one-run` through the dialog; open the dialog again, read the text view, replace the text with `ECHO cancelled-run` and click `Cancel`; open it a third time.
- Expect: the second and third openings show `ECHO one-run`; `cancelled-run` never appears in the Console.

### RUN-027: Saved scripts: Save…, the pop-up, Delete, the menu and npes_saved.txt
- Covers: -
- Channel: ui, modal, files, menu
- Steps: In the dialog type `ECHO saved-one`, queue `{button: 1, field: "first"}` and click `Save…`; type `ECHO saved-two`, save as `second`; select `first` in the pop-up; then select `second` and click `Delete`; Cancel.
- Expect: after the saves `home/…/NotepadMac/npes_saved.txt` is `::first\nECHO saved-one\n::second\nECHO saved-two\n`, the pop-up lists both, the Plugins › NppExec menu ends with a separator and `first`, `second`; selecting `first` loads `ECHO saved-one` into the text view; after Delete the file holds only `first`, the pop-up is back on `<temporary script>`, and the menu lists only `first`.

### RUN-028: A saved script from the menu; Execute Previous and its keys
- Covers: -
- Channel: menu, keys, ui, files
- Steps: Write `npes_saved.txt` through the dialog with a script `greet` = `ECHO greeting $(FILE_NAME)`; run `Plugins|NppExec|greet`; then run `Plugins|NppExec|Execute Previous NppExec Script` and press `ctrl+f6`. Separately, with `fresh_app` (no previous script), run Execute Previous deferred (`performSelector` with `executePreviousScript:`).
- Expect: the Console gets `greeting <name>` three times; the Execute Previous item's key is `ctrl+f6`; with no previous script the Execute NppExec Script dialog opens instead (Cancel closes it).

### RUN-029: Script flow: SET, arithmetic, IF…GOTO, block IF, THEN
- Covers: -
- Channel: ui
- Steps: Run through the dialog: `SET n = 0`, `:again`, `SET n ~ $(n) + 1`, `ECHO pass $(n)`, `IF $(n) < 3 GOTO again`, `IF "$(n)" == "3"` / `ECHO three` / `ELSE IF $(n) == 4` / `ECHO four` / `ELSE` / `ECHO other` / `ENDIF`, `SET half ~ 7 / 2`, `ECHO half=$(half)`, `SET expr = a==b`, `IF "$(expr)" == "a==b" THEN` / `ECHO operator-inside` / `ENDIF`, `SET`.
- Expect: the Console shows `pass 1`, `pass 2`, `pass 3` and no `pass 4`; `three` and neither `four` nor `other`; `half=3.5`; `operator-inside`; the bare `SET` lists the script's variables sorted by name, among them `$(ARGC) = 0`, `$(EXPR) = a==b`, `$(HALF) = 3.5`, `$(N) = 3` in that order.

### RUN-030: Programs, their output variables, CD and the environment
- Covers: -
- Channel: ui, files
- Steps: Make `tmp/x/one.txt` and `tmp/x/two.txt`; open `tmp/doc.txt`; run a script: `/bin/pwd`, `CD <tmp>/x`, `ENV_SET GREETING = hello from env`, `/bin/echo "$(SYS.GREETING)"; exit 3`, `ECHO code=$(EXITCODE) out=$(OUTPUT)`, `ls *.txt`, `ECHO first=$(OUTPUT1) last=$(OUTPUTL)`, `CD`, `CD /no/such/dir`, `ECHO not-reached`.
- Expect: the first program prints `<tmp>` (a script starts in the document's folder); the Console shows `CD: <tmp>/x`, `code=3 out=hello from env`, `<<< Process finished. (Exit code 3)`, `first=one.txt last=two.txt`, `Current directory: <tmp>/x`, `- CD: no such folder: /no/such/dir`; `not-reached` is not shown (a failed command ends the script).

### RUN-031: Editor commands from a script
- Covers: -
- Channel: ui, files, mcp
- Steps: Write `tmp/y/one.txt` = `alpha\n`, `tmp/y/two.txt` = `beta\n`; with the script folder `CD <tmp>/y`, run `NPP_OPEN *.txt`, `NPP_SWITCH one.txt`, `ECHO line=$(CURRENT_LINESTR)`, `SCI_SENDMSG 2013`, `SEL_SETTEXT+ gamma\tdelta\n`, `NPP_SAVE`, `NPP_SAVEAS copy.txt`, `NPP_CLOSE copy.txt`, `NPP_CLOSE two.txt`, `NPP_SENDMSG 1234`, then in a second script with an untitled document in front `NPP_SAVE`.
- Expect: `line=alpha`; `one.txt` on disk is `gamma\tdelta\n` and `copy.txt` the same; afterwards neither `copy.txt` nor `two.txt` is open (`list_documents`); the Console shows `NPP_SENDMSG is not available on macOS`; the untitled `NPP_SAVE` prints `NPP_SAVE: new N - failed` and opens no Save panel (the modal log is empty).

### RUN-032: NPP_EXEC with arguments, EXIT, INPUTBOX and NPP_MENUCOMMAND
- Covers: -
- Channel: ui, modal, mcp
- Steps: Save scripts `t_greet` = `ECHO hi $(ARGV[1]) of $(ARGC)` and `t_inner` = `ECHO inner-start\nEXIT $(ARGV[1])\nECHO inner-not-reached`; with a document `abc` in front and the answer `{button: 1, field: "Hello World"}` queued, run: `INPUTBOX "Who?" : Hello`, `NPP_EXEC t_greet "$(INPUT[2])" two`, `ECHO argc now [$(ARGC)]`, `NPP_MENUCOMMAND Edit|Select All`, `NPP_MENUCOMMAND Edit|No Such Command`, then a second script `NPP_EXEC t_inner 0`, `ECHO outer-goes-on`, `NPP_EXEC t_inner 1`, `ECHO outer-not-reached`; a third script `INPUTBOX "Again?"`, `ECHO after-cancel` with the answer `2` queued.
- Expect: the INPUTBOX alert's message is `NppExec` and informative text `Who?` with field `Hello`; the Console shows `hi World of 2` and `argc now [0]`; the whole document `abc` is selected (`get_selection`); `NPP_MENUCOMMAND: Edit|No Such Command - no such command` ends the first script; `outer-goes-on` appears, `inner-start` twice, neither `inner-not-reached` nor `outer-not-reached`; the cancelled INPUTBOX prints `- INPUTBOX: cancelled` and not `after-cancel`.

### RUN-033: Script errors and a runaway loop are reported, not hung on
- Covers: -
- Channel: ui, mcp
- Steps: Run separately: `GOTO nowhere`; `IF abc` / `ECHO x` / `ENDIF`; `SET v ~ 2 + evil()`; `:top` / `GOTO top`.
- Expect: the Console shows `- GOTO: no label "nowhere"`, `- IF: no comparison in "abc"`, `- SET: cannot calculate "2 + evil()"` and `- the script was stopped: too many steps (an endless loop?)`; the runaway script ends within 20 s, the Stop item is disabled again, and the editor answers `get_document` meanwhile.

### RUN-034: Stop Running NppExec Script ends the program and the script
- Covers: -
- Channel: menu, ui
- Steps: Check `Plugins|NppExec|Stop Running NppExec Script` is disabled; run a script `ECHO start` / `/bin/sh -c "/bin/sleep 20; true"` / `ECHO after`; wait until Stop is enabled; run Stop and time it.
- Expect: Stop is enabled only while the script runs; within 5 s it is disabled again; the Console shows `- the script was stopped` and `<<< Process finished. (Exit code 15)` and no `after`; the `> /bin/sh -c …` line comes before `- the script was stopped` (observed today in the reverse order, the command line being appended asynchronously - check and mark xfail if still so).

### RUN-035: A new script stops the one running; CLS and NPP_CONSOLE
- Covers: -
- Channel: ui
- Steps: Start `/bin/sleep 20` / `ECHO old-after` from the dialog; at once run a second script `ECHO new-one`; then run `ECHO before-cls` / `CLS` / `ECHO after-cls`; then `NPP_CONSOLE 0` and later `NPP_CONSOLE 1`.
- Expect: within 5 s `new-one` is shown and `old-after` never; after the second script the Console text is exactly `after-cls\n`; `NPP_CONSOLE 0` hides the Console window and `NPP_CONSOLE 1` shows it without making it key.

### RUN-036: NppExec's own variables and quoting of document text
- Covers: -
- Channel: ui, clipboard, mcp, files
- Steps: Open `tmp/q.txt` containing `x; touch PWNED3` and select all; set the clipboard to `clip-text`; run `ECHO [$(#1)] [$(#0)]`, `ECHO clip=$(CLIPBOARD_TEXT) cwd=$(CWD)`, `ECHO cfg=$(PLUGINS_CONFIG_DIR)`, `SET sel = $(SELECTED_TEXT)`, `/bin/echo $(sel)`, `SET flags = a b`, `/usr/bin/printf '%s|' $(flags) tail`, `ECHO $(output)`.
- Expect: `$(#1)` is the first open document's path and `$(#0)` the app's executable; `clip=clip-text`, `cwd=<tmp>`; `cfg=` is the Application Support folder under the test home; the selected text is printed literally as one word and `PWNED3` is not created; the author's own `$(flags)` splits into words: `a|b|tail|`; variable names are case-insensitive (`$(output)` = `$(OUTPUT)`).
