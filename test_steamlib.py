"""Tests for the pure helpers in steamlib: store status classification."""
import unittest

from steamlib import steam_status


def details(**over):
    """A minimal appdetails 'data' node, shaped like a live paid game."""
    d = {"type": "game", "name": "Some Game", "is_free": False,
         "packages": [12345], "package_groups": [{"name": "default"}],
         "price_overview": {"final": 1999}, "release_date": {"coming_soon": False,
                                                             "date": "1 Jan, 2020"}}
    d.update(over)
    return d


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
