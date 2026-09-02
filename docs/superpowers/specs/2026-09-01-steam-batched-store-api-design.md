# Batched Steam Store API

**Status:** approved, not yet implemented
**Branch:** `steam-batched-store-api`

## Problem

A first run takes about an hour. The cost is almost entirely rate-limit waiting on
two `store.steampowered.com` endpoints, both of which answer for exactly one appid
per request:

| call | throttle | calls per title |
|---|---|---|
| `SearchApps` | 0.7s | 1 |
| `appdetails` | 1.6s | 1-4 (one per candidate, most discarded) |
| `appreviews` | 1.6s | 1 |

For the 390 titles in a real library that is roughly 35-55 minutes of sleeping.
`appdetails` rejects multiple appids outright (HTTP 400), so the per-request
ceiling cannot be raised.

## Endpoints

Two `api.steampowered.com` endpoints replace all three. Neither needs an API key.
Both are the store frontend's own, undocumented but public, and catalogued at
steamapi.xpaw.me.

### `IStoreQueryService/SearchSuggestions/v1`

Takes a search term, returns matching store items **with their full data inline** -
reviews, tags, categories, release, developers, `type`. One request replaces a
search plus up to four `appdetails` probes.

Measured: ~0.33s per call. Correct top hit on 12 of 12 titles sampled at random
from the real library.

### `IStoreBrowseService/GetItems/v1`

Takes a list of appids, returns the same store-item shape for each.

- **243 appids per request** is the hard ceiling; 244 returns HTTP 414. The limit is
  URL length, and POST is rejected (HTTP 405), so it cannot be raised. Chunk at 200.
- 100 appids in one request: 0.87s. 40 back-to-back requests: no throttling observed.

Used wherever an appid arrives from somewhere other than search - in practice the
PCGamingWiki fallback.

### Lookup tables

`IStoreService/GetTagList/v1` (446 tags) and
`IStoreBrowseService/GetStoreCategories/v1` (72 categories) turn the ids in a store
item into names. One cached call each per run.

## What the new endpoints do not carry

Both were verified absent under every `data_request` flag:

- **Metacritic** - no equivalent field. The column is removed.
- **Genres** - store items carry weighted *tags* instead. Steam's genre ids are a
  separate namespace from tag ids (RPG is genre 3, tag 122), so genres cannot be
  reconstructed. The column becomes the **top 3 tags by weight**, relabelled Tags.

Both losses were accepted deliberately in favour of a ~2 minute run.

## Architecture

New module `steamstore.py` owns the Store API and the shape of its responses.
`epic_steam.py` returns to orchestration only.

```
steamstore.py
  search_items(term)   -> [item]          SearchSuggestions, cached per normalised term
  get_items(appids)    -> {appid: item}   GetItems, chunked at 200, cached per appid
  tag_names()          -> {tagid: name}   GetTagList, cached
  category_names()     -> {catid: name}   GetStoreCategories, cached
  item_fields(item)    -> {flat fields}   store item -> games.json columns
  item_status(item)    -> listed | delisted | unreleased | unknown
```

Supporting changes:

- **`steamlib.py`**: the retry/throttle/HTTP core of `cached_json` is extracted into
  `fetch_json(url, bucket, delay, tries)`. `cached_json` keeps its URL-keyed
  behaviour on top of it. `get_items` uses `fetch_json` directly so it can cache
  **per appid** rather than per URL - without this, a rerun whose batches group
  differently would miss cache entirely.
- **`steam_status()` leaves `steamlib.py`** and becomes `item_status()` in
  `steamstore.py`. It classifies store items now, not appdetails nodes. Its tests
  move with it.
- `appdetails()` and `appreviews()` are **deleted**. Nothing calls them afterward.

## Data flow

Phases 2 and 3 of `epic_steam.py` merge into one request per title:

```
items = steamstore.search_items(title)      # search + data, one call
pick  = first item of type 0 (game), ranked by normalised-name closeness
apply_steam(g, item)
```

The `candidates()` -> `appdetails()` probe loop is deleted. `type` arrives inline, so
DLC (4), soundtracks (11) and software (6) are rejected without a second request.

The existing `normalise()`-based ranking is **kept** rather than trusting the
endpoint's relevance order - it is what stops a loosened query landing on an
unrelated game, and it is already proven against this library.

`second_pass.py` keeps its structure. The variants ladder calls `search_items()`;
the PCGamingWiki fallback collects its resolved appids and settles them in one
batched `get_items()` call.

Throttling: a new `storeapi` bucket at **0.3s**. No rate limiting was observed at
any cadence tested; this is politeness margin, not a measured limit. 390 titles
lands at roughly 2 minutes.

## Field mapping

Every field in `out/games.json` keeps its name and type. The sources change:

