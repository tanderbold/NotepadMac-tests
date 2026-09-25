"""ENCODING: end-to-end tests (plan: plan/ENCODING.md)."""
import unicodedata
from pathlib import Path

import pytest

from harness.sci import *  # noqa: F401,F403
from _util_enc import (UNICODE_ITEMS, checked_items, read, reopen, save, save_untitled,
                       status_encoding, status_eol, write)

TEXT_1251 = "Привет, мир! Это проверка кодировки текста.\n"
SJIS = "日本語のテキストです。これは文字コードの検出テストです。\n"


# ---------------------------------------------------------------- interpret as

@pytest.mark.case("ENCODING-001")
@pytest.mark.parametrize("cmd,prefix,codec,name", [
    ("IDM_FORMAT_AS_UTF_8", b"", "utf-8", "UTF-8"),
    ("IDM_FORMAT_UTF_8", b"\xef\xbb\xbf", "utf-8", "UTF-8-BOM"),
    ("IDM_FORMAT_UTF_16BE", b"\xfe\xff", "utf-16-be", "UTF-16BE"),
    ("IDM_FORMAT_UTF_16LE", b"\xff\xfe", "utf-16-le", "UTF-16LE"),
    ("IDM_FORMAT_ANSI", b"", "latin-1", "ISO-8859-1"),
])
def test_encoding_001_each_unicode_ansi_item_saves_the_same_text_in_its_own_byte_f(app, tmp, cmd, prefix, codec, name):
    """ENCODING-001: Each Unicode/ANSI item saves the same text in its own byte form"""
    text = "round trip\n"
    p = write(tmp, "enc.txt", text.encode())
    app.open(p)
    app.run(cmd)
    if cmd not in ("IDM_FORMAT_AS_UTF_8", "IDM_FORMAT_ANSI"):
        assert app.doc()["modified"]
        save(app)
    else:
        # UTF-8 already, or ANSI from UTF-8 without BOM (the same bytes read the other way,
        # shouldBeDirty false in Notepad_plus::command): the document stays clean and Save is
        # off (checkDocState), as upstream; the bytes are the right ones.
        assert not app.doc()["modified"] and not app.enabled("IDM_FILE_SAVE")
    assert read(p) == prefix + text.encode(codec)
    reopen(app, p)
    assert app.text() == text
    # A seven-bit file reopens as UTF-8 under the default preferences.
    expected = "UTF-8" if name == "ISO-8859-1" else name
    assert app.doc()["encoding"] == expected


@pytest.mark.case("ENCODING-002")
@pytest.mark.parametrize("cmd,prefix,codec", [
    ("IDM_FORMAT_UTF_8", b"\xef\xbb\xbf", "utf-8"),
    ("IDM_FORMAT_UTF_16BE", b"\xfe\xff", "utf-16-be"),
    ("IDM_FORMAT_UTF_16LE", b"\xff\xfe", "utf-16-le"),
])
def test_encoding_002_non_ascii_text_survives_each_unicode_item(app, tmp, cmd, prefix, codec):
    """ENCODING-002: Non-ASCII text survives each Unicode item"""
    text = "snow ☃ é 日本 😀\n"
    p = write(tmp, "u.txt", text.encode())
    app.open(p)
    app.run(cmd)
    save(app)
    assert read(p) == prefix + text.encode(codec)
    reopen(app, p)
    assert app.text() == text


@pytest.mark.case("ENCODING-003")
def test_encoding_003_the_checkmark_follows_the_current_encoding_radio_group(app):
    """ENCODING-003: The checkmark follows the current encoding (radio group)"""
    app.new("")
    assert checked_items(app) == ["IDM_FORMAT_AS_UTF_8"]
    for cmd in UNICODE_ITEMS:
        app.run(cmd)
        assert checked_items(app) == [cmd]


@pytest.mark.case("ENCODING-004")
def test_encoding_004_choosing_the_encoding_a_document_already_has_does_not_dirty(app, tmp):
    """ENCODING-004: Choosing the encoding a document already has does not dirty it"""
    p = write(tmp, "u8.txt", "naïve\n".encode())
    app.open(p)
    app.run("IDM_FORMAT_AS_UTF_8")
    assert not app.doc()["modified"]
    p2 = write(tmp, "u8bom.txt", b"\xef\xbb\xbf" + "naïve\n".encode())
    app.open(p2)
    app.run("IDM_FORMAT_UTF_8")
    assert not app.doc()["modified"]


@pytest.mark.case("ENCODING-005")
def test_encoding_005_ansi_and_utf_8_reinterpret_the_file_s_bytes_as_notepad_does(app, tmp):
    """ENCODING-005: ANSI and UTF-8 reinterpret the file's bytes, as Notepad++ does"""
    data = b"caf\xc3\xa9\n"
    p = write(tmp, "cafe.txt", data)
    app.open(p)
    app.run("IDM_FORMAT_ANSI")
    assert app.text() == "cafÃ©\n"
    assert not app.doc()["modified"]
    app.run("IDM_FORMAT_AS_UTF_8")
    assert app.text() == "café\n"
    assert not app.doc()["modified"] and not app.enabled("IDM_FILE_SAVE")
    assert read(p) == data


@pytest.mark.case("ENCODING-006")
def test_encoding_006_a_utf_16_item_on_an_untitled_document_decides_the_bytes_of_i(app, tmp):
    """ENCODING-006: A UTF-16 item on an untitled document decides the bytes of its first save"""
    app.new("abc\n")
    app.run("IDM_FORMAT_UTF_16LE")
    p = tmp / "new16.txt"
    save_untitled(app, p)
    assert read(p) == bytes.fromhex("FFFE 6100 6200 6300 0A00")
    assert status_encoding(app) == "UTF-16 LE BOM"


