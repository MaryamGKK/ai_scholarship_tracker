import os, smtplib, logging, json
from email.message import EmailMessage
from typing import List, Dict

logger = logging.getLogger("scholarship-tracker.notifier")

SMTP_USER = os.getenv("GMAIL_SMTP_USER")
SMTP_PASS = os.getenv("GMAIL_SMTP_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")

def send_email(subject: str, html_body: str, to_addr: str=None):
    to_addr = to_addr or EMAIL_TO
    if not (SMTP_USER and SMTP_PASS and to_addr):
        raise ValueError("SMTP credentials and recipient required")
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content("Please view this email in HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    logger.info("Sent email to %s", to_addr)

def format_email_items(items: List[Dict]):
    rows = []
    for it in items:
        rows.append(f"<li><b>{it.get('title') or 'Unknown'}</b> — Deadline: {it.get('deadline') or 'N/A'}<br/>Source: <a href='{it.get('source')}'>{it.get('source')}</a><br/>Eligibility: {it.get('eligibility') or 'N/A'}</li>")
    body = f"<html><body><h2>Scholarships found ({len(items)})</h2><ul>{''.join(rows)}</ul></body></html>"
    return body
