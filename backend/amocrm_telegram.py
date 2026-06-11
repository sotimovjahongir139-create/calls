import os
import sys
import time
from datetime import datetime, timedelta
from collections import defaultdict

import requests
from dotenv import load_dotenv
from db import get_conn

load_dotenv()

# ============================================================
# CONFIG — tokenlar .env dan o'qiladi
# ============================================================
ACCESS_TOKEN = os.getenv("AMOCRM_TOKEN")
# Accept either AMOCRM_SUBDOMAIN or extract from AMOCRM_DOMAIN
_domain   = os.getenv("AMOCRM_DOMAIN", "")
SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN") or (_domain.split(".")[0] if _domain else None)

if not ACCESS_TOKEN or not SUBDOMAIN:
    print("XATO: .env da AMOCRM_TOKEN yoki AMOCRM_SUBDOMAIN/AMOCRM_DOMAIN topilmadi.")
    sys.exit(1)

TARGET_MANAGER_NAME            = os.getenv("TARGET_MANAGER", "Asadbek")
FILTER_BY_RESPONSIBLE_MANAGER = True
TELEGRAM_ORIGIN               = "ru.whatcrm.telegram"

DB_TELEGRAM = os.getenv("MYSQL_DB_TELEGRAM", "telegram_dashboard")

SAVE_TO_SQL = True
REPORT_NAME = "ALL_TELEGRAM"

BASE_URL = f"https://{SUBDOMAIN}.amocrm.ru/api/v4"
HEADERS  = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type":  "application/json",
}

TIMEOUT     = 60
RETRIES     = 3
RETRY_DELAY = 3

# ============================================================
# SANA — argument yoki kecha
# ============================================================
report_day = datetime.now() - timedelta(days=1)
if len(sys.argv) > 1:
    try:
        report_day = datetime.strptime(sys.argv[1], "%Y-%m-%d")
        print(f"Manual sana: {report_day.strftime('%d.%m.%Y')}")
    except ValueError:
        pass  # not a date arg (e.g. uvicorn args), use yesterday

DAY_START = report_day.replace(hour=0,  minute=0,  second=0,  microsecond=0)
DAY_END   = report_day.replace(hour=23, minute=59, second=59, microsecond=0)

TS_FROM = int(DAY_START.timestamp())
TS_TO   = int(DAY_END.timestamp())


