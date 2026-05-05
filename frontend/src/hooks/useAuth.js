/**
 * useAuth Hook
 * Provides access to authentication context
 */
import { useContext } from 'react'
import { AuthContext } from '../contexts/AuthContext'

/**
 * Hook to access authentication state and functions
 * @returns {import('../contexts/AuthContext').AuthContextType}
 */
export function useAuth() {
  const context = useContext(AuthContext)
  
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  
  return context
}