/**
 * Admin Filtering Integration Test
 * Tests admin filtering flow: filter application → API request → results update
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuthProvider } from '../../contexts/AuthContext'
import { AdminPage } from '../../pages/AdminPage'
import * as adminService from '../../services/adminService'
import * as jobService from '../../services/jobService'
import api from '../../services/api'

// Mock the API module to prevent real HTTP requests
vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn().mockResolvedValue({ data: { items: [], total: 0, page: 1, page_size: 50, pages: 0 } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  }
}))

// Mock the services
vi.mock('../../services/adminService')
vi.mock('../../services/jobService')

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

describe('Admin Filtering Integration', () => {
  const mockCategories = {
    items: [
      { id: 1, name: 'hotels', display_name: 'Hotels' },
      { id: 2, name: 'restaurants', display_name: 'Restaurants' }
    ]
  }

  const mockSources = [
    { id: 1, name: 'booking-com', display_name: 'Booking.com' },
    { id: 2, name: 'agoda', display_name: 'Agoda' }
  ]

  const mockResults = {
    items: [
      {
        id: 1,
        name: 'Hotel ABC',
        city: 'Kathmandu',
        category_id: 1,
        source_id: 1,
        rating_overall: 8.5,
        price_min: 5000,
        currency: 'NPR',
        data_completeness: 85,
        validation_status: 'APPROVED',
        created_at: '2024-01-01T10:00:00Z'
      },
      {
        id: 2,
        name: 'Restaurant XYZ',
        city: 'Pokhara',
        category_id: 2,
        source_id: 2,
        rating_overall: 7.2,
        price_min: 1500,
        currency: 'NPR',
        data_completeness: 65,
        validation_status: 'PENDING',
        created_at: '2024-01-02T11:00:00Z'
      }
    ],
    total: 2,
    pages: 1,
    page: 1
  }

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock default API responses
    jobService.getCategories.mockResolvedValue(mockCategories)
    jobService.getSourcesForCategory.mockResolvedValue(mockSources)
    adminService.getAdminResults.mockResolvedValue(mockResults)
  })

  it('loads initial data and displays results without filters', async () => {
    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial data to load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
      expect(screen.getByText('Restaurant XYZ')).toBeInTheDocument()
    })

    // Verify initial API calls were made
    expect(jobService.getCategories).toHaveBeenCalled()
    expect(adminService.getAdminResults).toHaveBeenCalledWith(
      expect.objectContaining({
        page: 1,
        page_size: 50
      })
    )

    // Verify table content is displayed
    expect(screen.getByText('Kathmandu')).toBeInTheDocument()
    expect(screen.getByText('Pokhara')).toBeInTheDocument()
    expect(screen.getAllByText('Hotels')[0]).toBeInTheDocument() // Category display name
    expect(screen.getAllByText('Restaurants')[1]).toBeInTheDocument() // Use the table cell, not dropdown option
    // Rating and price format may vary by component implementation
    expect(screen.getByText('Kathmandu')).toBeInTheDocument()
    expect(screen.getByText('Pokhara')).toBeInTheDocument()
  })

  it('applies status filter and updates results', async () => {
    // Mock filtered results
    const filteredResults = {
      items: [mockResults.items[0]], // Only APPROVED result
      total: 1,
      pages: 1,
      page: 1
    }

    adminService.getAdminResults.mockResolvedValueOnce(mockResults) // Initial load
    adminService.getAdminResults.mockResolvedValueOnce(filteredResults) // After filter

    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
      expect(screen.getByText('Restaurant XYZ')).toBeInTheDocument()
    })

    // Apply status filter
    const statusFilter = screen.getByLabelText(/status/i)
    fireEvent.change(statusFilter, { target: { value: 'APPROVED' } })

    // Verify API call with status filter
    await waitFor(() => {
      expect(adminService.getAdminResults).toHaveBeenCalledWith({
        page: 1,
        page_size: 50,
        sort_by: 'created_at',
        status: 'APPROVED'
      })
    })

    // Verify filtered results are displayed
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
      expect(screen.queryByText('Restaurant XYZ')).not.toBeInTheDocument()
    })
  })

  it('applies category filter and updates results', async () => {
    const filteredResults = {
      items: [mockResults.items[1]], // Only restaurant result
      total: 1,
      pages: 1,
      page: 1
    }

    adminService.getAdminResults.mockResolvedValueOnce(mockResults) // Initial load
    adminService.getAdminResults.mockResolvedValueOnce(filteredResults) // After filter

    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
    })

    // Apply category filter
    const categoryFilter = screen.getByLabelText(/category/i)
    fireEvent.change(categoryFilter, { target: { value: '2' } })

    // Verify API call with category filter
    await waitFor(() => {
      expect(adminService.getAdminResults).toHaveBeenCalledWith({
        page: 1,
        page_size: 50,
        sort_by: 'created_at',
        category_id: 2
      })
    })

    // Verify filtered results
    await waitFor(() => {
      expect(screen.queryByText('Hotel ABC')).not.toBeInTheDocument()
      expect(screen.getByText('Restaurant XYZ')).toBeInTheDocument()
    })
  })

  it('applies city filter and updates results', async () => {
    const filteredResults = {
      items: [mockResults.items[0]], // Only Kathmandu result
      total: 1,
      pages: 1,
      page: 1
    }

    adminService.getAdminResults.mockResolvedValueOnce(mockResults) // Initial load
    adminService.getAdminResults.mockResolvedValueOnce(filteredResults) // After filter

    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
    })

    // Apply city filter
    const cityFilter = screen.getByLabelText(/city/i)
    fireEvent.change(cityFilter, { target: { value: 'Kathmandu' } })

    // Verify API call with city filter
    await waitFor(() => {
      expect(adminService.getAdminResults).toHaveBeenCalledWith({
        page: 1,
        page_size: 50,
        sort_by: 'created_at',
        city: 'Kathmandu'
      })
    })

    // Verify filtered results
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
      expect(screen.queryByText('Restaurant XYZ')).not.toBeInTheDocument()
    })
  })

  it('applies multiple filters simultaneously', async () => {
    const filteredResults = {
      items: [], // No results match all filters
      total: 0,
      pages: 0,
      page: 1
    }

    adminService.getAdminResults.mockResolvedValueOnce(mockResults) // Initial load
    
    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
    })

    // Set up mock for filtered results before applying filters
    adminService.getAdminResults.mockResolvedValue(filteredResults)

    // Apply multiple filters
    const statusFilter = screen.getByLabelText(/status/i)
    const categoryFilter = screen.getByLabelText(/category/i)
    const cityFilter = screen.getByLabelText(/city/i)

    fireEvent.change(statusFilter, { target: { value: 'APPROVED' } })
    fireEvent.change(categoryFilter, { target: { value: '2' } })
    fireEvent.change(cityFilter, { target: { value: 'Kathmandu' } })

    // Verify API call with all filters
    await waitFor(() => {
      expect(adminService.getAdminResults).toHaveBeenCalledWith({
        page: 1,
        page_size: 50,
        sort_by: 'created_at',
        status: 'APPROVED',
        category_id: 2,
        city: 'Kathmandu'
      })
    })

    // Verify empty state is shown
    await waitFor(() => {
      expect(screen.getByText(/no results found/i)).toBeInTheDocument()
    })
  })

  it('clears all filters and reloads original results', async () => {
    const filteredResults = {
      items: [mockResults.items[0]],
      total: 1,
      pages: 1,
      page: 1
    }

    adminService.getAdminResults
      .mockResolvedValueOnce(mockResults) // Initial load
      .mockResolvedValueOnce(filteredResults) // After filter
      .mockResolvedValueOnce(mockResults) // After clear

    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
      expect(screen.getByText('Restaurant XYZ')).toBeInTheDocument()
    })

    // Apply a filter
    const statusFilter = screen.getByLabelText(/status/i)
    fireEvent.change(statusFilter, { target: { value: 'APPROVED' } })

    // Wait for filtered results
    await waitFor(() => {
      expect(screen.queryByText('Restaurant XYZ')).not.toBeInTheDocument()
    })

    // Clear filters
    const clearButton = screen.getByRole('button', { name: /clear filters/i })
    fireEvent.click(clearButton)

    // Verify API call without filters
    await waitFor(() => {
      expect(adminService.getAdminResults).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 50,
        sort_by: 'created_at'
      })
    })

    // Verify all results are shown again
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
      expect(screen.getByText('Restaurant XYZ')).toBeInTheDocument()
    })

    // Verify filter inputs are cleared
    expect(statusFilter.value).toBe('')
  })

  it('applies sorting and updates results', async () => {
    const sortedResults = {
      items: [mockResults.items[1], mockResults.items[0]], // Reversed order
      total: 2,
      pages: 1,
      page: 1
    }

    adminService.getAdminResults.mockResolvedValueOnce(mockResults) // Initial load
    adminService.getAdminResults.mockResolvedValueOnce(sortedResults) // After sort

    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
    })

    // Click on completeness column header to sort
    const completenessHeader = screen.getByRole('button', { name: /completeness/i })
    fireEvent.click(completenessHeader)

    // Verify API call with sort parameter
    await waitFor(() => {
      expect(adminService.getAdminResults).toHaveBeenCalledWith({
        page: 1,
        page_size: 50,
        sort_by: 'data_completeness'
      })
    })
  })

  it('preserves filters when changing pages', async () => {
    const page1Results = {
      items: [mockResults.items[0]],
      total: 2,
      pages: 2,
      page: 1
    }

    const page2Results = {
      items: [mockResults.items[1]],
      total: 2,
      pages: 2,
      page: 2
    }

    adminService.getAdminResults
      .mockResolvedValueOnce(mockResults) // Initial load
      .mockResolvedValueOnce(page1Results) // After filter
      .mockResolvedValueOnce(page2Results) // Page 2 with filter

    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
    })

    // Apply status filter
    const statusFilter = screen.getByLabelText(/status/i)
    fireEvent.change(statusFilter, { target: { value: 'APPROVED' } })

    // Wait for filtered results
    await waitFor(() => {
      expect(adminService.getAdminResults).toHaveBeenCalledWith({
        page: 1,
        page_size: 50,
        sort_by: 'created_at',
        status: 'APPROVED'
      })
    })

    // Navigate to page 2
    const nextButton = screen.getByRole('button', { name: /next/i })
    fireEvent.click(nextButton)

    // Verify API call preserves filter on page 2
    await waitFor(() => {
      expect(adminService.getAdminResults).toHaveBeenCalledWith({
        page: 2,
        page_size: 50,
        sort_by: 'created_at',
        status: 'APPROVED'
      })
    })
  })

  it('handles filter API errors gracefully', async () => {
    adminService.getAdminResults.mockResolvedValueOnce(mockResults) // Initial load
    adminService.getAdminResults.mockRejectedValueOnce(new Error('Filter failed')) // Filter error

    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
    })

    // Apply filter that will fail
    const statusFilter = screen.getByLabelText(/status/i)
    fireEvent.change(statusFilter, { target: { value: 'APPROVED' } })

    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(/failed to load admin results/i)).toBeInTheDocument()
    })

    // Verify original results are cleared
    expect(screen.queryByText('Hotel ABC')).not.toBeInTheDocument()
  })

  it('displays active filters count and descriptions', async () => {
    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
    })

    // Apply multiple filters
    const statusFilter = screen.getByLabelText(/status/i)
    const cityFilter = screen.getByLabelText(/city/i)

    fireEvent.change(statusFilter, { target: { value: 'APPROVED' } })
    fireEvent.change(cityFilter, { target: { value: 'Kathmandu' } })

    // Verify active filters are displayed
    await waitFor(() => {
      expect(screen.getByText(/status: approved/i)).toBeInTheDocument()
      expect(screen.getByText(/city: kathmandu/i)).toBeInTheDocument()
    })
  })

  it('handles empty filter values correctly', async () => {
    adminService.getAdminResults.mockResolvedValueOnce(mockResults) // Initial load
    adminService.getAdminResults.mockResolvedValueOnce(mockResults) // After empty filter

    render(
      <TestWrapper>
        <AdminPage />
      </TestWrapper>
    )

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
    })

    // Set filter to empty value
    const statusFilter = screen.getByLabelText(/status/i)
    fireEvent.change(statusFilter, { target: { value: '' } })

    // Verify API call doesn't include empty filter
    await waitFor(() => {
      expect(adminService.getAdminResults).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 50,
        sort_by: 'created_at'
        // No status parameter
      })
    })
  })
})