"""Dashboard design system: tokens, sidebar shell, command palette, theme toggle, PWA hooks."""
from __future__ import annotations

ICONS = {
    "today": '<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    "train": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M7 11v5c0 1.5 2.2 3 5 3s5-1.5 5-3v-5"/>',
    "outbox": '<path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4z"/>',
    "inbox": '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
    "chat": '<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-6.4A8 8 0 1 1 21 12z"/>',
    "signals": '<circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 0 1 0 8.4M7.8 16.2a6 6 0 0 1 0-8.4M19 5a10 10 0 0 1 0 14M5 19A10 10 0 0 1 5 5"/>',
    "discover": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "companies": '<path d="M3 21h18M5 21V7l7-4 7 4v14M9 9h1M9 13h1M14 9h1M14 13h1M10 21v-4h4v4"/>',
    "contacts": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5c2.2.7 3.5 2.6 3.5 5.5"/>',
    "campaigns": '<path d="M3 11v3a1 1 0 0 0 1 1h3l6 4V7L7 11H4a1 1 0 0 0-1 0z"/><path d="M17 8a5 5 0 0 1 0 8"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "usage": '<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',
    "controls": '<path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.8 0"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.4 8.3-8 9-4.6-.7-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "plug": '<path d="M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4"/>',
    "phone": '<rect x="6" y="2" width="12" height="20" rx="3"/><path d="M11 18h2"/>',
    "help": '<circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.5-3 4.5M12 17.5h.01"/>',
    "menu": '<path d="M4 6h16M4 12h16M4 18h16"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
}

NAV = [
    ("Work", [("Today", "/", "today"), ("Your company", "/train", "train"), ("Outbox", "/drafts", "outbox"),
              ("Inboxes", "/connections", "inbox"), ("Conversations", "/inbox", "chat")]),
    ("Pipeline", [("Signals", "/signals", "signals"), ("Discover", "/discover", "discover"),
                  ("Companies", "/companies", "companies"), ("Contacts", "/contacts", "contacts"),
                  ("Campaigns", "/campaigns", "campaigns")]),
    ("System", [("Activity", "/activity", "activity"), ("Usage", "/usage", "usage"), ("Controls", "/controls", "controls"),
                ("Compliance", "/compliance", "shield"), ("WhatsApp", "/whatsapp", "phone"),
                ("Settings", "/settings", "settings"), ("Help", "/help", "help")]),
]


def icon(name: str, size: int = 18) -> str:
    return (f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS.get(name, "")}</svg>')