# ============================================================
# SQL
# ============================================================
def ensure_tables():
    conn = get_conn(DB_TELEGRAM)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_daily_stats (
            report_date             DATE         NOT NULL,
            report_name             VARCHAR(100) NOT NULL,
            unique_contacts         INT NOT NULL DEFAULT 0,
            unique_talks            INT NOT NULL DEFAULT 0,
            unique_leads            INT NOT NULL DEFAULT 0,
            total_events            INT NOT NULL DEFAULT 0,
            client_messages         INT NOT NULL DEFAULT 0,
            manager_messages        INT NOT NULL DEFAULT 0,
            client_turns            INT NOT NULL DEFAULT 0,
            answered_turns          INT NOT NULL DEFAULT 0,
            waiting_turns           INT NOT NULL DEFAULT 0,
            response_rate           FLOAT NOT NULL DEFAULT 0,
            avg_response_minutes    FLOAT NULL,
            median_response_minutes FLOAT NULL,
            loaded_at               DATETIME NOT NULL DEFAULT NOW(),
            PRIMARY KEY (report_date, report_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_response_details (
            id                        BIGINT AUTO_INCREMENT PRIMARY KEY,
            report_date               DATE NOT NULL,
            report_name               VARCHAR(100) NOT NULL,
            contact_id                BIGINT NULL,
            lead_id                   BIGINT NULL,
            talk_id                   BIGINT NULL,
            client_time               DATETIME NULL,
            manager_reply_time        DATETIME NULL,
            response_minutes          FLOAT NULL,
            status                    VARCHAR(30) NOT NULL,
            client_messages_in_turn   INT NULL,
            manager_messages_in_reply INT NULL,
            loaded_at                 DATETIME NOT NULL DEFAULT NOW()
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit(); cur.close(); conn.close()
    print("Tables OK")


def save_to_sql(summary, detail_rows):
    ensure_tables()
    conn = get_conn(DB_TELEGRAM)
    cur  = conn.cursor()
    rd, rn = summary["report_date"], summary["report_name"]

    cur.execute("DELETE FROM telegram_response_details WHERE report_date=%s AND report_name=%s", (rd, rn))
    cur.execute("DELETE FROM telegram_daily_stats       WHERE report_date=%s AND report_name=%s", (rd, rn))

    cur.execute("""
        INSERT INTO telegram_daily_stats (
            report_date, report_name,
            unique_contacts, unique_talks, unique_leads,
            total_events, client_messages, manager_messages,
            client_turns, answered_turns, waiting_turns,
            response_rate, avg_response_minutes, median_response_minutes
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        rd, rn,
        summary["unique_contacts"], summary["unique_talks"], summary["unique_leads"],
        summary["total_events"], summary["client_messages"], summary["manager_messages"],
        summary["client_turns"], summary["answered_turns"], summary["waiting_turns"],
        summary["response_rate"],
        summary["avg_response_minutes"],
        summary["median_response_minutes"],
    ))

    for row in detail_rows:
        cur.execute("""
            INSERT INTO telegram_response_details (
                report_date, report_name,
                contact_id, lead_id, talk_id,
                client_time, manager_reply_time,
                response_minutes, status,
                client_messages_in_turn, manager_messages_in_reply
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            row["report_date"], row["report_name"],
            row["contact_id"], row["lead_id"], row["talk_id"],
            row["client_time"], row["manager_reply_time"],
            row["response_minutes"], row["status"],
            row["client_messages_in_turn"], row["manager_messages_in_reply"],
        ))

    conn.commit(); cur.close(); conn.close()
    print("SQL saqlandi.")


# ============================================================
# API HELPERS
# ============================================================
def safe_get(url, params=None):
    for attempt in range(1, RETRIES + 1):
        try:
            return requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            print(f"API xato: {e}. Urinish {attempt}/{RETRIES}")
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY)
    return None


def get_manager_id_by_name(name):
    r = safe_get(f"{BASE_URL}/users")
    if not r:
        print("Users API javob bermadi.")
        return None, None
    if r.status_code == 401:
        print("Token noto'g'ri yoki muddati o'tgan.")
        sys.exit(1)
    users   = r.json().get("_embedded", {}).get("users", [])
    matches = [(u["id"], u["name"]) for u in users
               if name.lower() in u.get("name", "").lower()]
    if not matches:
        print(f"Manager topilmadi: {name}")
        for u in users:
            print(f"  {u.get('name')} | ID: {u.get('id')}")
        return None, None
    if len(matches) > 1:
        print(f"Bir nechta topildi, birinchisi: {matches[0][1]}")
    return matches[0]


def extract_message_info(event):
    for item in event.get("value_after", []) or []:
        msg = item.get("message")
        if msg:
            return {
                "message_id": msg.get("id"),
                "origin":     msg.get("origin"),
                "talk_id":    msg.get("talk_id"),
            }
    return {"message_id": None, "origin": None, "talk_id": None}


# ============================================================
# FETCH EVENTS
# ============================================================
def fetch_chat_events():
    all_events = []
    for etype in ["incoming_chat_message", "outgoing_chat_message"]:
        page = 1
        while True:
            params = {
                "limit": 250, "page": page,
                "filter[created_at][from]": TS_FROM,
                "filter[created_at][to]":   TS_TO,
                "filter[type]":             etype,
            }
            r = safe_get(f"{BASE_URL}/events", params=params)
            if not r or r.status_code == 204:
                break
            if r.status_code != 200:
                print(f"Events xato: {r.status_code}")
                break
            data  = r.json()
            items = data.get("_embedded", {}).get("events", [])
            if not items:
                break
            for e in items:
                msg = extract_message_info(e)
                if msg["origin"] != TELEGRAM_ORIGIN:
                    continue
                talk_contact_id = (
                    e.get("_embedded", {})
                     .get("entity", {})
                     .get("linked_talk_contact_id")
                )
                all_events.append({
                    "event_id":              e.get("id"),
                    "type":                  e.get("type"),
                    "lead_id":               e.get("entity_id"),
                    "entity_type":           e.get("entity_type"),
                    "created_at":            e.get("created_at"),
                    "created_by":            e.get("created_by"),
                    "message_id":            msg["message_id"],
                    "origin":                msg["origin"],
                    "talk_id":               msg["talk_id"],
                    "linked_talk_contact_id": talk_contact_id,
                })
            print(f"   {etype}: page {page}, jami: {len(all_events)}", end="\r")
            if "next" not in data.get("_links", {}):
                break
            page += 1
            time.sleep(0.1)
    print()
    return all_events


def fetch_lead_info_map(lead_ids):
    lead_ids = list(set(x for x in lead_ids if x))
    result   = {}
    for i in range(0, len(lead_ids), 50):
        batch  = lead_ids[i:i+50]
        params = {"limit": 50, "with": "contacts"}
        for j, lid in enumerate(batch):
            params[f"filter[id][{j}]"] = lid
        r = safe_get(f"{BASE_URL}/leads", params=params)
        if not r or r.status_code == 204:
            continue
        for lead in r.json().get("_embedded", {}).get("leads", []):
            lid      = lead.get("id")
            contacts = lead.get("_embedded", {}).get("contacts", []) or []
            result[lid] = {
                "responsible_user_id": lead.get("responsible_user_id"),
                "contact_id":          contacts[0].get("id") if contacts else None,
            }
        print(f"Lead info: {min(i+50, len(lead_ids))}/{len(lead_ids)}", end="\r")
        time.sleep(0.1)
    print()
    for lid in lead_ids:
        result.setdefault(lid, {"responsible_user_id": None, "contact_id": None})
    return result


def build_turns(events):
    turns = []
    for e in sorted(events, key=lambda x: x["created_at"]):
        side = ("CLIENT"  if e["type"] == "incoming_chat_message" else
                "MANAGER" if e["type"] == "outgoing_chat_message" else None)
        if not side:
            continue
        if not turns or turns[-1]["side"] != side:
            turns.append({
                "side":       side,
                "start_ts":   e["created_at"],
                "end_ts":     e["created_at"],
                "count":      1,
                "lead_id":    e.get("lead_id"),
                "contact_id": e.get("contact_id"),
                "talk_id":    e.get("talk_id"),
            })
        else:
            turns[-1]["end_ts"] = e["created_at"]
            turns[-1]["count"] += 1
    return turns


def analyze_conversation(group_key, events):
    rows             = []
    response_minutes = []
    turns            = build_turns(events)

    for idx, turn in enumerate(turns):
        if turn["side"] != "CLIENT":
            continue

        next_manager_turn = None
        for nxt in turns[idx + 1:]:
            if nxt["side"] == "MANAGER":
                next_manager_turn = nxt
                break

        client_time = datetime.fromtimestamp(turn["end_ts"])

        if next_manager_turn:
            diff_min = (next_manager_turn["start_ts"] - turn["end_ts"]) / 60
            if diff_min < 0 or diff_min > 1440:
                continue
            reply_time = datetime.fromtimestamp(next_manager_turn["start_ts"])
            rows.append({
                "report_date": DAY_START.date(),
                "report_name": REPORT_NAME,
                "group_key":   group_key,
                "contact_id":  turn["contact_id"],
                "lead_id":     turn["lead_id"],
                "talk_id":     turn["talk_id"],
                "client_time":          client_time,
                "manager_reply_time":   reply_time,
                "response_minutes":     diff_min,
                "status":               "ANSWERED",
                "client_messages_in_turn":    turn["count"],
                "manager_messages_in_reply":  next_manager_turn["count"],
            })
            response_minutes.append(diff_min)
        else:
            rows.append({
                "report_date": DAY_START.date(),
                "report_name": REPORT_NAME,
                "group_key":   group_key,
                "contact_id":  turn["contact_id"],
                "lead_id":     turn["lead_id"],
                "talk_id":     turn["talk_id"],
                "client_time":          client_time,
                "manager_reply_time":   None,
                "response_minutes":     None,
                "status":               "WAITING",
                "client_messages_in_turn":   turn["count"],
                "manager_messages_in_reply": None,
            })

    return rows, response_minutes


def format_minutes(value):
    if value is None:
        return "aniqlanmadi"
    total = int(round(value))
    h, m  = divmod(total, 60)
    return f"{h} soat {m} daqiqa" if h else f"{m} daqiqa"


def group_events(filtered_events):
    grouped = defaultdict(list)
    for e in filtered_events:
        key = e.get("talk_id") or e.get("contact_id") or e.get("lead_id")
        grouped[key].append(e)
    return grouped


# ============================================================
# MAIN
# ============================================================
def main():
    manager_id, manager_name = get_manager_id_by_name(TARGET_MANAGER_NAME)
    if not manager_id:
        sys.exit(1)

    print("\n" + "=" * 70)
    print(f"Sana   : {DAY_START.strftime('%d.%m.%Y')}")
    print(f"Report : {'Barcha Telegram chatlar' if not FILTER_BY_RESPONSIBLE_MANAGER else manager_name}")
    print(f"Manager: {manager_name} | ID: {manager_id}")
    print("=" * 70)

    print("\nTelegram chat events olinmoqda...")
    events = fetch_chat_events()
    print(f"Jami Telegram events: {len(events)}")

    if not events:
        print("Event topilmadi.")
        sys.exit(0)

    lead_ids      = [e["lead_id"] for e in events if e["lead_id"]]
    lead_info_map = fetch_lead_info_map(lead_ids)

    filtered_events = []
    for e in events:
        info = lead_info_map.get(e["lead_id"], {})
        e["responsible_user_id"] = info.get("responsible_user_id")
        e["contact_id"] = info.get("contact_id") or e.get("linked_talk_contact_id")
        if FILTER_BY_RESPONSIBLE_MANAGER and info.get("responsible_user_id") != manager_id:
            continue
        filtered_events.append(e)

    print(f"Filtrdan keyin: {len(filtered_events)} event")
    if not filtered_events:
        print("Bu filter bo'yicha event topilmadi.")
        sys.exit(0)

    incoming_count  = sum(1 for e in filtered_events if e["type"] == "incoming_chat_message")
    outgoing_count  = sum(1 for e in filtered_events if e["type"] == "outgoing_chat_message")
    unique_contacts = set(e["contact_id"] for e in filtered_events if e["contact_id"])
    unique_talks    = set(e["talk_id"]    for e in filtered_events if e["talk_id"])
    unique_leads    = set(e["lead_id"]    for e in filtered_events if e["lead_id"])

    grouped = group_events(filtered_events)

    all_rows             = []
    all_response_minutes = []
    for gkey, gevents in grouped.items():
        rows, minutes = analyze_conversation(gkey, gevents)
        all_rows.extend(rows)
        all_response_minutes.extend(minutes)

    answered_turns = sum(1 for r in all_rows if r["status"] == "ANSWERED")
    waiting_turns  = sum(1 for r in all_rows if r["status"] == "WAITING")
    client_turns   = answered_turns + waiting_turns
    response_rate  = (answered_turns / client_turns * 100) if client_turns else 0

    avg_response   = (sum(all_response_minutes) / len(all_response_minutes)
                      if all_response_minutes else None)
    sorted_minutes = sorted(all_response_minutes)
    if sorted_minutes:
        mid = len(sorted_minutes) // 2
        median_response = (sorted_minutes[mid] if len(sorted_minutes) % 2 == 1
                           else (sorted_minutes[mid-1] + sorted_minutes[mid]) / 2)
    else:
        median_response = None

    summary = {
        "report_date":    DAY_START.date(),
        "report_name":    REPORT_NAME,
        "unique_contacts": len(unique_contacts),
        "unique_talks":    len(unique_talks),
        "unique_leads":    len(unique_leads),
        "total_events":    len(filtered_events),
        "client_messages":  incoming_count,
        "manager_messages": outgoing_count,
        "client_turns":     client_turns,
        "answered_turns":   answered_turns,
        "waiting_turns":    waiting_turns,
        "response_rate":    round(response_rate, 2),
        "avg_response_minutes":    round(avg_response, 2)    if avg_response    is not None else None,
        "median_response_minutes": round(median_response, 2) if median_response is not None else None,
    }

    print("\n" + "=" * 70)
    print(f"Unik kontaktlar          : {summary['unique_contacts']}")
    print(f"Unik chatlar (talk)      : {summary['unique_talks']}")
    print(f"Unik leadlar             : {summary['unique_leads']}")
    print(f"Jami events              : {summary['total_events']}")
    print(f"Klient xabarlari         : {summary['client_messages']}")
    print(f"Manager javoblari        : {summary['manager_messages']}")
    print(f"Klient murojaat turnlari : {summary['client_turns']}")
    print(f"Javob berilgan           : {summary['answered_turns']}")
    print(f"Javob kutilayotgan       : {summary['waiting_turns']}")
    print(f"Javob berish darajasi    : {summary['response_rate']:.2f}%")
    print(f"O'rtacha javob vaqti     : {format_minutes(summary['avg_response_minutes'])}")
    print(f"Median javob vaqti       : {format_minutes(summary['median_response_minutes'])}")
    print("=" * 70)

    if SAVE_TO_SQL:
        print("\nSQL'ga yozilmoqda...")
        save_to_sql(summary, all_rows)

    print(f"\nTugadi: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    main()
