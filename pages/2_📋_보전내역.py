import streamlit as st
import sys, os
import html
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import (
    get_maintenance, insert_maintenance, update_maintenance, delete_maintenance,
    get_equipment, get_issue_code_options, get_issue_codes, get_available_years, init_db
)
from utils.constants import FACTORIES, MAINTENANCE_STATUS_LIST as STATUS_LIST, SHIFT_LIST, RECV_TYPE_LIST, CONTRACTOR_LIST
from utils.style import inject_css, page_header, kpi_cards, status_badge
import pandas as pd
from datetime import datetime, date

init_db()

inject_css()

page_header("📋 보전내역 관리", "보전 작업 등록 · 조회 · 수정 · 삭제")


@st.dialog("보전내역 수정 · 삭제", width="large")
def maintenance_edit_dialog(row, edit_id):
    st.caption(f"ID {edit_id} · {row['equipment_code'] or '-'} · {row['equipment_name'] or ''}")
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        e_factory = st.selectbox("팩토리", FACTORIES,
            index=FACTORIES.index(row["factory"]) if row["factory"] in FACTORIES else 0)
        e_shift = st.selectbox("Shift", SHIFT_LIST,
            index=SHIFT_LIST.index(row["shift"]) if row["shift"] in SHIFT_LIST else 0)
        e_status = st.selectbox("진행상태", STATUS_LIST,
            index=STATUS_LIST.index(row["status"]) if row["status"] in STATUS_LIST else 0)
    with ec2:
        e_eq_code = st.text_input("설비코드", value=row["equipment_code"] or "")
        e_eq_name = st.text_input("설비명", value=row["equipment_name"] or "")
        issue_opts = get_issue_code_options()
        e_issue = st.selectbox("이슈코드", [""] + issue_opts,
            index=([""] + issue_opts).index(row["issue_code"]) if row["issue_code"] in issue_opts else 0)
    with ec3:
        e_comp_date = st.date_input("조치일자",
            value=pd.to_datetime(row["comp_date"]).date() if row["comp_date"] else date.today())
        e_downtime = st.number_input("고장시간(분)", value=int(row["downtime_min"] or 0), min_value=0)
        e_assignee = st.text_input("담당자", value=row["assignee"] or "")

    e_issue_desc = st.text_area("이상 접수 내용", value=row["issue_desc"] or "", height=80)
    e_root_cause = st.text_area("발생원인", value=row["root_cause"] or "", height=80)
    e_slack = st.text_input("슬랙 링크", value=row["slack_link"] or "")

    sb1, sb2 = st.columns(2)
    with sb1:
        if st.button("💾 저장", use_container_width=True, type="primary"):
            update_maintenance(edit_id, {
                "factory": e_factory, "shift": e_shift, "status": e_status,
                "equipment_code": e_eq_code, "equipment_name": e_eq_name,
                "issue_code": e_issue,
                "comp_date": str(e_comp_date),
                "downtime_min": e_downtime, "assignee": e_assignee,
                "issue_desc": e_issue_desc, "root_cause": e_root_cause,
                "slack_link": e_slack,
            })
            st.cache_data.clear()
            st.rerun()
    with sb2:
        if st.button("🗑️ 삭제", use_container_width=True):
            delete_maintenance(edit_id)
            st.cache_data.clear()
            st.rerun()


# ─── 탭 ───
tab1, tab2 = st.tabs(["📋 목록 조회", "➕ 신규 등록"])

