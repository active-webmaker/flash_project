from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime

import streamlit as st

from utils.api import APIClient

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    LOG_DIR = "logs"
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, f"code_generation_{datetime.now().strftime('%Y%m%d')}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel(logging.DEBUG)

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
API_BASE_URL = os.getenv("STREAMLIT_API_BASE_URL", "http://localhost:8000")
client = APIClient(API_BASE_URL)

st.set_page_config(page_title="코드 생성", layout="wide", initial_sidebar_state="expanded")

if "auth" not in st.session_state:
    st.session_state.auth = {"access": None, "refresh": None, "username": None}
if "analysis_mode" not in st.session_state:
    st.session_state.analysis_mode = None


def _tree_lines(node: dict, depth: int = 0) -> list[str]:
    """Render file tree JSON into indented markdown bullets."""
    if not isinstance(node, dict):
        return []
    icon = "📁" if node.get("type") == "directory" else "📄"
    name = node.get("name") or node.get("path") or "item"
    size = node.get("size")
    label = name if size is None else f"{name} ({size}B)"
    indent = "  " * depth
    lines = [f"{indent}- {icon} {label}"]
    for child in node.get("children", []):
        lines.extend(_tree_lines(child, depth + 1))
    return lines


# ----------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------
with st.sidebar:
    st.title("Flash 메뉴")
    if st.session_state.auth["access"]:
        st.success(f"**{st.session_state.auth['username']}** 님 환영합니다")
    st.divider()

if not st.session_state.auth["access"]:
    st.warning("먼저 로그인해 주세요.")
    st.stop()

access = st.session_state.auth["access"]

# ----------------------------------------------------------------------
# Main UI
# ----------------------------------------------------------------------
st.title("AI 코드 생성")
st.markdown("AI로 코드를 생성하고, 생성된 코드로 학습 퀴즈를 풀어보세요.")
st.divider()

# Project registration
with st.expander("프로젝트 등록하기"):
    with st.form("register_project"):
        st.subheader("프로젝트 정보 입력")
        prj_name = st.text_input("프로젝트 이름", placeholder="예) My Awesome App")
        prj_local = st.text_input("로컬 경로", placeholder="예) /path/to/your/project")
        prj_remote = st.text_input("원격 URL (옵션)", placeholder="예) https://github.com/user/repo")
        reg_submit = st.form_submit_button("등록", use_container_width=True, type="primary")

    if reg_submit and prj_name:
        with st.spinner("프로젝트를 등록하는 중..."):
            created = client.register_project(access, prj_name, prj_local, prj_remote)
        if created:
            st.success("프로젝트가 등록되었습니다. 새로고침 후 목록을 확인하세요.")
            st.balloons()
        else:
            st.error("프로젝트 등록에 실패했습니다. 입력 정보를 확인하세요.")

# Job creation
with st.container(border=True):
    st.subheader("코드 생성 설정")
    projects = client.projects(access)

    if not projects:
        st.warning("등록된 프로젝트가 없습니다. 위에서 프로젝트를 먼저 등록하세요.", icon="⚠️")
        selected = None
    else:
        project_names = [f"{p.get('id')} - {p.get('name')}" for p in projects]
        selected = st.selectbox("작업할 프로젝트를 선택하세요", project_names)

    prompt = st.text_area("프롬프트", height=150, placeholder="예) '로그인 기능이 있는 API 코드를 만들어줘'")
    language = st.selectbox("프로그래밍 언어", ["python", "javascript", "go", "java", "typescript"])

    run = st.button("🚀 코드 생성 시작", type="primary", disabled=(not prompt or not selected), use_container_width=True)

# Repository analysis buttons
with st.container(border=True):
    st.subheader("리포지터리 분석 도구")
    repo_col1, repo_col2, repo_col3 = st.columns(3)
    with repo_col1:
        run_scan = st.button("📂 파일 트리 분석", disabled=(not selected), use_container_width=True)
    with repo_col2:
        run_loc = st.button("🧮 언어별 코드 라인", disabled=(not selected), use_container_width=True)
    with repo_col3:
        run_diff = st.button("📑 Git Diff 보기", disabled=(not selected), use_container_width=True)

    job_payload = None
    if run_scan:
        run = True
        job_type = "repository_analysis"
        job_payload = {"tool_name": "scan_file_tree", "tool_args": {}}
        st.session_state.analysis_mode = "file_tree"

    if run_loc:
        run = True
        job_type = "repository_analysis"
        job_payload = {"tool_name": "calculate_loc_per_language", "tool_args": {}}
        language = "json"
        st.session_state.analysis_mode = "loc"

    if run_diff:
        run = True
        job_type = "repository_analysis"
        job_payload = {"tool_name": "get_diff", "tool_args": {}}
        language = "diff"
        st.session_state.analysis_mode = "git_diff"

