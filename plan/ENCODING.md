# ENCODING — Encoding menu, character sets, detection and line endings on disk

The Encoding menu (56 commands): the five "interpret as" items (ANSI, UTF-8, UTF-8-BOM, UTF-16 BE BOM, UTF-16 LE BOM), the 46 "Character sets" items (Encode in: the bytes stay, their reading changes), and the five "Convert to" items (the text stays, the bytes written change). Also in scope: how a file's encoding is found on open (BOM, UTF-16 without a mark, UTF-8 validity, uchardet with the port's Cyrillic arbitration, the MISC./New Document preferences that steer it), bytes that are not valid in the encoding, the encoding and EOL shown in the status bar and the menu checkmarks, the EOL format of saved files, and the encoding kept by reload, Save As and the session. Out of scope: the Edit > EOL Conversion commands themselves (IDM_FORMAT_TODOS/TOUNIX/TOMAC belong to EDIT; here only the EOL a file is read with, shown with and written with), the Preferences dialog controls (SETTINGS; here preferences are set with `app.set_prefs`), and the MIME/Base64 tools. Files are always written byte-exact with Python codecs into `tmp` and checked byte-exact on disk after save.

## Interpret as: ANSI, UTF-8, UTF-8-BOM, UTF-16

### ENCODING-001: Each Unicode/ANSI item saves the same text in its own byte form
- Covers: IDM_FORMAT_AS_UTF_8, IDM_FORMAT_UTF_8, IDM_FORMAT_UTF_16BE, IDM_FORMAT_UTF_16LE, IDM_FORMAT_ANSI
- Channel: mcp, files
- Steps: For each of the five items (with the expected bytes): write "round trip\n" as plain UTF-8 to tmp/enc.txt, open it, run the item, save (IDM_FILE_SAVE), close and reopen the file.
- Expect: after the command `doc()["modified"]` is true; bytes on disk are exactly: AS_UTF_8 `b"round trip\n"`, UTF_8 `EF BB BF` + text, UTF_16BE `FE FF` + text.encode("utf-16-be"), UTF_16LE `FF FE` + text.encode("utf-16-le"), ANSI text.encode("latin-1"); the reopened document's text is "round trip\n" and `doc()["encoding"]` is UTF-8 / UTF-8-BOM / UTF-16BE / UTF-16LE / ISO-8859-1 respectively.

### ENCODING-002: Non-ASCII text survives each Unicode item
- Covers: IDM_FORMAT_UTF_8, IDM_FORMAT_UTF_16BE, IDM_FORMAT_UTF_16LE
- Channel: mcp, files
- Steps: For each of UTF-8-BOM, UTF-16 BE BOM, UTF-16 LE BOM: open a UTF-8 file containing "snow ☃ é 日本 😀\n", run the item, save, reopen.
- Expect: the file bytes equal BOM + the text in that encoding (the emoji as a surrogate pair in UTF-16); the reopened text equals the original exactly.

### ENCODING-003: The checkmark follows the current encoding (radio group)
- Covers: IDM_FORMAT_ANSI, IDM_FORMAT_AS_UTF_8, IDM_FORMAT_UTF_8, IDM_FORMAT_UTF_16BE, IDM_FORMAT_UTF_16LE
- Channel: mcp, menu
- Steps: With a new document, run each of the five items in turn and after each read `app.menu()` for all five ids.
- Expect: exactly one of the five is checked each time, the one just run; a new document (default preferences) has IDM_FORMAT_AS_UTF_8 checked.

### ENCODING-004: Choosing the encoding a document already has does not dirty it
- Covers: IDM_FORMAT_AS_UTF_8, IDM_FORMAT_UTF_8
- Channel: mcp
- Steps: Open an unmodified UTF-8 file and run IDM_FORMAT_AS_UTF_8; open an unmodified UTF-8-BOM file and run IDM_FORMAT_UTF_8.
- Expect: `doc()["modified"]` stays false in both (upstream only sets the dirty flag when the mode changes); the title bar/tab shows no unsaved mark. (Probed: the port marks the document modified — expected xfail.)

