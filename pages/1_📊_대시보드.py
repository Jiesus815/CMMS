import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import get_kpi, get_monthly_count, get_factory_count, get_issue_top, get_overdue, init_db
from utils.style import inject_css, page_header, kpi_cards
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

init_db()

st.set_page_config(page_title="대시보드 · CMMS", page_icon="📊", layout="wide")
inject_css("""
.alert-box {
    background: #FFF7ED; border-left: 4px solid #F97316;
    padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 8px 0;
}
""")

# ─── 헤더 ───
current_year = datetime.now().year
page_header("📊 대시보드", f"보전 현황 한눈에 보기 · {datetime.now().strftime('%Y년 %m월 %d일')}")

# ─── 연도 필터 ───
col_f1, col_f2 = st.columns([1, 5])
with col_f1:
    year_sel = st.selectbox("연도", [current_year, current_year - 1], index=0, label_visibility="collapsed")

# ─── KPI 카드 ───
kpi = get_kpi(year_sel)
kpi_cards([
    {"label": "총 보전 건수", "value": f"{kpi['total']:,}건",  "icon": "📥", "color": "blue",   "sub": "전체 접수"},
    {"label": "완료",         "value": f"{kpi['done']:,}건",   "icon": "✅", "color": "green",  "sub": "처리 완료"},
    {"label": "미완료",       "value": f"{kpi['pending']:,}건","icon": "⏳", "color": "amber",  "sub": "진행 중 + 팬딩"},
    {"label": "처리율",       "value": f"{kpi['rate']}%",      "icon": "📈", "color": "purple", "sub": "목표 95%"},
    {"label": "평균 고장시간","value": f"{kpi['avg_down']}분", "icon": "⏱️", "color": "red",    "sub": "분 단위"},
])

st.markdown("---")

# ─── 차트 Row 1 ───
chart_col1, chart_col2 = st.columns([3, 2])

with chart_col1:
    st.subheader("📅 월별 보전 인입 건수")
    df_monthly = get_monthly_count(year_sel)
    if not df_monthly.empty:
        months_all = pd.DataFrame({"월": range(1, 13)})
        df_monthly = months_all.merge(df_monthly, on="월", how="left").fillna(0)
        df_monthly["월명"] = df_monthly["월"].apply(lambda x: f"{int(x)}월")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_monthly["월명"], y=df_monthly["건수"],
            marker_color="#2563EB", name="보전건수",
            text=df_monthly["건수"].astype(int),
            textposition="outside",
        ))
        fig.add_trace(go.Scatter(
            x=df_monthly["월명"], y=df_monthly["건수"],
            mode="lines+markers", line=dict(color="#F97316", width=2),
            marker=dict(size=6), name="추세",
        ))
        fig.update_layout(
            height=320, plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation="h", y=1.1),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("데이터가 없습니다.")

with chart_col2:
    st.subheader("🏭 팩토리별 건수")
    df_fac = get_factory_count(year_sel)
    if not df_fac.empty:
        colors = ["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE"]
        fig2 = px.pie(
            df_fac, names="팩토리", values="건수",
            color_discrete_sequence=colors,
            hole=0.45,
        )
        fig2.update_traces(textposition="outside", textinfo="label+percent")
        fig2.update_layout(
            height=320, margin=dict(l=0, r=0, t=20, b=0),
            showlegend=False, paper_bgcolor="white",
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("데이터가 없습니다.")

# ─── 차트 Row 2 ───
chart_col3, chart_col4 = st.columns([3, 2])

with chart_col3:
    st.subheader("🔩 이슈 유형 Top 15")
    df_issue = get_issue_top(year_sel, 15)
    if not df_issue.empty:
        fig3 = px.bar(
            df_issue.sort_values("건수"),
            x="건수", y="이슈코드",
            orientation="h",
            color="건수",
            color_continuous_scale=["#BFDBFE", "#2563EB"],
            text="건수",
        )
        fig3.update_traces(textposition="outside")
        fig3.update_layout(
            height=380, plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=0, r=0, t=20, b=0),
            coloraxis_showscale=False,
            xaxis=dict(showgrid=True, gridcolor="#F1F5F9"),
            yaxis=dict(showgrid=False),
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("데이터가 없습니다.")

with chart_col4:
    st.subheader("🚨 미완료 장기 건 (30일+)")
    df_over = get_overdue(30)
    if not df_over.empty:
        for _, row in df_over.iterrows():
            days = int(row["경과일수"])
            color = "#DC2626" if days >= 60 else "#F97316"
            st.markdown(f"""
            <div style="background:white;border-left:4px solid {color};
                padding:10px 14px;border-radius:0 8px 8px 0;margin:6px 0;
                border:1px solid #E2E8F0;">
                <div style="font-weight:600;font-size:0.9rem;color:#1E293B;">
                    {row['factory']} · {row['equipment_code']}
                </div>
                <div style="font-size:0.82rem;color:#64748B;margin-top:2px;">
                    {row['issue_desc'][:30] if row['issue_desc'] else '내용 없음'}
                </div>
                <div style="font-size:0.8rem;color:{color};font-weight:600;margin-top:4px;">
                    ⏰ {days}일 경과 · {row['status']}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ 30일 이상 미완료 건이 없습니다!")

st.markdown("---")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
