"""Tests for matching an Epic title to the right Steam game."""
import unittest

import epic_steam
import steamstore
from test_steamstore import HADES, NAMED_CATS, NAMED_TAGS


def hit(appid, name, type_=steamstore.GAME):
    return dict(HADES, appid=appid, name=name, type=type_)


class TestBest(unittest.TestCase):
    def test_an_exact_name_beats_an_earlier_loose_one(self):
        """Search puts sequels and bundles first often enough to matter."""
        items = [hit(1, "Limbo Soundtrack"), hit(2, "LIMBO")]
        self.assertEqual(epic_steam.best("Limbo", items)["appid"], 2)

    def test_an_edition_suffix_still_matches(self):
        """Epic sells 'Sundered Eldritch Edition'; Steam calls it 'Sundered: Eldritch Edition'."""
        items = [hit(535480, "Sundered: Eldritch Edition")]
        self.assertEqual(
            epic_steam.best("Sundered Eldritch Edition", items)["appid"], 535480)

    def test_dlc_is_never_the_answer(self):
        """A search for the game returns its season pass too; that is not the game."""
        items = [hit(2813100, "Dead Island 2 - Haus", steamstore.DLC)]
        self.assertIsNone(epic_steam.best("Dead Island 2", items))

    def test_a_soundtrack_is_never_the_answer(self):
        items = [hit(807320, "Into the Breach Soundtrack", 11)]
        self.assertIsNone(epic_steam.best("Into The Breach", items))

    def test_an_item_steam_would_not_answer_for_is_skipped(self):
        items = [dict(hit(1, "Ghost"), success=15)]
        self.assertIsNone(epic_steam.best("Ghost", items))

    def test_a_package_with_the_exact_name_is_never_the_answer(self):
        """Epic sells "Borderlands 2 Game of the Year"; Steam has a *package*
        by that exact name, type: 0 included, and it carries no appid at all -
        taking it as the best match would crash item_fields() outright."""
        package = {"name": "Borderlands 2 Game of the Year",
                   "type": steamstore.GAME, "item_type": 1, "success": 1}
        self.assertIsNone(
            epic_steam.best("Borderlands 2 Game of the Year", [package]))

    def test_nothing_matching_is_none(self):
        self.assertIsNone(epic_steam.best("Hades", []))


class TestApplySteam(unittest.TestCase):
    def setUp(self):
        self.addCleanup(setattr, steamstore, "_TAGS", None)
        self.addCleanup(setattr, steamstore, "_CATS", None)
        steamstore._TAGS = dict(NAMED_TAGS)
        steamstore._CATS = dict(NAMED_CATS)

    def test_it_records_where_the_match_came_from(self):
        g = epic_steam.apply_steam({"title": "Hades"}, HADES, source="pcgw")
        self.assertEqual(g["steam_source"], "pcgw")
        self.assertEqual(g["steam_appid"], 1145360)

    def test_epics_developer_fills_in_when_steam_names_none(self):
        """A delisted page often drops its credits; Epic still knows who made it."""
        anon = dict(HADES, basic_info={})
        g = epic_steam.apply_steam(
            {"title": "Hades", "epic_developer": "Supergiant"}, anon)
        self.assertEqual(g["developer"], "Supergiant")

    def test_steams_developer_wins_when_there_is_one(self):
        g = epic_steam.apply_steam(
            {"title": "Hades", "epic_developer": "Stale Value"}, HADES)
        self.assertEqual(g["developer"], "Supergiant Games")


if __name__ == "__main__":
    unittest.main()
