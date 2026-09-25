# PLUGINS — Built-in plugin stand-ins and the plugin host

The Plugins menu: the port's built-in stand-ins for the plugins Windows users install - JSON (JSON Viewer), XML tools, MIME Tools, Converter, NppExport, Spell check (DSpellCheck on the system engine), Markdown Preview (MarkdownViewer++) - and the host for native plugins (`macos/plugin-sdk`): building the sample plugin into the test home's `Application Support/NotepadMac/plugins`, loading it at launch, its menu items, `NPPM_*` messages and `NPPN_*` notifications, Open Plugins Folder and Import plugin(s). Compare, Git, FTP and NppExec live in the same menu but are planned in COMPARE, GIT, FTP and RUN. Plugins Admin does not exist in the port (README: "Plugins Admin is absent"). Commands without an IDM id are run by menu path (`Plugins|JSON|Format`). Spell check never uses Learn Spelling: it would write into the user's system-wide dictionary, which the harness cannot isolate; its presence is checked, it is never clicked. Tests that load a plugin add it to the scratch home, restart without cleaning the home, and remove it and restart again at the end.

## The Plugins menu

### PLUGINS-001: The Plugins menu holds the stand-ins in order, then Open Plugins Folder
- Covers: IDM_SETTING_OPENPLUGINSDIR
- Channel: menu
- Steps: Dump the Plugins menu (depth 2) with no third-party plugin installed.
- Expect: items JSON, Compare, XML, Git, FTP, MIME Tools, Converter, Export, Spell Check, Markdown Preview, NppExec, separator, "Open Plugins Folder…" and nothing after it; JSON holds Format (⌥⌘J), Compact, Sort Keys, Validate, Show JSON Tree; XML holds Pretty Print, Pretty Print — Indent Attributes, Linearize, Check XML Syntax Now, Validate Against Schema…, Validate Against DTD, Evaluate XPath Expression…, Current XML Path, Current XML Path with Predicates, Apply XSL Transformation…, Escape Characters in Selection, Unescape Characters in Selection; MIME Tools holds the two Quoted-printable items, six URL Encode items, URL Decode, SAML Decode; Converter holds "ASCII -> HEX", "HEX -> ASCII", Conversion Panel; Export holds Export to RTF, Export to HTML, Copy RTF to clipboard, Copy HTML to clipboard, Copy all formats to clipboard; no item mentions Plugins Admin.

### PLUGINS-002: Plugins Admin is absent (known gap)
- Covers: -
- Channel: menu, mcp
- Steps: Search the whole main menu tree and `list_commands` for "Plugins Admin" / IDM_SETTING_PLUGINADM.
- Expect: no menu item and no runnable command named Plugins Admin; running "IDM_SETTING_PLUGINADM" (if listed at all) reports it did not run.

## JSON

### PLUGINS-003: Format indents compact JSON and keeps its value
- Covers: -
- Channel: mcp, menu
- Steps: New document `{"b":1,"a":[1,2,{"c":null}],"s":"x"}`, caret on line 1; run `Plugins|JSON|Format`; parse the result with Python's json; undo once.
- Expect: the text has several lines, nested members indented by 4 spaces per level (jsonIndent default 4), parses to the same value as the input; the document is modified; one undo restores the original text exactly.

### PLUGINS-004: Format follows the jsonIndent preference
- Covers: -
- Channel: prefs, mcp
- Steps: Set pref jsonIndent = 2; format `{"a":{"b":[1]}}`; set jsonIndent = 8 and format again; restore the preference.
- Expect: with 2 the "b" line starts with exactly 4 spaces; with 8 it starts with exactly 16 spaces; values unchanged.

### PLUGINS-005: Format keeps the members in document order and writes "key": value
- Covers: -
- Channel: mcp
- Steps: Format `{"zeta":1,"alpha":2,"mid":{"y":1,"x":2}}`.
- Expect: in the result "zeta" comes before "alpha" and "y" before "x" (JSON Viewer keeps the order; only Sort Keys reorders); each member is written `"key": value` with no space before the colon, as JSON Viewer and the port's own HTTP window write it.

### PLUGINS-006: Format keeps Unicode readable and slashes unescaped
- Covers: -
- Channel: mcp
- Steps: Format `{"u":"Жук π 😀","p":"a\/b","e":"\u00e9","q":"say \"hi\""}`.
- Expect: the result contains "Жук π 😀", "a/b" (no "\/"), "é" or its escape that parses back to é, and `say \"hi\"`; json.loads of the result equals json.loads of the input.

