import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CategoryTree } from './CategoryTree'
import { buildCategoryTree } from '@/lib/categories'

const sample = buildCategoryTree([
  { id: '1', name: '產品功能', parent_id: null },
  { id: '2', name: '帳號', parent_id: '1' },
])

const baseResult = {
  tree: sample,
  loading: false,
  selectedId: null,
  pendingRenameId: null,
  select: vi.fn(),
  reload: vi.fn(),
  rename: vi.fn(),
  addChild: vi.fn(),
  remove: vi.fn(),
  clearPendingRename: vi.fn(),
  exportCategory: vi.fn(),
  importCategory: vi.fn(),
  syncCategory: vi.fn(),
}

describe('CategoryTree', () => {
  it('渲染樹狀結構', () => {
    render(<CategoryTree result={baseResult} />)
    expect(screen.getByText('產品功能')).toBeInTheDocument()
    expect(screen.getByText('帳號')).toBeInTheDocument()
  })

  it('+ 按鈕呼叫 addChild(null)', async () => {
    const user = userEvent.setup()
    const addChild = vi.fn()
    render(<CategoryTree result={{ ...baseResult, addChild }} />)
    await user.click(screen.getByLabelText('新增根類別'))
    expect(addChild).toHaveBeenCalledWith(null)
  })

  it('loading 顯示 skeleton', () => {
    render(<CategoryTree result={{ ...baseResult, loading: true, tree: [] }} />)
    expect(screen.queryByText('產品功能')).not.toBeInTheDocument()
  })

  it('空狀態顯示「尚無分類」', () => {
    render(<CategoryTree result={{ ...baseResult, tree: [] }} />)
    expect(screen.getByText('尚無分類')).toBeInTheDocument()
  })
})
