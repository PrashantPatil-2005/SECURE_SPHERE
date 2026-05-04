"""
campaign_aggregator.py — SecuriSphere Campaign Aggregation Layer

Groups incidents into campaigns by attacker identity + rolling activity
window. A campaign is the top-level unit for analyst review and Discord
notification: multiple correlated incidents from the same actor collapse
into one campaign record so analysts see ONE escalating story rather than
N independent alerts.

Identity model
--------------
actor_id = "ip:<source_ip>"  (preferred)
         | "user:<target_username>"  (fallback when no IP is known)

Lifecycle
---------
- A campaign opens on the first incident from an actor.
- Subsequent incidents from the same actor merge in:
    * service_path is concatenated (consecutive duplicates collapsed)
    * kill_chain_steps merged (deduped by event_id, sorted by timestamp)
    * mitre_techniques / layers_involved / stages_seen unioned
    * severity is monotonic max
- A campaign auto-closes when CAMPAIGN_IDLE_TIMEOUT seconds pass without a
  new incident.
- Sweep thread (driven from CorrelationEngine) closes idle campaigns.

Persistence
-----------
- PostgreSQL: durable source of truth (`campaigns` table).
- Redis: hot cache keyed by actor_id (`campaign:active:<actor_id>`) for
  sub-millisecond lookup. Cache TTL = idle timeout + 60s slack.
- Partial unique index on (actor_id) WHERE status='active' guarantees
  at most one open campaign per actor across concurrent engine workers.

Public API
----------
ingest(incident) -> (campaign, change_kind)
    change_kind ∈ {"created", "escalated", "extended", "duplicate"}
sweep_idle() -> int
attach_discord_message(campaign_id, message_id, channel_id) -> None
"""

import json
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import psycopg2
import psycopg2.errors
import psycopg2.extras
import redis

logger = logging.getLogger("CampaignAggregator")

CAMPAIGN_IDLE_TIMEOUT = int(os.getenv("CAMPAIGN_IDLE_TIMEOUT", 1800))   # 30 min
CAMPAIGN_REDIS_PREFIX = "campaign:active:"
CAMPAIGN_INDEX_KEY    = "campaign:active:index"

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

_SEV_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


