import { describe, it, expect, vi } from 'vitest'
import { exportCategoryFaqs, importCategoryFaqs } from '../categories'
import { apiClient } from '../../client'

vi.mock('../../client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('../../request', () => ({
  unwrap: vi.fn((promise: Promise<unknown>) => promise.then((r) => (r as { data: { data: unknown } }).data.data)),
}))

const AGENT_ID = 'agent-uuid'
const CAT_ID = 'cat-uuid'

describe('exportCategoryFaqs', () => {
  it('calls GET /categories/{id}/export with blob responseType', async () => {
    const mockBlob = new Blob(['test'])
    // headers 必須存在（函式讀取 content-disposition），空物件代表無 header
    vi.mocked(apiClient.get).mockResolvedValue({ data: mockBlob, headers: {} })

    const result = await exportCategoryFaqs(AGENT_ID, CAT_ID)

    expect(apiClient.get).toHaveBeenCalledWith(
      `/api/v1/agents/${AGENT_ID}/categories/${CAT_ID}/export`,
      { responseType: 'blob' }
    )
    // 函式回傳 { blob, filename }，而非直接回傳 blob
    expect(result.blob).toBe(mockBlob)
    expect(result.filename).toBe('category_export.xlsx') // content-disposition 為空時的預設值
  })
})

describe('importCategoryFaqs', () => {
  it('calls POST /categories/{id}/import with mode=append by default', async () => {
    const mockResult = { success: true, data: { imported: 1, skipped: 0, errors: [] } }
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResult })

    const file = new File(['col'], 'test.xlsx')
    const result = await importCategoryFaqs(AGENT_ID, CAT_ID, file)

    expect(apiClient.post).toHaveBeenCalledWith(
      `/api/v1/agents/${AGENT_ID}/categories/${CAT_ID}/import?mode=append`,
      expect.any(FormData)
    )
    expect(result).toEqual({ imported: 1, skipped: 0, errors: [] })
  })

  it('calls POST /categories/{id}/import with mode=replace when specified', async () => {
    const mockResult = { success: true, data: { imported: 2, skipped: 0, errors: [] } }
    vi.mocked(apiClient.post).mockResolvedValue({ data: mockResult })

    const file = new File(['col'], 'test.xlsx')
    const result = await importCategoryFaqs(AGENT_ID, CAT_ID, file, 'replace')

    expect(apiClient.post).toHaveBeenCalledWith(
      `/api/v1/agents/${AGENT_ID}/categories/${CAT_ID}/import?mode=replace`,
      expect.any(FormData)
    )
    expect(result).toEqual({ imported: 2, skipped: 0, errors: [] })
  })
})
