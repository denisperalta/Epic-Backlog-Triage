# Nocturne Report Restyle — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the generated report to the approved "Backlog Triage" design on the Nocturne design system, at feature parity with today.

**Architecture:** Nocturne's `:root` token block is inlined verbatim into `TEMPLATE`'s `<style>`, and the report's existing role variables (`--bg`, `--ink`, `--line`, …) are redefined as aliases onto those tokens. Every existing selector and every line of render JS keeps reading the same role names and needs no edit. Layout then moves from a centred column with a horizontal filter bar to a 268px sidebar rail plus a main column.

**Tech Stack:** Python 3 (stdlib only for rendering), vanilla ES5 in the page, `unittest`. No build step, no framework, no new dependency.

**Spec:** `docs/superpowers/specs/2026-09-02-nocturne-report-restyle-design.md`

## Global Constraints

- The report is **one self-contained HTML file**. No new external requests beyond the existing Google Fonts link.
- **Python stdlib only.** No new entries in `requirements.txt`.
- **Page JS stays ES5** — `var`, `function`, no arrow functions, no `const`/`let`, no template literals. It matches the existing style and runs from `file://`.
- Run tests with `python -m unittest discover -b` from the repo root.
- **Every new i18n key needs a real Spanish string**, not the English one. `test_nothing_is_left_in_english_by_accident` enforces this.
- **Every i18n key must be used**, and every used key must be defined. Removing a control means removing its keys in the same task.
- Keep the line `if (mine.indexOf(ACTIVE[i]) === -1) return false;` **character-for-character** — `test_every_active_tag_has_to_match` matches it by regex.
- Metacritic stays absent. Tags is the label, never "Genre". The Hours column keeps its `N.hasHours` condition.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `build_report.py` | EN/ES catalogues, `TEMPLATE`, `build()` | modified throughout |
| `test_build_report.py` | i18n drift + build integrity | modified; new cases added |

**Considered and deferred:** splitting `TEMPLATE` into separate `.css` / `.html` / `.js` files read at build time. It would make this diff far easier to review, but it changes `build()` and the `TEMPLATE`-reading tests, and it is not in the approved spec. Keep the single-string structure; work in the task order below so each step stays reviewable on its own.

---

### Task 1: Nocturne token layer and theme inversion

Replaces the three hand-rolled palette blocks with Nocturne's tokens plus role aliases, and flips the default from light to dark. Colour only — fonts and band colours come later.

**Files:**
- Modify: `build_report.py:265-296` (the `:root`, `@media`, and `:root[data-theme="dark"]` blocks)
- Test: `test_build_report.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the role variables `--bg`, `--surface`, `--surface-2`, `--ink`, `--muted`, `--faint`, `--line`, `--line-soft`, `--accent`, `--accent-soft`, `--accent-ink`, `--track`, `--chip-ink`, `--shadow`, defined in all three theme blocks. Later tasks consume these names and must not rename them.

- [ ] **Step 1: Write the failing test**

Add to `test_build_report.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest test_build_report.TestTheme -v`
Expected: FAIL — `--color-bg:#161826 is missing from the token block`.

- [ ] **Step 3: Replace the palette blocks**

In `build_report.py`, replace everything from `:root{` through the closing brace of `:root[data-theme="dark"]{...}` (lines 265-296) with:

