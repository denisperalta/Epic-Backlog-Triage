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
