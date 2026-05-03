// N8：locale 常數集中
const LOCALE = 'zh-TW'
const DASH = '—'

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return DASH
  return new Date(iso).toLocaleString(LOCALE, {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

/**
 * I15：保護極大值與 NaN／負值。
 */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return DASH
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
  const rawIndex = Math.floor(Math.log(bytes) / Math.log(1024))
  const i = Math.min(Math.max(rawIndex, 0), units.length - 1)
  return `${(bytes / Math.pow(1024, i)).toFixed(0)} ${units[i]}`
}

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return DASH
  const diff = Date.now() - new Date(iso).getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return '剛才'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min} 分鐘前`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr} 小時前`
  const day = Math.floor(hr / 24)
  return `${day} 天前`
}
