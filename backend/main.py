"""
FastAPI backend.
Run: uvicorn main:app --host 0.0.0.0 --port 8000
"""

import logging
from datetime import date, datetime

import pytz
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from db import get_conn, DB_CALLS, DB_TELEGRAM, DB_REALTIME, ensure_schema
from tasks_engine import get_tasks, complete_task
from rating_engine import calculate_rating

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Tashkent")

app = FastAPI(title="CRM Real-time Dashboard", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    ensure_schema()


@app.get("/health")
def health():
    return {"status": "ok"}


# ── /api/signals ──────────────────────────────────────────────────────────────

@app.get("/api/signals")
def api_signals():
    today = datetime.now(TZ).date()
    conn  = get_conn(DB_REALTIME)
    cur   = conn.cursor()

    cur.execute("""
        SELECT phone, waiting_minutes, sla_status
        FROM missed_calls_rt
        WHERE sla_status IN ('warning','breach')
        ORDER BY waiting_minutes DESC
    """)
    sla_breach = cur.fetchall()

    cur.execute("""
        SELECT
            COUNT(*)                                    AS total_closed,
            SUM(CASE WHEN on_time=0 THEN 1 ELSE 0 END) AS late_count,
            COALESCE(SUM(score),0)                      AS total_score,
            COUNT(*)*3                                  AS max_score
        FROM task_completions WHERE stat_date=%s
    """, (today,))
    tc = cur.fetchone()

    cur.execute("SELECT COUNT(*) AS cnt FROM missed_calls_rt")
    open_tasks = cur.fetchone()["cnt"]

    cur.close(); conn.close()

    score     = tc["total_score"] or 0
    max_score = tc["max_score"]   or 0
    pct       = round(score / max_score * 100, 1) if max_score else 0

    return {
        "sla_breach": [
            {"phone": r["phone"],
             "waiting_minutes": round(r["waiting_minutes"] or 0, 1),
             "sla_status": r["sla_status"]}
            for r in sla_breach
        ],
        "rating_warning": {
            "completed_pct": pct,
            "late_count":    tc["late_count"] or 0,
        },
        "info": {
            "recalled_today":    tc["total_closed"] or 0,
            "tasks_closed_today": tc["total_closed"] or 0,
            "open_tasks":        open_tasks,
        },
    }


# ── /api/tasks ────────────────────────────────────────────────────────────────

@app.get("/api/tasks")
def api_tasks():
    return get_tasks()


@app.post("/api/tasks/{contact_id}/complete")
def api_complete(contact_id: int):
    result = complete_task(contact_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "not_found"))
    return result


# ── /api/ratings ──────────────────────────────────────────────────────────────

@app.get("/api/ratings")
def api_ratings(date_str: str = Query(None, alias="date")):
    if date_str:
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Use YYYY-MM-DD")
    else:
        d = None
    return calculate_rating(d)


# ── /api/stats ────────────────────────────────────────────────────────────────

@app.get("/api/stats/calls")
def api_stats_calls(type: str = Query("daily", regex="^(daily|monthly)$")):
    table    = "amo_call_daily_stats"   if type == "daily" else "amo_call_monthly_stats"
    date_col = "stat_date"              if type == "daily" else "stat_month"
    try:
        conn = get_conn(DB_CALLS)
        cur  = conn.cursor()
        cur.execute(f"SELECT * FROM `{table}` ORDER BY {date_col} DESC LIMIT 100")
        rows = cur.fetchall()
        cur.close(); conn.close()
    except Exception as e:
        logger.error("calls stats: %s", e)
        raise HTTPException(status_code=500, detail="DB error")
    return {"type": type, "rows": rows}


