"""
Superadmin seed script.

Usage:
    python -m api.seed

Env vars: SEED_ADMIN_USERNAME, SEED_ADMIN_PASSWORD
Password rules: min 8 chars, uppercase + lowercase + digit（規格書 §18）
Bcrypt cost factor: 12
Idempotent: 僅在 users 表為空時執行
"""
from __future__ import annotations

import os
import re
import sys
import uuid

from passlib.context import CryptContext
from sqlalchemy import text

from api.database.session import SessionLocal

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise ValueError(f"密碼太短（{len(password)} 字元），最少需要 8 字元。")
    if not re.search(r"[A-Z]", password):
        raise ValueError("密碼必須包含至少一個大寫英文字母。")
    if not re.search(r"[a-z]", password):
        raise ValueError("密碼必須包含至少一個小寫英文字母。")
    if not re.search(r"\d", password):
        raise ValueError("密碼必須包含至少一個數字。")


def run_seed() -> None:
    username = os.environ.get("SEED_ADMIN_USERNAME", "").strip()
    password = os.environ.get("SEED_ADMIN_PASSWORD", "").strip()

    if not username:
        print("[seed] ERROR: SEED_ADMIN_USERNAME 未設定。", file=sys.stderr)
        sys.exit(1)
    if not password:
        print("[seed] ERROR: SEED_ADMIN_PASSWORD 未設定。", file=sys.stderr)
        sys.exit(1)

    try:
        _validate_password(password)
    except ValueError as exc:
        print(f"[seed] ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        db = SessionLocal()
    except Exception as exc:
        print(f"[seed] ERROR: 無法連線資料庫：{exc}", file=sys.stderr)
        sys.exit(1)

    try:
        count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()
        if count and count > 0:
            print(f"[seed] users 表已有 {count} 筆資料，跳過 seed。", flush=True)
            return

        password_hash = _pwd_context.hash(password)
        user_id = uuid.uuid4()
        db.execute(
            text(
                "INSERT INTO users (id, username, password_hash, is_superadmin, is_active) "
                "VALUES (:id, :username, :password_hash, TRUE, TRUE)"
            ),
            {"id": str(user_id), "username": username, "password_hash": password_hash},
        )
        db.commit()
        print(f"[seed] Superadmin '{username}' 建立成功（id={user_id}）。", flush=True)

    except Exception as exc:
        db.rollback()
        print(f"[seed] ERROR: 資料庫操作失敗：{exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
