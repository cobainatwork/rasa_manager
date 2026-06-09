"""
統一 HTTPException 樣板：以 ErrorCode + helper 函式取代散落各 route 的
raise HTTPException(status_code=..., detail={"code": ..., "message": ...})。

設計原則：
1. response body 結構保持 detail={"code": <code>, "message": <message>}，
   與既有測試 assert 完全等價。
2. 每個 helper 對應一個 HTTP status code，避免 callsite 自行傳入 status_code。
3. 對於非通用 code（例如 LOCKED、DUPLICATE_NAME、DEPTH_EXCEEDED），提供
   raise_http(code, status_code, message) 的低階入口供 route 直接使用。
"""
from __future__ import annotations

from enum import Enum
from typing import NoReturn

from fastapi import HTTPException, status


class ErrorCode(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNPROCESSABLE = "UNPROCESSABLE"
    RATE_LIMIT = "RATE_LIMIT"
    LOCKED = "LOCKED"
    BAD_GATEWAY = "BAD_GATEWAY"
    TIMEOUT = "TIMEOUT"
    DEPTH_EXCEEDED = "DEPTH_EXCEEDED"
    DUPLICATE_NAME = "DUPLICATE_NAME"


def raise_http(code: str, status_code: int, message: str) -> NoReturn:
    """通用入口：以 detail={"code": code, "message": message} 拋出 HTTPException。"""
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def raise_not_found(message: str) -> NoReturn:
    raise_http(ErrorCode.NOT_FOUND.value, status.HTTP_404_NOT_FOUND, message)


def raise_forbidden(message: str) -> NoReturn:
    raise_http(ErrorCode.FORBIDDEN.value, status.HTTP_403_FORBIDDEN, message)


def raise_unauthorized(message: str) -> NoReturn:
    raise_http(ErrorCode.UNAUTHORIZED.value, status.HTTP_401_UNAUTHORIZED, message)


def raise_conflict(message: str) -> NoReturn:
    raise_http(ErrorCode.CONFLICT.value, status.HTTP_409_CONFLICT, message)


def raise_validation_error(message: str) -> NoReturn:
    raise_http(
        ErrorCode.VALIDATION_ERROR.value, status.HTTP_400_BAD_REQUEST, message
    )


def raise_unprocessable(message: str) -> NoReturn:
    raise_http(
        ErrorCode.UNPROCESSABLE.value,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        message,
    )


def raise_locked(message: str) -> NoReturn:
    """編輯鎖衝突：與 raise_conflict 同 status 409，但 code 為 LOCKED。"""
    raise_http(ErrorCode.LOCKED.value, status.HTTP_409_CONFLICT, message)