### PLUGINS-007: Compact puts formatted JSON on one line without changing its value
- Covers: -
- Channel: mcp
- Steps: New document with a formatted multi-line object including nested arrays, numbers 2.5 and 12345678901234567890, true, false, null; run `Plugins|JSON|Compact`.
- Expect: the result has no newline and no space outside strings; it parses to the same value (the big integer kept exactly); true/false/null written as JSON literals.

### PLUGINS-008: Sort Keys orders the keys at every level and leaves arrays alone
- Covers: -
- Channel: mcp
- Steps: Run `Plugins|JSON|Sort Keys` on `{"b":{"z":1,"a":2},"a":[3,1,2],"c":0}`.
- Expect: top-level key order a, b, c; inside "b" a before z; the array stays [3, 1, 2]; the result is indented like Format's.

### PLUGINS-009: Format, Compact and Sort Keys refuse what is not JSON and say where
- Covers: -
- Channel: mcp, modal
- Steps: Document "{\n  \"ok\": 1,\n  bad\n}"; run Format, Compact and Sort Keys in turn, reading the modal log and the caret after each; also run Format on "this is not json".
- Expect: each shows the alert "This document is not valid JSON." with informative text starting "Line 3, column 3."; the document text is unchanged; the caret is on line 3; "this is not json" gives the same alert with "Line 1, column 1.".

### PLUGINS-010: Validate says "Valid JSON." for objects, arrays and scalars
- Covers: -
- Channel: mcp, modal
- Steps: Run `Plugins|JSON|Validate` on `{"a":1}`, `[1,2]`, `42`, `"text"` and `null`.
- Expect: each time one alert "Valid JSON." with empty informative text; the documents are unchanged.

### PLUGINS-011: Validate reports the first error's line and column and moves the caret there
- Covers: -
- Channel: mcp, modal
- Steps: For each of: single quotes `{'a':1}`; a comment `{"a":1 // c\n}`; an unclosed object "{\n\"a\": [1,\n2"; "{\"ok\": 1,\n  \"имя\": x}"; a trailing comma `{"a":1,}` - run Validate.
- Expect: each gives the alert "Invalid JSON." whose informative text starts "Line <l>, column <c>." followed by the parser's message: "Line 1, column 2.", "Line 1, column 8.", "Line 3, column 2.", "Line 2, column 10." (columns counted in characters from 1, the Cyrillic letters one each); the caret is moved to that line; the trailing comma is invalid JSON too (RFC 8259; JSON Viewer rejects it) - the port currently answers "Valid JSON." (suspected defect: NSJSONSerialization is lenient).

### PLUGINS-012: Validate on an empty document says why
- Covers: -
- Channel: mcp, modal
- Steps: Empty the document; run Validate.
- Expect: the alert "Invalid JSON." with informative "Unable to parse empty data." and no "Line" prefix; nothing else changes.

### PLUGINS-013: Show JSON Tree lists every node by its path
- Covers: -
- Channel: ui, mcp
- Steps: Document `{"top":{"inner":[10,20]},"s":"x","n":null,"t":true,"f":false}`; run `Plugins|JSON|Show JSON Tree`; read the "JSON Tree" window's text view.
- Expect: a window titled "JSON Tree" whose lines include "{} = {5}", "top = {1}", "top.inner = [2]", "top.inner[0] = 10", "top.inner[1] = 20", "s = \"x\"", "n = null", "t = true", "f = false"; keys listed in sorted order at each level.

### PLUGINS-014: The JSON tree is refused for invalid JSON and follows the document when shown again
- Covers: -
- Channel: ui, modal
- Steps: Show the tree for `{"a":1}`; change the document to "not json" and run Show JSON Tree; change it to `{"b":[true]}` and run it again.
- Expect: the invalid document gives the alert "This document is not valid JSON." and the tree window is not refreshed with garbage; the third run reuses the same window (same number), whose text now lists "b = [1]" and "b[0] = true" and no longer "a".

### PLUGINS-015: A large JSON document formats and compacts in reasonable time
- Covers: -
- Channel: mcp
- Steps: Document = json.dumps of a list of 20000 small objects (one line, ~1 MB); run Format, then Compact, timing each.
- Expect: each finishes within 10 s; after both, json.loads of the text equals the original list.

## XML

