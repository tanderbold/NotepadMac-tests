# FTP — FTP client (the NppFTP stand-in)

The FTP client under Plugins > FTP (`FtpClient.mm`, `FtpCommands.mm`, the `ftp*:` actions in
`AppDelegate.mm`): saved connections (Connections…, a chain of prompts; the password goes to the
Keychain, keyed by host + user + port + protocol), Connect…, Disconnect, the "Remote Files — <dir>"
panel (a one-column table: row 0 is `..`, directories end in `/`, files read `<name>   <n> bytes`),
opening a remote file (downloaded into `<home>/Library/Application Support/NotepadMac/ftp-cache/<host>/<remote path>`
and opened from there), and Upload Current File (to the path it came from, or into the directory
being browsed). Every case runs against the repository's own server `../npp/macos/test-ftp-server.py <root>`,
started by the test with `python3` on a fresh temporary root; it prints `PORT <n>` on its first
line (the OS picks a free port), accepts only user `tester` / password `secret`, and is killed
when the case ends. The Plugins > FTP items have no IDM ids: tests reach them with `run_command`
by menu path (`"Plugins|FTP|Connections…"`, `"Plugins|FTP|Connect…"`, `"Plugins|FTP|Disconnect"`,
`"Plugins|FTP|Show Remote Files"`, `"Plugins|FTP|Upload Current File"`) or `e2e_menu_invoke`;
prompts are answered with queued `{button, field}` answers and read back from the modal log.
A connection profile is made through the Connections… prompts, so its password lands in the
login Keychain: every case deletes it at the end (`security delete-internet-password -s 127.0.0.1 -a <user>`).
Out of scope: SFTP transfers (need an SSH server with a key), creating/renaming/deleting remote
files and folders (the port has no such commands, and the test server implements no RNFR/RNTO/RMD).

## Connections (profiles)

### FTP-001: Connections… with nothing saved says so and Close saves nothing
- Covers: -
- Channel: mcp, modal, prefs
- Steps: On a fresh app queue alert answer 2 (Close) and run "Plugins|FTP|Connections…".
- Expect: one alert logged, message "FTP connections", informative "No connections saved yet.", buttons ["Add…", "Close"]; preference `ftpProfiles` is still `[]`; no further prompt is shown.

### FTP-002: Add a connection through the prompt chain
- Covers: -
- Channel: mcp, modal, prefs
- Steps: Queue answers 1 (Add…), then fields "local", "127.0.0.1", "ftp", "<port>", "tester", "/", "secret" (each button 1) and run "Plugins|FTP|Connections…".
- Expect: the log shows, in order, the prompts "Connection name" (default "server"), "Host" (default ""), "Protocol: ftp, ftps or sftp" (default "ftp"), "Port (0 for the default)" (default "0"), "User name", "Initial directory" (default "/"), "Password (stored in the Keychain; leave empty for an SSH key)"; `ftpProfiles` is `[{name: "local", host: "127.0.0.1", protocol: 0, port: <port>, username: "tester", initialDirectory: "/"}]`; the password is not in the preferences; `security find-internet-password -s 127.0.0.1 -a tester` finds an item.

### FTP-003: The connections list shows each saved profile
- Covers: -
- Channel: mcp, modal
- Steps: Add profiles "local" (user tester) and "other" (user bob, host 127.0.0.2) as in FTP-002, then queue answer 2 and run "Plugins|FTP|Connections…" again.
- Expect: the alert's informative text is "local (tester@127.0.0.1)\nother (bob@127.0.0.2)".

### FTP-004: Protocol answers map to plain, FTPS and SFTP
- Covers: -
- Channel: mcp, modal, prefs
- Steps: For each of the protocol answers "ftp", "ftps", "sftp", "FTP-anything-else" add a profile named after it (host 127.0.0.1, empty password).
- Expect: the stored `protocol` is 0, 1, 2 and 0 respectively (only the "ftps"/"sftp" prefixes select TLS/SSH; anything else is plain FTP); an empty password answer stores no Keychain item.

