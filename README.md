# NotepadMac end-to-end tests

The black-box test suite of [NotepadMac](https://github.com/tanderbold/NotepadMac), the native
macOS port of Notepad++. About 1,500 tests in 23 areas drive the real application the way a user
does - menus, keys, clicks, dialogs, files on disk, a git repository, local FTP and HTTP servers -
and check what comes out: the text, the files written, the windows and their controls, the
pixels. NotepadMac's own repository has a second, in-app suite (`macos/app/Tests.mm`); this one
looks at the application only from the outside.

[![e2e](https://github.com/tanderbold/NotepadMac-tests/actions/workflows/e2e.yml/badge.svg)](https://github.com/tanderbold/NotepadMac-tests/actions/workflows/e2e.yml)

## How it works

- `harness/app.py` copies a build of NotepadMac under its own bundle id
  (`org.notepad-plus-plus.mac.e2e.<worker>`), with its own home folder, preferences and socket,
  so a test never touches a real user's settings or a running NotepadMac.
- It starts the copy with `NPPMAC_E2E=1` and talks to it over the application's MCP agent
  socket. With that variable, and only then, the application adds `e2e_*` tools
  (`macos/app/E2EHooks.mm` in NotepadMac): menu state, windows and controls, clicks and keys
  through AppKit's own event routing, snapshots, preferences, a private clipboard. Alerts and
  open/save panels take queued answers; opening URLs and printing are logged, not performed.
- Each case in `tests/` implements a case of the plan in `plan/<AREA>.md` (`@pytest.mark.case`),
  written against upstream Notepad++'s behaviour. A case that finds a defect is not bent to
  pass: it stays `xfail(strict=True)` with the defect in its reason until the application is
  fixed.
- The VISUAL area (`tests/test_visual.py`) looks at the window as the window server shows it:
  structural pixel checks for each layout (every pane shows its text and line numbers, tab bars
  their labels, panels are not blank) and golden pictures of a few stable windows
  (`fixtures/golden/2x` and `1x`, one set per screen scale). After an intended change of how those windows look,
  `pytest tests/test_visual.py --update-goldens` writes the goldens again.

## Running it

The application takes the keyboard focus while it runs, so **do not run the suite on a Mac you
are working at**. Use a spare Mac, a CI runner, or a macOS virtual machine:

- **Continuous integration**: `.github/workflows/e2e.yml` builds NotepadMac's `main` on a
  GitHub macOS runner and runs every area: on each push here, by hand (Actions → e2e → Run
  workflow, with a branch or commit of NotepadMac and optionally some areas), and hourly when
  NotepadMac's `main` has a commit not yet tested.
- **Another Mac or a runner**: `pip install -r requirements.txt`, build NotepadMac
  (`bash macos/build.sh` in its checkout), then
  `NPPMAC_E2E_APP=/path/to/NotepadMac.app tools/ci-run.sh [area ...]`.
  One area: `NPPMAC_E2E_APP=… NPPMAC_E2E_ACTIVATE=1 python3 -m pytest tests/test_search.py`.
- **A virtual machine on your own Mac** ([Tart](https://tart.run)): `tools/vm.sh` runs the
  suite inside the VM's GUI session, so nothing reaches your screen.
  `tools/vm-guest-setup.sh` prepares a fresh macOS guest (key-only ssh, Python, the Command
  Line Tools); then `NPPMAC_VM_APP=/path/to/NotepadMac.app tools/area.sh <worker> tests/test_x.py`.

The checkout of NotepadMac is looked for beside this one (`../npp`) unless `NPPMAC_E2E_APP`
names a build.

`tests/test_perf.py` (the "perf" area, every test marked `slow`) measures large inputs - 10 MB,
100 MB and 1 GB files, a 5 MB line, 100 tabs and a session of 100, Find All, Replace All,
Find in Files over 20,000 files, Compare, the Document Map, the Function List, a keystroke's
latency - with limits several times what a run measures, to catch a pathological regression.
It makes its inputs as it goes (up to about 1.5 GB in the temporary folder, 4 GB of memory for
the application at the peak) and takes about 20 minutes; `-s` prints the numbers, which are also
appended to `.work/<worker>/perf.jsonl`.

## Layout

| Path | What |
|---|---|
| `plan/`, `TEST_PLAN.md` | the cases, area by area, with the upstream behaviour each one checks |
| `tests/` | the tests, one file per area, and their helpers (`_util_*.py`) |
| `harness/` | the application under test: copy, launch, the MCP connection, the `e2e_*` calls |
| `fixtures/` | files the tests open; `fixtures/golden` the VISUAL area's pictures |
| `tools/` | `ci-run.sh`, the VM scripts, `shots.py` (the screenshots in NotepadMac's README and site) |
| `HARNESS.md` | how the harness and the hooks fit together |

Bugs found in NotepadMac go to [its Issues](https://github.com/tanderbold/NotepadMac/issues).
Licensed under the GPL version 3, like NotepadMac and Notepad++.
