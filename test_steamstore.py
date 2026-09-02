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
    it = {"appid": 1145360, "name": "Hades", "type": steamstore.GAME,
          "item_type": steamstore.APP, "success": 1,
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


class TestIsGame(unittest.TestCase):
    """type alone cannot tell a game from a package or a bundle - item_type can."""

    def test_rejects_a_package_even_though_type_says_game(self):
        """The real crash: Steam sells "Borderlands 2 Game of the Year" as a
        package with type: 0, and a package carries no appid at all."""
        package = {"name": "Borderlands 2 Game of the Year",
                   "type": steamstore.GAME, "item_type": 1, "success": 1}
        self.assertFalse(steamstore.is_game(package))

    def test_rejects_a_bundle(self):
        self.assertFalse(steamstore.is_game(item(item_type=2)))

    def test_rejects_dlc(self):
        self.assertFalse(steamstore.is_game(item(type=steamstore.DLC)))

    def test_rejects_an_item_steam_would_not_answer_for(self):
        self.assertFalse(steamstore.is_game(item(success=15)))

    def test_accepts_a_normal_game(self):
        self.assertTrue(steamstore.is_game(item()))


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


HADES = {
    "appid": 1145360, "name": "Hades", "type": 0, "item_type": 0,
    "success": 1, "visible": True,
    "categories": {"supported_player_categoryids": [2],
                   "feature_categoryids": [22, 29, 23],
                   "controller_categoryids": [28]},
    "reviews": {"summary_filtered": {"review_count": 285375, "percent_positive": 98,
                                     "review_score_label": "Overwhelmingly Positive"}},
    "basic_info": {"developers": [{"name": "Supergiant Games"}],
                   "publishers": [{"name": "Supergiant Games"}]},
    "release": {"steam_release_date": 1600353507,
                "original_steam_release_date": 1575997560},
    "tags": [{"tagid": 42804, "weight": 1052}, {"tagid": 3959, "weight": 766},
             {"tagid": 1646, "weight": 748}, {"tagid": 492, "weight": 737}],
}

NAMED_TAGS = {42804: "Action Roguelike", 3959: "Roguelite", 1646: "Hack and Slash",
              492: "Indie"}
NAMED_CATS = {2: "Single-player", 22: "Steam Achievements", 23: "Steam Cloud",
              29: "Steam Trading Cards", 28: "Full controller support",
              1: "Multi-player", 9: "Co-op", 38: "Online Co-op", 49: "PvP"}


class TestItemFields(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, steamstore, "_TAGS", None)
        self.addCleanup(setattr, steamstore, "_CATS", None)
        steamstore._TAGS = dict(NAMED_TAGS)
        steamstore._CATS = dict(NAMED_CATS)

    def test_the_headline_numbers(self):
        f = steamstore.item_fields(HADES)
        self.assertEqual(f["steam_appid"], 1145360)
        self.assertEqual(f["matched_name"], "Hades")
        self.assertEqual(f["steam_status"], "listed")
        self.assertEqual(f["reviews"], 285375)
        self.assertEqual(f["rating"], 98.0)
        self.assertEqual(f["review_desc"], "Overwhelmingly Positive")
        self.assertEqual(f["steam_url"],
                         "https://store.steampowered.com/app/1145360/")

    def test_positive_and_negative_are_derived_from_the_percentage(self):
        """Steam only gives a whole percent, so the split is reconstructed."""
        f = steamstore.item_fields(HADES)
        self.assertEqual(f["positive"], 279668)
        self.assertEqual(f["negative"], 285375 - 279668)
        self.assertLess(f["sort_score"], f["rating"])

    def test_only_the_three_heaviest_tags_are_kept(self):
        self.assertEqual(steamstore.item_fields(HADES)["tags"],
                         ["Action Roguelike", "Roguelite", "Hack and Slash"])

    def test_a_tag_with_no_known_name_is_skipped_not_numbered(self):
        thin = dict(HADES, tags=[{"tagid": 999999, "weight": 9}] + HADES["tags"][:2])
        self.assertEqual(steamstore.item_fields(thin)["tags"],
                         ["Action Roguelike", "Roguelite"])

    def test_the_release_date_is_the_one_steam_shows(self):
        """Hades left early access in September 2020; the report shows that year."""
        self.assertEqual(steamstore.item_fields(HADES)["release_date"], "2020-09-17")

    def test_an_unreleased_game_has_no_date_and_says_so(self):
        soon = dict(HADES, release={"is_coming_soon": True})
        f = steamstore.item_fields(soon)
        self.assertEqual(f["release_date"], "")
        self.assertTrue(f["coming_soon"])

    def test_player_modes_come_from_all_three_category_lists(self):
        f = steamstore.item_fields(HADES)
        self.assertTrue(f["singleplayer"])
        self.assertTrue(f["controller"])
        self.assertFalse(f["multiplayer"])
        self.assertFalse(f["coop"])

    def test_online_co_op_counts_as_both_multiplayer_and_co_op(self):
        """Dota 2's categories are Multi-player plus Online Co-op, and it is both."""
        social = dict(HADES, categories={"supported_player_categoryids": [1, 38, 49],
                                         "feature_categoryids": [],
                                         "controller_categoryids": []})
        f = steamstore.item_fields(social)
        self.assertTrue(f["multiplayer"])
        self.assertTrue(f["coop"])
        self.assertFalse(f["singleplayer"])

    def test_developers_and_publishers_are_joined_names(self):
        f = steamstore.item_fields(HADES)
        self.assertEqual(f["developer"], "Supergiant Games")
        self.assertEqual(f["publisher"], "Supergiant Games")

    def test_a_game_with_no_reviews_scores_nothing_rather_than_zero(self):
        """An unrated game must sort to the bottom, not to a hard zero."""
        fresh = dict(HADES)
        fresh.pop("reviews")
        f = steamstore.item_fields(fresh)
        self.assertEqual(f["reviews"], 0)
        self.assertIsNone(f["rating"])
        self.assertIsNone(f["sort_score"])

    def test_a_game_with_no_reviews_still_says_so_in_words(self):
        """The report translates that phrase into Spanish; a blank has nothing to translate."""
        fresh = dict(HADES)
        fresh.pop("reviews")
        self.assertEqual(steamstore.item_fields(fresh)["review_desc"],
                         "No user reviews")


class TestSearchItems(CacheDir):
    def test_results_come_back_in_order(self):
        self.seed("find_" + steamlib.normalise("Hades"),
                  {"response": {"store_items": [HADES, dict(HADES, appid=1, name="B")]}})
        got = steamstore.search_items("Hades")
        self.assertEqual([i["name"] for i in got], ["Hades", "B"])

    def test_an_empty_term_never_reaches_the_network(self):
        self.assertEqual(steamstore.search_items(""), [])

    def test_a_remembered_miss_is_an_empty_list(self):
        self.seed("find_" + steamlib.normalise("Nothing At All"), None)
        self.assertEqual(steamstore.search_items("Nothing At All"), [])


class TestGetItems(CacheDir):
    def test_a_cached_appid_is_not_fetched_again(self):
        self.seed("item_1145360", HADES)

        def explode(*a, **k):
            raise AssertionError("fetched an appid that was already cached")

        self.addCleanup(setattr, steamstore, "fetch_json", steamstore.fetch_json)
        steamstore.fetch_json = explode
        self.assertEqual(steamstore.get_items([1145360])[1145360]["name"], "Hades")

    def test_ids_are_requested_in_chunks(self):
        """Two hundred is the batch; 243 is where the URL stops being accepted."""
        calls = []

        def fake(url, **kw):
            calls.append(url)
            return {"response": {"store_items": []}}

        self.addCleanup(setattr, steamstore, "fetch_json", steamstore.fetch_json)
        steamstore.fetch_json = fake
        steamstore.get_items(range(10, 460))          # 450 ids
        self.assertEqual(len(calls), 3)

    def test_an_appid_steam_will_not_answer_for_is_remembered_as_a_miss(self):
        """A second run must not re-ask for an app that has been removed."""
        self.addCleanup(setattr, steamstore, "fetch_json", steamstore.fetch_json)
        steamstore.fetch_json = lambda url, **kw: {
            "response": {"store_items": [{"appid": 0, "success": 15}]}}
        self.assertEqual(steamstore.get_items([267550]), {})
        self.assertTrue(os.path.exists(steamlib.cache_path("item_267550")))

        def explode(*a, **k):
            raise AssertionError("re-asked for a remembered miss")

        steamstore.fetch_json = explode
        self.assertEqual(steamstore.get_items([267550]), {})

    def test_a_hard_failure_does_not_poison_the_cache(self):
        """None means the request never came back, not that Steam answered with
        nothing - remembering it as a miss would leave every appid in the chunk
        stuck at steam_status: unknown forever, including the delisted games the
        wiki fallback exists to rescue.
        """
        self.addCleanup(setattr, steamstore, "fetch_json", steamstore.fetch_json)
        steamstore.fetch_json = lambda url, **kw: None
        self.assertEqual(steamstore.get_items([1145360]), {})
        self.assertFalse(os.path.exists(steamlib.cache_path("item_1145360")))

        steamstore.fetch_json = lambda url, **kw: {
            "response": {"store_items": [HADES]}}
        got = steamstore.get_items([1145360])
        self.assertEqual(got[1145360]["name"], "Hades")
        self.assertTrue(os.path.exists(steamlib.cache_path("item_1145360")))

    def test_duplicate_ids_are_asked_for_once(self):
        calls = []

        def fake(url, **kw):
            calls.append(url)
            return {"response": {"store_items": [HADES]}}

        self.addCleanup(setattr, steamstore, "fetch_json", steamstore.fetch_json)
        steamstore.fetch_json = fake
        got = steamstore.get_items([1145360, 1145360, 1145360])
        self.assertEqual(len(calls), 1)
        self.assertEqual(list(got), [1145360])
