"""
Rating calculation. Called on-demand (cached 5 min) and persisted at 22:00.
"""

import logging
from datetime import date, datetime
import pytz
from db import get_conn, DB_REALTIME

logger = logging.getLogger(__name__)
TZ = pytz.timezone("Asia/Tashkent")

_cache: dict = {}
CACHE_TTL = 300   # 5 minutes


def _grade(pct: float) -> str:
    if pct >= 90: return "A"
    if pct >= 75: return "B"
    if pct >= 60: return "C"
    if pct >= 40: return "D"
    return "E"


def calculate_rating(stat_date: date = None) -> dict:
    if stat_date is None:
        stat_date = datetime.now(TZ).date()

    key    = str(stat_date)
    cached = _cache.get(key)
    if cached:
        age = (datetime.now(TZ) - cached["_ts"]).total_seconds()
        if age < CACHE_TTL:
            return {k: v for k, v in cached.items() if k != "_ts"}

    conn = get_conn(DB_REALTIME)
    cur  = conn.cursor()

    cur.execute("""
        SELECT
            COUNT(*)                                    AS total_tasks,
            SUM(CASE WHEN on_time=1 THEN 1 ELSE 0 END) AS completed_on_time,
            SUM(CASE WHEN on_time=0 THEN 1 ELSE 0 END) AS completed_late,
            COALESCE(SUM(score),0)                      AS total_score
        FROM task_completions
        WHERE stat_date=%s
    """, (stat_date,))
    tc = cur.fetchone()

    cur.execute("SELECT COUNT(*) AS cnt FROM missed_calls_rt")
    open_tasks = cur.fetchone()["cnt"]

    cur.close(); conn.close()

    total     = tc["total_tasks"]  or 0
    on_time   = tc["completed_on_time"] or 0
    late      = tc["completed_late"]    or 0
    score     = tc["total_score"]       or 0
    max_score = total * 3
    pct       = round(score / max_score * 100, 1) if max_score else 0

    result = {
        "stat_date":         str(stat_date),
        "total_tasks":       total,
        "completed_on_time": on_time,
        "completed_late":    late,
        "not_completed":     open_tasks,
        "total_score":       score,
        "max_score":         max_score,
        "pct":               pct,
        "grade":             _grade(pct),
        "open_tasks":        open_tasks,
    }
    _cache[key] = {**result, "_ts": datetime.now(TZ)}
    return result


def persist_daily_ratings(stat_date: date = None):
    if stat_date is None:
        stat_date = datetime.now(TZ).date()

    r = calculate_rating(stat_date)
    conn = get_conn(DB_REALTIME)
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO daily_ratings
            (stat_date, manager_name, total_tasks, completed_on_time, completed_late,
             not_completed, total_score, max_score, pct, grade, calculated_at)
        VALUES (%s,'all',%s,%s,%s,%s,%s,%s,%s,%s,NOW())
        ON DUPLICATE KEY UPDATE
            total_tasks=VALUES(total_tasks),
            completed_on_time=VALUES(completed_on_time),
            completed_late=VALUES(completed_late),
            not_completed=VALUES(not_completed),
            total_score=VALUES(total_score),
            max_score=VALUES(max_score),
            pct=VALUES(pct),
            grade=VALUES(grade),
            calculated_at=NOW()
    """, (stat_date, r["total_tasks"], r["completed_on_time"], r["completed_late"],
          r["not_completed"], r["total_score"], r["max_score"], r["pct"], r["grade"]))
    conn.commit(); cur.close(); conn.close()
    logger.info("Persisted daily_ratings for %s: grade=%s pct=%.1f", stat_date, r["grade"], r["pct"])
