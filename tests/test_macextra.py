"""MACEXTRA: end-to-end tests (plan: plan/MACEXTRA.md)."""
import pytest

from harness.app import App
from harness.sci import *  # noqa: F401,F403

import _util_macextra as U


@pytest.mark.case("MACEXTRA-001")
def test_macextra_001_the_mac_only_items_sit_where_the_port_puts_them(app):
    """MACEXTRA-001: The Mac-only items sit where the port puts them

    Covers: -
    Channel: menu
    Steps: Dump the Edit and Tools menus; read the enabled state of each item with an empty document and with a selection.
    Expect: Edit holds "Paste Image as Text" and "Recognize Text in File…"; Tools holds, after a separator, "QR Code from Selection" and "Read QR Code from Clipboard", then after another separator "Install Command Line Tool"; all five are enabled in both states (they report problems when run rather than greying out).
    """
    app.new("")
    tree = app.menu_tree("main", 2)
    by_first = {}
    for top in tree:
        titles = [i.get("title") for i in top.get("items", [])]
        by_first[tuple(titles[:1])] = titles
    edit = next(t for t in (top for top in tree) if any(i.get("title") == "Undo" for i in t.get("items", [])))
    edit_titles = [i.get("title") for i in edit["items"]]
    assert "Paste Image as Text" in edit_titles
    assert "Recognize Text in File…" in edit_titles
    tools = next(t for t in tree if [i.get("title") for i in t.get("items", [])][:2] == ["Hashes", "Base"])
    tools_titles = [i.get("title") for i in tools["items"]]
    assert tools_titles[4:] == [None, "QR Code from Selection", "Read QR Code from Clipboard", None,
                                "Install Command Line Tool"]
    paths = ["Edit|Paste Image as Text", "Edit|Recognize Text in File…", "Tools|QR Code from Selection",
             "Tools|Read QR Code from Clipboard", "Tools|Install Command Line Tool"]
    for state in ("empty", "selection"):
        if state == "selection":
            app.set_text("some text")
            app.select(1, 1, 1, 5)
        items = app.menu(*paths)
        for p in paths:
            assert items[p] is not None, p
            assert items[p]["enabled"], (state, p)


@pytest.mark.case("MACEXTRA-002")
def test_macextra_002_qr_code_from_selection_shows_the_code_of_the_selected_text(app):
    """MACEXTRA-002: QR Code from Selection shows the code of the selected text

    Covers: -
    Channel: mcp, ui
    Steps: Document "see https://example.com/π?a=1&b=2 end"; select the address; run `Tools|QR Code from Selection`; read the window's controls.
    Expect: a non-modal window titled "QR Code" with an image view holding an image (at least 260 × 260), the caption equal to the selected text, and the buttons "Copy Image", "Save…" and "Close"; the document and selection are unchanged.
    """
    addr = "https://example.com/π?a=1&b=2"
    app.new(f"see {addr} end")
    app.select(1, 5, 1, 5 + len(addr))
    before = app.selection()
    assert before["text"] == addr
    app.run("Tools|QR Code from Selection")
    w = app.wait(lambda: U.qr_window(app), 5)
    assert not w["modal"] and not w.get("sheet")
    img = U.image_control(app, w)
    assert img is not None and img.get("has_image")
    assert img["frame"][2] >= 260 and img["frame"][3] >= 260
    assert U.caption(app, w) == addr
    titles = {c.get("title") for c in app.ui(w["number"])["controls"]}
    assert {"Copy Image", "Save…", "Close"} <= titles
    assert app.text() == f"see {addr} end"
    after = app.selection()
    assert after["text"] == addr and after["start"] == before["start"] and after["end"] == before["end"]


