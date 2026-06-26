import streamlit as st

# ─── 공통 CSS ────────────────────────────────────────────────
_COMMON_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown, .stDataFrame, button, select, input, textarea {
    font-family: 'Noto Sans KR', sans-serif !important;
    -webkit-font-smoothing: antialiased;
}

/* ── 사이드바 ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #18345E 0%, #1B3B6F 100%);
    box-shadow: 2px 0 12px rgba(0,0,0,0.18);
}
section[data-testid="stSidebar"] * { color: #A8C8EE !important; }
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] span { color: #A8C8EE !important; }

/* ── 페이지 헤더 ── */
.page-header {
    display: flex; align-items: center; gap: 14px;
    background: linear-gradient(135deg, #18345E 0%, #2A6DE8 100%);
    padding: 14px 22px; border-radius: 12px; margin-bottom: 20px;
}
.page-header-icon {
    width: 44px; height: 44px; border-radius: 11px; flex-shrink: 0;
    background: rgba(255,255,255,0.15);
    display: flex; align-items: center; justify-content: center; font-size: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.page-header h1 { color: #fff; margin: 0; font-size: 1.2rem; font-weight: 800; letter-spacing: -0.3px; }
.page-header p  { color: #93C5FD; margin: 3px 0 0; font-size: 0.8rem; font-weight: 400; }

/* ── KPI 카드 그리드 ── */
.kpi-grid {
    display: grid; gap: 14px; margin-bottom: 18px;
}
.kpi-grid-4 { grid-template-columns: repeat(4, 1fr); }
.kpi-grid-5 { grid-template-columns: repeat(5, 1fr); }

.kpi-card {
    background: #fff; border-radius: 13px; padding: 17px 20px;
    position: relative; overflow: hidden;
    border: 1px solid transparent;
    transition: transform 0.15s, box-shadow 0.15s;
    cursor: default;
}
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; border-radius: 13px 13px 0 0;
}
.kpi-card:hover { transform: translateY(-2px); }

/* 색상 테마 */
.kpi-blue   { border-color: #C3D9FF; background: linear-gradient(145deg,#fff 55%,#EBF2FF); box-shadow: 0 2px 4px rgba(42,109,232,0.07), 0 6px 18px rgba(42,109,232,0.1); }
.kpi-green  { border-color: #B5EEDA; background: linear-gradient(145deg,#fff 55%,#EAFAF3); box-shadow: 0 2px 4px rgba(11,169,115,0.07), 0 6px 18px rgba(11,169,115,0.1); }
.kpi-amber  { border-color: #FFE49A; background: linear-gradient(145deg,#fff 55%,#FFF8E6); box-shadow: 0 2px 4px rgba(214,138,0,0.07),  0 6px 18px rgba(214,138,0,0.1); }
.kpi-purple { border-color: #D4BCFF; background: linear-gradient(145deg,#fff 55%,#F3EEFF); box-shadow: 0 2px 4px rgba(107,63,212,0.07),  0 6px 18px rgba(107,63,212,0.1); }
.kpi-red    { border-color: #FFBCBC; background: linear-gradient(145deg,#fff 55%,#FFF0F0); box-shadow: 0 2px 4px rgba(214,58,58,0.07),   0 6px 18px rgba(214,58,58,0.1); }

.kpi-blue::before   { background: linear-gradient(90deg,#3B82F6,#60A5FA); }
.kpi-green::before  { background: linear-gradient(90deg,#0BA973,#34D399); }
.kpi-amber::before  { background: linear-gradient(90deg,#D68A00,#F59E0B); }
.kpi-purple::before { background: linear-gradient(90deg,#6B3FD4,#A78BFA); }
.kpi-red::before    { background: linear-gradient(90deg,#D63A3A,#F87171); }

.kpi-blue:hover   { box-shadow: 0 4px 8px rgba(42,109,232,0.12),  0 10px 28px rgba(42,109,232,0.16); }
.kpi-green:hover  { box-shadow: 0 4px 8px rgba(11,169,115,0.12),  0 10px 28px rgba(11,169,115,0.16); }
.kpi-amber:hover  { box-shadow: 0 4px 8px rgba(214,138,0,0.12),   0 10px 28px rgba(214,138,0,0.16); }
.kpi-purple:hover { box-shadow: 0 4px 8px rgba(107,63,212,0.12),  0 10px 28px rgba(107,63,212,0.16); }
.kpi-red:hover    { box-shadow: 0 4px 8px rgba(214,58,58,0.12),   0 10px 28px rgba(214,58,58,0.16); }

.kpi-top    { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.kpi-lbl    { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }
.kpi-blue .kpi-lbl   { color: #2A6DE8; }
.kpi-green .kpi-lbl  { color: #0BA973; }
.kpi-amber .kpi-lbl  { color: #D68A00; }
.kpi-purple .kpi-lbl { color: #6B3FD4; }
.kpi-red .kpi-lbl    { color: #D63A3A; }

.kpi-ico {
    width: 34px; height: 34px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center; font-size: 16px;
}
.kpi-blue .kpi-ico   { background: #EBF2FF; }
.kpi-green .kpi-ico  { background: #EAFAF3; }
.kpi-amber .kpi-ico  { background: #FFF8E6; }
.kpi-purple .kpi-ico { background: #F3EEFF; }
.kpi-red .kpi-ico    { background: #FFF0F0; }

.kpi-val  { font-size: 28px; font-weight: 800; color: #0D1F3C; line-height: 1; letter-spacing: -1px; }
.kpi-sub  { font-size: 11px; color: #94AABB; margin-top: 6px; font-weight: 500; }

/* ── 상태 배지 ── */
.badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 700;
}
.badge-ing    { background: #FFF8E6; color: #D68A00; border: 1px solid #FFE49A; }
.badge-done   { background: #EAFAF3; color: #0BA973; border: 1px solid #B5EEDA; }
.badge-pend   { background: #F4F6F9; color: #5B7799; border: 1px solid #DDE6F0; }
.badge-broken { background: #FFF0F0; color: #D63A3A; border: 1px solid #FFBCBC; }
.badge-cancel { background: #F4F6F9; color: #9BAEC4; border: 1px solid #DDE6F0; }

.led { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; display: inline-block; }
.led-ing    { background: #D68A00; box-shadow: 0 0 5px rgba(214,138,0,0.7); }
.led-done   { background: #0BA973; box-shadow: 0 0 5px rgba(11,169,115,0.7); }
.led-pend   { background: #9BAEC4; }
.led-broken { background: #D63A3A; box-shadow: 0 0 5px rgba(214,58,58,0.6); }
.led-cancel { background: #9BAEC4; }

/* ── 카드형 패널 ── */
.panel-card {
    background: #fff; border: 1px solid #DDE6F0; border-radius: 12px;
    padding: 16px 20px; margin-bottom: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 10px rgba(0,0,0,0.03);
}

/* ── 데이터프레임 ── */
.stDataFrame thead tr th {
    background: #F7FAFD !important; color: #5B7799 !important;
    font-weight: 700 !important; font-size: 11px !important;
    text-transform: uppercase; letter-spacing: 0.6px;
}
.stDataFrame tbody tr:hover td { background: #F5F9FF !important; }

/* ── 버튼 ── */
.stButton > button {
    border-radius: 8px !important; font-weight: 700 !important;
    font-family: 'Noto Sans KR', sans-serif !important;
    transition: all 0.15s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg,#3B82F6,#1D6FF5) !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.35) !important;
    border: none !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 14px rgba(37,99,235,0.5) !important;
    transform: translateY(-1px) !important;
}

/* ── 구분선 ── */
hr { border-color: #EEF3F9 !important; }
"""

# 상태 → (배지 클래스, LED 클래스) 매핑
_STATUS_BADGE = {
    "진행 중": ("badge-ing",    "led-ing"),
    "완료":    ("badge-done",   "led-done"),
    "팬딩":    ("badge-pend",   "led-pend"),
    "고장":    ("badge-broken", "led-broken"),
    "취소":    ("badge-cancel", "led-cancel"),
}

# KPI 색상 순환
_KPI_COLORS = ["blue", "green", "amber", "purple", "red"]


def inject_css(extra: str = "") -> None:
    """공통 CSS + 페이지별 추가 CSS 주입"""
    st.markdown(f"<style>{_COMMON_CSS + extra}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    """상단 슬림 헤더 렌더링"""
    icon = title.split()[0] if title else "🔧"
    rest = " ".join(title.split()[1:]) if len(title.split()) > 1 else title
    st.markdown(f"""
<div class="page-header">
    <div class="page-header-icon">{icon}</div>
    <div><h1>{rest}</h1><p>{subtitle}</p></div>
</div>""", unsafe_allow_html=True)


def kpi_cards(cards: list) -> None:
    """
    KPI 카드 그리드 렌더링.

    cards = [
        {"label": "총 접수", "value": "1건", "icon": "📦", "color": "blue", "sub": "전체 보전"},
        ...
    ]
    color: "blue" | "green" | "amber" | "purple" | "red"
    """
    n = len(cards)
    grid_cls = "kpi-grid-5" if n >= 5 else "kpi-grid-4"
    items = ""
    for i, c in enumerate(cards):
        color = c.get("color", _KPI_COLORS[i % len(_KPI_COLORS)])
        items += f"""
<div class="kpi-card kpi-{color}">
    <div class="kpi-top">
        <span class="kpi-lbl">{c['label']}</span>
        <div class="kpi-ico">{c.get('icon','')}</div>
    </div>
    <div class="kpi-val">{c['value']}</div>
    <div class="kpi-sub">{c.get('sub','')}</div>
</div>"""
    st.markdown(f'<div class="kpi-grid {grid_cls}">{items}</div>', unsafe_allow_html=True)


def status_badge(status: str) -> str:
    """상태 문자열 → HTML 배지 반환"""
    bc, lc = _STATUS_BADGE.get(status, ("badge-pend", "led-pend"))
    return f'<span class="badge {bc}"><span class="led {lc}"></span>{status}</span>'
