# COMPARE — Compare (the ComparePlus engine)

Compare is the port's built-in stand-in for the ComparePlus plugin (`CompareCommands.mm` over
`macos/third_party/compareplus`): the document in front stays in the main pane, the other text is
put read-only into the second pane with the document's language, the engine marks changed / added /
removed / moved lines (background markers 0/2/3/4, margin symbols 10-19 in margin 5, changed
characters under indicator 18), aligns both panes with blank annotations, and a bar above the second
pane carries the summary, ◀ / ▶ and ✕. The port adds the re-comparison 0.4 s after typing, the revert
arrow (marker 9 in margin 5) and Escape. In scope: every item of Plugins > Compare, the Compare items
of Plugins > Git (Compare with HEAD, Clear Active Compare), the bar, the options and their
preferences (`compareIgnoreCase`, `compareIgnoreSpaces`, `compareIgnoreEmptyLines`,
`compareDetectMoves`, `compareCharDiffs`), and the MCP `compare` tool's `show` path as it affects the
view. Out of scope: the `compare` tool's text contract (AGENT), Git's own errors and margin (GIT).
None of these menu items has an IDM id, so every case has `Covers: -`; they are invoked with
`run_command` by menu path (`app.run("Plugins|Compare|Compare")`, `"Plugins|Compare|Compare with File..."`,
`"Plugins|Git|Compare with HEAD"`) or with `e2e_menu_invoke` (same `|` path); their checked state is
read with `app.menu_item("Plugins|Compare|Ignore Case")`. Compare, Compare with File and Compare
Summary end in an NSAlert titled "Compare" (buttons OK, Copy) whose informative text is the summary;
Set as First ends in an alert "Set as the first file to compare." — both are read from
`app.modal_log()`. The open panel of Compare with File is answered with `app.answers(panels=[path])`.
Fixture texts used below: OLD = "alpha\nbeta x\ngamma\n", NEW = "alpha\nbetta x\ngamma\ndelta\n";
MOVED_OLD = "int a = 1;\nint b = 2;\nint c = 3;\nint d = 4;\nint e = 5;\nint moved = 9;\nint f = 6;\n",
MOVED_NEW = "int moved = 9;\nint a = 1;\nint B = 2;\nint c = 3;\nint added = 0;\nint added2 = 0;\nint d = 4;\nint f = 6;\n".
Every test that toggles an option puts it back.

## Starting a comparison

### COMPARE-001: Set as First to Compare remembers a saved file and says so
- Covers: -
- Channel: menu, modal
- Steps: Open OLD saved as `old.txt` in tmp; run `Plugins|Compare|Set as First to Compare`; read the modal log.
- Expect: one alert with message "Set as the first file to compare." and informative text equal to the full path of old.txt; no second pane appears (no `compareSummary` control in `e2e_ui`); the document text is unchanged.

