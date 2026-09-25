"""Helpers for tests/test_visual.py: what the window server shows, checked by structure and by goldens.

A picture is the window as the window server composites it (e2e_snapshot screen=true): what a user
sees, so a view that paints over its neighbour shows up, which a view's own rendering never does.
Points of the screen (e2e_ui frames, y up) are mapped to the picture's pixels (y down, the screen's
backing scale); nothing assumes a screen size or a scale.

Structural checks do not depend on how text is rendered: a pane shows its document when its
line-number margin and its text area carry the colours Scintilla was given for them (so no other
view's paint lies over them) and have ink on them (digits, text); a tab shows its label when its
rectangle has ink; a panel is not blank when its header and its content have ink.

Goldens (fixtures/golden/<2x|1x>/<name>.png, by the screen's backing scale) are kept at 1x: a picture is scaled down to points, blurred a
little on both sides and compared per channel; it passes when few enough pixels differ by more than
the threshold. `pytest --update-goldens` writes them again.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from harness.sci import SCI_GETMARGINS, SCI_GETMARGINWIDTHN, SCI_STYLEGETBACK, STYLE_DEFAULT, STYLE_LINENUMBER

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "fixtures" / "golden"

# The window every layout is checked in: small enough for a 1024x768 screen (a CI runner's) with
# the menu bar and the Dock, and the same everywhere, so the goldens are.
WINDOW = (860, 560)

# A colour "is" the one expected within this much per channel (the window server's colour
# matching moves a value by a unit or two); "ink" is what differs from a background by more.
SAME = 12
INK = 60


def parse_rect(s) -> tuple[float, float, float, float]:
    if isinstance(s, (list, tuple)):
        return tuple(float(v) for v in s)
    nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", str(s))]
    return nums[0], nums[1], nums[2], nums[3]


def bgr(value: int) -> tuple[int, int, int]:
    """Scintilla's colour (0xBBGGRR) as RGB."""
    return value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF


def close(a, b, tol=SAME) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(a, b))


class Shot:
    """One picture of a window and the mapping from screen points to its pixels."""

    def __init__(self, app, path: Path, window="main"):
        self.app = app
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        info = next(w for w in app.windows() if (w["main_window"] if window == "main" else w["number"] == window))
        self.window = info
        app.idle(0.3)
        app.call("e2e_snapshot", window=info["number"], path=str(self.path), screen=True)
        self.image = Image.open(self.path).convert("RGB")
        self.frame = parse_rect(info["frame"])
        self.scale = self.image.size[0] / self.frame[2]

    def box(self, frame, inset=0.0) -> tuple[int, int, int, int]:
        """A screen rectangle (points, y up) as the picture's pixel box, clipped to the picture."""
        x, y, w, h = parse_rect(frame)
        wx, wy, ww, wh = self.frame
        s = self.scale
        left, top = (x - wx + inset) * s, (wy + wh - (y + h) + inset) * s
        right, bottom = (x - wx + w - inset) * s, (wy + wh - y - inset) * s
        W, H = self.image.size
        return (max(0, int(round(left))), max(0, int(round(top))),
                min(W, int(round(right))), min(H, int(round(bottom))))

    def crop(self, frame, inset=0.0) -> Image.Image:
        return self.image.crop(self.box(frame, inset))

    def mark(self, frames, colour=(255, 0, 255)):
        """A copy of the picture with rectangles drawn on it, saved beside it (for a failure's report)."""
        im = self.image.copy()
        d = ImageDraw.Draw(im)
        for f in frames:
            d.rectangle(self.box(f), outline=colour, width=max(1, int(self.scale)))
        out = self.path.with_name(self.path.stem + "-marked.png")
        im.save(out)
        return out


# ---- what a region holds ----------------------------------------------------

def _far(im: Image.Image, colour, tol) -> int:
    """How many pixels differ from colour by more than tol in some channel (in C, not per pixel)."""
    diff = ImageChops.difference(im, Image.new("RGB", im.size, tuple(colour)))
    r, g, b = diff.split()
    worst = ImageChops.lighter(ImageChops.lighter(r, g), b)
    return sum(worst.histogram()[tol + 1:])


