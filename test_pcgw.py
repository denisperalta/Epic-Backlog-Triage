"""Tests for the PCGamingWiki fallback resolver."""
import json
import os
import shutil
import tempfile
import unittest

import steamlib
from pcgw import page_content, parse_appid, steam_appid, title_matches, wiki_title

ROCKET_LEAGUE = """{{Infobox game
|cover        = Rocket League cover.jpg
|steam appid  = 252950
|steam appid side  = 384260,391680,393580
|gogcom id    =
}}"""

# Verbatim shape of a page for a game that was never on Steam: the main appid is
# blank and the next populated number on the page belongs to something else.
NEVER_ON_STEAM = """{{Infobox game
|cover        = Fortnite cover.jpg
|steam appid  = 
|steam appid side  = 384260,391680
|gogcom id    = 
|hltb         = 3657
}}"""


class TestParseAppid(unittest.TestCase):
    def test_reads_the_main_steam_appid(self):
        self.assertEqual(parse_appid(ROCKET_LEAGUE), 252950)

    def test_never_returns_a_side_appid(self):
        """'steam appid side' lists soundtracks and betas - not the game."""
        self.assertIsNone(parse_appid(NEVER_ON_STEAM))


class TestPageContent(unittest.TestCase):
    def test_reads_the_resolved_title_and_wikitext(self):
        """MediaWiki keys pages by id, so the caller cannot look them up by name."""
        resp = {"query": {"pages": {"26300": {
            "pageid": 26300, "title": "Rocket League",
            "revisions": [{"slots": {"main": {"*": ROCKET_LEAGUE}}}]}}}}
        self.assertEqual(page_content(resp), ("Rocket League", ROCKET_LEAGUE))

    def test_missing_page_comes_back_empty(self):
        """A title with no article is reported as page id -1, not as an error."""
        resp = {"query": {"pages": {"-1": {"ns": 0, "title": "Nope", "missing": ""}}}}
        self.assertEqual(page_content(resp), (None, None))

    def test_survives_a_failed_request(self):
        self.assertEqual(page_content(None), (None, None))


class TestTitleMatches(unittest.TestCase):
    def test_ignores_trademark_marks_epic_puts_in_titles(self):
        self.assertTrue(title_matches("Rocket League®", "Rocket League"))

    def test_accepts_the_year_pcgw_disambiguates_with(self):
        self.assertTrue(title_matches("Trackmania", "Trackmania (2020)"))

    def test_rejects_an_unrelated_page(self):
        self.assertFalse(title_matches("Divine Knockout", "Divinity: Original Sin"))


class TestWikiTitle(unittest.TestCase):
    def test_drops_the_trademark_marks_epic_ships_in_titles(self):
        """PCGamingWiki files the game under the plain name; Epic does not."""
        self.assertEqual(wiki_title("Rocket League®"), "Rocket League")
        self.assertEqual(wiki_title("Second Extinction™"), "Second Extinction")

    def test_keeps_punctuation_the_article_is_actually_titled_with(self):
        self.assertEqual(wiki_title("Stranger Things 3: The Game"),
                         "Stranger Things 3: The Game")


class TestSteamAppid(unittest.TestCase):
    """Drives the real lookup, answered from a seeded cache instead of the network."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.real_cache = steamlib.CACHE
        steamlib.CACHE = self.tmp
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, steamlib, "CACHE", self.real_cache)

    def seed(self, key, payload):
        # Through cache_path, so the test answers the key the resolver really asks
        # for rather than one that quietly misses and goes to the network.
        with open(steamlib.cache_path(key), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)

    def response(self, title, wikitext):
        return {"query": {"pages": {"1": {"title": title,
                "revisions": [{"slots": {"main": {"*": wikitext}}}]}}}}

    def test_resolves_a_title_steam_search_hides(self):
        self.seed("pcgw_rocket league", self.response("Rocket League", ROCKET_LEAGUE))
        self.assertEqual(steam_appid("Rocket League®"), (252950, "Rocket League"))

    def test_reports_nothing_when_the_page_has_no_appid(self):
        self.seed("pcgw_fortnite", self.response("Fortnite", NEVER_ON_STEAM))
        self.assertEqual(steam_appid("Fortnite"), (None, "Fortnite"))

    def test_refuses_a_page_about_a_different_game(self):
        """A wiki lookup can land anywhere; the appid is only taken if the name agrees."""
        self.seed("pcgw_divine knockout", self.response("Divinity: Original Sin", ROCKET_LEAGUE))
        self.assertEqual(steam_appid("Divine Knockout"), (None, "Divinity: Original Sin"))


if __name__ == "__main__":
    unittest.main()