@pytest.mark.case("MACEXTRA-003")
def test_macextra_003_save_writes_a_png_that_decodes_to_the_text(app, tmp):
    """MACEXTRA-003: Save… writes a PNG that decodes to the text

    Covers: -
    Channel: ui, modal, files
    Steps: From MACEXTRA-002's window queue `tmp/qr.png` and click "Save…"; read the file with the `read_qr` tool; then queue a cancel (None) and click Save… again.
    Expect: the save panel proposes "qr-code.png"; the file is a PNG; `read_qr` returns exactly the selected text (Unicode "π" included); the cancelled save writes nothing and shows no alert.
    """
    addr = "https://example.com/π?a=1&b=2"
    app.new(addr)
    app.sci(SCI_SELECTALL)
    app.run("Tools|QR Code from Selection")
    w = app.wait(lambda: U.qr_window(app), 5)
    out = tmp / "qr.png"
    app.answers(panels=[str(out)])
    app.click(w["number"], "Save…")
    app.wait(lambda: out.exists() and out.stat().st_size > 0, 5)
    log = app.modal_log()
    saves = [e for e in log if e["kind"] == "save"]
    assert saves and saves[0]["name"] == "qr-code.png"
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert app.call("read_qr", path=str(out))["text"] == addr
    before = sorted(p.name for p in tmp.iterdir())
    app.answers(panels=[None])
    app.click(w["number"], "Save…")
    app.idle(0.3)
    log = app.modal_log()
    assert not U.alerts(log)
    assert sorted(p.name for p in tmp.iterdir()) == before


@pytest.mark.case("MACEXTRA-004")
def test_macextra_004_copy_image_then_read_qr_code_from_clipboard_gives_the_text_b(app):
    """MACEXTRA-004: Copy Image, then Read QR Code from Clipboard, gives the text back at the caret

    Covers: -
    Channel: ui, clipboard, mcp
    Steps: Select "Grüße, 世界 ✓\\nsecond line" in a document and run QR Code from Selection; click "Copy Image"; read the clipboard types; in a new document "[x]" select "x" and run `Tools|Read QR Code from Clipboard`; undo once.
    Expect: the clipboard carries an image type (public.tiff) and no plain text; the new document reads "[Grüße, 世界 ✓\\nsecond line]"; one undo restores "[x]".
    """
    payload = "Grüße, 世界 ✓\nsecond line"
    app.new(payload)
    app.sci(SCI_SELECTALL)
    app.run("Tools|QR Code from Selection")
    w = app.wait(lambda: U.qr_window(app), 5)
    app.click(w["number"], "Copy Image")
    info = app.clipboard_info()
    assert "public.tiff" in info["types"]
    assert info["text"] is None
    U.close_qr(app)
    app.new("[x]")
    app.select(1, 2, 1, 3)
    app.run("Tools|Read QR Code from Clipboard")
    assert app.wait(lambda: app.text() == f"[{payload}]", 10)
    assert not U.alerts(app.modal_log())
    app.sci(SCI_UNDO)
    assert app.text() == "[x]"


@pytest.mark.case("MACEXTRA-005")
def test_macextra_005_with_nothing_selected_no_code_is_made(app):
    """MACEXTRA-005: With nothing selected no code is made

    Covers: -
    Channel: mcp, ui, modal
    Steps: Document "abc" with the caret and no selection; close any QR window; run QR Code from Selection.
    Expect: no QR window appears, no alert is logged (the app beeps), the document is unchanged.
    """
    U.close_qr(app)
    app.new("abc")
    app.select(1, 4)
    beeps = app.counters(reset=True)
    app.run("Tools|QR Code from Selection")
    app.idle(0.3)
    assert U.qr_window(app) is None
    assert not U.alerts(app.modal_log())
    assert app.text() == "abc"
    c = app.counters()
    assert c.get("beeps", 0) >= 1, c


@pytest.mark.case("MACEXTRA-006")
def test_macextra_006_a_selection_too_long_for_a_qr_code_is_refused_in_words(app):
    """MACEXTRA-006: A selection too long for a QR code is refused in words

    Covers: -
    Channel: mcp, modal, ui
    Steps: Document of 4000 "x", select all; run QR Code from Selection.
    Expect: the alert "The selection is too long for a QR code."; no QR window opens.
    """
    U.close_qr(app)
    app.new("x" * 4000)
    app.sci(SCI_SELECTALL)
    app.run("Tools|QR Code from Selection")
    app.idle(0.2)
    msgs = [e["message"] for e in U.alerts(app.modal_log())]
    assert msgs == ["The selection is too long for a QR code."]
    assert U.qr_window(app) is None


