# TYPING — Editor behaviour while typing

What the editor does while the user types and moves with the keyboard: text as an input method
delivers it (`app.type`, including non-ASCII), key chords as AppKit routes them (`app.keys`),
auto-closing of brackets, quotes and tags, auto-indentation, auto-completion and parameter hints
as the Preferences ask for them, smart highlighting, brace and tag matching, multiple carets,
column (rectangular) selection and typing, virtual space, Tab/Shift+Tab indentation, Home/End and
the other caret movement keys, line duplication, zoom keys, insert/overtype, and undo grouping of
typing. Menu commands themselves are in EDIT; macros in MACRO; the Preferences dialog in SETTINGS
(preferences are set here with `e2e_prefs` and restored). A caret is placed with keys
(Cmd+Up/Cmd+Down/arrows) or with `go_to` followed by an arrow press, so that Scintilla's
remembered column is the real one. Indicators are read with SCI_INDICATORVALUEAT (2507): smart
highlighting is indicator 12, tag matching 15, tag attributes 16.

## Plain typing and deleting

### TYPING-001: Typed text goes in at the caret
- Covers: -
- Channel: keys, mcp
- Steps: New document "ac"; caret after "a" (Cmd+Up, Right); type "b"; press Cmd+Down and type " done".
- Expect: "abc done"; the caret is at the end (1:9); the document reports modified=true.

### TYPING-002: Typing replaces the selection
- Covers: -
- Channel: keys, mcp
- Steps: New document "hello world"; select "world" (go_to 1:7-1:12); type "there".
- Expect: "hello there" with the caret after "there" and nothing selected.

### TYPING-003: Return inserts the document's line ending
- Covers: -
- Channel: keys, files
- Steps: Open a CRLF file "a\r\nb\r\n"; caret at the end of line 1; press Return and type "x". Repeat in an LF document and in a CR document (converted with Edit|EOL Conversion|Classic Mac).
- Expect: "a\r\nx\r\nb\r\n"; "a\nx\nb\n"; "a\rx\rb\r".

### TYPING-004: Backspace and Delete remove whole characters and join lines
- Covers: -
- Channel: keys
- Steps: New document "aé👍"; Cmd+Down; Backspace twice. New document "a\nb": Cmd+Up, Delete (forwarddelete); End, Delete; then Cmd+Down and Backspace at the start of an empty last line of "x\n".
- Expect: "aé" after one Backspace (the emoji goes whole), "a" after two; "\nb" then "b"; "x".

### TYPING-005: Consecutive typing is undone as one step
- Covers: -
- Channel: keys
- Steps: New document "hello world"; Cmd+Down; type " again"; press Cmd+Z; press Shift+Cmd+Z; then press Cmd+Up, type "b", and press Cmd+Z once.
- Expect: one Cmd+Z removes all of " again"; Shift+Cmd+Z brings it back; typing after moving the caret is a separate undo step: the last Cmd+Z removes only the "b" and leaves "hello world again".

### TYPING-006: Non-ASCII input: accents, CJK, emoji and combining marks
- Covers: -
- Channel: keys, mcp, files
- Steps: Empty document; type "héllo 日本語 👍 e\u0301" as an input method delivers it; save to tmp/u.txt.
- Expect: the text is exactly the typed string; `bytes` equals its UTF-8 length; the caret is at the end; the saved file is that UTF-8 without BOM; Left once from the end moves over the whole "e\u0301" cluster.

### TYPING-007: Composing text with an input method (marked text)
- Covers: -
- Channel: keys, mcp
- Steps: Empty document; start a composition with marked text "にほ" (setMarkedText through the IME hook), read the document; then commit "日本".
- Expect: while composing the provisional text is shown but the committed document text does not yet contain "にほ" as final text and undo has nothing from it; after commit the text is "日本" and one Cmd+Z removes it. (Needs a marked-text hook in e2e_keys.)

### TYPING-008: Typing into a read-only document changes nothing
- Covers: IDM_EDIT_TOGGLEREADONLY
- Channel: keys, mcp
- Steps: New document "ro\n"; make it read-only; type "zz", press Return, Backspace, Delete and Tab; clear read-only.
- Expect: the text stays "ro\n" and modified=false throughout.

## Auto-close and matched pairs

