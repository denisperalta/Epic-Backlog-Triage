"""Tests for the pure helpers in steamlib: store status classification."""
import json
import os
import shutil
import tempfile
import unittest

import steamlib
from steamlib import cached_json, fetch_json

from steamlib import steam_status


def details(**over):
    """A minimal appdetails 'data' node, shaped like a live paid game."""
    d = {"type": "game", "name": "Some Game", "is_free": False,
         "packages": [12345], "package_groups": [{"name": "default"}],
         "price_overview": {"final": 1999}, "release_date": {"coming_soon": False,
                                                             "date": "1 Jan, 2020"}}
    d.update(over)
    return d


class TestCachedJson(unittest.TestCase):
    """cached_json is now a wrapper; these pin the behaviour it must keep."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        real = steamlib.CACHE
        steamlib.CACHE = self.tmp
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(setattr, steamlib, "CACHE", real)

    def test_a_cached_file_is_returned_without_fetching(self):
        """The whole point of the cache: a rerun must not touch the network."""
        with open(steamlib.cache_path("k"), "w", encoding="utf-8") as fh:
            json.dump({"cached": True}, fh)

        def explode(*a, **k):
            raise AssertionError("fetch_json was called for a cached key")

        self.addCleanup(setattr, steamlib, "fetch_json", steamlib.fetch_json)
        steamlib.fetch_json = explode
        self.assertEqual(cached_json("k", "http://example.invalid/"), {"cached": True})

    def test_a_remembered_failure_is_not_retried(self):
        """A cached null means Steam had nothing; asking again just costs time."""
        with open(steamlib.cache_path("k"), "w", encoding="utf-8") as fh:
            json.dump(None, fh)

        def explode(*a, **k):
            raise AssertionError("fetch_json was called for a remembered failure")

        self.addCleanup(setattr, steamlib, "fetch_json", steamlib.fetch_json)
        steamlib.fetch_json = explode
        self.assertIsNone(cached_json("k", "http://example.invalid/"))

    def test_a_fetched_result_is_written_to_the_cache(self):
        self.addCleanup(setattr, steamlib, "fetch_json", steamlib.fetch_json)
        steamlib.fetch_json = lambda *a, **k: {"fresh": 1}
        self.assertEqual(cached_json("k2", "http://example.invalid/"), {"fresh": 1})
        with open(steamlib.cache_path("k2"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), {"fresh": 1})


class TestSteamStatus(unittest.TestCase):
    def test_paid_game_on_sale_is_listed(self):
        self.assertEqual(steam_status(details()), "listed")

    def test_nothing_left_to_buy_is_delisted(self):
        """Rocket League's page still answers, but nothing on it is purchasable."""
        gone = details(name="Rocket League", packages=[], package_groups=[])
        gone.pop("price_overview")
        self.assertEqual(steam_status(gone), "delisted")

    def test_free_to_play_with_no_packages_is_listed(self):
        """Rogue Company has nothing to buy either, but it is free, not gone."""
        f2p = details(name="Rogue Company", is_free=True, packages=[], package_groups=[])
        f2p.pop("price_overview")
        self.assertEqual(steam_status(f2p), "listed")

    def test_unreleased_game_is_not_delisted(self):
        """Spell Breakers is dated 2027 and sells nothing yet - that is not gone."""
        soon = details(name="Spell Breakers", packages=[], package_groups=[],
                       release_date={"coming_soon": True, "date": "2027"})
        soon.pop("price_overview")
        self.assertEqual(steam_status(soon), "unreleased")

    def test_no_details_at_all_is_unknown(self):
        """appdetails answers success:false for a purged appid and hands back nothing."""
        self.assertEqual(steam_status(None), "unknown")


if __name__ == "__main__":
    unittest.main()
