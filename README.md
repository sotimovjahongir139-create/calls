# CRM Real-time Dashboard

AmoCRM → missed calls → real-time dashboard (signals / tasks / rating).

## Stack
- **Backend**: Python 3.11, FastAPI, APScheduler, pymysql
- **Frontend**: React 18, Vite, Tailwind CSS
- **DB**: MySQL (external)
- **Deploy**: Render (backend) + Vercel (frontend)

---

## Local setup

### 1. Backend
```bash
cd backend
cp .env.example .env
# fill in .env

pip install -r requirements.txt

# Terminal A — API
uvicorn main:app --reload --port 8000

# Terminal B — scheduler + fetcher
python scheduler.py
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev      # → http://localhost:3000
```

---

## Deploy

### Render — 2 services (defined in render.yaml)

1. Go to [render.com](https://render.com) → New → Blueprint
2. Connect GitHub repo → Render reads `render.yaml` automatically
3. Two services are created: `crm-dashboard-api` (web) + `crm-dashboard-worker` (worker)
4. Fill in secret env vars in Render dashboard for both services:

| Variable        | Value                        |
|-----------------|------------------------------|
| `AMOCRM_DOMAIN` | `numbersarkon.amocrm.ru`     |
| `AMOCRM_TOKEN`  | your JWT token               |
| `MYSQL_HOST`    | your MySQL server IP         |
| `MYSQL_PORT`    | `3306`                       |
| `MYSQL_USER`    | your MySQL user              |
| `MYSQL_PASSWORD`| your MySQL password          |

### Vercel

1. Import repo, set **Root Directory** = `frontend`
2. Add env var: `VITE_API_URL=https://crm-dashboard-api.onrender.com`
3. Deploy.

---

## Architecture

```
AmoCRM API
  ↓ (every 10 min)
realtime_fetcher.py  →  missed_calls_rt (MySQL)
                              ↓
                        FastAPI backend
                              ↓
                        React frontend
                     (30s / 1min / 5min polling)
```

### SLA logic
| Waiting time | Status  | Color  |
|--------------|---------|--------|
| < 8 min      | ok      | green  |
| 8–10 min     | warning | yellow |
| > 10 min     | breach  | red    |

### Rating formula
```
score per task: +3 (on time) / +1 (late) / 0 (not done)
pct = total_score / (total_tasks × 3) × 100
A ≥ 90%  B ≥ 75%  C ≥ 60%  D ≥ 40%  E < 40%
```

### Deadline formula
```
deadline_minutes = open_task_count × TASK_MINUTES_PER_CLIENT (default 8)
```

---

## Env vars

```
AMOCRM_DOMAIN          yourdomain.amocrm.ru
AMOCRM_TOKEN           long-lived access token
AMOCRM_USER_ID         (optional) filter events by user id

MYSQL_HOST / PORT / USER / PASSWORD
MYSQL_DB_CALLS         calldb2
MYSQL_DB_TELEGRAM      telegram_dashboard
MYSQL_DB_REALTIME      crm_realtime

SLA_WARNING_MINUTES    8
SLA_BREACH_MINUTES     10
TASK_MINUTES_PER_CLIENT 8
```
