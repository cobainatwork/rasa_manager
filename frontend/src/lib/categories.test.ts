import { describe, it, expect } from 'vitest'
import { buildCategoryTree, flattenCategories, buildCategoryPath } from './categories'

const sample = [
  { id: '1', name: '產品功能', parent_id: null },
  { id: '2', name: '帳號', parent_id: '1' },
  { id: '3', name: '密碼', parent_id: '2' },
  { id: '4', name: '計費', parent_id: null },
]

describe('buildCategoryTree', () => {
  it('將平面陣列轉為巢狀樹', () => {
    const tree = buildCategoryTree(sample)
    expect(tree).toHaveLength(2)
    expect(tree[0].id).toBe('1')
    expect(tree[0].children[0].id).toBe('2')
    expect(tree[0].children[0].children[0].id).toBe('3')
  })
  it('空陣列回傳空陣列', () => expect(buildCategoryTree([])).toEqual([]))
  it('parent_id 找不到視為 root', () => {
    const tree = buildCategoryTree([{ id: '1', name: 'orphan', parent_id: 'missing' }])
    expect(tree).toHaveLength(1)
  })
})

describe('flattenCategories', () => {
  it('巢狀樹展平為 path', () => {
    const tree = buildCategoryTree(sample)
    expect(flattenCategories(tree)).toEqual([
      { id: '1', path: '產品功能' },
      { id: '2', path: '產品功能/帳號' },
      { id: '3', path: '產品功能/帳號/密碼' },
      { id: '4', path: '計費' },
    ])
  })
})

describe('buildCategoryPath', () => {
  it('依 id 反向追溯祖先', () => {
    expect(buildCategoryPath('3', sample)).toBe('產品功能/帳號/密碼')
    expect(buildCategoryPath('1', sample)).toBe('產品功能')
    expect(buildCategoryPath('missing', sample)).toBe('')
  })
})