| field | was | becomes |
|---|---|---|
| `matched_name` | `data.name` | `item.name` |
| `genres` | `genres[].description` | top 3 tags (see below) resolved through `tag_names()` |
| `rating` | `100 * pos / total` | `reviews.summary_filtered.percent_positive` |
| `reviews` | `total_reviews` | `summary_filtered.review_count` |
| `positive` / `negative` | exact integers | `round(count * pct/100)` and the remainder |
| `sort_score` | Wilson(pos, total) | Wilson(derived pos, count) |
| `review_desc` | `review_score_desc` | `review_score_label` |
| `release_date` | `"19 May, 2015"` | ISO `"2015-05-18"` |
| `coming_soon` | `release_date.coming_soon` | `release.is_coming_soon` |
| `developer` / `publisher` | `developers[]` | `basic_info.developers[].name` |
| `steam_url` | built from appid | built from appid (unchanged) |
| `metacritic` | `metacritic.score` | **removed from `COLUMNS`** |

Three notes on fidelity:

- **Review counts are the store's filtered summary.** `summary_unfiltered` exists
  for only a minority of apps, so `summary_filtered` - what the store page itself
  shows - is the only usable source. It differs slightly from today's
  `purchase_type=all` totals (Witcher 3: 821,567 vs 831,379).
- **`percent_positive` is an integer**, so `positive`/`negative` are derived and
  carry up to a half-percent of rounding. The effect on the Wilson lower bound is
  under 0.02 points at any realistic review count.
- **`release_date` as ISO is invisible.** `build_report.py` only regexes a 4-digit
  year out of that string; ISO satisfies it and sorts correctly besides.

### Tags

A store item carries both a `tagids` list and a `tags` list of
`{tagid, weight}` objects. The **`tags` list is the source** - it is explicitly
weight-ordered, so `genres` becomes the first three entries resolved through
`tag_names()`. A tagid with no name in the lookup table is skipped rather than
rendered as a number, and a game with fewer than three tags simply gets fewer.
`include_tag_count` is requested as 20 so the ordering has something to sort.

### Player modes

`GetItems` splits categories into `supported_player_categoryids`,
`feature_categoryids` and `controller_categoryids`. Resolving all three through
`category_names()` and taking the **union** reproduces `appdetails`' flat category
list exactly - verified byte-identical on The Witcher 3, Dota 2 and Hades, with all
four predicates agreeing.

Today's predicates are therefore kept verbatim, matching on names rather than ids:

```python
singleplayer = "Single-player" in cats
multiplayer  = any("Multi-player" in c or "PvP" in c for c in cats)
coop         = any("Co-op" in c for c in cats)
controller   = "Full controller support" in cats
```

### Status

`item_status()` reads the answer directly instead of inferring it from missing
packages. The conditions are checked **in this order** - an unreleased game that is
also unlisted reads as unreleased, matching today's behaviour, where `coming_soon`
is tested before the package check:

| # | condition | status |
|---|---|---|
| 1 | absent, or `success != 1` | `unknown` |
| 2 | `release.is_coming_soon` | `unreleased` |
| 3 | `unlisted` | `delisted` |
| 4 | otherwise | `listed` |

`unlisted` was verified against Rocket League (252950) and Marvel's Avengers
(997070). Fully removed apps return `success: 15` with no payload and fall to
`unknown`, which is what `appdetails` does today - the PCGamingWiki fallback that
separates *delisted* from *never on Steam* stays necessary and unchanged.

## Report changes

- Remove the Metacritic column: header, cell, sort option, and the `th_mc` / `so_mc`
  strings in both languages.
- Relabel Genre to **Tags** / **Etiquetas** - header, filter label, dropdown
  default, and the search placeholder, in both languages.
- `GENRE_ES` stays. Nine of its entries (Action, Adventure, Indie, RPG, Casual,
  Racing, Sports, Strategy, Simulation) are also tag names, so the common tags still
  translate and the rest fall through untranslated - already the documented
  behaviour of that map.
- Correct the footer credit, which currently names Metacritic and genres.
- README: the "about an hour, once" row, the phase list, and the methodology
  paragraph.

## Cache

The endpoint change orphans every `details_*.json` and `reviews_*.json` file.
`cache/` is generated and gitignored, so it is **deleted wholesale** as part of this
change rather than migrated.

## Testing

New `test_steamstore.py`, offline with stubbed fetches, in the existing style -
plain `unittest`, small builder helpers, docstrings naming the real game each case
came from:

- `item_fields()` maps a trimmed real payload onto the flat columns
- all four `item_status()` cases, including `success: 15`
- category union to the four mode predicates
- top-3 tag selection by weight, and a game with fewer than 3 tags
- `get_items()` chunks above 200 and skips appids already cached
- derived `positive`/`negative` rounding, and a zero-review game

Updated: `test_steamlib.py` (status tests move out; `fetch_json` split),
`test_second_pass.py` (wiki fallback now goes through `get_items`),
`test_build_report.py` (no Metacritic column).

The suite stays offline and silent - `run.bat` runs it before any fetching, so a
bad checkout still fails in seconds rather than mid-run.