### TYPING-009: Each auto-insert preference closes its own pair
- Covers: -
- Channel: keys, prefs
- Steps: For each (preference, typed, result): autoInsertParenthesis "(" → "()", autoInsertBracket "[" → "[]", autoInsertBrace "{" → "{}", autoInsertSingleQuote "'" → "''", autoInsertDoubleQuote "\"" → "\"\"": turn only that one on, type into an empty cpp document, read text and caret; turn it off and type again into another empty document.
- Expect: with the preference on the pair is inserted and the caret is between (1:2); with it off (the default) only the typed character is there.

### TYPING-010: Typing the closer steps over the one put in
- Covers: -
- Channel: keys, prefs
- Steps: autoInsertParenthesis on; cpp document; type "f(x)"; then type "g(" and move the caret away and back (Left, Right) and type ")".
- Expect: "f(x)" (not "f(x))") with the caret at the end; after "g(": "f(x)g()"; typing ")" right before the inserted closer steps over it: "f(x)g()".

### TYPING-011: A bracket is closed only before a blank, the end or a closer
- Covers: -
- Channel: keys, prefs
- Steps: autoInsertBracket and autoInsertParenthesis on; document "x": Cmd+Up, type "["; document "a )": caret before ")", type "(".
- Expect: "[x" (no closer before text); "a ())" (closed because a closer follows).

### TYPING-012: Quotes are closed between blanks and after an opening bracket only
- Covers: -
- Channel: keys, prefs
- Steps: autoInsertDoubleQuote on; type "\"" into an empty document; into "ab" at the end; into "f(" at the end; into "x y" between the space and "y".
- Expect: "\"\""; "ab\"" (after a letter no closer); "f(\"\""; "x \"y" (before text no closer).

### TYPING-013: User-defined matched pairs close before a blank only
- Covers: -
- Channel: keys, prefs
- Steps: Set userMatchedPairs ["<>", "*~"]; type "<" into an empty document; type "*" at the end of "a "; type "<" before "x" in "x"; restore.
- Expect: "<>" with the caret between; "a *~"; "<x".

### TYPING-014: HTML and XML close the tag just opened
- Covers: -
- Channel: keys, prefs
- Steps: autoInsertCloseTag on; HTML document: type "<div class=\"a\">"; empty it and type "<br>"; type "<img/>"; XML document: type "<item>"; plain text: type "<div>"; restore.
- Expect: "<div class=\"a\"></div>" with the caret before "</div>"; "<br>" (void element, not closed); "<img/>" unchanged; "<item></item>"; plain text "<div>" only.

### TYPING-015: Return between braces opens an indented block
- Covers: -
- Channel: keys, prefs
- Steps: autoInsertBrace on, autoIndentMode 2 (advanced), tabs of width 4; cpp document: type "int f() {", press Return.
- Expect: "int f() {\n\t\n}" with the caret on line 2 after the tab.

### TYPING-016: Nothing is auto-closed with several carets
- Covers: -
- Channel: keys, prefs
- Steps: autoInsertParenthesis on; document "a\nb\n"; a caret at the start of each line (SCI_ADDSELECTION or Alt+Shift+Down from 1:1); type "(".
- Expect: "(a\n(b\n": each caret gets "(" and no ")" is added.

## Auto-indent

