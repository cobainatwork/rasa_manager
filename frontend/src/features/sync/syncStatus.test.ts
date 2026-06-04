import { describe, it, expect } from 'vitest'
import { SYNC_STATUS_LABEL } from './syncStatus'
import type { SyncLog } from '@/api/types'

const ALL_STATUSES: SyncLog['status'][] = ['pending', 'running', 'completed', 'failed']

describe('SYNC_STATUS_LABEL', () => {
  it('所有 status 均有對應中文標籤', () => {
    ALL_STATUSES.forEach((s) => {
      expect(SYNC_STATUS_LABEL[s]).toBeTruthy()
    })
  })

  it('各標籤值正確', () => {
    expect(SYNC_STATUS_LABEL.pending).toBe('等待中')
    expect(SYNC_STATUS_LABEL.running).toBe('執行中')
    expect(SYNC_STATUS_LABEL.completed).toBe('完成')
    expect(SYNC_STATUS_LABEL.failed).toBe('失敗')
  })
})
