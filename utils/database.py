import os
import psycopg2
import pandas as pd
from datetime import datetime

try:
    import streamlit as st
    DATABASE_URL = st.secrets["DATABASE_URL"]
except Exception:
    DATABASE_URL = os.environ.get("DATABASE_URL", "")


def get_conn():
    url = DATABASE_URL
    if url and "sslmode" not in url:
        url += "?sslmode=require"
    return psycopg2.connect(url)


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

    conn.commit()
    _seed_issue_codes(c, conn)
    _seed_holidays_2026(c, conn)
    conn.close()


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
def get_equipment(factory=None, status=None):
    conn = get_conn()
    q = "SELECT * FROM equipment WHERE 1=1"
    params = []
    if factory:
        q += " AND factory=%s"
        params.append(factory)
    if status:
        q += " AND status=%s"
        params.append(status)
    q += " ORDER BY factory, equipment_code"
    df = pd.read_sql_query(q, conn, params=params if params else None)
    conn.close()
    return df


def upsert_equipment(data: dict):
    conn = get_conn()
    c = conn.cursor()
    if data.get("id"):
        c.execute("""
            UPDATE equipment SET factory=%s,equipment_code=%s,equipment_name=%s,
            location=%s,category=%s,status=%s,install_date=%s,memo=%s
            WHERE id=%s
        """, (data["factory"], data["equipment_code"], data["equipment_name"],
              data.get("location"), data.get("category"), data.get("status","정상"),
              data.get("install_date"), data.get("memo"), data["id"]))
    else:
        c.execute("""
            INSERT INTO equipment (factory,equipment_code,equipment_name,location,category,status,install_date,memo)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (data["factory"], data["equipment_code"], data["equipment_name"],
              data.get("location"), data.get("category"), data.get("status","정상"),
              data.get("install_date"), data.get("memo")))
    conn.commit()
    conn.close()


def delete_equipment(eq_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM equipment WHERE id=%s", (eq_id,))
    conn.commit()
    conn.close()


# ─────────── 보전내역 CRUD ───────────
def get_maintenance(factory=None, status=None, year=None, month=None, week=None):
    conn = get_conn()
    q = "SELECT * FROM maintenance WHERE 1=1"
    params = []
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
    df = pd.read_sql_query(q, conn, params=params if params else None)
    conn.close()
    return df


def insert_maintenance(data: dict, conn=None):
    own = conn is None
    if own:
        conn = get_conn()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            created_at, updated_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
        now, now
    ))
    eq_code = data.get("equipment_code")
    status = data.get("status", "진행 중")
    if eq_code:
        _sync_equipment_status(conn, eq_code, status, commit=False)
    if own:
        conn.commit()
        conn.close()


def _sync_equipment_status(conn, equipment_code: str, maint_status: str, commit: bool = True):
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
    c.execute("UPDATE equipment SET status=%s WHERE equipment_code=%s", (eq_status, equipment_code))
    if commit:
        conn.commit()


def update_maintenance(m_id: int, data: dict):
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
        UPDATE maintenance SET
            factory=%s, shift=%s, status=%s, region=%s, equipment_code=%s, equipment_name=%s,
            issue_code=%s, comp_year=%s, comp_month=%s, comp_week=%s,
            comp_date=%s, comp_hour=%s, comp_min=%s,
            downtime_min=%s, loss_time=%s, assignee=%s, contractor_type=%s,
            recv_type=%s, issue_desc=%s, root_cause=%s, slack_link=%s, updated_at=%s
        WHERE id=%s
    """, (
        data.get("factory"), data.get("shift"), data.get("status"),
        data.get("region"), data.get("equipment_code"), data.get("equipment_name"),
        data.get("issue_code"),
        comp_year, comp_month, comp_week,
        comp_date, data.get("comp_hour"), data.get("comp_min"),
        data.get("downtime_min", 0), data.get("loss_time", 0),
        data.get("assignee"), data.get("contractor_type"),
        data.get("recv_type"), data.get("issue_desc"), data.get("root_cause"),
        data.get("slack_link"), now, m_id
    ))
    conn.commit()
    eq_code = data.get("equipment_code")
    status = data.get("status")
    if eq_code and status:
        _sync_equipment_status(conn, eq_code, status)
    conn.close()


