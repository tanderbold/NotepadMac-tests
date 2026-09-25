"""VISUAL: what the window shows, in pixels (plan/VISUAL.md).

Every other area reads the app's state; a view that paints over another one leaves all of it right
and the window wrong (the second view's tab bar once painted the whole pane below it over). These
tests look at the window as the window server composites it: structural checks for each layout
(every pane shows its text and line numbers in its own colours, tab bars show their labels, panels
are not blank) and golden pictures of a few stable windows (_util_visual.py has the details).

The app runs here with fixed conditions: scroll bars always shown, the window at WINDOW points and
centred, the Default themes, the caret hidden before a golden is taken.
"""
from __future__ import annotations

import pytest

from harness.sci import SCI_GETCARETSTYLE, SCI_SETCARETSTYLE
from _util_visual import (WINDOW, Shot, check_main_window, check_region, compare_golden, content_frame, controls,
                          panes, parse_rect, report, tab_bars)
from _util_view import dock, write

DETERMINISTIC = ["-AppleShowScrollBars", "Always", "-NSAutomaticWindowAnimationsEnabled", "NO"]
APPEARANCE = {"light": 1, "dark": 2}
PANELS = {"functionList": "IDM_VIEW_FUNC_LIST", "documentMap": "IDM_VIEW_DOC_MAP", "documentList": "IDM_VIEW_DOCLIST",
          "workspace": "IDM_VIEW_FILEBROWSER", "git": "Plugins|Git|Git Panel",
          "markdownPreview": "Plugins|Markdown Preview"}
SIDES = {"left": 0, "right": 1, "top": 2, "bottom": 3}

DEMO = '''"""Hourly readings of a few weather stations."""
from dataclasses import dataclass
from statistics import mean


@dataclass
class Reading:
    station: str
    hour: int
    temperature: float


def daily_average(readings):
    """The mean temperature of a day, rounded to a tenth."""
    return round(mean(r.temperature for r in readings), 1)


def warmest(readings, top=3):
    return sorted(readings, key=lambda r: r.temperature, reverse=True)[:top]


class Report:
    def __init__(self, stations):
        self.stations = stations
        self.readings = []

    def add(self, reading):
        self.readings.append(reading)

    def lines(self):
        for station in sorted(self.stations):
            day = [r for r in self.readings if r.station == station]
            if day:
                yield f"{station}: {daily_average(day)}"
'''

OTHER = """export interface Station {
  id: string;
  name: string;
  height: number;
}

export function toFahrenheit(celsius: number): number {
  return celsius * 9 / 5 + 32;
}

export function label(s: Station): string {
  return `${s.name} (${s.height} m)`;
}
"""

README = """# Weather stations

A small service that collects hourly readings and prints a daily report.

## Stations

| Station | Height |
|---------|-------:|
| Harbour | 12 m   |
| Summit  | 1180 m |

Readings older than **30 days** are archived.
"""


# ---- the app under fixed conditions -------------------------------------------------

@pytest.fixture(scope="module")
def vapp(app_session):
    app_session.stop()
    app_session.start(args=DETERMINISTIC, defaults={"appearanceMode": 1})
    yield app_session
    app_session.stop()
    app_session.start()


def _hide_panels(app):
    for p in PANELS:
        if dock(app, "hasPanel:", p) and dock(app, "isPanelVisible:", p):
            dock(app, "hidePanel:", p)


def _window(app):
    """The main window at WINDOW points, centred, and whole on the screen (a CI runner's is 1024x768)."""
    app.act("main", "resize_window", value=list(WINDOW))
    app.invoke("window", "center")
    x, y, w, h = parse_rect(next(w for w in app.windows() if w["main_window"])["frame"])
    sx, sy, sw, sh = parse_rect(app.get("window", "screen.visibleFrame"))
    assert sx <= x and sy <= y and x + w <= sx + sw and y + h <= sy + sh, ((x, y, w, h), (sx, sy, sw, sh))


@pytest.fixture
def v(vapp, tmp):
    app = vapp
    app.reset()
    _hide_panels(app)
    app.set_prefs(appearanceMode=1, lightThemeName="Default")
    _window(app)
    yield app
    app.reset()
    _hide_panels(app)
    app.set_prefs(appearanceMode=1, tabBarVertical=None, tabBarMultiLine=None)


