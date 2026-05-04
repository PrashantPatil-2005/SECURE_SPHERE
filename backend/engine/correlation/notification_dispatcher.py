"""
notification_dispatcher.py — Campaign-scoped Discord notifier.

Replaces per-incident Discord alerts with one message per campaign that is
PATCHed in place as the campaign grows.

Behaviour by change_kind
------------------------
"created"   — POST a new webhook message; persist message_id on campaign.
"escalated" — PATCH the existing message (severity rose or new stage).
"extended"  — PATCH the existing message at most once per
              CAMPAIGN_PATCH_INTERVAL seconds (silent update, no @mention).
              Only fires for high/critical campaigns to avoid Discord spam.
"duplicate" — no-op.

Webhook semantics used
----------------------
- POST  {webhook}?wait=true              — returns message JSON (with id)
- PATCH {webhook}/messages/{message_id}  — edits the message
- 404 on PATCH means the message was deleted; we re-POST a fresh one.
"""

import logging
import os
import threading
import time
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("NotificationDispatcher")

CAMPAIGN_PATCH_INTERVAL = int(os.getenv("CAMPAIGN_PATCH_INTERVAL", 30))
DISCORD_MAX_RETRIES     = 3
DISCORD_TIMEOUT         = 5

_DISCORD_COLORS = {
    "critical": 0xFF0000,
    "high":     0xFF6600,
    "medium":   0xFFAA00,
    "low":      0x00AA00,
}

_PREFIX = {
    "created":   "🚨 CAMPAIGN DETECTED",
    "escalated": "⬆️ CAMPAIGN ESCALATED",
    "extended":  "📈 CAMPAIGN UPDATED",
}


