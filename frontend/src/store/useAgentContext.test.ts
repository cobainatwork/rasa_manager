import { describe, it, expect, beforeEach } from 'vitest'
import { useAgentContext } from './useAgentContext'
import type { Agent } from '@/api/types'

const FAKE_AGENT: Agent = {
  id: 'ag-1',
  name: '測試 Agent',
  qdrant_collection: 'agent_ag-1',
  txt_output_path: '/opt/test',
  rasa_rest_url: null,
  ingest_script_path: null,
  embedding_provider: 'openai',
  embedding_model: 'text-embedding-3-small',
  created_at: null,
}

beforeEach(() => {
  localStorage.clear()
  useAgentContext.setState({ current: null })
})

describe('useAgentContext', () => {
  it('初始 current 為 null', () => {
    expect(useAgentContext.getState().current).toBeNull()
  })

  it('setCurrent 更新 current', () => {
    useAgentContext.getState().setCurrent(FAKE_AGENT)
    expect(useAgentContext.getState().current).toEqual(FAKE_AGENT)
  })

  it('setCurrent(null) 清除 current', () => {
    useAgentContext.setState({ current: FAKE_AGENT })
    useAgentContext.getState().setCurrent(null)
    expect(useAgentContext.getState().current).toBeNull()
  })

  it('persist 至 localStorage（key: rasa-kb-current-agent）', () => {
    useAgentContext.getState().setCurrent(FAKE_AGENT)
    const raw = localStorage.getItem('rasa-kb-current-agent')
    expect(raw).not.toBeNull()
    const parsed = JSON.parse(raw!)
    expect(parsed.state.current).toEqual(FAKE_AGENT)
    expect(parsed.version).toBe(1)
  })
})
