# Epic Backlog Triage — local web app

**Status: WITHDRAWN 2026-09-03 — the local web app was never built.**
**Date:** 2026-09-03
**Design canvas:** `bc1cb362-1f06-45f2-a839-ce60fcb96ed3`

> This document is kept as a record, not as a plan. Everything it specifies about a
> server, a control panel, browser-based Epic auth, progress streaming and the
> `web/` split was **dropped before any of it was written**. Three incidental bug
> fixes buried in it *were* implemented, by a different route. Read
> "What was dropped, and why" and "What was actually built" below before taking
> anything here as an instruction.

## What was dropped, and why

**The deciding argument came from this spec's own decision 5.** "One source of truth
for the UI" guarantees the served page and the exported file render the *same
report*. So the server improved nothing about viewing — its entire value was the
control panel. And `run.bat` is already a control panel: double-click it and it
handles login, runs the pipeline, prints progress, and opens the report.

Measured against that, the web panel added: re-running without closing the page,
cancelling with a button instead of Ctrl-C, and pasting the Epic code into a page
instead of a console. The price was five new modules, a process that must stay
running, and a localhost attack surface — CSRF, DNS rebinding, a session token —
that does not exist today at all. Not worth it.

| Dropped | Why |
|---|---|
| The hosted, multi-user website | Epic publishes no library API; `legendary` impersonates the Launcher, so the service would hold strangers' Launcher-scoped OAuth tokens. Rejected on those grounds — see Context, which is still accurate. |
| `serve.py`, `jobs.py`, `epicauth.py` | The server bought only a control panel, and `run.bat` already is one. |
| The control panel in the rail | Nothing to control without the server. The canvas still does not cover it, so nothing was invented. |
| Browser-based Epic auth | `legendary auth` at the console still works and is the documented path. |
| SSE progress streaming | The scripts already print progress to the console `run.bat` shows. |
| The whole security model | Moot with no server. Genuinely load-bearing *if* a server is ever built — do not skim it then. |
| Export as an on-demand button | Export stays a pipeline step in `build_report.py`. |
| `reportdata.py`, the `web/` split | Superseded in fact: Nocturne Phase 2 landed its own `templates/` split the same day. |
| Removing `__HOURS_TH__` via `th-hours hidden` | Not needed once the `web/` split was abandoned. `HOURS_TH` still exists. |
| `run.bat` 7 → 5 steps, README restructuring | Both only made sense as consequences of the server. `run.bat --refresh` therefore still works. |

## What was actually built

Three defects this investigation turned up were real and independent of the server,
so they were fixed on their own, test-first, directly in `build_report.py` — no new
modules, no template edits:

1. **The rendered page had no document shell.** It began at `<title>`. Now wrapped
   in `<!doctype html>`, `<html lang="en">`, `<head>`, `<meta charset="utf-8">` and
   a viewport meta.
2. **`nums["stamp"]` used `date.today()`**, so a page read later than it was built
   misreported its own date. Now `os.path.getmtime(out/games.json)`.
3. **The chained `replace()` let substituted text be substituted again.** A Steam
   tag spelled `__NUMS__` put the entire nums object *inside the tag string* and
   broke the page's JavaScript with a syntax error. Now one `re.sub` pass.

**The doctype fix turned out to fix a fourth, invisible bug.** Measured in headless
Chromium before and after: in quirks mode a table does not inherit font from its
ancestors, so the cells were computing to the browser default `16px/normal` while
`templates/style.css` says `body{font:14px/1.55}` and neither `table` nor `tbody td`
overrides it. The table had never rendered the typography the stylesheet asks for.
In standards mode it computes `14px/21.7px` as intended, which makes rows 4px
taller — not a regression, but a density change worth checking against the artboard.

**One claim in this document is overstated.** The Template extraction section calls
the missing charset a live mojibake bug. It was tested: Chromium detects `UTF-8`
either way. Declaring it is still correct — detection is a guess, and over `file://`
no `Content-Type` can settle it — but it was a latent risk, not an active fault.

## Context

The question that started this was "how can I implement this project to be
available as a website?" The honest answer turned out to be that the report is
*already* a website — `out/report.html` is 312 KB of self-contained markup, CSS
and JS with no server behind it — and that the interesting half of the question
is the Epic library, not the page.

