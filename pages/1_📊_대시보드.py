import streamlit as st
import sys, os
import html
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import get_kpi, get_monthly_count, get_factory_count, get_issue_top, get_overdue, get_available_years, init_db
from utils.style import inject_css, page_header, kpi_cards, chart_title, style_plotly, IRIS, GOLD, CHART_SEQ, CHART_GRAD
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

init_db()

inject_css()

# ─── 헤더 ───
current_year = datetime.now().year
page_header("📊 대시보드", f"보전 현황 한눈에 보기 · {datetime.now().strftime('%Y년 %m월 %d일')}")

# ─── 연도 필터 ───
year_options = get_available_years()
if current_year not in year_options:
    year_options = [current_year] + year_options
col_f1, col_f2 = st.columns([1, 5])
with col_f1:
    year_sel = st.selectbox("연도", year_options, index=0, label_visibility="collapsed")

# ─── KPI 카드 ───
kpi = get_kpi(year_sel)
kpi_cards([
    {"label": "총 보전 건수", "value": f"{kpi['total']:,}건",  "icon": "📥", "color": "blue",   "sub": "전체 접수"},
    {"label": "완료",         "value": f"{kpi['done']:,}건",   "icon": "✅", "color": "green",  "sub": "처리 완료"},
    {"label": "미완료",       "value": f"{kpi['pending']:,}건","icon": "⏳", "color": "amber",  "sub": "진행 중 + 팬딩"},
    {"label": "처리율",       "value": f"{kpi['rate']}%",      "icon": "📈", "color": "purple", "sub": "목표 95%"},
    {"label": "평균 고장시간","value": f"{kpi['avg_down']}분", "icon": "⏱️", "color": "red",    "sub": "분 단위"},
])

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

# ═══════════════ 차트 Row 1 ═══════════════
chart_col1, chart_col2 = st.columns([1.5, 1], gap="medium")

with chart_col1:
    with st.container(border=True):
        chart_title("월별 보전 인입 추세", f"{year_sel}년 · 월별 접수 건수와 추세선")
        df_monthly = get_monthly_count(year_sel)
        if not df_monthly.empty:
            # 한글 컬럼명 정규화 이슈 회피: 위치 기반 ASCII 컬럼으로 통일
            df_monthly.columns = ["month", "count"]
            months_all = pd.DataFrame({"month": range(1, 13)})
            df_monthly = months_all.merge(df_monthly, on="month", how="left").fillna(0)
            df_monthly["label"] = df_monthly["month"].apply(lambda x: f"{int(x)}월")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_monthly["label"], y=df_monthly["count"],
                marker=dict(color=IRIS, line_width=0), name="건수",
                text=df_monthly["count"].astype(int),
                textposition="outside", textfont=dict(color="#9C978C", size=10),
                width=0.6, hovertemplate="%{x} · %{y}건<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df_monthly["label"], y=df_monthly["count"],
                mode="lines", line=dict(color=GOLD, width=2.5, shape="spline"),
                name="추세", hoverinfo="skip",
            ))
            style_plotly(fig, height=250, showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("데이터가 없습니다.")

with chart_col2:
    with st.container(border=True):
        chart_title("팩토리 분포", "팩토리별 보전 비중")
        df_fac = get_factory_count(year_sel)
        if not df_fac.empty:
            df_fac.columns = ["factory", "count"]
            total_fac = int(df_fac["count"].sum())
            fig2 = go.Figure(go.Pie(
                labels=df_fac["factory"], values=df_fac["count"],
                hole=0.62, sort=False,
                marker=dict(colors=CHART_SEQ, line=dict(color="white", width=2)),
                textinfo="percent", textfont=dict(size=11, color="white"),
                hovertemplate="%{label} · %{value}건 (%{percent})<extra></extra>",
            ))
            fig2.update_layout(
                annotations=[dict(text=f"<b>{total_fac}</b><br>총 건수", x=0.5, y=0.5,
                                  font=dict(size=15, color="#1A1814"), showarrow=False)],
            )
            style_plotly(fig2, height=250, showlegend=True)
            fig2.update_layout(legend=dict(orientation="v", x=1, y=0.5, font=dict(size=10)))
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("데이터가 없습니다.")

# ═══════════════ 차트 Row 2 ═══════════════
chart_col3, chart_col4 = st.columns([1.5, 1], gap="medium")

with chart_col3:
    with st.container(border=True):
        chart_title("이슈 유형 Top 10", "가장 빈번한 이슈코드")
        df_issue = get_issue_top(year_sel, 10)
        if not df_issue.empty:
            df_issue.columns = ["code", "count"]
            df_issue = df_issue.sort_values("count")
            fig3 = px.bar(
                df_issue,
                x="count", y="code",
                orientation="h",
                color="count",
                color_continuous_scale=CHART_GRAD,
                text="count",
            )
            fig3.update_traces(textposition="outside", textfont=dict(color="#9C978C", size=10),
                               marker_line_width=0, hovertemplate="%{y} · %{x}건<extra></extra>")
            style_plotly(fig3, height=260)
            fig3.update_layout(coloraxis_showscale=False, yaxis_title=None, xaxis_title=None)
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("데이터가 없습니다.")

with chart_col4:
    with st.container(border=True):
        chart_title("장기 미완료", "30일 이상 경과 건")
        df_over = get_overdue(30)
        if not df_over.empty:
            cards_html = '<div style="max-height:212px;overflow-y:auto;padding-right:4px;">'
            for _, row in df_over.iterrows():
                days = int(row["overdue_days"])
                color = "#D6485B" if days >= 60 else "#C98A18"
                fac_txt = html.escape(str(row['factory']))
                code_txt = html.escape(str(row['equipment_code']))
                desc_txt = html.escape(str(row['issue_desc'])[:28]) if row['issue_desc'] else '내용 없음'
                cards_html += f"""
                <div style="background:rgba(255,255,255,.7);border-left:3px solid {color};
                    padding:8px 12px;border-radius:0 10px 10px 0;margin:0 0 7px;
                    border:1px solid #EAE7E0;">
                    <div style="font-weight:700;font-size:0.82rem;color:#1A1814;">{fac_txt} · {code_txt}</div>
                    <div style="font-size:0.74rem;color:#6A655C;margin-top:2px;">{desc_txt}</div>
                    <div style="font-size:0.72rem;color:{color};font-weight:700;margin-top:3px;">⏰ {days}일 경과</div>
                </div>"""
            cards_html += "</div>"
            st.markdown(cards_html, unsafe_allow_html=True)
        else:
            st.success("✅ 30일 이상 미완료 건 없음")

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
