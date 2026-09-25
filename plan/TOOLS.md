# TOOLS — The Tools menu

The Tools menu as the port builds it: Notepad++'s four digests (MD5, SHA-1, SHA-256, SHA-512) with their three commands each (Generate…, Generate from files…, Generate from selection into clipboard), the six digests the port adds (SHA-224, SHA-384, SHA3-256, SHA3-512, BLAKE2b, CRC-32) with the same three commands, the password hashes (bcrypt, scrypt, Argon2, PBKDF2) with their settings, salts and verifier, the Base64/Base58/Base32 windows, the Password Generator and the HTTP Request window (driven against `../npp/macos/test-http-server.py`, started by the test on a free port and stopped afterwards, never an outside server). Every window is driven through its own controls (`e2e_ui` / `e2e_act`); results are checked against published test vectors or against Python's `hashlib`/`hmac`/`zlib`/`base64` computing the same bytes. The QR items and Install Command Line Tool, which sit at the bottom of this menu, are planned in MACEXTRA; Run's commands are in RUN. Menu paths used by non-IDM items are the English ones (`Tools|Hashes|SHA3-256|Generate…`).

## Menu and windows

### TOOLS-001: The Tools menu has its items in Notepad++'s order plus the port's
- Covers: IDM_TOOL_*
- Channel: menu
- Steps: Dump the Tools menu tree (depth 3) with `e2e_menu`; read the state of the twelve IDM_TOOL_* ids.
- Expect: top level is Hashes, Base, Password Generator, HTTP Request, separator, QR Code from Selection, Read QR Code from Clipboard, separator, Install Command Line Tool (9 items); Hashes holds MD5, SHA-1, SHA-256, SHA-512, SHA-224, SHA-384, SHA3-256, SHA3-512, BLAKE2b, CRC-32, separator, bcrypt, scrypt, Argon2, PBKDF2; each of those 14 submenus holds exactly "Generate…", "Generate from files…", "Generate from selection into clipboard"; Base holds "Base64…", "Base58…", "Base32…"; all twelve IDM_TOOL_* items exist and are enabled with an empty document open.

### TOOLS-002: Notepad++'s command ids reach their own digest's items and no other
- Covers: IDM_TOOL_*
- Channel: mcp, ui
- Steps: For each of the twelve IDM_TOOL_* ids read its label/menu with `list_commands` (query "IDM_TOOL"); run the four *_GENERATE ids one after the other and read the digest window's title; `list_commands` with query "SHA-224" and "BLAKE2b".
- Expect: the labels are "Generate…", "Generate from files…", "Generate from selection into clipboard" under the menus MD5, SHA-1, SHA-256, SHA-512 (ids 48501-48512 as upstream); IDM_TOOL_MD5_GENERATE opens a window titled "Generate MD5 digest", SHA1 "Generate SHA-1 digest", SHA256 "Generate SHA-256 digest", SHA512 "Generate SHA-512 digest"; no IDM_* command is listed for SHA-224 or BLAKE2b items.

### TOOLS-003: Tool windows are non-modal singletons that leave the editor usable
- Covers: IDM_TOOL_SHA256_GENERATE, IDM_TOOL_MD5_GENERATE
- Channel: ui, keys, mcp
- Steps: Run IDM_TOOL_SHA256_GENERATE twice, then IDM_TOOL_MD5_GENERATE; list windows. With the digest window open, change the document with `edit_document` and type into the editor after focusing the main window. Close the window with its Close button; reopen it and close it with Escape.
- Expect: after the three commands exactly one digest window exists (the same window number), now titled "Generate MD5 digest"; it is an NSPanel, not modal, and not a sheet; the document edit and the typed text land in the editor; Close and Escape each hide the window; no alert is logged.

### TOOLS-004: Every kind of Tools window can be open at once, each under its own title
- Covers: IDM_TOOL_SHA512_GENERATE
- Channel: ui
- Steps: Open IDM_TOOL_SHA512_GENERATE, Tools|Hashes|Argon2|Generate…, Tools|Base|Base58…, Tools|Password Generator and Tools|HTTP Request; list the visible windows; close the Base58 window with `close_window`.
- Expect: five distinct visible panels titled "Generate SHA-512 digest", "Generate Argon2 digest", "Base58", "Password Generator", "HTTP Request", none modal; after closing Base58 the four others are still visible and the main window is still the main window.

## Digests: Generate…

### TOOLS-005: MD5 Generate… gives RFC 1321's test vectors as the text is set
- Covers: IDM_TOOL_MD5_GENERATE
- Channel: ui
- Steps: Run IDM_TOOL_MD5_GENERATE; with "Treat each line…" unticked and no HMAC key, set the input text view to each of "a", "abc", "message digest", "The quick brown fox jumps over the lazy dog", and read the result view after each.
- Expect: results are 0cc175b9c0f1b6a831c399e269772661, 900150983cd24fb0d6963f7d28e17f72, f96b697d7cb7938d525a2f31aaf161d0, 9e107d9d372bb6826bd81d3542a419d6; the result is lowercase hex, 32 characters, with no trailing newline.