def delete_maintenance(m_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM maintenance WHERE id=%s", (m_id,))
    conn.commit()
    conn.close()


# ─────────── 이슈코드 조회 ───────────
def get_issue_codes():
    conn = get_conn()
    df = pd.read_sql_query("SELECT DISTINCT full_code, part_name, issue_name FROM issue_code ORDER BY full_code", conn)
    conn.close()
    return df


def get_issue_code_options():
    df = get_issue_codes()
    return df["full_code"].tolist()


# ─────────── 통계 쿼리 ───────────
def get_kpi(year=None):
    conn = get_conn()
    c = conn.cursor()
    if year:
        where = "WHERE recv_year=%s"
        params = (year,)
    else:
        where = ""
        params = ()
    c.execute(f"""
        SELECT
            COUNT(*),
            COUNT(*) FILTER (WHERE status='완료'),
            COUNT(*) FILTER (WHERE status IN ('진행 중','팬딩')),
            AVG(downtime_min) FILTER (WHERE downtime_min > 0)
        FROM maintenance {where}
    """, params)
    total, done, pending, avg_down = c.fetchone()
    conn.close()
    rate = round(done / total * 100, 1) if total else 0
    return {
        "total": total,
        "done": done,
        "pending": pending,
        "rate": rate,
        "avg_down": round(avg_down, 1) if avg_down else 0,
    }


def get_monthly_count(year=None):
    conn = get_conn()
    if year:
        where = "WHERE recv_year=%s"
        params = [year]
    else:
        where = ""
        params = []
    df = pd.read_sql_query(
        f"SELECT recv_month as 월, COUNT(*) as 건수 FROM maintenance {where} GROUP BY recv_month ORDER BY recv_month",
        conn,
        params=params if params else None,
    )
    conn.close()
    return df


def get_factory_count(year=None):
    conn = get_conn()
    if year:
        where = "WHERE recv_year=%s"
        params = [year]
    else:
        where = ""
        params = []
    df = pd.read_sql_query(
        f"SELECT factory as 팩토리, COUNT(*) as 건수 FROM maintenance {where} GROUP BY factory ORDER BY 건수 DESC",
        conn,
        params=params if params else None,
    )
    conn.close()
    return df


def get_issue_top(year=None, limit=15):
    conn = get_conn()
    if year:
        where = "WHERE recv_year=%s AND"
        params = [year]
    else:
        where = "WHERE"
        params = []
    df = pd.read_sql_query(
        f"SELECT issue_code as 이슈코드, COUNT(*) as 건수 FROM maintenance {where} issue_code IS NOT NULL GROUP BY issue_code ORDER BY 건수 DESC LIMIT {limit}",
        conn,
        params=params if params else None,
    )
    conn.close()
    return df


def get_weekly_pivot(year=None, factory=None):
    conn = get_conn()
    where_parts = []
    params = []
    if year:
        where_parts.append("recv_year=%s")
        params.append(year)
    if factory:
        where_parts.append("factory=%s")
        params.append(factory)
    where = "WHERE " + " AND ".join(where_parts) if where_parts else ""
    df = pd.read_sql_query(
        f"""SELECT factory, equipment_code, equipment_name, recv_week, COUNT(*) as cnt
            FROM maintenance {where}
            GROUP BY factory, equipment_code, equipment_name, recv_week
            ORDER BY factory, equipment_code, recv_week""",
        conn,
        params=params if params else None,
    )
    conn.close()
    return df


def get_overdue(days=30):
    conn = get_conn()
    df = pd.read_sql_query(
        """SELECT id, factory, equipment_code, equipment_name, recv_date, status, issue_desc,
            (CURRENT_DATE - recv_date::date)::INTEGER as 경과일수
            FROM maintenance
            WHERE status IN ('진행 중','팬딩')
            AND recv_date IS NOT NULL
            AND recv_date != ''
            AND (CURRENT_DATE - recv_date::date)::INTEGER >= %s
            ORDER BY 경과일수 DESC""",
        conn,
        params=[days],
    )
    conn.close()
    return df


# ─────────── Excel Import ───────────
def import_from_excel(file_path: str) -> dict:
    results = {"equipment": 0, "maintenance": 0, "errors": []}
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
                        "INSERT INTO equipment (factory,equipment_code,equipment_name) VALUES (%s,%s,%s) ON CONFLICT (equipment_code) DO NOTHING",
                        (factory, code, name),
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

    return results


def _safe_int(val):
    try:
        return int(float(val)) if val and str(val) != "nan" else 0
    except Exception:
        return 0


# ─────────── 슬랙 연동 CRUD ───────────
def upsert_slack_request(data: dict) -> int:
    """슬랙 보전요청 저장 또는 갱신. 생성된/기존 id 반환."""
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO slack_requests
            (channel_id, channel_name, message_ts, factory, equipment,
             symptom, inspection, assignee, status, is_matched, recv_date, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
        data.get("recv_date"), now,
    ))
    row = c.fetchone()
    req_id = row[0] if row else None
    conn.commit()
    conn.close()
    return req_id


