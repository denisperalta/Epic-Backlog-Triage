# Batched Steam Store API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the three throttled `store.steampowered.com` calls per title with two batched `api.steampowered.com` endpoints, cutting a first run from about an hour to a couple of minutes.

**Architecture:** A new `steamstore.py` owns the Store API - the two endpoints, the id-to-name lookup tables, and the mapping from a store item onto the flat columns of `games.json`. `epic_steam.py` goes back to being orchestration. `appdetails()` and `appreviews()` are deleted, and with them the candidate-probe loop, because the new search endpoint returns full item data inline.

**Tech Stack:** Python 3.8+, standard library only. `unittest`, run offline via `python -m unittest discover -b`.

**Spec:** `docs/superpowers/specs/2026-09-01-steam-batched-store-api-design.md`

## Global Constraints

- **Standard library only.** No new dependencies. `requirements.txt` stays `legendary-gl` alone.
- **Python 3.8 floor.** No walrus in comprehensions, no `dict |` merge, no `str.removeprefix`.
- **Tests must pass offline and silently.** `run.bat` runs `python -m unittest discover -b` before any network work. No test may make a real HTTP request.
- **Comments explain *why*, not *what*.** This codebase's docstrings carry reasoning and name the real game a rule exists for. Match that voice; do not add narrating comments.
- **All four status values stay:** `listed`, `delisted`, `unreleased`, `unknown`, plus `not-on-steam` and `duplicate` which `second_pass.py` assigns.
- **Endpoint constants**, copied verbatim from the spec:
  - `https://api.steampowered.com/IStoreQueryService/SearchSuggestions/v1/`
  - `https://api.steampowered.com/IStoreBrowseService/GetItems/v1/`
  - `https://api.steampowered.com/IStoreService/GetTagList/v1/?language=english`
  - `https://api.steampowered.com/IStoreBrowseService/GetStoreCategories/v1/?language=english`
  - Context: `{"language": "english", "country_code": "US", "steam_realm": 1}`
  - Chunk size **200** (hard ceiling is 243, POST is refused with 405)
  - Throttle bucket `"storeapi"`, delay **0.3**
  - `EStoreAppType`: game `0`, DLC `4`, software `6`, soundtrack `11`

---

### Task 1: Split the HTTP core out of `cached_json`

`get_items` caches one file per appid while fetching many per request, so it cannot use `cached_json`, which is keyed by URL. Extract the transport so both share retry and throttle behaviour.

**Files:**
- Modify: `steamlib.py:47-89` (`cached_json`)
- Test: `test_steamlib.py`

**Interfaces:**
- Produces: `steamlib.fetch_json(url, bucket="steam", delay=1.5, tries=5, post=None, headers=None) -> dict | list | None` - one throttled, retried round trip. `None` on hard failure. No caching.
- Produces: `steamlib.cached_json(...)` - unchanged signature and behaviour, now a disk-cache wrapper over `fetch_json`.

- [ ] **Step 1: Write the failing tests**

Add to `test_steamlib.py`:

```python
import json
import os
import shutil
import tempfile

import steamlib
from steamlib import cached_json, fetch_json


class TestCachedJson(unittest.TestCase):
    """cached_json is now a wrapper; these pin the behaviour it must keep."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        real = steamlib.CACHE
        steamlib.CACHE = self.tmp
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, steamlib, "CACHE", real)

    def test_a_cached_file_is_returned_without_fetching(self):
        """The whole point of the cache: a rerun must not touch the network."""
        with open(steamlib.cache_path("k"), "w", encoding="utf-8") as fh:
            json.dump({"cached": True}, fh)

        def explode(*a, **k):
            raise AssertionError("fetch_json was called for a cached key")

        self.addCleanup(setattr, steamlib, "fetch_json", steamlib.fetch_json)
        steamlib.fetch_json = explode
        self.assertEqual(cached_json("k", "http://example.invalid/"), {"cached": True})

    def test_a_remembered_failure_is_not_retried(self):
        """A cached null means Steam had nothing; asking again just costs time."""
        with open(steamlib.cache_path("k"), "w", encoding="utf-8") as fh:
            json.dump(None, fh)

        def explode(*a, **k):
            raise AssertionError("fetch_json was called for a remembered failure")

        self.addCleanup(setattr, steamlib, "fetch_json", steamlib.fetch_json)
        steamlib.fetch_json = explode
        self.assertIsNone(cached_json("k", "http://example.invalid/"))

    def test_a_fetched_result_is_written_to_the_cache(self):
        self.addCleanup(setattr, steamlib, "fetch_json", steamlib.fetch_json)
        steamlib.fetch_json = lambda *a, **k: {"fresh": 1}
        self.assertEqual(cached_json("k2", "http://example.invalid/"), {"fresh": 1})
        with open(steamlib.cache_path("k2"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"fresh": 1})
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `python -m unittest test_steamlib -v`
Expected: FAIL - `ImportError: cannot import name 'fetch_json' from 'steamlib'`

- [ ] **Step 3: Extract `fetch_json` and rewrite `cached_json` over it**

Replace the whole of `cached_json` in `steamlib.py` with:

```python
def fetch_json(url, bucket="steam", delay=1.5, tries=5, post=None, headers=None):
    """One throttled, retried request, decoded as JSON. None on hard failure.

    Separate from cached_json because the batched store endpoint caches one file
    per appid while fetching two hundred at a time - the cache key and the URL
    stop being the same thing.
    """
    for attempt in range(tries):
        _throttle(bucket, delay)
        try:
            hdrs = {"User-Agent": UA, "Accept": "application/json"}
            if headers:
                hdrs.update(headers)
            body = None
            if post is not None:
                body = json.dumps(post).encode()
                hdrs["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=body, headers=hdrs)
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503):
                time.sleep(min(60, 5 * (2 ** attempt)))
                continue
            return None
        except Exception:
            time.sleep(2 * (attempt + 1))
            continue
    return None


def cached_json(key, url, bucket="steam", delay=1.5, tries=5, post=None, headers=None):
    """Fetch url as JSON, memoised on disk under `key`. Returns None on hard failure.

    A cached null is a remembered failure and is NOT retried, so reruns stay fast.
    """
    path = cache_path(key)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (ValueError, OSError):
            pass

    data = fetch_json(url, bucket, delay, tries, post, headers)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except OSError:
        pass
    return data
```

- [ ] **Step 4: Run the tests and watch them pass**

Run: `python -m unittest test_steamlib -v`
Expected: PASS, all tests including the pre-existing `TestSteamStatus` cases.

- [ ] **Step 5: Commit**

```bash
git add steamlib.py test_steamlib.py
git commit -m "Split fetch_json out of cached_json"
```

---

### Task 2: `steamstore.py` - lookup tables

Store items carry category and tag **ids**. Two endpoints turn those into names, one cached call each per run.

**Files:**
- Create: `steamstore.py`
- Test: `test_steamstore.py`

**Interfaces:**
- Consumes: `steamlib.cached_json` (Task 1).
- Produces: `steamstore.API` (str), `steamstore.CTX` (dict), `steamstore.DATA_REQUEST` (dict), `steamstore.CHUNK` (200), `steamstore.BUCKET` ("storeapi"), `steamstore.DELAY` (0.3), `steamstore.GAME` (0), `steamstore.DLC` (4).
- Produces: `steamstore.tag_names() -> {int: str}` and `steamstore.category_names() -> {int: str}`, both memoised in module globals `_TAGS` and `_CATS` which tests may assign directly.

- [ ] **Step 1: Write the failing test**

Create `test_steamstore.py`:

```python
"""Tests for the Steam store API layer: lookups, item mapping, batching."""
import json
import os
import shutil
import tempfile
import unittest

import steamlib
import steamstore