@pytest.mark.case("MACEXTRA-007")
def test_macextra_007_a_long_payload_is_encoded_whole_but_its_caption_is_cut_at_20(app, tmp):
    """MACEXTRA-007: A long payload is encoded whole but its caption is cut at 200 characters

    Covers: -
    Channel: ui, modal, files
    Steps: Select a 500-character line of words; run QR Code from Selection; read the caption; save the image and decode it with `read_qr`.
    Expect: the caption is the first 200 characters followed by "…"; the decoded text is all 500 characters.
    """
    words = "alpha beta gamma delta epsilon zeta eta theta iota kappa "
    text = (words * 20)[:500]
    assert len(text) == 500
    app.new(text)
    app.sci(SCI_SELECTALL)
    app.run("Tools|QR Code from Selection")
    w = app.wait(lambda: U.qr_window(app), 5)
    assert U.caption(app, w) == text[:200] + "…"
    out = tmp / "long.png"
    app.answers(panels=[str(out)])
    app.click(w["number"], "Save…")
    app.wait(lambda: out.exists() and out.stat().st_size > 0, 5)
    assert app.call("read_qr", path=str(out))["text"] == text


@pytest.mark.case("MACEXTRA-008")
def test_macextra_008_read_qr_code_from_clipboard_with_no_image_is_refused_and_cha(app):
    """MACEXTRA-008: Read QR Code from Clipboard with no image is refused and changes nothing

    Covers: -
    Channel: clipboard, mcp, modal
    Steps: Set the clipboard to the text "plain"; document "keep"; run Read QR Code from Clipboard; then clear the clipboard and run it again.
    Expect: both times the alert "No QR code was found in the clipboard's image." and the document still reads "keep".
    """
    app.clipboard(set="plain")
    app.new("keep")
    app.run("Tools|Read QR Code from Clipboard")
    app.idle(0.2)
    assert [e["message"] for e in U.alerts(app.modal_log())] == ["No QR code was found in the clipboard's image."]
    assert app.text() == "keep"
    app.call("e2e_clipboard", clear=True)
    app.run("Tools|Read QR Code from Clipboard")
    app.idle(0.2)
    assert [e["message"] for e in U.alerts(app.modal_log())] == ["No QR code was found in the clipboard's image."]
    assert app.text() == "keep"


@pytest.mark.case("MACEXTRA-009")
def test_macextra_009_an_image_with_no_qr_code_and_an_image_with_two_on_the_clipbo(app, tmp):
    """MACEXTRA-009: An image with no QR code, and an image with two, on the clipboard

    Covers: -
    Channel: clipboard, mcp, modal
    Steps: (needs a hook to put an image file on the private clipboard) Put a white PNG with the word "hello" on the clipboard and run Read QR Code from Clipboard; then a PNG with two QR codes (made with Pillow from two QR images the app saved, one above the other, payloads "top" and "bottom").
    Expect: the first gives the alert "No QR code was found in the clipboard's image." and no text; the second inserts "top\\nbottom" (top to bottom).
    """
    from PIL import Image
    hello = U.text_image(tmp / "hello.png", ["hello"])
    app.clipboard_info(image=hello)
    app.new("keep")
    app.run("Tools|Read QR Code from Clipboard")
    app.wait(lambda: U.alerts(app.modal_log(clear=False)), 10)
    assert [e["message"] for e in U.alerts(app.modal_log())] == ["No QR code was found in the clipboard's image."]
    assert app.text() == "keep"
    # Two codes the app draws itself, one above the other.
    pngs = []
    for payload in ("top", "bottom"):
        app.new(payload)
        app.sci(SCI_SELECTALL)
        app.run("Tools|QR Code from Selection")
        w = app.wait(lambda: U.qr_window(app), 5)
        out = tmp / f"{payload}.png"
        app.answers(panels=[str(out)])
        app.click(w["number"], "Save…")
        app.wait(lambda: out.exists() and out.stat().st_size > 0, 5)
        pngs.append(Image.open(out).convert("RGB"))
    U.close_qr(app)
    side = max(i.width for i in pngs)
    both = Image.new("RGB", (side + 200, sum(i.height for i in pngs) + 300), "white")
    both.paste(pngs[0], (100, 100))
    both.paste(pngs[1], (100, 200 + pngs[0].height))
    both.save(tmp / "both.png")
    app.clipboard_info(image=tmp / "both.png")
    app.new("")
    app.run("Tools|Read QR Code from Clipboard")
    assert app.wait(lambda: app.text(), 10) == "top\nbottom"