### ENCODING-005: ANSI and UTF-8 reinterpret the file's bytes, as Notepad++ does
- Covers: IDM_FORMAT_ANSI, IDM_FORMAT_AS_UTF_8
- Channel: mcp, files
- Steps: Open a UTF-8 file with b"caf\xc3\xa9\n" (unmodified) and run IDM_FORMAT_ANSI; then run IDM_FORMAT_AS_UTF_8 again; save.
- Expect: under ANSI the text reads "cafÃ©\n" (the same two bytes read as ANSI), under UTF-8 again "café\n"; switching between ANSI and UTF-8 without BOM leaves the document unmodified; the file bytes are unchanged b"caf\xc3\xa9\n". (Probed: the port keeps the text and changes the bytes written instead — expected xfail, see report.)

### ENCODING-006: A UTF-16 item on an untitled document decides the bytes of its first save
- Covers: IDM_FORMAT_UTF_16LE
- Channel: mcp, modal, files
- Steps: `app.new("abc\n")`, run IDM_FORMAT_UTF_16LE, queue a save panel answer tmp/new16.txt and run IDM_FILE_SAVE.
- Expect: the file is `FF FE 61 00 62 00 63 00 0A 00`; the status bar encoding field reads "UTF-16 LE BOM".

### ENCODING-007: Undo does not undo an encoding change
- Covers: IDM_FORMAT_UTF_8
- Channel: mcp, keys
- Steps: Open a UTF-8 file, type "x" at the start, save, run IDM_FORMAT_UTF_8, then press cmd+z twice.
- Expect: the "x" is undone but the status bar still reads "UTF-8-BOM" and `doc()["modified"]` stays true (the encoding differs from disk even at the savepoint); saving writes EF BB BF followed by the original text.

### ENCODING-008: Interpret-as on a modified charset document asks to save first
- Covers: IDM_FORMAT_AS_UTF_8
- Channel: mcp, modal
- Steps: Open a Windows-1251 file, run IDM_FORMAT_WIN_1251, type a character, then run IDM_FORMAT_AS_UTF_8 with a queued alert answer "No" (button 2).
- Expect: an alert "Save Current Modification" is logged; with "No" nothing changes (text, encoding, typed character kept). (Upstream NppCommands.cpp IDM_FORMAT_ANSI…AS_UTF_8 with encoding != -1; the port shows no alert today — expected xfail.)

## Character sets (Encode in)

### ENCODING-009: Every character set reads a file written in it and saves the same bytes
- Covers: IDM_FORMAT_ISO_8859_6, IDM_FORMAT_DOS_720, IDM_FORMAT_WIN_1256, IDM_FORMAT_ISO_8859_4, IDM_FORMAT_ISO_8859_13, IDM_FORMAT_DOS_775, IDM_FORMAT_WIN_1257, IDM_FORMAT_ISO_8859_14, IDM_FORMAT_ISO_8859_5, IDM_FORMAT_KOI8R_CYRILLIC, IDM_FORMAT_KOI8U_CYRILLIC, IDM_FORMAT_MAC_CYRILLIC, IDM_FORMAT_DOS_855, IDM_FORMAT_DOS_866, IDM_FORMAT_WIN_1251, IDM_FORMAT_DOS_852, IDM_FORMAT_WIN_1250, IDM_FORMAT_BIG5, IDM_FORMAT_GB2312, IDM_FORMAT_ISO_8859_2, IDM_FORMAT_ISO_8859_7, IDM_FORMAT_DOS_737, IDM_FORMAT_DOS_869, IDM_FORMAT_WIN_1253, IDM_FORMAT_ISO_8859_8, IDM_FORMAT_DOS_862, IDM_FORMAT_WIN_1255, IDM_FORMAT_SHIFT_JIS, IDM_FORMAT_KOREAN_WIN, IDM_FORMAT_EUC_KR, IDM_FORMAT_DOS_861, IDM_FORMAT_DOS_865, IDM_FORMAT_TIS_620, IDM_FORMAT_ISO_8859_3, IDM_FORMAT_ISO_8859_9, IDM_FORMAT_DOS_857, IDM_FORMAT_WIN_1254, IDM_FORMAT_WIN_1258, IDM_FORMAT_ISO_8859_1, IDM_FORMAT_ISO_8859_15, IDM_FORMAT_DOS_850, IDM_FORMAT_DOS_858, IDM_FORMAT_DOS_860, IDM_FORMAT_DOS_863, IDM_FORMAT_DOS_437, IDM_FORMAT_WIN_1252
- Channel: mcp, files
- Steps: For each of the 46 commands, parametrized with its Python codec (iso8859_6, cp720, cp1256, iso8859_4, iso8859_13, cp775, cp1257, iso8859_14, iso8859_5, koi8_r, koi8_u, mac_cyrillic, cp855, cp866, cp1251, cp852, cp1250, cp950, cp936, iso8859_2, iso8859_7, cp737, cp869, cp1253, iso8859_8, cp862, cp1255, cp932, cp949, euc_kr, cp861, cp865, cp874, iso8859_3, iso8859_9, cp857, cp1254, cp1258, latin_1, iso8859_15, cp850, cp858, cp860, cp863, cp437, cp1252) and a sample in that script (Arabic "مرحبا بالعالم", Baltic "Labas rytas, ąčęėįšųūž", Celtic "Dia dhuit ŵŷẁ", Cyrillic "Привет мир, ёжик", Czech "Příliš žluťoučký kůň", "繁體中文", "简体中文", Greek "Καλημέρα κόσμε", Hebrew "שלום עולם", "日本語テキスト", "한국어 텍스트", Icelandic "Þetta er íslenska ðæö", Nordic "Blåbærsyltetøy Æ", Thai "สวัสดีครับ", Turkish "Günaydın İstanbul şğ", Vietnamese with combining marks, Western "Café € œ"): write sample+"\n" encoded with the codec, open it, run the command, save.
- Expect: `app.text()` equals the sample + "\n"; `doc()["encoding"]` is "cp<codepage>" (e.g. cp1251, cp28596, cp51949); `doc()["modified"]` is true before the save; after IDM_FILE_SAVE the file's bytes are identical to the ones written.

