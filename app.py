import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from utils.database import init_db

# ─── 페이지 기본 설정 (진입점에서 1회만) ───
st.set_page_config(
    page_title="스마팩 CMMS",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── DB 초기화 ───
init_db()

# ─── 카테고리 그룹 네비게이션 ───
_PAGES = os.path.join(os.path.dirname(__file__), "pages")

nav = {
    "현황": [
        st.Page(os.path.join(_PAGES, "1_📊_대시보드.py"), title="대시보드", icon="📊", default=True),
    ],
    "보전 관리": [
        st.Page(os.path.join(_PAGES, "2_📋_보전내역.py"), title="보전내역", icon="📋"),
        st.Page(os.path.join(_PAGES, "4_📅_주차별현황.py"), title="주차별 현황", icon="📅"),
        st.Page(os.path.join(_PAGES, "3_⚙️_설비Overview.py"), title="설비 현황", icon="🏭"),
        st.Page(os.path.join(_PAGES, "8_📝_작업일지.py"), title="작업일지", icon="📝"),
    ],
    "데이터 관리": [
        st.Page(os.path.join(_PAGES, "5_🏷️_이슈코드.py"), title="이슈코드", icon="🏷️"),
        st.Page(os.path.join(_PAGES, "7_💬_슬랙연동.py"), title="슬랙 연동", icon="💬"),
        st.Page(os.path.join(_PAGES, "6_📁_데이터관리.py"), title="가져오기 · 초기화", icon="📁"),
    ],
}

pg = st.navigation(nav)
pg.run()
