"""Retry the titles that phase 2 could not match, and settle why the rest failed.

Steam's storefront search only answers to fairly literal names, so Epic entries
carrying branch markers ("(Beta)", "Test branch"), episode numbering or trailing
subtitles come back empty. This walks a ladder of progressively looser queries
and stops at the first one that yields a real base game.

It also answers for games no query can reach. Steam's search only lists what it
currently sells, so a delisted game and one that was never on Steam both come
back as nothing at all. PCGamingWiki tells them apart, and gives the appid that
Steam's own appdetails and appreviews still answer for, so a pulled game keeps
its reviews and its place in the ranking instead of sinking to the bottom
unexplained. Every entry ends up carrying a steam_status: listed, delisted,
not-on-steam, duplicate, unreleased, or unknown.
"""
import json, os, re, urllib.parse
from collections import Counter

import pcgw
from steamlib import cached_json, normalise, use_utf8_stdout
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


STEAM_FIELDS = ("steam_appid", "matched_name", "genres", "rating", "reviews", "positive",
                "negative", "sort_score", "review_desc", "metacritic", "release_date",
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


def resolve_via_wiki(g):
    """Last resort: ask PCGamingWiki for the appid, and record what it settles.

    Steam's search only answers for games it currently sells, so everything that
    reaches here is either delisted, never on Steam, or named too oddly to find.
    The wiki knows which: an article carrying a Steam appid means the game is on
    Steam and the store simply stopped offering it, an article without one means
    it was never there, and no article at all means nobody can say.
    """
    appid, page_title = pcgw.steam_appid(g["title"])
    if not appid:
        g["steam_status"] = "not-on-steam" if page_title else "unknown"
        return False

    data = E.appdetails(appid)
    # A search hit of type "dlc" is a soundtrack dragged in by a loose query and
    # gets rejected, but the wiki points at one deliberate page - and Steam files
    # The Vanishing of Ethan Carter Redux as DLC - so it is taken here.
    if not data or data.get("type") not in ("game", "dlc"):
        g["steam_status"] = "unknown"
        return False

    E.apply_steam(g, appid, data, source="pcgw")
    return True


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
            hits = cached_json("search_" + normalise(v),
                               "https://steamcommunity.com/actions/SearchApps/"
                               + urllib.parse.quote(v[:120]),
                               bucket="community", delay=0.7)
            if not hits:
                continue
            want = normalise(g["title"], True)
            for h in hits[:3]:
                try:
                    appid = int(h["appid"])
                except (KeyError, TypeError, ValueError):
                    continue
                got = normalise(h.get("name") or "", True)
                # Guard against the loose queries dragging in an unrelated game.
                # Compare with spaces removed so "KillingFloor2Beta" still meets
                # "Killing Floor 2".
                a, b = got.replace(" ", ""), want.replace(" ", "")
                if not (a and b and (a == b or a in b or b in a)):
                    continue
                data = E.appdetails(appid)
                if not data or data.get("type") != "game":
                    continue
                E.apply_steam(g, appid, data)
                fixed += 1
                print("  + %-46s via %-28r -> %s" % (g["title"][:46], v[:28], data.get("name")))
                break
            if g.get("steam_appid"):
                break

        if not g.get("steam_appid") and resolve_via_wiki(g):
            fixed += 1
            print("  + %-46s via PCGamingWiki -> %s (%s)"
                  % (g["title"][:46], g["matched_name"], g["steam_status"]))

    dupes = mark_duplicates(games)

    E.emit(games)   # rewrites both games.json and games.csv, re-ranked
    verdicts = Counter(g.get("steam_status") or "unknown" for g in games)
    print("recovered %d, de-duplicated %d, of %d titles" % (fixed, dupes, len(games)))
    print("  " + ", ".join("%s %d" % (k, v) for k, v in sorted(verdicts.items())))


if __name__ == "__main__":
    main()
