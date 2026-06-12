import os
import requests
import sys
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from db import get_conn

load_dotenv()

AMOCRM_DOMAIN   = os.getenv("AMOCRM_DOMAIN")
AMOCRM_TOKEN    = os.getenv("AMOCRM_TOKEN")
TARGET_MANAGERS = [os.getenv("TARGET_MANAGER", "Asadbek")]

if not AMOCRM_DOMAIN or not AMOCRM_TOKEN:
    print("XATO: .env da AMOCRM_DOMAIN yoki AMOCRM_TOKEN topilmadi.")
    sys.exit(1)

# ============================================================
# VAQT: Toshkent = UTC+5
# ============================================================
TZ = timezone(timedelta(hours=5))

def to_ts(dt):
    """Lokal datetime -> UTC timestamp"""
    return int(dt.replace(tzinfo=TZ).timestamp())

def from_ts(ts):
    """UTC timestamp -> Lokal datetime"""
    return datetime.fromtimestamp(ts, tz=TZ).replace(tzinfo=None)

# ============================================================
# SANALAR
# Bugun 03.05 => kecha=02.05 => oylik: 01.05-02.05, kunlik: 02.05
# Bugun 02.05 => kecha=01.05 => oylik: 01.05-01.05, kunlik: 01.05
# ============================================================
now       = datetime.now()
yesterday = now - timedelta(days=1)

DAY_START   = yesterday.replace(hour=0,  minute=0,  second=0,  microsecond=0)
DAY_END     = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)
MONTH_START = DAY_START.replace(day=1)
MONTH_END   = DAY_END

STAT_DATE  = yesterday.date()
STAT_MONTH = MONTH_START.date()

# ============================================================
# CONFIG
# ============================================================
BASE_URL    = f"https://{AMOCRM_DOMAIN}"
HEADERS     = {"Authorization": f"Bearer {AMOCRM_TOKEN}"}
TIMEOUT     = 60
RETRIES     = 3
RETRY_DELAY = 5

DB_CALLS = os.getenv("MYSQL_DB_CALLS", "calldb2")


