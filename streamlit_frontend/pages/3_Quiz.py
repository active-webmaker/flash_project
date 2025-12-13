import os
import streamlit as st
from utils.api import APIClient

st.set_page_config(page_title="Quiz", layout="wide", initial_sidebar_state="expanded")
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

st.title("📝 퀴즈 풀")
st.markdown("다양한 주제의 퀴즈를 통해 지식을 테스트하고 학습 점수를 얻으세요.")
st.divider()

if not st.session_state.auth["access"]:
    st.warning("🔐 로그인이 필요합니다. 홈에서 로그인 해주세요.")
    st.stop()

pools_resp = client.quiz_pools(st.session_state.auth["access"]) or {}
pools = pools_resp.get("pools") or pools_resp

st.subheader("📚 이용 가능한 퀴즈")

if pools and isinstance(pools, list) and len(pools) > 0:
    cols = st.columns(3)
    for idx, pool in enumerate(pools):
        with cols[idx % 3]:
            with st.container(border=True):
                if isinstance(pool, dict):
                    # QuizPoolSerializer는 'title' 필드를 반환 (Topic.name -> 'title')
                    pool_title = pool.get('title') or pool.get('name', 'Unknown Pool')
                    st.markdown(f"### 📖 {pool_title}")
                    st.caption(f"{pool.get('description', '설명 없음')}")
                    st.divider()
                    st.metric("문제 수", pool.get('question_count', 0))
                    # st.button("퀴즈 시작", key=f"start_quiz_{pool.get('id', idx)}", use_container_width=True) # 기능 추가시 활성화
                else:
                    st.markdown(f"### 📖 {pool}")
                    st.caption("기본 퀴즈 풀")
else:
    st.info("📭 이용 가능한 퀴즈가 없습니다. 코드 생성 후 생성되는 퀴즈를 이용해보세요.")
