"""SMTP email alerts for campaign-level notifications."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict

logger = logging.getLogger("EmailAlerts")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "securisphere@localhost")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")


def send_campaign_email(campaign: Dict[str, Any], change_kind: str) -> bool:
    if not SMTP_HOST or not ALERT_EMAIL_TO:
        return False

    sev = (campaign.get("severity") or "low").upper()
    path = " → ".join(campaign.get("service_path") or []) or "N/A"
    subject = f"[SecuriSphere] {change_kind.upper()} — {sev} campaign {campaign.get('campaign_id', '')[:8]}"

    body = f"""SecuriSphere Campaign Alert ({change_kind})

Severity: {sev}
Actor: {campaign.get('actor_id')} ({campaign.get('actor_type', 'unknown')})
Service path: {path}
Incidents: {campaign.get('incident_count', 0)}
MITRE: {', '.join(campaign.get('mitre_techniques') or [])}
Confidence: {campaign.get('max_confidence', 0):.0%}
"""

    msg = MIMEMultipart()
    msg["From"] = ALERT_EMAIL_FROM
    msg["To"] = ALERT_EMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body.strip(), "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            if SMTP_USER:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(ALERT_EMAIL_FROM, [ALERT_EMAIL_TO], msg.as_string())
        logger.info("Campaign email sent to %s", ALERT_EMAIL_TO)
        return True
    except Exception as exc:
        logger.warning("Campaign email failed: %s", exc)
        return False
