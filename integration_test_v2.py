#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
프로젝트 통합 테스트 스크립트 v2
Desktop Backend, Local LLM Server, Django API, Streamlit Frontend 통합 테스트
"""

import os
import sys
import json
import time
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

# Windows 인코딩 처리
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

class IntegrationTestRunner:
    def __init__(self):
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": []
            }
        }
        self.project_root = Path(__file__).parent

    def log_test(self, name: str, status: str, message: str = "", details: Dict = None):
        """테스트 결과 기록"""
        test_result = {
            "name": name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        if details:
            test_result["details"] = details

        self.test_results["tests"].append(test_result)
        self.test_results["summary"]["total"] += 1

        if status == "PASSED":
            self.test_results["summary"]["passed"] += 1
            print(f"✅ {name}: PASSED")
        elif status == "FAILED":
            self.test_results["summary"]["failed"] += 1
            print(f"❌ {name}: FAILED - {message}")
            self.test_results["summary"]["errors"].append(f"{name}: {message}")
        elif status == "SKIPPED":
            self.test_results["summary"]["skipped"] += 1
            print(f"⏭️  {name}: SKIPPED - {message}")

    def test_dependencies(self) -> bool:
        """필수 패키지 설치 확인"""
        print("\n" + "="*60)
        print("테스트 1: 필수 의존성 확인")
        print("="*60)

        required_packages = {
            "streamlit": "Streamlit 프로트엔드",
            "requests": "HTTP 요청",
            "langchain": "Desktop Backend",
            "langgraph": "Agent Graph",
            "langchain_openai": "LangChain OpenAI",
            "django": "Django API",
            "dotenv": "환경 변수"
        }

        missing = []
        for package, description in required_packages.items():
            try:
                __import__(package.replace("-", "_"))
                self.log_test(f"패키지: {package}", "PASSED", description)
            except ImportError:
                missing.append(package)
                self.log_test(f"패키지: {package}", "FAILED", f"{description} - 설치되지 않음")

        return len(missing) == 0

    def test_env_configuration(self) -> bool:
        """환경 설정 파일 확인"""
        print("\n" + "="*60)
        print("테스트 2: 환경 설정 확인")
        print("="*60)

        env_file = self.project_root / ".env"
        if not env_file.exists():
            self.log_test("환경 설정 파일 (.env)", "FAILED", ".env 파일이 없습니다")
            return False

        self.log_test("환경 설정 파일 (.env)", "PASSED", ".env 파일이 존재합니다")

        # 주요 환경 변수 확인
        from dotenv import load_dotenv
        load_dotenv()

        important_vars = {
            "MODEL_PATH": "로컬 LLM 모델 경로",
            "MODEL_DOMAIN": "LLM 서버 도메인",
            "MODEL_PORT": "LLM 서버 포트",
        }

        all_set = True
        for var, description in important_vars.items():
            value = os.getenv(var)
            if value:
                self.log_test(f"환경변수: {var}", "PASSED", description)
            else:
                self.log_test(f"환경변수: {var}", "FAILED", f"{description} - 설정되지 않음")
                all_set = False

        return all_set

    def test_file_structure(self) -> bool:
        """프로젝트 파일 구조 확인"""
        print("\n" + "="*60)
        print("테스트 3: 프로젝트 파일 구조 확인")
        print("="*60)

        required_paths = {
            "streamlit_frontend/app.py": "Streamlit 메인 앱",
            "streamlit_frontend/utils/api.py": "Streamlit API 클라이언트",
            "streamlit_frontend/pages/4_Code_Generation.py": "코드 생성 페이지",
            "desktop_backend/agent.py": "Desktop Backend Agent",
            "desktop_backend/git_analyzer.py": "Git 분석 모듈",
            "desktop_backend/git_commit_module.py": "Git 커밋 모듈",
            "local_llm_server.py": "로컬 LLM 서버",
            "Django_Server/manage.py": "Django 프로젝트",
        }

        all_exist = True
        for path, description in required_paths.items():
            full_path = self.project_root / path
            if full_path.exists():
                self.log_test(f"파일: {path}", "PASSED", description)
            else:
                self.log_test(f"파일: {path}", "FAILED", f"{description} - 파일 없음")
                all_exist = False

        return all_exist

    def test_api_connectivity(self, url: str, endpoint: str, timeout: int = 5) -> Tuple[bool, Optional[str]]:
        """API 서버 연결 테스트"""
        try:
            response = requests.get(f"{url}{endpoint}", timeout=timeout)
            return response.ok, response.status_code
        except requests.exceptions.ConnectionError:
            return False, "Connection refused"
        except requests.exceptions.Timeout:
            return False, "Timeout"
        except Exception as e:
            return False, str(e)

    def test_django_api(self) -> bool:
        """Django API 연결 테스트"""
        print("\n" + "="*60)
        print("테스트 4: Django API 서버 연결")
        print("="*60)

        django_url = os.getenv("STREAMLIT_API_BASE_URL", "http://localhost:8000")

        print(f"Django API URL: {django_url}")

        ok, status = self.test_api_connectivity(django_url, "/api/v1/health")
        if ok:
            self.log_test("Django API Health Check", "PASSED", f"상태: {status}")
            return True
        else:
            self.log_test("Django API Health Check", "FAILED", f"API 서버 미응답: {status}")
            return False

    def test_local_llm_server(self) -> bool:
        """로컬 LLM 서버 연결 테스트"""
        print("\n" + "="*60)
        print("테스트 5: 로컬 LLM 서버 연결")
        print("="*60)

        llm_url = os.getenv("LOCAL_LLM_URL", "http://127.0.0.1:8001/v1")

        print(f"LLM Server URL: {llm_url}")

        ok, status = self.test_api_connectivity(llm_url, "/models", timeout=3)
        if ok:
            self.log_test("로컬 LLM 서버 연결", "PASSED", f"상태: {status}")
            return True
        else:
            self.log_test("로컬 LLM 서버 연결", "SKIPPED",
                         f"LLM 서버 미실행 - 이는 정상일 수 있습니다. {status}")
            return None  # 선택적 서비스

    def test_desktop_backend_imports(self) -> bool:
        """Desktop Backend 모듈 임포트 테스트"""
        print("\n" + "="*60)
        print("테스트 6: Desktop Backend 모듈 임포트")
        print("="*60)

        backend_path = self.project_root / "desktop_backend"
        sys.path.insert(0, str(backend_path))

        modules = {
            "git_analyzer": "Git 분석기",
            "git_commit_module": "Git 커밋 모듈",
            "agent": "Agent 메인 모듈"
        }

        all_imported = True
        for module, description in modules.items():
            try:
                __import__(module)
                self.log_test(f"모듈: {module}", "PASSED", description)
            except ImportError as e:
                self.log_test(f"모듈: {module}", "FAILED", f"{description} - {str(e)}")
                all_imported = False

        return all_imported

    def test_streamlit_frontend_imports(self) -> bool:
        """Streamlit 프론트엔드 모듈 임포트 테스트"""
        print("\n" + "="*60)
        print("테스트 7: Streamlit 프론트엔드 모듈 임포트")
        print("="*60)

        frontend_path = self.project_root / "streamlit_frontend"
        sys.path.insert(0, str(frontend_path))

        try:
            from utils.api import APIClient
            self.log_test("APIClient 임포트", "PASSED", "API 클라이언트 모듈")
            return True
        except ImportError as e:
            self.log_test("APIClient 임포트", "FAILED", f"API 클라이언트 모듈 - {str(e)}")
            return False

    def test_api_client_methods(self) -> bool:
        """API 클라이언트 메서드 테스트"""
        print("\n" + "="*60)
        print("테스트 8: API 클라이언트 메서드 확인")
        print("="*60)

        frontend_path = self.project_root / "streamlit_frontend"
        sys.path.insert(0, str(frontend_path))

        try:
            from utils.api import APIClient
            client = APIClient("http://localhost:8000")

            required_methods = [
                "login",
                "health",
                "me",
                "gami_profile",
                "gami_event",
                "quiz_pools",
                "projects",
                "register_project",
                "create_job",
                "get_job",
                "generate_quiz_from_code"
            ]

            all_exist = True
            for method in required_methods:
                if hasattr(client, method):
                    self.log_test(f"API 메서드: {method}", "PASSED", "메서드 존재")
                else:
                    self.log_test(f"API 메서드: {method}", "FAILED", "메서드 없음")
                    all_exist = False

            return all_exist
        except Exception as e:
            self.log_test("API 클라이언트 검증", "FAILED", str(e))
            return False

    def test_local_llm_server_file(self) -> bool:
        """로컬 LLM 서버 파일 구조 테스트"""
        print("\n" + "="*60)
        print("테스트 9: 로컬 LLM 서버 구성 확인")
        print("="*60)

        llm_server_file = self.project_root / "local_llm_server.py"

        if not llm_server_file.exists():
            self.log_test("LLM 서버 파일", "FAILED", "local_llm_server.py 파일 없음")
            return False

        self.log_test("LLM 서버 파일", "PASSED", "local_llm_server.py 파일 존재")

        # 파일 내용 확인
        try:
            with open(llm_server_file, 'r') as f:
                content = f.read()

            required_imports = [
                "from llama_cpp.server.app import create_app",
                "from llama_cpp.server.settings import Settings",
                "import uvicorn"
            ]

            all_imports_present = True
            for imp in required_imports:
                if imp in content:
                    self.log_test(f"LLM 임포트: {imp.split()[-1]}", "PASSED", "임포트 존재")
                else:
                    self.log_test(f"LLM 임포트: {imp.split()[-1]}", "FAILED", "임포트 없음")
                    all_imports_present = False

            return all_imports_present
        except Exception as e:
            self.log_test("LLM 서버 파일 검증", "FAILED", str(e))
            return False

    def test_desktop_backend_tools(self) -> bool:
        """Desktop Backend 도구 확인"""
        print("\n" + "="*60)
        print("테스트 10: Desktop Backend 도구 확인")
        print("="*60)

        backend_path = self.project_root / "desktop_backend"
        sys.path.insert(0, str(backend_path))

        try:
            # agent.py에서 도구 정의 확인
            agent_file = backend_path / "agent.py"
            with open(agent_file, 'r') as f:
                content = f.read()

            # 도구 확인
            tools = [
                "git_analyzer.scan_file_tree",
                "git_analyzer.calculate_loc_per_language",
                "git_commit_module.create_commit",
                "git_commit_module.get_diff"
            ]

            all_tools_present = True
            for tool in tools:
                if tool in content:
                    self.log_test(f"도구: {tool}", "PASSED", "도구 정의 존재")
                else:
                    self.log_test(f"도구: {tool}", "FAILED", "도구 정의 없음")
                    all_tools_present = False

            return all_tools_present
        except Exception as e:
            self.log_test("Desktop Backend 도구 검증", "FAILED", str(e))
            return False

    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*80)
        print("Flash AI 프로젝트 통합 테스트 v2 시작")
        print("="*80)

        tests = [
            ("의존성 확인", self.test_dependencies),
            ("환경 설정", self.test_env_configuration),
            ("파일 구조", self.test_file_structure),
            ("Django API", self.test_django_api),
            ("LLM 서버", self.test_local_llm_server),
            ("Backend 모듈", self.test_desktop_backend_imports),
            ("Frontend 모듈", self.test_streamlit_frontend_imports),
            ("API 클라이언트", self.test_api_client_methods),
            ("LLM 서버 파일", self.test_local_llm_server_file),
            ("Backend 도구", self.test_desktop_backend_tools),
        ]

        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"\n⚠️  테스트 '{test_name}' 실행 중 예외 발생: {str(e)}")
                self.test_results["summary"]["errors"].append(f"{test_name}: {str(e)}")

        self.print_summary()
        return self.save_results()

    def print_summary(self):
        """테스트 결과 요약 출력"""
        summary = self.test_results["summary"]

        print("\n" + "="*80)
        print("테스트 결과 요약")
        print("="*80)
        print(f"총 테스트: {summary['total']}")
        print(f"✅ 성공: {summary['passed']}")
        print(f"❌ 실패: {summary['failed']}")
        print(f"⏭️  건너뜀: {summary['skipped']}")

        if summary['errors']:
            print("\n오류 목록:")
            for error in summary['errors']:
                print(f"  - {error}")

        success_rate = (summary['passed'] / summary['total'] * 100) if summary['total'] > 0 else 0
        print(f"\n성공률: {success_rate:.1f}%")
        print("="*80 + "\n")

    def save_results(self) -> Dict:
        """테스트 결과를 JSON 파일로 저장"""
        output_file = self.project_root / "integration_test_v2_results.json"

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)

            print(f"✅ 테스트 결과가 저장되었습니다: {output_file}")
            return self.test_results
        except Exception as e:
            print(f"❌ 테스트 결과 저장 실패: {str(e)}")
            return self.test_results


def main():
    """메인 함수"""
    runner = IntegrationTestRunner()
    results = runner.run_all_tests()

    # 종료 코드 반환
    return 0 if results["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
