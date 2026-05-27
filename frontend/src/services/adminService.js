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
 * @param {number} [params.source_id] - Filter by source ID
 * @param {boolean} [params.is_duplicate] - Filter by duplicate status
 * @param {number} [params.min_completeness] - Minimum data completeness percentage
 * @param {boolean} [params.has_phone] - Filter by phone presence
 * @param {boolean} [params.has_website] - Filter by website presence
 * @param {boolean} [params.has_rating] - Filter by rating presence
 * @param {string} [params.created_after] - Filter by created date (ISO format)
 * @param {string} [params.created_before] - Filter by created date (ISO format)
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
    source_id,
    is_duplicate,
    min_completeness,
    has_phone,
    has_website,
    has_rating,
    has_opening_hours,
    created_after,
    created_before,
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
  if (source_id) queryParams.source_id = source_id
  if (is_duplicate !== undefined && is_duplicate !== null && is_duplicate !== '') {
    queryParams.is_duplicate = is_duplicate
  }
  if (min_completeness) queryParams.min_completeness = min_completeness
  if (has_phone !== undefined && has_phone !== null && has_phone !== '') {
    queryParams.has_phone = has_phone
  }
  if (has_website !== undefined && has_website !== null && has_website !== '') {
    queryParams.has_website = has_website
  }
  if (has_rating !== undefined && has_rating !== null && has_rating !== '') {
    queryParams.has_rating = has_rating
  }
  if (has_opening_hours !== undefined && has_opening_hours !== null && has_opening_hours !== '') {
    queryParams.has_opening_hours = has_opening_hours
  }
  if (created_after) queryParams.created_after = created_after
  if (created_before) queryParams.created_before = created_before

  const response = await api.get('/api/v1/admin/results/', {
    params: queryParams
  })
  return response.data
}

/**
 * Get all sources for dropdown
 * @returns {Promise<Array>} Array of sources
 */
export const getAllSources = async () => {
  const response = await api.get('/api/v1/admin/sources')
  return response.data
}

/**
 * Inline edit a single field in a cleaned result
 * Feature 2: Now supports temporary vs permanent edits
 * @param {string} resultId - UUID of the cleaned result
 * @param {string} fieldName - Name of the field to edit
 * @param {string|null} fieldValue - New value for the field
 * @param {boolean} [temporary=false] - If true, store in user_overrides; if false, update main column
 * @returns {Promise<Object>} Inline edit response
 */
export const inlineEditResult = async (resultId, fieldName, fieldValue, temporary = false) => {
  const response = await api.patch(`/api/v1/admin/results/${resultId}`, {
    field_name: fieldName,
    field_value: fieldValue,
    temporary: temporary
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
 * Export admin results as CSV, JSON, or Excel
 * @param {string} format - Export format ('csv', 'json', or 'excel')
 * @param {Object} filters - Active filters
 * @param {string} [filters.status] - Filter by status
 * @param {number} [filters.category_id] - Filter by category ID
 * @param {string} [filters.city] - Filter by city name
 * @param {number} [filters.source_id] - Filter by source ID
 * @param {boolean} [filters.is_duplicate] - Filter by duplicate status
 * @param {number} [filters.min_completeness] - Minimum completeness percentage
 * @param {boolean} [filters.has_phone] - Filter by phone presence
 * @param {boolean} [filters.has_website] - Filter by website presence
 * @param {boolean} [filters.has_rating] - Filter by rating presence
 * @param {string} [filters.created_after] - Filter by created date
 * @param {string} [filters.created_before] - Filter by created date
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


// ═══════════════════════════════════════════════════════════════════════════════
// COLUMN DEFINITIONS API (FIX 1)
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Get all custom column definitions
 * @returns {Promise<Array>} Array of column definitions
 */
export const getColumnDefinitions = async () => {
  const response = await api.get('/api/v1/admin/column-definitions')
  return response.data
}

/**
 * Create a new custom column definition
 * @param {string} name - Column key (e.g., "custom_verification_status")
 * @param {string} display_name - Human-readable label
 * @param {boolean} is_temporary - If true, column is session-scoped
 * @returns {Promise<Object>} Created column definition
 */
export const createColumnDefinition = async (name, display_name, is_temporary = false) => {
  const response = await api.post('/api/v1/admin/column-definitions', {
    name,
    display_name,
    is_temporary
  })
  return response.data
}

/**
 * Delete a custom column definition
 * @param {number} colId - Column definition ID
 * @returns {Promise<Object>} Success response
 */
export const deleteColumnDefinition = async (colId) => {
  const response = await api.delete(`/api/v1/admin/column-definitions/${colId}`)
  return response.data
}

/**
 * Update a column definition's display name (for permanent renames)
 * @param {number} colId - Column definition ID
 * @param {string} display_name - New display name
 * @returns {Promise<Object>} Updated column definition
 */
export const updateColumnDefinition = async (colId, display_name) => {
  const response = await api.put(`/api/v1/admin/column-definitions/${colId}`, null, {
    params: { display_name }
  })
  return response.data
}
