from flask import Blueprint, request, jsonify, Response
import json
import os
from datetime import datetime
from ai.client import generate_completion, stream_completion
from ai.prompts import CHAT_SYSTEM_PROMPT, POST_INCIDENT_REPORT_PROMPT

bp = Blueprint('ai', __name__, url_prefix='/api/ai')

# We'll use the existing redis client from app
# To avoid circular imports, we'll import it inside the route or assume the caller passes context.

@bp.route('/stream', methods=['GET'])
def get_thought_stream():
    # Fetch recent AI commentary from Redis
    try:
        from app import redis_client, redis_available
        if not redis_available:
            return jsonify({"stream": []})
        
        raw_stream = redis_client.lrange("ai_thought_stream_history", 0, 10)
        stream = [json.loads(s) for s in raw_stream]
        return jsonify({"stream": stream})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_msg = data.get('message', '')
    if not user_msg:
        return jsonify({"error": "Message is required"}), 400

    from app import get_incidents, get_risk_scores, get_all_events

    # Gather live context
    active_incidents = get_incidents(limit=5)
    risk_scores = get_risk_scores()
    recent_events = get_all_events(limit=10)

    context = {
        "current_time": datetime.utcnow().isoformat(),
        "active_incidents": active_incidents,
        "risk_scores": risk_scores,
        "recent_events": recent_events,
    }
    
    system_prompt = CHAT_SYSTEM_PROMPT.format(context=json.dumps(context, indent=2))
    
    # Optional: support streaming if requested
    if data.get('stream', False):
        def generate():
            for chunk in stream_completion(user_msg, system_prompt):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        return Response(generate(), mimetype='text/event-stream')
    else:
        response_text = generate_completion(user_msg, system_prompt)
        return jsonify({"response": response_text})


@bp.route('/report/<incident_id>', methods=['POST'])
def generate_report(incident_id):
    from app import get_incidents
    # Fetch incident
    incidents = get_incidents(limit=100)
    incident = next((i for i in incidents if i.get("incident_id") == incident_id), None)
    
    if not incident:
        # Check postgres directly
        try:
            import psycopg2
            conn = psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "database"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
                user=os.getenv("POSTGRES_USER", "securisphere_user"),
                password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
            )
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM correlated_incidents WHERE incident_id = %s", (incident_id,))
                    row = cur.fetchone()
                    if row:
                        incident = {"incident_id": incident_id, "title": row[2], "description": row[3], "severity": row[4]}
            conn.close()
        except Exception as e:
            pass
            
    if not incident:
        return jsonify({"error": "Incident not found"}), 404

    from ai.report_generator import generate_incident_report
    success, filename, report = generate_incident_report(incident)
    
    if not success:
        return jsonify({"error": report}), 500

    return jsonify({"success": True, "filename": filename, "report": report})


@bp.route('/reports/<incident_id>', methods=['GET'])
def get_reports(incident_id):
    from ai.report_generator import get_reports_for_incident
    reports = get_reports_for_incident(incident_id)
    return jsonify({"reports": reports})


@bp.route('/explain_anomaly', methods=['POST'])
def explain_anomaly():
    data = request.json
    service = data.get("service")
    score = data.get("score")
    top_events = data.get("top_events", [])
    
    if not service:
        return jsonify({"error": "Service is required"}), 400

    prompt = f"""
Analyze the following behavioral anomaly for the service '{service}'.
Risk Score: {score}/200
Top Contributing Events:
{json.dumps(top_events, indent=2)}

Provide a brief (2-3 sentences) AI explanation of why this is considered anomalous and what the potential threat might be.
"""
    explanation = generate_completion(prompt, max_tokens=150)
    if not explanation:
        return jsonify({"error": "Failed to generate explanation"}), 500

    return jsonify({"success": True, "explanation": explanation})
