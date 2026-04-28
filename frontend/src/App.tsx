import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from '@/routes/ProtectedRoute'
import { ToastContainer } from '@/components/ui/ToastContainer'
import { DialogContainer } from '@/components/ui/DialogContainer'
import { Login } from '@/pages/Login'
import { AgentSelect } from '@/pages/AgentSelect'
import { DashboardLayout } from '@/pages/DashboardLayout'
import { Dashboard } from '@/pages/Dashboard'
import { Categories } from '@/pages/Categories'
import { KnowledgeBase } from '@/pages/KnowledgeBase'
import { FaqDetail } from '@/pages/FaqDetail'
import { SyncPage } from '@/pages/SyncPage'
import { TestChat } from '@/pages/TestChat'
import { AuditLog } from '@/pages/AuditLog'
import { ImportExport } from '@/pages/ImportExport'
import { AgentSettings } from '@/pages/AgentSettings'
import { UserManagement } from '@/pages/UserManagement'

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route
          path="/agents"
          element={
            <ProtectedRoute>
              <AgentSelect />
            </ProtectedRoute>
          }
        />

        <Route
          path="/admin/users"
          element={
            <ProtectedRoute requireSuperadmin>
              <UserManagement />
            </ProtectedRoute>
          }
        />

        <Route
          path="/agents/:id"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="categories" element={<Categories />} />
          <Route path="faqs" element={<KnowledgeBase />} />
          <Route path="faqs/:faq_id" element={<FaqDetail />} />
          <Route path="sync" element={<SyncPage />} />
          <Route path="chat" element={<TestChat />} />
          <Route path="import-export" element={<ImportExport />} />
          <Route path="audit" element={<AuditLog />} />
          <Route path="settings" element={<AgentSettings />} />
        </Route>

        <Route path="/" element={<Navigate to="/agents" replace />} />
        <Route path="*" element={<Navigate to="/agents" replace />} />
      </Routes>

      <ToastContainer />
      <DialogContainer />
    </>
  )
}
