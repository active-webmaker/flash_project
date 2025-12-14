# Flash API 개발 가이드

# API 설명

### 1\. 공통 (인증/유저/헬스)

* **해당 컴포넌트:** `Django Server` (모든 클라이언트가 공통으로 사용)  
* **설명:** 시스템의 가장 기본이 되는 기능들입니다.  
  * `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`: 사용자가 시스템에 접속하고(로그인), 접속 상태를 유지하며(토큰 갱신), 나갈 수(로그아웃) 있게 합니다.  
  * `GET /me`, `POST /me`: 사용자가 '내 정보'를 조회하거나 수정합니다.  
  * `GET /health`: 서버가 "저 잘 살아있어요\!"라고 응답해주는, 시스템 상태 점검용 API입니다.

---

### 2\. Desktop\_Backend (LangGraph 에이전트, Git 모듈)

* **해당 컴포넌트:** `Desktop_Backend` (LangGraph Agent, Git Analyzer, Git Commit Module)  
* **설명:** 데스크톱에서 실행되는 'AI 작업자(LangGraph Agent)'와 관련된 API입니다. 이 에이전트는 Git 코드 분석이나 커밋 생성 같은 복잡한 작업을 처리합니다.  
  * **에이전트 작업 (Jobs):**  
    * `POST /agent/jobs/request`: 데스크톱 에이전트가 "서버님, 저 지금 일할 수 있는데 혹시 시킬 일 있나요?"라고 물어보고 작업을 받아 갑니다(작업 풀링).  
    * `POST /agent/jobs/{job_id}/start`: 작업을 시작할 때 "이 일은 이제 제가 맡을게요\!"라고 서버에 알립니다(락 획득).  
    * `POST /agent/jobs/{job_id}/progress`, `.../complete`: 작업 중간 과정과 최종 완료 상태를 서버에 보고합니다.  
  * **Git 분석 및 커밋 (Analyzer, Commit Module):**  
    * `POST /git/projects/register`: "이 Git 프로젝트를 관리 시작하겠습니다"라고 서버에 등록합니다.  
    * `POST /git/{project_id}/scan`, `.../issues`, `.../readme`: `Git Analyzer`가 분석한 프로젝트의 구조, 코드 품질 문제(린트), README 파일 등을 서버 DB에 업로드합니다.  
    * `POST /git/{project_id}/commits`, `.../diff`: `Git Commit Module`이 생성한 커밋 정보나 코드 변경사항(Diff)을 서버에 전송합니다.

---

### 3\. FastAPI\_Server (LLM 에이전트)

* **해당 컴포넌트:** `FastAPI_Server` (LangChain Agent)  
* **설명:** 실제 LLM(대규모 언어 모델) API를 호출하는 'AI 두뇌' 서버입니다. 이 서버는 **Django 서버에 자신의 활동 내역을 보고**하는 역할을 합니다.  
  * `POST /llm/traces`: "방금 이 프롬프트로 LLM을 호출했고, 이런 답변을 받았어요" 같은 상세한 사용 기록(트레이스)을 전송합니다.  
  * `POST /llm/feedback`: 사용자가 "이 답변은 별로예요"라고 피드백한 내용을 서버로 보냅니다. (모델 성능 개선용)  
  * `POST /llm/cost`: "이번 LLM 호출에 얼마의 비용이 들었어요"라고 비용을 집계하여 보고합니다.

---

### 4\. Desktop\_Frontend (데스크톱 GUI)

* **해당 컴포넌트:** `Desktop GUI App`  
* **설명:** 사용자가 직접 눈으로 보고 클릭하는 데스크톱 프로그램입니다. 이 프로그램이 Django 서버와 통신할 때 사용합니다.  
  * `POST /device/login`: 데스크톱 앱 자체를 로그인(활성화)합니다.  
  * `GET /device/updates`: "새로운 버전의 앱이 나왔나요?"라고 업데이트를 확인합니다.  
  * `GET /tasks/assigned`: "서버에서 저에게 하라고 배정한 작업(미션/퀴즈)이 있나요?"를 조회합니다.  
  * `POST /activity/logs`: 사용자의 클릭 같은 앱 사용 기록을 (분석을 위해) 서버로 전송합니다.

---

### 5\. Mobile App

