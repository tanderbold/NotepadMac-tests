# SEARCH — The Search menu and the Find dialog

Everything under the Search menu (66 commands in `plan/commands.tsv`) and the Find dialog driven through its own controls: the Find, Replace, Find in Files, Find in Projects and Mark tabs; the three search modes (Normal, Extended escapes, Boost-syntax regular expressions with ". matches newline"), Match case, Match whole word only, Wrap around, Backward direction, In selection; Find Next / Count / Find All / Replace / Replace All (also in all opened documents), replacement escapes and back-references; Find and Replace in Files over a scratch folder (filters, sub-folders, hidden folders, files checked on disk); the "Search results" tab (its report, going to a result, folding, copying, clearing); Select and Find, Volatile Find, Incremental Search; the five token styles and the Find Mark style; bookmarks and the bookmarked-line operations; Go to line; braces; Change History navigation; Find characters in range. Out of scope: the MCP `find` / `replace` tools (AGENT), macro recording of searches (MACRO), Preferences pages that only store search settings (SETTINGS), the Project panel itself (Find in Projects only uses it). Conventions used below: the dialog is the `NppPanel` window whose title follows its tab ("Find", "Replace", "Find in Files", "Find in Projects", "Mark"), so tests address it by class or number, never by the title "Find"; a button is targeted by title **and** class `NSButton` (the window frame carries the same title as the "Replace" and "Mark" buttons); "Find what" is the first `NSComboBox`, "Replace with" the second, Filters the third, Directory the fourth; the status line is the non-editable `NSTextField` at the bottom of the dialog; the search mode is the `NSMatrix` of three radios, set by focusing it and pressing up/down until `app.get("app", "modeRadios.selectedRow")` is 0/1/2 (a proper `select` on NSMatrix is a requested hook). Token style n (1-5) is Scintilla indicator 7+n, the Find Mark style indicator 13, bookmarks marker 1.

## Opening the dialog

### SEARCH-001: Find... opens the dialog on the Find tab with the Find controls
- Covers: IDM_SEARCH_FIND
- Channel: menu, ui
- Steps: With a document "one two one\n" and nothing selected, run IDM_SEARCH_FIND; read the dialog's controls.
- Expect: an NppPanel titled "Find" is visible and key; the segmented control has items Find, Replace, Find in Files, Find in Projects, Mark with index 0 selected; visible buttons are Find Next, Count, Find All in Current Document, Find All in All Opened Documents; Replace with / Filters / Directory fields are hidden; the check boxes Match case, Match whole word only, Wrap around (on), Backward direction, In selection are present; the Find what field has keyboard focus

### SEARCH-002: Each dialog command opens its own tab
- Covers: IDM_SEARCH_REPLACE, IDM_SEARCH_FINDINFILES, IDM_SEARCH_FIND
- Channel: menu, ui
- Steps: For each of (IDM_SEARCH_FIND, "Find", 0), (IDM_SEARCH_REPLACE, "Replace", 1), (IDM_SEARCH_FINDINFILES, "Find in Files", 2): run the command and read the dialog.
- Expect: the window title is the tab's name; the segmented control's selected index is the tab's; Replace shows Replace with, the swap button, Find Next, Replace, Replace All, Replace All in All Opened Documents; Find in Files shows Filters, Directory, Browse…, From doc, In all sub-folders (on), In hidden folders (off), Find All, Replace in Files and hides Backward direction and In selection

### SEARCH-003: Switching tabs in the dialog swaps controls and title and clears the status
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Open Find, press Count on "one" so the status line reads "Count: …", then select each segment "Replace", "Find in Files", "Find in Projects", "Mark" with e2e_act select.
- Expect: the window title follows the segment; the status line is empty after each switch; the Mark tab shows Bookmark line, Purge for each search, Mark All, Clear all marks, Copy Marked Text; the Find in Projects tab shows Project Panel 1 (on), Project Panel 2 (off), Project Panel 3 (off), Find All, Replace in Projects

### SEARCH-004: The selection seeds Find what
- Covers: IDM_SEARCH_FIND
- Channel: menu, ui
- Steps: For each of: a selection "two" in "one two three"; the caret inside "three" with nothing selected; a 2000-byte selection (over fillFindWhatThreshold 1024) after Find what held "prev": open the dialog.
- Expect: Find what is "two"; then "three" (the word under the caret); then still "prev" (a selection over the threshold does not seed the field)

### SEARCH-005: In selection follows the selection when the dialog opens
- Covers: IDM_SEARCH_FIND
- Channel: menu, ui
- Steps: For each of: no selection; a 3-character selection; a 1100-character selection: open the dialog (IDM_SEARCH_FIND) and read In selection.
- Expect: no selection: In selection disabled and off; 3 characters: enabled and unchanged (off); 1100 characters (at least inSelectionThreshold 1024): enabled and ticked

### SEARCH-006: Keyboard shortcuts of the Search menu
- Covers: IDM_SEARCH_FIND, IDM_SEARCH_REPLACE, IDM_SEARCH_FINDINFILES, IDM_SEARCH_FINDNEXT, IDM_SEARCH_FINDPREV, IDM_SEARCH_GOTOLINE, IDM_SEARCH_TOGGLE_BOOKMARK, IDM_SEARCH_NEXT_BOOKMARK, IDM_SEARCH_PREV_BOOKMARK, IDM_SEARCH_SETANDFINDNEXT, IDM_SEARCH_SETANDFINDPREV, IDM_SEARCH_FINDINCREMENT, IDM_SEARCH_GOTOMATCHINGBRACE, IDM_SEARCH_SELECTMATCHINGBRACES
- Channel: menu, keys
- Steps: Read each item's key equivalent with e2e_menu; then press cmd+f, alt+cmd+f, shift+cmd+f in the editor, and cmd+b on line 2 of a three-line document.
- Expect: keys are cmd+f, alt+cmd+f, shift+cmd+f, cmd+g, shift+cmd+g, cmd+l, cmd+b, shift+cmd+b, alt+cmd+b, cmd+e, shift+cmd+e, cmd+i, cmd+m, shift+cmd+m respectively; the three chords open the dialog on Find, Replace and Find in Files; cmd+b bookmarks line 2 (`bookmarks` tool lists [2])

### SEARCH-007: Escape and the close button hide the dialog, keeping its fields
- Covers: IDM_SEARCH_FIND
- Channel: keys, ui
- Steps: Open Find, set Find what to "keepme", press escape in the dialog; reopen with IDM_SEARCH_FIND with the caret on an empty line; then close it with close_window and reopen.
- Expect: after escape the dialog is not visible and the main window is still open; on reopening Find what still reads "keepme" and the options are as left

### SEARCH-008: The search options and mode are remembered across launches
- Covers: IDM_SEARCH_FIND
- Channel: ui, prefs, launch
- Steps: (fresh_app) In the dialog tick Match case and Match whole word only, untick Wrap around, pick Regular expression, press Count on "x"; restart keeping preferences; open the dialog.
- Expect: prefs findMatchCase true, findWholeWord true, findWrap false, findMode 2 after the Count; after the restart the boxes and the mode radio show the same state; Match whole word only is disabled (regex mode)

### SEARCH-009: Find what history keeps ten entries, newest first, and persists
- Covers: IDM_SEARCH_FIND
- Channel: ui, prefs
- Steps: Press Count for "term0" … "term11", then for "term3"; read the Find what combo items and the findHistory pref. Restore findHistory afterwards.
- Expect: exactly 10 items; first "term3", second "term11"; "term0" and "term1" are gone; findHistory equals the combo's items

### SEARCH-010: The swap button trades Find what and Replace with
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: On the Replace tab set Find what "left" and Replace with "right", click the "⇅" button.
- Expect: Find what reads "right" and Replace with reads "left"

### SEARCH-011: Mode-dependent options are greyed out
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Select each mode (Normal, Extended, Regular expression) and read Match whole word only and ". matches newline".
- Expect: Normal and Extended: whole word enabled, ". matches newline" disabled; Regular expression: whole word disabled, ". matches newline" enabled

### SEARCH-012: Dialog transparency on losing focus or always
- Covers: IDM_SEARCH_FIND
- Channel: ui, prefs
- Steps: Tick Transparency, choose "Always" (focus the second NSMatrix and press down), set the slider to 100; then untick Transparency. Read `window:<dialog>` alphaValue with e2e_invoke key after each step. Restore findTransparencyMode.
- Expect: with Always the alpha is about 100/255 even while key and pref findTransparencyMode is 2; unticked the alpha is 1.0 and findTransparencyMode is 0; the slider and radios are disabled when unticked

## Find: modes, options, Find Next, Count

### SEARCH-013: Find Next selects the next match and advances
- Covers: IDM_SEARCH_FIND
- Channel: ui, mcp
- Steps: Document "x x x\n", caret at 0; Find what "x", Normal; press Find Next three times, then a fourth time.
- Expect: selections are 0-1, 2-3, 4-5, then 0-1 again (wrap on); the status line is empty after the first three presses and, after the fourth, reads "Find: Reached document end, first occurrence from the top found." (SEARCH-016)

