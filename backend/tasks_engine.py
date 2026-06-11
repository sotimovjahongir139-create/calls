"""
Task deadline calculation and task completion logic.
"""

import os, logging
from datetime import datetime
import pytz
from dotenv import load_dotenv
from db import get_conn, DB_REALTIME

load_dotenv()
logger = logging.getLogger(__name__)

TZ                  = pytz.timezone("Asia/Tashkent")
MINUTES_PER_CLIENT  = float(os.getenv("TASK_MINUTES_PER_CLIENT", 20))


def get_tasks() -> dict:
    conn = get_conn(DB_REALTIME)
    cur  = conn.cursor()
    cur.execute("""
        SELECT contact_id, phone, manager_name, missed_at, waiting_minutes, sla_status
        FROM missed_calls_rt
        ORDER BY missed_at ASC
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()

    n              = len(rows)
    total_deadline = n * MINUTES_PER_CLIENT

    tasks = [
        {
            "contact_id":       row["contact_id"],
            "phone":            row["phone"] or "",
            "manager_name":     row["manager_name"] or "",
            "waiting_minutes":  round(row["waiting_minutes"] or 0, 1),
            "deadline_minutes": total_deadline,
            "sla_status":       row["sla_status"] or "ok",
        }
        for row in rows
    ]
    return {"tasks": tasks, "total_deadline_minutes": total_deadline}


def complete_task(contact_id: int) -> dict:
    now       = datetime.now(TZ)
    now_naive = now.replace(tzinfo=None)
    today     = now.date()

    conn = get_conn(DB_REALTIME)
    cur  = conn.cursor()

    try:
        cur.execute("SELECT * FROM missed_calls_rt WHERE contact_id=%s", (contact_id,))
        row = cur.fetchone()
        if not row:
            return {"success": False, "error": "task_not_found"}

        # deadline = current queue size × MINUTES_PER_CLIENT
        cur.execute("SELECT COUNT(*) AS cnt FROM missed_calls_rt")
        n                = cur.fetchone()["cnt"]
        deadline_minutes = n * MINUTES_PER_CLIENT

        missed_at        = row["missed_at"]          # naive datetime from MySQL
        response_minutes = (now_naive - missed_at).total_seconds() / 60
        on_time          = response_minutes <= deadline_minutes
        score            = 3 if on_time else 1

        cur.execute("""
            INSERT INTO task_completions
                (contact_id, manager_name, missed_at, completed_at,
                 response_minutes, deadline_minutes, on_time, score, stat_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            contact_id, row["manager_name"], missed_at, now_naive,
            round(response_minutes, 2), deadline_minutes,
            int(on_time), score, today,
        ))
        cur.execute("DELETE FROM missed_calls_rt WHERE contact_id=%s", (contact_id,))
        conn.commit()

        return {"success": True, "score": score, "on_time": on_time,
                "response_minutes": round(response_minutes, 1)}

    except Exception as e:
        conn.rollback()
        logger.error("complete_task error: %s", e)
        raise
    finally:
        cur.close(); conn.close()
