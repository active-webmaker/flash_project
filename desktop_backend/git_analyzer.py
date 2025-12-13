
import os
from git import Repo, GitCommandError
from langchain.tools import tool
import logging

# agent.py 또는 main.py에서 설정한 로거를 가져옵니다.
logger = logging.getLogger(__name__)


class GitAnalyzer:
    """
    Git 저장소 분석을 위한 도구 모음.
    - 파일 트리 스캔
    - 언어별 코드 라인 수(LOC) 계산
    """

    def __init__(self, repo_path: str):
        logger.debug(f"GitAnalyzer 초기화 시도: {repo_path}")
        if not os.path.isdir(repo_path):
            logger.error(f"제공된 경로가 디렉터리가 아님: {repo_path}")
            raise ValueError(f"'{repo_path}'는 유효한 디렉터리가 아닙니다.")
        
        try:
            self.repo = Repo(repo_path)
            self.repo_path = repo_path
            logger.info(f"GitAnalyzer가 성공적으로 초기화되었습니다: {repo_path}")
        except Exception as e:
            logger.error(f"저장소 초기화 실패: {repo_path} - {e}", exc_info=True)
            raise

    def scan_file_tree(self) -> dict:
        """로컬 저장소의 파일/디렉터리 트리를 JSON-호환 dict로 반환합니다."""
        logger.info(f"파일 트리 스캔 시작: {self.repo_path}")
        ignore_dirs = {'.git', '__pycache__', '.mypy_cache', '.pytest_cache', '.venv', 'node_modules'}
        ignore_files = {'.DS_Store', 'Thumbs.db'}

        def is_git_private(path_fragment: str) -> bool:
            if not path_fragment:
                return False
            normalized = path_fragment.replace('\\', '/').lstrip('./')
            return normalized == '.git' or normalized.startswith('.git/')

        try:
            repo_root = os.path.abspath(self.repo_path)
            root_name = os.path.basename(repo_root.rstrip(os.sep)) or "repository"
            tree = {
                "name": root_name,
                "path": ".",
                "type": "directory",
                "children": [],
            }
            nodes = {repo_root: tree}
            
            logger.debug(f"os.walk 시작: {repo_root}")
            for current_dir, dirs, files in os.walk(repo_root):
                logger.critical(f"--- AGENT DEBUG: Processing directory -> {current_dir} ---")
                abs_current = os.path.abspath(current_dir)
                rel_dir = os.path.relpath(current_dir, repo_root)
                rel_dir = "." if rel_dir == "." else rel_dir.replace('\\', '/')
                logger.debug(f"디렉터리 순회 중: {rel_dir}")

                if is_git_private(rel_dir):
                    logger.debug(f"Git 비공개 디렉터리 건너뛰기: {rel_dir}")
                    continue

                current_node = nodes.get(abs_current)
                if current_node is None:
                    logger.warning(f"상위 노드를 찾을 수 없어 건너뜁니다: {abs_current}")
                    continue

                # 필터링된 하위 디렉터리 제거
                original_dirs = list(dirs)
                dirs[:] = [
                    d for d in dirs
                    if d not in ignore_dirs and not is_git_private(os.path.join(rel_dir, d).replace('\\', '/'))
                ]
                filtered_dirs = [d for d in original_dirs if d not in dirs]
                if filtered_dirs:
                    logger.debug(f"무시된 하위 디렉터리: {filtered_dirs} in {rel_dir}")


                for directory_name in dirs:
                    abs_child = os.path.join(current_dir, directory_name)
                    rel_child = os.path.relpath(abs_child, repo_root).replace('\\', '/')
                    child_node = {
                        "name": directory_name,
                        "path": rel_child,
                        "type": "directory",
                        "children": [],
                    }
                    current_node["children"].append(child_node)
                    nodes[os.path.abspath(abs_child)] = child_node

                for file_name in files:
                    if file_name in ignore_files:
                        continue
                    abs_file = os.path.join(current_dir, file_name)
                    rel_file = os.path.relpath(abs_file, repo_root).replace('\\', '/')
                    if is_git_private(rel_file):
                        continue
                    try:
                        size = os.path.getsize(abs_file)
                    except OSError as e:
                        logger.warning(f"파일 크기를 가져올 수 없습니다: {abs_file} - {e}")
                        continue
                    current_node["children"].append({
                        "name": file_name,
                        "path": rel_file,
                        "type": "file",
                        "size": size,
                    })

            def sort_children(node: dict):
                children = node.get("children", [])
                children.sort(key=lambda child: (child.get("type") != "directory", child.get("name", "").lower()))
                for child in children:
                    if child.get("type") == "directory":
                        sort_children(child)

            sort_children(tree)
            logger.info("파일 트리 스캔 성공.")
            return tree
        except Exception as e:
            logger.error(f"파일 트리 스캔 중 예외 발생: {e}", exc_info=True)
            return {"error": str(e)}

    def calculate_loc_per_language(self) -> dict:
        """저장소 내 각 프로그래밍 언어별 코드 라인 수(LOC)를 계산합니다."""
        logger.info(f"언어별 LOC 계산 시작: {self.repo_path}")
        language_stats = {}

        # 언어별 확장자 매핑
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.c': 'C',
            '.h': 'C',
            '.cpp': 'C++',
            '.hpp': 'C++',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.md': 'Markdown',
            '.html': 'HTML',
            '.css': 'CSS',
        }

        try:
            tracked_files = self.repo.git.ls_files().split('\n')
            logger.debug(f"{len(tracked_files)}개의 추적된 파일을 찾았습니다.")
            for file_path in tracked_files:
                if not file_path:
                    continue
                _, extension = os.path.splitext(file_path)
                language = language_map.get(extension)

                if language:
                    full_path = os.path.join(self.repo_path, file_path)
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            line_count = len([line for line in lines if line.strip() != ''])

                        language_stats[language] = language_stats.get(language, 0) + line_count
                    except FileNotFoundError:
                        logger.warning(f"LOC 계산 중 파일을 찾을 수 없음: {full_path}")
                        continue
                    except Exception as e:
                        logger.error(f"파일 읽기 오류 {full_path}: {e}")

            logger.info(f"LOC 계산 완료: {language_stats}")
            return language_stats
        except GitCommandError as e:
            logger.error(f"Git ls-files 명령어 실행 실패: {e}", exc_info=True)
            return {"error": f"Git command failed: {e}"}
        except Exception as e:
            logger.error(f"LOC 계산 중 에러 발생: {e}", exc_info=True)
            return {"error": str(e)}


if __name__ == '__main__':
    # 테스트용: 로깅을 명시적으로 설정
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 실제 프로젝트 경로로 변경하여 사용하세요.
    repo_path = "C:/Users/DS29/Documents/python_proj/final_proj"
    if not os.path.exists(repo_path) or not os.path.isdir(os.path.join(repo_path, '.git')):
        print(f"'{repo_path}'는 유효한 Git 저장소가 아닙니다. 테스트를 위해 임시 저장소를 생성합니다.")
        repo_path = "./temp_repo_for_testing"
        if not os.path.exists(repo_path):
            os.mkdir(repo_path)
        Repo.init(repo_path)
        with open(os.path.join(repo_path, "test.py"), "w") as f:
            f.write("print('hello world')\n")
            f.write("# a comment\n")
        Repo(repo_path).index.add(["test.py"])
        Repo(repo_path).index.commit("initial commit")

    analyzer = GitAnalyzer(repo_path=repo_path)

    print("--- 파일 트리 스캔 ---")
    file_tree = analyzer.scan_file_tree()
    import json
    print(json.dumps(file_tree, indent=2))

    print("\n--- 언어별 LOC 계산 ---")
    loc_stats = analyzer.calculate_loc_per_language()
    print(loc_stats)

