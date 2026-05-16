from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes.agent_flow import router as agent_flow_router
from backend.config import CORS_ORIGINS, TASK_DIR
from backend.api.routes.datasets import router as datasets_router
from backend.api.routes.models import router as models_router
from backend.api.routes.prediction import router as prediction_router
from backend.api.routes.recommendation import router as recommendation_router
from backend.api.routes.tasks import router as tasks_router

logger = logging.getLogger(__name__)


def create_api_app() -> FastAPI:
    app = FastAPI(title="Clinical Workbench Backend API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok"}

    app.include_router(tasks_router)
    app.include_router(datasets_router)
    app.include_router(models_router)
    app.include_router(prediction_router)
    app.include_router(recommendation_router)
    app.include_router(agent_flow_router)
    app.mount("/static", StaticFiles(directory=TASK_DIR), name="static")

    @app.on_event("startup")
    def _log_prediction_routes() -> None:
        """Helps verify whether routes such as POST /prediction/single are registered when diagnosing 404s."""
        lines: list[str] = []
        for r in app.routes:
            path = str(getattr(r, "path", "") or "")
            methods = getattr(r, "methods", None) or set()
            if "/prediction" in path:
                lines.append(f"{sorted(methods)} {path}")
        if lines:
            logger.warning("[prediction routes] %s", " | ".join(sorted(lines)))
        else:
            logger.warning("[prediction routes] none matched /prediction — check include_router(prediction_router)")

    return app

