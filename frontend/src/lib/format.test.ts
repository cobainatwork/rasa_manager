import { describe, it, expect } from 'vitest'
import { formatDate, formatBytes, relativeTime } from './format'

describe('formatDate', () => {
  it('null 回傳 dash', () => expect(formatDate(null)).toBe('—'))
  it('ISO 字串轉本地時間', () => expect(formatDate('2026-04-30T14:23:00Z')).toMatch(/2026/))
})

describe('formatBytes', () => {
  it('0 bytes', () => expect(formatBytes(0)).toBe('0 B'))
  it('1024 bytes → 1 KB', () => expect(formatBytes(1024)).toBe('1 KB'))
  it('1MB', () => expect(formatBytes(1048576)).toBe('1 MB'))
  // I15 guards
  it('負值回傳 dash', () => expect(formatBytes(-1)).toBe('—'))
  it('NaN 回傳 dash', () => expect(formatBytes(NaN)).toBe('—'))
  it('Infinity 回傳 dash', () => expect(formatBytes(Infinity)).toBe('—'))
  it('TB 量級正常顯示', () => expect(formatBytes(1024 ** 4)).toBe('1 TB'))
  it('超過 PB 量級 clamp 至 PB', () => expect(formatBytes(1024 ** 6)).toMatch(/PB$/))
})

describe('relativeTime', () => {
  it('剛才（< 1 分鐘）', () => {
    const now = new Date()
    expect(relativeTime(now.toISOString())).toBe('剛才')
  })
  it('幾分鐘前', () => {
    const past = new Date(Date.now() - 5 * 60 * 1000).toISOString()
    expect(relativeTime(past)).toBe('5 分鐘前')
  })
  it('幾小時前', () => {
    const past = new Date(Date.now() - 3 * 3600 * 1000).toISOString()
    expect(relativeTime(past)).toBe('3 小時前')
  })
  it('幾天前', () => {
    const past = new Date(Date.now() - 2 * 86400 * 1000).toISOString()
    expect(relativeTime(past)).toBe('2 天前')
  })
  it('null 回傳 dash', () => expect(relativeTime(null)).toBe('—'))
})