### ENCODING-010: Every character set is reachable in its script submenu under its Notepad++ label
- Covers: IDM_FORMAT_ISO_8859_6, IDM_FORMAT_WIN_1251, IDM_FORMAT_SHIFT_JIS, IDM_FORMAT_DOS_437, IDM_FORMAT_WIN_1258
- Channel: menu
- Steps: Read `app.menu_tree("Encoding", depth=3)`; for each row of plan/commands.tsv with menu "Encoding" and a "Character sets › Group › Label" label, find the item.
- Expect: "Character sets" holds exactly the 16 groups of commands.tsv (Arabic, Baltic, Celtic, Cyrillic, Central European, Chinese, Eastern European, Greek, Hebrew, Japanese, Korean, North European, Thai, Turkish, Western European, Vietnamese); every one of the 46 labels is present in its group and enabled; `app.run("Encoding|Character sets|Cyrillic|KOI8-R")` runs IDM_FORMAT_KOI8R_CYRILLIC. (The group order is not asserted: the port sorts Vietnamese before Western European.)

### ENCODING-011: Encode in is a reading, not a conversion: switching sets back and forth is lossless
- Covers: IDM_FORMAT_KOI8R_CYRILLIC, IDM_FORMAT_WIN_1251, IDM_FORMAT_DOS_866
- Channel: mcp, files
- Steps: Open a Windows-1251 file "Привет мир\n"; run IDM_FORMAT_KOI8R_CYRILLIC, then IDM_FORMAT_DOS_866, then IDM_FORMAT_WIN_1251; save.
- Expect: under KOI8-R the text is "оПХБЕР ЛХП\n" (the same bytes read as KOI8-R, bytes.decode("koi8_r")); after returning to Windows-1251 the text is "Привет мир\n" again; the file on disk is byte-identical to the original.

### ENCODING-012: The chosen character set is checked in the menu
- Covers: IDM_FORMAT_WIN_1251, IDM_FORMAT_KOI8R_CYRILLIC
- Channel: mcp, menu
- Steps: Open a Windows-1251 file, run IDM_FORMAT_WIN_1251, read the checked state of IDM_FORMAT_WIN_1251, IDM_FORMAT_KOI8R_CYRILLIC and the five Unicode/ANSI items; then run IDM_FORMAT_KOI8R_CYRILLIC and read again.
- Expect: only the chosen charset item is checked (upstream checkUnicodeMenuItems radio-checks the IDM_FORMAT_ENCODE range) and none of ANSI/UTF-8/UTF-8-BOM/UTF-16 is checked. (Probed: no charset item is ever checked and UTF-8 stays checked — expected xfail.)

