"""PLUGINS: end-to-end tests (plan: plan/PLUGINS.md)."""
import base64
import html as htmllib
import json
import re
import shutil
import time
import xml.etree.ElementTree as ET

import pytest

from harness.app import App, ToolError
from harness.sci import *  # noqa: F401,F403
from _util_plugins import *  # noqa: F401,F403
from _util_plugins import FIXTURES, SAMPLE

NOTELOG = FIXTURES / "notelog.c"


@pytest.mark.case("PLUGINS-001")
def test_plugins_001_the_plugins_menu_holds_the_stand_ins_in_order_then_open_plug(app):
    """PLUGINS-001: The Plugins menu holds the stand-ins in order, then Open Plugins Folder

    Covers: IDM_SETTING_OPENPLUGINSDIR
    Channel: menu
    Steps: Dump the Plugins menu (depth 2) with no third-party plugin installed.
    Expect: items JSON, Compare, XML, Git, FTP, MIME Tools, Converter, Export, Spell Check, Markdown Preview, NppExec, separator, "Open Plugins Folder…" and nothing after it; JSON holds Format (⌥⌘J), Compact, Sort Keys, Validate, Show JSON Tree; XML holds Pretty Print, Pretty Print — Indent Attributes, Linearize, Check XML Syntax Now, Validate Against Schema…, Validate Against DTD, Evaluate XPath Expression…, Current XML Path, Current XML Path with Predicates, Apply XSL Transformation…, Escape Characters in Selection, Unescape Characters in Selection; MIME Tools holds the two Quoted-printable items, six URL Encode items, URL Decode, SAML Decode; Converter holds "ASCII -> HEX", "HEX -> ASCII", Conversion Panel; Export holds Export to RTF, Export to HTML, Copy RTF to clipboard, Copy HTML to clipboard, Copy all formats to clipboard; no item mentions Plugins Admin.
    """
    items = plugins_menu(app)
    assert titles(items) == ["JSON", "Compare", "XML", "Git", "FTP", "MIME Tools", "Converter", "Export",
                             "Spell Check", "Markdown Preview", "NppExec", "-", "Open Plugins Folder…"]
    json_items = submenu(items, "JSON")
    assert titles(json_items) == ["Format", "Compact", "Sort Keys", "Validate", "Show JSON Tree"]
    assert json_items[0].get("key") == "alt+cmd+j"
    assert titles(submenu(items, "XML")) == [
        "Pretty Print", "Pretty Print — Indent Attributes", "Linearize", "-", "Check XML Syntax Now",
        "Validate Against Schema…", "Validate Against DTD", "-", "Evaluate XPath Expression…", "Current XML Path",
        "Current XML Path with Predicates", "Apply XSL Transformation…", "-", "Escape Characters in Selection",
        "Unescape Characters in Selection"]
    assert [t for t in titles(submenu(items, "MIME Tools")) if t != "-"] == [
        "Quoted-printable Encode", "Quoted-printable Decode", "URL Encode (RFC1738)", "URL Encode (RFC1738) by line",
        "URL Encode (Extended)", "URL Encode (Extended) by line", "URL Encode (Full)", "URL Encode (Full) by line",
        "URL Decode", "SAML Decode"]
    assert [t for t in titles(submenu(items, "Converter")) if t != "-"] == ["ASCII -> HEX", "HEX -> ASCII", "Conversion Panel"]
    assert [t for t in titles(submenu(items, "Export")) if t != "-"] == [
        "Export to RTF", "Export to HTML", "Copy RTF to clipboard", "Copy HTML to clipboard", "Copy all formats to clipboard"]
    flat = json.dumps(items)
    assert "Plugins Admin" not in flat
    item = app.menu_item("IDM_SETTING_OPENPLUGINSDIR")
    assert item["enabled"]


@pytest.mark.case("PLUGINS-002")
def test_plugins_002_plugins_admin_is_absent_known_gap(app):
    """PLUGINS-002: Plugins Admin is absent (known gap)

    Covers: -
    Channel: menu, mcp
    Steps: Search the whole main menu tree and `list_commands` for "Plugins Admin" / IDM_SETTING_PLUGINADM.
    Expect: no menu item and no runnable command named Plugins Admin; running "IDM_SETTING_PLUGINADM" (if listed at all) reports it did not run.
    """
    def walk(nodes):
        for n in nodes:
            yield n.get("title") or ""
            yield from walk(n.get("items", []))
    assert not [t for t in walk(app.menu_tree("main", 5)) if "plugins admin" in t.lower()]
    # list_commands knows all of Notepad++'s ids; Plugins Admin's must not run.
    adm = app.call("list_commands", query="Plugins Admin")["commands"]
    for c in adm:
        try:
            r = app.run(c["name"], expect_ran=False)
        except ToolError:
            continue
        assert not r.get("ran"), r


@pytest.mark.case("PLUGINS-003")
def test_plugins_003_format_indents_compact_json_and_keeps_its_value(app):
    """PLUGINS-003: Format indents compact JSON and keeps its value

    Covers: -
    Channel: mcp, menu
    Steps: New document `{"b":1,"a":[1,2,{"c":null}],"s":"x"}`, caret on line 1; run `Plugins|JSON|Format`; parse the result with Python's json; undo once.
    Expect: the text has several lines, nested members indented by 4 spaces per level (jsonIndent default 4), parses to the same value as the input; the document is modified; one undo restores the original text exactly.
    """
    original = '{"b":1,"a":[1,2,{"c":null}],"s":"x"}'
    app.new(original)
    app.select(1, 1)
    app.run("Plugins|JSON|Format")
    text = app.text()
    assert text.count("\n") >= 5
    assert re.search(r'^ {4}"b"', text, re.M) and re.search(r'^ {12}"c"', text, re.M), text
    assert json.loads(text) == json.loads(original)
    assert app.doc()["modified"]
    undo(app)
    assert app.text() == original


@pytest.mark.case("PLUGINS-004")
def test_plugins_004_format_follows_the_jsonindent_preference(app):
    """PLUGINS-004: Format follows the jsonIndent preference

    Covers: -
    Channel: prefs, mcp
    Steps: Set pref jsonIndent = 2; format `{"a":{"b":[1]}}`; set jsonIndent = 8 and format again; restore the preference.
    Expect: with 2 the "b" line starts with exactly 4 spaces; with 8 it starts with exactly 16 spaces; values unchanged.
    """
    try:
        app.set_prefs(jsonIndent=2)
        app.new('{"a":{"b":[1]}}')
        app.run("Plugins|JSON|Format")
        assert re.search(r'^ {4}"b"', app.text(), re.M), app.text()
        app.set_prefs(jsonIndent=8)
        app.run("Plugins|JSON|Format")
        assert re.search(r'^ {16}"b"', app.text(), re.M), app.text()
        assert json.loads(app.text()) == {"a": {"b": [1]}}
    finally:
        app.set_prefs(jsonIndent=None)


@pytest.mark.case("PLUGINS-005")
def test_plugins_005_format_keeps_the_members_in_document_order_and_writes_key_va(app):
    """PLUGINS-005: Format keeps the members in document order and writes "key": value

    Covers: -
    Channel: mcp
    Steps: Format `{"zeta":1,"alpha":2,"mid":{"y":1,"x":2}}`.
    Expect: in the result "zeta" comes before "alpha" and "y" before "x" (JSON Viewer keeps the order; only Sort Keys reorders); each member is written `"key": value` with no space before the colon, as JSON Viewer and the port's own HTTP window write it.
    """
    app.new('{"zeta":1,"alpha":2,"mid":{"y":1,"x":2}}')
    app.run("Plugins|JSON|Format")
    text = app.text()
    assert text.index('"zeta"') < text.index('"alpha"') < text.index('"mid"'), text
    assert text.index('"y"') < text.index('"x"'), text
    assert '"zeta": 1' in text and '" :' not in text, text


@pytest.mark.case("PLUGINS-006")
def test_plugins_006_format_keeps_unicode_readable_and_slashes_unescaped(app):
    """PLUGINS-006: Format keeps Unicode readable and slashes unescaped

    Covers: -
    Channel: mcp
    Steps: Format `{"u":"Жук π 😀","p":"a\\/b","e":"\\u00e9","q":"say \\"hi\\""}`.
    Expect: the result contains "Жук π 😀", "a/b" (no "\\/"), "é" or its escape that parses back to é, and `say \\"hi\\"`; json.loads of the result equals json.loads of the input.
    """
    original = '{"u":"Жук π 😀","p":"a\\/b","e":"\\u00e9","q":"say \\"hi\\""}'
    app.new(original)
    app.run("Plugins|JSON|Format")
    text = app.text()
    assert "Жук π 😀" in text
    assert "a/b" in text and "\\/" not in text
    assert 'say \\"hi\\"' in text
    assert json.loads(text) == json.loads(original)
    assert json.loads(text)["e"] == "é"


@pytest.mark.case("PLUGINS-007")
def test_plugins_007_compact_puts_formatted_json_on_one_line_without_changing_its(app):
    """PLUGINS-007: Compact puts formatted JSON on one line without changing its value

    Covers: -
    Channel: mcp
    Steps: New document with a formatted multi-line object including nested arrays, numbers 2.5 and 12345678901234567890, true, false, null; run `Plugins|JSON|Compact`.
    Expect: the result has no newline and no space outside strings; it parses to the same value (the big integer kept exactly); true/false/null written as JSON literals.
    """
    value = {"list": [[1, 2], {"n": 2.5}], "big": 12345678901234567890, "t": True, "f": False, "z": None,
             "s": "two words"}
    app.new(json.dumps(value, indent=4))
    app.run("Plugins|JSON|Compact")
    text = app.text()
    assert "\n" not in text
    outside = re.sub(r'"(?:[^"\\]|\\.)*"', '""', text)
    assert not re.search(r"\s", outside), text
    assert json.loads(text) == value
    assert "true" in outside and "false" in outside and "null" in outside


@pytest.mark.case("PLUGINS-008")
def test_plugins_008_sort_keys_orders_the_keys_at_every_level_and_leaves_arrays_a(app):
    """PLUGINS-008: Sort Keys orders the keys at every level and leaves arrays alone

    Covers: -
    Channel: mcp
    Steps: Run `Plugins|JSON|Sort Keys` on `{"b":{"z":1,"a":2},"a":[3,1,2],"c":0}`.
    Expect: top-level key order a, b, c; inside "b" a before z; the array stays [3, 1, 2]; the result is indented like Format's.
    """
    app.new('{"b":{"z":1,"a":2},"a":[3,1,2],"c":0}')
    app.run("Plugins|JSON|Sort Keys")
    text = app.text()
    assert "\n" in text
    assert text.index('"a"') < text.index('"b"') < text.index('"c"'), text
    inner = text[text.index('"b"'):]
    assert inner.index('"a"') < inner.index('"z"'), text
    assert json.loads(text)["a"] == [3, 1, 2]