@pytest.mark.case("ENCODING-007")
def test_encoding_007_undo_does_not_undo_an_encoding_change(app, tmp):
    """ENCODING-007: Undo does not undo an encoding change"""
    p = write(tmp, "u.txt", b"abc\n")
    app.open(p)
    app.select(1, 1)
    app.type("x")
    save(app)
    assert read(p) == b"xabc\n"
    app.run("IDM_FORMAT_UTF_8")
    app.keys("cmd+z")
    app.keys("cmd+z")
    assert app.text() == "abc\n"
    assert status_encoding(app) == "UTF-8-BOM"
    assert app.doc()["modified"]
    save(app)
    assert read(p) == b"\xef\xbb\xbfabc\n"


@pytest.mark.case("ENCODING-008")
def test_encoding_008_interpret_as_on_a_modified_charset_document_asks_to_save_fir(app, tmp):
    """ENCODING-008: Interpret-as on a modified charset document asks to save first"""
    p = write(tmp, "r.txt", "Привет мир\n".encode("cp1251"))
    app.open(p)
    app.run("IDM_FORMAT_WIN_1251")
    app.select(1, 1)
    app.type("Ж")
    before = app.text()
    app.modal_log()
    app.answers(alerts=[2])
    app.run("IDM_FORMAT_AS_UTF_8")
    log = app.modal_log()
    assert any("modification" in (e.get("message", "") + e.get("informative", "")).lower() for e in log), log
    assert app.text() == before
    assert app.doc()["encoding"] == "cp1251"


def edit_and_save(app):
    """Encode in reads the file again (fileReload) and leaves nothing to save: an edit undone by
    hand makes the document savable, so Save writes the text back in its character set."""
    app.select(1, 1)
    app.type("x")
    app.keys("backspace")
    save(app)


# ---------------------------------------------------------------- character sets

VIET = "Tiếng Việt"
SAMPLES = {
    "ar": "مرحبا بالعالم", "bal": "Labas rytas, ąčęėįšųūž", "celt": "Dia dhuit ŵŷẁ",
    "cyr": "Привет мир, ёжик", "ce": "Příliš žluťoučký kůň", "zh_t": "繁體中文", "zh_s": "简体中文",
    "gr": "Καλημέρα κόσμε", "he": "שלום עולם", "ja": "日本語テキスト", "ko": "한국어 텍스트",
    "ice": "Þetta er íslenska ðæö", "nord": "Blåbærsyltetøy Æ", "th": "สวัสดีครับ",
    "tr": "Günaydın İstanbul şğ", "vi": VIET, "we": "Café crème à la mode", "we15": "Café € œ",
    "pt": "Ação coração", "fr": "Côté français è",
}
CHARSETS = [
    ("IDM_FORMAT_ISO_8859_6", "iso8859_6", "ar", 28596), ("IDM_FORMAT_DOS_720", "cp720", "ar", 720),
    ("IDM_FORMAT_WIN_1256", "cp1256", "ar", 1256), ("IDM_FORMAT_ISO_8859_4", "iso8859_4", "bal", 28594),
    ("IDM_FORMAT_ISO_8859_13", "iso8859_13", "bal", 28603), ("IDM_FORMAT_DOS_775", "cp775", "bal", 775),
    ("IDM_FORMAT_WIN_1257", "cp1257", "bal", 1257), ("IDM_FORMAT_ISO_8859_14", "iso8859_14", "celt", 28604),
    ("IDM_FORMAT_ISO_8859_5", "iso8859_5", "cyr", 28595), ("IDM_FORMAT_KOI8R_CYRILLIC", "koi8_r", "cyr", 20866),
    ("IDM_FORMAT_KOI8U_CYRILLIC", "koi8_u", "cyr", 21866), ("IDM_FORMAT_MAC_CYRILLIC", "mac_cyrillic", "cyr", 10007),
    ("IDM_FORMAT_DOS_855", "cp855", "cyr", 855), ("IDM_FORMAT_DOS_866", "cp866", "cyr", 866),
    ("IDM_FORMAT_WIN_1251", "cp1251", "cyr", 1251), ("IDM_FORMAT_DOS_852", "cp852", "ce", 852),
    ("IDM_FORMAT_WIN_1250", "cp1250", "ce", 1250), ("IDM_FORMAT_BIG5", "cp950", "zh_t", 950),
    ("IDM_FORMAT_GB2312", "cp936", "zh_s", 936), ("IDM_FORMAT_ISO_8859_2", "iso8859_2", "ce", 28592),
    ("IDM_FORMAT_ISO_8859_7", "iso8859_7", "gr", 28597), ("IDM_FORMAT_DOS_737", "cp737", "gr", 737),
    ("IDM_FORMAT_DOS_869", "cp869", "gr", 869), ("IDM_FORMAT_WIN_1253", "cp1253", "gr", 1253),
    ("IDM_FORMAT_ISO_8859_8", "iso8859_8", "he", 28598), ("IDM_FORMAT_DOS_862", "cp862", "he", 862),
    ("IDM_FORMAT_WIN_1255", "cp1255", "he", 1255), ("IDM_FORMAT_SHIFT_JIS", "cp932", "ja", 932),
    ("IDM_FORMAT_KOREAN_WIN", "cp949", "ko", 949), ("IDM_FORMAT_EUC_KR", "euc_kr", "ko", 51949),
    ("IDM_FORMAT_DOS_861", "cp861", "ice", 861), ("IDM_FORMAT_DOS_865", "cp865", "nord", 865),
    ("IDM_FORMAT_TIS_620", "cp874", "th", 874), ("IDM_FORMAT_ISO_8859_3", "iso8859_3", "tr", 28593),
    ("IDM_FORMAT_ISO_8859_9", "iso8859_9", "tr", 28599), ("IDM_FORMAT_DOS_857", "cp857", "tr", 857),
    ("IDM_FORMAT_WIN_1254", "cp1254", "tr", 1254), ("IDM_FORMAT_WIN_1258", "cp1258", "vi", 1258),
    ("IDM_FORMAT_ISO_8859_1", "latin_1", "we", 28591), ("IDM_FORMAT_ISO_8859_15", "iso8859_15", "we15", 28605),
    ("IDM_FORMAT_DOS_850", "cp850", "we", 850), ("IDM_FORMAT_DOS_858", "cp858", "we", 858),
    ("IDM_FORMAT_DOS_860", "cp860", "pt", 860), ("IDM_FORMAT_DOS_863", "cp863", "fr", 863),
    ("IDM_FORMAT_DOS_437", "cp437", "we", 437), ("IDM_FORMAT_WIN_1252", "cp1252", "we15", 1252),
]