class CacheDir(unittest.TestCase):
    """Every test here answers from a seeded cache instead of the network."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        real = steamlib.CACHE
        steamlib.CACHE = self.tmp
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, steamlib, "CACHE", real)
        self.addCleanup(setattr, steamstore, "_TAGS", None)
        self.addCleanup(setattr, steamstore, "_CATS", None)
        steamstore._TAGS = None
        steamstore._CATS = None

    def seed(self, key, payload):
        with open(steamlib.cache_path(key), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)


class TestLookups(CacheDir):
    def test_tag_ids_become_names(self):
        self.seed("steam_taglist",
                  {"response": {"tags": [{"tagid": 492, "name": "Indie"},
                                         {"tagid": 3959, "name": "Roguelite"}]}})
        self.assertEqual(steamstore.tag_names()[3959], "Roguelite")

    def test_category_ids_become_names(self):
        self.seed("steam_categories",
                  {"response": {"categories": [{"categoryid": 2,
                                                "display_name": "Single-player"}]}})
        self.assertEqual(steamstore.category_names()[2], "Single-player")

    def test_a_missing_table_is_empty_rather_than_fatal(self):
        """Losing the tag names should cost the Tags column, not the whole run."""
        self.seed("steam_taglist", None)
        self.assertEqual(steamstore.tag_names(), {})
```

- [ ] **Step 2: Run the test and watch it fail**

Run: `python -m unittest test_steamstore -v`
Expected: FAIL - `ModuleNotFoundError: No module named 'steamstore'`

- [ ] **Step 3: Create `steamstore.py` with the constants and lookups**

```python
"""The Steam store API: search, batched appid lookup, and the shape of the answers.

Everything the report needs comes from two endpoints on api.steampowered.com -
the store frontend's own, no key required:

  SearchSuggestions   a search term  -> matching items, their data included
  GetItems            a list of ids  -> the same item shape for each

They replace store.steampowered.com's appdetails and appreviews, which answer
for one appid per request and tolerate roughly one request every 1.6 seconds.
That, not the size of a library, is what made a first run take an hour.

GetItems is capped at 243 ids by URL length rather than by policy, and refuses
POST outright, so the cap cannot be lifted - requests here chunk at 200.