```css
:root{
  /* Nocturne tokens, inlined from the design system's styles.css. */
  --color-bg:#161826; --color-surface:#232532; --color-text:#e9e9ed;
  --color-accent:#9184d9; --color-accent-2:#a7a1db;
  --color-divider:color-mix(in srgb,#e9e9ed 16%,transparent);
  --color-neutral-100:#f3f5fe; --color-neutral-200:#e4e7f5; --color-neutral-300:#cfd3e5;
  --color-neutral-400:#b2b6ca; --color-neutral-500:#9397ab; --color-neutral-600:#75798c;
  --color-neutral-700:#595d6c; --color-neutral-800:#3f424d; --color-neutral-900:#292b31;
  --color-accent-100:#f5f4ff; --color-accent-200:#e7e5fe; --color-accent-300:#d2cefd;
  --color-accent-400:#b5abfc; --color-accent-500:#968ae0; --color-accent-600:#796cbf;
  --color-accent-700:#5d5294; --color-accent-800:#423a6a; --color-accent-900:#2b2741;
  --font-heading:"Inter",system-ui,sans-serif;
  --font-body:"Inter",system-ui,sans-serif;
  --mono:ui-monospace,SFMono-Regular,Menlo,monospace;
  --space-2:5.6px; --space-3:8.4px; --space-4:11.2px; --space-6:16.8px; --space-8:22.4px;
  --radius-sm:4px; --radius-md:8px; --radius-lg:14px;
  --shadow-md:0 0 0 1px #595d6c,0 6px 18px rgba(0,0,0,.55);

  /* The report's own roles, aliased onto the tokens. Dark is the default. */
  --bg:var(--color-bg); --surface:var(--color-surface);
  --surface-2:var(--color-neutral-900);
  --ink:var(--color-text); --muted:var(--color-neutral-500);
  --faint:var(--color-neutral-600);
  --line:var(--color-divider);
  --line-soft:color-mix(in srgb,var(--color-text) 7%,transparent);
  --accent:var(--color-accent);
  --accent-soft:color-mix(in srgb,var(--color-accent) 14%,transparent);
  --accent-ink:var(--color-accent-400);
  --track:var(--color-neutral-800); --chip-ink:var(--color-accent-100);
  --shadow:var(--shadow-md);
}
/* The light theme inverts onto the accent ramps - no new colours. */
:root[data-theme="light"]{
  --bg:var(--color-accent-200); --surface:var(--color-accent-100);
  --surface-2:color-mix(in srgb,var(--color-accent-200) 78%,var(--color-accent-300));
  --ink:var(--color-neutral-900); --muted:var(--color-neutral-800);
  --faint:var(--color-neutral-600);
  --line:color-mix(in srgb,var(--color-neutral-900) 15%,transparent);
  --line-soft:color-mix(in srgb,var(--color-neutral-900) 7%,transparent);
  --accent:var(--color-accent-600);
  --accent-soft:color-mix(in srgb,var(--color-accent-600) 12%,transparent);
  --accent-ink:var(--color-accent-700);
  --track:color-mix(in srgb,var(--color-neutral-900) 10%,transparent);
  --chip-ink:var(--color-accent-100);
  --shadow:0 1px 2px color-mix(in srgb,var(--color-neutral-900) 6%,transparent),
           0 12px 30px -18px color-mix(in srgb,var(--color-neutral-900) 45%,transparent);
}
@media (prefers-color-scheme:light){
  :root:not([data-theme="dark"]){
    --bg:var(--color-accent-200); --surface:var(--color-accent-100);
    --surface-2:color-mix(in srgb,var(--color-accent-200) 78%,var(--color-accent-300));
    --ink:var(--color-neutral-900); --muted:var(--color-neutral-800);
    --faint:var(--color-neutral-600);
    --line:color-mix(in srgb,var(--color-neutral-900) 15%,transparent);
    --line-soft:color-mix(in srgb,var(--color-neutral-900) 7%,transparent);
    --accent:var(--color-accent-600);
    --accent-soft:color-mix(in srgb,var(--color-accent-600) 12%,transparent);
    --accent-ink:var(--color-accent-700);
    --track:color-mix(in srgb,var(--color-neutral-900) 10%,transparent);
    --chip-ink:var(--color-accent-100);
    --shadow:0 1px 2px color-mix(in srgb,var(--color-neutral-900) 6%,transparent),
             0 12px 30px -18px color-mix(in srgb,var(--color-neutral-900) 45%,transparent);
  }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -b`
Expected: PASS. The `--b1`..`--b5` band variables are now undefined — that is expected and fixed in Task 3. Nothing asserts on them yet.

- [ ] **Step 5: Commit**

```bash
git add build_report.py test_build_report.py
git commit -m "Build the report on Nocturne's tokens, dark by default"
```

---

### Task 2: Typography — three families become one

**Files:**
- Modify: `build_report.py:262-264` (the font link), and every `font-family` / `font` shorthand naming a retired family
- Test: `test_build_report.py`

**Interfaces:**
- Consumes: `--font-body`, `--font-heading`, `--mono` from Task 1.
- Produces: nothing new.

- [ ] **Step 1: Write the failing test**

Add to `TestTheme`:

```python
    def test_only_inter_is_fetched(self):
        self.assertIn("family=Inter", TEMPLATE)
        for dead in ("Bricolage", "IBM+Plex", "IBM Plex"):
            self.assertNotIn(dead, TEMPLATE, "%s is still referenced" % dead)

    def test_numerals_use_a_system_mono_stack(self):
        self.assertIn("--mono:ui-monospace", TEMPLATE)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest test_build_report.TestTheme -v`
Expected: FAIL — `Bricolage is still referenced`.

- [ ] **Step 3: Swap the font link and the declarations**

Replace the stylesheet link with:

```html
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
```

Then replace every retired family reference:

