import re, html, json, pathlib, datetime
from zoneinfo import ZoneInfo
import feedparser

feedparser.USER_AGENT = "Mozilla/5.0 (compatible; MinAvis/1.0)"

NAME = "Min Avis"
TAGLINE = "Dagens nyheter, samlet automatisk"
PER_FEED = 6

# Kilder per kolonne: (navn, RSS-adresse, farge, vises som standard?)
# Slå kilder av/på her, eller la leseren velge i «Velg kilder» på siden.
# Adresser som ikke virker hoppes stille over (se loggen i Actions).
SECTIONS = {
    "Innland": [
        ("NRK Norge", "https://www.nrk.no/norge/toppsaker.rss", "#0b6bcb", True),
        ("Aftenposten", "https://www.aftenposten.no/rss", "#6b4e9b", True),
        ("VG", "https://www.vg.no/rss/feed", "#c8102e", True),
        ("TV 2", "https://www.tv2.no/rss/nyheter", "#e2001a", True),
        ("Dagbladet", "https://www.dagbladet.no/?lab_viewport=rss", "#d4002a", True),
        # Lokalt (av som standard, slås på i «Velg kilder»)
        ("NRK Vestland", "https://www.nrk.no/vestland/toppsaker.rss", "#2a7ab0", False),
        ("NRK Trøndelag", "https://www.nrk.no/trondelag/toppsaker.rss", "#2a7ab0", False),
        ("NRK Rogaland", "https://www.nrk.no/rogaland/toppsaker.rss", "#2a7ab0", False),
        ("NRK Nordland", "https://www.nrk.no/nordland/toppsaker.rss", "#2a7ab0", False),
        ("NRK Troms og Finnmark", "https://www.nrk.no/tromsogfinnmark/toppsaker.rss", "#2a7ab0", False),
        ("NRK Møre og Romsdal", "https://www.nrk.no/mr/toppsaker.rss", "#2a7ab0", False),
        ("Bergens Tidende", "https://www.bt.no/rss", "#00507a", False),
        ("Adresseavisen", "https://www.adressa.no/rss", "#8a5a00", False),
        ("Stavanger Aftenblad", "https://www.aftenbladet.no/rss", "#1a6a8a", False),
        ("Fædrelandsvennen", "https://www.fvn.no/rss", "#3a6a3a", False),
    ],
    "Utland": [
        ("NRK Urix", "https://www.nrk.no/urix/toppsaker.rss", "#0b6bcb", True),
        ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", "#bb1919", True),
        ("The Guardian", "https://www.theguardian.com/world/rss", "#05298a", True),
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "#b8860b", True),
        ("NYT World", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "#333333", True),
        ("NPR World", "https://feeds.npr.org/1004/rss.xml", "#c0392b", False),
        ("DW", "https://rss.dw.com/rdf/rss-en-all", "#00a5ff", False),
    ],
    "Annet": [
        ("NRK Kultur", "https://www.nrk.no/kultur/toppsaker.rss", "#d9822b", True),
        ("NRK Sport", "https://www.nrk.no/sport/toppsaker.rss", "#1b9a4b", True),
        ("NRK Viten", "https://www.nrk.no/viten/toppsaker.rss", "#7a5ab0", True),
        ("E24", "https://e24.no/rss", "#1b7f5c", True),
        ("The Onion", "https://theonion.com/feed/", "#2e8b57", True),
        ("Atlas Obscura", "https://www.atlasobscura.com/feeds/latest", "#a0522d", True),
    ],
}

DAYS = ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag"]
MONTHS = ["januar", "februar", "mars", "april", "mai", "juni", "juli",
          "august", "september", "oktober", "november", "desember"]
esc = html.escape


def clean(text, limit=150):
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


