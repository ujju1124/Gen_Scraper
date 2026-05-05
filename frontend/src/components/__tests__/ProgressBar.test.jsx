/**
 * ProgressBar Component Tests
 * Tests color coding and percentage display for data completeness
 */
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ProgressBar } from '../ProgressBar'

describe('ProgressBar', () => {
  it('renders 0% with red color coding', () => {
    render(<ProgressBar percentage={0} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-red-500')
    
    expect(progressBar).toBeInTheDocument()
    expect(progressBar).toHaveAttribute('aria-valuenow', '0')
    expect(progressBar).toHaveAttribute('aria-valuemin', '0')
    expect(progressBar).toHaveAttribute('aria-valuemax', '100')
    expect(progressFill).toBeInTheDocument()
    expect(progressFill).toHaveStyle({ width: '0%' })
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('renders 25% with red color coding', () => {
    render(<ProgressBar percentage={25} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-red-500')
    
    expect(progressBar).toHaveAttribute('aria-valuenow', '25')
    expect(progressFill).toBeInTheDocument()
    expect(progressFill).toHaveStyle({ width: '25%' })
    expect(screen.getByText('25%')).toBeInTheDocument()
  })

  it('renders 49% with red color coding (boundary test)', () => {
    render(<ProgressBar percentage={49} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-red-500')
    
    expect(progressFill).toBeInTheDocument()
    expect(progressFill).toHaveStyle({ width: '49%' })
    expect(screen.getByText('49%')).toBeInTheDocument()
  })

  it('renders 50% with yellow color coding (boundary test)', () => {
    render(<ProgressBar percentage={50} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-yellow-500')
    
    expect(progressFill).toBeInTheDocument()
    expect(progressFill).toHaveStyle({ width: '50%' })
    expect(screen.getByText('50%')).toBeInTheDocument()
  })

  it('renders 65% with yellow color coding', () => {
    render(<ProgressBar percentage={65} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-yellow-500')
    
    expect(progressFill).toBeInTheDocument()
    expect(progressFill).toHaveStyle({ width: '65%' })
    expect(screen.getByText('65%')).toBeInTheDocument()
  })

  it('renders 80% with green color coding (boundary test)', () => {
    render(<ProgressBar percentage={80} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-green-500') // 80% is green (>= 80)
    
    expect(progressFill).toBeInTheDocument()
    expect(progressFill).toHaveStyle({ width: '80%' })
    expect(screen.getByText('80%')).toBeInTheDocument()
  })

  it('renders 81% with green color coding (boundary test)', () => {
    render(<ProgressBar percentage={81} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-green-500')
    
    expect(progressFill).toBeInTheDocument()
    expect(progressFill).toHaveStyle({ width: '81%' })
    expect(screen.getByText('81%')).toBeInTheDocument()
  })

  it('renders 100% with green color coding', () => {
    render(<ProgressBar percentage={100} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-green-500')
    
    expect(progressFill).toBeInTheDocument()
    expect(progressFill).toHaveStyle({ width: '100%' })
    expect(screen.getByText('100%')).toBeInTheDocument()
  })

  it('handles decimal percentages', () => {
    render(<ProgressBar percentage={67.5} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-yellow-500')
    
    expect(progressBar).toHaveAttribute('aria-valuenow', '67.5')
    expect(progressFill).toHaveStyle({ width: '67.5%' })
    expect(screen.getByText('68%')).toBeInTheDocument() // Rounded display
  })

  it('handles negative percentages as 0%', () => {
    render(<ProgressBar percentage={-10} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-red-500')
    
    expect(progressBar).toHaveAttribute('aria-valuenow', '0')
    expect(progressFill).toHaveStyle({ width: '0%' })
    expect(screen.getByText('-10%')).toBeInTheDocument() // Shows original value but clamps width
  })

  it('handles percentages over 100% as 100%', () => {
    render(<ProgressBar percentage={150} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-green-500')
    
    expect(progressBar).toHaveAttribute('aria-valuenow', '100')
    expect(progressFill).toHaveStyle({ width: '100%' })
    expect(screen.getByText('150%')).toBeInTheDocument() // Shows original value but clamps width
  })

  it('handles undefined percentage as 0%', () => {
    render(<ProgressBar percentage={undefined} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-red-500')
    
    expect(progressBar).toHaveAttribute('aria-valuenow', '0')
    expect(progressFill).toHaveStyle({ width: '0%' })
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('handles null percentage as 0%', () => {
    render(<ProgressBar percentage={null} />)
    const progressBar = screen.getByRole('progressbar')
    const progressFill = progressBar.querySelector('.bg-red-500')
    
    expect(progressBar).toHaveAttribute('aria-valuenow', '0')
    expect(progressFill).toHaveStyle({ width: '0%' })
    expect(screen.getByText('0%')).toBeInTheDocument()
  })
})