### FTP-005: Saving a profile under an existing name replaces it
- Covers: -
- Channel: mcp, modal, prefs
- Steps: Add profile "local" with port 2121, then add "local" again with port <port> and initial directory "/sub".
- Expect: `ftpProfiles` holds exactly one "local", with port <port> and initialDirectory "/sub".

### FTP-006: Cancelling or leaving the name or host empty saves nothing
- Covers: -
- Channel: mcp, modal, prefs
- Steps: For each of: Cancel on "Connection name"; empty field on "Connection name"; Cancel on "Host"; empty field on "Host" — queue Add… plus that answer and run Connections….
- Expect: the chain stops at that prompt (no later prompt in the log); `ftpProfiles` stays `[]`.

### FTP-007: Profiles survive a restart
- Covers: -
- Channel: mcp, modal, prefs, launch
- Steps: Add profile "local"; `app.restart()`; queue answer 2 and run Connections….
- Expect: the list still reads "local (tester@127.0.0.1)"; `ftpProfiles` is unchanged; connecting (FTP-009 steps) works without asking for the password again.

## Connecting

### FTP-008: Connect… with no profile goes to Connections
- Covers: -
- Channel: mcp, modal
- Steps: On a fresh app queue answer 2 and run "Plugins|FTP|Connect…".
- Expect: the logged alert is "FTP connections" / "No connections saved yet." (not a "Connect to which?" prompt); no "Remote Files" window appears.

### FTP-009: Connect lists the initial directory in the Remote Files panel
- Covers: -
- Channel: mcp, modal, ui
- Steps: Server root holds `greeting.txt` ("remote hello\n", 13 bytes) and folder `sub/`. Add profile "local", queue `{field: "local"}` and run "Plugins|FTP|Connect…".
- Expect: the prompt logged is "Connect to which? (local)" with default "local"; a visible `NppPanel` window titled "Remote Files — /" appears; its NSTableView cells are [[".."], ["greeting.txt   13 bytes"], ["sub/"]] (sorted as the server lists); no error alert.

### FTP-010: The profile's initial directory is where browsing starts
- Covers: -
- Channel: mcp, modal, ui
- Steps: Profile "local" with initial directory "/sub" (holding `inner.txt`, 6 bytes); connect.
- Expect: panel title "Remote Files — /sub"; cells [[".."], ["inner.txt   6 bytes"]].

### FTP-011: Choosing among several profiles; an unknown name or Cancel does nothing
- Covers: -
- Channel: mcp, modal, ui
- Steps: Profiles "local" and "other"; run Connect… with field "bogus", then with button 2 (Cancel), then with field "local".
- Expect: the prompt reads "Connect to which? (local, other)"; "bogus" and Cancel show no further alert and open no Remote Files window; "local" opens "Remote Files — /".

### FTP-012: Wrong credentials are refused with "Cannot connect."
- Covers: -
- Channel: mcp, modal, ui
- Steps: For each of: user "nobody" with password "secret"; user "tester" with password "wrong" — add a profile and connect to it.
- Expect: an alert "Cannot connect." is logged whose informative text is not empty; no Remote Files window; Upload Current File afterwards shows no alert (not connected).

### FTP-013: A server that is not there is reported, not hung on
- Covers: -
- Channel: mcp, modal
- Steps: Profile with host 127.0.0.1 and a port nothing listens on (bind a socket, take its port, close it); connect with a 20 s call timeout.
- Expect: the call returns within the timeout; alert "Cannot connect." logged; the connection state stays disconnected (Show Remote Files asks "Connect to which?" again).