epoch = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
seen, columns = set(), {}
for section, feeds in SECTIONS.items():
    items = []
    for source, url, color, _ in feeds:
        try:
            feed = feedparser.parse(url)
            entries = feed.entries[:PER_FEED]
            print(f"{source}: {len(entries)} saker")
        except Exception as ex:
            print("FEIL:", source, ex)
            continue
        for e in entries:
            link = e.get("link")
            if not link or link in seen:
                continue
            seen.add(link)
            img = image_of(e)
            items.append({
                "source": source, "color": color,
                "title": clean(e.get("title")), "link": link, "time": ts(e),
                "img": img if img and img.startswith("https://") else None,
            })
    items.sort(key=lambda i: i["time"] or epoch, reverse=True)
    columns[section] = items

oslo = ZoneInfo("Europe/Oslo")
n = datetime.datetime.now(oslo)
date_str = f"{DAYS[n.weekday()].capitalize()} {n.day}. {MONTHS[n.month - 1]} {n.year}"
updated = n.strftime("%d.%m.%Y kl. %H:%M")


def row(i):
    img = (f'<img src="{esc(i["img"])}" alt="" loading="lazy" referrerpolicy="no-referrer" '
           f'onerror="this.remove()">') if i["img"] else ""
    t = i["time"].astimezone(oslo).strftime("%d.%m. %H:%M") if i["time"] else ""
    return f"""<li data-src="{esc(i['source'])}"><a href="{esc(i['link'])}" target="_blank" rel="noopener">
<span class="thumb" style="--c:{i['color']}" data-i="{esc(i['source'][0])}">{img}</span>
<span class="txt"><span class="meta"><b style="color:{i['color']}">{esc(i['source'])}</b> · {t}</span>
<span class="title">{esc(i['title'])}</span></span></a></li>"""


cols = "".join(
    f'<section class="col" data-sec="{esc(name)}"><h2>{esc(name)}</h2><ul>{"".join(row(i) for i in items) or "<li class=empty>Ingen saker akkurat nå</li>"}</ul></section>'
    for name, items in columns.items())

tabs = '<button class="tab" data-sec="">Alle</button>' + "".join(
    f'<button class="tab" data-sec="{esc(s)}">{esc(s)}</button>' for s in SECTIONS)

settings = "".join(
    f'<div class="grp"><h4>{esc(sec)}</h4>' + "".join(
        f'<label><input type="checkbox" data-src="{esc(name)}" data-def="{1 if on else 0}"> {esc(name)}</label>'
        for name, _, _, on in feeds) + "</div>"
    for sec, feeds in SECTIONS.items())

