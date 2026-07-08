import os
import psycopg2
import pandas as pd
import hashlib
import base64
import hmac
from contextlib import contextmanager
from datetime import datetime

try:
    import streamlit as st
    DATABASE_URL = st.secrets["DATABASE_URL"]
except Exception:
    DATABASE_URL = os.environ.get("DATABASE_URL", "")


# ─────────── 비밀번호 해싱 (표준 라이브러리 pbkdf2) ───────────
def hash_password(password: str, iterations: int = 200_000) -> str:
    """pbkdf2-sha256 해시 문자열 생성 (salt 포함). 평문은 절대 저장하지 않음."""
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    """저장된 해시와 평문 비밀번호 비교 (타이밍 안전)."""
    try:
        algo, iters, salt_b64, hash_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iters))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False



def get_conn():
    url = DATABASE_URL
    if url and "sslmode" not in url:
        url += "?sslmode=require"
    return psycopg2.connect(url)


@contextmanager
def db_connection():
    """커넥션을 안전하게 열고, 예외 발생 여부와 무관하게 반드시 닫는다."""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def db_cursor(commit: bool = False):
    """커서를 열고, 정상 종료 시 (commit=True면) 커밋, 예외 시 롤백, 항상 커넥션을 닫는다."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        yield conn, cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@st.cache_resource
def init_db():
    conn = get_conn()
    c = conn.cursor()

    # 설비 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id SERIAL PRIMARY KEY,
            factory TEXT NOT NULL,
            equipment_code TEXT UNIQUE NOT NULL,
            equipment_name TEXT NOT NULL,
            location TEXT,
            category TEXT,
            status TEXT DEFAULT '정상',
            install_date TEXT,
            memo TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # 보전내역 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS maintenance (
            id SERIAL PRIMARY KEY,
            factory TEXT,
            shift TEXT,
            status TEXT DEFAULT '진행 중',
            region TEXT,
            equipment_code TEXT,
            equipment_name TEXT,
            issue_code TEXT,
            recv_year INTEGER,
            recv_month INTEGER,
            recv_week INTEGER,
            recv_weekday TEXT,
            recv_date TEXT,
            recv_hour INTEGER,
            recv_min INTEGER,
            comp_year INTEGER,
            comp_month INTEGER,
            comp_week INTEGER,
            comp_date TEXT,
            comp_hour INTEGER,
            comp_min INTEGER,
            downtime_min INTEGER DEFAULT 0,
            loss_time INTEGER DEFAULT 0,
            holiday_between INTEGER DEFAULT 0,
            assignee TEXT,
            contractor_type TEXT,
            recv_type TEXT,
            issue_desc TEXT,
            root_cause TEXT,
            slack_link TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # 이슈 코드 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS issue_code (
            id SERIAL PRIMARY KEY,
            part_name TEXT,
            part_name_en TEXT,
            part_code TEXT,
            issue_name TEXT,
            issue_name_en TEXT,
            issue_code TEXT,
            full_code TEXT UNIQUE
        )
    """)

    # 공휴일 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS holiday (
            id SERIAL PRIMARY KEY,
            holiday_date TEXT UNIQUE NOT NULL,
            holiday_name TEXT
        )
    """)

    # 슬랙 보전요청 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS slack_requests (
            id SERIAL PRIMARY KEY,
            channel_id TEXT NOT NULL,
            channel_name TEXT,
            message_ts TEXT NOT NULL,
            factory TEXT,
            equipment TEXT,
            symptom TEXT,
            inspection TEXT,
            assignee TEXT,
            status TEXT DEFAULT '진행 중',
            is_matched BOOLEAN DEFAULT FALSE,
            maintenance_id INTEGER REFERENCES maintenance(id) ON DELETE SET NULL,
            recv_date TEXT,
            comp_date TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(channel_id, message_ts)
        )
    """)

    # 슬랙 미매칭 데이터 테이블 (팩토리/설비명이 기존 데이터와 다를 때)
    c.execute("""
        CREATE TABLE IF NOT EXISTS slack_unmatched (
            id SERIAL PRIMARY KEY,
            slack_request_id INTEGER REFERENCES slack_requests(id) ON DELETE CASCADE,
            factory_raw TEXT,
            equipment_raw TEXT,
            channel_name TEXT,
            recv_date TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # 슬랙 채널별 마지막 동기화 타임스탬프
    c.execute("""
        CREATE TABLE IF NOT EXISTS slack_sync_state (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT,
            last_ts TEXT DEFAULT '0',
            synced_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # 작업일지 (작성자가 수기로 기입하는 일지)
    c.execute("""
        CREATE TABLE IF NOT EXISTS work_log (
            id SERIAL PRIMARY KEY,
            log_date TEXT NOT NULL,
            author TEXT,
            factory TEXT,
            category TEXT,
            title TEXT,
            content TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # 테넌트(회사) 테이블 — 멀티테넌시 기반 (현재는 단일 테넌트로 운영)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tenant (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    c.execute("INSERT INTO tenant (id, name) VALUES (1, '기본') ON CONFLICT DO NOTHING")

    # 사용자 계정 테이블 (관리자가 계정 생성, 자유가입 없음)
    c.execute("""
        CREATE TABLE IF NOT EXISTS app_user (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            role TEXT DEFAULT 'user',
            tenant_id INTEGER REFERENCES tenant(id) DEFAULT 1,
            is_active BOOLEAN DEFAULT TRUE,
            created_by TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_login TIMESTAMPTZ
        )
    """)

    # 감사 로그 테이블 (누가·언제·무엇을 변경했는지 추적)
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER DEFAULT 1,
            actor TEXT,
            action TEXT,
            entity TEXT,
            entity_id TEXT,
            detail TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # 예방보전(PM) 스케줄 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS pm_schedule (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER DEFAULT 1,
            equipment_code TEXT,
            equipment_name TEXT,
            title TEXT,
            interval_days INTEGER DEFAULT 30,
            last_done TEXT,
            next_due TEXT,
            memo TEXT,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # 부품 재고 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS part_inventory (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER DEFAULT 1,
            part_code TEXT,
            part_name TEXT,
            stock INTEGER DEFAULT 0,
            min_stock INTEGER DEFAULT 0,
            unit TEXT,
            location TEXT,
            memo TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # ── 멀티테넌시 마이그레이션: 운영 테이블에 tenant_id 부여 (멱등) ──
    # 기존 행은 DEFAULT 1 로 자동 backfill 되어 '기본' 테넌트에 귀속된다.
    for _tbl in ("equipment", "maintenance", "work_log", "slack_requests", "slack_unmatched"):
        c.execute(f"ALTER TABLE {_tbl} ADD COLUMN IF NOT EXISTS tenant_id INTEGER DEFAULT 1")
    c.execute("ALTER TABLE maintenance ADD COLUMN IF NOT EXISTS cost INTEGER DEFAULT 0")
    # 설비코드 전역 UNIQUE → (tenant_id, equipment_code) 복합 UNIQUE 로 전환
    c.execute("ALTER TABLE equipment DROP CONSTRAINT IF EXISTS equipment_equipment_code_key")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS equipment_tenant_code_uidx ON equipment (tenant_id, equipment_code)")

    # ── 성능 인덱스: 자주 필터/정렬되는 컬럼 (데이터 증가 대비) ──
    _idx = [
        "CREATE INDEX IF NOT EXISTS idx_maint_tenant ON maintenance(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_maint_tenant_year ON maintenance(tenant_id, recv_year)",
        "CREATE INDEX IF NOT EXISTS idx_maint_tenant_factory ON maintenance(tenant_id, factory)",
        "CREATE INDEX IF NOT EXISTS idx_maint_tenant_status ON maintenance(tenant_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_maint_tenant_eqcode ON maintenance(tenant_id, equipment_code)",
        "CREATE INDEX IF NOT EXISTS idx_equip_tenant ON equipment(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_worklog_tenant_date ON work_log(tenant_id, log_date)",
        "CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_log(tenant_id, id)",
        "CREATE INDEX IF NOT EXISTS idx_pm_tenant_due ON pm_schedule(tenant_id, next_due)",
        "CREATE INDEX IF NOT EXISTS idx_part_tenant ON part_inventory(tenant_id)",
        "CREATE INDEX IF NOT EXISTS idx_slackreq_tenant ON slack_requests(tenant_id)",
    ]
    for _q in _idx:
        try:
            c.execute(_q)
        except Exception:
            pass

    conn.commit()
    _seed_issue_codes(c, conn)
    _seed_holidays_2026(c, conn)
    _seed_admin(c, conn)
    conn.close()


def _seed_admin(c, conn):
    """최초 실행 시 최고관리자 계정 1개 생성 (부트스트랩).
    secrets [admin] username/password 사용, 없으면 기본값(admin/admin1234)."""
    c.execute("SELECT COUNT(*) FROM app_user WHERE role='superadmin'")
    if c.fetchone()[0] > 0:
        return
    try:
        admin_user = st.secrets["admin"]["username"]
        admin_pw = st.secrets["admin"]["password"]
    except Exception:
        admin_user = "admin"
        admin_pw = "admin1234"
    c.execute(
        "INSERT INTO app_user (username, password_hash, display_name, role, tenant_id, created_by) "
        "VALUES (%s,%s,%s,'superadmin',1,'system') ON CONFLICT (username) DO NOTHING",
        (admin_user, hash_password(admin_pw), "최고관리자"),
    )
    conn.commit()



def _seed_issue_codes(c, conn):
    """이슈 코드 기초 데이터 삽입"""
    c.execute("SELECT COUNT(*) FROM issue_code")
    count = c.fetchone()[0]
    if count > 0:
        return

    parts = [
        ("가이드", "Guide", "GDE"),
        ("갈림캠 (모아)", "Gating Cam", "GCM"),
        ("갈림날 (린선)", "Gating Blade", "GBD"),
        ("구조물", "Structure/Frame", "STR"),
        ("기어류, 베벨 포함", "Gear", "GEA"),
        ("노즐", "Nozzle", "NOZ"),
        ("레일, 컨베이어 레인", "Rail", "RAI"),
        ("린스 투입기", "Rinse Feeder", "RIF"),
        ("모터", "Motor", "MOT"),
        ("배관, 호스", "Pipe/Hose", "PIP"),
        ("밸브", "Valve", "VLV"),
        ("베어링", "Bearing", "BRG"),
        ("복합", "Multiple", "MIX"),
        ("브레이커", "Breaker", "BRK"),
        ("센서", "Sensor", "SNS"),
        ("세제 투입기", "Detergent Feeder", "DTF"),
        ("스프라켓", "Sprocket", "SPR"),
        ("에어실린더", "Air Cylinder", "ACY"),
        ("어셈블리", "Assembly", "ACH"),
        ("전기판넬", "Electric Panel", "PWR"),
        ("전등", "Light", "LGT"),
        ("체인", "Chain", "CHN"),
        ("컨베이어 벨트", "Conveyor Belt", "CVB"),
        ("펌프", "Pump", "PMP"),
        ("팬", "Fan", "FAN"),
        ("히터", "Heater", "HTR"),
    ]

    issues = [
        ("정렬/조정", "Adjustment", "A"),
        ("청소불량", "Cleaning Deficiency", "C"),
        ("이탈", "Dislocation", "D"),
        ("에러/센서 이상", "Error", "E"),
        ("파손/고장/변형", "Failure", "F"),
        ("윤활/그리스/오일 부족", "Grease", "G"),
        ("과열", "Overheated", "H"),
        ("점검/유지보수", "Inspection", "I"),
        ("끼임", "Jam", "J"),
        ("장력 이상", "Tension", "T"),
        ("누설", "Leakage", "L"),
        ("누기", "Air Leakage", "AL"),
        ("누전", "Electric Leakage", "EL"),
        ("소음/진동", "Noise/Vibration", "NV"),
        ("기타", "Others", "O"),
    ]

    rows = []
    for p_name, p_en, p_code in parts:
        for i_name, i_en, i_code in issues:
            full = f"{p_code}-{i_code}"
            rows.append((p_name, p_en, p_code, i_name, i_en, i_code, full))

    c.executemany(
        "INSERT INTO issue_code (part_name,part_name_en,part_code,issue_name,issue_name_en,issue_code,full_code) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (full_code) DO NOTHING",
        rows,
    )
    conn.commit()


def _seed_holidays_2026(c, conn):
    """2026년 공휴일 삽입"""
    c.execute("SELECT COUNT(*) FROM holiday")
    count = c.fetchone()[0]
    if count > 0:
        return

    holidays = [
        ("2026-01-01", "신정"),
        ("2026-01-28", "설날 연휴"),
        ("2026-01-29", "설날"),
        ("2026-01-30", "설날 연휴"),
        ("2026-03-01", "삼일절"),
        ("2026-05-05", "어린이날"),
        ("2026-05-25", "부처님오신날"),
        ("2026-06-06", "현충일"),
        ("2026-08-15", "광복절"),
        ("2026-09-24", "추석 연휴"),
        ("2026-09-25", "추석"),
        ("2026-09-26", "추석 연휴"),
        ("2026-10-03", "개천절"),
        ("2026-10-09", "한글날"),
        ("2026-12-25", "크리스마스"),
    ]
    c.executemany("INSERT INTO holiday (holiday_date,holiday_name) VALUES (%s,%s) ON CONFLICT (holiday_date) DO NOTHING", holidays)
    conn.commit()


# ─────────── 설비 CRUD ───────────
def _current_tenant() -> int:
    """현재 로그인 사용자의 테넌트 id. 미로그인/미설정 시 기본 테넌트(1)."""
    try:
        u = st.session_state.get("auth_user")
        if u and u.get("tenant_id"):
            return int(u["tenant_id"])
    except Exception:
        pass
    return 1


@st.cache_data(ttl=300)
def _get_equipment_q(tenant_id, factory=None, status=None):
    q = "SELECT * FROM equipment WHERE tenant_id=%s"
    params = [tenant_id]
    if factory:
        q += " AND factory=%s"
        params.append(factory)
    if status:
        q += " AND status=%s"
        params.append(status)
    q += " ORDER BY factory, equipment_code"
    with db_connection() as conn:
        return pd.read_sql_query(q, conn, params=params)


def get_equipment(factory=None, status=None):
    return _get_equipment_q(_current_tenant(), factory, status)


def upsert_equipment(data: dict):
    tid = _current_tenant()
    with db_cursor(commit=True) as (conn, c):
        if data.get("id"):
            c.execute("""
                UPDATE equipment SET factory=%s,equipment_code=%s,equipment_name=%s,
                location=%s,category=%s,status=%s,install_date=%s,memo=%s
                WHERE id=%s AND tenant_id=%s
            """, (data["factory"], data["equipment_code"], data["equipment_name"],
                  data.get("location"), data.get("category"), data.get("status","정상"),
                  data.get("install_date"), data.get("memo"), data["id"], tid))
        else:
            c.execute("""
                INSERT INTO equipment (factory,equipment_code,equipment_name,location,category,status,install_date,memo,tenant_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (data["factory"], data["equipment_code"], data["equipment_name"],
                  data.get("location"), data.get("category"), data.get("status","정상"),
                  data.get("install_date"), data.get("memo"), tid))
    log_audit("등록/수정", "설비", data.get("equipment_code",""), data.get("equipment_name",""))


def delete_equipment(eq_id: int):
    with db_cursor(commit=True) as (conn, c):
        c.execute("DELETE FROM equipment WHERE id=%s AND tenant_id=%s", (eq_id, _current_tenant()))
    log_audit("삭제", "설비", eq_id)



# ─────────── 보전내역 CRUD ───────────
@st.cache_data(ttl=300)
def _get_maintenance_q(tenant_id, factory=None, status=None, year=None, month=None, week=None):
    q = "SELECT * FROM maintenance WHERE tenant_id=%s"
    params = [tenant_id]
    if factory:
        q += " AND factory=%s"
        params.append(factory)
    if status:
        q += " AND status=%s"
        params.append(status)
    if year:
        q += " AND recv_year=%s"
        params.append(year)
    if month:
        q += " AND recv_month=%s"
        params.append(month)
    if week:
        q += " AND recv_week=%s"
        params.append(week)
    q += " ORDER BY recv_date DESC, id DESC"
    with db_connection() as conn:
        return pd.read_sql_query(q, conn, params=params)


def get_maintenance(factory=None, status=None, year=None, month=None, week=None):
    return _get_maintenance_q(_current_tenant(), factory, status, year, month, week)


def insert_maintenance(data: dict, conn=None):
    own = conn is None
    if own:
        conn = get_conn()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tid = _current_tenant()


    recv_date = data.get("recv_date", "")
    if recv_date:
        try:
            dt = datetime.strptime(recv_date, "%Y-%m-%d")
            recv_year = dt.year
            recv_month = dt.month
            recv_week = int(dt.strftime("%W"))
            recv_weekday = ["월요일","화요일","수요일","목요일","금요일","토요일","일요일"][dt.weekday()]
        except Exception:
            recv_year = recv_month = recv_week = None
            recv_weekday = None
    else:
        recv_year = recv_month = recv_week = recv_weekday = None

    comp_date = data.get("comp_date", "")
    if comp_date:
        try:
            dt2 = datetime.strptime(comp_date, "%Y-%m-%d")
            comp_year = dt2.year
            comp_month = dt2.month
            comp_week = int(dt2.strftime("%W"))
        except Exception:
            comp_year = comp_month = comp_week = None
    else:
        comp_year = comp_month = comp_week = None

    c.execute("""
        INSERT INTO maintenance (
            factory, shift, status, region, equipment_code, equipment_name,
            issue_code, recv_year, recv_month, recv_week, recv_weekday,
            recv_date, recv_hour, recv_min,
            comp_year, comp_month, comp_week, comp_date, comp_hour, comp_min,
            downtime_min, loss_time, holiday_between,
            assignee, contractor_type, recv_type, issue_desc, root_cause, slack_link,
            created_at, updated_at, tenant_id, cost
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data.get("factory"), data.get("shift"), data.get("status","진행 중"),
        data.get("region"), data.get("equipment_code"), data.get("equipment_name"),
        data.get("issue_code"),
        recv_year, recv_month, recv_week, recv_weekday,
        recv_date, data.get("recv_hour"), data.get("recv_min"),
        comp_year, comp_month, comp_week,
        comp_date, data.get("comp_hour"), data.get("comp_min"),
        data.get("downtime_min", 0), data.get("loss_time", 0), data.get("holiday_between", 0),
        data.get("assignee"), data.get("contractor_type"), data.get("recv_type"),
        data.get("issue_desc"), data.get("root_cause"), data.get("slack_link"),
        now, now, tid, int(data.get("cost", 0) or 0)
    ))
    eq_code = data.get("equipment_code")
    status = data.get("status", "진행 중")
    if eq_code:
        _sync_equipment_status(conn, eq_code, status, commit=False, tenant_id=tid)
    if own:
        conn.commit()
        conn.close()
        log_audit("등록", "보전내역", eq_code or "", f"{data.get('factory','')} · {(data.get('issue_desc') or '')[:50]}")


def _sync_equipment_status(conn, equipment_code: str, maint_status: str, commit: bool = True, tenant_id: int = 1):
    if maint_status == "진행 중":
        eq_status = "점검중"
    elif maint_status == "팬딩":
        eq_status = "팬딩"
    elif maint_status == "고장":
        eq_status = "고장"
    elif maint_status in ("완료", "취소"):
        eq_status = "정상"
    else:
        return
    c = conn.cursor()
    c.execute("UPDATE equipment SET status=%s WHERE equipment_code=%s AND tenant_id=%s",
              (eq_status, equipment_code, tenant_id))
    if commit:
        conn.commit()



def update_maintenance(m_id: int, data: dict):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tid = _current_tenant()

    comp_date = data.get("comp_date", "")
    if comp_date:
        try:
            dt2 = datetime.strptime(comp_date, "%Y-%m-%d")
            comp_year = dt2.year
            comp_month = dt2.month
            comp_week = int(dt2.strftime("%W"))
        except Exception:
            comp_year = comp_month = comp_week = None
    else:
        comp_year = comp_month = comp_week = None

    with db_cursor(commit=True) as (conn, c):
        c.execute("""
            UPDATE maintenance SET
                factory=%s, shift=%s, status=%s, region=%s, equipment_code=%s, equipment_name=%s,
                issue_code=%s, comp_year=%s, comp_month=%s, comp_week=%s,
                comp_date=%s, comp_hour=%s, comp_min=%s,
                downtime_min=%s, loss_time=%s, assignee=%s, contractor_type=%s,
                recv_type=%s, issue_desc=%s, root_cause=%s, slack_link=%s, cost=%s, updated_at=%s
            WHERE id=%s AND tenant_id=%s
        """, (
            data.get("factory"), data.get("shift"), data.get("status"),
            data.get("region"), data.get("equipment_code"), data.get("equipment_name"),
            data.get("issue_code"),
            comp_year, comp_month, comp_week,
            comp_date, data.get("comp_hour"), data.get("comp_min"),
            data.get("downtime_min", 0), data.get("loss_time", 0),
            data.get("assignee"), data.get("contractor_type"),
            data.get("recv_type"), data.get("issue_desc"), data.get("root_cause"),
            data.get("slack_link"), int(data.get("cost", 0) or 0), now, m_id, tid
        ))
        eq_code = data.get("equipment_code")
        status = data.get("status")
        if eq_code and status:
            _sync_equipment_status(conn, eq_code, status, commit=False, tenant_id=tid)
    log_audit("수정", "보전내역", m_id, f"{data.get('equipment_code','')} · {data.get('status','')}")


def delete_maintenance(m_id: int):
    with db_cursor(commit=True) as (conn, c):
        c.execute("DELETE FROM maintenance WHERE id=%s AND tenant_id=%s", (m_id, _current_tenant()))
    log_audit("삭제", "보전내역", m_id)



# ─────────── 이슈코드 조회 ───────────
@st.cache_data(ttl=600)
def get_issue_codes():
    with db_connection() as conn:
        return pd.read_sql_query("SELECT DISTINCT full_code, part_name, issue_name FROM issue_code ORDER BY full_code", conn)


@st.cache_data(ttl=600)
def get_issue_code_full():
    """이슈코드 전체 상세(부품/이슈 영문 포함) 목록."""
    with db_connection() as conn:
        return pd.read_sql_query(
            "SELECT id, part_name, part_name_en, part_code, issue_name, issue_name_en, issue_code, full_code "
            "FROM issue_code ORDER BY part_code, issue_code",
            conn,
        )


@st.cache_data(ttl=600)
def get_part_codes():
    """부품코드 distinct 목록."""
    with db_connection() as conn:
        return pd.read_sql_query(
            "SELECT DISTINCT part_code, part_name, part_name_en FROM issue_code ORDER BY part_code",
            conn,
        )


def add_issue_code(part_name, part_name_en, part_code, issue_name, issue_name_en, issue_code) -> bool:
    """이슈코드 추가. 중복(full_code)이면 False, 신규 삽입이면 True."""
    full = f"{part_code}-{issue_code}"
    with db_cursor(commit=True) as (conn, c):
        c.execute(
            "INSERT INTO issue_code (part_name,part_name_en,part_code,issue_name,issue_name_en,issue_code,full_code) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (full_code) DO NOTHING",
            (part_name, part_name_en, part_code, issue_name, issue_name_en, issue_code, full),
        )
        return c.rowcount > 0


def get_issue_code_options():
    df = get_issue_codes()
    return df["full_code"].tolist()


# ─────────── 통계 쿼리 ───────────
@st.cache_data(ttl=300)
def _get_available_years_q(tenant_id):
    from datetime import datetime as _dt
    with db_connection() as conn:
        df = pd.read_sql_query(
            "SELECT DISTINCT recv_year FROM maintenance WHERE tenant_id=%s AND recv_year IS NOT NULL ORDER BY recv_year DESC",
            conn, params=[tenant_id],
        )
    years = [int(y) for y in df["recv_year"].tolist()] if not df.empty else []
    if not years:
        years = [_dt.now().year]
    return years


def get_available_years():
    """maintenance에 존재하는 접수 연도 목록(내림차순). 없으면 올해 연도 1개."""
    return _get_available_years_q(_current_tenant())


@st.cache_data(ttl=300)
def _get_kpi_q(tenant_id, year=None):
    conds = ["tenant_id=%s"]
    params = [tenant_id]
    if year:
        conds.append("recv_year=%s")
        params.append(year)
    where = "WHERE " + " AND ".join(conds)
    with db_cursor() as (conn, c):
        c.execute(f"""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (WHERE status='완료'),
                COUNT(*) FILTER (WHERE status IN ('진행 중','팬딩')),
                AVG(downtime_min) FILTER (WHERE downtime_min > 0)
            FROM maintenance {where}
        """, params)
        total, done, pending, avg_down = c.fetchone()
    rate = round(done / total * 100, 1) if total else 0
    return {
        "total": total,
        "done": done,
        "pending": pending,
        "rate": rate,
        "avg_down": round(avg_down, 1) if avg_down else 0,
    }


def get_kpi(year=None):
    return _get_kpi_q(_current_tenant(), year)


@st.cache_data(ttl=300)
def _get_monthly_count_q(tenant_id, year=None):
    conds = ["tenant_id=%s"]
    params = [tenant_id]
    if year:
        conds.append("recv_year=%s")
        params.append(year)
    where = "WHERE " + " AND ".join(conds)
    with db_connection() as conn:
        return pd.read_sql_query(
            f"SELECT recv_month as 월, COUNT(*) as 건수 FROM maintenance {where} GROUP BY recv_month ORDER BY recv_month",
            conn, params=params,
        )


def get_monthly_count(year=None):
    return _get_monthly_count_q(_current_tenant(), year)


@st.cache_data(ttl=300)
def _get_factory_count_q(tenant_id, year=None):
    conds = ["tenant_id=%s"]
    params = [tenant_id]
    if year:
        conds.append("recv_year=%s")
        params.append(year)
    where = "WHERE " + " AND ".join(conds)
    with db_connection() as conn:
        return pd.read_sql_query(
            f"SELECT factory as 팭토리, COUNT(*) as 건수 FROM maintenance {where} GROUP BY factory ORDER BY 건수 DESC",
            conn, params=params,
        )


def get_factory_count(year=None):
    return _get_factory_count_q(_current_tenant(), year)


@st.cache_data(ttl=300)
def _get_issue_top_q(tenant_id, year=None, limit=15):
    conds = ["tenant_id=%s", "issue_code IS NOT NULL"]
    params = [tenant_id]
    if year:
        conds.insert(1, "recv_year=%s")
        params.append(year)
    where = "WHERE " + " AND ".join(conds)
    with db_connection() as conn:
        return pd.read_sql_query(
            f"SELECT issue_code as 이슈코드, COUNT(*) as 건수 FROM maintenance {where} GROUP BY issue_code ORDER BY 건수 DESC LIMIT {int(limit)}",
            conn, params=params,
        )


def get_issue_top(year=None, limit=15):
    return _get_issue_top_q(_current_tenant(), year, limit)


@st.cache_data(ttl=300)
def _get_weekly_pivot_q(tenant_id, year=None, factory=None):
    where_parts = ["tenant_id=%s"]
    params = [tenant_id]
    if year:
        where_parts.append("recv_year=%s")
        params.append(year)
    if factory:
        where_parts.append("factory=%s")
        params.append(factory)
    where = "WHERE " + " AND ".join(where_parts)
    with db_connection() as conn:
        return pd.read_sql_query(
            f"""SELECT factory, equipment_code, equipment_name, recv_week, COUNT(*) as cnt
                FROM maintenance {where}
                GROUP BY factory, equipment_code, equipment_name, recv_week
                ORDER BY factory, equipment_code, recv_week""",
            conn, params=params,
        )


def get_weekly_pivot(year=None, factory=None):
    return _get_weekly_pivot_q(_current_tenant(), year, factory)


@st.cache_data(ttl=300)
def _get_overdue_q(tenant_id, days=30):
    with db_connection() as conn:
        return pd.read_sql_query(
            """SELECT id, factory, equipment_code, equipment_name, recv_date, status, issue_desc,
                (CURRENT_DATE - recv_date::date)::INTEGER as overdue_days
                FROM maintenance
                WHERE tenant_id=%s
                AND status IN ('진행 중','팬딩')
                AND recv_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                AND (CURRENT_DATE - recv_date::date)::INTEGER >= %s
                ORDER BY overdue_days DESC""",
            conn, params=[tenant_id, days],
        )


def get_overdue(days=30):
    return _get_overdue_q(_current_tenant(), days)


# ─────────── 설비별 이력 · 지표(MTBF/MTTR) ───────────
@st.cache_data(ttl=300)
def _get_equipment_history_q(tenant_id, equipment_code):
    with db_connection() as conn:
        return pd.read_sql_query(
            "SELECT id, recv_date, comp_date, status, issue_code, issue_desc, "
            "downtime_min, assignee "
            "FROM maintenance WHERE tenant_id=%s AND equipment_code=%s "
            "ORDER BY recv_date DESC, id DESC LIMIT 200",
            conn, params=[tenant_id, equipment_code],
        )


def get_equipment_history(equipment_code):
    return _get_equipment_history_q(_current_tenant(), equipment_code)


@st.cache_data(ttl=300)
def _get_equipment_stats_q(tenant_id, equipment_code):
    with db_cursor() as (conn, c):
        c.execute(
            """SELECT COUNT(*),
                      AVG(downtime_min) FILTER (WHERE status='완료' AND downtime_min > 0),
                      MAX(recv_date)
               FROM maintenance
               WHERE tenant_id=%s AND equipment_code=%s""",
            (tenant_id, equipment_code),
        )
        cnt, mttr, last_date = c.fetchone()
        c.execute(
            """SELECT AVG(gap) FROM (
                   SELECT (recv_date::date - LAG(recv_date::date)
                           OVER (ORDER BY recv_date::date)) AS gap
                   FROM maintenance
                   WHERE tenant_id=%s AND equipment_code=%s
                     AND recv_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
               ) t WHERE gap IS NOT NULL""",
            (tenant_id, equipment_code),
        )
        mtbf = c.fetchone()[0]
    return {
        "count": cnt or 0,
        "mttr": round(float(mttr), 1) if mttr else 0,
        "mtbf_days": round(float(mtbf), 1) if mtbf else 0,
        "last_date": last_date or "-",
    }


def get_equipment_stats(equipment_code):
    return _get_equipment_stats_q(_current_tenant(), equipment_code)


# ─────────── 예방보전(PM) 스케줄 CRUD ───────────
def _add_days(date_str: str, days: int) -> str:
    from datetime import datetime as _dt, timedelta as _td
    try:
        return (_dt.strptime(date_str, "%Y-%m-%d") + _td(days=int(days))).strftime("%Y-%m-%d")
    except Exception:
        return date_str


def add_pm(data: dict):
    from datetime import datetime as _dt
    interval = int(data.get("interval_days") or 30)
    last_done = data.get("last_done") or _dt.now().strftime("%Y-%m-%d")
    next_due = _add_days(last_done, interval)
    with db_cursor(commit=True) as (conn, c):
        c.execute(
            "INSERT INTO pm_schedule (tenant_id, equipment_code, equipment_name, title, "
            "interval_days, last_done, next_due, memo) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (_current_tenant(), data.get("equipment_code"), data.get("equipment_name"),
             data.get("title"), interval, last_done, next_due, data.get("memo")),
        )
    log_audit("등록", "예방보전", data.get("equipment_code", ""), data.get("title", ""))


@st.cache_data(ttl=120)
def _get_pm_list_q(tenant_id, active_only=True):
    q = ("SELECT id, equipment_code, equipment_name, title, interval_days, "
         "last_done, next_due, memo, active FROM pm_schedule WHERE tenant_id=%s")
    if active_only:
        q += " AND active=TRUE"
    q += " ORDER BY next_due ASC NULLS LAST, id DESC"
    with db_connection() as conn:
        return pd.read_sql_query(q, conn, params=[tenant_id])


def get_pm_list(active_only=True):
    return _get_pm_list_q(_current_tenant(), active_only)


def mark_pm_done(pm_id: int, done_date: str = None):
    from datetime import datetime as _dt
    done = done_date or _dt.now().strftime("%Y-%m-%d")
    with db_cursor(commit=True) as (conn, c):
        c.execute("SELECT interval_days FROM pm_schedule WHERE id=%s AND tenant_id=%s",
                  (pm_id, _current_tenant()))
        row = c.fetchone()
        interval = int(row[0]) if row and row[0] else 30
        next_due = _add_days(done, interval)
        c.execute("UPDATE pm_schedule SET last_done=%s, next_due=%s WHERE id=%s AND tenant_id=%s",
                  (done, next_due, pm_id, _current_tenant()))
    log_audit("완료처리", "예방보전", pm_id)


def delete_pm(pm_id: int):
    with db_cursor(commit=True) as (conn, c):
        c.execute("DELETE FROM pm_schedule WHERE id=%s AND tenant_id=%s", (pm_id, _current_tenant()))
    log_audit("삭제", "예방보전", pm_id)


def get_pm_due_count(within_days: int = 7) -> int:
    """마감 임박(오늘~within_days 이내) PM 건수. 대시보드 알림용."""
    from datetime import datetime as _dt, timedelta as _td
    limit = (_dt.now() + _td(days=within_days)).strftime("%Y-%m-%d")
    try:
        with db_cursor() as (conn, c):
            c.execute(
                "SELECT COUNT(*) FROM pm_schedule WHERE tenant_id=%s AND active=TRUE "
                "AND next_due IS NOT NULL AND next_due<=%s",
                (_current_tenant(), limit),
            )
            return c.fetchone()[0] or 0
    except Exception:
        return 0


# ─────────── 부품 재고 CRUD ───────────
def add_part(data: dict):
    tid = _current_tenant()
    with db_cursor(commit=True) as (conn, c):
        if data.get("id"):
            c.execute(
                "UPDATE part_inventory SET part_code=%s, part_name=%s, stock=%s, "
                "min_stock=%s, unit=%s, location=%s, memo=%s WHERE id=%s AND tenant_id=%s",
                (data.get("part_code"), data.get("part_name"), int(data.get("stock") or 0),
                 int(data.get("min_stock") or 0), data.get("unit"), data.get("location"),
                 data.get("memo"), data["id"], tid),
            )
        else:
            c.execute(
                "INSERT INTO part_inventory (tenant_id, part_code, part_name, stock, "
                "min_stock, unit, location, memo) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (tid, data.get("part_code"), data.get("part_name"), int(data.get("stock") or 0),
                 int(data.get("min_stock") or 0), data.get("unit"), data.get("location"),
                 data.get("memo")),
            )
    log_audit("등록/수정", "부품", data.get("part_code", ""), data.get("part_name", ""))


def adjust_part_stock(part_id: int, delta: int):
    with db_cursor(commit=True) as (conn, c):
        c.execute(
            "UPDATE part_inventory SET stock=GREATEST(0, stock + %s) WHERE id=%s AND tenant_id=%s",
            (int(delta), part_id, _current_tenant()),
        )
    log_audit("입출고", "부품", part_id, f"{'+' if delta >= 0 else ''}{delta}")


@st.cache_data(ttl=120)
def _get_parts_q(tenant_id):
    with db_connection() as conn:
        return pd.read_sql_query(
            "SELECT id, part_code, part_name, stock, min_stock, unit, location, memo "
            "FROM part_inventory WHERE tenant_id=%s ORDER BY part_name, part_code",
            conn, params=[tenant_id],
        )


def get_parts():
    return _get_parts_q(_current_tenant())


def delete_part(part_id: int):
    with db_cursor(commit=True) as (conn, c):
        c.execute("DELETE FROM part_inventory WHERE id=%s AND tenant_id=%s",
                  (part_id, _current_tenant()))
    log_audit("삭제", "부품", part_id)


def get_low_stock_count() -> int:
    try:
        with db_cursor() as (conn, c):
            c.execute(
                "SELECT COUNT(*) FROM part_inventory WHERE tenant_id=%s "
                "AND min_stock > 0 AND stock <= min_stock",
                (_current_tenant(),),
            )
            return c.fetchone()[0] or 0
    except Exception:
        return 0





# ─────────── Excel Import ───────────
def import_from_excel(file_path: str) -> dict:
    results = {"equipment": 0, "maintenance": 0, "errors": []}
    tid = _current_tenant()
    try:
        xl = pd.ExcelFile(file_path)
        sheet_names = xl.sheet_names

        # Raw 설비리스트 import
        equip_sheet = next((s for s in sheet_names if "설비리스트" in s), None)
        if equip_sheet:
            df_eq = xl.parse(equip_sheet, header=0)
            df_eq.columns = [str(c).strip() for c in df_eq.columns]
            conn = get_conn()
            c = conn.cursor()
            for _, row in df_eq.iterrows():
                try:
                    factory = str(row.get("팩토리", row.iloc[0] if len(row) > 0 else "")).strip()
                    code = str(row.get("설비코드", row.iloc[1] if len(row) > 1 else "")).strip()
                    name = str(row.get("설비명", row.iloc[2] if len(row) > 2 else "")).strip()
                    if not code or code in ("nan", "설비코드"):
                        continue
                    c.execute(
                        "INSERT INTO equipment (factory,equipment_code,equipment_name,tenant_id) VALUES (%s,%s,%s,%s) ON CONFLICT (tenant_id, equipment_code) DO NOTHING",
                        (factory, code, name, tid),
                    )
                    results["equipment"] += 1
                except Exception as e:
                    results["errors"].append(f"설비: {e}")
            conn.commit()
            conn.close()

        # Raw 보전내역 import
        maint_sheet = next((s for s in sheet_names if "Raw 보전" in s or "보전내역" in s), None)
        if maint_sheet:
            df_m = xl.parse(maint_sheet, header=1)
            df_m.columns = [str(c).strip() for c in df_m.columns]
            conn_m = get_conn()
            for _, row in df_m.iterrows():
                try:
                    factory = str(row.get("팩토리", "")).split("주")[0].split("야")[0].strip()
                    if not factory or factory == "nan":
                        continue
                    recv_date_raw = row.get("발생일자", "")
                    recv_date = ""
                    if recv_date_raw and str(recv_date_raw) != "nan":
                        try:
                            if isinstance(recv_date_raw, (int, float)):
                                from datetime import date
                                import datetime as dt_mod
                                origin = dt_mod.datetime(1899, 12, 30)
                                recv_date = (origin + dt_mod.timedelta(days=int(recv_date_raw))).strftime("%Y-%m-%d")
                            else:
                                recv_date = pd.to_datetime(recv_date_raw).strftime("%Y-%m-%d")
                        except Exception:
                            recv_date = str(recv_date_raw)[:10]

                    comp_date_raw = row.get("조치 일자", row.get("조치일자", ""))
                    comp_date = ""
                    if comp_date_raw and str(comp_date_raw) != "nan":
                        try:
                            if isinstance(comp_date_raw, (int, float)):
                                from datetime import date
                                import datetime as dt_mod
                                origin = dt_mod.datetime(1899, 12, 30)
                                comp_date = (origin + dt_mod.timedelta(days=int(comp_date_raw))).strftime("%Y-%m-%d")
                            else:
                                comp_date = pd.to_datetime(comp_date_raw).strftime("%Y-%m-%d")
                        except Exception:
                            comp_date = str(comp_date_raw)[:10]

                    data = {
                        "factory": factory,
                        "shift": str(row.get("Shift", "")).strip(),
                        "status": str(row.get("진행 상태", "완료")).strip(),
                        "region": str(row.get("지역", "")).strip(),
                        "equipment_code": str(row.get("코드", "")).strip(),
                        "equipment_name": str(row.get("접수 대상", "")).strip(),
                        "issue_code": str(row.get("이슈 구분", "")).strip(),
                        "recv_date": recv_date,
                        "recv_hour": _safe_int(row.get("시", 0)),
                        "recv_min": _safe_int(row.get("분", 0)),
                        "comp_date": comp_date,
                        "comp_hour": _safe_int(row.get("시.1", 0)),
                        "comp_min": _safe_int(row.get("분.1", 0)),
                        "downtime_min": _safe_int(row.get("고장 시간(분)", 0)),
                        "loss_time": _safe_int(row.get("로스 시간", 0)),
                        "assignee": str(row.get("종결 담당자", "")).strip(),
                        "contractor_type": str(row.get("외주/자체", "")).strip(),
                        "recv_type": str(row.get("접수 구분", "")).strip(),
                        "issue_desc": str(row.get("이상 접수 내용", "")).strip(),
                        "root_cause": str(row.get("발생원인", "")).strip(),
                    }
                    insert_maintenance(data, conn=conn_m)
                    conn_m.commit()
                    results["maintenance"] += 1
                except Exception as e:
                    conn_m.rollback()
                    results["errors"].append(f"보전: {e}")
            conn_m.close()

    except Exception as e:
        results["errors"].append(str(e))

    if results["equipment"] or results["maintenance"]:
        log_audit("엑셀임포트", "데이터", "",
                  f"설비 {results['equipment']}건 · 보전 {results['maintenance']}건")

    return results


def _safe_int(val):
    try:
        return int(float(val)) if val and str(val) != "nan" else 0
    except Exception:
        return 0


# ─────────── 슬랙 연동 CRUD ───────────
def upsert_slack_request(data: dict) -> int:
    """슬랙 보전요청 저장 또는 갱신. 생성된/기존 id 반환."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_cursor(commit=True) as (conn, c):
        c.execute("""
            INSERT INTO slack_requests
                (channel_id, channel_name, message_ts, factory, equipment,
                 symptom, inspection, assignee, status, is_matched, recv_date, updated_at, tenant_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (channel_id, message_ts) DO UPDATE SET
                status = EXCLUDED.status,
                is_matched = EXCLUDED.is_matched,
                comp_date = CASE
                    WHEN EXCLUDED.status='완료' AND slack_requests.comp_date IS NULL
                    THEN EXCLUDED.recv_date
                    ELSE slack_requests.comp_date
                END,
                updated_at = EXCLUDED.updated_at
            RETURNING id
        """, (
            data["channel_id"], data.get("channel_name"), data["message_ts"],
            data.get("factory"), data.get("equipment"),
            data.get("symptom"), data.get("inspection"), data.get("assignee"),
            data.get("status", "진행 중"), data.get("is_matched", False),
            data.get("recv_date"), now, _current_tenant(),
        ))
        row = c.fetchone()
        return row[0] if row else None


def get_slack_last_ts(channel_id: str) -> str:
    """채널의 마지막 동기화 타임스탬프 반환. 없으면 '0'."""
    try:
        with db_cursor() as (conn, c):
            c.execute("SELECT last_ts FROM slack_sync_state WHERE channel_id=%s", (channel_id,))
            row = c.fetchone()
        return row[0] if row else "0"
    except Exception:
        return "0"


def save_slack_last_ts(channel_id: str, channel_name: str, last_ts: str):
    """채널의 마지막 동기화 타임스탬프 저장."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db_cursor(commit=True) as (conn, c):
        c.execute("""
            INSERT INTO slack_sync_state (channel_id, channel_name, last_ts, synced_at)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (channel_id) DO UPDATE SET
                last_ts = EXCLUDED.last_ts,
                synced_at = EXCLUDED.synced_at
        """, (channel_id, channel_name, last_ts, now))


def save_slack_unmatched(slack_request_id: int, factory_raw: str, equipment_raw: str,
                         channel_name: str, recv_date: str):
    """미매칭 데이터 저장 (중복 방지)."""
    with db_cursor(commit=True) as (conn, c):
        c.execute(
            "SELECT id FROM slack_unmatched WHERE slack_request_id=%s", (slack_request_id,)
        )
        if c.fetchone() is None:
            c.execute("""
                INSERT INTO slack_unmatched (slack_request_id, factory_raw, equipment_raw, channel_name, recv_date, tenant_id)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (slack_request_id, factory_raw, equipment_raw, channel_name, recv_date, _current_tenant()))


@st.cache_data(ttl=120)
def _get_slack_requests_q(tenant_id, status: str = None, channel_name: str = None) -> "pd.DataFrame":
    q = """
        SELECT id, channel_name, factory, equipment, symptom, inspection,
               assignee, status, is_matched, recv_date, comp_date, updated_at
        FROM slack_requests WHERE tenant_id=%s
    """
    params = [tenant_id]
    if status:
        q += " AND status=%s"
        params.append(status)
    if channel_name:
        q += " AND channel_name ILIKE %s"
        params.append(f"%{channel_name}%")
    q += " ORDER BY recv_date DESC, id DESC LIMIT 500"
    with db_connection() as conn:
        return pd.read_sql_query(q, conn, params=params)


def get_slack_requests(status: str = None, channel_name: str = None) -> "pd.DataFrame":
    return _get_slack_requests_q(_current_tenant(), status, channel_name)


@st.cache_data(ttl=120)
def _get_slack_unmatched_q(tenant_id) -> "pd.DataFrame":
    with db_connection() as conn:
        return pd.read_sql_query(
            """SELECT su.recv_date, su.channel_name, su.factory_raw, su.equipment_raw,
                      sr.symptom, sr.status as req_status
               FROM slack_unmatched su
               LEFT JOIN slack_requests sr ON su.slack_request_id = sr.id
               WHERE su.tenant_id=%s
               ORDER BY su.created_at DESC LIMIT 200""",
            conn, params=[tenant_id],
        )


def get_slack_unmatched() -> "pd.DataFrame":
    return _get_slack_unmatched_q(_current_tenant())


# ─────────── 데이터 초기화 ───────────
def clear_maintenance():
    """보전내역만 삭제하고 설비 상태를 정상으로 복구 (현재 테넌트 범위)."""
    tid = _current_tenant()
    with db_cursor(commit=True) as (conn, c):
        c.execute("DELETE FROM maintenance WHERE tenant_id=%s", (tid,))
        c.execute("UPDATE equipment SET status='정상' WHERE tenant_id=%s", (tid,))
    log_audit("초기화", "보전내역", "", "보전내역 전체 삭제")


def clear_all_data():
    """현재 테넌트의 운영 데이터 초기화 (보전내역·설비·슬랙 수집 데이터)."""
    tid = _current_tenant()
    with db_cursor(commit=True) as (conn, c):
        c.execute("DELETE FROM slack_unmatched WHERE tenant_id=%s", (tid,))
        c.execute("DELETE FROM slack_requests WHERE tenant_id=%s", (tid,))
        c.execute("DELETE FROM maintenance WHERE tenant_id=%s", (tid,))
        c.execute("DELETE FROM equipment WHERE tenant_id=%s", (tid,))
    log_audit("전체초기화", "데이터", "", "보전내역·설비·슬랙 전체 삭제")


# ─────────── 작업일지 CRUD ───────────
def add_work_log(data: dict):
    """작업일지 기록 추가."""
    with db_cursor(commit=True) as (conn, c):
        c.execute("""
            INSERT INTO work_log (log_date, author, factory, category, title, content, tenant_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            data.get("log_date"), data.get("author"), data.get("factory"),
            data.get("category"), data.get("title"), data.get("content"), _current_tenant(),
        ))
    log_audit("작성", "작업일지", "", (data.get("title") or "")[:50])


@st.cache_data(ttl=300)
def _get_work_logs_q(tenant_id, year=None, month=None, author=None, factory=None):
    q = "SELECT id, log_date, author, factory, category, title, content FROM work_log WHERE tenant_id=%s"
    params = [tenant_id]
    if year:
        q += " AND log_date LIKE %s"
        params.append(f"{int(year):04d}-%")
    if month:
        q += " AND log_date LIKE %s"
        params.append(f"%-{int(month):02d}-%")
    if author:
        q += " AND author ILIKE %s"
        params.append(f"%{author}%")
    if factory:
        q += " AND factory=%s"
        params.append(factory)
    q += " ORDER BY log_date DESC, id DESC LIMIT 1000"
    with db_connection() as conn:
        return pd.read_sql_query(q, conn, params=params)


def get_work_logs(year=None, month=None, author=None, factory=None):
    """작업일지 조회. 컴럼은 ASCII로 반환."""
    return _get_work_logs_q(_current_tenant(), year, month, author, factory)


def delete_work_log(log_id: int):
    """작업일지 삭제."""
    with db_cursor(commit=True) as (conn, c):
        c.execute("DELETE FROM work_log WHERE id=%s AND tenant_id=%s", (log_id, _current_tenant()))
    log_audit("삭제", "작업일지", log_id)


# ─────────── 사용자 계정 CRUD ───────────
def verify_login(username: str, password: str):
    """로그인 검증. 성공 시 사용자 dict, 실패 시 None."""
    with db_cursor() as (conn, c):
        c.execute(
            "SELECT id, username, password_hash, display_name, role, tenant_id, is_active "
            "FROM app_user WHERE username=%s",
            (username,),
        )
        row = c.fetchone()
    if not row or not row[6]:  # 없거나 비활성
        return None
    if not verify_password(password, row[2]):
        return None
    try:
        with db_cursor(commit=True) as (conn, c):
            c.execute("UPDATE app_user SET last_login=NOW() WHERE id=%s", (row[0],))
    except Exception:
        pass
    return {"id": row[0], "username": row[1], "display_name": row[3],
            "role": row[4], "tenant_id": row[5]}


def get_user_by_id(user_id: int):
    """id로 활성 사용자 조회 (쿠키 세션 복원용). 없거나 비활성이면 None."""
    with db_cursor() as (conn, c):
        c.execute(
            "SELECT id, username, display_name, role, tenant_id, is_active "
            "FROM app_user WHERE id=%s",
            (user_id,),
        )
        row = c.fetchone()
    if not row or not row[5]:
        return None
    return {"id": row[0], "username": row[1], "display_name": row[2],
            "role": row[3], "tenant_id": row[4]}


def list_users(tenant_id=None):
    q = ("SELECT id, username, display_name, role, tenant_id, is_active, last_login, created_at "
         "FROM app_user")
    params = []
    if tenant_id:
        q += " WHERE tenant_id=%s"
        params.append(tenant_id)
    q += " ORDER BY role, username"
    with db_connection() as conn:
        return pd.read_sql_query(q, conn, params=params if params else None)


def create_user(username: str, password: str, display_name: str,
                role: str = "user", tenant_id: int = 1, created_by: str = "") -> bool:
    """계정 생성. 중복 아이디면 False."""
    with db_cursor(commit=True) as (conn, c):
        c.execute("SELECT 1 FROM app_user WHERE username=%s", (username,))
        if c.fetchone():
            return False
        c.execute(
            "INSERT INTO app_user (username, password_hash, display_name, role, tenant_id, created_by) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (username, hash_password(password), display_name, role, tenant_id, created_by),
        )
        log_audit("계정생성", "계정", username, f"권한={role}")
        return True


def delete_user(user_id: int):
    """계정 삭제 (최고관리자는 삭제 불가)."""
    with db_cursor(commit=True) as (conn, c):
        c.execute("DELETE FROM app_user WHERE id=%s AND role<>'superadmin'", (user_id,))
    log_audit("계정삭제", "계정", user_id)


def reset_user_password(user_id: int, new_password: str):
    """비밀번호 초기화."""
    with db_cursor(commit=True) as (conn, c):
        c.execute("UPDATE app_user SET password_hash=%s WHERE id=%s",
                  (hash_password(new_password), user_id))


def set_user_active(user_id: int, active: bool):
    """계정 활성/비활성 (최고관리자는 변경 불가)."""
    with db_cursor(commit=True) as (conn, c):
        c.execute("UPDATE app_user SET is_active=%s WHERE id=%s AND role<>'superadmin'",
                  (active, user_id))


def change_own_password(user_id: int, old_password: str, new_password: str) -> bool:
    """본인 비밀번호 변경. 기존 비번이 맞아야 True."""
    with db_cursor() as (conn, c):
        c.execute("SELECT password_hash FROM app_user WHERE id=%s", (user_id,))
        row = c.fetchone()
    if not row or not verify_password(old_password, row[0]):
        return False
    with db_cursor(commit=True) as (conn, c):
        c.execute("UPDATE app_user SET password_hash=%s WHERE id=%s",
                  (hash_password(new_password), user_id))
    return True


def set_user_tenant(user_id: int, tenant_id: int):
    """사용자를 특정 테넌트(회사)에 배정 (최고관리자 제외)."""
    with db_cursor(commit=True) as (conn, c):
        c.execute("UPDATE app_user SET tenant_id=%s WHERE id=%s AND role<>'superadmin'",
                  (tenant_id, user_id))


# ─────────── 테넌트(회사) CRUD ───────────
def list_tenants():
    with db_connection() as conn:
        return pd.read_sql_query(
            "SELECT t.id, t.name, t.created_at, "
            "(SELECT COUNT(*) FROM app_user u WHERE u.tenant_id=t.id) AS user_count "
            "FROM tenant t ORDER BY t.id",
            conn,
        )


def create_tenant(name: str) -> bool:
    """회사(테넌트) 생성. 중복 이름이면 False."""
    with db_cursor(commit=True) as (conn, c):
        c.execute("SELECT 1 FROM tenant WHERE name=%s", (name,))
        if c.fetchone():
            return False
        c.execute("INSERT INTO tenant (name) VALUES (%s)", (name,))
        return True


# ─────────── 감사 로그 ───────────
def _current_actor() -> str:
    try:
        u = st.session_state.get("auth_user")
        if u:
            return u.get("username") or "-"
    except Exception:
        pass
    return "system"


def log_audit(action: str, entity: str, entity_id="", detail: str = ""):
    """감사 로그 1건 기록. 실패해도 본작업에 영향 주지 않도록 조용히 무시."""
    try:
        with db_cursor(commit=True) as (conn, c):
            c.execute(
                "INSERT INTO audit_log (tenant_id, actor, action, entity, entity_id, detail) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (_current_tenant(), _current_actor(), action, entity, str(entity_id), detail[:500]),
            )
    except Exception:
        pass


@st.cache_data(ttl=60)
def _get_audit_logs_q(tenant_id, limit=300):
    with db_connection() as conn:
        return pd.read_sql_query(
            "SELECT created_at, actor, action, entity, entity_id, detail "
            "FROM audit_log WHERE tenant_id=%s ORDER BY id DESC LIMIT %s",
            conn, params=[tenant_id, limit],
        )


def get_audit_logs(limit=300):
    return _get_audit_logs_q(_current_tenant(), limit)


