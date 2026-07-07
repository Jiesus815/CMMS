import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import import_from_excel, init_db, get_conn, get_maintenance, get_equipment
from utils.style import inject_css, page_header
import tempfile
from datetime import datetime

init_db()

inject_css("""
.info-card {
    background: white; border: 1px solid #E2E8F0;
    border-radius: 12px; padding: 20px; margin: 8px 0;
}
""")

page_header("📁 데이터 관리", "Excel Import · DB 백업 · 데이터 초기화")

tab1, tab2, tab3 = st.tabs(["📥 Excel Import", "💾 DB 백업", "⚠️ 초기화"])

# ══════════════════════════════
# 탭1: Excel Import
# ══════════════════════════════
with tab1:
    st.subheader("📥 Excel 파일 Import")
    st.markdown("""
    <div class="info-card">
    <b>지원 시트:</b><br>
    • <code>Raw 보전내역</code> 또는 <code>보전내역</code> → 보전내역 DB로 import<br>
    • <code>Raw 설비리스트</code> 또는 <code>설비리스트</code> → 설비 DB로 import<br><br>
    <b>주의:</b> 기존 데이터와 중복 시 설비코드 기준으로 건너뜁니다.
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Excel 파일 선택 (.xlsx)",
        type=["xlsx"],
        help="[스마팩] 2026 보전시트.xlsx 형식을 지원합니다.",
    )

    if uploaded:
        st.info(f"파일명: **{uploaded.name}** | 크기: {uploaded.size / 1024:.1f} KB")

        if st.button("🚀 Import 시작", type="primary", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name

            with st.spinner("데이터 처리 중..."):
                results = import_from_excel(tmp_path)

            os.remove(tmp_path)

            if results["errors"]:
                st.warning(f"⚠️ 일부 오류 발생 ({len(results['errors'])}건)")
                with st.expander("오류 내역 보기"):
                    for e in results["errors"][:20]:
                        st.text(e)

            st.success(f"""
            ✅ Import 완료!
            - 설비: **{results['equipment']}건** import
            - 보전내역: **{results['maintenance']}건** import
            """)

# ══════════════════════════════
# 탭2: DB 백업
# ══════════════════════════════
with tab2:
    st.subheader("💾 데이터 백업 (CSV)")
    st.markdown("""
    <div class="info-card">
    Supabase(PostgreSQL) 사용 중입니다.<br>
    각 테이블을 CSV 파일로 다운로드하여 백업할 수 있습니다.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 보전내역 CSV 다운로드", use_container_width=True):
            df_m = get_maintenance()
            csv = df_m.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ 보전내역.csv",
                data=csv.encode("utf-8-sig"),
                file_name=f"보전내역_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    with col2:
        if st.button("📥 설비목록 CSV 다운로드", use_container_width=True):
            df_e = get_equipment()
            csv = df_e.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ 설비목록.csv",
                data=csv.encode("utf-8-sig"),
                file_name=f"설비목록_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

# ══════════════════════════════
# 탭3: 초기화
# ══════════════════════════════
with tab3:
    st.subheader("⚠️ 데이터 초기화")
    st.error("⚠️ 주의: 아래 작업은 되돌릴 수 없습니다!")

    admin_pw = st.text_input("🔐 관리자 비밀번호", type="password", key="admin_pw")

    try:
        correct_pw = st.secrets["ADMIN_PASSWORD"]
    except Exception:
        correct_pw = ""

    if not admin_pw:
        st.info("관리자 비밀번호를 입력하면 초기화 기능이 활성화됩니다.")
    elif admin_pw != correct_pw:
        st.error("비밀번호가 틀렸습니다.")
    else:
        st.success("✅ 인증되었습니다.")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**보전내역만 삭제**")
            confirm1 = st.text_input("확인 문구 입력 ('삭제확인')", key="c1")
            if st.button("🗑️ 보전내역 전체 삭제", use_container_width=True):
                if confirm1 == "삭제확인":
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute("DELETE FROM maintenance")
                    conn.commit()
                    conn.close()
                    st.success("보전내역이 삭제되었습니다.")
                else:
                    st.error("확인 문구가 일치하지 않습니다.")

        with col2:
            st.markdown("**전체 데이터 초기화**")
            confirm2 = st.text_input("확인 문구 입력 ('전체초기화')", key="c2")
            if st.button("💥 전체 DB 초기화", use_container_width=True):
                if confirm2 == "전체초기화":
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute("DELETE FROM maintenance")
                    c.execute("DELETE FROM equipment")
                    conn.commit()
                    conn.close()
                    st.success("전체 데이터가 초기화되었습니다.")
                else:
                    st.error("확인 문구가 일치하지 않습니다.")