### FTP-014: The connect error names the cause (curl's message)
- Covers: -
- Channel: mcp, modal
- Steps: Repeat FTP-013 (refused port) and a profile with protocol "ftps" against the plain test server (it answers 502 to AUTH TLS).
- Expect: the "Cannot connect." alert's informative text carries the transfer error (e.g. contains "connect" / "SSL"/"TLS"), not only the generic "The server did not answer, or the credentials were refused." (currently fails: the failed client is discarded before its lastError is read — mark xfail BUG).

### FTP-015: SFTP to a non-SSH port fails with an alert
- Covers: -
- Channel: mcp, modal
- Steps: Profile with protocol "sftp", host 127.0.0.1, port = the FTP test server's port, user tester; connect with a 60 s call timeout.
- Expect: alert "Cannot connect." logged; no Remote Files window; no password prompt or hang (the system sftp runs in BatchMode).

## Browsing

### FTP-016: Double-click a folder descends, ".." goes back up
- Covers: -
- Channel: mcp, ui
- Steps: Connected at "/" (FTP-009); `e2e_act double_click` row of "sub/" in the Remote Files table; then double_click row 0 (".."); then row 0 again.
- Expect: after the first: title "Remote Files — /sub", cells [[".."], ["inner.txt   6 bytes"]]; after "..": title "Remote Files — /" and the root listing; ".." at the root stays at "Remote Files — /". (Needs `double_click` to set the table's clickedRow; see hooks.)

### FTP-017: Show Remote Files refreshes the listing from the server
- Covers: -
- Channel: mcp, ui, files
- Steps: Connected at "/"; create `new.txt` (3 bytes) in the server root on disk; run "Plugins|FTP|Show Remote Files".
- Expect: the table now includes ["new.txt   3 bytes"]; the panel is key and still titled "Remote Files — /".

### FTP-018: Show Remote Files while disconnected asks which profile to connect
- Covers: -
- Channel: mcp, modal, ui
- Steps: With profile "local" saved and not connected, queue `{field: "local"}` and run "Plugins|FTP|Show Remote Files".
- Expect: the "Connect to which? (local)" prompt is logged; then the Remote Files panel lists the root.

### FTP-019: Losing the server while browsing shows the transfer error
- Covers: -
- Channel: mcp, modal
- Steps: Connect; kill the server process; queue answer 1 and run "Plugins|FTP|Show Remote Files".
- Expect: an alert titled "FTP" with buttons ["OK", "Copy"] and a non-empty informative text (curl's "Couldn't connect to server" or similar) is logged; the app keeps running.

### FTP-020: Closing the panel and showing it again
- Covers: -
- Channel: mcp, ui
- Steps: Connect; close the Remote Files window with `close_window`; run Show Remote Files.
- Expect: the panel is hidden after closing, the connection is kept (no connect prompt logged), and it reappears with the same directory and listing.

## Remote files

### FTP-021: Double-click a file opens it from the cache
- Covers: -
- Channel: mcp, ui, files
- Steps: Connected at "/"; double_click the "greeting.txt" row.
- Expect: a new tab "greeting.txt" is current with text "remote hello\n", not modified; its path is `<home>/Library/Application Support/NotepadMac/ftp-cache/127.0.0.1/greeting.txt` and that file on disk has the same bytes.

### FTP-022: Names with spaces, '#' and non-ASCII text download intact
- Covers: -
- Channel: mcp, ui, files
- Steps: Server root has `a b#c.txt` ("odd\n") and `cyr.txt` ("привет\r\n" in UTF-8); open each by double-click.
- Expect: the tabs read "odd\n" and "привет\r\n" (EOL CRLF, encoding UTF-8); cache files `ftp-cache/127.0.0.1/a b#c.txt` and `.../cyr.txt` exist.

### FTP-023: Same file name in two folders gets two cache files
- Covers: -
- Channel: mcp, ui, files
- Steps: Root `greeting.txt` ("remote hello\n") and `sub/greeting.txt` ("inner\n"); open the root one, then descend into sub/ and open that one.
- Expect: two tabs, both titled "greeting.txt", with their own texts; cache paths `.../127.0.0.1/greeting.txt` and `.../127.0.0.1/sub/greeting.txt`.

### FTP-024: A file that vanished from the server reports an error and opens nothing
- Covers: -
- Channel: mcp, ui, modal, files
- Steps: Connected, listing shows `gone.txt`; delete it on disk; queue answer 1 and double-click its row.
- Expect: an alert titled "FTP" with a non-empty informative text is logged; the document count and current tab are unchanged; no `ftp-cache/127.0.0.1/gone.txt` is written.

## Uploading

### FTP-025: Edit, save and upload a remote file back to where it came from
- Covers: IDM_FILE_SAVE
- Channel: mcp, modal, files
- Steps: Open `greeting.txt` from the panel; replace the text with "changed here\n"; run IDM_FILE_SAVE; check the server file; queue answer 1 and run "Plugins|FTP|Upload Current File".
- Expect: after Save the cache file holds "changed here\n" and the server root's `greeting.txt` still holds "remote hello\n" (saving does not upload); after Upload an alert "FTP" / "Uploaded to /greeting.txt" (buttons ["OK", "Copy"]) is logged and the server file holds "changed here\n".

### FTP-026: A file from a subfolder goes back to its subfolder even after browsing elsewhere
- Covers: -
- Channel: mcp, modal, files, ui
- Steps: Open `sub/greeting.txt` from the panel, go ".." back to "/", edit to "inner 2\n", Upload.
- Expect: "Uploaded to /sub/greeting.txt"; `sub/greeting.txt` on the server is "inner 2\n"; root `greeting.txt` is untouched.

### FTP-027: Upload recreates a missing remote folder
- Covers: -
- Channel: mcp, modal, files
- Steps: Open `sub/greeting.txt`; delete the whole `sub` folder on the server's disk; edit and Upload.
- Expect: "Uploaded to /sub/greeting.txt"; the server root has `sub/greeting.txt` again with the new text (missing directories are created with MKD).

### FTP-028: A local file is uploaded into the directory being browsed; Copy copies the message
- Covers: -
- Channel: mcp, modal, files, clipboard
- Steps: Connected, browsing "/sub"; open a local file `<tmp>/local.txt` ("from local\n"); queue answer 2 (Copy) and run Upload Current File; then edit it and Upload again.
- Expect: alert "Uploaded to /sub/local.txt"; the clipboard is "Uploaded to /sub/local.txt"; `sub/local.txt` on the server holds "from local\n", and after the second upload the edited text (the remembered remote path is reused).

### FTP-029: Upload sends the bytes Save writes (encoding and BOM kept)
- Covers: IDM_FORMAT_CONV2_UTF_8, IDM_FORMAT_CONV2_AS_UTF_8
- Channel: mcp, modal, files
- Steps: Open `cyr.txt` ("привет\r\n" UTF-8) from the panel; for each of IDM_FORMAT_CONV2_UTF_8 (UTF-8-BOM) and IDM_FORMAT_CONV2_AS_UTF_8 (back to UTF-8): convert, IDM_FILE_SAVE, Upload Current File.
- Expect: after each upload the server file's bytes equal the cache file's bytes (EF BB BF + the UTF-8 text for UTF-8-BOM; the plain UTF-8 text afterwards). Currently the UTF-8-BOM upload drops the BOM (the text is re-encoded without it) — mark xfail BUG.

### FTP-030: Upload and Disconnect without a connection; Disconnect hides the panel
- Covers: -
- Channel: mcp, modal, ui
- Steps: Connect, open `greeting.txt`, run "Plugins|FTP|Disconnect"; then run Upload Current File; then queue answer 2 and run Show Remote Files.
- Expect: after Disconnect no Remote Files window is visible; Upload shows no alert and the server file is unchanged (it only beeps); Show Remote Files logs the "Connect to which?" prompt (answered Cancel) and opens no panel; the opened tab stays open with its cache path.
