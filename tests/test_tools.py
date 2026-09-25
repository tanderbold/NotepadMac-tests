"""TOOLS: end-to-end tests (plan: plan/TOOLS.md)."""
import base64
import hashlib
import hmac
import json
import os
import re
import time
import unicodedata
import zlib

import pytest

from harness.sci import *  # noqa: F401,F403
from tests._util_tools import (  # noqa: F401
    DIGESTS, KINDS, THREE, after_label, by_title, click, controls, digest_of, digest_window, field,
    hash_window, http_answer, http_answer_view, http_json, http_section, http_send, http_server,
    http_set, http_status, http_window, input_view, open_tool, output_views, problem_line, result,
    set_field, set_input, set_state, state, static_texts, text_views, tool_windows, verdict_line,
    verify, wait_result, wait_result_value,
)

ABC = {
    "MD5": "900150983cd24fb0d6963f7d28e17f72",
    "SHA-1": "a9993e364706816aba3e25717850c26c9cd0d89d",
    "SHA-256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    "SHA-512": "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a"
               "2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f",
    "SHA-224": "23097d223405d8228642a477bda255b32aadbce4bda0b3f7e36c9da7",
    "SHA-384": "cb00753f45a35e8bb5a03d699ac65007272c32ab0eded1631a8b605a43ff5bed"
               "8086072ba1e7cc2358baeca134c825a7",
    "SHA3-256": "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532",
    "SHA3-512": "b751850b1a57168a5693cd924b6b096e08f621827444f70d884f5d0240d2712e"
                "10e116e9192af3c91a7ec57647e3934057340b4cf408d5a56592f8274eec53f0",
    "BLAKE2b": "ba80a53f981c4d0d6a2797b69f12f6e94c212f14685ac4b74b12bb6fdbffa2d1"
               "7d87c5392aab792dc252d5de4533cc9518d38aa8dbf1925ab92386edd4009923",
    "CRC-32": "cbf43926",   # of "123456789"
}
HASHLIB = {"MD5": "md5", "SHA-1": "sha1", "SHA-256": "sha256", "SHA-512": "sha512", "SHA-224": "sha224",
           "SHA-384": "sha384", "SHA3-256": "sha3_256", "SHA3-512": "sha3_512", "BLAKE2b": "blake2b"}
IDS = {"MD5": "MD5", "SHA-1": "SHA1", "SHA-256": "SHA256", "SHA-512": "SHA512"}


def pyhash(name, data: bytes) -> str:
    if name == "CRC-32":
        return "%08x" % (zlib.crc32(data) & 0xFFFFFFFF)
    return hashlib.new(HASHLIB[name], data).hexdigest()


def vector_input(name):
    return "123456789" if name == "CRC-32" else "abc"


BCRYPT_VECTOR = "$2a$05$CCCCCCCCCCCCCCCCCCCCC.E5YPO9kmyuRGyh0XouQYb4YMJKvyOeW"
BCRYPT_SALT = "10 41 04 10 41 04 10 41 04 10 41 04 10 41 04 10"


def b64d(s):
    return base64.b64decode(s + "=" * (-len(s) % 4))


def bcrypt_window(app, cost="5", version="2a", salt=BCRYPT_SALT):
    w = hash_window(app, "bcrypt")
    set_state(app, w, "Treat each line as a separate string", False)
    set_state(app, w, "Show the bare key in hexadecimal", False)
    set_field(app, w, "Cost (4-31):", cost)
    set_field(app, w, "Version:", version)
    set_field(app, w, "Salt (hexadecimal):", salt)
    return w


def compute(app, w, text, timeout=30):
    """Sets the input and waits for a fresh result (or a problem)."""
    set_input(app, w, "")
    app.wait(lambda: not result(app, w), 10, "result cleared")
    set_input(app, w, text)
    return wait_result(app, w, timeout)


def base_window(app, name):
    return open_tool(app, f"Tools|Base|{name}…", name)


def base_direction(app, w, direction):
    seg = [c for c in controls(app, w) if c["class"] == "NSSegmentedControl"][0]
    app.act(w, "select", direction, path=seg["path"])


def base_input_kind(app, w, title):
    c = by_title(app, w, title)
    if c is not None:
        app.act(w, "click", path=c["path"])


def base_problem(app, w):
    cs = controls(app, w)
    for i, c in enumerate(cs):
        if c["class"] == "NSTextView" and c.get("editable"):
            nxt = cs[i + 1]
            return nxt.get("value") if nxt["class"] == "NSTextField" and not nxt.get("editable") else None
    return None


def pw_window(app):
    return open_tool(app, "Tools|Password Generator", "Password Generator")


def pw_set(app, w, length=None, count=None, upper=None, lower=None, digits=None, symbols=None,
           symbol_text=None, lookalikes=None, each=None, hash_kind=None):
    if length is not None:
        set_field(app, w, "Length:", str(length))
    if count is not None:
        set_field(app, w, "Number of passwords:", str(count))
    for title, v in (("Uppercase letters (A-Z)", upper), ("Lowercase letters (a-z)", lower), ("Digits (0-9)", digits),
                     ("Symbols:", symbols), ("Leave out characters that look alike (O 0 o I l 1)", lookalikes),
                     ("At least one character of each kind", each)):
        if v is not None:
            set_state(app, w, title, v)
    if symbol_text is not None:
        c = by_title(app, w, "Symbols:")
        cs = controls(app, w)
        i = [k for k, d in enumerate(cs) if d["path"] == c["path"]][0]
        app.act(w, "set_value", symbol_text, path=cs[i + 1]["path"])
    if hash_kind is not None:
        set_field(app, w, "Hash:", hash_kind)


def pw_generate(app, w):
    before = result(app, w)
    click(app, w, "Generate")
    app.idle(0.05)
    return result(app, w)


def pw_entropy(app, w):
    for t in static_texts(app, w):
        if t and (t.startswith("Entropy") or t.startswith("Choose")):
            return t
    return None


@pytest.mark.case("TOOLS-001")
def test_tools_001_the_tools_menu_has_its_items_in_notepad_s_order_plus_the_por(app):
    """TOOLS-001: The Tools menu has its items in Notepad++'s order plus the port's

    Covers: IDM_TOOL_*
    Channel: menu
    Steps: Dump the Tools menu tree (depth 3) with `e2e_menu`; read the state of the twelve IDM_TOOL_* ids.
    Expect: top level is Hashes, Base, Password Generator, HTTP Request, separator, QR Code from Selection, Read QR Code from Clipboard, separator, Install Command Line Tool (9 items); Hashes holds MD5, SHA-1, SHA-256, SHA-512, SHA-224, SHA-384, SHA3-256, SHA3-512, BLAKE2b, CRC-32, separator, bcrypt, scrypt, Argon2, PBKDF2; each of those 14 submenus holds exactly "Generate…", "Generate from files…", "Generate from selection into clipboard"; Base holds "Base64…", "Base58…", "Base32…"; all twelve IDM_TOOL_* items exist and are enabled with an empty document open.
    """
    tree = app.menu_tree("main", 4)
    tools = [t for t in tree if [i.get("title") for i in t.get("items", [])][:2] == ["Hashes", "Base"]]
    assert tools, "no Tools menu"
    items = tools[0]["items"]
    tops = ["-" if i.get("separator") else i["title"] for i in items]
    assert tops == ["Hashes", "Base", "Password Generator", "HTTP Request", "-", "QR Code from Selection",
                    "Read QR Code from Clipboard", "-", "Install Command Line Tool"]
    hashes = items[0]["items"]
    names = ["-" if i.get("separator") else i["title"] for i in hashes]
    assert names == DIGESTS + ["-"] + KINDS
    for sub in hashes:
        if sub.get("separator"):
            continue
        assert [c["title"] for c in sub["items"]] == THREE, sub["title"]
    assert [i["title"] for i in items[1]["items"]] == ["Base64…", "Base58…", "Base32…"]
    ids = [f"IDM_TOOL_{d}_{k}" for d in ("MD5", "SHA1", "SHA256", "SHA512")
           for k in ("GENERATE", "GENERATEFROMFILE", "GENERATEINTOCLIPBOARD")]
    state_ = app.menu(*ids)
    for i in ids:
        assert state_[i] is not None and state_[i]["enabled"], i


@pytest.mark.case("TOOLS-002")
def test_tools_002_notepad_s_command_ids_reach_their_own_digest_s_items_and_no(app):
    """TOOLS-002: Notepad++'s command ids reach their own digest's items and no other

    Covers: IDM_TOOL_*
    Channel: mcp, ui
    Steps: For each of the twelve IDM_TOOL_* ids read its label/menu with `list_commands` (query "IDM_TOOL"); run the four *_GENERATE ids one after the other and read the digest window's title; `list_commands` with query "SHA-224" and "BLAKE2b".
    Expect: the labels are "Generate…", "Generate from files…", "Generate from selection into clipboard" under the menus MD5, SHA-1, SHA-256, SHA-512 (ids 48501-48512 as upstream); IDM_TOOL_MD5_GENERATE opens a window titled "Generate MD5 digest", SHA1 "Generate SHA-1 digest", SHA256 "Generate SHA-256 digest", SHA512 "Generate SHA-512 digest"; no IDM_* command is listed for SHA-224 or BLAKE2b items.
    """
    cmds = app.call("list_commands", query="IDM_TOOL", limit=100)["commands"]
    by = {c["name"]: c for c in cmds}
    number = 48501
    for d in ("MD5", "SHA256", "SHA1", "SHA512"):   # upstream's numbering order
        for k, label in zip(("GENERATE", "GENERATEFROMFILE", "GENERATEINTOCLIPBOARD"),
                            ("Generate...", "Generate from files...", "Generate from selection into clipboard")):
            c = by[f"IDM_TOOL_{d}_{k}"]
            assert c["id"] == number, c
            assert c["label"].replace("…", "...") == label, c
            number += 1
    for name, d in IDS.items():
        app.run(f"IDM_TOOL_{d}_GENERATE")
        app.wait(lambda: any(w["title"] == f"Generate {name} digest" for w in tool_windows(app)), 5, name)
    for q in ("SHA-224", "BLAKE2b"):
        found = app.call("list_commands", query=q)["commands"]
        assert not [c for c in found if c["name"].startswith("IDM_")], found


@pytest.mark.case("TOOLS-003")
def test_tools_003_tool_windows_are_non_modal_singletons_that_leave_the_editor(app):
    """TOOLS-003: Tool windows are non-modal singletons that leave the editor usable

    Covers: IDM_TOOL_SHA256_GENERATE, IDM_TOOL_MD5_GENERATE
    Channel: ui, keys, mcp
    Steps: Run IDM_TOOL_SHA256_GENERATE twice, then IDM_TOOL_MD5_GENERATE; list windows. With the digest window open, change the document with `edit_document` and type into the editor after focusing the main window. Close the window with its Close button; reopen it and close it with Escape.
    Expect: after the three commands exactly one digest window exists (the same window number), now titled "Generate MD5 digest"; it is an NSPanel, not modal, and not a sheet; the document edit and the typed text land in the editor; Close and Escape each hide the window; no alert is logged.
    """
    app.new("start")
    app.run("IDM_TOOL_SHA256_GENERATE")
    first = app.wait(lambda: [w for w in tool_windows(app)], 5)
    app.run("IDM_TOOL_SHA256_GENERATE")
    app.run("IDM_TOOL_MD5_GENERATE")
    ws = tool_windows(app)
    assert len(ws) == 1 and ws[0]["number"] == first[0]["number"]
    w = ws[0]
    assert w["title"] == "Generate MD5 digest"
    assert w["class"] == "NSPanel" and not w["modal"] and not w.get("sheet")
    app.set_text("edited")
    app.select(1, 7)
    app.type("!", window="main")
    assert app.text() == "edited!"
    click(app, w["number"], "Close")
    app.wait(lambda: not tool_windows(app), 5, "closed")
    app.run("IDM_TOOL_MD5_GENERATE")
    w = app.wait(lambda: tool_windows(app), 5)[0]["number"]
    app.keys("escape", window=w)
    app.wait(lambda: not tool_windows(app), 5, "closed by escape")
    assert not [e for e in app.modal_log() if e["kind"] == "alert"]


@pytest.mark.case("TOOLS-004")
def test_tools_004_every_kind_of_tools_window_can_be_open_at_once_each_under_it(app):
    """TOOLS-004: Every kind of Tools window can be open at once, each under its own title

    Covers: IDM_TOOL_SHA512_GENERATE
    Channel: ui
    Steps: Open IDM_TOOL_SHA512_GENERATE, Tools|Hashes|Argon2|Generate…, Tools|Base|Base58…, Tools|Password Generator and Tools|HTTP Request; list the visible windows; close the Base58 window with `close_window`.
    Expect: five distinct visible panels titled "Generate SHA-512 digest", "Generate Argon2 digest", "Base58", "Password Generator", "HTTP Request", none modal; after closing Base58 the four others are still visible and the main window is still the main window.
    """
    expected = []
    app.run("IDM_TOOL_SHA512_GENERATE"); expected.append("Generate SHA-512 digest")
    app.run("Tools|Hashes|Argon2|Generate…"); expected.append("Generate Argon2 digest")
    app.run("Tools|Base|Base58…"); expected.append("Base58")
    app.run("Tools|Password Generator"); expected.append("Password Generator")
    app.run("Tools|HTTP Request"); expected.append("HTTP Request")
    ws = app.wait(lambda: len(tool_windows(app)) == 5 and tool_windows(app), 5)
    assert sorted(w["title"] for w in ws) == sorted(expected)
    assert len({w["number"] for w in ws}) == 5 and not any(w["modal"] for w in ws)
    base58 = [w for w in ws if w["title"] == "Base58"][0]
    app.close_window(base58["number"])
    rest = tool_windows(app)
    assert sorted(w["title"] for w in rest) == sorted(t for t in expected if t != "Base58")
    assert [w for w in app.windows() if w["main_window"]]


