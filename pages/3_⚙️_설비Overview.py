import streamlit as st
import sys, os
import html
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import (
    get_equipment, upsert_equipment, delete_equipment, init_db,
    get_equipment_history, get_equipment_stats,
)
from utils.constants import FACTORIES, EQUIPMENT_STATUS_LIST as STATUS_LIST, CATEGORY_LIST
from utils.style import inject_css, page_header, kpi_cards, status_badge, flash, render_flash
import pandas as pd
from datetime import date

init_db()

inject_css()
render_flash()

page_header("⚙️ 설비 Overview", "설비 상태 현황 · 등록 · 수정")


@st.dialog("설비 수정 · 삭제", width="large")
def equipment_edit_dialog(row):
    st.caption(f"{row['equipment_code']} · {row['equipment_name']} ({row['factory']})")
    ec1, ec2 = st.columns(2)
    with ec1:
        e_fac = st.selectbox("팩토리", FACTORIES,
            index=FACTORIES.index(row["factory"]) if row["factory"] in FACTORIES else 0)
        e_code = st.text_input("설비코드", value=row["equipment_code"])
        e_name = st.text_input("설비명", value=row["equipment_name"])
        e_cat = st.selectbox("분류", CATEGORY_LIST,
            index=CATEGORY_LIST.index(row["category"]) if row.get("category") in CATEGORY_LIST else 0)
    with ec2:
        e_loc = st.text_input("위치", value=row.get("location") or "")
        e_st = st.selectbox("상태", STATUS_LIST,
            index=STATUS_LIST.index(row["status"]) if row["status"] in STATUS_LIST else 0)
        e_install = st.text_input("설치일 (YYYY-MM-DD)", value=row.get("install_date") or "")
        e_memo = st.text_area("비고", value=row.get("memo") or "", height=80)
    sb1, sb2 = st.columns(2)
    with sb1:
        if st.button("💾 저장", use_container_width=True, type="primary"):
            upsert_equipment({
                "id": int(row["id"]), "factory": e_fac, "equipment_code": e_code,
                "equipment_name": e_name, "category": e_cat, "location": e_loc,
                "status": e_st, "install_date": e_install, "memo": e_memo,
            })
            st.cache_data.clear()
            st.rerun()
    with sb2:
        if st.button("🗑️ 삭제", use_container_width=True):
            delete_equipment(int(row["id"]))
            st.cache_data.clear()
            st.rerun()


tab1, tab2, tab3 = st.tabs(["📋 설비 목록", "➕ 설비 등록", "📈 설비 이력"])

