/**
 * API Client with Axios
 * Implements failedQueue pattern to prevent race conditions during token refresh
 */
import axios from 'axios'

// Get API base URL from environment variable
// Empty string means use relative URLs (for Vite proxy)
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

// Create Axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Include httpOnly cookies
  headers: {
    'Content-Type': 'application/json',
  },
})

// FailedQueue pattern from Addendum B20
// Prevents race conditions when multiple 401 responses arrive simultaneously
let isRefreshing = false
let failedQueue = [] // requests that failed while a refresh was in progress

/**
 * Process all queued requests after refresh completes
 * @param {Error|null} error - Error if refresh failed, null if successful
 */
function processQueue(error) {
  failedQueue.forEach(prom => error ? prom.reject(error) : prom.resolve())
  failedQueue = []
}

// Request interceptor: add credentials and request ID
api.interceptors.request.use(
  (config) => {
    // Add request ID for tracing
    config.headers['X-Request-ID'] = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor: handle 401 errors with token refresh
api.interceptors.response.use(
  (response) => {
    // Success response, return as-is
    return response
  },
  async (error) => {
    const originalRequest = error.config

    // Handle 401 Unauthorized errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Another refresh is already in-flight — queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(() => api(originalRequest)).catch(err => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // Attempt to refresh the access token
        await api.post('/api/v1/auth/refresh/')
        
        // Refresh succeeded, process queued requests
        processQueue(null)
        isRefreshing = false
        
        // Retry the original request
        return api(originalRequest)
      } catch (refreshError) {
        // Refresh failed, reject all queued requests
        processQueue(refreshError)
        isRefreshing = false
        
        // Redirect to login (handled by auth context)
        return Promise.reject(refreshError)
      }
    }

    // Transform error into user-friendly message
    const transformedError = transformError(error)
    return Promise.reject(transformedError)
  }
)

/**
 * Transform API errors into user-friendly messages
 * @param {Error} error - Axios error object
 * @returns {Object} Transformed error with user-friendly message
 */
function transformError(error) {
  if (!error.response) {
    // Network error
    return {
      message: 'Network error. Please check your connection.',
      status: 0,
      detail: error.message,
    }
  }

  const { status, data } = error.response

  switch (status) {
    case 400:
      return {
        message: data.detail || 'Invalid request. Please check your input.',
        status,
        detail: data.detail,
      }
    case 401:
      return {
        message: 'Unauthorized. Please log in again.',
        status,
        detail: data.detail,
      }
    case 403:
      return {
        message: "You don't have permission to access this resource.",
        status,
        detail: data.detail,
      }
    case 429:
      return {
        message: 'Rate limit exceeded. Please wait before trying again.',
        status,
        detail: data.detail,
      }
    case 500:
      return {
        message: 'Server error. Please try again later.',
        status,
        detail: data.detail,
      }
    default:
      return {
        message: data.detail || 'An unexpected error occurred.',
        status,
        detail: data.detail,
      }
  }
}

export default api