* **해당 컴포넌트:** `Mobile App`  
* **설명:** 모바일 앱 전용 API입니다.  
  * `POST /auth/mobile/login`: 모바일 앱에서 소셜 로그인 등을 처리합니다.  
  * `GET /mobile/feed`: 사용자에게 맞춤화된 '피드' (새로운 퀴즈, 배지 획득 소식 등)를 받아옵니다.  
  * `GET /notifications`, `POST /notifications/token`: 모바일 기기에 푸시 알림을 보내기 위한 기능들입니다.

---

### 6\. Quiz Engine & Gamification Engine

* **해당 컴포넌트:** `Django_Module` (Quiz Engine, Gamification Engine)  
* **설명:** Django 서버 내부에 포함된 모듈로, '학습'과 '재미' 요소를 담당합니다. 데스크톱 앱이나 모바일 앱에서 이 API들을 호출하여 퀴즈와 게임 기능을 사용합니다.  
  * **Quiz Engine:** 퀴즈 문제를 가져오고(`.../pools`), 퀴즈 세션을 시작하며(`.../sessions`), 답을 제출하고(`.../answers`), 결과를 채점합니다(`.../finish`).  
  * **Gamification Engine:** 사용자의 점수/레벨(`.../profile`)을 관리하고, 특정 활동(예: 첫 커밋)에 대한 보상(`.../events`)을 주며, 배지(`.../badges`)나 랭킹(`.../leaderboard`)을 보여줍니다.

---

### 7\. 기타 (파일, 알림)

* **파일/데이터/문서:** `POST /files`, `POST /datasets` 등은 시스템 전반에서 파일이나 데이터셋을 업로드하고 관리하기 위한 공용 API입니다.  
* **알림/웹훅/실시간:**  
  * `POST /webhooks/git`: 외부 Git 서버(예: GitHub)에서 "방금 코드가 푸시됐어요\!" 같은 이벤트를 수신합니다.

# API 데이터 예시

## 1\. 공통 (인증/유저/헬스)

* **`POST /auth/login`**: 로그인  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "username": "your_username",  
      
      "password": "your_password"  
      
    }

---

## 2-1. Projects & Jobs (Streamlit 코드 생성 플로우)

* **해당 컴포넌트:** `Django Server` + `Streamlit Frontend` + `Desktop_Backend Agent`  
* **설명:** Streamlit 코드 생성 화면은 Django를 통해 Job을 생성하고, Desktop_Backend 에이전트가 그 Job을 처리한 뒤, 결과를 다시 Django에 저장합니다. 프론트엔드는 Django에서 Job 상태를 폴링합니다.  

* **`GET /projects`**: 등록된 프로젝트 목록 조회  
  * Streamlit에서 코드 생성 대상 프로젝트를 선택할 때 사용합니다.  

* **`POST /projects/{project_id}/jobs`**: 프로젝트에 대한 작업(Job) 생성  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "job_type": "code_generation",  
      
      "payload": { "prompt": "로그인 폼을 만들어줘", "language": "python" }  
      
    }  
  * 생성된 Job은 `status: "pending"` 상태로 저장되고, Desktop_Backend 에이전트가 `/agent/jobs/request`를 통해 가져가 처리합니다.  

* **`GET /projects/{project_id}/jobs/{job_id}`**: Job 상세/진행 상태 조회  
  * Streamlit이 주기적으로 호출하여 `status`, `progress_log`, `summary`(최종 코드) 등을 확인합니다.  
  * Job이 완료되면 `summary` 필드에 생성된 코드가 담기며, 프론트엔드는 이 값을 화면에 표시하고 퀴즈 생성에 사용합니다.  

    
* **`POST /auth/refresh`**: 토큰 갱신  
  * 현재 Django 백엔드에서는 직접 사용하지 않는 보조 엔드포인트입니다.  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "refresh\_token": "your\_long\_refresh\_token"  
      
    }

    
* **`POST /auth/logout`**: 로그아웃/토큰 블랙리스트  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "refresh\_token": "your\_long\_refresh\_token\_to\_blacklist"  
      
    }

    
* **`GET /health`**: 헬스 체크  
  * 데이터 필요 없음  
* **`GET /me`**: 내 프로필 조회  
  * 데이터 필요 없음 (인증 토큰으로 사용자 식별)  
