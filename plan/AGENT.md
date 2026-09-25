# AGENT — The MCP interface (the product's agent server)

The application's own Model Context Protocol server (`AgentServer.mm`): JSON-RPC 2.0, one message per
line, over a Unix socket (`NPPMAC_AGENT_SOCKET`, 0600), the `nppmac mcp` stdio bridge
(`macos/cli/nppmac.m`), the MISC. preference "Let AI agents drive the editor (MCP)" (`agentServer`,
off by default) and the 21 product tools: `list_documents`, `get_document`, `get_selection`,
`open_document`, `close_document`, `go_to`, `edit_document`, `save_document`, `bookmarks`,
`list_commands`, `run_command`, `detect_language`, `tokens`, `function_list`, `find`, `replace`,
`compare`, `file_encoding`, `ocr`, `read_qr`, `spell_check`. Each case speaks the protocol either through
`App.call`/`App.conn.request` or, where framing matters, over a raw `socket.AF_UNIX` connection to
`app.socket_path` that the test writes bytes to and reads lines from. Lines and columns are one-based and
columns count characters (Unicode code points), as the tools' descriptions and README promise. What the
tools report is checked against what the editor shows through the `e2e_*` hooks (`e2e_sci`, `e2e_menu`,
`e2e_ui`, `e2e_log`) and against files on disk. Out of scope: the `e2e_*` tools themselves (the harness);
the engines behind the tools in depth (search syntax, lexers, Compare markers, the language model: SEARCH,
LANG, COMPARE); only their contract as the agent sees it is tested here. Cases that make the application die
(a crash is the defect under test) use `fresh_app` and leave it restarted. Paths: the application reports
files under the temporary folder as `/var/...` (not `/private/var/...`), so compare paths with
`os.path.realpath` applied to both sides.

## Protocol

### AGENT-001: initialize names the server and negotiates the protocol version
- Covers: -
- Channel: mcp
- Steps: On a raw connection, send `initialize` with protocolVersion "2024-11-05", then "2025-03-26", then "2025-06-18", then "1999-01-01" (ids 1-4).
- Expect: each answer has the same id and `result.protocolVersion` equal to the version asked for, except "1999-01-01", which gets "2025-06-18"; `serverInfo.name` is "NotepadMac", `serverInfo.title` is "NotepadMac (Notepad++ for macOS)", `serverInfo.version` equals `CFBundleShortVersionString` of the copy's Info.plist; `capabilities.tools.listChanged` is false; `instructions` is non-empty and says lines and columns are one-based.

### AGENT-002: ping answers with an empty result and ids come back exactly as sent
- Covers: -
- Channel: mcp
- Steps: Send `ping` with id 0, id "abc", id 9007199254740991 and id -5.
- Expect: each reply is `{"jsonrpc":"2.0","id":<the same id, same JSON type>,"result":{}}`, in the order sent.

### AGENT-003: tools/list describes exactly the 21 product tools with usable schemas
- Covers: -
- Channel: mcp
- Steps: Call `tools/list` and drop the `e2e_*` entries (present only under `NPPMAC_E2E=1`).
- Expect: the remaining names are the 21 tools in the order of the heading above; each has a non-empty description and an `inputSchema` with type "object" and `additionalProperties` false; `required` is ["line"] for go_to, ["command"] for run_command, ["what"] for find, ["what","replacement"] for replace, ["left","right"] for compare, ["path"] for file_encoding, ocr and read_qr, ["text"] for detect_language and [] for the others; `document` properties accept string or integer.

### AGENT-004: An unknown method is a JSON-RPC error, not a crash
- Covers: -
- Channel: mcp
- Steps: Send `{"jsonrpc":"2.0","id":3,"method":"resources/list"}` and then `ping` id 4 on the same connection.
- Expect: the first reply is an error with code -32601 and message "Method not found: resources/list" and id 3; the ping is answered normally.

### AGENT-005: Notifications never get a reply
- Covers: -
- Channel: mcp
- Steps: On a raw connection send, without ids: `notifications/initialized`, `notifications/cancelled`, an unknown method `foo/bar`, and `tools/call` with name "nope"; then `ping` id 9; read lines for 1 s.
- Expect: the only line received is the ping's reply (id 9); no error reply with `"id":null` is sent for the unknown notification or the id-less tools/call (JSON-RPC 2.0: a notification is never answered). (Currently the unknown method and the tools/call each get an error reply with id null: BUG.)

### AGENT-006: A line that is not JSON gets a parse error and the connection goes on
- Covers: -
- Channel: mcp
- Steps: On one raw connection send `not json`, then the bytes `{"a":"\xff\xfe"}` (invalid UTF-8), then `ping` id 7.
- Expect: two replies with error code -32700 "Parse error" and id null, then the ping's result for id 7; the connection stays open.

### AGENT-007: Invalid requests and batches are refused with -32600
- Covers: -
- Channel: mcp
- Steps: Send `{"jsonrpc":"2.0","id":8}` (no method), `{"jsonrpc":"2.0","id":10,"method":42}`, and the array `[{"jsonrpc":"2.0","id":1,"method":"ping"}]`.
- Expect: the first two get code -32600 "Invalid Request" with their ids; the array (a batch, which MCP 2025-06-18 does not support) gets code -32600 rather than -32700, since it is valid JSON. (Currently the array gets -32700 "Parse error": BUG.)

### AGENT-008: Responses sent by the client are ignored
- Covers: -
- Channel: mcp
- Steps: Send `{"jsonrpc":"2.0","id":5,"result":{}}` and `{"jsonrpc":"2.0","id":6,"error":{"code":1,"message":"x"}}`, then `ping` id 7.
- Expect: the only reply is the ping's.

### AGENT-009: tools/call with an unknown or missing tool name is a -32602 error
- Covers: -
- Channel: mcp
- Steps: Call tools/call with name "no_such_tool", then with params `{}` (no name), then with `arguments` given as the string "x" for `list_documents`.
- Expect: the first two are JSON-RPC errors code -32602 whose message starts "Unknown tool:" (the first names "no_such_tool"); the third succeeds as if arguments were `{}` (a documents list comes back).

### AGENT-010: A tool's failure is an error result, its success carries text and structured content
- Covers: -
- Channel: mcp
- Steps: Call `get_document` with document "no-such.txt", then `list_documents`, both through `conn.request` without unwrapping.
- Expect: the first is a result (not a JSON-RPC error) with `isError` true and `content[0]` = `{type:"text", text:"No open document is no-such.txt"}`; the second has `isError` false, `content[0].type` "text" whose text parses as JSON equal to `structuredContent`, and `structuredContent.documents` is a list.

