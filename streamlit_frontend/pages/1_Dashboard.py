import os
import json
import streamlit as st
from utils.api import APIClient

st.set_page_config(page_title="Dashboard", layout="wide", initial_sidebar_state="expanded")
API_BASE_URL = os.getenv("STREAMLIT_API_BASE_URL", "http://localhost:8000")
client = APIClient(API_BASE_URL)

if "auth" not in st.session_state:
    st.session_state.auth = {"access": None, "refresh": None, "username": None}

# --- Sidebar ---
with st.sidebar:
    st.title("Flash 메뉴")
    if st.session_state.auth["access"]:
        st.success(f"**{st.session_state.auth['username']}** 님, 환영합니다!")
    st.divider()

st.title("📊 상세 대시보드")
st.markdown("시스템의 현재 상태와 API 응답을 자세히 확인할 수 있습니다.")
st.divider()

if not st.session_state.auth["access"]:
    st.warning("🔐 로그인이 필요합니다. 홈에서 로그인 해주세요.")
    st.stop()

ok, data = client.health()

with st.container(border=True):
    st.subheader("🔗 시스템 상태")
    if ok:
        st.success("✅ API 서버가 정상적으로 연결되었습니다.")
    else:
        st.error("❌ API 서버 연결에 실패했습니다. 관리자에게 문의하세요.")

with st.container(border=True):
    st.subheader("ℹ️ API 응답 전문")
    if data:
        try:
            # JSON 문자열을 파싱하여 보기 좋게 표시
            info = json.loads(data) if isinstance(data, str) else data
            st.json(info)
        except json.JSONDecodeError:
            st.text(f"RAW 응답:\n{data}")
    else:
        st.info("상태 정보가 없습니다.")

st.info("💡 이 페이지는 시스템의 기술적인 상태를 보여줍니다. 일반적인 사용 정보는 홈 화면을 참고하세요.")