* **`POST /me`**: 내 프로필 수정  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "display\_name": "새로운 닉네임",  
      
      "email": "new\_email@example.com",  
      
      "old\_password": "current\_password", // 비밀번호 변경 시  
      
      "new\_password": "a\_new\_strong\_password" // 비밀번호 변경 시  
      
    }

    
* **`GET /config`**: 앱/에이전트 공통 설정 로드  
  * **Query Parameter** (예:) `?client_type=desktop` 또는 `?client_version=1.2.0`

---

## 2\. Desktop\_Backend (LangGraph 에이전트, Git 모듈)

* **`POST /agent/jobs/request`**: 에이전트가 할당 가능한 작업 요청  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "agent\_id": "agent-uuid-12345",  
      
      "capabilities": \["git\_scan", "commit\_generation", "readme\_update"\],  
      
      "status": "idle",  
      
      "max\_jobs": 1  
      
    }

    
* **`POST /agent/jobs/{job_id}/start`**: 작업 시작 알림  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "agent\_id": "agent-uuid-12345",  
      
      "start\_time": "2025-10-28T10:00:00Z"  
      
    }

    
* **`POST /agent/jobs/{job_id}/progress`**: 진행 로그/중간 산출물 업로드  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "log\_message": "Scanning file: src/main.py...",  
      
      "percent\_complete": 30,  
      
      "intermediate\_artifact": { "type": "complexity\_report", "data": { ... } }  
      
    }

    
* **`POST /agent/jobs/{job_id}/complete`**: 작업 완료 보고  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "status": "success", // or "failed"  
      
      "summary": "Git scan completed. Found 5 issues.",  
      
      "final\_result\_url": "s3://bucket/results/result.json",  
      
      "error\_message": null // 실패 시 에러 메시지  
      
    }

    
* **`POST /agent/callbacks/tool`**: 도구 호출/결과 콜백  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "run\_id": "run-abcde",  
      
      "tool\_name": "git\_analyzer\_tool",  
      
      "tool\_input": { "file\_path": "src/utils.py" },  
      
      "tool\_output": { "loc": 150, "complexity": 12 }  
      
    }

    
* **`POST /agent/telemetry`**: 토큰 사용량/지연시간/에러 메트릭 전송  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "agent\_id": "agent-uuid-12345",  
      
      "metrics": \[  
      
        { "name": "llm\_tokens\_used", "value": 1500, "model": "gpt-4o" },  
      
        { "name": "tool\_call\_latency\_ms", "value": 1200, "tool": "git\_analyzer" }  
      
      \]  
      
    }

    
* **`POST /agent/heartbeat`**: 에이전트 하트비트  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "agent\_id": "agent-uuid-12345",  
      
      "status": "processing",  
      
      "agent\_version": "v1.0.1",  
      
      "current\_job\_id": "job-xyz"  
      
    }

    
* **`POST /git/projects/register`**: 프로젝트 등록  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "name": "MyProject",  
      
      "local_path": "C:/Users/User/projects/MyProject",  
      
      "remote_url": "git@github.com:username/myproject.git"  
      
    }

    
* **`POST /git/{project_id}/scan`**: 파일/폴더 트리, 언어 지표 업로드  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "file\_tree": \[ {"path": "src/main.py", "size": 1024}, ... \],  
      
      "language\_stats": { "Python": 10240, "JavaScript": 5120 },  
      
      "total\_loc": 15360,  
      
      "avg\_complexity": 8.5  
      
    }

    
* **`POST /git/{project_id}/issues`**: 정적 분석 결과 업로드  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "analyzer": "eslint",  
      
      "issues": \[  
      
        { "file": "src/app.js", "line": 10, "rule\_id": "no-unused-vars", "severity": "warning" }  
      
      \]  
      
    }

    
* **`POST /git/{project_id}/readme`**: 생성/갱신된 README 초안 업로드  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "content": "\# MyProject\\n\\nThis is the auto-generated README...",  
      
      "version": "draft\_v1"  
      
    }

    
* **`POST /git/{project_id}/commits`**: 커밋 메타데이터/메시지 보고  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "commit\_hash": "a1b2c3d4e5f6...",  
      
      "author\_email": "author@example.com",  
      
      "message": "Feat: Add user login functionality",  
      
      "timestamp": "2025-10-28T10:30:00Z"  
      
    }

    