That half does not have the answer it looks like it has. **Epic publishes no API
for reading a user's library.** Epic Account Services offers `basic_profile`,
`friends_list`, `presence` and `country`; there is no library scope. The Ecom Web
APIs verify ownership of *your own* product and cannot enumerate what someone
owns. Epic's own support documentation confirms you cannot view your library on
epicgames.com at all — it requires the Launcher.

`legendary` gets the library by impersonating the Launcher. It hardcodes the
Launcher's own client id and secret (`legendary/api/egs.py:24-25`) and reads
`library-service.live.use1a.on.epicgames.com/library/api/public/items`
(`egs.py:239-250`) — an internal endpoint. Authentication is an interactive
browser flow ending in a pasted `authorizationCode` (`legendary/cli.py:165-205`).
There is no headless variant.

So a hosted multi-user service would require strangers to paste Epic
authorization codes into a website, and would make this project the custodian of
Launcher-scoped OAuth tokens for accounts it does not own — tokens that grant far
more than a game list. The enforcement risk for that lands on *users'* accounts,
where an Epic ban is permanent and forfeits everything purchased. **That option
is rejected on those grounds, not on effort.**

A second finding constrains the alternatives. Steam's store API returns **no CORS
headers at all** — verified live against both `IStoreQueryService/SearchSuggestions/v1`
and `IStoreBrowseService/GetItems/v1` with an `Origin` request header; neither
response carries `Access-Control-Allow-Origin`. A browser therefore cannot call
Steam directly, so no design can push the matching pipeline entirely client-side.

**The outcome *at the time*:** keep the pipeline exactly where it is, and turn the
thing in front of it into a real web app that runs on the user's own machine.
Anyone can use it — they run it themselves. Credentials never leave the machine.
The browser becomes the interface instead of a file you double-click.

> **This conclusion did not survive.** Everything above it — the Epic API findings
> and the Steam CORS result — is verified and still true, and is the reason a hosted
> version is not on the table. The local-web-app conclusion drawn from it was
> abandoned; see "What was dropped, and why" at the top.

## Decisions

> **DROPPED.** Decisions 1, 2, 3 and 6 were abandoned. Decision 4 (stdlib only) and decision 5 (one source of truth) still describe the project — and decision 5 is what argued the rest of them away.

1. **Local web app, `127.0.0.1` only.** Not hosted, not exposed on the LAN. The
   server binds loopback; Epic credentials stay where `legendary` already puts
   them (`~/.config/legendary`) and never cross the network.
2. **Full control panel.** The page shows Epic connection status, starts the Epic
   login, triggers the pipeline, streams live progress, and cancels. `run.bat`
   becomes "start the server and open the browser".
3. **The standalone export survives as a button**, not a pipeline step. It writes
   a self-contained `out/report.html` for sharing and archiving.
4. **Stdlib only.** `http.server`, no Flask, no FastAPI, no Node. `legendary-gl`
   remains the single third-party dependency.
5. **One source of truth for the UI.** The template is extracted from the Python
   raw string into real `web/` files that are *served* over HTTP and *inlined*
   for the export.
6. **The control panel lives at the top of the existing left rail**, built only
   from Nocturne primitives already present in the report.

## Relationship to Nocturne Phase 2

`docs/superpowers/specs/2026-09-03-nocturne-phase-2-design.md` is being worked on
in a concurrent session. Its Task 1 splits the same 750 lines into `templates/`,
aiming for a byte-identical `TEMPLATE`; this spec splits them into `web/` as
served files. **Both cannot happen — that would restructure the same code twice.**

**Resolved: Phase 2 won, and this work was dropped.** Phase 2 landed the same day
(`ae15428` split `TEMPLATE` into `templates/`, then the drawer and FLIP animations
in `671a233`, `bb7718e`, `36bf125`). The conflict is therefore gone — the 750 lines
were restructured once, into `templates/`, not `web/`. The three bug fixes above
were applied on top of that split and touch no template file.

## Architecture

> **DROPPED.** Nothing in this section was built. It is kept because the constraints it documents — the filelock hang, the subprocess reasoning, the SSE pitfalls — are what any future attempt would have to rediscover.

### Module layout

The flat root is the house convention — `unittest discover -b` already works from
`.`, and imports stay `import jobs` alongside `import steamstore`.