| Selector | Was | Becomes |
|---|---|---|
| `body` | `15px/1.55 "IBM Plex Sans",…` | `14px/1.55 var(--font-body)` |
| `h1` | `"Bricolage Grotesque",…` weight 800 | `var(--font-heading)`, weight 500 |
| `.sub code` | `"IBM Plex Mono",…` | `var(--mono)` |
| `.tile .v` | `"Bricolage Grotesque",…` weight 700 | `var(--font-heading)`, weight 500 |
| `.foot code`, `.rng b`, `.num`, `.rate .pct` | `"IBM Plex Mono",…` | `var(--mono)` |
| `input[type=search],select`, `.chip button`, `button.clear`, `button.reset` | `"IBM Plex Sans",sans-serif` | `var(--font-body)` |
| `.lang button` | `"IBM Plex Mono",…` | `var(--mono)` |

Nocturne's rule is that hierarchy comes from size and space, not weight: **do not bolden headings past 500**. Change `h1`'s `font-weight:800` to `500` and `.tile .v`'s `700` to `500`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -b`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add build_report.py test_build_report.py
git commit -m "Move the report to Inter and a system mono stack"
```

---

### Task 3: Retuned band colours

The five green-to-red band hues survive Nocturne's mono palette, re-derived to sit on the new grounds. Values below were generated in OKLCH and contrast-checked; use them exactly.

**Files:**
- Modify: `build_report.py` — all three theme blocks from Task 1
- Test: `test_build_report.py`

**Interfaces:**
- Consumes: the theme blocks from Task 1.
- Produces: `--b1`..`--b5` in every theme block. The `.t1`-`.t5` and `.f1`-`.f5` classes and the render JS's `band` field already consume these and need no change.

Derivation, for the record: dark at OKLCH L 0.72 / C 0.125, light at L 0.52 / C 0.105 (0.125 pushes `b3` outside sRGB on the light ground). Hues 148, 130, 100, 55, 25.

| | dark, on `#161826` | light, on `#e7e5fe` |
|---|---|---|
| `--b1` | `#6aba77` (7.46:1) | `#397945` (4.26:1) |
| `--b2` | `#8ab45d` (7.35:1) | `#54752f` (4.30:1) |
| `--b3` | `#b7a63d` (7.16:1) | `#776a0a` (4.42:1) |
| `--b4` | `#e08e53` (6.84:1) | `#965726` (4.62:1) |
| `--b5` | `#e8847c` (6.73:1) | `#9c4e49` (4.73:1) |

- [ ] **Step 1: Write the failing test**

Add to `test_build_report.py`:

```python
class TestBands(unittest.TestCase):
    """The five rating bands survive the mono palette, in both themes."""

    BLOCKS = 3  # :root, [data-theme="light"], and the prefers-color-scheme block

    def test_every_band_is_defined_in_every_theme_block(self):
        for n in range(1, 6):
            found = len(re.findall(r"--b%d:#[0-9a-f]{6}" % n, TEMPLATE))
            self.assertEqual(found, self.BLOCKS,
                             "--b%d is defined %d times, expected %d"
                             % (n, found, self.BLOCKS))

    def test_the_dark_bands_are_the_derived_values(self):
        for name, value in (("b1", "#6aba77"), ("b2", "#8ab45d"), ("b3", "#b7a63d"),
                            ("b4", "#e08e53"), ("b5", "#e8847c")):
            self.assertIn("--%s:%s" % (name, value), TEMPLATE)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest test_build_report.TestBands -v`
Expected: FAIL — `--b1 is defined 0 times, expected 3`.

- [ ] **Step 3: Add the band variables to each theme block**

Into `:root{ … }`, beside the other role aliases:

```css
  --b1:#6aba77; --b2:#8ab45d; --b3:#b7a63d; --b4:#e08e53; --b5:#e8847c;
```

Into **both** the `:root[data-theme="light"]` block and the `prefers-color-scheme:light` block:

```css
  --b1:#397945; --b2:#54752f; --b3:#776a0a; --b4:#965726; --b5:#9c4e49;
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -b`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add build_report.py test_build_report.py
git commit -m "Retune the five rating bands for the Nocturne grounds"
```

---

### Task 4: Theme toggle

`data-theme` has always been a dead hook — no JS ever set it. Now that dark is the default, a manual override matters.

**Files:**
- Modify: `build_report.py` — EN/ES catalogues, the masthead markup, and the page JS
- Test: `test_build_report.py`

**Interfaces:**
- Consumes: the theme blocks from Task 1.
- Produces: `applyTheme(mode)` in the page JS, where `mode` is `"dark"` or `"light"`; a `#theme` button; i18n keys `light`, `dark`, `al_theme`.

- [ ] **Step 1: Write the failing test**

```python
class TestThemeToggle(unittest.TestCase):
    def test_the_toggle_ships(self):
        self.assertIn('id="theme"', TEMPLATE)
        self.assertIn('data-i18n-al="al_theme"', TEMPLATE)

    def test_the_toggle_writes_the_attribute_and_remembers(self):
        self.assertIn('setAttribute("data-theme"', TEMPLATE)
        self.assertIn('localStorage.setItem("eb.theme"', TEMPLATE)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest test_build_report.TestThemeToggle -v`
