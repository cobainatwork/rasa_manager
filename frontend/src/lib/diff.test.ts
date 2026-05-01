import { describe, it, expect } from 'vitest'
import { computeDiff, deepEqual, type DiffEntry } from './diff'

describe('computeDiff', () => {
  it('回傳變更欄位的 before/after', () => {
    const result = computeDiff(
      { question: '舊問題', answer: '舊答案', category_id: 'a' },
      { question: '新問題', answer: '舊答案', category_id: 'a' }
    )
    expect(result).toEqual<DiffEntry[]>([
      { field: 'question', before: '舊問題', after: '新問題' },
    ])
  })
  it('多個欄位變更', () => {
    expect(computeDiff({ question: 'q1', answer: 'a1' }, { question: 'q2', answer: 'a2' })).toHaveLength(2)
  })
  it('完全相同回傳空陣列', () => expect(computeDiff({ a: 1 }, { a: 1 })).toEqual([]))
  it('陣列比對（內容相同視為相等）', () => {
    expect(computeDiff({ tags: ['a', 'b'] }, { tags: ['a', 'b'] })).toEqual([])
    expect(computeDiff({ tags: ['a', 'b'] }, { tags: ['a', 'c'] })).toHaveLength(1)
  })
})

describe('deepEqual（I16）', () => {
  it('物件 key 順序不同視為相等', () => {
    expect(deepEqual({ a: 1, b: 2 }, { b: 2, a: 1 })).toBe(true)
  })

  it('undefined value 視為相等於缺漏 key', () => {
    expect(deepEqual({ a: undefined }, {})).toBe(true)
    expect(deepEqual({ a: 1, b: undefined }, { a: 1 })).toBe(true)
  })

  it('巢狀物件深層比對', () => {
    expect(deepEqual({ a: { b: { c: [1, 2] } } }, { a: { b: { c: [1, 2] } } })).toBe(true)
    expect(deepEqual({ a: { b: 1 } }, { a: { b: 2 } })).toBe(false)
  })

  it('null 與 undefined 區分', () => {
    expect(deepEqual(null, undefined)).toBe(false)
    expect(deepEqual({ a: null }, { a: undefined })).toBe(false)
  })

  it('陣列順序敏感', () => {
    expect(deepEqual([1, 2], [2, 1])).toBe(false)
  })

  it('陣列 vs 物件不同型別', () => {
    expect(deepEqual([], {})).toBe(false)
  })

  it('原始型別比對', () => {
    expect(deepEqual(1, 1)).toBe(true)
    expect(deepEqual('a', 'a')).toBe(true)
    expect(deepEqual(NaN, NaN)).toBe(true)
    expect(deepEqual(0, -0)).toBe(false)
  })
})
