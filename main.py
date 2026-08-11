import os, json, re, time
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from supabase import create_client
import secrets, httpx
from bs4 import BeautifulSoup

app = FastAPI()

SUPABASE_URL = os.environ["SUPABASE_URL"].strip()
SUPABASE_KEY = re.sub(r'[^\x20-\x7E]', '', os.environ["SUPABASE_KEY"]).strip()
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "sensibilis2026")

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://anme15.github.io"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)

# ── Passwortpruefung per Header + Bremse gegen Rateversuche ──────────
# Das Passwort steht nicht mehr in der Adresszeile, sondern im Header
# X-Dashboard-Token. Nach _SPERRE_AB Fehlversuchen je IP innerhalb von
# _ZEITFENSTER Sekunden wird nur noch abgewiesen.
_FEHLVERSUCHE: dict = {}
_SPERRE_AB   = 5
_ZEITFENSTER = 900


def _ip(request: Request) -> str:
    # WICHTIG: den LETZTEN Eintrag nehmen, nicht den ersten.
    # Der Client kann X-Forwarded-For selbst mitschicken und bei jedem
    # Versuch faelschen; Renders Proxy haengt die echte IP hinten an.
    # Der erste Eintrag ist also angreifergesteuert, der letzte nicht.
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        teile = [t.strip() for t in fwd.split(",") if t.strip()]
        if teile:
            return teile[-1]
    return (request.client.host if request.client else "?") or "?"


def _pruefe(request: Request):
    ip    = _ip(request)
    jetzt = time.time()
    liste = [t for t in _FEHLVERSUCHE.get(ip, []) if jetzt - t < _ZEITFENSTER]
    _FEHLVERSUCHE[ip] = liste

    if len(liste) >= _SPERRE_AB:
        raise HTTPException(status_code=429, detail="Zu viele Fehlversuche. Bitte 15 Minuten warten.")

    token = request.headers.get("X-Dashboard-Token", "")
    if not secrets.compare_digest(token.encode(), DASHBOARD_PASSWORD.encode()):
        liste.append(jetzt)
        _FEHLVERSUCHE[ip] = liste
        raise HTTPException(status_code=401, detail="Nicht autorisiert")

    _FEHLVERSUCHE.pop(ip, None)

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