Expected: FAIL — `'id="theme"' not found`.

- [ ] **Step 3: Add the keys, the control, and the JS**

Add to `EN`:

```python
    "light": "LIGHT",
    "dark": "DARK",
    "al_theme": "Switch between the light and dark theme",
```

Add to `ES`:

```python
    "light": "CLARO",
    "dark": "OSCURO",
    "al_theme": "Cambiar entre el tema claro y el oscuro",
```

In the masthead, immediately before the `.lang` group:

```html
      <button type="button" id="theme" class="theme" data-i18n-al="al_theme"></button>
```

Style it beside `.lang`:

```css
.theme{display:inline-flex;align-items:center;gap:7px;align-self:flex-start;
  font:600 10.5px/1 var(--mono);letter-spacing:.1em;padding:8px 12px;cursor:pointer;
  border:1px solid var(--line);border-radius:var(--radius-md);background:transparent;
  color:var(--muted)}
.theme:hover{color:var(--accent);border-color:var(--accent)}
.theme .dot{width:9px;height:9px;border-radius:50%;border:1.5px solid currentColor}
:root[data-theme="light"] .theme .dot{background:currentColor}
```

Add to the page JS, near `applyLang`:

```javascript
  /* ---------- theme ---------- */

  // Dark is the default. An explicit choice is remembered and wins over the
  // system preference; with nothing saved the media query decides.
  var THEME = "dark";

  function savedTheme(){
    try {
      var s = localStorage.getItem("eb.theme");
      if (s === "dark" || s === "light") return s;
    } catch (e) {}
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light" : "dark";
  }

  function applyTheme(mode){
    THEME = mode === "light" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", THEME);
    try { localStorage.setItem("eb.theme", THEME); } catch (e) {}
    $("theme").innerHTML = '<span class="dot"></span>' + esc(t(THEME));
  }

  $("theme").addEventListener("click", function(){
    applyTheme(THEME === "dark" ? "light" : "dark");
  });
```

The button's label is language-dependent, so call `applyTheme(THEME)` at the end of `applyLang` to re-render it, and `applyTheme(savedTheme())` once at start-up **before** `applyLang(preferred())`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -b`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add build_report.py test_build_report.py
git commit -m "Add the theme toggle and make data-theme live"
```

---

### Task 5: Layout shell — sidebar rail and main column

Structural only: `.wrap` becomes a flex row, the existing controls move bodily into the rail still as `<select>`s, and the sticky header offset is re-established. Controls are converted in Task 6.

**Files:**
- Modify: `build_report.py` — `.wrap`/`.mast`/`.bar` CSS and the body markup; the `syncBar` JS
- Test: `test_build_report.py`

**Interfaces:**
- Consumes: the role variables from Task 1.
- Produces: `<aside class="rail">` and `<main class="main">` in the markup. Task 6 fills the rail; Tasks 7-8 style what is inside `main`.

- [ ] **Step 1: Write the failing test**

```python
class TestLayout(unittest.TestCase):
    def test_the_page_is_a_rail_beside_a_main_column(self):
        self.assertIn('<aside class="rail">', TEMPLATE)
        self.assertIn('<main class="main">', TEMPLATE)

    def test_the_horizontal_filter_bar_is_gone(self):
        self.assertNotIn('class="bar"', TEMPLATE)
        self.assertNotIn('class="row1"', TEMPLATE)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest test_build_report.TestLayout -v`
Expected: FAIL — `'<aside class="rail">' not found`.

- [ ] **Step 3: Restructure the shell**

Replace the `.wrap` rule with:

```css
.wrap{display:flex;min-height:100vh;align-items:stretch}
.rail{width:268px;flex:none;padding:22px 20px 28px;display:flex;flex-direction:column;
  gap:20px;background:var(--surface-2);border-right:1px solid var(--line-soft);
  position:sticky;top:0;height:100vh;overflow-y:auto}
.main{flex:1;min-width:0;display:flex;flex-direction:column;padding:0 28px 26px}
.rail .brand{display:flex;flex-direction:column;gap:3px}
.rail .kicker{font:600 9.5px/1 var(--font-body);letter-spacing:.16em;
  text-transform:uppercase;color:var(--accent)}
/* Not `.name` - that class is already the table's title cell. */
.rail .brandname{font:500 19px/1.1 var(--font-body);letter-spacing:-.02em}
.rail .meta{font:400 11.5px/1.4 var(--mono);color:var(--faint);margin-top:2px;
  font-variant-numeric:tabular-nums}
