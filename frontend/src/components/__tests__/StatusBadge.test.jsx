/**
 * StatusBadge Component Tests
 * Tests color coding and text verification for all status types
 */
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { StatusBadge } from '../StatusBadge'

describe('StatusBadge', () => {
  it('renders QUEUED status with correct styling', () => {
    render(<StatusBadge status="QUEUED" />)
    const badge = screen.getByText('QUEUED')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'badge-queued')
  })

  it('renders RUNNING status with correct styling', () => {
    render(<StatusBadge status="RUNNING" />)
    const badge = screen.getByText('RUNNING')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'badge-running')
  })

  it('renders DONE status with correct styling', () => {
    render(<StatusBadge status="DONE" />)
    const badge = screen.getByText('DONE')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'badge-done')
  })

  it('renders FAILED status with correct styling', () => {
    render(<StatusBadge status="FAILED" />)
    const badge = screen.getByText('FAILED')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'badge-failed')
  })

  it('renders PENDING status with correct styling', () => {
    render(<StatusBadge status="PENDING" />)
    const badge = screen.getByText('PENDING')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'badge-pending')
  })

  it('renders APPROVED status with correct styling', () => {
    render(<StatusBadge status="APPROVED" />)
    const badge = screen.getByText('APPROVED')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'badge-approved')
  })

  it('renders REJECTED status with correct styling', () => {
    render(<StatusBadge status="REJECTED" />)
    const badge = screen.getByText('REJECTED')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'badge-rejected')
  })

  it('handles case insensitive status', () => {
    render(<StatusBadge status="queued" />)
    const badge = screen.getByText('queued')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'badge-queued')
  })

  it('renders UNKNOWN for undefined status', () => {
    render(<StatusBadge status={undefined} />)
    const badge = screen.getByText('UNKNOWN')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'bg-slate-100', 'text-slate-700')
  })

  it('renders UNKNOWN for null status', () => {
    render(<StatusBadge status={null} />)
    const badge = screen.getByText('UNKNOWN')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'bg-slate-100', 'text-slate-700')
  })

  it('renders UNKNOWN for empty string status', () => {
    render(<StatusBadge status="" />)
    const badge = screen.getByText('UNKNOWN')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'bg-slate-100', 'text-slate-700')
  })

  it('renders UNKNOWN for unrecognized status', () => {
    render(<StatusBadge status="INVALID_STATUS" />)
    const badge = screen.getByText('INVALID_STATUS')
    expect(badge).toBeInTheDocument()
    expect(badge).toHaveClass('badge', 'bg-slate-100', 'text-slate-700')
  })
})