@pytest.mark.case("TOOLS-005")
def test_tools_005_md5_generate_gives_rfc_1321_s_test_vectors_as_the_text_is_se(app):
    """TOOLS-005: MD5 Generate… gives RFC 1321's test vectors as the text is set

    Covers: IDM_TOOL_MD5_GENERATE
    Channel: ui
    Steps: Run IDM_TOOL_MD5_GENERATE; with "Treat each line…" unticked and no HMAC key, set the input text view to each of "a", "abc", "message digest", "The quick brown fox jumps over the lazy dog", and read the result view after each.
    Expect: results are 0cc175b9c0f1b6a831c399e269772661, 900150983cd24fb0d6963f7d28e17f72, f96b697d7cb7938d525a2f31aaf161d0, 9e107d9d372bb6826bd81d3542a419d6; the result is lowercase hex, 32 characters, with no trailing newline.
    """
    app.run("IDM_TOOL_MD5_GENERATE")
    w = app.wait(lambda: tool_windows(app), 5)[0]["number"]
    set_field(app, w, "HMAC key (optional):", "")
    for text, want in (("a", "0cc175b9c0f1b6a831c399e269772661"), ("abc", ABC["MD5"]),
                       ("message digest", "f96b697d7cb7938d525a2f31aaf161d0"),
                       ("The quick brown fox jumps over the lazy dog", "9e107d9d372bb6826bd81d3542a419d6")):
        assert digest_of(app, w, text) == want


@pytest.mark.case("TOOLS-006")
def test_tools_006_sha_1_generate_gives_fips_180_s_vectors(app):
    """TOOLS-006: SHA-1 Generate… gives FIPS 180's vectors

    Covers: IDM_TOOL_SHA1_GENERATE
    Channel: ui
    Steps: Run IDM_TOOL_SHA1_GENERATE; set the input to "abc", then to "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq".
    Expect: a9993e364706816aba3e25717850c26c9cd0d89d, then 84983e441c3bd26ebaae4aa1f95129e5e54670f1; the window title is "Generate SHA-1 digest".
    """
    app.run("IDM_TOOL_SHA1_GENERATE")
    w = app.wait(lambda: tool_windows(app), 5)[0]
    assert w["title"] == "Generate SHA-1 digest"
    w = w["number"]
    set_field(app, w, "HMAC key (optional):", "")
    assert digest_of(app, w, "abc") == ABC["SHA-1"]
    assert digest_of(app, w, "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq") == \
        "84983e441c3bd26ebaae4aa1f95129e5e54670f1"


@pytest.mark.case("TOOLS-007")
def test_tools_007_sha_256_generate_gives_fips_180_s_vectors(app):
    """TOOLS-007: SHA-256 Generate… gives FIPS 180's vectors

    Covers: IDM_TOOL_SHA256_GENERATE
    Channel: ui
    Steps: Run IDM_TOOL_SHA256_GENERATE; set the input to "abc", then to "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq".
    Expect: ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad, then 248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1.
    """
    app.run("IDM_TOOL_SHA256_GENERATE")
    w = app.wait(lambda: tool_windows(app), 5)[0]["number"]
    set_field(app, w, "HMAC key (optional):", "")
    assert digest_of(app, w, "abc") == ABC["SHA-256"]
    assert digest_of(app, w, "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq") == \
        "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1"


@pytest.mark.case("TOOLS-008")
def test_tools_008_sha_512_generate_gives_fips_180_s_vectors(app):
    """TOOLS-008: SHA-512 Generate… gives FIPS 180's vectors

    Covers: IDM_TOOL_SHA512_GENERATE
    Channel: ui
    Steps: Run IDM_TOOL_SHA512_GENERATE; set the input to "abc", then to the 896-bit message "abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu".
    Expect: ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f, then 8e959b75dae313da8cf4f72814fc143f8f7779c6eb9f7fa17299aeadb6889018501d289e4900f7e4331b99dec4b5433ac7d329eeb6dd26545e96e55b874be909.
    """
    app.run("IDM_TOOL_SHA512_GENERATE")
    w = app.wait(lambda: tool_windows(app), 5)[0]["number"]
    set_field(app, w, "HMAC key (optional):", "")
    assert digest_of(app, w, "abc") == ABC["SHA-512"]
    msg = ("abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmno"
           "ijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu")
    assert digest_of(app, w, msg) == ("8e959b75dae313da8cf4f72814fc143f8f7779c6eb9f7fa17299aeadb6889018"
                                      "501d289e4900f7e4331b99dec4b5433ac7d329eeb6dd26545e96e55b874be909")


@pytest.mark.case("TOOLS-009")
def test_tools_009_the_port_s_six_digests_give_their_published_vectors_in_the_s(app):
    """TOOLS-009: The port's six digests give their published vectors in the same window

    Covers: -
    Channel: ui
    Steps: For each of SHA-224, SHA-384, SHA3-256, SHA3-512, BLAKE2b, CRC-32: run `Tools|Hashes|<name>|Generate…`, set the input to "abc" (CRC-32: "123456789"), read title and result; for SHA3-256 also set 200 × "a".
    Expect: titles "Generate <name> digest"; SHA-224 23097d223405d8228642a477bda255b32aadbce4bda0b3f7e36c9da7; SHA-384 cb00753f45a35e8bb5a03d699ac65007272c32ab0eded1631a8b605a43ff5bed8086072ba1e7cc2358baeca134c825a7; SHA3-256 3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532; SHA3-512 b751850b1a57168a5693cd924b6b096e08f621827444f70d884f5d0240d2712e10e116e9192af3c91a7ec57647e3934057340b4cf408d5a56592f8274eec53f0; BLAKE2b (512-bit) ba80a53f981c4d0d6a2797b69f12f6e94c212f14685ac4b74b12bb6fdbffa2d17d87c5392aab792dc252d5de4533cc9518d38aa8dbf1925ab92386edd4009923; CRC-32 cbf43926 (8 hex digits); SHA3-256 of 200 "a" cce34485baf2bf2aca99b94833892a4f52896d3d153f7b840cc4f9fe695f1387.
    """
    for name in ("SHA-224", "SHA-384", "SHA3-256", "SHA3-512", "BLAKE2b", "CRC-32"):
        w = digest_window(app, name)
        assert digest_of(app, w, vector_input(name)) == ABC[name], name
    w = digest_window(app, "SHA3-256")
    assert digest_of(app, w, "a" * 200) == "cce34485baf2bf2aca99b94833892a4f52896d3d153f7b840cc4f9fe695f1387"


@pytest.mark.case("TOOLS-010")
def test_tools_010_a_unicode_text_is_hashed_as_its_utf_8_bytes(app):
    """TOOLS-010: A Unicode text is hashed as its UTF-8 bytes

    Covers: IDM_TOOL_SHA256_GENERATE, IDM_TOOL_MD5_GENERATE
    Channel: ui
    Steps: For MD5 and SHA-256 Generate…, set the input to "Привет, 世界 😀 é" (é precomposed) and read the result; compute the digest of the same string's UTF-8 bytes with hashlib.
    Expect: each result equals hashlib's hex digest of `text.encode("utf-8")`.
    """
    text = "Привет, 世界 😀 é"
    for name in ("MD5", "SHA-256"):
        w = digest_window(app, name)
        set_field(app, w, "HMAC key (optional):", "")
        assert digest_of(app, w, text) == pyhash(name, text.encode("utf-8")), name


@pytest.mark.case("TOOLS-011")
def test_tools_011_the_digest_follows_the_text_as_it_is_typed_and_empties_with(app):
    """TOOLS-011: The digest follows the text as it is typed and empties with it

    Covers: IDM_TOOL_SHA1_GENERATE
    Channel: ui, keys
    Steps: Run IDM_TOOL_SHA1_GENERATE, focus the input view, type "ab" then "c" with `e2e_keys` text, reading the result after each; then select all in the input and delete it with keys.
    Expect: after "ab" the result is SHA-1("ab") = da23614e02469a0d7c7bd1bdab5c9c474b1904dc; after "c" it is a9993e364706816aba3e25717850c26c9cd0d89d; with the input emptied the result is empty (no digest of the empty string is shown).
    """
    app.run("IDM_TOOL_SHA1_GENERATE")
    w = app.wait(lambda: tool_windows(app), 5)[0]["number"]
    set_state(app, w, "Treat each line as a separate string", False)
    set_field(app, w, "HMAC key (optional):", "")
    set_input(app, w, "")
    app.act(w, "focus", path=input_view(app, w)["path"])
    app.type("ab", window=w)
    app.wait(lambda: result(app, w) == "da23614e02469a0d7c7bd1bdab5c9c474b1904dc", 5, "digest of ab")
    app.type("c", window=w)
    app.wait(lambda: result(app, w) == ABC["SHA-1"], 5, "digest of abc")
    app.keys("cmd+a", "delete", window=w)
    app.wait(lambda: input_view(app, w)["value"] == "", 5, "input emptied")
    assert result(app, w) == ""


@pytest.mark.case("TOOLS-012")
def test_tools_012_treat_each_line_as_a_separate_string_gives_a_digest_per_line(app):
    """TOOLS-012: "Treat each line as a separate string" gives a digest per line

    Covers: IDM_TOOL_MD5_GENERATE
    Channel: ui
    Steps: In MD5 Generate…, tick "Treat each line as a separate string" and set the input to "abc\\n\\nx"; then to "abc\\nx\\n"; then untick it with the input "abc".
    Expect: first result is "900150983cd24fb0d6963f7d28e17f72\\n\\n9dd4e461268c8034f5c8564e155c67a6" (empty line kept empty); the second has two lines only (no digest for the empty tail after the last newline); unticked, the result is the single digest 900150983cd24fb0d6963f7d28e17f72.
    """
    w = digest_window(app, "MD5")
    set_field(app, w, "HMAC key (optional):", "")
    x = "9dd4e461268c8034f5c8564e155c67a6"
    assert digest_of(app, w, "abc\n\nx", each_line=True) == f"{ABC['MD5']}\n\n{x}"
    assert digest_of(app, w, "abc\nx\n", each_line=True) == f"{ABC['MD5']}\n{x}"
    assert digest_of(app, w, "abc", each_line=False) == ABC["MD5"]


@pytest.mark.case("TOOLS-013")
def test_tools_013_an_hmac_key_turns_the_six_commoncrypto_digests_into_hmacs(app):
    """TOOLS-013: An HMAC key turns the six CommonCrypto digests into HMACs

    Covers: IDM_TOOL_MD5_GENERATE, IDM_TOOL_SHA1_GENERATE, IDM_TOOL_SHA256_GENERATE, IDM_TOOL_SHA512_GENERATE
    Channel: ui
    Steps: For each of MD5, SHA-1, SHA-256, SHA-512, SHA-224, SHA-384 Generate…: set the input to "The quick brown fox jumps over the lazy dog" and the "HMAC key (optional):" field to "key"; then tick each-line with input "a\\nb"; then clear the key.
    Expect: the HMAC row is visible; results equal Python `hmac.new(b"key", msg, <alg>).hexdigest()` (SHA-256 gives f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8, MD5 80070713463e7749b90c2dc24911e275); with each-line the two lines are the HMACs of "a" and "b"; with the key cleared the result is the plain digest again.
    """
    msg = "The quick brown fox jumps over the lazy dog"
    algs = {"MD5": "md5", "SHA-1": "sha1", "SHA-256": "sha256", "SHA-512": "sha512", "SHA-224": "sha224", "SHA-384": "sha384"}
    for name, alg in algs.items():
        w = digest_window(app, name)
        assert by_title(app, w, "Treat each line as a separate string")
        assert "HMAC key (optional):" in static_texts(app, w), name
        got = digest_of(app, w, msg, each_line=False, key="key")
        assert got == hmac.new(b"key", msg.encode(), alg).hexdigest(), name
        per = digest_of(app, w, "a\nb", each_line=True, key="key")
        assert per == "\n".join(hmac.new(b"key", t, alg).hexdigest() for t in (b"a", b"b")), name
        plain = digest_of(app, w, msg, each_line=False, key="")
        assert plain == hashlib.new(alg, msg.encode()).hexdigest(), name
    w = digest_window(app, "SHA-256")
    assert digest_of(app, w, msg, key="key") == "f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8"
    w = digest_window(app, "MD5")
    assert digest_of(app, w, msg, key="key") == "80070713463e7749b90c2dc24911e275"
    set_field(app, w, "HMAC key (optional):", "")


@pytest.mark.case("TOOLS-014")
def test_tools_014_the_hmac_row_is_hidden_where_there_is_no_hmac(app):
    """TOOLS-014: The HMAC row is hidden where there is no HMAC

    Covers: IDM_TOOL_SHA256_GENERATEFROMFILE
    Channel: ui
    Steps: Open Generate… for SHA3-256, SHA3-512, BLAKE2b and CRC-32, then IDM_TOOL_SHA256_GENERATEFROMFILE; list the controls of the window each time.
    Expect: no control titled "HMAC key (optional):" is visible in any of these, and none of them has an editable single-line key field; SHA3-256 of "abc" is still the plain vector.
    """
    for name in ("SHA3-256", "SHA3-512", "BLAKE2b", "CRC-32"):
        w = digest_window(app, name)
        assert "HMAC key (optional):" not in static_texts(app, w), name
        assert not [c for c in controls(app, w) if c["class"] == "NSTextField" and c.get("editable")], name
    w = digest_window(app, "SHA3-256")
    assert digest_of(app, w, "abc") == ABC["SHA3-256"]
    app.run("IDM_TOOL_SHA256_GENERATEFROMFILE")
    w = app.wait(lambda: [x for x in tool_windows(app) if x["title"] == "Generate SHA-256 digest from files"], 5)[0]["number"]
    assert "HMAC key (optional):" not in static_texts(app, w)


@pytest.mark.case("TOOLS-015")
def test_tools_015_copy_to_clipboard_takes_the_result_exactly(app):
    """TOOLS-015: Copy to Clipboard takes the result exactly

    Covers: IDM_TOOL_SHA512_GENERATE
    Channel: ui, clipboard
    Steps: In SHA-512 Generate… with each-line ticked set the input to "abc\\ndef"; click "Copy to Clipboard"; read the clipboard.
    Expect: the clipboard text equals the result view's text (two 128-hex-digit lines joined by "\\n", no trailing newline); the document is unchanged.
    """
    app.new("doc")
    w = digest_window(app, "SHA-512")
    set_field(app, w, "HMAC key (optional):", "")
    r = digest_of(app, w, "abc\ndef", each_line=True)
    lines = r.split("\n")
    assert len(lines) == 2 and all(len(l) == 128 for l in lines) and not r.endswith("\n")
    click(app, w, "Copy to Clipboard")
    assert app.clipboard() == r
    assert app.text() == "doc"
    set_state(app, w, "Treat each line as a separate string", False)


