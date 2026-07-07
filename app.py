import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from utils.database import init_db
from utils.style import inject_css, page_header

# ─── 페이지 기본 설정 ───
st.set_page_config(
    page_title="스마팩 CMMS",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── DB 초기화 ───
init_db()

# ─── 전역 CSS ───
inject_css()

# ─── 메인 화면 ───
page_header("🔧 스마트팩토리 CMMS", "설비 보전 관리 시스템 · Computerized Maintenance Management System")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("📊 **대시보드** — 좌측 메뉴에서 이동하세요")
with col2:
    st.info("📋 **보전내역 관리** — 작업 등록/조회/수정")
with col3:
    st.info("⚙️ **설비 관리** — 설비 목록 관리")

st.markdown("---")
st.caption("© 2026 스마트팩토리팀 · CMMS v1.0")
