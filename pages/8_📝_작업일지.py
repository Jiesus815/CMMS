import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import add_work_log, get_work_logs, delete_work_log, get_available_years, init_db
from utils.constants import FACTORIES
from utils.style import inject_css, page_header, kpi_cards
from datetime import date, datetime

init_db()

inject_css()

page_header("📝 작업일지", "작업자가 직접 기록하는 일일 작업 이력")

WORK_CATEGORY = ["점검", "수리", "교체", "청소", "조정", "개선", "기타"]

tab1, tab2 = st.tabs(["📋 일지 조회", "➕ 일지 작성"])

# ══════════════════════════════
# 탭1: 일지 조회
# ══════════════════════════════
with tab1:
    years = get_available_years()
    cur_year = datetime.now().year
    if cur_year not in years:
        years = [cur_year] + years

    fc1, fc2, fc3 = st.columns([1, 1, 2])
    with fc1:
        f_year = st.selectbox("연도", ["전체"] + years, key="wl_year")
    with fc2:
        f_month = st.selectbox("월", ["전체"] + list(range(1, 13)), key="wl_month")
    with fc3:
        f_author = st.text_input("작성자 검색", placeholder="이름 입력", key="wl_author")

    df = get_work_logs(
        year=None if f_year == "전체" else f_year,
        month=None if f_month == "전체" else f_month,
        author=f_author.strip() if f_author.strip() else None,
    )

    if df.empty:
        st.info("작성된 작업일지가 없습니다. '일지 작성' 탭에서 기록해 주세요.")
    else:
        this_month = datetime.now().strftime("%Y-%m")
        month_cnt = int(df["log_date"].astype(str).str.startswith(this_month).sum())
        kpi_cards([
            {"label": "전체 일지",   "value": f"{len(df):,}건", "color": "blue",  "sub": "조회 결과"},
            {"label": "이번 달",     "value": f"{month_cnt:,}건", "color": "green", "sub": this_month},
            {"label": "작성자 수",   "value": f"{df['author'].nunique():,}명", "color": "purple", "sub": "고유 작성자"},
        ])

        st.markdown("")
        df_show = df.rename(columns={
            "id": "ID", "log_date": "작업일자", "author": "작성자", "factory": "팩토리",
            "category": "구분", "title": "제목", "content": "내용",
        })
        st.dataframe(
            df_show[["작업일자", "작성자", "팩토리", "구분", "제목", "내용"]],
            use_container_width=True, height=420, hide_index=True,
        )

        csv = df_show.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "⬇️ CSV 다운로드", data=csv,
            file_name=f"작업일지_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv",
        )

        st.markdown("---")
        st.subheader("🗑️ 일지 삭제")
        del_col1, del_col2 = st.columns([1, 3])
        with del_col1:
            id_opts = df["id"].tolist()
            del_id = st.selectbox("삭제할 일지 ID", id_opts, key="wl_del_id")
        with del_col2:
            sel = df[df["id"] == del_id]
            if not sel.empty:
                r = sel.iloc[0]
                st.caption(f"📌 {r['log_date']} · {r['author'] or '-'} · {r['title'] or '(제목 없음)'}")
        if st.button("선택한 일지 삭제", type="secondary"):
            delete_work_log(int(del_id))
            st.success(f"ID {del_id} 삭제 완료!")
            st.rerun()

# ══════════════════════════════
# 탭2: 일지 작성
# ══════════════════════════════
with tab2:
    st.subheader("➕ 작업일지 작성")
    with st.form("work_log_form", clear_on_submit=True):
        wc1, wc2, wc3 = st.columns(3)
        with wc1:
            n_date = st.date_input("작업일자 *", value=date.today())
            n_author = st.text_input("작성자 *", placeholder="이름")
        with wc2:
            n_factory = st.selectbox("팩토리", ["-"] + FACTORIES)
            n_category = st.selectbox("작업 구분", WORK_CATEGORY)
        with wc3:
            n_title = st.text_input("제목 *", placeholder="작업 요약")

        n_content = st.text_area("작업 내용 *", height=160, placeholder="수행한 작업 내용을 자유롭게 기록하세요")

        submitted = st.form_submit_button("💾 저장", use_container_width=True, type="primary")

    if submitted:
        if not n_author or not n_title or not n_content:
            st.error("작성자 · 제목 · 작업 내용은 필수입니다.")
        else:
            add_work_log({
                "log_date": str(n_date),
                "author": n_author.strip(),
                "factory": None if n_factory == "-" else n_factory,
                "category": n_category,
                "title": n_title.strip(),
                "content": n_content.strip(),
            })
            st.success("✅ 작업일지가 저장되었습니다!")
            st.balloons()
