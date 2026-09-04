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

def _tpl(name):
    with open(os.path.join(HERE, "templates", name), encoding="utf-8") as fh:
        return fh.read()


TEMPLATE = (_tpl("head.html")
            + "<style>\n" + _tpl("style.css") + "</style>\n"
            + _tpl("body.html")
            + "<script>\n" + _tpl("app.js") + "</script>\n")


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
