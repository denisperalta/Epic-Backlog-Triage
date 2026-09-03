# Nocturne report restyle — Phase 1

**Status:** awaiting review
**Design canvas:** `bc1cb362-1f06-45f2-a839-ce60fcb96ed3`, artboard `Backlog Triage.dc.html`

## Problem

`out/report.html` is rendered from `TEMPLATE`, a 613-line raw string at
`build_report.py:261-874` carrying its own `<style>`, markup and render JS. Its
look is self-invented: a light-first palette on a warm amber accent, three
webfont families, a 1300px centred column, and a horizontal filter bar of
native `<select>` controls.

There is now an approved design — "Backlog Triage", drawn against the Nocturne
design system — that the report should follow. Nocturne is dark-first, mono on a
single blurple accent, Inter throughout, compact (0.7x density), 8px radii.

The design was drawn against an older shape of the data and does not match the
repo in several places. This spec records what was decided and what Phase 1
builds.

## Design vs repo: the conflicts

Checked against `out/games.json` (389 records).

| Design expects | Repo reality | Decision |
|---|---|---|
| `g.genres`, column "Genre" | field is `tags`; `b9473ba` relabelled Genre to Tags | repo wins — Tags |
| `g.metacritic`, MC column + drawer fact | field does not exist; `b9473ba` dropped it | drop from the design |
| positives as `rating * reviews` | real `positive`/`negative` counts in the data | use the real fields |
| no Hours column | conditional HowLongToBeat column (`HOURS_TH`) | keep as an extra column |
| 9-column CSS grid of divs | real `<table>` with `data-k` headers | keep `<table>`, restyle |
| mono bands (accent tints + grey) | five hues, green to red (`--b1`..`--b5`) | keep five hues, retuned |
| 214 titles | 389 | mock data only; no action |

The two deviations from the design are deliberate:

**Keep `<table>`.** The grid-of-divs is a mock-authoring convenience, not a
design requirement. A real table keeps row/column semantics for screen readers,
`aria-sort` on headers, the working sticky `thead`, and the markup the tests
read. It can be made to look identical.

**Keep five band hues.** Nocturne's mono rule exists so saturated fills do not
flood large areas. The band colors are hairline bars and small numerals, not
floods, and hue is the only at-a-glance quality signal in a table built for
scanning. The five are re-derived to sit correctly on the dark ground rather
than dropped.

## Scope

**In:** Nocturne token layer, theme inversion plus a working theme toggle, the
sidebar rail, the stat band, the restyled sortable table, Inter, retuned bands.

**Out (Phase 2):** grid/card view, the 404px detail drawer, FLIP animations on
re-sort.

## Architecture

### Token layer

Nocturne's `:root` block is inlined verbatim into `TEMPLATE`'s `<style>`:
~60 lines of plain hex, `color-mix(in srgb, ...)`, and the space/radius/shadow
scales. No OKLCH at runtime, no `@property`, no build step. The report stays a
single self-contained file.

The report's existing role variables are then redefined as aliases onto those
tokens:

```css
:root{
  --bg:var(--color-bg); --surface:var(--color-surface);
  --ink:var(--color-text); --line:var(--color-divider); ...
}
```

This is the pattern the artboard itself uses (`.ebt{--bg:var(--color-bg);...}`).
Every existing selector and every line of render JS keeps reading `var(--bg)`,
`var(--ink)`, `var(--line)` and needs no edit.

**Rejected:** vendoring all of `styles.css` — its `.btn`/`.card`/`.table`/`.seg`
layer styles markup this report does not have, so adopting it means rewriting the
markup and overriding most of what it brings. **Rejected:** fetching `styles.css`
at build time — puts a network and auth dependency into `build()`, which today
reads only local JSON.

### Theme

Today: light-first `:root`, with `@media (prefers-color-scheme:dark)` guarded by
`:root:not([data-theme="light"])`, plus `:root[data-theme="dark"]`
(`build_report.py:266-296`). `data-theme` is never set by any JS — a dead hook.

After: the same three-block structure, inverted. `:root` carries dark Nocturne.
The light set — inverted onto the accent ramps, taken from the artboard's
`.ebt[data-t="light"]` rules — moves into `:root[data-theme="light"]` and a
`@media (prefers-color-scheme:light)` block guarded by
`:root:not([data-theme="dark"])`.

Phase 1 adds the design's DARK/LIGHT toggle in the header, writing `data-theme`
on `documentElement` and persisting to `localStorage`. This makes the existing
hook live and gives the flipped default a manual override.

### Layout

`.wrap` (max-width 1300px, centred) becomes a full-width flex row: a 268px
`<aside>` rail and a `<main>`. The horizontal `.bar` dissolves into the rail.