Neither endpoint carries Metacritic scores or Steam's own genres, at any
data_request setting. Weighted tags stand in for genres; nothing stands in for
Metacritic, so the report no longer shows it.
"""
import json
import os
import urllib.parse

from steamlib import cache_path, cached_json, fetch_json, normalise, wilson_lower

API = "https://api.steampowered.com"
CTX = {"language": "english", "country_code": "US", "steam_realm": 1}

# include_tag_count asks for twenty so the weight ordering has something to sort;
# only the first few are ever shown.
DATA_REQUEST = {"include_basic_info": True, "include_reviews": True,
                "include_release": True, "include_tag_count": 20}

CHUNK = 200
BUCKET, DELAY = "storeapi", 0.3

# EStoreAppType, as far as this script cares: everything that is not a game is
# rejected by search, and only the wiki fallback is allowed to accept a DLC.
GAME, DLC = 0, 4

_TAGS = None
_CATS = None


def _url(service, method, payload):
    return "%s/%s/%s/v1/?input_json=%s" % (
        API, service, method, urllib.parse.quote(json.dumps(payload)))


def tag_names():
    """tagid -> name, for every tag Steam knows. One cached call per run."""
    global _TAGS
    if _TAGS is None:
        d = cached_json("steam_taglist",
                        API + "/IStoreService/GetTagList/v1/?language=english",
                        bucket=BUCKET, delay=DELAY) or {}
        _TAGS = {t["tagid"]: t["name"]
                 for t in (d.get("response") or {}).get("tags") or []
                 if t.get("tagid") and t.get("name")}
    return _TAGS


def category_names():
    """categoryid -> name: Single-player, Full controller support, Online Co-op."""
    global _CATS
    if _CATS is None:
        d = cached_json("steam_categories",
                        API + "/IStoreBrowseService/GetStoreCategories/v1/"
                              "?language=english",
                        bucket=BUCKET, delay=DELAY) or {}
        _CATS = {c["categoryid"]: c["display_name"]
                 for c in (d.get("response") or {}).get("categories") or []
                 if c.get("categoryid") and c.get("display_name")}
    return _CATS
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `python -m unittest test_steamstore -v`
Expected: PASS, 3 tests.

- [ ] **Step 5: Commit**

```bash
git add steamstore.py test_steamstore.py
git commit -m "Add steamstore with the store API lookup tables"
```

---

### Task 3: `item_status` - and move the status tests off `steamlib`

Delisting stops being inferred from missing packages and becomes a flag Steam sets.

**Files:**
- Modify: `steamstore.py` (append)
- Modify: `steamlib.py` - delete `steam_status()` (`steamlib.py:116-137`)
- Modify: `test_steamlib.py` - delete `TestSteamStatus`
- Test: `test_steamstore.py`

**Interfaces:**
- Produces: `steamstore.item_status(item) -> "listed" | "delisted" | "unreleased" | "unknown"`

- [ ] **Step 1: Write the failing test**

Add to `test_steamstore.py`:

```python
def item(**over):
    """A store item shaped like a live paid game, as GetItems returns one."""
    it = {"appid": 1145360, "name": "Hades", "type": steamstore.GAME, "success": 1,
          "visible": True, "release": {"steam_release_date": 1600353507}}
    it.update(over)
    return it


class TestItemStatus(unittest.TestCase):
    def test_a_game_on_sale_is_listed(self):
        self.assertEqual(steamstore.item_status(item()), "listed")

    def test_an_unlisted_game_is_delisted(self):
        """Rocket League still has a page and its reviews; Steam stopped selling it."""
        self.assertEqual(
            steamstore.item_status(item(name="Rocket League", unlisted=True)),
            "delisted")

    def test_coming_soon_is_unreleased_not_delisted(self):
        """Dodo Peak sells nothing yet - that is not the same as being pulled."""
        soon = item(name="Dodo Peak", release={"is_coming_soon": True})
        self.assertEqual(steamstore.item_status(soon), "unreleased")

    def test_unreleased_wins_over_unlisted(self):
        """Both flags at once reads as unreleased, as the packages check did."""
        both = item(release={"is_coming_soon": True}, unlisted=True)
        self.assertEqual(steamstore.item_status(both), "unreleased")

    def test_an_app_steam_will_not_answer_for_is_unknown(self):
        """A fully removed app comes back as success 15 with no payload at all."""
        self.assertEqual(steamstore.item_status({"success": 15}), "unknown")

    def test_nothing_at_all_is_unknown(self):
        self.assertEqual(steamstore.item_status(None), "unknown")
```

- [ ] **Step 2: Run the test and watch it fail**

Run: `python -m unittest test_steamstore -v`
Expected: FAIL - `AttributeError: module 'steamstore' has no attribute 'item_status'`

- [ ] **Step 3: Implement `item_status`, and delete `steam_status`**

Append to `steamstore.py`:

```python
def item_status(item):
    """Classify a store item: listed, delisted, unreleased, or unknown.

    Steam used to make this an inference - a pulled game kept its page and its
    reviews but lost every package, so "nothing left to buy, and not free" meant
    delisted. The store API says it outright with `unlisted`, and answers for a
    pulled game the same way it answers for a live one.

    Order matters: an unannounced game has no packages either, so coming_soon is
    checked first, exactly as it was against appdetails.

    "unknown" means Steam would not answer for the appid at all - a fully removed
    app returns success 15 and no payload. Telling that apart from a game that was
    never on Steam is PCGamingWiki's job, in second_pass.
    """
    if not item or item.get("success") != 1:
        return "unknown"
    if (item.get("release") or {}).get("is_coming_soon"):
        return "unreleased"
    if item.get("unlisted"):
        return "delisted"
    return "listed"
```

Delete `steam_status()` from `steamlib.py` entirely, and delete the `TestSteamStatus` class and its `details()` helper from `test_steamlib.py`.

- [ ] **Step 4: Run the full suite**

Run: `python -m unittest discover -v`
Expected: `test_steamstore` and `test_steamlib` PASS. `test_second_pass` and `epic_steam` still import `steam_status` - if the suite reports an ImportError there, that is expected and Task 6 fixes it. Confirm the failure is only that import, nothing else.

- [ ] **Step 5: Commit**

```bash
git add steamstore.py steamlib.py test_steamstore.py test_steamlib.py
git commit -m "Read delisting off the unlisted flag instead of missing packages"
```

---

### Task 4: `item_fields` - a store item becomes a report row

The single mapping function every other module goes through.

**Files:**
- Modify: `steamstore.py` (append)
- Test: `test_steamstore.py`

**Interfaces:**
- Consumes: `tag_names()`, `category_names()`, `item_status()`, `steamlib.wilson_lower`.
- Produces: `steamstore.item_fields(item) -> dict` with keys: `steam_appid`, `matched_name`, `steam_status`, `tags`, `rating`, `reviews`, `positive`, `negative`, `sort_score`, `review_desc`, `release_date`, `coming_soon`, `developer`, `publisher`, `singleplayer`, `multiplayer`, `coop`, `controller`, `steam_url`.

- [ ] **Step 1: Write the failing test**

Add to `test_steamstore.py`. `HADES` is a real `GetItems` response, trimmed:

```python
HADES = {
    "appid": 1145360, "name": "Hades", "type": 0, "success": 1, "visible": True,
    "categories": {"supported_player_categoryids": [2],
                   "feature_categoryids": [22, 29, 23],
                   "controller_categoryids": [28]},
    "reviews": {"summary_filtered": {"review_count": 285375, "percent_positive": 98,
                                     "review_score_label": "Overwhelmingly Positive"}},
    "basic_info": {"developers": [{"name": "Supergiant Games"}],
                   "publishers": [{"name": "Supergiant Games"}]},
    "release": {"steam_release_date": 1600353507,
                "original_steam_release_date": 1575997560},
    "tags": [{"tagid": 42804, "weight": 1052}, {"tagid": 3959, "weight": 766},
             {"tagid": 1646, "weight": 748}, {"tagid": 492, "weight": 737}],
}

NAMED_TAGS = {42804: "Action Roguelike", 3959: "Roguelite", 1646: "Hack and Slash",
              492: "Indie"}
NAMED_CATS = {2: "Single-player", 22: "Steam Achievements", 23: "Steam Cloud",
              29: "Steam Trading Cards", 28: "Full controller support",
              1: "Multi-player", 9: "Co-op", 38: "Online Co-op", 49: "PvP"}


class TestItemFields(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, steamstore, "_TAGS", None)
        self.addCleanup(setattr, steamstore, "_CATS", None)
        steamstore._TAGS = dict(NAMED_TAGS)
        steamstore._CATS = dict(NAMED_CATS)

    def test_the_headline_numbers(self):
        f = steamstore.item_fields(HADES)
        self.assertEqual(f["steam_appid"], 1145360)
        self.assertEqual(f["matched_name"], "Hades")
        self.assertEqual(f["steam_status"], "listed")
        self.assertEqual(f["reviews"], 285375)
        self.assertEqual(f["rating"], 98.0)
        self.assertEqual(f["review_desc"], "Overwhelmingly Positive")
        self.assertEqual(f["steam_url"],
                         "https://store.steampowered.com/app/1145360/")

    def test_positive_and_negative_are_derived_from_the_percentage(self):
        """Steam only gives a whole percent, so the split is reconstructed."""
        f = steamstore.item_fields(HADES)
        self.assertEqual(f["positive"], 279668)
        self.assertEqual(f["negative"], 285375 - 279668)
        self.assertLess(f["sort_score"], f["rating"])

    def test_only_the_three_heaviest_tags_are_kept(self):
        self.assertEqual(steamstore.item_fields(HADES)["tags"],
                         ["Action Roguelike", "Roguelite", "Hack and Slash"])

    def test_a_tag_with_no_known_name_is_skipped_not_numbered(self):
        thin = dict(HADES, tags=[{"tagid": 999999, "weight": 9}] + HADES["tags"][:2])
        self.assertEqual(steamstore.item_fields(thin)["tags"],
                         ["Action Roguelike", "Roguelite"])

    def test_the_release_date_is_the_one_steam_shows(self):
        """Hades left early access in September 2020; the report shows that year."""
        self.assertEqual(steamstore.item_fields(HADES)["release_date"], "2020-09-17")

    def test_an_unreleased_game_has_no_date_and_says_so(self):
        soon = dict(HADES, release={"is_coming_soon": True})
        f = steamstore.item_fields(soon)
        self.assertEqual(f["release_date"], "")
        self.assertTrue(f["coming_soon"])

    def test_player_modes_come_from_all_three_category_lists(self):
        f = steamstore.item_fields(HADES)
        self.assertTrue(f["singleplayer"])
        self.assertTrue(f["controller"])
        self.assertFalse(f["multiplayer"])
        self.assertFalse(f["coop"])

    def test_online_co_op_counts_as_both_multiplayer_and_co_op(self):
        """Dota 2's categories are Multi-player plus Online Co-op, and it is both."""
        social = dict(HADES, categories={"supported_player_categoryids": [1, 38, 49],
                                         "feature_categoryids": [],
                                         "controller_categoryids": []})
        f = steamstore.item_fields(social)
        self.assertTrue(f["multiplayer"])
        self.assertTrue(f["coop"])
        self.assertFalse(f["singleplayer"])

    def test_developers_and_publishers_are_joined_names(self):
        f = steamstore.item_fields(HADES)
        self.assertEqual(f["developer"], "Supergiant Games")
        self.assertEqual(f["publisher"], "Supergiant Games")

    def test_a_game_with_no_reviews_scores_nothing_rather_than_zero(self):
        """An unrated game must sort to the bottom, not to a hard zero."""
        fresh = dict(HADES)
        fresh.pop("reviews")
        f = steamstore.item_fields(fresh)
        self.assertEqual(f["reviews"], 0)
        self.assertIsNone(f["rating"])
        self.assertIsNone(f["sort_score"])

    def test_a_game_with_no_reviews_still_says_so_in_words(self):
        """The report translates that phrase into Spanish; a blank has nothing to translate."""
        fresh = dict(HADES)
        fresh.pop("reviews")
        self.assertEqual(steamstore.item_fields(fresh)["review_desc"],
                         "No user reviews")
```

- [ ] **Step 2: Run the test and watch it fail**

Run: `python -m unittest test_steamstore -v`
Expected: FAIL - `AttributeError: module 'steamstore' has no attribute 'item_fields'`

- [ ] **Step 3: Implement the mapping**

Append to `steamstore.py`:

```python
def _category_names(item):
    """Every category on the item, from the three lists it splits them across.

    The union reproduces the flat list appdetails used to return, byte for byte -
    checked against The Witcher 3, Dota 2 and Hades - so the mode predicates below
    are the same ones, matching on names rather than on ids that Valve may reuse.
    """
    cats = item.get("categories") or {}
    known = category_names()
    return {known[i]
            for key in ("supported_player_categoryids", "feature_categoryids",
                        "controller_categoryids")
            for i in (cats.get(key) or []) if i in known}


def _top_tags(item, limit=3):
    """The heaviest tags, named. `tags` is weight-ordered; `tagids` is not."""
    known = tag_names()
    out = []
    for t in item.get("tags") or []:
        name = known.get(t.get("tagid"))
        if name and name not in out:
            out.append(name)
        if len(out) >= limit:
            break
    return out


