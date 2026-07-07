import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
import pandas as pd

from utils.database import get_slack_requests, get_slack_unmatched, init_db
from utils.style import inject_css, page_header

init_db()

inject_css()

page_header("💬 슬랙 보전요청 연동", "슬랙 채널에서 보전 요청을 자동으로 수집합니다")

# ─── Bot Token 로드 ──────────────────────────────────────────────
def _get_token() -> str | None:
    try:
        return st.secrets["slack"]["bot_token"]
    except Exception:
        return None

# ─── 사이드바: 설정 & 동기화 ────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 슬랙 연동 설정")

    token_from_secrets = _get_token()

    if token_from_secrets:
        st.success("Bot Token: secrets 에서 로드됨")
        bot_token = token_from_secrets
    else:
        bot_token = st.text_input(
            "Slack Bot Token",
            type="password",
            placeholder="xoxb-...",
            help=".streamlit/secrets.toml의 [slack] bot_token 에 저장하면 매번 입력 불필요",
        )

    st.markdown("---")
    st.markdown("**동기화 범위**")
    full_resync = st.checkbox(
        "전체 재수집",
        value=False,
        help="체크 시 처음부터 전부 다시 수집합니다. 평소에는 꺼두세요 (마지막 동기화 이후 새 메시지만 가져옴)",
    )
    oldest_ts = "0" if full_resync else "auto"

    sync_btn = st.button("🔄 지금 동기화", use_container_width=True, type="primary")

    st.markdown("---")
    st.markdown(
        """
        **필요 Bot 권한 (OAuth Scopes)**
        - `channels:read`
        - `channels:history`
        - `groups:read`
        - `groups:history`
        - `reactions:read`
        """
    )

# ─── 동기화 실행 ─────────────────────────────────────────────────
if sync_btn:
    if not bot_token:
        st.error("Bot Token을 입력하거나 secrets.toml에 설정해주세요.")
    else:
        with st.spinner("슬랙 채널 동기화 중..."):
            try:
                from utils.slack_sync import run_full_sync
                results = run_full_sync(bot_token, oldest=oldest_ts)
            except Exception as e:
                st.error(f"동기화 오류: {e}")
                results = {}

        if results:
            st.success(f"동기화 완료 — {len(results)}개 채널 처리")
            for ch_name, stats in results.items():
                if "error" in stats:
                    st.warning(f"⚠️ `{ch_name}`: {stats['error']}")
                else:
                    st.info(
                        f"📌 **{ch_name}** — 처리 {stats.get('processed', 0)}건 "
                        f"/ 건너뜀 {stats.get('skipped', 0)}건 "
                        f"/ 미매칭 {stats.get('unmatched', 0)}건"
                    )
        else:
            st.warning("보전요청 채널을 찾을 수 없거나 처리할 메시지가 없습니다.")

st.markdown("---")

# ─── 탭 ─────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📋 수집된 보전요청", "⚠️ 미매칭 데이터"])

# ══════════════════════════════
# 탭1: 수집된 보전요청 목록
# ══════════════════════════════
with tab1:
    fc1, fc2, fc3 = st.columns([2, 2, 1])
    with fc1:
        f_status = st.selectbox("진행상태", ["전체", "진행 중", "완료"], key="sl_status")
    with fc2:
        f_channel = st.text_input("채널명 필터", placeholder="예: 클린허브", key="sl_ch")
    with fc3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔍 조회", key="sl_search"):
            pass

    df = get_slack_requests(
        status=None if f_status == "전체" else f_status,
        channel_name=f_channel.strip() if f_channel.strip() else None,
    )

    if df.empty:
        st.info("수집된 보전요청이 없습니다. 동기화를 실행해 주세요.")
    else:
        # KPI
        total = len(df)
        done = len(df[df["status"] == "완료"])
        in_prog = len(df[df["status"] == "진행 중"])
        unmatched = len(df[df["is_matched"] == False])

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("전체", total)
        k2.metric("진행 중", in_prog)
        k3.metric("완료", done)
        k4.metric("미매칭", unmatched)

        st.markdown("---")

        # 표시 컬럼 정리
        show_cols = {
            "recv_date": "접수일",
            "channel_name": "채널",
            "factory": "팩토리",
            "equipment": "설비명/위치",
            "symptom": "증상",
            "inspection": "점검사항",
            "assignee": "담당자",
            "status": "진행상태",
            "is_matched": "매칭여부",
        }
        df_view = df[[c for c in show_cols if c in df.columns]].rename(columns=show_cols)

        # 상태 배지
        def status_badge(val):
            if val == "완료":
                return "✅ 완료"
            elif val == "진행 중":
                return "🔄 진행 중"
            return val

        if "진행상태" in df_view.columns:
            df_view["진행상태"] = df_view["진행상태"].apply(status_badge)

        if "매칭여부" in df_view.columns:
            df_view["매칭여부"] = df_view["매칭여부"].apply(lambda x: "✅" if x else "❌")

        st.dataframe(df_view, use_container_width=True, hide_index=True)

        # 엑셀 다운로드
        csv = df_view.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 CSV 다운로드", csv, "slack_requests.csv", "text/csv")

# ══════════════════════════════
# 탭2: 미매칭 데이터
# ══════════════════════════════
with tab2:
    st.caption(
        "팩토리명 또는 설비명이 기존 데이터(FACTORIES 목록 / equipment 테이블)와 "
        "일치하지 않는 보전요청입니다. 설비 데이터 추가 또는 이름 정규화에 활용하세요."
    )

    df_um = get_slack_unmatched()

    if df_um.empty:
        st.success("미매칭 데이터가 없습니다.")
    else:
        st.warning(f"⚠️ 미매칭 {len(df_um)}건")

        show_cols_um = {
            "recv_date": "접수일",
            "channel_name": "채널",
            "factory_raw": "팩토리(원본)",
            "equipment_raw": "설비명(원본)",
            "symptom": "증상",
            "req_status": "진행상태",
        }
        df_um_view = df_um[[c for c in show_cols_um if c in df_um.columns]].rename(columns=show_cols_um)
        st.dataframe(df_um_view, use_container_width=True, hide_index=True)

        csv_um = df_um_view.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 미매칭 CSV 다운로드", csv_um, "slack_unmatched.csv", "text/csv")