@pytest.mark.case("PLUGINS-009")
def test_plugins_009_format_compact_and_sort_keys_refuse_what_is_not_json_and_say(app):
    """PLUGINS-009: Format, Compact and Sort Keys refuse what is not JSON and say where

    Covers: -
    Channel: mcp, modal
    Steps: Document "{\\n  \\"ok\\": 1,\\n  bad\\n}"; run Format, Compact and Sort Keys in turn, reading the modal log and the caret after each; also run Format on "this is not json".
    Expect: each shows the alert "This document is not valid JSON." with informative text starting "Line 3, column 3."; the document text is unchanged; the caret is on line 3; "this is not json" gives the same alert with "Line 1, column 1.".
    """
    bad = '{\n  "ok": 1,\n  bad\n}'
    app.new(bad)
    for command in ("Plugins|JSON|Format", "Plugins|JSON|Compact", "Plugins|JSON|Sort Keys"):
        app.select(1, 1)
        shown = run_alert(app, command)
        assert len(shown) == 1 and shown[0]["message"] == "This document is not valid JSON.", shown
        assert shown[0]["informative"].startswith("Line 3, column 3."), shown
        assert app.text() == bad
        assert caret_line(app) == 3
    app.set_text("this is not json")
    shown = run_alert(app, "Plugins|JSON|Format")
    assert shown[0]["message"] == "This document is not valid JSON."
    assert shown[0]["informative"].startswith("Line 1, column 1.")
    assert app.text() == "this is not json"


@pytest.mark.case("PLUGINS-010")
def test_plugins_010_validate_says_valid_json_for_objects_arrays_and_scalars(app):
    """PLUGINS-010: Validate says "Valid JSON." for objects, arrays and scalars

    Covers: -
    Channel: mcp, modal
    Steps: Run `Plugins|JSON|Validate` on `{"a":1}`, `[1,2]`, `42`, `"text"` and `null`.
    Expect: each time one alert "Valid JSON." with empty informative text; the documents are unchanged.
    """
    app.new("")
    for text in ('{"a":1}', "[1,2]", "42", '"text"', "null"):
        app.set_text(text)
        shown = run_alert(app, "Plugins|JSON|Validate")
        assert [(a["message"], a["informative"]) for a in shown] == [("Valid JSON.", "")], (text, shown)
        assert app.text() == text


@pytest.mark.case("PLUGINS-011")
def test_plugins_011_validate_reports_the_first_error_s_line_and_column_and_moves(app):
    """PLUGINS-011: Validate reports the first error's line and column and moves the caret there

    Covers: -
    Channel: mcp, modal
    Steps: For each of: single quotes `{'a':1}`; a comment `{"a":1 // c\\n}`; an unclosed object "{\\n\\"a\\": [1,\\n2"; "{\\"ok\\": 1,\\n  \\"имя\\": x}"; a trailing comma `{"a":1,}` - run Validate.
    Expect: each gives the alert "Invalid JSON." whose informative text starts "Line <l>, column <c>." followed by the parser's message: "Line 1, column 2.", "Line 1, column 8.", "Line 3, column 2.", "Line 2, column 10." (columns counted in characters from 1, the Cyrillic letters one each); the caret is moved to that line; the trailing comma is invalid JSON too (RFC 8259; JSON Viewer rejects it) - the port currently answers "Valid JSON." (suspected defect: NSJSONSerialization is lenient).
    """
    app.new("")
    for text, where, line in (("{'a':1}", "Line 1, column 2.", 1), ('{"a":1 // c\n}', "Line 1, column 8.", 1),
                              ('{\n"a": [1,\n2', "Line 3, column 2.", 3),
                              ('{"ok": 1,\n  "имя": x}', "Line 2, column 10.", 2)):
        app.set_text(text)
        app.select(1, 1)
        shown = run_alert(app, "Plugins|JSON|Validate")
        assert len(shown) == 1 and shown[0]["message"] == "Invalid JSON.", (text, shown)
        assert shown[0]["informative"].startswith(where + "\n\n") and len(shown[0]["informative"]) > len(where) + 2, (text, shown)
        assert caret_line(app) == line
    app.set_text('{"a":1,}')
    shown = run_alert(app, "Plugins|JSON|Validate")
    assert shown[0]["message"] == "Invalid JSON.", shown


@pytest.mark.case("PLUGINS-012")
def test_plugins_012_validate_on_an_empty_document_says_why(app):
    """PLUGINS-012: Validate on an empty document says why

    Covers: -
    Channel: mcp, modal
    Steps: Empty the document; run Validate.
    Expect: the alert "Invalid JSON." with informative "Unable to parse empty data." and no "Line" prefix; nothing else changes.
    """
    app.new("")
    shown = run_alert(app, "Plugins|JSON|Validate")
    assert len(shown) == 1 and shown[0]["message"] == "Invalid JSON."
    assert shown[0]["informative"] and not shown[0]["informative"].startswith("Line")
    assert "empty" in shown[0]["informative"].lower()
    assert app.text() == ""


@pytest.mark.case("PLUGINS-013")
def test_plugins_013_show_json_tree_lists_every_node_by_its_path(app):
    """PLUGINS-013: Show JSON Tree lists every node by its path

    Covers: -
    Channel: ui, mcp
    Steps: Document `{"top":{"inner":[10,20]},"s":"x","n":null,"t":true,"f":false}`; run `Plugins|JSON|Show JSON Tree`; read the "JSON Tree" window's text view.
    Expect: a window titled "JSON Tree" whose lines include "{} = {5}", "top = {1}", "top.inner = [2]", "top.inner[0] = 10", "top.inner[1] = 20", "s = \\"x\\"", "n = null", "t = true", "f = false"; keys listed in sorted order at each level.
    """
    app.new('{"top":{"inner":[10,20]},"s":"x","n":null,"t":true,"f":false}')
    app.run("Plugins|JSON|Show JSON Tree")
    w = window_titled(app, "JSON Tree")
    lines = textviews(app, w["number"])[0]["value"].splitlines()
    for want in ("{} = {5}", "top = {1}", "top.inner = [2]", "top.inner[0] = 10", "top.inner[1] = 20",
                 's = "x"', "n = null"):
        assert want in lines, (want, lines)
    keys = [l.split(" = ")[0] for l in lines if "." not in l.split(" = ")[0] and "[" not in l.split(" = ")[0]]
    assert keys == ["{}", "f", "n", "s", "t", "top"], keys
    assert "t = true" in lines and "f = false" in lines, lines


@pytest.mark.case("PLUGINS-014")
def test_plugins_014_the_json_tree_is_refused_for_invalid_json_and_follows_the_do(app):
    """PLUGINS-014: The JSON tree is refused for invalid JSON and follows the document when shown again

    Covers: -
    Channel: ui, modal
    Steps: Show the tree for `{"a":1}`; change the document to "not json" and run Show JSON Tree; change it to `{"b":[true]}` and run it again.
    Expect: the invalid document gives the alert "This document is not valid JSON." and the tree window is not refreshed with garbage; the third run reuses the same window (same number), whose text now lists "b = [1]" and "b[0] = true" and no longer "a".
    """
    app.new('{"a":1}')
    app.run("Plugins|JSON|Show JSON Tree")
    w = window_titled(app, "JSON Tree")
    before = textviews(app, w["number"])[0]["value"]
    assert "a = 1" in before.splitlines()
    app.set_text("not json")
    shown = run_alert(app, "Plugins|JSON|Show JSON Tree")
    assert shown and shown[0]["message"] == "This document is not valid JSON."
    assert textviews(app, w["number"])[0]["value"] == before
    app.set_text('{"b":[true]}')
    app.run("Plugins|JSON|Show JSON Tree")
    trees = [x for x in others(app) if x["title"] == "JSON Tree"]
    assert [x["number"] for x in trees] == [w["number"]]
    lines = textviews(app, w["number"])[0]["value"].splitlines()
    assert "b = [1]" in lines and not any(l.startswith("a ") for l in lines), lines
    assert "b[0] = true" in lines, lines


@pytest.mark.case("PLUGINS-015")
def test_plugins_015_a_large_json_document_formats_and_compacts_in_reasonable_tim(app):
    """PLUGINS-015: A large JSON document formats and compacts in reasonable time

    Covers: -
    Channel: mcp
    Steps: Document = json.dumps of a list of 20000 small objects (one line, ~1 MB); run Format, then Compact, timing each.
    Expect: each finishes within 10 s; after both, json.loads of the text equals the original list.
    """
    value = [{"i": i, "s": f"x{i}", "l": [i, i + 1]} for i in range(20000)]
    app.new(json.dumps(value, separators=(",", ":")))
    for command in ("Plugins|JSON|Format", "Plugins|JSON|Compact"):
        began = time.monotonic()
        app.call("run_command", timeout=30, command=command)
        assert time.monotonic() - began < 10, command
    assert json.loads(app.text()) == value


@pytest.mark.case("PLUGINS-016")
def test_plugins_016_pretty_print_indents_a_one_line_document_without_changing_it(app):
    """PLUGINS-016: Pretty Print indents a one-line document without changing its content

    Covers: -
    Channel: mcp
    Steps: Document `<?xml version="1.0"?><root a="1" b="2"><item>one</item><item>two</item></root>`; run `Plugins|XML|Pretty Print`; undo once.
    Expect: the result has more than 3 lines, contains the line "    <item>one</item>" (4-space indent), and an XPath count of //item on it is 2 (via `Evaluate XPath Expression…` or Python's ElementTree); one undo restores the original.
    """
    original = '<?xml version="1.0"?><root a="1" b="2"><item>one</item><item>two</item></root>'
    app.new(original)
    app.run("Plugins|XML|Pretty Print")
    text = app.text()
    assert len(text.splitlines()) > 3
    assert "    <item>one</item>" in text.splitlines(), text
    root = ET.fromstring(text.encode("utf-8"))
    assert [i.text for i in root.iter("item")] == ["one", "two"] and root.attrib == {"a": "1", "b": "2"}
    undo(app)
    assert app.text() == original


@pytest.mark.case("PLUGINS-017")
def test_plugins_017_indent_attributes_puts_each_attribute_on_its_own_line(app):
    """PLUGINS-017: Indent Attributes puts each attribute on its own line

    Covers: -
    Channel: mcp
    Steps: Run `Plugins|XML|Pretty Print — Indent Attributes` on `<root a="1" b="two words"><item id="x" k="v">t</item></root>`.
    Expect: "a=\\"1\\"" and "b=\\"two words\\"" are on separate lines, each indented 4 spaces deeper than "<root"; the quoted value "two words" is not split; the document has more lines than plain Pretty Print gives; ElementTree parses it with the same attributes.
    """
    original = '<root a="1" b="two words"><item id="x" k="v">t</item></root>'
    app.new(original)
    app.run("Plugins|XML|Pretty Print")
    plain_lines = len(app.text().splitlines())
    app.set_text(original)
    app.run("Plugins|XML|Pretty Print — Indent Attributes")
    lines = app.text().splitlines()
    root_line = next(l for l in lines if l.lstrip().startswith("<root"))
    a_line = next(l for l in lines if 'a="1"' in l)
    b_line = next(l for l in lines if 'b="two words"' in l)
    assert a_line != b_line and a_line.strip() == 'a="1"' and b_line.strip().startswith('b="two words"'), lines
    indent = len(root_line) - len(root_line.lstrip())
    assert len(a_line) - len(a_line.lstrip()) == indent + 4
    assert len(b_line) - len(b_line.lstrip()) == indent + 4
    assert len(lines) > plain_lines
    root = ET.fromstring(app.text().encode("utf-8"))
    assert root.attrib == {"a": "1", "b": "two words"} and root.find("item").attrib == {"id": "x", "k": "v"}


