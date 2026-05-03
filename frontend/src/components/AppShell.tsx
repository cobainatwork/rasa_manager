import { Outlet } from 'react-router-dom'
import { Topbar } from './Topbar'
import { Sidebar } from './Sidebar'
import { ErrorBoundary } from './ErrorBoundary'
import { KeyboardShortcuts } from './KeyboardShortcuts'

export function AppShell() {
  return (
    <div className="h-screen bg-canvas flex flex-col">
      <Topbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
      <KeyboardShortcuts />
    </div>
  )
}
