"""Screenshots for README and the site, taken in the VM's GUI session.

Runs an isolated copy of the app (the e2e harness), opens neutral demo files and
captures whole windows with screencapture -l (title bar, tabs, panels, status bar).
Run: NPPMAC_VM_APP=<build> NPPMAC_E2E_WORKER=shots tools/vm.sh gui-sh '~/nm/venv/bin/python tools/shots.py <which...>'
Pictures land in .work/shots/out; tools/vm.sh pull shots brings them back.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness.app import App  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / ".work" / "shots" / "out"
DEMO = Path(os.environ.get("SHOTS_DEMO") or Path.home() / "Projects" / "weather")
DOCK = "class:NppDockingManager"


def capture(app, name, window="main"):
    """The window with its frame and no shadow, at the screen's (retina) scale."""
    OUT.mkdir(parents=True, exist_ok=True)
    w = app.window(window) if window != "main" else app.windows()[0]
    app.idle(0.6)
    path = OUT / f"{name}.png"
    if os.environ.get("SHOTS_SCREENCAPTURE"):
        # What the screen shows (needs the Screen Recording permission): the window, no shadow.
        subprocess.run(["screencapture", "-x", "-o", f"-l{w['number']}", str(path)], check=True)
    else:
        # The window as the window server shows it, taken by the app itself: screencapture would need
        # the Screen Recording permission, which a VM job cannot be given without someone at its screen.
        mode = {"frame": True} if os.environ.get("SHOTS_FRAME") else {"screen": True}
        app.call("e2e_snapshot", window=w["number"], path=str(path), **mode)
    print("SHOT", path.name, w.get("title"))
    return path


def main(which):
    app = App(worker=os.environ.get("NPPMAC_E2E_WORKER", "shots"))
    app.start()
    try:
        for name in which:
            globals()[f"shot_{name}"](app)
    finally:
        app.stop()



FORECAST = """\"\"\"Hourly forecast for the stations in stations.json.\"\"\"
from dataclasses import dataclass
from statistics import mean
import json


@dataclass
class Reading:
    station: str
    hour: int
    temperature: float   # degrees Celsius
    wind: float          # metres per second


def load_stations(path="stations.json"):
    with open(path, encoding="utf-8") as f:
        return {s["id"]: s for s in json.load(f)["stations"]}


def daily_average(readings):
    \"\"\"The mean temperature of a day, rounded to a tenth.\"\"\"
    return round(mean(r.temperature for r in readings), 1)


def windiest(readings, top=3):
    return sorted(readings, key=lambda r: r.wind, reverse=True)[:top]


def feels_like(temperature, wind):
    # Wind chill, valid below 10 °C and above 1.3 m/s.
    if temperature > 10 or wind < 1.3:
        return temperature
    v = (wind * 3.6) ** 0.16
    return 13.12 + 0.6215 * temperature - 11.37 * v + 0.3965 * temperature * v


class Forecast:
    def __init__(self, stations):
        self.stations = stations
        self.readings = []

    def add(self, reading):
        if reading.station not in self.stations:
            raise KeyError(f"unknown station {reading.station}")
        self.readings.append(reading)

    def report(self):
        for station in sorted(self.stations):
            day = [r for r in self.readings if r.station == station]
            if day:
                print(f"{station}: {daily_average(day)} °C")
"""

API = """import { Reading } from "./types";

const BASE = "https://api.example.org/v2";

export interface Station {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
}

export async function fetchStations(): Promise<Station[]> {
  const response = await fetch(`${BASE}/stations`);
  if (!response.ok) {
    throw new Error(`stations: ${response.status}`);
  }
  return (await response.json()).stations;
}

export async function hourly(station: string, hours = 24): Promise<Reading[]> {
  const url = new URL(`${BASE}/readings`);
  url.searchParams.set("station", station);
  url.searchParams.set("hours", String(hours));
  const response = await fetch(url);
  return response.ok ? response.json() : [];
}

export function toFahrenheit(celsius: number): number {
  return celsius * 9 / 5 + 32;
}
"""