CSS = """
:root{--bg:#faf8f3;--card:#fff;--fg:#1a1a1a;--muted:#666;--line:#d9d4c7;--accent:#8a1c1c}
@media (prefers-color-scheme: dark){:root{--bg:#141414;--card:#1e1e1e;--fg:#eee;--muted:#a0a0a0;--line:#333;--accent:#e07a7a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:Georgia,'Times New Roman',serif}
a{color:inherit;text-decoration:none}
header{text-align:center;padding:1.6rem 1rem .8rem;border-bottom:3px double var(--line);max-width:1200px;margin:0 auto}
header .date{font:600 .75rem system-ui,sans-serif;letter-spacing:.15em;text-transform:uppercase;color:var(--muted)}
header h1{margin:.2rem 0;font-size:clamp(2.4rem,8vw,4.5rem);letter-spacing:.03em;font-weight:900}
header p{margin:0;color:var(--muted);font-style:italic}
.bar{max-width:1200px;margin:0 auto;padding:1rem 1rem 0;font-family:system-ui,sans-serif}
.tabs{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center}
.tab,summary{font:600 .8rem system-ui,sans-serif;border:1px solid var(--line);background:var(--card);color:var(--fg);padding:.45rem 1rem;border-radius:999px;cursor:pointer;list-style:none}
.tab.on{background:var(--fg);color:var(--bg);border-color:var(--fg)}
details{margin-left:auto}
details[open] summary{background:var(--fg);color:var(--bg)}
.panel{margin-top:.8rem;padding:1rem;background:var(--card);border:1px solid var(--line);border-radius:8px;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem}
.panel h4{margin:0 0 .4rem;font-size:.75rem;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}
.panel label{display:block;font-size:.85rem;padding:.15rem 0;cursor:pointer}
.reset{grid-column:1/-1;justify-self:start;font:600 .75rem system-ui,sans-serif;background:none;border:1px solid var(--line);color:var(--fg);padding:.35rem .8rem;border-radius:999px;cursor:pointer}
main{max-width:1200px;margin:0 auto;padding:1.2rem 1rem;display:grid;grid-template-columns:repeat(3,1fr);gap:1.5rem;align-items:start}
.col h2{margin:0 0 .6rem;padding-bottom:.4rem;border-bottom:3px solid var(--fg);font-size:1.4rem;text-transform:uppercase;letter-spacing:.08em}
ul{list-style:none;margin:0;padding:0}
li{border-bottom:1px solid var(--line)}
li a{display:flex;gap:.8rem;padding:.8rem 0;align-items:flex-start}
li a:hover .title{color:var(--accent)}
.thumb{position:relative;flex:0 0 88px;height:66px;border-radius:4px;overflow:hidden;background:linear-gradient(135deg,var(--c),#1b1b1b)}
.thumb::after{content:attr(data-i);position:absolute;inset:0;display:grid;place-items:center;font:900 1.6rem system-ui,sans-serif;color:rgba(255,255,255,.4)}
.thumb img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:1}
.txt{display:flex;flex-direction:column;gap:.25rem;min-width:0}
.meta{font:.7rem system-ui,sans-serif;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.title{font-size:1rem;line-height:1.25;font-weight:600}
.empty{padding:1rem 0;color:var(--muted)}
main.single{grid-template-columns:1fr}
.single ul{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));column-gap:1.5rem}
footer{text-align:center;color:var(--muted);font:.8rem system-ui,sans-serif;padding:2rem 1rem}
@media(max-width:900px){main{grid-template-columns:1fr}details{margin-left:0}}
"""

JS = """
const KEY='avis-innstillinger';
const boxes=[...document.querySelectorAll('.panel input')];
const defOff=()=>boxes.filter(b=>b.dataset.def==='0').map(b=>b.dataset.src);
let st={sec:'',off:null};
try{st=Object.assign(st,JSON.parse(localStorage.getItem(KEY)||'{}'))}catch(e){}
if(!Array.isArray(st.off))st.off=defOff();
function apply(){
  document.querySelector('main').classList.toggle('single',!!st.sec);
  document.querySelectorAll('.col').forEach(c=>c.style.display=(!st.sec||c.dataset.sec===st.sec)?'':'none');
  document.querySelectorAll('li[data-src]').forEach(li=>li.style.display=st.off.includes(li.dataset.src)?'none':'');
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on',t.dataset.sec===st.sec));
  boxes.forEach(b=>b.checked=!st.off.includes(b.dataset.src));
  try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}
}
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{st.sec=t.dataset.sec;apply()});
boxes.forEach(b=>b.onchange=()=>{st.off=boxes.filter(x=>!x.checked).map(x=>x.dataset.src);apply()});
document.querySelector('.reset').onclick=()=>{st={sec:'',off:defOff()};apply()};
apply();
"""

page = f"""<!doctype html>
<html lang="nb"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(NAME)}</title>
<style>{CSS}</style></head>
<body>
<header><div class="date">{date_str}</div><h1>{esc(NAME)}</h1><p>{esc(TAGLINE)}</p></header>
<div class="bar">
<div class="tabs">{tabs}
<details><summary>Velg kilder</summary><div class="panel">{settings}<button class="reset" type="button">Nullstill</button></div></details>
</div></div>
<main>{cols}</main>
<footer>Sist oppdatert {updated}. Overskrifter og bilder tilhører kildene. Klikk for å lese hele saken der.</footer>
<script>{JS}</script>
</body></html>"""

out = pathlib.Path("docs")
out.mkdir(exist_ok=True)
(out / "index.html").write_text(page, encoding="utf-8")
(out / ".nojekyll").write_text("", encoding="utf-8")
print({k: len(v) for k, v in columns.items()})