@pytest.mark.case("TOOLS-016")
def test_tools_016_the_digest_window_keeps_its_input_when_switched_to_another_d(app):
    """TOOLS-016: The digest window keeps its input when switched to another digest

    Covers: IDM_TOOL_SHA256_GENERATE
    Channel: ui
    Steps: Run IDM_TOOL_SHA256_GENERATE, set input "abc"; run `Tools|Hashes|SHA3-256|Generate…` without closing.
    Expect: the same window is retitled "Generate SHA3-256 digest"; its input still reads "abc" and its result is 3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532.
    """
    app.run("IDM_TOOL_SHA256_GENERATE")
    w = app.wait(lambda: tool_windows(app), 5)[0]["number"]
    set_field(app, w, "HMAC key (optional):", "")
    digest_of(app, w, "abc")
    app.run("Tools|Hashes|SHA3-256|Generate…")
    ws = tool_windows(app)
    assert len(ws) == 1 and ws[0]["number"] == w and ws[0]["title"] == "Generate SHA3-256 digest"
    assert input_view(app, w)["value"] == "abc"
    assert result(app, w) == ABC["SHA3-256"]


@pytest.mark.case("TOOLS-017")
def test_tools_017_md5_generate_from_files_lists_digest_name_for_each_chosen_fi(app, tmp):
    """TOOLS-017: MD5 Generate from files… lists "digest  name" for each chosen file

    Covers: IDM_TOOL_MD5_GENERATEFROMFILE
    Channel: ui, modal, files
    Steps: Write `a.txt` = "abc" and `b.txt` = "message digest" in `tmp`; run IDM_TOOL_MD5_GENERATEFROMFILE; queue an open-panel answer with both paths; click "Choose files to generate MD5...".
    Expect: the window is titled "Generate MD5 digest from files"; no input view and no each-line box are visible; the result is "900150983cd24fb0d6963f7d28e17f72  a.txt\\nf96b697d7cb7938d525a2f31aaf161d0  b.txt" (two spaces, file name only, in the chosen order); the modal log shows one open panel answered with the two paths.
    """
    (tmp / "a.txt").write_text("abc")
    (tmp / "b.txt").write_text("message digest")
    app.run("IDM_TOOL_MD5_GENERATEFROMFILE")
    w = app.wait(lambda: [x for x in tool_windows(app) if x["title"] == "Generate MD5 digest from files"], 5)[0]["number"]
    assert not [c for c in text_views(app, w) if c.get("editable")]
    assert by_title(app, w, "Treat each line as a separate string") is None
    app.answers(panels=[[str(tmp / "a.txt"), str(tmp / "b.txt")]])
    click(app, w, "Choose files to generate MD5...")
    app.wait(lambda: result(app, w), 5, "file digests")
    assert result(app, w) == ("900150983cd24fb0d6963f7d28e17f72  a.txt\n"
                              "f96b697d7cb7938d525a2f31aaf161d0  b.txt")
    log = [e for e in app.modal_log() if e["kind"] == "open"]
    assert len(log) == 1 and len(log[0]["answered"]) == 2


@pytest.mark.case("TOOLS-018")
def test_tools_018_sha_1_sha_256_and_sha_512_generate_from_files_hash_the_file(app, tmp):
    """TOOLS-018: SHA-1, SHA-256 and SHA-512 Generate from files… hash the file bytes

    Covers: IDM_TOOL_SHA1_GENERATEFROMFILE, IDM_TOOL_SHA256_GENERATEFROMFILE, IDM_TOOL_SHA512_GENERATEFROMFILE
    Channel: ui, modal, files
    Steps: For each of the three ids: write a file with 256 bytes 0x00..0xFF and a UTF-8 file "Привет\\r\\n"; run the command, queue both paths, click the Choose button (its title "Choose files to generate SHA-1..." etc.).
    Expect: each line's digest equals hashlib's digest of the file's bytes (CRLF and binary bytes included, no text conversion); the button title names the digest; the title is "Generate <name> digest from files".
    """
    binary = tmp / "bytes.bin"
    binary.write_bytes(bytes(range(256)))
    cyr = tmp / "cyr.txt"
    cyr.write_bytes("Привет\r\n".encode("utf-8"))
    for name, d in (("SHA-1", "SHA1"), ("SHA-256", "SHA256"), ("SHA-512", "SHA512")):
        app.run(f"IDM_TOOL_{d}_GENERATEFROMFILE")
        title = f"Generate {name} digest from files"
        w = app.wait(lambda: [x for x in tool_windows(app) if x["title"] == title], 5)[0]["number"]
        app.answers(panels=[[str(binary), str(cyr)]])
        click(app, w, f"Choose files to generate {name}...")
        want = (f"{pyhash(name, bytes(range(256)))}  bytes.bin\n"
                f"{pyhash(name, cyr.read_bytes())}  cyr.txt")
        app.wait(lambda: result(app, w) == want, 5, f"{name} file digests")


@pytest.mark.case("TOOLS-019")
def test_tools_019_from_files_an_empty_file_a_unicode_name_and_a_large_file(app, tmp):
    """TOOLS-019: From files: an empty file, a Unicode name and a large file

    Covers: IDM_TOOL_SHA256_GENERATEFROMFILE
    Channel: ui, modal, files
    Steps: Write an empty file `empty.txt`, a file named `отчёт 1.txt` with "x", and a 20 MB file of pseudo-random bytes; choose all three in SHA-256 from files.
    Expect: the empty file's line starts with e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855; the second line ends with "  отчёт 1.txt"; the large file's digest equals hashlib's; the result appears within 10 s.
    """
    (tmp / "empty.txt").write_bytes(b"")
    (tmp / "отчёт 1.txt").write_text("x")
    big = os.urandom(20 * 1024 * 1024)
    (tmp / "big.bin").write_bytes(big)
    w = digest_window(app, "SHA-256", files=True)
    app.answers(panels=[[str(tmp / "empty.txt"), str(tmp / "отчёт 1.txt"), str(tmp / "big.bin")]])
    click(app, w, "Choose files to generate SHA-256...")
    lines = app.wait(lambda: (result(app, w) or "").count("\n") == 2 and result(app, w).split("\n"), 10, "3 lines")
    # the file system hands names back decomposed (NFD); compare the characters, not their form
    lines = [unicodedata.normalize("NFC", l) for l in lines]
    assert lines[0] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  empty.txt"
    assert lines[1] == f"{hashlib.sha256(b'x').hexdigest()}  отчёт 1.txt"
    assert lines[2] == f"{hashlib.sha256(big).hexdigest()}  big.bin"


@pytest.mark.case("TOOLS-020")
def test_tools_020_cancelling_the_file_choice_changes_nothing(app, tmp):
    """TOOLS-020: Cancelling the file choice changes nothing

    Covers: IDM_TOOL_SHA1_GENERATEFROMFILE
    Channel: ui, modal
    Steps: In SHA-1 from files, choose one file (queued) so a line is shown; then queue a cancel (None) and click the Choose button again.
    Expect: the result still shows the first line unchanged; no alert is logged; the modal log shows the second panel cancelled.
    """
    (tmp / "a.txt").write_text("abc")
    app.run("IDM_TOOL_SHA1_GENERATEFROMFILE")
    w = app.wait(lambda: [x for x in tool_windows(app) if x["title"] == "Generate SHA-1 digest from files"], 5)[0]["number"]
    app.answers(panels=[str(tmp / "a.txt")])
    click(app, w, "Choose files to generate SHA-1...")
    line = app.wait(lambda: result(app, w), 5)
    assert line == f"{ABC['SHA-1']}  a.txt"
    app.modal_log()
    app.answers(panels=[None])
    click(app, w, "Choose files to generate SHA-1...")
    app.idle(0.2)
    assert result(app, w) == line
    log = app.modal_log()
    assert [e for e in log if e["kind"] == "open"] and not [e for e in log if e["kind"] == "alert"]


@pytest.mark.case("TOOLS-021")
def test_tools_021_the_port_s_digests_from_files_crc_32_and_sha3_512(app, tmp):
    """TOOLS-021: The port's digests from files: CRC-32 and SHA3-512

    Covers: -
    Channel: ui, modal, files
    Steps: Write `a.txt` = "abc", `b.txt` = "123456789"; run `Tools|Hashes|CRC-32|Generate from files…`, choose both; then `Tools|Hashes|SHA3-512|Generate from files…`, choose `a.txt`.
    Expect: CRC-32 result is "352441c2  a.txt\\ncbf43926  b.txt"; SHA3-512 result is the "abc" vector followed by "  a.txt"; titles "Generate CRC-32 digest from files" / "Generate SHA3-512 digest from files".
    """
    (tmp / "a.txt").write_text("abc")
    (tmp / "b.txt").write_text("123456789")
    w = digest_window(app, "CRC-32", files=True)
    app.answers(panels=[[str(tmp / "a.txt"), str(tmp / "b.txt")]])
    click(app, w, "Choose files to generate CRC-32...")
    app.wait(lambda: result(app, w) == "352441c2  a.txt\ncbf43926  b.txt", 5, "crc lines")
    w = digest_window(app, "SHA3-512", files=True)
    app.answers(panels=[[str(tmp / "a.txt")]])
    click(app, w, "Choose files to generate SHA3-512...")
    app.wait(lambda: result(app, w) == f"{ABC['SHA3-512']}  a.txt", 5, "sha3 line")


@pytest.mark.case("TOOLS-022")
def test_tools_022_copy_to_clipboard_in_from_files_mode_takes_every_line(app, tmp):
    """TOOLS-022: Copy to Clipboard in from-files mode takes every line

    Covers: IDM_TOOL_MD5_GENERATEFROMFILE
    Channel: ui, clipboard, modal
    Steps: Choose two files in MD5 from files; click "Copy to Clipboard".
    Expect: the clipboard text equals the two-line result exactly.
    """
    (tmp / "a.txt").write_text("abc")
    (tmp / "b.txt").write_text("a")
    w = digest_window(app, "MD5", files=True)
    app.answers(panels=[[str(tmp / "a.txt"), str(tmp / "b.txt")]])
    click(app, w, "Choose files to generate MD5...")
    r = app.wait(lambda: (result(app, w) or "").count("\n") == 1 and result(app, w), 5)
    click(app, w, "Copy to Clipboard")
    assert app.clipboard() == r


@pytest.mark.case("TOOLS-023")
def test_tools_023_the_four_notepad_digests_of_the_selection_go_to_the_clipboar(app):
    """TOOLS-023: The four Notepad++ digests of the selection go to the clipboard

    Covers: IDM_TOOL_MD5_GENERATEINTOCLIPBOARD, IDM_TOOL_SHA1_GENERATEINTOCLIPBOARD, IDM_TOOL_SHA256_GENERATEINTOCLIPBOARD, IDM_TOOL_SHA512_GENERATEINTOCLIPBOARD
    Channel: mcp, clipboard
    Steps: New document "xabcx"; select columns 2-4 ("abc"); for each of the four ids set the clipboard to "" and run the command.
    Expect: the clipboard holds exactly the "abc" vector of that digest (lowercase hex, no newline); the document text and selection are unchanged; no window opens.
    """
    app.new("xabcx")
    for name, d in IDS.items():
        app.select(1, 2, 1, 5)
        app.clipboard(set="")
        app.run(f"IDM_TOOL_{d}_GENERATEINTOCLIPBOARD")
        assert app.clipboard() == ABC[name], name
        assert app.text() == "xabcx"
        assert app.selection()["text"] == "abc"
    assert not tool_windows(app)


@pytest.mark.case("TOOLS-024")
def test_tools_024_with_nothing_selected_the_whole_document_is_hashed(app):
    """TOOLS-024: With nothing selected the whole document is hashed

    Covers: IDM_TOOL_MD5_GENERATEINTOCLIPBOARD, IDM_TOOL_SHA256_GENERATEINTOCLIPBOARD
    Channel: mcp, clipboard
    Steps: New document "abc" with the caret at the end and no selection; run IDM_TOOL_MD5_GENERATEINTOCLIPBOARD; then empty the document and run IDM_TOOL_SHA256_GENERATEINTOCLIPBOARD.
    Expect: first clipboard is 900150983cd24fb0d6963f7d28e17f72 (the port hashes the document when nothing is selected); for the empty document the clipboard is e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 (SHA-256 of nothing).
    """
    app.new("abc")
    app.select(1, 4)
    app.run("IDM_TOOL_MD5_GENERATEINTOCLIPBOARD")
    assert app.clipboard() == ABC["MD5"]
    app.set_text("")
    app.clipboard(set="x")
    app.run("IDM_TOOL_SHA256_GENERATEINTOCLIPBOARD")
    assert app.clipboard() == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@pytest.mark.case("TOOLS-025")
def test_tools_025_a_unicode_selection_in_a_non_utf_8_file_is_hashed_as_utf_8(app, tmp):
    """TOOLS-025: A Unicode selection in a non-UTF-8 file is hashed as UTF-8

    Covers: IDM_TOOL_SHA1_GENERATEINTOCLIPBOARD
    Channel: mcp, clipboard, files
    Steps: Write a Windows-1251 file containing "Привет мир" (bytes cp1251), open it (the app detects/labels 1251), select "Привет"; run IDM_TOOL_SHA1_GENERATEINTOCLIPBOARD.
    Expect: the clipboard equals hashlib.sha1("Привет".encode("utf-8")) (Notepad++ hashes its UTF-8 buffer, not the file's bytes).
    """
    p = tmp / "cp1251.txt"
    p.write_bytes("Привет мир, это проверка кодировки windows-1251".encode("cp1251"))
    app.open(p)
    if not app.text().startswith("Привет"):
        app.run("IDM_FORMAT_WIN_1251")
    assert app.text().startswith("Привет"), app.doc()
    app.select(1, 1, 1, 7)
    assert app.selection()["text"] == "Привет"
    app.run("IDM_TOOL_SHA1_GENERATEINTOCLIPBOARD")
    assert app.clipboard() == hashlib.sha1("Привет".encode("utf-8")).hexdigest()


@pytest.mark.case("TOOLS-026")
def test_tools_026_a_selection_spanning_crlf_lines_includes_the_line_ends(app):
    """TOOLS-026: A selection spanning CRLF lines includes the line ends

    Covers: IDM_TOOL_MD5_GENERATEINTOCLIPBOARD
    Channel: mcp, clipboard
    Steps: New document "one\\r\\ntwo" with CRLF line ends (set EOL with IDM_FORMAT_TODOS if needed); select all; run IDM_TOOL_MD5_GENERATEINTOCLIPBOARD.
    Expect: the clipboard equals md5(b"one\\r\\ntwo").
    """
    app.new("one\r\ntwo")
    assert app.text() == "one\r\ntwo"
    app.select_all()
    app.run("IDM_TOOL_MD5_GENERATEINTOCLIPBOARD")
    assert app.clipboard() == hashlib.md5(b"one\r\ntwo").hexdigest()


