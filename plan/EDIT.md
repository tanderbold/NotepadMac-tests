# EDIT — Edit menu

The whole Edit menu of NotepadMac as `plan/commands.tsv` lists it (104 commands): undo/redo, the
clipboard, Select All, Begin/End Select, Insert date/time, Copy to Clipboard (paths and names),
indentation, Convert Case, Line Operations (duplicate, remove duplicates, split, join, move, blank
lines, reverse, randomize and every sort Notepad++ has), Comment/Uncomment per language, the
Auto-Completion commands, EOL Conversion, Blank Operations, Paste Special (HTML, RTF, binary), On
Selection (open file, reveal, redact, search on internet), Multi-select, Column Mode/Column Editor,
the Character Panel, Clipboard History and the read-only commands. Commands are run the way a user
runs them: `run_command` by `IDM_*` name (the menu item's own action), key equivalents through
`e2e_keys`, and the few prompts the port shows answered through `e2e_answers`. Out of scope here:
behaviour while typing (TYPING), macros (MACRO), the Find/Replace dialog (SEARCH), the Preferences
pages themselves (SETTINGS) and Paste Image as Text / Recognize Text in File (MACEXTRA). Unless a
case says otherwise a document is created with `app.new(text, language)`, positions are 1-based
line/column as `go_to` takes them, and "the text" is `get_document`'s text. Where the port and
Windows Notepad++ differ, the expectation is Notepad++'s (`PowerEditor/src`), and a failing case is
marked xfail with the defect in its reason and reported as an issue in the NotepadMac repository.

## Undo, redo and the clipboard

### EDIT-001: Undo and Redo revert and reapply a typed edit
- Covers: IDM_EDIT_UNDO, IDM_EDIT_REDO
- Channel: mcp, keys
- Steps: New document "abc"; put the caret at the end and type "d". Run IDM_EDIT_UNDO, then IDM_EDIT_REDO; then the same with Cmd+Z and Shift+Cmd+Z.
- Expect: after typing the text is "abcd"; after Undo "abc" and the document is still modified; after Redo "abcd"; the key equivalents give the same two results; the menu items show "cmd+z" and "shift+cmd+z" as their keys.

### EDIT-002: Undo and Redo are enabled only when there is something to undo or redo
- Covers: IDM_EDIT_UNDO, IDM_EDIT_REDO
- Channel: mcp, menu
- Steps: In a fresh empty document read the enabled state of both items; type "x"; read them; Undo; read them; type "y"; read them.
- Expect: fresh: Undo disabled, Redo disabled; after typing: Undo enabled, Redo disabled; after Undo: Undo disabled, Redo enabled; after typing again: Redo disabled (the redo history is dropped).

### EDIT-003: One Undo takes back a whole-document command
- Covers: IDM_EDIT_UNDO, IDM_EDIT_REDO, IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING, IDM_EDIT_UPPERCASE
- Channel: mcp, keys
- Steps: For each of Sort Lines Lexicographically Ascending on "c\nb\na\n" (no selection) and UPPERCASE on "one two" (all selected): run the command, press Cmd+Z once, then Shift+Cmd+Z once.
- Expect: one Cmd+Z restores the original text exactly; one Shift+Cmd+Z brings back "a\nb\nc\n" / "ONE TWO".

### EDIT-004: Undoing back to the saved state clears the modified mark
- Covers: IDM_EDIT_UNDO
- Channel: mcp, keys, files
- Steps: Write "saved\n" to tmp/u.txt and open it; type "X" at the start; press Cmd+Z.
- Expect: after typing `get_document` reports modified=true; after Undo the text is "saved\n" and modified=false; the file on disk is unchanged.

### EDIT-005: Copy puts exactly the selection on the clipboard
- Covers: IDM_EDIT_COPY
- Channel: mcp, keys, clipboard
- Steps: New document "héllo wörld 👍\r\nline two"; select from 1:1 to 2:5 and run IDM_EDIT_COPY; then select "wörld" and press Cmd+C.
- Expect: the clipboard holds "héllo wörld 👍\r\nline" after the command (line ending kept as in the document) and "wörld" after Cmd+C; the document text is unchanged and the selection stays.

### EDIT-006: Cut removes the selection and puts it on the clipboard
- Covers: IDM_EDIT_CUT, IDM_EDIT_UNDO
- Channel: mcp, keys, clipboard
- Steps: New document "cut this text"; select "this " (1:5-1:10) and run IDM_EDIT_CUT; press Cmd+Z; select "text" and press Cmd+X.
- Expect: after the command the text is "cut text" and the clipboard "this "; after Undo "cut this text"; after Cmd+X the text is "cut this " and the clipboard "text".

### EDIT-007: Copy and Cut with nothing selected take the whole line
- Covers: IDM_EDIT_COPY, IDM_EDIT_CUT
- Channel: mcp, keys, clipboard, prefs
- Steps: With lineCopyCutWithoutSelection at its default (on), new document "line1\nline2\nlast"; caret at 1:3, Cmd+C; caret at 2:2, Cmd+X; caret on "last" (no line end), Cmd+C.
- Expect: first clipboard "line1\n", text unchanged; after Cmd+X clipboard "line2\n" and text "line1\nlast"; copying the last line gives "last" plus the document's line ending as Scintilla's COPYALLOWLINE does ("last\n").

### EDIT-008: With line copy turned off, Copy and Cut with no selection do nothing
- Covers: IDM_EDIT_COPY, IDM_EDIT_CUT
- Channel: mcp, clipboard, prefs
- Steps: Set lineCopyCutWithoutSelection=false; put "keep" on the clipboard; new document "line1\nline2\n", caret at 1:3; run IDM_EDIT_COPY then IDM_EDIT_CUT; restore the preference.
- Expect: the clipboard still holds "keep"; the text is unchanged.

### EDIT-009: Paste inserts at the caret and replaces a selection
- Covers: IDM_EDIT_PASTE
- Channel: mcp, keys, clipboard
- Steps: Clipboard "XY"; new document "abc"; caret at 1:2, run IDM_EDIT_PASTE; select "c" and press Cmd+V.
- Expect: after the command the text is "aXYbc" with the caret at 1:4; after Cmd+V "aXYbXY"; the Paste item is enabled while the clipboard has text.

### EDIT-010: Paste is disabled with an empty clipboard and in a read-only document
- Covers: IDM_EDIT_PASTE, IDM_EDIT_TOGGLEREADONLY
- Channel: mcp, menu, clipboard
- Steps: Empty the clipboard (set ""), new document "abc": read Paste's enabled state; put "z" on the clipboard: read it; make the document read-only (IDM_EDIT_TOGGLEREADONLY) and read it; run IDM_EDIT_PASTE anyway; clear read-only.
- Expect: disabled, enabled, disabled; run_command reports ran=false for the disabled command and the text stays "abc".

### EDIT-011: Pasted line endings follow the document's end-of-line format
- Covers: IDM_EDIT_PASTE
- Channel: mcp, files, clipboard
- Steps: Write "a\r\nb\r\n" to tmp/crlf.txt and open it (EOL reported CRLF); put "x\ny\n" on the clipboard; caret at 3:1; run IDM_EDIT_PASTE.
- Expect: the text is "a\r\nb\r\nx\r\ny\r\n"; the document still reports eol CRLF.

### EDIT-012: Pasting code into an empty document detects its language
- Covers: IDM_EDIT_PASTE
- Channel: mcp, clipboard
- Steps: Clipboard "#!/usr/bin/env python3\nprint('hi')\n"; new empty document (plain text); run IDM_EDIT_PASTE; then paste the same into a non-empty plain document "x\n".
- Expect: the empty document now has language "python" (the shebang declares it, no question is asked, the modal log is empty); the non-empty document stays "normal".

### EDIT-013: Delete removes the selection, or the character after the caret
- Covers: IDM_EDIT_DELETE
- Channel: mcp
- Steps: New document "delete me"; select "delete " and run IDM_EDIT_DELETE; put the caret at 1:1 and run it again; new document "é👍x", caret at 1:2, run it.
- Expect: "me"; then "e"; in the unicode document the whole emoji goes ("éx"), never half a character; the clipboard is untouched by Delete.

### EDIT-014: Select All selects the whole document
- Covers: IDM_EDIT_SELECTALL
- Channel: mcp, keys
- Steps: New document "one\ntwo 日本\n"; run IDM_EDIT_SELECTALL; collapse the selection; press Cmd+A; also on an empty document.
- Expect: the selection runs from 1:1 to the end (selection text equals the document text, byte length equals `bytes`); the same after Cmd+A; on an empty document the command runs and the selection is empty.

### EDIT-015: Copy works in a read-only document but Cut, Paste and Delete do not change it
- Covers: IDM_EDIT_COPY, IDM_EDIT_CUT, IDM_EDIT_PASTE, IDM_EDIT_DELETE, IDM_EDIT_TOGGLEREADONLY
- Channel: mcp, keys, clipboard
- Steps: New document "locked text", make it read-only; select "locked"; press Cmd+C; press Cmd+X; put "Z" on the clipboard and press Cmd+V; run IDM_EDIT_DELETE; clear read-only.
- Expect: the clipboard held "locked" after Cmd+C; the text is "locked text" after every other step.

## Begin/End Select

### EDIT-016: Begin/End Select anchors, then selects to the caret
- Covers: IDM_EDIT_BEGINENDSELECT
- Channel: mcp
- Steps: New document "0123456789\n"; caret at 1:3, run IDM_EDIT_BEGINENDSELECT; caret at 1:7, run it again. Repeat backwards: anchor at 1:8, end at 1:2.
- Expect: after the first run nothing is selected; after the second the selection is "2345" (1:3-1:7); backwards the selection is "123456" with the caret at 1:2 (anchor 1:8).

### EDIT-017: Begin/End Select in Column Mode makes a rectangle
- Covers: IDM_EDIT_BEGINENDSELECT_COLUMNMODE
- Channel: mcp
- Steps: New document "0123456789\nabcdefghij\n"; caret at 1:3, run IDM_EDIT_BEGINENDSELECT_COLUMNMODE; caret at 2:6, run it again; read the selections with SCI_GETSELECTIONNSTART/END.
- Expect: `get_selection` reports rectangular=true with 2 selections; they cover "234" on line 1 and "cde" on line 2; typing "#" then gives "01#56789\nab#fghij\n".

### EDIT-018: Begin/End Select shows that it has started
- Covers: IDM_EDIT_BEGINENDSELECT, IDM_EDIT_BEGINENDSELECT_COLUMNMODE
- Channel: menu, mcp
- Steps: Run IDM_EDIT_BEGINENDSELECT once and read both items' state; run it a second time and read again.
- Expect: as Notepad++ (NppCommands.cpp): while started, Begin/End Select is checked and Begin/End Select in Column Mode is disabled; after the second run it is unchecked and the other one enabled again.

## Insert date and time

### EDIT-019: Insert Date Time (short) and (long)
- Covers: IDM_EDIT_INSERT_DATETIME_SHORT, IDM_EDIT_INSERT_DATETIME_LONG
- Channel: mcp
- Steps: For each of the two commands: new document "[]", caret at 1:2, run it.
- Expect: the text is "[" + stamp + "]"; the stamp is the time without seconds (hh:mm, as the system formats a short time) followed by a space and the date; the short date contains today's day and year in digits, the long date today's month name in English and the year; the caret is right after the stamp.

### EDIT-020: Reverse date/time order puts the date first
- Covers: IDM_EDIT_INSERT_DATETIME_SHORT, IDM_EDIT_INSERT_DATETIME_LONG
- Channel: mcp, prefs
- Steps: Set reverseDateTimeOrder=true; insert a short and a long stamp into empty documents; restore the preference.
- Expect: each stamp starts with the date and ends with the time (hh:mm at the end).

### EDIT-021: Insert Date Time (customized) uses the format from Preferences
- Covers: IDM_EDIT_INSERT_DATETIME_CUSTOMIZED
- Channel: mcp, prefs
- Steps: With the default customDateFormat run the command in an empty document; set customDateFormat to "yyyy/MM/dd" and run it in another; set it to "HH:mm" and run it in a third; restore.
- Expect: default: matches ^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$ with today's date; "yyyy/MM/dd": exactly today's date as 2026/09/23-style text; "HH:mm": ^\d{2}:\d{2}$; no dialog is shown (modal log empty).

### EDIT-022: An inserted stamp replaces the selection in one undo step
- Covers: IDM_EDIT_INSERT_DATETIME_CUSTOMIZED, IDM_EDIT_UNDO
- Channel: mcp, keys
- Steps: customDateFormat "yyyy"; new document "year: XXXX."; select "XXXX" and run the command; press Cmd+Z once.
- Expect: "year: 2026." (the current year); after one Undo "year: XXXX.".

## Copy to Clipboard: paths and names

### EDIT-023: Copy full path, file name and folder of a saved file
- Covers: IDM_EDIT_FULLPATHTOCLIP, IDM_EDIT_FILENAMETOCLIP, IDM_EDIT_CURRENTDIRTOCLIP
- Channel: mcp, clipboard, files
- Steps: Write tmp/dir with space/Ünï file.txt and open it; for each of the three commands, set the clipboard to "zzz" and run it.
- Expect: full path = the file's absolute path; file name = "Ünï file.txt"; folder = tmp/"dir with space" without a trailing slash.

### EDIT-024: Copy path and name of an untitled document
- Covers: IDM_EDIT_FULLPATHTOCLIP, IDM_EDIT_FILENAMETOCLIP, IDM_EDIT_CURRENTDIRTOCLIP
- Channel: mcp, clipboard
- Steps: With only the untitled "new 1" open, set the clipboard to "zzz" and run each of the three commands.
- Expect: as Notepad++ (the buffer's full path name of an untitled document is its tab name): full path "new 1", file name "new 1", folder "" (empty string, the "zzz" is replaced).

### EDIT-025: Copy All Filenames and Copy All File Paths list every tab in order
- Covers: IDM_EDIT_COPY_ALL_NAMES, IDM_EDIT_COPY_ALL_PATHS
- Channel: mcp, clipboard, files
- Steps: Open tmp/a.txt and tmp/b.md next to the untitled "new 1"; run IDM_EDIT_COPY_ALL_NAMES, then IDM_EDIT_COPY_ALL_PATHS.
- Expect: names: "new 1\na.txt\nb.md" in tab order; paths: the two absolute paths in tab order, with the untitled document given by its name "new 1" as Notepad++ does; no trailing newline.

## Indent

### EDIT-026: Increase and Decrease Line Indent shift whole lines
- Covers: IDM_EDIT_INS_TAB, IDM_EDIT_RMV_TAB
- Channel: mcp, prefs
- Steps: With default indentation (tabs, width 4) new document "a\n  b\nc\n"; select from 1:1 to 2:2 and run IDM_EDIT_INS_TAB; run IDM_EDIT_RMV_TAB twice; then set useSpaces=true, tabWidth=2 (applied), run IDM_EDIT_INS_TAB with the caret on line 3; restore.
- Expect: after increase "\ta\n\t  b\nc\n" (line 3 untouched, selected text is not replaced by a tab); after two decreases "a\nb\nc\n"; with spaces/width 2 line 3 becomes "  c".

### EDIT-027: Indent keys Cmd+] and Cmd+[ and indenting a line in the middle of text
- Covers: IDM_EDIT_INS_TAB, IDM_EDIT_RMV_TAB
- Channel: keys, mcp
- Steps: New document "x = 1\n"; caret at 1:3 (inside the line); press Cmd+], then Cmd+[; then Cmd+[ once more on the unindented line.
- Expect: "\tx = 1\n" with the caret still before "= 1"; back to "x = 1\n"; the extra decrease leaves it unchanged.

## Convert Case

### EDIT-028: Each case conversion transforms the selected text
- Covers: IDM_EDIT_UPPERCASE, IDM_EDIT_LOWERCASE, IDM_EDIT_PROPERCASE_FORCE, IDM_EDIT_PROPERCASE_BLEND, IDM_EDIT_SENTENCECASE_FORCE, IDM_EDIT_SENTENCECASE_BLEND, IDM_EDIT_INVERTCASE
- Channel: mcp
- Steps: For each (command, input, output): new document with the input, select all, run the command. UPPERCASE "hello Wörld é" → "HELLO WÖRLD É"; lowercase "HeLLo WÖRLD" → "hello wörld"; Proper Case "hELLO wORLD don't 3rd" → "Hello World Don't 3rd"; Proper Case (blend) "hELLO wORLD" → "HELLO WORLD"; Sentence case "hi THERE. bye! ok? i think so" → "Hi there. Bye! Ok? I think so"; Sentence case (blend) "hi THERE. bye" → "Hi THERE. Bye"; iNVERT cASE "AbC dÉ" → "aBc Dé".
- Expect: the text equals the output; the converted text stays selected (selection length = its UTF-8 length).

### EDIT-029: Random case keeps the letters and scrambles their case
- Covers: IDM_EDIT_RANDOMCASE
- Channel: mcp
- Steps: New document with 64 lowercase letters "abcdefgh" x8; select all; run IDM_EDIT_RANDOMCASE; repeat up to 5 times until the text differs from all-lowercase.
- Expect: the lowercased result equals the input, the length is the same, and at least one run produced some uppercase letters (with 64 letters an unchanged result every time is practically impossible).

### EDIT-030: Convert case with nothing selected leaves the document alone
- Covers: IDM_EDIT_UPPERCASE, IDM_EDIT_LOWERCASE
- Channel: mcp
- Steps: New document "hello world"; caret at 1:3, no selection; run IDM_EDIT_UPPERCASE, then IDM_EDIT_LOWERCASE on "HELLO".
- Expect: as Notepad++ (ScintillaEditView::convertSelectedTextTo converts only a non-empty selection): the texts are unchanged and the document is not modified.

### EDIT-031: Convert case in a rectangular or multiple selection converts only what is selected
- Covers: IDM_EDIT_UPPERCASE, IDM_EDIT_INVERTCASE
- Channel: mcp, keys
- Steps: New document "abcd\nabcd\n"; make a rectangle over columns 2-3 of both lines (Begin/End Select in Column Mode from 1:2 to 2:4); run IDM_EDIT_UPPERCASE. Then new document "ab ab ab", multi-select all "ab" (IDM_EDIT_MULTISELECTALL on the first word) and run IDM_EDIT_INVERTCASE.
- Expect: "aBCd\naBCd\n" (outside the rectangle nothing changes); "AB AB AB"; the selections are kept.

### EDIT-032: Case conversion of non-ASCII text and text that changes length
- Covers: IDM_EDIT_UPPERCASE, IDM_EDIT_LOWERCASE
- Channel: mcp
- Steps: New document "straße ǆ ﬁ ΣΑΣ x"; select "straße ǆ ﬁ" and run UPPERCASE; select "ΣΑΣ" and run lowercase.
- Expect: the selected part is converted and the rest ("ΣΑΣ x" in the first step) is untouched; the document stays valid UTF-8 and the selection covers exactly the converted text whatever its new length.

## Line Operations: duplicate, remove, split, join, move, blank lines

### EDIT-033: Duplicate Current Line
- Covers: IDM_EDIT_DUP_LINE
- Channel: mcp, keys
- Steps: New document "one\ntwo"; caret at 1:2, run IDM_EDIT_DUP_LINE; caret on the last line "two" (no line end), press Cmd+D.
- Expect: "one\none\ntwo" with the caret still on line 1 at column 2; then "one\none\ntwo\ntwo"; the menu item shows "cmd+d".

### EDIT-034: Remove Duplicate Lines keeps the first of each
- Covers: IDM_EDIT_REMOVE_ANY_DUP_LINES
- Channel: mcp
- Steps: Documents "a\nb\na\nc\nb\n", "A\na\n" and "x\r\ny\r\nx\r\n" (opened from a CRLF file); run the command on each with no selection.
- Expect: "a\nb\nc\n"; "A\na\n" (comparison is case-sensitive); "x\r\ny\r\n" (CRLF kept).

### EDIT-035: Remove Consecutive Duplicate Lines collapses only neighbours
- Covers: IDM_EDIT_REMOVE_CONSECUTIVE_DUP_LINES
- Channel: mcp
- Steps: New document "a\na\nb\na\na\na\n"; run the command.
- Expect: "a\nb\na\n".

### EDIT-036: Line removals act only on the selected lines
- Covers: IDM_EDIT_REMOVE_ANY_DUP_LINES, IDM_EDIT_REMOVEEMPTYLINES
- Channel: mcp
- Steps: New document "a\nb\nb\na\nb\n"; select from 2:1 to 4:2 and run IDM_EDIT_REMOVE_ANY_DUP_LINES. New document "x\n\ny\n\nz\n"; select from 1:1 to 3:2 and run IDM_EDIT_REMOVEEMPTYLINES.
- Expect: duplicates are removed only within lines 2-4: "a\nb\na\nb\n" (line 1's "a" and line 5's "b" are outside the selection and stay); only the empty line inside the selection goes: "x\ny\n\nz\n".

### EDIT-037: Split Lines breaks long lines at the edge column
- Covers: IDM_EDIT_SPLIT_LINES
- Channel: mcp, prefs
- Steps: Set edgeMode=1 and edgeColumns="8" (applied); new document "aaa bbb ccc ddd eee fff\nshort\n"; select all; run the command; restore the preferences.
- Expect: "aaa bbb\nccc ddd\neee fff\nshort\n"; no produced line is longer than 8 characters; the short line is untouched.

### EDIT-038: Join Lines joins with single spaces
- Covers: IDM_EDIT_JOIN_LINES
- Channel: mcp
- Steps: New document "a\nb\nc"; select from 1:1 to 2:2 and run the command; then with no selection on "a\nb\nc\n"; then on a one-line document "x\n".
- Expect: "a b\nc"; "a b c\n" (the last line ending is kept); "x\n" unchanged.

### EDIT-039: Move Up and Move Down Current Line
- Covers: IDM_EDIT_LINE_UP, IDM_EDIT_LINE_DOWN
- Channel: mcp
- Steps: New document "line1\nline2\nline3\n"; caret at 3:2, run IDM_EDIT_LINE_UP; run IDM_EDIT_LINE_DOWN; caret at 1:1 run IDM_EDIT_LINE_UP; select lines 1-2 (1:1-2:3) and run IDM_EDIT_LINE_DOWN.
- Expect: "line1\nline3\nline2\n" with the caret on line 2 in "line3"; back to "line1\nline2\nline3\n"; moving the first line up changes nothing; the selected block moves as a whole: "line3\nline1\nline2\n" with the two lines still selected.

### EDIT-040: Remove Empty Lines and Remove Empty Lines (Containing Blank characters)
- Covers: IDM_EDIT_REMOVEEMPTYLINES, IDM_EDIT_REMOVEEMPTYLINESWITHBLANK
- Channel: mcp
- Steps: Input "a\n\n   \n\t\nb\n\n" for each command, no selection.
- Expect: Remove Empty Lines: "a\n   \n\t\nb\n" (only truly empty lines go); with blank characters: "a\nb\n".

### EDIT-041: Insert Blank Line Above and Below Current
- Covers: IDM_EDIT_BLANKLINEABOVECURRENT, IDM_EDIT_BLANKLINEBELOWCURRENT
- Channel: mcp, files
- Steps: New document "x\ny\n", caret at 2:1, run Above; caret at 1:1 run Below. Then open tmp/crlf.txt ("a\r\nb\r\n") and run Below on line 1.
- Expect: "x\n\ny\n" with the caret on the new empty line 2; then "x\n\n\ny\n" with the caret on line 2; in the CRLF file "a\r\n\r\nb\r\n" (the inserted line uses the document's EOL).

## Line Operations: reverse, randomize, sort

### EDIT-042: Reverse Line Order
- Covers: IDM_EDIT_SORTLINES_REVERSE_ORDER
- Channel: mcp
- Steps: "a\nb\nc\n" with no selection; "1\n2\n3\n4\n" with lines 2-3 selected; "x\ny" (no final line end).
- Expect: "c\nb\na\n"; "1\n3\n2\n4\n"; "y\nx" (the file still has no final line end).

### EDIT-043: Randomize Line Order keeps every line
- Covers: IDM_EDIT_SORTLINES_RANDOMLY
- Channel: mcp
- Steps: New document with lines "l01".."l20" each ending "\n"; run the command up to 5 times until the order changes.
- Expect: every run gives a permutation of the 20 lines (same multiset, each line still ending "\n"); at least one run changed the order.

### EDIT-044: Each sort command orders the lines as Notepad++ does
- Covers: IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING, IDM_EDIT_SORTLINES_LEXICOGRAPHIC_DESCENDING, IDM_EDIT_SORTLINES_LEXICO_CASE_INSENS_ASCENDING, IDM_EDIT_SORTLINES_LEXICO_CASE_INSENS_DESCENDING, IDM_EDIT_SORTLINES_LOCALE_ASCENDING, IDM_EDIT_SORTLINES_LOCALE_DESCENDING, IDM_EDIT_SORTLINES_INTEGER_ASCENDING, IDM_EDIT_SORTLINES_INTEGER_DESCENDING, IDM_EDIT_SORTLINES_DECIMALCOMMA_ASCENDING, IDM_EDIT_SORTLINES_DECIMALCOMMA_DESCENDING, IDM_EDIT_SORTLINES_DECIMALDOT_ASCENDING, IDM_EDIT_SORTLINES_DECIMALDOT_DESCENDING, IDM_EDIT_SORTLINES_LENGTH_ASCENDING, IDM_EDIT_SORTLINES_LENGTH_DESCENDING
- Channel: mcp
- Steps: For each command, a document with the given input and no selection: Lexicographic asc "B\na\nb\nA\n" → "A\nB\na\nb\n", desc → "b\na\nB\nA\n"; ignoring case asc "B\na\nC\n" → "a\nB\nC\n", desc → "C\nB\na\n"; locale asc "é\nz\ne\nf\n" → "e\né\nf\nz\n", desc → "z\nf\né\ne\n"; integers asc "10\n9\n-3\n2\n" → "-3\n2\n9\n10\n", desc → "10\n9\n2\n-3\n"; decimals comma asc "1,5\n-2,25\n10\n" → "-2,25\n1,5\n10\n", desc reversed; decimals dot asc "1.5\n1.25\n-0.5\n" → "-0.5\n1.25\n1.5\n", desc reversed; length asc "ccc\na\nbb\n" → "a\nbb\nccc\n", desc → "ccc\nbb\na\n".
- Expect: the text equals the listed output; no dialog is shown.

### EDIT-045: Integer sort compares digit runs as numbers (natural order)
- Covers: IDM_EDIT_SORTLINES_INTEGER_ASCENDING, IDM_EDIT_SORTLINES_INTEGER_DESCENDING
- Channel: mcp
- Steps: Sort "item10\nitem9\nitem2\n" ascending; "x007\nx7\nx07\n" ascending; "a100000000000000000000\na99\n" ascending; "item10\nitem9\nitem2\n" descending.
- Expect: "item2\nitem9\nitem10\n"; "x007\nx07\nx7\n" (more leading zeros first on a tie, as Sorters.h); "a99\na100000000000000000000\n" (numbers longer than any integer type); "item10\nitem9\nitem2\n".

### EDIT-046: A decimal sort refuses a line it cannot read and names it
- Covers: IDM_EDIT_SORTLINES_DECIMALDOT_ASCENDING, IDM_EDIT_SORTLINES_DECIMALCOMMA_ASCENDING
- Channel: mcp, modal
- Steps: Queue an OK answer; sort "2.5\n-\n1.5\n" with Decimals (Dot) Ascending and read the modal log; queue OK and sort "3,5\n1,5\n-\n" with Decimals (Comma) Ascending; sort "2.5\nplain\n1.5\n" with Dot ascending, and again descending.
- Expect: an alert "Sorting Error" with "Unable to perform numeric sorting due to line 2." and the text unchanged; for the comma sort the alert names line 3 and the text is unchanged; a line with no number at all is not an error: "plain\n1.5\n2.5\n" ascending and "2.5\n1.5\nplain\n" descending, with no alert.

### EDIT-047: Sorting is stable and keeps line endings
- Covers: IDM_EDIT_SORTLINES_LENGTH_DESCENDING, IDM_EDIT_SORTLINES_LEXICO_CASE_INSENS_ASCENDING, IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING
- Channel: mcp, files
- Steps: Length descending on "b 1\na 1\nc 0\n"; case-insensitive ascending on "b\nA\na\nB\n"; lexicographic ascending on a CRLF file "b\r\na\r\nc" (no final EOL) and on "A\rC\rB\r" (CR only).
- Expect: "b 1\na 1\nc 0\n" (equal lengths keep their order); "A\na\nb\nB\n" (equal-ignoring-case lines keep their order); "a\r\nb\r\nc" (still no final EOL); "A\rB\rC\r".

### EDIT-048: Sorting only the selected lines
- Covers: IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING, IDM_EDIT_SORTLINES_REVERSE_ORDER
- Channel: mcp
- Steps: New document "d\nc\nb\na\n"; select from 2:1 to 3:2 (partly into line 3) and sort ascending; then select from 2:1 to 4:1 (ending at the start of line 4) and reverse.
- Expect: "d\nb\nc\na\n" (only lines 2-3, whole lines, even though line 3 is partly selected); then lines 2-3 only are reversed: "d\nc\nb\na\n" (a selection ending at column 1 does not include that line).

### EDIT-049: A rectangular selection sorts whole lines by the text in its columns
- Covers: IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING, IDM_EDIT_SORTLINES_DECIMALDOT_ASCENDING, IDM_EDIT_SORTLINES_DECIMALDOT_DESCENDING
- Channel: mcp, keys
- Steps: New document "c 2\nb 3\na 1\n"; make a rectangle over column 3 of all three lines (Begin/End Select in Column Mode from 1:3 to 3:4) and sort lexicographically ascending. Then "a\t2.5\tx\nb\t10\ty\nc\t-1\tz\nd\t2.5\tw\n" with a zero-width column after the first tab on all lines, sorted Decimals (Dot) ascending and descending.
- Expect: "a 1\nc 2\nb 3\n"; ascending "c\t-1\tz\na\t2.5\tx\nd\t2.5\tw\nb\t10\ty\n"; descending "b\t10\ty\na\t2.5\tx\nd\t2.5\tw\nc\t-1\tz\n" (equal keys keep their order both ways).

### EDIT-050: Line operations on an empty document and a single line
- Covers: IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING, IDM_EDIT_SORTLINES_RANDOMLY, IDM_EDIT_REMOVE_ANY_DUP_LINES, IDM_EDIT_JOIN_LINES, IDM_EDIT_SPLIT_LINES, IDM_EDIT_REMOVEEMPTYLINES
- Channel: mcp
- Steps: On an empty document and on "only" run each of the listed commands.
- Expect: every command reports ran=true; the empty document stays "" and "only" stays "only"; the app keeps answering (a following get_document works) and no dialog appears.

## Comment/Uncomment

### EDIT-051: Toggle Single Line Comment comments and uncomments per language
- Covers: IDM_EDIT_BLOCK_COMMENT
- Channel: mcp, keys
- Steps: For each language and token (cpp "//", python "#", sql "--", ini ";", vb "'", batch "REM", bash "#"): new document "x = 1\n  y = 2\n\n" in that language, select all, run the command; select all again and run it again. Also once with Cmd+/.
- Expect: after the first run "TOKEN x = 1\n  TOKEN y = 2\n\n" (the token and one space go after the indentation; the blank line is left alone); after the second the original text; Cmd+/ toggles the same way.

### EDIT-052: Toggling keeps the lines selected, so toggling twice restores
- Covers: IDM_EDIT_BLOCK_COMMENT
- Channel: mcp
- Steps: Python document "x = 1\n  y = 2\n"; select all; run the command twice without touching the selection.
- Expect: as Notepad++ (doBlockComment re-selects the lines): after the first run both lines are commented and still selected; after the second the text is "x = 1\n  y = 2\n" again.

### EDIT-053: Mixed commented and uncommented lines are all commented
- Covers: IDM_EDIT_BLOCK_COMMENT
- Channel: mcp
- Steps: cpp document "// a\nb\n"; select all; run the command.
- Expect: "// // a\n// b\n" (not every line was commented, so every line gets a comment, as Notepad++'s toggle does).

### EDIT-054: Single Line Comment always adds a comment
- Covers: IDM_EDIT_BLOCK_COMMENT_SET
- Channel: mcp
- Steps: cpp document "// a\nb\n"; select all; run IDM_EDIT_BLOCK_COMMENT_SET; run it again on "a\n".
- Expect: the command is in this build's menus and runs (run_command ran=true); "// // a\n// b\n"; "// a\n".

### EDIT-055: Single Line Uncomment strips one comment level
- Covers: IDM_EDIT_BLOCK_UNCOMMENT
- Channel: mcp
- Steps: cpp document "// x\n  //y\nz\n// // w\n"; select all; run the command.
- Expect: "x\n  y\nz\n// w\n" (the token and one following space go; indentation stays; an uncommented line is unchanged; only one level is removed).

### EDIT-056: Single-line commands in a language with no line comment
- Covers: IDM_EDIT_BLOCK_COMMENT, IDM_EDIT_BLOCK_UNCOMMENT
- Channel: mcp
- Steps: Plain text document "text\n": select all, run Toggle Single Line Comment. HTML document "<p>hi</p>\n": select all, run Toggle Single Line Comment, then Single Line Uncomment.
- Expect: plain text: unchanged. HTML (only stream comments): as Notepad++'s advanced single-line mode, the line is wrapped "<!-- <p>hi</p> -->\n" and uncommenting restores "<p>hi</p>\n".

### EDIT-057: Block Comment wraps the selection in the language's stream comment
- Covers: IDM_EDIT_STREAM_COMMENT
- Channel: mcp, keys
- Steps: cpp document "int value;\n"; select "value" and run IDM_EDIT_STREAM_COMMENT; HTML "<p>hi</p>\n": select the tag text and press Shift+Cmd+/; CSS "a{}\n" likewise with the command.
- Expect: "int /*value*/;\n" with the commented text selected; "<!--<p>hi</p>-->\n"; "/*a{}*/\n".

### EDIT-058: Block Uncomment removes the stream comment around the selection
- Covers: IDM_EDIT_STREAM_UNCOMMENT
- Channel: mcp
- Steps: cpp "int /*value*/;\n": select "/*value*/" and run the command; HTML "<!--<p>hi</p>-->\n": select the whole comment and run it.
- Expect: "int value;\n"; "<p>hi</p>\n".

### EDIT-059: Block Comment in a language without stream comments changes nothing
- Covers: IDM_EDIT_STREAM_COMMENT, IDM_EDIT_STREAM_UNCOMMENT
- Channel: mcp
- Steps: Python "x = 1\n" and plain text "text\n": select all, run Block Comment, then Block Uncomment.
- Expect: the texts are unchanged and no dialog appears.

## Auto-Completion commands

### EDIT-060: Function Completion lists the language's functions
- Covers: IDM_EDIT_AUTOCOMPLETE
- Channel: mcp, keys, prefs
- Steps: C document "int main() { pri" with the caret at the end; run IDM_EDIT_AUTOCOMPLETE; read SCI_AUTOCACTIVE and the current entry (SCI_AUTOCGETCURRENTTEXT); press Return. Repeat with Ctrl+Space.
- Expect: the list is active; its current entry starts with "pri"; the list holds "printf" (lastCompletionList through e2e_invoke), which is not in the document; after Return the word is completed to the current entry; Ctrl+Space opens the same list.

### EDIT-061: Word Completion offers the document's words and types a lone one
- Covers: IDM_EDIT_AUTOCOMPLETE_CURRENTFILE
- Channel: mcp, keys
- Steps: Plain text "alphabet alpine Alpha\nalp", caret at the end, run the command; Escape; then "alphabet beta\nalp" and press Cmd+Return.
- Expect: first: the list is active with "alphabet" and "alpine" but not "Alpha" (plain text respects case) and not "alp" itself; second: no list, the text becomes "alphabet beta\nalphabet" at once.

### EDIT-062: Word Completion ignores case where the language's API file says so
- Covers: IDM_EDIT_AUTOCOMPLETE_CURRENTFILE
- Channel: mcp
- Steps: SQL document "alphabet Alpine\nalp", caret at the end; run the command.
- Expect: the list is active and holds both "alphabet" and "Alpine".

### EDIT-063: Function Parameters Hint shows the shipped signature
- Covers: IDM_EDIT_FUNCCALLTIP
- Channel: mcp, keys
- Steps: C document "x = abs(1);\n"; caret at 1:10 (inside the parentheses); run the command; Escape; press Ctrl+Shift+Space.
- Expect: SCI_CALLTIPACTIVE is 1; the tip is for "abs" ("int abs (int i)", read through apiCallTipState/callTipCandidates on the editor); Escape closes it; the key opens it again.

### EDIT-064: Previous and Next Hint step between overloads
- Covers: IDM_EDIT_FUNCCALLTIP_NEXT, IDM_EDIT_FUNCCALLTIP_PREVIOUS
- Channel: mcp
- Steps: Perl document "$x = abs($y);\n", caret inside "abs(...)", run Function Parameters Hint; run Next, then Previous. Then a C document with "abs(" (one overload) and run Next.
- Expect: in Perl the tip stays active and its overload goes 0 → 1 → 0; in C the overload stays 0 (nothing to step to) and the tip is still shown.

### EDIT-065: Path Completion lists folder entries
- Covers: IDM_EDIT_AUTOCOMPLETE_PATH
- Channel: mcp, keys, files
- Steps: Create tmp/pc/target.txt and tmp/pc/my dir/Sub/; new document "cat \"<tmp>/pc/my dir/su" with the caret at the end, run the command, read the current entry, press Return; then "<tmp>/pc/tar" with Ctrl+Alt+Space; then "no path here" and run it.
- Expect: the list is active and the current entry is "<tmp>/pc/my dir/Sub/" (whole path with the space, case ignored, folder ends in "/"); Return puts it in; the second shows "<tmp>/pc/target.txt"; with no path before the caret no list appears and the text is unchanged.

## EOL Conversion

### EDIT-066: EOL Conversion rewrites every line ending
- Covers: IDM_FORMAT_TODOS, IDM_FORMAT_TOUNIX, IDM_FORMAT_TOMAC
- Channel: mcp, files
- Steps: Open a file with mixed endings "a\nb\r\nc\rd"; run IDM_FORMAT_TODOS, then IDM_FORMAT_TOMAC, then IDM_FORMAT_TOUNIX, reading the text and `eol` after each; save and read the file's bytes.
- Expect: "a\r\nb\r\nc\r\nd" / CRLF; "a\rb\rc\rd" / CR; "a\nb\nc\nd" / LF; the saved file has exactly "a\nb\nc\nd"; each conversion is one undo step.

### EDIT-067: The current format's conversion is disabled
- Covers: IDM_FORMAT_TODOS, IDM_FORMAT_TOUNIX, IDM_FORMAT_TOMAC
- Channel: menu, mcp
- Steps: In an LF document read the three items' enabled state; convert to CRLF and read again.
- Expect: as Notepad++ (enableConvertMenuItems): Unix (LF) disabled and the other two enabled; after the conversion Windows (CR LF) disabled and the other two enabled.

### EDIT-068: New typing after a conversion uses the new EOL
- Covers: IDM_FORMAT_TODOS
- Channel: mcp, keys
- Steps: New LF document "a"; run IDM_FORMAT_TODOS; caret at the end, press Return and type "b".
- Expect: "a\r\nb".

## Blank Operations

### EDIT-069: Trim Trailing, Trim Leading and Trim Both
- Covers: IDM_EDIT_TRIMTRAILING, IDM_EDIT_TRIMLINEHEAD, IDM_EDIT_TRIM_BOTH
- Channel: mcp
- Steps: For each command on "  a  \n\tb\t\n c \n" with no selection.
- Expect: trailing: "  a\n\tb\n c \n"; leading: "a  \nb\t\n c \n"; both: "a\nb\n c \n" (spaces and tabs only; a no-break space is content).

### EDIT-070: Blank operations limited to the selected lines
- Covers: IDM_EDIT_TRIMTRAILING, IDM_EDIT_TRIMLINEHEAD
- Channel: mcp
- Steps: "a  \nb  \nc  \n": select from 2:1 to 2:2 and Trim Trailing; "  a\n  b\n": select line 2 and Trim Leading.
- Expect: "a  \nb\nc  \n"; "  a\nb\n".

### EDIT-071: EOL to Space and Trim both and EOL to Space
- Covers: IDM_EDIT_EOL2WS, IDM_EDIT_TRIMALL
- Channel: mcp
- Steps: EOL to Space on "a\nb\r\nc\n" (no selection) and on "1\n2\n3\n4\n" with lines 2-3 selected; Trim both and EOL to Space on "  a  \n\tb\t\n  c\n".
- Expect: "a b c" followed by the document's final line end; lines 2-3 joined only: "1\n2 3\n4\n"; "a b c" followed by the final line end (each line trimmed before joining).

### EDIT-072: TAB to Space fills to the next tab stop
- Covers: IDM_EDIT_TAB2SW
- Channel: mcp, prefs
- Steps: With tab width 4: "\tx\n", "a\tb\n", "abcd\te\n", "ab\t\tc\n"; run the command on each.
- Expect: as Notepad++ (wsTabConvert counts columns): "    x\n", "a   b\n", "abcd    e\n", "ab      c\n".

### EDIT-073: Space to TAB (All) and (Leading)
- Covers: IDM_EDIT_SW2TAB_ALL, IDM_EDIT_SW2TAB_LEADING
- Channel: mcp
- Steps: With tab width 4 run each command on "        a    b\nab  cd\n".
- Expect: All: "\t\ta\tb\nab\tcd\n" (runs of spaces that reach a tab stop become tabs, as wsTabConvert does); Leading: "\t\ta    b\nab  cd\n" (only the indentation is converted).

### EDIT-074: Blank operations are one undo step and ignore a rectangle
- Covers: IDM_EDIT_TRIM_BOTH, IDM_EDIT_TAB2SW
- Channel: mcp, keys
- Steps: Trim Both on "  a  \n  b  \n", then one Cmd+Z; then make a rectangle over two lines of "\ta\n\tb\n" and run TAB to Space.
- Expect: one Undo restores "  a  \n  b  \n"; with a rectangular selection TAB to Space does nothing, as Notepad++ ("block selection is not supported").

## Paste Special

### EDIT-075: Paste HTML Content pastes the HTML source
- Covers: IDM_EDIT_PASTE_AS_HTML
- Channel: mcp, clipboard
- Steps: HTML document "<b>bold</b> text": select all and run Plugins|Export|Copy HTML to clipboard (puts public.html on the clipboard); in a new document run IDM_EDIT_PASTE_AS_HTML.
- Expect: the clipboard types include public.html; the new document holds the HTML source (starts "<!DOCTYPE html>", contains "bold" inside markup); the caret is after it.

### EDIT-076: Paste RTF Content pastes the RTF source
- Covers: IDM_EDIT_PASTE_AS_RTF
- Channel: mcp, clipboard
- Steps: Document "rich": select all, Plugins|Export|Copy RTF to clipboard; new document; run IDM_EDIT_PASTE_AS_RTF.
- Expect: the document starts with "{\rtf1" and contains "rich".

### EDIT-077: Paste HTML/RTF with plain text on the clipboard does nothing
- Covers: IDM_EDIT_PASTE_AS_HTML, IDM_EDIT_PASTE_AS_RTF
- Channel: mcp, clipboard
- Steps: Clipboard "plain"; document "x"; run both commands.
- Expect: the text stays "x".

### EDIT-078: Copy, Cut and Paste Binary Content round-trip bytes
- Covers: IDM_EDIT_COPY_BINARY, IDM_EDIT_CUT_BINARY, IDM_EDIT_PASTE_BINARY
- Channel: mcp, clipboard
- Steps: Document "ab é": select "ab" and Copy Binary; select "é" and Cut Binary; caret at the end, Paste Binary; then clipboard "C3 A9 zz 41" and Paste Binary into "[]" at 1:2.
- Expect: clipboard "61 62"; after the cut the clipboard is "C3 A9" and "é" is gone; pasting gives back "é" at the caret; the last paste gives "[éA]" (pairs that are not hex are skipped).

### EDIT-079: Binary copy keeps a NUL byte
- Covers: IDM_EDIT_COPY_BINARY, IDM_EDIT_PASTE_BINARY
- Channel: mcp, files, clipboard
- Steps: Open a file whose bytes are "a\x00b"; select all; Copy Binary; new document; Paste Binary; save it to tmp and read the bytes.
- Expect: the clipboard is "61 00 62"; the saved file is exactly the three bytes 61 00 62 (the NUL survives, which is what binary copy is for).

### EDIT-080: Binary commands with nothing selected
- Covers: IDM_EDIT_COPY_BINARY, IDM_EDIT_CUT_BINARY, IDM_EDIT_PASTE_BINARY
- Channel: mcp, clipboard
- Steps: Clipboard "keep"; document "abc" with no selection; run Copy Binary and Cut Binary; clipboard "" and run Paste Binary.
- Expect: clipboard still "keep" after the first two; the text stays "abc" throughout.

## On Selection

### EDIT-081: Open File opens the file the selection names
- Covers: IDM_EDIT_OPENSELECTEDFILETOEDIT
- Channel: mcp, files
- Steps: Create tmp/target.txt and tmp/holder.txt containing lines: the absolute path of target, "target.txt", "\"<abs path>\"", "~/home.txt" (a file created in the app's scratch home); open holder; for each line select it and run the command, closing the opened tab in between.
- Expect: each time a tab opens with path = the file named (relative paths resolve against holder's folder, quotes are stripped, "~" is the app's home) and it becomes the current document.

### EDIT-082: Open File on a word under the caret and on a name that does not exist
- Covers: IDM_EDIT_OPENSELECTEDFILETOEDIT
- Channel: mcp, files
- Steps: tmp/holder.txt contains "see notes.md and missing.txt" and tmp/notes.md exists; open holder; select "notes.md" and run the command; back in holder select "missing.txt" (not on disk) and run it; then select nothing, caret in "see", and run it.
- Expect: notes.md opens as the current document; for "missing.txt" and for the word "see" no document is added, the current document stays holder and no dialog appears.

### EDIT-083: Open Containing Folder is reachable and refuses a missing file
- Covers: IDM_EDIT_OPENSELECTEDFILEFOLDERINEXPLORER
- Channel: mcp, menu
- Steps: Document "no/such/file.txt"; select it; run IDM_EDIT_OPENSELECTEDFILEFOLDERINEXPLORER by id; also invoke Edit|On Selection|Open Containing Folder in Finder.
- Expect: the command is found by its id (run_command does not fail with "not in this build's menus"); nothing opens, no document or window is added. (Revealing an existing file needs the URL/Finder interception hook.)

### EDIT-084: Redact Selection replaces each character with a block
- Covers: IDM_EDIT_REDACT_SELECTION
- Channel: mcp
- Steps: Document "secret é👍 ok"; select "secret é👍" and run the command; one Cmd+Z; then multi-select both "ab" in "ab x ab" and run it; then with no selection.
- Expect: "█████████ ok" (one block per character, 9, whatever their byte length); Undo restores; "██ x ██"; with no selection nothing changes.

### EDIT-085: Redact with Shift uses bullets
- Covers: IDM_EDIT_REDACT_SELECTION
- Channel: menu
- Steps: Document "pin 1234"; select "1234"; invoke the command with Shift held (needs the modifier hook for e2e_menu_invoke).
- Expect: "pin ●●●●".

### EDIT-086: Search on Internet with nothing to search does nothing
- Covers: IDM_EDIT_SEARCHONINTERNET
- Channel: mcp
- Steps: Empty document; run the command; document "   " with the caret between spaces; run it.
- Expect: no document or window is added, the text is unchanged, the app stays responsive. With a word selected the URL opened must be the engine's with the word escaped: to be checked once the URL interception hook exists (no browser is opened by the suite).

### EDIT-087: Change Search Engine stores a custom engine
- Covers: IDM_EDIT_CHANGESEARCHENGINE
- Channel: mcp, modal, prefs
- Steps: Run the command with a queued answer {button 1, field "https://example.invalid/?q=$(CURRENT_WORD)"}; read the modal log and prefs searchEngine, searchEngineCustom; run it again answering Cancel; restore the preferences.
- Expect: the prompt's default shows the current engine with "$(CURRENT_WORD)"; afterwards searchEngine=4 and searchEngineCustom is the URL; Cancel changes nothing.

## Multi-selection

### EDIT-088: Multi-select All with each matching mode
- Covers: IDM_EDIT_MULTISELECTALL, IDM_EDIT_MULTISELECTALLMATCHCASE, IDM_EDIT_MULTISELECTALLWHOLEWORD, IDM_EDIT_MULTISELECTALLMATCHCASEWHOLEWORD
- Channel: mcp
- Steps: For each command: document "Cat cat catalog\n", select "cat" (1:5-1:8), run it, read the selection count and ranges.
- Expect: Ignore Case & Whole Word (neither flag): 3 selections (Cat, cat, and "cat" in catalog); Match Case Only: 2; Match Whole Word Only: 2 (Cat, cat); Match Case & Whole Word: 1.

### EDIT-089: Typing over a multi-selection edits every occurrence
- Covers: IDM_EDIT_MULTISELECTALL
- Channel: mcp, keys
- Steps: Document "foo Foo foo\n"; select the first "foo"; run Multi-select All (Match Case Only); type "bar"; press Cmd+Z.
- Expect: "bar Foo bar\n"; one Undo restores "foo Foo foo\n".

### EDIT-090: Multi-select All uses the word under the caret
- Covers: IDM_EDIT_MULTISELECTALLWHOLEWORD
- Channel: mcp
- Steps: Document "one two one", caret at 1:2 with nothing selected; run the command.
- Expect: 2 selections covering both "one".

### EDIT-091: Multi-select Next adds the next occurrence under each mode
- Covers: IDM_EDIT_MULTISELECTNEXT, IDM_EDIT_MULTISELECTNEXTMATCHCASE, IDM_EDIT_MULTISELECTNEXTWHOLEWORD, IDM_EDIT_MULTISELECTNEXTMATCHCASEWHOLEWORD
- Channel: mcp
- Steps: For each command: document "Cat cat catalog\n" with "cat" (1:5-1:8) selected; run it once.
- Expect: Ignore Case & Whole Word and Match Case Only each add the "cat" of "catalog" (1:9-1:12), 2 selections; Match Whole Word Only finds nothing after the caret and wraps round to "Cat" at 1:1-1:4, 2 selections; Match Case & Whole Word has no other match and leaves 1 selection.

### EDIT-092: Undo the Latest Added Multi-Select and Skip Current
- Covers: IDM_EDIT_MULTISELECTUNDO, IDM_EDIT_MULTISELECTSSKIP, IDM_EDIT_MULTISELECTNEXT
- Channel: mcp
- Steps: Document "foo foo foo\n"; select the first; Multi-select Next twice (3 selections); run Undo the Latest Added; run Skip Current & Go to Next.
- Expect: after Undo 2 selections (the third "foo" is dropped); after Skip still 2 selections, the second "foo" replaced by the third (selections cover 1:1-1:4 and 1:9-1:12).

### EDIT-093: Multi-select commands with nothing to find
- Covers: IDM_EDIT_MULTISELECTALL, IDM_EDIT_MULTISELECTNEXT, IDM_EDIT_MULTISELECTUNDO
- Channel: mcp
- Steps: Empty document: run Multi-select All and Next; document "foo bar" with "foo" selected: run Next; with one selection run Undo the Latest Added.
- Expect: nothing changes: still one (empty or "foo") selection, text unchanged.

## Column Mode and Column Editor

### EDIT-094: Column Mode… explains column selection
- Covers: IDM_EDIT_COLUMNMODETIP
- Channel: mcp, modal
- Steps: Queue OK; run the command; read the modal log.
- Expect: one alert "Column mode" whose text mentions Option-drag and Begin/End Select in Column Mode; after OK the document is unchanged.

### EDIT-095: Column Editor inserts text into every row of a zero-width column
- Covers: IDM_EDIT_COLUMNMODE
- Channel: mcp, modal
- Steps: Document "a\nb\nc\n"; zero-width rectangle at column 1 over lines 1-3 (Begin/End Select in Column Mode from 1:1 to 3:1); queue answers {1,"text"} and {1,">"}; run the command.
- Expect: prompts 'Column Editor - "text" or "number"?' then 'Text to insert'; the text is ">a\n>b\n>c\n"; one Cmd+Z restores it.

### EDIT-096: Column Editor replaces a selected block and pads short lines
- Covers: IDM_EDIT_COLUMNMODE
- Channel: mcp, modal
- Steps: Document "abcd\nab\nabcd\n"; rectangle from 1:3 to 3:5 (reaching past the short line 2 into virtual space); answer "text" and "XY".
- Expect: "abXY\nabXY\nabXY\n" (the selected columns are replaced; the short line gets the text at column 3).

### EDIT-097: Column Editor with no selection works from the caret line to the end
- Covers: IDM_EDIT_COLUMNMODE
- Channel: mcp, modal
- Steps: Document "12345\n1\n12345"; caret at 1:4 with nothing selected; answer "text" and "|".
- Expect: "123|45\n1  |\n123|45" (every line from the caret's down gets the text at the caret's column; the short line is padded with spaces).

### EDIT-098: Column Editor numbers: initial, increase, repeat, zeros and base
- Covers: IDM_EDIT_COLUMNMODE
- Channel: mcp, modal
- Steps: For each set of answers (mode "number", initial, increase, repeat, leading zeros, format) on a zero-width column at column 1 over the 4 lines "x\nx\nx\nx": (9,1,1,yes,dec); (1,1,2,no,dec); (8,2,1,no,hex); (5,1,1,yes,bin); (7,1,1,no,oct).
- Expect: respectively "09x\n10x\n11x\n12x"; "1x\n1x\n2x\n2x"; "8x\nAx\nCx\nEx"; "0101x\n0110x\n0111x\n1000x" (zero-padded to the widest); "7x\n10x\n11x\n12x"; six prompts are answered each time.

### EDIT-099: Cancelling the Column Editor changes nothing
- Covers: IDM_EDIT_COLUMNMODE
- Channel: mcp, modal
- Steps: Zero-width column over "a\nb\n"; queue Cancel for the first prompt; run; then answer "text" and Cancel the second; then "number", "1", Cancel.
- Expect: the text is "a\nb\n" after each attempt.

## Panels

### EDIT-100: Character Panel shows 256 characters and inserts one on double click
- Covers: IDM_EDIT_CHAR_PANEL
- Channel: mcp, ui
- Steps: Run IDM_EDIT_CHAR_PANEL; find the table with columns Value, Hex, Character, HTML Name, HTML Decimal, HTML Hexadecimal in the main window; read rows 10, 38, 128, 255; with an empty document double-click row 65, then row 233.
- Expect: 256 rows; row 10 is "LF", row 38 has "&amp;", row 128 is "€" with "&#x20ac;", row 255 hex "FF"; the document becomes "Aé".

### EDIT-101: Character Panel toggles and inserts HTML forms from their columns
- Covers: IDM_EDIT_CHAR_PANEL
- Channel: mcp, ui
- Steps: Double-click the HTML Name cell of row 233 and the HTML Decimal cell of row 147 (needs the clicked-column hook); run IDM_EDIT_CHAR_PANEL again.
- Expect: the document gets "&eacute;&#8220;"; the second run hides the panel (the table is no longer in the main window's controls) and the menu item's check follows the panel's visibility.

### EDIT-102: Clipboard History keeps copies and pastes an earlier one
- Covers: IDM_EDIT_CLIPBOARDHISTORY_PANEL
- Channel: mcp, ui, clipboard
- Steps: Run IDM_EDIT_CLIPBOARDHISTORY_PANEL; copy "history one" and then "history two" from a document with Cmd+C; wait until the panel's table has 2 rows; in an empty document double-click the row holding "history one".
- Expect: the rows are newest first ("history two", "history one"); the document becomes "history one"; running the command again hides the panel.

## Read-only

### EDIT-103: Read-Only on Current Document blocks editing and is checked
- Covers: IDM_EDIT_TOGGLEREADONLY
- Channel: mcp, keys, menu
- Steps: Document "ro\n"; run the command; type "zz", press Return and Backspace; read `read_only` and the item's checked state; run it again and type "x" at the start.
- Expect: while on: text stays "ro\n", read_only=true, the item is checked (as Notepad++ CheckMenuItem); after the second run read_only=false, unchecked, and "xro\n".

### EDIT-104: Commands do not change a read-only document
- Covers: IDM_EDIT_TOGGLEREADONLY, IDM_EDIT_UPPERCASE, IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING, IDM_EDIT_JOIN_LINES, IDM_EDIT_TRIMTRAILING, IDM_EDIT_REMOVE_ANY_DUP_LINES, IDM_EDIT_DUP_LINE, IDM_EDIT_INS_TAB, IDM_EDIT_INSERT_DATETIME_SHORT, IDM_EDIT_BLOCK_COMMENT, IDM_FORMAT_TODOS, IDM_EDIT_REDACT_SELECTION, IDM_EDIT_COLUMNMODE
- Channel: mcp
- Steps: Document "b  \na\na\n" (cpp) made read-only, all selected; run each listed command (Column Editor with queued answers "text", "X"); clear read-only at the end.
- Expect: after every command the text is still "b  \na\na\n", the eol is still LF and modified is false.

### EDIT-105: Read-Only for All Documents and Clear Read-Only for All Documents
- Covers: IDM_EDIT_SETREADONLYFORALLDOCS, IDM_EDIT_CLEARREADONLYFORALLDOCS
- Channel: mcp
- Steps: Open three documents, the second current; run Read-Only for All Documents; list documents; type into each via select; run Clear Read-Only for All Documents; list again.
- Expect: every document reports read_only=true and refuses typing, and the second is still the current one; after clearing every one is read_only=false.

### EDIT-106: Read-Only Attribute on disk toggles the file's write permission
- Covers: IDM_EDIT_TOGGLESYSTEMREADONLY
- Channel: mcp, files
- Steps: Write tmp/perm.txt (mode 0644) and open it; run the command; stat the file; run it again; stat it; then run it on an untitled document.
- Expect: after the first run no write bit is set (mode 0444); after the second the owner write bit is back; on an untitled document nothing happens and no dialog appears.

### EDIT-107: Read-only state survives switching tabs
- Covers: IDM_EDIT_TOGGLEREADONLY
- Channel: mcp, keys
- Steps: Make document A read-only; switch to document B and type; switch back to A and type.
- Expect: B is editable; A still refuses typing and reports read_only=true.