# ══════════════════════════════
# 탭1: 목록 조회
# ══════════════════════════════
with tab1:
    # 필터
    fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 2, 2, 1])
    with fc1:
        f_factory = st.selectbox("팩토리", ["전체"] + FACTORIES, key="f_fac")
    with fc2:
        f_status = st.selectbox("진행상태", ["전체"] + STATUS_LIST, key="f_st")
    with fc3:
        f_year = st.selectbox("연도", ["전체"] + get_available_years(), key="f_yr")
    with fc4:
        f_month = st.selectbox("월", ["전체"] + list(range(1, 13)), key="f_mo")
    with fc5:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_search = st.button("🔍 조회", use_container_width=True)

    df = get_maintenance(
        factory=None if f_factory == "전체" else f_factory,
        status=None if f_status == "전체" else f_status,
        year=None if f_year == "전체" else f_year,
        month=None if f_month == "전체" else f_month,
    )

    # KPI 요약
    if not df.empty:
        total = len(df)
        done = len(df[df["status"] == "완료"])
        pending = len(df[df["status"].isin(["진행 중", "팬딩"])])
        rate = round(done / total * 100, 1) if total else 0
        kpi_cards([
            {"label": "총 건수",  "value": f"{total:,}건", "icon": "📦", "color": "blue",   "sub": "전체 접수"},
            {"label": "완료",    "value": f"{done:,}건",  "icon": "✅", "color": "green",  "sub": "처리 완료"},
            {"label": "미완료",  "value": f"{pending:,}건","icon": "⏳", "color": "amber",  "sub": "진행 중 + 팬딩"},
            {"label": "처리율",  "value": f"{rate}%",     "icon": "📈", "color": "purple", "sub": "목표 95%"},
        ])

    if df.empty:
        st.info("조회된 데이터가 없습니다.")
    else:
        df = df.reset_index(drop=True)

        PAGE_SIZE = 15
        total_rows = len(df)
        total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)
        pc1, pc2 = st.columns([3, 1])
        with pc2:
            page = st.number_input("페이지", min_value=1, max_value=total_pages,
                                   value=1, step=1, key="rec_page")
        start = (int(page) - 1) * PAGE_SIZE
        df_page = df.iloc[start:start + PAGE_SIZE]
        with pc1:
            st.caption(f"총 {total_rows:,}건 중 {start + 1:,}–{min(start + PAGE_SIZE, total_rows):,}건  ·  {int(page)}/{total_pages} 페이지")

        _BORDER = {"완료": "#2FA37A", "진행 중": "#C98A18", "팬딩": "#9C978C",
                   "고장": "#D6485B", "취소": "#9C978C"}
        cards = '<div class="rec-scroll">'
        for i, row in df_page.iterrows():
            seq = i + 1
            status = str(row.get("status") or "")
            color = _BORDER.get(status, "#6E62E6")
            name = html.escape(str(row.get("equipment_name") or "-"))
            code = html.escape(str(row.get("equipment_code") or ""))
            fac = html.escape(str(row.get("factory") or ""))
            issue = html.escape(str(row.get("issue_code") or "-"))
            recv = html.escape(str(row.get("recv_date") or "-"))
            comp = html.escape(str(row.get("comp_date") or ""))
            down = row.get("downtime_min") or 0
            assignee = html.escape(str(row.get("assignee") or ""))
            desc = html.escape(str(row.get("issue_desc") or "").strip())

            meta = f'<span>🏷️ <b>{issue}</b></span><span>📅 발생 {recv}</span>'
            if comp:
                meta += f'<span>✅ 조치 {comp}</span>'
            if down:
                meta += f'<span>⏱️ <b>{int(down)}</b>분</span>'
            if assignee:
                meta += f'<span>👤 {assignee}</span>'
            desc_html = f'<div class="rec-desc">{desc}</div>' if desc else ''
            cards += (
                f'<div class="rec-card" style="border-left-color:{color}">'
                f'<div class="rec-top"><span class="rec-seq">#{seq}</span>'
                f'<span class="rec-name">{name}</span><span class="rec-sub">{code}</span>'
                f'{status_badge(status)}<span class="rec-spacer"></span>'
                f'<span class="rec-fac">{fac}</span></div>'
                f'<div class="rec-meta">{meta}</div>{desc_html}</div>'
            )
        cards += '</div>'
        st.markdown(cards, unsafe_allow_html=True)

        # 다운로드
        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ Excel 다운로드 (CSV)",
            data=csv,
            file_name=f"보전내역_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

        st.markdown("---")
        st.markdown("##### ✏️ 수정 / 삭제")
        esc1, esc2 = st.columns([1, 3])
        with esc1:
            edit_seq = st.number_input("순번 선택", min_value=1, max_value=len(df), step=1, key="edit_id")
        with esc2:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("✏️ 선택 항목 수정 / 삭제 열기", type="primary"):
                row = df.iloc[int(edit_seq) - 1]
                maintenance_edit_dialog(row, int(row["id"]))

