# Nocturne Report — Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a detail drawer that opens on row click and FLIP animations on re-sort to the Nocturne report, after first splitting the 752-line inline `TEMPLATE` string into separate template files so the diff is reviewable.

**Architecture:** `build_report.py`'s giant `TEMPLATE` raw string is split into `templates/head.html`, `templates/style.css`, `templates/body.html` and `templates/app.js`, read at import time and reassembled into the same `TEMPLATE` string. Each table row gains `data-row="<title>"`, which serves as the key for both a delegated click/keydown handler that opens a drawer (an empty `<aside>` shell whose `innerHTML` is rebuilt per selection) and a before/after `getBoundingClientRect()` comparison that drives FLIP animation via the Web Animations API on re-sort only.

**Tech Stack:** Python 3 (stdlib only for rendering), vanilla ES5 in the page, `unittest`. No build step, no framework, no new dependency.

**Spec:** `docs/superpowers/specs/2026-09-03-nocturne-phase-2-design.md`

## Global Constraints

- The report is **one self-contained HTML file**. Only the *source* is split into `templates/`; `build()` still writes a single `out/report.html`.
- **Python stdlib only.** No new entries in `requirements.txt`.
- **Page JS stays ES5** — `var`, `function`, no arrow functions, no `const`/`let`, no template literals, no `Array.prototype.includes`/`padStart`/etc. It matches the existing style and runs from `file://`.
- Run tests with `python -m unittest discover -b` from the repo root.
- **Every new i18n key needs a real Spanish string**, not the English one. `test_nothing_is_left_in_english_by_accident` enforces this.
- **Every i18n key must be used, and every used key must be defined.** Keys must be reachable as **literal** `t("key")` calls — `SCRIPT_KEYS = re.compile(r'\bt\("(\w+)"')` cannot see `t(someVar)`.
- `d_delta` takes placeholders and both languages must use the same placeholder set — `test_placeholders_survive_translation` compares them.
- Keep the line `if (mine.indexOf(ACTIVE[i]) === -1) return false;` **character-for-character** — `test_every_active_tag_has_to_match` matches it by regex.
- Metacritic stays absent. No playtime fact — `hltb_main` is absent from the current data entirely.
- **The card/grid view is out of scope by decision.** No `VIEW` state, no second renderer, no Table/Grid toggle, no `v_table`/`v_grid`/`al_view` keys.
- **The artboard's "Hide" button is dropped.** Do not build it.
- **Row click, not the title, opens the drawer.** The title stops being an `<a>`; the drawer's "Open Steam page" link is the only way to reach Steam from the row.
- **FLIP fires on sort only, never on filter.**
- **The split (Task 1) comes before any feature work**, and must produce a byte-identical `out/report.html`.
- **A browser pass is a required completion step, not optional** — Task 4 exists specifically because Phase 1 shipped an unusable control through eight green task reviews.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `templates/head.html` | `<title>` and font `<link>`s | new |
| `templates/style.css` | the stylesheet, unwrapped | new |
| `templates/body.html` | the page markup, unwrapped | new |
| `templates/app.js` | the page JavaScript, unwrapped | new |
| `build_report.py` | `_tpl()` + `TEMPLATE` assembly (EN/ES catalogues, `TAG_ES`, `REVIEW_ES`, `HOURS_TH`, `build()` stay here unchanged) | modified |
| `test_build_report.py` | i18n drift + build integrity | modified; new cases added |

---

### Task 1: Split `TEMPLATE` into external files

