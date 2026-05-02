"""
分類路徑工具函式，供 import_export.py 與 tasks.py 共用。
"""
from __future__ import annotations

from typing import Any


def build_category_path(
    category_id: Any, cat_map: dict[Any, Any]
) -> str:
    """
    從 category_id 向上追溯組合完整路徑字串（/ 分隔）。
    使用預先載入的 cat_map（id -> Category）避免 N+1 query。
    category_id 不在 cat_map 中時回傳空字串。
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


def collect_category_subtree(
    root_id: Any, cat_map: dict[Any, Any]
) -> set[Any]:
    """
    從 root_id 出發，以迭代 DFS 收集所有子孫分類 ID（含自身）。
    使用預先載入的 cat_map 避免 N+1 查詢。
    先建立 parent_id -> children 反向索引（O(N)），DFS 整體複雜度 O(N)。
    """
    # 預先建立反向索引，避免每步 DFS 全表掃描造成 O(N²)
    children_map: dict[Any, list[Any]] = {}
    for cat in cat_map.values():
        if cat.parent_id is not None:
            children_map.setdefault(cat.parent_id, []).append(cat.id)

    result: set[Any] = set()
    stack = [root_id]
    while stack:
        cid = stack.pop()
        if cid in result:
            continue
        result.add(cid)
        stack.extend(children_map.get(cid, []))
    return result
