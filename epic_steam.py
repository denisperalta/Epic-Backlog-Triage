"""Build a decide-what-to-play list from an Epic library (legendary) + official Steam data.

Phases, each independently cached under cache/ so reruns are cheap:
  1 library   legendary list --json  -> real games only
  2 steam     title -> the Steam store item, in one request per title (steamstore)
  3 hltb      HowLongToBeat playtime (third-party, best effort)
  4 emit      out/games.json, out/games.csv
"""
import csv, json, os, re, subprocess, sys

import steamstore
from steamlib import CACHE, cached_json, normalise, use_utf8_stdout

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
        log("[1/4] querying legendary ...")
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
    log(f"[1/4] {len(raw)} library entries -> {len(uniq)} games")
    return uniq


# ---------------------------------------------------------------- phase 2
def best(title, items):
    """The closest real game in a result list, or None.

    Search is ordered by Steam's idea of relevance, which is not ours: a query
    for a game returns its soundtrack, its season pass and its sequel too. Rank
    on the normalised name instead, and take nothing that is not a game -
    including a package: Epic sells "Borderlands 2 Game of the Year", and
    Steam has a *package* by that exact name, which would otherwise win
    outright on an exact-name match and then crash item_fields() for lack of
    an appid.
    """
    want, want_loose = normalise(title), normalise(title, True)
    ranked = []
    for it in items:
        if not steamstore.is_game(it):
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


# ---------------------------------------------------------------- phase 3
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
        log("[3/4] HowLongToBeat refuses direct requests - leaving playtime blank")
        return games

    log("[3/4] HowLongToBeat reachable, fetching playtimes ...")
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
            log("  [3/4] %d/%d" % (i, len(games)))
    return games


# ---------------------------------------------------------------- phase 4
COLUMNS = ["title", "steam_status", "rating", "reviews", "sort_score", "review_desc",
           "tags", "hltb_main", "release_date", "developer", "publisher",
           "singleplayer", "multiplayer", "coop", "controller", "duplicate_of",
           "steam_appid", "steam_source", "steam_url", "matched_name", "app_name"]


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
    log(f"[4/4] wrote out/games.json + out/games.csv "
        f"({matched}/{len(ranked)} matched to Steam)")
    return ranked


def main():
    use_utf8_stdout()
    refresh = "--refresh" in sys.argv
    games = epic_library(refresh)
    log(f"[2/4] matching {len(games)} games against the Steam store ...")
    games = enrich(games)
    if "--no-hltb" not in sys.argv:
        games = hltb_hours(games)
    emit(games)


if __name__ == "__main__":
    main()
