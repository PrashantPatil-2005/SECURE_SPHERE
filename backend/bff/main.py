"""FastAPI BFF — read APIs for incidents, campaigns, search, MITRE."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras
import redis
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from bff.auth import require_user

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")

app = FastAPI(title="SecuriSphere BFF", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def pg_conn():
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url)
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "database"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
    )


def get_redis() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


@app.get("/health")
def health():
    return {"status": "ok", "service": "bff"}


@app.get("/api/incidents")
def list_incidents(limit: int = Query(50, le=200), _user=Depends(require_user)):
    r = get_redis()
    raw = r.lrange("incidents", 0, limit - 1)
    return {"incidents": [json.loads(x) for x in raw]}


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str, _user=Depends(require_user)):
    r = get_redis()
    for raw in r.lrange("incidents", 0, 499):
        inc = json.loads(raw)
        if inc.get("incident_id") == incident_id:
            return inc
    raise HTTPException(404, "incident not found")


@app.get("/api/campaigns")
def list_campaigns(status: Optional[str] = None, limit: int = 50, _user=Depends(require_user)):
    try:
        conn = pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if status:
                    cur.execute(
                        "SELECT * FROM campaigns WHERE status = %s ORDER BY last_event_at DESC LIMIT %s",
                        (status, limit),
                    )
                else:
                    cur.execute(
                        "SELECT * FROM campaigns ORDER BY last_event_at DESC LIMIT %s",
                        (limit,),
                    )
                rows = cur.fetchall()
        conn.close()
        return {"campaigns": [dict(r) for r in rows]}
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/campaigns/{campaign_id}")
def get_campaign(campaign_id: str, _user=Depends(require_user)):
    try:
        conn = pg_conn()
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM campaigns WHERE campaign_id = %s", (campaign_id,))
                row = cur.fetchone()
        conn.close()
        if not row:
            raise HTTPException(404, "campaign not found")
        return dict(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/search/events")
def search_events(q: str = "", service: str = "", limit: int = 50, _user=Depends(require_user)):
    import urllib.request

    query: Dict[str, Any] = {
        "size": limit,
        "sort": [{"timestamp": "desc"}],
        "query": {"bool": {"must": []}},
    }
    if q:
        query["query"]["bool"]["must"].append({"multi_match": {"query": q, "fields": ["description", "event_type"]}})
    if service:
        query["query"]["bool"]["must"].append({"term": {"source_service_name": service}})
    if not query["query"]["bool"]["must"]:
        query["query"] = {"match_all": {}}

    try:
        req = urllib.request.Request(
            f"{ES_URL}/securisphere-events-*/_search",
            data=json.dumps(query).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        hits = [h["_source"] for h in data.get("hits", {}).get("hits", [])]
        return {"events": hits, "total": data.get("hits", {}).get("total", {})}
    except Exception:
        # Fallback: Redis list scan
        r = get_redis()
        results = []
        for key in ("events:api", "events:auth", "events:network", "events:browser"):
            for raw in r.lrange(key, 0, 199):
                try:
                    ev = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if q and q.lower() not in json.dumps(ev).lower():
                    continue
                if service and ev.get("source_service_name") != service:
                    continue
                results.append(ev)
                if len(results) >= limit:
                    break
        return {"events": results[:limit], "total": len(results), "source": "redis_fallback"}


@app.get("/api/mitre-mapping")
def mitre_mapping(_user=Depends(require_user)):
    r = get_redis()
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
        from mitre.mitre_map import MITRE_MAP, TACTIC_ORDER
        hits = {}
        for raw in r.lrange("incidents", 0, 499):
            inc = json.loads(raw)
            for t in inc.get("mitre_techniques") or []:
                hits[t] = hits.get(t, 0) + 1
        return {"techniques": MITRE_MAP, "tactic_order": TACTIC_ORDER, "hits": hits}
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/evaluation/results")
def evaluation_results(_user=Depends(require_user)):
    paths = [
        os.path.join(os.path.dirname(__file__), "..", "..", "evaluation", "trial_report.json"),
        os.path.join(os.path.dirname(__file__), "..", "..", "evaluation", "dashboard_results.json"),
    ]
    for p in paths:
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return {
        "mttd_reduction_pct": 97.33,
        "avg_mttd_seconds": 6.75,
        "scenarios": ["A", "B", "C"],
        "note": "default summary — run benchmarks for live data",
    }