@pytest.mark.case("MACEXTRA-010")
def test_macextra_010_paste_image_as_text_puts_the_image_s_words_at_the_caret(app, tmp):
    """MACEXTRA-010: Paste Image as Text puts the image's words at the caret

    Covers: -
    Channel: clipboard, mcp
    Steps: (needs the image-on-clipboard hook) Make a PNG "Hello OCR World 2026" with Pillow; put it on the clipboard; document "[x]" with "x" selected; run `Edit|Paste Image as Text`; undo once.
    Expect: the document reads "[Hello OCR World 2026]"; one undo restores "[x]"; no alert.
    """
    png = U.text_image(tmp / "ocr.png", ["Hello OCR World 2026"])
    app.clipboard_info(image=png)
    app.new("[x]")
    app.select(1, 2, 1, 3)
    app.run("Edit|Paste Image as Text")
    assert app.wait(lambda: app.text() != "[x]" and app.text(), 20) == "[Hello OCR World 2026]"
    assert not U.alerts(app.modal_log())
    app.sci(SCI_UNDO)
    assert app.text() == "[x]"


@pytest.mark.case("MACEXTRA-011")
def test_macextra_011_a_file_copied_in_finder_is_read_too(app, tmp):
    """MACEXTRA-011: A file copied in Finder is read too

    Covers: -
    Channel: clipboard, mcp
    Steps: (needs a hook to put a file URL, type public.file-url, on the clipboard) Put the URL of the PNG of MACEXTRA-010 on the clipboard; run Paste Image as Text in an empty document.
    Expect: the document reads "Hello OCR World 2026".
    """
    png = U.text_image(tmp / "ocr.png", ["Hello OCR World 2026"])
    app.clipboard_info(files=[png])
    app.new("")
    app.run("Edit|Paste Image as Text")
    assert app.wait(lambda: app.text(), 20) == "Hello OCR World 2026"


@pytest.mark.case("MACEXTRA-012")
def test_macextra_012_paste_image_as_text_without_an_image_says_so(app, tmp):
    """MACEXTRA-012: Paste Image as Text without an image says so

    Covers: -
    Channel: clipboard, mcp, modal
    Steps: Set the clipboard to the text "not an image"; document "keep"; run Paste Image as Text; then (image hook) a plain white PNG.
    Expect: the alert "No text was found in the clipboard's image." each time; the document still reads "keep".
    """
    app.clipboard(set="not an image")
    app.new("keep")
    app.run("Edit|Paste Image as Text")
    app.wait(lambda: U.alerts(app.modal_log(clear=False)), 10)
    assert [e["message"] for e in U.alerts(app.modal_log())] == ["No text was found in the clipboard's image."]
    assert app.text() == "keep"
    app.clipboard_info(image=U.blank_image(tmp / "blank.png"))
    app.run("Edit|Paste Image as Text")
    app.wait(lambda: U.alerts(app.modal_log(clear=False)), 20)
    assert [e["message"] for e in U.alerts(app.modal_log())] == ["No text was found in the clipboard's image."]
    assert app.text() == "keep"