def get_slack_last_ts(channel_id: str) -> str:
    """채널의 마지막 동기화 타임스탬프 반환. 없으면 '0'."""
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT last_ts FROM slack_sync_state WHERE channel_id=%s", (channel_id,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else "0"
    except Exception:
        return "0"


def save_slack_last_ts(channel_id: str, channel_name: str, last_ts: str):
    """채널의 마지막 동기화 타임스탬프 저장."""
    conn = get_conn()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO slack_sync_state (channel_id, channel_name, last_ts, synced_at)
        VALUES (%s,%s,%s,%s)
        ON CONFLICT (channel_id) DO UPDATE SET
            last_ts = EXCLUDED.last_ts,
            synced_at = EXCLUDED.synced_at
    """, (channel_id, channel_name, last_ts, now))
    conn.commit()
    conn.close()


def save_slack_unmatched(slack_request_id: int, factory_raw: str, equipment_raw: str,
                         channel_name: str, recv_date: str):
    """미매칭 데이터 저장 (중복 방지)."""
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM slack_unmatched WHERE slack_request_id=%s", (slack_request_id,)
    )
    if c.fetchone() is None:
        c.execute("""
            INSERT INTO slack_unmatched (slack_request_id, factory_raw, equipment_raw, channel_name, recv_date)
            VALUES (%s,%s,%s,%s,%s)
        """, (slack_request_id, factory_raw, equipment_raw, channel_name, recv_date))
        conn.commit()
    conn.close()


@st.cache_data(ttl=120)
def get_slack_requests(status: str = None, channel_name: str = None) -> "pd.DataFrame":
    conn = get_conn()
    q = """
        SELECT id, channel_name, factory, equipment, symptom, inspection,
               assignee, status, is_matched, recv_date, comp_date, updated_at
        FROM slack_requests WHERE 1=1
    """
    params = []
    if status:
        q += " AND status=%s"
        params.append(status)
    if channel_name:
        q += " AND channel_name ILIKE %s"
        params.append(f"%{channel_name}%")
    q += " ORDER BY recv_date DESC, id DESC LIMIT 500"
    df = pd.read_sql_query(q, conn, params=params if params else None)
    conn.close()
    return df


@st.cache_data(ttl=120)
def get_slack_unmatched() -> "pd.DataFrame":
    conn = get_conn()
    df = pd.read_sql_query(
        """SELECT su.recv_date, su.channel_name, su.factory_raw, su.equipment_raw,
                  sr.symptom, sr.status as req_status
           FROM slack_unmatched su
           LEFT JOIN slack_requests sr ON su.slack_request_id = sr.id
           ORDER BY su.created_at DESC LIMIT 200""",
        conn,
    )
    conn.close()
    return df
