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
