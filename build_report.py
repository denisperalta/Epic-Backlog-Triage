"""Render out/games.json into a single self-contained HTML report."""
import json, os, datetime
from collections import Counter

from steamlib import use_utf8_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

EN = {
    "title": "Epic Backlog Triage",
    "h1": "What should I <em>actually</em> play?",
    "sub": "{n} games in the Epic library, pulled with <code>legendary</code> and scored "
           "against live Steam review data. Ranked by <b>confidence score</b> &mdash; the "
           "Wilson lower bound, which discounts a perfect rating built on a handful of "
           "reviews. Click any column to re-sort.",
    "al_lang": "Language",
    "lang_en": "EN",
    "lang_es": "ES",

    "tile_total_k": "Games in library",
    "tile_total_n": "{rated} found on Steam",
    "tile_great_k": "Rated 90%+",
    "tile_great_n": "confidence score, 500+ reviews",
    "tile_median_k": "Median rating",
    "tile_median_n": "across {rated} rated titles",
    "tile_short_k": "Short enough",
    "tile_short_n": "12 hours or less to finish",
    "tile_gone_k": "Delisted on Steam",
    "tile_gone_n": "pulled from sale, still yours",

    "ph_search": "Search title, tag or developer\u2026",
    "al_search": "Search",
    "al_tags": "Filter by tag",
    "opt_tags": "All tags",
    "al_status": "Filter by Steam listing",
    "st_any": "Any Steam status",
    "st_listed": "On Steam now",
    "st_delisted": "Delisted from Steam",
    "st_not": "Never on Steam",
    "st_dup": "Duplicate entry",
    "st_unreleased": "Not released yet",
    "st_unknown": "Unidentified",
    "al_sort": "Sort by",
    "so_conf": "Confidence, high first",
    "so_az": "Name, A to Z",
    "so_za": "Name, Z to A",
    "so_rating": "Steam rating, high first",
    "so_reviews": "Reviews, most first",
    "so_new": "Year, newest first",
    "so_old": "Year, oldest first",
    "lbl_minr": "min reviews",
    "al_minr": "Minimum review count",
    "chk_pad": "Controller",
    "btn_reset": "Reset",
    "count": "<b>{n}</b> shown",

    "th_game": "Game",
    "th_conf": "Confidence",
    "th_rating": "Steam rating",
    "th_reviews": "Reviews",
    "th_tags": "Tags",
    "th_hours": "Hours",
    "th_year": "Year",
    "th_modes": "Modes",
    "empty": "Nothing matches those filters.",

    "tag_delisted": "Delisted",
    "tag_not": "Never on Steam",
    "tag_dup": "Duplicate",
    "tag_unreleased": "Unreleased",
    "tag_unknown": "No match",
    "why_delisted": "pulled from sale on Steam - the reviews it earned still count",
    "why_dup": "same Steam page as {name}",
    "why_dup_any": "another entry",
    "why_not": "never sold on Steam",
    "why_unreleased": "not released yet",
    "why_unknown": "no Steam listing found",
    "tip_pcgw": " (matched as {name} via PCGamingWiki)",
    "mode_solo": "Solo",
    "mode_coop": "Co-op",
    "mode_mp": "MP",

    "foot_hours": "Playtime is HowLongToBeat&rsquo;s main-story figure. ",
    "foot_nohours": "Playtime is not shown: HowLongToBeat now requires a browser session "
                    "fingerprint and refuses direct requests. ",
    "foot": "Steam ratings, review counts, tags and player modes come "
            "from Valve&rsquo;s own <code>SearchSuggestions</code> and <code>GetItems</code> "
            "endpoints on <code>api.steampowered.com</code>, fetched {date}. "
            "{playtime}Steam&rsquo;s search only answers for games "
            "it currently sells, so anything it cannot find is looked up on PCGamingWiki "
            "instead: {delisted} titles here were <b>delisted</b> &mdash; pulled from sale but "
            "still carrying their reviews, which are scored and ranked like any other &mdash; "
            "{notOnSteam} were <b>never on Steam</b>, {duplicate} are <b>duplicate</b> Epic "
            "entries for a game already in the list, and {unknown} could not be identified "
            "either way. Confidence score is the Wilson 95% lower bound on the share of "
            "positive reviews: it starts at the raw rating and pulls downward the fewer "
            "reviews there are, so 100% from 14 reviews lands well below 98% from 300,000.",
}