### AGENT-011: Framing: CRLF, blank lines, pipelining and split writes
- Covers: -
- Channel: mcp
- Steps: On a raw connection: send `ping` id 1 ending in `\r\n`; send `\n\n`; send three requests (ids 2, 3, 4) in one `sendall`; send one `tools/call list_documents` (id 5) one byte per write with 1 ms between writes.
- Expect: exactly five replies, ids 1, 2, 3, 4, 5 in that order, each one line ending in `\n`; blank lines produce nothing.

### AGENT-012: A multi-megabyte request and answer travel whole
- Covers: -
- Channel: mcp
- Steps: `edit_document` with `text` = 5,000,000 characters ("0123456789" repeated, one newline per 100 characters) on a new document, then `get_document`.
- Expect: `applied` 1 and `bytes` 5,000,000 within 10 s; `get_document` with first_line 1..9000 and with 41001..50000 returns exactly those lines of the source (each under the million-character cut); every reply is one line that parses as JSON.

### AGENT-013: A client that disconnects before reading its answer does not kill the application
- Covers: -
- Channel: mcp
- Steps: With `fresh_app`: open a raw connection, send `{"jsonrpc":"2.0","id":1,"method":"ping"}\n` and close the socket at once; repeat with a `tools/call get_document`; wait 1 s.
- Expect: the application is still running (`app.running`) and a new connection's `ping` is answered. (Currently the process dies of SIGPIPE, exit status -13, on the first such client: BUG. Restart the app afterwards so later cases have one.)

### AGENT-014: Several connections at once are each served correctly
- Covers: -
- Channel: mcp
- Steps: Open 20 connections at once (more than the listen backlog of 8) and `ping` on each; then run 12 threads, each with its own connection making 40 `list_documents` and `get_document` calls.
- Expect: all 20 pings are answered; every reply's id matches its request and its content is well-formed; no call fails; the whole run takes under 10 s.

### AGENT-015: Concurrent edits from two connections are all applied
- Covers: -
- Channel: mcp
- Steps: On a new empty document, two threads with their own connections each make 50 `edit_document` calls inserting a distinct line ("A1".."A50", "B1".."B50") at line 1 column 1.
- Expect: the final text has exactly 100 lines and contains every inserted line once; no call fails; the document is modified.

### AGENT-016: While a modal dialog opened by a tool is up, other connections are still answered
- Covers: IDM_EDIT_COLUMNMODE
- Channel: mcp, modal, ui
- Steps: With `answers(real_modals=True)`, start `run_command` "IDM_EDIT_COLUMNMODE" with `run_async`; once the Column Editor window is visible, send `ping` on a second connection with a 3 s timeout; then close the dialog with `e2e_act` (Cancel) from that connection.
- Expect: the ping is answered within 3 s and the dialog can be closed from the second connection, after which the first call returns `ran` true. (Currently every message on every connection waits until the dialog ends, because each is handled inside a `dispatch_sync` on the main queue: BUG. Kill and restart the app if the ping times out.)

## Socket, preference and bridge

### AGENT-017: The socket is the user's alone
- Covers: -
- Channel: launch, files
- Steps: Start the app with `NPPMAC_AGENT_SOCKET` pointing at `<tmp>/newdir/s.sock` (a folder that does not exist yet; keep the path under 104 bytes); stat the socket and its folder.
- Expect: the path is a socket (`stat.S_ISSOCK`) with permission bits 0600, owned by the current user; `newdir` was created with mode 0700; a connection to it answers `ping`.

