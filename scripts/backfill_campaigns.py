#!/usr/bin/env python3
"""
backfill_campaigns.py — Retroactively group existing incidents into campaigns.

Run this ONCE after applying migration 004_campaigns.sql so historical
incidents already in `correlated_incidents` / `kill_chains` are grouped
under campaign records the same way new incidents will be.

Algorithm:
    1. Fetch all incidents ordered by detected_at ASC.
    2. Walk forward; group by actor_id (source_ip preferred, else
       target_username) where consecutive incidents fall within
       CAMPAIGN_IDLE_TIMEOUT seconds.
    3. For each group: build campaign row, INSERT, then UPDATE
       correlated_incidents.campaign_id and kill_chains.campaign_id
       to back-link.

Idempotent: incidents that already carry a campaign_id are skipped.

Usage:
    python scripts/backfill_campaigns.py
    python scripts/backfill_campaigns.py --dry-run
    python scripts/backfill_campaigns.py --idle-timeout 1800
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("backfill")

KILL_CHAIN_STAGES = [
    "reconnaissance", "weaponization", "delivery", "exploitation",
    "installation", "command_and_control", "actions_on_objectives",
]
TACTIC_TO_STAGE = {
    "Reconnaissance":       "reconnaissance",
    "Resource Development": "weaponization",
    "Initial Access":       "delivery",
    "Execution":            "exploitation",
    "Persistence":          "installation",
    "Privilege Escalation": "exploitation",
    "Defense Evasion":      "exploitation",
    "Credential Access":    "exploitation",
    "Discovery":            "reconnaissance",
    "Lateral Movement":     "exploitation",
    "Collection":           "actions_on_objectives",
    "Command and Control":  "command_and_control",
    "Exfiltration":         "actions_on_objectives",
    "Impact":               "actions_on_objectives",
}
SEV_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def pg_connect():
    if os.getenv("DATABASE_URL"):
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "database"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
    )


def actor_id(inc: Dict[str, Any]) -> Optional[str]:
    ip = inc.get("source_ip")
    if ip and ip not in ("0.0.0.0", "127.0.0.1", "?", "", "unknown"):
        return f"ip:{ip}"
    user = inc.get("target_username")
    if user:
        return f"user:{user}"
    return None


def stages_for(inc: Dict[str, Any]) -> List[str]:
    stages = set()
    for step in inc.get("kill_chain_steps") or []:
        tactic = step.get("tactic") or step.get("mitre_tactic")
        if tactic and tactic in TACTIC_TO_STAGE:
            stages.add(TACTIC_TO_STAGE[tactic])
    if not stages:
        t = inc.get("tactic")
        if t and t in TACTIC_TO_STAGE:
            stages.add(TACTIC_TO_STAGE[t])
    return sorted(stages, key=lambda s: KILL_CHAIN_STAGES.index(s))


def fetch_incidents(conn) -> List[Dict[str, Any]]:
    """Pull incidents joined with their kill chain so we can group properly."""
    sql = """
        SELECT
            ci.incident_id,
            ci.incident_type,
            ci.source_ip,
            ci.target_username,
            ci.severity,
            ci.confidence,
            ci.tactic,
            ci.mitre_techniques,
            ci.layers_involved,
            ci.campaign_id,
            kc.service_path,
            kc.steps           AS kill_chain_steps,
            kc.first_event_at,
            kc.detected_at,
            kc.severity        AS kc_severity
        FROM correlated_incidents ci
        LEFT JOIN kill_chains kc USING (incident_id)
        ORDER BY COALESCE(kc.first_event_at, kc.detected_at, NOW()) ASC
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        if isinstance(r.get("kill_chain_steps"), str):
            try:
                r["kill_chain_steps"] = json.loads(r["kill_chain_steps"])
            except Exception:
                r["kill_chain_steps"] = []
        r["kill_chain_steps"] = r.get("kill_chain_steps") or []
        r["service_path"]     = r.get("service_path") or []
        r["mitre_techniques"] = r.get("mitre_techniques") or []
        r["layers_involved"]  = r.get("layers_involved") or []
    return rows


def group_by_actor_window(
    incidents: List[Dict[str, Any]],
    idle_timeout: timedelta,
) -> List[List[Dict[str, Any]]]:
    """Walk forward; cut a new group when the same actor goes silent
    longer than idle_timeout."""
    open_groups: Dict[str, List[Dict[str, Any]]] = {}
    finalized: List[List[Dict[str, Any]]] = []

    for inc in incidents:
        if inc.get("campaign_id"):
            continue
        a = actor_id(inc)
        if not a:
            continue

        ts = inc.get("first_event_at") or inc.get("detected_at")
        if ts and ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        existing = open_groups.get(a)
        if existing:
            last_ts = existing[-1].get("first_event_at") or existing[-1].get("detected_at")
            if last_ts and last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
            if ts and last_ts and (ts - last_ts) > idle_timeout:
                finalized.append(existing)
                open_groups[a] = [inc]
                continue
            existing.append(inc)
        else:
            open_groups[a] = [inc]

    finalized.extend(open_groups.values())
    return [g for g in finalized if g]


