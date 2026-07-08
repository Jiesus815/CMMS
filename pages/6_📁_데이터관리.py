import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import (
    import_from_excel, init_db, get_conn, get_maintenance, get_equipment,
    clear_maintenance, clear_all_data,
    list_users, create_user, delete_user, reset_user_password, set_user_active,
    list_tenants, create_tenant, set_user_tenant, get_audit_logs,
)
from utils.style import inject_css, page_header, flash, render_flash
from utils.auth import auth_enabled, is_admin, is_superadmin, current_user
import tempfile
from datetime import datetime

init_db()

inject_css("""
.info-card {
    background: white; border: 1px solid #E2E8F0;
    border-radius: 12px; padding: 20px; margin: 8px 0;
}
""")
render_flash()

page_header("📁 데이터 관리", "Excel Import · DB 백업 · 데이터 초기화")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📥 Excel Import", "💾 DB 백업", "⚠️ 초기화", "👥 계정 관리", "🏢 회사 관리", "📜 감사 로그",
])

# ══════════════════════════════
# 탭1: Excel Import
# ══════════════════════════════
with tab1:
    st.subheader("📥 Excel 파일 Import")
    st.markdown("""
    <div class="info-card">
    <b>지원 시트:</b><br>
    • <code>Raw 보전내역</code> 또는 <code>보전내역</code> → 보전내역 DB로 import<br>
    • <code>Raw 설비리스트</code> 또는 <code>설비리스트</code> → 설비 DB로 import<br><br>
    <b>주의:</b> 기존 데이터와 중복 시 설비코드 기준으로 건너뜁니다.
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Excel 파일 선택 (.xlsx)",
        type=["xlsx"],
        help="[스마팩] 2026 보전시트.xlsx 형식을 지원합니다.",
    )

    if uploaded:
        st.info(f"파일명: **{uploaded.name}** | 크기: {uploaded.size / 1024:.1f} KB")

        if st.button("🚀 Import 시작", type="primary", use_container_width=True):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name

            with st.spinner("데이터 처리 중..."):
                results = import_from_excel(tmp_path)

            os.remove(tmp_path)

            st.cache_data.clear()

            if results["errors"]:
                st.warning(f"⚠️ 일부 오류 발생 ({len(results['errors'])}건)")
                with st.expander("오류 내역 보기"):
                    for e in results["errors"][:20]:
                        st.text(e)

            st.success(f"""
            ✅ Import 완료!
            - 설비: **{results['equipment']}건** import
            - 보전내역: **{results['maintenance']}건** import
            """)

# ══════════════════════════════
# 탭2: DB 백업
# ══════════════════════════════
with tab2:
    st.subheader("💾 데이터 백업 (CSV)")
    st.markdown("""
    <div class="info-card">
    Supabase(PostgreSQL) 사용 중입니다.<br>
    각 테이블을 CSV 파일로 다운로드하여 백업할 수 있습니다.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 보전내역 CSV 다운로드", use_container_width=True):
            df_m = get_maintenance()
            csv = df_m.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ 보전내역.csv",
                data=csv.encode("utf-8-sig"),
                file_name=f"보전내역_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    with col2:
        if st.button("📥 설비목록 CSV 다운로드", use_container_width=True):
            df_e = get_equipment()
            csv = df_e.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                "⬇️ 설비목록.csv",
                data=csv.encode("utf-8-sig"),
                file_name=f"설비목록_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

# ══════════════════════════════
# 탭3: 초기화
# ══════════════════════════════
with tab3:
    st.subheader("⚠️ 데이터 초기화")
    st.error("⚠️ 주의: 아래 작업은 되돌릴 수 없습니다!")

    # 권한 판정: 로그인 게이트 켜지면 관리자 역할, 꺼져있으면 레거시 관리자 비번
    if is_admin():
        authorized = True
    elif not auth_enabled():
        admin_pw = st.text_input("🔐 관리자 비밀번호", type="password", key="admin_pw")
        try:
            correct_pw = st.secrets["ADMIN_PASSWORD"]
        except Exception:
            correct_pw = ""
        authorized = bool(admin_pw) and admin_pw == correct_pw
        if not admin_pw:
            st.info("관리자 비밀번호를 입력하면 초기화 기능이 활성화됩니다.")
        elif not authorized:
            st.error("비밀번호가 틀렸습니다.")
    else:
        authorized = False
        st.warning("관리자만 초기화할 수 있습니다.")

    if authorized:
        st.success("✅ 인증되었습니다.")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**보전내역만 삭제**")
            confirm1 = st.text_input("확인 문구 입력 ('삭제확인')", key="c1")
            if st.button("🗑️ 보전내역 전체 삭제", use_container_width=True):
                if confirm1 == "삭제확인":
                    clear_maintenance()
                    st.cache_data.clear()
                    st.success("보전내역이 삭제되었습니다.")
                else:
                    st.error("확인 문구가 일치하지 않습니다.")

        with col2:
            st.markdown("**전체 데이터 초기화**")
            confirm2 = st.text_input("확인 문구 입력 ('전체초기화')", key="c2")
            if st.button("💥 전체 DB 초기화", use_container_width=True):
                if confirm2 == "전체초기화":
                    clear_all_data()
                    st.cache_data.clear()
                    st.success("전체 데이터가 초기화되었습니다.")
                else:
                    st.error("확인 문구가 일치하지 않습니다.")


# ══════════════════════════════
# 탭4: 계정 관리
# ══════════════════════════════
with tab4:
    st.subheader("👥 계정 관리")

    if auth_enabled() and not is_admin():
        st.warning("관리자만 접근할 수 있습니다.")
    else:
        if not auth_enabled():
            st.info(
                "현재 로그인 게이트가 꺼져 있습니다. 계정을 만들고 로그인 테스트가 끝나면 "
                "secrets 에 `AUTH_ENABLED = true` 를 설정해 로그인을 활성화하세요."
            )

        # ── 계정 생성 ──
        st.markdown("##### ➕ 새 계정 생성")
        with st.form("user_new", clear_on_submit=True):
            uc1, uc2, uc3 = st.columns(3)
            with uc1:
                nu_id = st.text_input("아이디 *")
                nu_name = st.text_input("이름")
            with uc2:
                nu_pw = st.text_input("비밀번호 *", type="password")
                nu_pw2 = st.text_input("비밀번호 확인 *", type="password")
            with uc3:
                nu_role = st.selectbox("권한", ["user", "admin"],
                                       help="user=입력·조회만, admin=계정·초기화 가능")
                if is_superadmin():
                    _tn = list_tenants()
                    _topts = {int(r.id): r.name for r in _tn.itertuples()}
                    nu_tenant = st.selectbox("소속 회사", list(_topts.keys()),
                                             format_func=lambda x: _topts.get(x, x), key="nu_tenant")
                else:
                    _cu0 = current_user()
                    nu_tenant = int(_cu0["tenant_id"]) if _cu0 else 1
            add = st.form_submit_button("계정 생성", type="primary", use_container_width=True)
        if add:
            cu = current_user()
            creator = cu["username"] if cu else "system"
            if not nu_id or not nu_pw:
                st.error("아이디와 비밀번호는 필수입니다.")
            elif nu_pw != nu_pw2:
                st.error("비밀번호가 일치하지 않습니다.")
            elif len(nu_pw) < 8:
                st.error("비밀번호는 8자 이상이어야 합니다.")
            else:
                if create_user(nu_id.strip(), nu_pw, nu_name.strip(), nu_role, nu_tenant, creator):
                    flash(f"'{nu_id}' 계정이 생성되었습니다")
                    st.rerun()
                else:
                    st.error("이미 존재하는 아이디입니다.")

        st.markdown("---")
        st.markdown("##### 📋 계정 목록")
        df_u = list_users()
        if df_u.empty:
            st.info("계정이 없습니다.")
        else:
            show = df_u[["username", "display_name", "role", "is_active", "last_login"]].rename(columns={
                "username": "아이디", "display_name": "이름", "role": "권한",
                "is_active": "활성", "last_login": "마지막 로그인",
            })
            st.dataframe(show, use_container_width=True, hide_index=True)

            manage = df_u[df_u["role"] != "superadmin"]
            if manage.empty:
                st.caption("관리 가능한 하위 계정이 없습니다.")
            else:
                st.markdown("##### ⚙️ 계정 관리")
                id_to_label = {int(r.id): f"{r.username} ({r.display_name or '-'})"
                               for r in manage.itertuples()}
                sel_id = st.selectbox("관리할 계정", list(id_to_label.keys()),
                                      format_func=lambda x: id_to_label[x], key="mng_user")
                sel_row = manage[manage["id"] == sel_id].iloc[0]
                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    new_pw = st.text_input("새 비밀번호", type="password", key="rst_pw")
                    if st.button("🔑 비밀번호 초기화", use_container_width=True):
                        if len(new_pw) < 8:
                            st.error("8자 이상 입력하세요.")
                        else:
                            reset_user_password(int(sel_id), new_pw)
                            flash("비밀번호가 초기화되었습니다")
                            st.rerun()
                with mc2:
                    is_act = bool(sel_row["is_active"])
                    label = "🚫 비활성화" if is_act else "✅ 활성화"
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                    if st.button(label, use_container_width=True):
                        set_user_active(int(sel_id), not is_act)
                        flash("계정 상태가 변경되었습니다")
                        st.rerun()
                with mc3:
                    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                    if st.button("🗑️ 계정 삭제", use_container_width=True):
                        delete_user(int(sel_id))
                        flash("계정이 삭제되었습니다")
                        st.rerun()

                if is_superadmin():
                    _tn2 = list_tenants()
                    _topts2 = {int(r.id): r.name for r in _tn2.itertuples()}
                    tc1, tc2 = st.columns([2, 1])
                    with tc1:
                        _cur_tid = int(sel_row["tenant_id"]) if "tenant_id" in sel_row else 1
                        new_tid = st.selectbox(
                            "소속 회사 변경", list(_topts2.keys()),
                            index=list(_topts2.keys()).index(_cur_tid) if _cur_tid in _topts2 else 0,
                            format_func=lambda x: _topts2.get(x, x), key="mv_tenant")
                    with tc2:
                        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                        if st.button("🏢 회사 이동", use_container_width=True):
                            set_user_tenant(int(sel_id), int(new_tid))
                            flash("소속 회사가 변경되었습니다")
                            st.rerun()


# ══════════════════════════════
# 탭5: 회사(테넌트) 관리 — 최고관리자 전용
# ══════════════════════════════
with tab5:
    st.subheader("🏢 회사 관리")
    if not is_superadmin():
        st.warning("최고관리자만 접근할 수 있습니다.")
    else:
        st.caption("회사(테넌트)별로 데이터가 완전히 분리됩니다. 새 회사를 만들고 계정 관리에서 사용자를 배정하세요.")
        with st.form("tenant_new", clear_on_submit=True):
            tn_name = st.text_input("새 회사 이름 *", placeholder="예: 스마팩 2공장")
            tadd = st.form_submit_button("회사 생성", type="primary", use_container_width=True)
        if tadd:
            if not tn_name.strip():
                st.error("회사 이름을 입력하세요.")
            elif create_tenant(tn_name.strip()):
                flash(f"'{tn_name}' 회사가 생성되었습니다")
                st.rerun()
            else:
                st.error("이미 존재하는 회사 이름입니다.")

        st.markdown("---")
        st.markdown("##### 📋 회사 목록")
        df_t = list_tenants().rename(columns={
            "id": "ID", "name": "회사명", "user_count": "사용자 수", "created_at": "생성일",
        })
        st.dataframe(df_t, use_container_width=True, hide_index=True)


# ══════════════════════════════
# 탭6: 감사 로그
# ══════════════════════════════
with tab6:
    st.subheader("📜 감사 로그")
    if auth_enabled() and not is_admin():
        st.warning("관리자만 접근할 수 있습니다.")
    else:
        st.caption("데이터 변경 이력(누가·언제·무엇을) — 최근 300건")
        df_a = get_audit_logs(300)
        if df_a.empty:
            st.info("기록된 감사 로그가 없습니다.")
        else:
            show_a = df_a.rename(columns={
                "created_at": "시각", "actor": "작업자", "action": "동작",
                "entity": "대상", "entity_id": "대상ID", "detail": "상세",
            })
            st.dataframe(show_a, use_container_width=True, hide_index=True, height=520)
            csv_a = df_a.to_csv(index=False, encoding="utf-8-sig")
            st.download_button("⬇️ 감사 로그 CSV", data=csv_a.encode("utf-8-sig"),
                               file_name=f"감사로그_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                               mime="text/csv")