/* TABS */
.tab-bar{display:flex;gap:6px;margin-bottom:32px;background:rgba(13,28,63,.1);border-radius:14px;padding:6px;position:sticky;top:68px;z-index:50;box-shadow:0 4px 24px rgba(13,28,63,.18);backdrop-filter:blur(10px);border:1.5px solid rgba(13,28,63,.08)}
.tab-btn{flex:1;padding:12px 20px;background:rgba(255,255,255,.5);border:1.5px solid rgba(13,28,63,.08);border-radius:10px;font-size:13px;font-weight:700;color:rgba(13,28,63,.6);cursor:pointer;transition:.18s;text-align:center;letter-spacing:.01em}
.tab-btn.active{background:linear-gradient(135deg,var(--n) 0%,#1e4080 100%);color:#fff;border-color:transparent;box-shadow:0 3px 14px rgba(13,28,63,.35)}
.tab-btn:hover:not(.active){color:var(--n);background:rgba(255,255,255,.85);border-color:rgba(13,28,63,.15)}
.chat-log-msg{max-width:280px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* LEADS & PIPELINE */
.score-hot{background:#fdf2f2;color:#8C1A2A;font-size:11px;font-weight:700;padding:3px 9px;border-radius:20px;display:inline-block}
.score-warm{background:#fff8ec;color:#8C5A00;font-size:11px;font-weight:700;padding:3px 9px;border-radius:20px;display:inline-block}
.score-cold{background:#eef3fb;color:#1a3f6b;font-size:11px;font-weight:700;padding:3px 9px;border-radius:20px;display:inline-block}
.ltable{width:100%;border-collapse:collapse;font-size:13px}
.ltable th{background:var(--n);color:#fff;padding:10px 14px;text-align:left;font-size:10px;letter-spacing:.1em;text-transform:uppercase;font-weight:600}
.ltable td{padding:11px 14px;border-bottom:1px solid var(--bdr);color:var(--ink);vertical-align:middle}
.ltable tr:last-child td{border-bottom:none}
.ltable tr:hover td{background:rgba(184,146,74,.05)}
.ltable .tm{color:var(--ink2);font-size:12px}
.ltable tbody tr{cursor:pointer}
.ltable tbody tr:hover td{background:rgba(184,146,74,.1)!important}
/* AKTIONSZENTRALE */
.ak-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media(max-width:900px){.ak-grid{grid-template-columns:1fr}}
.ak-col{background:var(--surf);border-radius:var(--radius);overflow:hidden;box-shadow:var(--shadow)}
.ak-head{padding:11px 16px;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;display:flex;align-items:center;gap:8px}
.ak-col.heute .ak-head{background:#fdf2f2;color:var(--c);border-bottom:2px solid var(--c)}
.ak-col.morgen .ak-head{background:#fff8ec;color:#8C5A00;border-bottom:2px solid var(--g)}
.ak-col.warten .ak-head{background:#f4f4f4;color:var(--ink2);border-bottom:2px solid #d8d8d8}
.ak-body{padding:10px;display:flex;flex-direction:column;gap:8px;min-height:52px}
.ak-card{background:var(--page);border-radius:8px;padding:11px 13px}
.ak-name{font-size:13px;font-weight:700;color:var(--ink);margin-bottom:3px}
.ak-grund{font-size:11px;color:var(--ink2);line-height:1.5;margin-bottom:9px}
.ak-btns{display:flex;gap:7px}
.ak-btn{flex:1;text-align:center;padding:7px 8px;border-radius:7px;font-size:11px;font-weight:600;text-decoration:none;display:block}
.ak-btn.call{background:var(--n);color:#fff}
.ak-btn.mail{background:transparent;color:var(--n);border:1.5px solid var(--bdr)}
.ak-empty{font-size:12px;color:var(--ink2);padding:14px;text-align:center;opacity:.55}
/* TIMELINE */
.tl-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px}
.tl-kpi{background:var(--surf);border-radius:10px;padding:14px 16px;box-shadow:var(--shadow);text-align:center}
.tl-kpi-val{font-size:30px;font-weight:800;color:var(--n);font-variant-numeric:tabular-nums;line-height:1}
.tl-kpi-lbl{font-size:10px;color:var(--ink2);text-transform:uppercase;letter-spacing:.08em;margin-top:5px;font-weight:600}
.tl-filter{display:flex;gap:6px;margin-bottom:16px}
.tl-fbtn{background:var(--page);border:1.5px solid var(--bdr);color:var(--ink2);font-size:11px;font-weight:600;padding:5px 14px;border-radius:20px;cursor:pointer;transition:.15s}
.tl-fbtn:hover{border-color:var(--n);color:var(--n)}
.tl-fbtn.active{background:var(--n);color:#fff;border-color:var(--n)}
.tl-lead-block{margin-bottom:16px}
.tl-lead-hd{font-size:13px;font-weight:700;color:var(--ink);padding:10px 14px;background:var(--surf);border-radius:8px 8px 0 0;border-bottom:1px solid var(--bdr);display:flex;align-items:center;justify-content:space-between}
.tl-track{padding:16px 14px 10px 42px;background:var(--surf);border-radius:0 0 8px 8px;position:relative}
.tl-track::before{content:'';position:absolute;left:21px;top:0;bottom:0;width:2px;background:var(--bdr)}
.tl-evt{position:relative;margin-bottom:14px}
.tl-evt:last-child{margin-bottom:0}
.tl-dot{position:absolute;left:-28px;width:14px;height:14px;border-radius:50%;top:2px;border:2.5px solid var(--surf)}
.tl-evt-lbl{font-size:12px;font-weight:700;color:var(--ink);margin-bottom:2px}
.tl-evt-meta{font-size:11px;color:var(--ink2)}
.dot-form{background:var(--g)}.dot-sent{background:var(--n)}.dot-opened{background:var(--ok)}.dot-clicked{background:#0a5429}.dot-stage{background:#6b3fa0}.dot-call{background:#8C5A00}.dot-note{background:var(--ink2)}
/* LEAD DETAIL PANEL */
.lead-overlay{position:fixed;inset:0;background:rgba(13,28,63,.38);z-index:200;display:none}
.lead-overlay.open{display:block}
.lead-panel{position:fixed;top:0;right:0;width:480px;max-width:96vw;height:100vh;background:var(--surf);z-index:201;overflow-y:auto;box-shadow:-4px 0 36px rgba(13,28,63,.2);transform:translateX(100%);transition:transform .28s cubic-bezier(.4,0,.2,1)}
.lead-panel.open{transform:translateX(0)}
.lp-head{background:linear-gradient(135deg,var(--n),#1a3a72);padding:28px 24px 22px;position:sticky;top:0;z-index:1}
.lp-name{font-size:20px;font-weight:700;color:#fff;margin-bottom:8px;line-height:1.2}
.lp-meta-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.lp-lemail{font-size:12px;color:rgba(255,255,255,.6)}
.lp-close{position:absolute;top:18px;right:18px;background:rgba(255,255,255,.12);border:none;color:#fff;width:32px;height:32px;border-radius:50%;font-size:20px;cursor:pointer;line-height:30px;text-align:center;transition:.15s}
.lp-close:hover{background:rgba(255,255,255,.25)}
.lp-body{padding:20px 24px 40px}
.lp-section{margin-bottom:18px}
.lp-lbl{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--ink2);margin-bottom:6px}
.lp-val{font-size:13px;color:var(--ink);line-height:1.7;background:var(--page);border-radius:8px;padding:11px 14px}
.lp-2col{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.lp-act-btns{display:flex;gap:10px;margin-bottom:20px}
.lp-act-btn{flex:1;padding:11px;border-radius:9px;font-size:13px;font-weight:600;text-align:center;cursor:pointer;border:none;text-decoration:none;display:block}
.lp-act-btn.primary{background:var(--n);color:#fff}
.lp-act-btn.secondary{background:var(--page);color:var(--n);border:1.5px solid var(--bdr)}
.lp-tl-item{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--bdr)}
.lp-tl-item:last-child{border-bottom:none}
.lp-tl-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0;margin-top:3px}
.lp-tl-lbl{font-size:12px;font-weight:600;color:var(--ink);margin-bottom:2px}
.lp-tl-meta{font-size:11px;color:var(--ink2)}
.lp-abschluss-btns{display:flex;gap:10px;margin-top:4px}
.lp-won-btn{flex:1;background:#1a6b2e;color:#fff;border:none;border-radius:8px;padding:10px;font-size:13px;font-weight:700;cursor:pointer;transition:.15s}
.lp-won-btn:hover{background:#155a26}
.lp-lost-btn{flex:1;background:transparent;color:#9e1a2c;border:2px solid #9e1a2c;border-radius:8px;padding:10px;font-size:13px;font-weight:700;cursor:pointer;transition:.15s}
.lp-lost-btn:hover{background:#fdf2f2}
/* PIPELINE BOARD */
.hot-zone{background:linear-gradient(135deg,#7a1020,#9e1a2c);border-radius:14px;padding:20px 22px 22px;margin-bottom:24px}
.hot-zone-hd{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.65);margin-bottom:14px}
.hot-zone-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
.hot-zcard{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.16);border-radius:10px;padding:15px 17px;cursor:pointer;transition:.15s}
.hot-zcard:hover{background:rgba(255,255,255,.19)}
.hot-zname{font-size:15px;font-weight:700;color:#fff;margin-bottom:2px}
.hot-zco{font-size:11px;color:rgba(255,255,255,.5);margin-bottom:8px}
.hot-zpain{font-size:12px;color:rgba(255,255,255,.88);line-height:1.55;font-style:italic;margin-bottom:9px;border-left:2.5px solid rgba(255,255,255,.28);padding-left:10px}
.hot-zmeta{font-size:11px;color:rgba(255,255,255,.42);margin-bottom:10px}
.hot-zbtn{display:inline-block;background:rgba(255,255,255,.9);color:#7a1020;font-size:11px;font-weight:700;padding:6px 14px;border-radius:20px;text-decoration:none;transition:.1s}
.hot-zbtn:hover{background:#fff}
.pipe-bar{display:flex;align-items:center;justify-content:space-between;margin-bottom:22px;padding:0 2px}
.pipe-stats{font-size:13px;color:var(--ink2)}
.pipe-rbtn{background:var(--page);border:1.5px solid var(--bdr);color:var(--ink2);font-size:12px;font-weight:600;padding:6px 14px;border-radius:8px;cursor:pointer;transition:.15s}
.pipe-rbtn:hover{border-color:var(--n);color:var(--n)}
.pipe-track{margin-bottom:28px}
.pipe-track{border-radius:14px;padding:20px;margin-bottom:8px}
.pipe-track-lbl{font-size:12px;font-weight:900;letter-spacing:.18em;text-transform:uppercase;margin-bottom:16px;display:flex;align-items:center;gap:14px;padding:12px 18px;border-radius:10px}
.pipe-track-lbl::after{content:'';flex:1;height:2px}
.warm-lbl{color:#6b3d00;background:linear-gradient(90deg,rgba(184,146,74,.25),rgba(184,146,74,.06));border-left:5px solid #c49a3a;border-top:1px solid rgba(196,154,58,.3);border-bottom:1px solid rgba(196,154,58,.3)}.warm-lbl::after{background:linear-gradient(90deg,rgba(184,146,74,.5),rgba(184,146,74,.08))}
.cold-lbl{color:#091d46;background:linear-gradient(90deg,rgba(13,28,63,.14),rgba(13,28,63,.03));border-left:5px solid #3a6ab0;border-top:1px solid rgba(74,127,193,.25);border-bottom:1px solid rgba(74,127,193,.25)}.cold-lbl::after{background:linear-gradient(90deg,rgba(26,63,107,.45),rgba(26,63,107,.06))}
.abschluss-lbl{color:#0e3d1c;background:linear-gradient(90deg,rgba(26,92,46,.14),rgba(26,92,46,.03));border-left:5px solid #2a8a46;border-top:1px solid rgba(42,138,70,.25);border-bottom:1px solid rgba(42,138,70,.25)}.abschluss-lbl::after{background:linear-gradient(90deg,rgba(26,92,46,.4),rgba(26,92,46,.06))}
.won-hd{background:#edf7f0;border-bottom:2px solid #1a6b2e}
.lost-hd{background:#fdf2f2;border-bottom:2px solid #9e1a2c}
.pipe-row{display:grid;gap:12px;overflow-x:auto}
.pipe-row-2{grid-template-columns:repeat(2,1fr)}
.pipe-row-3{grid-template-columns:repeat(3,1fr)}
.pipe-row-4{grid-template-columns:repeat(4,1fr)}
.pipe-row-5{grid-template-columns:repeat(5,1fr)}
.pipe-date{font-size:10px;color:var(--ink2);background:transparent!important;padding:0!important}
.pipe-col{background:var(--surf);border-radius:12px;overflow:hidden;box-shadow:var(--shadow);min-width:0}
.pipe-col-hd{padding:10px 14px;display:flex;align-items:center;justify-content:space-between}
.warm-hd{background:#fff8ec;border-bottom:2px solid var(--g)}
.cold-hd{background:#eef3fb;border-bottom:2px solid #7a9fd4}
.pipe-col-lbl{font-size:11px;font-weight:700;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pipe-col-cnt{font-size:12px;font-weight:800;background:var(--page);color:var(--ink2);width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-left:6px}
.pipe-col-body{padding:8px;display:flex;flex-direction:column;gap:8px;min-height:72px}
.pipe-card{background:var(--page);border-radius:9px;padding:12px 13px;cursor:pointer;transition:.15s;border:1.5px solid transparent}
.pipe-card:hover{border-color:var(--g);background:#fffdf6}
.pipe-card.rotting{border-color:rgba(180,30,30,.35);background:#fff8f8}
.pipe-card.rotting:hover{border-color:rgba(180,30,30,.6);background:#fff2f2}
.rot-badge{font-size:10px;font-weight:700;color:#b41e1e;background:rgba(180,30,30,.1);padding:2px 8px;border-radius:20px;display:inline-flex;align-items:center;gap:4px;margin-bottom:5px;white-space:nowrap}
.last-contact{font-size:10px;color:var(--ink2);white-space:nowrap}
.pipe-card-top{display:flex;align-items:flex-start;justify-content:space-between;gap:6px;margin-bottom:4px}
.pipe-name{font-size:13px;font-weight:700;color:var(--ink);line-height:1.2;flex:1}
.pipe-co{font-size:11px;color:var(--ink2);margin-bottom:6px}
.pipe-pain{font-size:11px;color:var(--ink);line-height:1.5;margin-bottom:8px;opacity:.7;font-style:italic;border-left:2px solid var(--bdr);padding-left:8px}
.pipe-foot{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.pipe-tag{font-size:10px;font-weight:600;padding:2px 7px;border-radius:20px;background:var(--surf);color:var(--ink2);white-space:nowrap}
.pipe-day{color:var(--n);background:rgba(13,28,63,.07)}
.pipe-mail{font-size:10px;font-weight:700;padding:3px 9px;border-radius:20px;background:var(--n);color:#fff;text-decoration:none;margin-left:auto;white-space:nowrap}
.pipe-mail:hover{opacity:.85}
.pipe-none{font-size:11px;color:var(--ink2);text-align:center;padding:20px 10px;opacity:.4}
@media(max-width:1000px){.pipe-row-5{grid-template-columns:repeat(3,1fr)}}
@media(max-width:800px){.pipe-row-3{grid-template-columns:repeat(2,1fr)}.pipe-row-4{grid-template-columns:repeat(2,1fr)}.pipe-row-5{grid-template-columns:repeat(2,1fr)}}
@media(max-width:480px){.pipe-row-3,.pipe-row-4,.pipe-row-5{grid-template-columns:1fr}}
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
  <main>
    <div class="tab-bar">
      <button class="tab-btn active" onclick="switchTab('analytics')" id="tab-analytics">&#128202; Analytik</button>
      <button class="tab-btn" onclick="switchTab('chat')" id="tab-chat">&#128172; Chatbot</button>
      <button class="tab-btn" onclick="switchTab('leads')" id="tab-leads">&#128203; CRM Pipeline</button>
    </div>
    <div id="content"><div class="loading">Daten werden geladen&hellip;</div></div>
    <div id="content-chat" style="display:none"><div class="loading">Chatbot-Daten werden geladen&hellip;</div></div>
    <div id="leads-content" style="display:none"></div>
  </main>
  <div class="dash-foot">Sensibilis Analytics &mdash; nur zur internen Nutzung</div>
</div>
<div class="lead-overlay" id="lead-overlay" onclick="closeLeadPanel()"></div>
<div class="lead-panel" id="lead-panel">
  <div class="lp-head">
    <button class="lp-close" onclick="closeLeadPanel()">&#215;</button>
    <div class="lp-name" id="lp-name">&#8212;</div>
    <div class="lp-meta-row">
      <span id="lp-score" class="score-cold">COLD</span>
      <span class="lp-lemail" id="lp-lemail">&#8212;</span>
    </div>
  </div>
  <div class="lp-body" id="lp-body"></div>
</div>
<script>
const N='#0D1C3F',G='#B8924A',C='#8C1A2A';
let _pw='';
const $=id=>document.getElementById(id);
const esc=v=>String(v==null?'':v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]);
let curDays=30,curCompare=false;
let _leadsCache=[],_tlLeads=[],_tlEvts=[];
function doLogin(){const pw=$('pw').value.trim();if(!pw){showE('Bitte Passwort eingeben.');return;}_pw=pw;$('lerr').textContent='Wird geprüft…';load();}
$('pw').addEventListener('keydown',e=>{if(e.key==='Enter')doLogin();});
function doLogout(){_pw='';$('app').style.display='none';$('login').style.display='flex';$('pw').value='';}
function showE(m){$('lerr').textContent=m;}

let curTab='analytics';
function switchTab(t){
  curTab=t;
  ['analytics','chat','leads'].forEach(function(id){
    var btn=$('tab-'+id);if(btn)btn.classList.toggle('active',id===t);
    var c=id==='analytics'?$('content'):id==='chat'?$('content-chat'):$('leads-content');
    if(c)c.style.display=id===t?'':'none';
  });
  if(t==='chat'&&_pw)loadChat();
  if(t==='leads'&&_pw)loadLeads();
}
function setPeriod(d){
  curDays=d;
  ['p7','p30','p90'].forEach(id=>$('p'+id.slice(1))&&$('p'+id.slice(1)).classList.remove('active'));
  $('p'+d)&&$('p'+d).classList.add('active');
  load();
  if(curTab==='chat'&&_pw)loadChat();
  if(curTab==='leads')loadLeads();
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
      fetch('/dashboard/data?days='+curDays+'&compare='+(curCompare?'true':'false'),{headers:{'X-Dashboard-Token':_pw}}),
      fetch('/dashboard/seo',{headers:{'X-Dashboard-Token':_pw}})
    ]);
    if(r.status===429){showE('Zu viele Fehlversuche. Bitte 15 Minuten warten.');_pw='';return;}
    if(r.status===401){showE('Falsches Passwort.');_pw='';return;}
    if(!r.ok){const t=await r.json().catch(()=>({}));throw new Error('HTTP '+r.status+': '+(t.detail||'?'));}
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
function pN(id){const m={home:'Startseite',beratung:'Beratung',preise:'Preise',zukunft:'KI & Zukunft',faq:'FAQ',kontakt:'Kontakt',blog:'Blog',kipass:'KI Pass',contentplaner:'Content Planer',webcheck:'Web Check',dms:'DMS',tools:'Tools',prozesse:'Prozesse',impressum:'Impressum',datenschutz:'Datenschutz',agb:'AGB',glossar:'Glossar',checkliste:'Schnellcheck'};return m[id]||esc(id);}
function srcLabel(s){const m={direkt:'Direkt / Lesezeichen',google:'Google',social:'Social Media',email:'E-Mail',referral:'Andere Website'};return m[s]||esc(s);}
function fmtTime(s){if(!s)return'—';if(s<60)return s+'s';return Math.floor(s/60)+'m '+(s%60)+'s';}
function eRow(r){const dt=new Date(r.created_at).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',year:'2-digit'});return`<tr><td>${r.name?esc(r.name):'—'}</td><td>${esc(r.email)}</td><td>${r.source?`<span class="pill">${esc(r.source)}</span>`:'—'}</td><td>${dt}</td></tr>`;}

async function loadChat(){
  const el=$('content-chat');
  if(el)el.innerHTML='<div class="loading">Chatbot-Daten werden geladen…</div>';
  try{
    const r=await fetch('/dashboard/chat?days='+curDays,{headers:{'X-Dashboard-Token':_pw}});
    if(!r.ok)throw new Error('HTTP '+r.status);
    const d=await r.json();
    renderChat(d);
  }catch(e){if(el)el.innerHTML='<div class="loading">Fehler: '+e.message+'</div>';}
}
function renderChat(d){
  const el=$('content-chat');
  if(!el)return;
  const sessions=d.sessions||0,msgs=d.messages||0,leads=d.leads||0;
  const leadRate=msgs>0?((leads/msgs)*100).toFixed(1):'0.0';
  const topics=d.topics||[];
  const maxT=topics[0]?topics[0][1]:1;
  const logs=d.log||[];
  const unanswered=d.unanswered||[];
  const daily=d.daily||[];

  const convMap={};
  [...logs].reverse().forEach(r=>{
    const sid=r.session_id||'anon';
    if(!convMap[sid])convMap[sid]=[];
    convMap[sid].push(r);
  });
  const convs=Object.entries(convMap).sort((a,b)=>new Date(b[1][b[1].length-1].created_at)-new Date(a[1][a[1].length-1].created_at));

  el.innerHTML=`
  <div class="sec">
    <div class="sec-title"><span class="sec-icon">💬</span> Chatbot-Übersicht</div>
    <div class="kpi-grid">
      <div class="kpi k-n"><div class="kpi-icon">💬</div><div class="kpi-label">Chat-Sessions</div><div class="kpi-value">${sessions}</div><div class="kpi-sub">Einzelne Gespräche</div></div>
      <div class="kpi k-n"><div class="kpi-icon">✉️</div><div class="kpi-label">Nachrichten</div><div class="kpi-value">${msgs}</div><div class="kpi-sub">Fragen von Besuchern</div></div>
      <div class="kpi k-c"><div class="kpi-icon">🎯</div><div class="kpi-label">Leads</div><div class="kpi-value">${leads}</div><div class="kpi-sub">Kontakt-Absicht erkannt</div></div>
      <div class="kpi k-g"><div class="kpi-icon">📈</div><div class="kpi-label">Lead-Rate</div><div class="kpi-value">${leadRate}%</div><div class="kpi-sub">Anteil mit Lead-Absicht</div></div>
    </div>
  </div>

  ${daily.length>0?`
  <div class="sec">
    <div class="sec-title"><span class="sec-icon">📅</span> Chat-Verlauf</div>
    <div class="card"><div class="card-title">Nachrichten pro Tag</div><div class="card-sub">Nutzungsfrequenz des Chatbots</div><div class="chart-wrap"><canvas id="cch"></canvas></div></div>
  </div>`:''}

  <div class="sec">
    <div class="sec-title"><span class="sec-icon">🔥</span> Top-Themen — Was interessiert die Besucher?</div>
    <div class="card">
      ${topics.length>0?`<div class="clist">${topics.map((t,i)=>`<div class="citem"><div class="crank">${i+1}</div><div class="cname">${esc(t[0])}</div><div class="cbar-wrap"><div class="cbar"><div class="cbar-fill" style="width:${Math.round(t[1]/maxT*100)}%"></div></div></div><div class="ccount">${t[1]}</div></div>`).join('')}</div>`:`<div class="empty-state"><div class="e-icon">💬</div><p>Noch keine Chat-Daten.<br>Sobald jemand den Chatbot nutzt, erscheinen hier die Themen.</p></div>`}
    </div>
  </div>

  ${unanswered.length>0?`
  <div class="sec">
    <div class="sec-title"><span class="sec-icon">❓</span> Unbeantwortete Fragen (${unanswered.length})</div>
    <div class="sec-sub">Fragen ohne Treffer — zeigen Wissenslücken und mögliche Erweiterungen des Chatbots</div>
    <div class="card" style="padding:0;overflow:hidden">
      <table class="perf-table">
        <thead><tr><th>Datum/Zeit</th><th>Frage</th></tr></thead>
        <tbody>${unanswered.map(r=>`<tr><td style="white-space:nowrap">${new Date(r.created_at).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}</td><td>${esc(r.user_message)}</td></tr>`).join('')}</tbody>
      </table>
    </div>
  </div>`:''}

  ${convs.length>0?`
  <div class="sec">
    <div class="sec-title"><span class="sec-icon">📋</span> Gespräche (${convs.length} Sessions)</div>
    <div style="display:flex;flex-direction:column;gap:8px">
      ${convs.map(([sid,ms])=>{
        const last=ms[ms.length-1];
        const dt=new Date(last.created_at).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});
        const previewRaw=(ms[0].user_message||'').slice(0,60);
        const preview=esc(previewRaw);
        const hasLead=ms.some(m=>m.led_to_contact);
        return`<details style="background:#fff;border-radius:var(--radius);box-shadow:var(--shadow);overflow:hidden">
          <summary style="padding:14px 20px;cursor:pointer;display:flex;align-items:center;gap:12px;list-style:none;font-size:13px;user-select:none">
            <span style="color:var(--ink2);white-space:nowrap;flex-shrink:0">${dt}</span>
            <span style="flex:1;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">"${preview}${previewRaw.length>=60?'…':''}"</span>
            <span style="color:var(--ink2);white-space:nowrap;flex-shrink:0">${ms.length} Nachricht${ms.length>1?'en':''}</span>
            ${hasLead?'<span class="perf-badge perf-gut" style="flex-shrink:0">Lead</span>':''}
          </summary>
          <div style="border-top:1px solid var(--bdr);padding:16px 20px;display:flex;flex-direction:column;gap:12px">
            ${ms.map(m=>`<div>
              <div style="font-size:10px;font-weight:700;color:var(--c);text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">Besucher</div>
              <div style="font-size:13px;color:var(--ink);background:rgba(140,26,42,.06);padding:8px 12px;border-radius:6px;line-height:1.5">${esc(m.user_message)}</div>
              <div style="font-size:10px;font-weight:700;color:var(--n);text-transform:uppercase;letter-spacing:.08em;margin:8px 0 4px">Chatbot${m.matched_topic?' · <span style="font-weight:400;text-transform:none;letter-spacing:0">'+esc(m.matched_topic)+'</span>':''}</div>
              <div style="font-size:13px;color:var(--ink2);background:var(--page);padding:8px 12px;border-radius:6px;line-height:1.5">${esc((m.bot_reply||'').slice(0,220))}${(m.bot_reply||'').length>220?'…':''}</div>
            </div>`).join('<div style="height:1px;background:var(--bdr)"></div>')}
          </div>
        </details>`;
      }).join('')}
    </div>
  </div>`:''}
  `;

  if(daily.length){
    const ttOpts={backgroundColor:'rgba(13,28,63,.92)',titleColor:'#fff',bodyColor:'rgba(255,255,255,.75)',padding:10,cornerRadius:6,displayColors:false};
    const dL=daily.map(x=>new Date(x[0]).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit'}));
    const dV=daily.map(x=>x[1]);
    const canv=$('cch');
    if(canv)new Chart(canv,{type:'line',data:{labels:dL,datasets:[{data:dV,borderColor:C,borderWidth:2,backgroundColor:'rgba(140,26,42,.08)',fill:true,tension:0.4,pointRadius:dV.length<15?4:0,pointHoverRadius:6,pointBackgroundColor:G,pointBorderColor:C,pointBorderWidth:1.5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:ttOpts},scales:{x:{grid:{color:'rgba(0,0,0,.05)'},ticks:{color:'#999',font:{size:10}},border:{display:false}},y:{grid:{color:'rgba(0,0,0,.05)'},ticks:{color:'#999',font:{size:10}},border:{display:false},beginAtZero:true}}}});
  }
}

/* ===== CRM PIPELINE / LEADS ===== */
function prodLabel(k){const m={'ki-pass':'KI Pass','content-planer':'Content Planer','beratung':'Beratung'};return m[k]||k||'—';}
function leadValue(l){const p={'ki-pass':59,'content-planer':490,'beratung':1200};return p[l.produkt]||500;}
function fmtEur(n){return n.toLocaleString('de-DE')+' €';}
function mailLabel(m){return{w1:'Erstantwort',w2:'Kosten des Wartens',w3:'Letzte Einladung',c1:'Erstantwort',c2:'Das stille Problem',c3:'Die eigentliche Frage',c4:'Konkretes Bild',c5:'Abschluss'}[(m||'').toLowerCase()]||m||'—';}
function leadName(l){const n=((l.vorname||'')+' '+(l.nachname||'')).trim();return n||l.email||'Unbekannt';}

async function loadLeads(){
  const el=$('leads-content');
  if(!el)return;
  el.innerHTML='<div class="loading">Leads werden geladen…</div>';
  try{
    const r=await fetch('/dashboard/leads',{headers:{'X-Dashboard-Token':_pw}});
    if(!r.ok)throw new Error('HTTP '+r.status);
    const leads=await r.json();
    renderLeads(Array.isArray(leads)?leads:[]);
  }catch(e){el.innerHTML='<div class="loading">Fehler beim Laden der Leads: '+e.message+'</div>';}
}

function renderLeads(leads){
  _leadsCache=leads;
  const el=$('leads-content');
  if(!el)return;
  const gewonnen=leads.filter(l=>l.abschluss==='gewonnen');
  const verloren=leads.filter(l=>l.abschluss==='verloren');
  const active=leads.filter(l=>!l.abschluss);
  const hot=active.filter(l=>l.score==='hot');
  const warm=active.filter(l=>l.score==='warm');
  const cold=active.filter(l=>l.score==='cold');

  function stg(l){
    const d=Math.floor((Date.now()-new Date(l.created_at))/86400000);
    if(l.score==='warm')return d<3?'w1':d<7?'w2':'w3';
    return d<3?'c1':d<7?'c2':d<11?'c3':d<15?'c4':'c5';
  }
  function stgDate(l){
    if(!l.stage_entered_at)return'';
    return new Date(l.stage_entered_at).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',year:'numeric'});
  }
  function dSince(l){return Math.floor((Date.now()-new Date(l.created_at))/86400000);}
  function isRotting(l){
    const ref=l.stage_entered_at||l.created_at;
    return Math.floor((Date.now()-new Date(ref))/86400000)>=3;
  }
  function lastContact(l){
    const ref=l.stage_entered_at||l.created_at;
    const d=Math.floor((Date.now()-new Date(ref))/86400000);
    return d===0?'Heute':d===1?'Gestern':'vor '+d+'d';
  }

  function pipeCard(l){
    const idx=_leadsCache.indexOf(l);
    const d=dSince(l);
    const rot=isRotting(l);
    const pain=l.herausforderung?(l.herausforderung.length>80?l.herausforderung.slice(0,80)+'…':l.herausforderung):'';
    return`<div class="pipe-card${rot?' rotting':''}" onclick="openLead(_leadsCache[${idx}])">
      <div class="pipe-card-top">
        <span class="pipe-name">${esc(leadName(l))}</span>
        <span class="score-${esc(l.score||'cold')}" style="font-size:10px">${esc((l.score||'').toUpperCase())}</span>
      </div>
      ${rot?`<span class="rot-badge">&#9888; Kein Kontakt seit ${lastContact(l)}</span>`:''}
      ${l.unternehmen?`<div class="pipe-co">${esc(l.unternehmen)}</div>`:''}
      ${pain?`<div class="pipe-pain">${esc(pain)}</div>`:''}
      <div class="pipe-foot">
        ${l.produkt?`<span class="pipe-tag">${esc(prodLabel(l.produkt))}</span>`:''}
        <span class="pipe-tag pipe-day">${d===0?'heute':d+'d im Funnel'}</span>
        <span class="last-contact">Letzter Kontakt: ${lastContact(l)}</span>
        ${l.email?`<a class="pipe-mail" href="mailto:${esc(l.email)}" onclick="event.stopPropagation()">Mail ↗</a>`:''}
      </div>
    </div>`;
  }

  function pipeCol(title,stagLeads,hcls){
    return`<div class="pipe-col">
      <div class="pipe-col-hd ${hcls}">
        <span class="pipe-col-lbl" title="${title}">${title}</span>
        <span class="pipe-col-cnt">${stagLeads.length}</span>
      </div>
      <div class="pipe-col-body">${stagLeads.length>0?stagLeads.map(pipeCard).join(''):'<div class="pipe-none">Keine</div>'}</div>
    </div>`;
  }

  const hotHtml=hot.length===0?'':
  `<div class="hot-zone">
    <div class="hot-zone-hd">Sofort handeln — ${hot.length} Hot Lead${hot.length>1?'s':''}</div>
    <div class="hot-zone-cards">${hot.map(l=>{
      const idx=_leadsCache.indexOf(l);
      const d=dSince(l);
      const pain=l.herausforderung?(l.herausforderung.length>100?l.herausforderung.slice(0,100)+'…':l.herausforderung):'';
      return`<div class="hot-zcard" onclick="openLead(_leadsCache[${idx}])">
        <div class="hot-zname">${esc(leadName(l))}</div>
        ${l.unternehmen?`<div class="hot-zco">${esc(l.unternehmen)}</div>`:''}
        ${pain?`<div class="hot-zpain">${esc(pain)}</div>`:''}
        <div class="hot-zmeta">${l.email?esc(l.email):'—'}${l.telefon?' · '+esc(l.telefon):''} · ${d===0?'heute':d+'d'} im Funnel</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          ${l.email?`<a class="hot-zbtn" href="mailto:${esc(l.email)}" onclick="event.stopPropagation()">Mail schreiben ↗</a>`:''}
          ${l.telefon?`<a class="hot-zbtn" href="tel:${esc(l.telefon)}" onclick="event.stopPropagation()" style="background:rgba(255,255,255,.2);color:#fff;border:1px solid rgba(255,255,255,.4)">Anrufen ↗</a>`:''}
        </div>
      </div>`;
    }).join('')}</div>
  </div>`;

  const warmVal=warm.reduce((s,l)=>s+leadValue(l),0);
  const coldVal=cold.reduce((s,l)=>s+leadValue(l),0);
  const warmHtml=`<div class="pipe-track" style="background:linear-gradient(160deg,rgba(196,154,58,.1) 0%,rgba(196,154,58,.04) 40%,transparent 100%);border:1.5px solid rgba(196,154,58,.2)">
    <div class="pipe-track-lbl warm-lbl">&#x1F525; Warm-Spur <span style="font-weight:400;font-size:11px;letter-spacing:0;text-transform:none;opacity:.8">${warm.length} Leads &nbsp;·&nbsp; ${fmtEur(warmVal)}</span></div>
    <div class="pipe-row pipe-row-3">
      ${pipeCol('Erstantwort',warm.filter(l=>stg(l)==='w1'),'warm-hd')}
      ${pipeCol('Kosten des Wartens',warm.filter(l=>stg(l)==='w2'),'warm-hd')}
      ${pipeCol('Letzte Einladung',warm.filter(l=>stg(l)==='w3'),'warm-hd')}
    </div>
  </div>`;

  const coldHtml=`<div class="pipe-track" style="background:linear-gradient(160deg,rgba(13,28,63,.08) 0%,rgba(13,28,63,.03) 40%,transparent 100%);border:1.5px solid rgba(74,127,193,.2)">
    <div class="pipe-track-lbl cold-lbl">&#x2744;&#xFE0F; Kalt-Spur <span style="font-weight:400;font-size:11px;letter-spacing:0;text-transform:none;opacity:.8">${cold.length} Leads &nbsp;·&nbsp; ${fmtEur(coldVal)}</span></div>
    <div class="pipe-row pipe-row-5">
      ${pipeCol('Erstantwort',cold.filter(l=>stg(l)==='c1'),'cold-hd')}
      ${pipeCol('Das stille Problem',cold.filter(l=>stg(l)==='c2'),'cold-hd')}
      ${pipeCol('Die eigentliche Frage',cold.filter(l=>stg(l)==='c3'),'cold-hd')}
      ${pipeCol('Konkretes Bild',cold.filter(l=>stg(l)==='c4'),'cold-hd')}
      ${pipeCol('Abschluss',cold.filter(l=>stg(l)==='c5'),'cold-hd')}
    </div>
  </div>`;

  const abschlussHtml=`<div class="pipe-track" style="background:linear-gradient(160deg,rgba(26,92,46,.07) 0%,transparent 100%);border:1.5px solid rgba(42,138,70,.18)">
    <div class="pipe-track-lbl abschluss-lbl">&#x2705; Abgeschlossen</div>
    <div class="pipe-row pipe-row-2">
      <div class="pipe-col"><div class="pipe-col-hd won-hd"><span class="pipe-col-lbl">Gewonnen</span><span class="pipe-col-cnt">${gewonnen.length}</span></div><div class="pipe-col-body">${gewonnen.length>0?gewonnen.map(pipeCard).join(''):'<div class="pipe-none">Keine</div>'}</div></div>
      <div class="pipe-col"><div class="pipe-col-hd lost-hd"><span class="pipe-col-lbl">Nicht gewonnen</span><span class="pipe-col-cnt">${verloren.length}</span></div><div class="pipe-col-body">${verloren.length>0?verloren.map(pipeCard).join(''):'<div class="pipe-none">Keine</div>'}</div></div>
    </div>
  </div>`;

  el.innerHTML=`
  <div class="sec" style="margin-top:0">
    <div class="sec-title"><span class="sec-icon">⏰</span> Aktionszentrale</div>
    ${renderAktionszentrale(leads)}
  </div>
  ${hotHtml}
  <div class="pipe-bar">
    <div class="pipe-stats"><b>${active.length}</b> aktiv &nbsp;·&nbsp; <span style="color:var(--c)"><b>${hot.length}</b> Hot</span> &nbsp;·&nbsp; <span style="color:#8C5A00"><b>${warm.length}</b> Warm</span> &nbsp;·&nbsp; <span style="color:var(--info)"><b>${cold.length}</b> Kalt</span>${gewonnen.length+verloren.length>0?` &nbsp;·&nbsp; <span style="color:#1a6b2e"><b>${gewonnen.length}</b> Gewonnen</span> &nbsp;·&nbsp; <span style="color:var(--c)"><b>${verloren.length}</b> Nicht gew.</span>`:''} &nbsp;·&nbsp; <span style="color:#1a5c2e;font-weight:700">&#128176; Pipeline: ${fmtEur(active.reduce((s,l)=>s+leadValue(l),0))}</span></div>
    <button onclick="loadLeads()" class="pipe-rbtn">Aktualisieren</button>
  </div>
  ${leads.length===0?'<div class="empty-state" style="margin-top:60px"><div class="e-icon">📋</div><p>Noch keine Leads vorhanden.<br>Sobald das erste Formular abgesendet wird, erscheint es hier.</p></div>':''}
  ${warmHtml}
  ${coldHtml}
  ${abschlussHtml}
  <div id="tl-section" style="margin-top:32px"></div>`;

  loadAndRenderTimeline(leads);
}

function renderAktionszentrale(leads){
  const tom=new Date();tom.setHours(0,0,0,0);tom.setDate(tom.getDate()+1);
  const dat=new Date(tom);dat.setDate(dat.getDate()+1);
  const active=leads.filter(l=>l.next_action_at);
  const heute=active.filter(l=>new Date(l.next_action_at)<tom);
  const morgen=active.filter(l=>{const d=new Date(l.next_action_at);return d>=tom&&d<dat;});
  const warten=active.filter(l=>new Date(l.next_action_at)>=dat);
  function akCard(l){
    const nm=leadName(l);
    const idx=_leadsCache.indexOf(l);
    const typ={call:'Anrufen',mail:'E-Mail senden',auto:'Automatisch',none:'Keine Aktion'}[l.next_action_type]||'Nachfassen';
    const heraus=l.herausforderung?(l.herausforderung.length>65?l.herausforderung.slice(0,65)+'…':l.herausforderung):'';
    return`<div class="ak-card" onclick="openLead(_leadsCache[${idx}])" style="cursor:pointer">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
        <div class="ak-name">${esc(nm)}</div>
        <span class="score-${esc(l.score||'cold')}" style="font-size:10px">${esc((l.score||'—').toUpperCase())}</span>
      </div>
      ${heraus?`<div style="font-size:11px;color:var(--ink2);margin-bottom:7px;line-height:1.5">${esc(heraus)}</div>`:''}
      <div class="ak-grund">${typ}${l.email?' · '+esc(l.email):''}</div>
      <div class="ak-btns"><a class="ak-btn call" href="tel:${esc(l.telefon||'')}">Anrufen</a><a class="ak-btn mail" href="mailto:${esc(l.email||'')}">Mail ↗</a></div>
    </div>`;
  }
  function akCol(ls,cls,lbl){
    return`<div class="ak-col ${cls}"><div class="ak-head">${lbl}<span style="margin-left:auto;font-size:14px;font-weight:800">${ls.length}</span></div><div class="ak-body">${ls.length>0?ls.map(akCard).join(''):'<div class="ak-empty">Nichts fällig</div>'}</div></div>`;
  }
  if(active.length===0)return`<div class="ak-grid">${akCol([],'heute','Heute')}${akCol([],'morgen','Morgen')}${akCol([],'warten','Kann warten')}</div><div style="font-size:12px;color:var(--ink2);padding:12px 0">Noch keine Aktionen geplant.</div>`;
  return`<div class="ak-grid">${akCol(heute,'heute','Heute')}${akCol(morgen,'morgen','Morgen')}${akCol(warten,'warten','Kann warten')}</div>`;
}

async function loadAndRenderTimeline(leads){
  _tlLeads=leads;
  try{
    const r=await fetch('/dashboard/timeline',{headers:{'X-Dashboard-Token':_pw}});
    const data=await r.json();
    _tlEvts=Array.isArray(data)?data:[];
  }catch(e){_tlEvts=[];}
  renderTimeline(_tlLeads,_tlEvts,'all');
}

function renderTimeline(leads,events,filter){
  const el=document.getElementById('tl-section');
  if(!el)return;
  const sent=events.filter(e=>e.type==='email_sent').length;
  const opened=events.filter(e=>e.type==='email_opened').length;
  const clicked=events.filter(e=>e.type==='email_clicked').length;
  const daysArr=leads.map(l=>{
    const evts=events.filter(e=>e.lead_id===l.id||e.contact_id===l.email);
    if(evts.length<2)return 0;
    return Math.ceil((new Date(evts[evts.length-1].created_at)-new Date(evts[0].created_at))/86400000);
  });
  const avg=daysArr.length>0?Math.round(daysArr.reduce((a,b)=>a+b,0)/daysArr.length):0;
  const TL={form_submitted:'Formular ausgefüllt',email_sent:'E-Mail gesendet',email_opened:'E-Mail geöffnet',email_clicked:'Link geklickt',stage_changed:'Status geändert',call_made:'Anruf',manual_mail:'Manuelle Mail',note_added:'Notiz'};
  const DC={form_submitted:'dot-form',email_sent:'dot-sent',email_opened:'dot-opened',email_clicked:'dot-clicked',stage_changed:'dot-stage',call_made:'dot-call',manual_mail:'dot-sent',note_added:'dot-note'};
  const mailT=['email_sent','email_opened','email_clicked','manual_mail'];
  const statT=['form_submitted','stage_changed'];
  const blocks=leads.map(l=>{
    const nm=((l.vorname||'')+' '+(l.nachname||'')).trim()||l.email||'Unbekannt';
    let evts=events.filter(e=>e.lead_id===l.id||e.contact_id===l.email);
    if(filter==='mail')evts=evts.filter(e=>mailT.includes(e.type));
    if(filter==='status')evts=evts.filter(e=>statT.includes(e.type));
    const items=evts.length>0?evts.map(e=>{
      const dt=new Date(e.created_at).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'});
      const meta=e.metadata?Object.values(e.metadata).filter(v=>typeof v==='string').join(' · '):'';
      return`<div class="tl-evt"><div class="tl-dot ${DC[e.type]||'dot-note'}"></div><div><div class="tl-evt-lbl">${TL[e.type]||esc(e.type)}${meta?` <span style="font-weight:400;font-size:11px;color:var(--ink2)">— ${esc(meta)}</span>`:''}</div><div class="tl-evt-meta">${dt}</div></div></div>`;
    }).join(''):`<div style="font-size:12px;color:var(--ink2);opacity:.5;padding:4px 0">Noch keine Ereignisse aufgezeichnet</div>`;
    return`<div class="tl-lead-block"><div class="tl-lead-hd"><span>${esc(nm)}</span><span class="score-${esc(l.score||'cold')}">${esc((l.score||'—').toUpperCase())}</span></div><div class="tl-track">${items}</div></div>`;
  }).join('');
  el.innerHTML=`
  <div class="sec-title" style="margin-top:32px"><span class="sec-icon">📅</span> E-Mail-Verlauf & Timeline</div>
  <div class="tl-kpis">
    <div class="tl-kpi"><div class="tl-kpi-val">${sent}</div><div class="tl-kpi-lbl">Mails gesendet</div></div>
    <div class="tl-kpi"><div class="tl-kpi-val">${opened}</div><div class="tl-kpi-lbl">Öffnungen</div></div>
    <div class="tl-kpi"><div class="tl-kpi-val">${clicked}</div><div class="tl-kpi-lbl">Klicks</div></div>
    <div class="tl-kpi"><div class="tl-kpi-val">${avg}</div><div class="tl-kpi-lbl">Ø Tage aktiv</div></div>
  </div>
  <div class="tl-filter">
    <button class="tl-fbtn ${filter==='all'?'active':''}" onclick="setTlFilter('all')">Alle</button>
    <button class="tl-fbtn ${filter==='mail'?'active':''}" onclick="setTlFilter('mail')">Nur Mails</button>
    <button class="tl-fbtn ${filter==='status'?'active':''}" onclick="setTlFilter('status')">Nur Status</button>
  </div>
  ${leads.length>0?blocks:'<div class="empty-state"><div class="e-icon">📅</div><p>Noch keine Leads vorhanden.</p></div>'}`;
}

function setTlFilter(f){renderTimeline(_tlLeads,_tlEvts,f);}

function openLead(l){
  if(!l)return;
  document.getElementById('lp-name').textContent=leadName(l);
  document.getElementById('lp-lemail').textContent=l.email||'Keine E-Mail';
  const sc=document.getElementById('lp-score');
  sc.className='score-'+(l.score||'cold');
  sc.textContent=(l.score||'—').toUpperCase();
  const evts=_tlEvts.filter(e=>e.contact_id===l.email||(l.id&&e.lead_id===l.id));
  const TL={form_submitted:'Formular ausgefüllt',email_sent:'E-Mail gesendet',email_opened:'E-Mail geöffnet',email_clicked:'Link geklickt',stage_changed:'Status geändert',call_made:'Anruf',manual_mail:'Manuelle Mail',note_added:'Notiz'};
  const DC={form_submitted:'var(--g)',email_sent:'var(--n)',email_opened:'var(--ok)',email_clicked:'#0a5429',stage_changed:'#6b3fa0',call_made:'#8C5A00',manual_mail:'var(--n)',note_added:'var(--ink2)'};
  const tlHtml=evts.length>0?evts.map(e=>{
    const dt=new Date(e.created_at).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit'});
    const meta=e.metadata?Object.values(e.metadata).filter(v=>typeof v==='string').join(' · '):'';
    return`<div class="lp-tl-item"><div class="lp-tl-dot" style="background:${DC[e.type]||'var(--ink2)'}"></div><div><div class="lp-tl-lbl">${TL[e.type]||esc(e.type)}${meta?` <span style="font-weight:400;color:var(--ink2)">— ${esc(meta)}</span>`:''}</div><div class="lp-tl-meta">${dt}</div></div></div>`;
  }).join(''):`<div style="font-size:12px;color:var(--ink2);padding:4px 0">Noch keine Ereignisse aufgezeichnet</div>`;
  const dSince=Math.floor((Date.now()-new Date(l.created_at))/86400000);
  const eingang=new Date(l.created_at).toLocaleDateString('de-DE',{day:'2-digit',month:'2-digit',year:'numeric'});
  const s=[];
  s.push(`<div class="lp-section"><div class="lp-lbl">Kontakt</div><div class="lp-val">${l.email?esc(l.email):'—'}${l.telefon?'<br>'+esc(l.telefon):''}</div></div>`);
  s.push(`<div class="lp-2col"><div class="lp-section"><div class="lp-lbl">Mail-Stufe</div><div class="lp-val" style="font-weight:700;color:var(--n)">${esc(mailLabel(l.stage||l.empfohlene_mail))}</div></div><div class="lp-section"><div class="lp-lbl">Im Funnel seit</div><div class="lp-val">${dSince===0?'Heute':dSince+' Tage'} (${eingang})</div></div></div>`);
  if(l.herausforderung)s.push(`<div class="lp-section"><div class="lp-lbl">Schmerzpunkt</div><div class="lp-val" style="border-left:3px solid var(--c);background:#fdf2f2">${esc(l.herausforderung)}</div></div>`);
  if(l.zusammenfassung)s.push(`<div class="lp-section"><div class="lp-lbl">KI-Einschätzung</div><div class="lp-val">${esc(l.zusammenfassung)}</div></div>`);
  if(l.unternehmen||l.produkt)s.push(`<div class="lp-2col">${l.unternehmen?`<div class="lp-section"><div class="lp-lbl">Unternehmen</div><div class="lp-val">${esc(l.unternehmen)}</div></div>`:''}${l.produkt?`<div class="lp-section"><div class="lp-lbl">Interesse</div><div class="lp-val">${esc(prodLabel(l.produkt))}</div></div>`:''}</div>`);
  if(l.zeitplan)s.push(`<div class="lp-section"><div class="lp-lbl">Zeitplan / Dringlichkeit</div><div class="lp-val">${esc(l.zeitplan)}</div></div>`);
  s.push(`<div class="lp-section"><div class="lp-lbl">Verlauf</div>${tlHtml}</div>`);
  const callBtn=l.telefon?`<a class="lp-act-btn secondary" href="tel:${esc(l.telefon)}">Anrufen ↗</a>`:'<span class="lp-act-btn secondary" style="opacity:.4;cursor:default">Kein Telefon</span>';
  const abschlussBlock=l.abschluss
    ?`<div class="lp-section"><div class="lp-lbl">Status</div><div class="lp-val" style="font-weight:700;color:${l.abschluss==='gewonnen'?'#1a6b2e':'#9e1a2c'}">${l.abschluss==='gewonnen'?'Gewonnen':'Nicht gewonnen'}</div></div>`
    :`<div class="lp-section"><div class="lp-lbl">Abschluss</div><div class="lp-abschluss-btns"><button class="lp-won-btn" onclick="markAbschluss('${esc(l.id)}','gewonnen')">Gewonnen</button><button class="lp-lost-btn" onclick="markAbschluss('${esc(l.id)}','verloren')">Nicht gewonnen</button></div></div>`;
  document.getElementById('lp-body').innerHTML=`<div class="lp-act-btns">${l.email?`<a class="lp-act-btn primary" href="mailto:${esc(l.email)}">Mail schreiben ↗</a>`:''}${callBtn}</div>${s.join('')}${abschlussBlock}`;
  document.getElementById('lead-panel').classList.add('open');
  document.getElementById('lead-overlay').classList.add('open');
}

function closeLeadPanel(){
  document.getElementById('lead-panel').classList.remove('open');
  document.getElementById('lead-overlay').classList.remove('open');
}

async function markAbschluss(id,value){
  const label=value==='gewonnen'?'Gewonnen':'Nicht gewonnen';
  if(!confirm('Lead als "'+label+'" markieren?'))return;
  try{
    const r=await fetch('/dashboard/lead/abschluss',{
      method:'POST',
      headers:{'Content-Type':'application/json','X-Dashboard-Token':_pw},
      body:JSON.stringify({id:id,abschluss:value})
    });
    if(!r.ok)throw new Error('HTTP '+r.status);
  }catch(e){alert('Fehler beim Speichern: '+e.message);return;}
  closeLeadPanel();
  loadLeads();
}
</script>
</body>
</html>"""

SITE_URL = "https://anme15.github.io/Sensibilis-Ki/"
ROBOTS_URL = "https://anme15.github.io/Sensibilis-Ki/robots.txt"
LLMS_URL   = "https://anme15.github.io/Sensibilis-Ki/llms.txt"

AI_BOTS = ["GPTBot","ClaudeBot","PerplexityBot","anthropic-ai","GoogleBot","Googlebot-Extended","cohere-ai","YouBot","BingBot"]

@app.get("/dashboard/seo")
async def dashboard_seo(request: Request):
    _pruefe(request)

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
    from fastapi.responses import HTMLResponse as HR
    return HR(content=DASHBOARD_HTML, headers={"Cache-Control": "no-store"})

@app.get("/dashboard/data")
def dashboard_data(request: Request, days: int = Query(default=30), compare: bool = Query(default=False)):
    import traceback
    _pruefe(request)
    try:
        return _dashboard_data_inner(days, compare)
    except Exception as exc:
        traceback.print_exc()                      # vollstaendig, aber nur ins Render-Log
        raise HTTPException(status_code=500, detail=f"{type(exc).__name__}: {exc}")

def _dashboard_data_inner(days: int, compare: bool):
    now  = datetime.now(timezone.utc)
    d7   = (now - timedelta(days=7)).isoformat()
    d30  = (now - timedelta(days=days)).isoformat()
    prev_start = (now - timedelta(days=days*2)).isoformat()
    prev_end   = (now - timedelta(days=days)).isoformat()

    pv7  = sb.table("sensibilis_pageviews").select("page,session_id,device,is_new,ref_source,created_at").gte("created_at", d7).execute().data
    pv30 = sb.table("sensibilis_pageviews").select("page,session_id,device,is_new,ref_source,created_at").gte("created_at", d30).execute().data
    cl30 = sb.table("sensibilis_clicks").select("label,page,created_at").gte("created_at", d30).execute().data
    tm30 = sb.table("sensibilis_timing").select("page,time_on_page,scroll_depth,is_exit,created_at").gte("created_at", d30).execute().data
    try:
        emails = sb.table("sensibilis_emails").select("email,name,source,created_at").order("created_at", desc=True).limit(50).execute().data
    except Exception:
        emails = []

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


@app.get("/dashboard/chat")
def dashboard_chat(request: Request, days: int = Query(default=30)):
    _pruefe(request)
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).isoformat()
    rows = sb.table("sensibilis_chats").select("*").gte("created_at", since).order("created_at", desc=True).limit(500).execute().data
    sessions = len(set(r.get("session_id", "") for r in rows))
    messages = len(rows)
    leads = sum(1 for r in rows if r.get("led_to_contact"))
    topics: dict = {}
    daily: dict = {}
    for r in rows:
        t = r.get("matched_topic")
        if t:
            topics[t] = topics.get(t, 0) + 1
        d = (r.get("created_at") or "")[:10]
        if d:
            daily[d] = daily.get(d, 0) + 1
    unanswered = [r for r in rows if not r.get("matched_topic")]
    return {
        "sessions": sessions,
        "messages": messages,
        "leads": leads,
        "topics": sorted(topics.items(), key=lambda x: x[1], reverse=True),
        "daily": sorted(daily.items()),
        "unanswered": unanswered[:20],
        "log": rows[:100],
    }


# ── CRM: Leads und Timeline serverseitig, passwortgeschuetzt ──────────
@app.get("/dashboard/leads")
def dashboard_leads(request: Request):
    _pruefe(request)
    return sb.table("funnel_leads").select("*").order("created_at", desc=True).execute().data


@app.get("/dashboard/timeline")
def dashboard_timeline(request: Request):
    _pruefe(request)
    return sb.table("timeline_events").select("*").order("created_at").execute().data


@app.post("/dashboard/lead/abschluss")
async def dashboard_lead_abschluss(request: Request):
    _pruefe(request)
    daten   = await request.json()
    lead_id = (daten.get("id") or "").strip()
    wert    = daten.get("abschluss")
    if not lead_id or wert not in ("gewonnen", "verloren"):
        raise HTTPException(status_code=400, detail="Ungueltige Angaben")
    sb.table("funnel_leads").update({"abschluss": wert}).eq("id", lead_id).execute()
    return {"ok": True}
