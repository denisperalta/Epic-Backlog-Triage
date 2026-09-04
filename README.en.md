# Epic Backlog Triage

**Versión en español:** [README.md](README.md)

## TL;DR

Pulls your Epic Games library with [legendary](https://github.com/derrod/legendary), matches every
title against Steam review data, and renders a single offline HTML report ranked by a confidence
score — so you can pick something to play instead of scrolling a launcher full of games you've
never opened. Nothing is tied to the original author's account: clone the repo, connect your own
Epic login, and you get your own library, ranked the same way. On Windows, double-click `run.bat`;
everyone else follows the three commands under [Setup by hand](#setup-by-hand).

## Index

- [What you need](#what-you-need)
- [Quick start (Windows)](#quick-start-windows)
- [Setup by hand](#setup-by-hand)
- [Reading the report](#reading-the-report)
- [What lands where](#what-lands-where)
- [How a game gets its numbers](#how-a-game-gets-its-numbers)
- [Why a game has no score](#why-a-game-has-no-score)
- [The confidence score](#the-confidence-score)
- [Playtime](#playtime)
- [Troubleshooting](#troubleshooting)
- [Files](#files)
- [License](#license)

![The report: 389 games from one Epic library, ranked by confidence score](docs/screenshot.png)

## What you need

| | |
|---|---|
| **Python 3.8+** | Standard library only |
| **An Epic Games account** | Read-only: just the library listing |
| **A couple of minutes** | Every HTTP response is cached, so later runs take seconds |

Windows, macOS and Linux all work. The Epic Games Launcher does **not** need to be installed.

## Quick start (Windows)

Download or clone the repo, then double-click `run.bat`. It:

1. finds a Python 3.8+ (the `py` launcher first, avoiding the Microsoft Store stub)
2. builds a private `.venv` in the folder
3. installs legendary into it
4. runs the test suite, so a bad checkout stops here instead of mid-fetch
5. opens the Epic login the first time only
6. fetches your library and Steam data, retrying misses and settling delisted titles
7. renders `out/report.html` and opens it

Run it again any time — it reuses the environment and cache, so later runs take seconds. Flags
pass through to the fetch step: `run.bat --refresh` re-reads your Epic library instead of the
cache. A failed step stops there and explains what to do; the window stays open so you can read it.

## Setup by hand

Use this on macOS/Linux, or on Windows if you'd rather drive it yourself.

### 1. Get the code and install legendary

```sh
git clone <this-repo-url>
cd "Epic Games List"

python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

python -m pip install -r requirements.txt
```

On macOS/Linux use `python3` wherever this doc says `python`. The venv is optional —
`python -m pip install --user legendary-gl` also works; if your shell then can't find `legendary`,
the scripts fall back to running it through the same interpreter.

### 2. Connect your Epic account

This is the one step that's yours rather than the repo's — legendary needs your permission to read
your library, which means an interactive Epic login. The scripts never see your password.

```sh
legendary auth
```

What to expect:

1. A browser tab opens to Epic's real login page (`epicgames.com` in the address bar). Log in as
   usual — email/username, password, 2FA if you use it.
2. Nothing opened automatically? Go to <https://legendary.gl/epiclogin> and log in there instead.
3. After logging in, the tab redirects to a plain page of raw text starting with `{` — that's
   correct, not an error. It looks like:

   ```json
   {"authorizationCode":"3b1a9f...", "expiresInSeconds":600, ...}
   ```

4. Select all of it (Ctrl+A / Cmd+A) and copy it (Ctrl+C / Cmd+C) — the whole block, braces
   included.
5. Switch back to the terminal, which is waiting for it, paste it, and press Enter. legendary
   extracts the code itself.

The code expires within a few minutes; if pasting fails, reload the login page for a fresh one and
repeat from step 3.

Prefer passing the code directly instead of through the prompt? Extract just the value between the
quotes after `"authorizationCode":` and run:

```sh
legendary auth --code <authorization code>
```

Already signed into the Epic Games Launcher? `legendary auth --import` takes the session from it
(and signs the launcher out). Confirm with:

```sh
legendary status
```

It should print your display name. Credentials live in legendary's own config directory
(`%USERPROFILE%\.config\legendary` on Windows, `~/.config/legendary` elsewhere) — never in this
repo.

### 3. Build the report

```sh
python epic_steam.py      # library -> Steam data        -> out/games.json, out/games.csv
python second_pass.py     # retry the titles that missed    (optional, recommended)
python build_report.py    # render                       -> out/report.html
```

The first `epic_steam.py` run is slow on purpose — Steam is rate-limited, so requests are
throttled and cached under `cache/`. Later runs read the cache and finish in seconds.

| Flag | Effect |
|---|---|
| `--refresh` | Re-query legendary instead of the cached library dump |
| `--no-hltb` | Skip the HowLongToBeat phase |

## Reading the report

One self-contained file: no server, no build step, no dependencies. Open it from disk, mail it,
carry it on a stick — the only network request is for webfonts, and everything has a system
fallback.

Filters stack: search matches title/tag/developer/publisher, the status dropdown narrows by Steam
listing, the min-reviews slider steps through 0/100/500/2,000/10,000/50,000 (opens at 100), and
Solo/Co-op/Controller keep only games declaring that support. **Reset** clears everything. Sort
from the dropdown or a column heading; click again to flip direction.

Tags stack and narrow: picking two tags shows games with **both**, not either — *Action* +
*Open World* is the eleven open-world action games, not the hundred-odd that are one or the other.
Each chip has an ×, *Clear tags* drops them all.

The page opens in your browser's language (Windows follows the system display language); the
`ES`/`EN` switch at top right overrides and remembers it. Switching translates the UI, Steam's tag
names and review tiers, and reformats numbers/dates for the locale — titles, developers and
publishers stay as-is since they're names. Filtering/sorting is unaffected by language. Steam has
~400 tags; only the common ones are translated, the rest stay in English.

## What lands where

```
out/report.html   the page you actually look at
out/games.json    every field, one object per game
out/games.csv     the same rows, for a spreadsheet
cache/            one JSON file per appid, plus your library dump
```

`out/` and `cache/` are generated and git-ignored — your library never ends up in a commit. Delete
either at any time; the scripts recreate what they need.

## How a game gets its numbers

1. **Library** — `legendary list --json -T`, keeping entries categorized `games` or `software`
   (drops Unreal Engine assets/plugins/sample projects, keeps oddities like RPG in a Box).
2. **Match** — each title queries Steam's `SearchSuggestions` endpoint, which returns matching
   store items with reviews, tags, categories, release date and developer attached. Results rank
   by name-match closeness (exact, then edition-stripped, then substring); DLC/soundtracks/demos
   are rejected outright.
3. **Second pass** — `second_pass.py` retries empty matches with looser queries: drop `(Beta)`,
   drop the subtitle, strip punctuation, split concatenated words. Matches are still name-checked;
   duplicate Epic entries landing on the same Steam page are merged.
4. **Verdict** — anything still unmatched is looked up on PCGamingWiki, which covers delisted and
   never-on-Steam games alike (Steam's search only knows what it currently sells). The wiki's
   Steam appid, when present, is enough — `GetItems` still answers for pulled games long after the
   store stops listing them.

Review counts are Steam's filtered totals, the same number its store page shows. There's no
Metacritic column and no Steam genres — the batched endpoints don't carry either, so Tags stands
in for genre.

## Why a game has no score

Every row carries a `steam_status`:

| Status | Meaning |
|---|---|
| `listed` | On sale on Steam now, or free to play |
| `delisted` | Pulled from sale, but the page and reviews survive — **scored and ranked normally** |
| `not-on-steam` | PCGamingWiki has an article listing no Steam appid: never there |
| `duplicate` | A second Epic entry for a game already listed |
| `unreleased` | Steam has a page, dated in the future |
| `unknown` | Nothing found either way |

Pick a status from the **Any Steam status** dropdown to see just those — doing so also lifts the
min-reviews floor, so categories with no reviews to count don't stay hidden.

Delisted is read directly from Steam's own `unlisted` marker, not inferred. A wiki match is weaker
than a Steam search hit and is flagged as such — hover the badge to see which page it landed on; a
reused name can occasionally pick the wrong release (Epic's free 2014 *Unreal Tournament* vs.
PCGamingWiki's 1999 article of the same title).

## The confidence score

Raw positive-review percentage puts *100% from 14 reviews* above *98% from 300,000* — backwards
for deciding what to play. `sort_score` is instead the **Wilson 95% lower bound** on the
positive-review proportion:

```
         p + z²/2n - z·√( p(1-p)/n + z²/4n² )
score = ──────────────────────────────────────   ,  z = 1.96
                    1 + z²/n
```

It starts at the raw rating and pulls down the fewer reviews there are. Hades (98.01%, 308k
reviews) barely moves, to 97.96; a game at 100% on 14 reviews lands near 78.

## Playtime

Not included. HowLongToBeat's search endpoint now rejects direct requests, and this project
doesn't forge a browser session to get around that. `epic_steam.py` probes once, logs it's
unavailable, and moves on; `build_report.py` drops the Hours column when no data is present. If
HLTB reopens, both halves work again with no code changes.

## Troubleshooting

**`Could not run legendary`** — not installed in the interpreter you're running; rerun
`python -m pip install -r requirements.txt` with the same `python`.

**`legendary could not list your library`** — almost always auth. Run `legendary status`; if it
doesn't show your display name, redo [step 2](#2-connect-your-epic-account).

**Lots of games with no Steam data** — a dropped connection mid-run caches failures as `null` and
won't retry them. Clear and rerun:

```sh
python -c "import json,glob,os; [os.remove(p) for p in glob.glob('cache/*.json') if json.load(open(p,encoding='utf-8')) is None]"
```

**Stale review counts** — delete `cache/item_*.json` and rerun `epic_steam.py`.

**A game matched to the wrong Steam page** — delete the matching `cache/find_<title>.json` and
rerun; that title re-matches from scratch.

**Garbled titles in the terminal** — cosmetic; stdout is UTF-8 but a legacy-codepage terminal can
still draw glyphs wrong. `out/games.json` and the report are UTF-8 regardless.

## Files

```
run.bat           Windows one-click: environment, self-check, login, fetch, report
epic_steam.py     phases 1-5: library -> match -> Steam -> playtime -> emit
second_pass.py    retries unmatched titles, then settles delisted vs never-there
pcgw.py           PCGamingWiki lookup: title -> Steam appid, for titles search hides
steamstore.py     the Steam store API: search, batched lookup, item -> row
build_report.py   renders out/games.json into a sortable HTML page, in English and Spanish
steamlib.py       cached/throttled HTTP, name normalisation, Wilson score
test_*.py         unit tests: matching, delisting, the report and its two languages
requirements.txt  legendary-gl (the scripts themselves are standard library only)
LICENSE           MIT
docs/             the screenshot at the top of this README
cache/            one JSON file per appid, not per response  (generated, git-ignored)
out/              games.json, games.csv, report.html   (generated, git-ignored)
```

Run tests with `python -m unittest discover` — no network, no cache of yours touched.

## License

[MIT](LICENSE) for the code. What it fetches isn't: review numbers and store metadata are Valve's,
article data is [PCGamingWiki's](https://www.pcgamingwiki.com/wiki/PCGamingWiki:Copyrights). Both
are read through their public endpoints, rate-limited, and cached locally rather than redistributed.
