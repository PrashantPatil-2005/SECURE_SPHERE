"""Redis Stream → Elasticsearch bulk indexer."""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request

import redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SearchIndexer")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
STREAM = os.getenv("EVENT_STREAM", "securisphere:events")
GROUP = "search-indexer"
CONSUMER = os.getenv("INDEXER_CONSUMER", "indexer-1")
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://elasticsearch:9200")
INDEX_PREFIX = "securisphere-events"


def ensure_group(r: redis.Redis) -> None:
    try:
        r.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
        logger.info("Created consumer group %s", GROUP)
    except redis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def ensure_index() -> None:
    index = f"{INDEX_PREFIX}-000001"
    mapping = {
        "mappings": {
            "properties": {
                "event_id": {"type": "keyword"},
                "timestamp": {"type": "date"},
                "source_service_name": {"type": "keyword"},
                "destination_service_name": {"type": "keyword"},
                "correlation_key": {"type": "keyword"},
                "event_type": {"type": "keyword"},
                "severity_level": {"type": "keyword"},
                "description": {"type": "text"},
            }
        }
    }
    req = urllib.request.Request(
        f"{ES_URL}/{index}",
        data=json.dumps(mapping).encode(),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        logger.info("Index %s ready", index)
    except Exception as exc:
        logger.warning("Index setup: %s", exc)


def bulk_index(docs: list) -> None:
    if not docs:
        return
    index = f"{INDEX_PREFIX}-000001"
    lines = []
    for doc in docs:
        lines.append(json.dumps({"index": {"_index": index}}))
        lines.append(json.dumps(doc))
    body = "\n".join(lines) + "\n"
    req = urllib.request.Request(
        f"{ES_URL}/_bulk",
        data=body.encode(),
        headers={"Content-Type": "application/x-ndjson"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=15)


def run() -> None:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    while True:
        try:
            r.ping()
            break
        except redis.ConnectionError:
            time.sleep(2)

    ensure_group(r)
    ensure_index()
    logger.info("Indexer running on %s", STREAM)

    while True:
        try:
            msgs = r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=50, block=5000)
            batch = []
            ack_ids = []
            for _stream, entries in msgs or []:
                for msg_id, fields in entries:
                    payload = fields.get("payload") or fields.get("data")
                    if not payload:
                        ack_ids.append(msg_id)
                        continue
                    try:
                        ev = json.loads(payload)
                    except json.JSONDecodeError:
                        ack_ids.append(msg_id)
                        continue
                    batch.append({
                        "event_id": ev.get("event_id"),
                        "timestamp": ev.get("timestamp"),
                        "source_service_name": ev.get("source_service_name"),
                        "destination_service_name": ev.get("destination_service_name"),
                        "correlation_key": ev.get("correlation_key"),
                        "event_type": ev.get("event_type"),
                        "severity_level": (ev.get("severity") or {}).get("level"),
                        "description": (ev.get("detection_details") or {}).get("description", ""),
                    })
                    ack_ids.append(msg_id)
            if batch:
                bulk_index(batch)
            if ack_ids:
                r.xack(STREAM, GROUP, *ack_ids)
        except Exception as exc:
            logger.warning("Indexer loop error: %s", exc)
            time.sleep(2)


if __name__ == "__main__":
    run()
