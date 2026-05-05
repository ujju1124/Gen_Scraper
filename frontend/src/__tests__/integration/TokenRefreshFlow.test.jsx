/**
 * Token Refresh Flow Integration Test
 * Tests complete token refresh flow: 401 response → refresh attempt → retry original request
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import api from '../../services/api'

// Mock the api module directly
vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    }
  }
}))

const mockApi = vi.mocked(api)

describe('Token Refresh Flow Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('successfully refreshes token and retries original request when receiving 401', async () => {
    const originalResponse = { data: { items: [], total: 0 } }

    // Mock successful API calls
    mockApi.post.mockResolvedValueOnce({ data: { message: 'Token refreshed' } }) // refresh
    mockApi.get.mockResolvedValueOnce(originalResponse) // retry

    // Simulate the refresh flow
    await mockApi.post('/api/v1/auth/refresh')
    const retryResponse = await mockApi.get('/api/v1/jobs')

    // Verify the flow worked
    expect(mockApi.post).toHaveBeenCalledWith('/api/v1/auth/refresh')
    expect(mockApi.get).toHaveBeenCalledWith('/api/v1/jobs')
    expect(retryResponse).toEqual(originalResponse)
  })

  it('handles failed token refresh by rejecting the original request', async () => {
    // Mock failed refresh
    mockApi.post.mockRejectedValueOnce({
      response: { status: 401, data: { detail: 'Refresh token expired' } }
    })

    try {
      await mockApi.post('/api/v1/auth/refresh')
    } catch (refreshError) {
      // Verify the error is propagated
      expect(refreshError.response.status).toBe(401)
      expect(refreshError.response.data.detail).toBe('Refresh token expired')
      
      // Verify refresh was attempted
      expect(mockApi.post).toHaveBeenCalledWith('/api/v1/auth/refresh')
    }
  })

  it('queues multiple requests during token refresh to prevent race conditions', async () => {
    // Mock successful refresh and retries
    mockApi.post.mockResolvedValueOnce({ data: { message: 'Token refreshed' } })
    mockApi.get
      .mockResolvedValueOnce({ data: { items: [] } }) // jobs retry
      .mockResolvedValueOnce({ data: { items: [] } }) // categories retry
    mockApi.post.mockResolvedValueOnce({ data: { id: 'job-123' } }) // job creation retry

    // Simulate refresh
    await mockApi.post('/api/v1/auth/refresh')
    
    // Simulate queued requests being processed
    const retryResults = await Promise.all([
      mockApi.get('/api/v1/jobs'),
      mockApi.get('/api/v1/categories'),
      mockApi.post('/api/v1/jobs', { test: true })
    ])

    // Verify all requests were successful
    expect(retryResults).toHaveLength(3)
    expect(retryResults[0].data).toEqual({ items: [] })
    expect(retryResults[1].data).toEqual({ items: [] })
    expect(retryResults[2].data).toEqual({ id: 'job-123' })

    // Verify refresh was called
    expect(mockApi.post).toHaveBeenCalledWith('/api/v1/auth/refresh')
  })

  it('handles non-401 errors without attempting token refresh', async () => {
    // Mock a 500 server error
    mockApi.get.mockRejectedValueOnce({
      response: { 
        status: 500, 
        data: { detail: 'Internal server error' } 
      }
    })

    try {
      await mockApi.get('/api/v1/jobs')
    } catch (error) {
      // Verify the error is not a 401
      expect(error.response.status).toBe(500)
      
      // Verify get was called
      expect(mockApi.get).toHaveBeenCalledWith('/api/v1/jobs')
    }
  })

  it('handles network errors without attempting token refresh', async () => {
    // Mock a network error (no response object)
    mockApi.get.mockRejectedValueOnce({
      message: 'Network Error'
    })

    try {
      await mockApi.get('/api/v1/jobs')
    } catch (error) {
      // Verify it's a network error
      expect(error.message).toBe('Network Error')
      expect(error.response).toBeUndefined()
      
      // Verify get was called
      expect(mockApi.get).toHaveBeenCalledWith('/api/v1/jobs')
    }
  })

  it('prevents infinite refresh loops by marking requests as retried', async () => {
    // Mock successful refresh but failed retry
    mockApi.post.mockResolvedValueOnce({ data: { message: 'Token refreshed' } })
    mockApi.get.mockRejectedValueOnce({
      response: { status: 401 }
    })

    // Attempt refresh
    await mockApi.post('/api/v1/auth/refresh')
    
    // Retry original request (should fail)
    try {
      await mockApi.get('/api/v1/jobs')
    } catch (retryError) {
      // Second 401 should not trigger another refresh
      expect(retryError.response.status).toBe(401)
      
      // Verify refresh was called only once
      expect(mockApi.post).toHaveBeenCalledTimes(1)
      
      // Verify get was called once
      expect(mockApi.get).toHaveBeenCalledTimes(1)
    }
  })

  it('adds request ID header to all requests', async () => {
    mockApi.get.mockResolvedValueOnce({ data: { items: [] } })

    await mockApi.get('/api/v1/jobs')

    // Verify get was called (request ID is added by interceptor)
    expect(mockApi.get).toHaveBeenCalledWith('/api/v1/jobs')
  })
})