**Files:**
- Create: `templates/head.html`, `templates/style.css`, `templates/body.html`, `templates/app.js`
- Modify: `build_report.py:253-1005` (the `TEMPLATE = r"""..."""` assignment)
- Test: `test_build_report.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `TEMPLATE` (module-level string, identical content to today). Every later task edits the four template files directly, never a `TEMPLATE = r"""` block.

This is a pure refactor — the test below should **already pass before you touch anything**. That is expected and is exactly the safety net: it is computed from the current, unmodified output, so a mistake in the split shows up as this test *breaking*, not as it starting to pass.

- [ ] **Step 1: Write the byte-identity test**

Add to `test_build_report.py`. Add `hashlib` to the existing `import contextlib, io, json, os, re, tempfile, unittest` line.

```python
class TestTemplateSplit(unittest.TestCase):
    """Splitting TEMPLATE into files must not change a single byte of output."""

    # sha256 of out/report.html built from the TestBuild fixture, captured from the
    # pre-split TEMPLATE. If this stops matching, the split changed something.
    GOLDEN_SHA256 = "0858411f51357b3a33ce91afc4050338b4bbf52292e02842e383d64da063da7b"

    def test_the_split_build_is_byte_identical_to_before(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(setattr, build_report, "OUT", build_report.OUT)
        build_report.OUT = tmp
        with open(os.path.join(tmp, "games.json"), "w", encoding="utf-8") as fh:
            json.dump([{"title": "A Game", "steam_status": "listed", "rating": 92.5,
                        "reviews": 1200, "sort_score": 90.8, "review_desc": "Very Positive",
                        "tags": ["Action"], "release_date": "2020-01-01",
                        "developer": "Someone", "singleplayer": True},
                       {"title": "Gone Game", "steam_status": "delisted", "rating": None,
                        "reviews": 0, "tags": []}], fh)
        with contextlib.redirect_stdout(io.StringIO()):
            build_report.build()
        with open(os.path.join(tmp, "report.html"), encoding="utf-8") as fh:
            html = fh.read()
        self.assertEqual(hashlib.sha256(html.encode("utf-8")).hexdigest(), self.GOLDEN_SHA256)
```

- [ ] **Step 2: Run it to confirm it currently passes**

Run: `python -m unittest test_build_report.TestTemplateSplit -v`
Expected: PASS — this is the pre-split baseline, proving the hash is right before you change anything.

- [ ] **Step 3: Run the one-off extraction script**

Save this as `scratch_split.py` in the repo root and run it once with `python scratch_split.py`. It reads the current `TEMPLATE` out of `build_report.py` and writes the four files, byte-for-byte:

```python
"""One-off migration: splits build_report.py's inline TEMPLATE into
templates/head.html, templates/style.css, templates/body.html and templates/app.js.
Run once from the repo root, then delete this file."""
import os

with open("build_report.py", encoding="utf-8") as fh:
    src = fh.read()

i_tpl_start = src.index('TEMPLATE = r"""') + len('TEMPLATE = r"""')
i_tpl_end = src.index('"""\n\n\ndef _median', i_tpl_start)
tpl = src[i_tpl_start:i_tpl_end]

i_style_open_tag = tpl.index("<style>\n")
i_style_open = i_style_open_tag + len("<style>\n")
i_style_close = tpl.index("</style>\n")
i_bare_script_tag = tpl.index("<script>\n", i_style_close)
i_script_open = i_bare_script_tag + len("<script>\n")
i_script_close = tpl.rindex("</script>\n")

head = tpl[:i_style_open_tag]
style = tpl[i_style_open:i_style_close]
body = tpl[i_style_close + len("</style>\n"): i_bare_script_tag]
app = tpl[i_script_open:i_script_close]

os.makedirs("templates", exist_ok=True)
for name, content in (("head.html", head), ("style.css", style),
                      ("body.html", body), ("app.js", app)):
    with open(os.path.join("templates", name), "w", encoding="utf-8", newline="") as fh:
        fh.write(content)

