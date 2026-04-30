import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import { AdminRoute } from '@/routes/AdminRoute'
import { AppShell } from '@/components/AppShell'
import { LoginPage } from '@/features/auth/LoginPage'
import { AgentSelectPage } from '@/features/agents/AgentSelectPage'
import { AgentSettingsPage } from '@/features/agents/AgentSettingsPage'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { KnowledgePage } from '@/features/knowledge/KnowledgePage'
import { SyncPage } from '@/features/sync/SyncPage'
import { ImportExportPage } from '@/features/import-export/ImportExportPage'
import { AuditPage } from '@/features/audit/AuditPage'
import { TestChatPage } from '@/features/chat/TestChatPage'
import { UserManagementPage } from '@/features/users/UserManagementPage'

export function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/agents" element={<AgentSelectPage />} />
          <Route element={<AdminRoute />}>
            <Route path="/admin/users" element={<UserManagementPage />} />
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
        <Route path="*" element={<Navigate to="/agents" replace />} />
      </Routes>
      <Toaster richColors position="bottom-right" />
    </>
  )
}
