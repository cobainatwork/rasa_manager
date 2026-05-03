"""
FastAPI 應用入口：掛載所有路由、CORS 中間件、健康檢查端點。
"""
import logging
import os

import redis as redis_lib
import structlog
from fastapi import Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.database.session import get_db
from api.routes import agent_admin, agents, audit, auth, categories, chat, faq, import_export, sync, users


def _resolve_log_level(level_name: str) -> int:
    """將具名 log level（"INFO"、"DEBUG"）或數字字串（"20"）轉為 logging 整數常數。"""
    return getattr(logging, level_name.upper(), logging.INFO)


# ── structlog 全域設定 ────────────────────────────────────────────────────
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        _resolve_log_level(os.environ.get("LOG_LEVEL", "INFO"))
    ),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

app = FastAPI(
    title="Rasa RAG Knowledge Base API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

_cors_origin = os.environ.get("CORS_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# I13：health check 專用 module-level singleton，避免每次健檢都新建 connection pool
_health_redis_client: redis_lib.Redis | None = None


def _get_health_redis() -> redis_lib.Redis:
    global _health_redis_client
    if _health_redis_client is None:
        _health_redis_client = redis_lib.from_url(REDIS_URL)
    return _health_redis_client

# ── 路由掛載 ──────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(agents.router)
app.include_router(categories.router)
app.include_router(import_export.router)   # 必須在 faq.router 之前（/faqs/export 優先於 /faqs/{faq_id}）
app.include_router(faq.router)
app.include_router(sync.router)
app.include_router(agent_admin.router)
app.include_router(chat.router)
app.include_router(audit.router)


# ── 健康檢查（不需認證）──────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["health"])
def health_check(
    response: Response, db: Session = Depends(get_db)
) -> dict[str, str]:
    result: dict[str, str] = {"status": "ok", "db": "unknown", "redis": "unknown"}
    overall_ok = True

    try:
        db.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception:
        result["db"] = "error"
        overall_ok = False

    try:
        r = _get_health_redis()
        r.ping()
        result["redis"] = "ok"
    except Exception:
        result["redis"] = "error"
        overall_ok = False

    if not overall_ok:
        response.status_code = 503
        result["status"] = "error"

    return result
