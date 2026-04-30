import { describe, it, expect } from 'vitest'
import { computeDiff, type DiffEntry } from './diff'

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
  it('陣列以 JSON 比對', () => expect(computeDiff({ tags: ['a', 'b'] }, { tags: ['a', 'c'] })).toHaveLength(1))
})