def demo(app, tmp, *names):
    """The demo files written to tmp and opened, the leftover empty tab closed."""
    texts = {"forecast.py": DEMO, "stations.ts": OTHER, "README.md": README}
    for n in names:
        app.open(write(tmp, n, texts[n]))
    for d in app.docs():
        if d["title"] == "new 1" and not d["path"] and len(app.docs()) > 1:
            app.call("close_document", document=d["index"], discard_changes=True)
            break
    app.select(1, 1)


def pictures(app):
    """Where the pictures go: .work/<worker>/visual, kept after the run (tools/vm.sh pull brings them back)."""
    return app.work / "visual"


def look(app, tmp, name, expect_panes=None, expect_bars=None, extra=()):
    """The main window's picture and what is wrong in it; fails with the list and the picture."""
    shot = Shot(app, pictures(app) / f"{name}.png")
    cs = controls(app)
    problems = check_main_window(shot, cs, expect_panes, expect_bars)
    for check in extra:
        problems += check(shot, cs)
    assert not problems, report(shot, problems, [p["frame"] for p in panes(app, cs)] + [b["frame"] for b in tab_bars(cs)])
    return shot, cs


def appearance(app, which):
    app.set_prefs(appearanceMode=APPEARANCE[which])
    app.wait(lambda: ("Dark" in str(app.get("nsapp", "effectiveAppearance.name"))) == (which == "dark"),
             message=f"the {which} appearance")


# ---- structure: panes, tab bars, panels ---------------------------------------------------

@pytest.mark.case("VISUAL-001")
@pytest.mark.parametrize("mode", ["light", "dark"])
def test_visual_001_one_view_shows_its_text_line_numbers_and_tab_labels(v, tmp, mode):
    appearance(v, mode)
    demo(v, tmp, "stations.ts", "forecast.py")
    look(v, tmp, f"one-view-{mode}", expect_panes=1, expect_bars=1)


@pytest.mark.case("VISUAL-002")
@pytest.mark.parametrize("mode", ["light", "dark"])
def test_visual_002_two_views_side_by_side_both_show_their_documents(v, tmp, mode):
    appearance(v, mode)
    demo(v, tmp, "stations.ts", "forecast.py")
    v.run("IDM_VIEW_GOTO_ANOTHER_VIEW")
    look(v, tmp, f"two-views-{mode}", expect_panes=2, expect_bars=2)


@pytest.mark.case("VISUAL-003")
def test_visual_003_two_views_one_above_the_other_both_show_their_documents(v, tmp):
    # The port has no Rotate on the divider's menu (upstream's SplitterContainer::rotateTo): the split
    # is turned by its NSSplitView.vertical before the second view opens, as the layout code allows.
    demo(v, tmp, "stations.ts", "forecast.py")
    v.invoke("app", "setValue:forKeyPath:", [False, "editor.editorSplit.vertical"])
    try:
        v.run("IDM_VIEW_GOTO_ANOTHER_VIEW")
        _, cs = look(v, tmp, "two-views-stacked", expect_panes=2, expect_bars=2)
        main, sub = sorted(panes(v, cs), key=lambda p: p["view"])
        assert sub["frame"][1] + sub["frame"][3] <= main["frame"][1] + 1, (main, sub)   # below it
    finally:
        v.reset()
        v.invoke("app", "setValue:forKeyPath:", [True, "editor.editorSplit.vertical"])


def _dock_region(app, cs, side) -> tuple:
    """Where a dock container on one side is: between the content's edge and the editor's panes and bars."""
    parts = [p["frame"] for p in panes(app, cs)] + [b["frame"] for b in tab_bars(cs)]
    left = min(f[0] for f in parts)
    right = max(f[0] + f[2] for f in parts)
    bottom = min(f[1] for f in parts)
    top = max(f[1] + f[3] for f in parts)
    cx, cy, cw, ch = content_frame(app)
    status = max((c["frame"][1] + c["frame"][3] for c in cs if c["class"] == "NppStatusPathField"), default=cy)
    if side == "left":
        return cx, bottom, left - cx - 1, top - bottom
    if side == "right":
        return right + 1, bottom, cx + cw - right - 1, top - bottom
    if side == "top":
        return left, top + 1, right - left, cy + ch - top - 1
    return left, status + 1, right - left, bottom - status - 2


def _panel_checks(side, name, header=24):
    def check(shot, cs):
        x, y, w, h = _dock_region(shot.app, cs, side)
        if w < 40 or h < 40:
            return [f"{name} docked {side}: no room for it ({w:.0f}x{h:.0f})"]
        return (check_region(shot, (x + 2, y + h - header, w - 4, header - 2), f"{name} docked {side}: its tab",
                             min_ink=15, min_colours=3) +
                check_region(shot, (x + 2, y + 2, w - 4, h - header - 4), f"{name} docked {side}: its content"))
    return check


