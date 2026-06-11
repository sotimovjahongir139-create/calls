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
        if type == "monthly":
            cur.execute("""
                SELECT
                    COALESCE(SUM(total_events),0)     AS total_events,
                    COALESCE(SUM(client_messages),0)  AS client_messages,
                    COALESCE(SUM(manager_messages),0) AS manager_messages,
                    COALESCE(SUM(client_turns),0)     AS client_turns,
                    COALESCE(SUM(answered_turns),0)   AS answered_turns,
                    COALESCE(SUM(waiting_turns),0)    AS waiting_turns,
                    COALESCE(ROUND(AVG(response_rate),2),0)           AS response_rate,
                    COALESCE(ROUND(AVG(avg_response_minutes),2),0)    AS avg_response_minutes
                FROM telegram_daily_stats
                WHERE report_date >= DATE_FORMAT(NOW(), '%%Y-%%m-01')
            """)
        else:
            cur.execute("SELECT * FROM telegram_daily_stats ORDER BY report_date DESC LIMIT 1")
        row = cur.fetchone()
        cur.close(); conn.close()
        return dict(row) if row else {}
    except Exception as e:
        logger.error("telegram stats: %s", e)
        return {"error": str(e), "total_events": 0}


# ── /api/debug/telegram ──────────────────────────────────────────────────────

@app.get("/api/debug/telegram")
def debug_telegram():
    try:
        conn = get_conn(DB_TELEGRAM)
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) AS cnt FROM telegram_daily_stats")
        count = cur.fetchone()
        cur.execute("""
            SELECT report_date, report_name, total_events,
                   client_messages, manager_messages, response_rate
            FROM telegram_daily_stats
            ORDER BY report_date DESC LIMIT 5
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return {"total_rows": count["cnt"], "latest": rows}
    except Exception as e:
        return {"error": str(e)}


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
