/**
 * Validated Results Service
 * API calls for accessing validated business data
 */
import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

/**
 * Get paginated validated results with filters
 */
export async function getValidatedResults(params = {}) {
  const response = await axios.get(`${API_BASE_URL}/validated/`, { params })
  return response.data
}

/**
 * Get a single validated result by ID
 */
export async function getValidatedResultById(id) {
  const response = await axios.get(`${API_BASE_URL}/validated/${id}`)
  return response.data
}

/**
 * Get validated results statistics
 */
export async function getValidatedStats() {
  const response = await axios.get(`${API_BASE_URL}/validated/stats/summary`)
  return response.data
}
