/**
 * Login Flow Integration Test
 * Tests complete login flow: form submission → API call → state update → redirect
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuthProvider } from '../../contexts/AuthContext'
import { LoginPage } from '../../pages/LoginPage'
import * as authService from '../../services/authService'

// Mock the auth service
vi.mock('../../services/authService')

// Mock react-router-dom navigate
const mockNavigate = vi.fn()
const mockUseLocation = vi.fn()

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => mockUseLocation()
  }
})

// Test wrapper component
function TestWrapper({ children }) {
  return (
    <BrowserRouter>
      <AuthProvider>
        {children}
      </AuthProvider>
    </BrowserRouter>
  )
}

describe('Login Flow Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default location mock
    mockUseLocation.mockReturnValue({ state: null })
  })

  it('completes successful login flow with form submission, API call, state update, and redirect', async () => {
    // Mock successful login response
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      role: 'user'
    }
    
    authService.login.mockResolvedValue(mockUser)
    authService.getCurrentUser.mockResolvedValue(mockUser)

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    // Verify form elements are present
    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    expect(emailInput).toBeInTheDocument()
    expect(passwordInput).toBeInTheDocument()
    expect(submitButton).toBeInTheDocument()
    expect(submitButton).not.toBeDisabled()

    // Fill out the form
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })

    // Verify form validation passes
    expect(emailInput.value).toBe('test@example.com')
    expect(passwordInput.value).toBe('password123')

    // Submit the form
    fireEvent.click(submitButton)

    // Verify loading state is shown
    await waitFor(() => {
      expect(submitButton).toBeDisabled()
      expect(screen.getByText(/signing in/i)).toBeInTheDocument()
    })

    // Verify API call was made with correct parameters
    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith('test@example.com', 'password123')
      expect(authService.login).toHaveBeenCalledTimes(1)
    })

    // Verify redirect to dashboard occurs
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })
  })

  it('handles login failure with error display', async () => {
    // Mock failed login response
    const errorMessage = 'Invalid email or password'
    authService.login.mockRejectedValue(new Error(errorMessage))

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    // Fill out the form with invalid credentials
    fireEvent.change(emailInput, { target: { value: 'invalid@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } })

    // Submit the form
    fireEvent.click(submitButton)

    // Verify loading state
    await waitFor(() => {
      expect(submitButton).toBeDisabled()
    })

    // Verify API call was made
    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith('invalid@example.com', 'wrongpassword')
    })

    // Verify error message is displayed
    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
    })

    // Verify form is re-enabled after error
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled()
      expect(submitButton).toHaveTextContent('Sign in')
    })

    // Verify no redirect occurred
    expect(mockNavigate).not.toHaveBeenCalled()
  })

  it('handles network errors gracefully', async () => {
    // Mock network error
    authService.login.mockRejectedValue(new Error('Network error. Please check your connection.'))

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    // Fill out and submit form
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    fireEvent.click(submitButton)

    // Verify network error is displayed
    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument()
    })

    // Verify form is re-enabled
    await waitFor(() => {
      expect(submitButton).not.toBeDisabled()
    })
  })

  it('validates empty email field', async () => {
    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const submitButton = screen.getByRole('button', { name: /sign in/i })

    // Try to submit with empty fields
    fireEvent.click(submitButton)

    // Verify validation error for empty email
    await waitFor(() => {
      expect(screen.getByText('Email is required')).toBeInTheDocument()
    })

    // Verify no API call was made
    expect(authService.login).not.toHaveBeenCalled()
  })

  it('redirects to original path after login when coming from AuthGuard', async () => {
    // Mock successful login
    const mockUser = { id: 1, email: 'test@example.com', role: 'user' }
    authService.login.mockResolvedValue(mockUser)
    authService.getCurrentUser.mockResolvedValue(mockUser)

    // Mock location state with original path
    mockUseLocation.mockReturnValue({
      state: { from: '/admin' }
    })

    render(
      <TestWrapper>
        <LoginPage />
      </TestWrapper>
    )

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    // Complete login flow
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    fireEvent.click(submitButton)

    // Verify redirect to original path
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/admin', { replace: true })
    })
  })
})