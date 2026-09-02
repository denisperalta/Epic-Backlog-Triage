"""Tests for the second-pass retry: wiki fallback, and entries that collide."""
import json
import shutil
import tempfile
import unittest

import steamlib
import steamstore
from second_pass import mark_duplicates, wiki_pass


def entry(title, appid=None, matched_name=None):
    g = {"title": title}
    if appid:
        g.update(steam_appid=appid, matched_name=matched_name, rating=90.0,
                 reviews=1000, sort_score=88.0,
                 steam_url="https://store.steampowered.com/app/%d/" % appid)
    return g


class TestMarkDuplicates(unittest.TestCase):
    def test_branch_entry_defers_to_the_game_it_is_a_branch_of(self):
        """Epic lists test branches as separate titles; both resolve to one appid."""
        base = entry("Satisfactory", 526870, "Satisfactory")
        beta = entry("Satisfactory Experimental", 526870, "Satisfactory")
        mark_duplicates([base, beta])

        self.assertEqual(base["steam_appid"], 526870)
        self.assertEqual(beta.get("steam_appid"), None)
        self.assertEqual(beta["steam_status"], "duplicate")
        self.assertEqual(beta["duplicate_of"], "Satisfactory")

    def test_says_which_entry_it_deferred_to(self):
        """A blank row is only useful if it names the row holding the data."""
        base = entry("Mortal Shell", 1110910, "Mortal Shell")
        b1 = entry("Mortal Shell - Beta", 1110910, "Mortal Shell")
        b2 = entry("Mortal Shell Tech Beta", 1110910, "Mortal Shell")
        mark_duplicates([base, b1, b2])

        self.assertEqual([g["duplicate_of"] for g in (b1, b2)],
                         ["Mortal Shell", "Mortal Shell"])

    def test_leaves_a_lone_match_alone(self):
        only = entry("Hades", 1145360, "Hades")
        mark_duplicates([only])
        self.assertEqual(only["steam_appid"], 1145360)
        self.assertNotIn("duplicate_of", only)


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

HAS_APPID = """{{Infobox game
|steam appid  = 389140
|steam appid side  =
}}"""

NO_APPID = """{{Infobox game
|steam appid  =
|steam appid side  =
}}"""


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


if __name__ == "__main__":
    unittest.main()