@pytest.mark.case("ENCODING-009")
@pytest.mark.parametrize("cmd,codec,sample,codepage", CHARSETS, ids=[c[0] for c in CHARSETS])
def test_encoding_009_every_character_set_reads_a_file_written_in_it_and_saves_the(app, tmp, cmd, codec, sample, codepage):
    """ENCODING-009: Every character set reads a file written in it and saves the same bytes"""
    text = SAMPLES[sample] + "\n"
    data = text.encode(codec)
    p = write(tmp, "cs.txt", data)
    app.open(p)
    app.run(cmd)
    got = app.text()
    # Vietnamese is written with combining marks; a composed reading is the same text.
    assert unicodedata.normalize("NFC", got) == unicodedata.normalize("NFC", text)
    assert app.doc()["encoding"] == f"cp{codepage}"
    # Encode in reads the file again (fileReload): the document is as the file is.
    assert not app.doc()["modified"]
    edit_and_save(app)
    assert read(p) == data


def _charset_rows():
    rows = []
    tsv = Path(__file__).resolve().parent.parent / "plan" / "commands.tsv"
    for line in tsv.read_text().splitlines()[1:]:
        menu, ident, label = line.split("\t")
        if menu == "Encoding" and label.startswith("Character sets › "):
            _, group, item = label.split(" › ")
            rows.append((ident, group, item))
    return rows


@pytest.mark.case("ENCODING-010")
def test_encoding_010_every_character_set_is_reachable_in_its_script_submenu_under(app, tmp):
    """ENCODING-010: Every character set is reachable in its script submenu under its Notepad++ label"""
    tree = app.menu_tree("Encoding", depth=3)
    charsets = next(i for i in tree if i.get("title") == "Character sets")
    groups = {g["title"]: g for g in charsets["items"] if not g.get("separator")}
    rows = _charset_rows()
    assert len(rows) == 46
    assert set(groups) == {g for _, g, _ in rows}
    assert len(groups) == 16
    for ident, group, label in rows:
        titles = {i.get("title"): i for i in groups[group]["items"]}
        assert label in titles, (group, label)
        assert titles[label]["enabled"]
        assert app.menu_item(ident)["title"] == label
    p = write(tmp, "k.txt", "Привет мир\n".encode("koi8_r"))
    app.open(p)
    r = app.run("Encoding|Character sets|Cyrillic|KOI8-R")
    assert r["ran"]
    assert app.doc()["encoding"] == "cp20866"
    assert app.text() == "Привет мир\n"


@pytest.mark.case("ENCODING-011")
def test_encoding_011_encode_in_is_a_reading_not_a_conversion_switching_sets_back(app, tmp):
    """ENCODING-011: Encode in is a reading, not a conversion: switching sets back and forth is lossless"""
    data = "Привет мир\n".encode("cp1251")
    p = write(tmp, "r.txt", data)
    app.open(p)
    app.run("IDM_FORMAT_KOI8R_CYRILLIC")
    assert app.text() == data.decode("koi8_r")
    app.run("IDM_FORMAT_DOS_866")
    assert app.text() == data.decode("cp866")
    app.run("IDM_FORMAT_WIN_1251")
    assert app.text() == "Привет мир\n"
    assert not app.doc()["modified"]
    assert read(p) == data


@pytest.mark.case("ENCODING-012")
def test_encoding_012_the_chosen_character_set_is_checked_in_the_menu(app, tmp):
    """ENCODING-012: The chosen character set is checked in the menu"""
    p = write(tmp, "r.txt", "Привет мир\n".encode("cp1251"))
    app.open(p)
    ids = ["IDM_FORMAT_WIN_1251", "IDM_FORMAT_KOI8R_CYRILLIC"] + UNICODE_ITEMS
    app.run("IDM_FORMAT_WIN_1251")
    assert checked_items(app, ids) == ["IDM_FORMAT_WIN_1251"]
    app.run("IDM_FORMAT_KOI8R_CYRILLIC")
    assert checked_items(app, ids) == ["IDM_FORMAT_KOI8R_CYRILLIC"]


@pytest.mark.case("ENCODING-013")
def test_encoding_013_the_status_bar_names_the_chosen_character_set(app, tmp):
    """ENCODING-013: The status bar names the chosen character set"""
    p = write(tmp, "r.txt", "Привет мир\n".encode("cp1251"))
    app.open(p)
    app.run("IDM_FORMAT_WIN_1251")
    assert status_encoding(app) == "Windows-1251"
    p2 = write(tmp, "j.txt", SJIS.encode("shift_jis"))
    app.open(p2)
    app.run("IDM_FORMAT_SHIFT_JIS")
    assert status_encoding(app) == "Shift-JIS"


@pytest.mark.case("ENCODING-014")
def test_encoding_014_text_typed_into_a_charset_document_is_saved_in_that_set_unre(app, tmp):
    """ENCODING-014: Text typed into a charset document is saved in that set; unrepresentable characters become "?\""""
    data = "Пока мир\n".encode("cp1251")
    p = write(tmp, "r.txt", data)
    app.open(p)
    app.run("IDM_FORMAT_WIN_1251")
    app.select(1, 1)
    app.type("Ж€☃")
    save(app)
    assert read(p) == b"\xc6\x88?" + data


@pytest.mark.case("ENCODING-015")
def test_encoding_015_a_code_page_that_cannot_read_the_bytes_declines_with_an_aler(app, tmp):
    """ENCODING-015: A code page that cannot read the bytes declines with an alert"""
    data = b"abc \x81\x20 \xff\xfd\n"
    p = write(tmp, "bad.txt", data)
    app.open(p)
    before = app.text()
    assert before == data.decode("latin-1")
    app.modal_log()
    app.answers(alerts=[1, 1])
    app.run("IDM_FORMAT_SHIFT_JIS")
    app.run("IDM_FORMAT_BIG5")
    messages = [e.get("message") for e in app.modal_log()]
    assert "Cannot read this document as Shift-JIS." in messages
    assert "Cannot read this document as Big5 (Traditional)." in messages
    assert app.text() == before
    assert app.doc()["encoding"] == "ISO-8859-1"