### ENCODING-013: The status bar names the chosen character set
- Covers: IDM_FORMAT_WIN_1251, IDM_FORMAT_SHIFT_JIS
- Channel: mcp, ui
- Steps: Open a Windows-1251 file and run IDM_FORMAT_WIN_1251; read the status bar field (the NSTextField of the main window whose value contains "Ln:"); repeat with a Shift-JIS file and IDM_FORMAT_SHIFT_JIS.
- Expect: the encoding field (between the EOL name and INS/OVR) names the set, "Windows-1251" / "Shift-JIS", not "UTF-8". (Probed: the port shows "UTF-8" — expected xfail.)

### ENCODING-014: Text typed into a charset document is saved in that set; unrepresentable characters become "?"
- Covers: IDM_FORMAT_WIN_1251
- Channel: mcp, keys, files
- Steps: Open a Windows-1251 file "Пока мир\n", run IDM_FORMAT_WIN_1251, put the caret at 1:1 and type "Ж€☃", save.
- Expect: the file bytes are b"\xc6\x88?" followed by the original bytes (Ж=C6, €=88, ☃ has no byte in 1251).

### ENCODING-015: A code page that cannot read the bytes declines with an alert
- Covers: IDM_FORMAT_SHIFT_JIS, IDM_FORMAT_BIG5
- Channel: mcp, modal
- Steps: Open a file with bytes b"abc \x81\x20 \xff\xfd\n" (opens as ANSI); run IDM_FORMAT_SHIFT_JIS, then IDM_FORMAT_BIG5, each with a queued alert answer 1.
- Expect: the modal log shows "Cannot read this document as Shift-JIS." and "Cannot read this document as Big5 (Traditional)."; the text is unchanged ("abc \x81 ÿý\n") and `doc()["encoding"]` is still ISO-8859-1.