@pytest.fixture
def repo(tmp):
    """The demo files in a repository with a change, so the Git panel and the margin have something."""
    from _util_git import commit_all, make_repo
    root = make_repo(tmp, "weather", files={"forecast.py": DEMO, "stations.ts": OTHER, "README.md": README})
    (root / "forecast.py").write_text(DEMO.replace("top=3", "top=5"))
    (root / "notes.txt").write_text("Check the summit station.\n")
    return root


@pytest.mark.case("VISUAL-004")
@pytest.mark.parametrize("side", list(SIDES))
def test_visual_004_each_panel_docked_on_each_side_is_drawn_beside_the_editor(v, repo, tmp, side):
    v.open(repo / "stations.ts")
    v.open(repo / "forecast.py")
    for d in v.docs():
        if d["title"] == "new 1":
            v.call("close_document", document=d["index"], discard_changes=True)
    for name in ("functionList", "documentMap", "documentList", "workspace", "git"):
        v.run(PANELS[name])
        v.wait(lambda: dock(v, "isPanelVisible:", name), 5, message=f"{name} shown")
        dock(v, "movePanel:to:", name, SIDES[side])
        v.idle(0.4)
        look(v, tmp, f"dock-{side}-{name}", expect_panes=1, expect_bars=1, extra=[_panel_checks(side, name)])
        dock(v, "hidePanel:", name)


@pytest.mark.case("VISUAL-005")
def test_visual_005_a_vertical_tab_bar_shows_every_label_beside_the_pane(v, tmp):
    for i in range(6):
        write(tmp, f"part{i}.py", DEMO)
    for i in range(6):
        v.open(tmp / f"part{i}.py")
    demo(v, tmp)
    v.set_prefs(tabBarVertical=True)
    _, cs = look(v, tmp, "tabs-vertical", expect_panes=1, expect_bars=1)
    bar, pane = tab_bars(cs)[0], panes(v, cs)[0]
    assert bar["frame"][0] + bar["frame"][2] <= pane["frame"][0] + 1 and len(bar["tabs"]) == 6


@pytest.mark.case("VISUAL-006")
def test_visual_006_multi_line_tabs_show_every_label_above_the_pane(v, tmp):
    for i in range(14):
        v.open(write(tmp, f"station-{i:02}.py", DEMO))
    demo(v, tmp)
    v.set_prefs(tabBarMultiLine=True)
    _, cs = look(v, tmp, "tabs-multiline", expect_panes=1, expect_bars=1)
    rows = {t["frame"][1] for t in tab_bars(cs)[0]["tabs"]}
    assert len(rows) > 1, rows


@pytest.mark.case("VISUAL-007")
def test_visual_007_compare_shows_both_texts_side_by_side(v, tmp):
    from _util_compare import CLEAR_ALL, compare_with_file
    old = write(tmp, "old.py", DEMO)
    new = write(tmp, "new.py", DEMO.replace("top=3", "top=5").replace("        self.readings = []\n",
                                                                      "        self.readings = []\n        self.updated = None\n"))
    v.open(new)
    try:
        compare_with_file(v, old)
        v.wait(lambda: v.get("editor", "secondaryViewVisible"), 5, message="the compare view")
        v.select(1, 1)
        look(v, tmp, "compare", expect_panes=2)
    finally:
        v.run(CLEAR_ALL)
        v.modal_log(clear=True)


@pytest.mark.case("VISUAL-008")
def test_visual_008_markdown_preview_renders_beside_the_text(v, tmp):
    demo(v, tmp, "README.md")
    v.run(PANELS["markdownPreview"])
    v.wait(lambda: v.get("app", "markdownPanel.lastHTML"), 10, message="the preview")
    v.wait(lambda: not v.get("app", "markdownPanel.webView.loading"), 10, message="the page loaded")
    v.idle(0.8)
    side = next(s for s, n in SIDES.items() if n == dock(v, "placeOfPanel:", "markdownPreview"))
    look(v, tmp, "markdown-preview", expect_panes=1, expect_bars=1,
         extra=[_panel_checks(side, "Markdown Preview")])