@pytest.mark.case("PLUGINS-018")
def test_plugins_018_linearize_joins_the_tags_but_keeps_text_cdata_and_comments(app):
    """PLUGINS-018: Linearize joins the tags but keeps text, CDATA and comments

    Covers: -
    Channel: mcp
    Steps: Document "<r>\\n  <a>line1\\nline2</a>\\n  <!-- keep\\n  me -->\\n  <![CDATA[x\\n  y]]>\\n  <b/>\\n</r>"; run `Plugins|XML|Linearize`.
    Expect: no newline remains between one tag and the next ("</a><!--", "--><![CDATA[", "]]><b/></r>"); "line1\\nline2", the comment's inner newline and the CDATA's inner newline are kept; ElementTree reads the same text for <a>.
    """
    app.new("<r>\n  <a>line1\nline2</a>\n  <!-- keep\n  me -->\n  <![CDATA[x\n  y]]>\n  <b/>\n</r>")
    app.run("Plugins|XML|Linearize")
    text = app.text()
    assert "</a><!--" in text and "--><![CDATA[" in text and "]]><b/></r>" in text, text
    assert "<a>line1\nline2</a>" in text and "<!-- keep\n  me -->" in text and "<![CDATA[x\n  y]]>" in text
    assert ET.fromstring(text.encode("utf-8")).find("a").text == "line1\nline2"


@pytest.mark.case("PLUGINS-019")
def test_plugins_019_formatting_a_malformed_document_is_refused_with_the_place_of(app):
    """PLUGINS-019: Formatting a malformed document is refused with the place of the fault

    Covers: -
    Channel: mcp, modal
    Steps: Document "<a>\\n  <b>\\n</a>"; run Pretty Print, Indent Attributes and Linearize in turn.
    Expect: Pretty Print and Indent Attributes show "Cannot format this document.", Linearize "Cannot linearize this document.", each with informative text starting "Line 3, column"; the document is unchanged; the caret is on line 3.
    """
    bad = "<a>\n  <b>\n</a>"
    app.new(bad)
    for command, title in (("Plugins|XML|Pretty Print", "Cannot format this document."),
                           ("Plugins|XML|Pretty Print — Indent Attributes", "Cannot format this document."),
                           ("Plugins|XML|Linearize", "Cannot linearize this document.")):
        app.select(1, 1)
        shown = run_alert(app, command)
        assert len(shown) == 1 and shown[0]["message"] == title, shown
        assert shown[0]["informative"].startswith("Line 3, column"), shown
        assert app.text() == bad
        assert caret_line(app) == 3


@pytest.mark.case("PLUGINS-020")
def test_plugins_020_check_xml_syntax_now_says_valid_or_where_it_is_not(app):
    """PLUGINS-020: Check XML Syntax Now says valid, or where it is not

    Covers: -
    Channel: mcp, modal
    Steps: Run `Plugins|XML|Check XML Syntax Now` on "<a><b/></a>", then on "<a>\\n  <b>\\n</a>", then on "<a>Жук &amp; &bogus;</a>".
    Expect: "The document is valid XML."; then "The document is not well formed." with "Line 3, column …" and the caret on line 3; the undefined entity is reported as not well formed too.
    """
    app.new("<a><b/></a>")
    assert [a["message"] for a in run_alert(app, "Plugins|XML|Check XML Syntax Now")] == ["The document is valid XML."]
    app.set_text("<a>\n  <b>\n</a>")
    app.select(1, 1)
    shown = run_alert(app, "Plugins|XML|Check XML Syntax Now")
    assert shown[0]["message"] == "The document is not well formed."
    assert shown[0]["informative"].startswith("Line 3, column")
    assert caret_line(app) == 3
    app.set_text("<a>Жук &amp; &bogus;</a>")
    shown = run_alert(app, "Plugins|XML|Check XML Syntax Now")
    assert shown[0]["message"] == "The document is not well formed.", shown


@pytest.mark.case("PLUGINS-021")
def test_plugins_021_validate_against_dtd_checks_the_internal_dtd(app):
    """PLUGINS-021: Validate Against DTD checks the internal DTD

    Covers: -
    Channel: mcp, modal
    Steps: Run `Plugins|XML|Validate Against DTD` on a note with `<!DOCTYPE note [<!ELEMENT note (to)><!ELEMENT to (#PCDATA)>]>` and body `<note><to>x</to></note>`; then with body `<note><from>x</from></note>`.
    Expect: "The document is valid XML."; then "The document does not match its DTD." whose informative text names "from" and the expected "(to)" on line 3.
    """
    head = '<?xml version="1.0"?>\n<!DOCTYPE note [<!ELEMENT note (to)><!ELEMENT to (#PCDATA)>]>\n'
    app.new(head + "<note><to>x</to></note>")
    assert [a["message"] for a in run_alert(app, "Plugins|XML|Validate Against DTD")] == ["The document is valid XML."]
    app.set_text(head + "<note><from>x</from></note>")
    shown = run_alert(app, "Plugins|XML|Validate Against DTD")
    assert shown[0]["message"] == "The document does not match its DTD."
    info = shown[0]["informative"]
    assert "from" in info and "(to)" in info and "Line 3" in info, info


@pytest.mark.case("PLUGINS-022")
def test_plugins_022_validate_against_schema_checks_the_document_against_a_chosen(app, tmp):
    """PLUGINS-022: Validate Against Schema… checks the document against a chosen XSD

    Covers: -
    Channel: mcp, modal, files
    Steps: Write `note.xsd` (element note with a sequence of one element "to" of xs:string); document `<note><to>you</to></note>`; queue the XSD path and run `Plugins|XML|Validate Against Schema…`; change the document to `<note><wrong>x</wrong></note>` and repeat; repeat with a cancelled panel; repeat with a file "not a schema" as the XSD.
    Expect: the open panel is titled "Choose an XSD schema"; first "The document is valid XML."; second "The document does not match the schema." with libxml2's text naming "wrong"; the cancelled panel shows no alert; the bad schema gives an alert whose text says the schema is not valid (or libxml2's reason).
    """
    xsd = tmp / "note.xsd"
    xsd.write_text('<?xml version="1.0"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">'
                   '<xs:element name="note"><xs:complexType><xs:sequence>'
                   '<xs:element name="to" type="xs:string"/></xs:sequence></xs:complexType></xs:element></xs:schema>')
    app.new("<note><to>you</to></note>")
    app.answers(panels=[str(xsd)])
    app.run("Plugins|XML|Validate Against Schema…")
    log = app.modal_log()
    panel = [e for e in log if e["kind"] == "open"]
    assert panel and panel[0]["title"] == "Choose an XSD schema", log
    assert [e["message"] for e in log if e["kind"] == "alert"] == ["The document is valid XML."]
    app.set_text("<note><wrong>x</wrong></note>")
    app.answers(panels=[str(xsd)])
    app.run("Plugins|XML|Validate Against Schema…")
    shown = alerts(app)
    assert shown[0]["message"] == "The document does not match the schema." and "wrong" in shown[0]["informative"], shown
    app.answers(panels=[None])
    app.run("Plugins|XML|Validate Against Schema…")
    assert alerts(app) == []
    junk = tmp / "junk.xsd"
    junk.write_text("not a schema")
    app.answers(panels=[str(junk)])
    app.run("Plugins|XML|Validate Against Schema…")
    shown = alerts(app)
    assert len(shown) == 1 and shown[0]["informative"].strip(), shown


@pytest.mark.case("PLUGINS-023")
def test_plugins_023_evaluate_xpath_expression_lists_the_matches_in_an_alert(app):
    """PLUGINS-023: Evaluate XPath Expression… lists the matches in an alert

    Covers: -
    Channel: mcp, modal
    Steps: Document `<catalog><book id="a"><title>First</title></book><book id="b"><title>Second</title></book></catalog>`; queue a prompt answer {button 1, field "//title/text()"} and run `Plugins|XML|Evaluate XPath Expression…`; repeat with "//book/@id", "//missing", "//[[", and a Cancel answer (button 2).
    Expect: the prompt reads "XPath expression" with default "//*"; results: alert "XPath" with informative "2 result(s):\\n\\nFirst\\nSecond"; "2 result(s):\\n\\na\\nb"; "The expression matched nothing."; for "//[[" an alert "XPath" carrying the engine's error text; Cancel shows no second alert.
    """
    app.new('<catalog><book id="a"><title>First</title></book><book id="b"><title>Second</title></book></catalog>')

    def xpath(expression):
        app.modal_log(clear=True)
        app.answers(alerts=[{"button": 1, "field": expression}])
        app.run("Plugins|XML|Evaluate XPath Expression…")
        return alerts(app)
    shown = xpath("//title/text()")
    assert shown[0]["message"] == "XPath expression" and shown[0]["fields"] == ["//*"], shown
    assert shown[1]["message"] == "XPath" and shown[1]["informative"] == "2 result(s):\n\nFirst\nSecond", shown
    assert xpath("//book/@id")[1]["informative"] == "2 result(s):\n\na\nb"
    assert xpath("//missing")[1]["informative"] == "The expression matched nothing."
    bad = xpath("//[[")[1]
    assert bad["message"] == "XPath" and bad["informative"] and "result(s)" not in bad["informative"], bad
    app.modal_log(clear=True)
    app.answers(alerts=[2])
    app.run("Plugins|XML|Evaluate XPath Expression…")
    assert len(alerts(app)) == 1


@pytest.mark.case("PLUGINS-024")
def test_plugins_024_xpath_on_a_malformed_document_and_copy_of_the_result(app):
    """PLUGINS-024: XPath on a malformed document, and Copy of the result

    Covers: -
    Channel: mcp, modal, clipboard
    Steps: Document "<a><b></a>", XPath "//b"; then valid document `<r><x>1</x></r>`, XPath "//x/text()" answered with the alert's "Copy" button (queued alerts: {button 1, field}, "Copy").
    Expect: first alert informative "The document is not well formed."; the second puts "1 result(s):\\n\\n1" on the clipboard.
    """
    app.new("<a><b></a>")
    app.answers(alerts=[{"button": 1, "field": "//b"}])
    app.run("Plugins|XML|Evaluate XPath Expression…")
    assert alerts(app)[1]["informative"] == "The document is not well formed."
    app.set_text("<r><x>1</x></r>")
    app.clipboard(set="")
    app.answers(alerts=[{"button": 1, "field": "//x/text()"}, "Copy"])
    app.run("Plugins|XML|Evaluate XPath Expression…")
    assert app.clipboard() == "1 result(s):\n\n1"


@pytest.mark.case("PLUGINS-025")
def test_plugins_025_current_xml_path_works_on_a_document_still_being_typed(app):
    """PLUGINS-025: Current XML Path works on a document still being typed

    Covers: -
    Channel: mcp, modal
    Steps: Document "<root>\\n  <list>\\n    <item>one</item>\\n    <item>tw" with the caret at the end; run `Plugins|XML|Current XML Path`, then `…with Predicates`; then put the caret at position 0 of `<root><a/></root>` and run Current XML Path.
    Expect: alert "Current XML Path" with informative "/root/list/item", then "/root[1]/list[1]/item[2]"; at position 0 "The current node cannot be resolved."; each alert has the buttons OK and Copy.
    """
    app.new("<root>\n  <list>\n    <item>one</item>\n    <item>tw")
    app.sci(SCI_DOCUMENTEND)
    shown = run_alert(app, "Plugins|XML|Current XML Path")
    assert (shown[0]["message"], shown[0]["informative"]) == ("Current XML Path", "/root/list/item")
    assert shown[0]["buttons"] == ["OK", "Copy"]
    shown = run_alert(app, "Plugins|XML|Current XML Path with Predicates")
    assert shown[0]["informative"] == "/root[1]/list[1]/item[2]"
    app.set_text("<root><a/></root>")
    app.sci(SCI_GOTOPOS, 0)
    shown = run_alert(app, "Plugins|XML|Current XML Path")
    assert shown[0]["informative"] == "The current node cannot be resolved."


