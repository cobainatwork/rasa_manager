import { describe, it, expect } from 'vitest'
import { FAQ_STATUS_LABEL, FAQ_STATUS_BADGE_CLASS } from './faqStatus'
import type { Faq } from '@/api/types'

const ALL_STATUSES: Faq['status'][] = ['draft', 'pending', 'approved', 'rejected', 'synced']

describe('FAQ_STATUS_LABEL', () => {
  it('所有 status 均有對應中文標籤', () => {
    ALL_STATUSES.forEach((s) => {
      expect(FAQ_STATUS_LABEL[s]).toBeTruthy()
    })
  })

  it('各標籤值正確', () => {
    expect(FAQ_STATUS_LABEL.draft).toBe('草稿')
    expect(FAQ_STATUS_LABEL.pending).toBe('待審核')
    expect(FAQ_STATUS_LABEL.approved).toBe('已核准')
    expect(FAQ_STATUS_LABEL.rejected).toBe('已退回')
    expect(FAQ_STATUS_LABEL.synced).toBe('已同步')
  })
})

describe('FAQ_STATUS_BADGE_CLASS', () => {
  it('所有 status 均有對應 badge class', () => {
    ALL_STATUSES.forEach((s) => {
      expect(FAQ_STATUS_BADGE_CLASS[s]).toBeTruthy()
    })
  })

  it('badge class 包含背景色與文字色', () => {
    ALL_STATUSES.forEach((s) => {
      const cls = FAQ_STATUS_BADGE_CLASS[s]
      expect(cls).toMatch(/bg-/)
      expect(cls).toMatch(/text-/)
    })
  })
})
