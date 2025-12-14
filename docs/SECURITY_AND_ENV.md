# 보안/환경변수 가이드 (SECURITY_AND_ENV)

이 프로젝트는 GitHub 업로드를 전제로 하며, **비밀정보(API Key/토큰/비밀번호)를 저장소에 커밋하지 않는 것**을 원칙으로 합니다.

## 1) 절대 커밋하면 안 되는 것

- `.env` 파일
- API Key/토큰/비밀번호/서명키 등 모든 민감정보
- 개인 PC 경로가 포함된 모델 파일 경로, 다운로드 URL 등(필요 시 로컬에서만 관리)

## 2) 권장 방식

- `.env.example`을 템플릿으로 유지합니다.
- 실제 값은 로컬의 `.env`에만 저장합니다.
- 배포 환경에서는 CI/CD 또는 배포 플랫폼의 Secret/Environment Variable 기능을 사용합니다.

## 3) 주요 환경변수(이름만 안내)

아래 변수들은 `.env.example`에 정의되어 있으며, 필요한 경우 `.env`에서 설정합니다.

- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_PORT`
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`
- `API_BASE_URL`
- `LOCAL_LLM_URL`
- `OPENAI_API_KEY` (선택)
- 로컬 LLM 실행용: `MODEL_PATH`, `MODEL_DOMAIN`, `MODEL_PORT`

## 4) 로컬 LLM(OpenAI 호환) 사용 시 주의

- 로컬 LLM 서버는 OpenAI 호환 API(`/v1`)를 제공합니다.
- `OPENAI_API_KEY`가 없을 때도 동작하도록 `LOCAL_LLM_URL`을 사용합니다.
- 로컬 LLM 서버 구동에 필요한 모델 파일은 저장소에 포함하지 않는 것을 권장합니다.
