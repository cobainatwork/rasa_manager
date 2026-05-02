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
from typing import Any, Literal, Optional

import openpyxl
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.database.models import AuditLog, Category, KnowledgeItem, User
from api.database.session import get_db
from api.dependencies import get_current_user, require_agent_access

router = APIRouter(tags=["import-export"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_ROWS = 5000


# ── 分類路徑工具函式 ──────────────────────────────────────────────────────────

def _resolve_category_path(
    db: Session, agent_id: Any, path_str: str
) -> tuple[Any, bool]:
    """
    解析 / 分隔的 category_path，自動建立缺少的節點。
    回傳 (最末層 category.id, 本次是否新建任何分類層)。
    """
    parts = [p.strip() for p in path_str.split("/") if p.strip()]
    if not parts:
        raise ValueError(f"category_path 不可為空：{path_str!r}")

    parent_id: Optional[Any] = None
    created = False
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
            created = True
        parent_id = cat.id

    return parent_id, created


def _build_category_path(
    category_id: Any, cat_map: dict[Any, Category]
) -> str:
    """
    從 category_id 向上追溯組合完整路徑字串（/ 分隔）。
    使用預先載入的 cat_map（id -> Category）避免 N+1 query。
    """
    parts: list[str] = []
    current_id = category_id
    visited: set[Any] = set()
    while current_id is not None:
        if current_id in visited:
            break
        visited.add(current_id)
        cat = cat_map.get(current_id)
        if cat is None:
            break
        parts.insert(0, str(cat.name))
        current_id = cat.parent_id
    return "/".join(parts)


def _collect_category_ids(root_id: Any, cat_map: dict[Any, Category]) -> set[Any]:
    """
    從 root_id 出發，以迭代 DFS 收集所有子孫分類 ID（含自身）。
    使用預先載入的 cat_map 避免 N+1 查詢。
    """
    result: set[Any] = set()
    stack = [root_id]
    while stack:
        cid = stack.pop()
        if cid in result:
            continue
        result.add(cid)
        for cat in cat_map.values():
            if cat.parent_id == cid:
                stack.append(cat.id)
    return result


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

        # 使用 SAVEPOINT（nested transaction）：單筆失敗只 rollback 該筆，
        # 不影響先前已 flush 的成功項目。
        try:
            with db.begin_nested():
                # I2：以 _resolve_category_path 回傳的 created flag 取代前後兩次 count()
                category_id, created = _resolve_category_path(
                    db, agent_id, category_path
                )
                if created:
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
            # SAVEPOINT 已自動 rollback 該筆，無需手動 rollback 整批
            errors.append({"row": row_num, "reason": str(exc)})

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

    # I6：一次性載入該 agent 所有 categories，避免每筆 FAQ 重新遞迴查詢
    all_cats = db.query(Category).filter(Category.agent_id == agent_id).all()
    cat_map: dict[Any, Category] = {c.id: c for c in all_cats}

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "FAQs"  # type: ignore[union-attr]

    ws.append(  # type: ignore[union-attr]
        ["id", "status", "category_path", "tags", "question", "answer",
         "version", "created_at", "updated_at"]
    )

    for item in items:
        category_path = _build_category_path(item.category_id, cat_map)
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


# ── 分類匯出端點 ──────────────────────────────────────────────────────────────

@router.get("/api/v1/agents/{agent_id}/categories/{category_id}/export")
def export_category_faqs(
    agent_id: uuid.UUID,
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    require_agent_access(agent_id, current_user, db)

    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.agent_id == agent_id)
        .first()
    )
    if category is None:
        raise HTTPException(status_code=404, detail="找不到分類")

    all_cats = db.query(Category).filter(Category.agent_id == agent_id).all()
    cat_map: dict[Any, Category] = {c.id: c for c in all_cats}

    cat_ids = _collect_category_ids(category_id, cat_map)

    items = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.agent_id == agent_id)
        .filter(KnowledgeItem.category_id.in_(cat_ids))
        .order_by(KnowledgeItem.created_at)
        .all()
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "FAQs"  # type: ignore[union-attr]
    ws.append(["question", "answer", "tags", "status", "version"])  # type: ignore[union-attr]

    for item in items:
        tags_str = ",".join(item.tags) if item.tags else ""
        ws.append([  # type: ignore[union-attr]
            str(item.question),
            str(item.answer),
            tags_str,
            str(item.status),
            item.version if item.version is not None else 1,
        ])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    db.add(AuditLog(
        id=uuid.uuid4(),
        agent_id=agent_id,
        item_id=None,
        action="export_category",
        performed_by=current_user.id,
        diff={"category_id": str(category_id), "count": len(items)},
    ))
    db.commit()

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=category_{category_id}_export.xlsx"
        },
    )


