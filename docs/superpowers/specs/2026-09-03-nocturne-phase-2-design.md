# Nocturne report — Phase 2

**Status:** awaiting review
**Design canvas:** `bc1cb362-1f06-45f2-a839-ce60fcb96ed3`, artboard `Backlog Triage.dc.html`
**Phase 1 spec:** `docs/superpowers/specs/2026-09-02-nocturne-report-restyle-design.md`

## Problem

Phase 1 restyled the report onto Nocturne at feature parity and deliberately
deferred three things the artboard draws: a card/grid view, a detail drawer that
opens on row click, and FLIP animations on re-sort.

This spec covers **the drawer and the animations**, plus one structural change that
has to come first. **The card/grid view is out of scope by decision** — the table
stays the only view, and neither the grid nor its Table/Grid toggle is built.

## The structural change comes first

`TEMPLATE` is now 752 lines inside a 1,088-line `build_report.py` — 241 lines of
CSS, 81 of markup, 431 of page JavaScript, all in one Python raw string. Phase 1's
own risk section named this as its top risk: "the edit is large and cannot be
meaningfully diffed in pieces," and that is exactly what made Phase 1's largest
task hard to review.

Phase 2 adds roughly 300 more lines of JavaScript and 100 of CSS. Splitting
first is therefore Task 1, before any feature work.

**The split:**

```
templates/head.html    the <title> and the font <link>s
templates/style.css    the stylesheet, without the <style> wrapper
templates/body.html    the page markup
templates/app.js       the page JavaScript, without the <script> wrapper
```

`build_report.py` reads these at **import time** and assembles the same
`TEMPLATE` string it exposes today:

```python
def _tpl(name):
    with open(os.path.join(HERE, "templates", name), encoding="utf-8") as fh:
        return fh.read()

TEMPLATE = (_tpl("head.html")
            + "<style>\n" + _tpl("style.css") + "</style>\n"
            + _tpl("body.html")
            + "<script>\n" + _tpl("app.js") + "</script>\n")
```

The `<script id="data" type="application/json">__DATA__</script>` tag stays at the
end of `body.html`, not in the assembly — the assembly adds only the `<style>` and
`<script>` wrappers around the two files that need them, and nothing else.

**This is why the split is safe.** `test_build_report.py` does
`from build_report import HOURS_TH, I18N, TEMPLATE` and computes
`MARKUP = TEMPLATE + HOURS_TH`. As long as `TEMPLATE` remains a module-level
string with identical content, **every existing test passes unchanged**. The
split is mechanical: no test edits, no behaviour change, and `python
build_report.py` must produce a byte-identical `out/report.html` before and
after. That byte-identity is the task's acceptance test.

The generated report stays one self-contained HTML file. Only the source is
split.

## Decisions taken

| Question | Decision | Why |
|---|---|---|
| The artboard's card/grid view | **Not built** | Denis's call. The table is the only view; no `VIEW` state, no second renderer, no Table/Grid toggle, and the three keys that toggle would need are not added. |
| The artboard's "Hide" button | **Dropped** | The design gives it no behaviour, no persistence and no unhide path. Building it properly is a feature with its own surface; shipping it inert is a dead control. |
| Row click vs. the title's Steam link | **Row opens the drawer; the title stops being an `<a>`; the drawer's "Open Steam page" is the way out** | Two different click targets in one row is a usability trap. Costs one extra click to reach Steam. |
| FLIP scope | **Re-sort only** | Filter changes fire on every keystroke in the search box; measuring ~800 element rects per keystroke against 389 rows would be visible lag. Sorting is where rows visibly travel to a new rank, which is the effect worth having. |
| File structure | **Split first** | See above. |

## Architecture

### The row as a key

`render()` keeps its current shape — filter, sort, build one `innerHTML` string for
`#body`. The only change is that each `<tr>` gains `data-row="<title>"`.

That single attribute serves both new features: the delegated click handler that
opens the drawer, and the key FLIP matches old positions against. No view state, no
second renderer, no container switching.

### Drawer

Markup ships as an empty shell:

```html
<div id="veil" hidden></div>
<aside id="drawer" role="dialog" aria-modal="true" aria-labelledby="dr-title" hidden></aside>
```

`openDrawer(title)` looks the game up, builds the panel's `innerHTML`, unhides
both elements, and moves focus to the close button. `closeDrawer()` hides them and
restores focus to the row that opened it.

