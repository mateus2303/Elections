from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from typing import Any
from zoneinfo import ZoneInfo

from .db import Database


def _short(record: dict[str, Any]) -> str:
    return " | ".join(str(x) for x in [record.get("protocol"), record.get("company_name"), record.get("electoral_unit_name"), record.get("positions_raw"), record.get("publication_allowed_at"), record.get("publication_status")] if x)


def build_digest(new_records: list[dict[str, Any]], changed_records: list[dict[str, Any]], records: list[dict[str, Any]], run_id: int, window_days: int = 7) -> tuple[str, str, list[str]]:
    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    tomorrow = today.fromordinal(today.toordinal() + 1)
    allowed_today = []
    allowed_tomorrow = []
    next_days = []
    for record in records:
        value = record.get("publication_allowed_at")
        if not value:
            continue
        try:
            day = datetime.fromisoformat(value).date()
        except ValueError:
            continue
        if day == today:
            allowed_today.append(record)
        elif day == tomorrow:
            allowed_tomorrow.append(record)
        elif today < day <= today.fromordinal(today.toordinal() + window_days):
            next_days.append(record)
    subject = f"Monitor TSE — {len(new_records)} pesquisas novas e {len(allowed_tomorrow)} divulgações amanhã"
    lines = [f"Execução {run_id}", "", f"Novos registros: {len(new_records)}"]
    lines.extend(f"- {_short(x)}" for x in new_records[:50])
    lines.append(f"\nRegistros alterados: {len(changed_records)}")
    lines.extend(f"- {_short(x)}" for x in changed_records[:50])
    lines.append(f"\nDivulgação permitida hoje: {len(allowed_today)}")
    lines.extend(f"- {_short(x)}" for x in allowed_today[:50])
    lines.append(f"\nDivulgação permitida amanhã: {len(allowed_tomorrow)}")
    lines.extend(f"- {_short(x)}" for x in allowed_tomorrow[:50])
    lines.append(f"\nPróximos {window_days} dias: {len(next_days)}")
    lines.extend(f"- {_short(x)}" for x in next_days[:50])
    lines.append("\nA data permitida pelo TSE não confirma publicação efetiva.")
    keys = [f"new:{x.get('protocol')}" for x in new_records] + [f"changed:{x.get('protocol')}" for x in changed_records]
    keys.extend(
        f"allowed:{record.get('protocol')}:{record.get('publication_allowed_at', '')[:10]}"
        for record in allowed_today + allowed_tomorrow + next_days
    )
    return subject, "\n".join(lines), keys


def send_pending(db: Database) -> tuple[int, list[str]]:
    host = os.environ.get("MONITOR_TSE_SMTP_HOST")
    port = int(os.environ.get("MONITOR_TSE_SMTP_PORT", "587"))
    username = os.environ.get("MONITOR_TSE_SMTP_USERNAME")
    password = os.environ.get("MONITOR_TSE_SMTP_PASSWORD")
    sender = os.environ.get("MONITOR_TSE_EMAIL_FROM")
    recipients = [x.strip() for x in os.environ.get("MONITOR_TSE_EMAIL_TO", "").split(",") if x.strip()]
    if not all([host, sender, recipients]):
        return 0, ["SMTP não configurado"]
    sent = 0
    errors: list[str] = []
    rows = db.conn.execute("SELECT * FROM alerts WHERE status='pending' ORDER BY alert_id").fetchall()
    if not rows:
        return 0, errors
    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            if port != 25:
                server.starttls()
                server.ehlo()
            if username:
                server.login(username, password or "")
            for row in rows:
                msg = EmailMessage()
                msg["Subject"] = row["subject"]
                msg["From"] = sender
                msg["To"] = ", ".join(recipients)
                msg["Message-ID"] = f"<{row['idempotency_key'].replace(':', '.')}.{row['alert_id']}@monitor-tse.local>"
                msg.set_content(row["body"])
                try:
                    server.send_message(msg)
                    db.mark_alert(row["idempotency_key"], "sent")
                    sent += 1
                except Exception as exc:
                    db.mark_alert(row["idempotency_key"], "delivery_uncertain", str(exc))
                    errors.append(str(exc))
    except Exception as exc:
        errors.append(str(exc))
    return sent, errors