### SEARCH-014: Find Next without a match reports it and leaves the selection
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "abc\n" with caret at 1; Find what "zzz"; press Find Next.
- Expect: selection unchanged (caret 1, nothing selected); status line reads `Find: Can't find the text "zzz"`

### SEARCH-015: Wrap around off stops at the end of the document
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "one one\n", caret after the second "one"; untick Wrap around; press Find Next; tick it again and press Find Next.
- Expect: unticked: selection unchanged and status `Find: Can't find the text "one"`; ticked: the first "one" (0-3) is selected

### SEARCH-016: Find Next reports wrapping round the end (Notepad++ status)
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "one one\n", caret after the second "one", Wrap around on; press Find Next. Then tick Backward direction, caret at 0, press Find Next.
- Expect: forward: selection 0-3 and status "Find: Reached document end, first occurrence from the top found."; backward: selection 4-7 and status "Find: Reached document beginning, first occurrence from the bottom found." (the port's dialog Find Next leaves the status empty: likely defect)

### SEARCH-017: Backward direction searches up from the selection
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "a1 a2 a3\n", select "a3" (6-8); tick Backward direction; Find what "a"; press Find Next twice.
- Expect: selections 3-4 then 0-1; untick Backward direction afterwards

### SEARCH-018: Match case narrows the matches
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "alpha Alpha alphabet\n"; Find what "alpha"; press Count with Match case off, then on.
- Expect: "Count: 3 matches", then "Count: 2 matches"

### SEARCH-019: Match whole word only narrows the matches
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "alpha Alpha alphabet\n"; Match case on; tick Match whole word only; Count "alpha". Then Normal mode "a.b" whole word in "a.b xa.b".
- Expect: "Count: 1 match"; the second count is "Count: 1 match" (word boundary around a literal with a dot)

### SEARCH-020: Normal mode takes regex metacharacters literally
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: For each of "a.c", "(x)", "[1]", "a*b", "$", "\\d": document containing each once plus look-alikes ("a.c abc (x) x [1] 1 a*b aab $ \\d 5"); Normal mode, Match case on; Count.
- Expect: each count is "Count: 1 match"

### SEARCH-021: Extended mode converts its escapes
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: For each (Find what, document, expected count): ("a\\tb", "a\tb a b", 1), ("\\n", "x\ny\nz", 2), ("\\x41", "ABA", 2), ("\\d065", "A", 1), ("\\o101", "A", 1), ("\\u0041", "A", 1), ("\\b01000001", "A", 1), ("\\\\", "a\\b", 1), ("\\q", "\\q q", 1): Extended mode, Match case on, Count.
- Expect: each status reads "Count: <expected> match(es)" with the expected number; an unknown escape "\\q" keeps its backslash

### SEARCH-022: Extended \r\n finds CRLF line endings
- Covers: IDM_SEARCH_FIND
- Channel: ui, files
- Steps: Open a file saved with CRLF endings "a\r\nb\r\nc\r\n"; Extended mode, Find what "\\r\\n"; Count; then Find what "\\n" alone; then "b\\r".
- Expect: "Count: 3 matches" for both "\\r\\n" and "\\n"; "Count: 1 match" for "b\\r"

### SEARCH-023: Regular expressions use Boost syntax
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: For each (pattern, document, count): ("\\d+", "one 11 two 22 three 333", 3), ("\\d{3}", same, 1), ("^.", "abc\ndef\n", 2), ("\\bfoo\\b", "foo food foo", 2), ("(?<=a)b", "ab cb", 1), ("\\p{Lu}", "aBcD", 2), ("[[:digit:]]+", "a1b22", 2), ("(?i)ABC", "abc", 1): Regular expression mode, Match case on, Count.
- Expect: each count as listed

### SEARCH-024: ". matches newline" decides whether . crosses line ends
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "a\nb\n"; regex "a.b"; Count with ". matches newline" off, then on; then document "a\r\nb" with "a..b" and the box on.
- Expect: "Count: 0 matches", then "Count: 1 match"; the CRLF document gives "Count: 1 match"

### SEARCH-025: $ and ^ anchor per line, also in CRLF documents
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: For each document "ab\ncd\n" and "ab\r\ncd\r\n": regex "b$", Count; then "^c", Count; then press Find Next on "d$" from caret 0.
- Expect: "Count: 1 match" for each pattern in both documents; Find Next selects "d" (not including "\r")

### SEARCH-026: An empty match does not trap Find Next
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "ab\ncd\nef\n"; regex "$"; caret at 0; press Find Next four times.
- Expect: the caret visits positions 2, 5, 8, 9 (the ends of lines 1-3 and of the empty last line), then wraps to 2; it never stays on the same position twice in a row

### SEARCH-027: An invalid regular expression is reported as invalid
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Regex mode, Find what "("; press Find Next, then Count; also "a{2,1}".
- Expect: the selection and document are unchanged and no alert is shown; the status line reads "Find: Invalid regular expression" as Notepad++ says (the port says `Find: Can't find the text "("` and "Count: 0 matches": likely defect)

### SEARCH-028: Count with no match, one match, and a huge number of matches
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document of 100000 "a" characters on 1000 lines; Count "a"; Count "aa" (non-overlapping); Count "b"; Count with Find what emptied.
- Expect: "Count: 100000 matches" within 10 s; "Count: 50000 matches"; "Count: 0 matches"; empty Find what gives "Count: 0 matches" and changes nothing

### SEARCH-029: Empty Find what does nothing on Find Next
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "abc", caret at 1; clear Find what; press Find Next.
- Expect: selection and document unchanged; no alert; nothing is added to the Find what history

### SEARCH-030: Unicode text is found and selected on the right bytes
- Covers: IDM_SEARCH_FIND
- Channel: ui, mcp
- Steps: Document "😀 café Ωμέγα 日本語 café\n"; for each of "café", "日本", "Ω", "😀": caret at 0, Find Next; then Count "CAFÉ" with Match case off.
- Expect: get_selection text equals the term each time; "Count: 2 matches" for "CAFÉ" (case folding beyond ASCII)

### SEARCH-031: Match whole word only treats accented letters as word characters
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "café naïve cafés CAFÉ\n"; Normal mode, Match case off; Count "café" with Match whole word only off, then on.
- Expect: "Count: 3 matches", then "Count: 2 matches" ("café" and "CAFÉ", not the "café" inside "cafés"), as Notepad++'s Unicode word boundaries give; the port's ASCII \b gives 1 match, the wrong one: likely defect

### SEARCH-032: \w and \b in a regular expression are Unicode-aware
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Regex mode; document "café naïve cafés CAFÉ\n"; Count "\w+"; Count "\bcaf\w\b" with Match case off.
- Expect: as Boost in Notepad++: "Count: 4 matches" for "\w+" (the port counts 6: caf, na, ve, caf, s, CAF: likely defect); "Count: 2 matches" for the second

### SEARCH-033: In selection limits Find Next and Count to the selection
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: Document "q q q q\n"; select 0-3; run IDM_SEARCH_FIND (In selection becomes enabled only when the dialog becomes key), tick In selection, then set Find what "q"; Count; untick; Count.
- Expect: "Count: 2 matches" with In selection, "Count: 4 matches" without

## Find All

### SEARCH-034: Find All in Current Document lists every hit line in the results tab
- Covers: IDM_SEARCH_FIND, IDM_FOCUS_ON_FOUND_RESULTS
- Channel: ui, mcp
- Steps: Untitled document "one two one\nthree one\nnone\n" (title "new N"); Find what "one", whole word off; press Find All in Current Document.
- Expect: a tab "Search results" is in front whose text is `Search "one" in new N\n\n\tLine 1: one two one\n\tLine 2: three one\n\tLine 3: none\n\n4 hits\n`; each line appears once however many hits it has; the results tab is read-only and not modified

### SEARCH-035: Find All closes the dialog unless told to stay open
- Covers: IDM_SEARCH_FIND
- Channel: ui, prefs
- Steps: Press Find All in Current Document with pref findDialogStaysOpen false; reopen; set findDialogStaysOpen true and press it again; restore the pref.
- Expect: first: the dialog is hidden afterwards; second: the dialog stays visible with status "N found"

### SEARCH-036: Find All for a saved file names its path, and a CRLF file reports clean lines
- Covers: IDM_SEARCH_FIND
- Channel: ui, files
- Steps: Save "alpha\r\nbeta alpha\r\n" to tmp/crlf.txt and open it; Find All in Current Document for "alpha".
- Expect: the report's first line is `Search "alpha" in <tmp>/crlf.txt`; hit lines are "\tLine 1: alpha" and "\tLine 2: beta alpha" with no "\r"; last line "2 hits"

### SEARCH-037: Find All in All Opened Documents searches every tab
- Covers: IDM_SEARCH_FIND
- Channel: ui, mcp
- Steps: Open three documents: "zqx first\nzqx again zqx\n", "second zqx\n", "nothing\n" (plus the initial empty new 1); make the second one current; press Find All in All Opened Documents for "zqx".
- Expect: the results text starts `Search "zqx" (4 hits in 2 files of 4 searched)`; it contains "(3 hits)\n\tLine 1: zqx first\n\tLine 2: zqx again zqx\n" under the first document's title and "(1 hit)" under the second's; the dialog status (if kept open) reads "4 found in all opened documents"; the searched documents are unchanged (the results tab is a tab here, so which tab is in front after closing it is not part of the case)

### SEARCH-038: Find All in All Opened Documents ignores In selection and the results tab itself
- Covers: IDM_SEARCH_FIND
- Channel: ui
- Steps: With an earlier results tab open containing "zqx" text, and a small selection ticked In selection in one document, run Find All in All Opened Documents for "zqx" twice.
- Expect: the second report's hit counts equal the first's (the results tab is not searched); every match in every document is counted, not only the selected part

## Replace

### SEARCH-039: Replace first selects a match, then replaces it and moves on
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Document "one one one\n", caret at 0; Find what "one", Replace with "1"; press Replace four times.
- Expect: after 1: text unchanged, selection 0-3; after 2: "1 one one\n" with the next "one" selected; after 3: "1 1 one\n"; after 4: "1 1 1\n" and status "Replace: no occurrence was found"

### SEARCH-040: Replace does not touch a selection that is not a match
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Document "abc one\n"; select "abc"; Find what "one", Replace with "X"; press Replace.
- Expect: text unchanged "abc one\n"; "one" (4-7) is selected

### SEARCH-041: Replace All replaces every match as one undo step
- Covers: IDM_SEARCH_REPLACE
- Channel: ui, mcp, keys
- Steps: Document "cat dog cat cat\n"; Replace All "cat" → "bird"; then IDM_EDIT_UNDO once.
- Expect: text "bird dog bird bird\n"; status "Replace All: 3 occurrences were replaced"; one undo restores "cat dog cat cat\n"

### SEARCH-042: Replace All status forms for one and none
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Replace All "dog" → "x" in "cat dog\n"; then Replace All "zzz" → "y".
- Expect: "Replace All: 1 occurrence was replaced"; then "Replace All: 0 occurrences were replaced" and the text unchanged

### SEARCH-043: Replace All does not re-search its own output
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Document "aaa\n"; Replace All "a" → "aa".
- Expect: text "aaaaaa\n"; status "Replace All: 3 occurrences were replaced"

### SEARCH-044: Replace All in selection only changes the selection
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Document "q q q q\n"; select 0-3; run IDM_SEARCH_REPLACE so the dialog becomes key; tick In selection; set Find what "q", Replace with "Z"; Replace All.
- Expect: text "Z Z q q\n"; status "Replace All: 2 occurrences were replaced"

### SEARCH-045: Replace with an empty replacement deletes the matches
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Document "a-b-c\n"; Replace with empty; Replace All "-".
- Expect: text "abc\n"; status "Replace All: 2 occurrences were replaced"

### SEARCH-046: Extended replacement escapes
- Covers: IDM_SEARCH_REPLACE
- Channel: ui, mcp
- Steps: Extended mode. For each (document, find, replace, result): ("a,b", ",", "\\n", "a\nb"), ("a,b", ",", "\\t", "a\tb"), ("a,b", ",", "\\x41", "aAb"), ("a\nb", "\\n", " ", "a b"), ("a-b", "-", "\\0", "a<NUL>b"): Replace All.
- Expect: document text equals the result; the NUL case leaves a 3-character document whose middle character is U+0000

### SEARCH-047: Normal-mode replacement is literal text
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Normal mode; document "x\n"; Replace All "x" → "$1\\n\\2".
- Expect: text "$1\\n\\2\n" exactly (no escapes or groups interpreted)

### SEARCH-048: Regex back-references in \n and $n form
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Regex mode. "john smith\njane doe\n" with "(\\w+) (\\w+)" → "\\2, \\1"; "ab\n" with "(a)(b)(c)?" → "$2$1$3"; "abcdefghij" with "(a)(b)(c)(d)(e)(f)(g)(h)(i)(j)" → "\\10|$10|${1}0".
- Expect: "smith, john\ndoe, jane\n" with status "Replace All: 2 occurrences were replaced"; "ba\n" (an unmatched group adds nothing); "a0|j|a0"

### SEARCH-049: Boost format features in the replacement
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Regex mode, Match case on. For each (document, pattern, replacement, result): ("xx ab-12 yy", "(?<w>[a-z]+)-(\\d+)", "[$+{w}|$2|$&|$$|$`|$']", "xx [ab|12|ab-12|$|xx | yy] yy"), ("a1 b", "([a-z])(\\d)?", "(?2<$1$2>:[$1])", "<a1> [b]"), ("q", "q", "\\x41\\x{263A}\\\\", "A☺\\"), ("x", "x", "\\d+", "d+"): Replace All.
- Expect: each document equals its result

### SEARCH-050: Case-changing escapes in a regex replacement
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Regex mode. "hello world" with "(\\w+) (\\w+)" → "\\U\\1\\E \\2"; "HELLO WORLD" → "\\L\\1 \\2"; "hello world" → "\\u\\1 \\u\\2"; "john smith\n" with "^(\\w)" → "\\U$1".
- Expect: "HELLO world", "hello world", "Hello World", "John smith\n"

### SEARCH-051: A lookahead match survives Replace
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Regex mode; document "foobar foobaz foobar\n"; Find what "foo(?=bar)", Replace with "X"; caret at 0; press Replace three times.
- Expect: text "Xbar foobaz Xbar\n"; the "foo" of "foobaz" is never replaced

### SEARCH-052: Regex replace with . matches newline joins lines
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Regex mode, document "a\nb\n"; Replace All "a.b" → "X" with ". matches newline" off, then on.
- Expect: off: "Replace All: 0 occurrences were replaced", text unchanged; on: text "X\n", "Replace All: 1 occurrence was replaced"

### SEARCH-053: Replace All with an invalid regex changes nothing and says why
- Covers: IDM_SEARCH_REPLACE
- Channel: ui
- Steps: Regex mode; document "a(b\n"; Replace All "(" → "x".
- Expect: text unchanged; status reports an invalid regular expression (Notepad++ "Find: Invalid regular expression"; the port says "Replace All: 0 occurrences were replaced": likely defect)

### SEARCH-054: Replace All on a read-only document changes nothing
- Covers: IDM_SEARCH_REPLACE
- Channel: ui, menu
- Steps: Document "cat\n"; IDM_EDIT_TOGGLEREADONLY on; Replace All "cat" → "dog"; turn read-only off again.
- Expect: text still "cat\n"; the document is not modified

### SEARCH-055: Replace All in All Opened Documents asks, then replaces everywhere
- Covers: IDM_SEARCH_REPLACE
- Channel: ui, modal
- Steps: Documents "cat dog cat\n" and "cat\n"; Replace tab "cat" → "CAT"; queue alert answer 2 (Cancel) and press Replace All in All Opened Documents; then queue 1 and press it again.
- Expect: the alert logged has message "Replace All in All Opened Documents", informative "Are you sure you want to replace all occurrences in all open documents?", buttons Replace, Cancel; after Cancel both texts unchanged; after Replace "CAT dog CAT\n" and "CAT\n", status "Replace in Opened Files: 3 occurrences were replaced"

### SEARCH-056: Replace All in All Opened Documents without the confirmation
- Covers: IDM_SEARCH_REPLACE
- Channel: ui, prefs, modal
- Steps: Set pref confirmReplaceAllOpenDocs false; with two documents containing "a", press Replace All in All Opened Documents "a" → "b"; restore the pref.
- Expect: no alert in the modal log; both documents replaced; status "Replace in Opened Files: 2 occurrences were replaced" (or the count in upstream's form)

### SEARCH-057: Replace history keeps the replacements
- Covers: IDM_SEARCH_REPLACE
- Channel: ui, prefs
- Steps: Press Replace All with Replace with "r1", then "r2"; read the Replace with combo items and pref replaceHistory; restore it.
- Expect: items start ["r2", "r1"]; replaceHistory matches

## Find in Files and Replace in Files

### SEARCH-058: Find in Files over a folder lists every hit with its file and line
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, files
- Steps: tmp tree: a.txt "hello needle\nplain\n", b.log "needle again\r\nneedle twice\r\n", sub/c.txt "needle deep\n", .hid/d.txt "needle hidden\n", bin.dat with NUL bytes and "needle". Find in Files tab: Find what "needle", Directory tmp, Filters empty, sub-folders on, hidden off; press Find All; wait for the status to end in "found".
- Expect: status "4 found"; the results tab starts `Search "needle" (<tmp>)`, holds "<tmp>/a.txt (1 hit)\n\tLine 1: hello needle", "<tmp>/b.log (2 hits)\n\tLine 1: needle again\n\tLine 2: needle twice" (no "\r"), "<tmp>/sub/c.txt (1 hit)"; it does not mention .hid or bin.dat; it ends "4 hits in 3 files"

### SEARCH-059: Filters include and exclude files and folders
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, files
- Steps: Same tree as SEARCH-058. For each filter: "*.txt", "*.log", "*.txt *.log", "!*.log", "*.* !\\sub", "*.TXT": Find All and read the report.
- Expect: "*.txt": a.txt and sub/c.txt only; "*.log": b.log only; both: all three; "!*.log": a.txt and sub/c.txt; "!\\sub": a.txt and b.log; "*.TXT": matches case-insensitively (a.txt, sub/c.txt)

### SEARCH-060: In all sub-folders and In hidden folders
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, files
- Steps: Same tree. Find All with sub-folders off; then sub-folders on and hidden on.
- Expect: off: only a.txt and b.log files ("3 hits in 2 files"); with hidden: .hid/d.txt appears too ("5 hits in 4 files")

### SEARCH-061: Find in Files honours the mode and options
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, files
- Steps: Folder with x.txt "Needle\nneedle\nneedles\n". Find All "needle" with Match case on; then whole word on; then regex "^need.e$" with case off.
- Expect: "2 found" then "1 found" (line 2) then "2 found" (lines 1 and 2)

### SEARCH-062: Find in Files reads other encodings
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, files
- Steps: Folder with u16.txt (UTF-16 LE with BOM) "héllo needle\n", latin.txt (ISO-8859-1 bytes) "caf\xe9 needle\n", utf8bom.txt (UTF-8 BOM) "needle\n"; Find All "needle"; then Find All "café".
- Expect: "3 found" listing all three files; "café" is found in latin.txt ("1 found")

### SEARCH-063: Find in Files with no directory, a missing folder, or an empty term
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui
- Steps: Directory empty → Find All; Directory "/nonexistent/folder" → Find All; Directory tmp with Find what empty → Find All.
- Expect: first: status "Choose a folder first" and no results tab created; second: status "0 found" and a report ending "0 hits in 0 files"; third: no hits, nothing replaced or opened, no crash

### SEARCH-064: From doc and Browse… fill the Directory
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, modal
- Steps: Open tmp/sub/c.txt; on the Find in Files tab click "From doc"; then with an untitled document in front click "From doc"; then queue a panel answer tmp and click "Browse…"; then queue None and click it again.
- Expect: Directory becomes "<tmp>/sub"; the untitled case leaves it and sets status "This document has no folder"; Browse sets Directory to tmp; the cancelled panel leaves Directory at tmp

### SEARCH-065: The Directory fills from the active document when asked
- Covers: IDM_SEARCH_FINDINFILES
- Channel: menu, ui, prefs
- Steps: With pref fillDirectoryFromActiveDocument false and Directory already "/tmp", open tmp/sub/c.txt and run IDM_SEARCH_FINDINFILES; then set the pref true and run it again; restore.
- Expect: first Directory stays "/tmp"; second Directory is "<tmp>/sub"

### SEARCH-066: Filters and Directory histories are kept
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, prefs
- Steps: Find All with Filters "*.txt" in tmp, then Filters "*.log" in tmp/sub; read the two combos' items and prefs filterHistory, directoryHistory; restore them.
- Expect: Filters items start ["*.log", "*.txt"]; Directory items start ["<tmp>/sub", "<tmp>"]

### SEARCH-067: Find in Files does not block and can be stopped
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, files
- Steps: Create 3000 files of 20 KB each containing "needle" once; Find All; while the Stop button is visible click it; wait for the status.
- Expect: while running, Stop is visible, Find All and Replace in Files are disabled and get_document still answers; after Stop the status ends "(stopped)", the report ends " - search stopped", Stop is hidden and the buttons are enabled again

### SEARCH-068: Find in Files shows progress while it runs
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui
- Steps: With the 3000-file tree, press Find All and poll the status line and the results tab.
- Expect: at some point the status reads "<n> files searched, <m> found" with n > 0 before the final "3000 found"; the results tab grows while the search runs

### SEARCH-069: Replace in Files asks first; Cancel leaves the files alone
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, modal, files
- Steps: Tree of SEARCH-058; Find what "needle", Replace with "PIN", Filters empty; queue alert 2; press Replace in Files.
- Expect: an alert "Are you sure?" whose informative text contains "Are you sure you want to replace all occurrences in:", the folder path, "For file type:" and "*.*"; after Cancel every file on disk is byte-identical

### SEARCH-070: Replace in Files rewrites matching files on disk
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, modal, files
- Steps: Same tree; Filters "*.txt"; queue alert 1; press Replace in Files; wait for the status.
- Expect: status "2 replaced in 2 files"; a.txt reads "hello PIN\nplain\n", sub/c.txt "PIN deep\n"; b.log, .hid/d.txt and bin.dat are unchanged; the alert's informative text names "*.txt"

### SEARCH-071: Replace in Files keeps encodings, BOM and line endings
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, modal, files
- Steps: Folder with u16.txt (UTF-16 LE BOM, CRLF) "one needle\r\n", bom.txt (UTF-8 BOM) "needle\n", latin.txt (Latin-1) "caf\xe9 needle\n"; Replace in Files "needle" → "pin" (confirm with 1).
- Expect: u16.txt still starts FF FE and decodes to "one pin\r\n"; bom.txt starts EF BB BF and reads "pin\n"; latin.txt bytes are "caf\xe9 pin\n"; status "3 replaced in 3 files"

### SEARCH-072: Replace in Files with regex back-references
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, modal, files
- Steps: Folder with names.txt "john smith\njane doe\n"; regex "(\\w+) (\\w+)" → "\\2 \\1"; Replace in Files (confirm).
- Expect: names.txt reads "smith john\ndoe jane\n"; status "2 replaced in 1 file"

### SEARCH-073: Replace in Files with no directory
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, modal
- Steps: Directory empty; press Replace in Files.
- Expect: no alert is shown; status "Choose a folder first"

## Find in Projects

### SEARCH-074: Find in Projects searches the files of the ticked project panels
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, prefs, files
- Steps: Write tmp/ws.xml, a Notepad++ workspace with project "P" listing tmp/p1.txt ("needle one\n") and tmp/p2.txt ("none\n"); set pref projectWorkspaces {"1": "<tmp>/ws.xml"} (or load it into Project Panel 1); open the dialog, select "Find in Projects", Project Panel 1 ticked; Find All "needle".
- Expect: status "1 found"; the results tab starts `Search "needle" (the projects)` and lists "<tmp>/p1.txt (1 hit)\n\tLine 1: needle one"; p2.txt is not listed

### SEARCH-075: Find in Projects with no files in the ticked panels
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui
- Steps: No workspace loaded; untick Project Panel 1, tick Project Panel 3; press Find All on the Find in Projects tab.
- Expect: status "The ticked project panels have no files"; no results tab is created

### SEARCH-076: Replace in Projects asks and rewrites the project files
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, modal, files
- Steps: Workspace of SEARCH-074; Replace with "pin"; queue alert 1; press Replace in Projects; wait for the status.
- Expect: alert "Are you sure?" with informative "Do you want to replace all occurrences in all documents in the selected Project Panel(s)?"; p1.txt reads "pin one\n"; status "1 replaced in 1 file"; with alert answer 2 instead nothing changes on disk

## The Search results tab

### SEARCH-077: Search Results Window brings the results tab to the front
- Covers: IDM_FOCUS_ON_FOUND_RESULTS
- Channel: menu, mcp
- Steps: Run Find All in Current Document, switch back to the searched document, run IDM_FOCUS_ON_FOUND_RESULTS; then close the results tab and run it again.
- Expect: first: the current tab is "Search results" and its text is the report; second: nothing changes (the current document stays), no new tab is created

### SEARCH-078: Only one results tab, reused by every search
- Covers: IDM_SEARCH_FINDINFILES, IDM_FOCUS_ON_FOUND_RESULTS
- Channel: ui, mcp
- Steps: Run Find All in Current Document three times with different terms, and Find in Files once; count tabs titled "Search results" (via tab titles in e2e_ui of the main window or the window list).
- Expect: exactly one "Search results" tab; a user document that happens to be named "Search results" is left alone

### SEARCH-079: Newer searches go on top and older ones fold away
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, mcp
- Steps: Find All "one" then Find All "two" in the same document (purge off); read the results text and e2e_sci SCI_GETFOLDLEVEL / SCI_GETFOLDEXPANDED for the "Search \"" header lines.
- Expect: the text starts with the "two" search and ends with the "one" search; header lines carry SC_FOLDLEVELHEADERFLAG; file lines are one level deeper, hit lines two; the newest header is expanded, the older one contracted

### SEARCH-080: Purge for every search keeps only the newest search
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, prefs
- Steps: Set pref searchResultsPurge true; run two Find All searches; restore the pref.
- Expect: the results text contains only the second search

### SEARCH-081: Next and Previous Search Result step through hit lines
- Covers: IDM_SEARCH_GOTONEXTFOUND, IDM_SEARCH_GOTOPREVFOUND
- Channel: menu, mcp
- Steps: After the Find in Files of SEARCH-058 (4 hit lines), put the caret on line 1 of the results; run IDM_SEARCH_GOTONEXTFOUND five times, then IDM_SEARCH_GOTOPREVFOUND once.
- Expect: the caret moves to each "\tLine " line in turn, skipping file headers and blank lines; after the last hit the fifth Next leaves it on the last hit; Previous moves back one hit line; the results tab is in front throughout

### SEARCH-082: Next Search Result with no results does nothing
- Covers: IDM_SEARCH_GOTONEXTFOUND, IDM_SEARCH_GOTOPREVFOUND
- Channel: menu, mcp
- Steps: With no results tab, in document "abc", run IDM_SEARCH_GOTONEXTFOUND and IDM_SEARCH_GOTOPREVFOUND.
- Expect: the current document, its text and caret are unchanged; no tab is created

### SEARCH-083: Going to a result opens the file on that line
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, mcp
- Steps: tmp/target.txt "one\ntwo\nthree needle\nfour\n" not open; Find in Files "needle" in tmp; in the results put the caret on the "\tLine 3:" line and double-click it (requested hook; until then `invoke("editor", "openSearchResultAtCaret")`).
- Expect: target.txt is opened and current; line 3 is selected whole ("three needle"); a second open of the same result does not open a second tab

### SEARCH-084: Going to a result of an untitled document selects that tab
- Covers: IDM_SEARCH_FIND
- Channel: ui, mcp
- Steps: Untitled "a\nb needle\n" plus another tab; Find All in Current Document "needle"; go to the "\tLine 2:" result (as SEARCH-083).
- Expect: the untitled tab becomes current with line 2 selected

### SEARCH-085: A file heading or the search header goes to line 1, the folder is not a result
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, mcp
- Steps: After Find in Files, go to the result on a file heading line "<path> (1 hit)"; then on the `Search "needle" (<tmp>)` header line; then on the summary line.
- Expect: the heading opens the file with line 1 selected; the header and summary open nothing (no new tab, results tab stays current)

### SEARCH-086: Results tab menu: copy lines and pathnames
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, clipboard
- Steps: After Find in Files over a.txt ("alpha one", "alpha two" on lines 1-2), select from the file heading to the second hit in the results; use the results tab's "Copy Selected Line(s)" then "Copy Selected Pathname(s)" (results context menu; requested hook, until then invoke editor resultsCopyLines:/resultsCopyPaths:).
- Expect: clipboard "alpha one\nalpha two" (without "Line n:"); then "<tmp>/a.txt"

### SEARCH-087: Results tab menu: fold all, unfold all, delete this search, clear all
- Covers: IDM_SEARCH_FINDINFILES
- Channel: ui, mcp
- Steps: With two stacked searches: Fold all, Unfold all (read SCI_GETFOLDEXPANDED of both headers); caret in the newer search, Delete This Search; then Clear all.
- Expect: fold all contracts both headers, unfold all expands both; delete leaves exactly the older search's text; clear all leaves an empty results tab that is not modified

### SEARCH-088: The results tab is read-only
- Covers: IDM_FOCUS_ON_FOUND_RESULTS
- Channel: keys, mcp
- Steps: Bring the results tab to the front and type "xyz"; press delete.
- Expect: the results text is unchanged; the tab is not marked modified

## Mark tab

### SEARCH-089: Mark All marks every match with the Find Mark style
- Covers: IDM_SEARCH_FIND
- Channel: ui, mcp
- Steps: Document "one two one\nthree one\n"; Mark tab, Find what "one", Purge on; press Mark All; read indicator 13 with SCI_INDICATORVALUEAT at each position.
- Expect: status "Mark: 3 matches"; indicator 13 covers exactly 0-3, 8-11, 18-21 and nothing else

### SEARCH-090: Mark All with Bookmark line bookmarks the matching lines
- Covers: IDM_SEARCH_FIND
- Channel: ui, mcp
- Steps: Document "a x\nb\nc x\nd x x\n"; tick Bookmark line and Purge; Mark All "x"; read the `bookmarks` tool.
- Expect: bookmarked lines [1, 3, 4]; status "Mark: 4 matches"

### SEARCH-091: Without Purge, marks and bookmarks of earlier searches stay
- Covers: IDM_SEARCH_FIND
- Channel: ui, mcp
- Steps: Document "one\ntwo one\ntwo\n"; Purge off, Bookmark line on: Mark All "one", then Mark All "two"; then Purge on and Mark All "two".
- Expect: after the second: indicator 13 covers both "one"s and both "two"s, bookmarks [1, 2, 3]; after the purged one: only the "two"s are marked and bookmarks are [2, 3] (line 1, bookmarked only for "one", loses its bookmark)

### SEARCH-092: Clear all marks and Copy Marked Text
- Covers: IDM_SEARCH_FIND
- Channel: ui, clipboard
- Steps: Mark All "two" in "one two one two\n"; press Copy Marked Text; press Clear all marks; press Copy Marked Text again.
- Expect: clipboard "two\ntwo" and status "Marked text copied"; after clearing, status "Marks cleared" and no indicator 13 remains; the last copy leaves the clipboard as it was and says "Nothing is marked"

### SEARCH-093: Mark All with regex and In selection
- Covers: IDM_SEARCH_FIND
- Channel: ui, mcp
- Steps: Document "a1 b22 c333\n"; regex "\\d+" Mark All; then select "b22 " (3-7), bring the dialog back to key with IDM_SEARCH_FIND and the Mark segment, set Find what "\\d+" again, tick In selection and Purge, Mark All.
- Expect: "Mark: 3 matches" marking 1-2, 4-6, 8-11; then "Mark: 1 match" marking only 4-6

## Search menu: Find Next / Previous, Select and Find, Volatile, Incremental

### SEARCH-094: Find Next and Find Previous repeat the dialog's last search
- Covers: IDM_SEARCH_FINDNEXT, IDM_SEARCH_FINDPREV
- Channel: menu, keys, mcp
- Steps: Document "x1 x2 x3\n"; in the dialog Find Next "x" once (selects 0-1) and close it; run IDM_SEARCH_FINDNEXT twice, IDM_SEARCH_FINDPREV once; press cmd+g once.
- Expect: selections 3-4, 6-7, then 3-4 (Previous), then 6-7; the dialog stays closed

### SEARCH-095: Find Next / Previous ignore the dialog's Backward box
- Covers: IDM_SEARCH_FINDNEXT, IDM_SEARCH_FINDPREV
- Channel: menu, ui
- Steps: In the dialog tick Backward direction and Find Next "x" in "x x x\n" from the end; close it; run IDM_SEARCH_FINDNEXT from caret 0, then IDM_SEARCH_FINDPREV.
- Expect: Find Next moves forward (0-1 then onward), Find Previous backward, whatever the box says

### SEARCH-096: Find Next with nothing searched yet opens the dialog
- Covers: IDM_SEARCH_FINDNEXT, IDM_SEARCH_FINDPREV
- Channel: menu, ui
- Steps: (fresh_app) Document "abc"; run IDM_SEARCH_FINDNEXT; close the dialog; run IDM_SEARCH_FINDPREV.
- Expect: each time the dialog opens on the Find tab; the selection is unchanged

### SEARCH-097: Find Next without a match leaves the selection
- Covers: IDM_SEARCH_FINDNEXT
- Channel: menu, mcp
- Steps: Search "zzz" once in the dialog on "abc" (no match); close; run IDM_SEARCH_FINDNEXT with caret at 1.
- Expect: selection unchanged, document unchanged, no alert

### SEARCH-098: Select and Find Next / Previous use the selection and the dialog's options
- Covers: IDM_SEARCH_SETANDFINDNEXT, IDM_SEARCH_SETANDFINDPREV
- Channel: menu, ui, mcp
- Steps: Document "Word word Word\n"; Match case ticked in the dialog; select 0-4 ("Word"); run IDM_SEARCH_SETANDFINDNEXT; then IDM_SEARCH_SETANDFINDPREV.
- Expect: selection 10-14 (the lowercase "word" is skipped); Find what reads "Word" and heads the Find what history; Previous goes back to 0-4

### SEARCH-099: Select and Find Next takes the word under the caret
- Covers: IDM_SEARCH_SETANDFINDNEXT
- Channel: menu, mcp
- Steps: Document "foo bar foo\n"; caret inside the first "foo" (column 2) with nothing selected; run IDM_SEARCH_SETANDFINDNEXT; then at the last "foo" run it again.
- Expect: selection 8-11; then wraps to 0-3 (Wrap around on)

### SEARCH-100: Select and Find Next with no word at the caret does nothing
- Covers: IDM_SEARCH_SETANDFINDNEXT, IDM_SEARCH_SETANDFINDPREV
- Channel: menu, mcp
- Steps: Document "   \n" with the caret at 1; run both commands.
- Expect: selection and Find what unchanged

### SEARCH-101: Find Next continues what Select and Find Next started
- Covers: IDM_SEARCH_SETANDFINDNEXT, IDM_SEARCH_FINDNEXT
- Channel: menu, mcp
- Steps: (fresh_app, no dialog search yet) Document "foo a foo b foo\n"; select the first "foo"; run IDM_SEARCH_SETANDFINDNEXT, then IDM_SEARCH_FINDNEXT.
- Expect: selections 6-9 then 12-15 as in Notepad++ (F3 continues with Find what); the port opens the Find dialog instead: likely defect

### SEARCH-102: Volatile Find Next / Previous use the selection, any case, wrapping
- Covers: IDM_SEARCH_VOLATILE_FINDNEXT, IDM_SEARCH_VOLATILE_FINDPREV
- Channel: menu, ui, mcp
- Steps: With the dialog open, Match case ticked and Find what "untouched"; document "Word word Word\n"; select 10-14; run IDM_SEARCH_VOLATILE_FINDNEXT; then select 0-4 and run it; then IDM_SEARCH_VOLATILE_FINDPREV.
- Expect: first wraps to 0-4 and the dialog status reads "Find: Reached document end, first occurrence from the top found."; second selects 5-9 (case ignored) with an empty status; Previous selects 0-4; Find what still reads "untouched"

### SEARCH-103: Volatile Find with no selection does nothing
- Covers: IDM_SEARCH_VOLATILE_FINDNEXT, IDM_SEARCH_VOLATILE_FINDPREV
- Channel: menu, mcp
- Steps: Document "foo foo\n", caret inside the first "foo" with nothing selected; run both commands.
- Expect: the caret and selection are unchanged (the word under the caret is not used)

### SEARCH-104: Incremental Search finds the typed term from the caret, wrapping
- Covers: IDM_SEARCH_FINDINCREMENT
- Channel: menu, modal, mcp
- Steps: Document "aa bb aa cc aa\n", caret at 7; queue alert {button 1, field "CC"}; run IDM_SEARCH_FINDINCREMENT; then caret at 13, queue {1, "aa"} and run it.
- Expect: the prompt "Incremental search" was shown; "cc" (9-11) is selected (case ignored); the second selects 0-2 after wrapping

### SEARCH-105: Incremental Search remembers the term and can be cancelled
- Covers: IDM_SEARCH_FINDINCREMENT
- Channel: menu, modal, mcp
- Steps: Document "aa bb aa\n", caret at 0; run IDM_SEARCH_FINDINCREMENT answering {1, "bb"}; then queue alert 2 (Cancel) and run it again with the caret at 0; then queue {1, "zzz"} and run it.
- Expect: the second prompt's field (in the modal log) held "bb"; Cancel leaves the caret at 0 with nothing selected; "zzz" (absent) leaves the selection unchanged

## Mark... and token styles

### SEARCH-106: Mark... marks every whole-word occurrence with the Find Mark style
- Covers: IDM_SEARCH_MARK
- Channel: menu, ui, mcp
- Steps: Document "foo bar foo foobar Foo\n"; run IDM_SEARCH_MARK (it opens the Find dialog on its Mark tab, as upstream's MARK_DLG); Find what "foo", Match whole word only on, Match case off, Purge on; press Mark All; read indicator 13.
- Expect: indicator 13 covers 0-3, 8-11 and 19-22 (whole word, any case) but not "foobar".

### SEARCH-107: Mark... with a term that is not in the document marks nothing
- Covers: IDM_SEARCH_MARK
- Channel: menu, modal, mcp
- Steps: Document "foo bar foo\n"; queue {1, "zzz"}; run IDM_SEARCH_MARK; read indicator 13.
- Expect: no position carries indicator 13 (the port marks the word at the start of the document, "foo": likely defect)

### SEARCH-108: Mark... opens the Find dialog on its Mark tab (known gap)
- Covers: IDM_SEARCH_MARK
- Channel: menu, ui
- Steps: Run IDM_SEARCH_MARK.
- Expect: as in Notepad++ (and README's "Mark"), the dialog opens with the Mark segment selected and title "Mark"; the port shows a one-field prompt instead

### SEARCH-109: Style All Occurrences of Token marks each style's own token
- Covers: IDM_SEARCH_MARKALLEXT1, IDM_SEARCH_MARKALLEXT2, IDM_SEARCH_MARKALLEXT3, IDM_SEARCH_MARKALLEXT4, IDM_SEARCH_MARKALLEXT5
- Channel: menu, mcp
- Steps: For each style n in 1..5: document "foo bar foo foobar Foo\nbar foo\n"; select 0-3; run IDM_SEARCH_MARKALLEXTn; then click away (caret to 2:1) and read indicator 7+n.
- Expect: indicator 7+n covers 0-3, 8-11, 19-22, 27-30 (whole word, any case); "foobar" is not styled; no other style's indicator is set (for style 5 the marks must survive the caret move: the port's smart highlighting reuses indicator 12 and wipes them: likely defect)

### SEARCH-110: Style All Occurrences uses the word under the caret and respects its settings
- Covers: IDM_SEARCH_MARKALLEXT1
- Channel: menu, prefs, mcp
- Steps: Caret inside "foo" with no selection, run IDM_SEARCH_MARKALLEXT1; then set markAllCaseSensitive true and run again; then markAllWordOnly false and run again; restore both prefs.
- Expect: 4 styled ranges; then 3 (not "Foo"); then 4 including the "foo" of "foobar" but not "Foo"

### SEARCH-111: Styling again replaces the style's previous token; styles coexist
- Covers: IDM_SEARCH_MARKALLEXT1, IDM_SEARCH_MARKALLEXT2
- Channel: menu, mcp
- Steps: Style 1 on "foo", then style 1 on "bar", then style 2 on "foo".
- Expect: indicator 8 covers only the "bar"s; indicator 9 covers the "foo"s

### SEARCH-112: Style All with nothing under the caret does nothing
- Covers: IDM_SEARCH_MARKALLEXT1
- Channel: menu, mcp
- Steps: Document "   \n", caret at 1; run IDM_SEARCH_MARKALLEXT1.
- Expect: no indicator 8 anywhere; document unchanged

### SEARCH-113: Style One Token styles only the selection
- Covers: IDM_SEARCH_MARKONEEXT1, IDM_SEARCH_MARKONEEXT2, IDM_SEARCH_MARKONEEXT3, IDM_SEARCH_MARKONEEXT4, IDM_SEARCH_MARKONEEXT5
- Channel: menu, mcp
- Steps: For each style n: document "foo bar foo\n"; select 4-7 ("bar") and run IDM_SEARCH_MARKONEEXTn; then select 8-11 and run it again; move the caret.
- Expect: indicator 7+n covers 4-7 and 8-11 only (One Token adds, it does not purge); the first "foo" is not styled

### SEARCH-114: Style One Token without a selection does nothing
- Covers: IDM_SEARCH_MARKONEEXT1
- Channel: menu, mcp
- Steps: Caret inside "foo" with nothing selected; run IDM_SEARCH_MARKONEEXT1.
- Expect: no indicator 8 anywhere

### SEARCH-115: Clear Style removes one style and leaves the others
- Covers: IDM_SEARCH_UNMARKALLEXT1, IDM_SEARCH_UNMARKALLEXT2, IDM_SEARCH_UNMARKALLEXT3, IDM_SEARCH_UNMARKALLEXT4, IDM_SEARCH_UNMARKALLEXT5
- Channel: menu, mcp
- Steps: For each n: style "foo" with style n and "bar" with another style m ≠ n (One Token); run IDM_SEARCH_UNMARKALLEXTn.
- Expect: indicator 7+n is gone everywhere; indicator 7+m is untouched

### SEARCH-116: Clear all Styles removes the five styles and the Find Mark style
- Covers: IDM_SEARCH_CLEARALLMARKS
- Channel: menu, mcp
- Steps: Style tokens with all five styles and Mark All with the dialog; run IDM_SEARCH_CLEARALLMARKS.
- Expect: indicators 8-13 are clear over the whole document; bookmarks are not touched

### SEARCH-117: Jump Down / Jump Up move between a style's ranges and wrap
- Covers: IDM_SEARCH_GONEXTMARKER1, IDM_SEARCH_GONEXTMARKER2, IDM_SEARCH_GONEXTMARKER3, IDM_SEARCH_GONEXTMARKER4, IDM_SEARCH_GONEXTMARKER5, IDM_SEARCH_GOPREVMARKER1, IDM_SEARCH_GOPREVMARKER2, IDM_SEARCH_GOPREVMARKER3, IDM_SEARCH_GOPREVMARKER4, IDM_SEARCH_GOPREVMARKER5
- Channel: menu, mcp
- Steps: For each n: "foo bar foo foobar Foo\nbar foo\n" styled with style n on "foo" (Style All); caret at 1:1 (before, not inside, a selection); run IDM_SEARCH_GONEXTMARKERn four times, then IDM_SEARCH_GOPREVMARKERn twice.
- Expect: Jump Down selects 8-11, 19-22, 27-30, then wraps to 0-3; Jump Up from 0-3 wraps to 27-30, then 19-22

### SEARCH-118: Jump Up / Down on a style with no ranges does nothing
- Covers: IDM_SEARCH_GONEXTMARKER3, IDM_SEARCH_GOPREVMARKER3
- Channel: menu, mcp
- Steps: No style 3 anywhere; caret at 5; run both commands.
- Expect: caret and selection unchanged

### SEARCH-119: Jump Down / Up over the Find Mark style
- Covers: IDM_SEARCH_GONEXTMARKER_DEF, IDM_SEARCH_GOPREVMARKER_DEF
- Channel: menu, ui, mcp
- Steps: Mark All "find" in "find me find\nfind\n" (dialog, Mark tab); caret at end; run IDM_SEARCH_GONEXTMARKER_DEF, then IDM_SEARCH_GOPREVMARKER_DEF twice.
- Expect: Jump Down wraps to 0-4; Jump Up wraps to 13-17 then 8-12

### SEARCH-120: Copy Styled Text copies a style's text, one range per line
- Covers: IDM_SEARCH_STYLE1TOCLIP, IDM_SEARCH_STYLE2TOCLIP, IDM_SEARCH_STYLE3TOCLIP, IDM_SEARCH_STYLE4TOCLIP, IDM_SEARCH_STYLE5TOCLIP
- Channel: menu, clipboard
- Steps: For each n: "foo bar foo foobar Foo\nbar foo\n", Style All "foo" with style n, move the caret to 2:1 without selecting; run IDM_SEARCH_STYLEnTOCLIP.
- Expect: clipboard "foo\nfoo\nFoo\nfoo"; for style 5 this requires the style to survive the caret move (see SEARCH-109)

### SEARCH-121: Copy Styled Text of an unused style empties the clipboard text
- Covers: IDM_SEARCH_STYLE2TOCLIP
- Channel: menu, clipboard
- Steps: Clipboard "before"; nothing styled with style 2; run IDM_SEARCH_STYLE2TOCLIP.
- Expect: clipboard text is "" (the port writes an empty string)

### SEARCH-122: Copy Styled Text › All Styles gathers the five styles in order and nothing else
- Covers: IDM_SEARCH_ALLSTYLESTOCLIP
- Channel: menu, clipboard
- Steps: "foo bar baz\n": Style One Token "baz" with style 3, "foo" with style 1; select "bar" and leave it selected (smart highlighting active); Mark All "bar" with the dialog; run IDM_SEARCH_ALLSTYLESTOCLIP.
- Expect: clipboard "foo\nbaz" (style 1 before style 3); neither the Find Mark text nor smart-highlighted "bar" is included (the port includes smart highlights through indicator 12: likely defect)

### SEARCH-123: Copy Styled Text › Find Mark Style copies the marked text
- Covers: IDM_SEARCH_MARKEDTOCLIP
- Channel: menu, ui, clipboard
- Steps: Mark All "find" in "find me find\n" with the dialog; run IDM_SEARCH_MARKEDTOCLIP.
- Expect: clipboard "find\nfind"

## Bookmarks

### SEARCH-124: Toggle Bookmark adds and removes the caret line's bookmark
- Covers: IDM_SEARCH_TOGGLE_BOOKMARK
- Channel: menu, mcp
- Steps: "l1\nl2\nl3\nl4\n"; caret on line 2; run IDM_SEARCH_TOGGLE_BOOKMARK; caret on line 4, run it; run it again on line 4.
- Expect: `bookmarks` lists [2, 4] after the second, [2] after the third; SCI_MARKERGET of line index 1 has bit 1 set

### SEARCH-125: Next and Previous Bookmark move and wrap
- Covers: IDM_SEARCH_NEXT_BOOKMARK, IDM_SEARCH_PREV_BOOKMARK
- Channel: menu, mcp
- Steps: Bookmarks on lines 2 and 4 of a five-line document; caret line 1: Next three times; then Previous three times.
- Expect: Next: lines 2, 4, 2 (wraps); Previous from 2: 4 (wraps), 2, 4

### SEARCH-126: Next / Previous Bookmark with no bookmarks does nothing
- Covers: IDM_SEARCH_NEXT_BOOKMARK, IDM_SEARCH_PREV_BOOKMARK
- Channel: menu, mcp
- Steps: Caret at line 3 column 2 of a document without bookmarks; run both.
- Expect: caret unchanged

### SEARCH-127: Clear All Bookmarks removes every bookmark
- Covers: IDM_SEARCH_CLEAR_BOOKMARKS
- Channel: menu, mcp
- Steps: Bookmarks on lines 1 and 3; run IDM_SEARCH_CLEAR_BOOKMARKS (and look for Search › Bookmark › Clear All Bookmarks with e2e_menu).
- Expect: the menu item exists and runs; `bookmarks` lists []; text unchanged (the port's menus lack the item: run_command answers "Command 43008 is not in this build's menus": defect)

### SEARCH-128: Copy Bookmarked Lines copies each line with its ending
- Covers: IDM_SEARCH_COPYMARKEDLINES
- Channel: menu, clipboard
- Steps: For each document "l1\nl2\nl3\nl4\n" and CRLF file "l1\r\nl2\r\nl3\r\n": bookmark lines 2 and 4 (2 and 3 for CRLF); run IDM_SEARCH_COPYMARKEDLINES.
- Expect: clipboard "l2\nl4\n"; for CRLF "l2\r\nl3\r\n"; the document is unchanged

### SEARCH-129: Cut Bookmarked Lines copies then removes them, as one undo
- Covers: IDM_SEARCH_CUTMARKEDLINES
- Channel: menu, clipboard, mcp
- Steps: "keep1\ndrop1\nkeep2\ndrop2\n", bookmark lines 2 and 4; run IDM_SEARCH_CUTMARKEDLINES; then IDM_EDIT_UNDO.
- Expect: clipboard "drop1\ndrop2\n"; text "keep1\nkeep2\n"; one undo restores the original text

### SEARCH-130: Remove Bookmarked Lines and Remove Non-Bookmarked Lines
- Covers: IDM_SEARCH_DELETEMARKEDLINES, IDM_SEARCH_DELETEUNMARKEDLINES
- Channel: menu, mcp
- Steps: "keep1\ndrop1\nkeep2\ndrop2\n" with lines 1 and 3 bookmarked: run IDM_SEARCH_DELETEUNMARKEDLINES; restore the text and bookmarks, run IDM_SEARCH_DELETEMARKEDLINES; also run both on a document with no bookmarks.
- Expect: "keep1\nkeep2\n" with bookmarks still on the kept lines; then "drop1\ndrop2\n"; without bookmarks, Remove Bookmarked changes nothing and Remove Non-Bookmarked empties the document; the clipboard is untouched

### SEARCH-131: Paste to (Replace) Bookmarked Lines puts the clipboard into each
- Covers: IDM_SEARCH_PASTEMARKEDLINES
- Channel: menu, clipboard, mcp
- Steps: "a\nb\nc\n" with lines 1 and 3 bookmarked; clipboard "X\nY"; run IDM_SEARCH_PASTEMARKEDLINES; then with no bookmarks run it again.
- Expect: text "X\nY\nb\nX\nY\n"; with no bookmarks nothing changes

### SEARCH-132: Inverse Bookmarks flips every line
- Covers: IDM_SEARCH_INVERSEMARKS
- Channel: menu, mcp
- Steps: "l1\nl2\nl3\nl4\n" (5 lines with the empty last) with bookmarks on 2 and 4; run IDM_SEARCH_INVERSEMARKS twice.
- Expect: after one: [1, 3, 5]; after two: [2, 4]

### SEARCH-133: Bookmarks move with their lines when text is inserted above
- Covers: IDM_SEARCH_TOGGLE_BOOKMARK
- Channel: menu, keys, mcp
- Steps: Bookmark line 3 of "a\nb\nc\n"; at line 1 type "new\n".
- Expect: `bookmarks` lists [4]; the bookmarked line's text is still "c"

## Go to line

### SEARCH-134: Go to... moves the caret to a line
- Covers: IDM_SEARCH_GOTOLINE
- Channel: menu, modal, mcp
- Steps: "abc 123\nfoo(bar)\nline3\n"; queue alert {button 1, field "3"}; run IDM_SEARCH_GOTOLINE.
- Expect: the logged prompt reads "Go to line (1 to 4), or @offset (0 to 23)" with an empty field and buttons OK, Cancel; the caret is at line 3 column 1

### SEARCH-135: Go to an offset with @
- Covers: IDM_SEARCH_GOTOLINE
- Channel: menu, modal, mcp
- Steps: Same document; answers {1, "@5"}; then {1, "@0"}; then {1, "@23"}.
- Expect: caret positions 5 (line 1 column 6), 0, 23 (end)

### SEARCH-136: An offset inside a CRLF pair or a multi-byte character is moved to a boundary
- Covers: IDM_SEARCH_GOTOLINE
- Channel: menu, modal, mcp
- Steps: CRLF file "ab\r\ncd\r\n": go to "@3" (between \r and \n); document "é!" : go to "@1" (inside é).
- Expect: first caret at 4 (after the \r\n: GoToLineDlg snaps with POSITIONAFTER(POSITIONBEFORE(offset))); second caret at 2 (after the é, never inside it)

### SEARCH-137: A line past the end goes to the last line
- Covers: IDM_SEARCH_GOTOLINE
- Channel: menu, modal, mcp
- Steps: Four-line document, caret at 1:1; answer {1, "99"}.
- Expect: as Notepad++ (SCI_GOTOLINE clamps): caret on the last line (4); the port beeps and leaves the caret: likely defect

### SEARCH-138: Go to... refuses nonsense and can be cancelled
- Covers: IDM_SEARCH_GOTOLINE
- Channel: menu, modal, mcp
- Steps: Caret at 2:3; answers in turn: 2 (Cancel), {1, ""}, {1, "abc"}, {1, "0"}, {1, "@-1"}; then {1, "@9999"}.
- Expect: the caret stays at 2:3 after each; no text changes; "@9999" is clamped to the end (GoToLineDlg: POSITIONBEFORE/POSITIONAFTER clamp), so the caret goes to the end of the text

## Braces

### SEARCH-139: Go to Matching Brace jumps between brace pairs
- Covers: IDM_SEARCH_GOTOMATCHINGBRACE
- Channel: menu, keys, mcp
- Steps: "f(a[1], {b})\n": caret before "(" (1) → run; run again; caret after "]" (6) → run; caret before "{" → press cmd+m.
- Expect: caret 11 (at ")"), then back to 1; from after "]" to 3 ("["); from "{" to 10 ("}")

### SEARCH-140: Go to Matching Brace off a brace, or with an unmatched brace, does nothing
- Covers: IDM_SEARCH_GOTOMATCHINGBRACE
- Channel: menu, mcp
- Steps: "f(a\nxyz\n": caret at 1 (before the unmatched "("); caret at 5 (inside "xyz").
- Expect: caret unchanged both times

### SEARCH-141: Select All In-between selects the pair with its braces
- Covers: IDM_SEARCH_SELECTMATCHINGBRACES
- Channel: menu, keys, mcp
- Steps: "f(a[1], {b})\n": caret at 9 (just after "{") run IDM_SEARCH_SELECTMATCHINGBRACES; caret at 1 (before "(") press shift+cmd+m; across lines "{\n  x\n}\n" with caret at 0 run the command.
- Expect: selected text "{b}"; then "(a[1], {b})"; then "{\n  x\n}"

### SEARCH-142: Select All In-between without a brace does nothing
- Covers: IDM_SEARCH_SELECTMATCHINGBRACES
- Channel: menu, mcp
- Steps: "abc\n", caret at 1.
- Expect: nothing selected; caret at 1

## Change History

### SEARCH-143: Go to Next / Previous Change reach edited lines
- Covers: IDM_SEARCH_CHANGED_NEXT, IDM_SEARCH_CHANGED_PREV
- Channel: menu, keys, mcp
- Steps: Open a saved file "a\nb\nc\nd\ne\n"; type "X" at the start of line 3; caret at 1:1, run IDM_SEARCH_CHANGED_NEXT; caret at line 5, run IDM_SEARCH_CHANGED_PREV.
- Expect: both land on line 3 (column 1)

### SEARCH-144: Change navigation wraps around
- Covers: IDM_SEARCH_CHANGED_NEXT, IDM_SEARCH_CHANGED_PREV
- Channel: menu, keys, mcp
- Steps: Saved file of 6 lines; edit line 2 only; caret at line 5; run Next; caret at line 1, run Previous.
- Expect: as Notepad++ (changedHistoryGoTo wraps): Next lands on line 2, Previous lands on line 2; the port does not wrap: likely defect

### SEARCH-145: Change navigation skips over a block of changed lines
- Covers: IDM_SEARCH_CHANGED_NEXT, IDM_SEARCH_CHANGED_PREV
- Channel: menu, keys, mcp
- Steps: Saved 10-line file; edit lines 2, 3, 4 and 7; caret at line 2; run Next; then Previous from line 7.
- Expect: as Notepad++ (changedHistoryGoTo skips the block the caret is in): Next goes to line 7, not 3; Previous from line 7 goes to line 4; the port steps line by line: likely defect

### SEARCH-146: Saved changes are change-history stops too
- Covers: IDM_SEARCH_CHANGED_NEXT
- Channel: menu, keys, files, mcp
- Steps: Open a file, edit line 3, save (IDM_FILE_SAVE), caret at line 1; run IDM_SEARCH_CHANGED_NEXT.
- Expect: as Notepad++ (mask includes SC_MARKNUM_HISTORY_SAVED): the caret moves to line 3; the port ignores saved-change markers: likely defect

### SEARCH-147: Clear Change History removes the markers and the stops
- Covers: IDM_SEARCH_CLEAR_CHANGE_HISTORY, IDM_SEARCH_CHANGED_NEXT
- Channel: menu, keys, mcp
- Steps: Edit line 3 of a file; run IDM_SEARCH_CLEAR_CHANGE_HISTORY; caret at 1:1; run IDM_SEARCH_CHANGED_NEXT; read SCI_MARKERGET on line 3.
- Expect: no change-history marker bits on any line; the caret stays at 1:1; the text and its undo history are kept (IDM_EDIT_UNDO still undoes the edit)

### SEARCH-148: With no changes, change navigation does nothing
- Covers: IDM_SEARCH_CHANGED_NEXT, IDM_SEARCH_CHANGED_PREV
- Channel: menu, mcp
- Steps: Freshly opened unmodified file; caret at 2:1; run both commands.
- Expect: caret unchanged

## Find characters in range

### SEARCH-149: Find characters in range marks the characters in a code-point range
- Covers: IDM_SEARCH_FINDCHARINRANGE
- Channel: menu, modal, mcp
- Steps: "ascii é è\n"; queue alerts {1, "128"}, {1, "255"}, 1; run IDM_SEARCH_FINDCHARINRANGE; read indicator 13.
- Expect: prompts "Mark characters from (decimal code point)" (default 128) and "…to (decimal code point)" (default 65535) were shown, then an alert "2 characters marked"; indicator 13 covers exactly the bytes of "é" and "è"

### SEARCH-150: Find characters in range counts by code point after an emoji
- Covers: IDM_SEARCH_FINDCHARINRANGE
- Channel: menu, modal, mcp
- Steps: "😀 é\n"; range 233..233.
- Expect: "1 character marked"; indicator 13 covers bytes 5-7 (the é) and not the emoji's bytes 0-4

### SEARCH-151: Find characters in range reaches beyond the BMP
- Covers: IDM_SEARCH_FINDCHARINRANGE
- Channel: menu, modal, mcp
- Steps: "a 😀 b\n"; range 128..1114111.
- Expect: "1 character marked" covering the 4 bytes of 😀 (the port casts the bounds to 16 bits, so 1114111 becomes 65535 and the emoji is missed: likely defect)

### SEARCH-152: Find characters in range: nothing found, or cancelled
- Covers: IDM_SEARCH_FINDCHARINRANGE
- Channel: menu, modal, mcp
- Steps: Pure ASCII "abc\n" with range 128..65535; then run again answering 2 (Cancel) on the first prompt.
- Expect: "0 characters marked" and no indicator 13; the cancelled run shows only the first prompt and leaves the marks as they were

## Menu structure

### SEARCH-153: The Search menu carries every command, enabled
- Covers: IDM_SEARCH_*, IDM_FOCUS_ON_FOUND_RESULTS
- Channel: menu
- Steps: e2e_menu for every Search command id of plan/commands.tsv; e2e_menu tree "Search" depth 3.
- Expect: every id resolves to an enabled item whose title matches commands.tsv (with "…" for "..."), under the submenus Style All Occurrences of Token, Style One Token, Clear Style, Jump Up, Jump Down, Copy Styled Text, Bookmark, Change History; IDM_SEARCH_CLEAR_BOOKMARKS must be among them (see SEARCH-127)
