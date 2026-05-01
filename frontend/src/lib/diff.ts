export interface DiffEntry {
  field: string
  before: unknown
  after: unknown
}

/**
 * I16：以 type-aware 的 deepEqual 取代 JSON.stringify 比對，
 * 避免 key 順序差異或 undefined 欄位導致誤判。
 */
export function deepEqual(a: unknown, b: unknown): boolean {
  if (Object.is(a, b)) return true
  if (a === null || b === null) return false
  if (typeof a !== typeof b) return false
  if (typeof a !== 'object') return false

  // Array
  const aIsArr = Array.isArray(a)
  const bIsArr = Array.isArray(b)
  if (aIsArr !== bIsArr) return false
  if (aIsArr && bIsArr) {
    if (a.length !== b.length) return false
    for (let i = 0; i < a.length; i++) {
      if (!deepEqual(a[i], b[i])) return false
    }
    return true
  }

  // Plain object
  const ao = a as Record<string, unknown>
  const bo = b as Record<string, unknown>
  const keys = new Set([...Object.keys(ao), ...Object.keys(bo)])
  for (const k of keys) {
    if (!deepEqual(ao[k], bo[k])) return false
  }
  return true
}

export function computeDiff(
  prev: Record<string, unknown>,
  curr: Record<string, unknown>
): DiffEntry[] {
  const fields = new Set([...Object.keys(prev), ...Object.keys(curr)])
  const out: DiffEntry[] = []
  for (const field of fields) {
    const a = prev[field]
    const b = curr[field]
    if (!deepEqual(a, b)) {
      out.push({ field, before: a, after: b })
    }
  }
  return out
}