def _decode_lenient(data: bytes, codec: str) -> list:
    out = []
    for b in data:
        try:
            out.append(bytes([b]).decode(codec))
        except UnicodeDecodeError:
            out.append(None)
    return out


@pytest.mark.case("ENCODING-016")
@pytest.mark.parametrize("cmd,codec", [("IDM_FORMAT_DOS_720", "cp720"), ("IDM_FORMAT_DOS_858", "cp858"),
                                       ("IDM_FORMAT_DOS_850", "cp850"), ("IDM_FORMAT_DOS_861", "cp861")])
def test_encoding_016_code_page_720_and_858_follow_windows_not_the_macos_converter(app, tmp, cmd, codec):
    """ENCODING-016: Code page 720 and 858 follow Windows, not the macOS converters"""
    high = bytes(range(0x80, 0x100))
    data = high + b"\n"
    p = write(tmp, "high.txt", data)
    app.open(p)
    app.run(cmd)
    got = app.text()
    assert len(got) == 129 and got.endswith("\n")
    for i, want in enumerate(_decode_lenient(high, codec)):
        if want is None:
            assert got[i] == "�", (hex(0x80 + i), got[i])
        else:
            assert got[i] == want, (hex(0x80 + i), got[i], want)
    if codec == "cp858":
        assert got[0xD5 - 0x80] == "€"
    if codec == "cp850":
        assert got[0xD5 - 0x80] == "ı"
    edit_and_save(app)
    assert read(p) == data


@pytest.mark.case("ENCODING-017")
def test_encoding_017_undo_after_encode_in_does_not_leave_the_text_read_in_one_set(app, tmp):
    """ENCODING-017: Undo after Encode in does not leave the text read in one set and written in another"""
    data = bytes([0xEA, 0xA9, 0xA5, 0xA0, 0x9F, 0x0A])
    p = write(tmp, "ar.txt", data)
    app.open(p)
    app.run("IDM_FORMAT_DOS_720")
    assert app.text() == "مرحبا\n"
    app.keys("cmd+z")
    enc = app.doc()["encoding"]
    text = app.text()
    assert text == "مرحبا\n" or enc != "cp720"
    # Encode in reads the file again (Notepad++'s fileReload): nothing is left to undo or to save.
    assert text == "مرحبا\n" and not app.doc()["modified"]
    assert read(p) == data


@pytest.mark.case("ENCODING-018")
def test_encoding_018_reload_keeps_the_chosen_character_set(app, tmp):
    """ENCODING-018: Reload keeps the chosen character set"""
    p = write(tmp, "r.txt", "Привет мир\n".encode("cp1251"))
    app.open(p)
    app.run("IDM_FORMAT_WIN_1251")
    Path(p).write_bytes("Пока мир\n".encode("cp1251"))
    app.answers(alerts=[1, 1])
    app.run("IDM_FILE_RELOAD")
    app.wait(lambda: app.text() == "Пока мир\n", message="reloaded text")
    assert app.doc()["encoding"] == "cp1251"
    assert not app.doc()["modified"]


@pytest.mark.case("ENCODING-019")
def test_encoding_019_save_as_keeps_the_character_set(app, tmp):
    """ENCODING-019: Save As keeps the character set"""
    text = "Привіт, світе\n"
    p = write(tmp, "u.txt", text.encode("koi8_u"))
    app.open(p)
    app.run("IDM_FORMAT_KOI8U_CYRILLIC")
    assert app.text() == text
    copy = tmp / "copy.txt"
    app.answers(panels=[str(copy)])
    app.run("IDM_FILE_SAVEAS")
    app.wait(lambda: copy.exists(), message="copy saved")
    assert read(copy) == text.encode("koi8_u")
    d = app.doc()
    assert d["title"] == "copy.txt"
    assert d["encoding"] == "cp21866"


@pytest.mark.case("ENCODING-020")
@pytest.mark.restart
def test_encoding_020_the_character_set_of_a_file_is_remembered_in_the_session(app, tmp):
    """ENCODING-020: The character set of a file is remembered in the session"""
    text = "Привет мир\n"
    p = write(tmp, "cp855.txt", text.encode("cp855"))
    try:
        app.stop()
        app.start(session=True, defaults={"restoreSession": True})
        app.open(p)
        app.run("IDM_FORMAT_DOS_855")
        assert app.text() == text and not app.doc()["modified"]
        app.stop()
        session = (app.home / "Library/Application Support/NotepadMac/session.xml").read_text()
        assert 'encoding="855"' in session
        app.start(session=True, clean_home=False, reset=False)
        docs = app.wait(lambda: [d for d in app.docs() if d["title"] == "cp855.txt"], message="session restored")
        index = docs[0]["index"]
        assert app.text(document=index) == text
        d = app.doc(document=index)
        assert d["encoding"] == "cp855"
        assert not d["modified"]
    finally:
        app.stop()
        app.start()


# ---------------------------------------------------------------- convert to