### PLUGINS-016: Pretty Print indents a one-line document without changing its content
- Covers: -
- Channel: mcp
- Steps: Document `<?xml version="1.0"?><root a="1" b="2"><item>one</item><item>two</item></root>`; run `Plugins|XML|Pretty Print`; undo once.
- Expect: the result has more than 3 lines, contains the line "    <item>one</item>" (4-space indent), and an XPath count of //item on it is 2 (via `Evaluate XPath Expression…` or Python's ElementTree); one undo restores the original.

### PLUGINS-017: Indent Attributes puts each attribute on its own line
- Covers: -
- Channel: mcp
- Steps: Run `Plugins|XML|Pretty Print — Indent Attributes` on `<root a="1" b="two words"><item id="x" k="v">t</item></root>`.
- Expect: "a=\"1\"" and "b=\"two words\"" are on separate lines, each indented 4 spaces deeper than "<root"; the quoted value "two words" is not split; the document has more lines than plain Pretty Print gives; ElementTree parses it with the same attributes.

### PLUGINS-018: Linearize joins the tags but keeps text, CDATA and comments
- Covers: -
- Channel: mcp
- Steps: Document "<r>\n  <a>line1\nline2</a>\n  <!-- keep\n  me -->\n  <![CDATA[x\n  y]]>\n  <b/>\n</r>"; run `Plugins|XML|Linearize`.
- Expect: no newline remains between one tag and the next ("</a><!--", "--><![CDATA[", "]]><b/></r>"); "line1\nline2", the comment's inner newline and the CDATA's inner newline are kept; ElementTree reads the same text for <a>.

### PLUGINS-019: Formatting a malformed document is refused with the place of the fault
- Covers: -
- Channel: mcp, modal
- Steps: Document "<a>\n  <b>\n</a>"; run Pretty Print, Indent Attributes and Linearize in turn.
- Expect: Pretty Print and Indent Attributes show "Cannot format this document.", Linearize "Cannot linearize this document.", each with informative text starting "Line 3, column"; the document is unchanged; the caret is on line 3.

### PLUGINS-020: Check XML Syntax Now says valid, or where it is not
- Covers: -
- Channel: mcp, modal
- Steps: Run `Plugins|XML|Check XML Syntax Now` on "<a><b/></a>", then on "<a>\n  <b>\n</a>", then on "<a>Жук &amp; &bogus;</a>".
- Expect: "The document is valid XML."; then "The document is not well formed." with "Line 3, column …" and the caret on line 3; the undefined entity is reported as not well formed too.

### PLUGINS-021: Validate Against DTD checks the internal DTD
- Covers: -
- Channel: mcp, modal
- Steps: Run `Plugins|XML|Validate Against DTD` on a note with `<!DOCTYPE note [<!ELEMENT note (to)><!ELEMENT to (#PCDATA)>]>` and body `<note><to>x</to></note>`; then with body `<note><from>x</from></note>`.
- Expect: "The document is valid XML."; then "The document does not match its DTD." whose informative text names "from" and the expected "(to)" on line 3.

### PLUGINS-022: Validate Against Schema… checks the document against a chosen XSD
- Covers: -
- Channel: mcp, modal, files
- Steps: Write `note.xsd` (element note with a sequence of one element "to" of xs:string); document `<note><to>you</to></note>`; queue the XSD path and run `Plugins|XML|Validate Against Schema…`; change the document to `<note><wrong>x</wrong></note>` and repeat; repeat with a cancelled panel; repeat with a file "not a schema" as the XSD.
- Expect: the open panel is titled "Choose an XSD schema"; first "The document is valid XML."; second "The document does not match the schema." with libxml2's text naming "wrong"; the cancelled panel shows no alert; the bad schema gives an alert whose text says the schema is not valid (or libxml2's reason).

### PLUGINS-023: Evaluate XPath Expression… lists the matches in an alert
- Covers: -
- Channel: mcp, modal
- Steps: Document `<catalog><book id="a"><title>First</title></book><book id="b"><title>Second</title></book></catalog>`; queue a prompt answer {button 1, field "//title/text()"} and run `Plugins|XML|Evaluate XPath Expression…`; repeat with "//book/@id", "//missing", "//[[", and a Cancel answer (button 2).
- Expect: the prompt reads "XPath expression" with default "//*"; results: alert "XPath" with informative "2 result(s):\n\nFirst\nSecond"; "2 result(s):\n\na\nb"; "The expression matched nothing."; for "//[[" an alert "XPath" carrying the engine's error text; Cancel shows no second alert.

