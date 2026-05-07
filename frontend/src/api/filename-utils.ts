/**
 * 從 Content-Disposition header 解析檔名。
 * 支援 RFC 5987 格式（filename*=UTF-8''...）和簡單格式（filename="..."）。
 */
export function extractFilenameFromHeader(
  header: string | undefined,
  fallback: string
): string {
  if (!header) return fallback
  // RFC 5987: filename*=UTF-8''percent-encoded-filename
  // [^;\s]+ 同時排除分號和空白，避免尾部空白問題
  const rfcMatch = header.match(/filename\*=UTF-8''([^;\s]+)/i)
  if (rfcMatch) {
    try { return decodeURIComponent(rfcMatch[1]) } catch { /* fall */ }
  }
  // Simple: filename="..."
  const simpleMatch = header.match(/filename="([^"]+)"/)
  if (simpleMatch) return simpleMatch[1]
  return fallback
}