.rail h2{font:600 9.5px/1 var(--font-body);letter-spacing:.14em;text-transform:uppercase;
  color:var(--faint);margin:0 0 9px}
@media (max-width:900px){
  .wrap{display:block}
  .rail{width:auto;height:auto;position:static;border-right:0;
    border-bottom:1px solid var(--line-soft)}
  .main{padding:0 16px 40px}
}
```

Move the masthead inside `<main>`, wrap the filter controls in `<aside class="rail">`, and wrap the stats, table and footer in `<main class="main">`. The `.bar`, `.row1` and `.row2` wrappers go; their children move into the rail unchanged for now.

Because the rail is its own scroll container and the filter bar no longer exists, the sticky header offset is now zero. Delete `syncBar`, its `ResizeObserver`, its `resize` listener, its `document.fonts.ready` hook, and both call sites, then change the sticky rule:

```css
thead th{position:sticky;top:0;z-index:10;…}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -b`
Expected: PASS.

- [ ] **Step 5: Verify the page in a browser**

Run `python build_report.py`, open `out/report.html`, and confirm: the rail sits left and scrolls independently, the table header sticks to the top of the viewport when scrolling, and at a window narrower than 900px the rail stacks above the table.

- [ ] **Step 6: Commit**

```bash
git add build_report.py test_build_report.py
git commit -m "Move the report to a sidebar rail beside a main column"
```

---

### Task 6: Rail controls — tag chips, status counts, mode chips

The largest task. Three native `<select>`s and three checkboxes become buttons, and the sort dropdown disappears in favour of the column headers that already sort.

**Files:**
- Modify: `build_report.py` — EN/ES catalogues, rail markup, `passes()`, `applySort()`, all control wiring, `build()` for the status counts
- Test: `test_build_report.py`

**Interfaces:**
- Consumes: `<aside class="rail">` from Task 5; `ACTIVE` (unchanged).
- Produces: module-level `STATUS` (string, `""` for any) and `MODES` (object with `solo`/`coop`/`pad` booleans) in the page JS; `__STATUS_N__` substituted by `build()` as a JSON object mapping status to a whole-library count.

- [ ] **Step 1: Write the failing tests**

```python
class TestRailControls(unittest.TestCase):
    def test_the_selects_are_gone(self):
        for dead in ('<select id="tags"', '<select id="status"', '<select id="sort"'):
            self.assertNotIn(dead, TEMPLATE, "%s survived" % dead)

    def test_the_tag_filter_is_a_chip_rail(self):
        self.assertIn('id="tagchips"', TEMPLATE)
        self.assertIn('id="chips"', TEMPLATE)

    def test_status_rows_carry_a_whole_library_count(self):
        self.assertIn('id="statuslist"', TEMPLATE)
        self.assertIn("__STATUS_N__", TEMPLATE)

    def test_every_active_tag_still_has_to_match(self):
        self.assertRegex(TEMPLATE, r"ACTIVE\[i\]\) === -1\) return false")
```

And in `TestBuild`:

```python
    def test_the_status_counts_reach_the_page_as_numbers(self):
        html = self.build()
        counts = json.loads(re.search(r'var STATUS_N = (\{.*?\});', html).group(1))
        # The fixture is one listed game and one delisted game.
        self.assertEqual(counts["listed"], 1)
        self.assertEqual(counts["delisted"], 1)
        self.assertEqual(counts[""], 2)

    def test_the_status_counts_ignore_the_active_filter(self):
        # They describe the library, not the view, so they must be computed in
        # Python at build time rather than from the filtered rows in JS.
        html = self.build()
        self.assertNotIn("STATUS_N[", html.split("var STATUS_N")[0])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest test_build_report.TestRailControls -v`
Expected: FAIL — `<select id="tags" survived`.

- [ ] **Step 3: Churn the i18n catalogues**

Delete from **both** `EN` and `ES`: `so_conf`, `so_az`, `so_za`, `so_rating`, `so_reviews`, `so_new`, `so_old`, `al_sort`, `opt_tags`, `al_tags`.

Add to `EN`:

```python
    "f_tags": "Tags",
    "f_status": "Steam status",
    "f_minr": "Min reviews",
    "f_modes": "Modes",
    "railmeta": "{n} titles · {steam} on Steam",
```

Add to `ES`:

```python
    "f_tags": "Etiquetas",
    "f_status": "Estado en Steam",
    "f_minr": "Reseñas mín.",
    "f_modes": "Modos",
    "railmeta": "{n} títulos · {steam} en Steam",