class NotificationDispatcher:
    def __init__(self, redis_client, aggregator):
        self.redis = redis_client
        self.aggregator = aggregator
        self._patch_last: Dict[str, float] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public entry
    # ------------------------------------------------------------------

    def dispatch(self, campaign: Dict[str, Any], change_kind: str) -> None:
        if not campaign or change_kind == "duplicate":
            return

        webhook_url = self._webhook_url()
        if not webhook_url:
            return

        sev = (campaign.get("severity") or "low").lower()

        # Suppress noisy "extended" updates for low/medium campaigns
        if change_kind == "extended" and sev not in ("high", "critical"):
            return

        # Throttle "extended" PATCHes per-campaign
        if change_kind == "extended":
            with self._lock:
                last = self._patch_last.get(campaign["campaign_id"], 0)
                if time.time() - last < CAMPAIGN_PATCH_INTERVAL:
                    return
                self._patch_last[campaign["campaign_id"]] = time.time()

        if change_kind == "created" or not campaign.get("discord_message_id"):
            self._post_new(webhook_url, campaign)
        else:
            self._patch_existing(webhook_url, campaign, change_kind)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _webhook_url(self) -> Optional[str]:
        try:
            return self.redis.get("config:discord_webhook")
        except Exception:
            return None

    def _payload(self, c: Dict[str, Any], change_kind: str) -> Dict[str, Any]:
        sev    = (c.get("severity") or "low").lower()
        color  = _DISCORD_COLORS.get(sev, _DISCORD_COLORS["high"])
        path   = " → ".join(c.get("service_path") or []) or "N/A"
        techs  = ", ".join(c.get("mitre_techniques") or []) or "N/A"
        stages = " → ".join(c.get("stages_seen") or []) or "N/A"
        prefix = _PREFIX.get(change_kind, "📣 CAMPAIGN")

        first_seen = self._fmt_ts(c.get("first_event_at"))
        last_seen  = self._fmt_ts(c.get("last_event_at"))

        return {
            "embeds": [{
                "title": f"{prefix} — {c.get('actor_id', 'unknown')}",
                "description":
                    f"**{c.get('incident_count', 0)} correlated incidents** "
                    f"from `{c.get('source_ip') or c.get('actor_id')}`\n"
                    f"Severity: **{sev.upper()}** • Confidence: "
                    f"{float(c.get('max_confidence') or 0):.2f}",
                "color":  color,
                "fields": [
                    {"name": "Kill Chain Stages", "value": stages,                                       "inline": False},
                    {"name": "Service Path",      "value": path,                                         "inline": False},
                    {"name": "MITRE Techniques",  "value": techs[:1024],                                 "inline": False},
                    {"name": "First Seen",        "value": first_seen,                                   "inline": True},
                    {"name": "Last Seen",         "value": last_seen,                                    "inline": True},
                    {"name": "Incidents",         "value": str(c.get("incident_count", 0)),             "inline": True},
                ],
                "footer": {"text": f"campaign_id: {c.get('campaign_id')}"},
            }]
        }

    @staticmethod
    def _fmt_ts(v) -> str:
        if v is None:
            return "?"
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return str(v)

    def _post_new(self, url: str, c: Dict[str, Any]) -> None:
        post_url = url + ("&" if "?" in url else "?") + "wait=true"
        delay = 1
        for attempt in range(1, DISCORD_MAX_RETRIES + 1):
            try:
                r = requests.post(
                    post_url,
                    json=self._payload(c, "created"),
                    timeout=DISCORD_TIMEOUT,
                )
                if r.status_code in (200, 204):
                    msg_id = chan_id = None
                    if r.text:
                        try:
                            body = r.json()
                            msg_id  = body.get("id")
                            chan_id = body.get("channel_id")
                        except ValueError:
                            pass
                    if msg_id:
                        self.aggregator.attach_discord_message(
                            c["campaign_id"], msg_id, chan_id,
                        )
                    logger.info("campaign %s alert posted (msg=%s)",
                                c.get("campaign_id"), msg_id)
                    return
                if r.status_code == 429:
                    retry_after = self._retry_after(r, default=delay)
                    time.sleep(retry_after)
                    continue
                logger.warning("Discord POST %d (try %d/%d): %s",
                               r.status_code, attempt, DISCORD_MAX_RETRIES,
                               r.text[:200])
            except requests.RequestException as exc:
                logger.warning("Discord POST error (try %d): %s", attempt, exc)

            if attempt < DISCORD_MAX_RETRIES:
                time.sleep(delay)
                delay *= 2

    def _patch_existing(self, url: str, c: Dict[str, Any], change_kind: str) -> None:
        msg_id = c.get("discord_message_id")
        if not msg_id:
            self._post_new(url, c)
            return

        patch_url = f"{url}/messages/{msg_id}"
        delay = 1
        for attempt in range(1, DISCORD_MAX_RETRIES + 1):
            try:
                r = requests.patch(
                    patch_url,
                    json=self._payload(c, change_kind),
                    timeout=DISCORD_TIMEOUT,
                )
                if r.status_code in (200, 204):
                    logger.info("campaign %s alert patched (kind=%s)",
                                c.get("campaign_id"), change_kind)
                    return
                if r.status_code == 404:
                    logger.info(
                        "Discord message %s not found — reposting", msg_id,
                    )
                    self.aggregator.attach_discord_message(
                        c["campaign_id"], None, None,
                    )
                    self._post_new(url, c)
                    return
                if r.status_code == 429:
                    retry_after = self._retry_after(r, default=delay)
                    time.sleep(retry_after)
                    continue
                logger.warning("Discord PATCH %d (try %d/%d): %s",
                               r.status_code, attempt, DISCORD_MAX_RETRIES,
                               r.text[:200])
            except requests.RequestException as exc:
                logger.warning("Discord PATCH error (try %d): %s", attempt, exc)

            if attempt < DISCORD_MAX_RETRIES:
                time.sleep(delay)
                delay *= 2

    @staticmethod
    def _retry_after(resp, default: float) -> float:
        try:
            ra = resp.headers.get("Retry-After")
            if ra:
                return float(ra)
            body = resp.json()
            if isinstance(body, dict) and body.get("retry_after"):
                return float(body["retry_after"])
        except Exception:
            pass
        return default
