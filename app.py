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
inject_css("""
/* 폰트 & 전체 배경 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

/* 사이드바 */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E3A5F 0%, #2563EB 100%);
}
section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
section[data-testid="stSidebar"] .stRadio label { color: #E2E8F0 !important; }

/* 배지 */
.badge-red    { background: #FEE2E2; color: #DC2626; padding: 2px 10px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }
.badge-yellow { background: #FEF3C7; color: #D97706; padding: 2px 10px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }
.badge-green  { background: #D1FAE5; color: #059669; padding: 2px 10px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }

/* 테이블 */
.dataframe thead tr th { background: #F8FAFC !important; color: #374151 !important; font-weight: 600 !important; }

/* 버튼 */
.stButton > button { border-radius: 8px; font-weight: 500; }

/* 구분선 */
hr { border-color: #E2E8F0; }
""")

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