# ══════════════════════════════
# 탭1: 설비 목록
# ══════════════════════════════
with tab1:
    fc1, fc2 = st.columns([2, 2])
    with fc1:
        f_fac = st.selectbox("팩토리 선택", ["전체"] + FACTORIES, key="eq_fac_filter")
    with fc2:
        f_st = st.selectbox("상태 필터", ["전체"] + STATUS_LIST, key="eq_st_filter")

    df_all = get_equipment()

    # 전체 KPI (선택과 무관하게 전체 기준)
    kpi_cards([
        {"label": "전체 설비", "value": f"{len(df_all)}대", "color": "blue",   "sub": "등록 설비"},
        {"label": "정상",      "value": f"{len(df_all[df_all['status']=='정상'])}대",   "color": "green",  "sub": "🟢 가동"},
        {"label": "점검중",    "value": f"{len(df_all[df_all['status']=='점검중'])}대", "color": "amber",  "sub": "🟡 진행"},
        {"label": "팬딩",      "value": f"{len(df_all[df_all['status']=='팬딩'])}대",   "color": "purple", "sub": "🟠 대기"},
        {"label": "고장",      "value": f"{len(df_all[df_all['status']=='고장'])}대",   "color": "red",    "sub": "🔴 정지"},
    ])

    # 팩토리 필터 적용
    df = df_all.copy()
    if f_fac != "전체":
        df = df[df["factory"] == f_fac]
    if f_st != "전체":
        df = df[df["status"] == f_st]

    if df.empty:
        st.info("해당 조건의 설비가 없습니다.")
    else:
        # 팩토리별로 그룹핑해서 표시
        factories_in_view = df["factory"].unique().tolist()
        factories_in_view.sort()

        _EQ_COLOR = {"정상": "#2FA37A", "점검중": "#C98A18", "팬딩": "#9C978C",
                     "고장": "#D6485B", "폐기": "#9C978C"}

        for fac in factories_in_view:
            df_fac = df[df["factory"] == fac].copy()
            normal = len(df_fac[df_fac["status"] == "정상"])
            checking = len(df_fac[df_fac["status"] == "점검중"])
            pending = len(df_fac[df_fac["status"] == "팬딩"])
            broken = len(df_fac[df_fac["status"] == "고장"])

            st.markdown(f"### 🏭 {html.escape(str(fac))}  <span style='font-size:0.9rem; color:#9C978C;'>총 {len(df_fac)}대 &nbsp;·&nbsp; 🟢 {normal} &nbsp;🟡 {checking} &nbsp;🟠 {pending} &nbsp;🔴 {broken}</span>", unsafe_allow_html=True)

            grid = '<div class="rec-grid">'
            for _, e in df_fac.iterrows():
                stt = str(e.get("status") or "")
                color = _EQ_COLOR.get(stt, "#6E62E6")
                name = html.escape(str(e.get("equipment_name") or "-"))
                code = html.escape(str(e.get("equipment_code") or ""))
                cat = html.escape(str(e.get("category") or "")) if e.get("category") else ""
                loc = html.escape(str(e.get("location") or "")) if e.get("location") else ""
                memo = html.escape(str(e.get("memo") or "")) if e.get("memo") else ""
                meta_bits = []
                if cat:
                    meta_bits.append(f"🏷️ {cat}")
                if loc:
                    meta_bits.append(f"📍 {loc}")
                meta = " · ".join(meta_bits)
                grid += (
                    f'<div class="eq-card" style="border-left-color:{color}">'
                    f'<div class="eq-top"><span class="eq-name">{name}</span>'
                    f'<span class="eq-st" style="color:{color}"><span class="d" style="background:{color}"></span>{html.escape(stt)}</span></div>'
                    f'<div class="eq-code">{code}</div>'
                    + (f'<div class="eq-meta">{meta}</div>' if meta else '')
                    + (f'<div class="eq-meta" style="color:var(--tx3)">📝 {memo}</div>' if memo else '')
                    + '</div>'
                )
            grid += '</div>'
            st.markdown(grid, unsafe_allow_html=True)
            st.markdown("")

        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("⬇️ CSV 다운로드", data=csv,
                           file_name=f"설비목록_{date.today()}.csv", mime="text/csv")

        st.markdown("---")
        st.markdown("##### ✏️ 수정 / 삭제")
        esc1, esc2 = st.columns([1, 3])
        with esc1:
            edit_code = st.text_input("설비코드 입력", placeholder="예: MO-0100-06")
        with esc2:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("✏️ 수정 / 삭제 열기", type="primary"):
                row_data = df_all[df_all["equipment_code"] == edit_code.strip()] if edit_code.strip() else pd.DataFrame()
                if row_data.empty:
                    st.warning("설비코드를 정확히 입력하세요.")
                else:
                    equipment_edit_dialog(row_data.iloc[0])

# ══════════════════════════════
# 탭2: 설비 등록
# ══════════════════════════════
with tab2:
    st.subheader("➕ 설비 신규 등록")
    with st.form("eq_new", clear_on_submit=True):
        nc1, nc2 = st.columns(2)
        with nc1:
            n_fac = st.selectbox("팩토리 *", FACTORIES)
            n_code = st.text_input("설비코드 *", placeholder="예: MO-0100-06")
            n_name = st.text_input("설비명 *", placeholder="예: 모아주방 애벌기 1")
            n_cat = st.selectbox("분류", CATEGORY_LIST)
        with nc2:
            n_loc = st.text_input("위치", placeholder="예: A동 1층")
            n_st = st.selectbox("상태", STATUS_LIST)
            n_install = st.date_input("설치일")
            n_memo = st.text_area("비고", height=80)
        s_new = st.form_submit_button("💾 등록", use_container_width=True, type="primary")

    if s_new:
        if not n_code or not n_name:
            st.error("설비코드와 설비명은 필수입니다.")
        else:
            upsert_equipment({
                "factory": n_fac, "equipment_code": n_code, "equipment_name": n_name,
                "category": n_cat, "location": n_loc, "status": n_st,
                "install_date": str(n_install), "memo": n_memo,
            })
            st.cache_data.clear()
            flash(f"'{n_code}' 설비가 등록되었습니다")
            st.rerun()