@pytest.mark.case("TOOLS-027")
def test_tools_027_the_port_s_six_digests_into_the_clipboard(app):
    """TOOLS-027: The port's six digests into the clipboard

    Covers: -
    Channel: mcp, clipboard
    Steps: For each of SHA-224, SHA-384, SHA3-256, SHA3-512, BLAKE2b, CRC-32: document "abc" (CRC-32: "123456789") selected; run `Tools|Hashes|<name>|Generate from selection into clipboard`.
    Expect: the clipboard holds the vector listed in TOOLS-009 for that digest.
    """
    for name in ("SHA-224", "SHA-384", "SHA3-256", "SHA3-512", "BLAKE2b", "CRC-32"):
        app.new(vector_input(name))
        app.select_all()
        app.clipboard(set="")
        app.run(f"Tools|Hashes|{name}|Generate from selection into clipboard")
        assert app.clipboard() == ABC[name], name


@pytest.mark.case("TOOLS-028")
def test_tools_028_each_password_hash_window_shows_only_its_own_settings_with_i(app):
    """TOOLS-028: Each password-hash window shows only its own settings, with its defaults

    Covers: -
    Channel: ui
    Steps: Open `Tools|Hashes|<kind>|Generate…` for bcrypt, scrypt, Argon2 and PBKDF2; list visible controls each time.
    Expect: titles "Generate <kind> digest"; bcrypt shows "Cost (4-31):" = 12 and "Version:" popup [2b, 2a, 2y] with 2b; scrypt shows "N, as a power of 2:" = 15, "Block size (r):" = 8, "Parallelism (p):" = 1, "Hash length (bytes):" = 32; Argon2 shows "Variant:" [Argon2id, Argon2i, Argon2d], "Memory (KiB):" 19456, "Iterations:" 2, "Parallelism:" 1, hash length 32; PBKDF2 shows "Digest:" [SHA-256, SHA-512, SHA-1], "Iterations:" 600000, hash length 32; every kind has "Salt (hexadecimal):" with placeholder "Empty: a random salt each time", Random, the input, each-line box, "Show the bare key in hexadecimal", the result, the "Hash to check the password against:" field with Verify, Copy to Clipboard and Close; no kind shows another kind's fields.
    """
    own = {
        "bcrypt": {"Cost (4-31):": "12", "Version:": "2b"},
        "scrypt": {"N, as a power of 2:": "15", "Block size (r):": "8", "Parallelism (p):": "1", "Hash length (bytes):": "32"},
        "Argon2": {"Variant:": "Argon2id", "Memory (KiB):": "19456", "Iterations:": "2", "Parallelism:": "1", "Hash length (bytes):": "32"},
        "PBKDF2": {"Digest:": "SHA-256", "Iterations:": "600000", "Hash length (bytes):": "32"},
    }
    items = {"Version:": ["2b", "2a", "2y"], "Variant:": ["Argon2id", "Argon2i", "Argon2d"], "Digest:": ["SHA-256", "SHA-512", "SHA-1"]}
    all_labels = set(l for d in own.values() for l in d)
    for kind in KINDS:
        w = hash_window(app, kind)
        labels = static_texts(app, w)
        for label, value in own[kind].items():
            assert label in labels, (kind, label)
            c = after_label(app, w, label)
            assert c.get("value") == value, (kind, label, c)
            if label in items:
                assert c["items"] == items[label]
        for other in all_labels - set(own[kind]):
            assert other not in labels, (kind, other)
        salt = after_label(app, w, "Salt (hexadecimal):")
        assert salt.get("placeholder") == "Empty: a random salt each time"
        for title in ("Random", "Treat each line as a separate string", "Show the bare key in hexadecimal",
                      "Verify", "Copy to Clipboard", "Close"):
            assert by_title(app, w, title), (kind, title)
        assert "Hash to check the password against:" in labels
        assert input_view(app, w) and output_views(app, w)


@pytest.mark.case("TOOLS-029")
def test_tools_029_bcrypt_with_a_vector_s_salt_and_cost_gives_the_vector_s_hash(app):
    """TOOLS-029: bcrypt with a vector's salt and cost gives the vector's hash

    Covers: -
    Channel: ui
    Steps: In bcrypt Generate…: input "U*U", cost 5, version 2a, salt "10 41 04 10 41 04 10 41 04 10 41 04 10 41 04 10"; wait for the result; tick "Show the bare key in hexadecimal"; untick it, tick each-line and set input "U*U\\n\\nU*U".
    Expect: result is "$2a$05$CCCCCCCCCCCCCCCCCCCCC.E5YPO9kmyuRGyh0XouQYb4YMJKvyOeW"; bare key is 46 hex characters; per line the result is the vector, an empty line, the vector.
    """
    w = bcrypt_window(app)
    assert compute(app, w, "U*U") == ("result", BCRYPT_VECTOR)
    set_state(app, w, "Show the bare key in hexadecimal", True)
    bare = app.wait(lambda: (result(app, w) or "") != BCRYPT_VECTOR and result(app, w), 30)
    assert len(bare) == 46 and re.fullmatch(r"[0-9a-f]+", bare)
    set_state(app, w, "Show the bare key in hexadecimal", False)
    set_state(app, w, "Treat each line as a separate string", True)
    kind, value = compute(app, w, "U*U\n\nU*U")
    assert value == f"{BCRYPT_VECTOR}\n\n{BCRYPT_VECTOR}"
    set_state(app, w, "Treat each line as a separate string", False)
    set_field(app, w, "Salt (hexadecimal):", "")


@pytest.mark.case("TOOLS-030")
def test_tools_030_verify_says_match_no_match_and_not_such_a_hash(app):
    """TOOLS-030: Verify says match, no match, and "not such a hash"

    Covers: -
    Channel: ui
    Steps: In bcrypt Generate… with input "U*U", put the vector hash of TOOLS-029 into the check field and click Verify; change the input to "U*V" and Verify; put "5f4dcc3b5aa765d61d8327deb882cf99" into the check field and Verify; also verify "пароль" against "$2b$06$abcdefghijklmnopqrstuu0RbYLPpyLm/x71XGmlHQAdqmD5AbL2G".
    Expect: the verdict line reads "The password matches the hash.", then "The password does not match the hash.", then "This is not a bcrypt, scrypt, Argon2 or PBKDF2 hash."; the Cyrillic password matches its vector.
    """
    w = bcrypt_window(app)
    set_input(app, w, "U*U")
    assert verify(app, w, BCRYPT_VECTOR) == "The password matches the hash."
    set_input(app, w, "U*V")
    assert verify(app, w, BCRYPT_VECTOR) == "The password does not match the hash."
    assert verify(app, w, "5f4dcc3b5aa765d61d8327deb882cf99") == "This is not a bcrypt, scrypt, Argon2 or PBKDF2 hash."
    set_input(app, w, "пароль")
    assert verify(app, w, "$2b$06$abcdefghijklmnopqrstuu0RbYLPpyLm/x71XGmlHQAdqmD5AbL2G") == "The password matches the hash."
    set_field(app, w, "Salt (hexadecimal):", "")


@pytest.mark.case("TOOLS-031")
def test_tools_031_bcrypt_s_refusals_are_said_in_words_and_no_hash_is_shown(app):
    """TOOLS-031: bcrypt's refusals are said in words and no hash is shown

    Covers: -
    Channel: ui
    Steps: In bcrypt Generate… (cost 5): input of 80 "x"; then input "x" with salt "0102"; then salt "xyz"; then empty salt and cost 40.
    Expect: 80 bytes: a 60-character hash is shown and the problem line reads "bcrypt reads only the first 72 bytes."; salt "0102": "bcrypt takes a salt of exactly 16 bytes." and an empty result; "xyz": "The salt is not valid hexadecimal." and an empty result; cost 40: "The cost must be between 4 and 31." and an empty result.
    """
    w = bcrypt_window(app, salt="")
    set_input(app, w, "x" * 80)
    # the warning shows at once; the hash follows when computed
    value = app.wait(lambda: result(app, w), 30, "hash of 80 bytes")
    assert len(value) == 60 and value.startswith("$2a$05$")
    assert problem_line(app, w) == "bcrypt reads only the first 72 bytes."
    set_input(app, w, "x")
    for salt, message in (("0102", "bcrypt takes a salt of exactly 16 bytes."), ("xyz", "The salt is not valid hexadecimal.")):
        set_field(app, w, "Salt (hexadecimal):", salt)
        app.wait(lambda: problem_line(app, w) == message, 10, message)
        assert result(app, w) == ""
    set_field(app, w, "Salt (hexadecimal):", "")
    set_field(app, w, "Cost (4-31):", "40")
    app.wait(lambda: problem_line(app, w) == "The cost must be between 4 and 31.", 10, "cost")
    assert result(app, w) == ""
    set_field(app, w, "Cost (4-31):", "12")


@pytest.mark.case("TOOLS-032")
def test_tools_032_without_a_salt_every_hash_gets_its_own_random_makes_sixteen(app):
    """TOOLS-032: Without a salt every hash gets its own; Random makes sixteen new bytes

    Covers: -
    Channel: ui
    Steps: bcrypt Generate…, cost 5, empty salt, each-line ticked, input "same\\nsame"; then click Random twice, reading the salt field each time; verify each of the two result lines against "same" with the Verify box.
    Expect: the two lines differ, both start with "$2b$05$", both verify as matching; each Random fills the salt with 32 hex digits and the two salts differ.
    """
    w = bcrypt_window(app, version="2b", salt="")
    set_state(app, w, "Treat each line as a separate string", True)
    kind, value = compute(app, w, "same\nsame")
    one, two = value.split("\n")
    assert one != two and one.startswith("$2b$05$") and two.startswith("$2b$05$")
    set_state(app, w, "Treat each line as a separate string", False)
    set_input(app, w, "same")
    assert verify(app, w, one) == "The password matches the hash."
    assert verify(app, w, two) == "The password matches the hash."
    click(app, w, "Random")
    s1 = field(app, w, "Salt (hexadecimal):")
    click(app, w, "Random")
    s2 = field(app, w, "Salt (hexadecimal):")
    assert re.fullmatch(r"[0-9a-fA-F]{32}", s1.replace(" ", "")) and re.fullmatch(r"[0-9a-fA-F]{32}", s2.replace(" ", ""))
    assert s1 != s2
    set_field(app, w, "Salt (hexadecimal):", "")
    set_field(app, w, "Cost (4-31):", "12")


@pytest.mark.case("TOOLS-033")
def test_tools_033_scrypt_gives_rfc_7914_s_vector_and_a_verifiable_string(app):
    """TOOLS-033: scrypt gives RFC 7914's vector and a verifiable string

    Covers: -
    Channel: ui
    Steps: scrypt Generate…: input "pleaseletmein", salt = hex of "SodiumChloride", N power 14, r 8, p 1, length 32; read the result; tick bare key and read again.
    Expect: the string starts "$scrypt$ln=14,r=8,p=1$U29kaXVtQ2hsb3JpZGU$"; the bare key is 7023bdcb3afd7348461c06cd81fd38ebfda8fbba904f8e3ea9b543f6545da1f2 and equals `hashlib.scrypt(b"pleaseletmein", salt=b"SodiumChloride", n=16384, r=8, p=1, dklen=32)`; Verify of the string with the input says it matches.
    """
    w = hash_window(app, "scrypt")
    set_state(app, w, "Treat each line as a separate string", False)
    set_state(app, w, "Show the bare key in hexadecimal", False)
    set_field(app, w, "Salt (hexadecimal):", b"SodiumChloride".hex())
    set_field(app, w, "N, as a power of 2:", "14")
    set_field(app, w, "Block size (r):", "8")
    set_field(app, w, "Parallelism (p):", "1")
    set_field(app, w, "Hash length (bytes):", "32")
    kind, encoded = compute(app, w, "pleaseletmein")
    assert encoded.startswith("$scrypt$ln=14,r=8,p=1$U29kaXVtQ2hsb3JpZGU$"), encoded
    set_state(app, w, "Show the bare key in hexadecimal", True)
    bare = app.wait(lambda: result(app, w) != encoded and result(app, w), 30)
    want = hashlib.scrypt(b"pleaseletmein", salt=b"SodiumChloride", n=16384, r=8, p=1, dklen=32).hex()
    assert bare == want == "7023bdcb3afd7348461c06cd81fd38ebfda8fbba904f8e3ea9b543f6545da1f2"
    set_state(app, w, "Show the bare key in hexadecimal", False)
    assert verify(app, w, encoded) == "The password matches the hash."
    set_field(app, w, "Salt (hexadecimal):", "")
    set_field(app, w, "N, as a power of 2:", "15")


@pytest.mark.case("TOOLS-034")
def test_tools_034_scrypt_refuses_settings_that_would_need_more_than_2_gb(app):
    """TOOLS-034: scrypt refuses settings that would need more than 2 GB

    Covers: -
    Channel: ui
    Steps: scrypt Generate…, input "x", N power 24, r 64.
    Expect: the problem line is non-empty and the result is empty within 2 s; the app stays responsive (a later `get_document` answers).
    """
    w = hash_window(app, "scrypt")
    set_field(app, w, "Salt (hexadecimal):", "")
    set_field(app, w, "N, as a power of 2:", "24")
    set_field(app, w, "Block size (r):", "64")
    t0 = time.monotonic()
    set_input(app, w, "x")
    app.wait(lambda: problem_line(app, w), 2, "refusal")
    assert time.monotonic() - t0 < 2.5
    assert result(app, w) == ""
    assert app.text() is not None
    set_field(app, w, "N, as a power of 2:", "15")
    set_field(app, w, "Block size (r):", "8")


