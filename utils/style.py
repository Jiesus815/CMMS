import streamlit as st

# ─── 공통 CSS · Atelier 디자인 시스템 ────────────────────────────
# 에디토리얼 럭셔리: 세리프 헤드라인 · 웜 아이보리 · 아이리스+골드 액센트 · 필름 그레인
_COMMON_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');

:root {
    --iris:    #6E62E6;
    --iris-2:  #9A7CF0;
    --iris-ink:#4B41B8;
    --gold:    #C9A24B;
    --ok:   #2FA37A; --warn: #C98A18; --err: #D6485B;

    --bg:       #F7F6F3;
    --bg-tint:  #F1EFEA;
    --surface:  #FFFFFF;
    --border:   #EAE7E0;
    --border-2: #E1DDD4;
    --hair:     linear-gradient(90deg,transparent,rgba(0,0,0,.08),transparent);

    --tx1: #1A1814;
    --tx2: #6A655C;
    --tx3: #9C978C;

    --r-xl: 22px; --r-lg: 18px; --r-md: 13px; --r-sm: 10px;
    --sh-sm: 0 1px 2px rgba(26,24,20,.05), 0 2px 8px rgba(26,24,20,.04);
    --sh-md: 0 8px 30px rgba(26,24,20,.09), 0 2px 8px rgba(26,24,20,.05);
    --ease: cubic-bezier(.32,.72,0,1);
}

html, body, [class*="css"], .stMarkdown, button, select, input, textarea {
    font-family: 'Noto Sans KR','Inter',sans-serif !important;
    -webkit-font-smoothing: antialiased;
    letter-spacing: -.01em;
}
.serif { font-family:'Instrument Serif','Noto Sans KR',serif !important; }
.num   { font-family:'Inter','Noto Sans KR',sans-serif !important; font-variant-numeric: tabular-nums; letter-spacing:-.02em; }

/* ── 앱 배경: 그라디언트 메시 ── */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(900px 500px at 12% -8%, rgba(110,98,230,.10), transparent 60%),
        radial-gradient(700px 460px at 92% 0%, rgba(201,162,75,.09), transparent 55%),
        #F7F6F3;
}
[data-testid="stHeader"] { background: transparent; }

/* 필름 그레인 오버레이 */
[data-testid="stAppViewContainer"]::after {
    content:''; position:fixed; inset:0; pointer-events:none; z-index:0; opacity:.45; mix-blend-mode:soft-light;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.55'/%3E%3C/svg%3E");
}
.main .block-container { position: relative; z-index: 1; padding-top: 2.6rem; }

/* ── 사이드바 ── */
section[data-testid="stSidebar"] {
    background: rgba(255,255,255,.72);
    backdrop-filter: blur(14px) saturate(1.2);
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] * { color: var(--tx1) !important; }
section[data-testid="stSidebar"] a { font-weight: 500 !important; }

/* ── 에디토리얼 페이지 헤더 ── */
.ateli-head { margin-bottom: 26px; animation: rise .5s var(--ease) both; }
.ah-eyebrow { display:flex; align-items:center; gap:9px; margin-bottom: 6px; }
.ah-emoji {
    width: 34px; height: 34px; border-radius: 10px; flex-shrink:0;
    background: linear-gradient(145deg, var(--iris), var(--iris-2));
    display:flex; align-items:center; justify-content:center; font-size:16px;
    box-shadow: 0 6px 16px rgba(110,98,230,.35), inset 0 1px 0 rgba(255,255,255,.3);
}
.ah-kicker { font-size:.66rem; font-weight:600; letter-spacing:.22em; text-transform:uppercase; color: var(--iris); }
.ah-title { font-family:'Instrument Serif','Noto Sans KR',serif; font-weight:400; font-size:2.6rem; line-height:1.02; margin:2px 0 0; letter-spacing:-.015em;
    background: linear-gradient(120deg, var(--tx1) 55%, var(--iris-ink)); -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; color: var(--tx1); }
.ah-sub   { font-size:.86rem; color: var(--tx2); margin:7px 0 0; letter-spacing:.005em; }
.ah-divider { margin-top:18px; height:1px; background: var(--hair); }

/* ── KPI 그리드 ── */
.kpi-grid { display:grid; gap:14px; margin-bottom:22px; }
.kpi-grid-3 { grid-template-columns: repeat(3, 1fr); }
.kpi-grid-4 { grid-template-columns: repeat(4, 1fr); }
.kpi-grid-5 { grid-template-columns: repeat(5, 1fr); }