```
serve.py         NEW   server, request guard, route table, static whitelist, port, browser
jobs.py          NEW   one-run-at-a-time manager, log ring buffer, SSE fan-out
epicauth.py      NEW   legendary bridge: connection status, code redemption
reportdata.py    NEW   I18N + TAG_ES + REVIEW_ES + aggregate()  (lifted from build_report)
build_report.py  KEPT  shrinks to ~120 lines: page assembly and the standalone export
web/index.html   NEW   document shell + the existing .wrap markup
web/app.css      NEW   build_report.py:258-492, verbatim
web/app.js       NEW   build_report.py:575-1003, six lines changed
web/panel.html   NEW   control panel fragment  }  served only,
web/panel.css    NEW                           }  never inlined
web/panel.js     NEW                           }  into the export
```

Boundaries, one line each: **`reportdata`** is what the numbers are.
**`build_report`** is how a page is assembled. **`serve`** is who asks for it.
**`jobs`** is what is running. **`epicauth`** is who you are.

### Server

`ThreadingHTTPServer`, not `HTTPServer` — an SSE connection is a request that
never returns, so single-threaded the page could not fetch anything while the
pipeline ran.

Two class attributes matter:

- **`allow_reuse_address = False`.** `HTTPServer` defaults it to `True`, which on
  Windows lets a second process bind a port another process is already listening
  on. With the default, port detection silently succeeds on a busy port and two
  servers split connections nondeterministically. Setting it `False` makes
  `bind()` raise `EADDRINUSE` as intended.
- **`protocol_version = "HTTP/1.1"`**, plus `disable_nagle_algorithm = True` for
  SSE latency and an overridden `log_message` so the console the user is watching
  isn't one line per request.

Port **8765** by default, trying 8765–8774. Before falling through to the next
port, probe the busy one with a 0.5 s `GET /api/status`: if it answers with our
own `X-Epic-Backlog: 1` header, print "already running at …", open the browser
there and exit 0 — which is what double-clicking `run.bat` twice should do. Never
bind port 0; a URL that changes every launch breaks the bookmark.

`argparse` for `--port`, `--no-browser`, `--verbose`.

`TCPServer.__init__` binds *and* listens, so the browser can be opened
immediately after the constructor returns — no sleep, no thread, no race.

### Route table

| Method | Path | Response |
|---|---|---|
| GET | `/` | `build_report.index_html(panel=True)` |
| GET | `/app.css` `/app.js` `/panel.css` `/panel.js` | static whitelist |
| GET | `/api/meta` | `{i18n, tag_es, review_es, nums, tags, status_n}` |
| GET | `/api/games` | `out/games.json`, streamed from disk |
| GET | `/api/status` | `{epic, data, run}` |
| GET | `/api/events` | `text/event-stream` |
| POST | `/api/run` | `{steps, refresh}` → 202, or 409 if busy |
| POST | `/api/cancel` | 202 |
| POST | `/api/auth/code` | `{code}` → 200 / 401 / 409 |
| POST | `/api/export` | writes `out/report.html` → `{path, bytes}` |

`/api/games` and `/api/meta` are split so the 303 KB dataset streams straight off
disk via `shutil.copyfileobj` with an `os.stat` `Content-Length`, rather than
being parsed and re-serialised on every page load. `/api/meta` does need the
parse, so `reportdata.aggregate` is memoised on `(st_mtime_ns, st_size)`.

**Static serving uses an explicit dict, never `SimpleHTTPRequestHandler`.** The
server then never joins a request path onto a directory, so `..`, `%2e%2e`, UNC
paths and NTFS alternate data streams (`app.js::$DATA`) are non-issues by
construction rather than things to filter. Content types are hardcoded rather
than taken from `mimetypes`, which reads `HKEY_CLASSES_ROOT` on Windows — a
registry mapping `.js` to `text/plain` would serve a script the browser refuses
to execute once `nosniff` is set. Every text type carries `; charset=utf-8`.

### Running the pipeline: subprocess, not import

The three scripts are spawned as subprocesses. Five reasons, heaviest first:

1. **Cancellation is otherwise impossible.** `epic_steam.enrich()` loops 389
   titles, each a throttled call with `timeout=45` and up to five retries
   containing `time.sleep(min(60, 5 * 2**attempt))` (`steamlib.py:63`). Python
   cannot kill a thread. In-process, "Cancel" would mean threading a `should_stop`
   callback through `steamlib.fetch_json`, `steamstore`, `epic_steam` and
   `pcgw` — every module in the project, in service of the server.
   `proc.terminate()` works on the first sleep.
