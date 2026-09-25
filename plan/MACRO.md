# MACRO — Macro menu

Recording, playing back and keeping macros: Start/Stop Recording, Playback, Run a Macro Multiple
Times (a prompt for the count), Save Current Recorded Macro (a prompt for the name; the macro is
listed at the end of the Macro menu, kept in the home's macros.json and written into shortcuts.xml
under `<Macros>` as Notepad++ writes it), running a saved macro from the menu, macros that contain
menu commands (recorded by their Notepad++ id, type 2) and Find/Replace dialog actions (type 3),
and macros that come from a shortcuts.xml written by Windows Notepad++. Editing or deleting a saved
macro through the Shortcut Mapper belongs to SETTINGS. Menu commands that should be recorded are
invoked the way a click would invoke them, with `e2e_menu_invoke` (a menu path): `run_command`
sends the action without the menu's will/did-send notifications, so a command run that way is
recorded only as the Scintilla messages it happens to send. The home folder is
`.work/<worker>/home/Library/Application Support/NotepadMac`.

## Recording and playback

### MACRO-001: Record typed text and play it back
- Covers: IDM_MACRO_STARTRECORDINGMACRO, IDM_MACRO_STOPRECORDINGMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO
- Channel: mcp, keys
- Steps: New document; run Start Recording; type "ab" and press Return; run Stop Recording; open a new document "x", caret at the end, run Playback.
- Expect: the first document is "ab\n"; the second becomes "xab\n" (the typing replays at the caret, in whichever document is current).

### MACRO-002: Recorded caret movement replays relative to the caret
- Covers: IDM_MACRO_STARTRECORDINGMACRO, IDM_MACRO_STOPRECORDINGMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO
- Channel: mcp, keys
- Steps: Document "abc\ndef\nghi\n", caret at 1:1 (Cmd+Up); record: End, type ";", Down, Home; stop; run Playback twice.
- Expect: after recording "abc;\ndef\nghi\n" with the caret at 2:1; after the two playbacks "abc;\ndef;\nghi;\n".

### MACRO-003: Run a Macro Multiple Times runs it the number of times asked
- Covers: IDM_MACRO_RUNMULTIMACRODLG
- Channel: mcp, keys, modal
- Steps: Record the MACRO-002 macro; set the text "l1\nl2\nl3\nl4\nl5\n", caret at 1:1; queue {button 1, field "4"}; run Run a Macro Multiple Times; read the modal log.
- Expect: the prompt "Run how many times?" was shown; the text is "l1;\nl2;\nl3;\nl4;\nl5\n" (exactly four runs).

### MACRO-004: Cancelling or giving no count runs nothing extra
- Covers: IDM_MACRO_RUNMULTIMACRODLG
- Channel: mcp, modal
- Steps: With a macro that types "x" recorded, document "": queue Cancel and run the command; queue {1, "0"} and run it; queue {1, "abc"} and run it.
- Expect: after Cancel the text is ""; a count of 0 or a non-number runs the macro once (the port takes at least 1): "x" then "xx".

### MACRO-005: A playback is one undo step
- Covers: IDM_MACRO_PLAYBACKRECORDEDMACRO, IDM_MACRO_RUNMULTIMACRODLG
- Channel: mcp, keys, modal
- Steps: Record typing "hello " (then stop); new document "!"; caret at 1:1; Playback; Run Multiple Times with 3; press Cmd+Z once, then once more.
- Expect: "hello !" then "hello hello hello hello !"; the first Cmd+Z removes the three repetitions together, the second the first playback.

### MACRO-006: Playback with nothing recorded does nothing
- Covers: IDM_MACRO_PLAYBACKRECORDEDMACRO, IDM_MACRO_RUNMULTIMACRODLG
- Channel: mcp, modal
- Steps: Start the app fresh (fresh_app); new document "q"; run Playback; run Run Multiple Times with a queued {1, "3"}.
- Expect: the text stays "q"; no error. Both commands are disabled with nothing recorded (Notepad_plus::checkMacroState), so run_command reports them not run and no dialog comes up.

### MACRO-007: The Macro menu follows the recording state
- Covers: IDM_MACRO_STARTRECORDINGMACRO, IDM_MACRO_STOPRECORDINGMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO, IDM_MACRO_SAVECURRENTMACRO
- Channel: menu, mcp, ui
- Steps: fresh_app; read the enabled state of Start, Stop, Playback; start recording and read them and the toolbar's record button; type "a", stop, and read them again.
- Expect: as Notepad++ (Notepad_plus.cpp: Start enabled only when not recording, Stop only while recording, Playback only with a macro and not recording): before: Start on, Stop off, Playback off; while recording: Start off, Stop on, Playback off, the toolbar's record button shown active; after: Start on, Stop off, Playback on.

### MACRO-008: Recording a new macro replaces the previous one
- Covers: IDM_MACRO_STARTRECORDINGMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO
- Channel: mcp, keys
- Steps: Record typing "1"; record again typing "2"; in a new document run Playback.
- Expect: the new document is "2".

## What goes into a macro

### MACRO-009: A menu command is recorded by its id and replays as the command
- Covers: IDM_MACRO_STARTRECORDINGMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO, IDM_EDIT_UPPERCASE
- Channel: menu, keys, mcp
- Steps: Document "abc\n"; start recording; Cmd+A; invoke Edit|Convert Case to|UPPERCASE with e2e_menu_invoke; Down; type "x"; stop. New document "def\nghi\n", caret at 1:1; Playback.
- Expect: the first document is "ABC\nx"; the playback gives "DEF\nGHI\nx" (the conversion was replayed on the new text, not the old text pasted back); the recorded macro, once saved, has an Action type="2" wParam="42016".

