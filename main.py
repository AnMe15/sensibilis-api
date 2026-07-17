import os, json
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from supabase import create_client
import secrets

app = FastAPI()
security = HTTPBasic()

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

def check_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok = secrets.compare_digest(credentials.password.encode(), DASHBOARD_PASSWORD.encode())
    if not ok:
        raise HTTPException(status_code=401, detail="Nicht autorisiert",
                            headers={"WWW-Authenticate": "Basic"})
    return credentials.username

@app.get("/")
def root():
    return {"status": "Sensibilis Analytics API"}

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
def dashboard_data(username: str = Depends(check_auth)):
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