ES = {
    "title": "Triaje de la biblioteca de Epic",
    "h1": "\u00bfA qu\u00e9 deber\u00eda jugar <em>de verdad</em>?",
    "sub": "{n} juegos de la biblioteca de Epic, obtenidos con <code>legendary</code> y "
           "puntuados con los datos de rese\u00f1as de Steam en vivo. Ordenados por "
           "<b>puntuaci\u00f3n de confianza</b> &mdash; el l\u00edmite inferior de Wilson, "
           "que penaliza una valoraci\u00f3n perfecta construida sobre un pu\u00f1ado de "
           "rese\u00f1as. Pulsa cualquier columna para reordenar.",
    "al_lang": "Idioma",
    "lang_en": "EN",
    "lang_es": "ES",

    "tile_total_k": "Juegos en la biblioteca",
    "tile_total_n": "{rated} encontrados en Steam",
    "tile_great_k": "Con un 90 % o m\u00e1s",
    "tile_great_n": "de confianza, con 500 rese\u00f1as o m\u00e1s",
    "tile_median_k": "Valoraci\u00f3n mediana",
    "tile_median_n": "sobre {rated} t\u00edtulos valorados",
    "tile_short_k": "Lo bastante cortos",
    "tile_short_n": "12 horas o menos para terminarlos",
    "tile_gone_k": "Retirados de Steam",
    "tile_gone_n": "ya no se venden, y siguen siendo tuyos",

    "ph_search": "Busca por t\u00edtulo, etiqueta o desarrollador\u2026",
    "al_search": "Buscar",
    "al_tags": "Filtrar por etiqueta",
    "opt_tags": "Todas las etiquetas",
    "al_status": "Filtrar por estado en Steam",
    "st_any": "Cualquier estado en Steam",
    "st_listed": "Ahora en Steam",
    "st_delisted": "Retirado de Steam",
    "st_not": "Nunca estuvo en Steam",
    "st_dup": "Entrada duplicada",
    "st_unreleased": "A\u00fan sin lanzar",
    "st_unknown": "Sin identificar",
    "al_sort": "Ordenar por",
    "so_conf": "Confianza, de mayor a menor",
    "so_az": "Nombre, de la A a la Z",
    "so_za": "Nombre, de la Z a la A",
    "so_rating": "Valoraci\u00f3n en Steam, de mayor a menor",
    "so_reviews": "Rese\u00f1as, de m\u00e1s a menos",
    "so_new": "A\u00f1o, del m\u00e1s reciente",
    "so_old": "A\u00f1o, del m\u00e1s antiguo",
    "lbl_minr": "rese\u00f1as m\u00edn.",
    "al_minr": "N\u00famero m\u00ednimo de rese\u00f1as",
    "chk_pad": "Mando",
    "btn_reset": "Restablecer",
    "count": "<b>{n}</b> a la vista",

    "th_game": "Juego",
    "th_conf": "Confianza",
    "th_rating": "Valoraci\u00f3n",
    "th_reviews": "Rese\u00f1as",
    "th_tags": "Etiquetas",
    "th_hours": "Horas",
    "th_year": "A\u00f1o",
    "th_modes": "Modos",
    "empty": "Nada coincide con esos filtros.",

    "tag_delisted": "Retirado",
    "tag_not": "Nunca en Steam",
    "tag_dup": "Duplicado",
    "tag_unreleased": "Sin lanzar",
    "tag_unknown": "Sin coincidencia",
    "why_delisted": "retirado de la venta en Steam; las rese\u00f1as que consigui\u00f3 "
                    "siguen contando",
    "why_dup": "misma p\u00e1gina de Steam que {name}",
    "why_dup_any": "otra entrada",
    "why_not": "nunca se vendi\u00f3 en Steam",
    "why_unreleased": "a\u00fan sin lanzar",
    "why_unknown": "no se encontr\u00f3 ninguna ficha en Steam",
    "tip_pcgw": " (identificado como {name} mediante PCGamingWiki)",
    "mode_solo": "Un jugador",
    "mode_coop": "Cooperativo",
    "mode_mp": "Multi",

    "foot_hours": "La duraci\u00f3n es la de la historia principal seg\u00fan HowLongToBeat. ",
    "foot_nohours": "La duraci\u00f3n no se muestra: HowLongToBeat ahora exige la huella de "
                    "una sesi\u00f3n de navegador y rechaza las peticiones directas. ",
    "foot": "Las valoraciones, el n\u00famero de rese\u00f1as, las etiquetas y los modos de "
            "juego vienen de los propios endpoints <code>SearchSuggestions</code> y "
            "<code>GetItems</code> de Valve en <code>api.steampowered.com</code>, "
            "consultados el {date}. {playtime}La b\u00fasqueda de Steam solo responde "
            "por los juegos que "
            "vende ahora mismo, as\u00ed que lo que no encuentra se busca en PCGamingWiki: "
            "{delisted} t\u00edtulos de esta lista est\u00e1n <b>retirados</b> &mdash; ya no "
            "se venden, pero conservan sus rese\u00f1as, que se punt\u00faan y ordenan como "
            "las de cualquier otro &mdash;, {notOnSteam} <b>nunca estuvieron en Steam</b>, "
            "{duplicate} son entradas <b>duplicadas</b> de Epic de un juego que ya est\u00e1 "
            "en la lista y {unknown} no se pudieron identificar de ninguna de las dos formas. "
            "La puntuaci\u00f3n de confianza es el l\u00edmite inferior de Wilson al 95 % "
            "sobre la proporci\u00f3n de rese\u00f1as positivas: parte de la valoraci\u00f3n "
            "bruta y tira hacia abajo cuantas menos rese\u00f1as hay, de modo que un 100 % con "
            "14 rese\u00f1as queda muy por debajo de un 98 % con 300.000.",
}

