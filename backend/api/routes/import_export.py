"""
Excel 批次匯入 / 匯出路由。

匯入規格（§4.3 + §21.14）：
  - 僅接受 .xlsx，上限 10 MB / 5000 行
  - 必填欄：question、answer、category_path（/ 分隔）
  - 選填欄：tags（逗號分隔字串）
  - 一律建立為 draft 狀態
  - category_path 不存在時自動建立節點
  - 相同 agent_id + question 已存在 → 跳過
  - 操作結束後關閉 workbook（openpyxl read_only 模式）

匯出規格（§4.3）：
  - 欄位：id、status、category_path、tags、question、answer、version、created_at、updated_at
  - 回傳 StreamingResponse（xlsx）
"""
from __future__ import annotations

import io
import uuid
from typing import Any, Optional

import openpyxl
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.database.models import AuditLog, Category, KnowledgeItem, User
from api.database.session import get_db
from api.dependencies import get_current_user, require_agent_access

router = APIRouter(tags=["import-export"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ROWS = 5000


# ── 分類路徑工具函式 ──────────────────────────────────────────────────────────

def _resolve_category_path(db: Session, agent_id: Any, path_str: str) -> Any:
    """
    解析 / 分隔的 category_path，自動建立缺少的節點。
    回傳最末層的 category.id。
    """
    parts = [p.strip() for p in path_str.split("/") if p.strip()]
    if not parts:
        raise ValueError(f"category_path 不可為空：{path_str!r}")

    parent_id: Optional[Any] = None
    for part in parts:
        cat = (
            db.query(Category)
            .filter(
                Category.agent_id == agent_id,
                Category.name == part,
                Category.parent_id == parent_id,
            )
            .first()
        )
        if cat is None:
            cat = Category(
                id=uuid.uuid4(),
                agent_id=agent_id,
                parent_id=parent_id,
                name=part,
                sort_order=0,
            )
            db.add(cat)
            db.flush()
        parent_id = cat.id

    return parent_id


def _build_category_path(db: Session, category_id: Any) -> str:
    """從 category_id 向上追溯，組合完整路徑字串（/ 分隔）。"""
    parts: list[str] = []
    current_id = category_id
    visited: set[Any] = set()
    while current_id is not None:
        if current_id in visited:
            break
        visited.add(current_id)
        cat = db.query(Category).filter(Category.id == current_id).first()
        if cat is None:
            break
        parts.insert(0, str(cat.name))
        current_id = cat.parent_id
    return "/".join(parts)


# ── 匯入端點 ──────────────────────────────────────────────────────────────────

@router.post("/api/v1/agents/{agent_id}/faqs/import")
def import_faqs(
    agent_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_agent_access(agent_id, current_user, db)

    # ── 檔案格式與大小驗證 ─────────────────────────────────────────────────────
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="僅接受 .xlsx 格式檔案")

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="檔案大小超過 10 MB 上限")

    # ── 解析 Excel ─────────────────────────────────────────────────────────────
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            raise ValueError("找不到工作表")
        all_rows = list(ws.iter_rows(values_only=True))
        wb.close()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"無法解析 Excel 檔案：{exc}") from exc

    if len(all_rows) < 2:
        raise HTTPException(status_code=400, detail="Excel 無資料列（需含標題行）")

    header = [str(c).strip().lower() if c is not None else "" for c in all_rows[0]]
    data_rows = all_rows[1:]

    if len(data_rows) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f"資料列數超過 {MAX_ROWS} 行上限")

    # ── 欄位索引解析 ───────────────────────────────────────────────────────────
    def require_col(name: str) -> int:
        if name not in header:
            raise HTTPException(status_code=400, detail=f"缺少必填欄位：{name}")
        return header.index(name)

    q_idx = require_col("question")
    a_idx = require_col("answer")
    cp_idx = require_col("category_path")
    tags_idx: Optional[int] = header.index("tags") if "tags" in header else None

    # ── 預載已存在的 question（避免重複）──────────────────────────────────────
    existing_questions: set[str] = {
        str(q)
        for (q,) in db.query(KnowledgeItem.question)
        .filter(KnowledgeItem.agent_id == agent_id)
        .all()
    }

    success = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    new_categories: set[str] = set()

    for row_num, row in enumerate(data_rows, start=2):
        def cell(idx: int) -> str:
            val = row[idx] if idx < len(row) else None  # type: ignore[index]
            return str(val).strip() if val is not None else ""

        question = cell(q_idx)
        answer = cell(a_idx)
        category_path = cell(cp_idx)
        tags_raw = cell(tags_idx) if tags_idx is not None else ""

        # 空列跳過
        if not question and not answer and not category_path:
            continue

        if not question or not answer or not category_path:
            errors.append({
                "row": row_num,
                "reason": "question / answer / category_path 不可為空",
            })
            continue

        if question in existing_questions:
            skipped += 1
            continue

        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        try:
            cat_count_before = (
                db.query(Category).filter(Category.agent_id == agent_id).count()
            )
            category_id = _resolve_category_path(db, agent_id, category_path)
            cat_count_after = (
                db.query(Category).filter(Category.agent_id == agent_id).count()
            )
            if cat_count_after > cat_count_before:
                new_categories.add(category_path)

            item = KnowledgeItem(
                id=uuid.uuid4(),
                agent_id=agent_id,
                category_id=category_id,
                question=question,
                answer=answer,
                tags=tags_list,
                status="draft",
                version=1,
                created_by=current_user.id,
            )
            db.add(item)
            db.flush()

            db.add(AuditLog(
                id=uuid.uuid4(),
                agent_id=agent_id,
                item_id=item.id,
                action="import",
                performed_by=current_user.id,
                diff={"question": question, "category_path": category_path},
            ))

            existing_questions.add(question)
            success += 1

        except Exception as exc:
            db.rollback()
            errors.append({"row": row_num, "reason": str(exc)})
            # 重新載入 existing_questions 避免後續 flush 失效
            existing_questions = {
                str(q)
                for (q,) in db.query(KnowledgeItem.question)
                .filter(KnowledgeItem.agent_id == agent_id)
                .all()
            }

    db.commit()

    return {
        "success": True,
        "data": {
            "imported": success,
            "skipped": skipped,
            "errors": errors,
            "new_categories": sorted(new_categories),
        },
    }


# ── 匯出端點 ──────────────────────────────────────────────────────────────────

@router.get("/api/v1/agents/{agent_id}/faqs/export")
def export_faqs(
    agent_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    require_agent_access(agent_id, current_user, db)

    items = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.agent_id == agent_id)
        .order_by(KnowledgeItem.created_at)
        .all()
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "FAQs"  # type: ignore[union-attr]

    ws.append(  # type: ignore[union-attr]
        ["id", "status", "category_path", "tags", "question", "answer",
         "version", "created_at", "updated_at"]
    )

    for item in items:
        category_path = _build_category_path(db, item.category_id)
        tags_str = ",".join(item.tags) if item.tags else ""
        ws.append([  # type: ignore[union-attr]
            str(item.id),
            str(item.status),
            category_path,
            tags_str,
            str(item.question),
            str(item.answer),
            item.version if item.version is not None else 1,
            item.created_at.isoformat() if item.created_at else "",
            item.updated_at.isoformat() if item.updated_at else "",
        ])

    # 稽核紀錄
    db.add(AuditLog(
        id=uuid.uuid4(),
        agent_id=agent_id,
        item_id=None,
        action="export",
        performed_by=current_user.id,
        diff={"count": len(items)},
    ))
    db.commit()

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=faq_export.xlsx"},
    )
