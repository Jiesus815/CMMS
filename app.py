import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from utils.database import init_db, change_own_password
from utils.auth import require_login, current_user, logout

# ─── 페이지 기본 설정 (진입점에서 1회만) ───
st.set_page_config(
    page_title="스마팩 CMMS",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── DB 초기화 ───
try:
    init_db()
except Exception as _e:
    st.error("⚠️ 데이터베이스에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.")
    if st.button("🔄 다시 시도"):
        st.rerun()
    with st.expander("기술 상세 정보"):
        st.exception(_e)
    st.stop()

# ─── 로그인 게이트 (AUTH_ENABLED 활성 시) ───
require_login()


# ─── 카테고리 그룹 네비게이션 ───
_PAGES = os.path.join(os.path.dirname(__file__), "pages")

nav = {
    "홈": [
        st.Page(os.path.join(_PAGES, "1_📊_대시보드.py"), title="대시보드", icon="📊", default=True),
    ],
    "보전 관리": [
        st.Page(os.path.join(_PAGES, "2_📋_보전내역.py"), title="보전내역", icon="📋"),
        st.Page(os.path.join(_PAGES, "8_📝_작업일지.py"), title="작업일지", icon="📝"),
        st.Page(os.path.join(_PAGES, "9_🗓️_예방보전.py"), title="예방보전", icon="🗓️"),
        st.Page(os.path.join(_PAGES, "4_📅_주차별현황.py"), title="주차별 집계", icon="📅"),
    ],
    "설비 관리": [
        st.Page(os.path.join(_PAGES, "3_⚙️_설비Overview.py"), title="설비 목록", icon="🏭"),
    ],
    "시스템": [
        st.Page(os.path.join(_PAGES, "5_🏷️_이슈코드.py"), title="이슈코드", icon="🏷️"),
        st.Page(os.path.join(_PAGES, "7_💬_슬랙연동.py"), title="슬랙 연동", icon="💬"),
        st.Page(os.path.join(_PAGES, "6_📁_데이터관리.py"), title="시스템 관리", icon="⚙️"),
    ],
}

pg = st.navigation(nav)

# ─── 사이드바: 로그인 사용자 표시 · 로그아웃 ───
_u = current_user()
if _u:
    with st.sidebar:
        st.markdown("---")
        _role_label = {"superadmin": "최고관리자", "admin": "관리자", "user": "일반"}.get(_u.get("role"), _u.get("role"))
        st.caption(f"👤 {_u.get('display_name') or _u.get('username')} · {_role_label}")
        with st.expander("🔑 내 비밀번호 변경"):
            _cur = st.text_input("현재 비밀번호", type="password", key="_pw_cur")
            _new = st.text_input("새 비밀번호", type="password", key="_pw_new")
            _new2 = st.text_input("새 비밀번호 확인", type="password", key="_pw_new2")
            if st.button("변경", use_container_width=True, key="_pw_btn"):
                if not _cur or not _new:
                    st.warning("비밀번호를 입력하세요.")
                elif _new != _new2:
                    st.warning("새 비밀번호가 일치하지 않습니다.")
                elif len(_new) < 8:
                    st.warning("새 비밀번호는 8자 이상이어야 합니다.")
                elif change_own_password(int(_u["id"]), _cur, _new):
                    st.success("변경되었습니다.")
                else:
                    st.error("현재 비밀번호가 틀렸습니다.")
        if st.button("로그아웃", use_container_width=True):
            logout()
            st.rerun()

try:
    pg.run()
except Exception as _e:
    st.error("⚠️ 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
    if st.button("🔄 다시 시도", key="_retry_page"):
        st.rerun()
    with st.expander("기술 상세 정보"):
        st.exception(_e)
