"""로그인 게이트 · 세션 · 권한 헬퍼.

AUTH_ENABLED 플래그로 로그인 게이트를 켜고 끌 수 있다.
- secrets 또는 환경변수 AUTH_ENABLED 가 true 일 때만 로그인 요구.
- 기본값은 꺼짐(False) — 계정/로그인 테스트를 마친 뒤 켜서 잠김 위험을 방지.
"""
import os
import time
import json
import hmac
import base64
import hashlib
from datetime import datetime, timedelta

import streamlit as st

from utils.database import verify_login, get_user_by_id
from utils.style import inject_css

try:
    import extra_streamlit_components as stx
    _HAS_COOKIE = True
except Exception:
    _HAS_COOKIE = False

_COOKIE_NAME = "cmms_auth"
_TOKEN_DAYS = 7


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


# ─────────── 토큰(서명) / 쿠키 ───────────
def _secret() -> bytes:
    s = None
    try:
        s = st.secrets.get("AUTH_SECRET", None)
    except Exception:
        s = None
    if not s:
        s = os.environ.get("AUTH_SECRET", "cmms-default-secret-change-me")
    return str(s).encode("utf-8")


def _make_token(user: dict, days: int = _TOKEN_DAYS) -> str:
    payload = {"id": int(user["id"]), "u": user.get("username", ""),
               "exp": int(time.time()) + days * 86400}
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{sig}"


def _read_token(token: str):
    try:
        raw, sig = token.split(".")
        expected = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(raw.encode()))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def _cookie_manager():
    """세션당 1개의 CookieManager 인스턴스. 없으면 None."""
    if not _HAS_COOKIE:
        return None
    if "_cookie_mgr" not in st.session_state:
        try:
            st.session_state["_cookie_mgr"] = stx.CookieManager(key="cmms_cookie_mgr")
        except Exception:
            st.session_state["_cookie_mgr"] = None
    return st.session_state["_cookie_mgr"]


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
    cm = st.session_state.get("_cookie_mgr")
    if cm is not None:
        try:
            cm.delete(_COOKIE_NAME)
        except Exception:
            pass


def _login_form(cm=None):
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
            keep = st.checkbox("로그인 유지", value=True)
            ok = st.form_submit_button("로그인", use_container_width=True, type="primary")
        if ok:
            user = verify_login(username.strip(), password)
            if user:
                st.session_state["auth_user"] = user
                if keep and cm is not None:
                    try:
                        cm.set(_COOKIE_NAME, _make_token(user),
                               expires_at=datetime.now() + timedelta(days=_TOKEN_DAYS))
                    except Exception:
                        pass
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않거나 비활성 계정입니다.")


def require_login():
    """로그인 게이트. 활성화되어 있고 미로그인이면 로그인 폼을 띄우고 중단한다.
    쿠키에 유효한 토큰이 있으면 자동 로그인(세션 복원)."""
    if not auth_enabled():
        return
    if current_user():
        return

    cm = _cookie_manager()

    # 쿠키에서 자동 로그인 복원 시도
    token = None
    if cm is not None:
        try:
            token = cm.get(_COOKIE_NAME)
        except Exception:
            token = None
    if token:
        payload = _read_token(token)
        if payload:
            user = get_user_by_id(int(payload["id"]))
            if user:
                st.session_state["auth_user"] = user
                return

    _login_form(cm)
    st.stop()
