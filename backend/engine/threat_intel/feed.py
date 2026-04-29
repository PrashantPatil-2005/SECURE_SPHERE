"""Threat-intel feed ingestion.

Loads IP/hash indicators from one or more feed URLs into Redis sets, then
exposes ``lookup(ip)`` for the correlation engine to enrich events.

Why we host this in Redis instead of calling out per-event
---------------------------------------------------------
Per-event API calls add latency to the hot path and burn rate-limit budget
fast under attack. Pull the feeds once per ``THREAT_INTEL_REFRESH_SECONDS``
into Redis sets — lookup is then O(1) and survives restarts.

Default feeds (operator-overridable via ``THREAT_INTEL_FEEDS``):
- abuse.ch FeodoTracker IP blocklist (CSV-ish, IPs on column 1)

NB: outbound network is OFF by default in the demo lab. Operators wire
their own feeds via env: ``THREAT_INTEL_FEEDS="<url>,<url>,<url>"``. The
default config falls back to a tiny static list shipped under
``threat_intel/static_indicators.txt`` so the feature has *something* to
match against during demos.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Iterable, List, Optional

logger = logging.getLogger("ThreatIntel")

INDICATOR_SET_KEY = "threat_intel:ips"
META_KEY = "threat_intel:meta"
DEFAULT_REFRESH_SECONDS = 6 * 3600

DEFAULT_STATIC_INDICATORS_PATH = os.path.join(
    os.path.dirname(__file__), "static_indicators.txt"
)


class ThreatIntel:
    def __init__(self, redis_client) -> None:
        self.redis = redis_client
        self.refresh_interval = int(os.getenv("THREAT_INTEL_REFRESH_SECONDS", str(DEFAULT_REFRESH_SECONDS)))
        self.feeds = [u.strip() for u in os.getenv("THREAT_INTEL_FEEDS", "").split(",") if u.strip()]
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Lookup (hot path)
    # ------------------------------------------------------------------
    def lookup(self, ip: Optional[str]) -> bool:
        if not ip:
            return False
        try:
            return bool(self.redis.sismember(INDICATOR_SET_KEY, ip))
        except Exception:
            return False

    def stats(self) -> dict:
        try:
            count = self.redis.scard(INDICATOR_SET_KEY) or 0
            meta = self.redis.hgetall(META_KEY) or {}
        except Exception:
            count, meta = 0, {}
        return {"indicator_count": int(count), "meta": meta, "feeds": self.feeds}

    # ------------------------------------------------------------------
    # Refresh loop
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="threat-intel-refresh")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        # Initial seed from static file so demos work offline
        self._seed_static()
        if self.feeds:
            self.refresh_now()
        while not self._stop.wait(self.refresh_interval):
            try:
                if self.feeds:
                    self.refresh_now()
            except Exception as exc:
                logger.debug("ti refresh failed: %s", exc)

    def _seed_static(self) -> None:
        ips = self._read_static()
        if not ips:
            return
        self._bulk_load(ips, source="static")

    def _read_static(self) -> List[str]:
        path = os.getenv("THREAT_INTEL_STATIC_FILE", DEFAULT_STATIC_INDICATORS_PATH)
        try:
            with open(path, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except FileNotFoundError:
            return []
        except Exception as exc:
            logger.debug("static indicators read failed: %s", exc)
            return []

    def refresh_now(self) -> int:
        """Pull every configured feed and replace the indicator set."""
        try:
            import requests  # type: ignore
        except Exception:
            logger.warning("requests not available; skipping feed refresh")
            return 0

        all_ips: List[str] = list(self._read_static())
        for url in self.feeds:
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                for line in resp.text.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Take the first whitespace/comma-separated token as the IP
                    token = line.split()[0].split(",")[0].strip()
                    if token:
                        all_ips.append(token)
            except Exception as exc:
                logger.warning("feed pull failed (%s): %s", url, exc)

        if not all_ips:
            return 0
        return self._bulk_load(all_ips, source=",".join(self.feeds) or "static")

    def _bulk_load(self, ips: Iterable[str], source: str) -> int:
        try:
            pipe = self.redis.pipeline()
            pipe.delete(INDICATOR_SET_KEY)
            chunk: List[str] = []
            n = 0
            for ip in ips:
                chunk.append(ip)
                if len(chunk) >= 1000:
                    pipe.sadd(INDICATOR_SET_KEY, *chunk)
                    n += len(chunk)
                    chunk = []
            if chunk:
                pipe.sadd(INDICATOR_SET_KEY, *chunk)
                n += len(chunk)
            pipe.hset(META_KEY, mapping={
                "loaded_at": str(int(time.time())),
                "source":    source,
                "count":     str(n),
            })
            pipe.execute()
            logger.info("Threat intel: loaded %d indicators from %s", n, source)
            return n
        except Exception as exc:
            logger.warning("bulk load failed: %s", exc)
            return 0