@pytest.mark.case("ENCODING-021")
@pytest.mark.parametrize("cmd,expected", [
    ("IDM_FORMAT_CONV2_ANSI", b"snow \xe9\n"),
    ("IDM_FORMAT_CONV2_AS_UTF_8", b"snow \xc3\xa9\n"),
    ("IDM_FORMAT_CONV2_UTF_8", b"\xef\xbb\xbfsnow \xc3\xa9\n"),
    ("IDM_FORMAT_CONV2_UTF_16BE", b"\xfe\xff" + "snow é\n".encode("utf-16-be")),
    ("IDM_FORMAT_CONV2_UTF_16LE", b"\xff\xfe" + "snow é\n".encode("utf-16-le")),
])
def test_encoding_021_each_convert_to_item_writes_the_same_text_in_the_new_byte_fo(app, tmp, cmd, expected):
    """ENCODING-021: Each Convert to item writes the same text in the new byte form"""
    text = "snow é\n"
    p = write(tmp, "c.txt", text.encode())
    app.open(p)
    app.run(cmd)
    assert app.text() == text
    if cmd == "IDM_FORMAT_CONV2_AS_UTF_8":
        # Converting a UTF-8 file to UTF-8 changes nothing: clean, Save off, as upstream.
        assert not app.doc()["modified"] and not app.enabled("IDM_FILE_SAVE")
    else:
        save(app)
    assert read(p) == expected
    reopen(app, p)
    assert app.text() == text


@pytest.mark.case("ENCODING-022")
def test_encoding_022_convert_to_marks_the_document_modified_and_updates_the_statu(app, tmp):
    """ENCODING-022: Convert to marks the document modified and updates the status bar and checkmark"""
    p = write(tmp, "c.txt", "é\n".encode())
    app.open(p)
    assert not app.doc()["modified"]
    app.run("IDM_FORMAT_CONV2_UTF_16BE")
    assert app.doc()["modified"]
    assert status_encoding(app) == "UTF-16 BE BOM"
    assert checked_items(app) == ["IDM_FORMAT_UTF_16BE"]
    app.run("IDM_FORMAT_CONV2_UTF_8")
    assert status_encoding(app) == "UTF-8-BOM"
    assert checked_items(app) == ["IDM_FORMAT_UTF_8"]


@pytest.mark.case("ENCODING-023")
def test_encoding_023_converting_to_ansi_replaces_characters_ansi_cannot_hold(app, tmp):
    """ENCODING-023: Converting to ANSI replaces characters ANSI cannot hold"""
    p = write(tmp, "s.txt", "snow ☃ é\n".encode())
    app.open(p)
    app.run("IDM_FORMAT_CONV2_ANSI")
    assert status_encoding(app) == "ANSI"
    save(app)
    assert read(p) == b"snow ? \xe9\n"
    reopen(app, p)
    assert app.text() == "snow ? é\n"


@pytest.mark.case("ENCODING-024")
@pytest.mark.parametrize("cmd,prefix,codec,name", [
    ("IDM_FORMAT_CONV2_AS_UTF_8", b"", "utf-8", "UTF-8"),
    ("IDM_FORMAT_CONV2_UTF_16LE", b"\xff\xfe", "utf-16-le", "UTF-16LE"),
])
def test_encoding_024_convert_to_from_a_character_set_really_changes_the_bytes(app, tmp, cmd, prefix, codec, name):
    """ENCODING-024: Convert to from a character set really changes the bytes"""
    text = "Привет мир\n"
    p = write(tmp, "k.txt", text.encode("koi8_r"))
    app.open(p)
    app.run("IDM_FORMAT_KOI8R_CYRILLIC")
    app.run(cmd)
    save(app)
    assert read(p) == prefix + text.encode(codec)
    assert app.doc()["encoding"] == name


@pytest.mark.case("ENCODING-025")
def test_encoding_025_a_conversion_survives_undo_and_redo_of_text_edits(app, tmp):
    """ENCODING-025: A conversion survives undo and redo of text edits"""
    p = write(tmp, "a.txt", b"abc\n")
    app.open(p)
    app.select(1, 1)
    app.type("X")
    app.run("IDM_FORMAT_CONV2_UTF_8")
    for _ in range(3):
        if app.text() == "abc\n":
            break
        app.keys("cmd+z")
    assert app.text() == "abc\n"
    assert app.doc()["modified"]
    save(app)
    assert read(p) == b"\xef\xbb\xbfabc\n"


@pytest.mark.case("ENCODING-026")
def test_encoding_026_converting_a_utf_16_file_back_to_utf_8_drops_the_bom(app, tmp):
    """ENCODING-026: Converting a UTF-16 file back to UTF-8 drops the BOM"""
    p = write(tmp, "w.txt", b"\xff\xfe" + "hi Ω\n".encode("utf-16-le"))
    app.open(p)
    app.run("IDM_FORMAT_CONV2_AS_UTF_8")
    save(app)
    assert read(p) == b"hi \xce\xa9\n"
    info = app.call("file_encoding", path=p)
    assert info["bom"] == "none"
    assert info["encoding"] == "UTF-8"


# ---------------------------------------------------------------- detection on open

@pytest.mark.case("ENCODING-027")
@pytest.mark.parametrize("prefix,codec,enc,label,item", [
    (b"\xef\xbb\xbf", "utf-8", "UTF-8-BOM", "UTF-8-BOM", "IDM_FORMAT_UTF_8"),
    (b"\xff\xfe", "utf-16-le", "UTF-16LE", "UTF-16 LE BOM", "IDM_FORMAT_UTF_16LE"),
    (b"\xfe\xff", "utf-16-be", "UTF-16BE", "UTF-16 BE BOM", "IDM_FORMAT_UTF_16BE"),
])
def test_encoding_027_a_bom_decides_the_encoding_and_is_not_part_of_the_text(app, tmp, prefix, codec, enc, label, item):
    """ENCODING-027: A BOM decides the encoding and is not part of the text"""
    data = prefix + "hi Ω\n".encode(codec)
    p = write(tmp, "b.txt", data)
    app.open(p)
    assert app.text() == "hi Ω\n"
    assert app.sci(SCI_GETCHARAT, 0) == ord("h")
    d = app.doc()
    assert d["encoding"] == enc
    assert not d["modified"]
    assert status_encoding(app) == label
    assert checked_items(app) == [item]
    app.select(1, 1)
    app.type("x")
    app.keys("backspace")
    save(app)
    assert read(p) == data