def dominant(im: Image.Image) -> tuple[tuple, float]:
    total = im.size[0] * im.size[1]
    if not total:
        return (0, 0, 0), 0.0
    n, colour = max(im.getcolors(total))
    return colour, n / total


def share(im: Image.Image, colour, tol=SAME) -> float:
    total = im.size[0] * im.size[1]
    return (total - _far(im, colour, tol)) / total if total else 0.0


def ink(im: Image.Image, background=None, tol=INK) -> int:
    """How many pixels differ from the background (the region's own dominant colour by default)."""
    if not im.size[0] * im.size[1]:
        return 0
    if background is None:
        background = dominant(im)[0]
    return _far(im, background, tol)


def distinct(im: Image.Image) -> int:
    return len(im.getcolors(im.size[0] * im.size[1]) or [])


# ---- the window's parts ---------------------------------------------------------

def controls(app, window="main") -> list[dict]:
    return app.call("e2e_ui", window=window, timeout=20)["controls"]


def content_frame(app) -> tuple:
    """The main window's content below the title bar and toolbar, in screen points."""
    win = parse_rect(next(w for w in app.windows() if w["main_window"])["frame"])
    cx, cy, cw, ch = parse_rect(app.get("window", "contentLayoutRect"))
    return win[0] + cx, win[1] + cy, cw, ch


def panes(app, cs) -> list[dict]:
    """The editor's panes on screen: [{view: 'main'|'sub', frame}], matched to e2e_ui's ScintillaViews
    by size (the editor's views know their frame in their host only); equal sizes go in split order."""
    scis = [c for c in cs if c["class"] == "ScintillaView" and not c.get("hidden")]
    out, taken = [], set()
    for view, key in (("main", "sciView"), ("sub", "secondarySci")):
        if not app.get("editor", f"{key}.window") or app.get("editor", f"{key}.hiddenOrHasHiddenAncestor"):
            continue
        w, h = parse_rect(app.get("editor", f"{key}.frame"))[2:]
        for i, c in enumerate(scis):
            if i not in taken and abs(c["frame"][2] - w) < 0.5 and abs(c["frame"][3] - h) < 0.5:
                taken.add(i)
                out.append({"view": view, "frame": c["frame"]})
                break
    return out


def tab_bars(cs) -> list[dict]:
    return [c for c in cs if c["class"] == "NppTabBarView" and not c.get("hidden")]


def overlaps(a, b, slack=0.5) -> bool:
    ax, ay, aw, ah = parse_rect(a)
    bx, by, bw, bh = parse_rect(b)
    return ax + slack < bx + bw and bx + slack < ax + aw and ay + slack < by + bh and by + slack < ay + ah


# ---- the checks ----------------------------------------------------------------

def check_pane(shot: Shot, pane: dict, bands: int = 4) -> list[str]:
    """What is wrong with how a pane shows its document ([] = nothing)."""
    app, view = shot.app, pane["view"]
    x, y, w, h = pane["frame"]
    margins = [app.sci(SCI_GETMARGINWIDTHN, i, view=view) for i in range(app.sci(SCI_GETMARGINS, view=view))]
    numbers = margins[0] if margins else 0
    text_left = x + sum(margins)
    back = bgr(app.sci(SCI_STYLEGETBACK, STYLE_DEFAULT, view=view))
    margin_back = bgr(app.sci(SCI_STYLEGETBACK, STYLE_LINENUMBER, view=view))
    problems = []
    # The scroll bars (right, bottom) are not the pane's text; 16 points leaves them out in any style.
    usable_h = h - 16
    text_w = x + w - 16 - text_left
    if text_w < 20 or usable_h < 20:
        return [f"{view}: the pane is too small to show text ({w}x{h})"]
    band_h = usable_h / bands
    top = y + h        # screen y grows upwards: the first band is the pane's top
    for i in range(bands):
        by = top - (i + 1) * band_h
        text = shot.crop((text_left + 2, by, text_w - 2, band_h))
        s = share(text, back)
        if s < 0.3:
            problems.append(f"{view}: text band {i + 1}/{bands} is not the editor's background "
                            f"{back} (only {s:.0%}; mostly {dominant(text)[0]})")
        if numbers >= 8:
            m = shot.crop((x + 1, by, numbers - 2, band_h))
            s = share(m, margin_back)
            if s < 0.5:
                problems.append(f"{view}: line-number margin band {i + 1}/{bands} is not the margin's "
                                f"colour {margin_back} (only {s:.0%}; mostly {dominant(m)[0]})")
    first = shot.crop((text_left + 2, top - band_h, text_w - 2, band_h))
    if ink(first, back) < 20 * shot.scale ** 2 or distinct(first) < 4:
        problems.append(f"{view}: no text drawn at the pane's top (ink {ink(first, back)}, "
                        f"{distinct(first)} colours)")
    if numbers >= 8:
        m = shot.crop((x + 1, top - band_h, numbers - 2, band_h))
        if ink(m, margin_back) < 10 * shot.scale ** 2:
            problems.append(f"{view}: no line numbers drawn (ink {ink(m, margin_back)})")
    return problems


