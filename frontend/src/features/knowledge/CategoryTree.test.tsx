import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
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

// CategoryTree 使用 useParams 取 agentId，需搭配 Router + 路由參數
function renderTree(result = baseResult) {
  return render(
    <MemoryRouter initialEntries={['/agents/a1/knowledge']}>
      <Routes>
        <Route path="/agents/:id/knowledge" element={<CategoryTree result={result} />} />
      </Routes>
    </MemoryRouter>
  )
}

beforeEach(() => {
  // 預設展開根節點 '1'，子節點才會被渲染（isExpanded 從 localStorage 讀取）
  localStorage.setItem('kb_cat_expanded_a1', JSON.stringify({ '1': true }))
})

describe('CategoryTree', () => {
  it('渲染樹狀結構（含展開的子節點）', () => {
    renderTree()
    expect(screen.getByText('產品功能')).toBeInTheDocument()
    expect(screen.getByText('帳號')).toBeInTheDocument()
  })

  it('+ 按鈕呼叫 addChild(null)', async () => {
    const user = userEvent.setup()
    const addChild = vi.fn()
    renderTree({ ...baseResult, addChild })
    await user.click(screen.getByLabelText('新增根類別'))
    expect(addChild).toHaveBeenCalledWith(null)
  })

  it('loading 顯示 skeleton', () => {
    renderTree({ ...baseResult, loading: true, tree: [] })
    expect(screen.queryByText('產品功能')).not.toBeInTheDocument()
  })

  it('空狀態顯示「尚無分類」', () => {
    renderTree({ ...baseResult, tree: [] })
    expect(screen.getByText('尚無分類')).toBeInTheDocument()
  })
})