@pytest.mark.case("TOOLS-035")
def test_tools_035_argon2_s_three_variants_give_the_reference_implementation_s(app):
    """TOOLS-035: Argon2's three variants give the reference implementation's strings

    Covers: -
    Channel: ui
    Steps: Argon2 Generate…: input "password", salt = hex of "somesalt", memory 64, iterations 2, parallelism 2, length 32; select Argon2id, Argon2i, Argon2d in turn and read the result; then memory 8 with parallelism 4; then salt "0102".
    Expect: "$argon2id$v=19$m=64,t=2,p=2$c29tZXNhbHQ$lDh0Fd+4TtGXdGWh6GJgc630K9Turh+qHdTiOh/2hZ8", "$argon2i$v=19$m=64,t=2,p=2$c29tZXNhbHQ$u3EC2QpYDSqhwag4F/JKsYx8yBDM0sKg0MgMlK0pkWc", "$argon2d$v=19$m=64,t=2,p=2$c29tZXNhbHQ$1q8bgD0xYiK3sMCt/uIryr7jP0g04fs9QOITesC7M88"; memory 8 with 4 lanes and the 2-byte salt each give a problem line and no result.
    """
    w = hash_window(app, "Argon2")
    set_state(app, w, "Treat each line as a separate string", False)
    set_state(app, w, "Show the bare key in hexadecimal", False)
    set_field(app, w, "Salt (hexadecimal):", b"somesalt".hex())
    set_field(app, w, "Memory (KiB):", "64")
    set_field(app, w, "Iterations:", "2")
    set_field(app, w, "Parallelism:", "2")
    set_field(app, w, "Hash length (bytes):", "32")
    want = {
        "Argon2id": "$argon2id$v=19$m=64,t=2,p=2$c29tZXNhbHQ$lDh0Fd+4TtGXdGWh6GJgc630K9Turh+qHdTiOh/2hZ8",
        "Argon2i": "$argon2i$v=19$m=64,t=2,p=2$c29tZXNhbHQ$u3EC2QpYDSqhwag4F/JKsYx8yBDM0sKg0MgMlK0pkWc",
        "Argon2d": "$argon2d$v=19$m=64,t=2,p=2$c29tZXNhbHQ$1q8bgD0xYiK3sMCt/uIryr7jP0g04fs9QOITesC7M88",
    }
    set_input(app, w, "password")
    for variant, string in want.items():
        set_field(app, w, "Variant:", variant)
        app.wait(lambda: result(app, w) == string, 30, variant)
    set_field(app, w, "Memory (KiB):", "8")
    set_field(app, w, "Parallelism:", "4")
    app.wait(lambda: problem_line(app, w) and not result(app, w), 10, "too little memory")
    set_field(app, w, "Memory (KiB):", "64")
    set_field(app, w, "Parallelism:", "2")
    set_field(app, w, "Salt (hexadecimal):", "0102")
    app.wait(lambda: problem_line(app, w) and not result(app, w), 10, "short salt")
    for label, v in (("Salt (hexadecimal):", ""), ("Memory (KiB):", "19456"), ("Parallelism:", "1"), ("Variant:", "Argon2id")):
        set_field(app, w, label, v)


@pytest.mark.case("TOOLS-036")
def test_tools_036_pbkdf2_gives_the_known_key_and_a_verifiable_string_for_each(app):
    """TOOLS-036: PBKDF2 gives the known key and a verifiable string for each digest

    Covers: -
    Channel: ui
    Steps: PBKDF2 Generate…: input "password", salt = hex of "salt", iterations 4096, length 32, digest SHA-256; read result and bare key; switch digest to SHA-512 and SHA-1 and read the bare key.
    Expect: the string starts "$pbkdf2-sha256$4096$c2FsdA$"; SHA-256 bare key c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a; the SHA-512 and SHA-1 bare keys equal `hashlib.pbkdf2_hmac(<alg>, b"password", b"salt", 4096, 32)`; Verify of the string with "password" matches, with "passwor" does not.
    """
    w = hash_window(app, "PBKDF2")
    set_state(app, w, "Treat each line as a separate string", False)
    set_state(app, w, "Show the bare key in hexadecimal", False)
    set_field(app, w, "Salt (hexadecimal):", b"salt".hex())
    set_field(app, w, "Iterations:", "4096")
    set_field(app, w, "Hash length (bytes):", "32")
    set_field(app, w, "Digest:", "SHA-256")
    kind, encoded = compute(app, w, "password")
    assert encoded.startswith("$pbkdf2-sha256$4096$c2FsdA$"), encoded
    assert verify(app, w, encoded) == "The password matches the hash."
    set_input(app, w, "passwor")
    assert verify(app, w, encoded) == "The password does not match the hash."
    set_input(app, w, "password")
    set_state(app, w, "Show the bare key in hexadecimal", True)
    for digest, alg in (("SHA-256", "sha256"), ("SHA-512", "sha512"), ("SHA-1", "sha1")):
        set_field(app, w, "Digest:", digest)
        want = hashlib.pbkdf2_hmac(alg, b"password", b"salt", 4096, 32).hex()
        app.wait(lambda: result(app, w) == want, 30, digest)
    assert hashlib.pbkdf2_hmac("sha256", b"password", b"salt", 4096, 32).hex() == \
        "c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a"
    set_state(app, w, "Show the bare key in hexadecimal", False)
    for label, v in (("Salt (hexadecimal):", ""), ("Iterations:", "600000"), ("Digest:", "SHA-256")):
        set_field(app, w, label, v)


@pytest.mark.case("TOOLS-037")
def test_tools_037_password_hashes_from_files_a_line_per_file_of_the_file_s_byt(app, tmp):
    """TOOLS-037: Password hashes from files: a line per file, of the file's bytes

    Covers: -
    Channel: ui, modal, files
    Steps: Write `k1.txt` = "password", `k2.txt` = "other"; for each kind open `Tools|Hashes|<kind>|Generate from files…` (PBKDF2: salt hex of "salt", 4096 rounds, bare key ticked), queue both paths and click "Choose files to generate <kind>...".
    Expect: titles "Generate <kind> digest from files"; the input and each-line box are hidden; two lines ending "  k1.txt" and "  k2.txt"; for PBKDF2 the first line is "c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a  k1.txt"; for scrypt the key part of the first line is hashlib.scrypt of "password" with the salt in its own string; Copy to Clipboard takes both lines.
    """
    (tmp / "k1.txt").write_text("password")
    (tmp / "k2.txt").write_text("other")
    paths = [str(tmp / "k1.txt"), str(tmp / "k2.txt")]
    for kind in KINDS:
        w = hash_window(app, kind, files=True)
        assert by_title(app, w, "Treat each line as a separate string") is None
        assert not [c for c in text_views(app, w) if c.get("editable")]
        if kind == "PBKDF2":
            set_field(app, w, "Salt (hexadecimal):", b"salt".hex())
            set_field(app, w, "Iterations:", "4096")
            set_state(app, w, "Show the bare key in hexadecimal", True)
        if kind == "bcrypt":
            set_field(app, w, "Cost (4-31):", "5")
        app.answers(panels=[paths])
        click(app, w, f"Choose files to generate {kind}...")
        lines = app.wait(lambda: (result(app, w) or "").count("\n") == 1 and result(app, w).split("\n"), 60, kind)
        assert lines[0].endswith("  k1.txt") and lines[1].endswith("  k2.txt"), lines
        if kind == "PBKDF2":
            assert lines[0] == "c5e478d59288c841aa530db6845c4c8d962893a001ce4e11a4963873aa98134a  k1.txt"
        if kind == "scrypt":
            enc = lines[0].split("  ")[0]
            m = re.match(r"\$scrypt\$ln=(\d+),r=(\d+),p=(\d+)\$([^$]+)\$([^$]+)$", enc)
            ln, r, p = int(m[1]), int(m[2]), int(m[3])
            key = hashlib.scrypt(b"password", salt=b64d(m[4]), n=2 ** ln, r=r, p=p, dklen=len(b64d(m[5])),
                                 maxmem=2 ** 31 - 1)
            assert key == b64d(m[5])
        click(app, w, "Copy to Clipboard")
        assert app.clipboard() == "\n".join(lines)
        if kind == "PBKDF2":
            set_state(app, w, "Show the bare key in hexadecimal", False)
            set_field(app, w, "Salt (hexadecimal):", "")
            set_field(app, w, "Iterations:", "600000")
        if kind == "bcrypt":
            set_field(app, w, "Cost (4-31):", "12")


@pytest.mark.case("TOOLS-038")
def test_tools_038_password_hashes_of_the_selection_go_to_the_clipboard_with_de(app):
    """TOOLS-038: Password hashes of the selection go to the clipboard with default settings

    Covers: -
    Channel: mcp, clipboard, ui
    Steps: Document "user: hunter2 end", select "hunter2"; run `Tools|Hashes|<kind>|Generate from selection into clipboard` for the four kinds, reading the clipboard each time; verify bcrypt's and Argon2's strings with the kind's Verify box and input "hunter2"; then with an empty document set the clipboard to "keep" and run the bcrypt command.
    Expect: prefixes "$2b$12$", "$scrypt$ln=15,r=8,p=1$", "$argon2id$v=19$m=19456,t=2,p=1$", "$pbkdf2-sha256$600000$"; scrypt's and PBKDF2's keys equal hashlib's with the salt decoded from the string; bcrypt and Argon2 verify with "hunter2" and not with "hunter3"; with the empty document the clipboard still reads "keep".
    """
    app.new("user: hunter2 end")
    got = {}
    for kind in KINDS:
        app.select(1, 7, 1, 14)
        app.clipboard(set="")
        app.run(f"Tools|Hashes|{kind}|Generate from selection into clipboard")
        got[kind] = app.wait(lambda: app.clipboard() or None, 30, kind)
    assert got["bcrypt"].startswith("$2b$12$")
    assert got["scrypt"].startswith("$scrypt$ln=15,r=8,p=1$")
    assert got["Argon2"].startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert got["PBKDF2"].startswith("$pbkdf2-sha256$600000$")
    m = re.match(r"\$scrypt\$ln=15,r=8,p=1\$([^$]+)\$([^$]+)$", got["scrypt"])
    assert hashlib.scrypt(b"hunter2", salt=b64d(m[1]), n=2 ** 15, r=8, p=1, dklen=len(b64d(m[2])), maxmem=2 ** 31 - 1) == b64d(m[2])
    m = re.match(r"\$pbkdf2-sha256\$600000\$([^$]+)\$([^$]+)$", got["PBKDF2"])
    salt = base64.b64decode(m[1].replace(".", "+") + "=" * (-len(m[1]) % 4))
    assert hashlib.pbkdf2_hmac("sha256", b"hunter2", salt, 600000, 32) == base64.b64decode(m[2].replace(".", "+") + "=" * (-len(m[2]) % 4))
    for kind in ("bcrypt", "Argon2"):
        w = hash_window(app, kind)
        set_input(app, w, "hunter2")
        assert verify(app, w, got[kind]) == "The password matches the hash.", kind
        set_input(app, w, "hunter3")
        assert verify(app, w, got[kind]) == "The password does not match the hash.", kind
        app.close_window(w)
    app.new("")
    app.clipboard(set="keep")
    app.run("Tools|Hashes|bcrypt|Generate from selection into clipboard")
    app.idle(0.3)
    assert app.clipboard() == "keep"


@pytest.mark.case("TOOLS-039")
def test_tools_039_base64_encodes_text_as_utf_8_and_hex_bytes_as_themselves(app):
    """TOOLS-039: Base64 encodes text as UTF-8 and hex bytes as themselves

    Covers: -
    Channel: ui
    Steps: `Tools|Base|Base64…`, Encode, input is Text: input "Привет"; switch to "Bytes in hexadecimal" and input "fb ff"; tick "Base64 (URL-safe)"; then input "fb f".
    Expect: "0J/RgNC40LLQtdGC"; "+/8="; URL-safe "-_8="; for "fb f" an empty result and the problem line "The input is not bytes written in hexadecimal."; the window has no popup to choose another base; the result label reads "Result:".
    """
    w = base_window(app, "Base64")
    base_direction(app, w, "Encode")
    base_input_kind(app, w, "Text")
    set_state(app, w, "Base64 (URL-safe)", False)
    set_input(app, w, "Привет")
    assert result(app, w) == "0J/RgNC40LLQtdGC"
    assert "Result:" in static_texts(app, w)
    assert not [c for c in controls(app, w) if c["class"] == "NSPopUpButton"]
    base_input_kind(app, w, "Bytes in hexadecimal")
    set_input(app, w, "fb ff")
    assert result(app, w) == "+/8="
    set_state(app, w, "Base64 (URL-safe)", True)
    app.wait(lambda: result(app, w) == "-_8=", 5, "url-safe")
    set_state(app, w, "Base64 (URL-safe)", False)
    set_input(app, w, "fb f")
    assert result(app, w) == "" and base_problem(app, w) == "The input is not bytes written in hexadecimal."
    base_input_kind(app, w, "Text")
    set_input(app, w, "")


@pytest.mark.case("TOOLS-040")
def test_tools_040_base64_decodes_to_text_and_bytes_and_refuses_rubbish(app):
    """TOOLS-040: Base64 decodes to text and bytes, and refuses rubbish

    Covers: -
    Channel: ui
    Steps: Base64 window, Decode: input "SGVs\\nbG8=\\n"; then "SGVsbG8" (unpadded); then "SGVsbG8*"; then "//8=".
    Expect: text "Hello" and bytes "48656c6c6f" for both of the first two; "SGVsbG8*" gives empty outputs and "The input is not valid Base64."; "//8=" gives bytes "ffff", an empty text and a problem line starting "The decoded bytes are not UTF-8 text"; decode shows "Text:" and "Bytes in hexadecimal:" with a Copy button each.
    """
    w = base_window(app, "Base64")
    base_direction(app, w, "Decode")
    labels = static_texts(app, w)
    assert "Text:" in labels and "Bytes in hexadecimal:" in labels
    assert len([c for c in controls(app, w) if c.get("title") == "Copy"]) == 2
    for text in ("SGVs\nbG8=\n", "SGVsbG8"):
        set_input(app, w, text)
        assert result(app, w, 0) == "Hello" and result(app, w, 1) == "48656c6c6f", text
    set_input(app, w, "SGVsbG8*")
    assert result(app, w, 0) == "" and result(app, w, 1) == ""
    assert base_problem(app, w) == "The input is not valid Base64."
    set_input(app, w, "//8=")
    assert result(app, w, 0) == "" and result(app, w, 1) == "ffff"
    assert base_problem(app, w).startswith("The decoded bytes are not UTF-8 text")
    set_input(app, w, "")
    base_direction(app, w, "Encode")