class CampaignAggregator:
    def __init__(self, redis_client: redis.Redis, pg_dsn_kwargs: Dict[str, Any]):
        self.redis = redis_client
        self.pg_kwargs = pg_dsn_kwargs
        self._lock = threading.RLock()
        self.idle_timeout = timedelta(seconds=CAMPAIGN_IDLE_TIMEOUT)
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def ingest(self, incident: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Attach incident to matching campaign or create new one.

        Returns (campaign, change_kind) where change_kind is:
          "created"    — new campaign opened
          "escalated"  — severity rose or new kill-chain stage entered
          "extended"   — appended without escalation
          "duplicate"  — incident already linked (idempotent retry)
        """
        with self._lock:
            actor_id = self._actor_id(incident)
            if not actor_id:
                logger.debug("incident lacks actor_id — skipping campaign attach")
                return ({}, "duplicate")

            existing = self._load_active_campaign(actor_id)
            if existing and self._is_idle(existing):
                self._close_campaign(existing, reason="idle_timeout")
                existing = None

            if existing is None:
                # Race-safe: partial unique index on (actor_id) WHERE status='active'
                campaign = self._create(actor_id, incident)
                try:
                    self._persist_insert(campaign)
                    kind = "created"
                except psycopg2.errors.UniqueViolation:
                    # Lost race with another worker — reload + merge
                    existing = self._load_active_campaign(actor_id)
                    if existing is None:
                        # Should not happen; fall back to extended state
                        return ({}, "duplicate")
                    campaign, kind = self._merge(existing, incident)
                    self._persist_update(campaign)
            else:
                if incident.get("incident_id") in existing["incident_ids"]:
                    return (existing, "duplicate")
                campaign, kind = self._merge(existing, incident)
                self._persist_update(campaign)

            self._cache(campaign)
            return (campaign, kind)

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @staticmethod
    def _actor_id(incident: Dict[str, Any]) -> Optional[str]:
        ip = incident.get("source_ip")
        if ip and ip not in ("0.0.0.0", "127.0.0.1", "?", "", "unknown"):
            return f"ip:{ip}"
        user = incident.get("target_username")
        if user:
            return f"user:{user}"
        return None

    # ------------------------------------------------------------------
    # Create / merge
    # ------------------------------------------------------------------

    def _create(self, actor_id: str, incident: Dict[str, Any]) -> Dict[str, Any]:
        now = _utcnow()
        first_evt = _parse_iso(incident.get("first_event_at")) or now
        return {
            "campaign_id":       str(uuid4()),
            "actor_id":          actor_id,
            "source_ip":         incident.get("source_ip"),
            "target_usernames":  [incident["target_username"]] if incident.get("target_username") else [],
            "incident_ids":      [incident["incident_id"]],
            "incident_count":    1,
            "service_path":      list(incident.get("service_path") or []),
            "kill_chain_steps":  list(incident.get("kill_chain_steps") or []),
            "mitre_techniques":  list(incident.get("mitre_techniques") or []),
            "layers_involved":   list(incident.get("layers_involved") or []),
            "stages_seen":       self._stages_for(incident),
            "severity":          (incident.get("severity") or "low").lower(),
            "max_confidence":    float(incident.get("confidence") or 0),
            "first_event_at":    first_evt,
            "last_event_at":     now,
            "status":            "active",
            "discord_message_id": None,
            "discord_channel_id": None,
            "created_at":        now,
            "updated_at":        now,
        }

    def _merge(self, campaign: Dict[str, Any],
                     incident: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        prev_severity = campaign["severity"]
        prev_stages   = set(campaign["stages_seen"])

        campaign["incident_ids"].append(incident["incident_id"])
        campaign["incident_count"] += 1

        for svc in (incident.get("service_path") or []):
            if not campaign["service_path"] or campaign["service_path"][-1] != svc:
                campaign["service_path"].append(svc)

        seen_evt = {s.get("event_id") for s in campaign["kill_chain_steps"] if s.get("event_id")}
        for step in (incident.get("kill_chain_steps") or []):
            evt_id = step.get("event_id")
            if evt_id and evt_id in seen_evt:
                continue
            campaign["kill_chain_steps"].append(step)
            if evt_id:
                seen_evt.add(evt_id)
        campaign["kill_chain_steps"].sort(key=lambda s: s.get("timestamp") or "")

        campaign["mitre_techniques"] = sorted(
            set(campaign["mitre_techniques"]) | set(incident.get("mitre_techniques") or [])
        )
        campaign["layers_involved"] = sorted(
            set(campaign["layers_involved"]) | set(incident.get("layers_involved") or [])
        )

        new_stages = set(self._stages_for(incident))
        merged_stages = (set(campaign["stages_seen"]) | new_stages)
        campaign["stages_seen"] = sorted(
            merged_stages,
            key=lambda s: KILL_CHAIN_STAGES.index(s) if s in KILL_CHAIN_STAGES else 99,
        )

        username = incident.get("target_username")
        if username and username not in campaign["target_usernames"]:
            campaign["target_usernames"].append(username)

        campaign["severity"] = self._max_severity(prev_severity, incident.get("severity"))
        if incident.get("confidence"):
            try:
                campaign["max_confidence"] = max(
                    campaign["max_confidence"], float(incident["confidence"])
                )
            except (TypeError, ValueError):
                pass

        campaign["last_event_at"] = _utcnow()
        campaign["updated_at"]    = _utcnow()

        if _SEV_RANK.get(campaign["severity"], 0) > _SEV_RANK.get(prev_severity, 0):
            kind = "escalated"
        elif new_stages - prev_stages:
            kind = "escalated"
        else:
            kind = "extended"
        return campaign, kind

    @staticmethod
    def _stages_for(incident: Dict[str, Any]) -> List[str]:
        stages = set()
        for step in incident.get("kill_chain_steps") or []:
            tactic = step.get("tactic") or step.get("mitre_tactic")
            if tactic and tactic in TACTIC_TO_STAGE:
                stages.add(TACTIC_TO_STAGE[tactic])
        if not stages:
            t = incident.get("tactic")
            if t and t in TACTIC_TO_STAGE:
                stages.add(TACTIC_TO_STAGE[t])
        return sorted(stages, key=lambda s: KILL_CHAIN_STAGES.index(s))

    @classmethod
    def _max_severity(cls, a: Optional[str], b: Optional[str]) -> str:
        a = (a or "low").lower()
        b = (b or "low").lower()
        return a if _SEV_RANK.get(a, 0) >= _SEV_RANK.get(b, 0) else b

    def _is_idle(self, campaign: Dict[str, Any]) -> bool:
        last = campaign.get("last_event_at")
        if isinstance(last, str):
            last = _parse_iso(last) or _utcnow()
        if last is None:
            return True
        return (_utcnow() - last) > self.idle_timeout

    # ------------------------------------------------------------------
    # Lookup / cache
    # ------------------------------------------------------------------

    def _load_active_campaign(self, actor_id: str) -> Optional[Dict[str, Any]]:
        try:
            raw = self.redis.get(CAMPAIGN_REDIS_PREFIX + actor_id)
            if raw:
                return self._deserialize(json.loads(raw))
        except Exception as exc:
            logger.debug("redis campaign lookup failed: %s", exc)

        try:
            with psycopg2.connect(**self.pg_kwargs) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""
                        SELECT * FROM campaigns
                        WHERE actor_id = %s AND status = 'active'
                        ORDER BY last_event_at DESC LIMIT 1
                    """, (actor_id,))
                    row = cur.fetchone()
            return self._deserialize(dict(row)) if row else None
        except Exception as exc:
            logger.debug("pg campaign lookup failed: %s", exc)
            return None

    def _cache(self, campaign: Dict[str, Any]) -> None:
        try:
            ttl = max(int(self.idle_timeout.total_seconds()) + 60, 60)
            self.redis.setex(
                CAMPAIGN_REDIS_PREFIX + campaign["actor_id"],
                ttl,
                json.dumps(self._serialize(campaign)),
            )
            self.redis.sadd(CAMPAIGN_INDEX_KEY, campaign["actor_id"])
        except Exception as exc:
            logger.debug("redis campaign cache failed: %s", exc)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_insert(self, c: Dict[str, Any]) -> None:
        with psycopg2.connect(**self.pg_kwargs) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO campaigns (
                        campaign_id, actor_id, source_ip, target_usernames,
                        incident_ids, incident_count,
                        service_path, kill_chain_steps,
                        mitre_techniques, layers_involved, stages_seen,
                        severity, max_confidence,
                        first_event_at, last_event_at, status,
                        discord_message_id, discord_channel_id,
                        created_at, updated_at
                    ) VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                    )
                """, (
                    c["campaign_id"], c["actor_id"], c["source_ip"], c["target_usernames"],
                    c["incident_ids"], c["incident_count"],
                    c["service_path"], json.dumps(c["kill_chain_steps"]),
                    c["mitre_techniques"], c["layers_involved"], c["stages_seen"],
                    c["severity"], c["max_confidence"],
                    c["first_event_at"], c["last_event_at"], c["status"],
                    c.get("discord_message_id"), c.get("discord_channel_id"),
                    c["created_at"], c["updated_at"],
                ))
                self._backlink(cur, c)

    def _persist_update(self, c: Dict[str, Any]) -> None:
        try:
            with psycopg2.connect(**self.pg_kwargs) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE campaigns SET
                            incident_ids       = %s,
                            incident_count     = %s,
                            service_path       = %s,
                            kill_chain_steps   = %s,
                            mitre_techniques   = %s,
                            layers_involved    = %s,
                            stages_seen        = %s,
                            severity           = %s,
                            max_confidence     = %s,
                            last_event_at      = %s,
                            target_usernames   = %s,
                            updated_at         = %s
                        WHERE campaign_id = %s
                    """, (
                        c["incident_ids"], c["incident_count"],
                        c["service_path"], json.dumps(c["kill_chain_steps"]),
                        c["mitre_techniques"], c["layers_involved"], c["stages_seen"],
                        c["severity"], c["max_confidence"],
                        c["last_event_at"], c["target_usernames"], c["updated_at"],
                        c["campaign_id"],
                    ))
                    self._backlink(cur, c)
        except Exception as exc:
            logger.error("campaign update failed (%s): %s", c.get("campaign_id"), exc)

    @staticmethod
    def _backlink(cur, c: Dict[str, Any]) -> None:
        """Stamp campaign_id onto the constituent incident + kill-chain rows."""
        try:
            cur.execute("""
                UPDATE correlated_incidents
                   SET campaign_id = %s
                 WHERE incident_id = ANY(%s)
                   AND campaign_id IS DISTINCT FROM %s
            """, (c["campaign_id"], c["incident_ids"], c["campaign_id"]))
            cur.execute("""
                UPDATE kill_chains
                   SET campaign_id = %s
                 WHERE incident_id = ANY(%s)
                   AND campaign_id IS DISTINCT FROM %s
            """, (c["campaign_id"], c["incident_ids"], c["campaign_id"]))
        except Exception as exc:
            logger.debug("campaign backlink failed: %s", exc)

    def _close_campaign(self, c: Dict[str, Any], reason: str) -> None:
        try:
            with psycopg2.connect(**self.pg_kwargs) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE campaigns
                           SET status = 'closed', closed_reason = %s,
                               closed_at = NOW(), updated_at = NOW()
                         WHERE campaign_id = %s
                    """, (reason, c["campaign_id"]))
            try:
                self.redis.delete(CAMPAIGN_REDIS_PREFIX + c["actor_id"])
                self.redis.srem(CAMPAIGN_INDEX_KEY, c["actor_id"])
            except Exception:
                pass
            logger.info("campaign %s closed (%s)", c["campaign_id"], reason)
        except Exception as exc:
            logger.warning("close campaign failed: %s", exc)

    # ------------------------------------------------------------------
    # Janitor
    # ------------------------------------------------------------------

    def sweep_idle(self) -> int:
        closed = 0
        try:
            actors = list(self.redis.smembers(CAMPAIGN_INDEX_KEY) or [])
        except Exception:
            actors = []

        # Also catch campaigns whose Redis cache was evicted but row still active
        try:
            with psycopg2.connect(**self.pg_kwargs) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT actor_id FROM campaigns
                         WHERE status = 'active'
                           AND last_event_at < NOW() - (%s || ' seconds')::interval
                    """, (str(int(self.idle_timeout.total_seconds())),))
                    actors.extend([r[0] for r in cur.fetchall()])
        except Exception as exc:
            logger.debug("sweep pg scan failed: %s", exc)

        for actor_id in set(actors):
            c = self._load_active_campaign(actor_id)
            if c and self._is_idle(c):
                self._close_campaign(c, reason="idle_timeout")
                closed += 1
        return closed

    # ------------------------------------------------------------------
    # Discord message tracking
    # ------------------------------------------------------------------

    def attach_discord_message(self, campaign_id: str,
                               message_id: Optional[str],
                               channel_id: Optional[str]) -> None:
        try:
            with psycopg2.connect(**self.pg_kwargs) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE campaigns
                           SET discord_message_id = %s,
                               discord_channel_id = %s,
                               updated_at = NOW()
                         WHERE campaign_id = %s
                    """, (message_id, channel_id, campaign_id))
            actor = self._actor_for_campaign(campaign_id)
            if actor:
                cached = self._load_active_campaign(actor)
                if cached:
                    cached["discord_message_id"] = message_id
                    cached["discord_channel_id"] = channel_id
                    self._cache(cached)
        except Exception as exc:
            logger.debug("attach_discord_message failed: %s", exc)

    def _actor_for_campaign(self, campaign_id: str) -> Optional[str]:
        try:
            with psycopg2.connect(**self.pg_kwargs) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT actor_id FROM campaigns WHERE campaign_id = %s",
                        (campaign_id,),
                    )
                    row = cur.fetchone()
                    return row[0] if row else None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Schema (idempotent — safe to call on every boot)
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS campaigns (
            campaign_id        UUID PRIMARY KEY,
            actor_id           VARCHAR(100) NOT NULL,
            source_ip          VARCHAR(45),
            target_usernames   TEXT[]       NOT NULL DEFAULT '{}',
            incident_ids       UUID[]       NOT NULL DEFAULT '{}',
            incident_count     INTEGER      NOT NULL DEFAULT 0,
            service_path       TEXT[]       NOT NULL DEFAULT '{}',
            kill_chain_steps   JSONB        NOT NULL DEFAULT '[]',
            mitre_techniques   TEXT[]       NOT NULL DEFAULT '{}',
            layers_involved    TEXT[]       NOT NULL DEFAULT '{}',
            stages_seen        TEXT[]       NOT NULL DEFAULT '{}',
            severity           VARCHAR(20)  NOT NULL DEFAULT 'low',
            max_confidence     FLOAT        NOT NULL DEFAULT 0,
            first_event_at     TIMESTAMPTZ  NOT NULL,
            last_event_at      TIMESTAMPTZ  NOT NULL,
            status             VARCHAR(20)  NOT NULL DEFAULT 'active',
            closed_reason      VARCHAR(40),
            closed_at          TIMESTAMPTZ,
            discord_message_id VARCHAR(40),
            discord_channel_id VARCHAR(40),
            created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
        );
        CREATE UNIQUE INDEX IF NOT EXISTS uq_campaign_active_actor
            ON campaigns (actor_id) WHERE status = 'active';
        CREATE INDEX IF NOT EXISTS idx_campaigns_status_last
            ON campaigns (status, last_event_at DESC);
        CREATE INDEX IF NOT EXISTS idx_campaigns_source_ip
            ON campaigns (source_ip);
        CREATE INDEX IF NOT EXISTS idx_campaigns_severity
            ON campaigns (severity);
        CREATE INDEX IF NOT EXISTS idx_campaigns_techniques_gin
            ON campaigns USING GIN (mitre_techniques);

        ALTER TABLE correlated_incidents
            ADD COLUMN IF NOT EXISTS campaign_id UUID;
        CREATE INDEX IF NOT EXISTS idx_incidents_campaign
            ON correlated_incidents (campaign_id);

        ALTER TABLE kill_chains
            ADD COLUMN IF NOT EXISTS campaign_id UUID;
        CREATE INDEX IF NOT EXISTS idx_kc_campaign
            ON kill_chains (campaign_id);
        """
        try:
            with psycopg2.connect(**self.pg_kwargs) as conn:
                with conn.cursor() as cur:
                    cur.execute(ddl)
            logger.info("campaigns schema ready")
        except Exception as exc:
            logger.error("campaigns schema ensure failed: %s", exc)

    # ------------------------------------------------------------------
    # (De)serialization for Redis cache
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(c: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(c)
        for k in ("first_event_at", "last_event_at", "created_at",
                  "updated_at", "closed_at"):
            v = out.get(k)
            if isinstance(v, datetime):
                out[k] = v.isoformat()
        return out

    @staticmethod
    def _deserialize(c: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(c)
        for k in ("first_event_at", "last_event_at", "created_at",
                  "updated_at", "closed_at"):
            v = out.get(k)
            if isinstance(v, str):
                out[k] = _parse_iso(v) or _utcnow()
        kcs = out.get("kill_chain_steps")
        if isinstance(kcs, str):
            try:
                out["kill_chain_steps"] = json.loads(kcs)
            except Exception:
                out["kill_chain_steps"] = []
        # psycopg2 returns Postgres arrays as lists already; normalize None
        for k in ("incident_ids", "service_path", "mitre_techniques",
                  "layers_involved", "stages_seen", "target_usernames"):
            if out.get(k) is None:
                out[k] = []
        # incident_ids stored as UUID[] — coerce to str
        out["incident_ids"] = [str(x) for x in out.get("incident_ids", [])]
        return out
