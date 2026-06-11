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

    conn = get_conn(DB_CALLS)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS amo_call_monthly_stats (
            id                   INT AUTO_INCREMENT PRIMARY KEY,
            stat_month           DATE NOT NULL,
            manager_name         VARCHAR(100) NOT NULL,
            period_start         DATE,
            period_end           DATE,
            total_calls          INT DEFAULT 0,
            incoming_answered    INT DEFAULT 0,
            outgoing_answered    INT DEFAULT 0,
            missed_clients       INT DEFAULT 0,
            recalled_clients     INT DEFAULT 0,
            not_recalled_clients INT DEFAULT 0,
            answer_rate          FLOAT DEFAULT 0,
            recall_rate          FLOAT DEFAULT 0,
            no_recall_pct        FLOAT DEFAULT 0,
            h_09_11 INT DEFAULT 0,
            h_11_13 INT DEFAULT 0,
            h_13_15 INT DEFAULT 0,
            h_15_17 INT DEFAULT 0,
            h_17_19 INT DEFAULT 0,
            h_19_21 INT DEFAULT 0,
            h_21_23 INT DEFAULT 0,
            loaded_at DATETIME DEFAULT NOW(),
            UNIQUE KEY uq_month_mgr (stat_month, manager_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS amo_call_daily_stats (
            id                   INT AUTO_INCREMENT PRIMARY KEY,
            stat_date            DATE NOT NULL,
            manager_name         VARCHAR(100) NOT NULL,
            total_calls          INT DEFAULT 0,
            incoming_answered    INT DEFAULT 0,
            outgoing_answered    INT DEFAULT 0,
            missed_clients       INT DEFAULT 0,
            recalled_clients     INT DEFAULT 0,
            not_recalled_clients INT DEFAULT 0,
            answer_rate          FLOAT DEFAULT 0,
            recall_rate          FLOAT DEFAULT 0,
            no_recall_pct        FLOAT DEFAULT 0,
            h_09_11 INT DEFAULT 0,
            h_11_13 INT DEFAULT 0,
            h_13_15 INT DEFAULT 0,
            h_15_17 INT DEFAULT 0,
            h_17_19 INT DEFAULT 0,
            h_19_21 INT DEFAULT 0,
            h_21_23 INT DEFAULT 0,
            loaded_at DATETIME DEFAULT NOW(),
            UNIQUE KEY uq_date_mgr (stat_date, manager_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    conn.commit(); cur.close(); conn.close()

    conn = get_conn(DB_TELEGRAM)
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS telegram_daily_stats (
            report_date             DATE NOT NULL,
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