@pytest.mark.case("TOOLS-041")
def test_tools_041_base58_and_base58check_follow_bitcoin_s_alphabet(app):
    """TOOLS-041: Base58 and Base58Check follow Bitcoin's alphabet

    Covers: -
    Channel: ui
    Steps: `Tools|Base|Base58…`: encode "Hello World!"; encode hex "0000287fb4cd"; tick Base58Check and encode hex "00f54a5851e9372b87810a8e60cdd2e7cfd80b6e31"; Decode "2NEpo7TZRRrLZSi2U", "2NEpo7TZRRrLZSi20", and (Base58Check) "1PMycacnJaSqwwJqjawXBErnLsZ7RkXUAt".
    Expect: "2NEpo7TZRRrLZSi2U"; "11233QC4" (leading zero bytes as 1s); "1PMycacnJaSqwwJqjawXBErnLsZ7RkXUAs"; decode gives "Hello World!" and bytes 48656c6c6f20576f726c6421; the "0" input gives "The input is not valid Base58." and no output; the address with a wrong last character is refused; the box is titled "Base58Check".
    """
    w = base_window(app, "Base58")
    base_direction(app, w, "Encode")
    base_input_kind(app, w, "Text")
    set_state(app, w, "Base58Check", False)
    set_input(app, w, "Hello World!")
    assert result(app, w) == "2NEpo7TZRRrLZSi2U"
    base_input_kind(app, w, "Bytes in hexadecimal")
    set_input(app, w, "0000287fb4cd")
    assert result(app, w) == "11233QC4"
    set_input(app, w, "00f54a5851e9372b87810a8e60cdd2e7cfd80b6e31")
    set_state(app, w, "Base58Check", True)
    app.wait(lambda: result(app, w) == "1PMycacnJaSqwwJqjawXBErnLsZ7RkXUAs", 5, "base58check")
    set_state(app, w, "Base58Check", False)
    base_input_kind(app, w, "Text")
    base_direction(app, w, "Decode")
    set_input(app, w, "2NEpo7TZRRrLZSi2U")
    assert result(app, w, 0) == "Hello World!" and result(app, w, 1) == "48656c6c6f20576f726c6421"
    set_input(app, w, "2NEpo7TZRRrLZSi20")
    assert result(app, w, 0) == "" and result(app, w, 1) == ""
    assert base_problem(app, w) == "The input is not valid Base58."
    set_state(app, w, "Base58Check", True)
    set_input(app, w, "1PMycacnJaSqwwJqjawXBErnLsZ7RkXUAt")
    app.idle(0.1)
    assert result(app, w, 1) == "" and base_problem(app, w)
    set_input(app, w, "1PMycacnJaSqwwJqjawXBErnLsZ7RkXUAs")
    app.wait(lambda: result(app, w, 1) == "00f54a5851e9372b87810a8e60cdd2e7cfd80b6e31", 5, "check decode")
    set_state(app, w, "Base58Check", False)
    set_input(app, w, "")
    base_direction(app, w, "Encode")


@pytest.mark.case("TOOLS-042")
def test_tools_042_base32_gives_rfc_4648_s_vectors_both_ways(app):
    """TOOLS-042: Base32 gives RFC 4648's vectors both ways

    Covers: -
    Channel: ui
    Steps: `Tools|Base|Base32…`: encode each of "f", "fo", "foo", "foob", "fooba", "foobar"; decode "MZXW6YTBOI======", "mzxw6ytboi", "MZXW1".
    Expect: MY======, MZXQ====, MZXW6===, MZXW6YQ=, MZXW6YTB, MZXW6YTBOI======; both decodings give "foobar" / 666f6f626172; "MZXW1" gives empty outputs and a problem line; the window has no variant box.
    """
    w = base_window(app, "Base32")
    assert by_title(app, w, "Base64 (URL-safe)") is None and by_title(app, w, "Base58Check") is None
    assert not [c for c in controls(app, w) if c["class"] == "NSButton" and c.get("title") not in
                ("Text", "Bytes in hexadecimal", "Copy", "Close")]
    base_direction(app, w, "Encode")
    base_input_kind(app, w, "Text")
    for text, enc in (("f", "MY======"), ("fo", "MZXQ===="), ("foo", "MZXW6==="), ("foob", "MZXW6YQ="),
                      ("fooba", "MZXW6YTB"), ("foobar", "MZXW6YTBOI======")):
        set_input(app, w, text)
        assert result(app, w) == enc, text
    base_direction(app, w, "Decode")
    for text in ("MZXW6YTBOI======", "mzxw6ytboi"):
        set_input(app, w, text)
        assert result(app, w, 0) == "foobar" and result(app, w, 1) == "666f6f626172", text
    set_input(app, w, "MZXW1")
    assert result(app, w, 0) == "" and result(app, w, 1) == "" and base_problem(app, w)
    set_input(app, w, "")
    base_direction(app, w, "Encode")


@pytest.mark.case("TOOLS-043")
def test_tools_043_a_base_window_opens_with_the_editor_s_selection_as_input(app):
    """TOOLS-043: A Base window opens with the editor's selection as input

    Covers: -
    Channel: ui, mcp
    Steps: Document "see SGVsbG8= here", select "SGVsbG8="; run `Tools|Base|Base64…`; choose Decode; click the Copy beside the text.
    Expect: the input view reads "SGVsbG8="; the text output is "Hello"; the clipboard reads "Hello".
    """
    app.new("see SGVsbG8= here")
    app.select(1, 5, 1, 13)
    w = base_window(app, "Base64")
    assert input_view(app, w)["value"] == "SGVsbG8="
    base_direction(app, w, "Decode")
    app.wait(lambda: result(app, w, 0) == "Hello", 5)
    copies = [c for c in controls(app, w) if c.get("title") == "Copy"]
    app.act(w, "click", path=copies[0]["path"])
    assert app.clipboard() == "Hello"
    set_input(app, w, "")
    base_direction(app, w, "Encode")


@pytest.mark.case("TOOLS-044")
def test_tools_044_empty_input_gives_empty_output_and_no_complaint(app):
    """TOOLS-044: Empty input gives empty output and no complaint

    Covers: -
    Channel: ui
    Steps: For Base64, Base58, Base32, in both directions, set the input empty.
    Expect: every output view is empty and the problem line is empty.
    """
    for name in ("Base64", "Base58", "Base32"):
        w = base_window(app, name)
        for direction in ("Encode", "Decode"):
            base_direction(app, w, direction)
            set_input(app, w, "x")
            set_input(app, w, "")
            assert all(v["value"] == "" for v in output_views(app, w)), (name, direction)
            assert not base_problem(app, w), (name, direction)
        base_direction(app, w, "Encode")


@pytest.mark.case("TOOLS-045")
def test_tools_045_the_generator_opens_with_a_password_made_from_its_defaults(fresh_app):
    """TOOLS-045: The generator opens with a password made from its defaults

    Covers: -
    Channel: ui
    Steps: With fresh preferences run `Tools|Password Generator`; read the controls.
    Expect: "Length:" 20, "Number of passwords:" 1, Uppercase, Lowercase, Digits and "Symbols:" ticked with "!@#$%^&*()-_=+[]{};:,.<>?/~", look-alikes unticked, "At least one character of each kind" ticked, Hash popup "None"; the result already holds one password of 20 characters, all from those sets, with at least one of each kind; the entropy line reads "Entropy: about 129 bits".
    """
    app = fresh_app
    w = pw_window(app)
    assert field(app, w, "Length:") == "20"
    assert field(app, w, "Number of passwords:") == "1"
    for title in ("Uppercase letters (A-Z)", "Lowercase letters (a-z)", "Digits (0-9)", "Symbols:",
                  "At least one character of each kind"):
        assert state(app, w, title) == 1, title
    assert state(app, w, "Leave out characters that look alike (O 0 o I l 1)") == 0
    cs = controls(app, w)
    sym = cs[[i for i, c in enumerate(cs) if c.get("title") == "Symbols:"][0] + 1]["value"]
    assert sym == "!@#$%^&*()-_=+[]{};:,.<>?/~"
    assert field(app, w, "Hash:") == "None"
    pw = result(app, w)
    assert len(pw) == 20
    sets = ["ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz", "0123456789", sym]
    assert all(ch in "".join(sets) for ch in pw)
    assert all(any(ch in s for ch in pw) for s in sets)
    assert pw_entropy(app, w) == "Entropy: about 129 bits"


@pytest.mark.case("TOOLS-046")
def test_tools_046_several_passwords_of_a_chosen_shape_all_different(app):
    """TOOLS-046: Several passwords of a chosen shape, all different

    Covers: -
    Channel: ui
    Steps: Length 24, number 5, untick Symbols and look-alikes, keep each-kind; click Generate.
    Expect: five lines, pairwise different, each 24 characters of [A-Za-z0-9] containing an uppercase letter, a lowercase letter and a digit; "Entropy: about 142 bits".
    """
    w = pw_window(app)
    pw_set(app, w, length=24, count=5, upper=True, lower=True, digits=True, symbols=False, lookalikes=False, each=True, hash_kind="None")
    out = pw_generate(app, w).split("\n")
    assert len(out) == 5 and len(set(out)) == 5
    for p in out:
        assert re.fullmatch(r"[A-Za-z0-9]{24}", p) and re.search("[A-Z]", p) and re.search("[a-z]", p) and re.search("[0-9]", p)
    assert pw_entropy(app, w) == "Entropy: about 142 bits"


@pytest.mark.case("TOOLS-047")
def test_tools_047_own_symbols_look_alikes_left_out(app):
    """TOOLS-047: Own symbols, look-alikes left out

    Covers: -
    Channel: ui
    Steps: Untick Uppercase and Lowercase, keep Digits, Symbols "# $ %", length 40, number 1, Generate; then tick "Leave out characters that look alike (O 0 o I l 1)" and Generate 20 times.
    Expect: the password is 40 characters from "0123456789#$%" with at least one of #, $, %; with look-alikes left out no password contains 0 or 1.
    """
    w = pw_window(app)
    pw_set(app, w, length=40, count=1, upper=False, lower=False, digits=True, symbols=True, symbol_text="# $ %",
           lookalikes=False, each=True, hash_kind="None")
    p = pw_generate(app, w)
    assert len(p) == 40 and set(p) <= set("0123456789#$%") and set(p) & set("#$%")
    pw_set(app, w, lookalikes=True)
    for _ in range(20):
        p = pw_generate(app, w)
        assert "0" not in p and "1" not in p and set(p) <= set("23456789#$%")
    pw_set(app, w, length=20, upper=True, lower=True, symbol_text="!@#$%^&*()-_=+[]{};:,.<>?/~", lookalikes=False)


@pytest.mark.case("TOOLS-048")
def test_tools_048_no_kind_of_character_chosen_is_said_so(app):
    """TOOLS-048: No kind of character chosen is said so

    Covers: -
    Channel: ui
    Steps: Untick Uppercase, Lowercase, Digits and Symbols; Generate.
    Expect: the result is empty and the entropy line reads "Choose at least one kind of character."
    """
    w = pw_window(app)
    pw_set(app, w, upper=False, lower=False, digits=False, symbols=False)
    assert pw_generate(app, w) == ""
    assert pw_entropy(app, w) == "Choose at least one kind of character."
    pw_set(app, w, upper=True, lower=True, digits=True, symbols=True)


@pytest.mark.case("TOOLS-049")
def test_tools_049_lengths_at_the_edges(app):
    """TOOLS-049: Lengths at the edges

    Covers: -
    Channel: ui
    Steps: With all kinds ticked set the length to "1", "0", "abc" and "1000" in turn and Generate.
    Expect: "1", "0" and "abc" each give a single-character password; "1000" gives a 1000-character password; the app does not hang.
    """
    w = pw_window(app)
    pw_set(app, w, count=1, upper=True, lower=True, digits=True, symbols=True, hash_kind="None")
    for length, want in (("1", 1), ("0", 1), ("abc", 1), ("1000", 1000)):
        pw_set(app, w, length=length)
        assert len(pw_generate(app, w)) == want, length
    pw_set(app, w, length=20)


@pytest.mark.case("TOOLS-050")
def test_tools_050_a_hash_of_each_password_of_the_kind_chosen(app):
    """TOOLS-050: A hash of each password, of the kind chosen

    Covers: -
    Channel: ui
    Steps: Length 16, number 2; read the Hash popup's items; choose SHA-256 and Generate; choose PBKDF2 and Generate; choose None and Generate.
    Expect: the popup lists None, bcrypt, scrypt, Argon2, PBKDF2, MD5, SHA-1, SHA-256, SHA-512, SHA-224, SHA-384, SHA3-256, SHA3-512, BLAKE2b, CRC-32; with SHA-256 a second text view shows two lines, each hashlib.sha256 of the matching password; with PBKDF2 each line starts "$pbkdf2-sha256$600000$" and its key equals hashlib's for that password; with None the hash view is hidden and empty.
    """
    w = pw_window(app)
    pop = after_label(app, w, "Hash:")
    assert pop["items"] == ["None"] + KINDS + DIGESTS
    pw_set(app, w, length=16, count=2, hash_kind="SHA-256")
    def hashes_view():
        outs = output_views(app, w)
        return outs[1]["value"] if len(outs) > 1 else None
    pws = pw_generate(app, w).split("\n")
    hs = app.wait(lambda: hashes_view() and hashes_view().count("\n") == 1 and hashes_view().split("\n"), 10)
    assert len(pws) == 2 and hs == [hashlib.sha256(p.encode()).hexdigest() for p in pws]
    pw_set(app, w, hash_kind="PBKDF2")
    pws = pw_generate(app, w).split("\n")
    hs = app.wait(lambda: (hashes_view() or "").startswith("$pbkdf2") and hashes_view().count("\n") == 1
                  and hashes_view().split("\n"), 30)
    for p, h in zip(pws, hs):
        m = re.match(r"\$pbkdf2-sha256\$600000\$([^$]+)\$([^$]+)$", h)
        assert m, h
        dec = lambda s: base64.b64decode(s.replace(".", "+") + "=" * (-len(s) % 4))
        assert hashlib.pbkdf2_hmac("sha256", p.encode(), dec(m[1]), 600000, 32) == dec(m[2])
    pw_set(app, w, hash_kind="None")
    pw_generate(app, w)
    app.idle(0.2)
    assert hashes_view() in (None, "")


@pytest.mark.case("TOOLS-051")
def test_tools_051_copy_to_clipboard_and_insert_into_document(app):
    """TOOLS-051: Copy to Clipboard and Insert into Document

    Covers: -
    Channel: ui, clipboard, mcp
    Steps: Document "password=" with the caret at the end; Generate one password of 12; click Copy to Clipboard; click Insert into Document; undo once in the editor.
    Expect: the clipboard equals the password; the document becomes "password=" + the password; one undo gives "password=" back.
    """
    app.new("password=")
    app.select(1, 10)
    w = pw_window(app)
    pw_set(app, w, length=12, count=1, upper=True, lower=True, digits=True, symbols=False, hash_kind="None")
    p = pw_generate(app, w)
    assert len(p) == 12
    click(app, w, "Copy to Clipboard")
    assert app.clipboard() == p
    click(app, w, "Insert into Document")
    assert app.text() == "password=" + p
    app.run("IDM_EDIT_UNDO")
    assert app.text() == "password="
    pw_set(app, w, length=20, symbols=True)


