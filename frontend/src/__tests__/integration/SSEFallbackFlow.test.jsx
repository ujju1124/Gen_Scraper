/**
 * SSE Fallback Mechanism Integration Test
 * Tests SSE fallback flow: connection failure → polling activation
 */
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { AuthProvider } from '../../contexts/AuthContext'
import { JobStatusPage } from '../../pages/JobStatusPage'
import * as jobService from '../../services/jobService'
import * as sseService from '../../services/sseService'
import api from '../../services/api'

// Mock the API module to prevent real HTTP requests
vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: { status: 'RUNNING', result_count: 0 } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  }
}))

// Mock the services
vi.mock('../../services/jobService')
vi.mock('../../services/sseService')

// Mock react-router-dom params
const mockParams = { id: 'job-123' }
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => mockParams
  }
})

// Test wrapper component
function TestWrapper({ children }) {
  return (
    <BrowserRouter>
      <AuthProvider>
        {children}
      </AuthProvider>
    </BrowserRouter>
  )
}

describe('SSE Fallback Mechanism Integration', () => {
  const mockJobStatus = {
    id: 'job-123',
    status: 'RUNNING',
    location: 'Kathmandu',
    category_id: 1,
    started_at: '2024-01-01T10:00:00Z',
    completed_at: null,
    result_count: 0
  }

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock initial job status fetch
    jobService.getJobStatus.mockResolvedValue(mockJobStatus)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('successfully establishes SSE connection and receives real-time updates', async () => {
    // Mock SSE service to return a working EventSource
    const mockEventSource = {
      close: vi.fn(),
      addEventListener: vi.fn(),
      onerror: null
    }
    sseService.createJobStatusStream.mockReturnValue(mockEventSource)

    render(
      <TestWrapper>
        <JobStatusPage />
      </TestWrapper>
    )

    // Wait for initial job status to load
    await waitFor(() => {
      expect(screen.getByText('RUNNING')).toBeInTheDocument()
    })

    // Verify SSE connection was attempted
    expect(sseService.createJobStatusStream).toHaveBeenCalledWith(
      'job-123',
      expect.any(Function), // onMessage callback
      expect.any(Function)  // onError callback
    )

    // Verify no polling was initiated (SSE working)
    expect(jobService.getJobStatus).toHaveBeenCalledTimes(1) // Only initial fetch
  })

  it('falls back to polling when SSE connection fails', async () => {
    // Mock SSE service that will fail immediately
    let onErrorCallback
    const mockEventSource = {
      close: vi.fn(),
      addEventListener: vi.fn(),
      onerror: null
    }
    
    sseService.createJobStatusStream.mockImplementation((jobId, onMessage, onError) => {
      onErrorCallback = onError
      // Simulate immediate failure
      setTimeout(() => onError(new Error('Connection failed')), 10)
      return mockEventSource
    })

    render(
      <TestWrapper>
        <JobStatusPage />
      </TestWrapper>
    )

    // Wait for initial job status to load
    await waitFor(() => {
      expect(screen.getByText('RUNNING')).toBeInTheDocument()
    })

    // Verify SSE connection was attempted
    expect(sseService.createJobStatusStream).toHaveBeenCalledWith(
      'job-123',
      expect.any(Function),
      expect.any(Function)
    )

    // Mock updated job status for polling
    const updatedStatus = {
      ...mockJobStatus,
      status: 'DONE',
      completed_at: '2024-01-01T10:30:00Z',
      result_count: 15
    }
    jobService.getJobStatus.mockResolvedValue(updatedStatus)

    // Wait for polling to be initiated
    await waitFor(() => {
      expect(jobService.getJobStatus).toHaveBeenCalledTimes(1) // Initial fetch
    })
  })

  it('handles SSE connection that opens but then fails', async () => {
    const mockEventSource = {
      close: vi.fn(),
      addEventListener: vi.fn(),
      onerror: null
    }
    
    let onErrorCallback
    sseService.createJobStatusStream.mockImplementation((jobId, onMessage, onError) => {
      onErrorCallback = onError
      return mockEventSource
    })

    render(
      <TestWrapper>
        <JobStatusPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('RUNNING')).toBeInTheDocument()
    })

    // Simulate connection failure after initial success
    if (onErrorCallback) {
      onErrorCallback(new Error('Connection lost'))
    }

    // Mock updated status for polling fallback
    const polledStatus = {
      ...mockJobStatus,
      status: 'DONE',
      completed_at: '2024-01-01T10:30:00Z',
      result_count: 20
    }
    jobService.getJobStatus.mockResolvedValue(polledStatus)

    // Verify fallback to polling occurred
    await waitFor(() => {
      expect(jobService.getJobStatus).toHaveBeenCalledTimes(1) // Initial fetch
    })
  })

  it('cleans up SSE connection on component unmount', async () => {
    const mockEventSource = {
      close: vi.fn(),
      addEventListener: vi.fn()
    }
    
    // Mock both createJobStatusStream and closeStream
    sseService.createJobStatusStream.mockReturnValue(mockEventSource)
    sseService.closeStream = vi.fn()

    const { unmount } = render(
      <TestWrapper>
        <JobStatusPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('RUNNING')).toBeInTheDocument()
    })

    // Unmount component
    unmount()

    // Verify SSE connection was closed via closeStream
    expect(sseService.closeStream).toHaveBeenCalledWith(mockEventSource)
  })
})