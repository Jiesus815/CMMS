import streamlit as st
import sys, os
import html
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import (
    get_parts, add_part, adjust_part_stock, delete_part, init_db,
)
from utils.style import inject_css, page_header, kpi_cards, flash, render_flash
from datetime import datetime

init_db()
inject_css()
render_flash()

page_header("🧰 부품 재고", "예비 부품 재고 관리 · 입출고 · 부족 경고")

tab1, tab2 = st.tabs(["📦 재고 목록", "➕ 부품 등록"])

# ══════════════════════════════
# 탭1: 재고 목록
# ══════════════════════════════
with tab1:
    df = get_parts()
    if df.empty:
        st.info("등록된 부품이 없습니다. '부품 등록' 탭에서 추가하세요.")
    else:
        low = int(((df["min_stock"] > 0) & (df["stock"] <= df["min_stock"])).sum())
        total_stock = int(df["stock"].sum())
        kpi_cards([
            {"label": "품목 수", "value": f"{len(df):,}종", "color": "blue", "sub": "등록 부품"},
            {"label": "총 재고", "value": f"{total_stock:,}개", "color": "green", "sub": "전체 수량"},
            {"label": "재고 부족", "value": f"{low:,}종", "color": "red", "sub": "최소 재고 이하"},
        ])

        cards = '<div class="rec-scroll">'
        for _, r in df.iterrows():
            stock = int(r.get("stock") or 0)
            mins = int(r.get("min_stock") or 0)
            is_low = mins > 0 and stock <= mins
            color = "#D6485B" if is_low else "#2FA37A"
            name = html.escape(str(r.get("part_name") or "-"))
            code = html.escape(str(r.get("part_code") or ""))
            unit = html.escape(str(r.get("unit") or "개"))
            loc = html.escape(str(r.get("location") or ""))
            memo = html.escape(str(r.get("memo") or "").strip())
            meta = f'<span>📦 재고 <b>{stock}</b>{unit}</span><span>⚠️ 최소 {mins}{unit}</span>'
            if loc:
                meta += f'<span>📍 {loc}</span>'
            pill = ('<span class="rec-fac" style="color:#D6485B;background:#D6485B1a">부족</span>'
                    if is_low else '')
            desc_html = f'<div class="rec-desc">{memo}</div>' if memo else ''
            cards += (
                f'<div class="rec-card" style="border-left-color:{color}">'
                f'<div class="rec-top"><span class="rec-name">{name}</span>'
                f'<span class="rec-sub">{code}</span><span class="rec-spacer"></span>{pill}</div>'
                f'<div class="rec-meta">{meta}</div>{desc_html}</div>'
            )
        cards += '</div>'
        st.markdown(cards, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### 🔄 입·출고 / 삭제")
        id_to_label = {int(r.id): f"{r.part_name or '-'} ({r.part_code or ''}) · 재고 {int(r.stock or 0)}"
                       for r in df.itertuples()}
        sel_p = st.selectbox("부품 선택", list(id_to_label.keys()),
                             format_func=lambda x: id_to_label[x], key="part_sel")
        ac1, ac2, ac3 = st.columns([1, 1, 1])
        with ac1:
            qty = st.number_input("수량", min_value=1, value=1, step=1, key="part_qty")
        with ac2:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("➕ 입고", use_container_width=True, type="primary"):
                adjust_part_stock(int(sel_p), int(qty))
                st.cache_data.clear()
                flash("입고 처리되었습니다")
                st.rerun()
        with ac3:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("➖ 출고", use_container_width=True):
                adjust_part_stock(int(sel_p), -int(qty))
                st.cache_data.clear()
                flash("출고 처리되었습니다")
                st.rerun()
        if st.button("🗑️ 이 부품 삭제"):
            delete_part(int(sel_p))
            st.cache_data.clear()
            flash("부품이 삭제되었습니다")
            st.rerun()

# ══════════════════════════════
# 탭2: 부품 등록
# ══════════════════════════════
with tab2:
    st.subheader("➕ 부품 신규 등록")
    with st.form("part_new", clear_on_submit=True):
        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            n_name = st.text_input("부품명 *", placeholder="예: 6203 베어링")
            n_code = st.text_input("부품 코드", placeholder="예: BRG-6203")
        with pc2:
            n_stock = st.number_input("현재 재고", min_value=0, value=0, step=1)
            n_min = st.number_input("최소 재고(부족 기준)", min_value=0, value=0, step=1)
        with pc3:
            n_unit = st.text_input("단위", value="개")
            n_loc = st.text_input("보관 위치", placeholder="예: 자재창고 A-3")
        n_memo = st.text_area("메모", height=70)
        submitted = st.form_submit_button("💾 등록", use_container_width=True, type="primary")

    if submitted:
        if not n_name:
            st.error("부품명은 필수입니다.")
        else:
            add_part({
                "part_code": n_code.strip(), "part_name": n_name.strip(),
                "stock": int(n_stock), "min_stock": int(n_min),
                "unit": n_unit.strip() or "개", "location": n_loc.strip(),
                "memo": n_memo.strip(),
            })
            st.cache_data.clear()
            flash("부품이 등록되었습니다")
            st.rerun()
