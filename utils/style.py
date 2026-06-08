import streamlit as st

# ─── 공통 CSS ────────────────────────────────────────────────
_COMMON_CSS = """
[data-testid="metric-container"] {
    background: white; border-radius: 12px; padding: 16px 20px;
    border: 1px solid #E2E8F0; box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.page-header {
    background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%);
    color: white; padding: 20px 28px; border-radius: 12px; margin-bottom: 24px;
}
.page-header h1 { color: white; margin: 0; font-size: 1.6rem; }
.page-header p  { color: #BFDBFE; margin: 4px 0 0; font-size: 0.9rem; }
"""


def inject_css(extra: str = "") -> None:
    """공통 CSS + 페이지별 추가 CSS 주입"""
    css = _COMMON_CSS + extra
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    """상단 파란색 헤더 렌더링"""
    st.markdown(f"""
<div class="page-header">
    <h1>{title}</h1>
    <p>{subtitle}</p>
</div>
""", unsafe_allow_html=True)