def tab_frame_on_screen(bar: dict, tab: dict) -> tuple:
    """A tab's frame (in its flipped bar) as a screen rectangle."""
    bx, by, bw, bh = bar["frame"]
    tx, ty, tw, th = tab["frame"]
    return bx + tx, by + bh - ty - th, tw, th


def check_tab_bar(shot: Shot, bar: dict) -> list[str]:
    problems = []
    region = shot.crop(bar["frame"])
    if distinct(region) < 3:
        problems.append(f"tab bar at {bar['frame']}: blank ({distinct(region)} colours)")
    bx, by, bw, bh = bar["frame"]
    for tab in bar.get("tabs") or []:
        f = tab_frame_on_screen(bar, tab)
        # Only the tabs the bar shows whole (a vertical or multi-line bar may scroll).
        if f[0] < bx - 0.5 or f[0] + f[2] > bx + bw + 0.5 or f[1] < by - 0.5 or f[1] + f[3] > by + bh + 0.5:
            continue
        label = shot.crop((f[0] + 4, f[1] + 3, max(1, f[2] - 24), max(1, f[3] - 6)))
        n = ink(label, tol=INK // 2)
        if n < 6 * shot.scale ** 2:
            problems.append(f"tab {tab['label']!r}: no label drawn (ink {n})")
    return problems


def check_region(shot: Shot, frame, what: str, min_ink: float = 40, min_colours: int = 4) -> list[str]:
    im = shot.crop(frame)
    if im.size[0] < 4 or im.size[1] < 4:
        return [f"{what}: no room on screen ({frame})"]
    n, c = ink(im, tol=INK // 2), distinct(im)
    if n < min_ink * shot.scale ** 2 or c < min_colours:
        return [f"{what}: blank (ink {n}, {c} colours) at {tuple(round(v) for v in parse_rect(frame))}"]
    return []


def check_main_window(shot: Shot, cs: list[dict], expect_panes: int | None = None,
                      expect_bars: int | None = None) -> list[str]:
    """Every pane shows its text, no tab bar lies over a pane, every tab bar shows its labels."""
    app = shot.app
    ps = panes(app, cs)
    bars = tab_bars(cs)
    problems = []
    if expect_panes is not None and len(ps) != expect_panes:
        problems.append(f"{len(ps)} panes on screen, expected {expect_panes}")
    if expect_bars is not None and len(bars) != expect_bars:
        problems.append(f"{len(bars)} tab bars on screen, expected {expect_bars}")
    for p in ps:
        problems += check_pane(shot, p)
        for b in bars:
            if overlaps(p["frame"], b["frame"]):
                problems.append(f"{p['view']}: the tab bar at {b['frame']} lies over the pane at {p['frame']}")
    for b in bars:
        problems += check_tab_bar(shot, b)
    return problems


def report(shot: Shot, problems: list[str], frames=()) -> str:
    marked = shot.mark(frames) if frames else shot.path
    return "\n".join(problems + [f"picture: {marked}"])


# ---- goldens -----------------------------------------------------------------

def at_1x(shot: Shot) -> Image.Image:
    w, h = shot.image.size
    size = (max(1, round(w / shot.scale)), max(1, round(h / shot.scale)))
    return shot.image if shot.scale == 1 else shot.image.resize(size, Image.LANCZOS)


def blank_out(im: Image.Image, shot: Shot, frames) -> Image.Image:
    """Regions that may differ by design (a version number) filled with one grey in both pictures."""
    if not frames:
        return im
    im = im.copy()
    d = ImageDraw.Draw(im)
    for f in frames:
        l, t, r, b = shot.box(f)
        s = shot.scale
        d.rectangle((int(l / s), int(t / s), int(r / s) + 1, int(b / s) + 1), fill=(128, 128, 128))
    return im


def diff_ratio(a: Image.Image, b: Image.Image, threshold: int, blur: float) -> tuple[float, Image.Image]:
    """The share of pixels whose channels differ by more than threshold after a light blur of both
    (text rendered at another scale or hinting moves edges by a fraction of a pixel, not areas)."""
    if blur:
        a, b = a.filter(ImageFilter.GaussianBlur(blur)), b.filter(ImageFilter.GaussianBlur(blur))
    diff = ImageChops.difference(a, b)
    r, g, bb = diff.split()
    worst = ImageChops.lighter(ImageChops.lighter(r, g), bb)
    mask = worst.point(lambda v: 255 if v > threshold else 0)
    n = sum(worst.histogram()[threshold + 1:])
    return n / (mask.size[0] * mask.size[1]), mask


def compare_golden(shot: Shot, name: str, update: bool, masks=(), threshold: int = 40,
                   max_ratio: float = 0.01, blur: float = 1.0) -> str | None:
    """None when the picture matches fixtures/golden/<name>.png (or the golden was written);
    otherwise what differs, with the pictures saved beside the shot."""
    actual = blank_out(at_1x(shot), shot, masks)
    # Text is drawn differently on a Retina screen and scaled down than on a 1x screen (CI runners):
    # each backing scale has its own goldens.
    folder = GOLDEN / ("2x" if shot.scale >= 1.5 else "1x")
    golden_path = folder / f"{name}.png"
    if update or os.environ.get("NPPMAC_UPDATE_GOLDENS"):
        folder.mkdir(parents=True, exist_ok=True)
        # 256 colours: a third of the size, and the colours lost are far below the threshold.
        actual.quantize(256, method=Image.Quantize.MEDIANCUT).save(golden_path, optimize=True)
        return None
    if not golden_path.exists():
        if os.environ.get("CI"):
            # A runner with a scale that has no goldens yet: the picture is kept in the job's
            # artifact (.work-ci/golden-candidates) to be looked at and committed.
            import pytest
            cand = ROOT / ".work-ci" / "golden-candidates" / folder.name
            cand.mkdir(parents=True, exist_ok=True)
            actual.quantize(256, method=Image.Quantize.MEDIANCUT).save(cand / f"{name}.png", optimize=True)
            pytest.skip(f"no golden {golden_path.relative_to(ROOT)} yet: candidate in {cand.relative_to(ROOT)}")
        return f"no golden {golden_path.relative_to(ROOT)}: run with --update-goldens"
    golden = Image.open(golden_path).convert("RGB")
    out = shot.path.with_name(f"{name}-actual.png")
    actual.save(out)
    if golden.size != actual.size:
        return f"{name}: the window is {actual.size}, the golden {golden.size} (actual: {out})"
    ratio, mask = diff_ratio(actual, golden, threshold, blur)
    if ratio > max_ratio:
        mask_path = shot.path.with_name(f"{name}-diff.png")
        Image.composite(Image.new("RGB", actual.size, (255, 0, 255)), actual, mask).save(mask_path)
        return (f"{name}: {ratio:.2%} of the pixels differ by more than {threshold} "
                f"(allowed {max_ratio:.2%}); actual: {out}, differences: {mask_path}")
    return None