2. **`sys.exit` is the scripts' error channel** (`epic_steam.py:48,58`,
   `second_pass.py:129`, `build_report.py:1025`). In a subprocess that is already
   a non-zero code and a message on the stream.
3. **Module-level mutable state** — `steamstore._TAGS`/`_CATS`, `steamlib._last`,
   `epic_steam.main`'s `sys.argv` reads — would accumulate across runs in a
   long-lived server.
4. **Crash isolation.** A `MemoryError` mid-run takes down a subprocess, not the
   server the user is watching it through.
5. **Zero changes to the three scripts.** They stay runnable exactly as the
   README documents. The CLI is the fallback when the server itself is broken.

The spawn:

```python
subprocess.Popen(
    [sys.executable, "-X", "utf8", "-u", os.path.join(HERE, script), *args],
    cwd=HERE,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
    bufsize=1, text=True, encoding="utf-8", errors="replace",
)
```

**`-u` is the easiest thing here to get wrong.** `epic_steam.log()` passes
`flush=True`, but `second_pass.py` and `build_report.py` use bare `print()`. Once
stdout is a pipe it block-buffers at ~8 KB, so the second pass would appear to
hang and then dump everything at once. `-u` fixes it without touching the scripts.
`stderr=STDOUT` keeps a traceback in place in the log; `stdin=DEVNULL` stops
anything blocking on an invisible console prompt.

Progress is two-level and free: the scripts already emit `[2/4]` phase markers and
`[137/389]` per-title lines, so a small regex in `jobs.py` yields "phase 2 of 4,
title 137 of 389" with no changes to the pipeline.

**One run at a time**, enforced by a `threading.Lock` inside `jobs.start()` — not
in the browser, because two tabs each have a Run button. A second attempt gets
**409**. A run is a sequence of steps (`epic_steam.py [--refresh]`, then
`second_pass.py`); a non-zero exit skips the rest. `build_report.py` is not a
step — export is its own button.

### Progress streaming (SSE)

One long-lived stream per tab, opened on page load, carrying `log`, `state` and
`auth` events — not one stream per run. That makes `EventSource`'s automatic
reconnect always desirable, and keeps every open tab's buttons in sync.

Each run owns a `collections.deque(maxlen=2000)` of lines (a real run emits ~420,
so this is generous and bounded), a monotonic sequence id so `Last-Event-ID`
replay works, and a set of `queue.Queue(maxsize=4096)` subscribers. On
`queue.Full`, **the subscriber is dropped, not waited on** — a hung browser tab
must never stall the pipeline reader thread.

Three details that are easy to get wrong:

- **Never put a raw log line after `data:`.** A title or traceback containing a
  newline would terminate the frame early. JSON-encode the whole payload as one
  `data:` line and the multi-line rule never applies.
- **No explicit flush is needed.** `StreamRequestHandler.wbufsize == 0`, so
  `self.wfile` is an unbuffered `socketserver._SocketWriter`. The trap is wrapping
  it in a `TextIOWrapper` and forgetting to flush that.
- **A 15-second keepalive comment is how the server notices a dead client.** A
  write to a closed socket raises within a round trip; without periodic writes the
  handler thread sits in `q.get()` forever holding a subscriber slot.

**Closing the tab does not stop a run.** The subprocess belongs to the server, not
the connection; SSE clients are observers. Reopening the page replays the deque
and goes live. The alternative — killing the run when the last observer leaves —
would let an accidental Ctrl-W in minute three discard three minutes of fetching,
which is exactly what the cache exists to prevent.

**Cancel** sets a flag, calls `terminate()`, waits 5 s, then `kill()`. Nothing is
left corrupt: `epic_steam.emit()` is the only writer of `out/games.json` and runs
last, so a kill leaves the previous file intact, and everything fetched so far is
already on disk as complete per-key cache files, so resuming skips straight to
where it stopped.

*Known limitation:* `epic_steam.py` shells out to `legendary` as a grandchild;
`terminate()` on the Python child does not kill `legendary.exe`. An airtight tree
kill on Windows needs a Job Object. The window is a few seconds and a stray
`legendary` writes nothing we read (`_run_legendary` uses `capture_output`), so
ship the simple version and document it.

### Epic auth in the browser

**Do not shell out to `legendary auth`, and do not use pywebview.** With no flags
it either opens a second GUI window — and pywebview on Windows must run on the
main thread, which is `serve_forever` — or sits on `input()` reading a `DEVNULL`
stdin and hangs with no visible prompt. We already have a browser in front of the
user; the paste-the-code path is strictly better here, and it is the path
`cli.py:174-184` already implements.