def _release_date(item):
    """ISO, in UTC. Only the year is ever displayed, but ISO also sorts right.

    steam_release_date is the date the store shows: for Hades that is the 1.0
    release, not the early access one, which is what the old appdetails string
    said too.
    """
    r = item.get("release") or {}
    ts = (r.get("steam_release_date") or r.get("original_steam_release_date")
          or r.get("original_release_date") or 0)
    return time.strftime("%Y-%m-%d", time.gmtime(ts)) if ts else ""


def item_fields(item):
    """One store item, flattened onto the columns games.json carries.

    Review counts are the store's *filtered* summary - the number the store page
    itself shows. summary_unfiltered exists for only a minority of apps, so it is
    not a usable source.

    percent_positive is a whole number, so the positive/negative split is
    reconstructed rather than reported. Integer arithmetic keeps it deterministic;
    the half-percent of rounding moves the Wilson bound by under 0.02.
    """
    appid = int(item["appid"])
    summary = (item.get("reviews") or {}).get("summary_filtered") or {}
    total = summary.get("review_count") or 0
    pct = summary.get("percent_positive") or 0
    positive = (total * pct + 50) // 100
    cats = _category_names(item)
    info = item.get("basic_info") or {}

    return dict(
        steam_appid=appid,
        matched_name=item.get("name"),
        steam_status=item_status(item),
        tags=_top_tags(item),
        rating=float(pct) if total else None,
        reviews=total,
        positive=positive,
        negative=total - positive,
        sort_score=round(wilson_lower(positive, total), 2) if total else None,
        # Valve's own wording for the empty case, which appreviews used to supply
        # and which the report has a Spanish translation for.
        review_desc=summary.get("review_score_label")
        or ("" if total else "No user reviews"),
        release_date=_release_date(item),
        coming_soon=bool((item.get("release") or {}).get("is_coming_soon")),
        developer=", ".join(d["name"] for d in info.get("developers") or []
                            if d.get("name")),
        publisher=", ".join(p["name"] for p in info.get("publishers") or []
                            if p.get("name")),
        singleplayer="Single-player" in cats,
        multiplayer=any("Multi-player" in c or "PvP" in c for c in cats),
        coop=any("Co-op" in c for c in cats),
        controller="Full controller support" in cats,
        steam_url="https://store.steampowered.com/app/%d/" % appid,
    )
```

Add `import time` to the imports at the top of `steamstore.py`.

- [ ] **Step 4: Run the test and watch it pass**

Run: `python -m unittest test_steamstore -v`
Expected: PASS, all `TestItemFields` cases.

- [ ] **Step 5: Commit**

```bash
git add steamstore.py test_steamstore.py
git commit -m "Map a store item onto the report's columns"
```

---

### Task 5: `search_items` and `get_items`

The two network entry points. `get_items` caches per appid so a rerun that batches differently still costs nothing.

**Files:**
- Modify: `steamstore.py` (append)
- Test: `test_steamstore.py`

**Interfaces:**
- Produces: `steamstore.search_items(term) -> [item]` - relevance-ordered, cached under `find_<normalised term>`.
- Produces: `steamstore.get_items(appids) -> {int appid: item}` - only ids Steam answered for; chunked at `CHUNK`; each appid cached under `item_<appid>`.

- [ ] **Step 1: Write the failing test**

Add to `test_steamstore.py`:

```python
class TestSearchItems(CacheDir):
    def test_results_come_back_in_order(self):
        self.seed("find_" + steamlib.normalise("Hades"),
                  {"response": {"store_items": [HADES, dict(HADES, appid=1, name="B")]}})
        got = steamstore.search_items("Hades")
        self.assertEqual([i["name"] for i in got], ["Hades", "B"])

    def test_an_empty_term_never_reaches_the_network(self):
        self.assertEqual(steamstore.search_items(""), [])

    def test_a_remembered_miss_is_an_empty_list(self):
        self.seed("find_" + steamlib.normalise("Nothing At All"), None)
        self.assertEqual(steamstore.search_items("Nothing At All"), [])


class TestGetItems(CacheDir):
    def test_a_cached_appid_is_not_fetched_again(self):
        self.seed("item_1145360", HADES)

        def explode(*a, **k):
            raise AssertionError("fetched an appid that was already cached")

        self.addCleanup(setattr, steamstore, "fetch_json", steamstore.fetch_json)
        steamstore.fetch_json = explode
        self.assertEqual(steamstore.get_items([1145360])[1145360]["name"], "Hades")

    def test_ids_are_requested_in_chunks(self):
        """Two hundred is the batch; 243 is where the URL stops being accepted."""
        calls = []

        def fake(url, **kw):
            calls.append(url)
            return {"response": {"store_items": []}}

        self.addCleanup(setattr, steamstore, "fetch_json", steamstore.fetch_json)
        steamstore.fetch_json = fake
        steamstore.get_items(range(10, 460))          # 450 ids
        self.assertEqual(len(calls), 3)

    def test_an_appid_steam_will_not_answer_for_is_remembered_as_a_miss(self):
        """A second run must not re-ask for an app that has been removed."""
        self.addCleanup(setattr, steamstore, "fetch_json", steamstore.fetch_json)
        steamstore.fetch_json = lambda url, **kw: {
            "response": {"store_items": [{"appid": 0, "success": 15}]}}
        self.assertEqual(steamstore.get_items([267550]), {})
        self.assertTrue(os.path.exists(steamlib.cache_path("item_267550")))

        def explode(*a, **k):
            raise AssertionError("re-asked for a remembered miss")

        steamstore.fetch_json = explode
        self.assertEqual(steamstore.get_items([267550]), {})

    def test_duplicate_ids_are_asked_for_once(self):
        calls = []

        def fake(url, **kw):
            calls.append(url)
            return {"response": {"store_items": [HADES]}}

        self.addCleanup(setattr, steamstore, "fetch_json", steamstore.fetch_json)
        steamstore.fetch_json = fake
        got = steamstore.get_items([1145360, 1145360, 1145360])
        self.assertEqual(len(calls), 1)
        self.assertEqual(list(got), [1145360])
```

- [ ] **Step 2: Run the test and watch it fail**

Run: `python -m unittest test_steamstore -v`
Expected: FAIL - `AttributeError: module 'steamstore' has no attribute 'search_items'`

- [ ] **Step 3: Implement both**

Append to `steamstore.py`:

```python
def search_items(term):
    """Store items matching a search term, best first, with their data included.

    One request where the old path took two to five: the search itself, then an
    appdetails probe for each candidate appid until one turned out to be a game.
    `type` arrives here, so the wrong kind of hit is rejected without asking.

    Cached under `find_` rather than `search_`, which the retired storefront
    search used for a different payload shape.
    """
    if not term:
        return []
    payload = {"search_term": term[:120], "context": CTX,
               "data_request": DATA_REQUEST}
    d = cached_json("find_" + normalise(term),
                    _url("IStoreQueryService", "SearchSuggestions", payload),
                    bucket=BUCKET, delay=DELAY)
    return ((d or {}).get("response") or {}).get("store_items") or []


def get_items(appids):
    """appid -> store item, for every id Steam still answers for.

    Cached one file per appid rather than one per request, so a rerun that groups
    its batches differently still costs nothing. A null file remembers that Steam
    had nothing, the same bargain cached_json makes.
    """
    out, missing = {}, []
    for appid in dict.fromkeys(int(a) for a in appids):
        path = cache_path("item_%d" % appid)
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    seen = json.load(fh)
                if seen:
                    out[appid] = seen
                continue
            except (ValueError, OSError):
                pass
        missing.append(appid)

    for i in range(0, len(missing), CHUNK):
        chunk = missing[i:i + CHUNK]
        payload = {"ids": [{"appid": a} for a in chunk], "context": CTX,
                   "data_request": DATA_REQUEST}
        d = fetch_json(_url("IStoreBrowseService", "GetItems", payload),
                       bucket=BUCKET, delay=DELAY)
        answered = {}
        for it in ((d or {}).get("response") or {}).get("store_items") or []:
            if it.get("success") == 1 and it.get("appid"):
                answered[int(it["appid"])] = it
        for appid in chunk:
            item = answered.get(appid)
            if item:
                out[appid] = item
            try:
                with open(cache_path("item_%d" % appid), "w",
                          encoding="utf-8") as fh:
                    json.dump(item, fh)
            except OSError:
                pass
    return out
