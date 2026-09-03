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
    "light": "LIGHT",
    "dark": "DARK",
    "al_theme": "Switch between the light and dark theme",

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
    "f_tags": "Tags",
    "al_chips": "Tags being filtered on",
    "al_chip_remove": "Stop filtering by {tag}",
    "chip_clear": "Clear tags",
    "f_status": "Steam status",
    "st_any": "Any Steam status",
    "st_listed": "On Steam now",
    "st_delisted": "Delisted from Steam",
    "st_not": "Never on Steam",
    "st_dup": "Duplicate entry",
    "st_unreleased": "Not released yet",
    "st_unknown": "Unidentified",
    "f_minr": "Min reviews",
    "al_minr": "Minimum review count",
    "f_modes": "Modes",
    "chk_pad": "Controller",
    "btn_reset": "Reset",
    "railmeta": "{n} titles · {steam} on Steam",
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
    "light": "CLARO",
    "dark": "OSCURO",
    "al_theme": "Cambiar entre el tema claro y el oscuro",

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
    "f_tags": "Etiquetas",
    "al_chips": "Etiquetas por las que se filtra",
    "al_chip_remove": "Dejar de filtrar por {tag}",
    "chip_clear": "Quitar etiquetas",
    "f_status": "Estado en Steam",
    "st_any": "Cualquier estado en Steam",
    "st_listed": "Ahora en Steam",
    "st_delisted": "Retirado de Steam",
    "st_not": "Nunca estuvo en Steam",
    "st_dup": "Entrada duplicada",
    "st_unreleased": "A\u00fan sin lanzar",
    "st_unknown": "Sin identificar",
    "f_minr": "Rese\u00f1as m\u00edn.",
    "al_minr": "N\u00famero m\u00ednimo de rese\u00f1as",
    "f_modes": "Modos",
    "chk_pad": "Mando",
    "btn_reset": "Restablecer",
    "railmeta": "{n} t\u00edtulos \u00b7 {steam} en Steam",
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
HOURS_TH = ('          <th data-k="hltb_main" data-num="1">'
            '<span data-i18n="th_hours">Hours</span> <span class="ar"></span></th>\n')

