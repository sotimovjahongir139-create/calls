import os, pymysql
from dotenv import load_dotenv
load_dotenv()

DB_REALTIME = os.getenv('MYSQL_DB_REALTIME', 'crm_realtime')
DB_CALLS    = os.getenv('MYSQL_DB_CALLS',    'calldb2')
DB_TELEGRAM = os.getenv('MYSQL_DB_TELEGRAM', 'telegram_dashboard')

def get_conn(db=None):
    cfg = dict(
        host=os.getenv('MYSQL_HOST','localhost'),
        port=int(os.getenv('MYSQL_PORT',3306)),
        user=os.getenv('MYSQL_USER','root'),
        password=os.getenv('MYSQL_PASSWORD',''),
        charset='utf8mb4',
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=10,
    )
    if db: cfg['database'] = db
    return pymysql.connect(**cfg)

def ensure_schema():
    conn = get_conn()
    cur  = conn.cursor()
    for db in [DB_REALTIME, DB_CALLS, DB_TELEGRAM]:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db}` CHARACTER SET utf8mb4;")
    conn.commit(); cur.close(); conn.close()

    conn = get_conn(DB_REALTIME)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS missed_calls_rt (
            id INT AUTO_INCREMENT PRIMARY KEY,
            contact_id BIGINT NOT NULL,
            phone VARCHAR(30),
            manager_name VARCHAR(100),
            missed_at DATETIME NOT NULL,
            waiting_minutes FLOAT DEFAULT 0,
            sla_status ENUM('ok','warning','breach') DEFAULT 'ok',
            created_at DATETIME DEFAULT NOW(),
            UNIQUE KEY uq_contact (contact_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS task_completions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            contact_id BIGINT NOT NULL,
            manager_name VARCHAR(100),
            missed_at DATETIME NOT NULL,
            completed_at DATETIME NOT NULL,
            response_minutes FLOAT,
            deadline_minutes FLOAT,
            on_time BOOLEAN,
            score INT DEFAULT 0,
            stat_date DATE NOT NULL,
            created_at DATETIME DEFAULT NOW()
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_ratings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stat_date DATE NOT NULL,
            manager_name VARCHAR(100),
            total_tasks INT DEFAULT 0,
            completed_on_time INT DEFAULT 0,
            completed_late INT DEFAULT 0,
            not_completed INT DEFAULT 0,
            total_score INT DEFAULT 0,
            max_score INT DEFAULT 0,
            pct FLOAT DEFAULT 0,
            grade CHAR(1),
            calculated_at DATETIME DEFAULT NOW(),
            UNIQUE KEY uq_date_mgr (stat_date, manager_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    conn.commit(); cur.close(); conn.close()
