import streamlit as st
import sys, os
import html
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import (
    get_equipment, add_pm, get_pm_list, mark_pm_done, delete_pm, init_db,
)
from utils.constants import FACTORIES
from utils.style import inject_css, page_header, kpi_cards, flash, render_flash
from datetime import date, datetime

init_db()
inject_css()
render_flash()

page_header("🗓️ 예방보전", "정기 점검 일정 관리 · 마감 알림")

tab1, tab2 = st.tabs(["📋 일정 목록", "➕ 일정 등록"])

_TODAY = datetime.now().strftime("%Y-%m-%d")


def _due_state(next_due: str):
    """(색상, 라벨) 반환."""
    if not next_due:
        return "#9C978C", "미정"
    try:
        d = datetime.strptime(next_due, "%Y-%m-%d").date()
    except Exception:
        return "#9C978C", "미정"
    delta = (d - date.today()).days
    if delta < 0:
        return "#D6485B", f"{-delta}일 지연"
    if delta <= 7:
        return "#C98A18", f"{delta}일 남음"
    return "#2FA37A", f"{delta}일 남음"


# ══════════════════════════════
# 탭1: 일정 목록
# ══════════════════════════════
with tab1:
    df = get_pm_list(active_only=True)
    if df.empty:
        st.info("등록된 예방보전 일정이 없습니다. '일정 등록' 탭에서 추가하세요.")
    else:
        overdue = sum(1 for nd in df["next_due"] if nd and nd < _TODAY)
        soon = 0
        for nd in df["next_due"]:
            c, _ = _due_state(nd)
            if c == "#C98A18":
                soon += 1
        kpi_cards([
            {"label": "전체 일정", "value": f"{len(df):,}건", "color": "blue", "sub": "활성 PM"},
            {"label": "마감 임박", "value": f"{soon:,}건", "color": "amber", "sub": "7일 이내"},
            {"label": "지연", "value": f"{overdue:,}건", "color": "red", "sub": "기한 초과"},
        ])

        cards = '<div class="rec-scroll">'
        for _, r in df.iterrows():
            nd = str(r.get("next_due") or "")
            color, label = _due_state(nd)
            title = html.escape(str(r.get("title") or "(제목 없음)"))
            eqn = html.escape(str(r.get("equipment_name") or ""))
            eqc = html.escape(str(r.get("equipment_code") or ""))
            interval = int(r.get("interval_days") or 0)
            last = html.escape(str(r.get("last_done") or "-"))
            memo = html.escape(str(r.get("memo") or "").strip())
            meta = (f'<span>🔧 {eqn} {eqc}</span>'
                    f'<span>🔁 {interval}일 주기</span>'
                    f'<span>✅ 최근 {last}</span>'
                    f'<span>📅 예정 {html.escape(nd) or "-"}</span>')
            pill = f'<span class="rec-fac" style="color:{color};background:{color}1a">{label}</span>'
            desc_html = f'<div class="rec-desc">{memo}</div>' if memo else ''
            cards += (
                f'<div class="rec-card" style="border-left-color:{color}">'
                f'<div class="rec-top"><span class="rec-name">{title}</span>'
                f'<span class="rec-spacer"></span>{pill}</div>'
                f'<div class="rec-meta">{meta}</div>{desc_html}</div>'
            )
        cards += '</div>'
        st.markdown(cards, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### ✅ 점검 완료 처리 / 삭제")
        mc1, mc2, mc3 = st.columns([2, 1, 1])
        with mc1:
            id_to_label = {int(r.id): f"{r.title or '-'} · {r.equipment_name or ''}"
                           for r in df.itertuples()}
            sel_pm = st.selectbox("일정 선택", list(id_to_label.keys()),
                                  format_func=lambda x: id_to_label[x], key="pm_sel")
        with mc2:
            done_date = st.date_input("완료일", value=date.today(), key="pm_done_date")
        with mc3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("✅ 완료 처리", use_container_width=True, type="primary"):
                mark_pm_done(int(sel_pm), str(done_date))
                st.cache_data.clear()
                flash("점검 완료 처리되었습니다 (다음 예정일 갱신)")
                st.rerun()
        if st.button("🗑️ 이 일정 삭제"):
            delete_pm(int(sel_pm))
            st.cache_data.clear()
            flash("일정이 삭제되었습니다")
            st.rerun()


# ══════════════════════════════
# 탭2: 일정 등록
# ══════════════════════════════
with tab2:
    st.subheader("➕ 예방보전 일정 등록")
    df_eq = get_equipment()

    ec1, ec2 = st.columns(2)
    with ec1:
        pm_fac = st.selectbox("팩토리", FACTORIES, key="pm_fac")
    with ec2:
        if not df_eq.empty:
            df_f = df_eq[df_eq["factory"] == pm_fac]
            eq_opts = {r.equipment_code: f"{r.equipment_name} ({r.equipment_code})"
                       for r in df_f.itertuples()}
        else:
            eq_opts = {}
        pm_eq = st.selectbox("설비", list(eq_opts.keys()) or ["-"],
                             format_func=lambda x: eq_opts.get(x, x), key="pm_eq")

    with st.form("pm_new", clear_on_submit=True):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            pm_title = st.text_input("점검 제목 *", placeholder="예: 베어링 그리스 주입")
        with fc2:
            pm_interval = st.number_input("주기 (일)", min_value=1, value=30, step=1)
        with fc3:
            pm_last = st.date_input("마지막 시행일", value=date.today())
        pm_memo = st.text_area("메모", height=70, placeholder="점검 내용/체크리스트")
        submitted = st.form_submit_button("💾 등록", use_container_width=True, type="primary")

    if submitted:
        if not pm_title or not eq_opts:
            st.error("설비와 점검 제목은 필수입니다.")
        else:
            eq_name = df_eq[df_eq["equipment_code"] == pm_eq]["equipment_name"].values
            add_pm({
                "equipment_code": pm_eq,
                "equipment_name": eq_name[0] if len(eq_name) else "",
                "title": pm_title.strip(),
                "interval_days": int(pm_interval),
                "last_done": str(pm_last),
                "memo": pm_memo.strip(),
            })
            st.cache_data.clear()
            flash("예방보전 일정이 등록되었습니다")
            st.rerun()
