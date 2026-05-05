/**
 * RoleGuard Component
 * Restricts routes to admin users only
 * Redirects non-admin users to /dashboard with error message
 */
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

/**
 * RoleGuard wraps admin-only routes
 * Checks user.role === 'admin'
 */
export function RoleGuard({ children }) {
  const { user, loading } = useAuth()

  // Show loading spinner while checking auth status
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          <p className="mt-4 text-sm text-slate-600">Loading...</p>
        </div>
      </div>
    )
  }

  // Redirect to dashboard if not admin
  // Error message will be shown via toast notification
  if (!user || user.role !== 'admin') {
    return <Navigate to="/dashboard" state={{ error: 'Admin access required' }} replace />
  }

  // User is admin, render children
  return children
}