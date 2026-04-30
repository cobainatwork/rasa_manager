import type { CategoryNode } from '@/api/types'

type FlatCategory = Pick<CategoryNode, 'id' | 'name' | 'parent_id'> &
  Partial<Omit<CategoryNode, 'id' | 'name' | 'parent_id'>>

export function buildCategoryTree(items: FlatCategory[]): CategoryNode[] {
  const map = new Map<string, CategoryNode>()
  for (const it of items) {
    map.set(it.id, {
      id: it.id,
      name: it.name,
      parent_id: it.parent_id,
      sort_order: it.sort_order ?? 0,
      created_at: it.created_at ?? null,
      updated_at: it.updated_at ?? null,
      children: [],
    })
  }
  const roots: CategoryNode[] = []
  for (const node of map.values()) {
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id)!.children.push(node)
    } else {
      roots.push(node)
    }
  }
  return roots
}

export interface FlatPath { id: string; path: string }

export function flattenCategories(tree: CategoryNode[], prefix = ''): FlatPath[] {
  const out: FlatPath[] = []
  for (const node of tree) {
    const path = prefix ? `${prefix}/${node.name}` : node.name
    out.push({ id: node.id, path })
    if (node.children.length > 0) out.push(...flattenCategories(node.children, path))
  }
  return out
}

export function buildCategoryPath(targetId: string, items: FlatCategory[]): string {
  const map = new Map(items.map((c) => [c.id, c]))
  const segments: string[] = []
  let cur = map.get(targetId)
  while (cur) {
    segments.unshift(cur.name)
    cur = cur.parent_id ? map.get(cur.parent_id) : undefined
  }
  return segments.join('/')
}
