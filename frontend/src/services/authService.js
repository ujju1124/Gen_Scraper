/**
 * Authentication Service
 * Handles all auth-related API calls
 */
import api from './api'

/**
 * Register a new user
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<Object>} Registration response
 */
export const register = async (email, password) => {
  const response = await api.post('/api/v1/auth/register', { email, password })
  return response.data
}

/**
 * Login user
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<Object>} Login response
 */
export const login = async (email, password) => {
  const response = await api.post('/api/v1/auth/login', { email, password })
  return response.data
}

/**
 * Logout user
 * @returns {Promise<Object>} Logout response
 */
export const logout = async () => {
  const response = await api.post('/api/v1/auth/logout')
  return response.data
}

/**
 * Get current user information
 * @returns {Promise<Object>} User object with id, email, role
 */
export const getCurrentUser = async () => {
  const response = await api.get('/api/v1/auth/me')
  return response.data
}

/**
 * Refresh access token
 * @returns {Promise<Object>} Refresh response
 */
export const refreshToken = async () => {
  const response = await api.post('/api/v1/auth/refresh')
  return response.data
}