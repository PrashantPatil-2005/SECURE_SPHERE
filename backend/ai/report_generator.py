import os
import json
from datetime import datetime
from ai.client import generate_completion
from ai.prompts import POST_INCIDENT_REPORT_PROMPT

def generate_incident_report(incident: dict) -> tuple[bool, str, str]:
    """
    Generates a Markdown report for a given incident using AI.
    Returns (success_bool, filename, report_content)
    """
    prompt = POST_INCIDENT_REPORT_PROMPT.format(incident=json.dumps(incident, indent=2))
    report_markdown = generate_completion(prompt, max_tokens=1500)
    
    if not report_markdown:
        return False, "", "Failed to generate report"
        
    # Save report to disk
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    incident_id = incident.get("incident_id", "unknown")
    filename = f"incident_{incident_id}_{ts}.md"
    filepath = os.path.join(reports_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(report_markdown)

    return True, filename, report_markdown

def get_reports_for_incident(incident_id: str) -> list[dict]:
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    if not os.path.exists(reports_dir):
        return []
        
    reports = []
    for f in os.listdir(reports_dir):
        if incident_id in f and f.endswith('.md'):
            with open(os.path.join(reports_dir, f), 'r', encoding='utf-8') as file:
                reports.append({
                    "filename": f,
                    "content": file.read()
                })
    return reports
