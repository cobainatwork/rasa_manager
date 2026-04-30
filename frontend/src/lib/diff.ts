export interface DiffEntry {
  field: string
  before: unknown
  after: unknown
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
    if (JSON.stringify(a) !== JSON.stringify(b)) {
      out.push({ field, before: a, after: b })
    }
  }
  return out
}
