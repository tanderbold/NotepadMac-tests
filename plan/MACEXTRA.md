# MACEXTRA — What only the Mac port has: OCR, QR codes, the command-line tool

The menu commands that lean on macOS rather than on Notepad++: Edit > Paste Image as Text and Edit > Recognize Text in File… (Vision's text recognizer), Tools > QR Code from Selection and Tools > Read QR Code from Clipboard (Core Image and Vision), and Tools > Install Command Line Tool. Images and PDFs are made by the test with Pillow (black text on white, 60 px type or larger) or by the app itself (QR "Copy Image" / "Save…"); the MCP `ocr` and `read_qr` tools (planned in AGENT) are used here only as independent readers of files the app wrote. The clipboard is the harness's private pasteboard. Install Command Line Tool writes to `/usr/local/bin` with no confirmation and cannot be cancelled, so its success path is never run for real. The app registers no macOS Services (no NSServices in Info.plist), so there is nothing to plan for them. The `nppmac` tool itself is planned in CLI.

## The menus

### MACEXTRA-001: The Mac-only items sit where the port puts them
- Covers: -
- Channel: menu
- Steps: Dump the Edit and Tools menus; read the enabled state of each item with an empty document and with a selection.
- Expect: Edit holds "Paste Image as Text" and "Recognize Text in File…"; Tools holds, after a separator, "QR Code from Selection" and "Read QR Code from Clipboard", then after another separator "Install Command Line Tool"; all five are enabled in both states (they report problems when run rather than greying out).

## QR codes

### MACEXTRA-002: QR Code from Selection shows the code of the selected text
- Covers: -
- Channel: mcp, ui
- Steps: Document "see https://example.com/π?a=1&b=2 end"; select the address; run `Tools|QR Code from Selection`; read the window's controls.
- Expect: a non-modal window titled "QR Code" with an image view holding an image (at least 260 × 260), the caption equal to the selected text, and the buttons "Copy Image", "Save…" and "Close"; the document and selection are unchanged.

### MACEXTRA-003: Save… writes a PNG that decodes to the text
- Covers: -
- Channel: ui, modal, files
- Steps: From MACEXTRA-002's window queue `tmp/qr.png` and click "Save…"; read the file with the `read_qr` tool; then queue a cancel (None) and click Save… again.
- Expect: the save panel proposes "qr-code.png"; the file is a PNG; `read_qr` returns exactly the selected text (Unicode "π" included); the cancelled save writes nothing and shows no alert.

### MACEXTRA-004: Copy Image, then Read QR Code from Clipboard, gives the text back at the caret
- Covers: -
- Channel: ui, clipboard, mcp
- Steps: Select "Grüße, 世界 ✓\nsecond line" in a document and run QR Code from Selection; click "Copy Image"; read the clipboard types; in a new document "[x]" select "x" and run `Tools|Read QR Code from Clipboard`; undo once.
- Expect: the clipboard carries an image type (public.tiff) and no plain text; the new document reads "[Grüße, 世界 ✓\nsecond line]"; one undo restores "[x]".

### MACEXTRA-005: With nothing selected no code is made
- Covers: -
- Channel: mcp, ui, modal
- Steps: Document "abc" with the caret and no selection; close any QR window; run QR Code from Selection.
- Expect: no QR window appears, no alert is logged (the app beeps), the document is unchanged.

### MACEXTRA-006: A selection too long for a QR code is refused in words
- Covers: -
- Channel: mcp, modal, ui
- Steps: Document of 4000 "x", select all; run QR Code from Selection.
- Expect: the alert "The selection is too long for a QR code."; no QR window opens.

### MACEXTRA-007: A long payload is encoded whole but its caption is cut at 200 characters
- Covers: -
- Channel: ui, modal, files
- Steps: Select a 500-character line of words; run QR Code from Selection; read the caption; save the image and decode it with `read_qr`.
- Expect: the caption is the first 200 characters followed by "…"; the decoded text is all 500 characters.

### MACEXTRA-008: Read QR Code from Clipboard with no image is refused and changes nothing
- Covers: -
- Channel: clipboard, mcp, modal
- Steps: Set the clipboard to the text "plain"; document "keep"; run Read QR Code from Clipboard; then clear the clipboard and run it again.
- Expect: both times the alert "No QR code was found in the clipboard's image." and the document still reads "keep".

### MACEXTRA-009: An image with no QR code, and an image with two, on the clipboard
- Covers: -
- Channel: clipboard, mcp, modal
- Steps: (needs a hook to put an image file on the private clipboard) Put a white PNG with the word "hello" on the clipboard and run Read QR Code from Clipboard; then a PNG with two QR codes (made with Pillow from two QR images the app saved, one above the other, payloads "top" and "bottom").
- Expect: the first gives the alert "No QR code was found in the clipboard's image." and no text; the second inserts "top\nbottom" (top to bottom).

## Text recognition

### MACEXTRA-010: Paste Image as Text puts the image's words at the caret
- Covers: -
- Channel: clipboard, mcp
- Steps: (needs the image-on-clipboard hook) Make a PNG "Hello OCR World 2026" with Pillow; put it on the clipboard; document "[x]" with "x" selected; run `Edit|Paste Image as Text`; undo once.
- Expect: the document reads "[Hello OCR World 2026]"; one undo restores "[x]"; no alert.

### MACEXTRA-011: A file copied in Finder is read too
- Covers: -
- Channel: clipboard, mcp
- Steps: (needs a hook to put a file URL, type public.file-url, on the clipboard) Put the URL of the PNG of MACEXTRA-010 on the clipboard; run Paste Image as Text in an empty document.
- Expect: the document reads "Hello OCR World 2026".

### MACEXTRA-012: Paste Image as Text without an image says so
- Covers: -
- Channel: clipboard, mcp, modal
- Steps: Set the clipboard to the text "not an image"; document "keep"; run Paste Image as Text; then (image hook) a plain white PNG.
- Expect: the alert "No text was found in the clipboard's image." each time; the document still reads "keep".

### MACEXTRA-013: Recognize Text in File… opens a PNG's words in a new document
- Covers: -
- Channel: modal, mcp, files
- Steps: Make `ocr.png` with Pillow: three lines "First line 1", "Second line 2", "Third line 3" one below the other; document "keep" in front; queue the PNG's path and run `Edit|Recognize Text in File…`; wait for a new tab.
- Expect: an open panel was shown and answered with the path; a new untitled tab holds "First line 1\nSecond line 2\nThird line 3" (reading order top to bottom); the "keep" document is unchanged.

### MACEXTRA-014: A PDF is read page by page
- Covers: -
- Channel: modal, mcp, files
- Steps: Make a two-page PDF with Pillow (`save_all`) whose pages read "PAGE ONE 11" and "PAGE TWO 22"; queue it and run Recognize Text in File….
- Expect: a new tab containing "PAGE ONE 11", a blank line, then "PAGE TWO 22" (pages joined by "\n\n", in order).

### MACEXTRA-015: Recognize Text in File… with nothing to read, or cancelled
- Covers: -
- Channel: modal, mcp, files
- Steps: Make a plain white PNG; queue it and run Recognize Text in File…; wait up to 10 s; then queue a cancel (None) and run it again.
- Expect: the first run shows the alert "No text was found in the file." and opens no tab; the cancelled run opens no tab and shows no alert; the number of documents is unchanged throughout.

### MACEXTRA-016: Recognition does not hold up the editor
- Covers: -
- Channel: modal, mcp, files
- Steps: Make a 10-page PDF with a line of text on each page; queue it and run Recognize Text in File…; immediately call `get_document` and `edit_document` on the document in front; wait for the new tab.
- Expect: the two calls answer at once (well before the recognition finishes) and the edit lands; the new tab eventually holds ten pages of text in order.

## The command-line tool

### MACEXTRA-017: Install Command Line Tool where /usr/local/bin is not writable explains what to run
- Covers: -
- Channel: mcp, modal, files
- Steps: Skip the case unless `/usr/local/bin` exists and is not writable by the test user and `/usr/local/bin/nppmac` does not exist (then the command can change nothing); run `Tools|Install Command Line Tool`; read the modal log.
- Expect: the alert "Could not write to /usr/local/bin." whose informative text reads "Run this in Terminal:\n\nsudo ln -sf \"<bundle>/Contents/Helpers/nppmac\" /usr/local/bin/nppmac" with the running copy's bundle path; the helper named there exists and is executable; `/usr/local/bin/nppmac` still does not exist.

### MACEXTRA-018: Install Command Line Tool's success path links the helper (hook needed)
- Covers: -
- Channel: mcp, modal, files
- Steps: (needs a hook that points the link directory at a scratch folder, e.g. an E2E override of "/usr/local/bin") Create `tmp/bin` with an existing file `nppmac` in it; run Install Command Line Tool.
- Expect: `tmp/bin/nppmac` is a symbolic link to the bundle's `Contents/Helpers/nppmac`; the alert "The nppmac command is installed." lists "nppmac file.txt", "nppmac +42 file.txt" and "something | nppmac -"; the file that was there before is gone (replaced, as the command does without asking).