README = """# Weather stations

A small service that collects hourly readings from weather stations
and prints a daily report.

## Running it

```sh
python3 forecast.py --stations stations.json
```

## Stations

| Station | Height | Since |
|---------|-------:|------:|
| Harbour | 12 m   | 2019  |
| Airport | 48 m   | 2021  |
| Summit  | 1180 m | 2023  |

Readings older than **30 days** are archived.
"""

STATIONS = """{
  "updated": "2026-09-24T06:00:00Z",
  "stations": [
    { "id": "harbour", "name": "Harbour", "latitude": 59.91, "longitude": 10.75, "height": 12 },
    { "id": "airport", "name": "Airport", "latitude": 60.19, "longitude": 11.10, "height": 48 },
    { "id": "summit",  "name": "Summit",  "latitude": 61.63, "longitude": 8.31,  "height": 1180 }
  ]
}
"""


def demo_project(root=DEMO):
    root.mkdir(parents=True, exist_ok=True)
    for name, text in {"forecast.py": FORECAST, "api.ts": API, "README.md": README,
                       "stations.json": STATIONS}.items():
        (root / name).write_text(text, encoding="utf-8")
    return root


def fresh(app):
    # The results tab is not a document to close_all: closed by its place, as the harness's reset does.
    flags = app.get("editor", "documents.isSearchResults") or []
    for i in reversed([i for i, f in enumerate(flags) if f]):
        app.invoke("editor", "closeDocumentAtIndex:discardChanges:", [i, True])
    app.close_all()
    for p in ("IDM_VIEW_FUNC_LIST", "IDM_VIEW_DOC_MAP", "IDM_VIEW_DOCLIST"):
        if app.checked(p):
            app.run(p)


def shot_editor(app):
    """Tabs, Function List and Document Map beside a Python file."""
    root = demo_project()
    fresh(app)
    for name in ("README.md", "stations.json", "api.ts", "forecast.py"):
        app.open(root / name)
    app.run("IDM_VIEW_FUNC_LIST")
    app.invoke(DOCK, "movePanel:to:", ["functionList", 0])   # left, the map on the right
    app.run("IDM_VIEW_DOC_MAP")
    app.select(29, 5)
    capture(app, "editor-panels")


def shot_split(app):
    """Two views side by side, each with its own tabs."""
    root = demo_project()
    fresh(app)
    for name in ("forecast.py", "api.ts"):
        app.open(root / name)
    app.run("IDM_VIEW_GOTO_ANOTHER_VIEW")
    # A view that was never drawn comes out of the snapshot blank: a click there draws it.
    app.mouse(view="sub", point={"line": 7, "column": 1})
    app.mouse(view="main", point={"line": 20, "column": 5})
    path = capture(app, "two-views")
    if os.environ.get("SHOTS_CHECK_SUB"):
        from PIL import Image
        im = Image.open(path).convert("RGB")
        win = app.windows()[0]["frame"]
        scis = [c for c in app.ui()["controls"] if c["class"] == "ScintillaView"]
        x, y, w, h = scis[-1]["frame"]
        sx = im.size[0] / win[2]
        # Screen coordinates (y up) to the picture's (y down, the frame's scale).
        box = (int((x - win[0]) * sx), int((win[1] + win[3] - (y + h)) * sx),
               int((x - win[0] + w) * sx), int((win[1] + win[3] - y) * sx))
        print("SUBCOLORS", len(set(im.crop(box).get_flattened_data())), box)


def shot_search(app):
    """Find in Files with the results panel."""
    import sys as _s
    _s.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    from test_search import fif_dlg, fif_run
    root = demo_project()
    fresh(app)
    app.open(root / "forecast.py")
    d = fif_dlg(app, "station", root)
    fif_run(d)
    app.close_window(d.number)
    app.run("IDM_FOCUS_ON_FOUND_RESULTS")
    capture(app, "find-in-files")


