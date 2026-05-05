/**
 * Tests for JobResultsPage
 * Target: 5.42% → 70%+
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { JobResultsPage } from '../JobResultsPage'
import * as jobService from '../../services/jobService'

// Mock jobService
vi.mock('../../services/jobService')

const mockJobDetails = {
  id: 123,
  location: 'Kathmandu',
  status: 'DONE',
  category_name: 'Hotels'
}

const mockResults = {
  items: [
    {
      id: 1,
      name: 'Hotel Yak & Yeti',
      city: 'Kathmandu',
      address: 'Durbar Marg',
      rating_overall: 8.5,
      price_min: 5000,
      data_completeness: 85,
      status: 'approved'
    },
    {
      id: 2,
      name: 'Hyatt Regency',
      city: 'Kathmandu',
      address: 'Taragaon, Boudha',
      rating_overall: 9.2,
      price_min: 12000,
      data_completeness: 92,
      status: 'pending'
    },
    {
      id: 3,
      name: 'Dwarika\'s Hotel',
      city: 'Kathmandu',
      address: 'Battisputali',
      rating_overall: null,
      price_min: null,
      data_completeness: 45,
      status: 'rejected'
    }
  ],
  pages: 3,
  total: 125
}

const renderComponent = (jobId = '123') => {
  return render(
    <MemoryRouter initialEntries={[`/jobs/${jobId}/results`]}>
      <Routes>
        <Route path="/jobs/:id/results" element={<JobResultsPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('JobResultsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    jobService.getJobStatus.mockResolvedValue(mockJobDetails)
    jobService.getJobResults.mockResolvedValue(mockResults)
  })

  describe('Loading State', () => {
    it('shows loading spinner while fetching results', () => {
      jobService.getJobResults.mockImplementation(() => new Promise(() => {}))

      renderComponent()

      expect(screen.getByText(/loading results/i)).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: /results for/i })).toBeInTheDocument()
    })

    it('displays job location in header during loading', async () => {
      jobService.getJobResults.mockImplementation(() => new Promise(() => {}))

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/results for kathmandu/i)).toBeInTheDocument()
      })
    })
  })

  describe('Success State - Results List', () => {
    it('renders results table with all data', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Hotel Yak & Yeti')).toBeInTheDocument()
      })

      expect(screen.getByText('Hyatt Regency')).toBeInTheDocument()
      expect(screen.getByText('Dwarika\'s Hotel')).toBeInTheDocument()
      expect(screen.getAllByText('Kathmandu')).toHaveLength(3)
    })

    it('displays formatted ratings correctly', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('8.5 / 10')).toBeInTheDocument()
      })

      expect(screen.getByText('9.2 / 10')).toBeInTheDocument()
      expect(screen.getAllByText('N/A')).toHaveLength(2) // null rating and price
    })

    it('displays formatted prices correctly', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('NPR 5,000')).toBeInTheDocument()
      })

      expect(screen.getByText('NPR 12,000')).toBeInTheDocument()
    })

    it('displays all table columns', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Hotel Yak & Yeti')).toBeInTheDocument()
      })

      expect(screen.getByText('Name')).toBeInTheDocument()
      expect(screen.getByText('City')).toBeInTheDocument()
      expect(screen.getByText('Address')).toBeInTheDocument()
      expect(screen.getByText('Rating')).toBeInTheDocument()
      expect(screen.getByText('Price')).toBeInTheDocument()
      expect(screen.getByText('Completeness')).toBeInTheDocument()
      expect(screen.getByText('Status')).toBeInTheDocument()
    })

    it('renders back to job status link', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Hotel Yak & Yeti')).toBeInTheDocument()
      })

      const backLink = screen.getByRole('link', { name: /back to job status/i })
      expect(backLink).toHaveAttribute('href', '/jobs/123')
    })

    it('displays job ID in subtitle', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/viewing results for job #123/i)).toBeInTheDocument()
      })
    })
  })

  describe('Empty State', () => {
    it('shows empty state when no results exist', async () => {
      jobService.getJobResults.mockResolvedValue({
        items: [],
        pages: 1,
        total: 0
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/no results found/i)).toBeInTheDocument()
      })

      expect(screen.getByText(/this job did not return any results/i)).toBeInTheDocument()
    })

    it('displays empty state icon', async () => {
      jobService.getJobResults.mockResolvedValue({
        items: [],
        pages: 1,
        total: 0
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/no results found/i)).toBeInTheDocument()
      })

      // Check for SVG icon
      const svg = document.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })
  })

  describe('Error State', () => {
    it('shows error message when fetch fails', async () => {
      jobService.getJobResults.mockRejectedValue(new Error('API Error'))

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/failed to load results/i)).toBeInTheDocument()
      })
    })

    it('displays back link even in error state', async () => {
      jobService.getJobResults.mockRejectedValue(new Error('API Error'))

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/failed to load results/i)).toBeInTheDocument()
      })

      const backLink = screen.getByRole('link', { name: /back to job status/i })
      expect(backLink).toBeInTheDocument()
    })

    it('handles job details fetch error gracefully', async () => {
      jobService.getJobStatus.mockRejectedValue(new Error('Job not found'))

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Hotel Yak & Yeti')).toBeInTheDocument()
      })

      // Should still show results even if job details fail
      expect(screen.getByText(/results for unspecified location/i)).toBeInTheDocument()
    })
  })

  describe('Pagination', () => {
    it('renders pagination controls when results exist', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Hotel Yak & Yeti')).toBeInTheDocument()
      })

      // PaginationControls component should be rendered
      expect(screen.getByText(/125/)).toBeInTheDocument() // total count
    })

    it('fetches new page when pagination changes', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Hotel Yak & Yeti')).toBeInTheDocument()
      })

      // Initial call with page 1
      expect(jobService.getJobResults).toHaveBeenCalledWith('123', 1, 50)

      // Mock page 2 results
      jobService.getJobResults.mockResolvedValueOnce({
        items: [
          {
            id: 51,
            name: 'Hotel Page 2',
            city: 'Pokhara',
            address: 'Lakeside',
            rating_overall: 7.5,
            price_min: 3000,
            data_completeness: 70,
            validation_status: 'pending'
          }
        ],
        pages: 3,
        total: 125
      })

      // Find and click next page button (assuming PaginationControls renders it)
      const nextButton = screen.getByRole('button', { name: /next/i })
      fireEvent.click(nextButton)

      await waitFor(() => {
        expect(jobService.getJobResults).toHaveBeenCalledWith('123', 2, 50)
      })
    })

    it('does not show pagination for empty results', async () => {
      jobService.getJobResults.mockResolvedValue({
        items: [],
        pages: 1,
        total: 0
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/no results found/i)).toBeInTheDocument()
      })

      // Pagination should not be rendered
      expect(screen.queryByRole('button', { name: /next/i })).not.toBeInTheDocument()
    })
  })

  describe('Data Formatting', () => {
    it('handles missing data fields gracefully', async () => {
      jobService.getJobResults.mockResolvedValue({
        items: [
          {
            id: 1,
            name: null,
            city: null,
            address: null,
            rating_overall: null,
            price_min: null,
            data_completeness: 0,
            validation_status: 'pending'
          }
        ],
        pages: 1,
        total: 1
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getAllByText('N/A')).toHaveLength(5) // name, city, address, rating, price
      })
    })

    it('truncates long addresses', async () => {
      jobService.getJobResults.mockResolvedValue({
        items: [
          {
            id: 1,
            name: 'Test Hotel',
            city: 'Kathmandu',
            address: 'This is a very long address that should be truncated in the table display to prevent layout issues',
            rating_overall: 8.0,
            price_min: 5000,
            data_completeness: 80,
            validation_status: 'pending'
          }
        ],
        pages: 1,
        total: 1
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Test Hotel')).toBeInTheDocument()
      })

      // Address cell should have truncate class
      const addressCell = screen.getByText(/this is a very long address/i).closest('td')
      expect(addressCell).toHaveClass('truncate')
    })

    it('formats decimal ratings to one decimal place', async () => {
      jobService.getJobResults.mockResolvedValue({
        items: [
          {
            id: 1,
            name: 'Test Hotel',
            city: 'Kathmandu',
            address: 'Test Address',
            rating_overall: 8.567,
            price_min: 5000,
            data_completeness: 80,
            validation_status: 'pending'
          }
        ],
        pages: 1,
        total: 1
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('8.6 / 10')).toBeInTheDocument()
      })
    })

    it('formats prices with thousand separators', async () => {
      jobService.getJobResults.mockResolvedValue({
        items: [
          {
            id: 1,
            name: 'Luxury Hotel',
            city: 'Kathmandu',
            address: 'Test Address',
            rating_overall: 9.0,
            price_min: 25000,
            data_completeness: 90,
            validation_status: 'approved'
          }
        ],
        pages: 1,
        total: 1
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('NPR 25,000')).toBeInTheDocument()
      })
    })
  })

  describe('Component Integration', () => {
    it('renders StatusBadge component for each result', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Hotel Yak & Yeti')).toBeInTheDocument()
      })

      // StatusBadge should render status text (mocked component behavior)
      const statusCells = screen.getAllByRole('cell').filter(cell => 
        cell.textContent.includes('approved') || 
        cell.textContent.includes('pending') || 
        cell.textContent.includes('rejected')
      )
      expect(statusCells.length).toBeGreaterThan(0)
    })

    it('renders ProgressBar component for data completeness', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Hotel Yak & Yeti')).toBeInTheDocument()
      })

      // ProgressBar component should be rendered (check for percentage values)
      expect(screen.getByText('85%')).toBeInTheDocument()
      expect(screen.getByText('92%')).toBeInTheDocument()
      expect(screen.getByText('45%')).toBeInTheDocument()
    })
  })
})
