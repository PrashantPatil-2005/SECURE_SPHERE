# Elasticsearch Index Design

## Index pattern

`securisphere-events-{YYYY.MM}` (monthly rollover).

## Mapping

```json
{
  "mappings": {
    "properties": {
      "event_id": { "type": "keyword" },
      "timestamp": { "type": "date" },
      "source_service_name": { "type": "keyword" },
      "destination_service_name": { "type": "keyword" },
      "correlation_key": { "type": "keyword" },
      "source_layer": { "type": "keyword" },
      "event_type": { "type": "keyword" },
      "severity_level": { "type": "keyword" },
      "mitre_technique": { "type": "keyword" },
      "source_ip": { "type": "ip" },
      "description": { "type": "text" }
    }
  }
}
```

## Indexer

`backend/search/indexer.py` consumes `securisphere:events` via consumer group `search-indexer`, bulk-indexes with 5s flush interval.

## Query API

`GET /api/search/events?q=sql&service=api-server&from=...&to=...`

Proxied from Flask to FastAPI BFF when `BFF_URL` set.

## Dev profile

Elasticsearch runs under compose profile `search` to avoid RAM on laptops. CI skips ES unless `CI_ENABLE_ES=1`.
