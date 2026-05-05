/* eslint-env vitest */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('renders without crashing', () => {
    render(<App />)
    // App now shows loading state initially (AuthGuard checking auth)
    expect(screen.getByText('Loading...')).toBeInTheDocument()
  })

  it('shows auth guard loading state', () => {
    render(<App />)
    // AuthGuard shows loading spinner while checking authentication
    const loadingText = screen.getByText('Loading...')
    expect(loadingText).toBeInTheDocument()
  })
})