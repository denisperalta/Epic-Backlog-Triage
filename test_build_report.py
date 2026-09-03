"""Tests for the report's two-language text: the pairs that silently drift apart."""
import contextlib, io, json, os, re, tempfile, unittest

import build_report
from build_report import HOURS_TH, I18N, TEMPLATE

# The Hours column is only rendered when HowLongToBeat data survived, so it lives
# outside the template - but it is page markup like any other.
MARKUP = TEMPLATE + HOURS_TH

# Every way the template asks for a translated string.
MARKUP_KEYS = re.compile(r'data-i18n(?:-html|-ph|-al)?="(\w+)"')
SCRIPT_KEYS = re.compile(r'\bt\("(\w+)"')
FIELDS = re.compile(r"\{(\w+)\}")


class TestCatalogue(unittest.TestCase):
    def test_both_languages_carry_the_same_keys(self):
        self.assertEqual(sorted(I18N["en"]), sorted(I18N["es"]))

    def test_every_key_the_page_asks_for_exists(self):
        """A typo in a data-i18n or t() name would blank that text, not fail loudly."""
        wanted = set(MARKUP_KEYS.findall(MARKUP)) | set(SCRIPT_KEYS.findall(MARKUP))
        self.assertTrue(wanted, "found no translated strings in the template at all")
        for key in sorted(wanted):
            self.assertIn(key, I18N["en"], "%s is asked for but never defined" % key)

    def test_no_string_is_defined_and_never_used(self):
        used = set(MARKUP_KEYS.findall(MARKUP)) | set(SCRIPT_KEYS.findall(MARKUP))
        self.assertEqual(sorted(set(I18N["en"]) - used), [])

    def test_placeholders_survive_translation(self):
        """A {count} dropped in translation prints a sentence with a hole in it."""
        for key, english in I18N["en"].items():
            self.assertEqual(set(FIELDS.findall(english)),
                             set(FIELDS.findall(I18N["es"][key])),
                             "%s: the two languages fill different blanks" % key)

    def test_nothing_is_left_in_english_by_accident(self):
        for key, english in I18N["en"].items():
            spanish = I18N["es"][key]
            self.assertTrue(spanish.strip(), "%s has no Spanish at all" % key)
            if key not in ("lang_en", "lang_es"):
                self.assertNotEqual(spanish, english, "%s was never translated" % key)


class TestDataLabels(unittest.TestCase):
    def test_steam_review_tiers_are_all_covered(self):
        """Valve's nine tiers plus the no-reviews case, as the store API spells them."""
        for tier in ("Overwhelmingly Positive", "Very Positive", "Positive",
                     "Mostly Positive", "Mixed", "Mostly Negative", "Negative",
                     "Very Negative", "Overwhelmingly Negative", "No user reviews"):
            self.assertIn(tier, build_report.REVIEW_ES)

    def test_tags_seen_in_a_real_library_are_covered(self):
        """The overlap between Steam's tags and the genre names this map was built for."""
        for tag in ("Action", "Adventure", "Casual", "Early Access", "Indie",
                    "Massively Multiplayer", "RPG", "Racing", "Simulation",
                    "Sports", "Strategy"):
            self.assertIn(tag, build_report.TAG_ES)


class TestTagFilter(unittest.TestCase):
    """The page filters on a list of tags, not on one."""

    def test_the_dropdown_invites_adding_rather_than_replacing(self):
        self.assertNotIn("All tags", I18N["en"]["opt_tags"])
        self.assertNotIn("Todas las etiquetas", I18N["es"]["opt_tags"])

    def test_the_select_is_not_a_native_multiple(self):
        """A 200-tag <select multiple> in a sticky bar is the thing we avoided."""
        self.assertNotIn("multiple", re.search(r'<select id="tags".*?>', TEMPLATE).group(0))

    def test_every_active_tag_has_to_match(self):
        """AND, not OR: each tag added narrows the list further."""
        self.assertRegex(TEMPLATE, r"ACTIVE\[i\]\) === -1\) return false")


class TestBuild(unittest.TestCase):
    """The report still renders, and renders whole."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(setattr, build_report, "OUT", build_report.OUT)
        build_report.OUT = self.tmp
        with open(os.path.join(self.tmp, "games.json"), "w", encoding="utf-8") as fh:
            json.dump([{"title": "A Game", "steam_status": "listed", "rating": 92.5,
                        "reviews": 1200, "sort_score": 90.8, "review_desc": "Very Positive",
                        "tags": ["Action"], "release_date": "2020-01-01",
                        "developer": "Someone", "singleplayer": True},
                       {"title": "Gone Game", "steam_status": "delisted", "rating": None,
                        "reviews": 0, "tags": []}], fh)

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            build_report.build()
        with open(os.path.join(self.tmp, "report.html"), encoding="utf-8") as fh:
            return fh.read()

    def test_every_placeholder_is_filled(self):
        self.assertEqual(re.findall(r"__[A-Z_]+__", self.build()), [])

    def test_the_page_ships_both_languages_and_the_switcher(self):
        html = self.build()
        self.assertIn('data-lang="es"', html)
        self.assertIn('data-lang="en"', html)
        for key in ("th_game", "btn_reset"):
            self.assertIn(I18N["es"][key], html)

    def test_the_tag_filter_ships_a_chip_row_and_an_add_prompt(self):
        """Tags are picked one at a time and stack up as chips, so the dropdown
        is an "add" control and the active tags live somewhere else."""
        html = self.build()
        self.assertIn('id="chips"', html)
        self.assertIn('<option value="Action">Action</option>', html)
        for lang in ("en", "es"):
            self.assertIn(I18N[lang]["opt_tags"], html)

    def test_the_counts_reach_the_page_as_numbers(self):
        html = self.build()
        nums = json.loads(re.search(r"var N = (\{.*?\});", html, re.S).group(1))
        self.assertEqual(nums["count"], 2)
        self.assertEqual(nums["rated"], 1)
        self.assertEqual(nums["delisted"], 1)


class TestTheme(unittest.TestCase):
    """The page is built on the Nocturne tokens, dark by default."""

    def test_the_nocturne_tokens_are_inlined(self):
        for token in ("--color-bg:#161826", "--color-text:#e9e9ed",
                      "--color-accent:#9184d9", "--color-accent-200:#e7e5fe",
                      "--color-neutral-900:#292b31"):
            self.assertIn(token, TEMPLATE, "%s is missing from the token block" % token)

    def test_the_report_roles_alias_onto_the_tokens(self):
        for alias in ("--bg:var(--color-bg)", "--ink:var(--color-text)",
                      "--line:var(--color-divider)", "--accent:var(--color-accent)"):
            self.assertIn(alias, TEMPLATE, "%s is not aliased onto a token" % alias)

    def test_the_old_hand_rolled_palette_is_gone(self):
        for dead in ("#a75f10", "#f4f4f8", "#191b22", "#e9a54a"):
            self.assertNotIn(dead, TEMPLATE, "%s survived the restyle" % dead)

    def test_dark_is_the_default_and_light_is_the_override(self):
        self.assertIn(':root[data-theme="light"]', TEMPLATE)
        self.assertIn("@media (prefers-color-scheme:light)", TEMPLATE)
        self.assertIn(':root:not([data-theme="dark"])', TEMPLATE)


if __name__ == "__main__":
    unittest.main()
