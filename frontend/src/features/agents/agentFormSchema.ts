import { z } from 'zod'

/**
 * Agent 表單共用 Zod schema：CreateAgentInlinePanel 與 AgentSettingsPage 共用。
 *
 * 處理 `null` vs `''` 的設計：
 *   後端把 `rasa_rest_url` / `ingest_script_path` 視為 nullable（清除）；
 *   表單 input 永遠是字串，用 transform 把空字串/空白統一轉為 null，
 *   schema 層級就把「空 = 清除」與「有值需符合 URL 前綴」對齊好。
 */

const optionalNullableString = z
  .string()
  .nullish()
  .transform((v) => {
    if (v == null) return null
    const trimmed = v.trim()
    return trimmed === '' ? null : trimmed
  })

const rasaUrl = optionalNullableString.refine(
  (v) => !v || v.startsWith('http://') || v.startsWith('https://'),
  { message: 'Webhook URL 必須以 http:// 或 https:// 開頭' },
)

const qdrantCollection = z
  .string()
  .min(1, 'Collection 名稱必填')
  .max(255, '最多 255 字')
  .regex(
    /^[a-zA-Z_][a-zA-Z0-9_-]*$/,
    'Collection 名稱只能含英文字母、數字、底線與連字號，且須以英文字母或底線開頭',
  )

const embeddingProvider = z.enum(['openai', 'local'])
const embeddingModel = z.string().min(1, 'Embedding model 名稱必填').max(100)

/** 建立 Agent 時的 schema — embedding 在後端 default openai，前端 panel 直接帶 default。 */
export const agentCreateSchema = z.object({
  name: z.string().min(1, '必填').max(100, '最多 100 字'),
  qdrant_collection: qdrantCollection,
  txt_output_path: z.string().min(1, '必填').max(255, '最多 255 字'),
  rasa_rest_url: rasaUrl,
  ingest_script_path: optionalNullableString,
})
export type AgentCreateFormData = z.infer<typeof agentCreateSchema>

/** 編輯 Agent 時的 schema — 額外編輯 embedding 設定。 */
export const agentEditSchema = agentCreateSchema.extend({
  embedding_provider: embeddingProvider,
  embedding_model: embeddingModel,
})
export type AgentEditFormData = z.infer<typeof agentEditSchema>