```

- [ ] **Step 4: Run the test and watch it pass**

Run: `python -m unittest test_steamstore -v`
Expected: PASS, all tests in the file.

- [ ] **Step 5: Commit**

```bash
git add steamstore.py test_steamstore.py
git commit -m "Add batched item lookup and search over the store API"
```

---

### Task 6: Rewire `epic_steam.py` onto the store API

Phases 2 and 3 become one request per title. The candidate-probe loop, both store
functions and the retired-endpoint workaround all go.

**Files:**
- Modify: `epic_steam.py` - docstring, imports, `epic_steam.py:99-153` (delete `steam_index`, `_search`, `candidates`), `epic_steam.py:157-176` (delete `appdetails`, `appreviews`), `apply_steam`, `enrich`, `COLUMNS`, `main`
- Test: `test_epic_steam.py` (new)

**Interfaces:**
- Consumes: `steamstore.search_items`, `steamstore.item_fields`, `steamstore.GAME`.
- Produces: `epic_steam.best(title, items) -> item | None` - the closest game in a
  result list, or None.
- Produces: `epic_steam.match(title) -> item | None` - `best()` over a ladder of
  progressively looser queries.
- Produces: `epic_steam.apply_steam(g, item, source="search") -> g` - unchanged
  name and role; second argument is now a store item, not an appid plus data.
- Produces: `epic_steam.enrich(games) -> games` - one argument now, not three.

- [ ] **Step 1: Write the failing test**

Create `test_epic_steam.py`:

```python
"""Tests for matching an Epic title to the right Steam game."""
import unittest

import epic_steam
import steamstore
from test_steamstore import HADES, NAMED_CATS, NAMED_TAGS


def hit(appid, name, type_=steamstore.GAME):
    return dict(HADES, appid=appid, name=name, type=type_)


class TestBest(unittest.TestCase):
    def test_an_exact_name_beats_an_earlier_loose_one(self):
        """Search puts sequels and bundles first often enough to matter."""
        items = [hit(1, "Limbo Soundtrack"), hit(2, "LIMBO")]
        self.assertEqual(epic_steam.best("Limbo", items)["appid"], 2)

    def test_an_edition_suffix_still_matches(self):
        """Epic sells 'Sundered Eldritch Edition'; Steam calls it 'Sundered: Eldritch Edition'."""
        items = [hit(535480, "Sundered: Eldritch Edition")]
        self.assertEqual(
            epic_steam.best("Sundered Eldritch Edition", items)["appid"], 535480)

    def test_dlc_is_never_the_answer(self):
        """A search for the game returns its season pass too; that is not the game."""
        items = [hit(2813100, "Dead Island 2 - Haus", steamstore.DLC)]
        self.assertIsNone(epic_steam.best("Dead Island 2", items))

    def test_a_soundtrack_is_never_the_answer(self):
        items = [hit(807320, "Into the Breach Soundtrack", 11)]
        self.assertIsNone(epic_steam.best("Into The Breach", items))

    def test_an_item_steam_would_not_answer_for_is_skipped(self):
        items = [dict(hit(1, "Ghost"), success=15)]
        self.assertIsNone(epic_steam.best("Ghost", items))

    def test_nothing_matching_is_none(self):
        self.assertIsNone(epic_steam.best("Hades", []))


class TestApplySteam(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, steamstore, "_TAGS", None)
        self.addCleanup(setattr, steamstore, "_CATS", None)
        steamstore._TAGS = dict(NAMED_TAGS)
        steamstore._CATS = dict(NAMED_CATS)

    def test_it_records_where_the_match_came_from(self):
        g = epic_steam.apply_steam({"title": "Hades"}, HADES, source="pcgw")
        self.assertEqual(g["steam_source"], "pcgw")
        self.assertEqual(g["steam_appid"], 1145360)

    def test_epics_developer_fills_in_when_steam_names_none(self):
        """A delisted page often drops its credits; Epic still knows who made it."""
        anon = dict(HADES, basic_info={})
        g = epic_steam.apply_steam(
            {"title": "Hades", "epic_developer": "Supergiant"}, anon)
        self.assertEqual(g["developer"], "Supergiant")

    def test_steams_developer_wins_when_there_is_one(self):
        g = epic_steam.apply_steam(
            {"title": "Hades", "epic_developer": "Stale Value"}, HADES)
        self.assertEqual(g["developer"], "Supergiant Games")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and watch it fail**

Run: `python -m unittest test_epic_steam -v`
Expected: FAIL - `ImportError: cannot import name 'steam_status' from 'steamlib'`, because `epic_steam.py` still imports the function Task 3 deleted.

- [ ] **Step 3: Rewrite the matching and enrichment half of `epic_steam.py`**

Replace the module docstring's phase list:

```python
"""Build a decide-what-to-play list from an Epic library (legendary) + official Steam data.

Phases, each independently cached under cache/ so reruns are cheap:
  1 library   legendary list --json  -> real games only
  2 steam     title -> the Steam store item, in one request per title (steamstore)
  3 hltb      HowLongToBeat playtime (third-party, best effort)
  4 emit      out/games.json, out/games.csv
"""
```

Replace the import lines (`epic_steam.py:10-13`) with:

```python
import csv, json, os, re, subprocess, sys

import steamstore
from steamlib import CACHE, normalise, use_utf8_stdout
```

Delete `steam_index()`, `_search()` and `candidates()` outright, and replace them
with:

```python
# ---------------------------------------------------------------- phase 2
def best(title, items):
    """The closest real game in a result list, or None.

    Search is ordered by Steam's idea of relevance, which is not ours: a query
    for a game returns its soundtrack, its season pass and its sequel too. Rank
    on the normalised name instead, and take nothing that is not a game.
    """
    want, want_loose = normalise(title), normalise(title, True)
    ranked = []
    for it in items:
        if it.get("success") != 1 or it.get("type") != steamstore.GAME:
            continue
        name = it.get("name") or ""
        n, nl = normalise(name), normalise(name, True)
        if n == want:
            rank = 0
        elif nl == want_loose:
            rank = 1
        elif want_loose and (want_loose in nl or nl in want_loose):
            rank = 2
        else:
            rank = 3
        ranked.append((rank, it))
    # Sort on the rank alone: store items are dicts and do not compare.
    ranked.sort(key=lambda r: r[0])
    return ranked[0][1] if ranked else None


def match(title):
    """A Steam store item for an Epic title, trying looser queries in turn."""
    for term in (title, normalise(title, True), re.split(r"[:\-–]", title)[0].strip()):
        found = best(title, steamstore.search_items(term))
        if found:
            return found
    return None
```

Replace `appdetails()`, `appreviews()` and `apply_steam()` with:

