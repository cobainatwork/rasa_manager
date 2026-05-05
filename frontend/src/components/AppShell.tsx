import { useEffect, useRef } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Topbar } from './Topbar'
import { Sidebar } from './Sidebar'
import { ErrorBoundary } from './ErrorBoundary'
import { KeyboardShortcuts } from './KeyboardShortcuts'

export function AppShell() {
  const mainRef = useRef<HTMLElement>(null)
  const { pathname } = useLocation()

  // 路由切換時將 main 捲動位置歸零，避免從對話測試等頁面切換後頂部元素被遮蔽
  useEffect(() => {
    mainRef.current?.scrollTo(0, 0)
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