**Status (`GET /api/status`) must not construct a `LegendaryCore`.** Two measured
reasons: construction costs 150 ms, too slow to poll; and `core.lgd.userdata`
takes a **blocking, no-timeout** `filelock.FileLock` on `user.json.lock` — the
same lock `epic_steam.py`'s `legendary list` child holds across a token refresh.
A status poll during a run would hang a server thread indefinitely.

Instead `epicauth.status()` reads `user.json` directly, resolving the path by
LGDLFS's own rules (`LEGENDARY_CONFIG_PATH` → `$XDG_CONFIG_HOME/legendary` →
`~/.config/legendary`). Sub-millisecond, no import, no lock. `LockedJSONData`
writes non-atomically, so a torn read is caught and reported as `"stale": true`.
**It returns only `displayName` and `expires_at`** — that file also holds
`access_token` and `refresh_token`.

**Connect** is a plain `<a target="_blank" rel="noopener">` to
`https://legendary.gl/epiclogin` — the same URL `cli.py:177` uses, a user
gesture so no pop-up blocking, and one fewer side-effectful endpoint to defend.
Beside it, a text input and a Sign-in button.

**`POST /api/auth/code`** reproduces `cli.py:179-184` exactly, because the
legendary.gl page shows a JSON blob and users will paste the whole thing:

```python
raw = raw.strip()
if raw.startswith("{"):
    raw = json.loads(raw)["authorizationCode"]
code = raw.strip('"').strip()
```

then, with `legendary` imported **lazily inside the function** so `serve.py` stays
importable on a machine that has not run `pip install`:

```python
from legendary.core import LegendaryCore
core = LegendaryCore()
ok = core.auth_code(code)      # returns bool, never raises
```

`core.auth_code` swallows its exception and logs it at ERROR on the `'Core'`
logger. Attach a `logging.Handler` to that logger for the duration of the call and
put what it captured into the 401 body — six lines that turn "it failed" into "the
code expired". Broadcast an `auth` SSE event so other tabs update.

Guards: refuse with **409** while a run is in progress (same lock, same hang);
serialise all `epicauth` calls behind a module lock; return
`{"connected": false, "reason": "legendary is not installed"}` on `ImportError`
rather than a 500; cap the body at 512 chars; **never log the code** — it is a
live credential and the SSE stream is a log.

### Template extraction

The current template starts at `<title>` with **no doctype, no `<html>`, no
`<head>`, no `<meta charset>`**. It works today only because browsers do
quirks-mode recovery plus a locale-dependent default encoding for `file://` URLs.
Since the export contains `·`, `–`, `×`, `▲` and the Spanish payload, **this is
already a live bug** — on a browser defaulting to windows-1252 the export renders
as mojibake. Adding the shell is a fix, not tidiness.

```html
<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title data-i18n="title">Epic Backlog Triage</title>
… the three existing font links …
<link rel="stylesheet" href="/app.css">
<script>/* 3 lines: read localStorage["eb.theme"], set data-theme */</script>
<!--panel-head-->
</head>
<body>
<!--panel-->
   … build_report.py lines 495-571, verbatim …
<script src="/app.js" defer></script>
<!--panel-foot-->
</body>
</html>
```

Three details are load-bearing: `lang="en"` because `applyLang` writes
`document.documentElement.lang` but a document with none is an a11y failure;
`data-theme="dark"` plus the blocking three-line head script, because moving the
JS to `defer` turns today's negligible theme-flash gap into a network round trip;
and `defer` rather than `type="module"`, because the code is an old-style `var`
IIFE that gains nothing from strict mode.

**`__HOURS_TH__` disappears.** It is the only placeholder injecting markup, and it
exists solely because a static string cannot branch — but the page *already*
branches on the same condition client-side at `build_report.py:901`. Put the `<th>`
in `index.html` permanently with `id="th-hours" hidden`, and set
`$("th-hours").hidden = !N.hasHours` at init. `hidden` resolves to `display:none`,
which removes the cell from the column count exactly as omitting it does.

**The other seven placeholders become two endpoints.** `app.js` changes in six
lines: hoist the `var X = __PLACEHOLDER__` declarations into a loader's callback
and move the three init calls inside it.

**One source of truth**, via inlined-first / fetch-fallback:

