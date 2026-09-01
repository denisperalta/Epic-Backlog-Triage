"""PCGamingWiki fallback: resolve a title to a Steam appid Steam's own search hides.

Steam's search endpoints answer only for games that are currently on sale, so a
delisted title is indistinguishable from one that was never on Steam at all -
both are simply absent. PCGamingWiki keeps an article either way, with the Steam
appid in its infobox, which is enough to tell the two apart and to reach the
review data Steam still serves for a pulled game.
"""
import re
import urllib.parse

from steamlib import cached_json, normalise

API = "https://www.pcgamingwiki.com/w/api.php"

_APPID = re.compile(r"\|\s*steam\s+appid\s*=\s*(\d+)", re.I)


def parse_appid(wikitext):
    """The main Steam appid out of a PCGamingWiki infobox, or None."""
    m = _APPID.search(wikitext or "")
    return int(m.group(1)) if m else None


def wiki_title(title):
    """An Epic title as PCGamingWiki spells it.

    Only the trademark marks come off: MediaWiki looks pages up by their exact
    name, so the punctuation and capitalisation have to survive - normalise()
    would flatten "Stranger Things 3: The Game" into something with no article.
    """
    cleaned = re.sub(r"[\u2122\u00ae\u00a9\u2117]", "", title or "")
    return re.sub(r"\s+", " ", cleaned).strip()


def page_content(response):
    """(resolved title, wikitext) out of a MediaWiki query response.

    Pages come back keyed by page id, and a title with no article is reported
    as the sentinel id "-1" rather than as an error, so both have to be dug out
    rather than read off a known key.
    """
    pages = ((response or {}).get("query") or {}).get("pages") or {}
    for page_id, page in pages.items():
        if str(page_id) == "-1":
            continue
        try:
            return page.get("title"), page["revisions"][0]["slots"]["main"]["*"]
        except (KeyError, IndexError, TypeError):
            continue
    return None, None


def title_matches(epic_title, page_title):
    """Is a PCGamingWiki page really the Epic title, or a different game?

    Compared with spaces removed so PCGamingWiki's disambiguating year -
    "Trackmania (2020)" - and Epic's trademark marks both stop mattering.
    """
    a = normalise(epic_title, True).replace(" ", "")
    b = normalise(page_title, True).replace(" ", "")
    return bool(a and b and (a == b or a in b or b in a))


def steam_appid(title):
    """(Steam appid, PCGamingWiki page title) for an Epic title, either may be None.

    An appid of None with a page title means the wiki has an article and it
    carries no Steam appid - the game was never on Steam, as opposed to pulled
    from it. Both None means no article was found to judge by.
    """
    query = urllib.parse.urlencode({
        "action": "query", "format": "json", "prop": "revisions",
        "rvprop": "content", "rvslots": "main", "redirects": "1",
        "titles": wiki_title(title)[:250],
    })
    response = cached_json("pcgw_" + normalise(title), API + "?" + query,
                           bucket="pcgw", delay=1.0, tries=2)
    page_title, wikitext = page_content(response)
    if not page_title or not title_matches(title, page_title):
        return None, page_title
    return parse_appid(wikitext), page_title
