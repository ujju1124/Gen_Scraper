/**
 * AuthGuard Component
 * Protects routes that require authentication
 * Redirects unauthenticated users to /login
 */
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

/**
 * AuthGuard wraps protected routes
 * Stores original path for post-login redirect
 */
export function AuthGuard({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

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

  // Redirect to login if not authenticated
  // Store original path in state for post-login redirect
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  // User is authenticated, render children
  return children
}