```js
function load(url, id){
  var el = document.getElementById(id);
  return el ? Promise.resolve(JSON.parse(el.textContent))
            : fetch(url).then(function(r){ return r.json(); });
}
```

The export inlines `app.css` into a `<style>`, `app.js` into a `<script>`, and
`meta`/`data` into two `<script type="application/json">` blocks — with
`_json()`'s `.replace("</", "<\\/")` guard applied to **both** blocks, which is
what stops a game title containing `</script>` from ending it early. The export
carries zero panel bytes.

**A bug class disappears with it:** today `build()` does eight ordered
`str.replace()` calls on one string with `__DATA__` last, so a game titled
`__I18N__` would be substituted. Under the new scheme data goes into its own block
appended to an already-assembled document, never substituted into it.

### What `build_report.py` becomes

**`reportdata.py`** — pure data and pure functions, zero I/O: `EN`/`ES`/`I18N`
(lines 10-195), `TAG_ES`/`REVIEW_ES` (201-246), `median` (was `_median`), and
`aggregate(games, stamp)` returning `{nums, tags, status_n}` lifted from lines
1029-1062. It imports only `collections.Counter`, so it is testable with no
`legendary`, no network and no `out/`.

Its own module because both the server and the exporter need it — if the tables
stayed in `build_report.py`, the server would import the exporter in order to
serve a page, which is backwards.

**One bug to fix while moving.** `nums["stamp"] = datetime.date.today()`
(line 1050) means "today", not "when the data was fetched". Harmless when a page
is generated and read in one sitting; actively wrong for a served page that
outlives the run. Use `os.path.getmtime(out/games.json)` — same field, same
format, correct meaning, and it makes the export reproducible.

**`build_report.py`** keeps `_json()`, gains `read_web()`, `index_html(panel=)`
and `standalone()`, keeps `build()` and its `__main__` guard so
`python build_report.py` still works and the README stays true.

### The control panel

The design canvas holds two artboards — `Backlog Triage.dc.html` and
`Current Report.dc.html` — and **neither covers a control panel**. Per
`CLAUDE.local.md` this was raised rather than guessed at. The decision:

**The panel is a new "Library" section at the top of the existing left rail**,
above the search box, built **only from Nocturne primitives already present in the
report** — the rail's section headings, the counted status-list row pattern, chip
buttons, outlined (never filled) primary buttons, the existing dot indicators —
with every colour, space and radius taken from the tokens already inlined in the
stylesheet. No new visual vocabulary is invented.