### PLUGINS-024: XPath on a malformed document, and Copy of the result
- Covers: -
- Channel: mcp, modal, clipboard
- Steps: Document "<a><b></a>", XPath "//b"; then valid document `<r><x>1</x></r>`, XPath "//x/text()" answered with the alert's "Copy" button (queued alerts: {button 1, field}, "Copy").
- Expect: first alert informative "The document is not well formed."; the second puts "1 result(s):\n\n1" on the clipboard.

### PLUGINS-025: Current XML Path works on a document still being typed
- Covers: -
- Channel: mcp, modal
- Steps: Document "<root>\n  <list>\n    <item>one</item>\n    <item>tw" with the caret at the end; run `Plugins|XML|Current XML Path`, then `…with Predicates`; then put the caret at position 0 of `<root><a/></root>` and run Current XML Path.
- Expect: alert "Current XML Path" with informative "/root/list/item", then "/root[1]/list[1]/item[2]"; at position 0 "The current node cannot be resolved."; each alert has the buttons OK and Copy.

### PLUGINS-026: Apply XSL Transformation… opens the result in a new document
- Covers: -
- Channel: mcp, modal, files
- Steps: Write a stylesheet that outputs `<titles><t>…</t></titles>` for each //title; with the catalog of PLUGINS-023 in front queue its path and run `Plugins|XML|Apply XSL Transformation…`; then with a file that is not XSL; then with a cancelled panel.
- Expect: the panel is titled "Choose an XSL stylesheet"; a new tab opens containing "<t>First</t>" and "<t>Second</t>"; the source document is unchanged; the bad stylesheet shows an alert "XSL" and no new tab; cancel opens nothing.

### PLUGINS-027: Escape and Unescape change only the selection and round-trip
- Covers: -
- Channel: mcp
- Steps: Document "keep <x> | a <b> & \"c\" 'd' Жук"; select from "a" to the end; run `Plugins|XML|Escape Characters in Selection`; select the same (now longer) part and run Unescape.
- Expect: after Escape: "keep <x> | a &lt;b&gt; &amp; &quot;c&quot; &apos;d&apos; Жук" (the unselected "<x>" untouched, Cyrillic untouched); after Unescape the original text exactly.

## MIME Tools

### PLUGINS-028: Quoted-printable Encode escapes non-ASCII and "=" and wraps long lines
- Covers: -
- Channel: mcp
- Steps: Select all of "Ünïcödé = fun\n" and run `Plugins|MIME Tools|Quoted-printable Encode`; then select a line of 120 "x" and encode it.
- Expect: "=C3=9Cn=C3=AFc=C3=B6d=C3=A9 =3D fun\n"; the long line is split by "=\r\n" soft breaks into pieces of at most 76 characters.

### PLUGINS-029: Quoted-printable Decode restores the text and refuses bad escapes
- Covers: -
- Channel: mcp, modal
- Steps: Select-all decode of the two encodings from PLUGINS-028; then "a=\nb=\r\nc"; then "=ZZ".
- Expect: the originals come back exactly; "abc"; for "=ZZ" the alert "The selection is not valid Quoted-printable." and the text unchanged.

### PLUGINS-030: The six URL Encode commands
- Covers: -
- Channel: mcp
- Steps: Parametrized: select all and run each: "URL Encode (RFC1738)" on "a b&c(d)é" ; "URL Encode (Extended)" on "a(d)+x"; "URL Encode (Full)" on "Ab"; the three "by line" variants on "a b\nc d" / "(x)\n(y)" / "A\nB".
- Expect: "a%20b%26c(d)%C3%A9"; "a%28d%29%2Bx"; "%41%62"; by line: "a%20b\nc%20d", "%28x%29\n%28y%29", "%41\n%42" (line breaks kept as they are); without "by line" a newline is encoded (%0A).

### PLUGINS-031: URL Decode decodes triplets and leaves "+" and a stray "%"
- Covers: -
- Channel: mcp
- Steps: Select all and run `Plugins|MIME Tools|URL Decode` on "a%20b%26c%C3%A9"; then on "1+1%3D2 and 100%".
- Expect: "a b&cé"; "1+1=2 and 100%".