@app.get("/api/stats/telegram")
def api_stats_telegram(type: str = Query("daily", regex="^(daily|monthly)$")):
    try:
        conn = get_conn(DB_TELEGRAM)
        cur  = conn.cursor()
        if type == "daily":
            cur.execute("SELECT * FROM telegram_daily_stats ORDER BY report_date DESC LIMIT 100")
        else:
            cur.execute("""
                SELECT
                    DATE_FORMAT(report_date, '%%Y-%%m-01') AS report_month,
                    report_name,
                    SUM(unique_contacts)  AS unique_contacts,
                    SUM(unique_talks)     AS unique_talks,
                    SUM(unique_leads)     AS unique_leads,
                    SUM(total_events)     AS total_events,
                    SUM(client_messages)  AS client_messages,
                    SUM(manager_messages) AS manager_messages,
                    SUM(client_turns)     AS client_turns,
                    SUM(answered_turns)   AS answered_turns,
                    SUM(waiting_turns)    AS waiting_turns,
                    ROUND(SUM(answered_turns)/NULLIF(SUM(client_turns),0)*100, 2) AS response_rate,
                    ROUND(AVG(avg_response_minutes), 2)    AS avg_response_minutes,
                    ROUND(AVG(median_response_minutes), 2) AS median_response_minutes
                FROM telegram_daily_stats
                GROUP BY report_month, report_name
                ORDER BY report_month DESC
            """)
        rows = cur.fetchall()
        cur.close(); conn.close()
    except Exception as e:
        logger.error("telegram stats: %s", e)
        raise HTTPException(status_code=500, detail="DB error")
    return {"type": type, "rows": rows}


# ── /api/admin/clear-tables ──────────────────────────────────────────────────

@app.post("/api/admin/clear-tables")
def api_clear_tables():
    cleared = []
    try:
        conn = get_conn(DB_REALTIME)
        cur  = conn.cursor()
        for t in ("missed_calls_rt", "task_completions", "daily_ratings"):
            cur.execute(f"TRUNCATE TABLE {t}")
            cleared.append(f"{DB_REALTIME}.{t}")
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        logger.error("clear realtime: %s", e)

    try:
        conn = get_conn(DB_CALLS)
        cur  = conn.cursor()
        for t in ("amo_call_daily_stats", "amo_call_monthly_stats"):
            cur.execute(f"TRUNCATE TABLE {t}")
            cleared.append(f"{DB_CALLS}.{t}")
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        logger.error("clear calls: %s", e)

    try:
        conn = get_conn(DB_TELEGRAM)
        cur  = conn.cursor()
        for t in ("telegram_daily_stats", "telegram_response_details"):
            cur.execute(f"TRUNCATE TABLE {t}")
            cleared.append(f"{DB_TELEGRAM}.{t}")
        conn.commit(); cur.close(); conn.close()
    except Exception as e:
        logger.error("clear telegram: %s", e)

    return {"status": "cleared", "tables": cleared}


# ── /api/admin/run-etl ────────────────────────────────────────────────────────

@app.post("/api/admin/run-etl")
def api_run_etl(script: str = Query(..., regex="^(calls|telegram|all)$")):
    import threading, traceback
    results = {}

    def run_calls():
        try:
            import sys as _sys
            _sys.modules.pop("amocrm_calls", None)
            from amocrm_calls import main as calls_main
            calls_main()
            results["calls"] = "ok"
        except BaseException as e:
            results["calls"] = traceback.format_exc()

    def run_telegram():
        try:
            import sys as _sys
            _sys.modules.pop("amocrm_telegram", None)
            from amocrm_telegram import main as tg_main
            tg_main()
            results["telegram"] = "ok"
        except BaseException as e:
            results["telegram"] = traceback.format_exc()

    threads = []
    if script in ("calls", "all"):
        t = threading.Thread(target=run_calls)
        t.start(); threads.append(t)
    if script in ("telegram", "all"):
        t = threading.Thread(target=run_telegram)
        t.start(); threads.append(t)
    for t in threads:
        t.join(timeout=300)

    return {"status": "done", "results": results}
