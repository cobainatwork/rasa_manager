import { describe, it, expect } from 'vitest'
import { cn } from './utils'

describe('cn (className merger)', () => {
  it('合併多個 class 名', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('條件 class（false 過濾）', () => {
    const flag: boolean = false
    expect(cn('foo', flag && 'bar', 'baz')).toBe('foo baz')
  })

  it('衝突的 tailwind class 後者覆蓋前者', () => {
    expect(cn('px-2 px-4')).toBe('px-4')
  })

  it('undefined / null 忽略', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar')
  })
})
