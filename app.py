import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from utils.database import init_db

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
st.markdown("""
<style>
/* 폰트 & 전체 배경 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

/* 사이드바 */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1E3A5F 0%, #2563EB 100%);
}
section[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
section[data-testid="stSidebar"] .stRadio label { color: #E2E8F0 !important; }

/* 메트릭 카드 */
[data-testid="metric-container"] {
    background: white;
    border-radius: 12px;
    padding: 16px 20px;
    border: 1px solid #E2E8F0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

/* 헤더 */
.page-header {
    background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%);
    color: white;
    padding: 20px 28px;
    border-radius: 12px;
    margin-bottom: 24px;
}
.page-header h1 { color: white; margin: 0; font-size: 1.6rem; }
.page-header p { color: #BFDBFE; margin: 4px 0 0; font-size: 0.9rem; }

/* 경고 배지 */
.badge-red {
    background: #FEE2E2; color: #DC2626;
    padding: 2px 10px; border-radius: 999px;
    font-size: 0.8rem; font-weight: 600;
}
.badge-yellow {
    background: #FEF3C7; color: #D97706;
    padding: 2px 10px; border-radius: 999px;
    font-size: 0.8rem; font-weight: 600;
}
.badge-green {
    background: #D1FAE5; color: #059669;
    padding: 2px 10px; border-radius: 999px;
    font-size: 0.8rem; font-weight: 600;
}

/* 테이블 */
.dataframe thead tr th {
    background: #F8FAFC !important;
    color: #374151 !important;
    font-weight: 600 !important;
}

/* 버튼 */
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
}

/* 구분선 */
hr { border-color: #E2E8F0; }
</style>
""", unsafe_allow_html=True)

# ─── 메인 화면 ───
st.markdown("""
<div class="page-header">
    <h1>🔧 스마트팩토리 CMMS</h1>
    <p>설비 보전 관리 시스템 · Computerized Maintenance Management System</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    st.info("📊 **대시보드** — 좌측 메뉴에서 이동하세요")
with col2:
    st.info("📋 **보전내역 관리** — 작업 등록/조회/수정")
with col3:
    st.info("⚙️ **설비 관리** — 설비 목록 관리")

st.markdown("---")
st.caption("© 2026 스마트팩토리팀 · CMMS v1.0")