CSS = """<style>
:root{--bg:#f6f7f9;--side:#fff;--panel:#fff;--panel2:#f1f3f6;--line:#e3e7ee;--text:#111827;--muted:#6b7686;--accent:#4f46e5;--accent-ink:#fff;--accent-soft:#eef0ff;--green:#15803d;--green-soft:#e7f6ec;--amber:#b45309;--amber-soft:#fdf3e1;--red:#b91c1c;--red-soft:#fdecec;--shadow:0 1px 2px #0000000d,0 8px 24px #0000000a;--r:12px}
:root[data-theme=dark]{--bg:#0b0d10;--side:#0f1216;--panel:#14181d;--panel2:#1a1f26;--line:#252b34;--text:#eceff4;--muted:#8b95a5;--accent:#8b8dfc;--accent-ink:#0b0d10;--accent-soft:#1d2040;--green:#4ade80;--green-soft:#10281a;--amber:#fbbf24;--amber-soft:#2b2310;--red:#f87171;--red-soft:#2d1416;--shadow:none}
*{box-sizing:border-box}html{color-scheme:light}:root[data-theme=dark]{color-scheme:dark}
body{margin:0;background:var(--bg);color:var(--text);font:14.5px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.app{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:100vh}
aside{position:sticky;top:0;height:100vh;overflow-y:auto;background:var(--side);border-right:1px solid var(--line);padding:18px 12px;display:flex;flex-direction:column;gap:4px}
.brand{display:flex;align-items:center;gap:10px;padding:2px 10px 4px;font-weight:800;font-size:18px;letter-spacing:-.4px;color:var(--text)}.brand:hover{text-decoration:none}
.tag-line{padding:0 10px 14px;color:var(--muted);font-size:12px}
.grp{padding:14px 10px 6px;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.nav a{display:flex;align-items:center;gap:11px;padding:8px 10px;border-radius:9px;color:var(--muted);font-weight:550}
.nav a:hover{background:var(--panel2);color:var(--text);text-decoration:none}
.nav a.on{background:var(--accent-soft);color:var(--accent)}
.side-foot{margin-top:auto;padding:12px 10px 0;color:var(--muted);font-size:12px;border-top:1px solid var(--line)}
.topbar{display:flex;align-items:center;gap:10px;padding:12px 32px;border-bottom:1px solid var(--line);background:var(--bg);position:sticky;top:0;z-index:5;backdrop-filter:blur(10px)}
.topbar .sp{flex:1}
.kbtn{display:flex;align-items:center;gap:10px;min-width:260px;padding:8px 12px;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--muted);cursor:pointer;font:inherit}
.kbtn kbd{margin-left:auto;font:11px ui-monospace,monospace;border:1px solid var(--line);border-radius:5px;padding:1px 6px;background:var(--panel2)}
.iconbtn{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;padding:0;border:1px solid var(--line);border-radius:10px;background:var(--panel);color:var(--text);cursor:pointer}
.pill{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:999px;font-size:12px;font-weight:650;background:var(--green-soft);color:var(--green)}
.pill.warn{background:var(--amber-soft);color:var(--amber)}.pill.bad{background:var(--red-soft);color:var(--red)}.pill.info{background:var(--accent-soft);color:var(--accent)}
.pill::before{content:"";width:6px;height:6px;border-radius:50%;background:currentColor}
main{padding:30px 32px 64px;max-width:1280px;width:100%}
h1{font-size:26px;letter-spacing:-.6px;margin:0 0 6px;font-weight:750}h2{font-size:16px;margin:0 0 10px;font-weight:700}h3{font-size:14px;margin:18px 0 8px}
.muted,small{color:var(--muted)}p{margin:0 0 12px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:18px 0}
.card,section{background:var(--panel);border:1px solid var(--line);border-radius:var(--r);padding:18px 20px;margin-bottom:16px;box-shadow:var(--shadow)}
.grid .card{margin:0}.card .lbl{color:var(--muted);font-size:12.5px;font-weight:600}.number{font-size:30px;font-weight:780;letter-spacing:-1px;margin-top:4px}
.card .sub{font-size:12px;color:var(--muted)}
input,textarea,select{font:inherit;color:var(--text);background:var(--bg);border:1px solid var(--line);border-radius:9px;padding:9px 11px;width:100%;margin:4px 0 10px;outline:none}
input:focus,textarea:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-soft)}
label{font-size:12.5px;font-weight:650;color:var(--muted)}textarea{min-height:96px}
button{font:inherit;font-weight:650;border:0;border-radius:9px;padding:9px 16px;background:var(--accent);color:var(--accent-ink);cursor:pointer}
button:hover{filter:brightness(1.08)}button.secondary{background:var(--panel2);color:var(--text);border:1px solid var(--line)}
table{width:100%;border-collapse:collapse;display:block;overflow-x:auto;font-size:13.5px}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:700}
td,th{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}tr:hover td{background:var(--panel2)}
form.inline{display:inline}.tag{color:var(--green);font-weight:650}.warning{color:var(--amber);font-weight:550}
pre,code{font:12.5px ui-monospace,SFMono-Regular,Menlo,monospace}pre{background:var(--panel2);border:1px solid var(--line);border-radius:10px;padding:14px;overflow:auto}
.steps{list-style:none;margin:0;padding:0}.steps li{display:flex;gap:12px;align-items:flex-start;padding:11px 0;border-bottom:1px solid var(--line)}.steps li:last-child{border:0}
.dot{flex:none;width:22px;height:22px;border-radius:50%;border:2px solid var(--line);display:grid;place-items:center;font-size:12px;margin-top:1px}.dot.done{background:var(--green);border-color:var(--green);color:#fff}
.bar{height:8px;border-radius:99px;background:var(--panel2);overflow:hidden}.bar>i{display:block;height:100%;background:var(--accent);border-radius:99px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
#pal{position:fixed;inset:0;background:#0008;display:none;align-items:flex-start;justify-content:center;padding-top:14vh;z-index:50}
#pal.open{display:flex}#pal .box{width:min(560px,92vw);background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:0 24px 64px #0006;overflow:hidden}
#pal input{margin:0;border:0;border-bottom:1px solid var(--line);border-radius:0;padding:16px 18px;font-size:16px;background:transparent}#pal input:focus{box-shadow:none}
#pal ul{list-style:none;margin:0;padding:6px;max-height:50vh;overflow:auto}#pal li a{display:flex;gap:10px;align-items:center;padding:9px 12px;border-radius:8px;color:var(--text)}
#pal li.sel a,#pal li a:hover{background:var(--accent-soft);color:var(--accent);text-decoration:none}#pal .hint{padding:8px 16px;font-size:12px;color:var(--muted);border-top:1px solid var(--line)}
.menu-btn{display:none}
@media(max-width:900px){.app{grid-template-columns:1fr}aside{position:fixed;z-index:40;width:270px;transform:translateX(-100%);transition:transform .2s}body.nav-open aside{transform:none;box-shadow:0 0 0 100vmax #0006}.menu-btn{display:inline-flex}.topbar{padding:10px 14px}.kbtn{min-width:0;flex:1}.kbtn kbd{display:none}main{padding:20px 14px 56px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style>"""