def ensure_tables():
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CALLS}` CHARACTER SET utf8mb4")
    conn.commit(); cur.close(); conn.close()

    conn = get_conn(DB_CALLS)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS amo_call_monthly_stats (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            stat_month     DATE NOT NULL,
            manager_name   VARCHAR(100) NOT NULL,
            period_start   DATE,
            period_end     DATE,
            total_calls         INT DEFAULT 0,
            incoming_answered   INT DEFAULT 0,
            outgoing_answered   INT DEFAULT 0,
            missed_clients      INT DEFAULT 0,
            recalled_clients    INT DEFAULT 0,
            not_recalled_clients INT DEFAULT 0,
            answer_rate  FLOAT DEFAULT 0,
            recall_rate  FLOAT DEFAULT 0,
            no_recall_pct FLOAT DEFAULT 0,
            h_09_11 INT DEFAULT 0,
            h_11_13 INT DEFAULT 0,
            h_13_15 INT DEFAULT 0,
            h_15_17 INT DEFAULT 0,
            h_17_19 INT DEFAULT 0,
            h_19_21 INT DEFAULT 0,
            h_21_23 INT DEFAULT 0,
            avg_recall_minutes FLOAT DEFAULT 0,
            loaded_at DATETIME DEFAULT NOW(),
            UNIQUE KEY uq_month_mgr (stat_month, manager_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS amo_call_daily_stats (
            id             INT AUTO_INCREMENT PRIMARY KEY,
            stat_date      DATE NOT NULL,
            manager_name   VARCHAR(100) NOT NULL,
            total_calls         INT DEFAULT 0,
            incoming_answered   INT DEFAULT 0,
            outgoing_answered   INT DEFAULT 0,
            missed_clients      INT DEFAULT 0,
            recalled_clients    INT DEFAULT 0,
            not_recalled_clients INT DEFAULT 0,
            answer_rate  FLOAT DEFAULT 0,
            recall_rate  FLOAT DEFAULT 0,
            no_recall_pct FLOAT DEFAULT 0,
            h_09_11 INT DEFAULT 0,
            h_11_13 INT DEFAULT 0,
            h_13_15 INT DEFAULT 0,
            h_15_17 INT DEFAULT 0,
            h_17_19 INT DEFAULT 0,
            h_19_21 INT DEFAULT 0,
            h_21_23 INT DEFAULT 0,
            avg_recall_minutes FLOAT DEFAULT 0,
            loaded_at DATETIME DEFAULT NOW(),
            UNIQUE KEY uq_date_mgr (stat_date, manager_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    # migration: add avg_recall_minutes if missing on existing tables
    for tbl in ("amo_call_monthly_stats", "amo_call_daily_stats"):
        try:
            cur.execute(f"ALTER TABLE `{tbl}` ADD COLUMN avg_recall_minutes FLOAT DEFAULT 0")
        except Exception:
            pass
    conn.commit(); cur.close(); conn.close()

HOUR_SLOTS = [
    ("09:00-11:00", 9,  11),
    ("11:00-13:00", 11, 13),
    ("13:00-15:00", 13, 15),
    ("15:00-17:00", 15, 17),
    ("17:00-19:00", 17, 19),
    ("19:00-21:00", 19, 21),
    ("21:00-23:00", 21, 23),
]

# ============================================================
# API
# ============================================================
def safe_get(url, params=None):
    for attempt in range(1, RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
            return r
        except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            print(f"   Ulanish xatosi ({attempt}/{RETRIES}): {e}")
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY)
    raise Exception("Barcha urinishlar muvaffaqiyatsiz!")


def get_target_ids():
    r = safe_get(f"{BASE_URL}/api/v4/users")
    if r.status_code == 401:
        print("XATO: Token noto'g'ri.")
        sys.exit(1)
    ids = {}
    for u in r.json().get("_embedded", {}).get("users", []):
        name = u.get("name", "")
        for t in TARGET_MANAGERS:
            if t.lower() in name.lower():
                ids[u["id"]] = name
    return ids


def fetch_events(target_ids):
    start_ts = to_ts(MONTH_START)
    end_ts   = to_ts(MONTH_END)
    events   = []

    print(f"   Lokal: {MONTH_START.strftime('%d.%m.%Y %H:%M')} -> {MONTH_END.strftime('%d.%m.%Y %H:%M')}")
    print(f"   UTC timestamp: {start_ts} -> {end_ts}")

    for etype in ["incoming_call", "outgoing_call"]:
        page = 1
        while True:
            params = {
                "filter[created_at][from]": start_ts,
                "filter[created_at][to]":   end_ts,
                "filter[type]":             etype,
                "limit": 100,
                "page":  page,
            }
            r = safe_get(f"{BASE_URL}/api/v4/events", params=params)

            if r.status_code == 204:
                break
            if not r.ok:
                print(f"   Event xato: {r.status_code}")
                break

            data  = r.json()
            items = data.get("_embedded", {}).get("events", [])
            if not items:
                break

            filtered = [e for e in items if e.get("created_by") in target_ids]
            events.extend(filtered)
            print(f"   {etype}: {len(events)} ta, sahifa {page}", end="\r")

            if "next" not in data.get("_links", {}):
                break
            page += 1

    print()
    return events


def fetch_notes(note_ids):
    notes  = {}
    unique = list(set(note_ids))
    if not unique:
        return notes

    for i in range(0, len(unique), 50):
        batch = unique[i:i+50]
        for entity in ["contacts", "leads"]:
            params = {"limit": 50}
            for j, nid in enumerate(batch):
                params[f"filter[id][{j}]"] = nid
            r = safe_get(f"{BASE_URL}/api/v4/{entity}/notes", params=params)
            if r.ok and r.status_code != 204:
                for note in r.json().get("_embedded", {}).get("notes", []):
                    nid = note.get("id")
                    if nid:
                        notes[nid] = note.get("params", {}) or {}
                if any(nid in notes for nid in batch):
                    break
        print(f"   Notes: {len(notes)}/{len(unique)}", end="\r")

    print()
    return notes


# ============================================================
# HISOBLASH
# ============================================================
def build_records(events, notes):
    records = []
    for e in sorted(events, key=lambda x: x.get("created_at", 0)):
        etype      = e.get("type", "")
        contact_id = e.get("entity_id")
        created_at = e.get("created_at", 0)
        if not contact_id:
            continue

        note_id = None
        for va in e.get("value_after", []):
            note_id = va.get("note", {}).get("id")
            if note_id:
                break

        p         = notes.get(note_id, {}) if note_id else {}
        duration  = p.get("duration", -1)
        direction = p.get("direction", "")
        if not direction:
            direction = "inbound" if etype == "incoming_call" else "outbound"

        records.append({
            "direction":  direction,
            "duration":   duration,
            "contact_id": contact_id,
            "created_at": created_at,
        })
    return records


def calc(records):
    hours       = {label: 0 for label, _, _ in HOUR_SLOTS}
    missed_time = {}   # cid -> birinchi propushenniy timestamp
    missed      = set()
    recld       = set()
    recall_gaps = []   # har bir muvaffaqiyatli qayta aloqa uchun daqiqa
    in_a        = 0
    out_a       = 0

    for r in sorted(records, key=lambda x: x["created_at"]):
        cid = r["contact_id"]
        d   = r["direction"]
        dur = r["duration"]
        ts  = r["created_at"]

        if d == "inbound":
            if dur == 0 or dur == -1:
                missed.add(cid)
                if cid not in missed_time:
                    missed_time[cid] = ts
                h = from_ts(ts).hour
                for label, sh, eh in HOUR_SLOTS:
                    if sh <= h < eh:
                        hours[label] += 1
                        break

            elif dur > 0:
                in_a += 1
                if cid in missed:
                    # client called back and was answered — resolved without manager recall
                    missed.discard(cid)
                    missed_time.pop(cid, None)
                    recld.discard(cid)
                h = from_ts(ts).hour
                for label, sh, eh in HOUR_SLOTS:
                    if sh <= h < eh:
                        hours[label] += 1
                        break

        elif d == "outbound" and dur > 0:
            out_a += 1
            h = from_ts(ts).hour
            for label, sh, eh in HOUR_SLOTS:
                if sh <= h < eh:
                    hours[label] += 1
                    break

            if cid in missed and cid not in recld:
                recld.add(cid)
                if cid in missed_time:
                    gap_min = (ts - missed_time[cid]) / 60
                    if 0 < gap_min < 1440:
                        recall_gaps.append(gap_min)

    m     = len(missed)
    rc    = len(recld)
    nrc   = len(missed - recld)
    total = in_a + out_a + m

    ans   = round((in_a + out_a) / total * 100) if total else 0
    rec   = round(rc / m * 100) if m else 0
    norec = 100 - rec if m else 0
    avg_recall = round(sum(recall_gaps) / len(recall_gaps), 1) if recall_gaps else 0.0
    print(f"   [recall_gaps] count={len(recall_gaps)} sum={round(sum(recall_gaps),1)} avg={avg_recall}")
    print(f"   [recall_gaps] sample={[round(x,1) for x in recall_gaps[:10]]}")

    return {
        "total": total, "incoming": in_a, "outgoing": out_a,
        "missed": m, "recalled": rc, "not_recalled": nrc,
        "answer_rate": ans, "recall_rate": rec, "no_recall_pct": norec,
        "avg_recall_minutes": avg_recall,
        "hours": hours,
        "_recall_gaps_count": len(recall_gaps),
        "_recall_gaps_sample": recall_gaps[:5],
    }


def day_records(records, day_local):
    s = to_ts(day_local.replace(hour=0,  minute=0,  second=0,  microsecond=0))
    e = to_ts(day_local.replace(hour=23, minute=59, second=59, microsecond=0))
    r = [x for x in records if s <= x["created_at"] <= e]
    print(f"   Kunlik ({day_local.date()}): {len(r)} ta record | UTC {s}->{e}")
    return r


# ============================================================
# SQL
# ============================================================
def hv(s, l):
    return s["hours"].get(l, 0)


def save_monthly(stat_month, p_start, p_end, manager, s):
    conn = get_conn(DB_CALLS)
    cur  = conn.cursor()
    cur.execute("DELETE FROM amo_call_monthly_stats WHERE stat_month=%s AND manager_name=%s", (stat_month, manager))
    cur.execute("""
        INSERT INTO amo_call_monthly_stats (
            stat_month, manager_name, period_start, period_end,
            total_calls, incoming_answered, outgoing_answered,
            missed_clients, recalled_clients, not_recalled_clients,
            answer_rate, recall_rate, no_recall_pct,
            h_09_11, h_11_13, h_13_15, h_15_17, h_17_19, h_19_21, h_21_23,
            avg_recall_minutes
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        stat_month, manager, p_start, p_end,
        s["total"], s["incoming"], s["outgoing"],
        s["missed"], s["recalled"], s["not_recalled"],
        s["answer_rate"], s["recall_rate"], s["no_recall_pct"],
        hv(s,"09:00-11:00"), hv(s,"11:00-13:00"), hv(s,"13:00-15:00"),
        hv(s,"15:00-17:00"), hv(s,"17:00-19:00"), hv(s,"19:00-21:00"),
        hv(s,"21:00-23:00"), s.get("avg_recall_minutes", 0),
    ))
    conn.commit(); cur.close(); conn.close()
    print(f"   OK monthly -> {stat_month} | {manager} | total={s['total']}")


def save_daily(stat_date, manager, s):
    conn = get_conn(DB_CALLS)
    cur  = conn.cursor()
    cur.execute("DELETE FROM amo_call_daily_stats WHERE stat_date=%s AND manager_name=%s", (stat_date, manager))
    cur.execute("""
        INSERT INTO amo_call_daily_stats (
            stat_date, manager_name,
            total_calls, incoming_answered, outgoing_answered,
            missed_clients, recalled_clients, not_recalled_clients,
            answer_rate, recall_rate, no_recall_pct,
            h_09_11, h_11_13, h_13_15, h_15_17, h_17_19, h_19_21, h_21_23,
            avg_recall_minutes
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        stat_date, manager,
        s["total"], s["incoming"], s["outgoing"],
        s["missed"], s["recalled"], s["not_recalled"],
        s["answer_rate"], s["recall_rate"], s["no_recall_pct"],
        hv(s,"09:00-11:00"), hv(s,"11:00-13:00"), hv(s,"13:00-15:00"),
        hv(s,"15:00-17:00"), hv(s,"17:00-19:00"), hv(s,"19:00-21:00"),
        hv(s,"21:00-23:00"), s.get("avg_recall_minutes", 0),
    ))
    conn.commit(); cur.close(); conn.close()
    print(f"   OK daily   -> {stat_date} | {manager} | total={s['total']}")


# ============================================================
# CHIQARISH
# ============================================================
def bar(v, mx, w=20):
    f = round(v/mx*w) if mx else 0
    return "X"*f + "."*(w-f)


def print_stats(title, s):
    print("\n" + "="*65)
    print(f"  {title}")
    print("="*65)
    print(f"  Jami            : {s['total']}")
    print(f"  Kiruvchi        : {s['incoming']}")
    print(f"  Chiquvchi       : {s['outgoing']}")
    print(f"  Propushen       : {s['missed']}")
    print(f"  Qayta chiqilgan : {s['recalled']}")
    print(f"  Qayta chiqilmag : {s['not_recalled']}")
    print(f"  Javob berish %  : {s['answer_rate']}%")
    print(f"  Qayta chiqish % : {s['recall_rate']}%")
    print(f"  Qayta chiqilmag%: {s['no_recall_pct']}%")
    print(f"  O'rtacha qayta  : {s.get('avg_recall_minutes', 0)} daq")
    print("-"*65)
    mx = max(s["hours"].values()) if s["hours"] else 1
    for label, v in s["hours"].items():
        print(f"  {label}  {bar(v,mx)}  {v}")
    print("="*65)


# ============================================================
# MAIN
# ============================================================
def main():
    ensure_tables()
    print("="*65)
    print("  AMOCRM CALL ETL — " + now.strftime("%d.%m.%Y %H:%M"))
    print("="*65)
    print(f"  Oylik : {MONTH_START.strftime('%d.%m.%Y')} -> {MONTH_END.strftime('%d.%m.%Y')}")
    print(f"  Kunlik: {STAT_DATE} (kecha)")
    print("="*65)

    print("\n[1] Menejerlar...")
    target_ids = get_target_ids()
    if not target_ids:
        print("XATO: Menejer topilmadi!")
        sys.exit(1)
    for uid, name in target_ids.items():
        print(f"   {name} (ID: {uid})")
    manager = list(target_ids.values())[0]

    print("\n[2] Eventlar olinmoqda...")
    events = fetch_events(target_ids)
    print(f"   Jami {len(events)} ta event")

    note_ids = []
    for e in events:
        for va in e.get("value_after", []):
            nid = va.get("note", {}).get("id")
            if nid:
                note_ids.append(nid)
    print(f"\n[3] {len(note_ids)} ta note olinmoqda...")
    notes = fetch_notes(note_ids)
    print(f"   {len(notes)} ta note olindi")

    records = build_records(events, notes)
    print(f"\n[4] {len(records)} ta record")

    print("\n[DEBUG] Barcha recordlar (lokal vaqt):")
    for r in records:
        dt = from_ts(r["created_at"])
        print(f"   {dt.strftime('%d.%m %H:%M')} | {r['direction']} | dur={r['duration']} | cid={r['contact_id']}")

    print("\n[5] Hisob-kitob...")
    m_stats = calc(records)
    d_recs  = day_records(records, DAY_START)
    d_stats = calc(d_recs)

    print_stats(f"OYLIK | {MONTH_START.strftime('%d.%m')} - {MONTH_END.strftime('%d.%m.%Y')} | {manager}", m_stats)
    print_stats(f"KUNLIK | {STAT_DATE} | {manager}", d_stats)

    print("\n[6] SQL ga saqlanmoqda...")
    save_monthly(STAT_MONTH, MONTH_START.date(), MONTH_END.date(), manager, m_stats)
    save_daily(STAT_DATE, manager, d_stats)

    print("\nTAYYOR!\n")


if __name__ == "__main__":
    main()