@pytest.mark.case("TOOLS-052")
def test_tools_052_the_generator_s_settings_are_remembered_across_a_restart(fresh_app):
    """TOOLS-052: The generator's settings are remembered across a restart

    Covers: -
    Channel: ui, launch
    Steps: Set length 12, only Digits and Symbols "# $ %", Hash SHA-1, Generate, close the window; `app.restart()`; open the generator again (test uses `fresh_app` and leaves defaults cleared).
    Expect: after the restart the fields read length 12, Uppercase/Lowercase unticked, Digits ticked, symbols "# $ %", Hash SHA-1.
    """
    app = fresh_app
    try:
        w = pw_window(app)
        pw_set(app, w, length=12, upper=False, lower=False, digits=True, symbols=True, symbol_text="# $ %", hash_kind="SHA-1")
        pw_generate(app, w)
        click(app, w, "Close")
        app.restart()
        w = pw_window(app)
        assert field(app, w, "Length:") == "12"
        assert state(app, w, "Uppercase letters (A-Z)") == 0 and state(app, w, "Lowercase letters (a-z)") == 0
        assert state(app, w, "Digits (0-9)") == 1
        cs = controls(app, w)
        assert cs[[i for i, c in enumerate(cs) if c.get("title") == "Symbols:"][0] + 1]["value"] == "# $ %"
        assert field(app, w, "Hash:") == "SHA-1"
    finally:
        app.stop()
        app.start()


@pytest.mark.case("TOOLS-053")
def test_tools_053_get_with_parameters_and_headers_reaches_the_server_as_typed(app, http_server):
    """TOOLS-053: GET with parameters and headers reaches the server as typed

    Covers: -
    Channel: ui
    Steps: Start the test server; `Tools|HTTP Request`; method GET, address "127.0.0.1:<port>/echo?fixed=1" (no scheme), Parameters "q=a b&c\\nимя=Жук", Headers "X-Custom: 42\\n# not sent\\nAccept: application/json"; click Send; wait for the status line.
    Expect: the status line reads "HTTP/1.1 200 OK  ·  <n> ms  ·  <n> bytes"; the JSON answer (Body view) has method GET, query [["fixed","1"],["q","a b&c"],["имя","Жук"]], headers x-custom "42", accept "application/json", user-agent starting "NotepadMac/", and no "# not sent" header.
    """
    w = http_window(app)
    http_set(app, w, method="GET", address=f"127.0.0.1:{http_server.port}/echo?fixed=1",
             params="q=a b&c\nимя=Жук", headers="X-Custom: 42\n# not sent\nAccept: application/json",
             body="", user="", password="", fmt=False, follow=True)
    status = http_send(app, w)
    assert re.fullmatch(r"HTTP/1\.[01] 200 OK  ·  \d+ ms  ·  \d+ bytes", status), status
    http_answer_view(app, w, "Body")
    saw = http_json(app, w)
    assert saw["method"] == "GET"
    assert saw["query"] == [["fixed", "1"], ["q", "a b&c"], ["имя", "Жук"]]
    assert saw["headers"]["x-custom"] == "42" and saw["headers"]["accept"] == "application/json"
    assert saw["headers"]["user-agent"].startswith("NotepadMac/")
    assert not [k for k in saw["headers"] if "not sent" in k]


@pytest.mark.case("TOOLS-054")
def test_tools_054_post_put_patch_and_delete_carry_the_body_byte_for_byte(app, http_server):
    """TOOLS-054: POST, PUT, PATCH and DELETE carry the body byte for byte

    Covers: -
    Channel: ui
    Steps: For each method: address /echo, Body "{\\"имя\\": \\"Жук\\", \\"n\\": [1, 2]}\\n", content type popup "application/json"; Send.
    Expect: the echoed method is that method; body equals the text exactly; content-type "application/json"; content-length equals the UTF-8 byte count.
    """
    w = http_window(app)
    body = "{\"имя\": \"Жук\", \"n\": [1, 2]}\n"
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        http_set(app, w, method=method, address=f"{http_server.base}/echo", params="", headers="", body=body,
                 content_type="application/json", user="", password="", fmt=False)
        http_send(app, w)
        http_answer_view(app, w, "Body")
        saw = http_json(app, w)
        assert saw["method"] == method
        assert saw["body"] == body
        assert saw["headers"]["content-type"] == "application/json"
        assert int(saw["headers"]["content-length"]) == len(body.encode())


@pytest.mark.case("TOOLS-055")
def test_tools_055_a_content_type_among_the_headers_wins_no_body_no_content_typ(app, http_server):
    """TOOLS-055: A Content-Type among the headers wins; no body, no content type

    Covers: -
    Channel: ui
    Steps: POST to /echo with body "a,b" and popup "application/json" but header "content-type: text/csv"; Send; then clear header and body and Send GET.
    Expect: the first echo shows content-type "text/csv" only; the second shows no content-type header and an empty body.
    """
    w = http_window(app)
    http_set(app, w, method="POST", address=f"{http_server.base}/echo", params="", headers="content-type: text/csv",
             body="a,b", content_type="application/json", user="", password="", fmt=False)
    http_send(app, w)
    saw = http_json(app, w)
    assert saw["headers"]["content-type"] == "text/csv" and saw["body"] == "a,b"
    http_set(app, w, method="GET", headers="", body="")
    http_send(app, w)
    saw = http_json(app, w)
    assert "content-type" not in saw["headers"] and saw["body"] == ""


@pytest.mark.case("TOOLS-056")
def test_tools_056_head_shows_headers_and_no_body_options_arrives_as_options(app, http_server):
    """TOOLS-056: HEAD shows headers and no body; OPTIONS arrives as OPTIONS

    Covers: -
    Channel: ui
    Steps: HEAD /echo, Send, switch the answer to Headers; then OPTIONS /echo, Send.
    Expect: HEAD: status 200, the Body view is empty, the Headers view starts "HTTP/1." and contains "X-Test-Server: notepad" and a Content-Length > 0; OPTIONS: echoed method "OPTIONS".
    """
    w = http_window(app)
    http_set(app, w, method="HEAD", address=f"{http_server.base}/echo", params="", headers="", body="", user="", password="")
    status = http_send(app, w)
    assert "200" in status
    http_answer_view(app, w, "Body")
    assert http_answer(app, w) == ""
    http_answer_view(app, w, "Headers")
    h = http_answer(app, w)
    assert h.startswith("HTTP/1.") and "X-Test-Server: notepad" in h
    assert int(re.search(r"Content-Length: (\d+)", h)[1]) > 0
    http_answer_view(app, w, "Body")
    http_set(app, w, method="OPTIONS")
    http_send(app, w)
    assert http_json(app, w)["method"] == "OPTIONS"
    http_set(app, w, method="GET")


@pytest.mark.case("TOOLS-057")
def test_tools_057_a_name_and_password_go_as_basic_authentication_and_are_not_r(fresh_app, http_server):
    """TOOLS-057: A name and password go as Basic authentication and are not remembered

    Covers: -
    Channel: ui, launch
    Steps: Options section: user "igor", password "pa:ss word"; GET /echo; Send; close the window; `app.restart()`; reopen HTTP Request and read the Options fields.
    Expect: the echoed authorization is "Basic " + base64("igor:pa:ss word"); after the restart the method, address and user "igor" are restored and the password field is empty.
    """
    app = fresh_app
    try:
        w = http_window(app)
        http_set(app, w, method="GET", address=f"{http_server.base}/echo", user="igor", password="pa:ss word", fmt=False)
        http_send(app, w)
        saw = http_json(app, w)
        assert saw["headers"]["authorization"] == "Basic " + base64.b64encode(b"igor:pa:ss word").decode()
        click(app, w, "Close")
        app.restart()
        w = http_window(app)
        pop = [c for c in controls(app, w) if c["class"] == "NSPopUpButton" and "OPTIONS" in (c.get("items") or [])][0]
        assert pop["value"] == "GET"
        addr = [c for c in controls(app, w) if c.get("placeholder") == "https://example.com/path"][0]
        assert addr["value"] == f"{http_server.base}/echo"
        http_section(app, w, "Options")
        assert field(app, w, "User name:") == "igor"
        assert field(app, w, "Password:") == ""
    finally:
        app.stop()
        app.start()


@pytest.mark.case("TOOLS-058")
def test_tools_058_redirects_are_followed_or_shown_as_the_302_they_are(app, http_server):
    """TOOLS-058: Redirects are followed, or shown as the 302 they are

    Covers: -
    Channel: ui
    Steps: GET /redirect with "Follow redirects" ticked; Send; then untick it and Send; look at the Headers view.
    Expect: followed: status 200 and the echoed query [["redirected","1"]]; not followed: status line contains "302", body "moved", headers include "Location: /echo?redirected=1".
    """
    w = http_window(app)
    http_set(app, w, method="GET", address=f"{http_server.base}/redirect", params="", headers="", body="",
             user="", password="", follow=True, fmt=False)
    status = http_send(app, w)
    assert "200" in status
    http_answer_view(app, w, "Body")
    assert http_json(app, w)["query"] == [["redirected", "1"]]
    http_set(app, w, follow=False)
    status = http_send(app, w)
    assert "302" in status
    assert http_answer(app, w) == "moved"
    http_answer_view(app, w, "Headers")
    assert "Location: /echo?redirected=1" in http_answer(app, w)
    http_answer_view(app, w, "Body")
    http_set(app, w, follow=True)


@pytest.mark.case("TOOLS-059")
def test_tools_059_404_and_500_are_answers_not_errors(app, http_server):
    """TOOLS-059: 404 and 500 are answers, not errors

    Covers: -
    Channel: ui
    Steps: GET /status/404, Send; GET /status/500, Send.
    Expect: status lines contain "404" and "500"; the bodies are "status 404" / "status 500"; no alert is logged.
    """
    w = http_window(app)
    http_set(app, w, method="GET", params="", headers="", body="", user="", password="")
    for code in (404, 500):
        http_set(app, w, address=f"{http_server.base}/status/{code}")
        status = http_send(app, w)
        assert str(code) in status
        http_answer_view(app, w, "Body")
        assert http_answer(app, w) == f"status {code}"
    assert not [e for e in app.modal_log() if e["kind"] == "alert"]


@pytest.mark.case("TOOLS-060")
def test_tools_060_the_body_is_read_in_its_charset_unpacked_or_shown_as_bytes(app, http_server):
    """TOOLS-060: The body is read in its charset, unpacked, or shown as bytes

    Covers: -
    Channel: ui
    Steps: GET /latin1, /gzip and /binary in turn.
    Expect: "café crème"; "unpacked text"; "The answer is not text: 4 bytes.\\n\\nfffe00c3".
    """
    w = http_window(app)
    http_set(app, w, method="GET", params="", headers="", body="", user="", password="")
    http_answer_view(app, w, "Body")
    for path, want in (("latin1", "café crème"), ("gzip", "unpacked text"),
                       ("binary", "The answer is not text: 4 bytes.\n\nfffe00c3")):
        http_set(app, w, address=f"{http_server.base}/{path}")
        http_send(app, w)
        assert http_answer(app, w) == want, path


@pytest.mark.case("TOOLS-061")
def test_tools_061_a_slow_server_times_out_and_a_closed_port_is_an_error_in_wor(app, http_server):
    """TOOLS-061: A slow server times out and a closed port is an error in words

    Covers: -
    Channel: ui
    Steps: Options timeout 1, GET /slow, Send, time it; then address "127.0.0.1:1/", Send.
    Expect: the status line holds an error text (no status code) within 2.5 s of Send; the closed port also gives an error text and an empty answer; the Send button is usable again afterwards.
    """
    w = http_window(app)
    try:
        http_set(app, w, method="GET", address=f"{http_server.base}/slow", params="", headers="", body="",
                 user="", password="", timeout=1)
        t0 = time.monotonic()
        status = http_send(app, w, timeout=10)
        assert time.monotonic() - t0 < 2.5
        assert status and not re.match(r"HTTP/", status), status
        http_set(app, w, address="127.0.0.1:1/")
        status = http_send(app, w, timeout=10)
        assert status and not re.match(r"HTTP/", status), status
        http_answer_view(app, w, "Body")
        assert http_answer(app, w) == ""
        assert by_title(app, w, "Send").get("enabled", True) is not False
    finally:
        http_set(app, w, timeout=30)


@pytest.mark.case("TOOLS-062")
def test_tools_062_format_json_lays_out_the_answer_copy_takes_the_view(app, http_server):
    """TOOLS-062: Format JSON lays out the answer; Copy takes the view

    Covers: -
    Channel: ui, clipboard
    Steps: POST /echo with body "{\\"ok\\":true}" and "Format JSON" unticked; Send; tick "Format JSON"; click the answer's Copy.
    Expect: unticked the answer is one line; ticked it starts "{\\n  \\"method\\": \\"POST\\",\\n  \\"path\\": \\"/echo\\"" and parses to the same object; the clipboard equals the shown answer.
    """
    w = http_window(app)
    http_set(app, w, method="POST", address=f"{http_server.base}/echo", params="", headers="", body='{"ok":true}',
             content_type="None", user="", password="", fmt=False)
    http_send(app, w)
    http_answer_view(app, w, "Body")
    one = http_answer(app, w)
    assert "\n" not in one
    set_state(app, w, "Format JSON", True)
    laid = app.wait(lambda: "\n" in (http_answer(app, w) or "") and http_answer(app, w), 5)
    assert laid.startswith('{\n  "method": "POST",\n  "path": "/echo"'), laid[:80]
    assert json.loads(laid) == json.loads(one)
    copy = [c for c in controls(app, w) if c.get("title") == "Copy"][0]
    app.act(w, "click", path=copy["path"])
    assert app.clipboard() == laid


