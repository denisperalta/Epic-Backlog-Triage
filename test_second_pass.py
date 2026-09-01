"""Tests for the second-pass retry: wiki fallback, and entries that collide."""
import json
import shutil
import tempfile
import unittest

import steamlib
from second_pass import mark_duplicates, resolve_via_wiki


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


DELISTED_DETAILS = {"type": "game", "name": "Horizon Chase Turbo", "is_free": False,
                    "packages": [], "package_groups": [],
                    "release_date": {"coming_soon": False, "date": "30 May, 2018"},
                    "developers": ["AQUIRIS"], "publishers": ["AQUIRIS"],
                    "genres": [{"description": "Racing"}], "categories": []}

HAS_APPID = """{{Infobox game
|steam appid  = 389140
|steam appid side  =
}}"""

NO_APPID = """{{Infobox game
|steam appid  =
|steam appid side  =
}}"""


class TestResolveViaWiki(unittest.TestCase):
    """Drives the real fallback, answered from a seeded cache instead of the network."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        real = steamlib.CACHE
        steamlib.CACHE = self.tmp
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, steamlib, "CACHE", real)

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
        self.seed("details_389140", {"389140": {"success": True, "data": DELISTED_DETAILS}})
        self.seed("reviews_389140", {"success": 1, "query_summary": {
            "total_reviews": 5939, "total_positive": 5493, "total_negative": 446,
            "review_score_desc": "Very Positive"}})

        g = {"title": "Horizon Chase Turbo", "epic_developer": "AQUIRIS"}
        self.assertTrue(resolve_via_wiki(g))
        self.assertEqual(g["steam_appid"], 389140)
        self.assertEqual(g["steam_status"], "delisted")
        self.assertEqual(g["steam_source"], "pcgw")
        self.assertEqual(g["reviews"], 5939)
        self.assertAlmostEqual(g["rating"], 92.49, places=2)
        self.assertGreater(g["sort_score"], 90.0)

    def test_an_article_with_no_appid_means_never_on_steam(self):
        """Fortnite has a page; it has no Steam appid, and never did."""
        self.seed_wiki("Fortnite", "Fortnite", NO_APPID)

        g = {"title": "Fortnite", "epic_developer": "Epic Games"}
        self.assertFalse(resolve_via_wiki(g))
        self.assertEqual(g["steam_status"], "not-on-steam")
        self.assertIsNone(g.get("steam_appid"))

    def test_no_article_leaves_the_verdict_open(self):
        """Not knowing is a different answer from knowing it was never there."""
        self.seed("pcgw_" + steamlib.normalise("Death Stranding Content"),
                  {"query": {"pages": {"-1": {"title": "Death Stranding Content",
                                              "missing": ""}}}})

        g = {"title": "Death Stranding Content", "epic_developer": ""}
        self.assertFalse(resolve_via_wiki(g))
        self.assertEqual(g["steam_status"], "unknown")


if __name__ == "__main__":
    unittest.main()
