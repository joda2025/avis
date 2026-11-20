import re, html, pathlib, datetime
from zoneinfo import ZoneInfo
import feedparser

NAME = "Min Avis"
TAGLINE = "Dagens nyheter, samlet automatisk"
PER_FEED = 8
MAX_ITEMS = 41

# Kilde: (RSS-adresse, farge)
FEEDS = {
    "NRK": ("https://www.nrk.no/toppsaker.rss", "#0b6bcb"),
    "VG": ("https://www.vg.no/rss/feed", "#c8102e"),
    "E24": ("https://e24.no/rss", "#1b7f5c"),
    "Aftenposten": ("https://www.aftenposten.no/rss", "#6b4e9b"),
}

DAYS = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
MONTHS = ["januar", "februar", "mars", "april", "mai", "juni", "juli",
          "august", "september", "oktober", "november", "desember"]


def clean(text, limit=220):
    text = re.sub(r"<[^>]+>", "", text or "")
    text = html.unescape(text).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0] + "…"
    return text


def ts(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return datetime.datetime(*t[:6], tzinfo=datetime.timezone.utc) if t else None


def image_of(e):
    for key in ("media_content", "media_thumbnail"):
        for m in e.get(key) or []:
            if m.get("url"):
                return m["url"]
    for l in e.get("links", []):
        if l.get("rel") == "enclosure" and "image" in l.get("type", ""):
            return l.get("href")
    blob = e.get("summary", "") + "".join(c.get("value", "") for c in e.get("content", []))
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', blob)
    return m.group(1) if m else None


items, seen = [], set()
for source, (url, color) in FEEDS.items():
    try:
        feed = feedparser.parse(url)
    except Exception as ex:
        print("Feil:", source, ex)
        continue
    for e in feed.entries[:PER_FEED]:
        link = e.get("link")
        if not link or link in seen:
            continue
        seen.add(link)
        img = image_of(e)
        items.append({
            "source": source, "color": color,
            "title": clean(e.get("title"), 160),
            "summary": clean(e.get("summary")),
            "link": link, "time": ts(e),
            "img": img if img and img.startswith("https://") else None,
        })

epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
items.sort(key=lambda i: i["time"] or epoch, reverse=True)
items = items[:MAX_ITEMS]

oslo = ZoneInfo("Europe/Oslo")
n = datetime.datetime.now(oslo)
date_str = f"{DAYS[n.weekday()].capitalize()} {n.day}. {MONTHS[n.month - 1]} {n.year}"
updated = n.strftime("%d.%m.%Y kl. %H:%M")
esc = html.escape


def thumb(i):
    img = (f'<img src="{esc(i["img"])}" alt="" loading="lazy" referrerpolicy="no-referrer" '
           f'onerror="this.remove()">') if i["img"] else ""
    return f'<div class="thumb" style="--c:{i["color"]}" data-src="{esc(i["source"])}">{img}</div>'


def when(i):
    return i["time"].astimezone(oslo).strftime("%d.%m. %H:%M") if i["time"] else ""


def card(i):
    return f"""<article data-src="{esc(i['source'])}">
<a class="img" href="{esc(i['link'])}" target="_blank" rel="noopener">{thumb(i)}</a>
<div class="body"><div class="meta"><b style="color:{i['color']}">{esc(i['source'])}</b> · {when(i)}</div>
<h3><a href="{esc(i['link'])}" target="_blank" rel="noopener">{esc(i['title'])}</a></h3>
<p>{esc(i['summary'])}</p></div></article>"""


hero_i = next((i for i in items if i["img"]), items[0] if items else None)
rest = [i for i in items if i is not hero_i]

hero = ""
if hero_i:
    hero = f"""<section class="hero"><a class="img" href="{esc(hero_i['link'])}" target="_blank" rel="noopener">{thumb(hero_i)}</a>
<div class="body"><div class="meta"><b style="color:{hero_i['color']}">{esc(hero_i['source'])}</b> · {when(hero_i)}</div>
<h2><a href="{esc(hero_i['link'])}" target="_blank" rel="noopener">{esc(hero_i['title'])}</a></h2>
<p>{esc(hero_i['summary'])}</p></div></section>"""

ticker = "".join(f'<a href="{esc(i["link"])}" target="_blank" rel="noopener"><b style="color:{i["color"]}">{esc(i["source"])}</b> {esc(i["title"])}</a>'
                 for i in items[:8])
filters = '<button class="on" data-f="">Alle</button>' + "".join(
    f'<button data-f="{esc(s)}">{esc(s)}</button>' for s in FEEDS)

CSS = """
:root{--bg:#faf8f3;--card:#fff;--fg:#1a1a1a;--muted:#666;--line:#d9d4c7;--accent:#8a1c1c}
@media (prefers-color-scheme: dark){:root{--bg:#141414;--card:#1e1e1e;--fg:#eee;--muted:#a0a0a0;--line:#333;--accent:#e07a7a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Georgia,'Times New Roman',serif}
a{color:inherit;text-decoration:none}
header{text-align:center;padding:1.6rem 1rem .8rem;border-bottom:3px double var(--line);max-width:1100px;margin:0 auto}
header .date{font:600 .75rem system-ui,sans-serif;letter-spacing:.15em;text-transform:uppercase;color:var(--muted)}
header h1{margin:.2rem 0;font-size:clamp(2.4rem,8vw,4.5rem);letter-spacing:.03em;font-weight:900}
header p{margin:0;color:var(--muted);font-style:italic}
.ticker{background:var(--accent);color:#fff;overflow:hidden;white-space:nowrap;margin-top:1rem;font:.85rem system-ui,sans-serif}
.ticker div{display:inline-block;padding:.5rem 0;animation:run 90s linear infinite}
.ticker a{margin-right:2.5rem}.ticker b{color:#fff!important;opacity:.75;margin-right:.4rem;text-transform:uppercase;font-size:.7rem}
@keyframes run{from{transform:translateX(0)}to{transform:translateX(-50%)}}
@media (prefers-reduced-motion:reduce){.ticker div{animation:none}}
main{max-width:1100px;margin:0 auto;padding:1rem}
.filters{display:flex;gap:.5rem;flex-wrap:wrap;margin:.5rem 0 1.2rem}
.filters button{font:600 .8rem system-ui,sans-serif;border:1px solid var(--line);background:var(--card);color:var(--fg);padding:.4rem .9rem;border-radius:999px;cursor:pointer}
.filters button.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.thumb{position:relative;aspect-ratio:16/10;overflow:hidden;background:linear-gradient(135deg,var(--c),#1b1b1b)}
.thumb::after{content:attr(data-src);position:absolute;inset:0;display:grid;place-items:center;font:900 2rem system-ui,sans-serif;color:rgba(255,255,255,.35);letter-spacing:.05em}
.thumb img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1;transition:transform .4s}
.img:hover .thumb img{transform:scale(1.04)}
.meta{font:.75rem system-ui,sans-serif;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
.hero{display:grid;grid-template-columns:1.4fr 1fr;gap:1.5rem;align-items:center;padding-bottom:1.5rem;margin-bottom:1.5rem;border-bottom:1px solid var(--line)}
.hero h2{font-size:clamp(1.6rem,3.5vw,2.4rem);line-height:1.15;margin:.5rem 0}
.hero h2 a:hover,h3 a:hover{color:var(--accent)}
.hero p{color:var(--muted);line-height:1.5;font-size:1.05rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.4rem}
article{background:var(--card);border:1px solid var(--line);border-radius:6px;overflow:hidden;display:flex;flex-direction:column}
article .body{padding:.9rem 1rem 1.1rem}
h3{font-size:1.1rem;line-height:1.25;margin:.4rem 0}
article p{margin:0;color:var(--muted);line-height:1.45;font-size:.9rem}
footer{text-align:center;color:var(--muted);font:.8rem system-ui,sans-serif;padding:2rem 1rem}
@media(max-width:700px){.hero{grid-template-columns:1fr}}
"""

JS = """
document.querySelectorAll('.filters button').forEach(b=>b.onclick=()=>{
document.querySelectorAll('.filters button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
const f=b.dataset.f;document.querySelectorAll('.grid article').forEach(a=>a.style.display=(!f||a.dataset.src===f)?'':'none');});
"""

page = f"""<!doctype html>
<html lang="nb"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(NAME)}</title>
<style>{CSS}</style></head>
<body>
<header><div class="date">{date_str}</div><h1>{esc(NAME)}</h1><p>{esc(TAGLINE)}</p></header>
<div class="ticker"><div>{ticker}{ticker}</div></div>
<main>
{hero}
<div class="filters">{filters}</div>
<div class="grid">{''.join(card(i) for i in rest)}</div>
</main>
<footer>Sist oppdatert {updated}. Overskrifter, ingresser og bilder tilhører kildene. Klikk for å lese hele saken der.</footer>
<script>{JS}</script>
</body></html>"""

out = pathlib.Path("docs")
out.mkdir(exist_ok=True)
(out / "index.html").write_text(page, encoding="utf-8")
(out / ".nojekyll").write_text("", encoding="utf-8")
print(f"Skrev {len(items)} saker")