### TOOLS-006: SHA-1 Generate… gives FIPS 180's vectors
- Covers: IDM_TOOL_SHA1_GENERATE
- Channel: ui
- Steps: Run IDM_TOOL_SHA1_GENERATE; set the input to "abc", then to "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq".
- Expect: a9993e364706816aba3e25717850c26c9cd0d89d, then 84983e441c3bd26ebaae4aa1f95129e5e54670f1; the window title is "Generate SHA-1 digest".

### TOOLS-007: SHA-256 Generate… gives FIPS 180's vectors
- Covers: IDM_TOOL_SHA256_GENERATE
- Channel: ui
- Steps: Run IDM_TOOL_SHA256_GENERATE; set the input to "abc", then to "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq".
- Expect: ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad, then 248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1.

### TOOLS-008: SHA-512 Generate… gives FIPS 180's vectors
- Covers: IDM_TOOL_SHA512_GENERATE
- Channel: ui
- Steps: Run IDM_TOOL_SHA512_GENERATE; set the input to "abc", then to the 896-bit message "abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu".
- Expect: ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f, then 8e959b75dae313da8cf4f72814fc143f8f7779c6eb9f7fa17299aeadb6889018501d289e4900f7e4331b99dec4b5433ac7d329eeb6dd26545e96e55b874be909.

### TOOLS-009: The port's six digests give their published vectors in the same window
- Covers: -
- Channel: ui
- Steps: For each of SHA-224, SHA-384, SHA3-256, SHA3-512, BLAKE2b, CRC-32: run `Tools|Hashes|<name>|Generate…`, set the input to "abc" (CRC-32: "123456789"), read title and result; for SHA3-256 also set 200 × "a".
- Expect: titles "Generate <name> digest"; SHA-224 23097d223405d8228642a477bda255b32aadbce4bda0b3f7e36c9da7; SHA-384 cb00753f45a35e8bb5a03d699ac65007272c32ab0eded1631a8b605a43ff5bed8086072ba1e7cc2358baeca134c825a7; SHA3-256 3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532; SHA3-512 b751850b1a57168a5693cd924b6b096e08f621827444f70d884f5d0240d2712e10e116e9192af3c91a7ec57647e3934057340b4cf408d5a56592f8274eec53f0; BLAKE2b (512-bit) ba80a53f981c4d0d6a2797b69f12f6e94c212f14685ac4b74b12bb6fdbffa2d17d87c5392aab792dc252d5de4533cc9518d38aa8dbf1925ab92386edd4009923; CRC-32 cbf43926 (8 hex digits); SHA3-256 of 200 "a" cce34485baf2bf2aca99b94833892a4f52896d3d153f7b840cc4f9fe695f1387.

### TOOLS-010: A Unicode text is hashed as its UTF-8 bytes
- Covers: IDM_TOOL_SHA256_GENERATE, IDM_TOOL_MD5_GENERATE
- Channel: ui
- Steps: For MD5 and SHA-256 Generate…, set the input to "Привет, 世界 😀 é" (é precomposed) and read the result; compute the digest of the same string's UTF-8 bytes with hashlib.
- Expect: each result equals hashlib's hex digest of `text.encode("utf-8")`.

### TOOLS-011: The digest follows the text as it is typed and empties with it
- Covers: IDM_TOOL_SHA1_GENERATE
- Channel: ui, keys
- Steps: Run IDM_TOOL_SHA1_GENERATE, focus the input view, type "ab" then "c" with `e2e_keys` text, reading the result after each; then select all in the input and delete it with keys.
- Expect: after "ab" the result is SHA-1("ab") = da23614e02469a0d7c7bd1bdab5c9c474b1904dc; after "c" it is a9993e364706816aba3e25717850c26c9cd0d89d; with the input emptied the result is empty (no digest of the empty string is shown).

### TOOLS-012: "Treat each line as a separate string" gives a digest per line
- Covers: IDM_TOOL_MD5_GENERATE
- Channel: ui
- Steps: In MD5 Generate…, tick "Treat each line as a separate string" and set the input to "abc\n\nx"; then to "abc\nx\n"; then untick it with the input "abc".
- Expect: first result is "900150983cd24fb0d6963f7d28e17f72\n\n9dd4e461268c8034f5c8564e155c67a6" (empty line kept empty); the second has two lines only (no digest for the empty tail after the last newline); unticked, the result is the single digest 900150983cd24fb0d6963f7d28e17f72.

### TOOLS-013: An HMAC key turns the six CommonCrypto digests into HMACs
- Covers: IDM_TOOL_MD5_GENERATE, IDM_TOOL_SHA1_GENERATE, IDM_TOOL_SHA256_GENERATE, IDM_TOOL_SHA512_GENERATE
- Channel: ui
- Steps: For each of MD5, SHA-1, SHA-256, SHA-512, SHA-224, SHA-384 Generate…: set the input to "The quick brown fox jumps over the lazy dog" and the "HMAC key (optional):" field to "key"; then tick each-line with input "a\nb"; then clear the key.
- Expect: the HMAC row is visible; results equal Python `hmac.new(b"key", msg, <alg>).hexdigest()` (SHA-256 gives f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8, MD5 80070713463e7749b90c2dc24911e275); with each-line the two lines are the HMACs of "a" and "b"; with the key cleared the result is the plain digest again.

