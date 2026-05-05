/**
 * Job Service
 * Handles all job-related API calls
 */
import api from './api'

/**
 * Get all categories
 * @returns {Promise<Object>} Categories response with items array
 */
export const getCategories = async () => {
  const response = await api.get('/api/v1/categories/')
  return response.data
}

/**
 * Get sources for a specific category
 * @param {number} categoryId - Category ID
 * @returns {Promise<Array>} Array of sources
 */
export const getSourcesForCategory = async (categoryId) => {
  const response = await api.get(`/api/v1/categories/${categoryId}/sources`)
  return response.data
}

/**
 * Create a new scrape job
 * @param {Object} jobData - Job data
 * @param {number} jobData.category_id - Category ID
 * @param {string} jobData.location - Location/city name
 * @param {Array<number>} jobData.source_ids - Array of source IDs
 * @returns {Promise<Object>} Created job object
 */
export const createJob = async (jobData) => {
  const response = await api.post('/api/v1/jobs/', jobData)
  return response.data
}

/**
 * Get paginated job history for current user
 * @param {number} page - Page number (default 1)
 * @param {number} pageSize - Page size (default 20)
 * @returns {Promise<Object>} Paginated jobs response
 */
export const getJobs = async (page = 1, pageSize = 20) => {
  const response = await api.get('/api/v1/jobs/', {
    params: { page, page_size: pageSize }
  })
  return response.data
}

/**
 * Get job status
 * @param {string} jobId - Job ID
 * @returns {Promise<Object>} Job status object
 */
export const getJobStatus = async (jobId) => {
  const response = await api.get(`/api/v1/jobs/${jobId}/status`)
  return response.data
}

/**
 * Get paginated results for a job
 * @param {string} jobId - Job ID
 * @param {number} page - Page number (default 1)
 * @param {number} pageSize - Page size (default 50)
 * @returns {Promise<Object>} Paginated results response
 */
export const getJobResults = async (jobId, page = 1, pageSize = 50) => {
  const response = await api.get(`/api/v1/jobs/${jobId}/results`, {
    params: { page, page_size: pageSize }
  })
  return response.data
}

/**
 * Retry a failed job
 * @param {string} jobId - Job ID to retry
 * @returns {Promise<Object>} New job object
 */
export const retryJob = async (jobId) => {
  const response = await api.post(`/api/v1/jobs/${jobId}/retry`)
  return response.data
}

/**
 * Get full details for a single result
 * @param {string} resultId - Result ID
 * @returns {Promise<Object>} Full result object with all fields
 */
export const getResultDetail = async (resultId) => {
  const response = await api.get(`/api/v1/jobs/results/${resultId}`)
  return response.data
}