I18N = {"en": EN, "es": ES}

# Steam hands over tags and review tiers as English prose, so the Spanish page
# needs its own names for them - Valve's own store wording. Anything absent here
# falls through untranslated rather than vanishing from the page, which is what
# most of the four hundred-odd tags do.
TAG_ES = {
    "Action": "Acci\u00f3n",
    "Adventure": "Aventura",
    "Animation & Modeling": "Animaci\u00f3n y modelado",
    "Audio Production": "Producci\u00f3n de audio",
    "Casual": "Casual",
    "Design & Illustration": "Dise\u00f1o e ilustraci\u00f3n",
    "Documentary": "Documental",
    "Early Access": "Acceso anticipado",
    "Education": "Educaci\u00f3n",
    "Episodic": "Epis\u00f3dico",
    "Free To Play": "Free To Play",
    "Game Development": "Desarrollo de juegos",
    "Gore": "Sangre",
    "Indie": "Indie",
    "Massively Multiplayer": "Multijugador masivo",
    "Movie": "Pel\u00edcula",
    "Nudity": "Desnudez",
    "Photo Editing": "Edici\u00f3n de fotos",
    "RPG": "RPG",
    "Racing": "Carreras",
    "Sexual Content": "Contenido sexual",
    "Short": "Cortometraje",
    "Simulation": "Simulaci\u00f3n",
    "Software Training": "Formaci\u00f3n de software",
    "Sports": "Deportes",
    "Strategy": "Estrategia",
    "Tutorial": "Tutorial",
    "Utilities": "Utilidades",
    "Video Production": "Producci\u00f3n de v\u00eddeo",
    "Violent": "Violencia",
    "Web Publishing": "Publicaci\u00f3n web",
}

REVIEW_ES = {
    "Overwhelmingly Positive": "Extremadamente positivas",
    "Very Positive": "Muy positivas",
    "Positive": "Positivas",
    "Mostly Positive": "Mayormente positivas",
    "Mixed": "Variadas",
    "Mostly Negative": "Mayormente negativas",
    "Negative": "Negativas",
    "Very Negative": "Muy negativas",
    "Overwhelmingly Negative": "Extremadamente negativas",
    "No user reviews": "Sin rese\u00f1as de usuarios",
}

# Only rendered when HowLongToBeat data survived the fetch, so it lives out here
# rather than inside the template - the tests still see it as page markup.
HOURS_TH = ('        <th data-k="hltb_main" data-num="1">'
            '<span data-i18n="th_hours">Hours</span> <span class="ar"></span></th>\n')

