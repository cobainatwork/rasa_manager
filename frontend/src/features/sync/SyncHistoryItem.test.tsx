import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SyncHistoryItem } from './SyncHistoryItem'
import { formatEmbeddingSnapshot } from './embeddingSnapshot'
import type { SyncLogHistoryItem } from '@/api/types'

const BASE: SyncLogHistoryItem = {
  id: 'sl1',
  status: 'completed',
  triggered_by_username: 'admin',
  started_at: '2026-01-01T00:00:00Z',
  finished_at: '2026-01-01T00:01:00Z',
  duration_sec: 60,
  items_count: 10,
  output_file: null,
  stdout: null,
  stderr: null,
}

describe('formatEmbeddingSnapshot', () => {
  it('openai provider 顯示「OpenAI · {model}」', () => {
    expect(formatEmbeddingSnapshot('openai', 'text-embedding-3-small')).toBe(
      'OpenAI · text-embedding-3-small',
    )
  })

  it('local provider 顯示「Local · {model}」', () => {
    expect(formatEmbeddingSnapshot('local', 'bge-m3-q8_0')).toBe('Local · bge-m3-q8_0')
  })

  it('provider 為 null 顯示 em dash', () => {
    expect(formatEmbeddingSnapshot(null, 'text-embedding-3-small')).toBe('—')
  })

  it('model 為 null 顯示 em dash', () => {
    expect(formatEmbeddingSnapshot('openai', null)).toBe('—')
  })

  it('兩者皆 undefined（舊紀錄）顯示 em dash', () => {
    expect(formatEmbeddingSnapshot(undefined, undefined)).toBe('—')
  })
})

describe('SyncHistoryItem - embedding snapshot column', () => {
  it('openai + model 渲染「OpenAI · {model}」', () => {
    const item: SyncLogHistoryItem = {
      ...BASE,
      embedding_provider: 'openai',
      embedding_model: 'text-embedding-3-small',
    }
    render(<ul><SyncHistoryItem item={item} /></ul>)
    expect(screen.getByTestId('embedding-snapshot').textContent).toBe(
      'OpenAI · text-embedding-3-small',
    )
  })

  it('local + model 渲染「Local · {model}」', () => {
    const item: SyncLogHistoryItem = {
      ...BASE,
      embedding_provider: 'local',
      embedding_model: 'bge-m3-q8_0',
    }
    render(<ul><SyncHistoryItem item={item} /></ul>)
    expect(screen.getByTestId('embedding-snapshot').textContent).toBe('Local · bge-m3-q8_0')
  })

  it('migration 006 之前的舊紀錄（兩欄位皆缺）顯示 em dash', () => {
    render(<ul><SyncHistoryItem item={BASE} /></ul>)
    expect(screen.getByTestId('embedding-snapshot').textContent).toBe('—')
  })
})
