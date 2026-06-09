import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import { AdminRoute } from '@/routes/AdminRoute'
import { AuthProvider } from '@/routes/AuthProvider'
import { ROUTE_PATHS } from '@/routes/paths'
import { AppShell } from '@/components/AppShell'
import { Skeleton } from '@/components/ui/skeleton'
// Login / AgentSelect 為登入流程必要頁，保留 eager import 確保即時可用
import { LoginPage } from '@/features/auth/LoginPage'
import { AgentSelectPage } from '@/features/agents/AgentSelectPage'

// 業務頁面 code-split，降低初始 bundle 體積
const AgentSettingsPage = lazy(() =>
  import('@/features/agents/AgentSettingsPage').then((m) => ({ default: m.AgentSettingsPage })),
)
const DashboardPage = lazy(() =>
  import('@/features/dashboard/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const KnowledgePage = lazy(() =>
  import('@/features/knowledge/KnowledgePage').then((m) => ({ default: m.KnowledgePage })),
)
const SyncPage = lazy(() =>
  import('@/features/sync/SyncPage').then((m) => ({ default: m.SyncPage })),
)
const ImportExportPage = lazy(() =>
  import('@/features/import-export/ImportExportPage').then((m) => ({ default: m.ImportExportPage })),
)
const AuditPage = lazy(() =>
  import('@/features/audit/AuditPage').then((m) => ({ default: m.AuditPage })),
)
const TestChatPage = lazy(() =>
  import('@/features/chat/TestChatPage').then((m) => ({ default: m.TestChatPage })),
)
const UserManagementPage = lazy(() =>
  import('@/features/users/UserManagementPage').then((m) => ({ default: m.UserManagementPage })),
)

function PageFallback() {
  return (
    <div className="p-8 space-y-3">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-64" />
    </div>
  )
}

export function App() {
  return (
    <AuthProvider>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path={ROUTE_PATHS.login} element={<LoginPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path={ROUTE_PATHS.agents} element={<AgentSelectPage />} />
            <Route element={<AdminRoute />}>
              <Route path={ROUTE_PATHS.adminUsers} element={<UserManagementPage />} />
            </Route>
            <Route path="/agents/:id" element={<AppShell />}>
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="knowledge" element={<KnowledgePage />} />
              <Route path="sync" element={<SyncPage />} />
              <Route path="import-export" element={<ImportExportPage />} />
              <Route path="test-chat" element={<TestChatPage />} />
              <Route path="audit" element={<AuditPage />} />
              <Route element={<AdminRoute />}>
                <Route path="settings" element={<AgentSettingsPage />} />
              </Route>
            </Route>
          </Route>
          <Route path="*" element={<Navigate to={ROUTE_PATHS.agents} replace />} />
        </Routes>
      </Suspense>
      <Toaster richColors position="bottom-right" />
    </AuthProvider>
  )
}