```python
# ---------------------------------------------------------------- phase 2 (cont.)
def apply_steam(g, item, source="search"):
    """Copy one resolved Steam store item onto a library entry.

    Shared with second_pass so a title recovered on the second attempt carries
    exactly the same fields, from the same source of truth, as one matched first
    time round.
    """
    fields = steamstore.item_fields(item)
    fields["steam_source"] = source
    # Steam drops the credits from some pulled pages; Epic still knows who made it.
    fields["developer"] = fields["developer"] or g.get("epic_developer", "")
    g.update(fields)
    return g


def enrich(games):
    total = len(games)
    for i, g in enumerate(games, 1):
        item = match(g["title"])
        if not item:
            # Not "no Steam listing" yet - only that search, which answers for
            # games currently on sale, did not offer one. second_pass tells apart
            # delisted, never-there and simply not found.
            g.update(steam_appid=None, matched_name=None, steam_status="unknown")
            log(f"  [{i}/{total}] {g['title'][:52]:<52} -- no Steam match")
            continue

        apply_steam(g, item)
        log(f"  [{i}/{total}] {g['title'][:52]:<52} {g['rating'] or 0:>6}%  "
            f"n={g['reviews']:<7} sort={g['sort_score'] or 0:>6}")
    return games
```

- [ ] **Step 4: Renumber the phase logs and update `COLUMNS` and `main`**

There are four phases now, not five. Change every `[n/5]` log string in
`epic_steam.py`: both `[1/5]` lines in `epic_library` become `[1/4]`, the three
`[4/5]` lines in `hltb_hours` become `[3/4]`, and `emit`'s `[5/5]` becomes `[4/4]`.
The `[2/5]` and `[3/5]` lines belonged to functions this task deleted.

Replace `COLUMNS` - `metacritic` is gone and `genres` is now `tags`:

```python
COLUMNS = ["title", "steam_status", "rating", "reviews", "sort_score", "review_desc",
           "tags", "hltb_main", "release_date", "developer", "publisher",
           "singleplayer", "multiplayer", "coop", "controller", "duplicate_of",
           "steam_appid", "steam_source", "steam_url", "matched_name", "app_name"]
```

Replace `main()`:

```python
def main():
    use_utf8_stdout()
    refresh = "--refresh" in sys.argv
    games = epic_library(refresh)
    log(f"[2/4] matching {len(games)} games against the Steam store ...")
    games = enrich(games)
    if "--no-hltb" not in sys.argv:
        games = hltb_hours(games)
    emit(games)
```

- [ ] **Step 5: Run the suite**

Run: `python -m unittest discover -v`
Expected: `test_epic_steam`, `test_steamstore`, `test_steamlib`, `test_pcgw` PASS.
`test_second_pass` still fails - it drives `resolve_via_wiki`, which Task 7
replaces. Confirm nothing else fails.

- [ ] **Step 6: Commit**

```bash
git add epic_steam.py test_epic_steam.py
git commit -m "Match and enrich in one request per title"
```

---

### Task 7: Rewire `second_pass.py`

The variants ladder moves to the new search. The wiki fallback settles all its
appids in one batched call instead of one request each.

**Files:**
- Modify: `second_pass.py` - docstring, imports, `resolve_via_wiki` -> `wiki_pass`, `main`
- Modify: `test_second_pass.py` - `TestResolveViaWiki`

**Interfaces:**
- Consumes: `steamstore.search_items`, `steamstore.get_items`, `steamstore.GAME`, `steamstore.DLC`, `epic_steam.apply_steam`.
- Produces: `second_pass.wiki_pass(games) -> int` - resolves every entry in `games`
  that still has no appid, and returns how many it recovered. Replaces
  `resolve_via_wiki(g) -> bool`.

- [ ] **Step 1: Rewrite the wiki tests**

In `test_second_pass.py`, replace the `DELISTED_DETAILS` constant and the whole
`TestResolveViaWiki` class with:

```python
DELISTED_ITEM = {
    "appid": 389140, "name": "Horizon Chase Turbo", "type": 0, "success": 1,
    "visible": True, "unlisted": True,
    "categories": {"supported_player_categoryids": [2]},
    "reviews": {"summary_filtered": {"review_count": 5939, "percent_positive": 92,
                                     "review_score_label": "Very Positive"}},
    "basic_info": {"developers": [{"name": "AQUIRIS"}],
                   "publishers": [{"name": "AQUIRIS"}]},
    "release": {"steam_release_date": 1527638400},
    "tags": [{"tagid": 699, "weight": 100}],
}


class TestWikiPass(unittest.TestCase):
    """Drives the real fallback, answered from a seeded cache instead of the network."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        real = steamlib.CACHE
        steamlib.CACHE = self.tmp
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, steamlib, "CACHE", real)
        self.addCleanup(setattr, steamstore, "_TAGS", None)
        self.addCleanup(setattr, steamstore, "_CATS", None)
        steamstore._TAGS = {699: "Racing"}
        steamstore._CATS = {2: "Single-player"}

    def seed(self, key, payload):
        with open(steamlib.cache_path(key), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    def seed_wiki(self, title, page_title, wikitext):
        self.seed("pcgw_" + steamlib.normalise(title),
                  {"query": {"pages": {"1": {"title": page_title,
                   "revisions": [{"slots": {"main": {"*": wikitext}}}]}}}})

    def test_pulls_the_scores_of_a_game_steam_no_longer_sells(self):
        """The whole point: a delisted game still has reviews, and they should count."""
        self.seed_wiki("Horizon Chase Turbo", "Horizon Chase Turbo", HAS_APPID)
        self.seed("item_389140", DELISTED_ITEM)

        g = {"title": "Horizon Chase Turbo", "epic_developer": "AQUIRIS"}
        self.assertEqual(wiki_pass([g]), 1)
        self.assertEqual(g["steam_appid"], 389140)
        self.assertEqual(g["steam_status"], "delisted")
        self.assertEqual(g["steam_source"], "pcgw")
        self.assertEqual(g["reviews"], 5939)
        self.assertEqual(g["rating"], 92.0)
        self.assertGreater(g["sort_score"], 90.0)
        self.assertEqual(g["tags"], ["Racing"])

    def test_an_article_with_no_appid_means_never_on_steam(self):
        """Fortnite has a page; it has no Steam appid, and never did."""
        self.seed_wiki("Fortnite", "Fortnite", NO_APPID)

        g = {"title": "Fortnite", "epic_developer": "Epic Games"}
        self.assertEqual(wiki_pass([g]), 0)
        self.assertEqual(g["steam_status"], "not-on-steam")
        self.assertIsNone(g.get("steam_appid"))

    def test_no_article_leaves_the_verdict_open(self):
        """Not knowing is a different answer from knowing it was never there."""
        self.seed("pcgw_" + steamlib.normalise("Death Stranding Content"),
                  {"query": {"pages": {"-1": {"title": "Death Stranding Content",
                                              "missing": ""}}}})

        g = {"title": "Death Stranding Content", "epic_developer": ""}
        self.assertEqual(wiki_pass([g]), 0)
        self.assertEqual(g["steam_status"], "unknown")

    def test_an_appid_steam_will_not_answer_for_stays_unknown(self):
        """The wiki can name an appid for a game Steam has removed outright."""
        self.seed_wiki("Gone Game", "Gone Game", HAS_APPID)
        self.seed("item_389140", None)

        g = {"title": "Gone Game", "epic_developer": ""}
        self.assertEqual(wiki_pass([g]), 0)
        self.assertEqual(g["steam_status"], "unknown")

    def test_an_entry_that_already_matched_is_left_alone(self):
        g = {"title": "Hades", "steam_appid": 1145360, "steam_status": "listed"}
        self.assertEqual(wiki_pass([g]), 0)
        self.assertEqual(g["steam_status"], "listed")
```

Update that file's imports to `from second_pass import mark_duplicates, wiki_pass`
and add `import steamstore`.

- [ ] **Step 2: Run the test and watch it fail**

Run: `python -m unittest test_second_pass -v`
Expected: FAIL - `ImportError: cannot import name 'wiki_pass' from 'second_pass'`

- [ ] **Step 3: Rewrite `second_pass.py`**

Replace the second paragraph of the module docstring, which names the retired
endpoints:

