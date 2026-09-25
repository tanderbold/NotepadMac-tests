# Format of the plan files

`plan/<AREA>.md`, one per area; `tools/build_plan.py` joins them into
`TEST_PLAN.md`, checks menu-command coverage against `plan/commands.tsv`, and
`tools/gen_stubs.py` turns every case into a pytest stub. Keep to the format
exactly — it is parsed.

```
# <AREA> — <Area title>

<One paragraph: what the area is, what is in and out of scope.>

## <Group title>

### <AREA>-<NNN>: <Case title, imperative or descriptive, one line>
- Covers: IDM_FILE_NEW, IDM_FILE_OPEN        (menu command ids this case exercises; globs allowed, e.g. IDM_LANG_*; "-" if none)
- Channel: mcp, keys                          (any of: mcp, keys, ui, menu, cli, files, prefs, snapshot, clipboard, modal, launch)
- Steps: <what the test does, 1-4 sentences, concrete inputs>
- Expect: <what must hold, concrete and checkable; several facts separated by "; ">
```

Rules:

- IDs are the area code plus a three-digit number, unique, in order
  (`EDIT-001`, `EDIT-002`...). Area codes: FILE, SESSION, EDIT, TYPING, MACRO,
  SEARCH, VIEW, UI, L10N, ENCODING, LANG, SETTINGS, TOOLS, PLUGINS, COMPARE,
  FTP, RUN, GIT, AGENT, CLI, MACEXTRA, WINDOW, HELP, VISUAL.
- One case = one pytest test. A case may be parametrized (say so in Steps:
  "for each of ..."), which is how families like the 194 language commands or
  the 50 encodings are covered without 194 cases.
- Every menu command of your menus in `plan/commands.tsv` must appear in some
  case's `Covers`. Commands that open a dialog are covered by driving that
  dialog (queued answers or `e2e_act`), not just by opening it.
- Expectations follow Windows Notepad++ behaviour as the port implements it
  (read the port's code and its in-app suite `../npp/macos/app/Tests.mm`,
  and upstream's `../npp/PowerEditor/src` where the port follows it). Do not
  plan a behaviour the port does not have; if the port lacks something
  Notepad++ has, note it in a case titled "... (known gap)" only if the port's
  README/FEATURES claims it.
- Every case must be implementable with the channels in `HARNESS.md`.
- English only.
