"""Tests for the Steam store API layer: lookups, item mapping, batching."""
import json
import os
import shutil
import tempfile
import unittest

import steamlib
import steamstore


class CacheDir(unittest.TestCase):
    """Every test here answers from a seeded cache instead of the network."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        real = steamlib.CACHE
        steamlib.CACHE = self.tmp
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, steamlib, "CACHE", real)
        self.addCleanup(setattr, steamstore, "_TAGS", None)
        self.addCleanup(setattr, steamstore, "_CATS", None)
        steamstore._TAGS = None
        steamstore._CATS = None

    def seed(self, key, payload):
        with open(steamlib.cache_path(key), "w", encoding="utf-8") as fh:
            json.dump(payload, fh)


def item(**over):
    """A store item shaped like a live paid game, as GetItems returns one."""
    it = {"appid": 1145360, "name": "Hades", "type": steamstore.GAME, "success": 1,
          "visible": True, "release": {"steam_release_date": 1600353507}}
    it.update(over)
    return it


class TestItemStatus(unittest.TestCase):
    def test_a_game_on_sale_is_listed(self):
        self.assertEqual(steamstore.item_status(item()), "listed")

    def test_an_unlisted_game_is_delisted(self):
        """Rocket League still has a page and its reviews; Steam stopped selling it."""
        self.assertEqual(
            steamstore.item_status(item(name="Rocket League", unlisted=True)),
            "delisted")

    def test_coming_soon_is_unreleased_not_delisted(self):
        """Dodo Peak sells nothing yet - that is not the same as being pulled."""
        soon = item(name="Dodo Peak", release={"is_coming_soon": True})
        self.assertEqual(steamstore.item_status(soon), "unreleased")

    def test_unreleased_wins_over_unlisted(self):
        """Both flags at once reads as unreleased, as the packages check did."""
        both = item(release={"is_coming_soon": True}, unlisted=True)
        self.assertEqual(steamstore.item_status(both), "unreleased")

    def test_an_app_steam_will_not_answer_for_is_unknown(self):
        """A fully removed app comes back as success 15 with no payload at all."""
        self.assertEqual(steamstore.item_status({"success": 15}), "unknown")

    def test_nothing_at_all_is_unknown(self):
        self.assertEqual(steamstore.item_status(None), "unknown")


class TestLookups(CacheDir):
    def test_tag_ids_become_names(self):
        self.seed("steam_taglist",
                  {"response": {"tags": [{"tagid": 492, "name": "Indie"},
                                         {"tagid": 3959, "name": "Roguelite"}]}})
        self.assertEqual(steamstore.tag_names()[3959], "Roguelite")

    def test_category_ids_become_names(self):
        self.seed("steam_categories",
                  {"response": {"categories": [{"categoryid": 2,
                                                "display_name": "Single-player"}]}})
        self.assertEqual(steamstore.category_names()[2], "Single-player")

    def test_a_missing_table_is_empty_rather_than_fatal(self):
        """Losing the tag names should cost the Tags column, not the whole run."""
        self.seed("steam_taglist", None)
        self.assertEqual(steamstore.tag_names(), {})