# ── 分類匯入端點 ──────────────────────────────────────────────────────────────

@router.post("/api/v1/agents/{agent_id}/categories/{category_id}/import")
def import_category_faqs(
    agent_id: uuid.UUID,
    category_id: uuid.UUID,
    mode: Literal["append", "replace"] = Query("append"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    require_agent_access(agent_id, current_user, db)

    # 驗證分類存在且屬於此 agent
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.agent_id == agent_id)
        .first()
    )
    if category is None:
        raise HTTPException(status_code=404, detail="找不到分類")

    # replace 模式：先刪除該分類（含所有子分類）的全部 FAQ
    if mode == "replace":
        all_cats = db.query(Category).filter(Category.agent_id == agent_id).all()
        cat_map_del: dict[Any, Category] = {c.id: c for c in all_cats}
        del_cat_ids = _collect_category_ids(category_id, cat_map_del)
        items_to_del = (
            db.query(KnowledgeItem)
            .filter(
                KnowledgeItem.agent_id == agent_id,
                KnowledgeItem.category_id.in_(del_cat_ids),
            )
            .all()
        )
        deleted_count = len(items_to_del)
        for item in items_to_del:
            db.delete(item)
        db.flush()
        if deleted_count > 0:
            db.add(AuditLog(
                id=uuid.uuid4(),
                agent_id=agent_id,
                item_id=None,
                action="bulk_delete_category",
                performed_by=current_user.id,
                diff={"category_id": str(category_id), "deleted_count": deleted_count},
            ))

    # 檔案格式與大小驗證
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="僅接受 .xlsx 格式檔案")

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="檔案大小超過 10 MB 上限")

    # 解析 Excel
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

    # 只需 question + answer（無 category_path）
    def require_col(name: str) -> int:
        if name not in header:
            raise HTTPException(status_code=400, detail=f"缺少必填欄位：{name}")
        return header.index(name)

    q_idx = require_col("question")
    a_idx = require_col("answer")
    tags_idx: Optional[int] = header.index("tags") if "tags" in header else None

    # replace 後 existing_questions 應已清空，flush 確保可見
    existing_questions: set[str] = {
        str(q)
        for (q,) in db.query(KnowledgeItem.question)
        .filter(KnowledgeItem.agent_id == agent_id)
        .all()
    }

    success = 0
    skipped = 0
    errors: list[dict[str, Any]] = []

    for row_num, row in enumerate(data_rows, start=2):
        def cell(idx: int) -> str:
            val = row[idx] if idx < len(row) else None  # type: ignore[index]
            return str(val).strip() if val is not None else ""

        question = cell(q_idx)
        answer = cell(a_idx)
        tags_raw = cell(tags_idx) if tags_idx is not None else ""

        # 空列跳過
        if not question and not answer:
            continue

        if not question or not answer:
            errors.append({"row": row_num, "reason": "question / answer 不可為空"})
            continue

        if question in existing_questions:
            skipped += 1
            continue

        tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

        try:
            with db.begin_nested():
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
                    action="import_category",
                    performed_by=current_user.id,
                    diff={"question": question, "category_id": str(category_id)},
                ))

            existing_questions.add(question)
            success += 1

        except Exception as exc:
            errors.append({"row": row_num, "reason": str(exc)})

    db.commit()

    return {
        "success": True,
        "data": {
            "imported": success,
            "skipped": skipped,
            "errors": errors,
        },
    }