@pytest.mark.case("PLUGINS-026")
def test_plugins_026_apply_xsl_transformation_opens_the_result_in_a_new_document(app, tmp):
    """PLUGINS-026: Apply XSL Transformation… opens the result in a new document

    Covers: -
    Channel: mcp, modal, files
    Steps: Write a stylesheet that outputs `<titles><t>…</t></titles>` for each //title; with the catalog of PLUGINS-023 in front queue its path and run `Plugins|XML|Apply XSL Transformation…`; then with a file that is not XSL; then with a cancelled panel.
    Expect: the panel is titled "Choose an XSL stylesheet"; a new tab opens containing "<t>First</t>" and "<t>Second</t>"; the source document is unchanged; the bad stylesheet shows an alert "XSL" and no new tab; cancel opens nothing.
    """
    catalog = '<catalog><book id="a"><title>First</title></book><book id="b"><title>Second</title></book></catalog>'
    sheet = tmp / "titles.xsl"
    sheet.write_text('<?xml version="1.0"?><xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">'
                     '<xsl:output method="xml"/><xsl:template match="/"><titles><xsl:for-each select="//title">'
                     '<t><xsl:value-of select="."/></t></xsl:for-each></titles></xsl:template></xsl:stylesheet>')
    source = app.new(catalog)["index"]
    count = len(app.docs())
    app.answers(panels=[str(sheet)])
    app.run("Plugins|XML|Apply XSL Transformation…")
    log = app.modal_log()
    assert [e["title"] for e in log if e["kind"] == "open"] == ["Choose an XSL stylesheet"]
    app.wait(lambda: len(app.docs()) == count + 1)
    result = app.text()
    assert "<t>First</t>" in result and "<t>Second</t>" in result
    assert app.text(source) == catalog
    app.select(1, document=source)
    junk = tmp / "junk.xsl"
    junk.write_text("not xsl")
    app.answers(panels=[str(junk)])
    app.run("Plugins|XML|Apply XSL Transformation…")
    shown = alerts(app)
    assert shown and shown[0]["message"] == "XSL", shown
    assert len(app.docs()) == count + 1
    app.answers(panels=[None])
    app.run("Plugins|XML|Apply XSL Transformation…")
    assert alerts(app) == [] and len(app.docs()) == count + 1


@pytest.mark.case("PLUGINS-027")
def test_plugins_027_escape_and_unescape_change_only_the_selection_and_round_trip(app):
    """PLUGINS-027: Escape and Unescape change only the selection and round-trip

    Covers: -
    Channel: mcp
    Steps: Document "keep <x> | a <b> & \\"c\\" 'd' Жук"; select from "a" to the end; run `Plugins|XML|Escape Characters in Selection`; select the same (now longer) part and run Unescape.
    Expect: after Escape: "keep <x> | a &lt;b&gt; &amp; &quot;c&quot; &apos;d&apos; Жук" (the unselected "<x>" untouched, Cyrillic untouched); after Unescape the original text exactly.
    """
    original = "keep <x> | a <b> & \"c\" 'd' Жук"
    app.new(original)
    start = original.index("a <b") + 1
    app.select(1, start, 1, len(original) + 1)
    app.run("Plugins|XML|Escape Characters in Selection")
    escaped = "keep <x> | a &lt;b&gt; &amp; &quot;c&quot; &apos;d&apos; Жук"
    assert app.text() == escaped
    app.select(1, start, 1, len(escaped) + 1)
    app.run("Plugins|XML|Unescape Characters in Selection")
    assert app.text() == original


@pytest.mark.case("PLUGINS-028")
def test_plugins_028_quoted_printable_encode_escapes_non_ascii_and_and_wraps_long(app):
    """PLUGINS-028: Quoted-printable Encode escapes non-ASCII and "=" and wraps long lines

    Covers: -
    Channel: mcp
    Steps: Select all of "Ünïcödé = fun\\n" and run `Plugins|MIME Tools|Quoted-printable Encode`; then select a line of 120 "x" and encode it.
    Expect: "=C3=9Cn=C3=AFc=C3=B6d=C3=A9 =3D fun\\n"; the long line is split by "=\\r\\n" soft breaks into pieces of at most 76 characters.
    """
    app.new("")
    assert select_all_run(app, "Ünïcödé = fun\n", "Plugins|MIME Tools|Quoted-printable Encode") == \
        "=C3=9Cn=C3=AFc=C3=B6d=C3=A9 =3D fun\n"
    encoded = select_all_run(app, "x" * 120, "Plugins|MIME Tools|Quoted-printable Encode")
    pieces = encoded.split("\r\n")
    assert len(pieces) > 1 and all(len(p) <= 76 for p in pieces), pieces
    assert all(p.endswith("=") for p in pieces[:-1])
    assert "".join(p[:-1] for p in pieces[:-1]) + pieces[-1] == "x" * 120


@pytest.mark.case("PLUGINS-029")
def test_plugins_029_quoted_printable_decode_restores_the_text_and_refuses_bad_es(app):
    """PLUGINS-029: Quoted-printable Decode restores the text and refuses bad escapes

    Covers: -
    Channel: mcp, modal
    Steps: Select-all decode of the two encodings from PLUGINS-028; then "a=\\nb=\\r\\nc"; then "=ZZ".
    Expect: the originals come back exactly; "abc"; for "=ZZ" the alert "The selection is not valid Quoted-printable." and the text unchanged.
    """
    app.new("")
    assert select_all_run(app, "=C3=9Cn=C3=AFc=C3=B6d=C3=A9 =3D fun\n", "Plugins|MIME Tools|Quoted-printable Decode") == \
        "Ünïcödé = fun\n"
    long = select_all_run(app, "x" * 120, "Plugins|MIME Tools|Quoted-printable Encode")
    assert select_all_run(app, long, "Plugins|MIME Tools|Quoted-printable Decode") == "x" * 120
    assert select_all_run(app, "a=\nb=\r\nc", "Plugins|MIME Tools|Quoted-printable Decode") == "abc"
    assert select_all_run(app, "=ZZ", "Plugins|MIME Tools|Quoted-printable Decode") == "=ZZ"
    assert [a["message"] for a in alerts(app)] == ["The selection is not valid Quoted-printable."]


@pytest.mark.case("PLUGINS-030")
def test_plugins_030_the_six_url_encode_commands(app):
    """PLUGINS-030: The six URL Encode commands

    Covers: -
    Channel: mcp
    Steps: Parametrized: select all and run each: "URL Encode (RFC1738)" on "a b&c(d)é" ; "URL Encode (Extended)" on "a(d)+x"; "URL Encode (Full)" on "Ab"; the three "by line" variants on "a b\\nc d" / "(x)\\n(y)" / "A\\nB".
    Expect: "a%20b%26c(d)%C3%A9"; "a%28d%29%2Bx"; "%41%62"; by line: "a%20b\\nc%20d", "%28x%29\\n%28y%29", "%41\\n%42" (line breaks kept as they are); without "by line" a newline is encoded (%0A).
    """
    app.new("")
    for command, text, want in (
            ("URL Encode (RFC1738)", "a b&c(d)é", "a%20b%26c(d)%C3%A9"),
            ("URL Encode (Extended)", "a(d)+x", "a%28d%29%2Bx"),
            ("URL Encode (Full)", "Ab", "%41%62"),
            ("URL Encode (RFC1738) by line", "a b\nc d", "a%20b\nc%20d"),
            ("URL Encode (Extended) by line", "(x)\n(y)", "%28x%29\n%28y%29"),
            ("URL Encode (Full) by line", "A\nB", "%41\n%42"),
            ("URL Encode (RFC1738)", "a b\nc", "a%20b%0Ac")):
        assert select_all_run(app, text, "Plugins|MIME Tools|" + command) == want, command


@pytest.mark.case("PLUGINS-031")
def test_plugins_031_url_decode_decodes_triplets_and_leaves_and_a_stray(app):
    """PLUGINS-031: URL Decode decodes triplets and leaves "+" and a stray "%"

    Covers: -
    Channel: mcp
    Steps: Select all and run `Plugins|MIME Tools|URL Decode` on "a%20b%26c%C3%A9"; then on "1+1%3D2 and 100%".
    Expect: "a b&cé"; "1+1=2 and 100%".
    """
    app.new("")
    assert select_all_run(app, "a%20b%26c%C3%A9", "Plugins|MIME Tools|URL Decode") == "a b&cé"
    assert select_all_run(app, "1+1%3D2 and 100%", "Plugins|MIME Tools|URL Decode") == "1+1=2 and 100%"


@pytest.mark.case("PLUGINS-032")
def test_plugins_032_saml_decode_inflates_a_redirect_binding_message(app):
    """PLUGINS-032: SAML Decode inflates a redirect-binding message

    Covers: -
    Channel: mcp, modal
    Steps: Select all and run `Plugins|MIME Tools|SAML Decode` on "sylOzM0psHIsLcnIC0otLE0tLlHwdLFVqjBUsstIzcnJt9HHVGEHAA%3D%3D"; then on "PD94bWwgdmVyc2lvbj0iMS4wIj8+"; then on "zzz".
    Expect: `<samlp:AuthnRequest ID="x1">hello</samlp:AuthnRequest>`; text starting "<?xml"; for "zzz" the alert "The selection is not a SAML message." and the text unchanged.
    """
    app.new("")
    assert select_all_run(app, "sylOzM0psHIsLcnIC0otLE0tLlHwdLFVqjBUsstIzcnJt9HHVGEHAA%3D%3D",
                          "Plugins|MIME Tools|SAML Decode") == '<samlp:AuthnRequest ID="x1">hello</samlp:AuthnRequest>'
    assert select_all_run(app, "PD94bWwgdmVyc2lvbj0iMS4wIj8+", "Plugins|MIME Tools|SAML Decode").startswith("<?xml")
    assert select_all_run(app, "zzz", "Plugins|MIME Tools|SAML Decode") == "zzz"
    assert [a["message"] for a in alerts(app)] == ["The selection is not a SAML message."]


@pytest.mark.case("PLUGINS-033")
def test_plugins_033_mime_commands_work_on_the_selection_only_as_one_undo_step(app):
    """PLUGINS-033: MIME commands work on the selection only, as one undo step

    Covers: -
    Channel: mcp, modal
    Steps: Document "keep foobar keep", select "foobar", run URL Encode (Full); undo once; then with no selection run each MIME command.
    Expect: "keep %66%6F%6F%62%61%72 keep"; one undo gives the original; with no selection nothing changes and no alert is shown.
    """
    original = "keep foobar keep"
    app.new(original)
    app.select(1, 6, 1, 12)
    app.run("Plugins|MIME Tools|URL Encode (Full)")
    assert app.text() == "keep %66%6F%6F%62%61%72 keep"
    undo(app)
    assert app.text() == original
    app.select(1, 3)
    app.modal_log(clear=True)
    for command in ("Quoted-printable Encode", "Quoted-printable Decode", "URL Encode (RFC1738)",
                    "URL Encode (RFC1738) by line", "URL Encode (Extended)", "URL Encode (Extended) by line",
                    "URL Encode (Full)", "URL Encode (Full) by line", "URL Decode", "SAML Decode"):
        app.run("Plugins|MIME Tools|" + command)
        assert app.text() == original, command
    assert alerts(app) == []