.kpi-card {
    background:
        linear-gradient(180deg, rgba(255,255,255,.9), rgba(255,255,255,.72)),
        var(--surface);
    border:1px solid var(--border); border-radius: var(--r-lg);
    padding: 20px 22px 18px; position:relative; overflow:hidden;
    box-shadow: var(--sh-sm); animation: rise .55s var(--ease) both;
    transition: transform .28s var(--ease), box-shadow .28s var(--ease), border-color .28s var(--ease);
    backdrop-filter: blur(6px);
}
.kpi-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:2px;
    background: linear-gradient(90deg, var(--iris), var(--gold));
    opacity:.5; transition: opacity .3s var(--ease);
}
.kpi-card::after {
    content:''; position:absolute; right:-40px; top:-40px; width:120px; height:120px;
    background: radial-gradient(circle, rgba(110,98,230,.10), transparent 70%);
    pointer-events:none; opacity:0; transition: opacity .35s var(--ease);
}
.kpi-card:hover { transform: translateY(-5px); box-shadow: var(--sh-md); border-color: var(--border-2); }
.kpi-card:hover::before { opacity:1; }
.kpi-card:hover::after { opacity:1; }

.kpi-top { display:flex; align-items:center; gap:8px; }
.kpi-lbl { font-size:.75rem; font-weight:600; color: var(--tx2); letter-spacing:.01em; }
.kpi-dot { width:7px; height:7px; border-radius:50%; flex-shrink:0; }
.dot-iris{ background: var(--iris); box-shadow:0 0 0 3px rgba(110,98,230,.16); }
.dot-ok  { background: var(--ok);   box-shadow:0 0 0 3px rgba(47,163,122,.16); }
.dot-warn{ background: var(--warn); box-shadow:0 0 0 3px rgba(201,138,24,.16); }
.dot-gold{ background: var(--gold); box-shadow:0 0 0 3px rgba(201,162,75,.16); }
.dot-err { background: var(--err);  box-shadow:0 0 0 3px rgba(214,72,91,.16); }
.dot-mute{ background: var(--tx3);  box-shadow:0 0 0 3px rgba(156,151,140,.16); }

.kpi-ico { display:none; }  /* Atelier: 아이콘 대신 도트 사용 */
.kpi-val {
    font-family:'Inter','Noto Sans KR',sans-serif; font-weight:800; font-size:34px; line-height:1;
    letter-spacing:-.03em; margin-top:16px; font-variant-numeric: tabular-nums; white-space: nowrap;
    background: linear-gradient(135deg, var(--tx1) 30%, var(--iris-ink)); -webkit-background-clip: text;
    background-clip: text; -webkit-text-fill-color: transparent; color: var(--tx1);
}
.kpi-sub { font-size:.72rem; color: var(--tx3); margin-top:11px; font-weight:500; }

