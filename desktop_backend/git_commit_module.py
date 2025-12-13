
import os
from git import Repo, GitCommandError
from langchain.tools import tool
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GitCommitModule:
    """
    Git 커밋, 브랜치, Diff 생성 등 저장소 변경을 위한 도구 모음.
    """

    def __init__(self, repo_path: str):
        """
        저장소 경로를 받아 Repo 객체를 초기화합니다.
        :param repo_path: 로컬 Git 저장소 경로
        """
        try:
            self.repo = Repo(repo_path)
            self.repo_path = repo_path
        except Exception as e:
            logging.error(f"저장소 초기화 실패: {repo_path} - {e}")
            raise

    def create_commit(self, message: str, files_to_add: list[str]) -> dict:
        """
        지정된 파일들을 스테이징하고 새 커밋을 생성합니다.
        :param message: 커밋 메시지
        :param files_to_add: 커밋에 추가할 파일 경로 리스트 (저장소 루트 기준)
        :return: 성공 시 커밋 해시 정보, 실패 시 에러 메시지
        """
        logging.info(f"Attempting to create commit in {self.repo_path} with message: '{message}'")
        try:
            # 파일 존재 여부 확인 및 추가
            valid_files = []
            for file_path in files_to_add:
                full_path = os.path.join(self.repo_path, file_path)
                if os.path.exists(full_path):
                    valid_files.append(file_path)
                else:
                    logging.warning(f"File not found, cannot add to commit: {full_path}")
            
            if not valid_files:
                return {"success": False, "error": "No valid files to commit."}

            self.repo.index.add(valid_files)
            
            # 변경 사항이 있는지 확인
            if not self.repo.index.diff("HEAD"):
                logging.warning("No changes to commit.")
                return {"success": False, "error": "No changes to commit."}

            commit = self.repo.index.commit(message)
            logging.info(f"Commit created successfully: {commit.hexsha}")
            return {"success": True, "commit_hash": commit.hexsha}
        except GitCommandError as e:
            logging.error(f"Git 명령어 실행 실패: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logging.error(f"커밋 생성 중 에러 발생: {e}")
            return {"success": False, "error": str(e)}

    def get_diff(self, commit_hash: str = "HEAD") -> str:
        """
        특정 커밋 또는 HEAD의 변경 사항(diff)을 반환합니다.
        :param commit_hash: Diff를 생성할 커밋 해시 (기본값: "HEAD")
        :return: Diff 내용 문자열
        """
        logging.info(f"Getting diff for commit: {commit_hash}")
        try:
            # HEAD의 경우, 마지막 커밋과 워킹 디렉토리의 변경사항을 보여줍니다.
            # 특정 커밋의 경우, 해당 커밋과 그 부모 커밋 간의 변경사항을 보여줍니다.
            if commit_hash.upper() == "HEAD":
                # 저장소에 커밋이 있는지 확인
                if not self.repo.head.is_valid():
                    logging.info("No commits in repository yet")
                    return "아직 저장소에 커밋이 없습니다. 파일을 수정하고 커밋을 생성해주세요."

                # 마지막 커밋 이후의 변경사항 (스테이징된 것 포함)
                diff_content = self.repo.git.diff("HEAD")
            else:
                commit = self.repo.commit(commit_hash)
                # 해당 커밋의 변경 내용
                diff_content = self.repo.git.show(commit.hexsha)

            if not diff_content:
                return "No differences found."

            return diff_content
        except GitCommandError as e:
            logging.error(f"Git diff 명령어 실행 실패: {e}")
            return f"Error getting diff: {e}"
        except Exception as e:
            logging.error(f"Diff 생성 중 에러 발생: {e}")
            return f"Error getting diff: {e}"

if __name__ == '__main__':
    # 테스트용: 실제 프로젝트 경로로 변경하여 사용하세요.
    repo_path = "C:/Users/DS29/Documents/python_proj/final_proj"
    if not os.path.exists(repo_path) or not os.path.isdir(os.path.join(repo_path, '.git')):
        print(f"'{repo_path}'는 유효한 Git 저장소가 아닙니다. 테스트를 위해 임시 저장소를 생성합니다.")
        repo_path = "./temp_repo_for_testing"
        if not os.path.exists(repo_path):
            Repo.init(repo_path)
        repo = Repo(repo_path)
        if not repo.head.is_valid(): # 커밋이 하나도 없을 경우
             with open(os.path.join(repo_path, "test.py"), "w") as f:
                 f.write("print('hello world')\n")
             repo.index.add(["test.py"])
             repo.index.commit("initial commit")

    commit_module = GitCommitModule(repo_path=repo_path)

    # 테스트 1: 파일 수정 및 커밋 생성
    test_file = "test_commit_module.txt"
    with open(os.path.join(repo_path, test_file), "w") as f:
        f.write("This is a test file for GitCommitModule.\n")

    print(f"--- '{test_file}' 파일 생성 및 커밋 테스트 ---")
    commit_result = commit_module.create_commit(
        message="Test: Add test_commit_module.txt",
        files_to_add=[test_file]
    )
    print(commit_result)

    # 테스트 2: Diff 생성
    if commit_result.get("success"):
        print("\n--- 마지막 커밋의 Diff 내용 ---")
        diff = commit_module.get_diff(commit_hash=commit_result.get("commit_hash"))
        print(diff)

    # 테스트 3: 변경사항이 없을 때 Diff
    print("\n--- 변경사항이 없을 때의 Diff ---")
    # 마지막 커밋 이후 변경사항이 없으므로 diff는 비어있어야 함
    no_change_diff = commit_module.get_diff("HEAD")
    print(no_change_diff)

    # 테스트 4: 워킹 디렉토리 변경 후 Diff
    with open(os.path.join(repo_path, test_file), "a") as f:
        f.write("Appending a new line.\n")
    print(f"\n--- '{test_file}' 파일 수정 후 워킹 디렉토리 Diff ---")
    working_dir_diff = commit_module.get_diff("HEAD")
    print(working_dir_diff)

    # 테스트 파일 정리
    # os.remove(os.path.join(repo_path, test_file))
    # print(f"\n'{test_file}' 파일 삭제됨.")
