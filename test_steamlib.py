"""Tests for the disk cache behaviour of cached_json."""
import json
import os
import shutil
import tempfile
import unittest

import steamlib
from steamlib import cached_json, fetch_json


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


if __name__ == "__main__":
    unittest.main()