* **`POST /git/{project_id}/commits/{commit_id}/diff`**: 패치/디프 업로드  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "diff\_content": "--- a/src/main.py\\n+++ b/src/main.py\\n@@ \-1,1 \+1,2 @@\\n print('hello')\\n+print('world')"  
      
    }

    
* **`POST /git/{project_id}/artifacts`**: 빌드 산출물 업로드  
  * **Request Body (Multipart/Form-Data)** (예:)  
    * `file`: (빌드된 `.zip` 또는 `log.txt` 파일 바이너리)  
    * `type`: "build\_log"  
    * `commit_hash`: "a1b2c3d4e5f6"

---

## 3\. FastAPI\_Server (LLM 에이전트)

* **`POST /llm/traces`**: 프롬프트/응답 트레이스  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "run\_id": "llm-run-987",  
      
      "prompt": "Translate this to Korean: ...",  
      
      "response": "한국어로 번역: ...",  
      
      "masked\_prompt": "Translate this to Korean: \[MASKED\]",  
      
      "tool\_calls": \[ ... \],  
      
      "metadata": { "model": "gpt-4o-mini" }  
      
    }

    
* **`POST /llm/feedback`**: 휴먼 피드백  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "trace\_id": "llm-run-987",  
      
      "rating": "good", // or "bad", "neutral"  
      
      "comment": "번역이 매우 자연스러웠습니다.",  
      
      "tags": \["translation", "korean"\]  
      
    }

    
* **`POST /llm/cost`**: 모델별/요청별 비용 집계  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "model\_name": "gpt-4o-mini",  
      
      "input\_tokens": 1200,  
      
      "output\_tokens": 400,  
      
      "cost\_usd": 0.0024  
      
    }

    
* **`GET /policies/redteam`**: 금칙어/가드레일 정책 로드  
  * 데이터 필요 없음  
* **`POST /events/broadcast`**: 에이전트 → Django 이벤트  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "event\_type": "llm\_rate\_limit\_hit",  
      
      "payload": { "model": "gpt-4o", "user\_id": 123 },  
      
      "timestamp": "2025-10-28T11:00:00Z"  
      
    }

---

## 4\. Desktop\_Frontend (데스크톱 GUI)

* **`POST /device/login`**: 디바이스/앱 로그인 (디바이스 코드)  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "client\_id": "desktop-client-id",  
      
      "device\_code": "user-verification-code-from-browser"  
      
    }

    
* **`GET /device/updates`**: 앱 업데이트/공지사항  
  * **Query Parameter** (예:) `?current_version=1.0.0&platform=windows`  
* **`GET /tasks/assigned`**: 사용자에게 배정된 태스크  
  * **Query Parameter** (예:) `?status=pending` 또는 `?type=quiz&limit=5`  
* **`POST /uploads`**: 파일 업로드 (문서/데이터셋)  
  * **Request Body (Multipart/Form-Data)** (예:)  
    * `file`: (업로드할 `.csv` 또는 `.pdf` 파일 바이너리)  
    * `description`: "10월 판매 실적 데이터"  
    * `purpose`: "dataset\_analysis"  
* **`POST /activity/logs`**: UI 사용 로그/클릭스트림 전송  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "events": \[  
      
        { "timestamp": "...", "event\_type": "click", "element\_id": "btn\_start\_scan" },  
      
        { "timestamp": "...", "event\_type": "page\_view", "page\_name": "/dashboard" }  
      
      \]  
      
    }

---

## 5\. Mobile App

* **`POST /auth/mobile/login`**: 모바일 로그인 (소셜)  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "provider": "google", // or "kakao", "apple"  
      
      "access\_token": "social\_provider\_access\_token"  
      
    }

    
* **`GET /mobile/feed`**: 개인화 피드  
  * **Query Parameter** (예:) `?page=1&limit=10` 또는 `?since_id=last_feed_item_id`  
* **`POST /mobile/feedback`**: 앱 내 피드백/버그 리포트  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "rating": 4, // 1\~5  
      
      "comment": "퀴즈 푸는 화면이 가끔 멈춰요.",  
      
      "screen\_name": "/quiz/session/123",  
      
      "device\_info": { "os": "android", "version": "13" }  
      
    }

    
* **`GET /notifications`**: 푸시 알림 페치  
  * **Query Parameter** (예:) `?page=1&limit=20&read=false`  
