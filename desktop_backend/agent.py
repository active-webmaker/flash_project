import os
import re
import uuid
import time
import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime
from collections import defaultdict
import operator
from typing import Annotated, Sequence, TypedDict

import requests
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, FunctionMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor

from git_analyzer import GitAnalyzer
from git_commit_module import GitCommitModule

# 로거 설정 (파일 + 콘솔)
LOG_DIR = "/app/log"
os.makedirs(LOG_DIR, exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 콘솔 핸들러
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

# 파일 핸들러
log_file = os.path.join(LOG_DIR, "agent.log")
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=10
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:8001/v1")
REPO_PATH = os.getenv("REPO_PATH", "./test_repo")

AGENT_VERSION = os.getenv("AGENT_VERSION", "v1.0.0")
AGENT_ID = os.getenv("AGENT_ID", f"agent-py-{uuid.uuid4()}")

job_metrics = defaultdict(dict)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    job_id: str
    job_description: str
    job_payload: dict


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def safe_json_loads(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def ensure_jsonable(value):
    if isinstance(value, (dict, list, int, float, bool)) or value is None:
        return value
    return str(value)


def create_structured_tools(git_analyzer, git_commit_module):
    """
    인스턴스 메서드를 StructuredTool로 변환합니다.
    """
    tools = [
        StructuredTool.from_function(
            func=git_analyzer.scan_file_tree,
            name="scan_file_tree",
            description="로컬 저장소의 파일/디렉터리 트리를 JSON-호환 dict로 반환합니다."
        ),
        StructuredTool.from_function(
            func=git_analyzer.calculate_loc_per_language,
            name="calculate_loc_per_language",
            description="저장소 내 각 프로그래밍 언어별 코드 라인 수(LOC)를 계산합니다."
        ),
        StructuredTool.from_function(
            func=git_commit_module.create_commit,
            name="create_commit",
            description="지정된 파일들을 스테이징하고 새 커밋을 생성합니다."
        ),
        StructuredTool.from_function(
            func=git_commit_module.get_diff,
            name="get_diff",
            description="특정 커밋 또는 HEAD의 변경 사항(diff)을 반환합니다."
        ),
    ]
    return tools


def build_job_prompt(job_payload: dict, job_type: str) -> str:
    """
    LLM이 tool-calling을 더 잘 수행하도록 구조화된 프롬프트를 생성합니다.
    """
    # 지정된 도구명이 있는 경우 우선 사용
    tool_name = job_payload.get('tool_name')

    if tool_name:
        # 도구가 명시적으로 지정된 경우
        prompt_template = f"""당신은 제공된 도구를 사용하여 작업을 수행하는 AI 에이전트입니다.

## 지시사항
1. 아래의 **지정된 도구**를 사용하여 작업을 수행하세요.
2. 다른 도구가 아닌, 정확히 명시된 도구만 호출하세요.
3. 다른 어떤 텍스트도 없이, 도구를 호출하는 JSON 객체만을 응답으로 출력해야 합니다.

## 지정된 도구
{tool_name}

## 응답 형식
{{"name": "{tool_name}", "arguments": {{}}}}
"""
    else:
        # 도구가 명시되지 않은 경우 (일반적인 repository_analysis)
        description = (
            job_payload.get('description')
            or job_payload.get('prompt')
            or job_payload.get('title')
            or job_type
        )

        # 사용 가능한 도구 목록을 프롬프트에 명시적으로 추가
        tool_definitions = "\n".join([f"- {tool.name}: {tool.description}" for tool in tools])

        # 최종 프롬프템플릿
        prompt_template = f"""당신은 제공된 도구를 사용하여 작업을 수행하는 AI 에이전트입니다.

## 지시사항
1. 아래 `작업 내용`을 분석하세요.
2. `사용 가능한 도구` 목록에서 작업을 해결하는 데 가장 적합한 도구를 **하나만** 선택하세요.
3. 다른 어떤 텍스트도 없이, 선택한 도구를 호출하는 JSON 객체만을 응답으로 출력해야 합니다.

## 작업 내용
{description}

## 사용 가능한 도구
{tool_definitions}

## 응답 형식
반드시 다음 JSON 형식 중 하나로 응답하세요.

- 인수가 없는 도구의 경우:
{{"name": "도구_이름", "arguments": {{}}}}

- 인수가 있는 도구의 경우:
{{"name": "도구_이름", "arguments": {{"인수_이름": "값", ...}}}}
"""
    
    # payload의 다른 정보들을 추가 (선택적)
    # project_section = job_payload.get('project')
    # if isinstance(project_section, dict) and project_section:
    #     prompt_template += "\n\n## 프로젝트 컨텍스트\n" + json.dumps(project_section, indent=2, ensure_ascii=False)

    return prompt_template


def init_test_repo_with_samples(repo_path: str):
    """테스트용 repo를 샘플 파일과 함께 초기화합니다."""
    from git import Repo

    os.makedirs(repo_path, exist_ok=True)

    # 이미 git repo인지 확인
    git_dir = os.path.join(repo_path, '.git')
    if not os.path.exists(git_dir):
        Repo.init(repo_path)
        logger.info(f"Git repository initialized at {repo_path}")

    # 샘플 파일 구조 생성
    sample_files = {
        "README.md": "# Test Repository\n\nThis is a test repository for git analysis.\n",
        "src/main.py": "def hello():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    hello()\n",
        "src/utils.py": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n",
        "tests/test_main.py": "import unittest\nfrom src.main import hello\n\nclass TestMain(unittest.TestCase):\n    def test_hello(self):\n        self.assertTrue(True)\n",
        "config.json": '{"name": "test-project", "version": "1.0.0"}\n',
        ".gitignore": "__pycache__/\n*.pyc\n.venv/\n",
    }

    # 파일 생성
    files_created = False
    for file_path, content in sample_files.items():
        full_path = os.path.join(repo_path, file_path)
        dir_path = os.path.dirname(full_path)

        # 디렉터리 생성
        os.makedirs(dir_path, exist_ok=True)

        # 파일이 없으면 생성
        if not os.path.exists(full_path):
            with open(full_path, "w") as f:
                f.write(content)
            logger.debug(f"Created sample file: {file_path}")
            files_created = True

    if files_created:
        logger.info(f"Sample files created in {repo_path}")

        # 샘플 파일을 git에 커밋
        try:
            repo = Repo(repo_path)

            # Git 사용자 설정 (Docker 환경에서는 필요)
            try:
                with repo.config_reader() as git_config:
                    git_config.get_value("user", "name")
            except:
                # 사용자 설정이 없으면 추가
                repo.config_writer().set_value("user", "name", "Agent Bot").release()
                repo.config_writer().set_value("user", "email", "agent@bot.local").release()
                logger.debug("Git user config set")

            # 생성된 모든 파일을 스테이징 (명시적 리스트)
            files_to_add = list(sample_files.keys())
            repo.index.add(files_to_add)
            logger.debug(f"Staged files: {files_to_add}")

            # 커밋 생성
            repo.index.commit("Initial commit with sample files")
            logger.info(f"Sample files committed to git")
        except Exception as e:
            logger.warning(f"Failed to commit sample files: {e}", exc_info=True)
    else:
        # 파일이 이미 있어도 커밋되지 않았을 수 있으므로 확인
        try:
            repo = Repo(repo_path)

            # Git 사용자 설정 확인
            try:
                with repo.config_reader() as git_config:
                    git_config.get_value("user", "name")
            except:
                repo.config_writer().set_value("user", "name", "Agent Bot").release()
                repo.config_writer().set_value("user", "email", "agent@bot.local").release()

            # 커밋할 파일이 있는지 확인
            if repo.index.diff(None) or repo.untracked_files:
                # 모든 파일을 추가
                untracked = repo.untracked_files
                repo.index.add(untracked)
                logger.debug(f"Staged untracked files: {untracked}")

                repo.index.commit("Commit pending sample files")
                logger.info(f"Pending sample files committed to git")
        except Exception as e:
            logger.debug(f"No pending files to commit: {e}")


# repo 초기화 및 샘플 파일 생성
if not os.path.exists(REPO_PATH):
    logger.warning(f"Test repository not found at {REPO_PATH}. Initializing a new one.")
    init_test_repo_with_samples(REPO_PATH)
else:
    # 기존 repo가 있어도 샘플 파일이 없으면 생성
    if not os.path.exists(os.path.join(REPO_PATH, "src")):
        logger.info(f"Adding sample files to existing repository at {REPO_PATH}")
        init_test_repo_with_samples(REPO_PATH)


git_analyzer = GitAnalyzer(repo_path=REPO_PATH)
git_commit_module = GitCommitModule(repo_path=REPO_PATH)


# 전역 tools를 StructuredTool로 변환
tools = create_structured_tools(git_analyzer, git_commit_module)
tool_executor = ToolExecutor(tools)


llm = ChatOpenAI(
    openai_api_base=LOCAL_LLM_URL,
    openai_api_key="dummy_key",
    temperature=0,
    streaming=True,
)

# 도구 선택용 LLM (tool-calling 활성화)
llm_with_tools = llm.bind_tools(tools)

# 분석용 LLM (순수 채팅, tool-calling 없음)
llm_for_analysis = ChatOpenAI(
    openai_api_base=LOCAL_LLM_URL,
    openai_api_key="dummy_key",
    temperature=0,
    streaming=False,
)


def should_continue(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    # If the LLM makes a tool call, then we route to the "action" node
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    # Otherwise, we end the conversation
    return "end"


def call_model(state: AgentState):
    """
    LLM을 호출하고, 응답 텍스트에서 JSON 도구 호출을 파싱하여 구조화된 AIMessage를 생성합니다.
    """
    messages = state['messages']
    response = llm_with_tools.invoke(messages)
    
    # 모델의 텍스트 응답에서 JSON 블록을 찾으려는 시도
    try:
        # 응답 내용에서 ```json ... ``` 블록 또는 일반 JSON 객체 추출
        content = response.content
        match = re.search(r"```json\s*([\s\S]*?)\s*```|({[\s\S]*}*)", content)

        if match:
            json_str = match.group(1) or match.group(2)
            tool_call_data = json.loads(json_str)

            # LangChain의 ToolCall 형식으로 변환
            if "name" in tool_call_data and "arguments" in tool_call_data:
                response.tool_calls = [
                    {
                        "id": f"tool_call_{uuid.uuid4()}",
                        "name": tool_call_data["name"],
                        "args": tool_call_data["arguments"],
                    }
                ]
                logger.info(f"✅ 모델 응답에서 Tool Call을 성공적으로 파싱했습니다: {tool_call_data['name']}")
    except (json.JSONDecodeError, AttributeError) as e:
        logger.warning(f"⚠️ 모델 응답에서 Tool Call을 파싱하는 데 실패했습니다. 응답을 그대로 반환합니다. 오류: {e}")
        # 파싱 실패 시, tool_calls가 없는 원래 응답을 반환
        pass

    return {"messages": [response]}


from langchain_core.messages import BaseMessage, FunctionMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor, ToolInvocation

# ... (rest of the imports)

# ... (code before call_tool)

def call_tool(state: AgentState, executor=None):
    """Global tool executor를 사용하는 버전"""
    messages = state['messages']
    last_message = messages[-1]

    # tool_calls는 LangChain이 생성하는 표준 속성입니다.
    tool_invocations = []
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        logger.warning("call_tool 노드에 도달했지만, 마지막 메시지에 tool_calls가 없습니다.")
        return {"messages": [HumanMessage(content="모델이 도구를 호출하지 않고 응답을 종료했습니다.")]}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call.get("name")
        parsed_args = tool_call.get("args")
        
        logger.info(f"도구 호출: {tool_name} (인수: {parsed_args})")
        report_job_progress(state['job_id'], log_message=f"Calling tool '{tool_name}'")
        report_tool_callback(state['job_id'], tool_name, parsed_args)
        
        # ToolExecutor가 ToolInvocation 객체를 기대하므로 변환
        tool_invocations.append(
            ToolInvocation(tool=tool_name, tool_input=parsed_args)
        )

    # 모든 도구를 실행
    responses = tool_executor.batch(tool_invocations)
    
    # 각 실행 결과를 ToolMessage로 변환
    tool_messages = []
    for tool_call, response in zip(last_message.tool_calls, responses):
        tool_messages.append(
            ToolMessage(content=str(response), tool_call_id=tool_call.get("id"))
        )
        report_tool_callback(state['job_id'], tool_call.get("name"), tool_call.get("args"), tool_output=ensure_jsonable(response))

    job_metrics.setdefault(state['job_id'], {"tool_calls": 0, "started_at": time.time()})
    job_metrics[state['job_id']]['tool_calls'] += len(tool_invocations)

    return {"messages": tool_messages}


def call_tool_with_executor(state: AgentState, executor):
    """Job-specific tool executor를 사용하는 버전"""
    messages = state['messages']
    last_message = messages[-1]

    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        logger.warning("call_tool_with_executor 노드에 도달했지만, 마지막 메시지에 tool_calls가 없습니다.")
        return {"messages": [HumanMessage(content="모델이 도구를 호출하지 않고 응답을 종료했습니다.")]}
        
    tool_invocations = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call.get("name")
        parsed_args = tool_call.get("args")

        logger.info(f"Job-specific 도구 호출: {tool_name} (인수: {parsed_args})")
        report_job_progress(state['job_id'], log_message=f"Calling tool '{tool_name}'")
        report_tool_callback(state['job_id'], tool_name, parsed_args)

        tool_invocations.append(
            ToolInvocation(tool=tool_name, tool_input=parsed_args)
        )

    responses = executor.batch(tool_invocations)
    
    tool_messages = []
    for tool_call, response in zip(last_message.tool_calls, responses):
        tool_messages.append(
            ToolMessage(content=str(response), tool_call_id=tool_call.get("id"))
        )
        report_tool_callback(state['job_id'], tool_call.get("name"), tool_call.get("args"), tool_output=ensure_jsonable(response))

    job_metrics.setdefault(state['job_id'], {"tool_calls": 0, "started_at": time.time()})
    job_metrics[state['job_id']]['tool_calls'] += len(tool_invocations)

    return {"messages": tool_messages}


def analyze_tool_results(state: AgentState, llm):
    """도구 실행 결과를 LLM이 분석하고 해석합니다."""
    try:
        messages = state['messages']

        if not messages:
            logger.warning("메시지가 없어서 분석할 수 없습니다.")
            return {"messages": []}

        # 마지막 ToolMessage 찾기
        tool_message = None
        for msg in reversed(messages):
            if isinstance(msg, ToolMessage):
                tool_message = msg
                break

        if not tool_message:
            logger.warning("분석할 ToolMessage를 찾을 수 없습니다.")
            return {"messages": []}

        # 도구명 찾기
        tool_name = None
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if tool_call.get('id') == tool_message.tool_call_id:
                        tool_name = tool_call.get('name')
                        break
                if tool_name:
                    break

        # 도구별 분석 프롬프트
        analysis_prompts = {
            'calculate_loc_per_language': """다음은 저장소의 언어별 코드 라인 수(LOC) 분석 결과입니다.

결과: {result}

이 결과를 자연어로 분석하고 해석해 주세요. 예를 들어:
- 어떤 언어가 가장 많은가?
- 프로젝트의 기술 스택은 무엇인가?
- 각 언어의 비율은 어느 정도인가?
""",
            'get_diff': """다음은 저장소의 변경 사항(Diff) 조회 결과입니다.

결과: {result}

이 Diff를 자연어로 요약해 주세요. 예를 들어:
- 어떤 파일들이 변경되었는가?
- 주요 변경 사항은 무엇인가?
- 변경 규모는 어느 정도인가?
"""
        }

        # 도구별 분석 프롬프트 선택
        if tool_name in analysis_prompts:
            analysis_prompt = analysis_prompts[tool_name].format(result=tool_message.content)
            logger.info(f"도구 결과 분석 중: {tool_name}")

            # LLM으로 분석
            analysis_response = llm.invoke([
                HumanMessage(content=analysis_prompt)
            ])

            logger.info(f"분석 완료: {tool_name}")
            return {"messages": [analysis_response]}
        else:
            logger.debug(f"분석 대상이 아닌 도구: {tool_name}, 분석 스킵")
            return {"messages": []}

    except Exception as e:
        logger.error(f"도구 분석 중 오류 발생: {e}", exc_info=True)
        return {"messages": []}

# ... (rest of the file)



def report_job_status(job_id, phase, summary=None, result_url=None, error_message=None, job_status=None):
    endpoint = f"{API_BASE_URL}/agent/jobs/{job_id}/{phase}"
    payload = {"agent_id": AGENT_ID}

    if phase == 'start':
        payload['start_time'] = utc_now_iso()
    elif phase == 'complete':
        status_value = job_status or ('failed' if error_message else 'success')
        payload['status'] = status_value
        if summary is not None:
            payload['summary'] = summary
        if result_url is not None:
            payload['final_result_url'] = result_url
        if error_message is not None:
            payload['error_message'] = error_message
    else:
        logger.debug(f"Unsupported job phase '{phase}'")
        return

    try:
        requests.post(endpoint, json=payload).raise_for_status()
        logger.info(f"Reported job {job_id} phase '{phase}'")
    except requests.RequestException as exc:
        logger.error(f"Failed to report job phase '{phase}' for job {job_id}: {exc}")


def report_job_progress(job_id, log_message=None, percent_complete=None, intermediate_artifact=None):
    endpoint = f"{API_BASE_URL}/agent/jobs/{job_id}/progress"
    payload = {"agent_id": AGENT_ID}
    if log_message is not None:
        payload['log_message'] = log_message
    if percent_complete is not None:
        payload['percent_complete'] = percent_complete
    if intermediate_artifact is not None:
        payload['intermediate_artifact'] = intermediate_artifact

    try:
        requests.post(endpoint, json=payload).raise_for_status()
    except requests.RequestException as exc:
        logger.debug(f"Failed to report progress for job {job_id}: {exc}")


def report_tool_callback(job_id, tool_name, tool_input, tool_output=None):
    endpoint = f"{API_BASE_URL}/agent/callbacks/tool"
    payload = {
        'run_id': str(job_id),
        'tool_name': tool_name,
        'tool_input': ensure_jsonable(tool_input),
    }
    if tool_output is not None:
        payload['tool_output'] = ensure_jsonable(tool_output)

    try:
        requests.post(endpoint, json=payload).raise_for_status()
    except requests.RequestException as exc:
        logger.debug(f"Failed to report tool callback for job {job_id}: {exc}")


def report_telemetry(job_id, metrics):
    endpoint = f"{API_BASE_URL}/agent/telemetry"
    metrics_list = []
    if 'tool_calls' in metrics:
        metrics_list.append({
            'name': 'tool_calls',
            'value': float(metrics.get('tool_calls', 0)),
            'job_id': str(job_id),
        })
    if 'duration_ms' in metrics:
        metrics_list.append({
            'name': 'job_duration_ms',
            'value': float(metrics.get('duration_ms', 0)),
            'job_id': str(job_id),
        })

    if not metrics_list:
        metrics_list.append({'name': 'job_duration_ms', 'value': 0.0, 'job_id': str(job_id)})

    payload = {
        'agent_id': AGENT_ID,
        'metrics': metrics_list,
    }

    try:
        requests.post(endpoint, json=payload).raise_for_status()
    except requests.RequestException as exc:
        logger.debug(f"Failed to report telemetry for job {job_id}: {exc}")


def send_heartbeat(status_value, current_job_id=None):
    endpoint = f"{API_BASE_URL}/agent/heartbeat"
    payload = {
        'agent_id': AGENT_ID,
        'status': status_value,
        'agent_version': AGENT_VERSION,
    }
    if current_job_id:
        payload['current_job_id'] = str(current_job_id)

    try:
        requests.post(endpoint, json=payload).raise_for_status()
    except requests.RequestException as exc:
        logger.debug(f"Heartbeat failed: {exc}")


workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.add_node("action", call_tool)
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "action",
        "end": END,
    },
)
workflow.add_edge("action", "agent")
app = workflow.compile()


def run_agent():
    logger.info("=" * 80)
    logger.info(f"🚀 Starting agent {AGENT_ID} (version {AGENT_VERSION})...")
    logger.info("=" * 80)
    logger.info(f"API Server: {API_BASE_URL}")
    logger.info(f"Local LLM: {LOCAL_LLM_URL}")
    logger.info(f"Repository: {REPO_PATH}")
    logger.info("=" * 80)

    while True:
        try:
            send_heartbeat('idle')
            request_payload = {
                'agent_id': AGENT_ID,
                'capabilities': [tool.name for tool in tools],
                'status': 'idle',
                'max_jobs': 1,
                'agent_version': AGENT_VERSION,
            }
            logger.debug("📤 Job 요청 중...")
            response = requests.post(f"{API_BASE_URL}/agent/jobs/request", json=request_payload)

            if response.status_code == 204:
                logger.debug("⏳ Job 없음. 대기 중...")
                time.sleep(10)
                continue
            if response.status_code != 200:
                logger.warning(f"⚠️ 예상치 못한 응답 {response.status_code}: {response.text}")
                time.sleep(10)
                continue

            try:
                payload = response.json()
            except ValueError:
                logger.warning("⚠️ Job 요청 응답이 JSON 형식이 아님")
                time.sleep(10)
                continue

            jobs = payload.get('jobs') if isinstance(payload, dict) else None
            if not jobs:
                logger.debug("⏳ Job 없음. 대기 중...")
                time.sleep(10)
                continue

            job = jobs[0]
            job_id = job.get('job_id') or job.get('id')
            logger.debug(f" 수신된 JOB 페이로드: {job}")
            if job_id is None:
                logger.warning("⚠️ Job ID 없음. 스킵...")
                time.sleep(10)
                continue

            job_payload = job.get('payload', {}) or {}
            job_type = job.get('job_type', '')
            
            logger.info("=" * 80)
            logger.info(f"✅ 새 Job 수신: {job_id}, 타입: {job_type}")
            logger.info("=" * 80)

            # --- 경로 변환 로직 (모든 Job 유형에 공통) ---
            project_local_path = os.path.normpath(REPO_PATH)
            logger.info(f"Job path overridden to use REPO_PATH: '{project_local_path}'")
            
            # 이 job의 GitAnalyzer와 GitCommitModule을 새로 생성
            job_git_analyzer = GitAnalyzer(repo_path=project_local_path)
            job_git_commit_module = GitCommitModule(repo_path=project_local_path)

            # StructuredTool로 변환하여 self 바인딩 문제 해결
            job_tools = create_structured_tools(job_git_analyzer, job_git_commit_module)
            job_tool_executor = ToolExecutor(job_tools)
            # --- 경로 변환 로직 끝 ---

            # Job 유형에 따라 분기
            # repository_analysis에서 tool_name이 명시된 경우도 direct_tool_call처럼 처리
            is_direct_tool_call = (job_type == 'direct_tool_call') or (job_type == 'repository_analysis' and job_payload.get('tool_name'))

            if is_direct_tool_call:
                logger.info(f"🚀 직접 도구 호출 Job 처리 시작: {job_id}")
                send_heartbeat('processing', current_job_id=job_id)
                report_job_status(job_id, 'start')

                try:
                    tool_name = job_payload.get("tool_name")
                    tool_args = job_payload.get("tool_args", {})
                    
                    if not tool_name:
                        raise ValueError("Payload에 'tool_name'이 지정되지 않았습니다.")

                    logger.info(f"실행할 도구: {tool_name}, 인수: {tool_args}")
                    report_job_progress(job_id, log_message=f"Directly invoking tool: {tool_name}", percent_complete=30)
                    # Frontend가 결과를 파싱할 수 있도록 tool_invocations에 기록
                    report_tool_callback(job_id, tool_name, tool_args)


                    # 도구 실행
                    tool_to_run = next((t for t in job_tools if t.name == tool_name), None)
                    if not tool_to_run:
                        raise ValueError(f"'{tool_name}'에 해당하는 도구를 찾을 수 없습니다.")

                    result = tool_to_run.invoke(tool_args)

                    # 실행 결과를 tool_invocations에 업데이트
                    report_tool_callback(job_id, tool_name, tool_args, tool_output=ensure_jsonable(result))
                    logger.info(f"✅ 도구 실행 완료. 결과 타입: {type(result)}")

                    # 분석 대상 도구인 경우 LLM으로 결과 분석
                    analysis_tools = ['calculate_loc_per_language', 'get_diff']
                    final_summary = None

                    if tool_name in analysis_tools:
                        logger.info(f"도구 결과를 LLM으로 분석 중: {tool_name}")
                        report_job_progress(job_id, log_message=f"Analyzing tool output from {tool_name}...", percent_complete=70)

                        # 도구별 분석 프롬프트
                        analysis_prompts = {
                            'calculate_loc_per_language': """다음은 저장소의 언어별 코드 라인 수(LOC) 분석 결과입니다.

결과: {result}

이 결과를 자연어로 분석하고 해석해 주세요. 예를 들어:
- 어떤 언어가 가장 많은가?
- 프로젝트의 기술 스택은 무엇인가?
- 각 언어의 비율은 어느 정도인가?
""",
                            'get_diff': """다음은 저장소의 변경 사항(Diff) 조회 결과입니다.

결과: {result}

이 Diff를 자연어로 요약해 주세요. 예를 들어:
- 어떤 파일들이 변경되었는가?
- 주요 변경 사항은 무엇인가?
- 변경 규모는 어느 정도인가?
"""
                        }

                        if tool_name in analysis_prompts:
                            analysis_prompt = analysis_prompts[tool_name].format(result=str(result))

                            try:
                                analysis_response = llm_for_analysis.invoke([
                                    HumanMessage(content=analysis_prompt)
                                ])
                                final_summary = analysis_response.content
                                logger.info(f"✅ 분석 완료: {tool_name}")
                            except Exception as e:
                                logger.error(f"분석 중 오류: {e}", exc_info=True)
                                final_summary = str(result)
                        else:
                            final_summary = str(result)
                    else:
                        final_summary = str(result)

                    report_job_progress(job_id, log_message="Tool execution and analysis finished.", percent_complete=100)
                    report_job_status(job_id, 'complete', summary=final_summary, job_status='success')
                    
                    logger.info(f"🎉 직접 도구 호출 Job {job_id} 정상 완료")

                except Exception as e:
                    logger.exception(f"❌ 직접 도구 호출 Job {job_id} 실패: {e}")
                    report_job_status(job_id, 'complete', summary=str(e), error_message=str(e), job_status='failed')
                
                finally:
                    send_heartbeat('idle')
                    continue # LLM 호출 로직을 건너뛰고 다음 루프로 이동

            # --- 기존 LLM 기반 작업 처리 ---
            job_description = build_job_prompt(job_payload, job_type)
            
            # 이 job을 위한 새로운 app 생성
            job_workflow = StateGraph(AgentState)
            job_workflow.add_node("agent", call_model)
            job_workflow.add_node("action", lambda state: call_tool_with_executor(state, job_tool_executor))
            job_workflow.add_node("analyze", lambda state: analyze_tool_results(state, llm_with_tools))
            job_workflow.set_entry_point("agent")
            job_workflow.add_conditional_edges(
                "agent",
                should_continue,
                {
                    "continue": "action",
                    "end": END,
                },
            )
            def should_analyze(state: AgentState):
                """도구 실행 후 분석이 필요한지 판단"""
                # 분석 대상 도구 목록
                analysis_tools = ['calculate_loc_per_language', 'get_diff']

                # 마지막 메시지가 ToolMessage인지 확인
                if not state['messages']:
                    return "end"

                last_msg = state['messages'][-1]
                if not isinstance(last_msg, ToolMessage):
                    return "end"

                # AIMessage에서 tool_name 찾기
                tool_name = None
                for i in range(len(state['messages']) - 2, -1, -1):
                    msg = state['messages'][i]
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        # 마지막 ToolMessage와 일치하는 tool_call 찾기
                        for tool_call in msg.tool_calls:
                            if tool_call.get('id') == last_msg.tool_call_id:
                                tool_name = tool_call.get('name')
                                logger.debug(f"분석 결정: 도구명={tool_name}, 분석대상={tool_name in analysis_tools}")
                                return "analyze" if tool_name in analysis_tools else "end"

                logger.debug("도구명을 찾을 수 없어 분석 스킵")
                return "end"

            job_workflow.add_conditional_edges(
                "action",
                should_analyze,
                {
                    "analyze": "analyze",
                    "end": END,
                }
            )
            job_workflow.add_edge("analyze", END)
            job_app = job_workflow.compile()

            send_heartbeat('assigned', current_job_id=job_id)
            report_job_status(job_id, 'start')
            job_metrics[job_id] = {"tool_calls": 0, "started_at": time.time()}
            logger.info(f"🔄 Job {job_id} 수락 - Agent 처리 시작")
            report_job_progress(job_id, log_message="Job accepted by agent.", percent_complete=0)

            inputs = {
                'messages': [HumanMessage(content=job_description)],
                'job_id': str(job_id),
                'job_description': job_description,
                'job_payload': job_payload,
            }

            try:
                send_heartbeat('processing', current_job_id=job_id)
                logger.info(f"⚙️ Job {job_id} 실행 중...")
                final_state = job_app.invoke(inputs)
                final_message = final_state['messages'][-1].content
                logger.debug(f"Job {job_id} 최종 상태: {final_state}")


                logger.info(f"✅ Job {job_id} 실행 완료")
                logger.info(f"📝 결과 길이: {len(final_message)} 글자")

                report_job_progress(job_id, log_message="Job execution finished.", percent_complete=100)
                result_url = None
                metadata = job_payload.get('metadata')
                if isinstance(metadata, dict):
                    result_url = metadata.get('result_url')
                report_job_status(job_id, 'complete', summary=final_message, result_url=result_url)
                logger.info("=" * 80)
                logger.info(f"🎉 Job {job_id} 정상 완료")
                logger.info("=" * 80)

            except Exception as job_error:
                logger.exception(f"❌ Job {job_id} 실패: {job_error}")
                # 실패 상태를 API 서버에 보고
                report_job_progress(job_id, log_message=f"Job failed: {job_error}")
                report_job_status(
                    job_id,
                    'complete',
                    summary=f"An unexpected error occurred: {job_error}",
                    error_message=str(job_error),
                    job_status='failed',
                )
                logger.info("=" * 80)
                logger.error(f"❌ Job {job_id} 오류 완료")
                logger.info("=" * 80)

            finally:
                metrics = job_metrics.pop(job_id, {})
                started_at = metrics.get('started_at') or time.time()
                metrics['duration_ms'] = int((time.time() - started_at) * 1000)
                metrics['tool_calls'] = metrics.get('tool_calls', 0)
                logger.info(f"📊 Job {job_id} 메트릭 - 소요시간: {metrics['duration_ms']}ms, Tool 호출: {metrics['tool_calls']}회")
                report_telemetry(job_id, metrics)
                send_heartbeat('idle')

        except requests.RequestException as exc:
            logger.error(f"Could not connect to API server: {exc}. Retrying in 30 seconds...")
            time.sleep(30)
        except Exception as exc:
            logger.error(f"An unexpected error occurred: {exc}", exc_info=True)
            time.sleep(10)


if __name__ == "__main__":
    print("Desktop Backend Agent is running. Press Ctrl+C to stop.")
    # run_agent()  # Execution entrypoint is managed elsewhere.
