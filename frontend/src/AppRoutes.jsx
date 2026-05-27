/**
 * Application Routes
 * Defines all routes with guards
 */
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthGuard } from './components/guards/AuthGuard'
import { RoleGuard } from './components/guards/RoleGuard'
import { Layout } from './components/layout/Layout'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { DashboardPage } from './pages/DashboardPage'
import { JobStatusPage } from './pages/JobStatusPage'
import { JobResultsPage } from './pages/JobResultsPage'
import { ResultDetailPage } from './pages/ResultDetailPage'
import { AdminPage } from './pages/AdminPage'
import { ValidatedResultsPage } from './pages/ValidatedResultsPage'
import { SourceManagerPage } from './pages/SourceManagerPage'
import { UserManagementPage } from './pages/UserManagementPage'
import { MonitoringDashboard } from './pages/MonitoringDashboard'
import HealingDashboard from './pages/HealingDashboard'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/dashboard"
        element={
          <AuthGuard>
            <Layout>
              <DashboardPage />
            </Layout>
          </AuthGuard>
        }
      />
      <Route
        path="/jobs/:id"
        element={
          <AuthGuard>
            <Layout>
              <JobStatusPage />
            </Layout>
          </AuthGuard>
        }
      />
      <Route
        path="/jobs/:id/results"
        element={
          <AuthGuard>
            <Layout>
              <JobResultsPage />
            </Layout>
          </AuthGuard>
        }
      />
      <Route
        path="/results/:id"
        element={
          <AuthGuard>
            <Layout>
              <ResultDetailPage />
            </Layout>
          </AuthGuard>
        }
      />
      <Route
        path="/admin"
        element={
          <AuthGuard>
            <RoleGuard>
              <Layout>
                <AdminPage />
              </Layout>
            </RoleGuard>
          </AuthGuard>
        }
      />
      <Route
        path="/validated"
        element={
          <AuthGuard>
            <RoleGuard>
              <Layout>
                <ValidatedResultsPage />
              </Layout>
            </RoleGuard>
          </AuthGuard>
        }
      />
      <Route
        path="/admin/sources"
        element={
          <AuthGuard>
            <RoleGuard>
              <Layout>
                <SourceManagerPage />
              </Layout>
            </RoleGuard>
          </AuthGuard>
        }
      />
      <Route
        path="/admin/users"
        element={
          <AuthGuard>
            <RoleGuard>
              <Layout>
                <UserManagementPage />
              </Layout>
            </RoleGuard>
          </AuthGuard>
        }
      />
      <Route
        path="/admin/monitoring"
        element={
          <AuthGuard>
            <RoleGuard>
              <Layout>
                <MonitoringDashboard />
              </Layout>
            </RoleGuard>
          </AuthGuard>
        }
      />
      <Route
        path="/admin/healing"
        element={
          <AuthGuard>
            <RoleGuard>
              <Layout>
                <HealingDashboard />
              </Layout>
            </RoleGuard>
          </AuthGuard>
        }
      />
    </Routes>
  )
}