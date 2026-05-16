from __future__ import annotations

from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Body, Header, Request
from fastapi.responses import JSONResponse

from backend.agent.orchestrator import (
    AgentFlowError,
    handle_action_confirm,
    handle_chat_turn,
    health_check_chat_provider,
    registry,
)
from backend.api.request_locale import api_locale_prefers_english, resolve_api_user_locale_from_request
from backend.api.responses import error_response, success_response
from backend.config import ENABLE_DEBUG_ENDPOINTS
from backend.schemas.agent import ActionConfirmRequest, ChatTurnRequest
from backend.schemas.api_response import (
    ActionConfirmSuccessResponse,
    ChatTurnSuccessResponse,
    ErrorResponse,
    PendingActionDetailSuccessResponse,
)

router = APIRouter(tags=["agent"])


@router.post("/chat/turn", response_model=ChatTurnSuccessResponse, responses={400: {"model": ErrorResponse}})
async def chat_turn(
    req: ChatTurnRequest = Body(...),
    accept_language_header: Annotated[Optional[str], Header(alias="Accept-Language")] = None,
    x_ui_locale: Annotated[Optional[str], Header(alias="X-UI-Locale")] = None,
) -> Dict[str, Any]:
    try:
        ctx = dict(req.chat_context or {})
        hdr = accept_language_header
        if hdr and not ctx.get("accept_language") and not ctx.get("http_accept_language"):
            ctx["accept_language"] = hdr
        ui = (x_ui_locale or "").strip()
        if ui and not str(ctx.get("locale") or "").strip():
            ctx["locale"] = ui
        req = req.model_copy(update={"chat_context": ctx})
        data = handle_chat_turn(req)
        return success_response(data)
    except AgentFlowError as exc:
        return JSONResponse(status_code=400, content=error_response(str(exc), exc.error_code))


@router.post("/actions/confirm", response_model=ActionConfirmSuccessResponse, responses={400: {"model": ErrorResponse}})
async def actions_confirm(req: ActionConfirmRequest, request: Request) -> Dict[str, Any]:
    try:
        merged = req
        if not str(req.locale or "").strip():
            loc_hdr = (request.headers.get("x-ui-locale") or request.headers.get("X-UI-Locale") or "").strip()
            if loc_hdr:
                merged = req.model_copy(update={"locale": loc_hdr})
        data = handle_action_confirm(merged)
        return success_response(data)
    except AgentFlowError as exc:
        status_code = 400
        if exc.error_code in {"PENDING_ACTION_NOT_FOUND"}:
            status_code = 404
        return JSONResponse(status_code=status_code, content=error_response(str(exc), exc.error_code))

@router.get(
    "/pending-actions/{pending_action_id}",
    tags=["debug"],
    response_model=PendingActionDetailSuccessResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def get_pending_action(pending_action_id: str, request: Request) -> Dict[str, Any]:
    if not ENABLE_DEBUG_ENDPOINTS:
        return JSONResponse(
            status_code=403,
            content=error_response("debug endpoint disabled in current environment", "DEBUG_ENDPOINT_DISABLED"),
        )
    loc = resolve_api_user_locale_from_request(request)
    en = api_locale_prefers_english(loc)
    item = registry.get(pending_action_id)
    if not item:
        detail = (
            f"Pending action not found (pending_action_id={pending_action_id})."
            if en
            else f"pending_action_id={pending_action_id} not found"
        )
        return JSONResponse(
            status_code=404,
            content=error_response(detail, "PENDING_ACTION_NOT_FOUND"),
        )
    return success_response({"pending_action": item.model_dump(mode="json")})


@router.get("/chat/provider/health", tags=["agent"], responses={400: {"model": ErrorResponse}})
async def chat_provider_health() -> Dict[str, Any]:
    try:
        data = health_check_chat_provider()
        return success_response(data)
    except AgentFlowError as exc:
        return JSONResponse(status_code=400, content=error_response(str(exc), exc.error_code))