| Today | After |
|---|---|
| `<select id="tags">` + `#chips` row | tag chip buttons, selected state on the accent |
| `<select id="status">` | status list, one row per status, with per-status counts |
| `<select id="sort">` | sortable `<th>` headers (`data-k` and `.ar` already exist) |
| `#q` search input | same control, restyled, at the top of the rail |
| `#minr` range + `#minrv` | same, with the 0/500/10k/50k scale labels |
| three mode checkboxes | mode chip buttons |
| `#reset` | outlined reset button, pinned to the rail foot |
| `#count` | moves to the footer line under the table |

Per-status counts are new and must be computed. They count the **whole library**,
not the current filter, so the numbers do not move as you filter.

### Typography

Bricolage Grotesque + IBM Plex Sans + IBM Plex Mono collapse to **Inter alone**,
loaded from the same Google Fonts link. Tabular numerals use
`ui-monospace,SFMono-Regular,Menlo,monospace` — a system stack, no webfont. Three
families become one.

### Band colors

`--b1`..`--b5` stay five, re-derived rather than reused. Each must:

- sit in the ramp's 400-500 perceptual lightness band, so they carry the same
  visual weight as Nocturne's neutrals;
- hold chroma near the accent's (C 0.125 in OKLCH) — present, not loud;
- clear 3:1 against `--color-bg` (#161826) in dark and against the light ground
  (#e7e5fe, `--color-accent-200`) in light.

Exact values are derived and contrast-checked during implementation, not
guessed here. The light set needs its own derivation: the new light ground is
accent-tinted (#e7e5fe), not the neutral #f4f4f8 the current values were tuned
against.

## i18n

`build_report.py` carries EN and ES dicts (`build_report.py:10-256`) and the
template addresses them by `data-i18n` attributes. The suite enforces both
directions, so key churn is not optional:

**Removed** (the sort `<select>` goes): `so_conf`, `so_az`, `so_za`, `so_rating`,
`so_reviews`, `so_new`, `so_old`, `al_sort`, `opt_tags`, `al_tags`.
Leaving any in place fails `test_no_string_is_defined_and_never_used`.

**Added:** rail section headings (`f_tags`, `f_status`, `f_minr`, `f_modes`),
theme toggle labels (`light`, `dark`, `al_theme`), and the rail meta line
(`railmeta`). Each needs a real Spanish string or
`test_nothing_is_left_in_english_by_accident` fails.

`railmeta` carries counts ("389 titles · 312 on Steam"), so it takes `{}`
placeholders rather than baked numbers, and both languages must use the same
set — `test_placeholders_survive_translation` compares them.

Status labels (`st_any` .. `st_unknown`) and column headings (`th_game` ..
`th_modes`) carry over unchanged.

## Testing

TDD. `test_build_report.py` already covers the ground that matters and three of
its tests assert on markup being removed:

| Test | Impact |
|---|---|
| `test_the_select_is_not_a_native_multiple` | asserts `<select id="tags">` — rewrite for the chip rail |
| `test_the_dropdown_invites_adding_rather_than_replacing` | asserts on `opt_tags` — remove with the key |
| `test_the_tag_filter_ships_a_chip_row_and_an_add_prompt` | asserts `id="chips"` and an `<option>` — rewrite |
| `test_no_string_is_defined_and_never_used` | fails until the `so_*` keys go |
| `test_every_key_the_page_asks_for_exists` | fails until new keys land in both dicts |
| `test_every_active_tag_has_to_match` | asserts filter JS — must survive the rail rewrite |

New tests to add:

- per-status counts reach the page as numbers, and count the whole library
  rather than the filtered set;
- the theme toggle ships and writes `data-theme`;
- the Hours column still appears only when HLTB data survived;
- every `--b*` band variable is defined in both the dark and light blocks.

## Risks

- **The template is one 613-line string.** The edit is large and cannot be
  meaningfully diffed in pieces. Work in order — tokens, then theme blocks, then
  layout, then rail, then table — running the suite at each step.
- **Filter JS is coupled to control types.** Moving from `<select>` to chip
  buttons rewrites the read path for tags, status and modes. `ACTIVE` array
  handling for tags is asserted by test and must keep its semantics.
- **Contrast.** Nocturne's own readme warns the accent-to-ground pair is tuned
  to 3:1 — enough for chrome and large text, not for body copy. Muted text on
  the new grounds needs checking, not assuming.
- **Sticky `thead`** currently depends on the page scrolling as one column. The
  rail plus `<main>` layout changes the scroll container; the sticky offset has
  to be re-established.

## Phase 2 (deferred)

Card grid view with a Table/Grid toggle, the 404px detail drawer (confidence,
rating bar, positive/negative split from the real fields, fact grid, tags,
provenance line, Steam link), and FLIP animations on re-sort and re-filter.
