# Scalability Considerations

## Correlation engine horizontal scaling

- Multiple workers join consumer group `correlation-workers`
- Partition by `hash(correlation_key) % N` to avoid duplicate incident creation
- Campaign partial unique index prevents duplicate active campaigns per actor

## Redis
- Streams with consumer groups for at-least-once delivery
- `maxmemory-policy allkeys-lru` for dev; dedicated cluster in production

## PostgreSQL
- Indexes on `correlation_key`, `actor_id`, `detected_at`
- Connection pooling via psycopg2 per worker (consider PgBouncer at scale)

## Elasticsearch
- Single-node for dev; 3-node cluster for production search
- Monthly index rollover; ILM delete after 90 days

## Frontend
- Static nginx CDN in production
- WebSocket fan-out via Redis pub/sub bridge to multiple Flask workers (sticky sessions or Redis adapter)
