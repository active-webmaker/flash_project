# app.py (FastAPI 퀴즈/코드 생성 서버)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import asyncio
import json
import re
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Code Agent Minimal Orchestrator")

# 모델 인스턴스를 저장할 전역 변수
_rewrite_chain = None
_code_chain = None

# 스타트업 이벤트
@app.on_event("startup")
async def startup_event():
    """FastAPI 서버 시작 시 실행"""
    logger.info("=" * 80)
    logger.info("🚀 FastAPI 서버 시작됨")
    logger.info("=" * 80)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    local_llm_url = os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:8008/v1")

    if openai_api_key:
        logger.info("LLM 설정: OpenAI API 사용")
    else:
        logger.info(f"LLM 설정: 로컬 LLM 서버 ({local_llm_url})")

    logger.info("엔드포인트:")
    logger.info("  - POST /generate (코드 생성)")
    logger.info("  - POST /quiz_from_code (퀴즈 생성)")
    logger.info("  - GET /health (헬스 체크)")
    logger.info("=" * 80)

@app.get("/health")
async def health():
    """헬스 체크 엔드포인트"""
    return {"status": "ok", "service": "FastAPI Code/Quiz Generator"}

def get_llm_model():
    """
    LLM 모델 초기화 (지연 초기화)
    OpenAI API 키가 없으면 로컬 LLM으로 폴백
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")

    if openai_api_key:
        logger.info("OpenAI API 사용")
        return ChatOpenAI(model="gpt-4o-mini")
    else:
        logger.info("OpenAI API 키 미설정 - 로컬 LLM으로 폴백")
        # 로컬 LLM 서버 주소
        local_llm_url = os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:8008/v1")
        return ChatOpenAI(
            openai_api_base=local_llm_url,
            openai_api_key="dummy_key",
            temperature=0,
        )

def get_rewrite_chain():
    """프롬프트 재작성 체인 (지연 초기화)"""
    global _rewrite_chain
    if _rewrite_chain is None:
        model = get_llm_model()
        _rewrite_chain = (
            ChatPromptTemplate.from_template(
                "아래 사용자의 목적을 보존하면서 프롬프트를 명확하고 실행가능하게 재작성하세요.\n"
                "원문:\n{user_prompt}\n\n재작성:"
            ) | model | StrOutputParser()
        )
    return _rewrite_chain

def get_code_chain():
    """코드 생성 체인 (지연 초기화)"""
    global _code_chain
    if _code_chain is None:
        model = get_llm_model()
        _code_chain = (
            ChatPromptTemplate.from_template(
                "요구사항:\n{requirements}\n"
                "파이썬 함수로 구현하고, 주석/엣지케이스 포함. 코드만 출력:"
            ) | model | StrOutputParser()
        )
    return _code_chain

class GenerateIn(BaseModel):
    prompt: str

class GenerateOut(BaseModel):
    rewritten: str
    code: str

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_index: int

class QuizFromCodeIn(BaseModel):
    code: str
    num_questions: int = 5

class QuizFromCodeOut(BaseModel):
    questions: List[QuizQuestion]

@app.post("/generate", response_model=GenerateOut)
async def generate(body: GenerateIn):
    try:
        logger.info(f"[/generate] 요청 수신 - prompt 길이: {len(body.prompt)}")
        rewrite_chain = get_rewrite_chain()
        code_chain = get_code_chain()

        logger.info("[/generate] 프롬프트 재작성 중...")
        rewritten = await asyncio.to_thread(rewrite_chain.invoke, {"user_prompt": body.prompt})

        logger.info("[/generate] 코드 생성 중...")
        code = await asyncio.to_thread(code_chain.invoke, {"requirements": rewritten})

        logger.info(f"[/generate] 완료 - 생성된 코드 길이: {len(code)}")
        return {"rewritten": rewritten, "code": code}
    except Exception as e:
        logger.error(f"[/generate] 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(500, str(e))

@app.post("/quiz_from_code", response_model=QuizFromCodeOut)
async def quiz_from_code(body: QuizFromCodeIn):
    try:
        logger.info(f"[/quiz_from_code] 요청 수신 - code 길이: {len(body.code)}, num_questions: {body.num_questions}")

        # Force JSON output to reduce parsing errors
        # Use the same LLM selection logic as other handlers: prefer external OpenAI if API key is set,
        # otherwise fall back to local LLM server (default port 8008).
        openai_api_key = os.getenv("OPENAI_API_KEY")

        if openai_api_key:
            logger.info("[/quiz_from_code] OpenAI API 사용")
            quiz_model = ChatOpenAI(
                model="gpt-4o-mini",
                model_kwargs={"response_format": {"type": "json_object"}},
                temperature=0.2,
            )
        else:
            logger.info("[/quiz_from_code] 로컬 LLM으로 퀴즈 생성")
            local_llm_url = os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:8008/v1")
            quiz_model = ChatOpenAI(
                openai_api_base=local_llm_url,
                openai_api_key="dummy_key",
                temperature=0.2,
                model_kwargs={"response_format": {"type": "json_object"}},
            )

        prompt = ChatPromptTemplate.from_template(
            """
            다음 코드를 기반으로 객관식 퀴즈를 {num}문제 생성하세요.
            출력은 반드시 아래 JSON 오브젝트 형태여야 합니다.
            {{"questions": [{{"question": "...", "options": ["...","...","...","..."], "correct_index": 0}}, ...]}}
            - 'options'는 정확히 4개.
            - 'correct_index'는 0~3 범위의 정수.

            코드:
            {code}
            """
        )
        chain = prompt | quiz_model | StrOutputParser()
        logger.info("[/quiz_from_code] LLM에 퀴즈 생성 요청 중...")
        raw = await asyncio.to_thread(chain.invoke, {"code": body.code, "num": body.num_questions})
        logger.info("[/quiz_from_code] LLM 응답 수신")

        def parse_questions(text: str):
            try:
                obj = json.loads(text)
                if isinstance(obj, dict) and isinstance(obj.get("questions"), list):
                    return obj["questions"]
                if isinstance(obj, list):
                    return obj
            except Exception:
                pass
            # Fallback: extract first JSON array
            m = re.search(r"\[[\s\S]*\]", text)
            if m:
                try:
                    arr = json.loads(m.group(0))
                    return arr
                except Exception:
                    pass
            raise ValueError("Could not parse quiz JSON")

        logger.info("[/quiz_from_code] JSON 파싱 시작...")
        data = parse_questions(raw)
        logger.info(f"[/quiz_from_code] 파싱된 문항 수: {len(data)}")

        questions: List[QuizQuestion] = []
        for idx, item in enumerate(data):
            # Ensure all options are strings to prevent Pydantic validation errors
            raw_options = item.get("options") or []
            string_options = [str(opt) for opt in raw_options]

            q = QuizQuestion(
                question=item.get("question", ""),
                options=string_options[:4],
                correct_index=int(item.get("correct_index", 0)),
            )
            q.correct_index = max(0, min(3, q.correct_index))
            # pad/truncate options to 4
            opts = q.options + [""] * (4 - len(q.options))
            q.options = opts[:4]
            questions.append(q)
            logger.debug(f"[/quiz_from_code] 문항 {idx+1}: {q.question[:50]}...")

        logger.info(f"[/quiz_from_code] ✅ 완료 - {len(questions)}개 문항 반환")
        return {"questions": questions[: body.num_questions]}
    except Exception as e:
        logger.error(f"[/quiz_from_code] ❌ 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(500, f"quiz_from_code failed: {e}")
