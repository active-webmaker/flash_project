import os
import streamlit as st
from utils.api import APIClient

st.set_page_config(page_title="Gamification", layout="wide", initial_sidebar_state="expanded")
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

st.title("🏆 게이미피케이션")
st.markdown("다양한 활동을 통해 레벨을 올리고, 특별한 배지를 획득해보세요!")
st.divider()

if not st.session_state.auth["access"]:
    st.warning("🔐 로그인이 필요합니다. 홈에서 로그인 해주세요.")
    st.stop()

profile = client.gami_profile(st.session_state.auth["access"])

if not profile:
    st.error("프로필 정보를 불러오는 데 실패했습니다. 잠시 후 다시 시도해주세요.")
    st.stop()

# --- 통계 섹션 ---
st.subheader("📊 내 통계")
with st.container(border=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        level = profile.get("level", 0)
        st.metric("📈 레벨", level)
    with col2:
        xp = profile.get("total_xp", 0)
        st.metric("⚡ 총 경험치", f"{xp:,}")
    with col3:
        points = profile.get("points", 0)
        st.metric("💰 포인트", f"{points:,}")

# --- 배지 섹션 ---
st.divider()
st.subheader("🎖️ 획득한 배지")
badges = profile.get("badges") or []

if badges:
    cols = st.columns(4)
    for idx, badge in enumerate(badges):
        with cols[idx % 4]:
            with st.container(border=True):
                st.markdown(f"<div style='text-align: center; font-size: 3rem;'>{badge.get('icon', '🏅')}</div>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='text-align: center;'>{badge.get('name', 'Unknown')}</h3>", unsafe_allow_html=True)
                st.caption(f"<div style='text-align: center;'>{badge.get('description', '')}</div>", unsafe_allow_html=True)
else:
    st.info("아직 획득한 배지가 없습니다. 활동을 통해 배지를 획득해보세요! 💪")