@pytest.mark.case("PLUGINS-034")
def test_plugins_034_ascii_hex_with_the_default_settings(app):
    """PLUGINS-034: ASCII -> HEX with the default settings

    Covers: -
    Channel: mcp
    Steps: Select all of "AB" and run `Plugins|Converter|ASCII -> HEX`; then "Я j".
    Expect: "4142"; "d0af206a" (UTF-8 bytes, lowercase, no spaces).
    """
    app.new("")
    assert select_all_run(app, "AB", "Plugins|Converter|ASCII -> HEX") == "4142"
    assert select_all_run(app, "Я j", "Plugins|Converter|ASCII -> HEX") == "d0af206a"


@pytest.mark.case("PLUGINS-035")
def test_plugins_035_ascii_hex_follows_the_converter_settings_and_the_document_s(app):
    """PLUGINS-035: ASCII -> HEX follows the converter settings and the document's line ends

    Covers: -
    Channel: prefs, mcp
    Steps: Set prefs converterInsertSpace = true, converterUppercase = true, converterHexPerLine = 2; convert "ABCj" in an LF document and in a CRLF document; restore the prefs.
    Expect: LF: "41 42\\n43 6A\\n"; CRLF: "41 42\\r\\n43 6A\\r\\n"; with only insertSpace on "AB" gives "41 42 " (the plugin's trailing space).
    """
    try:
        app.set_prefs(converterInsertSpace=True, converterUppercase=True, converterHexPerLine=2)
        app.new("")
        assert select_all_run(app, "ABCj", "Plugins|Converter|ASCII -> HEX") == "41 42\n43 6A\n"
        app.new("")
        app.run("IDM_FORMAT_TODOS")
        assert app.doc()["eol"] == "CRLF"
        assert select_all_run(app, "ABCj", "Plugins|Converter|ASCII -> HEX") == "41 42\r\n43 6A\r\n"
        app.set_prefs(converterUppercase=None, converterHexPerLine=None)
        app.new("")
        assert select_all_run(app, "AB", "Plugins|Converter|ASCII -> HEX") == "41 42 "
    finally:
        app.set_prefs(converterInsertSpace=None, converterUppercase=None, converterHexPerLine=None)


@pytest.mark.case("PLUGINS-036")
def test_plugins_036_hex_ascii_reads_plain_spaced_and_multi_line_hex_and_refuses(app):
    """PLUGINS-036: HEX -> ASCII reads plain, spaced and multi-line hex and refuses bad input

    Covers: -
    Channel: mcp, modal
    Steps: Select all and run `Plugins|Converter|HEX -> ASCII` on "4142", "41 42", "41\\n42", "D0AF"; then on "414", "41 4243", "4Z", "4".
    Expect: "AB", "AB", "AB", "Я"; each bad input gives the alert "Hex format is not conformed" and leaves the text unchanged.
    """
    app.new("")
    for text, want in (("4142", "AB"), ("41 42", "AB"), ("41\n42", "AB"), ("D0AF", "Я")):
        assert select_all_run(app, text, "Plugins|Converter|HEX -> ASCII") == want, text
        assert alerts(app) == []
    for text in ("414", "41 4243", "4Z", "4"):
        assert select_all_run(app, text, "Plugins|Converter|HEX -> ASCII") == text
        assert [a["message"] for a in alerts(app)] == ["Hex format is not conformed"], text


@pytest.mark.case("PLUGINS-037")
def test_plugins_037_the_conversion_panel_shows_one_value_in_every_base(app):
    """PLUGINS-037: The Conversion Panel shows one value in every base

    Covers: -
    Channel: ui
    Steps: Run `Plugins|Converter|Conversion Panel`; set the Hexadecimal field ("hex") to "ff"; then the Character field ("ascii") to "A"; then Binary to "1010"; then Decimal to "12a", then Decimal to "7".
    Expect: the window is titled "Conversion Panel" with rows Character, Decimal, Hexadecimal, Binary, Octal; ff gives dec 255, bin 11111111, oct 377, character ÿ; "A" gives dec 65, hex 41; "1010" gives dec 10; "12a" puts no value derived from it in the other rows; "7" makes all rows agree again (hex 7, bin 111, oct 7).
    """
    app.run("Plugins|Converter|Conversion Panel")
    w = window_titled(app, "Conversion Panel")["number"]
    labels = [c["value"] for c in app.controls(w, editable=False) if c["class"] == "NSTextField"]
    assert labels[:5] == ["Character:", "Decimal:", "Hexadecimal:", "Binary:", "Octal:"], labels

    def rows():
        return {c["id"]: c["value"] for c in app.controls(w) if c.get("id")}

    def type_in(field, value):
        app.act(w, "set_value", value, id=field)
        app.idle(0.05)
        return rows()
    r = type_in("hex", "ff")
    assert (r["dec"], r["bin"], r["oct"], r["ascii"]) == ("255", "11111111", "377", "ÿ")
    r = type_in("ascii", "A")
    assert (r["dec"], r["hex"].lower()) == ("65", "41")
    before = type_in("bin", "1010")
    assert before["dec"] == "10"
    r = type_in("dec", "12a")
    assert {k: v for k, v in r.items() if k != "dec"} == {k: v for k, v in before.items() if k != "dec"}
    r = type_in("dec", "7")
    assert (r["hex"], r["bin"], r["oct"]) == ("7", "111", "7")


@pytest.mark.case("PLUGINS-038")
def test_plugins_038_the_conversion_panel_s_insert_and_copy(app):
    """PLUGINS-038: The Conversion Panel's Insert and Copy

    Covers: -
    Channel: ui, mcp, clipboard
    Steps: Empty document; in the panel set hex "ff"; click Insert on the Decimal row; click Copy on the Binary row.
    Expect: the document reads "255" with the caret after it; the clipboard reads "11111111".
    """
    app.new("")
    app.run("Plugins|Converter|Conversion Panel")
    w = window_titled(app, "Conversion Panel")["number"]
    app.act(w, "set_value", "ff", id="hex")
    app.act(w, "click", path="0.1.0.1.3")      # Insert, Decimal row
    assert app.text() == "255"
    assert app.selection()["caret"]["column"] == 4
    app.act(w, "click", path="0.1.0.3.2")      # Copy, Binary row
    assert app.clipboard() == "11111111"


@pytest.mark.case("PLUGINS-039")
def test_plugins_039_export_to_rtf_writes_the_styled_text_to_the_chosen_file(app, tmp):
    """PLUGINS-039: Export to RTF writes the styled text to the chosen file

    Covers: -
    Channel: mcp, modal, files
    Steps: Open `t_export.py` = "# comment <>&\\nx = 1 # Я\\n" from `tmp`, no selection; queue `out.rtf` and run `Plugins|Export|Export to RTF`; convert the file with `textutil -convert txt -stdout`.
    Expect: the save panel proposes the name "t_export.rtf"; the file starts "{\\rtf1" and contains "\\colortbl", "\\cf", "\\par" and "ၱ?" (Я); textutil gives back "# comment <>&\\nx = 1 # Я".
    """
    src = tmp / "t_export.py"
    src.write_text("# comment <>&\nx = 1 # Я\n", encoding="utf-8")
    app.open(src)
    app.select(1, 1)
    out = tmp / "out.rtf"
    app.answers(panels=[str(out)])
    app.run("Plugins|Export|Export to RTF")
    saves = [e for e in app.modal_log() if e["kind"] == "save"]
    assert saves and saves[0]["name"] == "t_export.rtf", saves
    rtf = out.read_bytes().decode("ascii")
    assert rtf.startswith("{\\rtf1") and "\\colortbl" in rtf and "\\cf" in rtf and "\\par" in rtf and "\\u1071?" in rtf
    assert textutil_text(out).rstrip("\n") == "# comment <>&\nx = 1 # Я"


@pytest.mark.case("PLUGINS-040")
def test_plugins_040_export_to_html_writes_a_page_in_the_editor_s_colours(app, tmp):
    """PLUGINS-040: Export to HTML writes a page in the editor's colours

    Covers: -
    Channel: mcp, modal, files
    Steps: Same document; queue `out.html`; run `Plugins|Export|Export to HTML`; read the file.
    Expect: proposed name "t_export.html"; UTF-8 with `<meta charset="utf-8">`, a `<title>` naming the document, a `<pre style=` block with the default style's colours, `<span` runs with "color:#" (more than one distinct colour), "&lt;&gt;&amp;" escaped, and "Я" as UTF-8.
    """
    src = tmp / "t_export.py"
    src.write_text("# comment <>&\nx = 1 # Я\n", encoding="utf-8")
    app.open(src)
    app.select(1, 1)
    out = tmp / "out.html"
    app.answers(panels=[str(out)])
    app.run("Plugins|Export|Export to HTML")
    saves = [e for e in app.modal_log() if e["kind"] == "save"]
    assert saves and saves[0]["name"] == "t_export.html", saves
    page = out.read_text(encoding="utf-8")
    assert '<meta charset="utf-8">' in page and "<title>t_export" in page
    assert "<pre style=" in page and "&lt;&gt;&amp;" in page and "Я" in page
    assert len(set(re.findall(r"<span style=\"color:(#[0-9a-fA-F]{6})", page))) > 1


@pytest.mark.case("PLUGINS-041")
def test_plugins_041_the_exported_colours_are_the_lexer_s(app, tmp):
    """PLUGINS-041: The exported colours are the lexer's

    Covers: -
    Channel: mcp, files
    Steps: Python document "def f():\\n    return 1\\n"; export to HTML; read the foreground of the style at "def" (SCI_GETSTYLEAT then SCI_STYLEGETFORE) and convert BGR to #rrggbb.
    Expect: the span holding "def" has that colour; the plain identifier "f" has a different colour.
    """
    app.new("def f():\n    return 1\n", language="python")
    out = tmp / "colours.html"
    app.answers(panels=[str(out)])
    app.run("Plugins|Export|Export to HTML")
    page = out.read_text(encoding="utf-8")

    def colour_at(pos):
        bgr = app.sci(SCI_STYLEGETFORE, app.sci(SCI_GETSTYLEAT, pos))
        return "#%02x%02x%02x" % (bgr & 0xFF, (bgr >> 8) & 0xFF, (bgr >> 16) & 0xFF)
    spans = dict((text, colour.lower()) for colour, text in re.findall(r'<span style="color:(#[0-9a-fA-F]{6})[^"]*">([^<]*)</span>', page))
    assert spans["def"] == colour_at(0)
    assert spans["f"] == colour_at(4) and spans["f"] != spans["def"]