### COMPARE-002: Set as First takes an untitled document too, and names its tab
- Covers: -
- Channel: mcp, menu, modal
- Steps: Clear All Compares; `app.new("x")` (no file); run `Plugins|Compare|Set as First to Compare`; then run `Plugins|Compare|Compare`.
- Expect: the Set-as-First alert's informative text is the tab's title (ComparePlus's setFirst takes any buffer); the following Compare from the same tab shows the alert "Nothing to compare with." with informative text `Choose "Set as First to Compare" on one file, then run Compare on the other.`; no bar, margin 5 width (`SCI_GETMARGINWIDTHN 5`) is 0.

### COMPARE-003: Compare with nothing set first explains what to do
- Covers: -
- Channel: menu, modal, ui
- Steps: After `Plugins|Compare|Clear All Compares`, open NEW from a file and run `Plugins|Compare|Compare`.
- Expect: exactly one alert "Nothing to compare with." with the informative text of COMPARE-002; `e2e_ui` of the main window has no `compareSummary` field and no ◀ ▶ ✕ buttons; `SCI_GETMARGINWIDTHN 5` is 0.

### COMPARE-004: Compare two open documents: first set aside, second in front
- Covers: -
- Channel: menu, modal, ui, mcp
- Steps: Open old.txt (OLD) and Set as First; open new.txt (NEW) so it is in front; run `Plugins|Compare|Compare`.
- Expect: an alert "Compare" with buttons ["OK", "Copy"] and informative "1 added, 0 removed, 1 changed, 2 unchanged."; the second pane's text (`e2e_sci` view "sub", `SCI_GETTEXT` with returns="string") is OLD; `SCI_GETREADONLY` on "sub" is 1; the front document is still new.txt and unmodified; the bar shows the same summary in the `compareSummary` field and buttons ◀, ▶, ✕ with tooltips "Previous Difference", "Next Difference", "Clear Active Compare"; the caret is on line 2 (the first difference).

### COMPARE-005: Compare takes the first document's current text, not only its saved file
- Covers: -
- Channel: mcp, menu, modal
- Steps: Open old.txt (OLD), change its tab to "alpha\nCHANGED\ngamma\n" with `edit_document` without saving, Set as First; bring new.txt (NEW) to front and run Compare.
- Expect: as ComparePlus compares the two buffers, the second pane holds "alpha\nCHANGED\ngamma\n" (the unsaved text), not OLD from disk.

### COMPARE-006: Compare with File compares the document in front with a chosen file
- Covers: -
- Channel: menu, modal
- Steps: Open new.txt (NEW); queue `panels=[old.txt]`; run `Plugins|Compare|Compare with File...`.
- Expect: the modal log has an `open` panel entry answered with old.txt, then the "Compare" alert with "1 added, 0 removed, 1 changed, 2 unchanged."; the second pane holds OLD; first-to-compare is not changed by it (a following `Plugins|Compare|Compare` after Clear All still says "Nothing to compare with.").

### COMPARE-007: Cancelling or failing Compare with File changes nothing
- Covers: -
- Channel: menu, modal, ui
- Steps: With new.txt in front and no comparison, queue `panels=[None]` and run Compare with File; then queue a panel answer with a path that does not exist and run it again.
- Expect: after each, the modal log has only the panel entry (no "Compare" alert); no bar controls, `SCI_GETMARGINWIDTHN 5` = 0, second pane not shown; the document text is unchanged.

### COMPARE-008: Identical texts are reported identical and nothing is marked
- Covers: -
- Channel: menu, modal, ui
- Steps: Open same.txt with OLD's text; Compare with File old.txt.
- Expect: the alert's informative text is "The files are identical."; the bar's `compareSummary` says "The files are identical."; `SCI_MARKERGET` on every line of both panes has none of bits 0, 2, 3, 4, 9-19; `SCI_GETMARGINWIDTHN 5` is 0.

### COMPARE-009: The Compare shortcut runs Compare
- Covers: -
- Channel: keys, menu, modal
- Steps: Read `app.menu_item("Plugins|Compare|Compare")["key"]`; Set as First on old.txt, bring new.txt to front, press `alt+cmd+d` with `app.keys`.
- Expect: the key is "alt+cmd+d"; the key press shows the "Compare" alert with "1 added, 0 removed, 1 changed, 2 unchanged." and the bar appears.

### COMPARE-010: Line endings and a Latin-1 file do not make lines differ
- Covers: -
- Channel: files, menu, modal
- Steps: For each pair (a) u.txt "a\nb\n" against w.txt written as bytes "a\r\nb\r\n"; (b) u2.txt "café\n" (UTF-8) against l.txt "café\n" encoded Latin-1: open the first, Compare with File the second.
- Expect: both report "The files are identical."

### COMPARE-011: A new comparison replaces the one on screen
- Covers: -
- Channel: menu, modal, mcp
- Steps: Open h2.txt "say hallo world now\n" and Compare with File h1.txt "say hello world now\n"; without clearing, Compare with File a 5000-line file L1.txt.
- Expect: the second pane now has L1.txt's text (`SCI_GETLINECOUNT` on "sub" = 5001); the alert and the bar say "1 added, 5000 removed, 0 changed, 0 unchanged."; indicator 18 is no longer set anywhere on line 1 of h2.txt.

### COMPARE-012: Compare with HEAD compares the file with its committed text
- Covers: -
- Channel: menu, files, ui
- Steps: In tmp, `git init`, set user.name/user.email in the repo config, commit f.txt "one\ntwo\nthree\n", then write "one\nTWO\nthree\nfour\n" to it; open f.txt; run `Plugins|Git|Compare with HEAD`.
- Expect: the second pane holds "one\ntwo\nthree\n"; the bar's summary is present and contains "added"; line 4 of f.txt has the added marker (bit 2); no alert is shown; `Plugins|Git|Clear Active Compare` then removes the bar and the second pane.

### COMPARE-013: The MCP compare tool with show opens the Compare view without changing the user's options
- Covers: -
- Channel: mcp, menu, prefs, ui
- Steps: Note the checked state of Plugins|Compare|Ignore Case (off); call `compare` with left={path: old.txt}, right={path: new.txt}, show=true, ignore_case=true.
- Expect: the result has shown=true and summary "1 added, 0 removed, 1 changed, 2 unchanged."; new.txt is in front and the bar shows that summary; afterwards Plugins|Compare|Ignore Case is still unchecked and `compareIgnoreCase` pref still false (the agent's options apply to that call only).

## Marks in the panes

### COMPARE-014: A changed line is marked in both panes with its margin symbol
- Covers: -
- Channel: mcp
- Steps: Compare new.txt (NEW) with old.txt; read `SCI_MARKERGET` of line index 1 in "main" and "sub", `SCI_GETMARGINWIDTHN 5` and `SCI_GETMARGINMASKN 1` of main.
- Expect: both lines have bit 0 (changed background) and bit 10 (changed symbol); margin 5 width > 0; margin 1's mask contains bits 2-5 (mask & 0x3C == 0x3C) so the backgrounds are drawn; unchanged lines 0 and 2 have none of bits 0, 2, 3, 4.

### COMPARE-015: An added line is marked in the document, nothing opposite
- Covers: -
- Channel: mcp
- Steps: Same comparison; read `SCI_MARKERGET` of main line index 3 ("delta") and the second pane's lines.
- Expect: main line 3 has bit 2 (added) and bit 12 (added symbol); no line of the second pane has bit 2 or bit 3.

### COMPARE-016: A removed line is marked in the second pane
- Covers: -
- Channel: mcp
- Steps: Set the document (a file) to "alpha\ngamma\n"; Compare with File old.txt.
- Expect: summary "0 added, 1 removed, 0 changed, 2 unchanged."; the second pane's line index 1 ("beta x") has bit 3 (removed) and bit 14 (removed symbol); no main line has bit 3.

### COMPARE-017: A moved line is marked moved on both sides and counted
- Covers: -
- Channel: mcp, menu, modal
- Steps: With Detect Moves on, open mn.txt (MOVED_NEW) and Compare with File mo.txt (MOVED_OLD).
- Expect: the alert says "2 added, 1 removed, 1 moved, 1 changed, 4 unchanged."; main line 0 has bits 4 and 16 (moved line + single moved symbol); second-pane line 5 has bit 4; main line 2 ("int B = 2;") has bit 0; main line 4 has bit 2; second-pane line 4 ("int e = 5;") has bit 3.

### COMPARE-018: A moved block carries begin / middle / end symbols
- Covers: -
- Channel: mcp
- Steps: Old = 12 distinct lines L0..L11; new = L0, L1, L8, L9, L10, L2..L7, L11; Compare with File.
- Expect: summary "0 added, 0 removed, 3 moved, 0 changed, 9 unchanged."; main lines 2, 3, 4 have bit 4 and respectively bit 17, 18, 19; lines 0, 1, 5-10 have no bit 4.

### COMPARE-019: Only the changed characters of a changed line are under indicator 18
- Covers: -
- Channel: mcp
- Steps: Compare MOVED_NEW with MOVED_OLD (Detect Character Differences on); read `SCI_INDICATORVALUEAT 18` at each position of main line 2 ("int B = 2;").
- Expect: non-zero at the "B" (offset 4) and zero at "int", "=", "2"; also "say hallo world now" against "say hello world now": only offset 5 ("a") is marked.

### COMPARE-020: Blank annotations align both panes
- Covers: -
- Channel: mcp
- Steps: Compare MOVED_NEW with MOVED_OLD; read `SCI_VISIBLEFROMDOCLINE` of "int d = 4;" (main line 6, sub line 3) and "int f = 6;" (main 7, sub 6), and `SCI_ANNOTATIONGETLINES` of every line of both panes; then Clear Active Compare and read the annotations again.
- Expect: "int d" is on the same visible line in both panes, as is "int f"; at least one line of each pane has annotation lines > 0; after clearing, every line of the main pane has 0 annotation lines.

### COMPARE-021: The second pane gets the document's language
- Covers: -
- Channel: mcp
- Steps: Open b.py "def f():\n    return 2\n" and Compare with File a.py "def f():\n    return 1\n".
- Expect: summary "0 added, 0 removed, 1 changed, 1 unchanged."; `SCI_GETLEXER` is equal in both panes (the Python lexer); `SCI_GETSTYLEAT 0` ("def") is the same keyword style in both panes; `SCI_STYLEGETBACK`/`SCI_STYLEGETSIZE` of STYLE_DEFAULT (32) are equal in both panes.

### COMPARE-022: The two panes scroll together while comparing
- Covers: -
- Channel: mcp
- Steps: Compare two 300-line files differing at line 151; after the compare set the main pane's first visible line with `SCI_SETFIRSTVISIBLELINE 20`, then `SCI_LINESCROLL 0 30`.
- Expect: right after Compare the caret is on line 151 and the first visible lines of main and sub are equal; after each scroll the second pane's `SCI_GETFIRSTVISIBLELINE` equals the main one's (20, then 50).

### COMPARE-023: A big comparison is quick
- Covers: -
- Channel: menu, modal
- Steps: Two 5000-line files, every hundredth line changed; time Compare with File from the call to the alert in the log.
- Expect: summary "0 added, 0 removed, 50 changed, 4950 unchanged."; the whole call returns in under 5 s.

## Navigation

### COMPARE-024: Next and Previous Difference walk the runs and wrap around
- Covers: -
- Channel: menu, mcp
- Steps: Compare NEW with OLD; `go_to` line 1; run `Plugins|Compare|Next Difference` three times, then `Plugins|Compare|Previous Difference` twice, reading `get_selection` caret after each.
- Expect: Next goes to line 2, then 4, then wraps to 2; Previous from 2 wraps to 4, then goes to 2; the selection is empty at column 1 each time.

### COMPARE-025: First and Last Difference
- Covers: -
- Channel: menu, mcp
- Steps: Compare MOVED_NEW with MOVED_OLD; put the caret on line 4; run `Plugins|Compare|Last Difference`, then `Plugins|Compare|First Difference`.
- Expect: Last puts the caret at line 7 column 1 ("int d = 4;", the main line matching the last marked line of the second pane, the removed "int e = 5;"); First puts it on line 1 ("int moved = 9;").

### COMPARE-026: Navigation stops at a removal that shows only in the second pane
- Covers: -
- Channel: menu, mcp
- Steps: Document x2.txt "a\nc\nd\nX\n" compared with file x1.txt "a\nb\nc\nd\n" (summary "1 added, 1 removed, 0 changed, 3 unchanged."); caret on line 1; Next Difference twice, reading the caret after each.
- Expect: each Next moves the caret forward (it never stays on line 1); after the second Next at the latest the caret is on line 4 ("X"); a third Next wraps back to the first difference.

### COMPARE-027: Navigation without a comparison does nothing
- Covers: -
- Channel: menu, mcp
- Steps: With no comparison, a document of 5 lines, caret on line 3; run Next, Previous, First and Last Difference.
- Expect: each returns ran; the caret stays on line 3 column 1 and the text is unchanged; no alert is logged.

### COMPARE-028: The bar's buttons navigate and close
- Covers: -
- Channel: ui, mcp
- Steps: Compare NEW with OLD; caret on line 1; `app.click("main", "▶")`, then `app.click("main", "◀")`, then `app.click("main", "✕")`.
- Expect: ▶ puts the caret on line 2; ◀ from there wraps to line 4; ✕ removes the bar and its buttons, hides the second pane, sets margin 5 width to 0.

## Summary

### COMPARE-029: Compare Summary shows the counts and copies them
- Covers: -
- Channel: menu, modal, clipboard
- Steps: Compare NEW with OLD; run `Plugins|Compare|Compare Summary`; then queue `alerts=[2]` and run it again.
- Expect: the first alert "Compare" has informative "1 added, 0 removed, 1 changed, 2 unchanged."; after the second one (answered Copy) `app.clipboard()` is exactly that text.

### COMPARE-030: Compare Summary before any comparison
- Covers: -
- Channel: menu, modal
- Steps: Clear All Compares; run `Plugins|Compare|Compare Summary`.
- Expect: the alert's informative text is "Nothing has been compared."

## Options

### COMPARE-031: The option items show and store their state
- Covers: -
- Channel: menu, prefs
- Steps: With `fresh_app`, read the checked state of Plugins|Compare|Ignore Case, Ignore Spaces, Ignore Empty Lines, Detect Moves, Detect Character Differences; for each of them: run it, read the checked state and the pref (`compareIgnoreCase`, `compareIgnoreSpaces`, `compareIgnoreEmptyLines`, `compareDetectMoves`, `compareCharDiffs`), run it again.
- Expect: defaults are off, off, off, on, on; each run flips both the checkmark and the pref; the second run restores them; after `app.restart()` a flipped state is still there (persisted).

### COMPARE-032: Each ignore option makes its kind of difference equal
- Covers: -
- Channel: menu, modal
- Steps: For each of (Ignore Case: "alpha\nx\n" vs "Alpha\nx\n"), (Ignore Spaces: "a b\nc\n" vs "a  b\nc\n"), (Ignore Empty Lines: "a\nb\n" vs "a\n\n\nb\n"): compare with the option off, turn it on, compare again, turn it off.
- Expect: off: the summary is not identical ("1 added, 1 removed, 0 changed, 1 unchanged.", "0 added, 0 removed, 1 changed, 1 unchanged.", "0 added, 2 removed, 0 changed, 2 unchanged." respectively); on: "The files are identical."

### COMPARE-033: Toggling an option while comparing re-runs the comparison at once
- Covers: -
- Channel: menu, ui
- Steps: For each of the three ignore options with its pair from COMPARE-032: compare with the option off, then run the option's menu item while the bar is up and read the bar's `compareSummary`; turn it back off.
- Expect: the bar says "The files are identical." right after the toggle, for all three (ComparePlus re-compares on an option change; Ignore Empty Lines, Detect Moves and Character Differences already do in the port).

### COMPARE-034: Turning an option off again brings the differences back
- Covers: -
- Channel: menu, ui
- Steps: Compare "a\nb\n" with "a\n\n\nb\n"; turn Ignore Empty Lines on (bar: identical); turn it off.
- Expect: the bar says "0 added, 2 removed, 0 changed, 2 unchanged." again and the removed lines carry bit 3 in the second pane.

### COMPARE-035: Detect Moves off turns a move into a removal and an addition
- Covers: -
- Channel: menu, ui, mcp
- Steps: Compare MOVED_NEW with MOVED_OLD; run `Plugins|Compare|Detect Moves` (off); read the bar and main line 0's markers; run it again.
- Expect: with moves off the bar says "3 added, 2 removed, 1 changed, 4 unchanged." and main line 0 has bit 2, not bit 4; turned back on, the summary returns to "2 added, 1 removed, 1 moved, 1 changed, 4 unchanged.".

### COMPARE-036: Detect Character Differences off marks the whole differing word
- Covers: -
- Channel: menu, mcp
- Steps: Compare "say hallo world now" with "say hello world now"; run `Plugins|Compare|Detect Character Differences` (off); read indicator 18 over offsets 0-11; turn it back on.
- Expect: on, only offset 5 is under indicator 18; off, offsets 4-8 ("hallo") are and offsets 0-3 and 9-11 are not; on again, only offset 5.

## Following the typing, the revert arrow, leaving

### COMPARE-037: Typing while comparing updates marks, arrows and summary
- Covers: -
- Channel: keys, mcp, ui
- Steps: Compare NEW with OLD; put the caret at line 4 column 1 and type "epsilon\n"; wait (poll) up to 5 s for main line 3 to carry bit 2.
- Expect: lines 4 and 5 ("epsilon", "delta") carry bit 2 and bit 9; the bar says "2 added, 0 removed, 1 changed, 2 unchanged."; the document is modified; the first visible line is unchanged by the refresh.

### COMPARE-038: Editing the texts equal turns the view identical
- Covers: -
- Channel: mcp, ui
- Steps: Compare NEW with OLD; `edit_document` the whole text to OLD; poll the bar.
- Expect: the bar says "The files are identical."; no line of either pane has bits 0, 2, 3, 4 or 9; margin 5 width is 0.

### COMPARE-039: Revert arrows stand beside each run of differences
- Covers: -
- Channel: mcp
- Steps: Compare NEW with OLD and read bit 9 (marker 9) on main lines 0-3; then compare "alpha\ngamma\n" with OLD and read line 1.
- Expect: bit 9 is on lines 1 and 3 (changed, added) and not on 0 and 2; for the removal, bit 9 is on the line after it (line 1, "gamma").

### COMPARE-040: The revert arrow puts a run back, in one undo step
- Covers: -
- Channel: mcp, keys, ui
- Steps: Compare NEW with OLD; click the revert margin (margin 5) at line index 1 (needs a margin-click hook; until then `app.invoke("editor", "compareRevertChangeAtLine:", [1])`); then revert line 3; press cmd+z twice; then compare "alpha\ngamma\n" with OLD and revert line 1; also revert at line 0 (no arrow).
- Expect: after the first revert the text is "alpha\nbeta x\ngamma\ndelta\n" and the bar "1 added, 0 removed, 0 changed, 3 unchanged."; after the second "alpha\nbeta x\ngamma\n" and "The files are identical."; after two undos the text is NEW again; the removal revert gives "alpha\nbeta x\ngamma\n"; the revert at line 0 changes nothing (returns NO).

### COMPARE-041: Escape in the document ends the comparison
- Covers: -
- Channel: keys, ui, mcp, menu, modal
- Steps: Set as First old.txt, compare new.txt; with the main pane focused press `escape`; then run `Plugins|Compare|Compare` again.
- Expect: after Escape the bar and its buttons are gone, the second pane is hidden, margin 5 width is 0, main lines carry none of bits 0, 2, 3, 4, 9; the text is unchanged; the second Compare works again (first-to-compare kept) and shows the same summary.

### COMPARE-042: Escape also leaves a comparison of identical files
- Covers: -
- Channel: keys, ui
- Steps: Compare same.txt with old.txt (identical); press `escape` in the main pane.
- Expect: the bar with its ✕ is gone and the second pane hidden, as for a comparison with differences.

### COMPARE-043: Clear Active Compare, from the Compare and the Git menu, keeps the first file
- Covers: -
- Channel: menu, ui, modal
- Steps: Set as First old.txt, compare new.txt; run `Plugins|Compare|Clear Active Compare`; Compare again; run `Plugins|Git|Clear Active Compare`; Compare again.
- Expect: after each clear: no bar, second pane hidden, margin 5 width 0, no compare markers; each following Compare shows "1 added, 0 removed, 1 changed, 2 unchanged." (the first file was kept).

### COMPARE-044: Clear All Compares also forgets the first file
- Covers: -
- Channel: menu, modal, ui
- Steps: Set as First old.txt, compare new.txt; run `Plugins|Compare|Clear All Compares`; run `Plugins|Compare|Compare`.
- Expect: the view is cleared as in COMPARE-043; the Compare after it shows "Nothing to compare with.".

### COMPARE-045: Switching tabs keeps the compared document's marks; closing it ends the comparison
- Covers: -
- Channel: mcp, ui, menu
- Steps: Compare new.txt with old.txt; `go_to` another open document c2.txt, then back to new.txt and read line 1's markers; then `close_document` new.txt (discard) and read the bar, the second pane, margin 5, and run Next Difference in the document now in front.
- Expect: back on new.txt line 1 still has bits 0 and 10; after closing new.txt the bar is gone, the second pane is hidden, margin 5 width is 0, and Next Difference does not move the caret of the remaining document.
