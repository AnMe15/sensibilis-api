import os, json, re
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from supabase import create_client
import secrets, httpx
from bs4 import BeautifulSoup

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
<title>Sensibilis — Analytics</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
<style>
:root{
  --c:#8C1A2A;--n:#0D1C3F;--g:#B8924A;--gl:#D4AB68;--iv:#F3EDE3;
  --ok:#1a6b3a;--ok-bg:#edf7f1;--warn:#8C1A2A;--warn-bg:#fdf2f2;--info:#1a3f6b;--info-bg:#eef3fb;
  --ink:#160A0D;--ink2:#6b5860;--bdr:#e2d9d0;
  --surf:#ffffff;--page:#f5ede3;
  --radius:12px;--shadow:0 1px 12px rgba(13,28,63,.08);--shadow-lg:0 4px 32px rgba(13,28,63,.13);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--page);color:var(--ink);min-height:100vh;font-size:14px}

#login{display:flex;align-items:center;justify-content:center;min-height:100vh;background:linear-gradient(135deg,var(--n) 0%,#1a3a72 100%)}
.lbox{background:#fff;border-radius:20px;padding:52px 44px;max-width:400px;width:90%;box-shadow:var(--shadow-lg);text-align:center}
.lbox-brand{font-family:Georgia,serif;font-size:26px;color:var(--n);margin-bottom:4px}
.lbox-brand em{color:var(--c);font-style:italic}
.lbox-sub{font-size:12px;color:var(--ink2);letter-spacing:.06em;text-transform:uppercase;margin-bottom:32px}
.lbox input{width:100%;border:1.5px solid var(--bdr);border-radius:10px;padding:14px 16px;font-size:15px;color:var(--ink);outline:none;transition:.2s;background:var(--page)}
.lbox input:focus{border-color:var(--g);background:#fff}
.lbox-btn{margin-top:12px;width:100%;background:linear-gradient(135deg,var(--n),#1a3a72);color:#fff;border:none;border-radius:10px;padding:14px;font-size:14px;font-weight:600;cursor:pointer;transition:.2s}
.lbox-btn:hover{opacity:.9}
.lerr{color:var(--c);font-size:12px;margin-top:10px;min-height:18px}

#app{display:none;min-height:100vh}
header{background:linear-gradient(135deg,var(--n) 0%,#1a3a72 100%);padding:0 28px;height:68px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;box-shadow:0 2px 20px rgba(13,28,63,.3)}
.hlogo{display:flex;align-items:center;gap:12px}
.hlogo-svg{width:36px;height:36px;flex-shrink:0}
.hlogo-text{font-family:Georgia,serif;font-size:19px;color:#fff;letter-spacing:-.01em}
.hlogo-text em{color:var(--gl);font-style:italic}
.hbadge{font-size:10px;background:rgba(255,255,255,.15);color:rgba(255,255,255,.75);padding:3px 9px;border-radius:20px;letter-spacing:.08em;margin-left:2px}
.hmeta{display:flex;align-items:center;gap:12px}
/* ZEITRAUM-WÄHLER */
.period-bar{display:flex;align-items:center;gap:6px;background:rgba(255,255,255,.1);border-radius:10px;padding:4px}
.pbtn{background:none;border:none;color:rgba(255,255,255,.65);font-size:12px;font-weight:600;padding:5px 12px;border-radius:7px;cursor:pointer;transition:.15s;white-space:nowrap}
.pbtn:hover{color:#fff;background:rgba(255,255,255,.12)}
.pbtn.active{background:rgba(255,255,255,.22);color:#fff}
.pbtn-sep{width:1px;height:16px;background:rgba(255,255,255,.2)}
.htime{font-size:11px;color:rgba(255,255,255,.45)}
.htime span{color:rgba(255,255,255,.7)}
.hlogout{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);color:rgba(255,255,255,.7);border-radius:8px;padding:6px 14px;font-size:12px;cursor:pointer;transition:.2s}
.hlogout:hover{background:rgba(255,255,255,.2);color:#fff}

main{max-width:1200px;margin:0 auto;padding:40px 28px 80px}

/* SECTION TITLE — groß und sichtbar */
.sec{margin-top:48px}.sec:first-child{margin-top:0}
.sec-title{font-size:18px;font-weight:700;color:var(--n);margin-bottom:20px;display:flex;align-items:center;gap:12px;letter-spacing:-.01em}
.sec-title .sec-icon{font-size:20px;opacity:.8}
.sec-title::after{content:'';flex:1;height:1.5px;background:var(--bdr);margin-left:4px}
.sec-sub{font-size:12px;color:var(--ink2);margin-top:-14px;margin-bottom:18px}

/* KPI */
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
@media(max-width:800px){.kpi-grid{grid-template-columns:repeat(2,1fr)}}
.kpi{background:var(--surf);border-radius:var(--radius);padding:24px 22px 20px;box-shadow:var(--shadow);position:relative;overflow:hidden}
.kpi::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.kpi.k-n::before{background:var(--n)}.kpi.k-g::before{background:var(--g)}.kpi.k-c::before{background:var(--c)}.kpi.k-ok::before{background:var(--ok)}
.kpi-icon{font-size:22px;margin-bottom:10px;opacity:.7}
.kpi-label{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink2);margin-bottom:6px}
.kpi-value{font-size:40px;font-weight:800;color:var(--ink);line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.kpi-sub{font-size:12px;color:var(--ink2);margin-top:8px}
.badge-up{color:var(--ok);font-weight:700}.badge-dn{color:var(--c);font-weight:700}.badge-neu{color:var(--info);font-weight:700}

/* FUNNEL */
.funnel{background:var(--surf);border-radius:var(--radius);padding:32px 40px;box-shadow:var(--shadow);display:flex;align-items:center}
.f-step{flex:1;text-align:center;position:relative}
.f-step::after{content:'→';position:absolute;right:-12px;top:40%;transform:translateY(-50%);color:var(--bdr);font-size:22px}
.f-step:last-child::after{display:none}
.f-bar{height:6px;border-radius:3px;margin:12px auto 0;background:var(--bdr);max-width:80px}
.f-bar-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--n),var(--g))}
.f-num{font-size:36px;font-weight:800;color:var(--n);letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.f-label{font-size:12px;color:var(--ink2);margin-top:6px;font-weight:500}
.f-pct{font-size:12px;font-weight:700;color:var(--g);margin-top:2px}

/* CARDS */
.chart-row{display:grid;grid-template-columns:2fr 1fr;gap:16px}
.chart-row-half{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:800px){.chart-row,.chart-row-half{grid-template-columns:1fr}}
.card{background:var(--surf);border-radius:var(--radius);padding:24px;box-shadow:var(--shadow)}
.card-title{font-size:14px;font-weight:700;color:var(--ink);margin-bottom:4px}
.card-sub{font-size:11px;color:var(--ink2);margin-bottom:18px}
.chart-wrap{position:relative;height:200px}
.chart-wrap.donut{height:180px}

/* SEITEN-PERFORMANCE TABELLE */
.perf-table{width:100%;border-collapse:collapse;font-size:13px}
.perf-table th{background:var(--n);color:#fff;padding:10px 14px;text-align:left;font-size:10px;letter-spacing:.1em;text-transform:uppercase;font-weight:600}
.perf-table th:not(:first-child){text-align:center}
.perf-table td{padding:11px 14px;border-bottom:1px solid var(--bdr);color:var(--ink);vertical-align:middle}
.perf-table td:not(:first-child){text-align:center;font-variant-numeric:tabular-nums;color:var(--ink2)}
.perf-table tr:last-child td{border-bottom:none}
.perf-table tr:hover td{background:rgba(184,146,74,.05)}
.perf-badge{display:inline-block;font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px}
.perf-gut{background:var(--ok-bg);color:var(--ok)}
.perf-ok{background:var(--info-bg);color:var(--info)}
.perf-schwach{background:var(--warn-bg);color:var(--warn)}

/* SIMPLE LIST */
.clist{display:flex;flex-direction:column;gap:10px}
.citem{display:flex;align-items:center;gap:10px}
.crank{font-size:11px;font-weight:700;color:var(--ink2);width:18px;text-align:center;flex-shrink:0}
.cname{flex:1;font-size:13px;color:var(--ink);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cbar-wrap{width:90px;flex-shrink:0}
.cbar{height:5px;background:var(--bdr);border-radius:3px;overflow:hidden}
.cbar-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--g),#e8b84b)}
.ccount{font-size:11px;color:var(--ink2);width:34px;text-align:right;font-variant-numeric:tabular-nums;flex-shrink:0}

/* SIMPLE PAGE LIST */
.ptable{width:100%;border-collapse:collapse}
.ptable td{padding:9px 0;border-bottom:1px solid var(--bdr);font-size:13px}
.ptable tr:last-child td{border-bottom:none}
.ptable .pname{color:var(--ink);font-weight:500}
.ptable .pcount{color:var(--ink2);text-align:right;font-variant-numeric:tabular-nums;width:48px}
.ptable .pbar-wrap{width:100px;padding:0 10px}
.pbar{height:5px;background:var(--bdr);border-radius:3px;overflow:hidden}
.pbar-fill{height:100%;border-radius:3px;background:linear-gradient(90deg,var(--n),#2a5aaa)}

/* EMPFEHLUNGEN */
.rec-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px}
.rec{background:var(--surf);border-radius:var(--radius);padding:20px 22px;box-shadow:var(--shadow);display:flex;gap:14px}
.rec-icon{font-size:20px;flex-shrink:0;width:38px;height:38px;border-radius:9px;display:flex;align-items:center;justify-content:center}
.rec.r-warn .rec-icon{background:var(--warn-bg)}.rec.r-ok .rec-icon{background:var(--ok-bg)}.rec.r-info .rec-icon{background:var(--info-bg)}
.rec-type{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px}
.rec.r-warn .rec-type{color:var(--warn)}.rec.r-ok .rec-type{color:var(--ok)}.rec.r-info .rec-type{color:var(--info)}
.rec h4{font-size:13px;font-weight:700;color:var(--ink);margin-bottom:4px;line-height:1.3}
.rec p{font-size:12px;color:var(--ink2);line-height:1.65}

/* EMAIL TABLE */
.etable{width:100%;border-collapse:collapse;font-size:13px}
.etable th{background:var(--n);color:#fff;padding:10px 14px;text-align:left;font-size:10px;letter-spacing:.1em;text-transform:uppercase;font-weight:600}
.etable td{padding:11px 14px;border-bottom:1px solid var(--bdr);color:var(--ink)}
.etable tr:last-child td{border-bottom:none}
.etable tr:hover td{background:rgba(184,146,74,.06)}
.etable .pill{display:inline-block;background:var(--info-bg);color:var(--info);font-size:10px;font-weight:600;padding:2px 8px;border-radius:20px}

.empty-state{text-align:center;padding:40px 24px;color:var(--ink2)}
.empty-state .e-icon{font-size:36px;margin-bottom:10px;opacity:.4}
.empty-state p{font-size:13px;line-height:1.7}

/* SEO/GEO */
.seo-score-bar{background:var(--surf);border-radius:var(--radius);padding:24px 28px;box-shadow:var(--shadow);display:flex;align-items:center;gap:28px;margin-bottom:16px}
.seo-score-ring{position:relative;width:80px;height:80px;flex-shrink:0}
.seo-score-ring svg{transform:rotate(-90deg)}
.seo-score-num{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;color:var(--n)}
.seo-score-info h3{font-size:15px;font-weight:700;color:var(--ink);margin-bottom:4px}
.seo-score-info p{font-size:12px;color:var(--ink2);line-height:1.6}
.seo-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
.seo-item{background:var(--surf);border-radius:10px;padding:16px 18px;box-shadow:var(--shadow);display:flex;gap:12px;align-items:flex-start}
.seo-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:4px}
.seo-dot.ok{background:var(--ok)}.seo-dot.warn{background:var(--g)}.seo-dot.error{background:var(--c)}.seo-dot.info{background:var(--info)}
.seo-body .seo-label{font-size:12px;font-weight:700;color:var(--ink);margin-bottom:2px}
.seo-body .seo-cat{font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--ink2);margin-bottom:4px}
.seo-body .seo-detail{font-size:12px;color:var(--ink2);line-height:1.5}
.seo-body .seo-tip{font-size:11px;color:var(--c);margin-top:5px;font-style:italic}
.seo-sep{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--ink2);margin:20px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--bdr)}

.dash-foot{text-align:center;padding:20px;font-size:11px;color:var(--ink2);opacity:.5}
.loading{text-align:center;padding:80px;color:var(--ink2)}
</style>
</head>
<body>
<div id="login">
  <div class="lbox">
    <div class="lbox-brand"><em>S</em>ensibilis</div>
    <div class="lbox-sub">Analytics &amp; Insights</div>
    <input type="password" id="pw" placeholder="Passwort eingeben" autocomplete="current-password">
    <button class="lbox-btn" onclick="doLogin()">Anmelden</button>
    <div class="lerr" id="lerr"></div>
  </div>
</div>
<div id="app">
  <header>
    <div class="hlogo">
      <svg class="hlogo-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
        <circle cx="16" cy="16" r="14" fill="none" stroke="#fff" stroke-width="1.2" opacity=".6"/>
        <circle cx="16" cy="16" r="9.5" fill="none" stroke="#B8924A" stroke-width="0.8" opacity=".9"/>
        <circle cx="16" cy="3"  r="1.2" fill="#B8924A"/><circle cx="16" cy="29" r="1.2" fill="#B8924A"/>
        <circle cx="3"  cy="16" r="1.2" fill="#B8924A"/><circle cx="29" cy="16" r="1.2" fill="#B8924A"/>
        <path d="M 19 10 C 19 7 13 7 12 10 C 11 13 17 15 16.5 17" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M 17 15.5 C 18 17 21 18.5 20.5 21.5 C 20 24 14 24.5 13 22" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round"/>
      </svg>
      <span class="hlogo-text"><em>S</em>ensibilis</span>
      <span class="hbadge">Analytics</span>
    </div>
    <div class="hmeta">
      <div class="period-bar">
        <button class="pbtn" onclick="setPeriod(7)" id="p7">7 Tage</button>
        <div class="pbtn-sep"></div>
        <button class="pbtn active" onclick="setPeriod(30)" id="p30">30 Tage</button>
        <div class="pbtn-sep"></div>
        <button class="pbtn" onclick="setPeriod(90)" id="p90">90 Tage</button>
        <div class="pbtn-sep"></div>
        <button class="pbtn" onclick="toggleCompare()" id="pcmp">&#8646; Vergleich</button>
      </div>
      <div class="htime">Stand: <span id="ts"></span></div>
      <button class="hlogout" onclick="doLogout()">Abmelden</button>
    </div>
  </header>
  <main><div id="content"><div class="loading">Daten werden geladen&hellip;</div></div></main>
  <div class="dash-foot">Sensibilis Analytics &mdash; nur zur internen Nutzung</div>
</div>
<script>
const N='#0D1C3F',G='#B8924A',C='#8C1A2A';
let _pw='';
const $=id=>document.getElementById(id);
let curDays=30,curCompare=false;
function doLogin(){const pw=$('pw').value.trim();if(!pw){showE('Bitte Passwort eingeben.');return;}_pw=pw;$('lerr').textContent='Wird geprüft…';load();}
$('pw').addEventListener('keydown',e=>{if(e.key==='Enter')doLogin();});
function doLogout(){_pw='';$('app').style.display='none';$('login').style.display='flex';$('pw').value='';}
function showE(m){$('lerr').textContent=m;}

function setPeriod(d){
  curDays=d;
  ['p7','p30','p90'].forEach(id=>$('p'+id.slice(1))&&$('p'+id.slice(1)).classList.remove('active'));
  $('p'+d)&&$('p'+d).classList.add('active');
  load();
}
function toggleCompare(){
  curCompare=!curCompare;
  const b=$('pcmp');
  if(b){b.classList.toggle('active',curCompare);b.textContent=curCompare?'✓ Vergleich':'⇄ Vergleich';}
  load();
}

async function load(){
  try{
    const [r, rs] = await Promise.all([
      fetch('/dashboard/data?token='+encodeURIComponent(_pw)+'&days='+curDays+'&compare='+(curCompare?'true':'false')),
      fetch('/dashboard/seo?token='+encodeURIComponent(_pw))
    ]);
    if(r.status===401){showE('Falsches Passwort.');_pw='';return;}
    if(!r.ok)throw new Error('HTTP '+r.status);
    const d=await r.json();
    const seo=rs.ok?await rs.json():{checks:[],score:null};
    ['top_pages_7d','top_clicks_30d','daily_30d','emails','traffic_sources',
     'avg_time_per_page','avg_scroll_per_page','exit_pages','entry_pages','page_performance'
    ].forEach(k=>{if(!d[k])d[k]=[];});
    d.devices=d.devices||{};
    $('login').style.display='none';$('app').style.display='block';
    $('ts').textContent=new Date().toLocaleString('de-DE',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'});
    render(d,seo);
  }catch(e){showE('Fehler: '+e.message);_pw='';}
}

function deltaBadge(cur,prev,label){
  if(!curCompare||prev==null)return '';
  if(prev===0)return cur>0?`<span class="badge-up">neu</span>`:'';
  const pct=Math.round((cur-prev)/prev*100);
  return pct>0?`<span class="badge-up">↑ +${pct}% ${label}</span>`:pct<0?`<span class="badge-dn">↓ ${pct}% ${label}</span>`:`<span class="badge-neu">= ${label}</span>`;
}
function render(d,seo){
  const el=$('content');
  const pvMain=d.sessions_30d,em=d.email_count,k30=d.kontakt_30d||0;
  const pv7=d.sessions_7d;
  const trend=pvMain>0?Math.round(pv7/pvMain*30/7*100-100):0;
  const conv=pvMain>0?(em/pvMain*100).toFixed(1):0;
  const tBadge=trend>0?`<span class="badge-up">↑ +${trend}%</span>`:trend<0?`<span class="badge-dn">↓ ${trend}%</span>`:`<span class="badge-neu">neu</span>`;
  const topPage=d.top_pages_7d[0],topClick=d.top_clicks_30d[0];
  const maxC=d.top_clicks_30d[0]?d.top_clicks_30d[0][1]:1;
  const recs=buildRecs(d,trend,topPage,topClick,conv);
  const dBesMain=deltaBadge(pvMain,d.prev_sessions,'vs. Vorperiode');
  const dEm=deltaBadge(em,d.prev_emails,'vs. Vorperiode');
  const periodLabel=curDays===7?'7 Tage':curDays===90?'90 Tage':'30 Tage';

  el.innerHTML=`
  <div class="sec">
    <div class="sec-title"><span class="sec-icon">📊</span> Überblick${curCompare?'<span style="font-size:12px;font-weight:400;color:var(--ink2);margin-left:8px">mit Vergleich zur Vorperiode</span>':''}</div>
    <div class="kpi-grid">
      <div class="kpi k-n"><div class="kpi-icon">👁</div><div class="kpi-label">Besuche — ${periodLabel}</div><div class="kpi-value">${pvMain}</div><div class="kpi-sub">${dBesMain||tBadge+' ggü. Wochenschnitt'}</div></div>
      <div class="kpi k-n"><div class="kpi-icon">📅</div><div class="kpi-label">Besuche — 7 Tage</div><div class="kpi-value">${pv7}</div><div class="kpi-sub">Aktueller Trend</div></div>
      <div class="kpi k-g"><div class="kpi-icon">✉️</div><div class="kpi-label">E-Mail-Leads</div><div class="kpi-value">${em}</div><div class="kpi-sub">${dEm||( pvMain>0?`Konversion: <strong>${conv}%</strong>`:'Tracking läuft')}</div></div>
      <div class="kpi k-c"><div class="kpi-icon">🏆</div><div class="kpi-label">Stärkste Seite (7T)</div><div class="kpi-value" style="font-size:${topPage?'20px':'36px'};line-height:1.35">${topPage?pN(topPage[0]):'—'}</div><div class="kpi-sub">${topPage?topPage[1]+' Aufrufe':'keine Daten'}</div></div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-title"><span class="sec-icon">🎯</span> Conversion-Funnel — 30 Tage</div>
    <div class="sec-sub">Alle drei Werte beziehen sich auf denselben 30-Tage-Zeitraum</div>
    <div class="funnel">
      ${fStep('Besucher gesamt',pvMain,100)}
      ${fStep('Kontaktseite besucht',k30,pvMain>0?Math.round(k30/pvMain*100):0)}
      ${fStep('E-Mail-Lead',em,pvMain>0?Math.round(em/pvMain*100):0)}
    </div>
  </div>

  <div class="sec">
    <div class="sec-title"><span class="sec-icon">👥</span> Wer kommt — 30 Tage</div>
    <div class="chart-row-half" style="margin-bottom:16px">
      <div class="card"><div class="card-title">Geräte</div><div class="card-sub">Mobile / Tablet / Desktop</div><div class="chart-wrap donut"><canvas id="cdev"></canvas></div></div>
      <div class="card"><div class="card-title">Neu vs. Wiederkehrend</div><div class="card-sub">Einzigartige Sessions</div><div class="chart-wrap donut"><canvas id="cnew"></canvas></div></div>
    </div>
    <div class="card">
      <div class="card-title">Traffic-Quellen</div><div class="card-sub">Woher kommen die Besucher</div>
      ${d.traffic_sources.length>0?`<div class="clist">${d.traffic_sources.map((s,i)=>{const tot=d.traffic_sources.reduce((a,x)=>a+x[1],0);return`<div class="citem"><div class="crank">${i+1}</div><div class="cname">${srcLabel(s[0])}</div><div class="cbar-wrap"><div class="cbar"><div class="cbar-fill" style="width:${Math.round(s[1]/tot*100)}%;background:linear-gradient(90deg,var(--n),#3a6aaa)"></div></div></div><div class="ccount">${s[1]}</div></div>`;}).join('')}</div>`:`<div class="empty-state"><div class="e-icon">📡</div><p>Noch keine Quellen-Daten.</p></div>`}
    </div>
  </div>

  <div class="sec">
    <div class="sec-title"><span class="sec-icon">📈</span> Besuchsverlauf — 30 Tage</div>
    <div class="card"><div class="card-title">Tägliche Seitenaufrufe</div><div class="card-sub">Gesamtvolumen pro Tag</div><div class="chart-wrap"><canvas id="cd"></canvas></div></div>
  </div>

  <div class="sec">
    <div class="sec-title"><span class="sec-icon">📄</span> Seiten-Performance — 30 Tage</div>
    <div class="sec-sub">Welche Seiten ranken gut (viele Besuche, lange Verweildauer, hohe Scroll-Tiefe) — welche nicht</div>
    <div class="card" style="padding:0;overflow:hidden">
      ${d.page_performance.length>0?`
      <table class="perf-table">
        <thead><tr><th>Seite</th><th>Aufrufe</th><th>Ø Zeit</th><th>Ø Scroll</th><th>Exit-Rate</th><th>Bewertung</th></tr></thead>
        <tbody>${d.page_performance.map(p=>{
          const score=perfScore(p);
          return`<tr><td><strong>${pN(p.page)}</strong></td><td>${p.visits}</td><td>${p.avg_time?fmtTime(p.avg_time):'—'}</td><td>${p.avg_scroll?p.avg_scroll+'%':'—'}</td><td>${p.exit_rate?p.exit_rate+'%':'—'}</td><td><span class="perf-badge perf-${score.cls}">${score.label}</span></td></tr>`;
        }).join('')}</tbody>
      </table>`:`<div class="empty-state"><div class="e-icon">📄</div><p>Noch keine Seiten-Daten.</p></div>`}
    </div>
  </div>

  <div class="sec">
    <div class="sec-title"><span class="sec-icon">🚪</span> Einstiegs- & Exit-Seiten — 30 Tage</div>
    <div class="chart-row-half">
      <div class="card">
        <div class="card-title">Einstiegsseiten</div><div class="card-sub">Erste Seite einer Session</div>
        ${d.entry_pages.length>0?`<table class="ptable">${d.entry_pages.map(p=>`<tr><td class="pname">${pN(p[0])}</td><td class="pbar-wrap"><div class="pbar"><div class="pbar-fill" style="width:${Math.round(p[1]/d.entry_pages[0][1]*100)}%"></div></div></td><td class="pcount">${p[1]}</td></tr>`).join('')}</table>`:`<div class="empty-state"><div class="e-icon">🚀</div><p>Noch keine Daten.</p></div>`}
      </div>
      <div class="card">
        <div class="card-title">Exit-Seiten</div><div class="card-sub">Letzte Seite vor dem Verlassen</div>
        ${d.exit_pages.length>0?`<table class="ptable">${d.exit_pages.map(p=>`<tr><td class="pname">${pN(p[0])}</td><td class="pbar-wrap"><div class="pbar"><div class="pbar-fill" style="width:${Math.round(p[1]/d.exit_pages[0][1]*100)}%;background:linear-gradient(90deg,var(--c),#c0392b)"></div></div></td><td class="pcount">${p[1]}</td></tr>`).join('')}</table>`:`<div class="empty-state"><div class="e-icon">🚪</div><p>Noch keine Daten.</p></div>`}
      </div>
    </div>
  </div>

  <div class="sec">
    <div class="sec-title"><span class="sec-icon">🖱️</span> Button-Klicks — 30 Tage</div>
    <div class="card">
      ${d.top_clicks_30d.length>0?`<div class="clist">${d.top_clicks_30d.slice(0,10).map((c,i)=>`<div class="citem"><div class="crank">${i+1}</div><div class="cname">${c[0]}</div><div class="cbar-wrap"><div class="cbar"><div class="cbar-fill" style="width:${Math.round(c[1]/maxC*100)}%"></div></div></div><div class="ccount">${c[1]}</div></div>`).join('')}</div>`:`<div class="empty-state"><div class="e-icon">🖱️</div><p>Noch keine Klick-Daten.<br>Alle Buttons werden automatisch erfasst.</p></div>`}
    </div>
  </div>

  <div class="sec">
    <div class="sec-title"><span class="sec-icon">⚠️</span> Handlungsempfehlungen</div>
    <div class="rec-grid">${recs.map(recCard).join('')}</div>
  </div>

  <div class="sec">
    <div class="sec-title"><span class="sec-icon">🔍</span> SEO & GEO — Live-Check der Website</div>
    <div class="sec-sub">Wird bei jedem Dashboard-Aufruf automatisch gegen die Live-Seite geprüft</div>
    ${seoSection(seo)}
  </div>

  <div class="sec">
    <div class="sec-title"><span class="sec-icon">⚡</span> PageSpeed Insights</div>
    <div class="sec-sub">Letzter Test manuell durchführen — Ergebnis öffnet direkt im Browser</div>
    <div class="card" style="display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;">
      <div>
        <div style="font-size:13px;font-weight:700;color:var(--ink);margin-bottom:4px;">Google PageSpeed — Sensibilis Website</div>
        <div style="font-size:12px;color:var(--ink2);line-height:1.6;">Testet Ladezeit, Barrierefreiheit, Best Practices und SEO.<br>Mobil &amp; Desktop in einem Bericht.</div>
      </div>
      <a href="https://pagespeed.web.dev/analysis?url=https%3A%2F%2Fanme15.github.io%2FSensibilis-Ki%2F" target="_blank" rel="noopener" style="display:inline-block;background:linear-gradient(135deg,var(--n),#1a3a72);color:#fff;text-decoration:none;border-radius:10px;padding:12px 22px;font-size:13px;font-weight:600;white-space:nowrap;flex-shrink:0;">Test jetzt starten &#x2192;</a>
    </div>
  </div>

  ${em>0?`
  <div class="sec">
    <div class="sec-title"><span class="sec-icon">✉️</span> E-Mail-Leads (${em})</div>
    <div class="card" style="padding:0;overflow:hidden">
      <table class="etable"><thead><tr><th>Name</th><th>E-Mail</th><th>Quelle</th><th>Datum</th></tr></thead>
      <tbody>${d.emails.map(eRow).join('')}</tbody></table>
    </div>
  </div>`:''}
  `;

  const g='rgba(0,0,0,.05)';
  const ttOpts={backgroundColor:'rgba(13,28,63,.92)',titleColor:'#fff',bodyColor:'rgba(255,255,255,.75)',padding:10,cornerRadius:6,displayColors:false};
  const dL=d.daily_30d.map(r=>new Date(r[0]).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit'}));
  const dV=d.daily_30d.map(r=>r[1]);
  if(dL.length){
    new Chart($('cd'),{type:'line',data:{labels:dL,datasets:[{data:dV,borderColor:N,borderWidth:2,backgroundColor:'rgba(13,28,63,.08)',fill:true,tension:0.4,pointRadius:dV.length<15?4:0,pointHoverRadius:6,pointBackgroundColor:G,pointBorderColor:N,pointBorderWidth:1.5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:ttOpts},scales:{x:{grid:{color:g},ticks:{color:'#999',font:{size:10}},border:{display:false}},y:{grid:{color:g},ticks:{color:'#999',font:{size:10}},border:{display:false},beginAtZero:true}}}});
  }
  const doOpts={responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{color:'#6b5860',font:{size:11},padding:12}},tooltip:ttOpts}};
  const devKeys=Object.keys(d.devices);
  if(devKeys.length)new Chart($('cdev'),{type:'doughnut',data:{labels:devKeys.map(k=>k==='mobile'?'📱 Mobile':k==='tablet'?'📟 Tablet':'🖥 Desktop'),datasets:[{data:devKeys.map(k=>d.devices[k]),backgroundColor:[N,G,C],borderWidth:0,hoverOffset:6}]},options:doOpts});
  const nv=d.new_visitors||0,rv=d.returning_visitors||0;
  if(nv+rv>0)new Chart($('cnew'),{type:'doughnut',data:{labels:['Neu','Wiederkehrend'],datasets:[{data:[nv,rv],backgroundColor:[N,G],borderWidth:0,hoverOffset:6}]},options:doOpts});
}

function fStep(label,val,pct){return`<div class="f-step"><div class="f-num">${val}</div><div class="f-label">${label}</div><div class="f-pct">${pct>0?pct+'%':''}</div><div class="f-bar"><div class="f-bar-fill" style="width:${pct}%"></div></div></div>`;}

function perfScore(p){
  let pts=0;
  if(p.avg_time>=60)pts+=2;else if(p.avg_time>=20)pts+=1;
  if(p.avg_scroll>=60)pts+=2;else if(p.avg_scroll>=35)pts+=1;
  if(p.exit_rate>0&&p.exit_rate<=40)pts+=2;else if(p.exit_rate<=60)pts+=1;
  if(pts>=5)return{cls:'gut',label:'Stark'};
  if(pts>=3)return{cls:'ok',label:'Okay'};
  return{cls:'schwach',label:'Optimieren'};
}

function buildRecs(d,trend,topPage,topClick,conv){
  const r=[],pv30=d.sessions_30d,em=d.email_count;
  // noindex — IMMER zuerst und prominent
  r.push({t:'warn',icon:'🔍',title:'noindex aktiv — Google sieht die Seite nicht',text:'Solange noindex gesetzt ist, erscheint Sensibilis in keiner Suche. Erst kurz vor Go-Live entfernen.'});
  // Kontaktformular
  if(em===0&&pv30>=5)r.push({t:'warn',icon:'⚠️',title:'Kontaktformular nicht aktiv',text:`${pv30} Besuche, kein einziger Lead. Das Formular ist noch nicht ans Backend angebunden — jeder Besucher geht verloren.`});
  else if(parseFloat(conv)<2&&pv30>=20)r.push({t:'warn',icon:'📉',title:`Konversionsrate niedrig (${conv}%)`,text:`Nur ${em} von ${pv30} Besuchen = Lead. CTA-Position, Sichtbarkeit und Formulartext prüfen.`});
  else if(em>0)r.push({t:'ok',icon:'✅',title:`${em} Leads (${conv}% Konversion)`,text:'Leads binnen 24 Stunden kontaktieren — dann ist die Abschlusswahrscheinlichkeit am höchsten.'});
  // Trend
  if(trend>20)r.push({t:'ok',icon:'📈',title:`Wachstum +${trend}% diese Woche`,text:'7 Tage liegen deutlich über dem Monatsdurchschnitt. Aktuellen Kanal oder Post weiterverfolgen.'});
  else if(trend<-20)r.push({t:'warn',icon:'📉',title:`Besucherrückgang ${trend}%`,text:'Woche liegt unter Schnitt. Verlinkungen, noindex-Status und Social-Media-Aktivität prüfen.'});
  // Seiten-Performance-Warnungen
  const schwach=(d.page_performance||[]).filter(p=>p.visits>=3&&perfScore(p).cls==='schwach');
  if(schwach.length>0)r.push({t:'warn',icon:'📄',title:`${schwach.length} Seite${schwach.length>1?'n':''} mit schlechter Performance`,text:`${schwach.map(p=>pN(p.page)).join(', ')} — kurze Verweildauer oder hohe Exit-Rate. CTA-Position und Content prüfen.`});
  // Mobile
  const mob=d.devices['mobile']||0,tot=Object.values(d.devices).reduce((a,b)=>a+b,0);
  if(tot>0&&mob/tot>0.6)r.push({t:'warn',icon:'📱',title:`${Math.round(mob/tot*100)}% der Besucher kommen mobil`,text:'Mehr als die Hälfte nutzt ein Smartphone. Mobile-Darstellung, CTA-Größe und Ladezeit genau prüfen.'});
  // Bester Button
  if(topClick)r.push({t:'ok',icon:'🖱️',title:`"${topClick[0]}" funktioniert`,text:`${topClick[1]} Klicks in 30 Tagen — dieser CTA performt. Formulierung auf andere Buttons übertragen.`});
  // Exit-Seite mit hoher Rate
  const topExit=d.exit_pages&&d.exit_pages[0];
  if(topExit&&d.page_performance){const ep=d.page_performance.find(p=>p.page===topExit[0]);if(ep&&ep.exit_rate>60)r.push({t:'warn',icon:'🚪',title:`"${pN(topExit[0])}" hat ${ep.exit_rate}% Exit-Rate`,text:'Mehr als die Hälfte aller Besucher verlässt die Website auf dieser Seite. CTA oder weiterführende Links ergänzen.'});}
  // Scroll
  const lowScroll=(d.avg_scroll_per_page||[]).filter(p=>p[1]<35&&(d.page_performance||[]).find(x=>x.page===p[0]&&x.visits>=3));
  if(lowScroll.length>0)r.push({t:'warn',icon:'📜',title:'Besucher scrollen nicht bis zum CTA',text:`Auf ${lowScroll.map(p=>pN(p[0])).join(', ')} wird im Schnitt weniger als 35% der Seite gelesen. CTA weiter nach oben setzen.`});
  if(pv30<10)r.push({t:'info',icon:'⏳',title:'Noch wenig Daten',text:'Unter 10 Besuchen — Aussagen sind noch nicht belastbar. In 2–3 Wochen ergibt sich ein klares Bild.'});
  return r;
}

function seoSection(seo){
  if(!seo||!seo.checks||seo.checks.length===0)return`<div class="empty-state"><div class="e-icon">🔍</div><p>SEO-Check konnte nicht geladen werden.</p></div>`;
  const sc=seo.score??0;
  const clr=sc>=75?'#1a6b3a':sc>=50?'#B8924A':'#8C1A2A';
  const r=36,circ=2*Math.PI*r,dash=circ*(sc/100),gap=circ-dash;
  const ring=`<svg width="80" height="80" viewBox="0 0 80 80"><circle cx="40" cy="40" r="${r}" fill="none" stroke="#e2d9d0" stroke-width="7"/><circle cx="40" cy="40" r="${r}" fill="none" stroke="${clr}" stroke-width="7" stroke-dasharray="${dash.toFixed(1)} ${gap.toFixed(1)}" stroke-linecap="round"/></svg>`;
  const lbl=sc>=75?'Gut aufgestellt':sc>=50?'Verbesserungsbedarf':'Dringend optimieren';
  const errs=seo.checks.filter(c=>c.status==='error').length;
  const warns=seo.checks.filter(c=>c.status==='warn').length;
  const oks=seo.checks.filter(c=>c.status==='ok').length;
  const scoreBar=`<div class="seo-score-bar"><div class="seo-score-ring">${ring}<div class="seo-score-num">${sc}%</div></div><div class="seo-score-info"><h3>${lbl}</h3><p>${oks} Punkte gut &nbsp;·&nbsp; ${warns} Warnungen &nbsp;·&nbsp; ${errs} Fehler<br>Geprüft: ${seo.checked_at?new Date(seo.checked_at).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):''}</p></div></div>`;
  const SEO_KEYS=['title','desc','canonical','noindex','h1','alt','og'];
  const GEO_KEYS=['jsonld','robots','llms','content'];
  const renderItems=(keys)=>seo.checks.filter(c=>keys.includes(c.key)).map(c=>`<div class="seo-item"><div class="seo-dot ${c.status}"></div><div class="seo-body"><div class="seo-label">${c.label}</div><div class="seo-detail">${c.detail}</div>${c.tip?`<div class="seo-tip">→ ${c.tip}</div>`:''}</div></div>`).join('');
  return`${scoreBar}<div class="seo-sep">SEO — Suchmaschinen</div><div class="seo-grid">${renderItems(SEO_KEYS)}</div><div class="seo-sep">GEO — KI-Sichtbarkeit (Generative Engine Optimization)</div><div class="seo-grid">${renderItems(GEO_KEYS)}</div>`;
}

function recCard(r){return`<div class="rec r-${r.t}"><div class="rec-icon">${r.icon}</div><div class="rec-body"><div class="rec-type">${r.t==='warn'?'Handlungsbedarf':r.t==='ok'?'Positiv':'Info'}</div><h4>${r.title}</h4><p>${r.text}</p></div></div>`;}
function pN(id){const m={home:'Startseite',beratung:'Beratung',preise:'Preise',zukunft:'KI & Zukunft',faq:'FAQ',kontakt:'Kontakt',blog:'Blog',kipass:'KI Pass',contentplaner:'Content Planer',webcheck:'Web Check',dms:'DMS',tools:'Tools',prozesse:'Prozesse',impressum:'Impressum',datenschutz:'Datenschutz',agb:'AGB',glossar:'Glossar',checkliste:'Schnellcheck'};return m[id]||id;}
function srcLabel(s){const m={direkt:'Direkt / Lesezeichen',google:'Google',social:'Social Media',email:'E-Mail',referral:'Andere Website'};return m[s]||s;}
function fmtTime(s){if(!s)return'—';if(s<60)return s+'s';return Math.floor(s/60)+'m '+(s%60)+'s';}
function eRow(r){const dt=new Date(r.created_at).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',year:'2-digit'});return`<tr><td>${r.name||'—'}</td><td>${r.email}</td><td>${r.source?`<span class="pill">${r.source}</span>`:'—'}</td><td>${dt}</td></tr>`;}
</script>
</body>
</html>"""

SITE_URL = "https://anme15.github.io/Sensibilis-Ki/"
ROBOTS_URL = "https://anme15.github.io/Sensibilis-Ki/robots.txt"
LLMS_URL   = "https://anme15.github.io/Sensibilis-Ki/llms.txt"

AI_BOTS = ["GPTBot","ClaudeBot","PerplexityBot","anthropic-ai","GoogleBot","Googlebot-Extended","cohere-ai","YouBot","BingBot"]

@app.get("/dashboard/seo")
async def dashboard_seo(token: str = Query(default="")):
    if not secrets.compare_digest(token.encode(), DASHBOARD_PASSWORD.encode()):
        raise HTTPException(status_code=401, detail="Nicht autorisiert")

    checks = []

    def chk(key, label, status, detail, tip=""):
        checks.append({"key":key,"label":label,"status":status,"detail":detail,"tip":tip})

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            # ── Hauptseite holen ──────────────────────────────────────────
            try:
                r = await client.get(SITE_URL)
                html = r.text
                soup = BeautifulSoup(html, "html.parser")
            except Exception as e:
                return {"error": f"Seite nicht erreichbar: {e}", "checks": []}

            # SEO: Title
            title = soup.find("title")
            if title and title.text.strip():
                chk("title","Title-Tag","ok",f'"{title.text.strip()[:60]}"')
            else:
                chk("title","Title-Tag","error","Kein Title-Tag gefunden","<title>Sensibilis – KI-Beratung für kleine Betriebe</title> im <head> ergänzen")

            # SEO: Meta Description
            desc = soup.find("meta", attrs={"name":"description"})
            if desc and desc.get("content","").strip():
                d = desc["content"].strip()
                l = len(d)
                if l < 50:
                    chk("desc","Meta-Description","warn",f"Zu kurz ({l} Zeichen)","Mindestens 120–155 Zeichen empfohlen")
                elif l > 160:
                    chk("desc","Meta-Description","warn",f"Zu lang ({l} Zeichen)","Google kürzt ab 155–160 Zeichen")
                else:
                    chk("desc","Meta-Description","ok",f"{l} Zeichen — passt")
            else:
                chk("desc","Meta-Description","error","Fehlt komplett","<meta name=\"description\" content=\"...\"> im <head> ergänzen")

            # SEO: Canonical
            canon = soup.find("link", attrs={"rel":"canonical"})
            if canon and canon.get("href","").strip():
                chk("canonical","Canonical-URL","ok",canon["href"].strip())
            else:
                chk("canonical","Canonical-URL","warn","Kein Canonical-Tag","<link rel=\"canonical\" href=\"https://anme15.github.io/Sensibilis-Ki/\"> ergänzen")

            # SEO: noindex
            robots_meta = soup.find("meta", attrs={"name": re.compile("robots", re.I)})
            noindex = robots_meta and "noindex" in robots_meta.get("content","").lower()
            if noindex:
                chk("noindex","noindex-Status","warn","Aktiv — Google und KI-Crawler indexieren die Seite nicht","Vor Go-Live noindex entfernen")
            else:
                chk("noindex","noindex-Status","ok","Nicht gesetzt — Seite ist indexierbar")

            # SEO: H1
            h1s = soup.find_all("h1")
            if len(h1s) == 1:
                chk("h1","H1-Überschrift","ok",f'"{h1s[0].text.strip()[:60]}"')
            elif len(h1s) == 0:
                chk("h1","H1-Überschrift","error","Keine H1 gefunden","Genau eine H1 pro Seite — die wichtigste Aussage")
            else:
                chk("h1","H1-Überschrift","warn",f"{len(h1s)} H1-Tags gefunden","Nur eine H1 pro Seite empfohlen")

            # SEO: Alt-Texte
            imgs = soup.find_all("img")
            no_alt = [i.get("src","")[-30:] for i in imgs if not i.get("alt","").strip()]
            if not imgs:
                chk("alt","Alt-Texte","info","Keine Bilder gefunden")
            elif no_alt:
                chk("alt","Alt-Texte","warn",f"{len(no_alt)} von {len(imgs)} Bildern ohne Alt-Text",f"Betroffen: {', '.join(no_alt[:3])}{'...' if len(no_alt)>3 else ''}")
            else:
                chk("alt","Alt-Texte","ok",f"Alle {len(imgs)} Bilder haben Alt-Texte")

            # SEO: Open Graph
            og_title = soup.find("meta", attrs={"property":"og:title"})
            og_desc  = soup.find("meta", attrs={"property":"og:description"})
            if og_title and og_desc:
                chk("og","Open Graph Tags","ok","og:title und og:description vorhanden")
            elif og_title or og_desc:
                chk("og","Open Graph Tags","warn","Nur teilweise vorhanden","og:title, og:description, og:image und og:url ergänzen")
            else:
                chk("og","Open Graph Tags","error","Fehlen komplett","Für Social-Media-Vorschauen und KI-Suchen wichtig")

            # GEO: JSON-LD
            jsonld = soup.find("script", attrs={"type":"application/ld+json"})
            if jsonld and jsonld.string and jsonld.string.strip():
                try:
                    data = json.loads(jsonld.string)
                    if "@graph" in data:
                        types = [n.get("@type","?") for n in data["@graph"] if isinstance(n,dict)]
                        typ = ", ".join(types) if types else "unbekannt"
                    else:
                        typ = data.get("@type","unbekannt")
                    chk("jsonld","JSON-LD Strukturdaten","ok",f"Vorhanden — Typ: {typ}")
                except Exception:
                    chk("jsonld","JSON-LD Strukturdaten","warn","Vorhanden aber ungültiges JSON","JSON-LD auf Syntaxfehler prüfen")
            else:
                chk("jsonld","JSON-LD Strukturdaten","error","Fehlt","KI-Systeme lesen JSON-LD als erstes. Schema.org/LocalBusiness oder Person ergänzen")

            # GEO: robots.txt + KI-Bots
            try:
                rob = await client.get(ROBOTS_URL)
                rob_text = rob.text if rob.status_code == 200 else ""
            except Exception:
                rob_text = ""

            if not rob_text:
                chk("robots","robots.txt","warn","Nicht gefunden","robots.txt anlegen und KI-Bots explizit erlauben")
            else:
                blocked = [b for b in AI_BOTS if f"User-agent: {b}" in rob_text and "Disallow: /" in rob_text]
                allowed = [b for b in AI_BOTS if f"User-agent: {b}" in rob_text and "Allow: /" in rob_text]
                if blocked:
                    chk("robots","robots.txt — KI-Bots","warn",f"Gesperrt: {', '.join(blocked)}","Gesperrte KI-Bots können Inhalte nicht lesen und nicht in Antworten einbeziehen")
                elif "User-agent: *" in rob_text and "Disallow:" in rob_text:
                    chk("robots","robots.txt — KI-Bots","warn","Wildcard-Sperre aktiv — könnte KI-Bots betreffen","Prüfen ob KI-Bots explizit erlaubt sind")
                else:
                    chk("robots","robots.txt — KI-Bots","ok","Keine KI-Bot-Sperren gefunden")

            # GEO: llms.txt
            try:
                llms = await client.get(LLMS_URL)
                if llms.status_code == 200 and llms.text.strip():
                    chk("llms","llms.txt","ok","Vorhanden — KI-Systeme können Seitenstruktur direkt lesen")
                else:
                    chk("llms","llms.txt","warn","Nicht gefunden","Neuer Standard: llms.txt beschreibt der KI deine Seite in Klartext. Erhöht Sichtbarkeit in ChatGPT, Perplexity etc.")
            except Exception:
                chk("llms","llms.txt","warn","Nicht erreichbar","llms.txt anlegen")

            # GEO: Textdichte (grober Check)
            body_text = soup.get_text(separator=" ", strip=True)
            word_count = len(body_text.split())
            if word_count < 200:
                chk("content","Textinhalt","warn",f"Nur ~{word_count} Wörter sichtbar","KI-Systeme bevorzugen Seiten mit substanziellem Text. Mehr Erklärtext ergänzen.")
            elif word_count < 500:
                chk("content","Textinhalt","info",f"~{word_count} Wörter — ausreichend, aber mehr wäre besser")
            else:
                chk("content","Textinhalt","ok",f"~{word_count} Wörter — gute Basis für KI-Indexierung")

    except Exception as e:
        return {"error": str(e), "checks": checks}

    score_map = {"ok":2,"info":1,"warn":0,"error":-1}
    total = sum(score_map.get(c["status"],0) for c in checks)
    max_score = len(checks) * 2
    pct = round(total / max_score * 100) if max_score else 0

    return {"checks": checks, "score": pct, "total": total, "checked_at": datetime.now(timezone.utc).isoformat()}


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
            "session_id": data.get("session_id", ""),
            "device": data.get("device", ""),
            "is_new": data.get("is_new", True),
            "referrer": data.get("referrer", ""),
            "ref_source": data.get("ref_source", "direkt"),
            "lang": data.get("lang", ""),
            "width": data.get("w"),
            "ts": data.get("ts"),
        }).execute()
    elif typ == "click":
        sb.table("sensibilis_clicks").insert({
            "label": data.get("label", ""),
            "page": data.get("page", ""),
            "session_id": data.get("session_id", ""),
            "ts": data.get("ts"),
        }).execute()
    elif typ == "timing":
        sb.table("sensibilis_timing").insert({
            "session_id": data.get("session_id", ""),
            "page": data.get("page", ""),
            "time_on_page": data.get("time_on_page", 0),
            "scroll_depth": data.get("scroll_depth", 0),
            "is_exit": data.get("is_exit", False),
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
def dashboard_data(token: str = Query(default=""), days: int = Query(default=30), compare: bool = Query(default=False)):
    if not secrets.compare_digest(token.encode(), DASHBOARD_PASSWORD.encode()):
        raise HTTPException(status_code=401, detail="Nicht autorisiert")
    now  = datetime.now(timezone.utc)
    d7   = (now - timedelta(days=7)).isoformat()
    d30  = (now - timedelta(days=days)).isoformat()
    prev_start = (now - timedelta(days=days*2)).isoformat()
    prev_end   = (now - timedelta(days=days)).isoformat()

    pv7  = sb.table("sensibilis_pageviews").select("page,session_id,device,is_new,ref_source,created_at").gte("created_at", d7).execute().data
    pv30 = sb.table("sensibilis_pageviews").select("page,session_id,device,is_new,ref_source,created_at").gte("created_at", d30).execute().data
    cl30 = sb.table("sensibilis_clicks").select("label,page,created_at").gte("created_at", d30).execute().data
    tm30 = sb.table("sensibilis_timing").select("page,time_on_page,scroll_depth,is_exit,created_at").gte("created_at", d30).execute().data
    emails = sb.table("sensibilis_emails").select("email,name,source,created_at").order("created_at", desc=True).limit(50).execute().data

    # Seitenaufrufe
    pages7, pages30, tage = {}, {}, {}
    for r in pv7:
        pages7[r["page"]] = pages7.get(r["page"], 0) + 1
    for r in pv30:
        pages30[r["page"]] = pages30.get(r["page"], 0) + 1
        tag = r["created_at"][:10]
        tage[tag] = tage.get(tag, 0) + 1

    # Einstiegsseiten (erste Seite pro Session, 30T)
    session_first: dict = {}
    for r in pv30:
        sid = r.get("session_id") or ""
        ts  = r.get("created_at", "")
        pg  = r.get("page", "")
        if sid and pg:
            if sid not in session_first or ts < session_first[sid][0]:
                session_first[sid] = (ts, pg)
    entry_pages: dict = {}
    for _, (_, pg) in session_first.items():
        entry_pages[pg] = entry_pages.get(pg, 0) + 1

    # Klicks
    clicks = {}
    for r in cl30:
        clicks[r["label"]] = clicks.get(r["label"], 0) + 1

    # Geräte (30T, pro Session)
    devices: dict = {}
    seen_dev: set = set()
    for r in pv30:
        sid = r.get("session_id") or ""
        if sid in seen_dev:
            continue
        seen_dev.add(sid)
        dv = r.get("device") or "unbekannt"
        devices[dv] = devices.get(dv, 0) + 1

    # Neu vs. wiederkehrend (30T, pro Session)
    seen_nv: set = set()
    new_count = returning_count = 0
    for r in pv30:
        sid = r.get("session_id") or ""
        if sid in seen_nv:
            continue
        seen_nv.add(sid)
        if r.get("is_new"):
            new_count += 1
        else:
            returning_count += 1

    # Traffic-Quellen (30T, pro Session)
    seen_src: set = set()
    sources: dict = {}
    for r in pv30:
        sid = r.get("session_id") or r.get("created_at", "")
        if sid in seen_src:
            continue
        seen_src.add(sid)
        src = r.get("ref_source") or "direkt"
        sources[src] = sources.get(src, 0) + 1

    # Timing pro Seite
    page_times: dict = {}
    page_scroll_raw: dict = {}
    exit_pages: dict = {}
    for r in tm30:
        pg = r.get("page", "")
        t  = r.get("time_on_page") or 0
        sc = r.get("scroll_depth") or 0
        if not pg:
            continue
        page_times.setdefault(pg, []).append(t)
        page_scroll_raw.setdefault(pg, []).append(sc)
        if r.get("is_exit"):
            exit_pages[pg] = exit_pages.get(pg, 0) + 1

    avg_time   = {pg: round(sum(v)/len(v)) for pg, v in page_times.items()}
    avg_scroll = {pg: round(sum(v)/len(v)) for pg, v in page_scroll_raw.items()}

    # Seiten-Performance (kombiniert: Aufrufe + Zeit + Scroll + Exit-Rate)
    all_pages = set(pages30.keys()) | set(avg_time.keys())
    page_perf = []
    for pg in all_pages:
        visits = pages30.get(pg, 0)
        exits  = exit_pages.get(pg, 0)
        t      = avg_time.get(pg, 0)
        sc     = avg_scroll.get(pg, 0)
        exit_rate = round(exits / visits * 100) if visits > 0 else 0
        page_perf.append({"page": pg, "visits": visits, "avg_time": t, "avg_scroll": sc, "exit_rate": exit_rate})
    page_perf.sort(key=lambda x: x["visits"], reverse=True)

    # Kontaktseite 30T für Funnel
    kontakt30 = pages30.get("kontakt", 0)

    return {
        # Vergleichszeitraum
        "prev_sessions": len(sb.table("sensibilis_pageviews").select("id").gte("created_at", prev_start).lt("created_at", prev_end).execute().data) if compare else None,
        "prev_emails":   len(sb.table("sensibilis_emails").select("id").gte("created_at", prev_start).lt("created_at", prev_end).execute().data) if compare else None,
        "days":                days,
        "sessions_7d":         len(pv7),
        "sessions_30d":        len(pv30),
        "kontakt_30d":         kontakt30,
        "top_pages_7d":        sorted(pages7.items(),  key=lambda x: x[1], reverse=True)[:10],
        "top_pages_30d":       sorted(pages30.items(), key=lambda x: x[1], reverse=True)[:10],
        "top_clicks_30d":      sorted(clicks.items(),  key=lambda x: x[1], reverse=True)[:10],
        "daily_30d":           sorted(tage.items()),
        "devices":             devices,
        "new_visitors":        new_count,
        "returning_visitors":  returning_count,
        "traffic_sources":     sorted(sources.items(), key=lambda x: x[1], reverse=True),
        "entry_pages":         sorted(entry_pages.items(), key=lambda x: x[1], reverse=True)[:8],
        "page_performance":    page_perf[:12],
        "avg_time_per_page":   sorted(avg_time.items(),   key=lambda x: x[1], reverse=True)[:8],
        "avg_scroll_per_page": sorted(avg_scroll.items(), key=lambda x: x[1], reverse=True)[:8],
        "exit_pages":          sorted(exit_pages.items(), key=lambda x: x[1], reverse=True)[:8],
        "emails":              emails,
        "email_count":         len(emails),
    }
