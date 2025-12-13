
import os
from dotenv import load_dotenv
from llama_cpp.server.app import create_app
from llama_cpp.server.settings import Settings, ModelSettings
import uvicorn

import ctypes
from llama_cpp import Llama

# GPU 레이어 설정 (n_gpu_layers)
# 0으로 설정하면 CPU만 사용하고, 1 이상의 값으로 설정하면 해당 수의 레이어를 GPU로 오프로드합니다.
n_gpu_layers = -1 # GPU 사용을 시도하도록 설정

# llama.cpp 라이브러리에서 CUDA 지원 여부를 확인하는 함수
def is_cuda_available():
    try:
        # llama.dll 또는 libllama.so 라이브러리를 로드하여 CUDA 빌드 여부를 확인
        lib = ctypes.CDLL(ctypes.util.find_library("llama"))
        return lib.llama_supports_gpu_offload()
    except Exception:
        return False

# GPU 사용 가능 여부 확인
gpu_enabled = is_cuda_available()

if n_gpu_layers > 0 and not gpu_enabled:
    print("⚠️ 경고: GPU 가속이 활성화되지 않았습니다.")
    print("모델 로딩 및 추론 속도가 매우 느릴 수 있습니다.")
    
    print("CPU 모드로 서버를 시작합니다...")
    n_gpu_layers = 0  # CPU만 사용하도록 설정 변경




# .env 파일에서 환경 변수 로드
load_dotenv()

# MODEL_PATH 환경 변수 가져오기
MODEL_PATH = os.getenv("MODEL_PATH")
MODEL_DOMAIN = os.getenv("MODEL_DOMAIN")
MODEL_PORT = os.getenv("MODEL_PORT")


if not MODEL_PATH:
    raise ValueError("MODEL_PATH가 .env 파일에 설정되지 않았습니다.")

# llama-cpp-python 서버 설정을 생성합니다.
# 여기에서 호스트, 포트 및 기타 서버 관련 옵션을 구성할 수 있습니다.
settings = Settings(
    model=MODEL_PATH,
    n_gpu_layers=n_gpu_layers, # n_gpu_layers=-1은 가능한 모든 레이어를 GPU로 오프로드. GPU가 없다면 0으로 설정.
    n_threads=os.cpu_count(),
    n_batch=1024,
    flash_attn=True,
    mul_mat_q=True,
    # cache_type_k="q8_0",          # KV 캐시 압축: vRAM 아끼며 속도는 근접
    # cache_type_v="q8_0",
    host=MODEL_DOMAIN if MODEL_DOMAIN else "0.0.0.0",
    port=int(MODEL_PORT) if MODEL_PORT else 8008,
    n_ctx=4096, # 컨텍스트 크기 설정
)

# 설정 객체를 사용하여 FastAPI 앱을 생성합니다.
app = create_app(settings=settings)

print(f"모델이 성공적으로 로드되었습니다. (n_gpu_layers={n_gpu_layers})")

if __name__ == "__main__":
    print("로컬 LLM 서버를 시작합니다.")
    print(f"모델 경로: {MODEL_PATH}")
    print(f"서버가 http://{settings.host}:{settings.port} 에서 실행됩니다.")
    print(f"OpenAI 호환 API 엔드포인트: http://{settings.host}:{settings.port}/v1")
    print("서버를 중지하려면 Ctrl+C를 누르세요.")
    
    # uvicorn을 사용하여 서버를 실행합니다.
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
    )