@pytest.mark.case("MACEXTRA-013")
def test_macextra_013_recognize_text_in_file_opens_a_png_s_words_in_a_new_document(app, tmp):
    """MACEXTRA-013: Recognize Text in File… opens a PNG's words in a new document

    Covers: -
    Channel: modal, mcp, files
    Steps: Make `ocr.png` with Pillow: three lines "First line 1", "Second line 2", "Third line 3" one below the other; document "keep" in front; queue the PNG's path and run `Edit|Recognize Text in File…`; wait for a new tab.
    Expect: an open panel was shown and answered with the path; a new untitled tab holds "First line 1\\nSecond line 2\\nThird line 3" (reading order top to bottom); the "keep" document is unchanged.
    """
    png = U.text_image(tmp / "ocr.png", ["First line 1", "Second line 2", "Third line 3"])
    app.new("keep")
    keep = app.doc()["index"]
    n = len(app.docs())
    app.answers(panels=[str(png)])
    app.run("Edit|Recognize Text in File…")
    app.wait(lambda: len(app.docs()) == n + 1, 30)
    opened = [e for e in app.modal_log() if e["kind"] == "open"]
    assert opened and opened[0]["answered"] == [str(png)]
    d = app.doc()
    assert d["path"] is None and d["index"] != keep
    assert app.text() == "First line 1\nSecond line 2\nThird line 3"
    assert app.text(keep) == "keep"


@pytest.mark.case("MACEXTRA-014")
def test_macextra_014_a_pdf_is_read_page_by_page(app, tmp):
    """MACEXTRA-014: A PDF is read page by page

    Covers: -
    Channel: modal, mcp, files
    Steps: Make a two-page PDF with Pillow (`save_all`) whose pages read "PAGE ONE 11" and "PAGE TWO 22"; queue it and run Recognize Text in File….
    Expect: a new tab containing "PAGE ONE 11", a blank line, then "PAGE TWO 22" (pages joined by "\\n\\n", in order).
    """
    pdf = U.text_pdf(tmp / "two.pdf", ["PAGE ONE 11", "PAGE TWO 22"])
    n = len(app.docs())
    app.answers(panels=[str(pdf)])
    app.run("Edit|Recognize Text in File…")
    app.wait(lambda: len(app.docs()) == n + 1, 60)
    assert app.text() == "PAGE ONE 11\n\nPAGE TWO 22"


@pytest.mark.case("MACEXTRA-015")
def test_macextra_015_recognize_text_in_file_with_nothing_to_read_or_cancelled(app, tmp):
    """MACEXTRA-015: Recognize Text in File… with nothing to read, or cancelled

    Covers: -
    Channel: modal, mcp, files
    Steps: Make a plain white PNG; queue it and run Recognize Text in File…; wait up to 10 s; then queue a cancel (None) and run it again.
    Expect: the first run shows the alert "No text was found in the file." and opens no tab; the cancelled run opens no tab and shows no alert; the number of documents is unchanged throughout.
    """
    blank = U.blank_image(tmp / "blank.png")
    n = len(app.docs())
    app.answers(panels=[str(blank)])
    app.run("Edit|Recognize Text in File…")
    app.wait(lambda: U.alerts(app.modal_log(clear=False)), 20)
    assert [e["message"] for e in U.alerts(app.modal_log())] == ["No text was found in the file."]
    assert len(app.docs()) == n
    app.answers(panels=[None])
    app.run("Edit|Recognize Text in File…")
    app.idle(0.5)
    log = app.modal_log()
    assert not U.alerts(log)
    assert [e["kind"] for e in log] == ["open"]
    assert len(app.docs()) == n


@pytest.mark.case("MACEXTRA-016")
def test_macextra_016_recognition_does_not_hold_up_the_editor(app, tmp):
    """MACEXTRA-016: Recognition does not hold up the editor

    Covers: -
    Channel: modal, mcp, files
    Steps: Make a 10-page PDF with a line of text on each page; queue it and run Recognize Text in File…; immediately call `get_document` and `edit_document` on the document in front; wait for the new tab.
    Expect: the two calls answer at once (well before the recognition finishes) and the edit lands; the new tab eventually holds ten pages of text in order.
    """
    import time
    pages = [f"PAGE NUMBER {i}" for i in range(1, 11)]
    pdf = U.text_pdf(tmp / "ten.pdf", pages)
    app.new("front")
    n = len(app.docs())
    app.answers(panels=[str(pdf)])
    app.run("Edit|Recognize Text in File…")
    began = time.monotonic()
    assert app.text() == "front"
    app.set_text("front edited")
    quick = time.monotonic() - began
    finished_already = len(app.docs()) > n
    assert app.text() == "front edited"
    assert quick < 1.0 and not finished_already, (quick, finished_already)
    app.wait(lambda: len(app.docs()) == n + 1, 90)
    assert app.text().split("\n\n") == pages