print("wrote templates/head.html templates/style.css templates/body.html templates/app.js")
```

Verified against the current file: this produces `head.html` ending in the font `<link>` line, `style.css` running from `:root{` through the `prefers-reduced-motion` line, `body.html` starting with a blank line then `<div class="wrap">` and ending with the `<script id="data" type="application/json">__DATA__</script>` line, and `app.js` running from `(function(){` to `})();`.

- [ ] **Step 4: Replace the inline TEMPLATE with the file-backed assembly**

In `build_report.py`, delete the entire `TEMPLATE = r"""..."""` block (everything from `TEMPLATE = r"""` through the closing `"""` before `def _median`) and replace it with:

```python
def _tpl(name):
    with open(os.path.join(HERE, "templates", name), encoding="utf-8") as fh:
        return fh.read()


TEMPLATE = (_tpl("head.html")
            + "<style>\n" + _tpl("style.css") + "</style>\n"
            + _tpl("body.html")
            + "<script>\n" + _tpl("app.js") + "</script>\n")
```

Delete `scratch_split.py` — it was a one-off tool, not part of the repo.

- [ ] **Step 5: Run the tests to verify they still pass**

Run: `python -m unittest discover -b`
Expected: PASS, including `TestTemplateSplit`. If it fails, the diagnostic is a length/first-diff comparison between the rebuilt string and the golden fixture — re-check the exact byte offsets used in Step 3's script against your actual file content rather than guessing at whitespace.

- [ ] **Step 6: Commit**

```bash
git add templates/head.html templates/style.css templates/body.html templates/app.js build_report.py test_build_report.py
git commit -m "Split the report's inline TEMPLATE into templates/*"
```

---

### Task 2: The row key and the drawer

The largest task. Every table row becomes a keyed, keyboard-operable click target; a new drawer shell renders a game's full detail on selection.

**Files:**
- Modify: `templates/style.css` (drawer positioning/animation/content rules, `.name` restyle, focus-visible, bar-grow keyframe)
- Modify: `templates/body.html` (the `#veil`/`#drawer` shell)
- Modify: `templates/app.js` (row markup, `whyFor()`, `VISIBLE`, `SEL`, `LAST_FOCUS`, `openDrawer`/`closeDrawer`/`renderDrawer`, event wiring, `applyLang` hook)
- Modify: `build_report.py` (16 new EN/ES keys)
- Test: `test_build_report.py`

**Interfaces:**
- Consumes: `TEMPLATE` from Task 1 (now file-backed — edit the template files directly).
- Produces: `openDrawer(title)`, `closeDrawer()`, `renderDrawer()`, `whyFor(g)`, module-level `VISIBLE` (array, the current filtered+sorted rows), `SEL` (string title or `null`), `LAST_FOCUS` (Element or `null`). Task 3 consumes `VISIBLE` and the existing `render()`/`applySort()` shape.

- [ ] **Step 1: Write the failing tests**

Add to `test_build_report.py`:

```python
class TestDrawer(unittest.TestCase):
    """The row is a keyed, keyboard-operable click target that opens a detail drawer."""

    def test_every_row_carries_a_key_and_is_focusable(self):
        self.assertIn('data-row="', TEMPLATE)
        self.assertIn('tabindex="0"', TEMPLATE)

    def test_the_title_is_no_longer_a_link(self):
        self.assertNotIn('<a href="\' + g.steam_url', TEMPLATE)

    def test_the_drawer_shell_ships_with_dialog_roles(self):
        self.assertIn('id="veil" hidden', TEMPLATE)
        self.assertIn('role="dialog"', TEMPLATE)
        self.assertIn('aria-modal="true"', TEMPLATE)
        self.assertIn('aria-labelledby="dr-title"', TEMPLATE)

    def test_row_activation_opens_the_drawer(self):
        self.assertIn("function openDrawer(", TEMPLATE)
        self.assertIn('closest("tr[data-row]")', TEMPLATE)

    def test_the_drawer_traps_focus_and_closes_on_escape(self):
        self.assertIn('e.key === "Escape"', TEMPLATE)
        self.assertIn('e.key === "Tab"', TEMPLATE)

    def test_every_keyframe_is_covered_by_the_reduced_motion_guard(self):
        self.assertIn(
            "@media (prefers-reduced-motion:reduce){*{animation:none!important;"
            "transition:none!important}}", TEMPLATE)
        self.assertTrue(re.findall(r"@keyframes (\w+)", TEMPLATE),
                         "no keyframes found to guard")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest test_build_report.TestDrawer -v`
Expected: FAIL — `'data-row="' not found`.

- [ ] **Step 3: Add the 16 i18n keys**

Add to `EN` in `build_report.py`:

```python
    "d_conf": "Confidence score",
    "d_rating": "Steam rating",
    "d_tags": "Tags",
    "d_wilson": "The Wilson 95% lower bound on the share of positive reviews. It starts "
                "at the raw rating and pulls downward the fewer reviews there are.",
    "d_open": "Open Steam page",
    "al_close": "Close",
    "d_delta": "{delta} below the raw {raw}",
    "f_dev": "Developer",
    "f_pub": "Publisher",
    "f_rel": "Released",
    "pos": "positive",
    "neg": "negative",
    "reviews_n": "reviews",
    "prov_search": "Matched through Steam's own storefront search.",
    "prov_pcgw": "Steam's search cannot return this title, so it was identified through "
                 "PCGamingWiki — a weaker source that can pick the wrong release "
                 "where a name is reused.",
    "prov_none": "Neither Steam's search nor PCGamingWiki returned a page for this title.",
```

Add to `ES`:

```python
    "d_conf": "Puntuación de confianza",
    "d_rating": "Valoración en Steam",
    "d_tags": "Etiquetas",
    "d_wilson": "El límite inferior de Wilson al 95 % sobre la proporción de "
                "reseñas positivas: parte de la valoración bruta y tira hacia "
                "abajo cuantas menos reseñas hay.",
    "d_open": "Abrir la ficha de Steam",
    "al_close": "Cerrar",
    "d_delta": "{delta} por debajo del {raw} bruto",
    "f_dev": "Desarrollador",
    "f_pub": "Distribuidora",
    "f_rel": "Lanzamiento",
    "pos": "positivas",
    "neg": "negativas",
    "reviews_n": "reseñas",
    "prov_search": "Identificado mediante la propia búsqueda de la tienda de Steam.",
    "prov_pcgw": "La búsqueda de Steam no devuelve este título, así que se "
                 "identificó mediante PCGamingWiki: una fuente más débil "
                 "que puede elegir el lanzamiento equivocado cuando un nombre se reutiliza.",
    "prov_none": "Ni la búsqueda de Steam ni PCGamingWiki devolvieron una ficha "
                 "para este título.",
```

Both `d_delta` strings use `{delta}` and `{raw}` — `test_placeholders_survive_translation` compares the sets. `f_modes` and `f_status` already exist and are reused as-is; do not add them again.

- [ ] **Step 4: Key the row, drop the title link, extract `whyFor`**

In `templates/app.js`, add a `whyFor` function beside `tagFor` (it replaces the inline ternary currently built fresh inside `render()`):

```javascript
  function whyFor(g){
    return g.steam_status === "delisted" ? t("why_delisted")
      : g.steam_status === "duplicate"
      ? t("why_dup", {name: esc(g.duplicate_of) || t("why_dup_any")})
      : g.steam_status === "not-on-steam" ? t("why_not")
      : g.steam_status === "unreleased" ? t("why_unreleased")
      : t("why_unknown");
  }
```

Declare `var VISIBLE = [];` beside the existing `var sortKey = "sort_score", sortDir = -1;` and `var ACTIVE = [];`.

In `render()`, replace the row-building block:

```javascript
    body.innerHTML = rows.map(function(g, i){
      var b = g.band;
      var why = whyFor(g);
      var rate = g.rating == null
        ? '<span class="dash">' + why + '</span>'
        : '<div class="top"><span class="pct t' + b + '">' + pct(g.rating, 2) + '</span>' +
          '<span class="desc">' + esc(reviewName(g.review_desc)) + '</span></div>' +
          '<div class="track"><div class="fill f' + b + '" style="width:' + g.rating + '%"></div></div>';
      var name = '<span class="t">' + esc(g.title) + '</span>';
      var tag = tagFor(g.steam_status);
      if (tag) {
        var tip = why + (g.steam_source === "pcgw"
          ? t("tip_pcgw", {name: esc(g.matched_name)}) : "");
        name += '<span class="tag' + (g.steam_status === "delisted" ? " gone" : "") +
                '" title="' + tip + '">' + esc(tag) + '</span>';
      }
      return '<tr data-row="' + esc(g.title) + '" tabindex="0" role="button" aria-haspopup="dialog">' +
        '<td class="num rank">' + (i + 1) + '</td>' +
        '<td class="name">' + name +
          (g.developer ? '<div class="dev">' + esc(g.developer) + '</div>' : '') + '</td>' +
        '<td class="num"><b class="t' + b + '">' +
          (g.sort_score == null ? '<span class="dash">&mdash;</span>' : dec(g.sort_score, 2)) +
          '</b></td>' +
        '<td class="rate">' + rate + '</td>' +
        '<td class="num">' + (g.reviews ? nfmt(g.reviews) : '<span class="dash">&mdash;</span>') + '</td>' +
        '<td><div class="taglist">' + (g.tags || []).map(function(x){
            return '<span>' + esc(tagName(x)) + '</span>'; }).join('') + '</div></td>' +
        (N.hasHours ? '<td class="num">' +
          (g.hltb_main ? hrs(g.hltb_main) : '<span class="dash">&mdash;</span>') + '</td>' : '') +
        '<td class="num">' + (g.year || '<span class="dash">&mdash;</span>') + '</td>' +
        '<td class="mode">' + esc(g.mode) + '</td>' +
      '</tr>';
    }).join("");
    VISIBLE = rows;

    $("count").innerHTML = t("count", {n: nfmt(rows.length)});
    $("none").hidden = rows.length > 0;
```

(Only the row template and the added `VISIBLE = rows;` line changed; the sort above this block is untouched.)

- [ ] **Step 5: Add the drawer shell markup and its CSS**

In `templates/body.html`, insert between `</div>` (closing `.wrap`) and the data script tag:

```html
<div id="veil" hidden></div>
<aside id="drawer" role="dialog" aria-modal="true" aria-labelledby="dr-title" hidden></aside>

```

In `templates/style.css`, replace the `.name a` rules:

```css
.name a{color:var(--ink);text-decoration:none;display:block;text-underline-offset:2px;
  font:500 13.5px/1.25 var(--font-body);letter-spacing:-.01em}
.name a[href]:hover{text-decoration:underline;color:var(--accent-ink)}
```

with:

```css
.name .t{color:var(--ink);display:block;
  font:500 13.5px/1.25 var(--font-body);letter-spacing:-.01em}
```

Add `cursor:pointer` to the existing hover rule:

```css
tbody tr:hover{background:var(--accent-soft);box-shadow:inset 2px 0 0 var(--accent);cursor:pointer}
```

Add `tr` to the existing focus-visible selector list:

```css
input:focus-visible,button:focus-visible,th:focus-visible,tr:focus-visible{
  outline:2px solid var(--accent);outline-offset:2px}
```

Add a new section near the end of the file, before the `@media (max-width:1080px)` rule:

```css
/* ---------- bar grow (table + drawer) ---------- */
@keyframes barGrow{from{transform:scaleX(0)}to{transform:scaleX(1)}}
.rate .fill,.d-fill{transform-origin:left;animation:barGrow .5s cubic-bezier(.2,.8,.2,1) both}

/* ---------- drawer ---------- */
#veil{position:fixed;inset:0;background:rgba(15,17,28,.42);z-index:20;
  animation:drawerVeil .22s ease both}
#drawer{position:fixed;top:0;right:0;bottom:0;width:404px;max-width:92vw;
  background:var(--surface);box-shadow:var(--shadow);z-index:21;
  display:flex;flex-direction:column;overflow-y:auto;
  animation:drawerIn .3s cubic-bezier(.2,.8,.2,1) both}
@keyframes drawerVeil{from{opacity:0}to{opacity:1}}
@keyframes drawerIn{from{opacity:0;transform:translateX(26px)}to{opacity:1;transform:none}}
.d-head{display:flex;align-items:flex-start;gap:12px;padding:22px 24px 18px;
  border-bottom:1px solid var(--line-soft)}
.d-headtext{flex:1;min-width:0}
.d-rank{font:600 9.5px/1 var(--font-body);letter-spacing:.15em;text-transform:uppercase;
  color:var(--accent)}
.d-title{font:500 22px/1.15 var(--font-heading);letter-spacing:-.025em;margin-top:8px}
.d-dev{font-size:12px;color:var(--muted);margin-top:4px}
.d-close{flex:none;width:28px;height:28px;border:1px solid var(--line);border-radius:var(--radius-md);
  background:transparent;color:var(--muted);cursor:pointer;font:400 13px/1 var(--font-body)}
.d-close:hover{color:var(--accent);border-color:var(--accent)}
.d-badge{margin:12px 24px 0;align-self:flex-start}
.d-body{padding:20px 24px;display:flex;flex-direction:column;gap:20px}
.d-k{font:600 9.5px/1 var(--font-body);letter-spacing:.15em;text-transform:uppercase;color:var(--faint)}
.d-conf{display:flex;align-items:flex-end;gap:10px;margin-top:9px}
.d-conf b{font:500 44px/1 var(--mono);letter-spacing:-.035em;font-variant-numeric:tabular-nums}
.d-delta{font-size:11.5px;color:var(--faint);padding-bottom:6px}
.d-wilson{margin:10px 0 0;font-size:11.5px;line-height:1.6;color:var(--muted)}
.d-track{height:5px;margin-top:10px;border-radius:3px;background:var(--line-soft);overflow:hidden}
.d-top{display:flex;align-items:baseline;justify-content:space-between;margin-top:8px}
.d-pct{font:500 19px/1 var(--mono);font-variant-numeric:tabular-nums}
.d-desc{font:400 11.5px/1 var(--font-body);color:var(--muted)}
.d-posneg{display:flex;justify-content:space-between;margin-top:7px;
  font:400 10.5px/1 var(--mono);color:var(--faint)}
.d-facts{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line-soft)}
.d-fact{background:var(--surface);padding:11px 13px}
.d-fact .k{font:600 9px/1 var(--font-body);letter-spacing:.14em;text-transform:uppercase;
  color:var(--faint)}
.d-fact .v{font:400 13px/1.3 var(--font-body);margin-top:5px}
.d-tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:9px}
.d-tags span{font-size:11px;color:var(--muted);border:1px solid var(--line);
  border-radius:var(--radius-sm);padding:3px 8px}
.d-prov{margin:0;font-size:11px;line-height:1.6;color:var(--faint);
  border-top:1px solid var(--line-soft);padding-top:14px}
.d-actions{display:flex}
.d-open{flex:1;display:inline-flex;align-items:center;justify-content:center;
  font:500 12.5px/1 var(--font-body);text-decoration:none;color:var(--accent);
  border:1px solid var(--accent);border-radius:var(--radius-md);padding:11px 14px}
.d-open:hover{background:var(--accent-soft)}
```

`.t1`-`.t5` and `.f1`-`.f5` are already global (defined without a parent-class prefix), so the drawer reuses them directly for band coloring — no new color classes needed.

- [ ] **Step 6: Wire the drawer's JS**

In `templates/app.js`, add beside `var ACTIVE = [];`:

```javascript
  var SEL = null;
  var LAST_FOCUS = null;
```

Add the drawer functions beside `render()`:

```javascript
  function pad2(n){ return (n < 10 ? "0" : "") + n; }

  function renderDrawer(){
    var g = null;
    for (var i = 0; i < GAMES.length; i++) { if (GAMES[i].title === SEL) { g = GAMES[i]; break; } }
    if (!g) { closeDrawer(); return; }
    var rank = VISIBLE.indexOf(g) + 1;
    var b = g.band;
    var tag = tagFor(g.steam_status);
    var why = whyFor(g);
    var confHtml;
    if (g.sort_score == null) {
      confHtml = '<span class="dash">' + why + '</span>';
    } else {
      var delta = g.rating - g.sort_score;
      confHtml = '<div class="d-conf"><b class="t' + b + '">' + dec(g.sort_score, 2) + '</b>' +
        '<span class="d-delta">' + esc(t("d_delta", {delta: dec(delta, 2), raw: pct(g.rating, 2)})) +
        '</span></div>';
    }
    var rateHtml;
    if (g.rating == null) {
      rateHtml = '<span class="dash">' + why + '</span>';
    } else {
      rateHtml =
        '<div class="d-top"><span class="d-pct t' + b + '">' + pct(g.rating, 2) + '</span>' +
        '<span class="d-desc">' + esc(reviewName(g.review_desc)) + '</span></div>' +
        '<div class="d-track"><div class="d-fill f' + b + '" style="width:' + g.rating + '%"></div></div>' +
        '<div class="d-posneg"><span>' + esc(nfmt(g.positive) + " " + t("pos")) + '</span>' +
        '<span>' + esc(nfmt(g.negative) + " " + t("neg")) + '</span></div>';
    }
    var facts = [
      [t("f_dev"), g.developer || "—"],
      [t("f_pub"), g.publisher || "—"],
      [t("f_rel"), g.release_date ? ymd(g.release_date) : "—"],
      [t("f_modes"), g.mode || "—"],
      [t("f_status"), g.steam_status === "listed" ? t("st_listed") : tag]
    ];
    var factsHtml = facts.map(function(f){
      return '<div class="d-fact"><div class="k">' + esc(f[0]) + '</div>' +
             '<div class="v">' + esc(f[1]) + '</div></div>';
    }).join("");
    var tagsHtml = (g.tags || []).map(function(x){
      return '<span>' + esc(tagName(x)) + '</span>';
    }).join("");
    var prov = g.steam_source === "pcgw" ? t("prov_pcgw")
      : g.steam_url ? t("prov_search") : t("prov_none");
    var linkHtml = g.steam_url
      ? '<a class="d-open" href="' + g.steam_url + '" target="_blank" rel="noopener">' +
        esc(t("d_open")) + '</a>'
      : "";

    $("drawer").innerHTML =
      '<div class="d-head">' +
        '<div class="d-headtext">' +
          '<div class="d-rank">#' + pad2(rank) + '</div>' +
          '<div id="dr-title" class="d-title">' + esc(g.title) + '</div>' +
          (g.developer ? '<div class="d-dev">' + esc(g.developer) + '</div>' : "") +
        '</div>' +
        '<button type="button" id="dr-close" class="d-close" aria-label="' +
          esc(t("al_close")) + '">✕</button>' +
      '</div>' +
      (tag ? '<div class="d-badge tag' + (g.steam_status === "delisted" ? " gone" : "") + '">' +
        esc(tag) + '</div>' : "") +
      '<div class="d-body">' +
        '<div><div class="d-k">' + esc(t("d_conf")) + '</div>' + confHtml +
          '<p class="d-wilson">' + esc(t("d_wilson")) + '</p></div>' +
        '<div><div class="d-k">' + esc(t("d_rating")) + '</div>' + rateHtml + '</div>' +
        '<div class="d-facts">' + factsHtml + '</div>' +
        '<div><div class="d-k">' + esc(t("d_tags")) + '</div>' +
          '<div class="d-tags">' + tagsHtml + '</div></div>' +
        '<p class="d-prov">' + esc(prov) + '</p>' +
        (linkHtml ? '<div class="d-actions">' + linkHtml + '</div>' : "") +
      '</div>';
  }

  function openDrawer(title){
    LAST_FOCUS = document.activeElement;
    SEL = title;
    renderDrawer();
    $("veil").hidden = false;
    $("drawer").hidden = false;
    var closeBtn = $("dr-close");
    if (closeBtn) closeBtn.focus();
  }

  function closeDrawer(){
    SEL = null;
    $("veil").hidden = true;
    $("drawer").hidden = true;
    if (LAST_FOCUS && LAST_FOCUS.focus) LAST_FOCUS.focus();
  }
```

Wire the events, beside the other `addEventListener` calls:

```javascript
  body.addEventListener("click", function(e){
    var tr = e.target.closest ? e.target.closest("tr[data-row]") : null;
    if (tr) openDrawer(tr.getAttribute("data-row"));
  });
  body.addEventListener("keydown", function(e){
    if (e.key !== "Enter" && e.key !== " ") return;
    var tr = e.target.closest ? e.target.closest("tr[data-row]") : null;
    if (!tr) return;
    e.preventDefault();
    openDrawer(tr.getAttribute("data-row"));
  });
  $("veil").addEventListener("click", closeDrawer);
  $("drawer").addEventListener("click", function(e){
    if (e.target.closest && e.target.closest("#dr-close")) closeDrawer();
  });
  document.addEventListener("keydown", function(e){
    if (!SEL) return;
    if (e.key === "Escape") { closeDrawer(); return; }
    if (e.key !== "Tab") return;
    var focusable = $("drawer").querySelectorAll('a[href], button:not([disabled])');
    if (!focusable.length) return;
    var first = focusable[0], last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  });
```

In `applyLang()`, add beside the existing `tagChips();` call:

```javascript
    if (SEL) renderDrawer();
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `python -m unittest discover -b`
Expected: PASS.

- [ ] **Step 8: Verify in a browser**

Run `python build_report.py`, open `out/report.html`, and confirm, in **both** themes and **both** languages:

- Clicking a row opens the drawer with that game's rank, title, developer, confidence (with delta), rating bar with real positive/negative counts, five facts, tags, provenance sentence, and a working "Open Steam page" link when `steam_url` exists (and no link when it does not).
- Tab to a row and press Enter or Space — the drawer opens the same way.
- Escape closes the drawer and returns focus to the row that opened it.
- Clicking the veil, and clicking the ✕ button, both close it the same way.
- Tab from the last focusable element inside the drawer wraps to the first (and Shift+Tab from the first wraps to the last).
- Switching language while the drawer is open re-renders its text in place.
- Every rating bar (table and drawer) animates in from zero width on load.
- With "prefers reduced motion" emulated in devtools, the drawer's slide/fade and the bar-grow animation stop.

- [ ] **Step 9: Commit**

```bash
git add templates/head.html templates/style.css templates/body.html templates/app.js build_report.py test_build_report.py
git commit -m "Add the row-click detail drawer"
```

---

### Task 3: FLIP animation on re-sort

**Files:**
- Modify: `templates/app.js` (`render()`, `applySort()`)
- Test: `test_build_report.py`

**Interfaces:**
- Consumes: `VISIBLE`, `render()`, `applySort()` from Task 2 (unchanged shape otherwise).
- Produces: `FLIP_PENDING` (module-level boolean), `flip(old)`.

- [ ] **Step 1: Write the failing tests**

```python
class TestFlip(unittest.TestCase):
    """Rows animate to their new rank on sort, and only on sort."""

    def test_flip_is_armed_from_apply_sort_only(self):
        self.assertEqual(TEMPLATE.count("FLIP_PENDING = true"), 1)
        self.assertIn("function applySort(", TEMPLATE)

    def test_flip_respects_reduced_motion(self):
        self.assertIn('matchMedia("(prefers-reduced-motion: reduce)")', TEMPLATE)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest test_build_report.TestFlip -v`
Expected: FAIL — `FLIP_PENDING = true` appears 0 times.

- [ ] **Step 3: Add the flag, the measurement, and the animation**

In `templates/app.js`, declare beside `var VISIBLE = [];`:

```javascript
  var FLIP_PENDING = false;
```

Add a `flip` function beside `render()`:

```javascript
  function flip(old){
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    each("[data-row]", function(el){
      var was = old[el.getAttribute("data-row")];
      if (!was) return;
      var now = el.getBoundingClientRect();
      var dx = was.left - now.left, dy = was.top - now.top;
      if (!dx && !dy) return;
      el.animate(
        [{transform: "translate(" + dx + "px," + dy + "px)"}, {transform: "none"}],
        {duration: 320, easing: "cubic-bezier(.2,.8,.2,1)"});
    });
  }
```

At the top of `render()`, before it filters and sorts, capture old positions when a sort triggered this render:

```javascript
  function render(){
    var old = null;
    if (FLIP_PENDING) {
      old = {};
      each("[data-row]", function(el){
        old[el.getAttribute("data-row")] = el.getBoundingClientRect();
      });
    }
    var rows = GAMES.filter(passes);
    ...
```

(The `rows.sort(...)` block and the row-building block from Task 2 are unchanged.) After the row markup is written and `VISIBLE = rows;` runs, before the `$("count")...` lines, add:

```javascript
    if (old) {
      flip(old);
      FLIP_PENDING = false;
    }
```

In `applySort(k, dir)`, set the flag immediately before calling `render()`:

```javascript
  function applySort(k, dir){
    sortKey = k;
    sortDir = dir;
    each("thead th", function(o){
      o.removeAttribute("aria-sort");
      var a = o.querySelector(".ar"); if (a) a.textContent = "";
    });
    var th = document.querySelector('thead th[data-k="' + k + '"]');
    if (th) {
      th.setAttribute("aria-sort", dir === 1 ? "ascending" : "descending");
      var ar = th.querySelector(".ar");
      if (ar) ar.textContent = dir === 1 ? "▲" : "▼";
    }
    FLIP_PENDING = true;
    render();
  }
```

Every other caller of `render()` (search input, tag/status/mode chips, min-reviews slider, reset, language switch, initial load) leaves `FLIP_PENDING` at its default `false`, so no measurement happens outside a sort.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest discover -b`
Expected: PASS.

- [ ] **Step 5: Verify in a browser**

Run `python build_report.py`, open `out/report.html`, click a sortable column header, and confirm rows visibly slide from their old rank to their new one. Click a second time (reversing direction) and confirm it animates again. Type in the search box and confirm rows appear/disappear **without** any slide animation. With "prefers reduced motion" emulated, confirm sorting still re-ranks the rows but with no animation.

- [ ] **Step 6: Commit**

```bash
git add templates/app.js test_build_report.py
git commit -m "Animate rows to their new rank with FLIP on sort"
```

---

### Task 4: Full interactive verification

Phase 1 shipped a filter rail nobody could use through eight green task reviews, because every reviewer saw diffs and never opened the page. This task is that page, checked end to end, with both features exercised together rather than in isolation.

**Files:** none expected — this is a verification pass. If it turns up a real defect, fix it in place, re-run `python -m unittest discover -b`, and fold the fix into this task's commit.

- [ ] **Step 1: Build and open the report**

Run `python build_report.py` and open `out/report.html` directly from disk (not through a dev server — the report must work from `file://`).

- [ ] **Step 2: Walk the checklist**

In **both** themes and **both** languages, confirm:

- Opening the drawer by mouse click, and by keyboard (Tab to a row, Enter or Space), both work.
- Closing by Escape, by clicking the veil, and by clicking ✕ all work, and each restores focus to the row that opened the drawer.
- Tab-wrapping inside the open drawer works forward and backward, and focus never escapes to the page behind the veil.
- Drawer content is correct for: a game with a Steam URL, a delisted game (badge shows, provenance mentions the sale pull), a game matched via PCGamingWiki (provenance says so), and a game with no Steam match at all (no link, no badge, "no page" provenance).
- Sorting by every column re-ranks rows with a visible FLIP slide; searching, tag-picking, status-picking, mode-picking and the min-reviews slider all re-filter with **no** slide.
- Switching language while the drawer is open updates its text without closing it.
- Switching theme does not break drawer positioning or contrast.
- At a browser width under 900px, the drawer still opens sanely (it is not scoped to the rail's responsive breakpoint, so check it does not overflow or clip).
- With "prefers reduced motion" emulated in devtools, the drawer opens/closes instantly (no slide/fade) and sorting reorders instantly (no FLIP), while everything above still functions.

- [ ] **Step 3: Resolve or close out**

If any item above fails, fix the underlying code, re-run `python -m unittest discover -b` to confirm nothing broke, and commit the fix with a message describing what was wrong. If everything passes, no commit is needed — this task's deliverable is the confirmation itself.

---

## Self-review

**Spec coverage.** Structural split → Task 1, with the byte-identity acceptance test spelled out concretely (golden hash, not a placeholder). Row-as-key architecture → Task 2 Step 4. Drawer shell, content sourcing (real `positive`/`negative`, five facts, dropped Metacritic/playtime, provenance from `steam_source`) → Task 2 Steps 5-6. Accessibility beyond the artboard (focus in/out, Escape, Tab wrap) → Task 2 Step 6, explicitly checked again in Task 2 Step 8 and Task 4. Bar-grow, drawer/veil keyframes → Task 2 Step 5, guarded by the pre-existing global `prefers-reduced-motion` rule (tested in Step 1). FLIP scope (sort only) → Task 3, with a test asserting `FLIP_PENDING = true` appears exactly once. Card/grid view, Hide button, view-toggle i18n keys → deliberately absent throughout; called out in Global Constraints. i18n churn (16 keys, `d_delta` placeholder parity, `f_modes`/`f_status` reuse) → Task 2 Step 3, validated by the existing catalogue tests plus the new `d_delta`-bearing keys. Required browser pass → Task 4, plus embedded browser steps in Tasks 2 and 3.

**Placeholders.** None — every step carries the real code, real i18n strings (including Spanish), and a real computed golden hash rather than a stand-in.

**Type consistency.** `VISIBLE` (array) is declared and populated in Task 2 Step 4, consumed unchanged by Task 3's `flip()`. `SEL` (string title or `null`) and `LAST_FOCUS` (Element or `null`) are declared and fully used within Task 2. `openDrawer(title)`, `closeDrawer()`, `renderDrawer()`, `whyFor(g)`, `pad2(n)` are each defined once and called with matching signatures everywhere they're used. `FLIP_PENDING` is declared in Task 3 and referenced only in `render()` and `applySort()`, both edited in that same task.

**Known ordering hazard.** Task 3 edits the same `render()` function Task 2 just wrote (the row-building block). If executed out of order, or by two agents against a stale copy of `app.js`, Task 3's diff will not apply cleanly — Task 3 must start from the `app.js` that Task 2 committed, not from Task 1's.
