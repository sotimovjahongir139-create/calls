"""
Delta-fetch missed calls from AmoCRM every 10 minutes.

Logic per event:
  incoming_call, duration=0/-1  → missed → INSERT/UPDATE missed_calls_rt
  incoming_call, duration>0     → client called back → DELETE from missed_calls_rt
  outgoing_call, duration>0     → manager called back → DELETE from missed_calls_rt

After processing events, refreshes waiting_minutes+sla_status for all open rows.
"""

import os, logging, requests
from datetime import datetime, timedelta
from pathlib import Path

import pytz
from dotenv import load_dotenv
from db import get_conn, DB_REALTIME

load_dotenv()
logger = logging.getLogger(__name__)

DOMAIN         = os.getenv("AMOCRM_DOMAIN")
TOKEN          = os.getenv("AMOCRM_TOKEN")
TARGET_USER_ID = os.getenv("AMOCRM_USER_ID")          # optional: filter by user id
TARGET_MANAGER = os.getenv("TARGET_MANAGER")           # optional: filter by manager name
SLA_WARNING    = float(os.getenv("SLA_WARNING_MINUTES", 8))
SLA_BREACH     = float(os.getenv("SLA_BREACH_MINUTES", 10))

TZ              = pytz.timezone("Asia/Tashkent")
LAST_FETCH_FILE = Path("/tmp/.last_fetch_ts")

HEADERS  = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
BASE_URL = f"https://{DOMAIN}/api/v4"

_phone_cache   = {}
_manager_cache = {}


# ── helpers ──────────────────────────────────────────────────────────────────

def _now_naive() -> datetime:
    """Current Tashkent time as naive datetime (for MySQL)."""
    return datetime.now(TZ).replace(tzinfo=None)


def _sla_status(waiting_min: float) -> str:
    if waiting_min < SLA_WARNING:  return "ok"
    if waiting_min < SLA_BREACH:   return "warning"
    return "breach"


def _get_last_fetch_ts() -> int:
    if LAST_FETCH_FILE.exists():
        return int(float(LAST_FETCH_FILE.read_text().strip()))
    return int((datetime.now(TZ) - timedelta(minutes=10)).timestamp())


def _save_last_fetch_ts(ts: int):
    LAST_FETCH_FILE.write_text(str(ts))


def _api_get(path: str, params: dict = None) -> dict | list:
    resp = requests.get(f"{BASE_URL}{path}", headers=HEADERS,
                        params=params, timeout=30)
    if resp.status_code == 204:
        return {}
    resp.raise_for_status()
    return resp.json()


def _fetch_events(since_ts: int) -> list:
    """Paginate through incoming_call + outgoing_call events since since_ts."""
    events = []
    for page in range(1, 20):   # safety cap at 4 750 events
        params = {
            "filter[type][0]":             "incoming_call",
            "filter[type][1]":             "outgoing_call",
            "filter[created_at][from]":    since_ts,
            "page":  page,
            "limit": 250,
        }
        if TARGET_USER_ID:
            params["filter[created_by][]"] = TARGET_USER_ID

        data = _api_get("/events", params)
        batch = data.get("_embedded", {}).get("events", []) if isinstance(data, dict) else []
        events.extend(batch)
        if len(batch) < 250:
            break
    return events


def _parse_duration(event: dict):
    """
    Extract call duration from event value_after.
    AmoCRM may store it as:
      [{note: {params: {duration: X}}}]   (older format)
      [{duration: X}]                      (newer format)
    Returns int or None.
    """
    for item in event.get("value_after") or []:
        if isinstance(item, dict):
            # nested note params
            params = item.get("note", {}).get("params", {})
            if "duration" in params:
                return params["duration"]
            # flat
            if "duration" in item:
                return item["duration"]
    return None


def _get_contact_id(event: dict):
    """Return contact_id from event, trying entity_links if entity_type != contacts."""
    if event.get("entity_type") == "contacts":
        return event.get("entity_id")
    for link in event.get("entity_links") or []:
        if link.get("entity_type") == "contacts":
            return link["entity_id"]
    return event.get("entity_id")


