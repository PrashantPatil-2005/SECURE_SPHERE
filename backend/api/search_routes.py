"""
SecuriSphere — Full-text search route
=====================================
Lightweight Redis-backed substring search across recent events. Token-protected.
"""

import json

from flask import Blueprint, request, jsonify

from auth import token_required
from services import get_all_events, get_events_from_redis

bp = Blueprint("search_routes", __name__)


@bp.route('/api/search')
@token_required
def search_events():
    """
    Lightweight substring search across the last 1 000 events.

    Query params
    ------------
    q        : required — search term (case-insensitive)
    layer    : optional filter by source_layer
    limit    : max results to return (default 50, max 200)

    This is a Redis-based fallback; replace with Elasticsearch for
    production-scale full-text search.
    """
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({"status": "error", "message": "Query parameter 'q' is required"}), 400

    layer = request.args.get('layer', 'all')
    limit = min(int(request.args.get('limit', 50)), 200)

    # Gather events to search across
    if layer == 'all':
        pool = get_all_events(1000)
    else:
        pool = get_events_from_redis(f'events:{layer}', 0, 1000)

    # Case-insensitive substring match against the JSON serialisation
    # (cheap but effective for up to ~1 000 events)
    matches = []
    for event in pool:
        haystack = json.dumps(event).lower()
        if q in haystack:
            matches.append(event)
        if len(matches) >= limit:
            break

    return jsonify({
        "status": "success",
        "data": {
            "query":   q,
            "results": matches,
            "count":   len(matches),
            "searched_events": len(pool),
            "note": "Redis substring search — deploy Elasticsearch for production full-text search",
        }
    })