Contents, top to bottom: a status dot and the Epic display name (or "Not
connected" plus the connect affordance); a Run button with a refresh checkbox; a
one-line progress readout that expands into the log while a run is in progress;
and an Export button showing the export's age.

**The export's age is shown deliberately.** With export demoted to a button,
`out/report.html` goes stale silently — run the pipeline, never click Export, and
the file someone mails to a friend is last week's data. Showing "Export · 3 runs
old" is cheaper and more honest than auto-exporting.

Panel strings go into `I18N` in **both** languages;
`test_nothing_is_left_in_english_by_accident` enforces it.

### Security

The threat is specific: any page the user visits — an ad iframe, a forum post —
can reach `http://127.0.0.1:8765`. Two endpoints change state, one redeems an Epic
OAuth code, and `/api/games` discloses the entire library.

1. **Host header allowlist — not optional.** Binding `127.0.0.1` does not stop a
   remote page: `attacker.com` resolves publicly, the page loads, the attacker's
   DNS re-answers `127.0.0.1`, and subsequent same-origin XHRs hit loopback while
   the browser still considers the origin `attacker.com`. It sends
   `Host: attacker.com`. A `guard()` at the top of both `do_GET` and `do_POST`,
   before any routing, rejects anything that is not `127.0.0.1` or `localhost`
   with **403**. A browser cannot forge `Host`, so this defeats rebinding
   entirely. Do **not** allow the machine's hostname or LAN IP. This must cover
   `/`, `/api/games` and `/api/events` too — it is the only thing protecting the
   library disclosure.
2. **Mutations are POST-only**, every route asserting its method. A GET route can
   be fired by `<img src>`, `<script src>`, a redirect or a prefetch with no JS.
3. **`Content-Type: application/json` required on mutating routes.** This is what
   actually blocks CSRF: a cross-origin form can only send urlencoded,
   multipart or text/plain, and a cross-origin `fetch` with a JSON content type is
   preflighted — we never answer `OPTIONS` and never send CORS headers, so the
   preflight fails and the real request is never sent. Wrong type → **415**.
4. **`Origin` required and checked** on every POST. `fetch` and XHR always send it,
   so present-and-wrong is a definite attack and missing is refused outright.
5. **A per-session token**, ~10 lines: `secrets.token_urlsafe(24)` at startup,
   emitted into a `<meta>` when `/` is served, sent back as `X-Epic-Token`,
   compared with `hmac.compare_digest`. It is the only control that survives a
   browser bug in `Origin` or preflight handling, and it protects against a
   same-machine non-browser process that can guess the port but cannot read the
   page. In a **header** — never a query string (lands in logs and `Referer`),
   never a cookie (sent automatically, reintroducing CSRF).
   **The GET/POST asymmetry is deliberate:** `EventSource` cannot set headers, so
   all GETs are protected by the Host check alone; all POSTs additionally require
   Origin + JSON content type + token.
6. **Response headers on everything:** `X-Content-Type-Options: nosniff`,
   `Referrer-Policy: no-referrer` (the page links to Steam), `Cache-Control:
   no-store`, and a CSP with `frame-ancestors 'none'`. **No CSP on the export** —
   a `<meta http-equiv>` CSP on a `file://` page needs different allowances and
   will only break it.
7. **Input handling.** Cap the body before reading — `self.rfile.read(int(...))`
   with an attacker-supplied `Content-Length` is an unbounded allocation and
   `BaseHTTPRequestHandler` does nothing for you; refuse >64 KB with **413**.
   `POST /api/run` has a closed vocabulary: `steps` a subset of `{"epic",
   "second"}`, `refresh` a bool. **Never build a command line from request data** —
   script paths are constants and the only flag ever appended is `--refresh`,
   chosen by a boolean. That comment belongs in the code; it is the difference
   between this server and remote code execution.

## Testing

> **DROPPED.** The test plan for the server was never needed. The three fixes that shipped were covered by `TestDocumentIntegrity` in `test_build_report.py` instead.

`python -m unittest discover -b` stays the runner. Budget: 0.264 s today,
~0.4 s after.

**67 tests are untouched** — `test_epic_steam.py`, `test_pcgw.py`,
`test_second_pass.py`, `test_steamlib.py`, `test_steamstore.py` neither import
`build_report` nor touch the template.

**`test_build_report.py` (31)** changes only at the top: `TEMPLATE` and `HOURS_TH`
are gone, replaced by `MARKUP` joined from the `web/` files and `CSS` read
separately. Roughly 20 tests have their subject line changed and their body
untouched; `TestBands`' offsets are identical because the CSS is copied verbatim.
Two get genuinely better: `test_status_rows_carry_a_whole_library_count` currently
asserts `"__STATUS_N__" in TEMPLATE` — a token that no longer exists — and becomes
an assertion about the actual contract (`aggregate()["status_n"]` has seven keys
and sums to `len(games)`); and `TestBuild`'s `var TAGS = (\[.*?\])` regex over
300 KB becomes a parse of the inlined `meta` block. `TestCatalogue` gets stronger
for free — it now scans the panel files too, so every new panel i18n key is
covered.

Two new tests there cover things never tested: that the export is self-contained
(no `/app.css`, `/api/` or surviving `<!--panel` markers) and that it is a whole
document (`<!doctype html>`, `<html lang=`, `<meta charset>`, viewport).

**New, all offline.** The rule that keeps them fast: never spawn a subprocess, and
bind at most one loopback socket.

- **`test_reportdata.py` (~8)** — pure functions on small fixtures.
- **`test_serve.py` (~14)** — **factor routing into a plain
  `route(method, path, headers, body)` function from the start.** That makes ~90%
  of the server testable as ordinary calls with no I/O, and it is painful to
  retrofit. Covers: `Host: evil.example` → 403 on both GET and POST; `GET
  /api/run` → 405; missing/wrong `Origin` → 403; wrong token → 403; `text/plain`
  → 415; `Content-Length: 999999999` → 413 *without allocating*;
  `GET /..%2fsteamlib.py` → 404 (proving the whitelist, not a filter); exact
  content types. One `ThreadingHTTPServer` on **port 0** in `setUpClass` for
  handler integration — loopback only, no DNS, cannot collide with a real
  instance.
- **`test_jobs.py` (~10)** — inject the spawner (`jobs.start(..., spawn=fake)`),
  so no process and no sleep. Second `start()` refused; ring buffer drops oldest;
  a mid-run subscriber gets backlog then live lines; a subscriber with `maxsize=1`
  is dropped and `publish` returns promptly (proving a hung tab cannot stall the
  pipeline); non-zero exit skips remaining steps; **`start(["rm -rf /"])` raises**
  rather than building a command line.
- **`test_epicauth.py` (~5)** — `legendary` stubbed into `sys.modules`. The code
  parser accepts all four shapes `cli.py` accepts; **`status()`'s returned dict
  contains no key whose name contains `token`** — the test that stops a future
  refactor leaking `access_token`; `ImportError` returns rather than raises.

**Untested, honestly:** nothing executes `app.js` or `panel.js`. **A manual
browser pass is a required completion step**, covering: cold start with no `out/`;
opening a fresh tab while a run is in progress; cancel mid-run; close the tab
mid-run and reopen; a deliberately expired auth code; export during a run.

## Staged delivery

> **DROPPED.** No stage ran as written. Only the incidental bug fixes from stages 1 and 2 were implemented, directly and without the module split.

Every stage leaves the project working with a green `unittest discover -b`.
**Stages 2+ wait for Nocturne Phase 2 to land.**

1. **`reportdata.py`.** Move the tables and `_median`, add `aggregate`, fix the
   `stamp` bug. `build_report.py` re-exports the names so existing test imports
   still resolve. *Acceptance: `python build_report.py` produces a byte-identical
   `out/report.html`.* This is the only stage where byte-identity is achievable —
   use it.
2. **Extract to `web/`.** Create `index.html` (shell, `th-hours`, panel markers),
   `app.css`, `app.js`; add `read_web`/`index_html`/`standalone`; delete
   `TEMPLATE` and `HOURS_TH`; update `test_build_report.py`. *Acceptance: the
   export differs from Stage 1's only by the shell and the two script-source
   lines; both render identically in a browser.*
3. **The server, read-only.** `guard()`, static whitelist, `GET /`, `/api/meta`,
   `/api/games`, `/api/status` (data freshness only), port selection with the
   already-running probe, browser open. *Acceptance: a cold start with **no
   `out/` at all** renders the chrome and an empty state, not an error.* Shippable
   on its own.
4. **`jobs.py` + SSE.** Manager with injectable spawner, `/api/events`,
   `/api/run`, `/api/cancel`, full POST guard stack. No UI — drive it from
   `http.client`.
5. **The panel.** `panel.html`/`.css`/`.js`, SSE client, Run/Cancel, log pane,
   status strip, both languages.
6. **`epicauth.py` + the login flow.** Completes decision 2 end to end.
7. **`POST /api/export`** on a worker thread, with the age readout.
8. **`run.bat` + README.** Last, deliberately — the batch file is what a user
   double-clicks and should change once, after the thing it launches is finished.
   7 steps → 5: the Epic-auth step and its ~35 lines of console prompting are
   deleted outright, and the server starts regardless so a user with no Epic
   account can still see the tool.

## Risks and open items

> **DROPPED.** These were risks of building the server. None apply: `run.bat --refresh` still works, the README's headline promise is unchanged, and nothing imports `legendary` outside a subprocess.

- **`run.bat --refresh` breaks.** It currently re-queries the Epic library and is
  promised in two places in the README. `serve.py --refresh` is meaningless;
  `--refresh` moves into the page. A small but real user-visible break.
- **The README's headline promise inverts.** "One self-contained page… needs no
  server" is now the *export*, not the default. The document needs restructuring,
  not just editing: lead with the local app, add "Connecting your Epic account",
  "The control panel", and "Why it only listens on 127.0.0.1" — users will ask
  whether they can run this on a NAS, and the honest answer with its reasons
  belongs in the README.
- **Grandchild `legendary.exe` survives cancel.** Documented, not fixed.
- **`unittest discover -b` now gates server startup in `run.bat`.** `-b` buffers
  stdout, so a hang in `test_serve.py`'s loopback server would hang `run.bat`
  *silently* before the browser opens. Give that test server a socket timeout and
  a `daemon=True` thread so a hang cannot outlive the process.
- **`legendary` is imported into the server process for the first time** (today it
  is only ever a subprocess). Import it lazily inside `epicauth`, never at module
  scope, so `serve.py` starts fast and imports cleanly where `legendary` is absent
  — which the offline tests require.