@pytest.mark.case("TOOLS-063")
def test_tools_063_paste_curl_command_fills_the_window_and_that_request_is_sent(app, http_server):
    """TOOLS-063: Paste curl Command fills the window and that request is sent

    Covers: -
    Channel: ui, clipboard
    Steps: Put on the clipboard "curl -X PATCH 'http://127.0.0.1:<port>/echo?x=1' -H 'X-Pasted: yes' -u me:pw --data-raw 'a=1' -k"; click "Paste curl Command"; read the controls; Send; click "Copy as curl" and read the clipboard.
    Expect: method PATCH, address ending "/echo?x=1", Headers "X-Pasted: yes", Body "a=1", user "me", password "pw", "Allow invalid certificates" ticked, "Follow redirects" unticked; the server sees PATCH with x-pasted "yes", body "a=1", Basic authorization; the copied command starts "curl -X PATCH 'http://127.0.0.1:" and contains "-H 'X-Pasted: yes'", "-u 'me:pw'", "--data-raw 'a=1'" and ends "-k".
    """
    w = http_window(app)
    http_set(app, w, fmt=False)
    app.clipboard(set=f"curl -X PATCH '{http_server.base}/echo?x=1' -H 'X-Pasted: yes' -u me:pw --data-raw 'a=1' -k")
    click(app, w, "Paste curl Command")
    pop = [c for c in controls(app, w) if c["class"] == "NSPopUpButton" and "OPTIONS" in (c.get("items") or [])][0]
    assert pop["value"] == "PATCH"
    addr = [c for c in controls(app, w) if c.get("placeholder") == "https://example.com/path"][0]["value"]
    assert addr.endswith("/echo?x=1")
    http_section(app, w, "Headers")
    assert input_view(app, w)["value"] == "X-Pasted: yes"
    http_section(app, w, "Body")
    assert input_view(app, w)["value"] == "a=1"
    http_section(app, w, "Options")
    assert field(app, w, "User name:") == "me" and field(app, w, "Password:") == "pw"
    assert state(app, w, "Allow invalid certificates") == 1 and state(app, w, "Follow redirects") == 0
    http_section(app, w, "Parameters")
    http_send(app, w)
    saw = http_json(app, w)
    assert saw["method"] == "PATCH" and saw["headers"]["x-pasted"] == "yes" and saw["body"] == "a=1"
    assert saw["headers"]["authorization"].startswith("Basic ")
    click(app, w, "Copy as curl")
    copied = app.clipboard()
    assert copied.startswith("curl -X PATCH 'http://127.0.0.1:")
    for part in ("-H 'X-Pasted: yes'", "-u 'me:pw'", "--data-raw 'a=1'"):
        assert part in copied, copied
    assert copied.endswith("-k")
    http_set(app, w, headers="", body="", user="", password="", follow=True, insecure=False)


@pytest.mark.case("TOOLS-064")
def test_tools_064_curl_commands_as_found_in_the_wild_are_understood(app):
    """TOOLS-064: curl commands as found in the wild are understood

    Covers: -
    Channel: ui, clipboard
    Steps: For each command, set it on the clipboard, click Paste curl Command and read the controls: (a) a browser's "curl 'https://example.com/api/login' \\\\\\n  -H 'accept: */*' \\\\\\n  --data-raw $'{\\"t\\":\\"a\\\\nb \\\\u0416 it\\\\'s\\"}' --compressed"; (b) "curl -sSLkX DELETE -uadmin:secret -m10 http://localhost:8080/x"; (c) "curl -G --data-urlencode 'q=a b&c' -d page=2 --url example.com/find -I"; (d) "curl --json '{\\"a\\":1}' --oauth2-bearer tok -A agent/1 https://example.com/j"; (e) "curl -d a=1 -d b=2 https://example.com/f".
    Expect: (a) POST, body with a real newline, "Ж" and "it's", Follow redirects unticked; (b) DELETE, user admin, password secret, timeout 10, invalid certificates allowed, redirects followed; (c) HEAD with address "example.com/find?q=a%20b%26c&page=2" and no body; (d) POST with headers Content-Type and Accept application/json, Authorization "Bearer tok", User-Agent "agent/1"; (e) body "a=1&b=2".
    """
    w = http_window(app)

    def paste(cmd):
        app.clipboard(set=cmd)
        click(app, w, "Paste curl Command")

    def section_text(name):
        http_section(app, w, name)
        v = input_view(app, w)["value"]
        return v

    def method():
        return [c for c in controls(app, w) if c["class"] == "NSPopUpButton" and "OPTIONS" in (c.get("items") or [])][0]["value"]

    def address():
        return [c for c in controls(app, w) if c.get("placeholder") == "https://example.com/path"][0]["value"]

    paste("curl 'https://example.com/api/login' \\\n  -H 'accept: */*' \\\n"
          "  --data-raw $'{\"t\":\"a\\nb \\u0416 it\\'s\"}' --compressed")
    assert method() == "POST" and address() == "https://example.com/api/login"
    assert section_text("Body") == '{"t":"a\nb Ж it\'s"}'
    http_section(app, w, "Options")
    assert state(app, w, "Follow redirects") == 0

    paste("curl -sSLkX DELETE -uadmin:secret -m10 http://localhost:8080/x")
    assert method() == "DELETE" and address() == "http://localhost:8080/x"
    http_section(app, w, "Options")
    assert field(app, w, "User name:") == "admin" and field(app, w, "Password:") == "secret"
    assert field(app, w, "Timeout (seconds):") == "10"
    assert state(app, w, "Allow invalid certificates") == 1 and state(app, w, "Follow redirects") == 1

    paste("curl -G --data-urlencode 'q=a b&c' -d page=2 --url example.com/find -I")
    assert method() == "HEAD" and address() == "example.com/find?q=a%20b%26c&page=2"
    assert section_text("Body") == ""

    paste("curl --json '{\"a\":1}' --oauth2-bearer tok -A agent/1 https://example.com/j")
    assert method() == "POST"
    headers = section_text("Headers")
    for line in ("Content-Type: application/json", "Accept: application/json", "Authorization: Bearer tok", "User-Agent: agent/1"):
        assert line in headers.split("\n"), headers

    paste("curl -d a=1 -d b=2 https://example.com/f")
    assert section_text("Body") == "a=1&b=2"
    http_set(app, w, method="GET", address="", headers="", body="", user="", password="", timeout=30, follow=True, insecure=False)


@pytest.mark.case("TOOLS-065")
def test_tools_065_what_is_not_a_usable_curl_command_is_refused_in_words_and_ch(app):
    """TOOLS-065: What is not a usable curl command is refused in words and changes nothing

    Covers: -
    Channel: ui, clipboard
    Steps: With the window filled (method PATCH), paste in turn "ls -la", "wget http://example.com", "curl -X POST -H 'A: b'", "curl -d @secrets.txt http://example.com", "curl -F file=@a.png http://example.com", "curl file:///etc/passwd".
    Expect: status line texts "This is not a curl command." (for ls and wget), "The command has no address.", one starting "The command reads its data from a file", one starting "Forms and uploads", one containing "not an http or https address"; the method stays PATCH each time.
    """
    w = http_window(app)
    http_set(app, w, method="PATCH")
    cases = [("ls -la", lambda s: s == "This is not a curl command."),
             ("wget http://example.com", lambda s: s == "This is not a curl command."),
             ("curl -X POST -H 'A: b'", lambda s: s == "The command has no address."),
             ("curl -d @secrets.txt http://example.com", lambda s: s.startswith("The command reads its data from a file")),
             ("curl -F file=@a.png http://example.com", lambda s: s.startswith("Forms and uploads")),
             ("curl file:///etc/passwd", lambda s: "not an http or https address" in s)]
    for cmd, ok in cases:
        app.clipboard(set=cmd)
        click(app, w, "Paste curl Command")
        s = http_status(app, w)
        assert ok(s), (cmd, s)
        pop = [c for c in controls(app, w) if c["class"] == "NSPopUpButton" and "OPTIONS" in (c.get("items") or [])][0]
        assert pop["value"] == "PATCH", cmd
    http_set(app, w, method="GET")


@pytest.mark.case("TOOLS-066")
def test_tools_066_only_http_and_https_addresses_are_sent(app):
    """TOOLS-066: Only http and https addresses are sent

    Covers: -
    Channel: ui
    Steps: Address "mailto:someone", Send; "file:///etc/passwd", Send; "ftp://example.com/x", Send; empty address, Send.
    Expect: each time, the empty address included, the status line reads "The address is not an http or https address." and the answer view is empty; no HTTP status line is shown.
    """
    w = http_window(app)
    http_set(app, w, method="GET", params="", headers="", body="")
    for address in ("mailto:someone", "file:///etc/passwd", "ftp://example.com/x", ""):
        http_set(app, w, address=address)
        click(app, w, "Send")
        s = app.wait(lambda: http_status(app, w), 5)
        assert s == "The address is not an http or https address.", (address, s)
        http_answer_view(app, w, "Body")
        assert http_answer(app, w) == ""


@pytest.mark.case("TOOLS-067")
def test_tools_067_open_in_new_document_gives_the_answer_a_tab_in_its_language(app, http_server):
    """TOOLS-067: Open in New Document gives the answer a tab in its language

    Covers: -
    Channel: ui, mcp
    Steps: POST /echo with "Format JSON" ticked, Send, click "Open in New Document"; then GET /status/404, Send, Open in New Document.
    Expect: a new tab whose text equals the answer view (laid out) and whose language is json; the second new tab holds "status 404" in Normal Text; the main window is in front.
    """
    w = http_window(app)
    http_set(app, w, method="POST", address=f"{http_server.base}/echo", params="", headers="", body='{"a":1}',
             content_type="application/json", user="", password="", fmt=True)
    http_send(app, w)
    http_answer_view(app, w, "Body")
    shown = http_answer(app, w)
    before = len(app.docs())
    click(app, w, "Open in New Document")
    app.wait(lambda: len(app.docs()) == before + 1, 5)
    assert app.text() == shown and app.doc()["language"] == "json"
    http_set(app, w, method="GET", address=f"{http_server.base}/status/404", body="")
    http_send(app, w)
    click(app, w, "Open in New Document")
    app.wait(lambda: len(app.docs()) == before + 2, 5)
    assert app.text() == "status 404" and app.doc()["language"] == "normal"
    # (the harness's app runs in the background, so "key" is not observable; the main window shows the new tab)
    main = [x for x in app.windows() if x["main_window"]][0]
    assert main["visible"] and main["title"] == app.doc()["title"]


@pytest.mark.case("TOOLS-068")
def test_tools_068_sections_are_shown_one_at_a_time_with_a_hint_on_how_to_write(app):
    """TOOLS-068: Sections are shown one at a time with a hint on how to write them

    Covers: -
    Channel: ui
    Steps: Select Parameters, Headers, Body and Options in the section control in turn, listing the visible controls.
    Expect: Parameters shows its text view and "One to a line: name=value. They are added to the address, encoded."; Headers "One to a line: Name: value"; Body its text view, "Sent as it is written, in UTF-8." and the "Content type:" popup [None, application/json, application/x-www-form-urlencoded, text/plain, application/xml]; Options shows User name, Password (secure field), "Timeout (seconds):" 30, Follow redirects, Allow invalid certificates and no hint; only the chosen section's editor is visible.
    """
    w = http_window(app)
    hints = {"Parameters": "One to a line: name=value. They are added to the address, encoded.",
             "Headers": "One to a line: Name: value",
             "Body": "Sent as it is written, in UTF-8."}
    for name in ("Parameters", "Headers", "Body", "Options"):
        http_section(app, w, name)
        labels = static_texts(app, w)
        editable_views = [c for c in text_views(app, w) if c.get("editable")]
        if name in hints:
            assert hints[name] in labels, (name, labels)
            assert len(editable_views) == 1
            assert not [h for n, h in hints.items() if n != name and h in labels]
        else:
            assert not [h for h in hints.values() if h in labels]
            assert not editable_views
            for label in ("User name:", "Password:", "Timeout (seconds):"):
                assert label in labels
            assert after_label(app, w, "Password:")["class"] == "NSSecureTextField"
            assert field(app, w, "Timeout (seconds):") == "30"
            assert by_title(app, w, "Follow redirects") and by_title(app, w, "Allow invalid certificates")
        if name == "Body":
            assert after_label(app, w, "Content type:")["items"] == [
                "None", "application/json", "application/x-www-form-urlencoded", "text/plain", "application/xml"]
    http_section(app, w, "Parameters")


@pytest.mark.case("TOOLS-069")
def test_tools_069_the_tools_menu_and_windows_are_translated_and_nothing_is_cut(app):
    """TOOLS-069: The Tools menu and windows are translated and nothing is cut

    Covers: IDM_TOOL_SHA256_GENERATE
    Channel: launch, ui, menu, snapshot
    Steps: Restart with `-NppMac.localizationFile russian.xml`; read the Tools menu; open SHA-384 Generate…, Argon2 Generate…, Base58…, Password Generator and HTTP Request; snapshot each window; restart without the option.
    Expect: the Hashes submenu is "Хеши", HTTP Request is "HTTP-запрос"; the digest window's title contains "SHA-384" and not "Generate"; the Password Generator is titled "Генератор паролей" and its uppercase box reads "Заглавные буквы (A-Z)"; the HTTP window's Send button reads "Отправить"; the snapshots show no label or button text cut off (checked by eye or by comparing control frames against their text).
    """
    try:
        app.restart(args=["-NppMac.localizationFile", "russian.xml"])
        tree = app.menu_tree("main", 2)
        tools = [t for t in tree if any(i.get("action") == "showHttpRequest:" for i in t.get("items", []))][0]
        titles = {i.get("action"): i.get("title") for i in tools["items"] if not i.get("separator")}
        assert tools["items"][0]["title"] == "Хеши"
        assert titles["showHttpRequest:"] == "HTTP-запрос"
        for path in ("Tools|Hashes|SHA-384|Generate…", "Tools|Hashes|Argon2|Generate…", "Tools|Base|Base58…",
                     "Tools|Password Generator", "Tools|HTTP Request"):
            app.run(path)
        ws = app.wait(lambda: len(tool_windows(app)) == 5 and tool_windows(app), 5)
        names = [w["title"] for w in ws]
        assert "Генератор паролей" in names and "HTTP-запрос" in names, names
        digest = [w for w in ws if "SHA-384" in w["title"]][0]
        assert "Generate" not in digest["title"], digest["title"]
        http = [w for w in ws if w["title"] == "HTTP-запрос"][0]["number"]
        assert by_title(app, http, "Отправить")
        pw = [w for w in ws if w["title"] == "Генератор паролей"][0]["number"]
        assert by_title(app, pw, "Заглавные буквы (A-Z)")
        for w in ws:
            # (a pop-up's cell size is that of its widest item, not of what it shows: left out, as the app's own suite does)
            cut = [(c["class"], c.get("title") or c.get("value")) for c in app.ui(w["number"])["controls"]
                   if c.get("fits") is False and c["class"] != "NSPopUpButton"]
            assert not cut, (w["title"], cut)
    finally:
        app.stop()
        app.start()