### TOOLS-014: The HMAC row is hidden where there is no HMAC
- Covers: IDM_TOOL_SHA256_GENERATEFROMFILE
- Channel: ui
- Steps: Open Generate… for SHA3-256, SHA3-512, BLAKE2b and CRC-32, then IDM_TOOL_SHA256_GENERATEFROMFILE; list the controls of the window each time.
- Expect: no control titled "HMAC key (optional):" is visible in any of these, and none of them has an editable single-line key field; SHA3-256 of "abc" is still the plain vector.

### TOOLS-015: Copy to Clipboard takes the result exactly
- Covers: IDM_TOOL_SHA512_GENERATE
- Channel: ui, clipboard
- Steps: In SHA-512 Generate… with each-line ticked set the input to "abc\ndef"; click "Copy to Clipboard"; read the clipboard.
- Expect: the clipboard text equals the result view's text (two 128-hex-digit lines joined by "\n", no trailing newline); the document is unchanged.

### TOOLS-016: The digest window keeps its input when switched to another digest
- Covers: IDM_TOOL_SHA256_GENERATE
- Channel: ui
- Steps: Run IDM_TOOL_SHA256_GENERATE, set input "abc"; run `Tools|Hashes|SHA3-256|Generate…` without closing.
- Expect: the same window is retitled "Generate SHA3-256 digest"; its input still reads "abc" and its result is 3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532.

## Digests: from files

### TOOLS-017: MD5 Generate from files… lists "digest  name" for each chosen file
- Covers: IDM_TOOL_MD5_GENERATEFROMFILE
- Channel: ui, modal, files
- Steps: Write `a.txt` = "abc" and `b.txt` = "message digest" in `tmp`; run IDM_TOOL_MD5_GENERATEFROMFILE; queue an open-panel answer with both paths; click "Choose files to generate MD5...".
- Expect: the window is titled "Generate MD5 digest from files"; no input view and no each-line box are visible; the result is "900150983cd24fb0d6963f7d28e17f72  a.txt\nf96b697d7cb7938d525a2f31aaf161d0  b.txt" (two spaces, file name only, in the chosen order); the modal log shows one open panel answered with the two paths.

### TOOLS-018: SHA-1, SHA-256 and SHA-512 Generate from files… hash the file bytes
- Covers: IDM_TOOL_SHA1_GENERATEFROMFILE, IDM_TOOL_SHA256_GENERATEFROMFILE, IDM_TOOL_SHA512_GENERATEFROMFILE
- Channel: ui, modal, files
- Steps: For each of the three ids: write a file with 256 bytes 0x00..0xFF and a UTF-8 file "Привет\r\n"; run the command, queue both paths, click the Choose button (its title "Choose files to generate SHA-1..." etc.).
- Expect: each line's digest equals hashlib's digest of the file's bytes (CRLF and binary bytes included, no text conversion); the button title names the digest; the title is "Generate <name> digest from files".

### TOOLS-019: From files: an empty file, a Unicode name and a large file
- Covers: IDM_TOOL_SHA256_GENERATEFROMFILE
- Channel: ui, modal, files
- Steps: Write an empty file `empty.txt`, a file named `отчёт 1.txt` with "x", and a 20 MB file of pseudo-random bytes; choose all three in SHA-256 from files.
- Expect: the empty file's line starts with e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855; the second line ends with "  отчёт 1.txt"; the large file's digest equals hashlib's; the result appears within 10 s.

### TOOLS-020: Cancelling the file choice changes nothing
- Covers: IDM_TOOL_SHA1_GENERATEFROMFILE
- Channel: ui, modal
- Steps: In SHA-1 from files, choose one file (queued) so a line is shown; then queue a cancel (None) and click the Choose button again.
- Expect: the result still shows the first line unchanged; no alert is logged; the modal log shows the second panel cancelled.

### TOOLS-021: The port's digests from files: CRC-32 and SHA3-512
- Covers: -
- Channel: ui, modal, files
- Steps: Write `a.txt` = "abc", `b.txt` = "123456789"; run `Tools|Hashes|CRC-32|Generate from files…`, choose both; then `Tools|Hashes|SHA3-512|Generate from files…`, choose `a.txt`.
- Expect: CRC-32 result is "352441c2  a.txt\ncbf43926  b.txt"; SHA3-512 result is the "abc" vector followed by "  a.txt"; titles "Generate CRC-32 digest from files" / "Generate SHA3-512 digest from files".

### TOOLS-022: Copy to Clipboard in from-files mode takes every line
- Covers: IDM_TOOL_MD5_GENERATEFROMFILE
- Channel: ui, clipboard, modal
- Steps: Choose two files in MD5 from files; click "Copy to Clipboard".
- Expect: the clipboard text equals the two-line result exactly.

## Digests: into the clipboard

### TOOLS-023: The four Notepad++ digests of the selection go to the clipboard
- Covers: IDM_TOOL_MD5_GENERATEINTOCLIPBOARD, IDM_TOOL_SHA1_GENERATEINTOCLIPBOARD, IDM_TOOL_SHA256_GENERATEINTOCLIPBOARD, IDM_TOOL_SHA512_GENERATEINTOCLIPBOARD
- Channel: mcp, clipboard
- Steps: New document "xabcx"; select columns 2-4 ("abc"); for each of the four ids set the clipboard to "" and run the command.
- Expect: the clipboard holds exactly the "abc" vector of that digest (lowercase hex, no newline); the document text and selection are unchanged; no window opens.

