import { describe, it, expect } from 'vitest'
import { cn, formatDate, STATUS_LABELS, ACTION_LABELS } from './utils'

describe('cn', () => {
  it('單一 class 原樣回傳', () => {
    expect(cn('foo')).toBe('foo')
  })

  it('合併多個 class', () => {
    expect(cn('a', 'b', 'c')).toBe('a b c')
  })

  it('忽略 falsy 值', () => {
    const flag = false
    expect(cn('a', flag && 'b', undefined, null, 'c')).toBe('a c')
  })

  it('tailwind-merge 去除衝突 class', () => {
    // twMerge 會讓後者覆蓋前者
    const result = cn('text-red-500', 'text-blue-500')
    expect(result).toBe('text-blue-500')
  })
})

describe('formatDate', () => {
  it('null 回傳 -', () => {
    expect(formatDate(null)).toBe('-')
  })

  it('undefined 回傳 -', () => {
    expect(formatDate(undefined)).toBe('-')
  })

  it('空字串回傳 -', () => {
    expect(formatDate('')).toBe('-')
  })

  it('有效 ISO 字串回傳可讀日期', () => {
    const result = formatDate('2024-06-15T08:30:00Z')
    expect(typeof result).toBe('string')
    expect(result.length).toBeGreaterThan(0)
    expect(result).not.toBe('-')
  })
})

describe('STATUS_LABELS', () => {
  const expectedStatuses = ['draft', 'pending', 'approved', 'rejected', 'synced']

  it.each(expectedStatuses)('%s 有對應標籤', (status) => {
    expect(STATUS_LABELS[status]).toBeDefined()
    expect(typeof STATUS_LABELS[status]).toBe('string')
    expect(STATUS_LABELS[status].length).toBeGreaterThan(0)
  })

  it('draft 標籤為「草稿」', () => {
    expect(STATUS_LABELS.draft).toBe('草稿')
  })

  it('approved 標籤為「已核准」', () => {
    expect(STATUS_LABELS.approved).toBe('已核准')
  })
})

describe('ACTION_LABELS', () => {
  const expectedActions = ['create', 'update', 'delete', 'approve', 'reject', 'export', 'import']

  it.each(expectedActions)('%s 有對應標籤', (action) => {
    expect(ACTION_LABELS[action]).toBeDefined()
    expect(typeof ACTION_LABELS[action]).toBe('string')
  })

  it('import 標籤為「匯入」', () => {
    expect(ACTION_LABELS.import).toBe('匯入')
  })

  it('export 標籤為「匯出」', () => {
    expect(ACTION_LABELS.export).toBe('匯出')
  })
})
