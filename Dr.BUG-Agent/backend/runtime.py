from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from backend.config import DATASET_DIR, MODEL_REGISTRY_PATH, TASK_DIR
from backend.repositories import FileDatasetRepo, FileModelRepo, FileTaskRepo

dataset_repo = FileDatasetRepo(DATASET_DIR)
model_repo = FileModelRepo(MODEL_REGISTRY_PATH)
task_repo = FileTaskRepo(TASK_DIR)
executor = ThreadPoolExecutor(max_workers=2)