### ENCODING-016: Code page 720 and 858 follow Windows, not the macOS converters
- Covers: IDM_FORMAT_DOS_720, IDM_FORMAT_DOS_858, IDM_FORMAT_DOS_850, IDM_FORMAT_DOS_861
- Channel: mcp, files
- Steps: Write bytes(range(0x80, 0x100)) + b"\n" to a file; open it and for each of DOS_720, DOS_858, DOS_850, DOS_861 run the command and read the text.
- Expect: the text equals bytes(range(0x80,0x100)).decode(codec) + "\n" for cp720/cp858/cp850/cp861 respectively (bytes Python's codec leaves undefined may read U+FFFD); under cp858 byte 0xD5 is "€" and under cp850 it is "ı"; saving without edits writes all 128 bytes back unchanged.

### ENCODING-017: Undo after Encode in does not leave the text read in one set and written in another
- Covers: IDM_FORMAT_DOS_720
- Channel: mcp, keys, files
- Steps: Open the bytes EA A9 A5 A0 9F 0A (cp720 "مرحبا"), run IDM_FORMAT_DOS_720, press cmd+z, then save.
- Expect: either the undo is not offered for the reinterpretation (text stays "مرحبا\n") or undoing also restores the previous reading; in both cases the file on disk after save is still EA A9 A5 A0 9F 0A. (Probed: undo brings back "ê©¥…" while the code page stays 720, so the save would write different bytes — expected xfail.)

### ENCODING-018: Reload keeps the chosen character set
- Covers: IDM_FORMAT_WIN_1251
- Channel: mcp, files
- Steps: Open a Windows-1251 file, run IDM_FORMAT_WIN_1251, save; rewrite the file externally with "Пока мир\n".encode("cp1251") and run IDM_FILE_RELOAD (answer any alert with button 1).
- Expect: the text is "Пока мир\n"; `doc()["encoding"]` stays cp1251; `doc()["modified"]` is false.

### ENCODING-019: Save As keeps the character set
- Covers: IDM_FORMAT_KOI8U_CYRILLIC
- Channel: mcp, modal, files
- Steps: Open a KOI8-U file "Привіт, світе\n", run IDM_FORMAT_KOI8U_CYRILLIC, queue the save panel answer tmp/copy.txt and run IDM_FILE_SAVEAS.
- Expect: tmp/copy.txt bytes equal "Привіт, світе\n".encode("koi8_u"); the tab is now copy.txt with encoding cp21866.

### ENCODING-020: The character set of a file is remembered in the session
- Covers: IDM_FORMAT_DOS_855
- Channel: mcp, launch, files
- Steps: Start with `session=True, defaults={"restoreSession": True}`; open a cp855 file "Привет мир\n" (it detects as something else), run IDM_FORMAT_DOS_855, save; quit through NSApp (`invoke("nsapp","terminate:")`) and start again with `session=True, clean_home=False, reset=False`.
- Expect: session.xml in the home has the file with `encoding="855"`; after the restart the file is open, reads "Привет мир\n", `doc()["encoding"]` is cp855 and it is not modified.

## Convert to

### ENCODING-021: Each Convert to item writes the same text in the new byte form
- Covers: IDM_FORMAT_CONV2_ANSI, IDM_FORMAT_CONV2_AS_UTF_8, IDM_FORMAT_CONV2_UTF_8, IDM_FORMAT_CONV2_UTF_16BE, IDM_FORMAT_CONV2_UTF_16LE
- Channel: mcp, files
- Steps: For each of the five: open a UTF-8 file "snow é\n", run the command, save, close, reopen.
- Expect: bytes on disk: ANSI b"snow \xe9\n", UTF-8 b"snow \xc3\xa9\n", UTF-8-BOM EF BB BF + UTF-8, UTF-16 BE FE FF + utf-16-be, UTF-16 LE FF FE + utf-16-le; the reopened text is "snow é\n" in every case; the text shown did not change at the moment of conversion.

### ENCODING-022: Convert to marks the document modified and updates the status bar and checkmark
- Covers: IDM_FORMAT_CONV2_UTF_16BE, IDM_FORMAT_CONV2_UTF_8
- Channel: mcp, ui, menu
- Steps: Open an unmodified UTF-8 file; run IDM_FORMAT_CONV2_UTF_16BE; read `doc()`, the status bar and the checked state of IDM_FORMAT_UTF_16BE; then IDM_FORMAT_CONV2_UTF_8 and read again.
- Expect: modified is true; the status bar encoding field reads "UTF-16 BE BOM" then "UTF-8-BOM"; the matching interpret item (IDM_FORMAT_UTF_16BE, then IDM_FORMAT_UTF_8) is the checked one.

### ENCODING-023: Converting to ANSI replaces characters ANSI cannot hold
- Covers: IDM_FORMAT_CONV2_ANSI
- Channel: mcp, files
- Steps: Open a UTF-8 file "snow ☃ é\n", run IDM_FORMAT_CONV2_ANSI, save.
- Expect: the file is b"snow ? \xe9\n"; the status bar reads "ANSI"; reopening shows "snow ? é\n".

### ENCODING-024: Convert to from a character set really changes the bytes
- Covers: IDM_FORMAT_CONV2_AS_UTF_8, IDM_FORMAT_CONV2_UTF_16LE, IDM_FORMAT_KOI8R_CYRILLIC
- Channel: mcp, files
- Steps: Open a KOI8-R file "Привет мир\n", run IDM_FORMAT_KOI8R_CYRILLIC, then IDM_FORMAT_CONV2_AS_UTF_8, save; repeat with IDM_FORMAT_CONV2_UTF_16LE.
- Expect: the file becomes "Привет мир\n".encode("utf-8") (resp. FF FE + utf-16-le); `doc()["encoding"]` is UTF-8 (resp. UTF-16LE), no longer cp20866. (Probed: the code page is kept and the file is written in KOI8-R again — expected xfail.)

### ENCODING-025: A conversion survives undo and redo of text edits
- Covers: IDM_FORMAT_CONV2_UTF_8
- Channel: mcp, keys, files
- Steps: Open a UTF-8 file "abc\n", type "X" at 1:1, run IDM_FORMAT_CONV2_UTF_8, press cmd+z until the text is "abc\n", save.
- Expect: the document is still modified after the undo (encoding differs from disk); the saved file is EF BB BF 61 62 63 0A.

### ENCODING-026: Converting a UTF-16 file back to UTF-8 drops the BOM
- Covers: IDM_FORMAT_CONV2_AS_UTF_8
- Channel: mcp, files
- Steps: Open a UTF-16 LE BOM file "hi Ω\n", run IDM_FORMAT_CONV2_AS_UTF_8, save.
- Expect: the file is exactly b"hi \xce\xa9\n" (no BOM, no NUL bytes); `app.call("file_encoding", path=...)` reports bom "none", encoding "UTF-8".

## Detection on open

### ENCODING-027: A BOM decides the encoding and is not part of the text
- Covers: IDM_FORMAT_UTF_8, IDM_FORMAT_UTF_16LE, IDM_FORMAT_UTF_16BE
- Channel: mcp, ui, menu
- Steps: For each of UTF-8-BOM, UTF-16 LE BOM, UTF-16 BE BOM: write BOM + "hi Ω\n" in that form and open it.
- Expect: text is "hi Ω\n" (no U+FEFF at position 0: `SCI_GETCHARAT 0` is "h"); `doc()["encoding"]` UTF-8-BOM / UTF-16LE / UTF-16BE; status bar "UTF-8-BOM" / "UTF-16 LE BOM" / "UTF-16 BE BOM"; the matching menu item is checked; not modified; saving unchanged writes identical bytes.

### ENCODING-028: UTF-16 without a BOM is recognised and saved without one
- Covers: IDM_FORMAT_UTF_16LE, IDM_FORMAT_UTF_16BE
- Channel: mcp, ui, files
- Steps: For LE and BE: write "hello world, plain\n" in UTF-16 without BOM, open it, append "!" before the newline, save.
- Expect: the text reads correctly on open; `doc()["encoding"]` is UTF-16LE / UTF-16BE; the saved file has no BOM and is the new text in the same byte order; the status bar does not claim a BOM (upstream shows "UTF-16 Little Endian" / "UTF-16 Big Endian"). (Probed: the status bar says "UTF-16 LE BOM" — the label part expected xfail.)

### ENCODING-029: Valid UTF-8 without a BOM opens as UTF-8
- Covers: IDM_FORMAT_AS_UTF_8
- Channel: mcp, ui
- Steps: Open a file b"na\xc3\xafve \xe2\x98\x83\n".
- Expect: text "naïve ☃\n"; encoding UTF-8; status bar "UTF-8"; IDM_FORMAT_AS_UTF_8 checked; not modified.

### ENCODING-030: Seven-bit files follow "Apply to opened ANSI files"
- Covers: IDM_FORMAT_AS_UTF_8, IDM_FORMAT_ANSI
- Channel: mcp, prefs, ui
- Steps: With defaults (defaultEncoding "UTF-8", openAnsiAsUtf8 true) open an ASCII file "plain\n"; then `set_prefs(openAnsiAsUtf8=False)` and open another ASCII file; restore the preference.
- Expect: the first opens as UTF-8 (status "UTF-8"), the second as ANSI (status "ANSI", encoding ISO-8859-1); an empty file follows the same rule.

### ENCODING-031: uchardet detects legacy character sets on open
- Covers: -
- Channel: mcp, files
- Steps: For each of: Shift-JIS "日本語のテキストです。これは文字コードの検出テストです。", GB2312 (simplified Chinese sentence), Big5 (traditional sentence), EUC-KR "한국어 텍스트 파일입니다. 인코딩 감지 테스트.", KOI8-R and CP866 Russian sentences, Windows-1255 Hebrew sentence, Windows-1253/ISO-8859-7 Greek sentence (all 40+ characters): write the file and open it.
- Expect: `app.text()` equals the original sentence exactly and the document is unmodified; `doc()["encoding"]` names a set that reads it (SHIFT_JIS, GB18030/GB2312, BIG5, EUC-KR, KOI8-R, CP866, WINDOWS-1255, ISO-8859-7/WINDOWS-1253); `file_encoding` on the path reports the same encoding and a matching `charset_detected`.

### ENCODING-032: Windows-1251 Russian text is detected as Windows-1251
- Covers: -
- Channel: mcp
- Steps: Open a file with "Привет, мир! Это проверка кодировки текста.\n".encode("cp1251").
- Expect: the text reads back exactly (capital П and Э included); `doc()["encoding"]` is WINDOWS-1251. (Probed: detected as X-MAC-CYRILLIC, reading "ѕривет … Ёто" — the letter-share arbitration ties; expected xfail.)

### ENCODING-033: Detection can be turned off
- Covers: -
- Channel: mcp, prefs
- Steps: `set_prefs(autoDetectCharacterEncoding=False)`, open the Shift-JIS file of ENCODING-031, restore the preference.
- Expect: the document opens as ANSI (encoding ISO-8859-1, status "ANSI") with each byte its Latin-1 character; running IDM_FORMAT_SHIFT_JIS then reads the Japanese sentence correctly.

### ENCODING-034: Detected legacy sets are shown and saved as that set
- Covers: -
- Channel: mcp, ui, files
- Steps: Open the Shift-JIS file of ENCODING-031, type "X" at 1:1, save.
- Expect: the file is b"X" + the original Shift-JIS bytes; the status bar encoding field shows the detected set ("Shift-JIS"), not "UTF-8". (Probed: bytes right, status bar says "UTF-8" — the label part expected xfail.)

### ENCODING-035: A large non-UTF-8 file is detected and converted piecewise
- Covers: -
- Channel: mcp, files
- Steps: Write a 65 MB file made of a repeated Windows-1251/KOI8-R Russian paragraph (above the 64 MB streaming threshold) and open it (timeout 60 s).
- Expect: the first and last lines read as Cyrillic (via `app.text()` with SCI_GETLINE through `e2e_sci`, not the whole text); `doc()["encoding"]` is the Cyrillic set; the line count equals the number written.

## Invalid and odd bytes

### ENCODING-036: A file that is not valid UTF-8 and not recognised opens as ANSI byte for byte
- Covers: IDM_FORMAT_ANSI
- Channel: mcp, ui, files
- Steps: Open a file b"ok \xff\xfe\x80 bad\n"; save it unchanged with IDM_FILE_SAVE after typing and deleting one character.
- Expect: the text has one character per byte ("ok ÿþ" + the 0x80 byte's ANSI character + " bad\n"); status bar "ANSI"; IDM_FORMAT_ANSI checked; the saved file is byte-identical to the original.

### ENCODING-037: Invalid UTF-8 sequences in the middle of UTF-8 text are not lost
- Covers: -
- Channel: mcp, files
- Steps: Open b"valid \xc3\xa9 then \xc3\x28 and \xe2\x82\n" (a valid sequence, then a bad continuation and a truncated one); type "x" at the end of the line and delete it again with backspace; save.
- Expect: opening does not fail; the whole file is read as ANSI (encoding ISO-8859-1, status "ANSI", text "valid Ã© then Ã( and â\x82\n"); IDM_FORMAT_AS_UTF_8 is not checked; the saved bytes are identical to the original; `file_encoding` reports binary false.

### ENCODING-038: NUL bytes do not cut the document
- Covers: -
- Channel: mcp, files
- Steps: Open b"a\x00b\x00c\nsecond\n" (not UTF-16 by the zero pattern), then save.
- Expect: `doc()["bytes"]` is 13 and `app.text()` is "a\x00b\x00c\nsecond\n" (the NULs are kept, the second line is present); after an edit-and-revert save the bytes are identical; `file_encoding` on it reports binary true.

### ENCODING-039: Mixed scripts that ANSI cannot hold survive an interpret-as change to UTF-16
- Covers: IDM_FORMAT_UTF_16LE, IDM_FORMAT_AS_UTF_8
- Channel: mcp, files
- Steps: Open UTF-8 "Ω 日本 😀\n", run IDM_FORMAT_UTF_16LE, save, then IDM_FORMAT_AS_UTF_8, save.
- Expect: after the first save the file is FF FE + utf-16-le of the text (😀 as D83D DE00); after the second it is the original UTF-8 bytes; the text never changes.

## Status bar and new documents

### ENCODING-040: The status bar shows the encoding of the active tab
- Covers: IDM_FORMAT_ANSI, IDM_FORMAT_UTF_8
- Channel: mcp, ui
- Steps: Open a UTF-8-BOM file, an ANSI (Latin-1 "café") file and a UTF-16 BE BOM file in three tabs; activate each with `go_to`/document index and read the status bar.
- Expect: the encoding field reads "UTF-8-BOM", "ANSI", "UTF-16 BE BOM" for the respective tab, and the checked Encoding item changes with it.

### ENCODING-041: New documents take the New Document encoding preference
- Covers: IDM_FORMAT_UTF_8, IDM_FORMAT_UTF_16LE, IDM_FORMAT_ANSI
- Channel: mcp, prefs, ui, files
- Steps: For each defaultEncoding of "UTF-8-BOM", "UTF-16 LE BOM", "ANSI": `set_prefs(defaultEncoding=...)`, run IDM_FILE_NEW, type "é\n", save through a queued save panel; finally restore "UTF-8".
- Expect: the status bar shows the preference's name and its item is checked; the saved bytes are EF BB BF C3 A9 0A / FF FE E9 00 0A 00 / E9 0A.

## Line endings on disk

### ENCODING-042: The first line ending decides a file's EOL format, shown in the status bar
- Covers: -
- Channel: mcp, ui
- Steps: Open files b"a\r\nb\r\n", b"a\nb\n", b"a\rb\r", b"a\nb\r\nc\r\n" and b"no newline".
- Expect: `doc()["eol"]` and the status bar EOL field: CRLF "Windows (CR LF)", LF "Unix (LF)", CR "Macintosh (CR)", mixed file "Unix (LF)" (the first ending), no ending "Unix (LF)"; the texts are unchanged (mixed endings are not normalised on open).

### ENCODING-043: Enter inserts the document's own line ending and saving keeps it
- Covers: -
- Channel: mcp, keys, files
- Steps: For CRLF, LF and CR files ("a<eol>b<eol>"): put the caret at the end of line 1, press return, type "z", save.
- Expect: the saved bytes are "a<eol>z<eol>b<eol>" with the file's own ending each time; nothing else changes.

### ENCODING-044: New documents take the default EOL preference
- Covers: -
- Channel: mcp, prefs, ui, files
- Steps: `set_prefs(defaultEOL=0)` (Windows), run IDM_FILE_NEW, press return twice, save via a queued panel; repeat with defaultEOL 2 (Unix) and 1 (Mac); restore 2.
- Expect: status bar "Windows (CR LF)" / "Unix (LF)" / "Macintosh (CR)"; the saved file contains "\r\n\r\n" / "\n\n" / "\r\r".

### ENCODING-045: Line endings survive a change of encoding
- Covers: IDM_FORMAT_CONV2_UTF_16LE, IDM_FORMAT_CONV2_ANSI
- Channel: mcp, files
- Steps: Open b"a\r\nb\r\n" (UTF-8), run IDM_FORMAT_CONV2_UTF_16LE, save; then IDM_FORMAT_CONV2_ANSI, save.
- Expect: the UTF-16 file is FF FE 61 00 0D 00 0A 00 62 00 0D 00 0A 00; the ANSI file is b"a\r\nb\r\n"; the status bar keeps "Windows (CR LF)".

### ENCODING-046: A UTF-16 file with CR LF endings is read with the right EOL
- Covers: -
- Channel: mcp, ui
- Steps: Open FF FE + "x\r\ny\r\n".encode("utf-16-le") and FE FF + the same in utf-16-be.
- Expect: two lines x and y; `doc()["eol"]` CRLF; status bar "Windows (CR LF)"; `file_encoding` reports eol "CRLF", mixed_eol false.

## The agent's view

### ENCODING-047: file_encoding reports the BOM, detected set, EOL and a preview without opening the file
- Covers: -
- Channel: mcp
- Steps: Call `file_encoding` on: a UTF-8-BOM CRLF file, a UTF-16 BE file without BOM, a KOI8-R file, a mixed-EOL file, and a PNG-like binary file with NULs.
- Expect: bom "UTF-8"/"none"/"none"; utf16_without_bom "UTF-16 BE" for the second; encoding "KOI8-R" and a Cyrillic preview for the third; eol "CRLF" and mixed_eol true for the mixed file; binary true (encoding null) for the binary file; `list_documents` count unchanged (nothing was opened).

### ENCODING-048: get_document reports the encoding as the menu does
- Covers: IDM_FORMAT_UTF_8, IDM_FORMAT_WIN_1250
- Channel: mcp
- Steps: `app.new("x")`, run IDM_FORMAT_UTF_8 and read `doc()["encoding"]`; open a Windows-1250 file, run IDM_FORMAT_WIN_1250 and read it again.
- Expect: "UTF-8-BOM", then "cp1250"; `list_documents` entries agree.