@pytest.mark.case("MACEXTRA-017")
def test_macextra_017_install_command_line_tool_where_usr_local_bin_is_not_writabl(app):
    """MACEXTRA-017: Install Command Line Tool where /usr/local/bin is not writable explains what to run

    Covers: -
    Channel: mcp, modal, files
    Steps: Skip the case unless `/usr/local/bin` exists and is not writable by the test user and `/usr/local/bin/nppmac` does not exist (then the command can change nothing); run `Tools|Install Command Line Tool`; read the modal log.
    Expect: the alert "Could not write to /usr/local/bin." whose informative text reads "Run this in Terminal:\\n\\nsudo ln -sf \\"<bundle>/Contents/Helpers/nppmac\\" /usr/local/bin/nppmac" with the running copy's bundle path; the helper named there exists and is executable; `/usr/local/bin/nppmac` still does not exist.
    """
    import os, stat
    bin_dir = app.work / "bin"
    link = bin_dir / "nppmac"
    if link.is_symlink() or link.exists():
        link.unlink()
    mode = bin_dir.stat().st_mode
    os.chmod(bin_dir, 0o555)
    try:
        if os.access(bin_dir, os.W_OK):
            pytest.skip("the scratch bin folder stays writable (running as root?)")
        app.run("Tools|Install Command Line Tool")
        log = U.alerts(app.modal_log())
        assert [e["message"] for e in log] == ["Could not write to /usr/local/bin."]
        helper = app.bundle / "Contents/Helpers/nppmac"
        info = log[0]["informative"]
        assert info.startswith("Run this in Terminal:\n\nsudo ln -sf \"")
        quoted = info.split('"')[1]
        assert App.same_path(quoted, helper)
        assert info.endswith(f"\" {link}") or info.rstrip().endswith("/nppmac")
        assert helper.exists() and os.access(helper, os.X_OK)
        assert not link.exists() and not link.is_symlink()
    finally:
        os.chmod(bin_dir, stat.S_IMODE(mode))


@pytest.mark.case("MACEXTRA-018")
def test_macextra_018_install_command_line_tool_s_success_path_links_the_helper_ho(app):
    """MACEXTRA-018: Install Command Line Tool's success path links the helper (hook needed)

    Covers: -
    Channel: mcp, modal, files
    Steps: (needs a hook that points the link directory at a scratch folder, e.g. an E2E override of "/usr/local/bin") Create `tmp/bin` with an existing file `nppmac` in it; run Install Command Line Tool.
    Expect: `tmp/bin/nppmac` is a symbolic link to the bundle's `Contents/Helpers/nppmac`; the alert "The nppmac command is installed." lists "nppmac file.txt", "nppmac +42 file.txt" and "something | nppmac -"; the file that was there before is gone (replaced, as the command does without asking).
    """
    import os
    bin_dir = app.work / "bin"
    link = bin_dir / "nppmac"
    if link.is_symlink() or link.exists():
        link.unlink()
    link.write_text("old")
    try:
        app.run("Tools|Install Command Line Tool")
        log = U.alerts(app.modal_log())
        assert [e["message"] for e in log] == ["The nppmac command is installed."]
        info = log[0]["informative"]
        for line in ("nppmac file.txt", "nppmac +42 file.txt", "something | nppmac -"):
            assert line in info
        assert link.is_symlink()
        assert App.same_path(os.readlink(link), app.bundle / "Contents/Helpers/nppmac")
    finally:
        if link.is_symlink() or link.exists():
            link.unlink()
