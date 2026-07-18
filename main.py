import os, json
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from supabase import create_client
import secrets

app = FastAPI()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "sensibilis2026")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://anme15.github.io", "http://localhost"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Sensibilis — Analytics Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
:root{--c:#8C1A2A;--n:#0D1C3F;--g:#B8924A;--iv:#F3EDE3;--ink:#160A0D;--ink2:#5a4850;--bdr:#ddd4c8;--surf:#fff;--page:#F3EDE3;--n-lt:#1a2d5a;--radius:10px;--shadow:0 2px 18px rgba(13,28,63,.10)}
@media(prefers-color-scheme:dark){:root{--surf:#111827;--page:#0a0f1c;--ink:#e8dfd4;--ink2:#9ca3af;--bdr:#1e2d4a;--n:#1e3a6a;--n-lt:#2a4f8a}}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,-apple-system,sans-serif;background:var(--page);color:var(--ink);min-height:100vh}
#login{display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px}
.login-box{background:var(--surf);border-radius:16px;padding:48px 40px;max-width:380px;width:100%;box-shadow:var(--shadow);text-align:center}
.login-box .brand{font-family:Georgia,serif;font-size:22px;color:var(--n);margin-bottom:6px}
.login-box .brand em{font-style:italic;color:var(--c)}
.login-box p{font-size:13px;color:var(--ink2);margin-bottom:28px}
.login-box input{width:100%;border:1.5px solid var(--bdr);border-radius:8px;padding:12px 14px;font-size:15px;background:var(--page);color:var(--ink);outline:none;transition:border .2s}
.login-box input:focus{border-color:var(--g)}
.login-box button{margin-top:14px;width:100%;background:var(--n);color:#fff;border:none;border-radius:8px;padding:13px;font-size:14px;font-weight:600;cursor:pointer}
.login-box button:hover{background:var(--n-lt)}
.login-err{color:var(--c);font-size:12px;margin-top:10px;min-height:18px}
#app{display:none}
header{background:var(--n);padding:0 32px;height:60px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
header .logo{font-family:Georgia,serif;font-size:17px;color:#fff}
.logo em{color:var(--g);font-style:italic}
header .meta{font-size:12px;color:rgba(255,255,255,.55);display:flex;gap:16px;align-items:center}
header .meta span{color:rgba(255,255,255,.75)}
header button.logout{background:none;border:1px solid rgba(255,255,255,.3);color:rgba(255,255,255,.7);border-radius:6px;padding:5px 12px;font-size:12px;cursor:pointer}
main{max-width:1100px;margin:0 auto;padding:32px 24px}
.section-title{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--ink2);margin:36px 0 14px}
.section-title:first-child{margin-top:0}
.kpi-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:8px}
.kpi{background:var(--surf);border-radius:var(--radius);padding:22px 24px;box-shadow:var(--shadow);border-top:3px solid transparent}
.kpi.navy{border-top-color:var(--n)}.kpi.gold{border-top-color:var(--g)}.kpi.burg{border-top-color:var(--c)}
.kpi .label{font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--ink2);margin-bottom:8px}
.kpi .value{font-size:34px;font-weight:700;color:var(--ink);line-height:1;font-variant-numeric:tabular-nums}
.kpi .sub{font-size:12px;color:var(--ink2);margin-top:6px}
.chart-grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px}
@media(max-width:700px){.chart-grid2{grid-template-columns:1fr}}
.card{background:var(--surf);border-radius:var(--radius);padding:24px;box-shadow:var(--shadow)}
.card h3{font-size:13px;font-weight:600;color:var(--ink);margin-bottom:4px}
.card .card-sub{font-size:11px;color:var(--ink2);margin-bottom:18px}
.chart-wrap{position:relative;width:100%;height:220px}
.recs{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.rec{background:var(--surf);border-radius:var(--radius);padding:20px 22px;box-shadow:var(--shadow);border-left:4px solid var(--g);display:flex;flex-direction:column;gap:8px}
.rec .rec-type{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--g)}
.rec .rec-type.warn{color:var(--c)}.rec .rec-type.ok{color:#2d7d46}
.rec h4{font-size:14px;font-weight:600;color:var(--ink);line-height:1.3}
.rec p{font-size:13px;color:var(--ink2);line-height:1.6}
.rec-warn{border-left-color:var(--c)}.rec-ok{border-left-color:#2d7d46}
.table-wrap{overflow-x:auto;border-radius:var(--radius)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{background:var(--n);color:#fff;padding:10px 14px;text-align:left;font-size:11px;letter-spacing:.08em;text-transform:uppercase;font-weight:600}
td{padding:10px 14px;border-bottom:1px solid var(--bdr);color:var(--ink)}
tr:hover td{background:rgba(184,146,74,.07)}
.dash-footer{text-align:center;padding:32px 0 16px;font-size:11px;color:var(--ink2)}
.loading{text-align:center;padding:80px;color:var(--ink2);font-size:14px}
</style>
</head>
<body>
<div id="login">
  <div class="login-box">
    <div class="brand"><em>S</em>ensibilis</div>
    <p>Analytics &amp; Insights &mdash; intern</p>
    <input type="password" id="pw" placeholder="Passwort" autocomplete="current-password">
    <button onclick="doLogin()">Anmelden</button>
    <div class="login-err" id="login-err"></div>
  </div>
</div>
<div id="app">
  <header>
    <div class="logo"><em>S</em>ensibilis &mdash; Dashboard</div>
    <div class="meta"><span id="last-update"></span><button class="logout" onclick="doLogout()">Abmelden</button></div>
  </header>
  <main><div id="content"><div class="loading">Daten werden geladen&hellip;</div></div></main>
  <div class="dash-footer">Sensibilis Analytics &mdash; nur zur internen Nutzung</div>
</div>
<script>
const CLR={navy:'#0D1C3F',gold:'#B8924A',burg:'#8C1A2A'};
const dark=()=>window.matchMedia('(prefers-color-scheme:dark)').matches;
const gc=()=>dark()?'rgba(255,255,255,.07)':'rgba(0,0,0,.06)';
let _pw='';
function doLogin(){const pw=document.getElementById('pw').value.trim();if(!pw){showErr('Bitte Passwort eingeben.');return;}_pw=pw;document.getElementById('login-err').textContent='Wird geprüft…';loadDashboard();}
document.getElementById('pw').addEventListener('keydown',e=>{if(e.key==='Enter')doLogin();});
function doLogout(){_pw='';document.getElementById('app').style.display='none';document.getElementById('login').style.display='flex';document.getElementById('pw').value='';}
function showErr(m){document.getElementById('login-err').textContent=m;}
async function loadDashboard(){
  try{
    const res=await fetch('/dashboard/data?token='+encodeURIComponent(_pw));
    if(res.status===401){showErr('Falsches Passwort.');_pw='';return;}
    if(!res.ok)throw new Error('HTTP '+res.status);
    const d=await res.json();
    d.top_pages_7d=d.top_pages_7d||[];d.top_clicks_30d=d.top_clicks_30d||[];d.daily_30d=d.daily_30d||[];
    document.getElementById('login').style.display='none';
    document.getElementById('app').style.display='block';
    document.getElementById('last-update').textContent='Stand: '+new Date().toLocaleString('de-DE',{dateStyle:'short',timeStyle:'short'});
    render(d);
  }catch(e){showErr('Verbindungsfehler: '+e.message);_pw='';}
}
function render(d){
  const el=document.getElementById('content');
  const trend=d.sessions_30d>0?Math.round(d.sessions_7d/d.sessions_30d*30/7*100-100):0;
  const tTxt=(trend>=0?'+':'')+trend+'% ggü. 30T-Schnitt';
  const topPage=d.top_pages_7d[0],topClick=d.top_clicks_30d[0];
  const recs=buildRecs(d,trend,topPage,topClick);
  const dL=d.daily_30d.map(r=>new Date(r[0]).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit'}));
  const dV=d.daily_30d.map(r=>r[1]);
  const pL=(d.top_pages_7d||[]).slice(0,7).map(r=>pN(r[0]));
  const pV=(d.top_pages_7d||[]).slice(0,7).map(r=>r[1]);
  const cL=(d.top_clicks_30d||[]).slice(0,7).map(r=>r[0]);
  const cV=(d.top_clicks_30d||[]).slice(0,7).map(r=>r[1]);
  el.innerHTML=`
    <div class="section-title">Überblick</div>
    <div class="kpi-row">
      <div class="kpi navy"><div class="label">Besuche 7 Tage</div><div class="value">${d.sessions_7d}</div><div class="sub">${tTxt}</div></div>
      <div class="kpi navy"><div class="label">Besuche 30 Tage</div><div class="value">${d.sessions_30d}</div><div class="sub">Gesamtreichweite</div></div>
      <div class="kpi gold"><div class="label">E-Mail-Leads</div><div class="value">${d.email_count}</div><div class="sub">in der Datenbank</div></div>
      <div class="kpi burg"><div class="label">Stärkste Seite (7T)</div><div class="value" style="font-size:20px;line-height:1.4">${topPage?pN(topPage[0]):'—'}</div><div class="sub">${topPage?topPage[1]+' Aufrufe':'keine Daten'}</div></div>
    </div>
    <div class="section-title">Besuchsverlauf — letzte 30 Tage</div>
    <div class="card"><h3>Tägliche Seitenaufrufe</h3><div class="card-sub">Gesamtvolumen pro Tag</div><div class="chart-wrap"><canvas id="cd"></canvas></div></div>
    <div class="chart-grid2">
      <div class="card"><h3>Top-Seiten (7 Tage)</h3><div class="card-sub">Meistbesuchte Bereiche</div><div class="chart-wrap"><canvas id="cp"></canvas></div></div>
      <div class="card"><h3>Top-Klicks (30 Tage)</h3><div class="card-sub">Welche Buttons werden gedrückt</div><div class="chart-wrap"><canvas id="cc"></canvas></div></div>
    </div>
    <div class="section-title">Handlungsempfehlungen</div>
    <div class="recs">${recs.map(recCard).join('')}</div>
    ${d.email_count>0?`<div class="section-title">Gesammelte E-Mails (${d.email_count})</div><div class="card"><div class="table-wrap"><table><thead><tr><th>Name</th><th>E-Mail</th><th>Quelle</th><th>Datum</th></tr></thead><tbody>${d.emails.map(eR).join('')}</tbody></table></div></div>`:''}
  `;
  const g=gc();
  const opts=(iy)=>({responsive:true,maintainAspectRatio:false,indexAxis:iy?'y':undefined,plugins:{legend:{display:false},tooltip:{backgroundColor:'rgba(13,28,63,.92)',titleColor:'#fff',bodyColor:'rgba(255,255,255,.75)',padding:10,cornerRadius:6}},scales:{x:{grid:{color:g},ticks:{color:'#888',font:{size:11}},border:{display:false}},y:{grid:{color:g},ticks:{color:'#888',font:{size:11}},border:{display:false}}}});
  new Chart(document.getElementById('cd'),{type:'line',data:{labels:dL,datasets:[{data:dV,borderColor:CLR.navy,borderWidth:2,backgroundColor:'rgba(13,28,63,.10)',fill:true,tension:0.35,pointRadius:3,pointHoverRadius:6,pointBackgroundColor:CLR.gold}]},options:opts(false)});
  new Chart(document.getElementById('cp'),{type:'bar',data:{labels:pL,datasets:[{data:pV,backgroundColor:pV.map((_,i)=>i===0?CLR.navy:'rgba(13,28,63,.35)'),borderRadius:4,borderSkipped:false}]},options:opts(true)});
  new Chart(document.getElementById('cc'),{type:'bar',data:{labels:cL,datasets:[{data:cV,backgroundColor:cV.map((_,i)=>i===0?CLR.gold:'rgba(184,146,74,.4)'),borderRadius:4,borderSkipped:false}]},options:opts(true)});
}
function buildRecs(d,trend,topPage,topClick){
  const r=[],pv30=d.sessions_30d,em=d.email_count,cv=pv30>0?(em/pv30*100).toFixed(1):0;
  if(em===0&&pv30>0)r.push({t:'warn',title:'Kontaktformular nicht aktiv',text:`${pv30} Besuche, aber 0 Leads. Formular noch nicht verdrahtet.`});
  else if(cv<2&&pv30>=20)r.push({t:'warn',title:`Konversionsrate niedrig (${cv}%)`,text:`Nur ${em} von ${pv30} Besuchen = Lead. CTA-Position prüfen.`});
  else if(em>0)r.push({t:'ok',title:`${em} Leads gesammelt (${cv}%)`,text:'Leads binnen 24h kontaktieren.'});
  if(trend>20)r.push({t:'ok',title:`Wachstumstrend +${trend}%`,text:'Letzte 7 Tage über dem Schnitt. Aktuellen Kanal weiterverfolgen.'});
  else if(trend<-20)r.push({t:'warn',title:`Besuchsrückgang ${trend}%`,text:'Woche unter Schnitt. Verlinkung oder noindex prüfen.'});
  if(topPage)r.push({t:'info',title:`"${pN(topPage[0])}" stärkster Einstieg`,text:'CTA auf dieser Seite besonders stark halten.'});
  r.push({t:'warn',title:'noindex noch aktiv',text:'Google indexiert die Seite noch nicht. Vor Go-Live entfernen.'});
  if(topClick)r.push({t:'ok',title:`Meistgeklickt: "${topClick[0]}"`,text:`${topClick[1]} Klicks — Formulierung als Vorlage nutzen.`});
  if(pv30<10)r.push({t:'info',title:'Noch wenig Daten',text:'Unter 10 Besuchen. In 2–3 Wochen aussagekräftig.'});
  return r;
}
function recCard(r){const cls=r.t==='warn'?'rec rec-warn':r.t==='ok'?'rec rec-ok':'rec';const lb=r.t==='warn'?'Handlungsbedarf':r.t==='ok'?'Positiv':'Info';return`<div class="${cls}"><div class="rec-type ${r.t}">${lb}</div><h4>${r.title}</h4><p>${r.text}</p></div>`;}
function pN(id){const m={home:'Startseite',beratung:'Beratung',preise:'Preise',zukunft:'KI & Zukunft',faq:'FAQ',kontakt:'Kontakt',blog:'Blog',kipass:'KI Pass',contentplaner:'Content Planer',webcheck:'Web Check',dms:'DMS',tools:'Tools',prozesse:'Prozesse',impressum:'Impressum',datenschutz:'Datenschutz',agb:'AGB',glossar:'Glossar'};return m[id]||id;}
function eR(r){const d=new Date(r.created_at).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',year:'2-digit'});return`<tr><td>${r.name||'—'}</td><td>${r.email}</td><td>${r.source||'—'}</td><td>${d}</td></tr>`;}
</script>
</body>
</html>"""

@app.get("/")
def root():
    return {"status": "Sensibilis Analytics API"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return DASHBOARD_HTML

@app.post("/track")
async def track(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Kein JSON")

    typ = data.get("type")
    if typ == "pageview":
        sb.table("sensibilis_pageviews").insert({
            "page": data.get("page", ""),
            "referrer": data.get("referrer", ""),
            "lang": data.get("lang", ""),
            "width": data.get("w"),
            "ts": data.get("ts"),
        }).execute()
    elif typ == "click":
        sb.table("sensibilis_clicks").insert({
            "label": data.get("label", ""),
            "page": data.get("page", ""),
            "ts": data.get("ts"),
        }).execute()

    return {"ok": True}

@app.post("/email")
async def save_email(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Kein JSON")

    email = data.get("email", "").strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="Ungültige E-Mail")

    try:
        sb.table("sensibilis_emails").insert({
            "email": email,
            "name": data.get("name", ""),
            "source": data.get("source", ""),
        }).execute()
    except Exception:
        pass  # UNIQUE-Constraint: E-Mail bereits vorhanden

    return {"ok": True}

@app.get("/dashboard/data")
def dashboard_data(token: str = Query(default="")):
    if not secrets.compare_digest(token.encode(), DASHBOARD_PASSWORD.encode()):
        raise HTTPException(status_code=401, detail="Nicht autorisiert")
    now = datetime.now(timezone.utc)
    d7 = (now - timedelta(days=7)).isoformat()
    d30 = (now - timedelta(days=30)).isoformat()

    pv7 = sb.table("sensibilis_pageviews").select("page, created_at").gte("created_at", d7).execute().data
    pv30 = sb.table("sensibilis_pageviews").select("page, created_at").gte("created_at", d30).execute().data
    cl30 = sb.table("sensibilis_clicks").select("label, page, created_at").gte("created_at", d30).execute().data
    emails = sb.table("sensibilis_emails").select("email, name, created_at").order("created_at", desc=True).limit(50).execute().data

    # Seitenaufrufe aggregieren
    pages7 = {}
    for r in pv7:
        pages7[r["page"]] = pages7.get(r["page"], 0) + 1

    pages30 = {}
    for r in pv30:
        pages30[r["page"]] = pages30.get(r["page"], 0) + 1

    # Klicks aggregieren
    clicks = {}
    for r in cl30:
        clicks[r["label"]] = clicks.get(r["label"], 0) + 1

    # Tagesverauf letzte 30 Tage
    tage = {}
    for r in pv30:
        tag = r["created_at"][:10]
        tage[tag] = tage.get(tag, 0) + 1

    return {
        "sessions_7d": len(pv7),
        "sessions_30d": len(pv30),
        "top_pages_7d": sorted(pages7.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_pages_30d": sorted(pages30.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_clicks_30d": sorted(clicks.items(), key=lambda x: x[1], reverse=True)[:10],
        "daily_30d": sorted(tage.items()),
        "emails": emails,
        "email_count": len(emails),
    }