```python
"""Retry the titles that phase 2 could not match, and settle why the rest failed.

Steam's store search only answers to fairly literal names, so Epic entries
carrying branch markers ("(Beta)", "Test branch"), episode numbering or trailing
subtitles come back empty. This walks a ladder of progressively looser queries
and stops at the first one that yields a real base game.

It also answers for games no query can reach. Search only lists what Steam
currently sells, so a delisted game and one that was never on Steam both come
back as nothing at all. PCGamingWiki tells them apart, and gives the appid that
GetItems still answers for, so a pulled game keeps its reviews and its place in
the ranking instead of sinking to the bottom unexplained. Every entry ends up
carrying a steam_status: listed, delisted, not-on-steam, duplicate, unreleased,
or unknown.
"""
import json, os, re
from collections import Counter

import pcgw
import steamstore
from steamlib import normalise, use_utf8_stdout
import epic_steam as E
```

`STEAM_FIELDS` loses `genres` and gains `tags`:

```python
STEAM_FIELDS = ("steam_appid", "matched_name", "tags", "rating", "reviews", "positive",
                "negative", "sort_score", "review_desc", "release_date",
                "developer", "publisher", "singleplayer", "multiplayer", "coop",
                "controller", "steam_url", "steam_source")
```

Replace `resolve_via_wiki` with:

```python
def wiki_pass(games):
    """Ask PCGamingWiki about everything still unmatched, then settle it in one call.

    Steam's search only answers for games it currently sells, so everything that
    reaches here is either delisted, never on Steam, or named too oddly to find.
    The wiki knows which: an article carrying a Steam appid means the game is on
    Steam and the store simply stopped offering it, an article without one means
    it was never there, and no article at all means nobody can say.

    The appids the wiki hands back are looked up together rather than one at a
    time - the wiki call is the slow part, so there is no reason to pay for a
    round trip per game on top of it.
    """
    pending = []
    for g in games:
        if g.get("steam_appid"):
            continue
        appid, page_title = pcgw.steam_appid(g["title"])
        if not appid:
            g["steam_status"] = "not-on-steam" if page_title else "unknown"
            continue
        pending.append((g, appid))

    items = steamstore.get_items([appid for _, appid in pending])
    fixed = 0
    for g, appid in pending:
        item = items.get(appid)
        # A search hit of type "dlc" is a soundtrack dragged in by a loose query
        # and gets rejected, but the wiki points at one deliberate page - and Steam
        # files The Vanishing of Ethan Carter Redux as DLC - so it is taken here.
        if not item or item.get("type") not in (steamstore.GAME, steamstore.DLC):
            g["steam_status"] = "unknown"
            continue
        E.apply_steam(g, item, source="pcgw")
        print("  + %-46s via PCGamingWiki -> %s (%s)"
              % (g["title"][:46], g["matched_name"], g["steam_status"]))
        fixed += 1
    return fixed
```

Replace the search block inside `main()` - the loop over `variants` - with:

```python
    fixed = 0
    for g in stuck:
        for v in variants(g["title"]):
            items = steamstore.search_items(v)
            if not items:
                continue
            want = normalise(g["title"], True)
            for it in items[:3]:
                if it.get("success") != 1 or it.get("type") != steamstore.GAME:
                    continue
                got = normalise(it.get("name") or "", True)
                # Guard against the loose queries dragging in an unrelated game.
                # Compare with spaces removed so "KillingFloor2Beta" still meets
                # "Killing Floor 2".
                a, b = got.replace(" ", ""), want.replace(" ", "")
                if not (a and b and (a == b or a in b or b in a)):
                    continue
                E.apply_steam(g, it)
                fixed += 1
                print("  + %-46s via %-28r -> %s"
                      % (g["title"][:46], v[:28], it.get("name")))
                break
            if g.get("steam_appid"):
                break

    fixed += wiki_pass(stuck)
```

- [ ] **Step 4: Run the suite**

Run: `python -m unittest discover -v`
Expected: PASS everywhere except `test_build_report`, which Task 8 fixes.

- [ ] **Step 5: Commit**

```bash
git add second_pass.py test_second_pass.py
git commit -m "Settle wiki-resolved appids in one batched lookup"
```

---

### Task 8: Report - drop Metacritic, rename Genre to Tags

**Files:**
- Modify: `build_report.py` - `EN`/`ES` dicts, `GENRE_ES`, the CSS, the template, the JS, `build()`
- Modify: `test_build_report.py`

