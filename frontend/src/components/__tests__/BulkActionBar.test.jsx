/**
 * Tests for BulkActionBar Component
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BulkActionBar } from '../BulkActionBar'

describe('BulkActionBar', () => {
  it('renders nothing when selectedCount is 0', () => {
    const { container } = render(
      <BulkActionBar
        selectedCount={0}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onClear={vi.fn()}
        isProcessing={false}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it('shows count and buttons when rows selected', () => {
    render(
      <BulkActionBar
        selectedCount={3}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onClear={vi.fn()}
        isProcessing={false}
      />
    )
    
    expect(screen.getByText('3 results selected')).toBeInTheDocument()
    expect(screen.getByText('Approve Selected (3)')).toBeInTheDocument()
    expect(screen.getByText('Reject Selected (3)')).toBeInTheDocument()
    expect(screen.getByText('Clear Selection')).toBeInTheDocument()
  })

  it('shows singular form when one row selected', () => {
    render(
      <BulkActionBar
        selectedCount={1}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onClear={vi.fn()}
        isProcessing={false}
      />
    )
    
    expect(screen.getByText('1 result selected')).toBeInTheDocument()
  })

  it('shows processing state', () => {
    render(
      <BulkActionBar
        selectedCount={2}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onClear={vi.fn()}
        isProcessing={true}
      />
    )
    
    // Should show "Processing..." text
    const processingTexts = screen.getAllByText('Processing...')
    expect(processingTexts.length).toBeGreaterThan(0)
    
    // Buttons should be disabled
    const buttons = screen.getAllByRole('button')
    const approveButton = buttons.find(btn => btn.textContent.includes('Processing'))
    const rejectButton = buttons.find(btn => btn.textContent.includes('Processing') && btn !== approveButton)
    
    expect(approveButton).toBeDisabled()
    expect(rejectButton).toBeDisabled()
  })

  it('calls onApprove when approve button clicked', () => {
    const onApprove = vi.fn()
    render(
      <BulkActionBar
        selectedCount={1}
        onApprove={onApprove}
        onReject={vi.fn()}
        onClear={vi.fn()}
        isProcessing={false}
      />
    )
    
    const approveButton = screen.getByText('Approve Selected (1)')
    fireEvent.click(approveButton)
    
    expect(onApprove).toHaveBeenCalledOnce()
  })

  it('calls onReject when reject button clicked', () => {
    const onReject = vi.fn()
    render(
      <BulkActionBar
        selectedCount={1}
        onApprove={vi.fn()}
        onReject={onReject}
        onClear={vi.fn()}
        isProcessing={false}
      />
    )
    
    const rejectButton = screen.getByText('Reject Selected (1)')
    fireEvent.click(rejectButton)
    
    expect(onReject).toHaveBeenCalledOnce()
  })

  it('calls onClear when clear selection button clicked', () => {
    const onClear = vi.fn()
    render(
      <BulkActionBar
        selectedCount={5}
        onApprove={vi.fn()}
        onReject={vi.fn()}
        onClear={onClear}
        isProcessing={false}
      />
    )
    
    const clearButton = screen.getByText('Clear Selection')
    fireEvent.click(clearButton)
    
    expect(onClear).toHaveBeenCalledOnce()
  })

  it('does not call handlers when buttons are disabled', () => {
    const onApprove = vi.fn()
    const onReject = vi.fn()
    
    render(
      <BulkActionBar
        selectedCount={2}
        onApprove={onApprove}
        onReject={onReject}
        onClear={vi.fn()}
        isProcessing={true}
      />
    )
    
    const buttons = screen.getAllByRole('button')
    const approveButton = buttons.find(btn => btn.textContent.includes('Processing'))
    const rejectButton = buttons.find(btn => btn.textContent.includes('Processing') && btn !== approveButton)
    
    fireEvent.click(approveButton)
    fireEvent.click(rejectButton)
    
    // Handlers should not be called when disabled
    expect(onApprove).not.toHaveBeenCalled()
    expect(onReject).not.toHaveBeenCalled()
  })
})
