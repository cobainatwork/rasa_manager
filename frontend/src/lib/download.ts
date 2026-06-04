/**
 * 觸發瀏覽器下載 Blob 檔案。
 *
 * WHY appendChild/remove：部分瀏覽器（Safari、舊版 Firefox）對未掛載至 DOM 的 <a>
 * 呼叫 .click() 不會觸發下載；掛載後點擊再移除可確保跨瀏覽器相容性。
 *
 * WHY 延遲 revoke：瀏覽器非同步處理下載，同步 revoke 會導致 URL 在下載前失效。
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
