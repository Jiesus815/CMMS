import streamlit as st
import sys, os
import html
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import get_equipment, upsert_equipment, delete_equipment, init_db
from utils.constants import FACTORIES, EQUIPMENT_STATUS_LIST as STATUS_LIST, CATEGORY_LIST
from utils.style import inject_css, page_header, kpi_cards
import pandas as pd
from datetime import date

init_db()

inject_css()

page_header("⚙️ 설비 Overview", "설비 상태 현황 · 등록 · 수정")

tab1, tab2 = st.tabs(["📋 설비 목록", "➕ 설비 등록"])

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

        def eq_status_icon(s):
            icons = {"정상": "🟢 정상", "점검중": "🟡 점검중", "팬딩": "🟠 팬딩", "고장": "🔴 고장", "폐기": "⚫ 폐기"}
            return icons.get(s, s)

        for fac in factories_in_view:
            df_fac = df[df["factory"] == fac].copy()
            normal = len(df_fac[df_fac["status"] == "정상"])
            checking = len(df_fac[df_fac["status"] == "점검중"])
            pending = len(df_fac[df_fac["status"] == "팬딩"])
            broken = len(df_fac[df_fac["status"] == "고장"])

            st.markdown(f"### 🏭 {html.escape(str(fac))}  <span style='font-size:0.9rem; color:#64748B;'>총 {len(df_fac)}대 &nbsp;·&nbsp; 🟢 {normal} &nbsp;🟡 {checking} &nbsp;🟠 {pending} &nbsp;🔴 {broken}</span>", unsafe_allow_html=True)

            display_cols = ["equipment_code", "equipment_name", "category", "location", "status", "memo"]
            display_cols = [c for c in display_cols if c in df_fac.columns]
            df_show = df_fac[display_cols].copy()
            df_show.columns = ["설비코드", "설비명", "분류", "위치", "상태", "비고"][:len(display_cols)]
            df_show["상태"] = df_show["상태"].apply(eq_status_icon)

            # 상태별 색상 강조: 점검중/고장 행 위에 배지
            st.dataframe(df_show, use_container_width=True,
                         height=min(80 + len(df_show) * 35, 400), hide_index=True)
            st.markdown("")

        csv = df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button("⬇️ CSV 다운로드", data=csv,
                           file_name=f"설비목록_{date.today()}.csv", mime="text/csv")

        st.markdown("---")
        st.subheader("✏️ 수정 / 삭제")
        st.caption("설비코드를 직접 입력하여 수정/삭제합니다.")
        edit_code = st.text_input("설비코드 입력", placeholder="예: MO-0100-06")
        if edit_code:
            row_data = df_all[df_all["equipment_code"] == edit_code.strip()]
            if row_data.empty:
                st.warning("해당 설비코드가 없습니다.")
            else:
                row = row_data.iloc[0]
                st.info(f"**{row['equipment_code']}** · {row['equipment_name']} ({row['factory']})")
                with st.form("eq_edit"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        e_fac = st.selectbox("팩토리", FACTORIES, key="eq_edit_fac",
                            index=FACTORIES.index(row["factory"]) if row["factory"] in FACTORIES else 0)
                        e_code = st.text_input("설비코드", value=row["equipment_code"])
                        e_name = st.text_input("설비명", value=row["equipment_name"])
                        e_cat = st.selectbox("분류", CATEGORY_LIST, key="eq_edit_cat",
                            index=CATEGORY_LIST.index(row["category"]) if row.get("category") in CATEGORY_LIST else 0)
                    with ec2:
                        e_loc = st.text_input("위치", value=row.get("location") or "")
                        e_st = st.selectbox("상태", STATUS_LIST, key="eq_edit_st",
                            index=STATUS_LIST.index(row["status"]) if row["status"] in STATUS_LIST else 0)
                        e_install = st.text_input("설치일 (YYYY-MM-DD)", value=row.get("install_date") or "")
                        e_memo = st.text_area("비고", value=row.get("memo") or "", height=80)
                    sb1, sb2 = st.columns(2)
                    with sb1:
                        s_edit = st.form_submit_button("💾 저장", use_container_width=True)
                    with sb2:
                        s_del = st.form_submit_button("🗑️ 삭제", use_container_width=True)

                if s_edit:
                    upsert_equipment({
                        "id": int(row["id"]), "factory": e_fac, "equipment_code": e_code,
                        "equipment_name": e_name, "category": e_cat, "location": e_loc,
                        "status": e_st, "install_date": e_install, "memo": e_memo,
                    })
                    st.success("수정 완료!")
                    st.rerun()
                if s_del:
                    delete_equipment(int(row["id"]))
                    st.success("삭제 완료!")
                    st.rerun()

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
            st.success(f"✅ '{n_code}' 설비가 등록되었습니다!")