```

Both `railmeta` strings use `{n}` and `{steam}` — `test_placeholders_survive_translation` compares the sets.

- [ ] **Step 4: Replace the rail markup**

```html
    <div class="brand">
      <div class="kicker">Epic backlog</div>
      <div class="brandname">Triage</div>
      <div class="meta" id="railmeta"></div>
    </div>

    <input type="search" id="q" data-i18n-ph="ph_search" data-i18n-al="al_search"
           placeholder="Search title, tag or developer&hellip;" aria-label="Search">

    <div>
      <h2 data-i18n="f_tags">Tags</h2>
      <div class="chiprail" id="tagchips"></div>
      <div class="row2" id="chips" hidden role="group" data-i18n-al="al_chips"
           aria-label="Tags being filtered on"></div>
    </div>

    <div>
      <h2 data-i18n="f_status">Steam status</h2>
      <div id="statuslist" class="statuslist"></div>
    </div>

    <div>
      <h2 data-i18n="f_minr">Min reviews</h2>
      <input type="range" id="minr" min="0" max="5" step="1" value="1"
             data-i18n-al="al_minr" aria-label="Minimum review count">
      <b id="minrv">100</b>
    </div>

    <div>
      <h2 data-i18n="f_modes">Modes</h2>
      <div class="chiprail" id="modechips"></div>
    </div>

    <button class="reset" id="reset" type="button" data-i18n="btn_reset">Reset</button>
```

Style the new pieces:

```css
.chiprail{display:flex;flex-wrap:wrap;gap:5px}
.chiprail button{font:400 11.5px/1 var(--font-body);padding:6px 9px;
  border-radius:var(--radius-sm);cursor:pointer;background:transparent;
  color:var(--muted);border:1px solid var(--line)}
.chiprail button:hover{border-color:var(--accent)}
.chiprail button[aria-pressed="true"]{background:var(--accent-soft);
  color:var(--accent-ink);border-color:var(--accent)}
.statuslist{display:flex;flex-direction:column;gap:5px}
.statuslist button{display:flex;align-items:center;gap:9px;width:100%;padding:6px 8px;
  border:0;border-radius:var(--radius-sm);cursor:pointer;text-align:left;
  background:transparent;color:var(--muted);font:400 12.5px/1.2 var(--font-body)}
.statuslist button:hover{background:var(--accent-soft)}
.statuslist button[aria-pressed="true"]{background:var(--accent-soft);color:var(--accent-ink)}
.statuslist .dot{width:5px;height:5px;flex:none;border-radius:50%;background:var(--faint)}
.statuslist button[aria-pressed="true"] .dot{background:var(--accent)}
.statuslist .n{margin-left:auto;font:400 11px/1 var(--mono);color:var(--faint);
  font-variant-numeric:tabular-nums}
```

- [ ] **Step 5: Compute the status counts in `build()`**

The counts describe the whole library, so they are computed once in Python, not from the filtered rows. In `build()`, beside the other substitutions:

```python
    statuses = ["listed", "delisted", "not-on-steam", "duplicate", "unreleased", "unknown"]
    status_n = {s: 0 for s in statuses}
    for g in games:
        key = g.get("steam_status") or "unknown"
        status_n[key if key in status_n else "unknown"] += 1
    status_n[""] = len(games)
    html = html.replace("__STATUS_N__", _json(status_n))
```

Add `var STATUS_N = __STATUS_N__;` beside the other `var N = __NUMS__;` declarations in the page JS.

- [ ] **Step 6: Rewrite the control reads and wiring**

`passes()` reads module state instead of DOM controls. Replace the `st`, `sp`, `co`, `pad` reads — the `ACTIVE` loop stays byte-identical:

```javascript
  var STATUS = "";
  var MODES = {solo: false, coop: false, pad: false};

  function passes(g){
    var q = $("q").value.trim().toLowerCase();
    if (q && g._hay.indexOf(q) === -1) return false;
    var mine = g.tags || [];
    for (var i = 0; i < ACTIVE.length; i++) {
      if (mine.indexOf(ACTIVE[i]) === -1) return false;
    }
    var st = STATUS;
    if (st && (g.steam_status || "unknown") !== st) return false;
    // The review floor is a browsing floor, and it would hide every row that has
    // no reviews to count - exactly the rows someone picking "never on Steam" or
    // "duplicate entry" asked to see. Asking for a status by name lifts it for
    // those rows only; rows that do have reviews are still filtered normally.
    if ((g.reviews || 0) < STEPS[+$("minr").value] && !(st && !g.reviews)) return false;
    if (MODES.solo && !g.singleplayer) return false;
    if (MODES.coop && !g.coop) return false;
    if (MODES.pad && !g.controller) return false;
    return true;
  }