JS = """<script>
(function(){var d=document,r=d.documentElement;
function setTheme(t){r.dataset.theme=t;try{localStorage.setItem('zh-theme',t)}catch(e){}}
var t='light';try{t=localStorage.getItem('zh-theme')||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light')}catch(e){}
r.dataset.theme=t;
d.addEventListener('DOMContentLoaded',function(){
 var tb=d.getElementById('theme');if(tb)tb.onclick=function(){setTheme(r.dataset.theme==='dark'?'light':'dark')};
 var mb=d.getElementById('menu');if(mb)mb.onclick=function(){d.body.classList.toggle('nav-open')};
 var pal=d.getElementById('pal'),inp=d.getElementById('palq'),list=d.getElementById('pall'),items=[],sel=0;
 var pages=JSON.parse(d.getElementById('palpages').textContent);
 function render(q){q=(q||'').toLowerCase();items=pages.filter(function(p){return p[0].toLowerCase().indexOf(q)>-1});sel=0;
  list.innerHTML=items.map(function(p,i){return '<li class="'+(i==sel?'sel':'')+'"><a href="'+p[1]+'">'+p[0]+'</a></li>'}).join('')||'<li><a>No match</a></li>'}
 function open(){pal.classList.add('open');inp.value='';render('');inp.focus()}
 function close(){pal.classList.remove('open')}
 d.getElementById('kbtn').onclick=open;pal.onclick=function(e){if(e.target===pal)close()};
 inp.oninput=function(){render(inp.value)};
 inp.onkeydown=function(e){var li=list.children;if(e.key==='ArrowDown'||e.key==='ArrowUp'){e.preventDefault();sel=(sel+(e.key==='ArrowDown'?1:-1)+li.length)%li.length;for(var i=0;i<li.length;i++)li[i].className=i==sel?'sel':''}
  if(e.key==='Enter'&&items[sel])location.href=items[sel][1];if(e.key==='Escape')close()};
 d.addEventListener('keydown',function(e){if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();open()}
  if(e.key==='Escape')close();
  if(!/INPUT|TEXTAREA|SELECT/.test((e.target.tagName||''))&&e.key==='g'){d._g=Date.now()}
  else if(d._g&&Date.now()-d._g<900&&!/INPUT|TEXTAREA|SELECT/.test((e.target.tagName||''))){var m={t:'/',o:'/drafts',c:'/companies',d:'/discover',s:'/settings',h:'/help'}[e.key];d._g=0;if(m)location.href=m}});
 if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(function(){});
});})();
</script>"""

BRAND_SVG = ('<img src="/brand.svg" width="30" height="30" alt="">')


def render_shell(body: str, path: str = "/", badge: int = 0, status: tuple[str, str] = ("Private workspace", "")) -> str:
    import json
    nav_html = ""
    pages = []
    for group, links in NAV:
        nav_html += f'<div class="grp">{group}</div>'
        for label, href, ic in links:
            on = ' class="on"' if (href == path or (href != "/" and path.startswith(href))) else ""
            b = f'<span class="pill info" style="margin-left:auto;padding:1px 8px">{badge}</span>' if (label == "Outbox" and badge) else ""
            nav_html += f'<a href="{href}"{on}>{icon(ic)}<span>{label}</span>{b}</a>'
            pages.append([label, href])
    pages += [["Export companies (CSV)", "/export/companies.csv"], ["Export contacts (CSV)", "/export/contacts.csv"]]
    label, kind = status
    return (f'<!doctype html><html lang="en" data-theme="light"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#4f46e5">'
            f'<link rel="manifest" href="/manifest.webmanifest"><link rel="icon" href="/brand.svg" type="image/svg+xml">'
            f'<title>Zero Hawk</title>{CSS}<script>try{{var t=localStorage.getItem("zh-theme");if(t)document.documentElement.dataset.theme=t;else if(matchMedia("(prefers-color-scheme:dark)").matches)document.documentElement.dataset.theme="dark"}}catch(e){{}}</script></head>'
            f'<body><div class="app"><aside><a class="brand" href="/">{BRAND_SVG}<span>Zero Hawk</span></a>'
            f'<div class="tag-line">Find them. Understand them. Reach out.</div><nav class="nav">{nav_html}</nav>'
            f'<div class="side-foot">Local-first · your data stays on this machine</div></aside>'
            f'<div><div class="topbar"><button class="iconbtn menu-btn" id="menu" aria-label="Menu">{icon("menu")}</button>'
            f'<button class="kbtn" id="kbtn">{icon("search", 16)}<span>Search pages and actions…</span><kbd>Ctrl K</kbd></button><span class="sp"></span>'
            f'<span class="pill {kind}">{label}</span>'
            f'<button class="iconbtn" id="theme" aria-label="Toggle theme">{icon("sun")}</button></div>'
            f'<main>{body}</main></div></div>'
            f'<div id="pal"><div class="box"><input id="palq" placeholder="Go to…" autocomplete="off"><ul id="pall"></ul>'
            f'<div class="hint">↑↓ navigate · Enter open · Esc close · G then T/O/C/D/S/H jump</div></div></div>'
            f'<script id="palpages" type="application/json">{json.dumps(pages)}</script>{JS}</body></html>')


MANIFEST = {"name": "Zero Hawk", "short_name": "Zero Hawk", "start_url": "/", "display": "standalone",
            "background_color": "#0b0d10", "theme_color": "#4f46e5",
            "icons": [{"src": "/brand.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}]}
SERVICE_WORKER = ("self.addEventListener('install',e=>self.skipWaiting());"
                  "self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));"
                  "self.addEventListener('fetch',()=>{});")
