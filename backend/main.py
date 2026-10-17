"""DevPet API — proxy FastAPI entre le widget et GitHub.

Le jeton GitHub reste ICI (variable d'environnement), jamais dans le HTML.
L'API ne renvoie que des statistiques agrégées (pas de noms de dépôts privés).
"""
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
USER = os.getenv("GITHUB_USER", "Mohamed-Gazali").strip()
TZ = ZoneInfo(os.getenv("TIMEZONE", "Africa/Niamey"))
ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500"
).split(",") if o.strip()]
CACHE_SECONDS = int(os.getenv("CACHE_SECONDS", "600"))

LANG_MAP = {
    "back": ["Python", "Java", "Go", "PHP", "C#", "C", "C++", "Rust", "Ruby", "Kotlin",
             "SQL", "PLpgSQL", "Shell", "Dockerfile", "PowerShell"],
    "front": ["JavaScript", "TypeScript", "HTML", "CSS", "SCSS", "Vue", "Svelte", "Dart"],
    "ai": ["Jupyter Notebook", "R"],
}

app = FastAPI(title="DevPet API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["GET"],
    allow_headers=["*"],
)

_cache: dict = {"ts": 0.0, "data": None}


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


async def _get(client: httpx.AsyncClient, url: str, params: dict | None = None):
    r = await client.get(url, params=params, headers=_headers())
    if r.status_code == 404:
        raise HTTPException(404, "Utilisateur GitHub introuvable")
    if r.status_code in (403, 429):
        raise HTTPException(429, "Limite de l'API GitHub atteinte")
    if r.status_code == 401:
        raise HTTPException(502, "Jeton GitHub invalide ou expiré")
    r.raise_for_status()
    return r.json()


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(TZ)


def compute_stats(events: list, repos: list) -> dict:
    now = datetime.now(TZ)
    per: dict = defaultdict(int)
    hours = [0] * 24
    c7 = c30 = c90 = n7 = 0
    last = None

    for ev in events:
        if ev.get("type") != "PushEvent":
            continue
        p = ev.get("payload") or {}
        n = max(1, p.get("size") or len(p.get("commits") or []) or 1)
        t = _parse(ev["created_at"])
        per[t.date()] += n
        c90 += n
        age = now - t
        if age < timedelta(days=30):
            c30 += n
        if age < timedelta(days=7):
            c7 += n
            if t.hour >= 23 or t.hour < 5:
                n7 += n
        hours[t.hour] += n
        if last is None or t > last:
            last = t

    d = now.date()
    if not per.get(d):
        d -= timedelta(days=1)
    streak = 0
    while per.get(d):
        streak += 1
        d -= timedelta(days=1)

    idle = (now.date() - last.date()).days if last else 999
    days = [per.get(now.date() - timedelta(days=i), 0) for i in range(27, -1, -1)]

    own = [r for r in repos if not r.get("fork")]
    recent = [r for r in own
              if r.get("pushed_at") and now - _parse(r["pushed_at"]) < timedelta(days=90)]
    pool = recent or own
    tr = {k: sum(1 for r in pool if r.get("language") in langs) for k, langs in LANG_MAP.items()}

    return {
        "commits7": c7, "commits30": c30, "commits90": c90,
        "today": per.get(now.date(), 0), "night7": n7,
        "streak": streak, "idle": idle, "days": days, "hours": hours,
        "tr": tr, "repos": len(own),
    }


async def build_stats() -> dict:
    base = f"https://api.github.com/users/{USER}"
    events_url = f"{base}/events" if TOKEN else f"{base}/events/public"
    repos_url = "https://api.github.com/user/repos" if TOKEN else f"{base}/repos"
    repo_params = {"per_page": 100, "sort": "pushed"}
    if TOKEN:
        repo_params["affiliation"] = "owner"

    async with httpx.AsyncClient(timeout=15) as client:
        repos = await _get(client, repos_url, repo_params)
        events: list = []
        for page in (1, 2, 3):
            chunk = await _get(client, events_url, {"per_page": 100, "page": page})
            if not chunk:
                break
            events += chunk
    return compute_stats(events, repos)


@app.get("/api/stats")
async def stats():
    if _cache["data"] and time.time() - _cache["ts"] < CACHE_SECONDS:
        return _cache["data"]
    data = await build_stats()
    _cache.update(ts=time.time(), data=data)
    return data


@app.get("/health")
async def health():
    return {"ok": True, "token_configured": bool(TOKEN)}
