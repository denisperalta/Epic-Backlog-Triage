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
import time
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

# EStoreItemType - a different enum from EStoreAppType above, despite sharing
# the value 0 for their respective "normal" case. `type` alone cannot tell a
# game from a package or a bundle: Steam sells "Borderlands 2 Game of the Year"
# as a package with that exact name and type: 0, and a package carries no
# `appid` at all, so treating `type` as the only discriminator crashes
# item_fields()'s int(item["appid"]) on the first Epic title that names one
# outright. item_type tells packages (1) and bundles (2) apart from apps (0).
APP = 0

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


def is_game(item):
    """True only for an answered, real app, of type GAME, that carries an appid.

    All four checks earn their place: `success` rejects an id Steam would not
    answer for, `item_type` rejects the packages and bundles that also carry
    `type: 0` (see APP above), `type` rejects DLC and soundtracks, and the
    appid check is what actually guards item_fields()'s int(item["appid"]) -
    a package such as "Borderlands 2 Game of the Year" clears `type` on its
    own and needs item_type to be turned away, but the appid check is kept as
    the last line of defence for whatever the next mis-typed item turns out
    to be.
    """
    return bool(item) and (item.get("success") == 1
                           and item.get("item_type") == APP
                           and item.get("type") == GAME
                           and item.get("appid") is not None)


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
        if d is None:
            # A hard transport failure after every retry, not an answer - "we
            # do not know" must not be written down as a remembered miss, or
            # every appid in the chunk is stuck at steam_status: unknown and
            # never retried, delisted games included.
            continue
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