# ══════════════════════════════
# 탭2: 신규 등록
# ══════════════════════════════
with tab2:
    st.subheader("➕ 보전 작업 신규 등록")

    df_eq = get_equipment()
    df_ic = get_issue_codes()

    # ── STEP 1 & 2: 폼 밖에서 실시간 연동 선택 ──
    st.markdown("#### 🔍 STEP 1 · 설비 선택")
    s1c1, s1c2 = st.columns(2)
    with s1c1:
        pre_factory = st.selectbox("① 팩토리", FACTORIES, key="pre_factory")
    with s1c2:
        if not df_eq.empty:
            df_eq_f = df_eq[df_eq["factory"] == pre_factory].copy()
            # 설비명 (설비코드) 형태로 표시
            df_eq_f["_display"] = df_eq_f["equipment_name"] + "  (" + df_eq_f["equipment_code"] + ")"
            eq_display_opts = df_eq_f["_display"].tolist() + ["직접입력"]
        else:
            df_eq_f = pd.DataFrame()
            eq_display_opts = ["직접입력"]
        pre_eq_disp = st.selectbox(
            f"② 설비 선택 ({pre_factory} 설비 {len(eq_display_opts)-1}개)",
            eq_display_opts, key="pre_eq"
        )

    if pre_eq_disp != "직접입력" and not df_eq_f.empty:
        eq_row = df_eq_f[df_eq_f["_display"] == pre_eq_disp]
        pre_eq_code_val = eq_row["equipment_code"].values[0] if not eq_row.empty else ""
        pre_eq_name = eq_row["equipment_name"].values[0] if not eq_row.empty else ""
        pre_location = eq_row["location"].values[0] if not eq_row.empty and "location" in eq_row.columns else ""
        st.info(f"📌 **{pre_eq_code_val}** · {pre_eq_name}" + (f"  |  위치: {pre_location}" if pre_location else ""))
        pre_eq_name_val = pre_eq_name
    else:
        pre_eq_code_val = ""
        pre_eq_name_val = ""

    st.markdown("#### 🏷️ STEP 2 · 이슈 선택")
    s2c1, s2c2 = st.columns(2)
    with s2c1:
        if not df_ic.empty:
            part_opts = ["선택"] + sorted(df_ic["part_name"].unique().tolist())
        else:
            part_opts = ["선택"]
        pre_part = st.selectbox("③ 부품명", part_opts, key="pre_part")

    with s2c2:
        if pre_part != "선택" and not df_ic.empty:
            issues_f = df_ic[df_ic["part_name"] == pre_part]
            issue_display = issues_f.apply(
                lambda r: f"{r['full_code']}  ·  {r['issue_name']}", axis=1
            ).tolist()
            pre_issue_disp = st.selectbox(
                f"④ 이슈 선택 ({len(issue_display)}개)",
                ["선택"] + issue_display, key="pre_issue"
            )
            pre_issue_val = pre_issue_disp.split("  ·  ")[0] if pre_issue_disp != "선택" else ""
        else:
            st.selectbox("④ 이슈 선택", ["← 부품명을 먼저 선택하세요"], disabled=True, key="pre_issue_dis")
            pre_issue_val = ""

    if pre_issue_val:
        st.success(f"✅ 선택된 이슈코드: **{pre_issue_val}**")

    st.markdown("---")
    st.markdown("#### 📝 STEP 3 · 상세 정보 입력")

    # ── STEP 3: 폼 ──
    with st.form("new_form", clear_on_submit=True):
        nc1, nc2, nc3 = st.columns(3)

        with nc1:
            st.markdown("**📍 기본 정보**")
            n_factory = st.selectbox("팩토리 *", FACTORIES,
                index=FACTORIES.index(pre_factory) if pre_factory in FACTORIES else 0)
            n_recv_type = st.selectbox("접수 구분", RECV_TYPE_LIST)
            n_contractor = st.selectbox("외주/자체", CONTRACTOR_LIST)
            n_assignee = st.text_input("담당자")

        with nc2:
            st.markdown("**🔩 설비 · 이슈 확인**")
            st.info(f"설비: **{pre_eq_code_val or '미선택'}** {pre_eq_name_val}\n\n이슈: **{pre_issue_val or '미선택'}**")
            n_eq_code = pre_eq_code_val
            n_eq_name = pre_eq_name_val
            n_issue = pre_issue_val
            n_shift = st.selectbox("Shift", SHIFT_LIST)

        with nc3:
            st.markdown("**📅 일시 정보**")
            n_recv_date = st.date_input("발생일자 *", value=date.today())
            nc3a, nc3b = st.columns(2)
            with nc3a:
                n_recv_hour = st.number_input("발생 시", min_value=0, max_value=23, value=8)
            with nc3b:
                n_recv_min = st.number_input("발생 분", min_value=0, max_value=59, value=0)
            n_status = st.selectbox("진행상태", STATUS_LIST)
            n_comp_date = st.date_input("조치일자", value=date.today())
            nc3c, nc3d = st.columns(2)
            with nc3c:
                n_comp_hour = st.number_input("조치 시", min_value=0, max_value=23, value=8)
            with nc3d:
                n_comp_min = st.number_input("조치 분", min_value=0, max_value=59, value=0)

        n_downtime = st.number_input("고장시간 (분)", min_value=0, value=0)
        n_issue_desc = st.text_area("이상 접수 내용 *", height=80, placeholder="발생한 이상 내용을 입력하세요")
        n_root_cause = st.text_area("발생원인", height=80, placeholder="원인 분석 내용")
        n_slack = st.text_input("슬랙 링크", placeholder="https://...")

        submitted = st.form_submit_button("💾 등록", use_container_width=True, type="primary")

    if submitted:
        if not n_eq_code or not n_issue_desc:
            st.error("설비코드와 이상 접수 내용은 필수입니다.")
        else:
            insert_maintenance({
                "factory": n_factory, "shift": n_shift, "status": n_status,
                "region": n_factory, "equipment_code": n_eq_code, "equipment_name": n_eq_name,
                "issue_code": n_issue,
                "recv_date": str(n_recv_date), "recv_hour": n_recv_hour, "recv_min": n_recv_min,
                "comp_date": str(n_comp_date) if n_status == "완료" else "",
                "comp_hour": n_comp_hour, "comp_min": n_comp_min,
                "downtime_min": n_downtime,
                "assignee": n_assignee, "contractor_type": n_contractor,
                "recv_type": n_recv_type, "issue_desc": n_issue_desc,
                "root_cause": n_root_cause, "slack_link": n_slack,
            })
            st.success("✅ 보전 작업이 등록되었습니다!")
            st.cache_data.clear()
            st.balloons()