@pytest.mark.case("PLUGINS-042")
def test_plugins_042_with_a_selection_only_the_selection_is_exported(app, tmp):
    """PLUGINS-042: With a selection only the selection is exported

    Covers: -
    Channel: mcp, files
    Steps: In the document of PLUGINS-039 select the first 9 characters ("# comment"); export to HTML and to RTF.
    Expect: the HTML's text content and textutil's reading of the RTF are "# comment" only.
    """
    src = tmp / "t_export.py"
    src.write_text("# comment <>&\nx = 1 # Я\n", encoding="utf-8")
    app.open(src)
    app.select(1, 1, 1, 10)
    html_out, rtf_out = tmp / "part.html", tmp / "part.rtf"
    app.answers(panels=[str(html_out)])
    app.run("Plugins|Export|Export to HTML")
    app.answers(panels=[str(rtf_out)])
    app.run("Plugins|Export|Export to RTF")
    pre = re.search(r"<pre[^>]*>(.*)</pre>", html_out.read_text(encoding="utf-8"), re.S).group(1)
    assert htmllib.unescape(re.sub(r"<[^>]+>", "", pre)) == "# comment"
    assert textutil_text(rtf_out).rstrip("\n") == "# comment"


@pytest.mark.case("PLUGINS-043")
def test_plugins_043_cancelling_the_save_panel_writes_nothing(app, tmp):
    """PLUGINS-043: Cancelling the save panel writes nothing

    Covers: -
    Channel: modal, files
    Steps: Queue a cancel (None) and run Export to RTF, then Export to HTML.
    Expect: no file appears in the default folder or `tmp`; no alert is logged; the document is unchanged.
    """
    app.new("some text")
    before = sorted(p.name for p in tmp.iterdir())
    app.answers(panels=[None, None])
    app.run("Plugins|Export|Export to RTF")
    app.run("Plugins|Export|Export to HTML")
    log = app.modal_log()
    assert [e["kind"] for e in log] == ["save", "save"] and all(e["answered"] in (None, "cancel") for e in log), log
    assert sorted(p.name for p in tmp.iterdir()) == before
    assert app.text() == "some text"


@pytest.mark.case("PLUGINS-044")
def test_plugins_044_the_clipboard_exports_carry_exactly_their_formats(app, tmp):
    """PLUGINS-044: The clipboard exports carry exactly their formats

    Covers: -
    Channel: mcp, clipboard
    Steps: With the export document in front run `Copy RTF to clipboard`, `Copy HTML to clipboard`, `Copy all formats to clipboard`, reading `e2e_clipboard` types (and data for public.rtf / public.html) after each.
    Expect: RTF: types include public.utf8-plain-text and public.rtf, not public.html; HTML: plain text and public.html, not public.rtf; all: all three; the plain text is always the exported text exactly; the RTF data starts "{\\rtf1"; the HTML contains "<pre".
    """
    src = tmp / "t_export.py"
    src.write_text("# comment <>&\nx = 1 # Я\n", encoding="utf-8")
    app.open(src)
    app.select(1, 1)
    want = "# comment <>&\nx = 1 # Я\n"
    for command, rtf, html in (("Copy RTF to clipboard", True, False), ("Copy HTML to clipboard", False, True),
                               ("Copy all formats to clipboard", True, True)):
        app.clipboard(set="")
        app.run("Plugins|Export|" + command)
        info = app.clipboard_info()
        types = info["types"]
        assert "public.utf8-plain-text" in types and info["text"] == want, (command, info)
        assert ("public.rtf" in types) == rtf and ("public.html" in types) == html, (command, types)
        if rtf:
            assert base64.b64decode(app.clipboard_info(type="public.rtf")["data"]).startswith(b"{\\rtf1")
        if html:
            assert b"<pre" in base64.b64decode(app.clipboard_info(type="public.html")["data"])


@pytest.mark.case("PLUGINS-045")
def test_plugins_045_the_menu_toggle_turns_spell_checking_on_and_off(app):
    """PLUGINS-045: The menu toggle turns spell checking on and off

    Covers: -
    Channel: menu, prefs, mcp
    Steps: Set pref spellCheckLanguage = "en" (skip the case if the `spell_check` tool finds nothing wrong in "helo" with language en); document "helo wrld\\n"; run `Plugins|Spell Check|Spell Check Document Automatically`; read indicator 17 (SCI_INDICATORVALUEAT) at positions 1 and 6 and the item's checked state; run the toggle again; restore the prefs.
    Expect: on: the item is checked, pref spellCheckEnabled is true, both words carry indicator 17 and a correct word ("wrld" replaced by "world") does not; off: unchecked, pref false, no position carries indicator 17.
    """
    app.set_prefs(spellCheckLanguage="en")
    if not spell_available(app, "helo", "en"):
        pytest.skip("the spelling engine offers no English here")
    app.new("helo wrld\n")
    try:
        app.run("Plugins|Spell Check|Spell Check Document Automatically")
        assert app.checked("Plugins|Spell Check|Spell Check Document Automatically")
        assert app.pref("spellCheckEnabled") is True
        app.wait(lambda: spell_at(app, 1) and spell_at(app, 6))
        app.set_text("helo world\n")
        app.wait(lambda: spell_at(app, 1) and not spell_at(app, 6))
        app.run("Plugins|Spell Check|Spell Check Document Automatically")
        assert not app.checked("Plugins|Spell Check|Spell Check Document Automatically")
        assert not app.pref("spellCheckEnabled")
        assert not any(spell_at(app, p) for p in range(10))
    finally:
        if app.pref("spellCheckEnabled"):
            app.run("Plugins|Spell Check|Spell Check Document Automatically")
        app.set_prefs(spellCheckLanguage=None, spellCheckEnabled=None)


@pytest.mark.case("PLUGINS-046")
def test_plugins_046_indicator_17_is_a_red_squiggle_under_the_text(app):
    """PLUGINS-046: Indicator 17 is a red squiggle under the text

    Covers: -
    Channel: mcp
    Steps: With spell checking on and a misspelling marked, read SCI_INDICGETSTYLE, SCI_INDICGETFORE and SCI_INDICGETUNDER for indicator 17.
    Expect: style INDIC_SQUIGGLE (1), fore 0x0000FF (red in BGR), under = 1.
    """
    app.new("helo\n")
    with spelling(app):
        app.wait(lambda: spell_at(app, 1))
        assert app.sci(SCI_INDICGETSTYLE, SPELL) == 1          # INDIC_SQUIGGLE
        assert app.sci(SCI_INDICGETFORE, SPELL) == 0x0000FF
        assert app.sci(SCI_INDICGETUNDER, SPELL) == 1


@pytest.mark.case("PLUGINS-047")
def test_plugins_047_in_code_only_comments_and_strings_are_checked(app, tmp):
    """PLUGINS-047: In code only comments and strings are checked

    Covers: -
    Channel: mcp, files
    Steps: Spell checking on (en); open `sp.py` = "wrld = 1  # helo wrld\\ns = 'speling'\\nspeling_var = 2\\n".
    Expect: the identifier "wrld" on line 1 and "speling_var" on line 3 carry no indicator; "helo" and "wrld" in the comment and "speling" inside the string do.
    """
    src = tmp / "sp.py"
    src.write_text("wrld = 1  # helo wrld\nspeling_var = 2\nd = \"speling\"\ns = 'speling'\n")
    with spelling(app):
        app.open(src)
        app.wait(lambda: spell_at(app, 13) and spell_at(app, 18))
        app.wait(lambda: spell_at(app, 44))          # "speling" in a double-quoted string
        assert not spell_at(app, 1)                  # identifier wrld
        assert not spell_at(app, 23)                 # identifier speling_var
        assert spell_at(app, 58)                     # 'speling' in a single-quoted string


@pytest.mark.case("PLUGINS-048")
def test_plugins_048_squiggles_follow_typing(app):
    """PLUGINS-048: Squiggles follow typing

    Covers: -
    Channel: keys, mcp
    Steps: Spell checking on (en), plain-text document "ok\\n"; type " teh" at the end; wait for the debounce; then select "teh" and type "the".
    Expect: after the wait "teh" carries indicator 17; after the correction no position on the line does.
    """
    app.new("ok\n")
    with spelling(app):
        app.select(1, 3)
        app.type(" teh")
        app.wait(lambda: spell_at(app, 4))
        app.select(1, 4, 1, 7)
        app.type("the")
        assert app.text() == "ok the\n"
        app.wait(lambda: not any(spell_at(app, p) for p in range(6)))


@pytest.mark.case("PLUGINS-049")
def test_plugins_049_the_language_follows_the_choice_or_is_detected(app):
    """PLUGINS-049: The language follows the choice, or is detected

    Covers: -
    Channel: prefs, mcp
    Steps: Spell checking on; with pref spellCheckLanguage = "" (Automatic) check "bonjur le monde\\n" (skip if the engine offers no French); with "en" check "helo"; with "de" check "Hallo Welt" (skip if no German); restore prefs.
    Expect: automatic marks "bonjur"; en marks "helo"; de does not mark "Hallo" or "Welt".
    """
    app.new("")
    languages = titles(submenu(submenu(plugins_menu(app, 3), "Spell Check"), "Language"))
    with spelling(app, "en"):
        app.set_text("helo\n")
        app.wait(lambda: spell_at(app, 1))
        if any("French" in (t or "") for t in languages) and spell_available(app, "bonjur", "fr"):
            app.set_prefs(spellCheckLanguage="")
            app.set_text("bonjur le monde\n")
            app.wait(lambda: spell_at(app, 1))
        if any("German" in (t or "") for t in languages) and spell_available(app, "Halllo", "de"):
            app.set_prefs(spellCheckLanguage="de")
            app.set_text("Hallo Welt\n")
            app.idle(0.8)
            assert not spell_at(app, 1) and not spell_at(app, 7)


@pytest.mark.case("PLUGINS-050")
def test_plugins_050_the_language_submenu_lists_automatic_and_the_installed_dicti(app):
    """PLUGINS-050: The Language submenu lists Automatic and the installed dictionaries

    Covers: -
    Channel: menu, prefs
    Steps: Open `Plugins|Spell Check|Language` (needs the hook that fills a menu through its delegate before dumping it); choose one listed language; then choose Automatic.
    Expect: the first item is "Automatic", then a separator, then the system's languages by display name; the checked item follows pref spellCheckLanguage; choosing a language sets the pref to its identifier and rechecks the document; Automatic sets it to "".
    """
    try:
        app.set_prefs(spellCheckLanguage="")
        items = submenu(submenu(plugins_menu(app, 3), "Spell Check"), "Language")
        names = titles(items)
        assert names[0] == "Automatic" and names[1] == "-" and len(names) > 2, names
        assert items[0]["checked"]
        chosen = names[2]
        r = app.call("e2e_menu_invoke", path=f"Plugins|Spell Check|Language|{chosen}")
        assert r["ran"]
        language = app.pref("spellCheckLanguage")
        assert language
        items = submenu(submenu(plugins_menu(app, 3), "Spell Check"), "Language")
        assert [i["title"] for i in items if i.get("checked")] == [chosen]
        app.call("e2e_menu_invoke", path="Plugins|Spell Check|Language|Automatic")
        assert app.pref("spellCheckLanguage") == ""
    finally:
        app.set_prefs(spellCheckLanguage=None)


