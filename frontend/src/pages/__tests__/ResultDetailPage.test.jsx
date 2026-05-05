/**
 * Tests for ResultDetailPage
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { ResultDetailPage } from '../ResultDetailPage'
import * as jobService from '../../services/jobService'

// Mock the jobService
vi.mock('../../services/jobService')

// Mock useParams and useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => ({ id: 'test-result-id-123' }),
    useNavigate: () => mockNavigate,
  }
})

// Mock MapView component
vi.mock('../../components/MapView', () => ({
  MapView: ({ results }) => (
    <div data-testid="map-view">Map with {results.length} result(s)</div>
  ),
}))

describe('ResultDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockResult = {
    id: 'test-result-id-123',
    name: 'Test Hotel',
    brand: 'Test Brand',
    property_type: 'Hotel',
    star_rating: 4,
    address: '123 Test Street, Thamel',
    street_address: '123 Test Street',
    city: 'Kathmandu',
    district: 'Kathmandu',
    latitude: 27.7172,
    longitude: 85.324,
    phone_primary: '+977-1-4123456',
    phone_secondary: '+977-9841234567',
    email: 'info@testhotel.com',
    website: 'https://testhotel.com',
    price_min: 5000.0,
    price_max: 10000.0,
    currency: 'NPR',
    includes_breakfast: true,
    rating_overall: 8.5,
    review_count: 250,
    rating_cleanliness: 8.7,
    rating_location: 9.0,
    rating_facilities: 8.3,
    amenities: ['WiFi', 'Parking', 'Restaurant', 'Pool'],
    pets_allowed: false,
    checkin_time: '14:00',
    checkout_time: '12:00',
    data_completeness: 85.5,
    status: 'PENDING',
    is_edited: false,
    is_duplicate: false,
    source_url: 'https://example.com/listing/123',
  }

  it('renders loading state while fetching', () => {
    jobService.getResultDetail.mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    expect(screen.getByText('Loading details...')).toBeInTheDocument()
    expect(screen.getByText('Result Details')).toBeInTheDocument()
  })

  it('renders all field groups when data loads', async () => {
    jobService.getResultDetail.mockResolvedValue(mockResult)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    // Check section headers exist
    expect(screen.getByRole('heading', { name: 'Identity' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Location' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Contact' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Pricing' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Reviews' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Facilities' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Data Quality' })).toBeInTheDocument()

    // Check some key values (use getAllByText for values that appear multiple times)
    expect(screen.getByText('Test Brand')).toBeInTheDocument()
    expect(screen.getAllByText('Kathmandu').length).toBeGreaterThan(0)
    expect(screen.getByText('+977-1-4123456')).toBeInTheDocument()
    expect(screen.getByText('info@testhotel.com')).toBeInTheDocument()
  })

  it('shows "Not available" for null fields', async () => {
    const resultWithNulls = {
      ...mockResult,
      brand: null,
      phone_secondary: null,
      email: null,
      rating_cleanliness: null,
    }

    jobService.getResultDetail.mockResolvedValue(resultWithNulls)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    // Should show "Not available" for null fields
    const notAvailableElements = screen.getAllByText('Not available')
    expect(notAvailableElements.length).toBeGreaterThan(0)
  })

  it('back button calls navigate(-1)', async () => {
    jobService.getResultDetail.mockResolvedValue(mockResult)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    const backButtons = screen.getAllByText('Back to Results')
    backButtons[0].click()

    expect(mockNavigate).toHaveBeenCalledWith(-1)
  })

  it('MapView renders when lat/lng present', async () => {
    jobService.getResultDetail.mockResolvedValue(mockResult)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    // Map should be rendered
    expect(screen.getByTestId('map-view')).toBeInTheDocument()
    expect(screen.getByText('Map with 1 result(s)')).toBeInTheDocument()
  })

  it('MapView hidden when lat/lng missing', async () => {
    const resultWithoutCoords = {
      ...mockResult,
      latitude: null,
      longitude: null,
    }

    jobService.getResultDetail.mockResolvedValue(resultWithoutCoords)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    // Map should not be rendered
    expect(screen.queryByTestId('map-view')).not.toBeInTheDocument()
    expect(screen.getByText('Not available')).toBeInTheDocument()
  })

  it('shows 404 error state when result not found', async () => {
    jobService.getResultDetail.mockRejectedValue({ status: 404 })

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Result not found')).toBeInTheDocument()
    })
  })

  it('shows generic error for other failures', async () => {
    jobService.getResultDetail.mockRejectedValue({ status: 500 })

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Failed to load result details')).toBeInTheDocument()
    })
  })

  it('renders amenities as tags', async () => {
    jobService.getResultDetail.mockResolvedValue(mockResult)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    // Check amenities are rendered
    expect(screen.getByText('WiFi')).toBeInTheDocument()
    expect(screen.getByText('Parking')).toBeInTheDocument()
    expect(screen.getByText('Restaurant')).toBeInTheDocument()
    expect(screen.getByText('Pool')).toBeInTheDocument()
  })

  it('renders website as clickable link', async () => {
    jobService.getResultDetail.mockResolvedValue(mockResult)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    const websiteLink = screen.getByText('https://testhotel.com')
    expect(websiteLink).toHaveAttribute('href', 'https://testhotel.com')
    expect(websiteLink).toHaveAttribute('target', '_blank')
  })

  it('renders source URL as clickable link', async () => {
    jobService.getResultDetail.mockResolvedValue(mockResult)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    const sourceLink = screen.getByText('View Source')
    expect(sourceLink).toHaveAttribute('href', 'https://example.com/listing/123')
    expect(sourceLink).toHaveAttribute('target', '_blank')
  })

  it('formats prices correctly', async () => {
    jobService.getResultDetail.mockResolvedValue(mockResult)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    // Check price formatting
    expect(screen.getByText('NPR 5,000')).toBeInTheDocument()
    expect(screen.getByText('NPR 10,000')).toBeInTheDocument()
  })

  it('formats ratings correctly', async () => {
    jobService.getResultDetail.mockResolvedValue(mockResult)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    // Check rating formatting
    expect(screen.getByText('8.5 / 10')).toBeInTheDocument()
    expect(screen.getByText('8.7 / 10')).toBeInTheDocument()
    expect(screen.getByText('9.0 / 10')).toBeInTheDocument()
  })

  it('formats boolean values correctly', async () => {
    jobService.getResultDetail.mockResolvedValue(mockResult)

    render(
      <BrowserRouter>
        <ResultDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const hotelNames = screen.getAllByText('Test Hotel')
      expect(hotelNames.length).toBeGreaterThan(0)
    })

    // Check boolean formatting
    const yesElements = screen.getAllByText('Yes')
    const noElements = screen.getAllByText('No')
    
    expect(yesElements.length).toBeGreaterThan(0) // includes_breakfast is true
    expect(noElements.length).toBeGreaterThan(0) // pets_allowed is false
  })
})
