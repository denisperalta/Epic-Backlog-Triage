"""Build a decide-what-to-play list from an Epic library (legendary) + official Steam data.

Phases, each independently cached under cache/ so reruns are cheap:
  1 library   legendary list --json  -> real games only
  2 match     title -> Steam appid   (official GetAppList, SearchApps fallback)
  3 steam     appreviews + appdetails per matched appid
  4 hltb      HowLongToBeat playtime (third-party, best effort)
  5 emit      out/games.json, out/games.csv
"""
import csv, json, os, re, subprocess, sys, time, urllib.parse

from steamlib import (CACHE, cached_json, cache_path, normalise, use_utf8_stdout,
                      wilson_lower)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
LIBRARY = os.path.join(CACHE, "_epic_library.json")


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- phase 1
LEGENDARY_HELP = """legendary is the Epic Games client this script reads your library through.
  install:       python -m pip install -r requirements.txt
  authenticate:  legendary auth      (or: legendary auth --code <authorization code>)
  confirm:       legendary status"""


def _run_legendary(args):
    """Run legendary and hand back the finished process.

    pip does not always leave the console script somewhere PATH can see it - an
    unactivated venv, a --user install on Windows - so fall back to calling the
    package with this very interpreter before declaring it missing.
    """
    attempts = [["legendary"] + args,
                [sys.executable, "-c", "from legendary.cli import main; main()"] + args]
    for cmd in attempts:
        try:
            # Explicit UTF-8: legendary hands back JSON with the real game titles
            # in it, and decoding those through a machine's local code page
            # either mangles them or raises outright.
            return subprocess.run(cmd, capture_output=True, timeout=600,
                                  encoding="utf-8", errors="replace")
        except FileNotFoundError:
            continue
    sys.exit("Could not run legendary.\n\n" + LEGENDARY_HELP)