TEMPLATE = r"""<title data-i18n="title">Epic Backlog Triage</title>
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
/* ---------- language switcher ---------- */
.lang{display:inline-flex;gap:2px;margin-left:auto;align-self:flex-start;padding:2px;
  background:var(--surface);border:1px solid var(--line);border-radius:8px;
  box-shadow:var(--shadow)}
.lang button{font:600 12px/1 "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.06em;
  background:none;border:0;border-radius:6px;padding:7px 11px;color:var(--muted);cursor:pointer}
.lang button:hover{color:var(--ink)}
.lang button[aria-pressed="true"]{background:var(--accent-soft);color:var(--accent-ink)}

@media (max-width:1080px){ .scroll{overflow-x:auto} thead th{top:0} }
@media (max-width:640px){ .wrap{padding:20px 12px 60px} .bar{position:static} }
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>

<div class="wrap">
  <div class="mast">
    <div>
      <h1 data-i18n-html="h1">What should I <em>actually</em> play?</h1>
      <p class="sub" data-i18n-html="sub">Games in the Epic library, pulled with <code>legendary</code>
      and scored against live Steam review data.</p>
    </div>
    <div class="lang" role="group" data-i18n-al="al_lang" aria-label="Language">
      <button type="button" data-lang="es" data-i18n="lang_es">ES</button>
      <button type="button" data-lang="en" data-i18n="lang_en">EN</button>
    </div>
  </div>

  <div class="stats" id="stats"></div>

  <div class="bar">
    <div class="row1">
      <input type="search" id="q" data-i18n-ph="ph_search" data-i18n-al="al_search"
             placeholder="Search title, tag or developer&hellip;" aria-label="Search">
      <select id="tags" data-i18n-al="al_tags" aria-label="Filter by tag">
        <option value="" data-i18n="opt_tags">All tags</option>__TAGS__
      </select>
      <select id="status" data-i18n-al="al_status" aria-label="Filter by Steam listing">
        <option value="" data-i18n="st_any">Any Steam status</option>
        <option value="listed" data-i18n="st_listed">On Steam now</option>
        <option value="delisted" data-i18n="st_delisted">Delisted from Steam</option>
        <option value="not-on-steam" data-i18n="st_not">Never on Steam</option>
        <option value="duplicate" data-i18n="st_dup">Duplicate entry</option>
        <option value="unreleased" data-i18n="st_unreleased">Not released yet</option>
        <option value="unknown" data-i18n="st_unknown">Unidentified</option>
      </select>
      <select id="sort" data-i18n-al="al_sort" aria-label="Sort by">
        <option value="sort_score|-1" data-i18n="so_conf">Confidence, high first</option>
        <option value="title|1" data-i18n="so_az">Name, A to Z</option>
        <option value="title|-1" data-i18n="so_za">Name, Z to A</option>
        <option value="rating|-1" data-i18n="so_rating">Steam rating, high first</option>
        <option value="reviews|-1" data-i18n="so_reviews">Reviews, most first</option>
        <option value="year|-1" data-i18n="so_new">Year, newest first</option>
        <option value="year|1" data-i18n="so_old">Year, oldest first</option>
      </select>
      <label class="rng"><span data-i18n="lbl_minr">min reviews</span>
        <input type="range" id="minr" min="0" max="5" step="1" value="1"
               data-i18n-al="al_minr" aria-label="Minimum review count"><b id="minrv">100</b></label>
      <label class="chk"><input type="checkbox" id="sp"> <span data-i18n="mode_solo">Solo</span></label>
      <label class="chk"><input type="checkbox" id="co"> <span data-i18n="mode_coop">Co-op</span></label>
      <label class="chk"><input type="checkbox" id="pad"> <span data-i18n="chk_pad">Controller</span></label>
      <button class="reset" id="reset" type="button" data-i18n="btn_reset">Reset</button>
      <span class="count" id="count"><b>0</b> shown</span>
    </div>
  </div>

  <div class="scroll">
    <table>
      <thead><tr>
        <th data-k="rank" style="cursor:default">#</th>
        <th data-k="title"><span data-i18n="th_game">Game</span> <span class="ar"></span></th>
        <th data-k="sort_score" data-num="1"><span data-i18n="th_conf">Confidence</span> <span class="ar"></span></th>
        <th data-k="rating" data-num="1"><span data-i18n="th_rating">Steam rating</span> <span class="ar"></span></th>
        <th data-k="reviews" data-num="1"><span data-i18n="th_reviews">Reviews</span> <span class="ar"></span></th>
        <th data-k="tags"><span data-i18n="th_tags">Tags</span> <span class="ar"></span></th>
__HOURS_TH__        <th data-k="year" data-num="1"><span data-i18n="th_year">Year</span> <span class="ar"></span></th>
        <th data-k="mode"><span data-i18n="th_modes">Modes</span> <span class="ar"></span></th>
      </tr></thead>
      <tbody id="body"></tbody>
    </table>
  </div>
  <div id="none" class="empty" hidden data-i18n="empty">Nothing matches those filters.</div>

  <p class="foot" id="foot"></p>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
  "use strict";
  var GAMES = JSON.parse(document.getElementById("data").textContent);
  var I18N = __I18N__;
  var TAG = __TAG_MAP__;
  var REVIEW = __REVIEW_MAP__;
  var N = __NUMS__;
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
    // Only the label changes: the option keeps its English value, so the filter in
    // passes() goes on comparing against what Steam actually sent.
    each("#tags option", function(o){ if (o.value) o.textContent = tagName(o.value); });
    each(".lang button", function(o){
      o.setAttribute("aria-pressed", o.getAttribute("data-lang") === LANG ? "true" : "false");
    });
    $("minrv").textContent = nfmt(STEPS[+$("minr").value]);
    tiles();
    $("foot").innerHTML = t("foot");
    render();
    syncBar();
  }

  var sortKey = "sort_score", sortDir = -1;

  function passes(g){
    var q = $("q").value.trim().toLowerCase();
    if (q && g._hay.indexOf(q) === -1) return false;
    var gen = $("tags").value;
    if (gen && (g.tags || []).indexOf(gen) === -1) return false;
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
        '<td><div class="gen">' + (g.tags || []).map(function(x){
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
    // Keep the dropdown showing the live state; blank when the table is sorted
    // by a column the dropdown has no entry for.
    var sel = $("sort"), want = k + "|" + dir, known = false;
    for (var i = 0; i < sel.options.length; i++) {
      if (sel.options[i].value === want) { known = true; break; }
    }
    sel.value = known ? want : "";
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

  $("sort").addEventListener("change", function(){
    var p = this.value.split("|");
    if (p.length === 2) applySort(p[0], +p[1]);
  });

  ["q", "tags", "status", "sp", "co", "pad"].forEach(function(id){
    $(id).addEventListener("input", render);
  });
  $("minr").addEventListener("input", function(){
    $("minrv").textContent = nfmt(STEPS[+this.value]);
    render();
  });
  $("reset").addEventListener("click", function(){
    $("q").value = ""; $("tags").value = ""; $("status").value = "";
    $("minr").value = 1;
    $("minrv").textContent = nfmt(STEPS[1]);
    $("sp").checked = $("co").checked = $("pad").checked = false;
    render();
  });
  each(".lang button", function(b){
    b.addEventListener("click", function(){ applyLang(b.getAttribute("data-lang")); });
  });

  // The filter bar wraps to a second row at narrow widths and grows again when
  // the webfont swaps in, so the sticky header's offset has to track its real
  // height rather than be measured once. Switching language moves it too.
  var bar = document.querySelector(".bar");
  function syncBar(){
    document.documentElement.style.setProperty(
      "--barh", Math.ceil(bar.getBoundingClientRect().height) + "px");
  }
  if (window.ResizeObserver) new ResizeObserver(syncBar).observe(bar);
  window.addEventListener("resize", syncBar);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(syncBar);
  syncBar();

  applyLang(preferred());
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


def _json(obj):
    """JSON that is safe to sit inside a <script> block."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def _esc(s):
    """Steam tags carry ampersands - "Animation & Modeling" - so they need escaping."""
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


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

    # The page carries both languages at once, so every sentence with a number in it
    # is assembled in the browser: Python sends the counts, the prose lives in I18N.
    # The date goes as ISO for the same reason - "1 September" is not the same words
    # in Spanish, and toLocaleDateString already knows them.
    nums = {
        "count": len(games),
        "rated": len(rated),
        "great": len(great),
        "median": round(_median([g["rating"] for g in rated]), 2),
        "short": sum(1 for h in hours if h <= 12),
        "hasHours": bool(hours),
        "delisted": verdicts["delisted"],
        "notOnSteam": verdicts["not-on-steam"],
        "duplicate": verdicts["duplicate"],
        "unknown": verdicts["unknown"],
        "stamp": datetime.date.today().isoformat(),
    }

    tags = sorted({x for g in games for x in (g.get("tags") or [])})
    opts = "".join('<option value="%s">%s</option>' % (_esc(t), _esc(t)) for t in tags)

    html = (TEMPLATE
            .replace("__TAGS__", opts)
            .replace("__HOURS_TH__", HOURS_TH if hours else "")
            .replace("__I18N__", _json(I18N))
            .replace("__TAG_MAP__", _json(TAG_ES))
            .replace("__REVIEW_MAP__", _json(REVIEW_ES))
            .replace("__NUMS__", _json(nums))
            .replace("__DATA__", _json(games)))

    path = os.path.join(OUT, "report.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("wrote %s  (%.0f KB, %d games, %d rated, %d tags)"
          % (path, len(html) / 1024.0, len(games), len(rated), len(tags)))
    # The headline answer, for anyone who runs this from run.bat and reads the
    # console rather than opening the page.
    print("      %d delisted on Steam, %d never on Steam, %d duplicate entries, "
          "%d unidentified" % (verdicts["delisted"], verdicts["not-on-steam"],
                               verdicts["duplicate"], verdicts["unknown"]))


if __name__ == "__main__":
    build()