**Interfaces:**
- Consumes: `tags` on each game row (Task 6's `COLUMNS`).
- Produces: `build_report.TAG_ES` (renamed from `GENRE_ES`).

- [ ] **Step 1: Update the tests first**

In `test_build_report.py`:

- In `test_nothing_is_left_in_english_by_accident`, drop `"th_mc"` from the
  exemption tuple, leaving `("lang_en", "lang_es")`.
- Rename `test_genres_seen_in_a_real_library_are_covered` to
  `test_tags_seen_in_a_real_library_are_covered`, point it at
  `build_report.TAG_ES`, and use names that are actually tags:

```python
    def test_tags_seen_in_a_real_library_are_covered(self):
        """The overlap between Steam's tags and the genre names this map was built for."""
        for tag in ("Action", "Adventure", "Casual", "Early Access", "Indie",
                    "Massively Multiplayer", "RPG", "Racing", "Simulation",
                    "Sports", "Strategy"):
            self.assertIn(tag, build_report.TAG_ES)
```

- In `TestBuild.setUp`, drop `"metacritic": 80` and rename the two `"genres"` keys
  to `"tags"`:

```python
            json.dump([{"title": "A Game", "steam_status": "listed", "rating": 92.5,
                        "reviews": 1200, "sort_score": 90.8, "review_desc": "Very Positive",
                        "tags": ["Action"], "release_date": "2020-01-01",
                        "developer": "Someone", "singleplayer": True},
                       {"title": "Gone Game", "steam_status": "delisted", "rating": None,
                        "reviews": 0, "tags": []}], fh)
```

- [ ] **Step 2: Run the tests and watch them fail**

Run: `python -m unittest test_build_report -v`
Expected: FAIL - `AttributeError: module 'build_report' has no attribute 'TAG_ES'`

- [ ] **Step 3: Edit the two language dictionaries**

In `EN` (`build_report.py:32-64`):

```python
    "ph_search": "Search title, tag or developer…",
    "al_tags": "Filter by tag",
    "opt_tags": "All tags",
    "th_tags": "Tags",
```

Delete the `"so_mc"` and `"th_mc"` entries.

In `ES` (`build_report.py:125-157`):

```python
    "ph_search": "Busca por título, etiqueta o desarrollador…",
    "al_tags": "Filtrar por etiqueta",
    "opt_tags": "Todas las etiquetas",
    "th_tags": "Etiquetas",
```

Delete the `"so_mc"` and `"th_mc"` entries here too.

Rename `GENRE_ES` to `TAG_ES` and update the comment above it:

```python
# Steam hands over tags and review tiers as English prose, so the Spanish page
# needs its own names for them - Valve's own store wording. Anything absent here
# falls through untranslated rather than vanishing from the page, which is what
# most of the four hundred-odd tags do.
TAG_ES = {
```

- [ ] **Step 4: Edit the template, CSS and JS**

Delete the `.mc{...}` CSS rule at `build_report.py:385`.

In the template:

```html
      <select id="tags" data-i18n-al="al_tags" aria-label="Filter by tag">
        <option value="" data-i18n="opt_tags">All tags</option>__TAGS__
```

Delete the Metacritic sort option line entirely:

```html
        <option value="metacritic|-1" data-i18n="so_mc">Metacritic, high first</option>
```

Replace the two table headers - the genre one changes, the MC one is deleted:

```html
        <th data-k="tags"><span data-i18n="th_tags">Tags</span> <span class="ar"></span></th>
```

In the JS:

- `function genreName(g){ return (LANG === "es" && GENRE[g]) || g; }` becomes
  `function tagName(g){ return (LANG === "es" && TAG[g]) || g; }`
- delete `function mcColour(s){ ... }`
- `g._base` uses `(g.tags || [])`
- `g._hay = g._base + " " + (g.tags || []).map(tagName).join(" ").toLowerCase();`
- `each("#tags option", function(o){ if (o.value) o.textContent = tagName(o.value); });`
- the filter reads `var gen = $("tags").value;` and tests `(g.tags || []).indexOf(gen) === -1`
- the row builder maps `(g.tags || [])` through `tagName`, and the whole
  Metacritic `<td>` - the three lines beginning `'<td class="num">' + (g.metacritic`
  - is deleted
- the listener list becomes `["q", "tags", "status", "sp", "co", "pad"]`
- the reset handler sets `$("tags").value = ""`

- [ ] **Step 5: Update `build()`**

```python
    tags = sorted({x for g in games for x in (g.get("tags") or [])})
    opts = "".join('<option value="%s">%s</option>' % (_esc(t), _esc(t)) for t in tags)
```

and the three replacements plus the summary line:

```python
            .replace("__TAGS__", opts)
            .replace("__TAG_MAP__", _json(TAG_ES))
```

```python
    print("wrote %s  (%.0f KB, %d games, %d rated, %d tags)"
          % (path, len(html) / 1024.0, len(games), len(rated), len(tags)))
```

Rename the `__GENRE_MAP__` placeholder in the template to `__TAG_MAP__` and the
`var GENRE =` it fills to `var TAG =`. Update the docstring at
`build_report.py:821` - it explains that genre names carry ampersands - to say
tags.

- [ ] **Step 6: Run the suite**

Run: `python -m unittest discover -v`
Expected: PASS, every test in every file. `test_every_placeholder_is_filled` is
the one that catches a missed `__GENRES__` / `__GENRE_MAP__` rename, and
`test_no_string_is_defined_and_never_used` catches an orphaned `so_mc`.

- [ ] **Step 7: Commit**

```bash
git add build_report.py test_build_report.py
git commit -m "Drop the Metacritic column and relabel Genre as Tags"
```

---

### Task 9: Documentation, and clear the stale cache

Every passage describing the old fetch path is now wrong. The spec lists them line
by line; this task works through that list.

**Files:**
- Modify: `README.md`
- Modify: `run.bat` - the `[6/7]` banner and the self-check comment
- Delete: `cache/` contents

- [ ] **Step 1: Clear the orphaned cache**

Every `details_*.json` and `reviews_*.json` file answers for an endpoint nothing
calls now, and the `search_*.json` files hold the retired payload shape.

```bash
rm -rf cache
```

The directory is recreated on import by `steamlib`, and it is gitignored, so
nothing is committed here.

- [ ] **Step 2: Rewrite the README passages**

Work through the spec's table. The substantive ones:

- **Line 24**, the requirements table: `| **About an hour, once** | ... |` becomes
  `| **A couple of minutes** | Every HTTP response is cached, so later runs take seconds |`
- **Lines 37 and 44**: "an hour into fetching" becomes "minutes into fetching";
  "rather than an hour" becomes "rather than minutes".
- **Line 137**, in *Reading the report*:

  > **The filters stack.** The search box matches title, tag, developer and publisher; the two
  > dropdowns narrow by tag and by Steam status; the *min reviews* slider steps through 0, 100, 500,

- **Lines 145-150**, in *English or Spanish* - two sentences change:

  > Switching translates the interface, Steam's
  > tag names and its review tiers (*Very Positive* becomes *Muy positivas*), and reformats numbers

  > alone — they are names, not text. Filtering and sorting are unaffected: the tag dropdown shows
  > translated names but still matches on what Steam actually sent. Steam has some four hundred
  > tags and only the common ones are translated; the rest stay in English rather than disappear.

- **Lines 170-174**, *How a game gets its numbers*: steps 2 and 3 become one step,
  and the list renumbers to four:

  > 2. **Match** — each title goes to `api.steampowered.com/IStoreQueryService/SearchSuggestions`,
  >    which answers with the matching store items and their reviews, tags, categories, release
  >    date and developer already attached. Results are ranked by how exactly the name matches
  >    (exact, then edition-stripped, then substring), and anything that is not a base game — DLC,
  >    a soundtrack, a demo — is rejected without a second request.

- **Line 183**, the end of the *Verdict* step:

  > its infobox when there is one. That appid is enough, because `GetItems` keeps answering for a
  > pulled game long after the store stops offering it.

- **Line 204**, *Why a game has no score* - replace the whole three-line paragraph:

  > Delisted games are not inferred any more: the store API marks a pulled title `unlisted`, and
  > still hands over its page, its metadata and its reviews. An unannounced game is checked first,
  > since it has nothing to sell either.
- **File inventory** near line 262: add
  `steamstore.py     the Steam store API: search, batched lookup, item -> row` and
  update the `steamlib.py` line, which no longer mentions store status.

Add a short note under *How a game gets its numbers* recording what was traded
away, since a reader comparing the report to a Steam page will notice:

> Review counts are Steam's filtered totals - the number its own store page shows.
> The report has no Metacritic column and no Steam genres, because the batched
> endpoints do not carry either; the Tags column stands in for genres.

- [ ] **Step 3: Rewrite the `run.bat` banner**

```bat
echo [6/7] reading your library and fetching Steam data ...
echo       The first run takes a couple of minutes. Every reply is cached, so
echo       every run after this one finishes in seconds.
echo.
```

And the comment above the self-check:

```bat
rem checkout is caught before the Epic login and the Steam fetching,
```

- [ ] **Step 4: Verify the docs match the code**

Run: `grep -rn "appdetails\|appreviews\|SearchApps\|Metacritic\|an hour" README.md run.bat *.py`
Expected: no hits outside `docs/superpowers/`, which records the history
deliberately.

Run: `python -m unittest discover -b`
Expected: silent, exit 0.

- [ ] **Step 5: Commit**

```bash
git add README.md run.bat
git commit -m "Update the docs for the batched store API

The screenshot still shows the Metacritic column and needs reshooting."
```

---

### Task 10: End-to-end check against the live API

The suite is offline by design, so nothing so far has proved the endpoints still
answer as the spec describes.

**Files:** none - this is a verification task.

- [ ] **Step 1: Fetch a small real library slice**

```bash
python -c "
import steamstore as s
it = s.search_items('Hades')[0]
f = s.item_fields(it)
print(f['matched_name'], f['rating'], f['reviews'], f['tags'], f['release_date'])
print(f['singleplayer'], f['controller'], f['steam_status'])
"
```

Expected: `Hades 98.0 <a number near 285000> ['Action Roguelike', 'Roguelite',
'Hack and Slash'] 2020-09-17` then `True True listed`.

- [ ] **Step 2: Check a delisted game resolves**

```bash
python -c "
import steamstore as s
print(s.item_status(s.get_items([252950])[252950]))
"
```

Expected: `delisted` (Rocket League).

- [ ] **Step 3: Run the real pipeline end to end**

```bash
python epic_steam.py && python second_pass.py && python build_report.py
```

Expected: the run finishes in a couple of minutes rather than an hour; the final
line reports a match count comparable to the previous run's, and `out/report.html`
opens with a Tags column and no MC column.

- [ ] **Step 4: Compare the match rate**

The previous run matched most of the library. If the new match count is
meaningfully lower, the ranking in `best()` is at fault, not the endpoints - check
the titles that regressed before accepting the result.

- [ ] **Step 5: Commit anything the run revealed**

Only if a fix was needed. Otherwise this task ends with a verified report and no
commit.
