"""Shared helpers: HTTP with cache + throttle, name normalisation, Wilson score."""
import json, math, os, re, sys, time, urllib.parse, urllib.request, urllib.error

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
# A fresh clone has no cache/ - it is generated, so it is not in the repository.
# Without this the very first run silently stops memoising and takes an hour
# every time.
os.makedirs(CACHE, exist_ok=True)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_last = {}


def use_utf8_stdout():
    """Print game titles without exploding on a legacy console code page.

    Windows terminals still default to cp1252 and friends, so the first title
    with a character outside it - an accent, a Japanese subtitle, a smart quote -
    would end an hour-long run with UnicodeEncodeError.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def _throttle(bucket, delay):
    now = time.monotonic()
    wait = _last.get(bucket, 0.0) + delay - now
    if wait > 0:
        time.sleep(wait)
    _last[bucket] = time.monotonic()


def cache_path(key):
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", key)[:150]
    return os.path.join(CACHE, safe + ".json")


def fetch_json(url, bucket="steam", delay=1.5, tries=5, post=None, headers=None):
    """One throttled, retried request, decoded as JSON. None on hard failure.

    Separate from cached_json because the batched store endpoint caches one file
    per appid while fetching two hundred at a time - the cache key and the URL
    stop being the same thing.
    """
    for attempt in range(tries):
        _throttle(bucket, delay)
        try:
            hdrs = {"User-Agent": UA, "Accept": "application/json"}
            if headers:
                hdrs.update(headers)
            body = None
            if post is not None:
                body = json.dumps(post).encode()
                hdrs["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=body, headers=hdrs)
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503):
                time.sleep(min(60, 5 * (2 ** attempt)))
                continue
            return None
        except Exception:
            time.sleep(2 * (attempt + 1))
            continue
    return None


def cached_json(key, url, bucket="steam", delay=1.5, tries=5, post=None, headers=None):
    """Fetch url as JSON, memoised on disk under `key`. Returns None on hard failure.

    A cached null is a remembered failure and is NOT retried, so reruns stay fast.
    """
    path = cache_path(key)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (ValueError, OSError):
            pass

    data = fetch_json(url, bucket, delay, tries, post, headers)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except OSError:
        pass
    return data


_EDITION = re.compile(
    r"\b(game of the year|goty|definitive|complete|deluxe|ultimate|enhanced|remastered|"
    r"director'?s cut|standard|gold|premium|anniversary|legendary|special|collectors?|"
    r"digital|extended)\b\s*(edition|bundle|pack)?", re.I)


def normalise(name, drop_edition=False):
    """Lowercase, strip trademark marks and punctuation, collapse whitespace."""
    s = (name or "").lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[\u2122\u00ae\u00a9\u2117]", "", s)
    s = re.sub(r"[\u2018\u2019\u02bc]", "'", s)
    s = re.sub(r"[\u2013\u2014]", "-", s)
    if drop_edition:
        s = _EDITION.sub(" ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def wilson_lower(pos, total, z=1.96):
    """Wilson score lower bound, as a percentage. 0.0 when there are no reviews."""
    if not total:
        return 0.0
    p = pos / total
    d = 1.0 + z * z / total
    centre = (p + z * z / (2 * total)) / d
    margin = (z / d) * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return max(0.0, (centre - margin) * 100.0)
