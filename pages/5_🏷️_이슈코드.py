import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import get_issue_code_full, get_part_codes, add_issue_code, init_db
from utils.style import inject_css, page_header, kpi_cards
import pandas as pd

init_db()

inject_css()

page_header("🏷️ 이슈 코드 관리", "부품코드 + 이슈코드 조합 테이블 관리")

tab1, tab2 = st.tabs(["📋 코드 목록", "➕ 코드 추가"])

with tab1:
    df = get_issue_code_full()

    search = st.text_input("🔍 검색 (부품명/이슈명/코드)", placeholder="예: GCM, 파손, 모터...")
    if search:
        mask = (
            df["part_name"].str.contains(search, case=False, na=False) |
            df["issue_name"].str.contains(search, case=False, na=False) |
            df["full_code"].str.contains(search, case=False, na=False) |
            df["part_code"].str.contains(search, case=False, na=False)
        )
        df = df[mask]

    kpi_cards([{"label": "조회 건수", "value": f"{len(df)}개", "icon": "🏷️", "color": "blue", "sub": "이슈코드 항목"}])
    df_show = df.rename(columns={
        "id": "ID", "part_name": "부품명", "part_name_en": "부품명(영문)",
        "part_code": "부품코드", "issue_name": "이슈명", "issue_name_en": "이슈명(영문)",
        "issue_code": "이슈코드", "full_code": "통합코드",
    })
    st.dataframe(df_show, use_container_width=True, height=480, hide_index=True)

    # 부품코드 요약
    st.markdown("---")
    st.subheader("📦 부품코드 목록")
    df_parts = get_part_codes()
    col1, col2 = st.columns(2)
    half = len(df_parts) // 2
    with col1:
        st.dataframe(df_parts.iloc[:half].reset_index(drop=True), use_container_width=True, hide_index=True)
    with col2:
        st.dataframe(df_parts.iloc[half:].reset_index(drop=True), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("➕ 이슈 코드 직접 추가")
    with st.form("new_code", clear_on_submit=True):
        ac1, ac2 = st.columns(2)
        with ac1:
            n_part_name = st.text_input("부품명 *", placeholder="예: 모터")
            n_part_en = st.text_input("부품명 영문", placeholder="예: Motor")
            n_part_code = st.text_input("부품코드 *", placeholder="예: MOT").upper()
        with ac2:
            n_issue_name = st.text_input("이슈명 *", placeholder="예: 파손/고장")
            n_issue_en = st.text_input("이슈명 영문", placeholder="예: Failure")
            n_issue_code = st.text_input("이슈코드 *", placeholder="예: F").upper()

        s = st.form_submit_button("💾 추가", use_container_width=True, type="primary")

    if s:
        if not n_part_name or not n_part_code or not n_issue_name or not n_issue_code:
            st.error("필수 항목을 입력하세요.")
        else:
            full = f"{n_part_code}-{n_issue_code}"
            try:
                if add_issue_code(n_part_name, n_part_en, n_part_code, n_issue_name, n_issue_en, n_issue_code):
                    st.cache_data.clear()
                    st.success(f"✅ '{full}' 코드가 추가되었습니다!")
                else:
                    st.warning(f"⚠️ '{full}' 코드는 이미 존재합니다.")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