# Create job and poll
if run and selected:
    project_id = int(selected.split(" - ", 1)[0])

    if not job_payload:
        job_type = "code_generation"
        job_payload = {"prompt": prompt, "language": language}
        st.session_state.analysis_mode = None

    logger.info(f"Job 생성 요청 - project_id={project_id}, job_type={job_type}")
    job = client.create_job(access, project_id, job_type, job_payload)

    if not job:
        st.error("작업 생성에 실패했습니다. API 서버 상태를 확인하세요.")
    else:
        job_id = job.get("id")
        st.success(f"작업이 생성되었습니다 (ID: {job_id})")
        st.divider()

        progress_area = st.container()
        poll_count = 0

        while True:
            poll_count += 1
            data = client.get_job(access, project_id, job_id)
            if not data:
                with progress_area:
                    st.warning("작업 상태 조회가 지연되고 있습니다. 잠시 후 다시 시도합니다...")
                time.sleep(2.5)
                continue

            status = data.get("status")
            logs = data.get("progress_log") or []
            summary = data.get("summary") or ""
            error = data.get("error_message")
            tool_invocations = data.get("tool_invocations") or []
            is_success = status in ("completed", "success")
            is_failed = status in ("failed", "error")

            if poll_count % 3 == 0 or is_success or is_failed:
                if logs:
                    latest_log = logs[-1]
                    pct = latest_log.get("percent_complete")
                    msg = latest_log.get("log_message")
                    if pct is not None:
                        st.progress(pct / 100, text=f"({pct}%) {msg or '진행 중'}")
                    else:
                        st.info(msg or f"상태: {status}")
                else:
                    st.info(f"상태: {status}")

            if is_success:
                st.success("작업이 완료되었습니다.")
                st.balloons()
                st.session_state.job_result = {
                    "summary": summary,
                    "language": language,
                    "job_type": job_type,
                    "project_id": project_id,
                    "job_id": job_id,
                    "tool_invocations": tool_invocations,
                    "analysis_mode": st.session_state.get("analysis_mode"),
                }
                st.rerun()

            if is_failed:
                st.error(f"작업이 실패했습니다: {error}")
                break

            time.sleep(2.5)

