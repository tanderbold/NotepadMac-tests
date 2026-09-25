"""Helpers for the A11Y tests: the accessibility tree VoiceOver reads (e2e_ax), walked and judged."""
import pytest

from harness.app import ToolError  # noqa: F401

# What a user operates: each needs a name VoiceOver can say.
INTERACTIVE = {"AXButton", "AXCheckBox", "AXRadioButton", "AXPopUpButton", "AXMenuButton", "AXTextField",
               "AXTextArea", "AXComboBox", "AXSlider", "AXIncrementor", "AXColorWell", "AXLink",
               "AXDisclosureTriangle", "AXSearchField", "AXDateTimeArea"}
# The window's own buttons and a scroll bar's parts: named by the system through their subrole.
SYSTEM_SUBROLES = {"AXCloseButton", "AXMinimizeButton", "AXZoomButton", "AXFullScreenButton", "AXToolbarButton",
                   "AXIncrementArrow", "AXDecrementArrow", "AXIncrementPage", "AXDecrementPage",
                   "AXSortButton"}


def ax(app, window="main", **kw) -> dict:
    return app.call("e2e_ax", window=window, **kw)


def nodes(tree, parents=()):
    """Every element with the chain of its ancestors."""
    yield tree, parents
    for c in tree.get("children", []):
        yield from nodes(c, parents + (tree,))


def name(n) -> str:
    return (n.get("name") or "").strip()


def in_table(parents) -> bool:
    """Cells of a table or outline: named by their row and column, as VoiceOver reads them."""
    return any(p.get("role") in ("AXRow", "AXCell", "AXTable", "AXOutline", "AXBrowser", "AXList") for p in parents)


def describe(n) -> str:
    bits = [n.get("role", "?")]
    if n.get("subrole"):
        bits.append(n["subrole"])
    for k in ("view_class", "value", "tooltip", "view_path", "path"):
        if n.get(k) not in (None, ""):
            bits.append(f"{k}={str(n[k])[:40]!r}")
    return " ".join(bits)


def unnamed(tree) -> list[str]:
    """Interactive elements without a label, a title or a linked title element."""
    out = []
    for n, parents in nodes(tree):
        role = n.get("role")
        if role not in INTERACTIVE or n.get("subrole") in SYSTEM_SUBROLES:
            continue
        if in_table(parents):
            continue
        if name(n):
            continue
        out.append(describe(n))
    return out


def unknown_roles(tree) -> list[str]:
    """Elements VoiceOver cannot say what they are - not inside the window's own buttons (whose
    menus live in another process) nor a stepper's arrows (AppKit's parts of an incrementor that
    is itself named and increments)."""
    return [describe(n) for n, parents in nodes(tree) if n.get("role") in (None, "", "AXUnknown")
            and not any(p.get("subrole") in SYSTEM_SUBROLES or p.get("role") == "AXIncrementor" for p in parents)]


def find(tree, **match):
    return [n for n, _ in nodes(tree) if all(n.get(k) == v for k, v in match.items())]


def open_window(app, command, timeout=6.0):
    """Runs a command that shows a window (modal or not) and returns (window, pending)."""
    before = {w["number"] for w in app.windows()}
    app.answers(real_modals=True)
    pending = app.run_async(command)
    try:
        w = app.wait(lambda: next((w for w in app.windows() if w["number"] not in before and w["visible"]), None),
                     timeout=timeout, message=f"a window from {command}")
    except Exception:
        close_window(app, None, pending)
        raise
    app.idle(0.2)
    return w, pending


def close_window(app, w, pending):
    try:
        if w:
            app.close_window(w["number"])
    finally:
        if pending:
            try:
                pending.wait(10)
            except Exception:  # noqa: BLE001
                pass
        app.answers(real_modals=False)


def skip_unless_ax(app):
    if "e2e_ax" not in {t["name"] for t in app.tools()}:
        pytest.skip("needs hook: e2e_ax")
