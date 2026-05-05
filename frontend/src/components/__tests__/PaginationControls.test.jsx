/**
 * PaginationControls Component Tests
 * Tests button states and click handlers for pagination
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { PaginationControls } from '../PaginationControls'

describe('PaginationControls', () => {
  const defaultProps = {
    currentPage: 1,
    totalPages: 5,
    totalCount: 100,
    onPageChange: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders pagination info correctly', () => {
    render(<PaginationControls {...defaultProps} />)
    
    expect(screen.getByText(/Page 1 of 5/)).toBeInTheDocument()
    expect(screen.getByText(/100 total results/)).toBeInTheDocument()
  })

  it('disables Previous button on first page', () => {
    render(<PaginationControls {...defaultProps} currentPage={1} />)
    
    const prevButton = screen.getByText('Previous')
    expect(prevButton).toBeDisabled()
    expect(prevButton).toHaveClass('disabled:opacity-50')
  })

  it('enables Previous button on pages after first', () => {
    render(<PaginationControls {...defaultProps} currentPage={2} />)
    
    const prevButton = screen.getByText('Previous')
    expect(prevButton).not.toBeDisabled()
  })

  it('disables Next button on last page', () => {
    render(<PaginationControls {...defaultProps} currentPage={5} totalPages={5} />)
    
    const nextButton = screen.getByText('Next')
    expect(nextButton).toBeDisabled()
    expect(nextButton).toHaveClass('disabled:opacity-50')
  })

  it('enables Next button on pages before last', () => {
    render(<PaginationControls {...defaultProps} currentPage={4} totalPages={5} />)
    
    const nextButton = screen.getByText('Next')
    expect(nextButton).not.toBeDisabled()
  })

  it('calls onPageChange with previous page when Previous clicked', () => {
    const onPageChange = vi.fn()
    render(<PaginationControls {...defaultProps} currentPage={3} onPageChange={onPageChange} />)
    
    const prevButton = screen.getByText('Previous')
    fireEvent.click(prevButton)
    
    expect(onPageChange).toHaveBeenCalledWith(2)
    expect(onPageChange).toHaveBeenCalledTimes(1)
  })

  it('calls onPageChange with next page when Next clicked', () => {
    const onPageChange = vi.fn()
    render(<PaginationControls {...defaultProps} currentPage={3} onPageChange={onPageChange} />)
    
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)
    
    expect(onPageChange).toHaveBeenCalledWith(4)
    expect(onPageChange).toHaveBeenCalledTimes(1)
  })

  it('does not call onPageChange when Previous clicked on first page', () => {
    const onPageChange = vi.fn()
    render(<PaginationControls {...defaultProps} currentPage={1} onPageChange={onPageChange} />)
    
    const prevButton = screen.getByText('Previous')
    fireEvent.click(prevButton)
    
    expect(onPageChange).not.toHaveBeenCalled()
  })

  it('does not call onPageChange when Next clicked on last page', () => {
    const onPageChange = vi.fn()
    render(<PaginationControls {...defaultProps} currentPage={5} totalPages={5} onPageChange={onPageChange} />)
    
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)
    
    expect(onPageChange).not.toHaveBeenCalled()
  })

  it('handles single page scenario', () => {
    render(<PaginationControls {...defaultProps} currentPage={1} totalPages={1} totalCount={10} />)
    
    expect(screen.getByText(/Page 1 of 1/)).toBeInTheDocument()
    expect(screen.getByText(/10 total results/)).toBeInTheDocument()
    
    const prevButton = screen.getByText('Previous')
    const nextButton = screen.getByText('Next')
    
    expect(prevButton).toBeDisabled()
    expect(nextButton).toBeDisabled()
  })

  it('handles zero pages scenario', () => {
    render(<PaginationControls {...defaultProps} currentPage={1} totalPages={0} totalCount={0} />)
    
    expect(screen.getByText(/Page 1 of 0/)).toBeInTheDocument()
    expect(screen.getByText(/0 total results/)).toBeInTheDocument()
    
    const prevButton = screen.getByText('Previous')
    const nextButton = screen.getByText('Next')
    
    expect(prevButton).toBeDisabled()
    expect(nextButton).toBeDisabled()
  })

  it('formats large total counts correctly', () => {
    render(<PaginationControls {...defaultProps} totalCount={1234567} />)
    
    expect(screen.getByText(/1,234,567 total results/)).toBeInTheDocument()
  })

  it('handles missing onPageChange prop gracefully', () => {
    const { currentPage, totalPages, totalCount } = defaultProps
    render(<PaginationControls currentPage={currentPage} totalPages={totalPages} totalCount={totalCount} />)
    
    const prevButton = screen.getByText('Previous')
    const nextButton = screen.getByText('Next')
    
    // Should not throw error when clicked without onPageChange
    expect(() => {
      fireEvent.click(prevButton)
      fireEvent.click(nextButton)
    }).not.toThrow()
  })

  it('applies correct CSS classes to buttons', () => {
    render(<PaginationControls {...defaultProps} currentPage={3} />)
    
    const prevButton = screen.getByText('Previous')
    const nextButton = screen.getByText('Next')
    
    expect(prevButton).toHaveClass('btn', 'btn-secondary')
    expect(nextButton).toHaveClass('btn', 'btn-secondary')
  })
})