@pytest.mark.case("ENCODING-028")
@pytest.mark.parametrize("codec,enc", [("utf-16-le", "UTF-16LE"), ("utf-16-be", "UTF-16BE")])
def test_encoding_028_utf_16_without_a_bom_is_recognised_and_saved_without_one(app, tmp, codec, enc):
    """ENCODING-028: UTF-16 without a BOM is recognised and saved without one"""
    p = write(tmp, "w.txt", "hello world, plain\n".encode(codec))
    app.open(p)
    assert app.text() == "hello world, plain\n"
    assert app.doc()["encoding"] == enc
    app.select(1, 19)
    app.type("!")
    save(app)
    assert read(p) == "hello world, plain!\n".encode(codec)
    assert "BOM" not in status_encoding(app)


@pytest.mark.case("ENCODING-029")
def test_encoding_029_valid_utf_8_without_a_bom_opens_as_utf_8(app, tmp):
    """ENCODING-029: Valid UTF-8 without a BOM opens as UTF-8"""
    p = write(tmp, "u.txt", b"na\xc3\xafve \xe2\x98\x83\n")
    app.open(p)
    assert app.text() == "naïve ☃\n"
    d = app.doc()
    assert d["encoding"] == "UTF-8"
    assert not d["modified"]
    assert status_encoding(app) == "UTF-8"
    assert checked_items(app) == ["IDM_FORMAT_AS_UTF_8"]


@pytest.mark.case("ENCODING-030")
def test_encoding_030_seven_bit_files_follow_apply_to_opened_ansi_files(app, tmp):
    """ENCODING-030: Seven-bit files follow "Apply to opened ANSI files\""""
    assert app.pref("defaultEncoding") == "UTF-8"
    old = app.pref("openAnsiAsUtf8")
    try:
        app.set_prefs(openAnsiAsUtf8=True)
        app.open(write(tmp, "a.txt", b"plain\n"))
        assert app.doc()["encoding"] == "UTF-8"
        assert status_encoding(app) == "UTF-8"
        app.open(write(tmp, "e1.txt", b""))
        assert app.doc()["encoding"] == "UTF-8"
        app.set_prefs(openAnsiAsUtf8=False)
        app.open(write(tmp, "b.txt", b"plain\n"))
        assert app.doc()["encoding"] == "ISO-8859-1"
        assert status_encoding(app) == "ANSI"
        app.open(write(tmp, "e2.txt", b""))
        assert app.doc()["encoding"] == "ISO-8859-1"
    finally:
        app.set_prefs(openAnsiAsUtf8=old)


DETECT = [
    ("sjis", SJIS, "shift_jis", {"SHIFT_JIS"}),
    ("gb", "这是一个简体中文的文本文件，用于测试编码检测功能是否正常。\n", "gb2312", {"GB18030", "GB2312", "GBK"}),
    ("big5", "這是一個繁體中文的文字檔案，用來測試編碼偵測功能是否正常。\n", "big5", {"BIG5"}),
    ("euckr", "한국어 텍스트 파일입니다. 인코딩 감지 테스트를 하고 있습니다.\n", "euc_kr", {"EUC-KR"}),
    ("koi8r", TEXT_1251, "koi8_r", {"KOI8-R"}),
    ("cp866", TEXT_1251, "cp866", {"CP866", "IBM866"}),
    ("hebrew", "שלום עולם, זהו קובץ טקסט לבדיקה של זיהוי הקידוד.\n", "cp1255", {"WINDOWS-1255", "ISO-8859-8"}),
    ("greek", "Καλημέρα κόσμε, αυτό είναι ένα δοκιμαστικό κείμενο.\n", "cp1253", {"WINDOWS-1253", "ISO-8859-7"}),
]


@pytest.mark.case("ENCODING-031")
@pytest.mark.parametrize("name,text,codec,accepted", DETECT, ids=[d[0] for d in DETECT])
def test_encoding_031_uchardet_detects_legacy_character_sets_on_open(app, tmp, name, text, codec, accepted):
    """ENCODING-031: uchardet detects legacy character sets on open"""
    p = write(tmp, f"{name}.txt", text.encode(codec))
    app.open(p)
    assert app.text() == text
    d = app.doc()
    assert not d["modified"]
    assert d["encoding"] in accepted
    info = app.call("file_encoding", path=p)
    assert info["encoding"] == d["encoding"]
    assert info["charset_detected"]


@pytest.mark.case("ENCODING-032")
def test_encoding_032_windows_1251_russian_text_is_detected_as_windows_1251(app, tmp):
    """ENCODING-032: Windows-1251 Russian text is detected as Windows-1251"""
    p = write(tmp, "r.txt", TEXT_1251.encode("cp1251"))
    app.open(p)
    assert app.text() == TEXT_1251
    assert app.doc()["encoding"] == "WINDOWS-1251"


@pytest.mark.case("ENCODING-033")
def test_encoding_033_detection_can_be_turned_off(app, tmp):
    """ENCODING-033: Detection can be turned off"""
    data = SJIS.encode("shift_jis")
    p = write(tmp, "j.txt", data)
    try:
        app.set_prefs(autoDetectCharacterEncoding=False)
        app.open(p)
        assert app.doc()["encoding"] == "ISO-8859-1"
        assert status_encoding(app) == "ANSI"
        assert app.text() == data.decode("latin-1")
        app.run("IDM_FORMAT_SHIFT_JIS")
        assert app.text() == SJIS
    finally:
        app.set_prefs(autoDetectCharacterEncoding=True)


@pytest.mark.case("ENCODING-034")
def test_encoding_034_detected_legacy_sets_are_shown_and_saved_as_that_set(app, tmp):
    """ENCODING-034: Detected legacy sets are shown and saved as that set"""
    data = SJIS.encode("shift_jis")
    p = write(tmp, "j.txt", data)
    app.open(p)
    app.select(1, 1)
    app.type("X")
    save(app)
    assert read(p) == b"X" + data
    assert status_encoding(app) == "Shift-JIS"


