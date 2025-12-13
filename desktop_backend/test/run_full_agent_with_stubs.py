import os
import sys
import types
import threading
import time
from pathlib import Path

# --- Ensure project root on path ---
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
DESKTOP_BACKEND_DIR = PROJECT_ROOT / 'desktop_backend'
if str(DESKTOP_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(DESKTOP_BACKEND_DIR))

# --- Stub langchain.tools.tool decorator ---
if 'langchain' not in sys.modules:
    sys.modules['langchain'] = types.ModuleType('langchain')
if 'langchain.tools' not in sys.modules:
    tools_mod = types.ModuleType('langchain.tools')
    def tool(name=None):
        def decorator(fn):
            # attach a .name attribute if provided to mimic @tool behavior
            setattr(fn, 'name', name or getattr(fn, '__name__', 'tool'))
            return fn
        return decorator
    tools_mod.tool = tool
    sys.modules['langchain.tools'] = tools_mod

# --- Stub langchain_core.messages ---
msgs_mod = types.ModuleType('langchain_core.messages')
class BaseMessage:
    def __init__(self, content=None):
        self.content = content
        self.additional_kwargs = {}
class HumanMessage(BaseMessage):
    pass
class FunctionMessage(BaseMessage):
    def __init__(self, content=None, name=None):
        super().__init__(content)
        self.name = name
        self.role = 'function'
msgs_mod.BaseMessage = BaseMessage
msgs_mod.HumanMessage = HumanMessage
msgs_mod.FunctionMessage = FunctionMessage
sys.modules['langchain_core.messages'] = msgs_mod

# --- Stub langchain_openai.ChatOpenAI ---
openai_mod = types.ModuleType('langchain_openai')
class ChatOpenAI:
    def __init__(self, openai_api_base=None, openai_api_key=None, temperature=0, streaming=False):
        self.base = openai_api_base
        self.key = openai_api_key
        self.temperature = temperature
        self.streaming = streaming
    def invoke(self, messages):
        # If a function message exists, end the loop
        if any(getattr(m, 'role', None) == 'function' for m in messages):
            m = BaseMessage("Repository analyzed. Finishing.")
            return m
        # Otherwise, request to call scan_file_tree tool
        m = BaseMessage()
        m.additional_kwargs = {
            'function_call': {
                'name': 'scan_file_tree',
                'arguments': '{}'
            }
        }
        return m
openai_mod.ChatOpenAI = ChatOpenAI
sys.modules['langchain_openai'] = openai_mod

# --- Stub langgraph.prebuilt.ToolExecutor ---
prebuilt_mod = types.ModuleType('langgraph.prebuilt')
class ToolExecutor:
    def __init__(self, tools):
        self.tools = {}
        for t in tools:
            name = getattr(t, 'name', getattr(t, '__name__', None))
            if not name:
                continue
            self.tools[name] = t
    def invoke(self, action):
        name = action.get('name') if isinstance(action, dict) else action.name
        args_json = action.get('arguments') if isinstance(action, dict) else '{}'
        import json
        try:
            kwargs = json.loads(args_json) if isinstance(args_json, str) else (args_json or {})
        except Exception:
            kwargs = {}
        fn = self.tools.get(name)
        if fn is None:
            raise RuntimeError(f"Tool '{name}' not found")
        return fn(**kwargs) if kwargs else fn()
prebuilt_mod.ToolExecutor = ToolExecutor
sys.modules['langgraph.prebuilt'] = prebuilt_mod

# --- Stub langgraph.graph ---
graph_mod = types.ModuleType('langgraph.graph')
END = object()
class StateGraph:
    def __init__(self, state_type):
        self.nodes = {}
        self.edges = []  # list of (src, dst)
        self.cond = {}   # node -> (fn, mapping)
        self.entry = None
    def add_node(self, name, fn):
        self.nodes[name] = fn
    def add_edge(self, src, dst):
        self.edges.append((src, dst))
    def set_entry_point(self, name):
        self.entry = name
    def add_conditional_edges(self, node, cond_fn, mapping):
        self.cond[node] = (cond_fn, mapping)
    def compile(self):
        class App:
            def __init__(self, sg):
                self.sg = sg
            def invoke(self, state):
                current = self.sg.entry
                visited = 0
                while True:
                    fn = self.sg.nodes[current]
                    delta = fn(state)
                    if delta:
                        # merge lists: for 'messages' we extend
                        for k, v in delta.items():
                            if k == 'messages':
                                state[k] = state.get(k, []) + v
                            else:
                                state[k] = v
                    # conditional?
                    if current in self.sg.cond:
                        cond_fn, mapping = self.sg.cond[current]
                        key = cond_fn(state)
                        nxt = mapping.get(key)
                        if nxt is END:
                            return state
                        current = nxt
                    else:
                        # find linear edge
                        nexts = [d for s, d in self.sg.edges if s == current]
                        if not nexts:
                            return state
                        current = nexts[0]
                        visited += 1
                        if visited > 50:
                            # safety
                            return state
        return App(self)

graph_mod.StateGraph = StateGraph
graph_mod.END = END
sys.modules['langgraph.graph'] = graph_mod

# --- Environment for the agent ---
os.environ.setdefault('API_BASE_URL', 'http://127.0.0.1:8000/api/v1')
os.environ.setdefault('LOCAL_LLM_URL', 'http://127.0.0.1:8001/v1')
os.environ['REPO_PATH'] = str((PROJECT_ROOT / 'desktop_backend' / '.tmp_repo_integration').resolve())

# --- Import and run agent in a daemon thread ---
from desktop_backend import agent as agent_mod

def run():
    t = threading.Thread(target=agent_mod.run_agent, daemon=True)
    t.start()
    # Let it run for a short duration to acquire one job and complete
    time.sleep(20)
    print('Full agent loop test finished.')

if __name__ == '__main__':
    run()
