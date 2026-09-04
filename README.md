# Epic Backlog Triage

**English version:** [README.en.md](README.en.md)

## Resumen

Descarga tu biblioteca de Epic Games con [legendary](https://github.com/derrod/legendary), cruza
cada título con las reseñas de Steam y genera un único informe HTML sin conexión, ordenado por una
puntuación de confianza — para que elijas algo a qué jugar en vez de desplazarte por un launcher
lleno de juegos que nunca abriste. Nada está ligado a la cuenta del autor original: clona el
repositorio, conecta tu propia cuenta de Epic y obtén tu propia biblioteca, ordenada igual. En
Windows basta con hacer doble clic en `run.bat`; el resto sigue los tres comandos de
[Configuración manual](#configuración-manual).

## Índice

- [Qué necesitas](#qué-necesitas)
- [Inicio rápido (Windows)](#inicio-rápido-windows)
- [Configuración manual](#configuración-manual)
- [Leer el informe](#leer-el-informe)
- [Qué se genera](#qué-se-genera)
- [Cómo se calculan los números](#cómo-se-calculan-los-números)
- [Por qué un juego no tiene puntuación](#por-qué-un-juego-no-tiene-puntuación)
- [La puntuación de confianza](#la-puntuación-de-confianza)
- [Tiempo de juego](#tiempo-de-juego)
- [Solución de problemas](#solución-de-problemas)
- [Archivos](#archivos)
- [Licencia](#licencia)

![El informe: 389 juegos de una biblioteca de Epic, ordenados por puntuación de confianza](docs/screenshot.png)

## Qué necesitas

| | |
|---|---|
| **Python 3.8 o superior** | Solo usa la biblioteca estándar |
| **Una cuenta de Epic Games** | Solo lectura: nada más que el listado de tu biblioteca |
| **Un par de minutos** | Cada respuesta HTTP queda en caché, así que las siguientes ejecuciones tardan segundos |

Funciona en Windows, macOS y Linux. No hace falta tener instalado el Epic Games Launcher.

Antes de arrancar `run.bat` (o los scripts a mano), y durante la primera ejecución, hay un par de
cosas que solo puedes hacer tú:

1. Ten una cuenta de Epic Games — créala en [epicgames.com](https://www.epicgames.com) si no
   tienes una.
2. En Windows, ten `winget` disponible: viene incluido en Windows 11 y en Windows 10 actualizado;
   si falta, instala **App Installer** desde la Microsoft Store. `run.bat` lo usa para instalar
   Python si no lo encuentra, pero winget solo existe en Windows — en macOS y Linux instala Python
   tú mismo (ver [Configuración manual](#configuración-manual)).
3. Ten conexión a internet la primera vez — las siguientes ejecuciones usan la caché.
4. Si Python no estaba instalado, acepta su instalación cuando `run.bat` te lo pida — winget
   necesita tu confirmación, y Windows puede pedir permiso de administrador.
5. Cuando se abra la pestaña del navegador, inicia sesión con tus credenciales de Epic Games.
6. Copia el código de autorización que te devuelve esa página y pégalo en la terminal cuando te lo
   pida.

## Inicio rápido (Windows)

Descarga o clona el repositorio y haz doble clic en `run.bat`. Esto:

1. busca un Python 3.8+ (primero el lanzador `py`, para no toparse con el stub de Microsoft Store)
2. crea un `.venv` privado dentro de la carpeta
3. instala legendary en él
4. ejecuta la batería de pruebas, así que un checkout roto se detiene aquí y no a mitad de la
   descarga
5. abre el login de Epic solo la primera vez
6. descarga tu biblioteca y los datos de Steam, reintenta lo que falló y decide qué está
   descatalogado
7. genera `out/report.html` y lo abre

Puedes ejecutarlo tantas veces como quieras: reutiliza el entorno y la caché, así que las
siguientes ejecuciones tardan segundos. Los argumentos pasan al paso de descarga: `run.bat
--refresh` vuelve a leer tu biblioteca de Epic en vez de usar la copia en caché. Si un paso falla,
se detiene ahí y explica qué hacer; la ventana se queda abierta para que puedas leerlo.

## Configuración manual

Úsala en macOS/Linux, o en Windows si prefieres hacerlo tú mismo paso a paso.

### 1. Obtén el código e instala legendary

```sh
git clone <this-repo-url>
cd "Epic Games List"

python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

python -m pip install -r requirements.txt
```

En macOS/Linux usa `python3` donde este documento dice `python`. El entorno virtual es opcional —
`python -m pip install --user legendary-gl` también funciona; si tu shell luego no encuentra el
comando `legendary`, los scripts recurren a ejecutarlo con el mismo intérprete.

### 2. Conecta tu cuenta de Epic

Este es el único paso que depende de ti y no del repositorio — legendary necesita tu permiso para
leer tu biblioteca, y eso implica un login interactivo en Epic. Los scripts nunca ven tu
contraseña.

```sh
legendary auth
```

Qué esperar:

1. Se abre una pestaña con el login real de Epic (`epicgames.com` en la barra de direcciones).
   Inicia sesión como siempre — email/usuario, contraseña, 2FA si lo usas.
2. ¿No se abrió nada automáticamente? Ve a <https://legendary.gl/epiclogin> e inicia sesión ahí.
3. Tras iniciar sesión, la pestaña redirige a una página de texto plano que empieza con `{` — eso
   es correcto, no un error. Se ve así:

   ```json
   {"authorizationCode":"3b1a9f...", "expiresInSeconds":600, ...}
   ```

4. Selecciona todo (Ctrl+A / Cmd+A) y cópialo (Ctrl+C / Cmd+C) — el bloque completo, llaves
   incluidas.
5. Vuelve a la terminal, que está esperando ese texto, pégalo y pulsa Enter. legendary extrae el
   código él mismo.

El código caduca en pocos minutos; si al pegarlo falla, recarga la página de login para conseguir
uno nuevo y repite desde el paso 3.

¿Prefieres pasar el código directamente en vez de por ese prompt? Extrae solo el valor entre
comillas que sigue a `"authorizationCode":` y ejecuta:

```sh
legendary auth --code <código de autorización>
```

¿Ya tienes el Epic Games Launcher instalado y con sesión iniciada? `legendary auth --import` toma
la sesión de ahí (y cierra la sesión del launcher). Confirma con:

```sh
legendary status
```

Debería imprimir tu nombre de usuario de Epic. Las credenciales viven en el directorio de
configuración de legendary (`%USERPROFILE%\.config\legendary` en Windows, `~/.config/legendary`
en el resto) — nunca en este repositorio.

### 3. Genera el informe

```sh
python epic_steam.py      # biblioteca -> datos de Steam    -> out/games.json, out/games.csv
python second_pass.py     # reintenta los títulos que fallaron (opcional, recomendado)
python build_report.py    # genera                        -> out/report.html
```

La primera ejecución de `epic_steam.py` es lenta a propósito — Steam limita la tasa de peticiones,
así que se regulan y cada respuesta se guarda en `cache/`. Las siguientes ejecuciones leen la
caché y terminan en segundos.

| Flag | Efecto |
|---|---|
| `--refresh` | Vuelve a consultar legendary en vez de usar el volcado de biblioteca en caché |
| `--no-hltb` | Omite por completo la fase de HowLongToBeat |

## Leer el informe

Un único archivo autocontenido: sin servidor, sin build, sin dependencias. Ábrelo desde el disco,
envíalo por correo, llévalo en un USB — lo único que pide a la red son las tipografías web, y todo
tiene una alternativa del sistema.

Los filtros se combinan: la búsqueda coincide con título, etiqueta, desarrollador y editor; el
desplegable de estado filtra por catalogación en Steam; el control de reseñas mínimas avanza por
0, 100, 500, 2.000, 10.000 y 50.000 (empieza en 100); y Solo, Cooperativo y Mando dejan solo los
juegos que declaran ese soporte. **Reset** lo limpia todo. Ordena desde el desplegable o pulsando
el encabezado de una columna; púlsalo de nuevo para invertir el orden.

Las etiquetas también se combinan y restringen: elegir dos etiquetas muestra los juegos que tienen
**ambas**, no cualquiera de las dos — *Acción* más *Mundo abierto* son los once juegos de acción
en mundo abierto, no el centenar que tiene una u otra. Cada chip tiene una x; *Clear tags* las
quita todas de golpe.

La página se abre en el idioma de tu navegador (en Windows sigue el idioma del sistema); el
interruptor `ES`/`EN` arriba a la derecha lo anula y recuerda tu elección. Cambiar de idioma
traduce la interfaz, los nombres de etiquetas de Steam y sus niveles de reseña, y reformatea
números y fechas según el idioma — los títulos, desarrolladores y editores se quedan igual porque
son nombres propios. Filtrar y ordenar no se ven afectados por el idioma. Steam tiene unas 400
etiquetas; solo las más comunes están traducidas, el resto se queda en inglés.

## Qué se genera

```
out/report.html   la página que realmente miras
out/games.json    todos los campos, un objeto por juego
out/games.csv     las mismas filas, para una hoja de cálculo
cache/            un JSON por appid, más el volcado de tu biblioteca
```

`out/` y `cache/` se generan y están en `.gitignore` — tu biblioteca nunca termina en un commit.
Puedes borrar cualquiera de las dos en cualquier momento; los scripts recrean lo que necesitan.

## Cómo se calculan los números

1. **Biblioteca** — `legendary list --json -T`, quedándose con las entradas categorizadas como
   `games` o `software` (descarta assets, plugins y proyectos de ejemplo de Unreal Engine,
   conserva rarezas como RPG in a Box).
2. **Match** — cada título consulta el endpoint `SearchSuggestions` de Steam, que devuelve los
   productos coincidentes con reseñas, etiquetas, categorías, fecha de lanzamiento y desarrollador
   ya incluidos. Los resultados se ordenan por cercanía del nombre (exacto, luego sin la edición,
   luego subcadena); DLC, bandas sonoras y demos se descartan directamente.
3. **Segunda pasada** — `second_pass.py` reintenta los que quedaron sin match con consultas más
   laxas: quita `(Beta)`, quita el subtítulo, elimina puntuación, separa palabras pegadas. Los
   resultados se siguen verificando por nombre; dos entradas de Epic que caen en la misma página
   de Steam se fusionan.
4. **Veredicto** — lo que sigue sin match se busca en PCGamingWiki, que cubre tanto los juegos
   descatalogados como los que nunca estuvieron en Steam (la búsqueda de Steam solo conoce lo que
   vende ahora mismo). El appid de Steam del wiki, cuando existe, basta — `GetItems` sigue
   respondiendo para juegos retirados mucho después de que la tienda deje de listarlos.

Los conteos de reseñas son los totales filtrados de Steam, el mismo número que muestra su propia
página de tienda. No hay columna de Metacritic ni de géneros de Steam — los endpoints agrupados no
traen ninguno de los dos, así que Tags hace las veces de género.

## Por qué un juego no tiene puntuación

Cada fila lleva un `steam_status`:

| Estado | Significado |
|---|---|
| `listed` | A la venta en Steam ahora, o gratuito |
| `delisted` | Retirado de la venta, pero la página y sus reseñas sobreviven — **se puntúa y ordena con normalidad** |
| `not-on-steam` | PCGamingWiki tiene artículo y no lista appid de Steam: nunca estuvo ahí |
| `duplicate` | Una segunda entrada de Epic para un juego que ya está en la lista |
| `unreleased` | Steam tiene página, con fecha futura |
| `unknown` | No se encontró nada en ningún lado |

Elige un estado en el desplegable **Any Steam status** para ver solo esos — al hacerlo también se
levanta el mínimo de reseñas, para que las categorías que por naturaleza no tienen reseñas no
queden ocultas.

`delisted` se lee directamente de la marca `unlisted` de la propia Steam, no se infiere. Un match
por wiki es más débil que uno por búsqueda en Steam y se marca como tal — pasa el cursor sobre la
insignia para ver a qué página de Steam corresponde; un nombre reutilizado puede, en ocasiones,
coger la edición equivocada (el *Unreal Tournament* gratuito de Epic es el de 2014, y el artículo
`Unreal Tournament` de PCGamingWiki es el de 1999).

## La puntuación de confianza

Ordenar por porcentaje de reseñas positivas puro pone *100% con 14 reseñas* por encima de *98% con
300.000* — justo al revés de lo que interesa para elegir qué jugar. `sort_score` es en cambio el
**límite inferior de Wilson al 95%** sobre la proporción de reseñas positivas:

```
         p + z²/2n - z·√( p(1-p)/n + z²/4n² )
score = ──────────────────────────────────────   ,  z = 1.96
                    1 + z²/n
```

Parte de la puntuación bruta y la reduce cuantas menos reseñas hay. Hades (98,01%, 308.000
reseñas) apenas se mueve, a 97,96. Un juego al 100% con 14 reseñas queda cerca de 78.

## Tiempo de juego

No incluido. El endpoint de búsqueda de HowLongToBeat ahora rechaza las peticiones directas, y
este proyecto no falsifica una sesión de navegador para sortearlo. `epic_steam.py` lo comprueba
una vez, registra que no está disponible y sigue; `build_report.py` omite la columna de horas
cuando no hay datos. Si HLTB vuelve a abrirse, ambas partes funcionan de nuevo sin cambiar código.

## Solución de problemas

**`Could not run legendary`** — no está instalado en el intérprete que estás usando; vuelve a
ejecutar `python -m pip install -r requirements.txt` con el mismo `python`.

**`legendary could not list your library`** — casi siempre es autenticación. Ejecuta
`legendary status`; si no muestra tu nombre de usuario, repite el
[paso 2](#2-conecta-tu-cuenta-de-epic).

**Muchos juegos sin datos de Steam** — si la red falló a mitad de la ejecución, esos fallos quedan
en caché como `null` y no se reintentan. Bórralos y vuelve a ejecutar:

```sh
python -c "import json,glob,os; [os.remove(p) for p in glob.glob('cache/*.json') if json.load(open(p,encoding='utf-8')) is None]"
```

**Conteos de reseñas desactualizados** — borra `cache/item_*.json` y vuelve a ejecutar
`epic_steam.py`.

**Un juego emparejado con la página de Steam equivocada** — borra el `cache/find_<title>.json`
correspondiente y vuelve a ejecutar; ese título se resuelve desde cero.

**Títulos con caracteres extraños en la terminal** — es cosmético; stdout usa UTF-8, pero una
terminal con una página de códigos antigua puede dibujar mal los glifos. `out/games.json` y el
informe siempre están en UTF-8.

## Archivos

```
run.bat           un clic en Windows: entorno, autocomprobación, login, descarga, informe
epic_steam.py     fases 1-5: biblioteca -> match -> Steam -> tiempo de juego -> salida
second_pass.py    reintenta títulos sin match, luego decide descatalogado vs. nunca-estuvo
pcgw.py           búsqueda en PCGamingWiki: título -> appid de Steam, para lo que la búsqueda no encuentra
steamstore.py     la API de la tienda de Steam: búsqueda, consulta por lotes, item -> fila
build_report.py   genera out/games.json como página HTML ordenable, en inglés y español
steamlib.py       HTTP con caché y limitación, normalización de nombres, puntuación de Wilson
test_*.py         pruebas unitarias: matching, descatalogados, el informe y sus dos idiomas
requirements.txt  legendary-gl (los scripts en sí solo usan la biblioteca estándar)
LICENSE           MIT
docs/             la captura de pantalla de este README
cache/            un JSON por appid, no por respuesta   (generado, en .gitignore)
out/              games.json, games.csv, report.html   (generado, en .gitignore)
```

Ejecuta las pruebas con `python -m unittest discover`. No tocan red ni tu caché.

## Licencia

[MIT](LICENSE) para el código. Lo que descarga no está cubierto por esa licencia: los números de
reseñas y los metadatos de la tienda son de Valve, y los datos de artículos son de
[PCGamingWiki](https://www.pcgamingwiki.com/wiki/PCGamingWiki:Copyrights). Ambos se leen a través
de sus endpoints públicos, respetando sus límites de tasa, y se guardan en caché local en vez de
redistribuirse.
