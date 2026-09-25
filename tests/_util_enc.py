"""Helpers shared by the ENCODING tests."""
from pathlib import Path

UNICODE_ITEMS = ["IDM_FORMAT_ANSI", "IDM_FORMAT_AS_UTF_8", "IDM_FORMAT_UTF_8",
                 "IDM_FORMAT_UTF_16BE", "IDM_FORMAT_UTF_16LE"]


def write(folder: Path, name: str, data: bytes) -> str:
    p = Path(folder) / name
    p.write_bytes(data)
    return str(p)


def read(path) -> bytes:
    return Path(path).read_bytes()


def status_text(app) -> str:
    """The main window's status bar line (the field that carries "Ln:")."""
    for c in app.ui()["controls"]:
        value = str(c.get("value", ""))
        if c.get("class") == "NSTextField" and "Ln:" in value:
            return value
    raise AssertionError("no status bar field found")


def status_fields(app) -> list[str]:
    return [f.strip() for f in status_text(app).split("    ") if f.strip()]


def status_encoding(app) -> str:
    """The field before INS/OVR."""
    fields = status_fields(app)
    for i, f in enumerate(fields):
        if f in ("INS", "OVR"):
            return fields[i - 1]
    raise AssertionError(f"no INS/OVR in status bar: {fields}")


def status_eol(app) -> str:
    fields = status_fields(app)
    for i, f in enumerate(fields):
        if f in ("INS", "OVR"):
            return fields[i - 2]
    raise AssertionError(f"no INS/OVR in status bar: {fields}")


def checked_items(app, ids=UNICODE_ITEMS) -> list[str]:
    items = app.menu(*ids)
    return [k for k, v in items.items() if v and v["checked"]]


def save(app):
    app.run("IDM_FILE_SAVE")


def reopen(app, path):
    """Closes the current document (changes discarded) and opens path again."""
    d = app.doc()
    app.call("close_document", document=d["index"], discard_changes=True)
    app.open(path)
    app.wait(lambda: app.doc().get("path") and app.same_path(app.doc()["path"], path), message="reopened")
    return app.doc()


def save_untitled(app, path):
    app.answers(panels=[str(path)])
    app.run("IDM_FILE_SAVE")
    app.wait(lambda: Path(path).exists(), message="file saved")
