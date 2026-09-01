"""Retry the titles that phase 2 could not match, using relaxed query forms.

Steam's storefront search only answers to fairly literal names, so Epic entries
carrying branch markers ("(Beta)", "Test branch"), episode numbering or trailing
subtitles come back empty. This walks a ladder of progressively looser queries
and stops at the first one that yields a real base game.
"""
import json, os, re, urllib.parse

from steamlib import cached_json, normalise, use_utf8_stdout, wilson_lower
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
                summary = E.appreviews(appid) or {}
                pos = summary.get("total_positive") or 0
                tot = summary.get("total_reviews") or 0
                cats = {c.get("description") for c in data.get("categories") or []}
                g.update(
                    steam_appid=appid, matched_name=data.get("name"),
                    genres=[x.get("description") for x in data.get("genres") or []
                            if x.get("description")],
                    rating=round(100.0 * pos / tot, 2) if tot else None,
                    reviews=tot, positive=pos,
                    negative=summary.get("total_negative") or 0,
                    sort_score=round(wilson_lower(pos, tot), 2) if tot else None,
                    review_desc=summary.get("review_score_desc") or "",
                    metacritic=(data.get("metacritic") or {}).get("score"),
                    release_date=(data.get("release_date") or {}).get("date") or "",
                    developer=", ".join(data.get("developers") or []) or g.get("epic_developer", ""),
                    publisher=", ".join(data.get("publishers") or []),
                    singleplayer="Single-player" in cats,
                    multiplayer=any("Multi-player" in c or "PvP" in c for c in cats),
                    coop=any("Co-op" in c for c in cats),
                    controller="Full controller support" in cats,
                    steam_url="https://store.steampowered.com/app/%d/" % appid,
                )
                fixed += 1
                print("  + %-46s via %-28r -> %s" % (g["title"][:46], v[:28], data.get("name")))
                break
            if g.get("steam_appid"):
                break

    # A relaxed query can land two Epic entries on one Steam page ("Death Stranding"
    # and "Death Stranding Content"). Keep whichever title is closest to the Steam
    # name and strip the Steam data off the other so it is not counted twice.
    best = {}
    for g in games:
        aid = g.get("steam_appid")
        if not aid:
            continue
        score = len(normalise(g["title"], True).replace(" ", "")) - \
            len(normalise(g.get("matched_name") or "", True).replace(" ", ""))
        if aid not in best or abs(score) < best[aid][0]:
            best[aid] = (abs(score), g)
    dupes = 0
    for g in games:
        aid = g.get("steam_appid")
        if aid and best[aid][1] is not g:
            for k in ("steam_appid", "matched_name", "genres", "rating", "reviews", "positive",
                      "negative", "sort_score", "review_desc", "metacritic", "release_date",
                      "developer", "publisher", "singleplayer", "multiplayer", "coop",
                      "controller", "steam_url"):
                g.pop(k, None)
            dupes += 1

    E.emit(games)   # rewrites both games.json and games.csv, re-ranked
    still = sum(1 for g in games if not g.get("steam_appid"))
    print("recovered %d, de-duplicated %d; %d still unmatched of %d"
          % (fixed, dupes, still, len(games)))


if __name__ == "__main__":
    main()