```

Render the three control groups, and re-render them from `applyLang` so their labels follow the language:

```javascript
  function statusList(){
    var rows = [["", "st_any"], ["listed", "st_listed"], ["delisted", "st_delisted"],
                ["not-on-steam", "st_not"], ["duplicate", "st_dup"],
                ["unreleased", "st_unreleased"], ["unknown", "st_unknown"]];
    $("statuslist").innerHTML = rows.map(function(r){
      return '<button type="button" data-st="' + esc(r[0]) + '" aria-pressed="' +
             (STATUS === r[0] ? "true" : "false") + '"><span class="dot"></span>' +
             '<span>' + esc(t(r[1])) + '</span>' +
             '<span class="n">' + esc(nfmt(STATUS_N[r[0]] || 0)) + '</span></button>';
    }).join("");
  }

  function modeChips(){
    var rows = [["solo", "mode_solo"], ["coop", "mode_coop"], ["pad", "chk_pad"]];
    $("modechips").innerHTML = rows.map(function(r){
      return '<button type="button" data-mode="' + r[0] + '" aria-pressed="' +
             (MODES[r[0]] ? "true" : "false") + '">' + esc(t(r[1])) + '</button>';
    }).join("");
  }

  // Offered tags are the ones not already picked; picking one moves it to a chip.
  function tagChips(){
    $("tagchips").innerHTML = TAGS.map(function(tag){
      if (ACTIVE.indexOf(tag) !== -1) return "";
      return '<button type="button" data-tag="' + esc(tag) + '" aria-pressed="false">' +
             esc(tagName(tag)) + '</button>';
    }).join("");
  }
```

`TAGS` replaces the `__TAGS__` option list: have `build()` substitute `var TAGS = __TAGS__;` as a JSON array of the same tag names the `<option>`s carried, and delete the `offer()` function — `tagChips()` now decides what is on offer.

Wire them by delegation, replacing the removed `$("tags")`, `$("status")`, `$("sort")`, `$("sp")`, `$("co")`, `$("pad")` listeners:

```javascript
  $("statuslist").addEventListener("click", function(e){
    var b = e.target.closest ? e.target.closest("button[data-st]") : null;
    if (!b) return;
    STATUS = b.dataset.st;
    statusList();
    render();
  });
  $("modechips").addEventListener("click", function(e){
    var b = e.target.closest ? e.target.closest("button[data-mode]") : null;
    if (!b) return;
    MODES[b.dataset.mode] = !MODES[b.dataset.mode];
    modeChips();
    render();
  });
  $("tagchips").addEventListener("click", function(e){
    var b = e.target.closest ? e.target.closest("button[data-tag]") : null;
    if (!b || ACTIVE.indexOf(b.dataset.tag) !== -1) return;
    ACTIVE.push(b.dataset.tag);
    tagChips();
    chips();
    render();
  });
  $("q").addEventListener("input", render);
```

In `drop()` and the `#chips` clear handler, replace each `offer(tag, true)` call with a single `tagChips()` after the splice. In `$("reset")`, replace the select resets and checkbox resets with `STATUS = ""; MODES = {solo:false, coop:false, pad:false};` followed by `statusList(); modeChips(); tagChips();`.

In `applySort()`, delete the whole block that syncs `$("sort")` — from the `// Keep the dropdown showing the live state` comment through `sel.value = known ? want : "";`.

In `applyLang()`, delete the `each("#tags option", …)` retranslation and add `statusList(); modeChips(); tagChips();` beside the existing `chips();` call, plus:

```javascript
    $("railmeta").textContent = t("railmeta", {n: nfmt(N.count), steam: nfmt(N.rated)});
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python -m unittest discover -b`
Expected: PASS. `test_the_dropdown_invites_adding_rather_than_replacing`, `test_the_select_is_not_a_native_multiple` and `test_the_tag_filter_ships_a_chip_row_and_an_add_prompt` will fail first — they assert on the removed `<select>`. Delete the first two outright (the prompt and the native-multiple concern no longer exist) and rewrite the third as `test_the_tag_filter_is_a_chip_rail` from Step 1.

- [ ] **Step 8: Verify the page in a browser**

Run `python build_report.py`, open `out/report.html`, and confirm: picking a tag moves it from the rail to a chip and filters; the status rows show whole-library counts that **do not change** as you filter; mode chips toggle; Reset clears everything; switching language relabels every control; column headers still sort.

- [ ] **Step 9: Commit**

```bash
git add build_report.py test_build_report.py
git commit -m "Move the filters into the rail as chips and a counted status list"
```

---

### Task 7: Stat band

**Files:**
- Modify: `build_report.py` — the `.stats` and `.tile` CSS only
- Test: none beyond the existing suite; this is presentation with no markup or behaviour change.

**Interfaces:**
- Consumes: the `.tile`/`.k`/`.v`/`.n` markup that `tiles()` already emits — do not change the JS.

- [ ] **Step 1: Replace the stat CSS**

