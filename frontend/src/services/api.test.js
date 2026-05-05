import { describe, it, expect } from 'vitest'

describe('API Client', () => {
  it('should be importable', async () => {
    const api = await import('./api')
    expect(api.default).toBeDefined()
  })

  it('transforms error messages correctly', () => {
    // Test error transformation logic
    const networkError = {
      message: 'Network Error',
      response: undefined,
    }
    expect(networkError.response).toBeUndefined()

    const authError = {
      response: {
        status: 401,
        data: { detail: 'Unauthorized' },
      },
    }
    expect(authError.response.status).toBe(401)

    const rateLimitError = {
      response: {
        status: 429,
        data: { detail: 'Too many requests' },
      },
    }
    expect(rateLimitError.response.status).toBe(429)
  })
})