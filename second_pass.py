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

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def variants(title):
    """Progressively looser query strings for one stubborn title."""
    out = []

    def add(s):
        s = re.sub(r"\s+", " ", (s or "")).strip(" -:,")
        if s and len(s) > 2 and s not in out:
            out.append(s)

    add(re.sub(r"\([^)]*\)", " ", title))                    # drop (Beta), (Test branch)
    add(re.sub(r"\b(beta|test branch|demo|trial|content|edition)\b", " ", title, flags=re.I))
    add(re.split(r"[:–—]", title)[0])              # drop the subtitle
    add(re.sub(r"[^A-Za-z0-9 ]+", " ", title))               # strip punctuation entirely
    add(" ".join(re.findall(r"[A-Z][a-z]+|\d+", title)))     # split KillingFloor2Beta
    add(" ".join(title.split()[:3]))
    add(" ".join(title.split()[:2]))
    return out


STEAM_FIELDS = ("steam_appid", "matched_name", "tags", "rating", "reviews", "positive",
                "negative", "sort_score", "review_desc", "release_date",
                "developer", "publisher", "singleplayer", "multiplayer", "coop",
                "controller", "steam_url", "steam_source")


def mark_duplicates(games):
    """Collapse Epic entries that resolved to the same Steam page. Returns the count.

    A relaxed query can land two Epic entries on one Steam page - "Death Stranding"
    and "Death Stranding Content", a game and its test branch. Keep whichever title
    is closest to the Steam name and strip the Steam data off the others, but say on
    each which row now holds it: a blank row is only a mystery if it does not point
    anywhere.
    """
    best = {}
    for g in games:
        aid = g.get("steam_appid")
        if not aid:
            continue
        score = (len(normalise(g["title"], True).replace(" ", ""))
                 - len(normalise(g.get("matched_name") or "", True)
                       .replace(" ", "")))
        if aid not in best or abs(score) < best[aid][0]:
            best[aid] = (abs(score), g)

    dupes = 0
    for g in games:
        aid = g.get("steam_appid")
        if not aid or best[aid][1] is g:
            continue
        for k in STEAM_FIELDS:
            g.pop(k, None)
        g["steam_status"] = "duplicate"
        g["duplicate_of"] = best[aid][1]["title"]
        dupes += 1
    return dupes


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


def main():
    use_utf8_stdout()
    path = os.path.join(OUT, "games.json")
    if not os.path.exists(path):
        raise SystemExit("out/games.json is missing - run epic_steam.py first.")
    with open(path, encoding="utf-8") as fh:
        games = json.load(fh)
    stuck = [g for g in games if not g.get("steam_appid")]
    print("retrying %d unmatched titles" % len(stuck))

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

    dupes = mark_duplicates(games)

    E.emit(games)   # rewrites both games.json and games.csv, re-ranked
    verdicts = Counter(g.get("steam_status") or "unknown" for g in games)
    print("recovered %d, de-duplicated %d, of %d titles" % (fixed, dupes, len(games)))
    print("  " + ", ".join("%s %d" % (k, v) for k, v in sorted(verdicts.items())))


if __name__ == "__main__":
    main()
