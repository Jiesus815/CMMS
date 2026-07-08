"""로그인 게이트 · 세션 · 권한 헬퍼.

AUTH_ENABLED 플래그로 로그인 게이트를 켜고 끌 수 있다.
- secrets 또는 환경변수 AUTH_ENABLED 가 true 일 때만 로그인 요구.
- 기본값은 꺼짐(False) — 계정/로그인 테스트를 마친 뒤 켜서 잠김 위험을 방지.
"""
import os
import streamlit as st

from utils.database import verify_login
from utils.style import inject_css


def auth_enabled() -> bool:
    """로그인 게이트 활성화 여부. 기본 False(안전)."""
    val = None
    try:
        val = st.secrets.get("AUTH_ENABLED", None)
    except Exception:
        val = None
    if val is None:
        val = os.environ.get("AUTH_ENABLED", "false")
    return str(val).strip().lower() in ("1", "true", "yes", "on")


def current_user():
    """로그인된 사용자 dict 또는 None."""
    return st.session_state.get("auth_user")


def is_admin() -> bool:
    """최고관리자/관리자 여부."""
    u = current_user()
    return bool(u and u.get("role") in ("superadmin", "admin"))


def is_superadmin() -> bool:
    u = current_user()
    return bool(u and u.get("role") == "superadmin")


def logout():
    st.session_state.pop("auth_user", None)


def _login_form():
    inject_css()
    st.markdown(
        """
        <div class="ateli-head" style="max-width:420px;margin:8vh auto 18px;text-align:center;">
            <div class="ah-eyebrow" style="justify-content:center;">
                <span class="ah-emoji">🔧</span>
                <span class="ah-kicker">스마팩 CMMS</span>
            </div>
            <h1 class="ah-title" style="font-size:2.2rem;">로그인</h1>
            <p class="ah-sub">계정으로 로그인하세요</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.form("login_form"):
            username = st.text_input("아이디")
            password = st.text_input("비밀번호", type="password")
            ok = st.form_submit_button("로그인", use_container_width=True, type="primary")
        if ok:
            user = verify_login(username.strip(), password)
            if user:
                st.session_state["auth_user"] = user
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않거나 비활성 계정입니다.")


def require_login():
    """로그인 게이트. 활성화되어 있고 미로그인이면 로그인 폼을 띄우고 중단한다."""
    if not auth_enabled():
        return
    if current_user():
        return
    _login_form()
    st.stop()