@pytest.mark.case("PLUGINS-051")
def test_plugins_051_the_context_menu_offers_guesses_ignore_and_learn_for_a_missp(app):
    """PLUGINS-051: The context menu offers guesses, Ignore and Learn for a misspelled word

    Covers: -
    Channel: menu, mcp
    Steps: Spell checking on (en), document "helo world\\n" with the caret inside "helo"; dump the editor context menu as a right click builds it (needs the hook: `e2e_menu context=editor` must include the spelling items the menu delegate adds at the caret); then put the caret on "world" and dump again.
    Expect: on "helo" the menu starts with at most five guesses including "hello", then "Ignore Spelling" and "Learn Spelling" (enabled; never clicked), then a separator, then the usual editor items; on "world" no spelling items appear.
    """
    app.new("helo world\n")
    with spelling(app):
        app.wait(lambda: spell_at(app, 1))
        menu = right_click(app, 1, 2)["menu"]
        # Edit > Calculate's item and its separator come first, disabled without a selected formula.
        assert titles(menu)[:2] == ["Calculate", "-"] and not menu[0]["enabled"]
        menu = menu[2:]
        guesses = [i for i in menu if i.get("action") == "spellReplaceWord:"]
        assert 1 <= len(guesses) <= 5
        names = titles(menu)
        k = len(guesses)
        assert names[:k] == [g["title"] for g in guesses]
        assert names[k:k + 3] == ["Ignore Spelling", "Learn Spelling", "-"], names
        assert menu[k]["enabled"] and menu[k + 1]["enabled"]
        assert "Cut" in names[k + 3:]
        menu = right_click(app, 1, 8)["menu"]
        assert spelling_items(menu) == [] and titles(menu)[:2] == ["Calculate", "-"]


@pytest.mark.case("PLUGINS-052")
def test_plugins_052_choosing_a_guess_replaces_the_word(app):
    """PLUGINS-052: Choosing a guess replaces the word

    Covers: -
    Channel: menu, mcp
    Steps: As PLUGINS-051, invoke the guess "hello" from the editor context menu (hook as above).
    Expect: the document reads "hello world\\n"; no indicator remains on line 1; one undo restores "helo".
    """
    app.new("helo world\n")
    with spelling(app):
        app.wait(lambda: spell_at(app, 1))
        menu = right_click(app, 1, 2)["menu"]
        guess = next(i["title"] for i in menu if i.get("action") == "spellReplaceWord:")
        right_click(app, 1, 2, menu_path=guess)
        assert app.text() == guess + " world\n"
        app.idle(0.5)
        assert not any(spell_at(app, p) for p in range(len(guess)))
        undo(app)
        assert app.text() == "helo world\n"


@pytest.mark.case("PLUGINS-053")
def test_plugins_053_ignore_spelling_clears_the_word_for_this_session_only(app):
    """PLUGINS-053: Ignore Spelling clears the word for this session only

    Covers: -
    Channel: menu, mcp
    Steps: Spell checking on (en), document "zqxwv zqxwv\\n", caret in the first word; invoke "Ignore Spelling" from the context menu (hook as above); restart the app and check the same text.
    Expect: after Ignore neither occurrence carries indicator 17; after the restart both are marked again (ignoring is not learning).
    """
    with spelling(app, probe="zqxwv"):
        app.new("zqxwv zqxwv\n")
        app.wait(lambda: spell_at(app, 1) and spell_at(app, 7))
        right_click(app, 1, 2, menu_path="Ignore Spelling")
        app.wait(lambda: not spell_at(app, 1) and not spell_at(app, 7))
        app.restart()
        app.new("zqxwv zqxwv\n")
        app.wait(lambda: spell_at(app, 1) and spell_at(app, 7))


@pytest.mark.case("PLUGINS-054")
def test_plugins_054_no_spelling_items_when_spell_checking_is_off(app):
    """PLUGINS-054: No spelling items when spell checking is off

    Covers: -
    Channel: menu
    Steps: Spell checking off; document "helo\\n" with the caret in the word; dump the editor context menu (hook as above).
    Expect: no "Ignore Spelling", "Learn Spelling" or guess items.
    """
    app.set_prefs(spellCheckEnabled=False)
    try:
        app.new("helo\n")
        menu = right_click(app, 1, 2)["menu"]
        assert spelling_items(menu) == []
        assert not any(i.get("action") == "spellReplaceWord:" for i in menu)
    finally:
        app.set_prefs(spellCheckEnabled=None)


@pytest.mark.case("PLUGINS-055")
def test_plugins_055_markdown_preview_toggles_a_docked_panel_that_renders_the_doc(app):
    """PLUGINS-055: Markdown Preview toggles a docked panel that renders the document

    Covers: -
    Channel: mcp, ui
    Steps: Document "# Hello\\n\\n- one\\n- two\\n\\nSome **bold** and `code`.\\n"; run `Plugins|Markdown Preview`; read `markdownPanel.visible` and `markdownPanel.lastHTML` on app; run it again.
    Expect: visible true; the HTML contains "<h1>Hello</h1>", "<li>one</li>", "<strong>bold</strong>", "<code>code</code>"; the panel is inside the main window (a WKWebView among its controls), not a separate window; the second toggle hides it (visible false).
    """
    app.new("# Hello\n\n- one\n- two\n\nSome **bold** and `code`.\n")
    windows_before = len(app.windows())
    try:
        app.run("Plugins|Markdown Preview")
        assert app.wait(lambda: markdown_visible(app))
        html = app.wait(lambda: markdown_html(app))
        for part in ("<h1>Hello</h1>", "<li>one</li>", "<strong>bold</strong>", "<code>code</code>"):
            assert part in html, part
        assert len(app.windows()) == windows_before       # docked in the main window
        app.run("Plugins|Markdown Preview")
        assert not markdown_visible(app)
    finally:
        if markdown_visible(app):
            app.run("Plugins|Markdown Preview")


@pytest.mark.case("PLUGINS-056")
def test_plugins_056_gfm_tables_render_with_alignment_escaped_pipes_and_inline_ma(app):
    """PLUGINS-056: GFM tables render with alignment, escaped pipes and inline Markdown

    Covers: -
    Channel: mcp
    Steps: With the preview shown, set the document to "| Name | N |\\n|:-----|--:|\\n| a\\\\|b | **1** |\\n| short |\\n\\n```\\n| not | a table |\\n|---|---|\\n```\\n"; wait for the render.
    Expect: lastHTML has `<th style="text-align:left">Name</th>`, `<td style="text-align:right"><strong>1</strong></td>`, a cell "a|b", the short row padded with an empty cell; the fenced lines appear inside <pre><code>, not as a second <table>.
    """
    app.new("x\n")
    try:
        app.run("Plugins|Markdown Preview")
        app.set_text("| Name | N |\n|:-----|--:|\n| a\\|b | **1** |\n| short |\n\n```\n| not | a table |\n|---|---|\n```\n")
        html = app.wait(lambda: (h := markdown_html(app)) and "<table>" in h and h)
        assert '<th style="text-align:left">Name</th>' in html
        assert '<td style="text-align:right"><strong>1</strong></td>' in html
        assert ">a|b</td>" in html
        assert re.search(r"<td[^>]*>short</td><td[^>]*></td>", html), html
        assert html.count("<table>") == 1
        assert re.search(r"<pre><code>\| not \| a table \|", html), html
    finally:
        if markdown_visible(app):
            app.run("Plugins|Markdown Preview")


@pytest.mark.case("PLUGINS-057")
def test_plugins_057_the_preview_follows_typing_and_the_tab_in_front(app):
    """PLUGINS-057: The preview follows typing and the tab in front

    Covers: -
    Channel: keys, mcp
    Steps: Preview shown on "# One\\n"; type "\\n## Two" at the end; wait ~0.5 s; open a second tab "# Other\\n" and wait; switch back to the first tab.
    Expect: lastHTML gains "<h2>Two</h2>" after the debounce; it shows "<h1>Other</h1>" while the second tab is in front and "<h1>One</h1>" again after switching back.
    """
    first = app.new("# One\n")["index"]
    try:
        app.run("Plugins|Markdown Preview")
        app.wait(lambda: "<h1>One</h1>" in markdown_html(app))
        app.sci(SCI_DOCUMENTEND)
        app.type("\n## Two")
        app.wait(lambda: "<h2>Two</h2>" in markdown_html(app))
        app.new("# Other\n")
        app.wait(lambda: "<h1>Other</h1>" in markdown_html(app))
        app.select(1, document=first)
        app.wait(lambda: "<h1>One</h1>" in markdown_html(app))
    finally:
        if markdown_visible(app):
            app.run("Plugins|Markdown Preview")


@pytest.mark.case("PLUGINS-058")
def test_plugins_058_raw_html_passes_through_scripts_stay_inert_relative_images_r(app, tmp):
    """PLUGINS-058: Raw HTML passes through, scripts stay inert, relative images resolve

    Covers: -
    Channel: mcp, files
    Steps: Save `doc.md` in `tmp` next to `pic.png`, containing "<b>raw</b>\\n\\n<script>document.title='ran'</script>\\n\\n![p](pic.png)\\n"; open it and show the preview.
    Expect: lastHTML contains "<b>raw</b>" and `<img src="pic.png"`; the web view's title (key path `markdownPanel.webView.title` on app) is not "ran" (JavaScript is off); a snapshot of the main window shows the picture's pixels in the panel area (the relative path resolved against the document's folder).
    """
    from PIL import Image
    Image.new("RGB", (120, 120), (255, 0, 0)).save(tmp / "pic.png")
    doc = tmp / "doc.md"
    doc.write_text("<b>raw</b>\n\n<script>document.title='ran'</script>\n\n![p](pic.png)\n")
    app.open(doc)
    try:
        app.run("Plugins|Markdown Preview")
        html = app.wait(lambda: "<b>raw</b>" in markdown_html(app) and markdown_html(app))
        assert '<img src="pic.png"' in html
        app.idle(1.0)
        assert app.get("app", "markdownPanel.webView.title") != "ran"
        shot = tmp / "shot.png"
        app.snapshot(shot)
        img = Image.open(shot).convert("RGB")
        raw = img.tobytes()
        reds = sum(1 for i in range(0, len(raw), 3) if raw[i] > 200 and raw[i + 1] < 60 and raw[i + 2] < 60)
        assert reds > 500, reds
    finally:
        if markdown_visible(app):
            app.run("Plugins|Markdown Preview")


@pytest.mark.case("PLUGINS-059")
def test_plugins_059_the_sample_plugin_builds_loads_at_launch_and_gets_a_submenu(app):
    """PLUGINS-059: The sample plugin builds, loads at launch and gets a submenu

    Covers: -
    Channel: files, launch, menu
    Steps: Compile `../npp/macos/plugin-sdk/sample/hellomac.c` with `clang -dynamiclib` into `<home>/Library/Application Support/NotepadMac/plugins/HelloMac/HelloMac.dylib`; `app.restart()` keeping the home; dump the Plugins menu.
    Expect: after "Open Plugins Folder…" come a separator and a "HelloMac" submenu with "Insert Greeting", a separator, "Insert File Name"; `class:NppPluginHost` reports one plugin named HelloMac.
    """
    with installed(app, lambda d: build(SAMPLE, d / "HelloMac" / "HelloMac.dylib")):
        items = plugins_menu(app)
        names = titles(items)
        at = names.index("Open Plugins Folder…")
        assert names[at + 1:] == ["-", "HelloMac"], names
        assert titles(submenu(items, "HelloMac")) == ["Insert Greeting", "-", "Insert File Name"]
        assert plugin_names(app) == ["HelloMac"]