/* ── 상태 배지 ── */
.badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 3px 10px; border-radius: 999px; font-size: 11.5px; font-weight: 600;
    background: var(--bg-tint); color: var(--tx2); border: 1px solid var(--border);
}
.badge-ing    { color:#9A6B10; } .badge-ing .led    { background:#C98A18; animation: pulse 1.8s var(--ease) infinite; }
.badge-done   { color:#217D5C; } .badge-done .led   { background:#2FA37A; }
.badge-pend   { color:#6A655C; } .badge-pend .led   { background:#9C978C; }
.badge-broken { color:#BE3A4C; } .badge-broken .led { background:#D6485B; animation: pulse 1.3s var(--ease) infinite; }
.badge-cancel { color:#9C978C; } .badge-cancel .led { background:#9C978C; }
.led { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; display: inline-block; }

/* ── 카드형 패널 ── */
.panel-card {
    background: var(--surface); border:1px solid var(--border); border-radius: var(--r-xl);
    padding: 22px 24px; margin-bottom: 16px; box-shadow: var(--sh-sm);
}

/* ── st.container(border=True) 프리미엄 카드화 ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(180deg, rgba(255,255,255,.9), rgba(255,255,255,.7));
    border: 1px solid var(--border) !important; border-radius: var(--r-lg) !important;
    padding: 16px 18px !important; box-shadow: var(--sh-sm);
    backdrop-filter: blur(6px);
    transition: box-shadow .28s var(--ease), transform .28s var(--ease);
}
[data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow: var(--sh-md); }

/* ── 차트 카드 타이틀 ── */
.chart-title {
    font-family:'Instrument Serif','Noto Sans KR',serif; font-size:1.2rem; font-weight:400;
    color: var(--tx1); margin:0 0 1px; display:flex; align-items:center; gap:9px; letter-spacing:-.01em;
}
.chart-title .ct-dot { width:8px; height:8px; border-radius:50%; background: linear-gradient(145deg,var(--iris),var(--gold)); box-shadow:0 0 0 3px rgba(110,98,230,.14); flex-shrink:0; }
.chart-cap { font-size:.72rem; color: var(--tx3); margin:0 0 10px 17px; font-weight:500; }

/* ── st.metric ── */
[data-testid="stMetric"] {
    background: var(--surface); border:1px solid var(--border); border-radius: var(--r-lg);
    padding: 16px 18px; box-shadow: var(--sh-sm);
}
[data-testid="stMetricLabel"] p { font-size:.76rem !important; color: var(--tx2) !important; font-weight:500 !important; }
[data-testid="stMetricValue"] {
    font-family:'Inter','Noto Sans KR',sans-serif !important; font-weight:800 !important;
    letter-spacing:-.03em; color: var(--tx1) !important; font-variant-numeric: tabular-nums;
}

/* ── 제목(st.subheader/markdown h2·h3) → 세리프 ── */
.main .block-container h1,
.main .block-container h2,
.main .block-container h3 {
    font-family:'Instrument Serif','Noto Sans KR',serif !important;
    font-weight:400 !important; letter-spacing:-.01em; color: var(--tx1);
}

/* ── 탭 ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 3px; padding: 4px; background: var(--bg-tint);
    border: 1px solid var(--border); border-radius: 12px;
}
.stTabs [data-baseweb="tab"] {
    height: auto; padding: 8px 18px; border-radius: 9px;
    font-weight: 500; font-size: .85rem; color: var(--tx2);
    background: transparent; border: none;
}
.stTabs [aria-selected="true"] {
    background: var(--surface) !important; color: var(--tx1) !important;
    font-weight: 600 !important; box-shadow: var(--sh-sm);
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }

/* ── 데이터프레임 ── */
.stDataFrame { border-radius: var(--r-md); overflow: hidden; border:1px solid var(--border); box-shadow: var(--sh-sm); }
.stDataFrame thead tr th {
    background: var(--bg-tint) !important; color: var(--tx3) !important;
    font-weight: 700 !important; font-size: 11px !important;
    text-transform: uppercase; letter-spacing: .08em;
}
.stDataFrame tbody tr:hover td { background: rgba(110,98,230,.05) !important; }

/* ── 입력 요소 ── */
[data-baseweb="select"] > div, .stTextInput input, .stNumberInput input, .stDateInput input {
    border-radius: var(--r-sm) !important; border-color: var(--border-2) !important;
    background: var(--surface) !important;
}
[data-baseweb="select"] > div:focus-within, .stTextInput input:focus {
    border-color: var(--iris) !important; box-shadow: 0 0 0 3px rgba(110,98,230,.14) !important;
}

/* ── 버튼 ── */
.stButton > button {
    border-radius: var(--r-sm) !important; font-weight: 600 !important;
    font-family: 'Noto Sans KR','Inter',sans-serif !important;
    border: 1px solid var(--border-2) !important; color: var(--tx1) !important;
    background: var(--surface) !important; transition: all .16s var(--ease) !important;
}
.stButton > button:hover { background: var(--bg-tint) !important; }
.stButton > button[kind="primary"] {
    background: linear-gradient(145deg, var(--iris), var(--iris-ink)) !important;
    color: #fff !important; border: none !important;
    box-shadow: 0 6px 18px rgba(110,98,230,.35), inset 0 1px 0 rgba(255,255,255,.2) !important;
}
.stButton > button[kind="primary"]:hover { filter: brightness(1.06); }

/* ── 파일 업로더 ── */
[data-testid="stFileUploaderDropzone"] {
    border: 1.5px dashed var(--border-2) !important; border-radius: var(--r-lg) !important;
    background: var(--surface) !important;
}

/* ── st.info / success / warning 등 ── */
[data-testid="stAlert"] { border-radius: var(--r-md); }

/* ── 코드 인라인 ── */
code { background: rgba(110,98,230,.09) !important; color: var(--iris-ink) !important;
    border-radius: 6px; font-family:'Inter',monospace !important; font-weight:600; }

/* ── 구분선 ── */
hr { border: none; height: 1px; background: var(--hair) !important; }

/* ── 애니메이션 ── */
@keyframes rise  { from { opacity:0; transform: translateY(12px); } to { opacity:1; transform:none; } }
@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.4; } }

/* ── 스크롤바 ── */
::-webkit-scrollbar { width:10px; height:10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(156,151,140,.4); border-radius:999px; border:3px solid transparent; background-clip: padding-box; }
::-webkit-scrollbar-thumb:hover { background: var(--tx3); background-clip: padding-box; }

@media (prefers-reduced-motion: reduce) { *,*::before,*::after { animation:none !important; transition:none !important; } }
"""

# 상태 → 배지 클래스 매핑
_STATUS_BADGE = {
    "진행 중": "badge-ing",
    "완료":    "badge-done",
    "팬딩":    "badge-pend",
    "고장":    "badge-broken",
    "취소":    "badge-cancel",
}

# KPI color 키 → 도트 클래스 매핑
_KPI_DOT = {
    "blue":   "dot-iris",
    "green":  "dot-ok",
    "amber":  "dot-warn",
    "purple": "dot-gold",
    "red":    "dot-err",
}

# KPI 색상 순환
_KPI_COLORS = ["blue", "green", "amber", "purple", "red"]


def inject_css(extra: str = "") -> None:
    """공통 CSS + 페이지별 추가 CSS 주입"""
    st.markdown(f"<style>{_COMMON_CSS + extra}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    """에디토리얼 페이지 헤더 렌더링"""
    icon = title.split()[0] if title else "🔧"
    rest = " ".join(title.split()[1:]) if len(title.split()) > 1 else title
    st.markdown(f"""
<div class="ateli-head">
    <div class="ah-eyebrow">
        <span class="ah-emoji">{icon}</span>
        <span class="ah-kicker">스마팩 CMMS</span>
    </div>
    <h1 class="ah-title">{rest}</h1>
    <p class="ah-sub">{subtitle}</p>
    <div class="ah-divider"></div>
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
    if n >= 5:
        grid_cls = "kpi-grid-5"
    elif n == 3:
        grid_cls = "kpi-grid-3"
    else:
        grid_cls = "kpi-grid-4"
    items = ""
    for i, c in enumerate(cards):
        color = c.get("color", _KPI_COLORS[i % len(_KPI_COLORS)])
        dot = _KPI_DOT.get(color, "dot-iris")
        items += f"""
<div class="kpi-card">
    <div class="kpi-top">
        <span class="kpi-dot {dot}"></span>
        <span class="kpi-lbl">{c['label']}</span>
    </div>
    <div class="kpi-val">{c['value']}</div>
    <div class="kpi-sub">{c.get('sub','')}</div>
</div>"""
    st.markdown(f'<div class="kpi-grid {grid_cls}">{items}</div>', unsafe_allow_html=True)


def status_badge(status: str) -> str:
    """상태 문자열 → HTML 배지 반환"""
    bc = _STATUS_BADGE.get(status, "badge-pend")
    return f'<span class="badge {bc}"><span class="led"></span>{status}</span>'


def chart_title(title: str, caption: str = "") -> None:
    """차트 카드용 컴팩트 타이틀(+선택 캡션) 렌더링."""
    st.markdown(
        f'<div class="chart-title"><span class="ct-dot"></span>{title}</div>'
        + (f'<div class="chart-cap">{caption}</div>' if caption else ''),
        unsafe_allow_html=True,
    )


# ─── 차트 색상 팔레트 (Atelier 아이리스/골드) ────────────────────
IRIS      = "#6E62E6"
IRIS_2    = "#9A7CF0"
IRIS_INK  = "#4B41B8"
GOLD      = "#C9A24B"
INK       = "#1A1814"
TX2       = "#6A655C"
GRID      = "rgba(26,24,20,.06)"

# 범주형 시퀀스 (파이/막대 등)
CHART_SEQ = ["#6E62E6", "#9A7CF0", "#C9A24B", "#2FA37A", "#D6485B", "#4B41B8", "#B98A2E"]
# 연속형 그라디언트 (연한 아이리스 → 진한 아이리스)
CHART_GRAD = ["#ECEAFB", "#C7BEF4", "#9A7CF0", "#6E62E6"]


def style_plotly(fig, height: int = 320, showlegend: bool = False):
    """Plotly figure에 Atelier 공통 테마를 입힌다."""
    fig.update_layout(
        height=height,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Noto Sans KR, sans-serif", color=INK, size=12),
        margin=dict(l=0, r=6, t=24, b=0),
        colorway=CHART_SEQ,
        showlegend=showlegend,
        legend=dict(orientation="h", y=1.14, x=0, font=dict(size=11, color=TX2)),
        hoverlabel=dict(
            bgcolor="white", bordercolor="rgba(26,24,20,.1)",
            font=dict(family="Inter, Noto Sans KR, sans-serif", color=INK, size=12),
        ),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False,
                     tickfont=dict(color=TX2, size=11), title_font=dict(color=TX2, size=11))
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, showline=False,
                     tickfont=dict(color=TX2, size=11), title_font=dict(color=TX2, size=11))
    return fig
