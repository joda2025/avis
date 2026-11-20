import re, html, pathlib, datetime
from zoneinfo import ZoneInfo
import feedparser

NAME = "Min Avis"
TAGLINE = "Dagens nyheter, samlet automatisk"
PER_FEED = 8
MAX_ITEMS = 40

# Legg til / bytt ut kilder her (sjekk at RSS-adressene fortsatt virker)
FEEDS = {
    "NRK": "https://www.nrk.no/toppsaker.rss",
    "VG": "https://www.vg.no/rss/feed",
    "E24": "https://e24.no/rss",
    "Aftenposten": "https://www.aftenposten.no/rss",
}


def clean(text, limit=220):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def ts(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime.datetime(*t[:6], tzinfo=datetime.timezone.utc) if t else None


items, seen = [], set()
for source, url in FEEDS.items():
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print("Feil:", source, e)
        continue
    for e in feed.entries[:PER_FEED]:
        link = e.get("link")
        if not link or link in seen:
            continue
        seen.add(link)
        items.append({
            "source": source,
            "title": clean(e.get("title"), 160),
            "summary": clean(e.get("summary")),
            "link": link,
            "time": ts(e),
        })

epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
items.sort(key=lambda i: i["time"] or epoch, reverse=True)
items = items[:MAX_ITEMS]

oslo = ZoneInfo("Europe/Oslo")
now = datetime.datetime.now(oslo).strftime("%d.%m.%Y kl. %H:%M")


def card(i):
    t = i["time"].astimezone(oslo).strftime("%d.%m. %H:%M") if i["time"] else ""
    return f"""<article>
<div class="meta">{html.escape(i['source'])} · {t}</div>
<h2><a href="{html.escape(i['link'])}" target="_blank" rel="noopener">{html.escape(i['title'])}</a></h2>
<p>{html.escape(i['summary'])}</p>
</article>"""


page = f"""<!doctype html>
<html lang="nb">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{NAME}</title>
<style>
:root{{--bg:#faf8f3;--fg:#1a1a1a;--muted:#666;--line:#d9d4c7;--link:#8a1c1c}}
@media (prefers-color-scheme: dark){{:root{{--bg:#151515;--fg:#eee;--muted:#999;--line:#333;--link:#e07a7a}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font-family:Georgia,'Times New Roman',serif}}
header{{text-align:center;padding:2rem 1rem 1rem;border-bottom:3px double var(--line)}}
header h1{{margin:0;font-size:clamp(2rem,6vw,3.5rem);letter-spacing:.02em}}
header p{{margin:.3rem 0 0;color:var(--muted);font-style:italic}}
main{{max-width:1000px;margin:0 auto;padding:1rem;display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:1.5rem}}
article{{border-bottom:1px solid var(--line);padding-bottom:1rem}}
.meta{{font:600 .75rem system-ui,sans-serif;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}}
h2{{font-size:1.2rem;line-height:1.25;margin:.4rem 0}}
h2 a{{color:var(--fg);text-decoration:none}} h2 a:hover{{color:var(--link)}}
article p{{margin:0;color:var(--muted);line-height:1.45;font-size:.95rem}}
footer{{text-align:center;color:var(--muted);font:.8rem system-ui,sans-serif;padding:2rem 1rem}}
</style>
</head>
<body>
<header><h1>{NAME}</h1><p>{TAGLINE}</p></header>
<main>
{''.join(card(i) for i in items)}
</main>
<footer>Sist oppdatert {now}. Overskrifter og ingresser tilhører kildene, klikk for å lese hele saken.</footer>
</body>
</html>"""

out = pathlib.Path("docs")
out.mkdir(exist_ok=True)
(out / "index.html").write_text(page, encoding="utf-8")
print(f"Skrev {len(items)} saker")
