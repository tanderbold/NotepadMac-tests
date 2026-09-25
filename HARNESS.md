# The harness: how the tests drive NotepadMac

The suite is black-box: it starts the real, built application and works it from
outside, as a user and an AI agent would. Nothing of the suite is compiled into
the app; the app only offers a few test hooks, and only when started with
`NPPMAC_E2E=1`.

## Isolation

`harness/app.py` (`App`) copies `../npp/macos/build/NotepadMac.app` to
`.work/<worker>/NotepadMacE2E.app`, gives the copy the bundle id
`org.notepad-plus-plus.mac.e2e.<worker>` and signs it ad hoc. Consequences:

- its preferences are its own domain; the user's `org.notepad-plus-plus.mac`
  is never read or written. `App.start()` empties the domain first
  (`defaults delete`), then writes `autoUpdateMode = 0`;
- `CFFIXED_USER_HOME=.work/<worker>/home` moves Application Support
  (session, plugins, macros, user languages, backups) into a scratch home;
- the agent socket is `$TMPDIR/npe2e-<worker>.sock`;
- the clipboard is a private pasteboard (the user's clipboard is never touched);
- `nppmac` inside the copy talks only to the copy (it posts to `<bundle id>.cli`).

Several suites can run at once with different `NPPMAC_E2E_WORKER` values.

## Channels

1. **MCP**, the product's own agent interface (21 tools): `open_document`,
   `get_document`, `edit_document`, `get_selection`, `go_to`, `list_documents`,
   `close_document`, `save_document`, `bookmarks`, `list_commands`,
   `run_command` (any of the 579 menu commands by `IDM_*` name, id or menu path),
   `detect_language`, `tokens`, `function_list`, `find`, `replace`, `compare`,
   `file_encoding`, `ocr`, `read_qr`, `spell_check`.
2. **E2E hooks** (`e2e_*` tools, `macos/app/E2EHooks.mm`):
   - `e2e_sci` – any Scintilla message to the main/sub view (read styles,
     markers, indicators, folding, zoom, wrap mode, selections...);
   - `e2e_menu` / `e2e_menu_invoke` – menu items' enabled/checked/key state,
     menu trees, the tab and editor context menus;
   - `e2e_windows`, `e2e_ui` – windows and every control in one (path, class,
     title/value/state/items, table cells, toolbar items);
   - `e2e_act` – click, set_value, set_state, select (popup/segment/tab/row),
     double_click, set_text, focus, close_window, toolbar;
   - `e2e_keys` – key chords (`cmd+f`, `escape`, `alt+shift+down`) through
     AppKit's own route (local monitors, key equivalents, first responder);
     `text` types characters as an input method delivers them;
   - `e2e_snapshot` – a window rendered to PNG;
   - `e2e_prefs` – read/write preferences (`NppMac.` prefix implied) and apply;
   - `e2e_clipboard` – the private clipboard (`app.clipboard_info(image=png)`
     puts a picture on it, `files=[...]` file URLs, `type=` reads one type);
   - `e2e_answers` / `e2e_log` – queued answers for NSAlert (button number,
     title, or `{button, field}` for prompts) and open/save panels (path, list,
     or `None` = cancel); the log of what was shown. Unanswered alerts take the
     first button and are logged `unexpected`; unanswered file panels cancel.
     `real_modals=True` lets them run for real, to be driven with `e2e_act`
     from a second connection (`App.call_async`);
   - `e2e_invoke` – call a method / read a key path on `app` (AppDelegate),
     `nsapp`, `editor`, `sci`, `sub`, `window`, `prefs`, `document`,
     `first_responder`, `class:<Name>` (shared instance), `window:<spec>`,
     `delegate:<window spec>`. Use it for state that has no other observable,
     never to skip the user-facing path you are testing;
   - `e2e_mouse` – clicks (1-3, with modifiers) on a control or at a text
     position `{line, column}` in an editor; `button="right"` returns the
     view's context menu (and performs `menu_path` in it) without popping it up —
     for an editor that is the real right-click menu, spelling items included;
     `point={"line": 3, "margin": 5}` clicks in a margin at a line;
   - menus built when opened (`menuNeedsUpdate:`) are filled before e2e_menu reads them;
   - `e2e_act double_click` on a table sends a real double click (clickedRow set);
   - `e2e_counters` – beeps (NppBeep), muted ones apart;
   - `e2e_ui` gives each control `cell_size` (what its text needs), `size`,
     `wraps`, `fits` (cut-off text check); a tab bar (`NppTabBarView`) lists its
     `tabs` (title, modified, pinned, colour, frame in the bar) — click one
     with `e2e_mouse` on `class="NppTabBarView"` at a point inside the frame;
   - `e2e_snapshot frame=True` draws the whole window with title bar and toolbar;
   - `e2e_act resize_window value=[w, h]` (content size, top edge kept);
   - `e2e_keys hold=["ctrl"] keys=[...] release=True` sends flagsChanged
     around the keys (Ctrl+Tab switcher); `keep_held=True` keeps them for later calls;
   - `e2e_mouse` on any view delivers a real mouse down/up (use it for views
     without an action, e.g. the status bar path field);
   - printing never reaches a printer: every print job is saved as
     `.work/<worker>/print/print-N.pdf` without panels and logged (`kind: print`,
     path, margins, orientation);
   - `env={"NPPMAC_E2E_RELEASE_URL": url_or_path}` at start sets the update
     checker's latest-release address;
   - the file-panel log carries `allowed_types`, `can_choose_directories`,
     `can_choose_files`, `multiple`;
   - "Open/Move in New Instance" launches are logged as `open_url_with` and not performed;
   - `e2e_sci view=<editor key>` reads any Scintilla view the editor holds by key;
   - `e2e_menu_invoke` takes `modifiers` (held keys, for commands that read
     them); `e2e_keys` takes `marked={"stages": [...], "commit": "..."}` for an
     input method's composition; `e2e_act double_click` takes `column`;
     `e2e_clipboard set_types={"public.html": "...", "public.rtf": "..."}`;
   - note: `run_command` does not send the menu's will/did-send notifications,
     so a command meant to be recorded into a macro goes through `e2e_menu_invoke`;
   - Finder and the browser are never opened: `NSWorkspace` open/reveal calls
     are logged in `e2e_log` (`kind`: open_url, open_url_with, reveal, open_file);
   - alert answers may also set the accessory's controls:
     `{"button": 1, "fields": [...], "states": {"Check box title": 1}, "popups": {"0": "Item"}, "suppress": true}`;
     `e2e_log` shows the accessory's check boxes and popups as `controls`;
   - `e2e_act` also selects NSMatrix rows (radio groups) and sets NSColorWell
     colours (`set_value "#RRGGBB"`);
   - `e2e_idle` – let the run loop turn (timers, delayed refreshes).
   - `e2e_ax` – a window's accessibility tree as VoiceOver reads it: the
     accessibility server's own answers (AXUIElement on the app's own process, which
     needs no Accessibility permission), per element `role`, `subrole`, `label`,
     `title`, `name` (label, title or linked title element), `value`, `enabled`,
     `actions`, `frame`, text attributes (`number_of_characters`, `selected_range`...),
     and the view under it (`view_class`, `view_path`, `tooltip`); windows add
     `default_button` / `cancel_button`; `focus` is the first responder's view (class,
     path; a field being edited, not the field editor) and `full_keyboard_access` whether
     Tab goes to every control; `key_loop=True` adds the window's `nextKeyView` chain (what
     Tab walks with Keyboard navigation on; `refuses` marks a control that refuses the focus);
     `perform={"path", "action"}`
     performs an accessibility action (AXPress, AXIncrement...) on an element.
     Only windows on screen have elements.

   While an alert or modal window is up, requests are still served (they run
   in the run loop's common modes), so `real_modals=True` + `call_async` +
   `e2e_act` from the main connection drives a real modal.
3. **The command line**: `app.cli` is the copy's `nppmac`.
4. **Files**: what the app writes (saved files, encodings, session.xml,
   backups, exported HTML/RTF) is checked on disk.
5. **Launch options** (`agent_flag=False, wait_socket=False` for a launch
   without the agent flag; `NPPMAC_E2E_CLI_DIR` = `.work/<worker>/bin` is where
   Install Command Line Tool links, never /usr/local/bin): `app.start(args=[...], env={...}, defaults={...})`,
   e.g. `-NppMac.localizationFile russian.xml`, command-line switches
   (`-n42`, `-l python`, `-multiInst`...), `session=True` to keep the session.

## Fixtures (`conftest.py`)

- `app` – the session's running app, reset before each test: queued answers
  cleared, extra windows closed, all documents closed (changes discarded),
  modal log and clipboard emptied. After `close_all()` one empty `new 1`
  remains, as in Notepad++.
- `fresh_app` – restarts with empty preferences and home (slow: ~3 s).
- `tmp` – a scratch folder with symlinks resolved. The app may report such a
  path as `/var/...` (without `/private`): compare with `App.same_path(a, b)`.

A test that changes a preference either uses `fresh_app` or sets it back.

## App helper methods (see `harness/app.py`)

`new(text, language, title)`, `open(path, line)`, `text()`, `set_text()`,
`doc()`, `docs()`, `selection()`, `select(line, col, end_line, end_col)`,
`run(cmd)` (asserts it ran), `run_async(cmd)`, `close_all()`,
`sci(msg, w, l, view, returns)`, `menu(*cmds)`, `menu_item(cmd)`,
`checked(cmd)`, `enabled(cmd)`, `menu_tree(top, depth)`, `windows()`,
`window(spec)`, `ui(window)`, `controls(window, **match)`,
`act(window, action, value, **target)`, `click(window, title)`,
`close_window(w)`, `keys(*chords)`, `type(text)`, `snapshot(path)`,
`prefs(*names)`, `pref(name)`, `set_prefs(**kv)`, `clipboard(set)`,
`answers(alerts, panels, real_modals, clear)`, `modal_log()`,
`invoke(target, selector, args)`, `get(target, keypath)`, `idle(s)`,
`wait(cond, timeout)`, `restart()`, `stop()`, `start()`. `start()` returns once the socket answers; launch-time work
(files from the command line) may still be settling — poll for it.

Scintilla message numbers: `harness/sci.py`.

## Rules for tests

- Observe what a user would see (text, selection, menus, windows, controls,
  files, the status bar) wherever possible; hooks into internals only when
  nothing visible carries the fact.
- Poll (`app.wait`) instead of sleeping.
- Each test is independent and leaves preferences as it found them.
- A test that finds a real defect is marked
  `@pytest.mark.xfail(strict=True, reason="BUG: ...")` and the defect is
  reported as an issue in the NotepadMac repository; the test is not bent to pass.