def _get_phone(contact_id: int) -> str:
    if contact_id in _phone_cache:
        return _phone_cache[contact_id]
    phone = ""
    try:
        data = _api_get(f"/contacts/{contact_id}")
        for field in data.get("custom_fields_values") or []:
            if field.get("field_code") in ("PHONE", "TEL"):
                vals = field.get("values") or []
                if vals:
                    phone = vals[0].get("value", "")
                    break
    except Exception as e:
        logger.warning("phone fetch failed contact=%s: %s", contact_id, e)
    _phone_cache[contact_id] = phone
    return phone


def _get_manager_name(user_id) -> str:
    if not user_id:
        return ""
    if user_id in _manager_cache:
        return _manager_cache[user_id]
    name = ""
    try:
        data = _api_get(f"/users/{user_id}")
        name = data.get("name", "")
    except Exception as e:
        logger.warning("user fetch failed id=%s: %s", user_id, e)
    _manager_cache[user_id] = name
    return name


# ── main ─────────────────────────────────────────────────────────────────────

def run_realtime_fetcher():
    logger.info("realtime_fetcher: start")
    now_naive = _now_naive()
    now_ts    = int(datetime.now(TZ).timestamp())
    since_ts  = _get_last_fetch_ts()

    try:
        events = _fetch_events(since_ts)
    except Exception as e:
        logger.error("API fetch failed: %s", e)
        return

    logger.info("Fetched %d events (since ts=%d)", len(events), since_ts)

    conn = get_conn(DB_REALTIME)
    cur  = conn.cursor()

    try:
        for ev in events:
            ev_type    = ev.get("type")
            duration   = _parse_duration(ev)
            contact_id = _get_contact_id(ev)
            user_id    = ev.get("created_by")

            if not contact_id:
                continue

            missed_at_naive = datetime.fromtimestamp(
                ev.get("created_at", now_ts), tz=TZ
            ).replace(tzinfo=None)

            if ev_type == "incoming_call":
                if duration in (None, 0, -1):
                    # ── missed call ──
                    phone        = _get_phone(contact_id)
                    manager_name = _get_manager_name(user_id)
                    if TARGET_MANAGER and TARGET_MANAGER.lower() not in manager_name.lower():
                        continue
                    waiting_min  = (now_naive - missed_at_naive).total_seconds() / 60
                    sla          = _sla_status(waiting_min)

                    cur.execute("""
                        INSERT INTO missed_calls_rt
                            (contact_id, phone, manager_name, missed_at, waiting_minutes, sla_status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            waiting_minutes = VALUES(waiting_minutes),
                            sla_status      = VALUES(sla_status)
                    """, (contact_id, phone, manager_name, missed_at_naive,
                          round(waiting_min, 2), sla))
                    logger.info("Missed: contact=%s waiting=%.1f min", contact_id, waiting_min)

                else:
                    # ── client called back (answered inbound) ──
                    n = cur.execute(
                        "DELETE FROM missed_calls_rt WHERE contact_id=%s", (contact_id,)
                    )
                    if n:
                        logger.info("Client recalled: contact=%s removed", contact_id)

            elif ev_type == "outgoing_call" and duration and duration > 0:
                # ── manager called back ──
                n = cur.execute(
                    "DELETE FROM missed_calls_rt WHERE contact_id=%s", (contact_id,)
                )
                if n:
                    logger.info("Manager recalled: contact=%s removed", contact_id)

        # ── refresh waiting_minutes for all open records ──
        cur.execute("SELECT id, missed_at FROM missed_calls_rt")
        for row in cur.fetchall():
            ma          = row["missed_at"]                        # naive datetime from MySQL
            waiting_min = (now_naive - ma).total_seconds() / 60
            sla         = _sla_status(waiting_min)
            cur.execute(
                "UPDATE missed_calls_rt SET waiting_minutes=%s, sla_status=%s WHERE id=%s",
                (round(waiting_min, 2), sla, row["id"]),
            )

        conn.commit()
        _save_last_fetch_ts(now_ts)
        logger.info("realtime_fetcher: done")

    except Exception as e:
        conn.rollback()
        logger.error("realtime_fetcher error: %s", e)
        raise
    finally:
        cur.close()
        conn.close()
