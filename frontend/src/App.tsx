import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import { AdminRoute } from '@/routes/AdminRoute'
import { AppShell } from '@/components/AppShell'
import { LoginPage } from '@/features/auth/LoginPage'

const Placeholder = ({ name }: { name: string }) => (
  <div className="p-8">
    <h1 className="text-2xl font-bold">{name}</h1>
    <p className="text-text-muted mt-2">此頁面尚未實作（Phase 進行中）</p>
  </div>
)

export function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/agents" element={<Placeholder name="Agent 選擇" />} />
          <Route element={<AdminRoute />}>
            <Route path="/admin/users" element={<Placeholder name="使用者管理" />} />
          </Route>
          <Route path="/agents/:id" element={<AppShell />}>
            <Route path="dashboard" element={<Placeholder name="儀表板" />} />
            <Route path="knowledge" element={<Placeholder name="知識庫" />} />
            <Route path="sync" element={<Placeholder name="同步" />} />
            <Route path="import-export" element={<Placeholder name="匯入匯出" />} />
            <Route path="test-chat" element={<Placeholder name="對話測試" />} />
            <Route path="audit" element={<Placeholder name="稽核日誌" />} />
            <Route element={<AdminRoute />}>
              <Route path="settings" element={<Placeholder name="Agent 設定" />} />
            </Route>
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/agents" replace />} />
      </Routes>
      <Toaster richColors position="bottom-right" />
    </>
  )
}