def build_campaign(group: List[Dict[str, Any]]) -> Dict[str, Any]:
    a = actor_id(group[0])
    service_path: List[str] = []
    kc_steps: List[Dict[str, Any]] = []
    seen_evt = set()
    techniques: set = set()
    layers: set = set()
    stages: set = set()
    usernames: List[str] = []
    incident_ids: List[str] = []
    severity = "low"
    max_conf = 0.0
    first_at = None
    last_at = None

    for inc in group:
        incident_ids.append(str(inc["incident_id"]))
        for svc in inc.get("service_path") or []:
            if not service_path or service_path[-1] != svc:
                service_path.append(svc)
        for step in inc.get("kill_chain_steps") or []:
            evt = step.get("event_id")
            if evt and evt in seen_evt:
                continue
            kc_steps.append(step)
            if evt:
                seen_evt.add(evt)
        techniques |= set(inc.get("mitre_techniques") or [])
        layers     |= set(inc.get("layers_involved") or [])
        stages     |= set(stages_for(inc))
        u = inc.get("target_username")
        if u and u not in usernames:
            usernames.append(u)

        sv = (inc.get("severity") or "low").lower()
        if SEV_RANK.get(sv, 0) > SEV_RANK.get(severity, 0):
            severity = sv
        if inc.get("confidence"):
            try:
                max_conf = max(max_conf, float(inc["confidence"]))
            except (TypeError, ValueError):
                pass

        ts = inc.get("first_event_at") or inc.get("detected_at")
        if ts:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if first_at is None or ts < first_at:
                first_at = ts
            if last_at is None or ts > last_at:
                last_at = ts

    kc_steps.sort(key=lambda s: s.get("timestamp") or "")
    now = datetime.now(timezone.utc)

    return {
        "campaign_id":       str(uuid4()),
        "actor_id":          a,
        "source_ip":         group[0].get("source_ip"),
        "target_usernames":  usernames,
        "incident_ids":      incident_ids,
        "incident_count":    len(incident_ids),
        "service_path":      service_path,
        "kill_chain_steps":  kc_steps,
        "mitre_techniques":  sorted(techniques),
        "layers_involved":   sorted(layers),
        "stages_seen":       sorted(stages, key=lambda s: KILL_CHAIN_STAGES.index(s)
                                    if s in KILL_CHAIN_STAGES else 99),
        "severity":          severity,
        "max_confidence":    max_conf,
        "first_event_at":    first_at or now,
        "last_event_at":     last_at  or now,
        "status":            "closed",       # historical → closed
        "closed_reason":     "backfill",
        "closed_at":         now,
        "created_at":        now,
        "updated_at":        now,
    }


def insert_campaign(conn, c: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO campaigns (
                campaign_id, actor_id, source_ip, target_usernames,
                incident_ids, incident_count,
                service_path, kill_chain_steps,
                mitre_techniques, layers_involved, stages_seen,
                severity, max_confidence,
                first_event_at, last_event_at, status,
                closed_reason, closed_at,
                created_at, updated_at
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            ) ON CONFLICT (campaign_id) DO NOTHING
        """, (
            c["campaign_id"], c["actor_id"], c["source_ip"], c["target_usernames"],
            c["incident_ids"], c["incident_count"],
            c["service_path"], json.dumps(c["kill_chain_steps"]),
            c["mitre_techniques"], c["layers_involved"], c["stages_seen"],
            c["severity"], c["max_confidence"],
            c["first_event_at"], c["last_event_at"], c["status"],
            c["closed_reason"], c["closed_at"],
            c["created_at"], c["updated_at"],
        ))
        cur.execute("""
            UPDATE correlated_incidents
               SET campaign_id = %s
             WHERE incident_id = ANY(%s) AND campaign_id IS NULL
        """, (c["campaign_id"], c["incident_ids"]))
        cur.execute("""
            UPDATE kill_chains
               SET campaign_id = %s
             WHERE incident_id = ANY(%s) AND campaign_id IS NULL
        """, (c["campaign_id"], c["incident_ids"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--idle-timeout", type=int, default=1800,
                        help="Seconds of inactivity before splitting a campaign (default: 1800)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be inserted; do not write")
    args = parser.parse_args()

    idle = timedelta(seconds=args.idle_timeout)

    try:
        conn = pg_connect()
    except Exception as exc:
        log.error("Postgres connect failed: %s", exc)
        sys.exit(1)

    try:
        incidents = fetch_incidents(conn)
        log.info("fetched %d incidents", len(incidents))

        groups = group_by_actor_window(incidents, idle)
        log.info("derived %d campaign groups", len(groups))

        if not groups:
            log.info("nothing to backfill — exiting")
            return

        for i, g in enumerate(groups, 1):
            c = build_campaign(g)
            log.info(
                "[%d/%d] %s — %d incidents, severity=%s, stages=%s",
                i, len(groups), c["actor_id"], c["incident_count"],
                c["severity"], c["stages_seen"],
            )
            if args.dry_run:
                continue
            try:
                insert_campaign(conn, c)
                conn.commit()
            except Exception as exc:
                conn.rollback()
                log.error("failed to insert campaign for %s: %s", c["actor_id"], exc)
        log.info("backfill complete")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
