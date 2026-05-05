import { useLayoutEffect, useRef } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Topbar } from './Topbar'
import { Sidebar } from './Sidebar'
import { ErrorBoundary } from './ErrorBoundary'
import { KeyboardShortcuts } from './KeyboardShortcuts'

export function AppShell() {
  const mainRef = useRef<HTMLElement>(null)
  const { pathname } = useLocation()

  // useLayoutEffect 在瀏覽器 paint 前同步執行，確保路由切換時捲動已歸零。
  // 同時重置 window，避免 Radix ScrollArea scrollIntoView 偶爾捲動到頁面根層。
  useLayoutEffect(() => {
    mainRef.current?.scrollTo(0, 0)
    window.scrollTo(0, 0)
  }, [pathname])

  return (
    <div className="h-screen bg-canvas flex flex-col">
      <Topbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main ref={mainRef} className="flex-1 overflow-auto">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
      <KeyboardShortcuts />
    </div>
  )
}