### PLUGINS-032: SAML Decode inflates a redirect-binding message
- Covers: -
- Channel: mcp, modal
- Steps: Select all and run `Plugins|MIME Tools|SAML Decode` on "sylOzM0psHIsLcnIC0otLE0tLlHwdLFVqjBUsstIzcnJt9HHVGEHAA%3D%3D"; then on "PD94bWwgdmVyc2lvbj0iMS4wIj8+"; then on "zzz".
- Expect: `<samlp:AuthnRequest ID="x1">hello</samlp:AuthnRequest>`; text starting "<?xml"; for "zzz" the alert "The selection is not a SAML message." and the text unchanged.

### PLUGINS-033: MIME commands work on the selection only, as one undo step
- Covers: -
- Channel: mcp, modal
- Steps: Document "keep foobar keep", select "foobar", run URL Encode (Full); undo once; then with no selection run each MIME command.
- Expect: "keep %66%6F%6F%62%61%72 keep"; one undo gives the original; with no selection nothing changes and no alert is shown.

## Converter

### PLUGINS-034: ASCII -> HEX with the default settings
- Covers: -
- Channel: mcp
- Steps: Select all of "AB" and run `Plugins|Converter|ASCII -> HEX`; then "Я j".
- Expect: "4142"; "d0af206a" (UTF-8 bytes, lowercase, no spaces).