@pytest.mark.case("VISUAL-009")
def test_visual_009_search_results_are_drawn_with_the_document(v, tmp):
    from _util_search import fresh_dlg, wait_search_done
    folder = tmp / "src"
    write(folder, "forecast.py", DEMO)
    write(folder, "stations.ts", OTHER)
    v.open(folder / "forecast.py")
    demo(v, tmp)
    d = fresh_dlg(v, "IDM_SEARCH_FINDINFILES")
    d.set("what", "station")
    d.set("dir", str(folder))
    d.press("Find All")
    wait_search_done(d)
    d.close()
    v.wait(lambda: any(v.get("editor", "documents.isSearchResults") or []), 5, message="the results")
    look(v, tmp, "search-results")


@pytest.mark.case("VISUAL-010")
def test_visual_010_distraction_free_mode_shows_the_text_alone(v, tmp):
    demo(v, tmp, "forecast.py")
    v.run("IDM_VIEW_DISTRACTIONFREE")
    try:
        v.idle(0.5)
        _, cs = look(v, tmp, "distraction-free", expect_panes=1)
        assert not tab_bars(cs)
    finally:
        v.run("IDM_VIEW_DISTRACTIONFREE")
        _window(v)


# ---- goldens: a few windows that do not change from run to run ---------------------------

def _no_caret(app) -> int:
    """The caret hidden (a blinking caret is in the picture half the time); the style it had."""
    before = app.sci(SCI_GETCARETSTYLE)
    app.sci(SCI_SETCARETSTYLE, 0)   # CARETSTYLE_INVISIBLE
    return before


def _window_shot(app, tmp, title, name):
    w = app.wait(lambda: next((w for w in app.windows() if w["visible"] and w["title"] == title), None), 5, title)
    app.invoke(f"window:{title}", "makeFirstResponder:", [None])
    app.idle(0.4)
    return Shot(app, pictures(app) / f"{name}.png", window=w["number"]), w


GOLDEN_PREFS = ["General", "Editing 1", "Margins/Border/Edge", "Tab Bar"]


@pytest.mark.case("VISUAL-011")
@pytest.mark.parametrize("page", GOLDEN_PREFS)
def test_visual_011_preferences_pages_look_as_recorded(v, tmp, update_goldens, page):
    from _util_set import close_prefs
    from _util_set import page as open_page
    open_page(v, page)
    try:
        shot, _ = _window_shot(v, tmp, "Preferences", "prefs")
        name = "prefs-" + "".join(ch if ch.isalnum() else "-" for ch in page.lower()).strip("-")
        problem = compare_golden(shot, name, update_goldens)
        assert not problem, problem
    finally:
        close_prefs(v)


@pytest.mark.case("VISUAL-012")
def test_visual_012_the_find_dialog_looks_as_recorded(v, tmp, update_goldens):
    from _util_search import fresh_dlg
    demo(v, tmp, "forecast.py")
    d = fresh_dlg(v, "IDM_SEARCH_FIND", tab="Find")
    try:
        shot, _ = _window_shot(v, tmp, d.title, "find")
        problem = compare_golden(shot, "find", update_goldens)
        assert not problem, problem
    finally:
        d.close()


@pytest.mark.case("VISUAL-013")
def test_visual_013_about_looks_as_recorded_but_for_its_version(v, tmp, update_goldens):
    v.run("IDM_ABOUT")
    shot, w = _window_shot(v, tmp, "About Notepad++", "about")
    try:
        # The version, the build number and the build time change with every build.
        masks = [c["frame"] for c in controls(v, w["number"])
                 if isinstance(c.get("value"), str) and c["value"].startswith(("Notepad++ v", "macOS port", "Build time"))]
        assert len(masks) == 3, masks
        problem = compare_golden(shot, "about", update_goldens, masks=masks)
        assert not problem, problem
    finally:
        v.close_window(w["number"])


@pytest.mark.case("VISUAL-014")
@pytest.mark.parametrize("mode", ["light", "dark"])
def test_visual_014_the_main_window_on_a_demo_file_looks_as_recorded(v, tmp, update_goldens, mode):
    appearance(v, mode)
    demo(v, tmp, "stations.ts", "forecast.py")
    v.select(12, 5)
    caret = _no_caret(v)
    try:
        shot = Shot(v, pictures(v) / f"main-{mode}.png")
        # The status bar's path and the window's title name the test's scratch folder, another one in
        # every run.
        top = content_frame(v)[1] + content_frame(v)[3]
        masks = [c["frame"] for c in controls(v) if c["class"] == "NppStatusPathField" or
                 (c["class"] == "NSTextField" and c["frame"][1] >= top)]
        problem = compare_golden(shot, f"main-{mode}", update_goldens, masks=masks)
        assert not problem, problem
    finally:
        v.sci(SCI_SETCARETSTYLE, caret)