A module-level `SEL` holds the selected title, so `applyLang` can re-render the
drawer on a language switch — the same pattern `statusList()`/`modeChips()`/
`tagChips()` already follow.

**Accessibility the artboard does not draw, but which a modal requires:**
Escape closes; focus moves in on open and is restored on close; Tab wraps within
the panel. Without these the drawer is broken for keyboard users.

### Drawer content

All from real fields — no estimates:

| Section | Source |
|---|---|
| Rank kicker | position in the current filtered+sorted list |
| Title, developer | `title`, `developer` |
| Status badge | `steam_status` via the existing `tagFor()` |
| Confidence | `sort_score` to 2dp, with its delta from the raw `rating` |
| Wilson explanation | static translated prose |
| Rating | `rating`, `review_desc`, and the **real `positive` / `negative` counts** (367/366 records carry them) rather than the artboard's `rating x reviews` estimate |
| Facts grid | Developer, Publisher, Released, Modes, Steam status — five, not the artboard's six |
| Tags | `tags`, through the existing `tagName()` translation |
| Provenance | `steam_source`: store search, PCGamingWiki, or neither |
| Steam link | `steam_url`; omitted when absent |

**Metacritic is dropped** — the field does not exist, as established in Phase 1.
**No playtime fact:** `hltb_main` is absent from the current data entirely, so the
Hours column is already dormant and a playtime fact would be too.

`Released` reuses the existing `ymd()` helper (`build_report.py:671`) rather than
inventing new date formatting.

### Animations

- **Bar grow** — a CSS keyframe on the rating `.fill`, cheap, always on.
- **Drawer and veil** — slide and fade keyframes, per the artboard.
- **FLIP on sort only** — `applySort` flags the render. Before writing the new
  HTML, `render` captures `getBoundingClientRect()` for each `[data-row]` node into
  a map keyed by title; after writing, each new node with a matching old rect is
  animated from its old offset via the Web Animations API.

Every animation sits behind the existing `prefers-reduced-motion` guard.

## i18n

Sixteen new keys, each needing a real Spanish string:

`d_conf`, `d_rating`, `d_tags`, `d_wilson`, `d_open`, `al_close`, `d_delta`,
`f_dev`, `f_pub`, `f_rel`, `pos`, `neg`, `reviews_n`, `prov_search`, `prov_pcgw`,
`prov_none`.

The three keys a view toggle would have needed (`v_table`, `v_grid`, `al_view`) are
not added, since the grid is not built.

`f_modes` and `f_status` already exist as rail headings and are reused as fact
labels rather than duplicated.

Two constraints Phase 1 established the hard way, both of which bit real tasks:

- Keys must be reachable as **literal** `t("key")` calls. `SCRIPT_KEYS` is
  `re.compile(r'\bt\("(\w+)"')` and cannot see `t(someVar)`.
- `d_delta` takes placeholders (the delta and the raw percentage) and both
  languages must use the same placeholder set — `test_placeholders_survive_translation`
  compares them.

## Testing

The suite is Python-only and cannot execute page JavaScript. It pins template
content and build output; it cannot verify that a click opens the drawer. That
limit is known and accepted — a JS runner would be a new dependency.

New tests:

- The split produces a byte-identical `out/report.html` (Task 1's acceptance test).
- The drawer shell ships with its dialog roles.
- Every table row carries `data-row` and is keyboard-focusable.
- Every animation keyframe is inside a `prefers-reduced-motion` guard.
- FLIP measurement runs on sort and not on filter.

**A browser pass is a required completion step, not an optional one.** Phase 1
shipped a filter rail nobody could use — 214 chips burying every control — through
eight green task reviews, because every reviewer saw diffs and none saw a page.
Both features here are more interactive than anything in Phase 1, and the drawer in
particular cannot be verified any other way.

## Risks

- **The drawer is the first true modal in this page.** Focus handling, Escape, and
  the veil's click target are easy to get subtly wrong and invisible to the suite.
- **FLIP against `innerHTML` replacement** means old nodes are destroyed before new
  ones exist. Positions must be captured before the write and matched by key after —
  a stale or mismatched key silently produces no animation rather than an error.
- **The row is now a click target containing no link.** Keyboard users need the row
  itself reachable and activatable, or the drawer is mouse-only.
- **Byte-identity in Task 1** depends on getting whitespace between the assembled
  parts exactly right. Expect the first attempt to differ by a newline.
