/**
 * Tests for MapView Component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MapView } from '../MapView'

// Mock react-leaflet components
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }) => <div data-testid="map-container">{children}</div>,
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({ children, title }) => (
    <div data-testid="marker" data-title={title}>
      {children}
    </div>
  ),
  Popup: ({ children }) => <div data-testid="popup">{children}</div>,
  useMap: () => ({
    fitBounds: vi.fn(),
  }),
}))

// Mock react-leaflet-cluster - override global mock with testid for assertions
vi.mock('react-leaflet-cluster', () => ({
  default: ({ children }) => <div data-testid="marker-cluster-group">{children}</div>,
}))

// Mock leaflet
vi.mock('leaflet', () => ({
  default: {
    Icon: {
      Default: {
        prototype: {
          _getIconUrl: vi.fn(),
        },
        mergeOptions: vi.fn(),
      },
    },
    latLngBounds: vi.fn(() => ({
      isValid: () => true,
    })),
  },
}))

describe('MapView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders empty state when no results provided', () => {
    render(<MapView results={[]} />)

    expect(screen.getByText('No data to display')).toBeInTheDocument()
    expect(screen.getByText('No results available to show on the map')).toBeInTheDocument()
  })

  it('renders empty state when results array is empty', () => {
    render(<MapView results={[]} height={500} />)

    const emptyState = screen.getByText('No data to display')
    expect(emptyState).toBeInTheDocument()
  })

  it('renders no coordinates message when all results lack coordinates', () => {
    const resultsWithoutCoords = [
      { id: 1, name: 'Business 1', latitude: null, longitude: null },
      { id: 2, name: 'Business 2', latitude: undefined, longitude: undefined },
      { id: 3, name: 'Business 3' },
    ]

    render(<MapView results={resultsWithoutCoords} />)

    expect(screen.getByText('No coordinates available')).toBeInTheDocument()
    expect(screen.getByText('3 results without valid location data')).toBeInTheDocument()
  })

  it('renders map container when valid coordinates exist', () => {
    const validResults = [
      {
        id: 1,
        name: 'Hotel ABC',
        latitude: 27.7172,
        longitude: 85.324,
        address: '123 Main St',
        city: 'Kathmandu',
      },
    ]

    render(<MapView results={validResults} />)

    expect(screen.getByTestId('map-container')).toBeInTheDocument()
    expect(screen.getByTestId('tile-layer')).toBeInTheDocument()
    expect(screen.getByTestId('marker-cluster-group')).toBeInTheDocument()
  })

  it('renders markers for each valid result', () => {
    const validResults = [
      {
        id: 1,
        name: 'Hotel ABC',
        latitude: 27.7172,
        longitude: 85.324,
      },
      {
        id: 2,
        name: 'Hotel XYZ',
        latitude: 27.7,
        longitude: 85.3,
      },
    ]

    render(<MapView results={validResults} />)

    const markers = screen.getAllByTestId('marker')
    expect(markers).toHaveLength(2)
    expect(markers[0]).toHaveAttribute('data-title', 'Hotel ABC')
    expect(markers[1]).toHaveAttribute('data-title', 'Hotel XYZ')
  })

  it('filters out results with invalid coordinates', () => {
    const mixedResults = [
      { id: 1, name: 'Valid 1', latitude: 27.7172, longitude: 85.324 },
      { id: 2, name: 'Invalid - null', latitude: null, longitude: null },
      { id: 3, name: 'Invalid - NaN', latitude: NaN, longitude: NaN },
      { id: 4, name: 'Invalid - out of range', latitude: 100, longitude: 200 },
      { id: 5, name: 'Valid 2', latitude: 27.7, longitude: 85.3 },
    ]

    render(<MapView results={mixedResults} />)

    const markers = screen.getAllByTestId('marker')
    expect(markers).toHaveLength(2)
  })

  it('shows skipped count message when some results lack coordinates', () => {
    const mixedResults = [
      { id: 1, name: 'Valid', latitude: 27.7172, longitude: 85.324 },
      { id: 2, name: 'Invalid', latitude: null, longitude: null },
      { id: 3, name: 'Invalid 2', latitude: undefined, longitude: undefined },
    ]

    render(<MapView results={mixedResults} />)

    expect(screen.getByText(/Showing 1 location on map/)).toBeInTheDocument()
    expect(screen.getByText(/2 results without coordinates/)).toBeInTheDocument()
  })

  it('renders popup with business details', () => {
    const result = {
      id: 1,
      name: 'Hotel ABC',
      latitude: 27.7172,
      longitude: 85.324,
      address: '123 Main St',
      city: 'Kathmandu',
      phone_primary: '123-456-7890',
      rating_overall: 8.5,
      price_min: 5000,
    }

    render(<MapView results={[result]} />)

    expect(screen.getByText('Hotel ABC')).toBeInTheDocument()
    expect(screen.getByText('123 Main St')).toBeInTheDocument()
    expect(screen.getByText('Kathmandu')).toBeInTheDocument()
    expect(screen.getByText('123-456-7890')).toBeInTheDocument()
  })

  it('handles missing optional fields in popup', () => {
    const minimalResult = {
      id: 1,
      name: 'Minimal Business',
      latitude: 27.7172,
      longitude: 85.324,
    }

    render(<MapView results={[minimalResult]} />)

    expect(screen.getByText('Minimal Business')).toBeInTheDocument()
    // Should not crash when optional fields are missing
    expect(screen.queryByText('Address:')).not.toBeInTheDocument()
  })

  it('uses custom height prop', () => {
    const validResults = [
      { id: 1, name: 'Hotel', latitude: 27.7172, longitude: 85.324 },
    ]

    const { container } = render(<MapView results={validResults} height={800} />)

    const mapWrapper = container.querySelector('[style*="height: 800px"]')
    expect(mapWrapper).toBeInTheDocument()
  })

  it('uses default height when not specified', () => {
    const validResults = [
      { id: 1, name: 'Hotel', latitude: 27.7172, longitude: 85.324 },
    ]

    const { container } = render(<MapView results={validResults} />)

    const mapWrapper = container.querySelector('[style*="height: 600px"]')
    expect(mapWrapper).toBeInTheDocument()
  })

  it('validates latitude range (-90 to 90)', () => {
    const results = [
      { id: 1, name: 'Valid', latitude: 27.7172, longitude: 85.324 },
      { id: 2, name: 'Too high', latitude: 91, longitude: 85.324 },
      { id: 3, name: 'Too low', latitude: -91, longitude: 85.324 },
    ]

    render(<MapView results={results} />)

    const markers = screen.getAllByTestId('marker')
    expect(markers).toHaveLength(1) // Only the valid one
  })

  it('validates longitude range (-180 to 180)', () => {
    const results = [
      { id: 1, name: 'Valid', latitude: 27.7172, longitude: 85.324 },
      { id: 2, name: 'Too high', latitude: 27.7172, longitude: 181 },
      { id: 3, name: 'Too low', latitude: 27.7172, longitude: -181 },
    ]

    render(<MapView results={results} />)

    const markers = screen.getAllByTestId('marker')
    expect(markers).toHaveLength(1) // Only the valid one
  })

  it('renders marker cluster group for clustering functionality', () => {
    const validResults = [
      { id: 1, name: 'Hotel 1', latitude: 27.7172, longitude: 85.324 },
      { id: 2, name: 'Hotel 2', latitude: 27.7173, longitude: 85.325 },
    ]

    render(<MapView results={validResults} />)

    expect(screen.getByTestId('marker-cluster-group')).toBeInTheDocument()
  })

  it('handles singular vs plural in skipped count message', () => {
    const results = [
      { id: 1, name: 'Valid', latitude: 27.7172, longitude: 85.324 },
      { id: 2, name: 'Invalid', latitude: null, longitude: null },
    ]

    render(<MapView results={results} />)

    // Should say "1 location" (singular) and "1 result" (singular)
    expect(screen.getByText(/Showing 1 location on map/)).toBeInTheDocument()
    expect(screen.getByText(/1 result without coordinates/)).toBeInTheDocument()
  })
})
