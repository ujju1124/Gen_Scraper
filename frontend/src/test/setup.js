import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock PNG/image imports for Leaflet
vi.mock('*.png', () => ({
  default: 'test-file-stub',
}))

// Mock CSS imports
vi.mock('*.css', () => ({}))
vi.mock('leaflet/dist/leaflet.css', () => ({}))

// Mock react-leaflet-cluster to avoid PNG require issues
vi.mock('react-leaflet-cluster', () => ({
  default: ({ children }) => children,
}))