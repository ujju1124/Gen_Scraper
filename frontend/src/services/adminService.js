/**
 * Admin Service
 * Handles all admin-related API calls
 */
import api from './api'

/**
 * Get paginated admin results with filters and sorting
 * @param {Object} params - Query parameters
 * @param {string} [params.status] - Filter by status (PENDING, APPROVED, REJECTED)
 * @param {number} [params.category_id] - Filter by category ID
 * @param {string} [params.city] - Filter by city name
 * @param {string} [params.sort_by] - Sort by field (data_completeness or created_at)
 * @param {number} [params.page] - Page number (default 1)
 * @param {number} [params.page_size] - Page size (default 50)
 * @returns {Promise<Object>} Paginated admin results response
 */
export const getAdminResults = async (params = {}) => {
  const {
    status,
    category_id,
    city,
    sort_by = 'created_at',
    page = 1,
    page_size = 50
  } = params

  const queryParams = {
    page,
    page_size,
    sort_by
  }

  if (status) queryParams.status = status
  if (category_id) queryParams.category_id = category_id
  if (city) queryParams.city = city

  const response = await api.get('/api/v1/admin/results/', {
    params: queryParams
  })
  return response.data
}

/**
 * Inline edit a single field in a cleaned result
 * @param {string} resultId - UUID of the cleaned result
 * @param {string} fieldName - Name of the field to edit
 * @param {string|null} fieldValue - New value for the field
 * @returns {Promise<Object>} Inline edit response
 */
export const inlineEditResult = async (resultId, fieldName, fieldValue) => {
  const response = await api.patch(`/api/v1/admin/results/${resultId}`, {
    field_name: fieldName,
    field_value: fieldValue
  })
  return response.data
}

/**
 * Approve a cleaned result
 * @param {string} resultId - UUID of the cleaned result
 * @param {string} [notes] - Optional notes about the approval
 * @returns {Promise<Object>} Approve response
 */
export const approveResult = async (resultId, notes = null) => {
  const response = await api.post(`/api/v1/admin/results/${resultId}/approve`, {
    notes
  })
  return response.data
}

/**
 * Reject a cleaned result
 * @param {string} resultId - UUID of the cleaned result
 * @param {string} [notes] - Optional notes about the rejection
 * @returns {Promise<Object>} Reject response
 */
export const rejectResult = async (resultId, notes = null) => {
  const response = await api.post(`/api/v1/admin/results/${resultId}/reject`, {
    notes
  })
  return response.data
}

/**
 * Send an APPROVED result to validated_results table
 * @param {string} resultId - UUID of the cleaned result
 * @param {string} [notes] - Optional notes about the validation
 * @returns {Promise<Object>} Send to validated response
 */
export const sendToValidated = async (resultId, notes = null) => {
  const response = await api.post(`/api/v1/admin/results/${resultId}/send-to-validated`, {
    notes
  })
  return response.data
}


/**
 * Export admin results as CSV or JSON
 * @param {string} format - Export format ('csv' or 'json')
 * @param {Object} filters - Active filters
 * @param {string} [filters.status] - Filter by status
 * @param {number} [filters.category_id] - Filter by category ID
 * @param {string} [filters.city] - Filter by city name
 * @param {string} [filters.sort_by] - Sort by field
 * @returns {Promise<Blob>} File blob for download
 */
export const exportResults = async (format, filters = {}) => {
  const queryParams = {
    format,
    ...filters
  }

  const response = await api.get('/api/v1/admin/export', {
    params: queryParams,
    responseType: 'blob' // Important for file download
  })

  return response.data
}

/**
 * Bulk approve or reject multiple results
 * @param {Array<string>} ids - Array of result UUIDs
 * @param {string} action - Action to perform ('approve' or 'reject')
 * @returns {Promise<Object>} Bulk action response with processed count
 */
export const bulkActionResults = async (ids, action) => {
  const response = await api.post('/api/v1/admin/results/bulk-action', {
    ids,
    action
  })
  return response.data
}

/**
 * Get paginated list of users
 * @param {Object} params - Query parameters
 * @param {number} [params.page] - Page number (default 1)
 * @param {number} [params.page_size] - Page size (default 20)
 * @returns {Promise<Object>} Paginated users response
 */
export const getUsers = async (params = {}) => {
  const { page = 1, page_size = 20 } = params

  const response = await api.get('/api/v1/admin/users', {
    params: { page, page_size }
  })
  return response.data
}

/**
 * Update user active status
 * @param {number} userId - User ID
 * @param {boolean} isActive - New active status
 * @returns {Promise<Object>} Updated user
 */
export const updateUserStatus = async (userId, isActive) => {
  const response = await api.patch(`/api/v1/admin/users/${userId}`, {
    is_active: isActive
  })
  return response.data
}

/**
 * Get monitoring dashboard data
 * @returns {Promise<Object>} Monitoring metrics including job success rate, scraper health, results per source, etc.
 */
export const getMonitoringData = async () => {
  const response = await api.get('/api/v1/admin/monitoring')
  return response.data
}