TEMPLATE = r"""<title data-i18n="title">Epic Backlog Triage</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<style>
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
  --chip-ink:var(--color-accent-100);
  --b1:#6aba77; --b2:#8ab45d; --b3:#b7a63d; --b4:#e08e53; --b5:#e8847c;
  --shadow:var(--shadow-md);
}
/* The light theme inverts onto the accent ramps - band colours are derived separately. */
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
  --chip-ink:var(--color-accent-100);
  --b1:#397945; --b2:#54752f; --b3:#776a0a; --b4:#965726; --b5:#9c4e49;
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
    --chip-ink:var(--color-accent-100);
    --b1:#397945; --b2:#54752f; --b3:#776a0a; --b4:#965726; --b5:#9c4e49;
    --shadow:0 1px 2px color-mix(in srgb,var(--color-neutral-900) 6%,transparent),
             0 12px 30px -18px color-mix(in srgb,var(--color-neutral-900) 45%,transparent);
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.55 var(--font-body);
  -webkit-font-smoothing:antialiased}
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

/* ---------- masthead ---------- */
.mast{display:flex;flex-wrap:wrap;align-items:flex-end;gap:16px 28px;margin-bottom:22px}
/* Groups the theme toggle with the language switcher so both sit right-aligned
   as one unit, instead of the toggle sitting flush against the title block. */
.mast .tools{display:flex;align-items:center;gap:10px;margin-left:auto;align-self:flex-start}
h1{font:500 30px/1.1 var(--font-heading);letter-spacing:-.03em;
  margin:0;text-wrap:balance}
h1 em{font-style:normal;color:var(--accent)}
.sub{color:var(--muted);font-size:12.5px;max-width:64ch;margin:9px 0 0}
.sub code{font-family:var(--mono);font-size:12.5px;
  background:var(--surface-2);border:1px solid var(--line);border-radius:4px;padding:1px 5px}
.sub b{color:var(--ink);font-weight:600}

/* ---------- stat tiles ---------- */
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

/* ---------- controls ---------- */
input[type=search]{font:14px/1.2 var(--font-body);color:var(--ink);
  background:var(--surface);border:1px solid var(--line);border-radius:7px;padding:8px 11px;
  /* A rail is a column: a flex-basis here would stretch the box down the page. */
  width:100%;flex:none}
input:focus-visible,button:focus-visible,th:focus-visible{
  outline:2px solid var(--accent);outline-offset:2px}
input[type=range]{accent-color:var(--accent);width:100%;margin:0}
#minrv{display:block;margin-top:5px;font:600 12.5px/1 var(--mono);color:var(--ink);
  font-variant-numeric:tabular-nums}
.chiprail{display:flex;flex-wrap:wrap;gap:5px}
.chiprail button{font:400 11.5px/1 var(--font-body);padding:6px 9px;
  border-radius:var(--radius-sm);cursor:pointer;background:transparent;
  color:var(--muted);border:1px solid var(--line)}
.chiprail button:hover{border-color:var(--accent)}
.chiprail button[aria-pressed="true"]{background:var(--accent-soft);
  color:var(--accent-ink);border-color:var(--accent)}
.chiprail button .n{margin-left:5px;font:400 11px/1 var(--mono);color:var(--faint);
  font-variant-numeric:tabular-nums}
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
.row2{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:9px}
.row2[hidden]{display:none}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:500;
  color:var(--accent-ink);background:var(--accent-soft);border:1px solid var(--accent);
  border-radius:999px;padding:4px 6px 4px 11px}
.chip button{font:600 14px/1 var(--font-body);color:inherit;background:none;
  border:0;border-radius:999px;width:18px;height:18px;padding:0;cursor:pointer;opacity:.65}
.chip button:hover{opacity:1;background:rgba(128,128,128,.22)}
button.clear{font:13px var(--font-body);background:none;border:0;
  color:var(--muted);padding:4px 6px;cursor:pointer;text-decoration:underline;
  text-underline-offset:3px}
button.clear:hover{color:var(--ink)}
.count{margin-top:10px;font-size:13px;color:var(--muted);white-space:nowrap}
.count b{color:var(--ink);font-weight:600;font-variant-numeric:tabular-nums}
button.reset{font:13.5px var(--font-body);background:none;border:1px solid var(--line);
  color:var(--muted);border-radius:7px;padding:8px 11px;cursor:pointer}
button.reset:hover{color:var(--ink);border-color:var(--muted)}

/* ---------- table ---------- */
/* No overflow container at desktop widths: an overflow box would become the
   containing scrollport for the sticky header, pinning it inside the table
   instead of below the filter bar. Narrow screens trade sticky for scroll. */
.scroll{background:none;border-top:0;margin-top:18px}
table{border-collapse:collapse;width:100%;min-width:1020px}
thead th{position:sticky;top:0;z-index:10;background:var(--bg);
  font:600 9px/1.2 var(--font-body);letter-spacing:.14em;text-transform:uppercase;
  color:var(--faint);text-align:left;padding:0 12px 9px;
  border-bottom:1px solid var(--line);cursor:pointer;white-space:nowrap;user-select:none}
thead th:hover{color:var(--ink)}
thead th[aria-sort]{color:var(--accent)}
thead th .ar{opacity:.55;font-size:9px;margin-left:3px}
tbody td{padding:11px 12px;border-bottom:1px solid var(--line-soft);vertical-align:middle}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:var(--accent-soft);box-shadow:inset 2px 0 0 var(--accent)}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums;
  font-size:13px;text-align:right;white-space:nowrap}
.rank{color:var(--faint);font-size:12px;width:46px}
.name{min-width:236px;max-width:340px}
.name a{color:var(--ink);text-decoration:none;display:block;text-underline-offset:2px;
  font:500 13.5px/1.25 var(--font-body);letter-spacing:-.01em}
.name a[href]:hover{text-decoration:underline;color:var(--accent-ink)}
.name .dev{color:var(--faint);font-size:11.5px;margin-top:2px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.taglist{display:flex;flex-wrap:wrap;gap:4px;min-width:150px;max-width:220px}
.taglist span{font-size:11px;color:var(--muted);background:none;
  border:1px solid var(--line-soft);border-radius:var(--radius-sm);padding:1px 7px;
  white-space:nowrap}

/* review bar: proportion positive, coloured by Steam's own tier */
.rate{min-width:152px}
.rate .top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.rate .pct{font-family:var(--mono);font-size:13px;font-weight:600;
  font-variant-numeric:tabular-nums}
.rate .desc{font-size:10.5px;color:var(--faint);text-align:right;line-height:1.2}
.rate .track{height:3px;background:var(--line-soft);border-radius:2px;margin-top:5px;
  overflow:hidden}
.rate .fill{height:100%;border-radius:2px}
.t1{color:var(--b1)} .t2{color:var(--b2)} .t3{color:var(--b3)}
.t4{color:var(--b4)} .t5{color:var(--b5)}
.f1{background:var(--b1)} .f2{background:var(--b2)} .f3{background:var(--b3)}
.f4{background:var(--b4)} .f5{background:var(--b5)}
.mode{font-size:11px;color:var(--muted);white-space:nowrap;letter-spacing:.02em}
.dash{color:var(--faint)}
.tag{display:inline-block;font-size:10px;font-weight:600;letter-spacing:.04em;
  text-transform:uppercase;border-radius:var(--radius-sm);padding:1px 5px;margin-left:6px;
  vertical-align:2px;white-space:nowrap;border:1px solid var(--line);
  background:var(--surface-2);color:var(--muted)}
.tag.gone{color:var(--accent-ink);border-color:var(--accent);background:transparent}
.empty{padding:52px 20px;text-align:center;color:var(--muted)}
.foot{display:block;margin-top:18px;font-size:12.5px;color:var(--faint);line-height:1.65;max-width:96ch}
.foot code{font-family:var(--mono);font-size:11.5px}
/* ---------- theme toggle ---------- */
.theme{display:inline-flex;align-items:center;gap:7px;
  font:600 10.5px/1 var(--mono);letter-spacing:.1em;padding:8px 12px;cursor:pointer;
  border:1px solid var(--line);border-radius:var(--radius-md);background:transparent;
  color:var(--muted)}
.theme:hover{color:var(--accent);border-color:var(--accent)}
.theme .dot{width:9px;height:9px;border-radius:50%;border:1.5px solid currentColor}
:root[data-theme="light"] .theme .dot{background:currentColor}
/* ---------- language switcher ---------- */
.lang{display:inline-flex;gap:2px;padding:2px;
  background:var(--surface);border:1px solid var(--line);border-radius:8px;
  box-shadow:var(--shadow)}
.lang button{font:600 12px/1 var(--mono);letter-spacing:.06em;
  background:none;border:0;border-radius:6px;padding:7px 11px;color:var(--muted);cursor:pointer}
.lang button:hover{color:var(--ink)}
.lang button[aria-pressed="true"]{background:var(--accent-soft);color:var(--accent-ink)}

@media (max-width:1080px){ .scroll{overflow-x:auto} }
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>

<div class="wrap">
  <aside class="rail">
    <div class="brand">
      <div class="kicker">Epic backlog</div>
      <div class="brandname">Triage</div>
      <div class="meta" id="railmeta"></div>
    </div>

    <input type="search" id="q" data-i18n-ph="ph_search" data-i18n-al="al_search"
           placeholder="Search title, tag or developer&hellip;" aria-label="Search">

    <div>
      <h2 id="h-tags" data-i18n="f_tags">Tags</h2>
      <div class="chiprail" id="tagchips" role="group" aria-labelledby="h-tags"></div>
      <div class="row2" id="chips" hidden role="group" data-i18n-al="al_chips"
           aria-label="Tags being filtered on"></div>
    </div>

    <div>
      <h2 id="h-status" data-i18n="f_status">Steam status</h2>
      <div id="statuslist" class="statuslist" role="group" aria-labelledby="h-status"></div>
    </div>

    <div>
      <h2 data-i18n="f_minr">Min reviews</h2>
      <input type="range" id="minr" min="0" max="5" step="1" value="1"
             data-i18n-al="al_minr" aria-label="Minimum review count">
      <b id="minrv">100</b>
    </div>

    <div>
      <h2 id="h-modes" data-i18n="f_modes">Modes</h2>
      <div class="chiprail" id="modechips" role="group" aria-labelledby="h-modes"></div>
    </div>

    <button class="reset" id="reset" type="button" data-i18n="btn_reset">Reset</button>
  </aside>

  <main class="main">
    <div class="mast">
      <div>
        <h1 data-i18n-html="h1">What should I <em>actually</em> play?</h1>
        <p class="sub" data-i18n-html="sub">Games in the Epic library, pulled with <code>legendary</code>
        and scored against live Steam review data.</p>
      </div>
      <div class="tools">
        <button type="button" id="theme" class="theme" data-i18n-al="al_theme"></button>
        <div class="lang" role="group" data-i18n-al="al_lang" aria-label="Language">
          <button type="button" data-lang="es" data-i18n="lang_es">ES</button>
          <button type="button" data-lang="en" data-i18n="lang_en">EN</button>
        </div>
      </div>
    </div>

    <div class="stats" id="stats"></div>

    <div class="scroll">
      <table>
        <thead><tr>
          <th data-k="rank" style="cursor:default">#</th>
          <th data-k="title"><span data-i18n="th_game">Game</span> <span class="ar"></span></th>
          <th data-k="sort_score" data-num="1"><span data-i18n="th_conf">Confidence</span> <span class="ar"></span></th>
          <th data-k="rating" data-num="1"><span data-i18n="th_rating">Steam rating</span> <span class="ar"></span></th>
          <th data-k="reviews" data-num="1"><span data-i18n="th_reviews">Reviews</span> <span class="ar"></span></th>
          <th data-k="tags"><span data-i18n="th_tags">Tags</span> <span class="ar"></span></th>
__HOURS_TH__          <th data-k="year" data-num="1"><span data-i18n="th_year">Year</span> <span class="ar"></span></th>
          <th data-k="mode"><span data-i18n="th_modes">Modes</span> <span class="ar"></span></th>
        </tr></thead>
        <tbody id="body"></tbody>
      </table>
    </div>
    <div id="none" class="empty" hidden data-i18n="empty">Nothing matches those filters.</div>
    <span class="count" id="count"><b>0</b> shown</span>

    <p class="foot" id="foot"></p>
  </main>
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

    # The rail shows the tags worth browsing at a glance; the search box,
    # which already matches tag names, reaches the other two hundred.
    tag_n = Counter(x for g in games for x in (g.get("tags") or []))
    top_tags = [[name, n] for name, n in tag_n.most_common(15)]

    # The status rows carry a count of the whole library, not of the current view,
    # so they are counted here rather than off the filtered rows in the browser.
    status_n = {s: verdicts[s] for s in
                ("listed", "delisted", "not-on-steam", "duplicate", "unreleased", "unknown")}
    status_n[""] = len(games)

    html = (TEMPLATE
            .replace("__TAGS__", _json(top_tags))
            .replace("__STATUS_N__", _json(status_n))
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
          % (path, len(html) / 1024.0, len(games), len(rated), len(tag_n)))
    # The headline answer, for anyone who runs this from run.bat and reads the
    # console rather than opening the page.
    print("      %d delisted on Steam, %d never on Steam, %d duplicate entries, "
          "%d unidentified" % (verdicts["delisted"], verdicts["not-on-steam"],
                               verdicts["duplicate"], verdicts["unknown"]))


if __name__ == "__main__":
    build()
