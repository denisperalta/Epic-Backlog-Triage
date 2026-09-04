(function(){
  "use strict";
  var GAMES = JSON.parse(document.getElementById("data").textContent);
  var I18N = __I18N__;
  var TAG = __TAG_MAP__;
  var REVIEW = __REVIEW_MAP__;
  var N = __NUMS__;
  var TAGS = __TAGS__;
  // Whole-library counts, one per status - they describe the library, not the view,
  // so they are counted once in Python and never recomputed from the filtered rows.
  var STATUS_N = __STATUS_N__;
  var STEPS = [0, 100, 500, 2000, 10000, 50000];
  var ENT = {"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;"};
  var LANG = "en", LOC = "en-US", V = {};

  var $ = function(id){ return document.getElementById(id); };
  var body = $("body");
  function each(sel, fn){
    Array.prototype.forEach.call(document.querySelectorAll(sel), fn);
  }
  function esc(s){
    return String(s == null ? "" : s).replace(/[&<>"]/g, function(c){ return ENT[c]; });
  }

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
    $("theme").innerHTML = '<span class="dot"></span>' +
      esc(THEME === "dark" ? t("dark") : t("light"));
  }

  $("theme").addEventListener("click", function(){
    applyTheme(THEME === "dark" ? "light" : "dark");
  });

  /* ---------- language ---------- */

  // A page opened off the disk has no server to negotiate with, so the reader's own
  // ordered preference list is the only thing that says which language to open in.
  // On Windows the browser takes that list from the system's display language.
  function preferred(){
    try {
      var saved = localStorage.getItem("eb.lang");
      if (I18N[saved]) return saved;
    } catch (e) {}
    var want = (navigator.languages && navigator.languages.length)
      ? navigator.languages : [navigator.language || ""];
    for (var i = 0; i < want.length; i++) {
      var tag = String(want[i] || "").toLowerCase();
      if (tag.indexOf("es") === 0) return "es";
      if (tag.indexOf("en") === 0) return "en";
    }
    return "en";
  }

  // A missing string falls back to English rather than leaving a hole in the page.
  function t(k, vars){
    var s = I18N[LANG][k];
    if (s == null) s = I18N.en[k];
    if (s == null) return "";
    return s.replace(/\{(\w+)\}/g, function(whole, name){
      var v = (vars || V)[name];
      return v == null ? whole : v;
    });
  }

  function nfmt(n){ return n == null ? "" : n.toLocaleString(LOC); }
  function dec(n, d){
    return n.toLocaleString(LOC, {minimumFractionDigits:d, maximumFractionDigits:d});
  }
  // Spanish sets the per-cent sign and the unit off from the number; English does not.
  // The gap has to be a hard space: the rating column is narrow enough that an
  // ordinary one drops the sign onto a line of its own.
  function pct(n, d){ return dec(n, d) + (LANG === "es" ? " %" : "%"); }
  function hrs(n){ return nfmt(n) + (LANG === "es" ? " h" : "h"); }
  function ymd(iso){
    // Assembled from its parts: new Date("2026-09-01") is read as UTC midnight, which
    // prints as the day before for every reader west of Greenwich.
    var p = iso.split("-");
    return new Date(+p[0], +p[1] - 1, +p[2])
      .toLocaleDateString(LOC, {day:"numeric", month:"long", year:"numeric"});
  }
  // Steam's own words for these, translated where we have a translation.
  function tagName(g){ return (LANG === "es" && TAG[g]) || g; }
  function reviewName(d){ return (LANG === "es" && REVIEW[d]) || d; }
  function tagFor(s){
    return s === "delisted" ? t("tag_delisted")
         : s === "not-on-steam" ? t("tag_not")
         : s === "duplicate" ? t("tag_dup")
         : s === "unreleased" ? t("tag_unreleased")
         : s === "unknown" ? t("tag_unknown") : "";
  }

  GAMES.forEach(function(g){
    var d = (g.release_date || "").match(/(19|20)\d{2}/);
    g.year = d ? +d[0] : null;
    g._base = ((g.title || "") + " " + (g.tags || []).join(" ") + " " +
               (g.developer || "") + " " + (g.publisher || "")).toLowerCase();
    // Steam's own review tiers, collapsed to five colour bands.
    var r = g.rating;
    g.band = r == null ? 0 : r >= 94 ? 1 : r >= 85 ? 2 : r >= 70 ? 3 : r >= 40 ? 4 : 5;
  });

  // Anything that reads as a sentence has to be rebuilt when the language changes -
  // including the two that are not visibly text: Modes is sorted on its own words,
  // and the search box has to find a tag by the name actually on screen.
  function retranslate(){
    V = {
      n: nfmt(N.count), rated: nfmt(N.rated), great: nfmt(N.great),
      median: pct(N.median, 1), short: nfmt(N.short), delisted: nfmt(N.delisted),
      notOnSteam: nfmt(N.notOnSteam), duplicate: nfmt(N.duplicate),
      unknown: nfmt(N.unknown), date: ymd(N.stamp),
      playtime: N.hasHours ? t("foot_hours", {}) : t("foot_nohours", {})
    };
    GAMES.forEach(function(g){
      g.mode = [g.singleplayer ? t("mode_solo") : "", g.coop ? t("mode_coop") : "",
                g.multiplayer ? t("mode_mp") : ""].filter(Boolean).join(" · ");
      g._hay = g._base + " " + (g.tags || []).map(tagName).join(" ").toLowerCase();
    });
  }

  function tiles(){
    var out = [[t("tile_total_k"), V.n, t("tile_total_n")],
               [t("tile_great_k"), V.great, t("tile_great_n")],
               [t("tile_median_k"), V.median, t("tile_median_n")]];
    if (N.hasHours) out.push([t("tile_short_k"), V.short, t("tile_short_n")]);
    out.push([t("tile_gone_k"), V.delisted, t("tile_gone_n")]);
    $("stats").innerHTML = out.map(function(o){
      return '<div class="tile"><div class="k">' + esc(o[0]) + '</div>' +
             '<div class="v">' + esc(o[1]) + '</div>' +
             '<div class="n">' + esc(o[2]) + '</div></div>';
    }).join("");
  }

  function applyLang(lang){
    LANG = I18N[lang] ? lang : "en";
    LOC = LANG === "es" ? "es-ES" : "en-US";
    document.documentElement.lang = LANG;
    try { localStorage.setItem("eb.lang", LANG); } catch (e) {}
    retranslate();
    each("[data-i18n]", function(o){ o.textContent = t(o.getAttribute("data-i18n")); });
    each("[data-i18n-html]", function(o){ o.innerHTML = t(o.getAttribute("data-i18n-html")); });
    each("[data-i18n-ph]", function(o){ o.placeholder = t(o.getAttribute("data-i18n-ph")); });
    each("[data-i18n-al]", function(o){
      o.setAttribute("aria-label", t(o.getAttribute("data-i18n-al")));
    });
    // The chips and the three control groups are built from I18N, so they are
    // rebuilt rather than retranslated in place. Only the labels change: the tag
    // buttons keep their English values, so the filter in passes() goes on
    // comparing against what Steam actually sent.
    chips();
    statusList();
    modeChips();
    tagChips();
    $("railmeta").textContent = t("railmeta", {n: nfmt(N.count), steam: nfmt(N.rated)});
    each(".lang button", function(o){
      o.setAttribute("aria-pressed", o.getAttribute("data-lang") === LANG ? "true" : "false");
    });
    $("minrv").textContent = nfmt(STEPS[+$("minr").value]);
    tiles();
    $("foot").innerHTML = t("foot");
    render();
    applyTheme(THEME);
  }

  var sortKey = "sort_score", sortDir = -1;

  // The tags being filtered on, held as the English names Steam sent - the same
  // values the options carry, so the filter survives a language switch.
  var ACTIVE = [];

  function chips(){
    var box = $("chips");
    box.hidden = !ACTIVE.length;
    box.innerHTML = ACTIVE.map(function(tag){
      var name = esc(tagName(tag));
      return '<span class="chip">' + name +
             '<button type="button" data-tag="' + esc(tag) + '" aria-label="' +
             esc(t("al_chip_remove", {tag: tagName(tag)})) + '">×</button></span>';
    }).join("") + (ACTIVE.length > 1
      ? '<button type="button" class="clear" data-clear="1">' + esc(t("chip_clear")) +
        '</button>'
      : "");
  }

  // The status rows and the mode chips are single-choice and multi-choice
  // respectively, so they are held as state rather than read back off the DOM.
  var STATUS = "";
  var MODES = {solo: false, coop: false, pad: false};

  // Both lists name their strings at the call, not through a key held in a
  // variable: the label has to be readable as a t("...") call to be seen as used.
  function statusList(){
    var rows = [["", t("st_any")], ["listed", t("st_listed")],
                ["delisted", t("st_delisted")], ["not-on-steam", t("st_not")],
                ["duplicate", t("st_dup")], ["unreleased", t("st_unreleased")],
                ["unknown", t("st_unknown")]];
    $("statuslist").innerHTML = rows.map(function(r){
      return '<button type="button" data-st="' + esc(r[0]) + '" aria-pressed="' +
             (STATUS === r[0] ? "true" : "false") + '"><span class="dot"></span>' +
             '<span>' + esc(r[1]) + '</span>' +
             '<span class="n">' + esc(nfmt(STATUS_N[r[0]] || 0)) + '</span></button>';
    }).join("");
  }

  function modeChips(){
    var rows = [["solo", t("mode_solo")], ["coop", t("mode_coop")], ["pad", t("chk_pad")]];
    $("modechips").innerHTML = rows.map(function(r){
      return '<button type="button" data-mode="' + r[0] + '" aria-pressed="' +
             (MODES[r[0]] ? "true" : "false") + '">' + esc(r[1]) + '</button>';
    }).join("");
  }

  // Offered tags are the ones not already picked; picking one moves it to a chip.
  function tagChips(){
    $("tagchips").innerHTML = TAGS.map(function(r){
      if (ACTIVE.indexOf(r[0]) !== -1) return "";
      return '<button type="button" data-tag="' + esc(r[0]) + '" aria-pressed="false">' +
             esc(tagName(r[0])) + '<span class="n">' + esc(nfmt(r[1])) + '</span></button>';
    }).join("");
  }

  function drop(tag){
    var i = ACTIVE.indexOf(tag);
    if (i === -1) return;
    ACTIVE.splice(i, 1);
    tagChips();
    chips();
    render();
  }

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

  function render(){
    var rows = GAMES.filter(passes);
    // sortDir: 1 ascending, -1 descending - the same sense for text and numbers.
    rows.sort(function(a, b){
      if (sortKey === "title") return a.title.localeCompare(b.title) * sortDir;
      var x = a[sortKey], y = b[sortKey];
      // Tags and Modes hold lists and strings, not numbers.
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
      var why = g.steam_status === "delisted" ? t("why_delisted")
        : g.steam_status === "duplicate"
        ? t("why_dup", {name: esc(g.duplicate_of) || t("why_dup_any")})
        : g.steam_status === "not-on-steam" ? t("why_not")
        : g.steam_status === "unreleased" ? t("why_unreleased")
        : t("why_unknown");
      var rate = g.rating == null
        ? '<span class="dash">' + why + '</span>'
        : '<div class="top"><span class="pct t' + b + '">' + pct(g.rating, 2) + '</span>' +
          '<span class="desc">' + esc(reviewName(g.review_desc)) + '</span></div>' +
          '<div class="track"><div class="fill f' + b + '" style="width:' + g.rating + '%"></div></div>';
      var name = g.steam_url
        ? '<a href="' + g.steam_url + '" target="_blank" rel="noopener">' + esc(g.title) + '</a>'
        : '<a>' + esc(g.title) + '</a>';
      var tag = tagFor(g.steam_status);
      if (tag) {
        // Say where a match came from: a title Steam's own search cannot return was
        // identified through PCGamingWiki, which is a weaker source than a store hit
        // and can pick the wrong game where a name is reused across releases.
        var tip = why + (g.steam_source === "pcgw"
          ? t("tip_pcgw", {name: esc(g.matched_name)}) : "");
        name += '<span class="tag' + (g.steam_status === "delisted" ? " gone" : "") +
                '" title="' + tip + '">' + esc(tag) + '</span>';
      }
      return '<tr>' +
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
        // A year is a label, not a quantity: it must not pick up a thousands separator.
        '<td class="num">' + (g.year || '<span class="dash">&mdash;</span>') + '</td>' +
        '<td class="mode">' + esc(g.mode) + '</td>' +
      '</tr>';
    }).join("");

    $("count").innerHTML = t("count", {n: nfmt(rows.length)});
    $("none").hidden = rows.length > 0;
  }

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
    render();
  }

  each("thead th[data-k]", function(th){
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

  $("q").addEventListener("input", render);
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
  $("chips").addEventListener("click", function(e){
    var b = e.target.closest ? e.target.closest("button") : null;
    if (!b) return;
    if (b.dataset.clear) {
      ACTIVE.splice(0);
      tagChips();
      chips();
      render();
    } else if (b.dataset.tag) {
      drop(b.dataset.tag);
    }
  });
  $("minr").addEventListener("input", function(){
    $("minrv").textContent = nfmt(STEPS[+this.value]);
    render();
  });
  $("reset").addEventListener("click", function(){
    $("q").value = "";
    ACTIVE.splice(0);
    STATUS = "";
    MODES = {solo: false, coop: false, pad: false};
    $("minr").value = 1;
    $("minrv").textContent = nfmt(STEPS[1]);
    chips();
    statusList();
    modeChips();
    tagChips();
    render();
  });
  each(".lang button", function(b){
    b.addEventListener("click", function(){ applyLang(b.getAttribute("data-lang")); });
  });

  applyTheme(savedTheme());
  applyLang(preferred());
  applySort("sort_score", -1);
})();
