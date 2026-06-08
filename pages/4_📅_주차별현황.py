import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import get_weekly_pivot, get_maintenance, init_db
import pandas as pd
from datetime import datetime

init_db()

st.set_page_config(page_title="주차별 현황 · CMMS", page_icon="📅", layout="wide")

st.markdown("""
<style>
.page-header {
    background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%);
    color: white; padding: 20px 28px; border-radius: 12px; margin-bottom: 24px;
}
.page-header h1 { color: white; margin: 0; font-size: 1.6rem; }
.page-header p { color: #BFDBFE; margin: 4px 0 0; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <h1>📅 주차별 보전 현황표</h1>
    <p>설비별 주차(Week) 보전 건수 피벗 테이블</p>
</div>
""", unsafe_allow_html=True)

FACTORIES = ["전체", "광명A", "광명B", "광명C", "광명D", "화성A", "화성B"]

fc1, fc2 = st.columns([1, 1])
with fc1:
    year_sel = st.selectbox("연도", [2026, 2025])
with fc2:
    fac_sel = st.selectbox("팩토리", FACTORIES)

df_raw = get_weekly_pivot(
    year=year_sel,
    factory=None if fac_sel == "전체" else fac_sel,
)

if df_raw.empty:
    st.info("데이터가 없습니다. 보전내역을 먼저 등록하거나 Excel import를 사용하세요.")
else:
    # 피벗 테이블 생성
    pivot = df_raw.pivot_table(
        index=["factory", "equipment_code", "equipment_name"],
        columns="recv_week",
        values="cnt",
        aggfunc="sum",
        fill_value=0,
    )

    # 주차 컬럼명 포맷
    pivot.columns = [f"{int(w)}W" for w in pivot.columns]
    pivot["계"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("계", ascending=False)
    pivot = pivot.reset_index()
    pivot.columns.name = None

    # 요약 정보
    m1, m2, m3 = st.columns(3)
    m1.metric("설비 수", f"{len(pivot)}대")
    m2.metric("총 보전 건수", f"{int(pivot['계'].sum()):,}건")
    m3.metric("평균 건수/설비", f"{pivot['계'].mean():.1f}건")

    st.markdown("")

    # 데이터프레임 표시
    # 숫자 컬럼에서 0은 빈칸으로 표시
    week_cols = [c for c in pivot.columns if c.endswith("W") or c == "계"]
    df_display = pivot.copy()
    for col in week_cols:
        df_display[col] = df_display[col].apply(lambda x: "" if x == 0 else int(x))

    df_display.rename(columns={
        "factory": "팩토리",
        "equipment_code": "설비코드",
        "equipment_name": "설비명",
    }, inplace=True)

    st.dataframe(
        df_display,
        use_container_width=True,
        height=520,
        hide_index=True,
    )

    # 다운로드
    csv = pivot.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ CSV 다운로드",
        data=csv,
        file_name=f"주차별현황_{year_sel}_{fac_sel}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

    st.markdown("---")

    # 월별 집계 요약 (주차 → 월 변환)
    st.subheader("📊 월별 설비 Top 10")
    df_m = get_maintenance(
        factory=None if fac_sel == "전체" else fac_sel,
        year=year_sel,
    )
    if not df_m.empty:
        top_eq = df_m.groupby("equipment_code").size().reset_index(name="건수")
        top_eq = top_eq.sort_values("건수", ascending=False).head(10)
        import plotly.express as px
        fig = px.bar(
            top_eq, x="equipment_code", y="건수",
            color="건수", color_continuous_scale=["#BFDBFE", "#2563EB"],
            text="건수",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=300, plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=0, r=0, t=20, b=0),
            coloraxis_showscale=False,
            xaxis_title="설비코드", yaxis_title="건수",
        )
        st.plotly_chart(fig, use_container_width=True)
