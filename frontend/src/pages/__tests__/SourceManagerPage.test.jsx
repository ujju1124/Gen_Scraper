/**
 * Tests for SourceManagerPage
 * Target: 4.18% → 70%+
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { SourceManagerPage } from '../SourceManagerPage'

// Mock fetch globally
global.fetch = vi.fn()

const mockSources = [
  {
    id: 1,
    name: 'booking_com',
    display_name: 'Booking.com',
    category_name: 'Hotels',
    is_active: true
  },
  {
    id: 2,
    name: 'agoda',
    display_name: 'Agoda',
    category_name: 'Hotels',
    is_active: false
  },
  {
    id: 3,
    name: 'nepalyp',
    display_name: 'NepalYP',
    category_name: 'Hotels',
    is_active: true
  }
]

const renderComponent = () => {
  return render(
    <BrowserRouter>
      <SourceManagerPage />
    </BrowserRouter>
  )
}

describe('SourceManagerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Clear any existing toasts
    document.body.innerHTML = ''
  })

  describe('Loading State', () => {
    it('shows loading spinner while fetching sources', () => {
      fetch.mockImplementation(() => new Promise(() => {})) // Never resolves

      renderComponent()

      expect(screen.getByText(/loading sources/i)).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: /source manager/i })).toBeInTheDocument()
    })
  })

  describe('Success State', () => {
    beforeEach(() => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => mockSources
      })
    })

    it('renders page with sources table', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Booking.com')).toBeInTheDocument()
      })

      expect(screen.getByText('Agoda')).toBeInTheDocument()
      expect(screen.getByText('NepalYP')).toBeInTheDocument()
      expect(screen.getAllByText('Hotels')).toHaveLength(3)
    })

    it('displays source status badges correctly', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Booking.com')).toBeInTheDocument()
      })

      const activeStatuses = screen.getAllByText('Active')
      const inactiveStatuses = screen.getAllByText('Inactive')

      expect(activeStatuses).toHaveLength(2) // booking_com and nepalyp
      expect(inactiveStatuses).toHaveLength(1) // agoda
    })

    it('shows empty state when no sources exist', async () => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => []
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/no sources found/i)).toBeInTheDocument()
      })
    })

    it('renders back to admin panel link', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Booking.com')).toBeInTheDocument()
      })

      const backLink = screen.getByRole('link', { name: /back to admin panel/i })
      expect(backLink).toHaveAttribute('href', '/admin')
    })
  })

  describe('Error State', () => {
    it('shows error message when fetch fails', async () => {
      fetch.mockResolvedValue({
        ok: false,
        status: 500
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/failed to load sources/i)).toBeInTheDocument()
      })

      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })

    it('retries fetch when retry button clicked', async () => {
      // First call fails
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500
      })

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/failed to load sources/i)).toBeInTheDocument()
      })

      // Second call succeeds
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockSources
      })

      const retryButton = screen.getByRole('button', { name: /retry/i })
      fireEvent.click(retryButton)

      await waitFor(() => {
        expect(screen.getByText('Booking.com')).toBeInTheDocument()
      })

      expect(fetch).toHaveBeenCalledTimes(2)
    })

    it('handles network error gracefully', async () => {
      fetch.mockRejectedValue(new Error('Network error'))

      renderComponent()

      await waitFor(() => {
        expect(screen.getByText(/failed to load sources/i)).toBeInTheDocument()
      })
    })
  })

  describe('Toggle Source Status', () => {
    beforeEach(() => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => mockSources
      })
    })

    it('toggles source from active to inactive', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Booking.com')).toBeInTheDocument()
      })

      // Mock the PATCH request
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockSources[0], is_active: false })
      })

      // Find the first toggle switch (Booking.com - active)
      const toggleButtons = screen.getAllByRole('button', { name: /disable source/i })
      fireEvent.click(toggleButtons[0])

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          '/api/v1/admin/sources/1',
          expect.objectContaining({
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ is_active: false })
          })
        )
      })

      // Check for success toast
      await waitFor(() => {
        expect(document.body.textContent).toContain('Source updated successfully')
      })
    })

    it('toggles source from inactive to active', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Agoda')).toBeInTheDocument()
      })

      // Mock the PATCH request
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockSources[1], is_active: true })
      })

      // Find the enable toggle (Agoda - inactive)
      const enableButton = screen.getByRole('button', { name: /enable source/i })
      fireEvent.click(enableButton)

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          '/api/v1/admin/sources/2',
          expect.objectContaining({
            method: 'PATCH',
            body: JSON.stringify({ is_active: true })
          })
        )
      })
    })

    it('shows error toast when toggle fails', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Booking.com')).toBeInTheDocument()
      })

      // Mock failed PATCH request
      fetch.mockResolvedValueOnce({
        ok: false,
        status: 500
      })

      const toggleButtons = screen.getAllByRole('button', { name: /disable source/i })
      fireEvent.click(toggleButtons[0])

      await waitFor(() => {
        expect(document.body.textContent).toContain('Failed to update source')
      })
    })

    it('disables toggle button during update', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Booking.com')).toBeInTheDocument()
      })

      // Mock slow PATCH request
      fetch.mockImplementation(() => new Promise(resolve => {
        setTimeout(() => resolve({ ok: true, json: async () => ({}) }), 100)
      }))

      const toggleButtons = screen.getAllByRole('button', { name: /disable source/i })
      const firstToggle = toggleButtons[0]

      fireEvent.click(firstToggle)

      // Button should be disabled during request
      expect(firstToggle).toBeDisabled()
    })
  })

  describe('Toast Notifications', () => {
    beforeEach(() => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => mockSources
      })
    })

    it('shows success toast when toggle succeeds', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Booking.com')).toBeInTheDocument()
      }, { timeout: 10000 })

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({})
      })

      const toggleButtons = screen.getAllByRole('button', { name: /disable source/i })
      fireEvent.click(toggleButtons[0])

      await waitFor(() => {
        expect(document.body.textContent).toContain('Source updated successfully')
      }, { timeout: 10000 })
    })
  })

  describe('Table Display', () => {
    beforeEach(() => {
      fetch.mockResolvedValue({
        ok: true,
        json: async () => mockSources
      })
    })

    it('displays all table columns', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Booking.com')).toBeInTheDocument()
      }, { timeout: 10000 })

      expect(screen.getByText('Source Name')).toBeInTheDocument()
      expect(screen.getByText('Category')).toBeInTheDocument()
      expect(screen.getByText('Status')).toBeInTheDocument()
      expect(screen.getByText('Actions')).toBeInTheDocument()
    })

    it('displays source display name and internal name', async () => {
      renderComponent()

      await waitFor(() => {
        expect(screen.getByText('Booking.com')).toBeInTheDocument()
      }, { timeout: 10000 })

      expect(screen.getByText('booking_com')).toBeInTheDocument()
      expect(screen.getByText('Agoda')).toBeInTheDocument()
      expect(screen.getByText('agoda')).toBeInTheDocument()
    })
  })
})