### TOOLS-024: With nothing selected the whole document is hashed
- Covers: IDM_TOOL_MD5_GENERATEINTOCLIPBOARD, IDM_TOOL_SHA256_GENERATEINTOCLIPBOARD
- Channel: mcp, clipboard
- Steps: New document "abc" with the caret at the end and no selection; run IDM_TOOL_MD5_GENERATEINTOCLIPBOARD; then empty the document and run IDM_TOOL_SHA256_GENERATEINTOCLIPBOARD.
- Expect: first clipboard is 900150983cd24fb0d6963f7d28e17f72 (the port hashes the document when nothing is selected); for the empty document the clipboard is e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 (SHA-256 of nothing).

### TOOLS-025: A Unicode selection in a non-UTF-8 file is hashed as UTF-8
- Covers: IDM_TOOL_SHA1_GENERATEINTOCLIPBOARD
- Channel: mcp, clipboard, files
- Steps: Write a Windows-1251 file containing "Привет мир" (bytes cp1251), open it (the app detects/labels 1251), select "Привет"; run IDM_TOOL_SHA1_GENERATEINTOCLIPBOARD.
- Expect: the clipboard equals hashlib.sha1("Привет".encode("utf-8")) (Notepad++ hashes its UTF-8 buffer, not the file's bytes).

### TOOLS-026: A selection spanning CRLF lines includes the line ends
- Covers: IDM_TOOL_MD5_GENERATEINTOCLIPBOARD
- Channel: mcp, clipboard
- Steps: New document "one\r\ntwo" with CRLF line ends (set EOL with IDM_FORMAT_TODOS if needed); select all; run IDM_TOOL_MD5_GENERATEINTOCLIPBOARD.
- Expect: the clipboard equals md5(b"one\r\ntwo").

### TOOLS-027: The port's six digests into the clipboard
- Covers: -
- Channel: mcp, clipboard
- Steps: For each of SHA-224, SHA-384, SHA3-256, SHA3-512, BLAKE2b, CRC-32: document "abc" (CRC-32: "123456789") selected; run `Tools|Hashes|<name>|Generate from selection into clipboard`.
- Expect: the clipboard holds the vector listed in TOOLS-009 for that digest.

## Password hashes

### TOOLS-028: Each password-hash window shows only its own settings, with its defaults
- Covers: -
- Channel: ui
- Steps: Open `Tools|Hashes|<kind>|Generate…` for bcrypt, scrypt, Argon2 and PBKDF2; list visible controls each time.
- Expect: titles "Generate <kind> digest"; bcrypt shows "Cost (4-31):" = 12 and "Version:" popup [2b, 2a, 2y] with 2b; scrypt shows "N, as a power of 2:" = 15, "Block size (r):" = 8, "Parallelism (p):" = 1, "Hash length (bytes):" = 32; Argon2 shows "Variant:" [Argon2id, Argon2i, Argon2d], "Memory (KiB):" 19456, "Iterations:" 2, "Parallelism:" 1, hash length 32; PBKDF2 shows "Digest:" [SHA-256, SHA-512, SHA-1], "Iterations:" 600000, hash length 32; every kind has "Salt (hexadecimal):" with placeholder "Empty: a random salt each time", Random, the input, each-line box, "Show the bare key in hexadecimal", the result, the "Hash to check the password against:" field with Verify, Copy to Clipboard and Close; no kind shows another kind's fields.

### TOOLS-029: bcrypt with a vector's salt and cost gives the vector's hash
- Covers: -
- Channel: ui
- Steps: In bcrypt Generate…: input "U*U", cost 5, version 2a, salt "10 41 04 10 41 04 10 41 04 10 41 04 10 41 04 10"; wait for the result; tick "Show the bare key in hexadecimal"; untick it, tick each-line and set input "U*U\n\nU*U".
- Expect: result is "$2a$05$CCCCCCCCCCCCCCCCCCCCC.E5YPO9kmyuRGyh0XouQYb4YMJKvyOeW"; bare key is 46 hex characters; per line the result is the vector, an empty line, the vector.

### TOOLS-030: Verify says match, no match, and "not such a hash"
- Covers: -
- Channel: ui
- Steps: In bcrypt Generate… with input "U*U", put the vector hash of TOOLS-029 into the check field and click Verify; change the input to "U*V" and Verify; put "5f4dcc3b5aa765d61d8327deb882cf99" into the check field and Verify; also verify "пароль" against "$2b$06$abcdefghijklmnopqrstuu0RbYLPpyLm/x71XGmlHQAdqmD5AbL2G".
- Expect: the verdict line reads "The password matches the hash.", then "The password does not match the hash.", then "This is not a bcrypt, scrypt, Argon2 or PBKDF2 hash."; the Cyrillic password matches its vector.

### TOOLS-031: bcrypt's refusals are said in words and no hash is shown
- Covers: -
- Channel: ui
- Steps: In bcrypt Generate… (cost 5): input of 80 "x"; then input "x" with salt "0102"; then salt "xyz"; then empty salt and cost 40.
- Expect: 80 bytes: a 60-character hash is shown and the problem line reads "bcrypt reads only the first 72 bytes."; salt "0102": "bcrypt takes a salt of exactly 16 bytes." and an empty result; "xyz": "The salt is not valid hexadecimal." and an empty result; cost 40: "The cost must be between 4 and 31." and an empty result.

### TOOLS-032: Without a salt every hash gets its own; Random makes sixteen new bytes
- Covers: -
- Channel: ui
- Steps: bcrypt Generate…, cost 5, empty salt, each-line ticked, input "same\nsame"; then click Random twice, reading the salt field each time; verify each of the two result lines against "same" with the Verify box.
- Expect: the two lines differ, both start with "$2b$05$", both verify as matching; each Random fills the salt with 32 hex digits and the two salts differ.

### TOOLS-033: scrypt gives RFC 7914's vector and a verifiable string
- Covers: -
- Channel: ui
- Steps: scrypt Generate…: input "pleaseletmein", salt = hex of "SodiumChloride", N power 14, r 8, p 1, length 32; read the result; tick bare key and read again.
- Expect: the string starts "$scrypt$ln=14,r=8,p=1$U29kaXVtQ2hsb3JpZGU$"; the bare key is 7023bdcb3afd7348461c06cd81fd38ebfda8fbba904f8e3ea9b543f6545da1f2 and equals `hashlib.scrypt(b"pleaseletmein", salt=b"SodiumChloride", n=16384, r=8, p=1, dklen=32)`; Verify of the string with the input says it matches.

### TOOLS-034: scrypt refuses settings that would need more than 2 GB
- Covers: -
- Channel: ui
- Steps: scrypt Generate…, input "x", N power 24, r 64.
- Expect: the problem line is non-empty and the result is empty within 2 s; the app stays responsive (a later `get_document` answers).

### TOOLS-035: Argon2's three variants give the reference implementation's strings
- Covers: -
- Channel: ui
- Steps: Argon2 Generate…: input "password", salt = hex of "somesalt", memory 64, iterations 2, parallelism 2, length 32; select Argon2id, Argon2i, Argon2d in turn and read the result; then memory 8 with parallelism 4; then salt "0102".
- Expect: "$argon2id$v=19$m=64,t=2,p=2$c29tZXNhbHQ$lDh0Fd+4TtGXdGWh6GJgc630K9Turh+qHdTiOh/2hZ8", "$argon2i$v=19$m=64,t=2,p=2$c29tZXNhbHQ$u3EC2QpYDSqhwag4F/JKsYx8yBDM0sKg0MgMlK0pkWc", "$argon2d$v=19$m=64,t=2,p=2$c29tZXNhbHQ$1q8bgD0xYiK3sMCt/uIryr7jP0g04fs9QOITesC7M88"; memory 8 with 4 lanes and the 2-byte salt each give a problem line and no result.

### TOOLS-036: PBKDF2 gives the known key and a verifiable string for each digest
- Covers: -
- Channel: ui
- Steps: PBKDF2 Generate…: input "password", salt = hex of "salt", iterations 4096, length 32, digest SHA-256; read result and bare key; switch digest to SHA-512 and SHA-1 and read the bare key.
- Expect: the string starts "$pbkdf2-sha256$4096$c2FsdA$"; SHA-256 bare key c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a; the SHA-512 and SHA-1 bare keys equal `hashlib.pbkdf2_hmac(<alg>, b"password", b"salt", 4096, 32)`; Verify of the string with "password" matches, with "passwor" does not.

### TOOLS-037: Password hashes from files: a line per file, of the file's bytes
- Covers: -
- Channel: ui, modal, files
- Steps: Write `k1.txt` = "password", `k2.txt` = "other"; for each kind open `Tools|Hashes|<kind>|Generate from files…` (PBKDF2: salt hex of "salt", 4096 rounds, bare key ticked), queue both paths and click "Choose files to generate <kind>...".
- Expect: titles "Generate <kind> digest from files"; the input and each-line box are hidden; two lines ending "  k1.txt" and "  k2.txt"; for PBKDF2 the first line is "c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a  k1.txt"; for scrypt the key part of the first line is hashlib.scrypt of "password" with the salt in its own string; Copy to Clipboard takes both lines.

### TOOLS-038: Password hashes of the selection go to the clipboard with default settings
- Covers: -
- Channel: mcp, clipboard, ui
- Steps: Document "user: hunter2 end", select "hunter2"; run `Tools|Hashes|<kind>|Generate from selection into clipboard` for the four kinds, reading the clipboard each time; verify bcrypt's and Argon2's strings with the kind's Verify box and input "hunter2"; then with an empty document set the clipboard to "keep" and run the bcrypt command.
- Expect: prefixes "$2b$12$", "$scrypt$ln=15,r=8,p=1$", "$argon2id$v=19$m=19456,t=2,p=1$", "$pbkdf2-sha256$600000$"; scrypt's and PBKDF2's keys equal hashlib's with the salt decoded from the string; bcrypt and Argon2 verify with "hunter2" and not with "hunter3"; with the empty document the clipboard still reads "keep".

## Base

### TOOLS-039: Base64 encodes text as UTF-8 and hex bytes as themselves
- Covers: -
- Channel: ui
- Steps: `Tools|Base|Base64…`, Encode, input is Text: input "Привет"; switch to "Bytes in hexadecimal" and input "fb ff"; tick "Base64 (URL-safe)"; then input "fb f".
- Expect: "0J/RgNC40LLQtdGC"; "+/8="; URL-safe "-_8="; for "fb f" an empty result and the problem line "The input is not bytes written in hexadecimal."; the window has no popup to choose another base; the result label reads "Result:".

### TOOLS-040: Base64 decodes to text and bytes, and refuses rubbish
- Covers: -
- Channel: ui
- Steps: Base64 window, Decode: input "SGVs\nbG8=\n"; then "SGVsbG8" (unpadded); then "SGVsbG8*"; then "//8=".
- Expect: text "Hello" and bytes "48656c6c6f" for both of the first two; "SGVsbG8*" gives empty outputs and "The input is not valid Base64."; "//8=" gives bytes "ffff", an empty text and a problem line starting "The decoded bytes are not UTF-8 text"; decode shows "Text:" and "Bytes in hexadecimal:" with a Copy button each.

### TOOLS-041: Base58 and Base58Check follow Bitcoin's alphabet
- Covers: -
- Channel: ui
- Steps: `Tools|Base|Base58…`: encode "Hello World!"; encode hex "0000287fb4cd"; tick Base58Check and encode hex "00f54a5851e9372b87810a8e60cdd2e7cfd80b6e31"; Decode "2NEpo7TZRRrLZSi2U", "2NEpo7TZRRrLZSi20", and (Base58Check) "1PMycacnJaSqwwJqjawXBErnLsZ7RkXUAt".
- Expect: "2NEpo7TZRRrLZSi2U"; "11233QC4" (leading zero bytes as 1s); "1PMycacnJaSqwwJqjawXBErnLsZ7RkXUAs"; decode gives "Hello World!" and bytes 48656c6c6f20576f726c6421; the "0" input gives "The input is not valid Base58." and no output; the address with a wrong last character is refused; the box is titled "Base58Check".

### TOOLS-042: Base32 gives RFC 4648's vectors both ways
- Covers: -
- Channel: ui
- Steps: `Tools|Base|Base32…`: encode each of "f", "fo", "foo", "foob", "fooba", "foobar"; decode "MZXW6YTBOI======", "mzxw6ytboi", "MZXW1".
- Expect: MY======, MZXQ====, MZXW6===, MZXW6YQ=, MZXW6YTB, MZXW6YTBOI======; both decodings give "foobar" / 666f6f626172; "MZXW1" gives empty outputs and a problem line; the window has no variant box.

### TOOLS-043: A Base window opens with the editor's selection as input
- Covers: -
- Channel: ui, mcp
- Steps: Document "see SGVsbG8= here", select "SGVsbG8="; run `Tools|Base|Base64…`; choose Decode; click the Copy beside the text.
- Expect: the input view reads "SGVsbG8="; the text output is "Hello"; the clipboard reads "Hello".

### TOOLS-044: Empty input gives empty output and no complaint
- Covers: -
- Channel: ui
- Steps: For Base64, Base58, Base32, in both directions, set the input empty.
- Expect: every output view is empty and the problem line is empty.

## Password Generator

### TOOLS-045: The generator opens with a password made from its defaults
- Covers: -
- Channel: ui
- Steps: With fresh preferences run `Tools|Password Generator`; read the controls.
- Expect: "Length:" 20, "Number of passwords:" 1, Uppercase, Lowercase, Digits and "Symbols:" ticked with "!@#$%^&*()-_=+[]{};:,.<>?/~", look-alikes unticked, "At least one character of each kind" ticked, Hash popup "None"; the result already holds one password of 20 characters, all from those sets, with at least one of each kind; the entropy line reads "Entropy: about 129 bits".

### TOOLS-046: Several passwords of a chosen shape, all different
- Covers: -
- Channel: ui
- Steps: Length 24, number 5, untick Symbols and look-alikes, keep each-kind; click Generate.
- Expect: five lines, pairwise different, each 24 characters of [A-Za-z0-9] containing an uppercase letter, a lowercase letter and a digit; "Entropy: about 142 bits".

### TOOLS-047: Own symbols, look-alikes left out
- Covers: -
- Channel: ui
- Steps: Untick Uppercase and Lowercase, keep Digits, Symbols "# $ %", length 40, number 1, Generate; then tick "Leave out characters that look alike (O 0 o I l 1)" and Generate 20 times.
- Expect: the password is 40 characters from "0123456789#$%" with at least one of #, $, %; with look-alikes left out no password contains 0 or 1.

### TOOLS-048: No kind of character chosen is said so
- Covers: -
- Channel: ui
- Steps: Untick Uppercase, Lowercase, Digits and Symbols; Generate.
- Expect: the result is empty and the entropy line reads "Choose at least one kind of character."

### TOOLS-049: Lengths at the edges
- Covers: -
- Channel: ui
- Steps: With all kinds ticked set the length to "1", "0", "abc" and "1000" in turn and Generate.
- Expect: "1", "0" and "abc" each give a single-character password; "1000" gives a 1000-character password; the app does not hang.

### TOOLS-050: A hash of each password, of the kind chosen
- Covers: -
- Channel: ui
- Steps: Length 16, number 2; read the Hash popup's items; choose SHA-256 and Generate; choose PBKDF2 and Generate; choose None and Generate.
- Expect: the popup lists None, bcrypt, scrypt, Argon2, PBKDF2, MD5, SHA-1, SHA-256, SHA-512, SHA-224, SHA-384, SHA3-256, SHA3-512, BLAKE2b, CRC-32; with SHA-256 a second text view shows two lines, each hashlib.sha256 of the matching password; with PBKDF2 each line starts "$pbkdf2-sha256$600000$" and its key equals hashlib's for that password; with None the hash view is hidden and empty.

### TOOLS-051: Copy to Clipboard and Insert into Document
- Covers: -
- Channel: ui, clipboard, mcp
- Steps: Document "password=" with the caret at the end; Generate one password of 12; click Copy to Clipboard; click Insert into Document; undo once in the editor.
- Expect: the clipboard equals the password; the document becomes "password=" + the password; one undo gives "password=" back.

### TOOLS-052: The generator's settings are remembered across a restart
- Covers: -
- Channel: ui, launch
- Steps: Set length 12, only Digits and Symbols "# $ %", Hash SHA-1, Generate, close the window; `app.restart()`; open the generator again (test uses `fresh_app` and leaves defaults cleared).
- Expect: after the restart the fields read length 12, Uppercase/Lowercase unticked, Digits ticked, symbols "# $ %", Hash SHA-1.

## HTTP Request

### TOOLS-053: GET with parameters and headers reaches the server as typed
- Covers: -
- Channel: ui
- Steps: Start the test server; `Tools|HTTP Request`; method GET, address "127.0.0.1:<port>/echo?fixed=1" (no scheme), Parameters "q=a b&c\nимя=Жук", Headers "X-Custom: 42\n# not sent\nAccept: application/json"; click Send; wait for the status line.
- Expect: the status line reads "HTTP/1.1 200 OK  ·  <n> ms  ·  <n> bytes"; the JSON answer (Body view) has method GET, query [["fixed","1"],["q","a b&c"],["имя","Жук"]], headers x-custom "42", accept "application/json", user-agent starting "NotepadMac/", and no "# not sent" header.

### TOOLS-054: POST, PUT, PATCH and DELETE carry the body byte for byte
- Covers: -
- Channel: ui
- Steps: For each method: address /echo, Body "{\"имя\": \"Жук\", \"n\": [1, 2]}\n", content type popup "application/json"; Send.
- Expect: the echoed method is that method; body equals the text exactly; content-type "application/json"; content-length equals the UTF-8 byte count.

### TOOLS-055: A Content-Type among the headers wins; no body, no content type
- Covers: -
- Channel: ui
- Steps: POST to /echo with body "a,b" and popup "application/json" but header "content-type: text/csv"; Send; then clear header and body and Send GET.
- Expect: the first echo shows content-type "text/csv" only; the second shows no content-type header and an empty body.

### TOOLS-056: HEAD shows headers and no body; OPTIONS arrives as OPTIONS
- Covers: -
- Channel: ui
- Steps: HEAD /echo, Send, switch the answer to Headers; then OPTIONS /echo, Send.
- Expect: HEAD: status 200, the Body view is empty, the Headers view starts "HTTP/1." and contains "X-Test-Server: notepad" and a Content-Length > 0; OPTIONS: echoed method "OPTIONS".

### TOOLS-057: A name and password go as Basic authentication and are not remembered
- Covers: -
- Channel: ui, launch
- Steps: Options section: user "igor", password "pa:ss word"; GET /echo; Send; close the window; `app.restart()`; reopen HTTP Request and read the Options fields.
- Expect: the echoed authorization is "Basic " + base64("igor:pa:ss word"); after the restart the method, address and user "igor" are restored and the password field is empty.

### TOOLS-058: Redirects are followed, or shown as the 302 they are
- Covers: -
- Channel: ui
- Steps: GET /redirect with "Follow redirects" ticked; Send; then untick it and Send; look at the Headers view.
- Expect: followed: status 200 and the echoed query [["redirected","1"]]; not followed: status line contains "302", body "moved", headers include "Location: /echo?redirected=1".

### TOOLS-059: 404 and 500 are answers, not errors
- Covers: -
- Channel: ui
- Steps: GET /status/404, Send; GET /status/500, Send.
- Expect: status lines contain "404" and "500"; the bodies are "status 404" / "status 500"; no alert is logged.

### TOOLS-060: The body is read in its charset, unpacked, or shown as bytes
- Covers: -
- Channel: ui
- Steps: GET /latin1, /gzip and /binary in turn.
- Expect: "café crème"; "unpacked text"; "The answer is not text: 4 bytes.\n\nfffe00c3".

### TOOLS-061: A slow server times out and a closed port is an error in words
- Covers: -
- Channel: ui
- Steps: Options timeout 1, GET /slow, Send, time it; then address "127.0.0.1:1/", Send.
- Expect: the status line holds an error text (no status code) within 2.5 s of Send; the closed port also gives an error text and an empty answer; the Send button is usable again afterwards.

### TOOLS-062: Format JSON lays out the answer; Copy takes the view
- Covers: -
- Channel: ui, clipboard
- Steps: POST /echo with body "{\"ok\":true}" and "Format JSON" unticked; Send; tick "Format JSON"; click the answer's Copy.
- Expect: unticked the answer is one line; ticked it starts "{\n  \"method\": \"POST\",\n  \"path\": \"/echo\"" and parses to the same object; the clipboard equals the shown answer.

### TOOLS-063: Paste curl Command fills the window and that request is sent
- Covers: -
- Channel: ui, clipboard
- Steps: Put on the clipboard "curl -X PATCH 'http://127.0.0.1:<port>/echo?x=1' -H 'X-Pasted: yes' -u me:pw --data-raw 'a=1' -k"; click "Paste curl Command"; read the controls; Send; click "Copy as curl" and read the clipboard.
- Expect: method PATCH, address ending "/echo?x=1", Headers "X-Pasted: yes", Body "a=1", user "me", password "pw", "Allow invalid certificates" ticked, "Follow redirects" unticked; the server sees PATCH with x-pasted "yes", body "a=1", Basic authorization; the copied command starts "curl -X PATCH 'http://127.0.0.1:" and contains "-H 'X-Pasted: yes'", "-u 'me:pw'", "--data-raw 'a=1'" and ends "-k".

### TOOLS-064: curl commands as found in the wild are understood
- Covers: -
- Channel: ui, clipboard
- Steps: For each command, set it on the clipboard, click Paste curl Command and read the controls: (a) a browser's "curl 'https://example.com/api/login' \\\n  -H 'accept: */*' \\\n  --data-raw $'{\"t\":\"a\\nb \\u0416 it\\'s\"}' --compressed"; (b) "curl -sSLkX DELETE -uadmin:secret -m10 http://localhost:8080/x"; (c) "curl -G --data-urlencode 'q=a b&c' -d page=2 --url example.com/find -I"; (d) "curl --json '{\"a\":1}' --oauth2-bearer tok -A agent/1 https://example.com/j"; (e) "curl -d a=1 -d b=2 https://example.com/f".
- Expect: (a) POST, body with a real newline, "Ж" and "it's", Follow redirects unticked; (b) DELETE, user admin, password secret, timeout 10, invalid certificates allowed, redirects followed; (c) HEAD with address "example.com/find?q=a%20b%26c&page=2" and no body; (d) POST with headers Content-Type and Accept application/json, Authorization "Bearer tok", User-Agent "agent/1"; (e) body "a=1&b=2".

### TOOLS-065: What is not a usable curl command is refused in words and changes nothing
- Covers: -
- Channel: ui, clipboard
- Steps: With the window filled (method PATCH), paste in turn "ls -la", "wget http://example.com", "curl -X POST -H 'A: b'", "curl -d @secrets.txt http://example.com", "curl -F file=@a.png http://example.com", "curl file:///etc/passwd".
- Expect: status line texts "This is not a curl command." (for ls and wget), "The command has no address.", one starting "The command reads its data from a file", one starting "Forms and uploads", one containing "not an http or https address"; the method stays PATCH each time.

### TOOLS-066: Only http and https addresses are sent
- Covers: -
- Channel: ui
- Steps: Address "mailto:someone", Send; "file:///etc/passwd", Send; "ftp://example.com/x", Send; empty address, Send.
- Expect: each time, the empty address included, the status line reads "The address is not an http or https address." and the answer view is empty; no HTTP status line is shown.

### TOOLS-067: Open in New Document gives the answer a tab in its language
- Covers: -
- Channel: ui, mcp
- Steps: POST /echo with "Format JSON" ticked, Send, click "Open in New Document"; then GET /status/404, Send, Open in New Document.
- Expect: a new tab whose text equals the answer view (laid out) and whose language is json; the second new tab holds "status 404" in Normal Text; the main window is in front.

### TOOLS-068: Sections are shown one at a time with a hint on how to write them
- Covers: -
- Channel: ui
- Steps: Select Parameters, Headers, Body and Options in the section control in turn, listing the visible controls.
- Expect: Parameters shows its text view and "One to a line: name=value. They are added to the address, encoded."; Headers "One to a line: Name: value"; Body its text view, "Sent as it is written, in UTF-8." and the "Content type:" popup [None, application/json, application/x-www-form-urlencoded, text/plain, application/xml]; Options shows User name, Password (secure field), "Timeout (seconds):" 30, Follow redirects, Allow invalid certificates and no hint; only the chosen section's editor is visible.

## Localisation

### TOOLS-069: The Tools menu and windows are translated and nothing is cut
- Covers: IDM_TOOL_SHA256_GENERATE
- Channel: launch, ui, menu, snapshot
- Steps: Restart with `-NppMac.localizationFile russian.xml`; read the Tools menu; open SHA-384 Generate…, Argon2 Generate…, Base58…, Password Generator and HTTP Request; snapshot each window; restart without the option.
- Expect: the Hashes submenu is "Хеши", HTTP Request is "HTTP-запрос"; the digest window's title contains "SHA-384" and not "Generate"; the Password Generator is titled "Генератор паролей" and its uppercase box reads "Заглавные буквы (A-Z)"; the HTTP window's Send button reads "Отправить"; the snapshots show no label or button text cut off (checked by eye or by comparing control frames against their text).
