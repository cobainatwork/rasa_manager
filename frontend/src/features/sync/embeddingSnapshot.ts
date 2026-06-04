/**
 * 將同步歷史紀錄的 embedding 快照欄位格式化為顯示字串。
 *
 * 範例：
 *   formatEmbeddingSnapshot('openai', 'text-embedding-3-small')
 *     // => 'OpenAI · text-embedding-3-small'
 *   formatEmbeddingSnapshot('local', 'bge-m3-q8_0')
 *     // => 'Local · bge-m3-q8_0'
 *   formatEmbeddingSnapshot(null, 'x') // => '—'
 *
 * 任一欄位為 null / undefined（migration 006 之前的紀錄）一律顯示 em dash「—」。
 */
export function formatEmbeddingSnapshot(
  provider: string | null | undefined,
  model: string | null | undefined,
): string {
  if (!provider || !model) return '—'
  const providerLabel =
    provider === 'openai' ? 'OpenAI' : provider === 'local' ? 'Local' : provider
  return `${providerLabel} · ${model}`
}