# ══════════════════════════════
# 탭3: 설비 이력 · 지표(MTBF/MTTR)
# ══════════════════════════════
with tab3:
    df_all_h = get_equipment()
    if df_all_h.empty:
        st.info("등록된 설비가 없습니다.")
    else:
        hc1, hc2 = st.columns([2, 3])
        with hc1:
            h_fac = st.selectbox("팩토리", ["전체"] + FACTORIES, key="hist_fac")
        df_pick = df_all_h if h_fac == "전체" else df_all_h[df_all_h["factory"] == h_fac]
        with hc2:
            if df_pick.empty:
                st.info("해당 팩토리 설비가 없습니다.")
                pick_code = None
            else:
                opts = {r.equipment_code: f"{r.equipment_name} ({r.equipment_code})"
                        for r in df_pick.itertuples()}
                pick_code = st.selectbox("설비 선택", list(opts.keys()),
                                         format_func=lambda x: opts[x], key="hist_eq")

        if pick_code:
            stt = get_equipment_stats(pick_code)
            kpi_cards([
                {"label": "총 보전 건수", "value": f"{stt['count']:,}건", "color": "blue", "sub": "누적 이력"},
                {"label": "MTBF", "value": f"{stt['mtbf_days']}일", "color": "green", "sub": "평균 고장간격"},
                {"label": "MTTR", "value": f"{stt['mttr']}분", "color": "amber", "sub": "평균 수리시간"},
                {"label": "마지막 보전", "value": str(stt['last_date']), "color": "purple", "sub": "최근 접수일"},
            ])
            st.caption("MTBF=평균 고장 사이 간격(길수록 안정), MTTR=평균 수리 소요시간(짧을수록 빠름)")

            df_h = get_equipment_history(pick_code)
            if df_h.empty:
                st.info("이 설비의 보전 이력이 없습니다.")
            else:
                _BC = {"완료": "#2FA37A", "진행 중": "#C98A18", "팬딩": "#9C978C",
                       "고장": "#D6485B", "취소": "#9C978C"}
                cards = '<div class="rec-scroll">'
                for _, r in df_h.iterrows():
                    status = str(r.get("status") or "")
                    color = _BC.get(status, "#6E62E6")
                    issue = html.escape(str(r.get("issue_code") or "-"))
                    recv = html.escape(str(r.get("recv_date") or "-"))
                    comp = html.escape(str(r.get("comp_date") or ""))
                    down = r.get("downtime_min") or 0
                    assignee = html.escape(str(r.get("assignee") or ""))
                    desc = html.escape(str(r.get("issue_desc") or "").strip())
                    meta = f'<span>🏷️ <b>{issue}</b></span><span>📅 {recv}</span>'
                    if comp:
                        meta += f'<span>✅ {comp}</span>'
                    if down:
                        meta += f'<span>⏱️ <b>{int(down)}</b>분</span>'
                    if assignee:
                        meta += f'<span>👤 {assignee}</span>'
                    desc_html = f'<div class="rec-desc">{desc}</div>' if desc else ''
                    cards += (
                        f'<div class="rec-card" style="border-left-color:{color}">'
                        f'<div class="rec-top">{status_badge(status)}'
                        f'<span class="rec-spacer"></span></div>'
                        f'<div class="rec-meta">{meta}</div>{desc_html}</div>'
                    )
                cards += '</div>'
                st.markdown(cards, unsafe_allow_html=True)