### AGENT-018: The agent interface is off by default
- Covers: -
- Channel: launch, cli, files
- Steps: Launch the copy with empty preferences and without `-NppMac.agentServer YES` (needs a harness launch option, see report); once its process has been running 3 s, check the socket path, then run `app.cli mcp` with `NPPMAC_AGENT_SOCKET` set to that path, write `initialize` id 1 and a `notifications/initialized`, and read stdout for up to 45 s (the bridge's own 15 s wait for the socket, after a Launch Services request that can take as long again); stop the app with SIGTERM.
- Expect: no file exists at the socket path; the bridge answers id 1 with error code -32000 whose message names Preferences > MISC. and "Let AI agents drive the editor"; the notification gets nothing; e2e cannot be used here (by design).

### AGENT-019: The MISC. preference starts and stops listening
- Covers: IDM_SETTING_PREFERENCE
- Channel: launch, ui, prefs, files
- Steps: Launch with `agentServer` = YES in the preference domain instead of the command-line argument (harness option, see report); open Settings > Preferences, page MISC., uncheck "Let AI agents drive the editor (MCP)" with `e2e_act` on the connection already open; then check it again.
- Expect: after unchecking, `agentServer` reads NO, the socket file is gone and a new `connect` is refused, while the already-open connection is still served; after checking again the socket file is back with mode 0600 and a new connection answers `ping`.

### AGENT-020: A stale socket file is replaced at launch
- Covers: -
- Channel: launch, files
- Steps: Write a regular file "stale" at the socket path, then start the app.
- Expect: the path is now a socket and a connection is served.

### AGENT-021: Quitting removes the socket file
- Covers: -
- Channel: launch, files
- Steps: With `fresh_app`: call `app.invoke("app","terminate:",[None])` with queued "don't save" answers, wait for the process to exit, then check the path before the harness's own clean-up runs.
- Expect: the process exits with status 0 and the socket file no longer exists; start the app again afterwards.

### AGENT-022: nppmac mcp relays requests and answers
- Covers: -
- Channel: cli, mcp
- Steps: Spawn `app.cli mcp` with `NPPMAC_AGENT_SOCKET=app.socket_path`; write `initialize` (id 1), `notifications/initialized`, `tools/call list_documents` (id 2); read two lines; close its stdin.
- Expect: the replies have ids 1 and 2, the first with `serverInfo.name` "NotepadMac", the second with `structuredContent.documents`; nothing is written for the notification; the bridge exits with status 0 within 5 s of its stdin closing; the app is still running.

### AGENT-023: nppmac mcp used as a one-shot pipe prints every answer before it exits
- Covers: -
- Channel: cli, mcp
- Steps: With `fresh_app`: run `app.cli mcp` with `subprocess.run(input=<initialize id 1 + tools/list id 2, newline-terminated>)`, so its stdin reaches end-of-file right after the two requests.
- Expect: stdout holds two JSON lines, ids 1 and 2; exit status 0; the app is still running afterwards. (Currently the bridge closes the socket as soon as its input ends: nothing is printed, and the application dies of SIGPIPE writing the answers: BUG.)

### AGENT-024: nppmac mcp forwards a last line without a newline
- Covers: -
- Channel: cli, mcp
- Steps: Spawn the bridge, write `{"jsonrpc":"2.0","id":1,"method":"ping"}` without a trailing newline and keep stdin open for 3 s, then close it.
- Expect: the ping is answered (id 1) before the bridge exits. (A final unterminated line is currently kept in the bridge's buffer and never sent: likely BUG.)

### AGENT-025: nppmac mcp ends when the application goes away
- Covers: -
- Channel: cli, launch
- Steps: With `fresh_app`: spawn the bridge and exchange one `ping`; then stop the app.
- Expect: the bridge exits by itself within 5 s with status 0 (its stdin still open); start the app again afterwards.

### AGENT-026: Tool descriptions, errors and English menu paths stay English in a localized interface
- Covers: IDM_EDIT_UPPERCASE
- Channel: launch, mcp
- Steps: Restart with `-NppMac.localizationFile russian.xml`; call `tools/list`, `get_document` for "nope.txt", and `run_command` "Edit|Convert Case to|UPPERCASE" on a document "abc" with everything selected; `list_commands` query "uppercase".
- Expect: descriptions and the error text are the English ones of AGENT-003/AGENT-010; the English menu path runs (`ran` true, text "ABC") although the menus are Russian; `list_commands` still lists IDM_EDIT_UPPERCASE; restore the default language afterwards.

## Documents and addressing

### AGENT-027: list_documents reports what the tabs and the status bar show
- Covers: -
- Channel: mcp, files
- Steps: Open a UTF-8 LF file `a.py`, a UTF-8-BOM file `b.txt`, a UTF-16 LE BOM CRLF file `c.txt`, and a new document "x" (unsaved); edit `a.py`.
- Expect: four entries with consecutive `index` 0..3 in tab order (the first "new 1" gone only if it was closed); each has `title`, `path` (null for the new document, the `/var/...` realpath-equal path for files), `language` ("python" for a.py, "normal" otherwise) and `language_title` ("Python"), `modified` (true only for a.py), `current` (true only for the last opened), `encoding` "UTF-8", "UTF-8-BOM", "UTF-16LE" and "UTF-8", `eol` "LF", "LF", "CRLF", "LF", `read_only` false, `lines` and `bytes` equal to SCI_GETLINECOUNT / SCI_GETLENGTH of each; `workspace_roots` is [].

### AGENT-028: Pinned tabs and workspace roots appear in the list
- Covers: -
- Channel: mcp, ui
- Steps: Pin the current tab with run_command "File|Pin Tab"; call `open_document` with a folder path; call `list_documents`.
- Expect: the pinned document has `pinned` true (others have no `pinned` key); `open_document` answered `{workspace_roots: [<folder>]}` and `list_documents.workspace_roots` holds the folder; the Folder as Workspace panel shows it (e2e_ui).

### AGENT-029: The Search results tab is neither listed nor addressable
- Covers: -
- Channel: mcp, ui
- Steps: Make documents "new 1", "one" ("foo\nfoo\n"); call `find` "foo" with `show_results` true; make a document "two"; list the documents; then call `get_document` with the index missing from the list.
- Expect: the Search results panel shows 2 hits; the list has no search-results entry (indices 0, 1, 3 — the tab positions); `get_document` with index 2 is an error "No document at index 2 ..." rather than the search results' text. (Currently index 2 answers with the Search results document: BUG.)

### AGENT-030: A document is found by index, path, name, title or "current"
- Covers: -
- Channel: mcp
- Steps: Open `<tmp>/dir1/same.txt` ("one\n") and a new document titled "notes"; address them with `get_document` by integer index, index as the string "1", full `/private/var/...` path, the `/var/...` path, a path with `..` in it, `~/h.txt` for a file opened from the app's home (`app.home`), file name "same.txt", tab title "notes", and "current"; then by 7, -1, "nope.txt", [1] and {"a":1}.
- Expect: each valid form returns the intended document's text; errors are "No document at index 7 (list_documents shows N)", "No document at index -1 (list_documents shows N)", "No open document is nope.txt", and "document must be an index, a path or a name" for the list and the object.

### AGENT-031: Same-named files and number-like titles are addressable
- Covers: -
- Channel: mcp
- Steps: Open `<tmp>/dir1/same.txt` and `<tmp>/dir2/same.txt` (different texts); make a new document titled "2024".
- Expect: the full paths reach each file; the name "same.txt" reaches the first in tab order; `get_document` with the string "2024" returns the document titled "2024". (Currently any all-digit string is taken as an index, so "2024" fails with "No document at index 2024": BUG.)

## get_document

### AGENT-032: The whole text comes back, unsaved changes included
- Covers: -
- Channel: mcp, files
- Steps: Open a file with "a\nb\n", change it with `edit_document` to "a\nB\nc\n" without saving; call `get_document` without arguments.
- Expect: `text` is "a\nB\nc\n" (the file on disk still "a\nb\n"); `first_line` 1, `last_line` 4 (the empty last line counts, as SCI_GETLINECOUNT does), `truncated` false; the info fields of AGENT-027 are included with `modified` true.

### AGENT-033: A line range returns exactly those lines
- Covers: -
- Channel: mcp
- Steps: On "l1\r\nl2\r\nl3\r\nl4\r\nl5" (CRLF file) ask for lines 2..3, 0..1, 4..99, 3..2 and 5..5.
- Expect: "l2\r\nl3\r\n" (first_line 2, last_line 3); "l1\r\n" (first_line 1); "l4\r\nl5" (last_line 5); "l3\r\n" (last_line raised to first_line 3); "l5".

### AGENT-034: A range past the end returns no text, not garbage
- Covers: -
- Channel: mcp
- Steps: On a 3-line document "one\ntwo\nthree\n" ask for first_line 99, and for first_line 5 last_line 7.
- Expect: either an error saying the line is outside 1..4, or empty `text` with `first_line`/`last_line` not beyond 4; in no case does `text` contain "\u0000". (Currently `text` is 14 NUL characters and `last_line` 99: BUG.)

### AGENT-035: Truncation at a million characters loses nothing on continuation
- Covers: -
- Channel: mcp, files
- Steps: Open a file of 12,000 lines, each "%09d" + 90 "y" + "\n" (1.2 MB); call `get_document`; then keep asking from the next line the answer says is still missing until the end; join the pieces.
- Expect: the first answer has `truncated` true and at most 1,000,000 characters; `last_line` is the last line that the text contains, fully or partly (if partly, the text says so by not ending in "\n"), so that the next request starting at `last_line + 1` (or at `last_line` for a partial line) and the pieces joined equal the file exactly. (Currently the text holds lines 1-10000 complete but `last_line` is 10001, so continuing at 10002 skips line 10001: BUG.)

### AGENT-036: The truncation limit counts characters, not bytes
- Covers: -
- Channel: mcp
- Steps: Make a document of 600,000 "é" plus "\n" (1.2 MB of UTF-8, 600,001 characters); call `get_document`.
- Expect: `truncated` false and `text` has 600,001 characters. (Currently it is cut at 500,000 characters because the limit is applied to bytes: BUG.)

### AGENT-037: A cut never splits a character
- Covers: -
- Channel: mcp
- Steps: Make one line of 400,000 "😀" (1.6 MB, 4 bytes each) and call `get_document`.
- Expect: `truncated` true; `text` consists only of whole "😀" characters (no U+FFFD, no lone surrogates), at most 1,000,000 characters; first_line and last_line are 1.

### AGENT-038: Reading a document behind the front one disturbs nothing
- Covers: -
- Channel: mcp
- Steps: Open a 1000-line document A, go_to line 500 column 3 with a selection to column 6; open document B; then `get_document`, `tokens` and `spell_check` for A; back in A read the selection.
- Expect: B stays `current` throughout; A's selection, caret and first visible line are exactly as before; A's text is complete.

### AGENT-039: Unusual characters survive the round trip
- Covers: -
- Channel: mcp
- Steps: `open_document` with text "a\u0000b\té字😀é‍\n" and read it back with `get_document`, `find` "b" and `get_selection` after selecting the line.
- Expect: the text comes back byte-identical (NUL included, as JSON "\u0000"); `bytes` equals the UTF-8 length; the find column of "b" is 3.

## get_selection and go_to

### AGENT-040: A caret without a selection
- Covers: -
- Channel: mcp
- Steps: On "hello\nworld\n" put the caret at line 2 column 3 with go_to; call `get_selection`.
- Expect: `text` ""; `start`, `end` and `caret` all `{line:2, column:3, position:8}`; `selections` 1; `rectangular` false; `first_visible_line` 1; `document.current` true.

### AGENT-041: A stream selection across lines with Unicode columns
- Covers: -
- Channel: mcp, keys
- Steps: On "😀é字x\nline2\n" go_to line 1 column 2 to end_line 2 end_column 3; then extend it with shift+right via e2e_keys.
- Expect: first `text` "é字x\nli"; `start` {line 1, column 2, position 4}; `end` {line 2, column 3, position 12}; after shift+right `text` ends "lin" and `caret` column 4.

### AGENT-042: Multiple selections are counted, the main one reported
- Covers: -
- Channel: mcp
- Steps: On "abc\ndef\n" select "a" (SCI_SETSELECTION 0,1) and add "e" (SCI_ADDSELECTION 5,6) with e2e_sci; call `get_selection`.
- Expect: `selections` 2; `rectangular` false; `text` is the main selection's text ("e", the last added).

### AGENT-043: A rectangular selection reports the block's text
- Covers: -
- Channel: mcp, keys
- Steps: On "abc\ndef\nghi\n" put the caret at line 1 column 1, press alt+shift+down twice and alt+shift+right once; call `get_selection`.
- Expect: `rectangular` true; `selections` 3; `text` is the column block "a\nd\ng" (what Copy would copy, IDM_EDIT_COPY then e2e_clipboard, gives the same lines). (Currently `text` is the whole stream "abc\ndef\ng": BUG.)

### AGENT-044: go_to puts the caret, centres the line and gives the editor the keys
- Covers: -
- Channel: mcp, keys
- Steps: On a 1000-line document ("line N" each) go_to line 500 column 3; then type "X" with e2e_keys text.
- Expect: the answer's `start` and `end` are {line 500, column 3}; `first_visible_line` from get_selection is between 450 and 500 (the line is centred); line 500 now reads "liXne 500".

### AGENT-045: go_to selects a range; end_column is exclusive and clamped
- Covers: -
- Channel: mcp
- Steps: On "abcdef\nghij\nkl\n": (a) line 1 col 2 to end_line 2 end_column 3; (b) line 2 col 1 with end_line 2 and no end_column; (c) line 1 col 99; (d) line 3 col 1 to end_line 99; (e) line 2 col 3 to end_line 1 end_column 2 (backwards).
- Expect: (a) selection "bcdef\ngh"; (b) "ghij"; (c) caret at the end of line 1 (column 7); (d) "kl\n" (end_line clamped to the last line, the empty line 4); (e) the selected text is "bcdef\ngh" (from line 2 column 3 back to line 1 column 2), with the caret at the earlier end (line 1 column 2) and the anchor at line 2 column 3.

### AGENT-046: go_to refuses lines outside the document and a missing line
- Covers: -
- Channel: mcp
- Steps: On a 3-line document call go_to with line 0, line 5, line -2, no line at all, and line "2" (a string).
- Expect: the first three are errors "Line 0 is outside 1..3" etc.; the missing and the string line are errors naming `line` as required / not an integer. (Currently a missing or string line silently goes to line 1: BUG.)

### AGENT-047: go_to brings a background document to front
- Covers: -
- Channel: mcp, ui
- Steps: Open A and B (B in front); go_to document "A" line 2.
- Expect: A is `current` in list_documents, the tab bar's selected tab (e2e_ui) is A, the caret is on line 2; B is unchanged.

## open_document and close_document

### AGENT-048: Opening a file, and again when it is already open
- Covers: -
- Channel: mcp, ui
- Steps: Open `<tmp>/f.py` (5 lines) with line 4; open a new document; open `<tmp>/f.py` again with line 2.
- Expect: the first answer has `path` equal (realpath) to the file, `language` "python", and the caret on line 4 (get_selection); the second open returns the same `index` as the first, the number of documents does not grow, f.py is in front with the caret on line 2.

### AGENT-049: A new document from text, with title and language
- Covers: IDM_EDIT_UNDO
- Channel: mcp, menu
- Steps: `open_document` text "int main(){}\n" title "demo.cpp" language "cpp"; then text "#!/usr/bin/env python3\nprint(1)\n" with no language.
- Expect: first: `title` "demo.cpp", `language` "cpp", `path` null, `modified` false, and Edit > Undo is disabled (nothing to undo); second: `language` "python" (detected from the shebang).

### AGENT-050: open_document refuses before it makes a tab
- Covers: -
- Channel: mcp
- Steps: Count the documents; call open_document with path "/nonexistent/x.txt", with text "x" and language "klingon", with no arguments, with text 42, and with both path (an existing file) and text "zzz".
- Expect: errors "No such file: /nonexistent/x.txt", "No language named klingon", "Give a path or a text" (twice); the document count is unchanged after the errors; the last call opens the file (path wins) and no document with "zzz" exists.

### AGENT-051: The eol of a new document agrees with the status bar
- Covers: -
- Channel: mcp, ui
- Steps: `open_document` text "a\r\nb\r\n"; read the answer's `eol` and the status bar field (e2e_ui, the NSTextField whose value holds "Ln:"); then open a CRLF file and do the same.
- Expect: for the text, `eol` "LF" and the status bar "Unix (LF)" (a new document takes the default format, as in Notepad++, whatever line endings the text holds); for the file, "CRLF" and "Windows (CR LF)"; the text's own "\r\n" are kept as typed (get_document).

### AGENT-052: close_document keeps the user's unsaved work unless told
- Covers: -
- Channel: mcp
- Steps: Make A (unmodified) and B (modified); close B without discard_changes; close B with discard_changes true; close A by path; then close the last remaining document.
- Expect: the first is an error "B has unsaved changes; pass discard_changes to close it anyway" and B stays open with its text; the second answers `closed` true; closing by path works; closing the last document answers `closed` true, `open_documents` 1 and leaves one empty "new 1", as Notepad++ does.

## edit_document

### AGENT-053: Replacing the whole text is one undo step
- Covers: IDM_EDIT_UNDO, IDM_EDIT_REDO
- Channel: mcp
- Steps: On a saved file "one\ntwo\n" call edit_document text "uno\ndos\ntres\n"; run IDM_EDIT_UNDO once, then IDM_EDIT_REDO.
- Expect: `applied` 1, `document.modified` true; after one undo the text is "one\ntwo\n" again and `modified` false; after redo it is the new text.

### AGENT-054: Whole-line edits use the original line numbers and land together
- Covers: IDM_EDIT_UNDO
- Channel: mcp
- Steps: On "1\n2\n3\n4\n5\n" apply, in this order, edits {3..3 "C\n"}, {1..1 ""}, {5..5 "E1\nE2\n"}.
- Expect: text "2\nC\n4\nE1\nE2\n"; `applied` 3; one IDM_EDIT_UNDO restores "1\n2\n3\n4\n5\n".

### AGENT-055: Column edits count characters
- Covers: -
- Channel: mcp
- Steps: On "😀é字x\nline2\n": replace line 1 columns 3..4 with "Z"; insert "-" at line 2 column 1 (start_column = end_column = 1); replace line 2 from column 3 with no end_column by "!"; replace line 1 columns 1..99 by "*".
- Expect: "😀éZx"; "-line2"; "-l!" (to the end of the line); the last gives "*" for line 1 (end_column clamped to the line end), the line ending kept.

### AGENT-056: Bad edits are refused whole, the document untouched
- Covers: -
- Channel: mcp, menu
- Steps: On "aaa\nbbb\nccc\n" send each of: overlapping edits {1..2}, {2..2}; start_line 9; end_line before start_line; an edit without text; an edit that is a string; no text and no edits; start_line "2" (a string).
- Expect: errors "Edits overlap", "Edit lines 9..9 are outside 1..4", "Edit lines 2..1 are outside 1..4", "An edit has no text", "Each edit must be an object", "Give text or edits", and for the string an error naming start_line as not an integer (currently "Edit lines 0..0 ..."); after all of them the text is unchanged, `modified` false and Undo disabled.

### AGENT-057: Two insertions at one place land in the order given
- Covers: -
- Channel: mcp
- Steps: On "aaa\n" send edits [{1,1..1,1 "A"}, {1,1..1,1 "B"}].
- Expect: the text is "ABaaa\n" (list order), or the call is refused as overlapping; never "BAaaa\n". (Currently "BAaaa\n": BUG.)

### AGENT-058: An empty edits list changes nothing
- Covers: -
- Channel: mcp
- Steps: On an unmodified document send `edits: []`.
- Expect: `applied` 0, the text unchanged and the document still unmodified.

### AGENT-059: A document read-only in Notepad++ is refused
- Covers: IDM_EDIT_TOGGLEREADONLY
- Channel: mcp
- Steps: On a new document "ro\n" run IDM_EDIT_TOGGLEREADONLY; call edit_document text "x", replace what "ro" replacement "x"; then toggle read-only off and edit again.
- Expect: `read_only` true in the info; both calls fail with "new N is read-only"; the text stays "ro\n"; after toggling off the edit applies.

### AGENT-060: A file with the read-only attribute is refused, not silently ignored
- Covers: -
- Channel: mcp, files
- Steps: Write `<tmp>/sys.txt` "abc\n", chmod 0444, open it; call edit_document text "zzz\n".
- Expect: the info shows `read_only` true; the call is an error saying the document is read-only; the text stays "abc\n". (Currently `read_only` is false and the call answers `applied` 1 while nothing changes, because Scintilla is read-only: BUG.)

### AGENT-061: Editing a document behind the front one keeps the user's place
- Covers: IDM_VIEW_TAB_NEXT
- Channel: mcp
- Steps: Open A ("a1\na2\na3\n", bookmark line 3, fold state irrelevant), then B, then C (C in front); edit A's line 1 through edit_document with document "A".
- Expect: C stays current; A is modified, B and C are not; A's bookmark is still on line 3 (bookmarks tool); the tab order and the recent-document order are what they were (the order a Ctrl+Tab-like IDM_VIEW_TAB_NEXT cycle visits them is unchanged).

### AGENT-062: A document in the second view can be listed, read and edited
- Covers: IDM_VIEW_GOTO_ANOTHER_VIEW
- Channel: mcp, ui
- Steps: Open files `<tmp>/one.txt` and `<tmp>/two.txt`; with two.txt in front run IDM_VIEW_GOTO_ANOTHER_VIEW; list the documents; edit two.txt by path and read it back.
- Expect: two.txt is listed with `in_second_view` true and one.txt without it; its text is readable and the edit lands in the second pane (e2e_sci on view "sub" shows it); two.txt stays in the second view. (A probe of this with two untitled documents saw the moved document disappear from the list: check and mark BUG if so.)

## save_document

### AGENT-063: A document behind the front one is saved in its own encoding and endings
- Covers: -
- Channel: mcp, files
- Steps: Open a UTF-16 LE BOM CRLF file "hé\r\nx\r\n", a UTF-8-BOM file and a Windows-1251 file (Cyrillic); edit each (replace one line); bring another document to front; call save_document for each by path.
- Expect: each answer is `{saved: true, path, document.modified: false}`; the bytes on disk are the edited text in the original encoding (UTF-16 LE with FF FE and CR LF; EF BB BF kept; 1251 bytes); the front document is unchanged.

### AGENT-064: A document without a file is not saved and no panel opens
- Covers: -
- Channel: mcp, modal
- Steps: Make a new document "x" and call save_document.
- Expect: error "new N has no file yet; the user chooses where it goes (File > Save As)"; the modal log is empty (no save panel); the document is still modified.

### AGENT-065: A failing save is an error, not a hidden alert
- Covers: -
- Channel: mcp, modal, files
- Steps: Open `<tmp>/w/f.txt`, edit it, then chmod the file 0444 and the folder 0555; queue alert answers 2; call save_document; restore permissions.
- Expect: the call is an error "Could not save <path>" (not `saved` true); the file on disk is unchanged; the document stays modified; any alert the save raised is in the modal log (none is left open).

## bookmarks

### AGENT-066: Adding, removing and clearing bookmarks
- Covers: IDM_SEARCH_NEXT_BOOKMARK
- Channel: mcp
- Steps: On a 6-line document call bookmarks add [5, 2, 2, 9]; then remove [5]; then clear true with add [1]; after the first call run IDM_SEARCH_NEXT_BOOKMARK from line 1.
- Expect: answers [2, 5], [2], [1] (sorted, no duplicates, line 9 ignored); SCI_MARKERGET has bit 1 (the bookmark marker) on exactly those lines; Next Bookmark moves the caret to line 2.

### AGENT-067: Bookmarks on a background or read-only document
- Covers: -
- Channel: mcp
- Steps: Open A, then B; bookmark A's lines 2 and 4 by name; make B read-only (IDM_EDIT_TOGGLEREADONLY) and bookmark its line 1.
- Expect: B stays in front; A's markers are there when A comes to front; B accepts the bookmark (bookmarks are not edits) and stays unmodified.

### AGENT-068: Bad bookmark lines are refused with a plain message
- Covers: -
- Channel: mcp
- Steps: Call bookmarks add ["2"], add [null], add [{"x":1}], add [1.5], remove "3".
- Expect: each is either ignored or an error that says lines must be integers; no error text contains an Objective-C selector such as "unrecognized selector"; the document is unchanged. (Currently add ["2"] answers "-[NSTaggedPointerString longValue]: unrecognized selector sent to instance …": BUG.)

## list_commands and run_command

### AGENT-069: list_commands finds commands by words of their name, path or label
- Covers: -
- Channel: mcp
- Steps: Call list_commands with query "", "uppercase", "SORT lines", "sort descending lines", "zzzz", "upper" with limit 0.
- Expect: "" returns 100 commands and a `total` equal to the number of menu commands README claims (579) (currently 602: check which entries are extra and mark BUG if README's number is wrong or the list holds non-menu ids); "uppercase" returns exactly IDM_EDIT_UPPERCASE with its `id`, `menu` and `label`; the word searches are case-insensitive and all words must match; "zzzz" gives [] and total 0; limit 0 gives [] with total 1; every IDM name in plan/commands.tsv is found by its own name.

### AGENT-070: run_command by name, number and menu path
- Covers: IDM_EDIT_UPPERCASE, IDM_EDIT_SORTLINES_LEXICOGRAPHIC_ASCENDING, IDM_EDIT_LOWERCASE
- Channel: mcp
- Steps: On "b\na\nc\n" with all selected run "IDM_EDIT_UPPERCASE"; run the number of IDM_EDIT_LOWERCASE (from list_commands); run "edit|line operations|sort lines lexicographically ascending..." (lower case, "..." instead of "…").
- Expect: the text becomes "B\nA\nC\n", then "b\na\nc\n", then "a\nb\nc\n"; the name and number answers are `{ran: true, enabled: true, command: <id>, label: <menu label>}`; the path answer has `ran` true.

### AGENT-071: A number given as a string runs the command
- Covers: IDM_EDIT_UPPERCASE
- Channel: mcp
- Steps: Select all of "abc" and run command "42016" (a string holding IDM_EDIT_UPPERCASE's number).
- Expect: `ran` true and the text "ABC", as for the integer. (Currently the string is taken as a menu path and answers `ran` false: BUG.)

### AGENT-072: A disabled command reports it did not run
- Covers: IDM_EDIT_UNDO, IDM_EDIT_REDO
- Channel: mcp
- Steps: On a new document with nothing to undo run IDM_EDIT_UNDO and IDM_EDIT_REDO.
- Expect: `{ran: false, enabled: false, label: "Undo"}` and the same for Redo; the text is unchanged.

### AGENT-073: Unknown commands are errors that name them
- Covers: -
- Channel: mcp
- Steps: Run "IDM_NOPE", 99999, "", and the path "Edit|Nope".
- Expect: "No command named IDM_NOPE"; "Command 99999 is not in this build's menus"; "Give a command"; the path answers `ran` false (or an error naming the path that was not found).

### AGENT-074: Quitting and moving to the Trash are refused
- Covers: IDM_FILE_EXIT, IDM_FILE_DELETE
- Channel: mcp, files, modal
- Steps: Open `<tmp>/victim.txt`; run IDM_FILE_EXIT, 41011, IDM_FILE_DELETE and 41016.
- Expect: each is an error "Command <id> is left to the user"; the app is still running; the file still exists and is open; the modal log is empty.

### AGENT-075: The refusals cannot be bypassed by menu path
- Covers: IDM_FILE_DELETE, IDM_FILE_EXIT
- Channel: mcp, files, modal
- Steps: Open `<tmp>/victim.txt`; queue alert answer 2 (No) in case one appears; run "File|Move to Trash"; then, with `fresh_app` in reserve, run the application menu's Quit by path ("NotepadMacE2E|Quit NotepadMacE2E" and "NotepadMac|Quit NotepadMac").
- Expect: every call is refused like AGENT-074; no "Delete file" alert is logged; the file exists; the app is still running. (Currently "File|Move to Trash" answers `ran` true and shows the "Delete file … will be moved to your Trash" alert — only the queued No saved the file: BUG.)

### AGENT-076: A command that opens a window returns at once
- Covers: IDM_SEARCH_FIND
- Channel: mcp, ui
- Steps: Run IDM_SEARCH_FIND; list the windows.
- Expect: the call returns `ran` true within 2 s and the Find window is visible; later calls are served while it stays open.

## detect_language, tokens and function_list

### AGENT-077: detect_language tells declared, offered and guessed languages
- Covers: -
- Channel: mcp
- Steps: For each of: "#!/usr/bin/env python3\nprint(1)\n"; "<?xml version=\"1.0\"?><a/>"; "{\"a\": [1, 2]}"; a 20-line C++ snippet; each with filename "x.rs"; then filename "Makefile", "noext".
- Expect: `declared` "python", "xml", "json" and null for the C++ snippet; `offered` ["python"] for the shebang; `guesses` has at most 5 entries, each {language, title, confidence in 0..1}, ordered by confidence, and the C++ snippet's first guess is "cpp"; `by_filename` "rust", "makefile", "normal".

### AGENT-078: detect_language edge inputs
- Covers: -
- Channel: mcp
- Steps: Call it with no text, text 5, text "", and a 5 MB text.
- Expect: "Give a text" for the first two; for "" empty `offered` and `guesses` and `declared` null; the 5 MB text answers within 5 s.

### AGENT-079: tokens carry Notepad++'s style names, one-based places and no blanks
- Covers: -
- Channel: mcp
- Steps: `open_document` text "def f():\n    # c\n    return 'é字'\n" language python; call tokens.
- Expect: tokens are [1,1,"KEYWORDS","def"], [1,5,"DEF NAME","f"], [1,6,"OPERATOR","():"], [2,5,"COMMENT LINE","# c"], [3,5,"KEYWORDS","return"], [3,12,"CHARACTER","'é字'"]; no token is whitespace only or spans a line ending; `language` "python", `lexer` "python"; `truncated` false.

### AGENT-080: tokens of a range, with fold levels, from a document behind
- Covers: -
- Channel: mcp
- Steps: Open a C++ document "int f() {\n  return 1;\n}\nint g() {}\n", put another document in front, call tokens with first_line 1, last_line 3, include_folds true.
- Expect: only tokens of lines 1-3; `folds` is [[1,0,true],[2,1,false],[3,1,false]] (line, level, is_header); the front document is unchanged.

### AGENT-081: tokens stops at 4000, stays fast, and handles odd ranges
- Covers: -
- Channel: mcp
- Steps: A JavaScript document of one 2 MB line "x=1;" repeated; call tokens. Then on a 2-line plain document call tokens with first_line 50.
- Expect: the first answers within 5 s with exactly 4000 tokens and `truncated` true; the second has no tokens (or an error) and no text with "\u0000"; for plain text `lexer` is JSON null, not the string "null". (Currently the range past the end returns a token "\u0000ab" and `lexer` is "null": BUG.)

### AGENT-082: function_list for a text and for a document
- Covers: -
- Channel: mcp
- Steps: Call it with text "int main(){return 0;}\nvoid g(){}\n" language cpp; with a Python text holding a class with a method and a function; for an open file `m.py`; with text but no language; with language "normal".
- Expect: cpp: entries main (line 1) and g (line 2), `parser` "cplusplus_syntax", `container` null; Python: the class `is_class` true, the method with `container` the class name; the document call includes `document` info and uses the file's language; no language: error "A text needs its language"; "normal": no entries and `parser` null.

## find and replace

### AGENT-083: find in a document with every mode and option
- Covers: -
- Channel: mcp
- Steps: On "Foo foo\tbar food\nFOO\n": find "foo" (normal); with match_case; with whole_word; "\\t" in extended mode; "f(o+)" in regex; "(?i)FOO$" in regex; "foo.bar" regex with and without dot_matches_newline on "foo\nbar"; "o" with limit 2.
- Expect: 4, 1, 3, 1, 3 and 2 hits respectively (checked against the Find dialog's Count for the same options); each match has `line`, `column` (characters), `position` (bytes), `length`, `match` and `line_text`; dot_matches_newline changes 0 hits to 1; limit 2 gives 2 matches, `hits` the full count and `truncated` true.

### AGENT-084: A regular expression that does not compile says why
- Covers: -
- Channel: mcp
- Steps: find "(" in regex mode; "(" in normal mode; "" in any mode; `(?<=a)b\Kc` and a named group `(?<n>x)\k<n>` in regex mode.
- Expect: the first is an error "The expression does not compile: missing closing parenthesis (at offset 1)"; the second finds the literal "("; "" gives "Give what to look for"; the Boost features are accepted and find what the Find dialog finds.

### AGENT-085: find in a folder returns Notepad++'s report
- Covers: -
- Channel: mcp, ui
- Steps: In `<tmp>/tree` make a.txt ("needle"), b.cpp ("needle"), sub/c.txt ("needle"), build/d.txt ("needle"); call find "needle" with folder, then with filters "*.txt", with recursive false, with filters "*.txt !\\build", with show_results true, and with folder "/nonexistent".
- Expect: hits 4, 3, 1 and 2; `report` lists each matching file with its line as the Search results panel does; show_results opens the Search results panel with the same report; the last is an error "No such folder: /nonexistent".

### AGENT-086: find on a document behind the front one leaves the user where they are
- Covers: -
- Channel: mcp
- Steps: Open A ("x\nx\n") then B with a selection at line 1 columns 1-3; call find "x" on A.
- Expect: 2 hits from A; B is still current with the same selection and first visible line.

### AGENT-087: find stays fast on a huge single line
- Covers: -
- Channel: mcp
- Steps: With `fresh_app` (a timed-out call makes the application die, see AGENT-013): a document of one 2 MB line "x;" repeated (1,000,000 hits); call find "x" with limit 5 and a 20 s timeout.
- Expect: the answer arrives within 10 s with `hits` 1000000, 5 matches and `truncated` true; each `line_text` is bounded (the whole answer is under 1 MB). (Currently no answer within 60 s: BUG. 20,000 hits on one line answer in 0.3 s, so the cost grows faster than the number of hits.)

### AGENT-088: replace with groups and case changes as one undo step
- Covers: IDM_EDIT_UNDO
- Channel: mcp
- Steps: On "hello world\n" replace "(o)" by "\\U$1" (regex); then "l" by "" (normal); then "\\n" by "\\r\\n" (extended); then run IDM_EDIT_UNDO three times.
- Expect: `replaced` 2 and "hellO wOrld\n"; `replaced` 3 and "heO wOrd\n"; `replaced` 1 and "heO wOrd\r\n"; each undo reverts exactly one replace; `document.modified` is true after each replace.

### AGENT-089: replace refusals and a document behind
- Covers: -
- Channel: mcp
- Steps: Call replace without replacement; with what ""; with "(" in regex mode; on a read-only document; then on a document behind the front one.
- Expect: "Give what and replacement" (twice); "The expression does not compile: ..."; "<title> is read-only"; the background replace lands in that document only and the front one stays current.

## compare

### AGENT-090: compare of two texts: counts and hunks
- Covers: -
- Channel: mcp
- Steps: Compare left text "a\nb\nc\n" with right text "a\nB\nc\nd\n"; then identical texts; then "A \n\nb\n" with "a\nb\n" with ignore_case, ignore_spaces and ignore_empty_lines together and each alone.
- Expect: first: `changed` 1, `added` 1, `removed` 0, `same` false, hunks [{old_start 2, new_start 2, old_lines ["b"], new_lines ["B"]}, {new_start 4, new_lines ["d"], old_lines []}] where the pure addition's `old_start` names the old line it follows or precedes (not 0; currently 0: likely BUG, confirm the intended contract); identical: `same` true and no hunks; all three options together make them `same`, each alone does not.

### AGENT-091: compare sides can be documents, files or texts, with a hunk limit
- Covers: -
- Channel: mcp
- Steps: Compare an open document (by name) with a file (by path) and with a text; compare two texts with 300 separated differences and limit 10; send left "x"; left {path: "/nope"}; left {document: "nope.txt"}.
- Expect: the document's unsaved text is what is compared; 10 hunks and `truncated` true with counts still over all 300; errors "left and right must be objects", "Cannot read /nope", "No open document is nope.txt".

### AGENT-092: compare with show opens the Compare view for the user
- Covers: -
- Channel: mcp, ui
- Steps: Write l.txt "a\nb\n" and r.txt "a\nb\nc\n"; call compare left {path l.txt} right {path r.txt} show true; then compare two texts with show true.
- Expect: both files are open, the Compare view is up (second pane visible with the other text, the summary bar field `compareSummary` shows "1 added, 0 removed, 0 changed, 2 unchanged."), `shown` true and `summary` the same text; for texts `shown` false with the note "Only documents or files can be shown; texts are compared here only."; clear with "Plugins|Compare|Clear All Compares" afterwards.

### AGENT-093: compare with show leaves the user's Compare options alone
- Covers: -
- Channel: mcp, menu
- Steps: Note the checked state of Plugins > Compare > Ignore Case, Ignore Spaces and Ignore Empty Lines (all off); call compare of two files with show true and ignore_case true; clear the comparison; read the three menu items again.
- Expect: all three are still unchecked (the call's options apply to that comparison only). (Currently Ignore Case stays checked afterwards: BUG, also reported under COMPARE-013.)

## file_encoding

### AGENT-094: file_encoding tells marks, character sets and line endings
- Covers: -
- Channel: mcp, files
- Steps: For each file: UTF-8 with BOM "x\ny"; UTF-16 LE with BOM "hé\r\nx\r\n"; UTF-16 BE with BOM; UTF-16 LE without BOM "hello\r\nworld"; Windows-1251 Cyrillic prose with CRLF; CR-only "a\rb\r"; mixed "a\r\nb\nc\r"; an empty file; 64 bytes of PNG header and binary; call file_encoding (preview_chars 1 for the first).
- Expect: `bom` "UTF-8", "UTF-16 LE", "UTF-16 BE", "none"...; `encoding` "UTF-8", "UTF-16LE", "UTF-16BE"...; `utf16_without_bom` "UTF-16 LE" for the fourth; `charset_detected` "WINDOWS-1251" (or the name uchardet gives) and a Cyrillic `preview` for the fifth; `eol` "LF", "CRLF", "CRLF", "CRLF", "CRLF", "CR", mixed `mixed_eol` true; the empty file has `eol` "none" and `lines` 0; binary `binary` true, `encoding` null; `preview` of the first is "x"; `bytes` equals the file size everywhere.

### AGENT-095: file_encoding counts the lines of a big file
- Covers: -
- Channel: mcp, files
- Steps: Write a file of 600,000 lines "ab\n" (1.8 MB) and call file_encoding.
- Expect: `lines` 600000. (Currently 349525 — only the first 2^20 characters are counted: BUG.)

### AGENT-096: file_encoding refusals
- Covers: -
- Channel: mcp
- Steps: Call it with a missing file, a folder, no path, and path "".
- Expect: errors "Cannot read <path>" for the first two and "Cannot read (no path)" (or a message naming the missing path) for the last two.

## ocr, read_qr and spell_check

### AGENT-097: ocr reads the text of an image and of a PDF
- Covers: IDM_VIEW_ZOOMIN
- Channel: mcp, snapshot, files
- Steps: Make a document "AGENT OCR 7", zoom in five times (IDM_VIEW_ZOOMIN), `e2e_snapshot` the main window to `<tmp>/ocr.png`; make a two-page PDF with `/usr/sbin/cupsfilter` from a text file whose pages say "PAGE ONE" and "PAGE TWO" (form feed between); call ocr on both.
- Expect: the PNG's `text` contains "AGENT OCR 7" (case-insensitive), `found` true; the PDF's text contains "PAGE ONE" before "PAGE TWO"; restore the zoom (IDM_VIEW_ZOOMRESTORE).

### AGENT-098: ocr of a file without text, and a missing file
- Covers: -
- Channel: mcp
- Steps: Call ocr on a plain text file, on a blank PNG snapshot of an empty document, and on "/nope.png".
- Expect: the first two answer `found` false with `text` ""; the last is an error "No such file: /nope.png".

### AGENT-099: read_qr reads codes the editor itself drew
- Covers: -
- Channel: mcp, snapshot
- Steps: Select "https://example.org/qr-test" in a document and run Tools > QR Code from Selection by menu path; snapshot its window to `<tmp>/qr.png`; call read_qr; then read_qr on a PNG without a code and on a text file.
- Expect: `text` "https://example.org/qr-test", `found` true; the PNG without a code gives `found` false and `text` ""; the text file is an error "Not an image: <path>".

### AGENT-100: spell_check finds misspellings with places and suggestions
- Covers: -
- Channel: mcp
- Steps: Call spell_check text "Thiss is a tset.\nAll good here.\nwrod\n" language "en"; then open a Python document "# a coment\nx = 1\n" and call spell_check without text, language "en".
- Expect: words "Thiss" (line 1, column 1), "tset" (1, 12), "wrod" (3, 1) in order, each with at most 5 suggestions and "test" among tset's; `language` "en", `truncated` false; the document call reports "coment" on line 1 and includes `document` info.

### AGENT-101: spell_check columns count characters
- Covers: -
- Channel: mcp
- Steps: Call spell_check text "😀 tset\n" language "en".
- Expect: "tset" at line 1, column 3 (the emoji is one character, as in go_to and find). (Currently column 4, counted in UTF-16 units: BUG.)

### AGENT-102: spell_check limit and truncated
- Covers: -
- Channel: mcp
- Steps: Call it on "tset wrod\n" with limit 2, and on "tset wrod smae\n" with limit 2.
- Expect: the first returns 2 words with `truncated` false (nothing was left out); the second 2 words with `truncated` true. (Currently the first says `truncated` true: BUG.)

### AGENT-103: spell_check languages
- Covers: -
- Channel: mcp, menu
- Steps: Note the Plugins > Spell Check > Language selection; call spell_check with language "xx_YY", then with "de" on "Das ist ein Tset", then without a language on English prose.
- Expect: "xx_YY" is an error "The spelling engine has no language xx_YY (it has: …)" listing available languages; "de" reports "Tset" and `language` "de"; the detected call reports `language` starting with "en"; the editor's Spell Check language selection is the same as before.

## Robustness across tools

### AGENT-104: Every document-taking tool refuses a document that is not open
- Covers: -
- Channel: mcp
- Steps: For each of get_document, tokens, bookmarks, edit_document (text "x"), save_document, close_document, go_to (line 1), find ("x"), replace ("x","y"), spell_check, function_list, call it with document "nope.txt".
- Expect: each is an error result whose text is "No open document is nope.txt"; no document changed and no tab was added.

### AGENT-105: Wrongly typed arguments are refused, not silently defaulted
- Covers: -
- Channel: mcp
- Steps: Call get_document first_line "2"; find what "o" limit "1"; go_to line true; bookmarks add "1"; compare left {"text": 5} right {"text": "5"}; open_document line "3".
- Expect: each is an error naming the argument and the expected type, as the tool's inputSchema declares; none silently falls back to its default. (Currently each runs with the default: BUG — fix one in the server's parameter layer for all tools.)