### PLUGINS-035: ASCII -> HEX follows the converter settings and the document's line ends
- Covers: -
- Channel: prefs, mcp
- Steps: Set prefs converterInsertSpace = true, converterUppercase = true, converterHexPerLine = 2; convert "ABCj" in an LF document and in a CRLF document; restore the prefs.
- Expect: LF: "41 42\n43 6A\n"; CRLF: "41 42\r\n43 6A\r\n"; with only insertSpace on "AB" gives "41 42 " (the plugin's trailing space).

### PLUGINS-036: HEX -> ASCII reads plain, spaced and multi-line hex and refuses bad input
- Covers: -
- Channel: mcp, modal
- Steps: Select all and run `Plugins|Converter|HEX -> ASCII` on "4142", "41 42", "41\n42", "D0AF"; then on "414", "41 4243", "4Z", "4".
- Expect: "AB", "AB", "AB", "Я"; each bad input gives the alert "Hex format is not conformed" and leaves the text unchanged.

### PLUGINS-037: The Conversion Panel shows one value in every base
- Covers: -
- Channel: ui
- Steps: Run `Plugins|Converter|Conversion Panel`; set the Hexadecimal field ("hex") to "ff"; then the Character field ("ascii") to "A"; then Binary to "1010"; then Decimal to "12a", then Decimal to "7".
- Expect: the window is titled "Conversion Panel" with rows Character, Decimal, Hexadecimal, Binary, Octal; ff gives dec 255, bin 11111111, oct 377, character ÿ; "A" gives dec 65, hex 41; "1010" gives dec 10; "12a" puts no value derived from it in the other rows; "7" makes all rows agree again (hex 7, bin 111, oct 7).

### PLUGINS-038: The Conversion Panel's Insert and Copy
- Covers: -
- Channel: ui, mcp, clipboard
- Steps: Empty document; in the panel set hex "ff"; click Insert on the Decimal row; click Copy on the Binary row.
- Expect: the document reads "255" with the caret after it; the clipboard reads "11111111".

## Export

### PLUGINS-039: Export to RTF writes the styled text to the chosen file
- Covers: -
- Channel: mcp, modal, files
- Steps: Open `t_export.py` = "# comment <>&\nx = 1 # Я\n" from `tmp`, no selection; queue `out.rtf` and run `Plugins|Export|Export to RTF`; convert the file with `textutil -convert txt -stdout`.
- Expect: the save panel proposes the name "t_export.rtf"; the file starts "{\rtf1" and contains "\colortbl", "\cf", "\par" and "ၱ?" (Я); textutil gives back "# comment <>&\nx = 1 # Я".

### PLUGINS-040: Export to HTML writes a page in the editor's colours
- Covers: -
- Channel: mcp, modal, files
- Steps: Same document; queue `out.html`; run `Plugins|Export|Export to HTML`; read the file.
- Expect: proposed name "t_export.html"; UTF-8 with `<meta charset="utf-8">`, a `<title>` naming the document, a `<pre style=` block with the default style's colours, `<span` runs with "color:#" (more than one distinct colour), "&lt;&gt;&amp;" escaped, and "Я" as UTF-8.

### PLUGINS-041: The exported colours are the lexer's
- Covers: -
- Channel: mcp, files
- Steps: Python document "def f():\n    return 1\n"; export to HTML; read the foreground of the style at "def" (SCI_GETSTYLEAT then SCI_STYLEGETFORE) and convert BGR to #rrggbb.
- Expect: the span holding "def" has that colour; the plain identifier "f" has a different colour.

### PLUGINS-042: With a selection only the selection is exported
- Covers: -
- Channel: mcp, files
- Steps: In the document of PLUGINS-039 select the first 9 characters ("# comment"); export to HTML and to RTF.
- Expect: the HTML's text content and textutil's reading of the RTF are "# comment" only.

### PLUGINS-043: Cancelling the save panel writes nothing
- Covers: -
- Channel: modal, files
- Steps: Queue a cancel (None) and run Export to RTF, then Export to HTML.
- Expect: no file appears in the default folder or `tmp`; no alert is logged; the document is unchanged.

### PLUGINS-044: The clipboard exports carry exactly their formats
- Covers: -
- Channel: mcp, clipboard
- Steps: With the export document in front run `Copy RTF to clipboard`, `Copy HTML to clipboard`, `Copy all formats to clipboard`, reading `e2e_clipboard` types (and data for public.rtf / public.html) after each.
- Expect: RTF: types include public.utf8-plain-text and public.rtf, not public.html; HTML: plain text and public.html, not public.rtf; all: all three; the plain text is always the exported text exactly; the RTF data starts "{\rtf1"; the HTML contains "<pre".

## Spell check

### PLUGINS-045: The menu toggle turns spell checking on and off
- Covers: -
- Channel: menu, prefs, mcp
- Steps: Set pref spellCheckLanguage = "en" (skip the case if the `spell_check` tool finds nothing wrong in "helo" with language en); document "helo wrld\n"; run `Plugins|Spell Check|Spell Check Document Automatically`; read indicator 17 (SCI_INDICATORVALUEAT) at positions 1 and 6 and the item's checked state; run the toggle again; restore the prefs.
- Expect: on: the item is checked, pref spellCheckEnabled is true, both words carry indicator 17 and a correct word ("wrld" replaced by "world") does not; off: unchecked, pref false, no position carries indicator 17.

### PLUGINS-046: Indicator 17 is a red squiggle under the text
- Covers: -
- Channel: mcp
- Steps: With spell checking on and a misspelling marked, read SCI_INDICGETSTYLE, SCI_INDICGETFORE and SCI_INDICGETUNDER for indicator 17.
- Expect: style INDIC_SQUIGGLE (1), fore 0x0000FF (red in BGR), under = 1.

### PLUGINS-047: In code only comments and strings are checked
- Covers: -
- Channel: mcp, files
- Steps: Spell checking on (en); open `sp.py` = "wrld = 1  # helo wrld\ns = 'speling'\nspeling_var = 2\n".
- Expect: the identifier "wrld" on line 1 and "speling_var" on line 3 carry no indicator; "helo" and "wrld" in the comment and "speling" inside the string do.

### PLUGINS-048: Squiggles follow typing
- Covers: -
- Channel: keys, mcp
- Steps: Spell checking on (en), plain-text document "ok\n"; type " teh" at the end; wait for the debounce; then select "teh" and type "the".
- Expect: after the wait "teh" carries indicator 17; after the correction no position on the line does.

### PLUGINS-049: The language follows the choice, or is detected
- Covers: -
- Channel: prefs, mcp
- Steps: Spell checking on; with pref spellCheckLanguage = "" (Automatic) check "bonjur le monde\n" (skip if the engine offers no French); with "en" check "helo"; with "de" check "Hallo Welt" (skip if no German); restore prefs.
- Expect: automatic marks "bonjur"; en marks "helo"; de does not mark "Hallo" or "Welt".

### PLUGINS-050: The Language submenu lists Automatic and the installed dictionaries
- Covers: -
- Channel: menu, prefs
- Steps: Open `Plugins|Spell Check|Language` (needs the hook that fills a menu through its delegate before dumping it); choose one listed language; then choose Automatic.
- Expect: the first item is "Automatic", then a separator, then the system's languages by display name; the checked item follows pref spellCheckLanguage; choosing a language sets the pref to its identifier and rechecks the document; Automatic sets it to "".

### PLUGINS-051: The context menu offers guesses, Ignore and Learn for a misspelled word
- Covers: -
- Channel: menu, mcp
- Steps: Spell checking on (en), document "helo world\n" with the caret inside "helo"; dump the editor context menu as a right click builds it (needs the hook: `e2e_menu context=editor` must include the spelling items the menu delegate adds at the caret); then put the caret on "world" and dump again.
- Expect: after the port's "Calculate" item (disabled without a selected formula) and its separator, on "helo" the menu offers at most five guesses including "hello", then "Ignore Spelling" and "Learn Spelling" (enabled; never clicked), then a separator, then the usual editor items; on "world" no spelling items appear.

### PLUGINS-052: Choosing a guess replaces the word
- Covers: -
- Channel: menu, mcp
- Steps: As PLUGINS-051, invoke the guess "hello" from the editor context menu (hook as above).
- Expect: the document reads "hello world\n"; no indicator remains on line 1; one undo restores "helo".

### PLUGINS-053: Ignore Spelling clears the word for this session only
- Covers: -
- Channel: menu, mcp
- Steps: Spell checking on (en), document "zqxwv zqxwv\n", caret in the first word; invoke "Ignore Spelling" from the context menu (hook as above); restart the app and check the same text.
- Expect: after Ignore neither occurrence carries indicator 17; after the restart both are marked again (ignoring is not learning).

### PLUGINS-054: No spelling items when spell checking is off
- Covers: -
- Channel: menu
- Steps: Spell checking off; document "helo\n" with the caret in the word; dump the editor context menu (hook as above).
- Expect: no "Ignore Spelling", "Learn Spelling" or guess items.

## Markdown Preview

### PLUGINS-055: Markdown Preview toggles a docked panel that renders the document
- Covers: -
- Channel: mcp, ui
- Steps: Document "# Hello\n\n- one\n- two\n\nSome **bold** and `code`.\n"; run `Plugins|Markdown Preview`; read `markdownPanel.visible` and `markdownPanel.lastHTML` on app; run it again.
- Expect: visible true; the HTML contains "<h1>Hello</h1>", "<li>one</li>", "<strong>bold</strong>", "<code>code</code>"; the panel is inside the main window (a WKWebView among its controls), not a separate window; the second toggle hides it (visible false).

### PLUGINS-056: GFM tables render with alignment, escaped pipes and inline Markdown
- Covers: -
- Channel: mcp
- Steps: With the preview shown, set the document to "| Name | N |\n|:-----|--:|\n| a\\|b | **1** |\n| short |\n\n```\n| not | a table |\n|---|---|\n```\n"; wait for the render.
- Expect: lastHTML has `<th style="text-align:left">Name</th>`, `<td style="text-align:right"><strong>1</strong></td>`, a cell "a|b", the short row padded with an empty cell; the fenced lines appear inside <pre><code>, not as a second <table>.

### PLUGINS-057: The preview follows typing and the tab in front
- Covers: -
- Channel: keys, mcp
- Steps: Preview shown on "# One\n"; type "\n## Two" at the end; wait ~0.5 s; open a second tab "# Other\n" and wait; switch back to the first tab.
- Expect: lastHTML gains "<h2>Two</h2>" after the debounce; it shows "<h1>Other</h1>" while the second tab is in front and "<h1>One</h1>" again after switching back.

### PLUGINS-058: Raw HTML passes through, scripts stay inert, relative images resolve
- Covers: -
- Channel: mcp, files
- Steps: Save `doc.md` in `tmp` next to `pic.png`, containing "<b>raw</b>\n\n<script>document.title='ran'</script>\n\n![p](pic.png)\n"; open it and show the preview.
- Expect: lastHTML contains "<b>raw</b>" and `<img src="pic.png"`; the web view's title (key path `markdownPanel.webView.title` on app) is not "ran" (JavaScript is off); a snapshot of the main window shows the picture's pixels in the panel area (the relative path resolved against the document's folder).

## Plugin host

### PLUGINS-059: The sample plugin builds, loads at launch and gets a submenu
- Covers: -
- Channel: files, launch, menu
- Steps: Compile `../npp/macos/plugin-sdk/sample/hellomac.c` with `clang -dynamiclib` into `<home>/Library/Application Support/NotepadMac/plugins/HelloMac/HelloMac.dylib`; `app.restart()` keeping the home; dump the Plugins menu.
- Expect: after "Open Plugins Folder…" come a separator and a "HelloMac" submenu with "Insert Greeting", a separator, "Insert File Name"; `class:NppPluginHost` reports one plugin named HelloMac.

### PLUGINS-060: A plugin command edits the document through Scintilla
- Covers: -
- Channel: menu, mcp
- Steps: With HelloMac loaded, new document "[x]" with "x" selected; invoke `Plugins|HelloMac|Insert Greeting` with `e2e_menu_invoke`; undo once.
- Expect: the document reads "[hello from the sample plugin]"; one undo gives "[x]" back.

### PLUGINS-061: NPPM_GETFILENAME answers for a saved file and for a new one
- Covers: -
- Channel: menu, mcp, files
- Steps: With HelloMac loaded, open `t_plugin.txt` from `tmp`, caret at 0; invoke `Plugins|HelloMac|Insert File Name`; then in a new tab invoke it again.
- Expect: the file's text starts "t_plugin.txt"; the new tab's text is its tab title ("new N").

### PLUGINS-062: Notifications reach a plugin: READY, FILEOPENED, FILESAVED, BUFFERACTIVATED, SHUTDOWN
- Covers: -
- Channel: files, launch, mcp
- Steps: Build the fixture plugin `fixtures/plugins/notelog.c` (exports the three required functions plus nppmac_beNotified, which appends each code to `<NPPM_GETPLUGINSCONFIGDIR>/notelog.txt`) into the plugins folder; restart; open a file, save it, switch tabs; quit the app gracefully; read the log.
- Expect: the log contains 1001 (READY) before anything else, then 1004 (FILEOPENED) after the open, 1008 (FILESAVED) after the save, 1010 (BUFFERACTIVATED) after the tab switch, and 1009 (SHUTDOWN) last; the config folder is `plugins/Config` inside the test home.

### PLUGINS-063: The application messages a plugin can send
- Covers: -
- Channel: files, menu, mcp
- Steps: The fixture plugin also has commands that write into the document the answers of NPPM_GETFULLCURRENTPATH, NPPM_GETCURRENTDIRECTORY and NPPM_GETNPPVERSION, and commands that call NPPM_DOOPEN on `tmp/other.txt` and NPPM_SAVECURRENTFILE; run each on a saved file after modifying it.
- Expect: the full path and folder of the file in front are inserted; the version answer is (8 << 16) | 908 printed as a number; DOOPEN opens `other.txt` in a tab and returns 1; SAVECURRENTFILE saves the modified file to disk (the file's bytes change, the document is no longer modified).

### PLUGINS-064: A flat plugin loads; broken ones are skipped
- Covers: -
- Channel: files, launch, menu
- Steps: Put in the plugins folder: `Flat.dylib` (a copy of the sample built as a flat file, name "HelloMac" in getName so rename it with a -D define to "FlatHello"), `junk.dylib` (a text file), `NoExports/NoExports.dylib` (a dylib exporting nothing of the interface), `Empty/Empty.dylib` (exports the functions with a zero-length command list); restart.
- Expect: the app starts; only FlatHello has a submenu (the others are logged and skipped); the app log mentions the skipped files.

### PLUGINS-065: Several plugins get a submenu each, in name order
- Covers: -
- Channel: files, launch, menu
- Steps: Install HelloMac and a second copy built with getName "AnotherHello" in `plugins/Another/Another.dylib`; restart.
- Expect: two submenus after one separator, in folder-name order (Another before HelloMac); each one's Insert Greeting works on the document in front.

### PLUGINS-066: Open Plugins Folder creates the folder when it is missing
- Covers: IDM_SETTING_OPENPLUGINSDIR
- Channel: mcp, files
- Steps: Remove `<home>/Library/Application Support/NotepadMac/plugins`; run IDM_SETTING_OPENPLUGINSDIR (needs a hook that records NSWorkspace reveal/open requests instead of performing them, so Finder does not open during the run).
- Expect: the command ran; the plugins folder exists afterwards inside the test home (not the real Application Support); the recorded reveal request names that folder.

### PLUGINS-067: Import plugin(s)… copies a dylib into the plugins folder, loaded at the next launch
- Covers: IDM_SETTING_IMPORTPLUGIN
- Channel: modal, files, launch, menu
- Steps: Build HelloMac.dylib in `tmp`; queue its path and run IDM_SETTING_IMPORTPLUGIN; read the modal log; restart; dump the Plugins menu; import it again.
- Expect: the open panel is titled "Import plugin(s)"; the alert says "1 file(s) imported into plugins"; `plugins/HelloMac.dylib` exists in the test home; after the restart the HelloMac submenu is there; importing again replaces the file (still one copy, no error).