@pytest.mark.case("ENCODING-035")
@pytest.mark.slow
def test_encoding_035_a_large_non_utf_8_file_is_detected_and_converted_piecewise(app, tmp):
    """ENCODING-035: A large non-UTF-8 file is detected and converted piecewise"""
    line = "Съешь же ещё этих мягких французских булок, да выпей чаю. Широкая электрификация южных губерний.\n"
    chunk = line.encode("koi8_r")
    count = (65 * 1024 * 1024) // len(chunk) + 1
    p = tmp / "big.txt"
    with open(p, "wb") as f:
        for _ in range(count):
            f.write(chunk)
    try:
        app.call("open_document", path=str(p), timeout=120)
        d = app.doc()
        assert d["encoding"] == "KOI8-R"
        assert app.sci(SCI_GETLINECOUNT) == count + 1
        assert app.sci(SCI_GETLINE, 0, returns="string") == line
        assert app.sci(SCI_GETLINE, count - 1, returns="string") == line
    finally:
        app.close_all()
        p.unlink()


# ---------------------------------------------------------------- invalid bytes

@pytest.mark.case("ENCODING-036")
def test_encoding_036_a_file_that_is_not_valid_utf_8_and_not_recognised_opens_as_a(app, tmp):
    """ENCODING-036: A file that is not valid UTF-8 and not recognised opens as ANSI byte for byte"""
    data = b"ok \xff\xfe\x80 bad\n"
    p = write(tmp, "bad.txt", data)
    app.open(p)
    assert app.text() == data.decode("latin-1")
    assert status_encoding(app) == "ANSI"
    assert checked_items(app) == ["IDM_FORMAT_ANSI"]
    app.select(1, 1)
    app.type("x")
    app.keys("backspace")
    save(app)
    assert read(p) == data


@pytest.mark.case("ENCODING-037")
def test_encoding_037_invalid_utf_8_sequences_in_the_middle_of_utf_8_text_are_not(app, tmp):
    """ENCODING-037: Invalid UTF-8 sequences in the middle of UTF-8 text are not lost"""
    data = b"valid \xc3\xa9 then \xc3\x28 and \xe2\x82\n"
    p = write(tmp, "inv.txt", data)
    app.open(p)
    assert app.doc()["encoding"] == "ISO-8859-1"
    assert status_encoding(app) == "ANSI"
    assert app.text() == data.decode("latin-1")
    assert "IDM_FORMAT_AS_UTF_8" not in checked_items(app)
    app.select(1, 5)
    app.type("x")
    app.keys("backspace")
    save(app)
    assert read(p) == data
    assert app.call("file_encoding", path=p)["binary"] is False


@pytest.mark.case("ENCODING-038")
def test_encoding_038_nul_bytes_do_not_cut_the_document(app, tmp):
    """ENCODING-038: NUL bytes do not cut the document"""
    data = b"a\x00b\x00c\nsecond\n"
    p = write(tmp, "nul.txt", data)
    app.open(p)
    assert app.doc()["bytes"] == 13
    assert app.text() == data.decode()
    app.select(2, 1)
    app.type("x")
    app.keys("backspace")
    save(app)
    assert read(p) == data
    assert app.call("file_encoding", path=p)["binary"] is True


@pytest.mark.case("ENCODING-039")
def test_encoding_039_mixed_scripts_that_ansi_cannot_hold_survive_an_interpret_as(app, tmp):
    """ENCODING-039: Mixed scripts that ANSI cannot hold survive an interpret-as change to UTF-16"""
    text = "Ω 日本 😀\n"
    p = write(tmp, "m.txt", text.encode())
    app.open(p)
    app.run("IDM_FORMAT_UTF_16LE")
    save(app)
    assert read(p) == b"\xff\xfe" + text.encode("utf-16-le")
    assert b"\x3d\xd8\x00\xde" in read(p)
    assert app.text() == text
    app.run("IDM_FORMAT_AS_UTF_8")
    save(app)
    assert read(p) == text.encode()
    assert app.text() == text


# ---------------------------------------------------------------- status bar, new documents

@pytest.mark.case("ENCODING-040")
def test_encoding_040_the_status_bar_shows_the_encoding_of_the_active_tab(app, tmp):
    """ENCODING-040: The status bar shows the encoding of the active tab"""
    files = [
        (write(tmp, "a.txt", b"\xef\xbb\xbfx\n"), "UTF-8-BOM", "IDM_FORMAT_UTF_8"),
        (write(tmp, "b.txt", "café\n".encode("latin-1")), "ANSI", "IDM_FORMAT_ANSI"),
        (write(tmp, "c.txt", b"\xfe\xff" + "x\n".encode("utf-16-be")), "UTF-16 BE BOM", "IDM_FORMAT_UTF_16BE"),
    ]
    for p, _, _ in files:
        app.open(p)
    by_title = {d["title"]: d["index"] for d in app.docs()}
    for p, label, item in files:
        index = by_title[Path(p).name]
        app.select(1, 1, document=index)
        app.wait(lambda: app.doc()["title"] == Path(p).name, message="tab active")
        assert status_encoding(app) == label
        assert checked_items(app) == [item]


@pytest.mark.case("ENCODING-041")
@pytest.mark.parametrize("pref,label,item,expected", [
    ("UTF-8-BOM", "UTF-8-BOM", "IDM_FORMAT_UTF_8", bytes.fromhex("EFBBBF C3A9 0A")),
    ("UTF-16 LE BOM", "UTF-16 LE BOM", "IDM_FORMAT_UTF_16LE", bytes.fromhex("FFFE E900 0A00")),
    ("ANSI", "ANSI", "IDM_FORMAT_ANSI", bytes.fromhex("E9 0A")),
])
def test_encoding_041_new_documents_take_the_new_document_encoding_preference(app, tmp, pref, label, item, expected):
    """ENCODING-041: New documents take the New Document encoding preference"""
    old = app.pref("defaultEncoding")
    try:
        app.set_prefs(defaultEncoding=pref)
        app.run("IDM_FILE_NEW")
        assert status_encoding(app) == label
        assert checked_items(app) == [item]
        app.type("é")
        app.keys("return")
        p = tmp / "n.txt"
        save_untitled(app, p)
        assert read(p) == expected
    finally:
        app.set_prefs(defaultEncoding=old)


# ---------------------------------------------------------------- line endings

