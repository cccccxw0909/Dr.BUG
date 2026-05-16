from __future__ import annotations

import json
import shutil
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import STATIC_BASE_URL
from backend.schemas.task import JobType, Task, TaskStatus
from backend.utils.time_utils import now_iso


class FileTaskRepo:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def task_dir(self, job_id: str) -> Path:
        return self.root / job_id

    def task_json(self, job_id: str) -> Path:
        return self.task_dir(job_id) / "task.json"

    def logs_jsonl(self, job_id: str) -> Path:
        return self.task_dir(job_id) / "logs.jsonl"

    def artifacts_dir(self, job_id: str) -> Path:
        return self.task_dir(job_id) / "artifacts"

    def create(self, job_type: JobType, params: Dict[str, Any]) -> Dict[str, Any]:
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        folder = self.task_dir(job_id)
        folder.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir(job_id).mkdir(parents=True, exist_ok=True)

        task = Task(
            id=job_id,
            job_type=job_type,
            status=TaskStatus.queued,
            progress=0,
            current_stage="queued",
            message="Job created",
            params=params,
            created_at=now_iso(),
        ).model_dump(mode="json")

        self._write_task(job_id, task)
        self.append_log(job_id, "Job created; waiting to run.")
        return task

    def _write_task(self, job_id: str, data: Dict[str, Any]) -> None:
        with self.lock:
            self.task_json(job_id).write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        path = self.task_json(job_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def update(self, job_id: str, **kwargs: Any) -> Dict[str, Any]:
        task = self.get(job_id)
        if not task:
            raise ValueError(f"job_id={job_id} not found")
        task.update(kwargs)
        Task.model_validate(task)
        self._write_task(job_id, task)
        return task

    def list(self, status: Optional[str] = None, job_type: Optional[str] = None) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for child in self.root.iterdir():
            if not child.is_dir():
                continue
            path = child / "task.json"
            if not path.exists():
                continue
            task = json.loads(path.read_text(encoding="utf-8"))
            if status and task["status"] != status:
                continue
            if job_type and task["job_type"] != job_type:
                continue
            results.append(task)
        results.sort(key=lambda item: item["created_at"], reverse=True)
        return results

    def append_log(self, job_id: str, message: str) -> None:
        line = {"time": now_iso(), "message": message}
        with self.lock:
            with self.logs_jsonl(job_id).open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(line, ensure_ascii=False) + "\n")

    def read_logs(self, job_id: str) -> List[Dict[str, Any]]:
        path = self.logs_jsonl(job_id)
        if not path.exists():
            return []
        rows: List[Dict[str, Any]] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if raw:
                rows.append(json.loads(raw))
        return rows

    def list_artifacts(self, job_id: str) -> Dict[str, str]:
        artifact_dir = self.artifacts_dir(job_id)
        if not artifact_dir.exists():
            return {}
        urls: Dict[str, str] = {}
        for file in artifact_dir.iterdir():
            if file.is_file():
                urls[file.name] = f"{STATIC_BASE_URL}/{job_id}/artifacts/{file.name}"
        return urls

    def resolve_safe_artifact_file(self, job_id: str, filename: str) -> Optional[Path]:
        """Resolve a basename inside this job's artifacts directory; rejects path traversal."""
        fn = str(filename or "").strip()
        if not fn or fn != Path(fn).name:
            return None
        if fn in {".", ".."} or ".." in fn:
            return None
        artifact_dir = self.artifacts_dir(job_id)
        if not artifact_dir.exists():
            return None
        candidate = (artifact_dir / fn).resolve()
        root = artifact_dir.resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return None
        if not candidate.is_file():
            return None
        return candidate

    def delete(self, job_id: str) -> bool:
        folder = self.task_dir(job_id)
        if not folder.exists() or not folder.is_dir():
            return False
        with self.lock:
            if not folder.exists():
                return False
            shutil.rmtree(folder)
        return True