# ----------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------
if "job_result" in st.session_state and st.session_state.job_result.get("summary"):
    jr = st.session_state.job_result
    st.divider()
    st.subheader("결과 및 학습")

    with st.container(border=True):
        st.subheader("- 수행 결과 -")
        summary = jr["summary"]
        lang = jr.get("language")
        job_type = jr.get("job_type")
        tool_invocations = jr.get("tool_invocations") or []
        analysis_mode = jr.get("analysis_mode")

        if job_type == "repository_analysis":
            mode_to_tool = {
                "file_tree": "scan_file_tree",
                "loc": "calculate_loc_per_language",
                "git_diff": "get_diff",
            }
            expected_tool = mode_to_tool.get(analysis_mode)
            tool_output = None
            if expected_tool:
                for invocation in reversed(tool_invocations):
                    if invocation.get("tool_name") == expected_tool:
                        tool_output = invocation.get("tool_output")
                        break

            data_obj = tool_output
            if isinstance(data_obj, str) and analysis_mode in ("file_tree", "loc"):
                try:
                    data_obj = json.loads(data_obj)
                except json.JSONDecodeError:
                    data_obj = None

            handled = False
            if analysis_mode == "file_tree" and isinstance(data_obj, dict):
                st.markdown("##### 📂 파일 트리")
                lines = _tree_lines(data_obj)
                st.markdown("\n".join(lines) if lines else "표시할 파일이 없습니다.")
                with st.expander("Raw JSON 보기"):
                    st.json(data_obj)
                handled = True
            elif analysis_mode == "loc" and isinstance(data_obj, dict) and data_obj:
                st.markdown("##### 🧮 언어별 코드 라인")
                st.bar_chart(data_obj)
                with st.expander("Raw 데이터 보기"):
                    st.json(data_obj)
                handled = True
            elif analysis_mode == "git_diff" and tool_output:
                st.markdown("##### 📑 Git Diff")
                st.code(str(tool_output), language="diff")
                handled = True

            if not handled:
                if lang == "diff":
                    st.code(summary, language="diff")
                elif lang == "json":
                    try:
                        st.json(json.loads(summary))
                    except json.JSONDecodeError:
                        st.code(summary, language="text")
                else:
                    st.code(summary, language="text")
        else:
            st.code(summary, language=lang or "python")

    # ------------------------------------------------------------------
    # Quiz section (code generation only)
    # ------------------------------------------------------------------
    if jr.get("job_type") == "code_generation":
        if "quiz_state" not in st.session_state:
            st.session_state.quiz_state = {"questions": None, "answers": {}, "score": None}

        with st.container(border=True):
            st.subheader("학습 퀴즈")
            st.info("생성된 코드를 바탕으로 퀴즈를 만들어 풀어보세요.")

            if st.button("🧠 퀴즈 생성하기", type="secondary", use_container_width=True):
                with st.spinner("AI가 퀴즈를 생성하는 중입니다..."):
                    quiz = client.generate_quiz_from_code(jr["summary"], num_questions=5)

                if not quiz or quiz.get("error"):
                    err_msg = quiz.get("error", "응답 없음") if quiz else "응답 없음"
                    st.error(f"퀴즈 생성 실패: {err_msg}")
                    if quiz and quiz.get("body"):
                        with st.expander("서버 응답 보기"):
                            st.code(quiz.get("body"), language="json")
                elif not quiz.get("questions"):
                    st.error("퀴즈 생성에 실패했습니다. (문항 없음)")
                else:
                    st.session_state.quiz_state = {"questions": quiz["questions"], "answers": {}, "score": None}
                    st.rerun()

        qs = st.session_state.quiz_state.get("questions")
        if qs:
            meta = {
                "job_id": jr.get("job_id"),
                "project_id": jr.get("project_id"),
                "language": lang,
            }
            if st.button("💾 퀴즈 결과 저장 (Django)", type="secondary", use_container_width=True):
                with st.spinner("퀴즈를 Django 서버에 저장하는 중입니다..."):
                    save_resp = client.save_generated_quiz(access, qs, source="code_generation", metadata=meta)
                if save_resp and save_resp.get("id"):
                    st.success(f"저장 완료! ID: {save_resp.get('id')}")
                else:
                    st.error("저장에 실패했습니다. log/front.log를 확인하세요.")

            with st.form("quiz_form"):
                st.subheader("여기서 퀴즈를 풀어보세요")
                for idx, q in enumerate(qs):
                    with st.container(border=True):
                        st.markdown(f"**Q{idx+1}. {q.get('question')}**")
                        opts = q.get("options") or []
                        key = f"quiz_q_{idx}"
                        st.session_state.quiz_state["answers"][idx] = st.radio(
                            "보기 선택",
                            options=list(range(len(opts))),
                            format_func=lambda i: f"{opts[i]}",
                            key=key,
                            label_visibility="collapsed",
                        )

                submitted = st.form_submit_button("제출 및 채점", type="primary", use_container_width=True)

                if submitted:
                    answers = st.session_state.quiz_state["answers"]
                    score = 0
                    for idx, q in enumerate(qs):
                        correct = int(q.get("correct_index", 0))
                        if answers.get(idx) == correct:
                            score += 1
                    st.session_state.quiz_state["score"] = score

                    st.subheader("채점 결과")
                    col1, col2, col3 = st.columns(3)
                    percentage = (score / len(qs)) * 100
                    col1.metric("정답", score)
                    col2.metric("오답", len(qs) - score)
                    col3.metric("정답률", f"{percentage:.1f}%")

                    if percentage == 100:
                        st.balloons()
                        st.success("완벽해요! 모든 문제를 맞췄습니다.")
                    else:
                        st.info("조금 더 연습해 보세요. 다음에는 더 좋은 결과가 있을 거예요.")

                    meta_event = {
                        "job_id": jr.get("job_id"),
                        "project_id": jr.get("project_id"),
                        "score": score,
                        "total": len(qs),
                    }
                    resp = client.gami_event(access, "QUIZ_COMPLETE", meta_event)
                    if resp:
                        st.success("게이미피케이션 이벤트가 기록되었습니다.")
                    else:
                        st.warning("⚠️ 이벤트 기록에 실패했습니다.")
