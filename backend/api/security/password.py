"""
密碼強度驗證 + bcrypt context 集中化。

規格 §五.6：最小 8 字元、需含大寫 + 小寫 + 數字；Bcrypt cost factor = 12。
單一函式以 ValueError 標示違規，由呼叫端自行轉換為 HTTPException 或 sys.exit。
"""
from __future__ import annotations

import re

from passlib.context import CryptContext

MIN_LENGTH: int = 8

# 共用的 bcrypt context。auth / users / seed 三處原各自實例化，集中於此避免漂移。
pwd_context: CryptContext = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def validate_password_strength(password: str) -> None:
    """
    依規格 §五.6 驗證密碼強度。違規時 raise ValueError。

    錯誤訊息以使用者可讀的繁體中文表達，呼叫端可直接轉發。
    """
    if len(password) < MIN_LENGTH:
        raise ValueError(f"密碼太短（{len(password)} 字元），最少需要 {MIN_LENGTH} 字元。")
    if not re.search(r"[A-Z]", password):
        raise ValueError("密碼必須包含至少一個大寫英文字母。")
    if not re.search(r"[a-z]", password):
        raise ValueError("密碼必須包含至少一個小寫英文字母。")
    if not re.search(r"\d", password):
        raise ValueError("密碼必須包含至少一個數字。")