### TYPING-017: Basic auto-indent keeps the previous line's indentation
- Covers: -
- Channel: keys, prefs
- Steps: autoIndentMode 1; plain text "    x"; Cmd+Down, Return, type "y"; press Return twice and type "z"; restore autoIndentMode 2.
- Expect: line 2 is "y" with indentation 4 columns (SCI_GETLINEINDENTATION = 4, written as the document's indent characters); line 4 "z" has indentation 4 too.

### TYPING-018: With auto-indent off Return starts at column 1
- Covers: -
- Channel: keys, prefs
- Steps: autoIndentMode 0; "    x"; Cmd+Down, Return; restore autoIndentMode 2.
- Expect: "    x\n" and the caret at 2:1.

### TYPING-019: Advanced auto-indent for C-like languages
- Covers: -
- Channel: keys, prefs
- Steps: autoIndentMode 2, tab width 4. cpp: type "if (x)\ny();\n"; empty and type "while (a) {\n"; type "b;\n}"; empty and type "    {\n" then "}"; Perl: type "if (x)\n".
- Expect: "if (x)\n\ty();\n" and the caret at column 1 of line 3 (one statement after a braceless if, then back); after "{" Return indents one level; typing "}" lines it up with "while" (indentation 0); the lone "}" lines up with its "{" (4); in Perl (always braces) the line after "if (x)" is not indented.

### TYPING-020: Advanced auto-indent for Python
- Covers: -
- Channel: keys, prefs
- Steps: Python document: type "def f(a):  # note\n"; empty and type "s = 'a:'\n"; empty and type "if x:\n    y = 1\n".
- Expect: after the colon line the indentation is one level (4 columns); after a line whose colon is inside a string it is 0; inside the block the next line keeps 4.

## Auto-completion and hints while typing

### TYPING-021: Word completion pops up while typing and Tab or Return accepts
- Covers: -
- Channel: keys, prefs
- Steps: Defaults (autoCompleteOnInput on, source 2, threshold 1); plain text "alphabet alpine\n"; Cmd+Down, type "alph"; press Tab. Repeat with Return instead of Tab.
- Expect: the list is active after typing (SCI_AUTOCACTIVE=1); Tab and Return each complete to "alphabet" and close the list.

### TYPING-022: Escape closes the list and keeps what was typed
- Covers: -
- Channel: keys
- Steps: "alphabet\n", type "alp" on line 2; press Escape.
- Expect: the list is closed; the text is "alphabet\nalp".

### TYPING-023: The completion threshold
- Covers: -
- Channel: keys, prefs
- Steps: autoCompleteThreshold 3; "alphabet\n"; type "al" on line 2, read SCI_AUTOCACTIVE, type "p", read it; restore 1.
- Expect: 0 after two letters, 1 after three.

### TYPING-024: Completion sources: words, functions, both
- Covers: -
- Channel: keys, prefs
- Steps: cpp document "retrieval\n"; for autoCompleteSource 0 (functions), 1 (words), 2 (both): type "ret" on line 2 and read the list (lastCompletionList via e2e_invoke), Escape, clear line 2.
- Expect: functions: contains "return", not "retrieval"; words: "retrieval", not "return"; both: both.

### TYPING-025: Numbers are not offered when "ignore numbers" is on
- Covers: -
- Channel: keys, prefs
- Steps: autoCompleteIgnoreNumbers on (default); "12345 12abc\n"; type "12" on line 2; then turn it off and type "12" again on line 3.
- Expect: with it on the list offers "12abc" only (not "12345"); with it off both.

### TYPING-026: Automatic completion is off when its preference is off
- Covers: -
- Channel: keys, prefs
- Steps: autoCompleteOnInput false; "alphabet\n"; type "alp" on line 2; then press Cmd+Return (Word Completion).
- Expect: no list after typing; the command still completes on demand ("alphabet").

### TYPING-027: The parameter hint follows the typing
- Covers: IDM_EDIT_FUNCCALLTIP
- Channel: keys, prefs
- Steps: functionHintOnInput on (default); C document "f = "; Cmd+Down; type "fopen(" and read SCI_CALLTIPACTIVE and the hint state (apiCallTipState: name, param); type "name, "; type "\"r\")".
- Expect: after "(" the hint is active for "fopen" at parameter 0; after the comma parameter 1; after ")" the hint is closed.

### TYPING-028: Completion shortcuts work from the keyboard
- Covers: IDM_EDIT_AUTOCOMPLETE, IDM_EDIT_AUTOCOMPLETE_CURRENTFILE, IDM_EDIT_FUNCCALLTIP, IDM_EDIT_AUTOCOMPLETE_PATH
- Channel: keys
- Steps: autoCompleteOnInput off; C document "int x = pri" → Ctrl+Space; "alpha alpine\nal" → Cmd+Return; "abs(" with the caret inside → Ctrl+Shift+Space; "<tmp>/" → Ctrl+Alt+Space.
- Expect: respectively a function list, a word list, a parameter hint and a path list are shown (SCI_AUTOCACTIVE / SCI_CALLTIPACTIVE).

## Highlighting

### TYPING-029: Smart highlighting marks the other whole-word occurrences
- Covers: -
- Channel: keys, mcp
- Steps: Defaults (smart highlighting on, match case off, whole word on); "foo bar foo foobar Foo\n"; select the first "foo" with Shift+Right x3; read indicator 12 over the line; then press Right (no selection) and read again.
- Expect: indicator 12 is set on 1-3, 9-11 and 20-22 (every "foo" and "Foo" as a whole word, not inside "foobar"); with the selection gone no position has it.

### TYPING-030: Smart highlighting options
- Covers: -
- Channel: keys, prefs
- Steps: For smartHighlightMatchCase on: select "foo" in "foo Foo foo"; for smartHighlightWholeWord off: select "foo" in "foo foobar"; for smartHighlightEnabled off: select "foo" in "foo x foo"; for smartHighlightUseFindSettings on with findMatchCase on: select "foo" in "foo Foo"; restore all.
- Expect: match case: "Foo" not marked; whole word off: "foo" inside "foobar" marked; disabled: nothing marked; find settings: "Foo" not marked.

### TYPING-031: Braces are highlighted when the caret is next to one
- Covers: -
- Channel: keys, snapshot
- Steps: cpp "f(a[1])"; put the caret right after "(" (and then before "]"); read the brace highlight (needs the brace-highlight readback hook), then an unmatched "(" in "g(x"; then with braceMatchEnabled off.
- Expect: the matching pair "(" at 1:2 and ")" at 1:7 (then "[" and "]") are highlighted; the unmatched brace gets the bad-brace style; with the preference off nothing is highlighted.

### TYPING-032: Matching HTML tags are highlighted
- Covers: -
- Channel: keys, prefs
- Steps: HTML "<div><span>x</span></div>"; put the caret inside "span" of the opening tag (1:8 then Right/Left); read indicators 15 and 16; HTML "<a href='x'>t</a>" with the caret in "a"; then highlightMatchingTags off.
- Expect: indicator 15 covers both "span" tags (opening and closing) and not "div"; in the second document the attribute "href='x'" has indicator 16 (highlightTagAttributes default on); with the preference off neither indicator is set.

## Multiple carets and column mode

### TYPING-033: Typing and deleting at several carets
- Covers: -
- Channel: keys, mcp
- Steps: "one\ntwo\nthree\n"; put carets at 1:1 and 2:1 (a caret, then SCI_ADDSELECTION); type "-"; press Backspace; type "+"; press Escape.
- Expect: "-one\n-two\nthree\n"; then back to the original; then "+one\n+two\nthree\n"; after Escape one caret is left (the main one).

### TYPING-034: Multi-editing preference
- Covers: -
- Channel: prefs, mcp
- Steps: Set multiEditing false and read SCI_GETMULTIPLESELECTION; set it back true and read it.
- Expect: 0 then 1 (Cmd+click can add carets only while it is on).

### TYPING-035: Alt+Shift+arrows make a rectangular selection and typing fills every row
- Covers: -
- Channel: keys, mcp
- Steps: "abcd\nabcd\nabcd\n"; caret at 1:2 (go_to, then Right and Left); press Alt+Shift+Down twice and Alt+Shift+Right twice; read the selection; type "Z".
- Expect: rectangular=true with 3 selections each covering "bc"; after typing "aZd\naZd\naZd\n" with a caret after each Z.

### TYPING-036: Typing into a zero-width column inserts on every line
- Covers: -
- Channel: keys
- Steps: "ab\ncd\nef\n"; caret at 1:2; Alt+Shift+Down twice (no horizontal move); type "|"; press Backspace.
- Expect: "a|b\nc|d\ne|f\n"; Backspace removes all three.

### TYPING-037: The caret column is kept when moving vertically after go_to
- Covers: -
- Channel: mcp, keys
- Steps: New document "abcd\nabcd\nabcd\n"; go_to 1:2; press Down; then go_to 1:2 and Alt+Shift+Down.
- Expect: the caret lands on 2:2 (position 6), and the rectangle covers column 2 only, as if the caret had been put there by a click.

### TYPING-038: Virtual space
- Covers: -
- Channel: keys, prefs
- Steps: virtualSpace on; "ab\nabcdef\n"; caret at the end of line 1; press Right twice and type "Q"; then virtualSpace off, same document, End of line 1 and Right.
- Expect: with it on the caret moves into virtual space (SCI_GETSELECTIONNCARETVIRTUALSPACE(0) = 2) and typing pads: "ab  Q\nabcdef\n"; with it off Right moves to the start of line 2.

### TYPING-039: A rectangle reaches past short lines even without virtual space
- Covers: -
- Channel: keys
- Steps: virtualSpace off; "abcdef\nab\nabcdef\n"; caret at 1:5; Alt+Shift+Down twice; type "X".
- Expect: "abcdXef\nab  X\nabcdXef\n" (the short line is padded with spaces up to column 5; the long lines get "X" inserted at column 5).

## Indentation keys

### TYPING-040: Tab inserts indentation according to the settings
- Covers: -
- Channel: keys, prefs
- Steps: Defaults (tabs, width 4): "ab", End, Tab. useSpaces on, tabWidth 4: "ab", End, Tab; "", Tab; restore.
- Expect: "ab\t"; "ab  " (spaces up to the next tab stop); "    ".

### TYPING-041: Tab and Shift+Tab on a multi-line selection indent the lines
- Covers: -
- Channel: keys
- Steps: "a\nb\nc\n"; select from 1:1 to 3:1; press Tab; press Shift+Tab; then in "    x" put the caret just before "x" (no selection) and press Shift+Tab.
- Expect: "\ta\n\tb\nc\n" (line 3 is not included); then "a\nb\nc\n"; Shift+Tab with no selection unindents the caret's line: "x".

### TYPING-042: Backspace unindents when that is on
- Covers: -
- Channel: keys, prefs
- Steps: backspaceUnindents on, tabs width 4; "        x" (8 spaces); caret before "x"; Backspace; then off and Backspace on "        x".
- Expect: on: the indentation goes from 8 to 4 columns in one press (line indentation 4); off: one space is removed (7 columns).

## Caret movement and selection keys

### TYPING-043: Home goes to the first non-blank, then to column 1; End to the line end
- Covers: -
- Channel: keys
- Steps: "    indented line\nsecond"; caret at 1:10; press Home, Home, End.
- Expect: 1:5 (first non-blank), 1:1, 1:18 (end of the line).

### TYPING-044: Cmd and Alt arrows move by line, document and word
- Covers: -
- Channel: keys
- Steps: "    ab cd\nef"; caret at 1:8; Cmd+Left; Cmd+Right; Alt+Left; Alt+Right; Cmd+Up; Cmd+Down.
- Expect: 1:5 (line start, first non-blank as Home), 1:10, 1:8 (start of "cd"), 1:10 (word end), 1:1, 2:3 (document end).

### TYPING-045: Shift with the movement keys extends the selection
- Covers: -
- Channel: keys, mcp
- Steps: "hello world\nnext"; caret at 1:1; Shift+Right five times; Shift+Cmd+Right; Shift+Down; Shift+Cmd+Up.
- Expect: selection "hello"; "hello world"; "hello world\nnext"; then the caret back at 1:1 with nothing selected.

### TYPING-046: Cmd+D duplicates the line and keeps the caret column
- Covers: IDM_EDIT_DUP_LINE
- Channel: keys
- Steps: "abc\nxyz"; caret at 1:2; Cmd+D twice; Cmd+Z.
- Expect: "abc\nabc\nabc\nxyz" with the caret still at 1:2; one Cmd+Z removes one copy.

## Zoom and overtype

### TYPING-047: Zoom keys
- Covers: -
- Channel: keys
- Steps: New document; read SCI_GETZOOM; press Cmd++ (Zoom In; Cmd+= is Edit > Calculate); Cmd+- twice; Cmd+0; press Cmd++ 40 times.
- Expect: 0; 1; -1; 0; the zoom stops growing at Scintilla's limit (it never exceeds the maximum and the app stays responsive); the text is never changed by zooming.

### TYPING-048: Overtype replaces characters instead of inserting
- Covers: -
- Channel: menu, keys
- Steps: "abcdef\ncd"; caret at 1:1; View|Toggle Insert/Overtype; read SCI_GETOVERTYPE; type "XY"; End and type "Z"; toggle back and type "i".
- Expect: overtype is 1; "XYcdef" (two characters replaced); at the end of the line "Z" is added (nothing to overwrite, the line end is not eaten); after toggling back SCI_GETOVERTYPE is 0 and "i" is inserted.