def epic_library(refresh=False):
    if refresh or not os.path.exists(LIBRARY):
        log("[1/5] querying legendary ...")
        # -T keeps titles that are not installable through Epic itself (EA/Origin
        # activations and similar); without it legendary silently hides them.
        proc = _run_legendary(["list", "--json", "-T"])
        if proc.returncode != 0:
            sys.exit("legendary could not list your library.\n\n"
                     + LEGENDARY_HELP + "\n\n" + (proc.stderr or "")[-2000:])
        with open(LIBRARY, "w", encoding="utf-8") as fh:
            fh.write(proc.stdout)
    with open(LIBRARY, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    games = []
    for entry in raw:
        meta = entry.get("metadata") or {}
        paths = {c.get("path") for c in meta.get("categories") or []}
        # Engine and marketplace content is the only thing to strip: every asset,
        # plugin and sample project carries 'asset-format', and nothing playable
        # does. Keying off that instead of requiring 'games' keeps entries Epic
        # files under 'software' (RPG in a Box) that are still yours to run.
        if "asset-format" in paths:
            continue
        if not paths & {"games", "software"}:
            continue
        title = entry.get("app_title") or meta.get("title") or ""
        if not title:
            continue
        games.append({
            "title": title,
            "app_name": entry.get("app_name"),
            "epic_developer": meta.get("developer") or "",
            "epic_namespace": meta.get("namespace") or "",
        })
    seen, uniq = set(), []
    for g in sorted(games, key=lambda g: g["title"].lower()):
        key = normalise(g["title"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(g)
    log(f"[1/5] {len(raw)} library entries -> {len(uniq)} games")
    return uniq


# ---------------------------------------------------------------- phase 2
def steam_index():
    """Valve retired ISteamApps/GetAppList (404s as of 2026), so matching goes
    through the storefront's own search endpoint instead - one cached request
    per title, and it handles punctuation/subtitle differences better anyway."""
    log("[2/5] matching via Steam storefront search")
    return None, None


def _search(term):
    if not term:
        return []
    hits = cached_json("search_" + normalise(term),
                       "https://steamcommunity.com/actions/SearchApps/"
                       + urllib.parse.quote(term[:120]),
                       bucket="community", delay=0.7)
    out = []
    for h in hits or []:
        try:
            out.append((int(h["appid"]), h.get("name") or ""))
        except (KeyError, TypeError, ValueError):
            pass
    return out


def candidates(title, _exact=None, _loose=None):
    """Ordered appid guesses for an Epic title, best first."""
    hits = _search(title)
    if not hits:
        hits = _search(normalise(title, True))
    if not hits:
        hits = _search(re.split(r"[:\-–]", title)[0].strip())
    if not hits:
        return []

    want, want_loose = normalise(title), normalise(title, True)
    ranked = []
    for appid, name in hits:
        n, nl = normalise(name), normalise(name, True)
        if n == want:
            rank = 0
        elif nl == want_loose:
            rank = 1
        elif want_loose and (want_loose in nl or nl in want_loose):
            rank = 2
        else:
            rank = 3
        ranked.append((rank, appid, name))
    ranked.sort(key=lambda r: r[0])

    seen, ordered = set(), []
    for _, appid, _name in ranked:
        if appid not in seen:
            seen.add(appid)
            ordered.append(appid)
    return ordered[:4]


# ---------------------------------------------------------------- phase 3
def appdetails(appid):
    d = cached_json(f"details_{appid}",
                    f"https://store.steampowered.com/api/appdetails?appids={appid}&l=english",
                    bucket="store", delay=1.6)
    if not d:
        return None
    node = d.get(str(appid)) or {}
    return node.get("data") if node.get("success") else None


def appreviews(appid):
    d = cached_json(f"reviews_{appid}",
                    f"https://store.steampowered.com/appreviews/{appid}"
                    "?json=1&language=all&purchase_type=all&num_per_page=0",
                    bucket="store", delay=1.6)
    if not d or d.get("success") != 1:
        return None
    return d.get("query_summary")


def enrich(games, exact, loose):
    total = len(games)
    for i, g in enumerate(games, 1):
        chosen = None
        for appid in candidates(g["title"], exact, loose):
            data = appdetails(appid)
            if not data:
                continue
            # Reject DLC, soundtracks, demos, videos - we want the playable base game.
            if data.get("type") != "game":
                continue
            chosen = (appid, data)
            break

        if not chosen:
            g.update(steam_appid=None, matched_name=None)
            log(f"  [{i}/{total}] {g['title'][:52]:<52} -- no Steam match")
            continue

        appid, data = chosen
        summary = appreviews(appid) or {}
        pos = summary.get("total_positive") or 0
        neg = summary.get("total_negative") or 0
        tot = summary.get("total_reviews") or 0
        cats = {c.get("description") for c in data.get("categories") or []}

        g.update(
            steam_appid=appid,
            matched_name=data.get("name"),
            genres=[x.get("description") for x in data.get("genres") or [] if x.get("description")],
            rating=round(100.0 * pos / tot, 2) if tot else None,
            reviews=tot,
            positive=pos,
            negative=neg,
            sort_score=round(wilson_lower(pos, tot), 2) if tot else None,
            review_desc=summary.get("review_score_desc") or "",
            metacritic=(data.get("metacritic") or {}).get("score"),
            release_date=(data.get("release_date") or {}).get("date") or "",
            coming_soon=bool((data.get("release_date") or {}).get("coming_soon")),
            developer=", ".join(data.get("developers") or []) or g["epic_developer"],
            publisher=", ".join(data.get("publishers") or []),
            singleplayer="Single-player" in cats,
            multiplayer=any("Multi-player" in c or "PvP" in c for c in cats),
            coop=any("Co-op" in c for c in cats),
            controller="Full controller support" in cats,
            steam_url=f"https://store.steampowered.com/app/{appid}/",
        )
        log(f"  [{i}/{total}] {g['title'][:52]:<52} {g['rating'] or 0:>6}%  "
            f"n={tot:<7} sort={g['sort_score'] or 0:>6}")
    return games


# ---------------------------------------------------------------- phase 4
HLTB_API = "https://howlongtobeat.com/api/search/site"


def _hltb_payload(name):
    return {"searchType": "games", "searchTerms": name.split(), "searchPage": 1, "size": 5,
            "searchOptions": {"games": {"userId": 0, "platform": "", "sortCategory": "popular",
                                        "rangeCategory": "main",
                                        "rangeTime": {"min": None, "max": None},
                                        "gameplay": {"perspective": "", "flow": "", "genre": "",
                                                     "difficulty": ""},
                                        "modifier": ""},
                              "users": {"sortCategory": "postcount"},
                              "lists": {"sortCategory": "follows"},
                              "filter": "", "sort": 0, "randomizer": 0}}


def hltb_hours(games):
    """Best-effort main-story playtime.

    HowLongToBeat gates /api/search/site behind a browser session fingerprint and
    answers direct requests with 403 {"error":"Session expired or invalid fingerprint"}.
    We probe once and give up if that is still the case - working around a deliberate
    block is not something this script does. Playtime simply stays blank and the
    report drops the column.
    """
    probe = cached_json("hltb_probe", HLTB_API, bucket="hltb", delay=1.0, tries=1,
                        post=_hltb_payload("Hades"),
                        headers={"Referer": "https://howlongtobeat.com/",
                                 "Origin": "https://howlongtobeat.com"})
    if not (probe or {}).get("data"):
        log("[4/5] HowLongToBeat refuses direct requests - leaving playtime blank")
        return games

    log("[4/5] HowLongToBeat reachable, fetching playtimes ...")
    for i, g in enumerate(games, 1):
        name = g.get("matched_name") or g["title"]
        res = cached_json("hltb_" + normalise(name), HLTB_API, bucket="hltb", delay=1.0,
                          post=_hltb_payload(name),
                          headers={"Referer": "https://howlongtobeat.com/",
                                   "Origin": "https://howlongtobeat.com"})
        hit = ((res or {}).get("data") or [None])[0]
        if hit and hit.get("comp_main"):
            g["hltb_main"] = round(hit["comp_main"] / 3600.0, 1)
            g["hltb_name"] = hit.get("game_name")
        if i % 50 == 0:
            log("  [4/5] %d/%d" % (i, len(games)))
    return games


# ---------------------------------------------------------------- phase 5
COLUMNS = ["title", "rating", "reviews", "sort_score", "review_desc", "genres",
           "metacritic", "hltb_main", "release_date", "developer", "publisher",
           "singleplayer", "multiplayer", "coop", "controller",
           "steam_appid", "steam_url", "matched_name", "app_name"]


def emit(games):
    os.makedirs(OUT, exist_ok=True)
    ranked = sorted(games,
                    key=lambda g: (g.get("sort_score") is None, -(g.get("sort_score") or 0)))
    with open(os.path.join(OUT, "games.json"), "w", encoding="utf-8") as fh:
        json.dump(ranked, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, "games.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for g in ranked:
            row = []
            for c in COLUMNS:
                v = g.get(c)
                row.append("; ".join(v) if isinstance(v, list) else ("" if v is None else v))
            w.writerow(row)
    matched = sum(1 for g in ranked if g.get("steam_appid"))
    log(f"[5/5] wrote out/games.json + out/games.csv "
        f"({matched}/{len(ranked)} matched to Steam)")
    return ranked


def main():
    use_utf8_stdout()
    refresh = "--refresh" in sys.argv
    games = epic_library(refresh)
    exact, loose = steam_index()
    log(f"[3/5] enriching {len(games)} games from the Steam store ...")
    games = enrich(games, exact, loose)
    if "--no-hltb" not in sys.argv:
        games = hltb_hours(games)
    emit(games)


if __name__ == "__main__":
    main()