@pytest.mark.case("ENCODING-042")
@pytest.mark.parametrize("data,eol,label", [
    (b"a\r\nb\r\n", "CRLF", "Windows (CR LF)"),
    (b"a\nb\n", "LF", "Unix (LF)"),
    (b"a\rb\r", "CR", "Macintosh (CR)"),
    (b"a\nb\r\nc\r\n", "LF", "Unix (LF)"),
    (b"no newline", "LF", "Unix (LF)"),
], ids=["crlf", "lf", "cr", "mixed", "none"])
def test_encoding_042_the_first_line_ending_decides_a_file_s_eol_format_shown_in_t(app, tmp, data, eol, label):
    """ENCODING-042: The first line ending decides a file's EOL format, shown in the status bar"""
    p = write(tmp, "e.txt", data)
    app.open(p)
    assert app.doc()["eol"] == eol
    assert status_eol(app) == label
    assert app.text() == data.decode()


@pytest.mark.case("ENCODING-043")
@pytest.mark.parametrize("eol", ["\r\n", "\n", "\r"], ids=["crlf", "lf", "cr"])
def test_encoding_043_enter_inserts_the_document_s_own_line_ending_and_saving_keep(app, tmp, eol):
    """ENCODING-043: Enter inserts the document's own line ending and saving keeps it"""
    p = write(tmp, "e.txt", f"a{eol}b{eol}".encode())
    app.open(p)
    app.select(1, 2)
    app.keys("return")
    app.type("z")
    save(app)
    assert read(p) == f"a{eol}z{eol}b{eol}".encode()


@pytest.mark.case("ENCODING-044")
@pytest.mark.parametrize("mode,label,eol", [(0, "Windows (CR LF)", b"\r\n"), (2, "Unix (LF)", b"\n"),
                                            (1, "Macintosh (CR)", b"\r")], ids=["crlf", "lf", "cr"])
def test_encoding_044_new_documents_take_the_default_eol_preference(app, tmp, mode, label, eol):
    """ENCODING-044: New documents take the default EOL preference"""
    old = app.pref("defaultEOL")
    try:
        app.set_prefs(defaultEOL=mode)
        app.run("IDM_FILE_NEW")
        assert status_eol(app) == label
        app.keys("return")
        app.keys("return")
        p = tmp / "n.txt"
        save_untitled(app, p)
        assert read(p) == eol * 2
    finally:
        app.set_prefs(defaultEOL=old)


@pytest.mark.case("ENCODING-045")
def test_encoding_045_line_endings_survive_a_change_of_encoding(app, tmp):
    """ENCODING-045: Line endings survive a change of encoding"""
    p = write(tmp, "e.txt", b"a\r\nb\r\n")
    app.open(p)
    app.run("IDM_FORMAT_CONV2_UTF_16LE")
    save(app)
    assert read(p) == bytes.fromhex("FFFE 6100 0D00 0A00 6200 0D00 0A00")
    app.run("IDM_FORMAT_CONV2_ANSI")
    save(app)
    assert read(p) == b"a\r\nb\r\n"
    assert status_eol(app) == "Windows (CR LF)"


@pytest.mark.case("ENCODING-046")
@pytest.mark.parametrize("prefix,codec", [(b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be")], ids=["le", "be"])
def test_encoding_046_a_utf_16_file_with_cr_lf_endings_is_read_with_the_right_eol(app, tmp, prefix, codec):
    """ENCODING-046: A UTF-16 file with CR LF endings is read with the right EOL"""
    p = write(tmp, "w.txt", prefix + "x\r\ny\r\n".encode(codec))
    app.open(p)
    assert app.text() == "x\r\ny\r\n"
    assert app.doc()["eol"] == "CRLF"
    assert status_eol(app) == "Windows (CR LF)"
    info = app.call("file_encoding", path=p)
    assert info["eol"] == "CRLF"
    assert info["mixed_eol"] is False


# ---------------------------------------------------------------- the agent's view

@pytest.mark.case("ENCODING-047")
def test_encoding_047_file_encoding_reports_the_bom_detected_set_eol_and_a_preview(app, tmp):
    """ENCODING-047: file_encoding reports the BOM, detected set, EOL and a preview without opening the file"""
    count = len(app.docs())
    fe = lambda p: app.call("file_encoding", path=p)  # noqa: E731
    a = fe(write(tmp, "a.txt", b"\xef\xbb\xbfone\r\ntwo\r\n"))
    assert a["bom"] == "UTF-8" and a["eol"] == "CRLF"
    b = fe(write(tmp, "b.txt", "hello world, plain\n".encode("utf-16-be")))
    assert b["bom"] == "none" and b["utf16_without_bom"] == "UTF-16 BE"
    c = fe(write(tmp, "c.txt", TEXT_1251.encode("koi8_r")))
    assert c["bom"] == "none" and c["encoding"] == "KOI8-R"
    assert c["preview"].startswith("Привет")
    m = fe(write(tmp, "m.txt", b"a\nb\r\nc\r\n"))
    assert m["eol"] == "CRLF" and m["mixed_eol"] is True
    z = fe(write(tmp, "z.bin", b"\x89PNG\r\n\x1a\n" + b"\x00" * 64))
    assert z["binary"] is True and z["encoding"] is None
    assert len(app.docs()) == count


@pytest.mark.case("ENCODING-048")
def test_encoding_048_get_document_reports_the_encoding_as_the_menu_does(app, tmp):
    """ENCODING-048: get_document reports the encoding as the menu does"""
    app.new("x")
    app.run("IDM_FORMAT_UTF_8")
    assert app.doc()["encoding"] == "UTF-8-BOM"
    p = write(tmp, "ce.txt", "Příliš žluťoučký kůň\n".encode("cp1250"))
    app.open(p)
    app.run("IDM_FORMAT_WIN_1250")
    d = app.doc()
    assert d["encoding"] == "cp1250"
    listed = {x["title"]: x for x in app.docs()}
    if "encoding" in listed["ce.txt"]:
        assert listed["ce.txt"]["encoding"] == "cp1250"