The design draws the tiles as one band ruled top and bottom, divided by hairlines, not as separate cards:

```css
.stats{display:flex;margin:22px 0 0;border-top:1px solid var(--line-soft);
  border-bottom:1px solid var(--line-soft)}
.tile{flex:1;padding:14px 18px 15px;border-left:1px solid var(--line-soft);
  background:none;border-radius:0;box-shadow:none}
.tile:first-child{border-left:0;padding-left:0}
.tile .k{font:600 9px/1 var(--font-body);letter-spacing:.15em;text-transform:uppercase;
  color:var(--faint)}
.tile .v{font:500 26px/1.15 var(--font-heading);letter-spacing:-.03em;margin-top:7px;
  font-variant-numeric:tabular-nums}
.tile .n{font-size:11.5px;color:var(--muted);margin-top:2px}
@media (max-width:900px){ .stats{flex-wrap:wrap} .tile{min-width:150px} }
```

- [ ] **Step 2: Run the tests to verify nothing broke**

Run: `python -m unittest discover -b`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add build_report.py
git commit -m "Draw the stat tiles as one ruled band"
```

---

### Task 8: Table

**Files:**
- Modify: `build_report.py` — the table CSS block and the masthead type
- Test: none beyond the existing suite; markup and JS are unchanged.

**Interfaces:**
- Consumes: everything above. Produces nothing new — the `<table>`, its `data-k` headers, and the row-render JS all stay exactly as they are.

- [ ] **Step 1: Restyle the table**

```css
.scroll{background:none;border-top:0;margin-top:18px}
table{border-collapse:collapse;width:100%;min-width:1020px}
thead th{position:sticky;top:0;z-index:10;background:var(--bg);
  font:600 9px/1.2 var(--font-body);letter-spacing:.14em;text-transform:uppercase;
  color:var(--faint);text-align:left;padding:0 12px 9px;
  border-bottom:1px solid var(--line);cursor:pointer;white-space:nowrap;user-select:none}
thead th:hover{color:var(--ink)}
thead th[aria-sort]{color:var(--accent)}
tbody td{padding:11px 12px;border-bottom:1px solid var(--line-soft);vertical-align:middle}
tbody tr:hover{background:var(--accent-soft);box-shadow:inset 2px 0 0 var(--accent)}
.name a{font:500 13.5px/1.25 var(--font-body);letter-spacing:-.01em}
.taglist span{border-radius:var(--radius-sm);border-color:var(--line-soft);
  background:none}
.rate .track{height:3px;border-radius:2px;background:var(--line-soft)}
.rate .fill{border-radius:2px}
.tag{border-radius:var(--radius-sm)}
.tag.gone{color:var(--accent-ink);border-color:var(--accent)}
```

Also bring the masthead down to the design's scale — `h1` at `font:500 30px/1.1 var(--font-heading)` with `letter-spacing:-.03em`, and `.sub` at `12.5px`.

- [ ] **Step 2: Run the tests to verify nothing broke**

Run: `python -m unittest discover -b`
Expected: PASS.

- [ ] **Step 3: Verify the whole page in a browser**

Run `python build_report.py` and open `out/report.html`. Check in **both** themes and **both** languages: the header sticks below nothing and stays legible over scrolling rows; row hover shows the accent edge; rating bars still carry their band colour; the delisted tag reads in the accent; nothing overflows horizontally at 1280px.

- [ ] **Step 4: Commit**

```bash
git add build_report.py
git commit -m "Restyle the table to the Backlog Triage design"
```

---

## Self-review

**Spec coverage.** Token layer → Task 1. Theme inversion → Task 1. Theme toggle → Task 4. Layout rail → Task 5. Typography → Task 2. Band colours → Task 3. i18n churn → Task 6. Per-status counts → Task 6. Stat band → Task 7. Table → Task 8. Sticky-header risk → Task 5 Step 3. Hours column: untouched by every task, so its `N.hasHours` condition survives — the spec's "Hours still appears only when HLTB data survived" is covered by the existing suite rather than a new test, since no task alters that path.

**Placeholders.** None. The band colours the spec deferred are derived and tabulated in Task 3; every code step carries real code.

**Type consistency.** `STATUS` (string) and `MODES` (object) are introduced in Task 6 Step 6 and consumed only there. `applyTheme(mode)` is defined and called in Task 4. `STATUS_N` is substituted in Step 5 and read in Step 6. `TAGS` replaces `__TAGS__` and is consumed by `tagChips()`; `offer()` is deleted in the same task that removes its only callers.

**Known ordering hazard.** Task 5 deletes `syncBar`, which Task 6 does not reference — but `applyLang` calls `syncBar()` today, so Task 5 must remove that call site too, or Task 6's `applyLang` edits will fail against a missing function.
