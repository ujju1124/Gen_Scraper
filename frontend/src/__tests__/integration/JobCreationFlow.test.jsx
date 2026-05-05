/**
 * Job Creation Flow Integration Test
 * Tests complete job creation flow: category selection → source loading → submission → navigation
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuthProvider } from '../../contexts/AuthContext'
import { JobCreationForm } from '../../components/dashboard/JobCreationForm'
import * as jobService from '../../services/jobService'

// Mock the job service
vi.mock('../../services/jobService')

// Mock react-router-dom navigate
const mockNavigate = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate
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

describe('Job Creation Flow Integration', () => {
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

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock successful category fetch
    jobService.getCategories.mockResolvedValue(mockCategories)
  })

  it('completes successful job creation flow with category selection, source loading, submission, and navigation', async () => {
    // Mock successful source fetch and job creation
    jobService.getSourcesForCategory.mockResolvedValue(mockSources)
    const mockCreatedJob = { id: 'job-123', status: 'QUEUED' }
    jobService.createJob.mockResolvedValue(mockCreatedJob)

    render(
      <TestWrapper>
        <JobCreationForm />
      </TestWrapper>
    )

    // Wait for categories to load
    await waitFor(() => {
      expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
    })

    // Verify initial form state
    const categorySelect = screen.getByLabelText(/category/i)
    const locationInput = screen.getByLabelText(/location/i)
    const submitButton = screen.getByRole('button', { name: /create job/i })

    expect(categorySelect).toBeInTheDocument()
    expect(locationInput).toBeInTheDocument()
    expect(submitButton).toBeInTheDocument()
    expect(submitButton).toBeDisabled() // Should be disabled initially

    // Step 1: Select category
    fireEvent.change(categorySelect, { target: { value: '1' } })

    // Verify API call for categories was made
    expect(jobService.getCategories).toHaveBeenCalledTimes(1)

    // Wait for sources to load after category selection
    await waitFor(() => {
      expect(jobService.getSourcesForCategory).toHaveBeenCalledWith("1")
    })

    // Step 2: Wait for sources to appear
    await waitFor(() => {
      expect(screen.getByText('Booking.com')).toBeInTheDocument()
      expect(screen.getByText('Agoda')).toBeInTheDocument()
    })

    // Step 3: Fill location
    fireEvent.change(locationInput, { target: { value: 'Kathmandu' } })

    // Step 4: Select at least one source
    const bookingCheckbox = screen.getByLabelText(/booking\.com/i)
    fireEvent.click(bookingCheckbox)

    // Verify form validation passes and submit button is enabled
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled()
    })

    // Step 5: Submit the form
    fireEvent.click(submitButton)

    // Verify loading state is shown
    await waitFor(() => {
      expect(submitButton).toBeDisabled()
      expect(screen.getByText(/creating job/i)).toBeInTheDocument()
    })

    // Verify API call was made with correct parameters
    await waitFor(() => {
      expect(jobService.createJob).toHaveBeenCalledWith(
        expect.objectContaining({
          category_id: 1,
          location: 'Kathmandu',
          source_ids: [1]
        })
      )
      expect(jobService.createJob).toHaveBeenCalledTimes(1)
    })

    // Verify navigation to job status page occurs
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/jobs/job-123')
    })
  })

  it('handles multiple source selection correctly', async () => {
    jobService.getSourcesForCategory.mockResolvedValue(mockSources)
    const mockCreatedJob = { id: 'job-456', status: 'QUEUED' }
    jobService.createJob.mockResolvedValue(mockCreatedJob)

    render(
      <TestWrapper>
        <JobCreationForm />
      </TestWrapper>
    )

    // Wait for form to load
    await waitFor(() => {
      expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
    })

    // Select category and wait for sources
    const categorySelect = screen.getByLabelText(/category/i)
    fireEvent.change(categorySelect, { target: { value: '1' } })

    await waitFor(() => {
      expect(screen.getByText('Booking.com')).toBeInTheDocument()
    })

    // Fill location
    const locationInput = screen.getByLabelText(/location/i)
    fireEvent.change(locationInput, { target: { value: 'Pokhara' } })

    // Select multiple sources
    const bookingCheckbox = screen.getByLabelText(/booking\.com/i)
    const agodaCheckbox = screen.getByLabelText(/agoda/i)
    fireEvent.click(bookingCheckbox)
    fireEvent.click(agodaCheckbox)

    // Submit form
    const submitButton = screen.getByRole('button', { name: /create job/i })
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled()
    })
    fireEvent.click(submitButton)

    // Verify API call includes both sources
    await waitFor(() => {
      expect(jobService.createJob).toHaveBeenCalledWith(
        expect.objectContaining({
          category_id: 1,
          location: 'Pokhara',
          source_ids: [1, 2]
        })
      )
    })

    // Verify navigation
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/jobs/job-456')
    })
  })

  it('handles form validation errors correctly', async () => {
    jobService.getSourcesForCategory.mockResolvedValue(mockSources)

    render(
      <TestWrapper>
        <JobCreationForm />
      </TestWrapper>
    )

    // Wait for form to load
    await waitFor(() => {
      expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
    })

    const submitButton = screen.getByRole('button', { name: /create job/i })

    // Try to submit without filling required fields
    expect(submitButton).toBeDisabled()

    // Fill only category
    const categorySelect = screen.getByLabelText(/category/i)
    fireEvent.change(categorySelect, { target: { value: '1' } })

    // Wait for sources to load
    await waitFor(() => {
      expect(screen.getByText('Booking.com')).toBeInTheDocument()
    })

    // Submit button should still be disabled (missing location and sources)
    expect(submitButton).toBeDisabled()

    // Fill location but no sources
    const locationInput = screen.getByLabelText(/location/i)
    fireEvent.change(locationInput, { target: { value: 'Kathmandu' } })

    // Submit button should still be disabled (no sources selected)
    expect(submitButton).toBeDisabled()

    // Select a source
    const bookingCheckbox = screen.getByLabelText(/booking\.com/i)
    fireEvent.click(bookingCheckbox)

    // Now submit button should be enabled
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled()
    })

    // Verify no API calls were made during validation
    expect(jobService.createJob).not.toHaveBeenCalled()
  })

  it('handles job creation API errors gracefully', async () => {
    jobService.getSourcesForCategory.mockResolvedValue(mockSources)
    const errorMessage = 'Failed to create job'
    jobService.createJob.mockRejectedValue(new Error(errorMessage))

    render(
      <TestWrapper>
        <JobCreationForm />
      </TestWrapper>
    )

    // Complete the form
    await waitFor(() => {
      expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
    })

    const categorySelect = screen.getByLabelText(/category/i)
    const locationInput = screen.getByLabelText(/location/i)
    const submitButton = screen.getByRole('button', { name: /create job/i })

    fireEvent.change(categorySelect, { target: { value: '1' } })

    await waitFor(() => {
      expect(screen.getByText('Booking.com')).toBeInTheDocument()
    })

    fireEvent.change(locationInput, { target: { value: 'Kathmandu' } })

    const bookingCheckbox = screen.getByLabelText(/booking\.com/i)
    fireEvent.click(bookingCheckbox)

    await waitFor(() => {
      expect(submitButton).not.toBeDisabled()
    })

    // Submit form
    fireEvent.click(submitButton)

    // Verify loading state
    await waitFor(() => {
      expect(submitButton).toBeDisabled()
    })

    // Verify API call was made
    await waitFor(() => {
      expect(jobService.createJob).toHaveBeenCalled()
    })

    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
    })

    // Verify form is re-enabled after error
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled()
      expect(submitButton).toHaveTextContent('Create Job')
    })

    // Verify no navigation occurred
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('handles category loading errors gracefully', async () => {
    // Mock category fetch failure
    jobService.getCategories.mockRejectedValue(new Error('Failed to load categories'))

    render(
      <TestWrapper>
        <JobCreationForm />
      </TestWrapper>
    )

    // Verify error state is shown
    await waitFor(() => {
      expect(screen.getByText(/failed to load categories/i)).toBeInTheDocument()
    })

    // Verify form is disabled when categories fail to load
    const submitButton = screen.getByRole('button', { name: /create job/i })
    expect(submitButton).toBeDisabled()
  })

  it('handles source loading errors gracefully', async () => {
    // Mock successful category fetch but failed source fetch
    jobService.getSourcesForCategory.mockRejectedValue(new Error('Failed to load sources'))

    render(
      <TestWrapper>
        <JobCreationForm />
      </TestWrapper>
    )

    // Wait for categories to load
    await waitFor(() => {
      expect(screen.getByLabelText(/category/i)).toBeInTheDocument()
    })

    // Select category
    const categorySelect = screen.getByLabelText(/category/i)
    fireEvent.change(categorySelect, { target: { value: '1' } })

    // Verify source loading error is shown
    await waitFor(() => {
      expect(screen.getByText(/failed to load sources/i)).toBeInTheDocument()
    })

    // Verify submit button remains disabled when sources fail to load
    const submitButton = screen.getByRole('button', { name: /create job/i })
    expect(submitButton).toBeDisabled()
  })
})