### MACRO-010: A Replace All from the Replace dialog is recorded and replays
- Covers: IDM_MACRO_STARTRECORDINGMACRO, IDM_MACRO_STOPRECORDINGMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO
- Channel: mcp, ui
- Steps: Document "cat cat\n"; start recording; open Replace (IDM_SEARCH_REPLACE); set Find what "cat" and Replace with "dog" (e2e_act set_value on the two combo boxes); click "Replace All"; close the dialog; stop. New document "a cat\n"; Playback.
- Expect: the first document is "dog dog\n"; the playback turns the new one into "a dog\n".

### MACRO-011: A Find Next from the dialog is recorded and replays as a search
- Covers: IDM_MACRO_STARTRECORDINGMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO
- Channel: mcp, ui, keys
- Steps: Document "x foo y foo z foo\n", caret at 1:1; start recording; Find dialog (IDM_SEARCH_FIND), Find what "foo", click "Find Next", close it; type "!"; stop. Playback twice.
- Expect: after recording "x ! y foo z foo\n" (the found "foo" was replaced by typing); after the two playbacks "x ! y ! z !\n".

### MACRO-012: Auto-close and auto-completion are left out of recording and playback
- Covers: IDM_MACRO_STARTRECORDINGMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO
- Channel: keys, prefs, mcp
- Steps: autoInsertParenthesis on; document "alphabet\n" (auto-completion on input on); start recording; on line 2 type "f(al"; stop; read SCI_AUTOCACTIVE; new document; Playback; restore.
- Expect: while recording no ")" is added and no completion list appears: "alphabet\nf(al"; the playback types exactly "f(al" with no ")" and no list.

## Saving and running saved macros

### MACRO-013: Save Current Recorded Macro lists it in the Macro menu and writes it to disk
- Covers: IDM_MACRO_SAVECURRENTMACRO
- Channel: mcp, modal, menu, files
- Steps: Record typing "a" then "b"; queue {1, "MyMac"}; run Save Current Recorded Macro; read the Macro menu tree, macros.json and shortcuts.xml in the home.
- Expect: the prompt "Save macro as" with default "macro"; the Macro menu ends with a separator and "MyMac"; macros.json has a key "MyMac"; shortcuts.xml has <Macros><Macro name="MyMac" Ctrl="no" Alt="no" Shift="no" Key="0"> whose Actions are type="1" message="2170" sParam="a" and sParam="b" with lParam="0".

### MACRO-014: A saved macro runs from the Macro menu
- Covers: IDM_MACRO_SAVECURRENTMACRO
- Channel: menu, mcp
- Steps: Record the MACRO-010 Replace All macro and save it as "Cat2Dog"; record something else afterwards (typing "z"); in a new document "my cat\n" invoke Macro|Cat2Dog.
- Expect: the document becomes "my dog\n" (the saved macro, not the latest recording, is played).

### MACRO-015: Saved macros survive a restart
- Covers: IDM_MACRO_SAVECURRENTMACRO, IDM_MACRO_PLAYBACKRECORDEDMACRO
- Channel: launch, menu, files
- Steps: Save the "Cat2Dog" macro; restart the app keeping home and preferences (app.restart()); read the Macro menu; invoke Macro|Cat2Dog in "my cat\n"; run Playback in a new document "q".
- Expect: "Cat2Dog" is still listed and replaces to "my dog\n"; the unsaved "current" macro did not survive: Playback leaves "q" unchanged.

### MACRO-016: Cancelling the save, or saving with nothing recorded, saves nothing
- Covers: IDM_MACRO_SAVECURRENTMACRO
- Channel: mcp, modal, files
- Steps: fresh_app; run Save Current Recorded Macro with {1, "Empty"} before anything is recorded; record typing "a"; run it again and answer Cancel; read the Macro menu and the home.
- Expect: no macro entry follows the five fixed items; macros.json has no "Empty" (or does not exist); shortcuts.xml has no <Macro>.

### MACRO-017: Saving under an existing name replaces that macro
- Covers: IDM_MACRO_SAVECURRENTMACRO
- Channel: mcp, modal, menu
- Steps: Record typing "1", save as "M"; record typing "2", save as "M"; invoke Macro|M in a new document.
- Expect: the menu lists "M" once; the document becomes "2".

### MACRO-018: A macro from a Windows shortcuts.xml is brought in with its key
- Covers: IDM_MACRO_PLAYBACKRECORDEDMACRO
- Channel: files, launch, menu, keys
- Steps: Stop the app; write shortcuts.xml into the home with <Macros><Macro name="From Windows" Ctrl="yes" Alt="yes" Shift="no" Key="77"> (Cmd+Alt+M; if the menus already use it, any combination they do not use) holding a type="1" message="2170" sParam="hi" action, a type="0" message="2013" (select all) action and a type="2" message="0" wParam="42016" lParam="0" action; start keeping the home; new document; invoke Macro|From Windows; then in another new document press Cmd+Alt+M.
- Expect: the Macro menu lists "From Windows" with the key "alt+cmd+m" (Windows Ctrl is Command); each run gives "HI" (typed, selected, uppercased by the menu command); macros.json now also holds it.

### MACRO-019: Several saved macros are listed in name order
- Covers: IDM_MACRO_SAVECURRENTMACRO
- Channel: mcp, modal, menu
- Steps: Save three recordings as "b macro", "A macro" and "c macro".
- Expect: after the separator the Macro menu lists "A macro", "b macro", "c macro" (the order the port sorts names in), each playing its own recording.