* **`POST /notifications/token`**: FCM/APNS 토큰 등록  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "device\_token": "fcm\_or\_apns\_device\_token\_string",  
      
      "platform": "fcm" // or "apns"  
      
    }

---

## 6\. Quiz Engine (Module)

* **`GET /quiz/pools`**: 퀴즈 풀 목록  
  * **Query Parameter** (예:) `?tag=python` 또는 `?difficulty=hard&category=git`  
* **`POST /quiz/sessions`**: 퀴즈 세션 시작  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "pool\_id": 5, // 'Python 기초' 퀴즈 풀 ID  
      
      "num\_questions": 10,  
      
      "mode": "timed" // or "practice"  
      
    }

    
* **`GET /quiz/sessions/{session_id}`**: 세션 상태/진행  
  * 데이터 필요 없음 (Path Parameter로 세션 식별)  
* **`POST /quiz/sessions/{session_id}/answers`**: 사용자의 답안 제출  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "question\_id": 101,  
      
      "selected\_option\_id": 3 // 사용자가 선택한 보기 ID  
      
    }

    
* **`POST /quiz/sessions/{session_id}/finish`**: 세션 종료/채점  
  * 데이터 필요 없음  
* **`GET /quiz/history`**: 퀴즈 이력/정오답 통계  
  * **Query Parameter** (예:) `?page=1&limit=10&pool_id=5`  
* **`GET /quiz/recommendations`**: 성취도 기반 추천 문제  
  * **Query Parameter** (예:) `?weak_topic=git_branch&limit=5`

---

## 7\. Gamification Engine (Module)

* **`GET /gami/profile`**: 유저 포인트/레벨/XP  
  * 데이터 필요 없음 (인증 토큰으로 사용자 식별)  
* **`POST /gami/events`**: 이벤트 수집 (퀴즈 완료, 커밋 완료 등)  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "event\_name": "first\_commit\_made",  
      
      "user\_id": 123, // (서버 내부 호출 시)  
      
      "context": { "project\_id": 10, "commit\_hash": "a1b2c3d4" }  
      
    }

    
* **`GET /gami/badges`**: 보유/획득가능 배지 목록  
  * **Query Parameter** (예:) `?status=earned` 또는 `?status=available`  
* **`POST /gami/redeem`**: 리워드 교환  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "reward\_id": "RWD-001", // "커피 쿠폰" ID  
      
      "quantity": 1  
      
    }

    
* **`GET /gami/leaderboard`**: 리더보드  
  * **Query Parameter** (예:) `?period=weekly` 또는 `?group=my_study_group`

---

## 8\. 파일/데이터/문서

* **`POST /files`**: 일반 파일 업로드  
  * **Request Body (Multipart/Form-Data)** (예:)  
    * `file`: (업로드할 파일 바이너리)  
    * `context_id`: "job-xyz" // 이 파일이 연관된 작업 ID  
    * `file_name`: "debug\_log.txt"  
* **`GET /files/{file_id}`**: 다운로드/메타 조회  
  * 데이터 필요 없음  
* **`POST /datasets`**: 데이터셋 등록  
  * **Request Body (JSON)** (예:)  
      
    {  
      
      "dataset\_name": "고객 이탈 데이터",  
      
      "source\_url": "s3://bucket/datasets/churn.csv",  
      
      "schema": \[ {"name": "age", "type": "int"}, {"name": "gender", "type": "string"} \],  
      
      "row\_count": 10000  
      
    }

    
* **`GET /datasets/{dataset_id}`**: 데이터셋 메타/버전  
  * **Query Parameter** (예:) `?version=2`

---

## 9\. 알림/웹훅/실시간

* **`POST /webhooks/agent`**: 외부 에이전트 일반 웹훅  
  * **Request Body (JSON)** (예:) (전송하는 시스템에 따라 다름)  
      
    {  
      
      "event\_type": "external\_scan\_complete",  
      
      "payload": { "scan\_id": "scan-999", "result": "..." }  
      
    }

    
* **`POST /webhooks/git`**: Git 서버/CI 파이프라인 웹훅 수신  
  * **Request Body (JSON)** (예:) (GitHub Push 이벤트 페이로드)  
      
    {  
      
      "ref": "refs/heads/main",  
      
      "repository": { "name": "MyProject", "full\_name": "user/MyProject" },  
      
      "commits": \[ ... \]  
      
    }

