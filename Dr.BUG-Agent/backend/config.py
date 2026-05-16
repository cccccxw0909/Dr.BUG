from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

BACKEND_DIR = BASE_DIR / "backend"
RUNTIME_DIR = BACKEND_DIR / "runtime_data"
DATASET_DIR = RUNTIME_DIR / "datasets"
TASK_DIR = RUNTIME_DIR / "tasks"
MODEL_DIR = BASE_DIR / "models"
MODEL_REGISTRY_PATH = MODEL_DIR / "registry.json"
TMP_UPLOAD_DIR = RUNTIME_DIR / "_tmp_uploads"
PENDING_ACTION_DIR = RUNTIME_DIR / "pending_actions"
AUDIT_DIR = RUNTIME_DIR / "audit"

STATIC_PORT = 8001
MCP_PORT = 8000
STATIC_BASE_URL = f"http://localhost:{STATIC_PORT}/static"

APP_ENV = os.getenv("APP_ENV", "dev").lower()
ENABLE_DEBUG_ENDPOINTS = os.getenv("ENABLE_DEBUG_ENDPOINTS", "1" if APP_ENV == "dev" else "0") == "1"

CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

# DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
# DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip() or "https://api.deepseek.com"
# DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip() or "deepseek-chat"
QWEN_API_KEY = os.getenv("QWEN_API_KEY", "").strip()
QWEN_BASE_URL = os.getenv(
    "QWEN_BASE_URL",
    "https://dashscope.aliyuncs.com/compatible-mode/v1",
).strip() or "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-plus").strip() or "qwen-plus"

# Narrative polish (optional LLM rewrite of chat text only; default off).
USE_LLM_NARRATIVE_POLISH = os.getenv("USE_LLM_NARRATIVE_POLISH", "false").strip().lower() in (
    "1",
    "true",
    "yes",
)
LLM_NARRATIVE_POLISH_SCENARIOS = tuple(
    s.strip()
    for s in (os.getenv("LLM_NARRATIVE_POLISH_SCENARIOS", "training_completed") or "").split(",")
    if s.strip()
)

for path in [RUNTIME_DIR, DATASET_DIR, TASK_DIR, MODEL_DIR, TMP_UPLOAD_DIR, PENDING_ACTION_DIR, AUDIT_DIR]:
    path.mkdir(parents=True, exist_ok=True)