def git(*args, cwd=DEMO):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def demo_repo():
    """The project under git: committed, then forecast.py changed - a line edited, lines added, one gone."""
    import shutil
    shutil.rmtree(DEMO / ".git", ignore_errors=True)
    (DEMO / "notes.txt").unlink(missing_ok=True)
    root = demo_project()
    git("init", "-q", "-b", "main")
    git("config", "user.name", "Demo")
    git("config", "user.email", "demo@example.org")
    git("add", ".")
    git("commit", "-q", "-m", "Hourly forecast")
    text = FORECAST.replace("    return round(mean(r.temperature for r in readings), 1)",
                            "    temps = [r.temperature for r in readings]\n    return round(mean(temps), 1) if temps else None")
    text = text.replace("def windiest(readings, top=3):", "def windiest(readings, top=5):")
    text = text.replace("        self.readings = []\n", "        self.readings = []\n        self.updated = None\n")
    text = text.replace("    # Wind chill, valid below 10 °C and above 1.3 m/s.\n", "")
    (root / "forecast.py").write_text(text, encoding="utf-8")
    (root / "notes.txt").write_text("Check the summit station's clock.\n", encoding="utf-8")
    return root


def shot_git(app):
    """Changed lines in the margin, the branch in the status bar, the Git panel."""
    root = demo_repo()
    fresh(app)
    app.open(root / "forecast.py")
    app.run("Plugins|Git|Refresh Git Status")
    app.run("Plugins|Git|Git Panel")
    # A wider dock, dragged by its divider as a user would, so the file names show whole.
    app.mouse(**{"class": "NppDockContainerView"}, divider="before", drag_by=[-90, 0])
    app.select(20, 1)
    app.idle(1.5)
    capture(app, "git")
    app.run("Plugins|Git|Git Panel")


def shot_compare(app):
    """Compare with HEAD: both texts aligned, the differences marked."""
    root = demo_repo()
    fresh(app)
    app.open(root / "forecast.py")
    app.run("Plugins|Git|Compare with HEAD")
    app.idle(1.5)
    app.select(18, 1)
    capture(app, "compare")
    app.run("Plugins|Git|Clear Active Compare")


NUMBERS = """Groceries
12.40, 3.75, 8.90, 2.15

Temperatures this week
14.2
16.8
13.5
17.1
15.9

Quick sums
sqrt(2) * 10 =
sin 30° =
200 + 15% =
log(1024; 2) =
"""


def shot_numbers(app):
    """Selected Numbers and Calculate: the results written after the numbers and after '='."""
    fresh(app)
    app.set_text(NUMBERS)   # into the "new 1" that close_all leaves
    app.select(2, 1, 2, len("12.40, 3.75, 8.90, 2.15") + 1)
    app.run("Edit|Selected Numbers|Sum")
    app.select(5, 1, 9, 5)
    app.run("Edit|Selected Numbers|Average")
    lines = app.text().split("\n")
    for n, line in enumerate(lines, 1):
        if line.rstrip().endswith("="):
            app.select(n, len(line) + 1)
            app.run("Edit|Calculate")
    app.select(1, 1)
    capture(app, "numbers")


def shot_markdown(app):
    """Markdown Preview beside the text."""
    root = demo_project()
    fresh(app)
    app.open(root / "README.md")
    app.run("Plugins|Markdown Preview")
    app.idle(2)
    capture(app, "markdown")
    app.run("Plugins|Markdown Preview")


def shot_http(app):
    """Tools > HTTP Request: a GET to a local server, the JSON answer laid out."""
    import functools
    import http.server
    import threading
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    from _util_tools import http_send, http_set, http_window
    root = demo_project()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        fresh(app)
        app.new("")
        w = http_window(app)
        http_set(app, w, method="GET", address=f"http://127.0.0.1:{server.server_port}/stations.json",
                 headers="Accept: application/json")
        http_send(app, w)
        capture(app, "http-request", window=w)
        app.close_window(w)
    finally:
        server.shutdown()


def shot_preferences(app):
    """Preferences with Notepad++'s pages and wording."""
    root = demo_project()
    fresh(app)
    for name in ("stations.json", "forecast.py"):
        app.open(root / name)
    main = app.windows()[0]["number"]
    app.run("IDM_SETTING_PREFERENCE")
    w = app.wait(lambda: next((w for w in app.windows() if w["number"] != main and w.get("visible")), None),
                 5, "Preferences")
    capture(app, "preferences", window=w["number"])
    app.close_window(w["number"])


if __name__ == "__main__":
    main(sys.argv[1:])