@pytest.mark.case("PLUGINS-060")
def test_plugins_060_a_plugin_command_edits_the_document_through_scintilla(app):
    """PLUGINS-060: A plugin command edits the document through Scintilla

    Covers: -
    Channel: menu, mcp
    Steps: With HelloMac loaded, new document "[x]" with "x" selected; invoke `Plugins|HelloMac|Insert Greeting` with `e2e_menu_invoke`; undo once.
    Expect: the document reads "[hello from the sample plugin]"; one undo gives "[x]" back.
    """
    with installed(app, lambda d: build(SAMPLE, d / "HelloMac" / "HelloMac.dylib")):
        app.new("[x]")
        app.select(1, 2, 1, 3)
        assert app.call("e2e_menu_invoke", path="Plugins|HelloMac|Insert Greeting")["ran"]
        assert app.text() == "[hello from the sample plugin]"
        undo(app)
        assert app.text() == "[x]"


@pytest.mark.case("PLUGINS-061")
def test_plugins_061_nppm_getfilename_answers_for_a_saved_file_and_for_a_new_one(app, tmp):
    """PLUGINS-061: NPPM_GETFILENAME answers for a saved file and for a new one

    Covers: -
    Channel: menu, mcp, files
    Steps: With HelloMac loaded, open `t_plugin.txt` from `tmp`, caret at 0; invoke `Plugins|HelloMac|Insert File Name`; then in a new tab invoke it again.
    Expect: the file's text starts "t_plugin.txt"; the new tab's text is its tab title ("new N").
    """
    src = tmp / "t_plugin.txt"
    src.write_text("plugin food\n")
    with installed(app, lambda d: build(SAMPLE, d / "HelloMac" / "HelloMac.dylib")):
        app.open(src)
        app.sci(SCI_GOTOPOS, 0)
        app.call("e2e_menu_invoke", path="Plugins|HelloMac|Insert File Name")
        assert app.text().startswith("t_plugin.txtplugin food")
        title = app.new("")["title"]
        app.call("e2e_menu_invoke", path="Plugins|HelloMac|Insert File Name")
        assert app.text() == title


@pytest.mark.case("PLUGINS-062")
def test_plugins_062_notifications_reach_a_plugin_ready_fileopened_filesaved_buff(app, tmp):
    """PLUGINS-062: Notifications reach a plugin: READY, FILEOPENED, FILESAVED, BUFFERACTIVATED, SHUTDOWN

    Covers: -
    Channel: files, launch, mcp
    Steps: Build the fixture plugin `fixtures/plugins/notelog.c` (exports the three required functions plus nppmac_beNotified, which appends each code to `<NPPM_GETPLUGINSCONFIGDIR>/notelog.txt`) into the plugins folder; restart; open a file, save it, switch tabs; quit the app gracefully; read the log.
    Expect: the log contains 1001 (READY) before anything else, then 1004 (FILEOPENED) after the open, 1008 (FILESAVED) after the save, 1010 (BUFFERACTIVATED) after the tab switch, and 1009 (SHUTDOWN) last; the config folder is `plugins/Config` inside the test home.
    """
    src = tmp / "note.txt"
    src.write_text("one\n")
    with installed(app, lambda d: build(NOTELOG, d / "NoteLog" / "NoteLog.dylib")) as folder:
        log = folder / "Config" / "NoteLog.log"

        def codes():
            return log.read_text().split() if log.exists() else []
        app.wait(lambda: codes())
        assert codes()[0] == "1001"
        app.open(src)
        app.wait(lambda: "1004" in codes())
        n = len(codes())
        app.set_text("two\n", document=str(src))
        app.call("save_document", document=str(src))
        app.wait(lambda: "1008" in codes()[n:])
        n = len(codes())
        other = app.new("x")["index"]
        app.select(1, document=str(src))
        app.wait(lambda: "1010" in codes()[n:])
        app.stop()
        assert codes()[-1] == "1009", codes()
        assert folder / "Config" == plugins_dir(app) / "Config"


@pytest.mark.case("PLUGINS-063")
def test_plugins_063_the_application_messages_a_plugin_can_send(app, tmp):
    """PLUGINS-063: The application messages a plugin can send

    Covers: -
    Channel: files, menu, mcp
    Steps: The fixture plugin also has commands that write into the document the answers of NPPM_GETFULLCURRENTPATH, NPPM_GETCURRENTDIRECTORY and NPPM_GETNPPVERSION, and commands that call NPPM_DOOPEN on `tmp/other.txt` and NPPM_SAVECURRENTFILE; run each on a saved file after modifying it.
    Expect: the full path and folder of the file in front are inserted; the version answer is (8 << 16) | 908 printed as a number; DOOPEN opens `other.txt` in a tab and returns 1; SAVECURRENTFILE saves the modified file to disk (the file's bytes change, the document is no longer modified).
    """
    src = tmp / "saved.txt"
    src.write_text("abc\n")
    other = tmp / "other.txt"
    other.write_text("other file\n")
    with installed(app, lambda d: build(NOTELOG, d / "NoteLog" / "NoteLog.dylib")) as folder:
        (folder / "Config").mkdir(exist_ok=True)
        (folder / "Config" / "open.txt").write_text(str(other) + "\n")
        log = folder / "Config" / "NoteLog.log"

        def command(name):
            assert app.call("e2e_menu_invoke", path=f"Plugins|NoteLog|{name}")["ran"]
        app.open(src)
        for name, want in (("Insert Full Path", str(src)), ("Insert Directory", str(src.parent)),
                           ("Insert Version", str((8 << 16) | 908))):
            app.set_text("")
            command(name)
            assert App.same_path(app.text(), want) if "Path" in name or "Directory" in name else app.text() == want, (name, app.text())
        count = len(app.docs())
        command("Open Other")
        app.wait(lambda: len(app.docs()) == count + 1)
        assert App.same_path(app.doc()["path"], other)
        assert "doopen=1" in log.read_text()
        app.select(1, document=str(src))
        app.set_text("changed\n")
        assert app.doc()["modified"]
        command("Save Current")
        assert "save=1" in log.read_text()
        assert src.read_text() == "changed\n" and not app.doc()["modified"]


@pytest.mark.case("PLUGINS-064")
def test_plugins_064_a_flat_plugin_loads_broken_ones_are_skipped(app):
    """PLUGINS-064: A flat plugin loads; broken ones are skipped

    Covers: -
    Channel: files, launch, menu
    Steps: Put in the plugins folder: `Flat.dylib` (a copy of the sample built as a flat file, name "HelloMac" in getName so rename it with a -D define to "FlatHello"), `junk.dylib` (a text file), `NoExports/NoExports.dylib` (a dylib exporting nothing of the interface), `Empty/Empty.dylib` (exports the functions with a zero-length command list); restart.
    Expect: the app starts; only FlatHello has a submenu (the others are logged and skipped); the app log mentions the skipped files.
    """
    def put(d):
        build(NOTELOG, d / "Flat.dylib", name="FlatHello")
        (d / "junk.dylib").write_text("this is not a library")
        build(FIXTURES / "noexports.c", d / "NoExports" / "NoExports.dylib")
        build(FIXTURES / "empty.c", d / "Empty" / "Empty.dylib")
    mark = app.log_path.stat().st_size if app.log_path.exists() else 0
    with installed(app, put):
        assert plugin_names(app) == ["FlatHello"]
        names = titles(plugins_menu(app))
        assert names[names.index("Open Plugins Folder…") + 1:] == ["-", "FlatHello"]
        with open(app.log_path, "rb") as f:
            f.seek(mark)
            said = f.read().decode("utf-8", "replace")
        assert "junk.dylib" in said and "NoExports" in said and "EmptyPlugin" in said, said[-2000:]


@pytest.mark.case("PLUGINS-065")
def test_plugins_065_several_plugins_get_a_submenu_each_in_name_order(app):
    """PLUGINS-065: Several plugins get a submenu each, in name order

    Covers: -
    Channel: files, launch, menu
    Steps: Install HelloMac and a second copy built with getName "AnotherHello" in `plugins/Another/Another.dylib`; restart.
    Expect: two submenus after one separator, in folder-name order (Another before HelloMac); each one's Insert Greeting works on the document in front.
    """
    def put(d):
        build(SAMPLE, d / "HelloMac" / "HelloMac.dylib")
        build(NOTELOG, d / "Another" / "Another.dylib", name="AnotherHello")
    with installed(app, put):
        names = titles(plugins_menu(app))
        assert names[names.index("Open Plugins Folder…") + 1:] == ["-", "AnotherHello", "HelloMac"], names
        app.new("")
        app.call("e2e_menu_invoke", path="Plugins|AnotherHello|Insert Greeting")
        assert app.text() == "hello from AnotherHello"
        app.new("")
        app.call("e2e_menu_invoke", path="Plugins|HelloMac|Insert Greeting")
        assert app.text() == "hello from the sample plugin"


@pytest.mark.case("PLUGINS-066")
def test_plugins_066_open_plugins_folder_creates_the_folder_when_it_is_missing(app):
    """PLUGINS-066: Open Plugins Folder creates the folder when it is missing

    Covers: IDM_SETTING_OPENPLUGINSDIR
    Channel: mcp, files
    Steps: Remove `<home>/Library/Application Support/NotepadMac/plugins`; run IDM_SETTING_OPENPLUGINSDIR (needs a hook that records NSWorkspace reveal/open requests instead of performing them, so Finder does not open during the run).
    Expect: the command ran; the plugins folder exists afterwards inside the test home (not the real Application Support); the recorded reveal request names that folder.
    """
    folder = plugins_dir(app)
    shutil.rmtree(folder, ignore_errors=True)
    app.modal_log(clear=True)
    app.run("IDM_SETTING_OPENPLUGINSDIR")
    assert folder.is_dir()
    assert str(app.home) in str(folder)
    reveals = [e for e in app.modal_log() if e["kind"] == "reveal"]
    assert reveals and App.same_path(reveals[0]["target"], folder), reveals


@pytest.mark.case("PLUGINS-067")
def test_plugins_067_import_plugin_s_copies_a_dylib_into_the_plugins_folder_loade(app, tmp):
    """PLUGINS-067: Import plugin(s)… copies a dylib into the plugins folder, loaded at the next launch

    Covers: IDM_SETTING_IMPORTPLUGIN
    Channel: modal, files, launch, menu
    Steps: Build HelloMac.dylib in `tmp`; queue its path and run IDM_SETTING_IMPORTPLUGIN; read the modal log; restart; dump the Plugins menu; import it again.
    Expect: the open panel is titled "Import plugin(s)"; the alert says "1 file(s) imported into plugins"; `plugins/HelloMac.dylib` exists in the test home; after the restart the HelloMac submenu is there; importing again replaces the file (still one copy, no error).
    """
    dylib = build(SAMPLE, tmp / "HelloMac.dylib")
    folder = plugins_dir(app)
    try:
        shutil.rmtree(folder, ignore_errors=True)
        app.answers(panels=[str(dylib)])
        app.run("IDM_SETTING_IMPORTPLUGIN")
        log = app.modal_log()
        opens = [e for e in log if e["kind"] == "open"]
        assert opens and opens[0]["title"] == "Import plugin(s)", log
        shown = [e for e in log if e["kind"] == "alert"]
        assert shown and shown[0]["informative"] == "1 file(s) imported into plugins", shown
        assert (folder / "HelloMac.dylib").is_file()
        app.restart()
        assert "HelloMac" in titles(plugins_menu(app))
        app.answers(panels=[str(dylib)])
        app.run("IDM_SETTING_IMPORTPLUGIN")
        assert [e["informative"] for e in app.modal_log() if e["kind"] == "alert"] == ["1 file(s) imported into plugins"]
        assert [p.name for p in folder.iterdir() if p.suffix == ".dylib"] == ["HelloMac.dylib"]
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        app.restart()
