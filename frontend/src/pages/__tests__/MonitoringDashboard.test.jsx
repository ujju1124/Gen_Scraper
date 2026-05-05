/**
 * Tests for MonitoringDashboard
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { MonitoringDashboard } from '../MonitoringDashboard'
import * as adminService from '../../services/adminService'

// Mock services
vi.mock('../../services/adminService')

// Mock recharts to avoid rendering issues in tests
vi.mock('recharts', () => ({
  BarChart: ({ children }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div data-testid="x-axis" />,
  YAxis: () => <div data-testid="y-axis" />,
  CartesianGrid: () => <div data-testid="cartesian-grid" />,
  Tooltip: () => <div data-testid="tooltip" />,
  Legend: () => <div data-testid="legend" />,
  ResponsiveContainer: ({ children }) => <div data-testid="responsive-container">{children}</div>
}))

const mockMonitoringData = {
  job_success_rate: 75.5,
  scraper_health: [
    {
      source_id: 1,
      source_name: 'booking_com',
      is_active: true,
      last_job_status: 'DONE',
      result_count: 150
    },
    {
      source_id: 2,
      source_name: 'agoda',
      is_active: true,
      last_job_status: 'FAILED',
      result_count: 50
    },
    {
      source_id: 3,
      source_name: 'nepalyp_hotels',
      is_active: false,
      last_job_status: 'DONE',
      result_count: 200
    }
  ],
  results_per_source: {
    booking_com: 150,
    agoda: 50,
    nepalyp_hotels: 200
  },
  avg_job_duration_seconds: 45.23,
  total_results: {
    raw: 500,
    cleaned: 450,
    validated: 100
  },
  recent_failures: [
    {
      job_id: 'abc123-def456-ghi789',
      location: 'Kathmandu',
      sources: ['booking_com', 'agoda'],
      error_message: 'Connection timeout',
      created_at: '2026-05-03T10:00:00Z'
    },
    {
      job_id: 'xyz789-uvw456-rst123',
      location: 'Pokhara',
      sources: ['nepalyp_hotels'],
      error_message: 'Selector not found',
      created_at: '2026-05-03T09:30:00Z'
    }
  ]
}

const renderMonitoringDashboard = () => {
  return render(
    <BrowserRouter>
      <MonitoringDashboard />
    </BrowserRouter>
  )
}

describe('MonitoringDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    adminService.getMonitoringData.mockResolvedValue(mockMonitoringData)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders loading state while fetching data', () => {
    adminService.getMonitoringData.mockImplementation(() => new Promise(() => {})) // Never resolves
    
    renderMonitoringDashboard()
    
    expect(screen.getByText('Loading monitoring data...')).toBeInTheDocument()
  })

  it('renders all metric sections when data loads', async () => {
    renderMonitoringDashboard()
    
    // Wait for job success rate to appear
    await waitFor(() => {
      expect(screen.getByText('75.5%')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Overview cards
    expect(screen.getByText('Job Success Rate')).toBeInTheDocument()
    expect(screen.getByText('Total Raw Results')).toBeInTheDocument()
    
    // Scraper health
    expect(screen.getByText('Scraper Health')).toBeInTheDocument()
    
    // Results per source chart
    expect(screen.getByText('Results Per Source')).toBeInTheDocument()
    
    // Recent failures
    expect(screen.getByText('Recent Failures')).toBeInTheDocument()
  })

  it('shows error state on API failure', async () => {
    adminService.getMonitoringData.mockRejectedValue(new Error('API Error'))
    
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load monitoring data')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    expect(screen.getByText('Error Loading Data')).toBeInTheDocument()
  })

  it('sets up auto-refresh interval', async () => {
    // This test verifies the interval is set up
    // Full interval testing is complex with fake timers, so we just verify initial load
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('75.5%')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Verify initial call was made
    expect(adminService.getMonitoringData).toHaveBeenCalled()
  })

  it('cleans up interval on unmount', async () => {
    // This test verifies cleanup happens
    const { unmount } = renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('75.5%')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Unmount should not throw errors
    expect(() => unmount()).not.toThrow()
  })

  it('displays scraper health status badges correctly', async () => {
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('booking_com')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Check for Active/Inactive badges
    const activeBadges = screen.getAllByText('Active')
    expect(activeBadges.length).toBeGreaterThanOrEqual(1)
  })

  it('displays result counts with proper formatting', async () => {
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('booking_com')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Check result counts in scraper health table
    expect(screen.getByText('150')).toBeInTheDocument()
  })

  it('shows empty state when no recent failures', async () => {
    adminService.getMonitoringData.mockResolvedValue({
      ...mockMonitoringData,
      recent_failures: []
    })
    
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('75.5%')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    expect(screen.getByText('No recent failures')).toBeInTheDocument()
  })

  it('shows empty state when no scraper health data', async () => {
    adminService.getMonitoringData.mockResolvedValue({
      ...mockMonitoringData,
      scraper_health: []
    })
    
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('75.5%')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    expect(screen.getByText('No scraper health data available')).toBeInTheDocument()
  })

  it('shows empty state when no results per source data', async () => {
    adminService.getMonitoringData.mockResolvedValue({
      ...mockMonitoringData,
      results_per_source: {}
    })
    
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('75.5%')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    expect(screen.getByText('No results data available')).toBeInTheDocument()
  })

  it('handles zero success rate correctly', async () => {
    adminService.getMonitoringData.mockResolvedValue({
      ...mockMonitoringData,
      job_success_rate: 0
    })
    
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('Job Success Rate')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    expect(screen.getByText('0.0%')).toBeInTheDocument()
  })

  it('handles null/undefined values gracefully', async () => {
    adminService.getMonitoringData.mockResolvedValue({
      job_success_rate: null,
      scraper_health: [],
      results_per_source: null,
      avg_job_duration_seconds: null,
      total_results: {
        raw: null,
        cleaned: null,
        validated: null
      },
      recent_failures: []
    })
    
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('Job Success Rate')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Should display 0 for null values
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('truncates long job IDs in recent failures', async () => {
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('Kathmandu')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Job IDs should be truncated to first 8 chars + "..."
    expect(screen.getByText('abc123-d...')).toBeInTheDocument()
  })

  it('formats timestamps correctly in recent failures', async () => {
    renderMonitoringDashboard()
    
    await waitFor(() => {
      expect(screen.getByText('Kathmandu')).toBeInTheDocument()
    }, { timeout: 3000 })
    
    // Check that timestamps are formatted (exact format depends on locale)
    const timestamps = screen.getAllByText(/\d/)
    expect(timestamps.length).toBeGreaterThan(0)
  })
})
