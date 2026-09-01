"""Render out/games.json into a single self-contained HTML report."""
import json, os, datetime
from collections import Counter

from steamlib import use_utf8_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

TEMPLATE = r"""<title>Epic Backlog Triage</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,800&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root{
  --bg:#f4f4f8; --surface:#ffffff; --surface-2:#fafafb;
  --ink:#191b22; --muted:#6a6e80; --faint:#9296a8;
  --line:#e3e4ec; --line-soft:#eeeff4;
  --accent:#a75f10; --accent-soft:#f5e7d3; --accent-ink:#7d460a;
  --b1:#2f8f5b; --b2:#6d9f34; --b3:#bd9418; --b4:#c46a2f; --b5:#bb4030;
  --track:#e9eaf1; --chip-ink:#ffffff;
  --shadow:0 1px 2px rgba(25,27,34,.06),0 10px 26px -18px rgba(25,27,34,.30);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#111218; --surface:#191b22; --surface-2:#1e202a;
    --ink:#e9eaf0; --muted:#969bad; --faint:#6d7285;
    --line:#2a2d38; --line-soft:#22252f;
    --accent:#e9a54a; --accent-soft:#3a2c17; --accent-ink:#f0b968;
    --b1:#4bb87a; --b2:#8fc44a; --b3:#d9b23c; --b4:#e08a4e; --b5:#dd6152;
    --track:#272a35; --chip-ink:#14161c;
    --shadow:0 1px 2px rgba(0,0,0,.40),0 10px 26px -18px rgba(0,0,0,.70);
  }
}
:root[data-theme="dark"]{
  --bg:#111218; --surface:#191b22; --surface-2:#1e202a;
  --ink:#e9eaf0; --muted:#969bad; --faint:#6d7285;
  --line:#2a2d38; --line-soft:#22252f;
  --accent:#e9a54a; --accent-soft:#3a2c17; --accent-ink:#f0b968;
  --b1:#4bb87a; --b2:#8fc44a; --b3:#d9b23c; --b4:#e08a4e; --b5:#dd6152;
  --track:#272a35; --chip-ink:#14161c;
  --shadow:0 1px 2px rgba(0,0,0,.40),0 10px 26px -18px rgba(0,0,0,.70);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 "IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;
  -webkit-font-smoothing:antialiased}
.wrap{max-width:1300px;margin:0 auto;padding:30px 20px 80px}

/* ---------- masthead ---------- */
.mast{display:flex;flex-wrap:wrap;align-items:flex-end;gap:16px 28px;margin-bottom:22px}
h1{font-family:"Bricolage Grotesque",ui-sans-serif,system-ui,sans-serif;
  font-weight:800;font-size:clamp(29px,4.4vw,44px);line-height:1.02;letter-spacing:-.022em;
  margin:0;text-wrap:balance}
h1 em{font-style:normal;color:var(--accent)}
.sub{color:var(--muted);font-size:14px;max-width:64ch;margin:9px 0 0}
.sub code{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12.5px;
  background:var(--surface-2);border:1px solid var(--line);border-radius:4px;padding:1px 5px}
.sub b{color:var(--ink);font-weight:600}

/* ---------- stat tiles ---------- */
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(148px,1fr));gap:12px;margin:0 0 22px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:9px;
  padding:13px 15px;box-shadow:var(--shadow)}
.tile .k{font-size:10.5px;letter-spacing:.10em;text-transform:uppercase;color:var(--faint);
  font-weight:600}
.tile .v{font-family:"Bricolage Grotesque",ui-sans-serif,sans-serif;font-weight:700;
  font-size:27px;line-height:1.15;margin-top:5px;font-variant-numeric:tabular-nums}
.tile .n{font-size:12px;color:var(--muted);margin-top:1px}

/* ---------- controls ---------- */
.bar{position:sticky;top:0;z-index:20;background:var(--bg);
  padding:11px 0 12px;border-bottom:1px solid var(--line);margin-bottom:2px}
.row1{display:flex;flex-wrap:wrap;gap:9px;align-items:center}
input[type=search],select{font:14px/1.2 "IBM Plex Sans",sans-serif;color:var(--ink);
  background:var(--surface);border:1px solid var(--line);border-radius:7px;padding:8px 11px}
input[type=search]{flex:1 1 180px;min-width:150px}
select{cursor:pointer}
input:focus-visible,select:focus-visible,button:focus-visible,th:focus-visible{
  outline:2px solid var(--accent);outline-offset:2px}
.chk{display:inline-flex;align-items:center;gap:6px;font-size:13.5px;color:var(--muted);
  background:var(--surface);border:1px solid var(--line);border-radius:7px;
  padding:8px 10px;cursor:pointer;user-select:none}
.chk input{accent-color:var(--accent);margin:0;cursor:pointer}
.chk:has(input:checked){color:var(--accent-ink);border-color:var(--accent);
  background:var(--accent-soft);font-weight:500}
.rng{display:inline-flex;align-items:center;gap:8px;background:var(--surface);
  border:1px solid var(--line);border-radius:7px;padding:6px 10px;font-size:13.5px;color:var(--muted)}
.rng input{accent-color:var(--accent);width:86px}
.rng b{font-family:"IBM Plex Mono",monospace;color:var(--ink);font-weight:600;
  font-variant-numeric:tabular-nums;min-width:52px;text-align:right}
.count{margin-left:auto;font-size:13px;color:var(--muted);white-space:nowrap}
.count b{color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums}
button.reset{font:13.5px "IBM Plex Sans",sans-serif;background:none;border:1px solid var(--line);
  color:var(--muted);border-radius:7px;padding:8px 11px;cursor:pointer}
button.reset:hover{color:var(--ink);border-color:var(--muted)}

/* ---------- table ---------- */
/* No overflow container at desktop widths: an overflow box would become the
   containing scrollport for the sticky header, pinning it inside the table
   instead of below the filter bar. Narrow screens trade sticky for scroll. */
.scroll{background:var(--surface);border-top:1px solid var(--line);margin-top:6px}
table{border-collapse:collapse;width:100%;min-width:1020px}
thead th{position:sticky;top:var(--barh,56px);z-index:10;background:var(--surface-2);
  font-size:10.5px;letter-spacing:.085em;text-transform:uppercase;color:var(--faint);
  font-weight:600;text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);
  cursor:pointer;white-space:nowrap;user-select:none}
thead th:hover{color:var(--ink)}
thead th[aria-sort]{color:var(--accent)}
thead th .ar{opacity:.55;font-size:9px;margin-left:3px}
tbody td{padding:9px 12px;border-bottom:1px solid var(--line-soft);vertical-align:middle}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--surface-2)}
.num{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums;
  font-size:13px;text-align:right;white-space:nowrap}
.rank{color:var(--faint);font-size:12px;width:46px}
.name{min-width:236px;max-width:340px}
.name a{color:var(--ink);text-decoration:none;font-weight:500;line-height:1.3;
  display:block;text-underline-offset:2px}
.name a[href]:hover{text-decoration:underline;color:var(--accent-ink)}
.name .dev{color:var(--faint);font-size:11.5px;margin-top:2px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.gen{display:flex;flex-wrap:wrap;gap:4px;min-width:150px;max-width:220px}
.gen span{font-size:11px;color:var(--muted);background:var(--surface-2);
  border:1px solid var(--line);border-radius:999px;padding:1px 7px;white-space:nowrap}

/* review bar: proportion positive, coloured by Steam's own tier */
.rate{min-width:152px}
.rate .top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.rate .pct{font-family:"IBM Plex Mono",monospace;font-size:13px;font-weight:600;
  font-variant-numeric:tabular-nums}
.rate .desc{font-size:10.5px;color:var(--faint);text-align:right;line-height:1.2}
.rate .track{height:4px;background:var(--track);border-radius:3px;margin-top:5px;overflow:hidden}
.rate .fill{height:100%;border-radius:3px}
.t1{color:var(--b1)} .t2{color:var(--b2)} .t3{color:var(--b3)}
.t4{color:var(--b4)} .t5{color:var(--b5)}
.f1{background:var(--b1)} .f2{background:var(--b2)} .f3{background:var(--b3)}
.f4{background:var(--b4)} .f5{background:var(--b5)}
.mc{display:inline-block;font-family:"IBM Plex Mono",monospace;font-size:12px;font-weight:600;
  border-radius:5px;padding:2px 7px;color:var(--chip-ink);font-variant-numeric:tabular-nums}
.mode{font-size:11px;color:var(--muted);white-space:nowrap;letter-spacing:.02em}
.dash{color:var(--faint)}
.tag{display:inline-block;font-size:10px;font-weight:600;letter-spacing:.04em;
  text-transform:uppercase;border-radius:4px;padding:1px 5px;margin-left:6px;
  vertical-align:2px;white-space:nowrap;border:1px solid var(--line);
  background:var(--surface-2);color:var(--muted)}
.tag.gone{color:var(--b4);border-color:var(--b4);background:transparent}
.empty{padding:52px 20px;text-align:center;color:var(--muted)}
.foot{display:block;margin-top:18px;font-size:12.5px;color:var(--faint);line-height:1.65;max-width:96ch}
.foot code{font-family:"IBM Plex Mono",monospace;font-size:11.5px}
@media (max-width:1080px){ .scroll{overflow-x:auto} thead th{top:0} }
@media (max-width:640px){ .wrap{padding:20px 12px 60px} .bar{position:static} }
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>

<div class="wrap">
  <div class="mast">
    <div>
      <h1>What should I <em>actually</em> play?</h1>
      <p class="sub">__COUNT__ games in the Epic library, pulled with <code>legendary</code> and scored
      against live Steam review data. Ranked by <b>confidence score</b> &mdash; the Wilson lower bound,
      which discounts a perfect rating built on a handful of reviews. Click any column to re-sort.</p>
    </div>
  </div>

  <div class="stats">__STATS__</div>

  <div class="bar">
    <div class="row1">
      <input type="search" id="q" placeholder="Search title, genre or developer&hellip;" aria-label="Search">
      <select id="genre" aria-label="Filter by genre">__GENRES__</select>
      <select id="status" aria-label="Filter by Steam listing">
        <option value="">Any Steam status</option>
        <option value="listed">On Steam now</option>
        <option value="delisted">Delisted from Steam</option>
        <option value="not-on-steam">Never on Steam</option>
        <option value="duplicate">Duplicate entry</option>
        <option value="unreleased">Not released yet</option>
        <option value="unknown">Unidentified</option>
      </select>
      <select id="sort" aria-label="Sort by">
        <option value="sort_score|-1">Confidence, high first</option>
        <option value="title|1">Name, A to Z</option>
        <option value="title|-1">Name, Z to A</option>
        <option value="rating|-1">Steam rating, high first</option>
        <option value="reviews|-1">Reviews, most first</option>
        <option value="metacritic|-1">Metacritic, high first</option>
        <option value="year|-1">Year, newest first</option>
        <option value="year|1">Year, oldest first</option>
      </select>
      <label class="rng">min reviews <input type="range" id="minr" min="0" max="5" step="1" value="1" aria-label="Minimum review count"><b id="minrv">100</b></label>
      <label class="chk"><input type="checkbox" id="sp"> Solo</label>
      <label class="chk"><input type="checkbox" id="co"> Co-op</label>
      <label class="chk"><input type="checkbox" id="pad"> Controller</label>
      <button class="reset" id="reset" type="button">Reset</button>
      <span class="count"><b id="shown">0</b> shown</span>
    </div>
  </div>

  <div class="scroll">
    <table>
      <thead><tr>
        <th data-k="rank" style="cursor:default">#</th>
        <th data-k="title">Game <span class="ar"></span></th>
        <th data-k="sort_score" data-num="1">Confidence <span class="ar"></span></th>
        <th data-k="rating" data-num="1">Steam rating <span class="ar"></span></th>
        <th data-k="reviews" data-num="1">Reviews <span class="ar"></span></th>
        <th data-k="genres">Genre <span class="ar"></span></th>
        <th data-k="metacritic" data-num="1">MC <span class="ar"></span></th>
__HOURS_TH__        <th data-k="year" data-num="1">Year <span class="ar"></span></th>
        <th data-k="mode">Modes <span class="ar"></span></th>
      </tr></thead>
      <tbody id="body"></tbody>
    </table>
  </div>
  <div id="none" class="empty" hidden>Nothing matches those filters.</div>

  <p class="foot">__FOOTER__</p>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
  "use strict";
  var GAMES = JSON.parse(document.getElementById("data").textContent);
  var STEPS = [0, 100, 500, 2000, 10000, 50000];
  var HAS_HOURS = __HAS_HOURS__;
  var ENT = {"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;"};
  // Why a row has no Steam numbers, in the row itself rather than a footnote.
  var TAG = {delisted:"Delisted", "not-on-steam":"Never on Steam",
             duplicate:"Duplicate", unreleased:"Unreleased", unknown:"No match"};

  GAMES.forEach(function(g){
    var d = (g.release_date || "").match(/(19|20)\d{2}/);
    g.year = d ? +d[0] : null;
    g.mode = [g.singleplayer ? "Solo" : "", g.coop ? "Co-op" : "", g.multiplayer ? "MP" : ""]
             .filter(Boolean).join(" · ");
    g._hay = ((g.title || "") + " " + (g.genres || []).join(" ") + " " +
              (g.developer || "") + " " + (g.publisher || "")).toLowerCase();
    // Steam's own review tiers, collapsed to five colour bands.
    var r = g.rating;
    g.band = r == null ? 0 : r >= 94 ? 1 : r >= 85 ? 2 : r >= 70 ? 3 : r >= 40 ? 4 : 5;
  });

  var sortKey = "sort_score", sortDir = -1;
  var $ = function(id){ return document.getElementById(id); };
  var body = $("body");

  function mcColour(s){ return s >= 75 ? "var(--b1)" : s >= 50 ? "var(--b3)" : "var(--b5)"; }
  function esc(s){
    return String(s == null ? "" : s).replace(/[&<>"]/g, function(c){ return ENT[c]; });
  }
  function nfmt(n){ return n == null ? "" : n.toLocaleString("en-US"); }

  function passes(g){
    var q = $("q").value.trim().toLowerCase();
    if (q && g._hay.indexOf(q) === -1) return false;
    var gen = $("genre").value;
    if (gen && (g.genres || []).indexOf(gen) === -1) return false;
    var st = $("status").value;
    if (st && (g.steam_status || "unknown") !== st) return false;
    // The review floor is a browsing floor, and it would hide every row that has
    // no reviews to count - exactly the rows someone picking "never on Steam" or
    // "duplicate entry" asked to see. Asking for a status by name lifts it for
    // those rows only; rows that do have reviews are still filtered normally.
    if ((g.reviews || 0) < STEPS[+$("minr").value] && !(st && !g.reviews)) return false;
    if ($("sp").checked && !g.singleplayer) return false;
    if ($("co").checked && !g.coop) return false;
    if ($("pad").checked && !g.controller) return false;
    return true;
  }

  function render(){
    var rows = GAMES.filter(passes);
    // sortDir: 1 ascending, -1 descending - the same sense for text and numbers.
    rows.sort(function(a, b){
      if (sortKey === "title") return a.title.localeCompare(b.title) * sortDir;
      var x = a[sortKey], y = b[sortKey];
      // Genre and Modes hold lists and strings, not numbers.
      if (Array.isArray(x) || Array.isArray(y) ||
          typeof x === "string" || typeof y === "string") {
        var sx = Array.isArray(x) ? x.join(", ") : (x || "");
        var sy = Array.isArray(y) ? y.join(", ") : (y || "");
        if (!sx && !sy) return 0;
        if (!sx) return 1;
        if (!sy) return -1;
        return sx.localeCompare(sy) * sortDir;
      }
      if (x == null && y == null) return 0;
      if (x == null) return 1;              // unknowns always sink to the bottom
      if (y == null) return -1;
      return (x - y) * sortDir;
    });

    body.innerHTML = rows.map(function(g, i){
      var b = g.band;
      var why = g.steam_status === "delisted"
        ? "pulled from sale on Steam - the reviews it earned still count"
        : g.steam_status === "duplicate"
        ? "same Steam page as " + esc(g.duplicate_of || "another entry")
        : g.steam_status === "not-on-steam" ? "never sold on Steam"
        : g.steam_status === "unreleased" ? "not released yet"
        : "no Steam listing found";
      var rate = g.rating == null
        ? '<span class="dash">' + why + '</span>'
        : '<div class="top"><span class="pct t' + b + '">' + g.rating.toFixed(2) + '%</span>' +
          '<span class="desc">' + esc(g.review_desc) + '</span></div>' +
          '<div class="track"><div class="fill f' + b + '" style="width:' + g.rating + '%"></div></div>';
      var name = g.steam_url
        ? '<a href="' + g.steam_url + '" target="_blank" rel="noopener">' + esc(g.title) + '</a>'
        : '<a>' + esc(g.title) + '</a>';
      var tag = TAG[g.steam_status];
      if (tag) {
        // Say where a match came from: a title Steam's own search cannot return was
        // identified through PCGamingWiki, which is a weaker source than a store hit
        // and can pick the wrong game where a name is reused across releases.
        var tip = why + (g.steam_source === "pcgw"
          ? " (matched as " + esc(g.matched_name) + " via PCGamingWiki)" : "");
        name += '<span class="tag' + (g.steam_status === "delisted" ? " gone" : "") +
                '" title="' + tip + '">' + tag + '</span>';
      }
      return '<tr>' +
        '<td class="num rank">' + (i + 1) + '</td>' +
        '<td class="name">' + name +
          (g.developer ? '<div class="dev">' + esc(g.developer) + '</div>' : '') + '</td>' +
        '<td class="num"><b class="t' + b + '">' +
          (g.sort_score == null ? '<span class="dash">&mdash;</span>' : g.sort_score.toFixed(2)) +
          '</b></td>' +
        '<td class="rate">' + rate + '</td>' +
        '<td class="num">' + (g.reviews ? nfmt(g.reviews) : '<span class="dash">&mdash;</span>') + '</td>' +
        '<td><div class="gen">' + (g.genres || []).map(function(x){
            return '<span>' + esc(x) + '</span>'; }).join('') + '</div></td>' +
        '<td class="num">' + (g.metacritic
            ? '<span class="mc" style="background:' + mcColour(g.metacritic) + '">' + g.metacritic + '</span>'
            : '<span class="dash">&mdash;</span>') + '</td>' +
        (HAS_HOURS ? '<td class="num">' +
          (g.hltb_main ? g.hltb_main + 'h' : '<span class="dash">&mdash;</span>') + '</td>' : '') +
        '<td class="num">' + (g.year || '<span class="dash">&mdash;</span>') + '</td>' +
        '<td class="mode">' + esc(g.mode) + '</td>' +
      '</tr>';
    }).join("");

    $("shown").textContent = rows.length;
    $("none").hidden = rows.length > 0;
  }

  function applySort(k, dir){
    sortKey = k;
    sortDir = dir;
    document.querySelectorAll("thead th").forEach(function(o){
      o.removeAttribute("aria-sort");
      var a = o.querySelector(".ar"); if (a) a.textContent = "";
    });
    var th = document.querySelector('thead th[data-k="' + k + '"]');
    if (th) {
      th.setAttribute("aria-sort", dir === 1 ? "ascending" : "descending");
      var ar = th.querySelector(".ar");
      if (ar) ar.textContent = dir === 1 ? "▲" : "▼";
    }
    // Keep the dropdown showing the live state; blank when the table is sorted
    // by a column the dropdown has no entry for.
    var sel = $("sort"), want = k + "|" + dir, known = false;
    for (var i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === want) { known = true; break; }
    }
    sel.value = known ? want : "";
    render();
  }

  document.querySelectorAll("thead th[data-k]").forEach(function(th){
    var k = th.dataset.k;
    if (k === "rank") return;
    th.tabIndex = 0;
    function go(){
      // Re-clicking a column flips it; a fresh column opens the way people
      // expect - names A to Z, numbers highest first.
      applySort(k, sortKey === k ? -sortDir : (th.dataset.num ? -1 : 1));
    }
    th.addEventListener("click", go);
    th.addEventListener("keydown", function(e){
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); }
    });
  });

  $("sort").addEventListener("change", function(){
    var p = this.value.split("|");
    if (p.length === 2) applySort(p[0], +p[1]);
  });

  ["q", "genre", "status", "sp", "co", "pad"].forEach(function(id){
    $(id).addEventListener("input", render);
  });
  $("minr").addEventListener("input", function(){
    $("minrv").textContent = nfmt(STEPS[+this.value]);
    render();
  });
  $("reset").addEventListener("click", function(){
    $("q").value = ""; $("genre").value = ""; $("status").value = "";
    $("minr").value = 1;
    $("minrv").textContent = "100";
    $("sp").checked = $("co").checked = $("pad").checked = false;
    render();
  });

  // The filter bar wraps to a second row at narrow widths and grows again when
  // the webfont swaps in, so the sticky header's offset has to track its real
  // height rather than be measured once.
  var bar = document.querySelector(".bar");
  function syncBar(){
    document.documentElement.style.setProperty(
      "--barh", Math.ceil(bar.getBoundingClientRect().height) + "px");
  }
  if (window.ResizeObserver) new ResizeObserver(syncBar).observe(bar);
  window.addEventListener("resize", syncBar);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(syncBar);
  syncBar();

  applySort("sort_score", -1);
})();
</script>
"""


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return 0.0
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def build():
    use_utf8_stdout()
    src = os.path.join(OUT, "games.json")
    if not os.path.exists(src):
        raise SystemExit("out/games.json is missing - run epic_steam.py first.")
    with open(src, encoding="utf-8") as fh:
        games = json.load(fh)

    verdicts = Counter(g.get("steam_status") or "unknown" for g in games)
    rated = [g for g in games if g.get("reviews")]
    solid = [g for g in rated if g["reviews"] >= 500]
    great = [g for g in solid if (g.get("sort_score") or 0) >= 90]
    hours = [g["hltb_main"] for g in games if g.get("hltb_main")]

    tiles = [
        ("Games in library", str(len(games)), "%d found on Steam" % len(rated)),
        ("Rated 90%+", str(len(great)), "confidence score, 500+ reviews"),
        ("Median rating", "%.1f%%" % _median([g["rating"] for g in rated]),
         "across %d rated titles" % len(rated)),
    ]
    if hours:
        tiles.append(("Short enough", str(sum(1 for h in hours if h <= 12)),
                      "12 hours or less to finish"))
    tiles.append(("Delisted on Steam", str(verdicts["delisted"]),
                  "pulled from sale, still yours"))

    stats = "".join(
        '<div class="tile"><div class="k">%s</div><div class="v">%s</div>'
        '<div class="n">%s</div></div>' % t for t in tiles)

    genres = sorted({x for g in games for x in (g.get("genres") or [])})
    opts = '<option value="">All genres</option>' + "".join(
        '<option value="%s">%s</option>' % (g, g) for g in genres)

    stamp = datetime.date.today().strftime("%d %B %Y")
    playtime = ("Playtime is HowLongToBeat&rsquo;s main-story figure. " if hours else
                "Playtime is not shown: HowLongToBeat now requires a browser session "
                "fingerprint and refuses direct requests. ")
    footer = (
        "Steam ratings, review counts, genres, Metacritic scores and player modes come from "
        "Valve&rsquo;s own <code>appreviews</code> and <code>appdetails</code> endpoints, fetched "
        "%s. %sSteam&rsquo;s search only answers for games it currently sells, so anything it "
        "cannot find is looked up on PCGamingWiki instead: %d titles here were <b>delisted</b> "
        "&mdash; pulled from sale but still carrying their reviews, which are scored and ranked "
        "like any other &mdash; %d were <b>never on Steam</b>, %d are <b>duplicate</b> Epic "
        "entries for a game already in the list, and %d could not be identified either way. "
        "Confidence score is the Wilson 95%% lower bound on the share of positive reviews: it "
        "starts at the raw rating and pulls downward the fewer reviews there are, so 100%% from "
        "14 reviews lands well below 98%% from 300,000."
        % (stamp, playtime, verdicts["delisted"], verdicts["not-on-steam"],
           verdicts["duplicate"], verdicts["unknown"]))

    hours_th = ('        <th data-k="hltb_main" data-num="1">Hours <span class="ar"></span></th>\n'
                if hours else "")

    html = (TEMPLATE
            .replace("__COUNT__", str(len(games)))
            .replace("__STATS__", stats)
            .replace("__GENRES__", opts)
            .replace("__HOURS_TH__", hours_th)
            .replace("__HAS_HOURS__", "true" if hours else "false")
            .replace("__FOOTER__", footer)
            .replace("__DATA__", json.dumps(games, ensure_ascii=False).replace("</", "<\\/")))

    path = os.path.join(OUT, "report.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("wrote %s  (%.0f KB, %d games, %d rated, %d genres)"
          % (path, len(html) / 1024.0, len(games), len(rated), len(genres)))
    # The headline answer, for anyone who runs this from run.bat and reads the
    # console rather than opening the page.
    print("      %d delisted on Steam, %d never on Steam, %d duplicate entries, "
          "%d unidentified" % (verdicts["delisted"], verdicts["not-on-steam"],
                               verdicts["duplicate"], verdicts["unknown"]))


if __name__ == "__main__":
    build()
