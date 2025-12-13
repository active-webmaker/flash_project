import os
import streamlit as st
from utils.api import APIClient

st.set_page_config(page_title="Flash AI Coding Agent", layout="wide", initial_sidebar_state="expanded")

API_BASE_URL = os.getenv("STREAMLIT_API_BASE_URL", "http://localhost:8000")
client = APIClient(API_BASE_URL)

if "auth" not in st.session_state:
    st.session_state.auth = {"access": None, "refresh": None, "username": None}


def show_login():
    st.markdown(
        """
        <style>
            .main {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }
            .st-form {
                background: white;
                padding: 2rem;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    col_empty, col_form, col_empty2 = st.columns([1, 1, 1])
    with col_form:
        st.title("⚡️ Flash AI 에이전트")
        st.caption("코딩의 미래, 지금 경험해보세요.")
        
        with st.form("login_form"):
            username = st.text_input("👤 사용자명", placeholder="사용자명을 입력하세요")
            password = st.text_input("🔑 비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            submitted = st.form_submit_button("로그인", use_container_width=True, type="primary")
            
        if submitted:
            try:
                tokens = client.login(username, password)
                st.session_state.auth.update({
                    "access": tokens.get("access"),
                    "refresh": tokens.get("refresh"),
                    "username": username,
                })
                st.success("✅ 로그인 성공! 대시보드로 이동합니다.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 로그인 실패: {str(e)}")


def show_header():
    with st.sidebar:
        st.title("Flash 메뉴")
        st.caption(f"API: {API_BASE_URL}")
        
        if st.session_state.auth["access"]:
            st.success(f"**{st.session_state.auth['username']}** 님, 환영합니다!")
            if st.button("로그아웃", use_container_width=True):
                st.session_state.auth = {"access": None, "refresh": None, "username": None}
                st.rerun()
        else:
            st.info("로그인이 필요합니다.")
        
        st.divider()


def main():
    show_header()
    if not st.session_state.auth["access"]:
        show_login()
        return

    st.title("🚀 Flash AI 대시보드")
    st.markdown("AI 기반 코딩 도우미 **Flash**에 오신 것을 환영합니다. 사이드바 메뉴를 통해 다양한 기능을 사용해보세요.")
    st.divider()

    col1, col2 = st.columns([1, 1])

    # API Health & User Profile
    with col1:
        with st.container(border=True):
            st.subheader("📈 시스템 상태")
            ok, data = client.health()
            if ok:
                st.success("✅ API 서버가 정상적으로 응답합니다.")
            else:
                st.error("❌ API 서버에 연결할 수 없습니다.")

        with st.container(border=True):
            st.subheader("👤 내 정보")
            profile = client.me(st.session_state.auth["access"]) or {}
            if profile:
                st.markdown(f"""
                - **이름:** {profile.get('username', 'N/A')}
                - **이메일:** {profile.get('email', 'N/A')}
                """)
            else:
                st.warning("프로필 정보를 불러올 수 없습니다.")

    # Quick Links
    with col2:
        with st.container(border=True):
            st.subheader("⚡ 빠른 메뉴")
            st.info("아래 링크를 클릭하여 Flash의 주요 기능으로 빠르게 이동할 수 있습니다.")
            
            col_link1, col_link2 = st.columns(2)
            with col_link1:
                st.page_link("pages/2_Gamification.py", label="**게이미피케이션**", use_container_width=True)
                st.caption("도전과제를 달성하고 보상을 받으세요.")
                st.page_link("pages/4_Code_Generation.py", label="**코드 생성**", use_container_width=True)
                st.caption("AI에게 코드 생성을 요청하세요.")
            with col_link2:
                st.page_link("pages/3_Quiz.py", label="**퀴즈**", use_container_width=True)
                st.caption("학습한 내용으로 퀴즈를 풀어보세요.")
                st.page_link("pages/1_Dashboard.py", label="**상세 대시보드**", use_container_width=True)
                st.caption("시스템의 상세 상태를 확인하세요.")


if __name__ == "__main__":
    main()
