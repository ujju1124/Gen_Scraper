/**
 * Authentication Context
 * Manages user authentication state and provides auth functions
 * 
 * IMPORTANT: When refresh token expires (401 from /auth/refresh),
 * this context redirects to /login. The api.js only rejects the promise.
 */
import { createContext, useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import * as authService from '../services/authService'

/**
 * @typedef {Object} User
 * @property {number} id
 * @property {string} email
 * @property {'user'|'admin'} role
 */

/**
 * @typedef {Object} AuthContextType
 * @property {User|null} user
 * @property {boolean} loading
 * @property {function(string, string): Promise<void>} login
 * @property {function(string, string): Promise<void>} register
 * @property {function(): Promise<void>} logout
 * @property {function(): Promise<void>} refreshUser
 */

export const AuthContext = createContext(null)

/**
 * AuthProvider component
 * Wraps the app and provides authentication state
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  /**
   * Fetch current user information
   * Called on app initialization and after login
   */
  const refreshUser = useCallback(async () => {
    try {
      const userData = await authService.getCurrentUser()
      setUser(userData)
    } catch (error) {
      // If 401, user is not authenticated
      if (error.status === 401) {
        setUser(null)
      }
      // Don't throw error, just set user to null
      console.log('Auth check failed:', error.message || error)
    }
  }, [])

  /**
   * Initialize auth state on mount
   * Attempts to fetch current user if cookies exist
   */
  useEffect(() => {
    const initAuth = async () => {
      try {
        await refreshUser()
      } catch (error) {
        // User not authenticated, that's okay
        console.log('Init auth failed:', error)
        setUser(null)
      } finally {
        setLoading(false)
      }
    }

    initAuth()
  }, [refreshUser])

  /**
   * Login user
   * @param {string} email
   * @param {string} password
   */
  const login = async (email, password) => {
    await authService.login(email, password)
    await refreshUser()
  }

  /**
   * Register new user
   * @param {string} email
   * @param {string} password
   */
  const register = async (email, password) => {
    await authService.register(email, password)
    // Don't auto-login after registration
    // User will be redirected to login page
  }

  /**
   * Logout user
   * Clears user state and redirects to login
   */
  const logout = async () => {
    try {
      await authService.logout()
    } catch (error) {
      // Even if logout fails, clear state and redirect
      console.error('Logout error:', error)
    } finally {
      setUser(null)
      navigate('/login')
    }
  }

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}