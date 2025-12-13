import os
import json
from git import Repo
from git_analyzer import GitAnalyzer

repo_path = os.path.abspath("./temp_test_repo")
if not os.path.exists(repo_path):
    os.makedirs(repo_path, exist_ok=True)
    Repo.init(repo_path)
    with open(os.path.join(repo_path, "a.py"), "w", encoding="utf-8") as f:
        f.write("print('hello')\n")
    with open(os.path.join(repo_path, "b.js"), "w", encoding="utf-8") as f:
        f.write("console.log('hi');\n")
    r = Repo(repo_path)
    r.index.add(["a.py", "b.js"])
    r.index.commit("initial commit")

analyzer = GitAnalyzer(repo_path=repo_path)

tool_obj = analyzer.scan_file_tree
print('TOOL TYPE:', type(tool_obj))
print('TOOL DIR sample:', [a for a in dir(tool_obj) if not a.startswith('_')][:50])

# langchain's @tool decorator returns a tool object. The original function may be
# accessible as `.func` or similar attribute depending on the langchain version.
tree = None
if hasattr(tool_obj, 'func'):
    tree = tool_obj.func(analyzer)
elif callable(tool_obj):
    # Some versions allow calling directly
    try:
        tree = tool_obj()
    except TypeError:
        try:
            tree = tool_obj(analyzer)
        except Exception as e:
            print('Could not call tool directly:', e)
else:
    print('Unknown tool object shape; falling back to direct attribute call.')

loc_tool = analyzer.calculate_loc_per_language
if hasattr(loc_tool, 'func'):
    loc = loc_tool.func(analyzer)
else:
    try:
        loc = loc_tool()
    except Exception:
        try:
            loc = loc_tool(analyzer)
        except Exception as e:
            loc = {}
            print('LOC tool call failed:', e)

print("=== TREE ===")
print(json.dumps(tree, ensure_ascii=False, indent=2)[:2000])
print("\n=== LOC ===")
print(json.dumps(loc, ensure_ascii=False, indent=2))
