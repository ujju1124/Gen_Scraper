/**
 * Tests for RegisterPage
 * Target: 5.43% → 70%+
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { RegisterPage } from '../RegisterPage'
import { AuthContext } from '../../contexts/AuthContext'

const mockRegister = vi.fn()
const mockNavigate = vi.fn()

// Mock react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate
  }
})

const renderComponent = () => {
  const authValue = {
    register: mockRegister,
    login: vi.fn(),
    logout: vi.fn(),
    user: null,
    loading: false
  }

  return render(
    <AuthContext.Provider value={authValue}>
      <BrowserRouter>
        <RegisterPage />
      </BrowserRouter>
    </AuthContext.Provider>
  )
}

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Form Rendering', () => {
    it('renders registration form with all fields', () => {
      renderComponent()

      expect(screen.getByRole('heading', { name: /create your account/i })).toBeInTheDocument()
      expect(screen.getByLabelText(/email address/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
    })

    it('renders page title and description', () => {
      renderComponent()

      expect(screen.getByText('Web Scraping Portal')).toBeInTheDocument()
      expect(screen.getByText(/professional data collection for nepal business intelligence/i)).toBeInTheDocument()
    })

    it('renders link to login page', () => {
      renderComponent()

      const loginLink = screen.getByRole('link', { name: /sign in/i })
      expect(loginLink).toHaveAttribute('href', '/login')
    })

    it('shows password requirement hint', () => {
      renderComponent()

      expect(screen.getByText(/must be at least 8 characters/i)).toBeInTheDocument()
    })
  })

  describe('Form Validation - Empty Fields', () => {
    it('shows error when email is empty', async () => {
      renderComponent()

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      expect(mockRegister).not.toHaveBeenCalled()
    })

    it('shows error when password is empty', async () => {
      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      expect(screen.getByText(/password is required/i)).toBeInTheDocument()
      expect(mockRegister).not.toHaveBeenCalled()
    })

    it('shows error when confirm password is empty', async () => {
      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
      expect(mockRegister).not.toHaveBeenCalled()
    })
  })

  describe('Form Validation - Email Format', () => {
    it('accepts valid email format', async () => {
      mockRegister.mockResolvedValue({})

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'valid@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'password123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith('valid@example.com', 'password123')
      })
    })
  })

  describe('Form Validation - Password Requirements', () => {
    it('shows error when password is too short', async () => {
      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'short' } })
      fireEvent.change(confirmInput, { target: { value: 'short' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument()
      expect(mockRegister).not.toHaveBeenCalled()
    })

    it('accepts password with 8 characters', async () => {
      mockRegister.mockResolvedValue({})

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: '12345678' } })
      fireEvent.change(confirmInput, { target: { value: '12345678' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalled()
      })
    })
  })

  describe('Form Validation - Password Mismatch', () => {
    it('shows error when passwords do not match', async () => {
      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'different456' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
      expect(mockRegister).not.toHaveBeenCalled()
    })

    it('submits when passwords match', async () => {
      mockRegister.mockResolvedValue({})

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'password123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith('test@example.com', 'password123')
      })
    })
  })

  describe('Successful Registration', () => {
    it('calls register function with correct credentials', async () => {
      mockRegister.mockResolvedValue({})

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'newuser@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'securepass123' } })
      fireEvent.change(confirmInput, { target: { value: 'securepass123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalledWith('newuser@example.com', 'securepass123')
      })
    })

    it('redirects to login page after successful registration', async () => {
      mockRegister.mockResolvedValue({})

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'password123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/login', {
          state: {
            message: 'Registration successful! Please sign in with your credentials.'
          }
        })
      })
    })

    it('shows loading state during registration', async () => {
      mockRegister.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'password123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      expect(screen.getByText(/creating account/i)).toBeInTheDocument()
      expect(submitButton).toBeDisabled()
    })

    it('disables form inputs during registration', async () => {
      mockRegister.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'password123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      expect(emailInput).toBeDisabled()
      expect(passwordInput).toBeDisabled()
      expect(confirmInput).toBeDisabled()
    })
  })

  describe('Registration Errors', () => {
    it('displays error message when registration fails', async () => {
      mockRegister.mockRejectedValue(new Error('Email already exists'))

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'existing@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'password123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/email already exists/i)).toBeInTheDocument()
      })
    })

    it('displays generic error when error has no message', async () => {
      mockRegister.mockRejectedValue(new Error())

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'password123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/registration failed\. please try again\./i)).toBeInTheDocument()
      })
    })

    it('re-enables form after error', async () => {
      mockRegister.mockRejectedValue(new Error('Server error'))

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'password123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/server error/i)).toBeInTheDocument()
      })

      expect(emailInput).not.toBeDisabled()
      expect(passwordInput).not.toBeDisabled()
      expect(confirmInput).not.toBeDisabled()
      expect(submitButton).not.toBeDisabled()
    })

    it('clears previous error when submitting again', async () => {
      mockRegister.mockRejectedValueOnce(new Error('First error'))

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'password123' } })

      const submitButton = screen.getByRole('button', { name: /create account/i })
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.getByText(/first error/i)).toBeInTheDocument()
      })

      // Submit again with success
      mockRegister.mockResolvedValue({})
      fireEvent.click(submitButton)

      await waitFor(() => {
        expect(screen.queryByText(/first error/i)).not.toBeInTheDocument()
      })
    })
  })

  describe('Form Interaction', () => {
    it('allows typing in all input fields', async () => {
      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'mypassword' } })
      fireEvent.change(confirmInput, { target: { value: 'mypassword' } })

      expect(emailInput).toHaveValue('test@example.com')
      expect(passwordInput).toHaveValue('mypassword')
      expect(confirmInput).toHaveValue('mypassword')
    })

    it('submits form on enter key in last field', async () => {
      mockRegister.mockResolvedValue({})

      renderComponent()

      const emailInput = screen.getByLabelText(/email address/i)
      const passwordInput = screen.getByLabelText(/^password$/i)
      const confirmInput = screen.getByLabelText(/confirm password/i)

      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.change(confirmInput, { target: { value: 'password123' } })
      fireEvent.submit(confirmInput.closest('form'))

      await waitFor(() => {
        expect(mockRegister).toHaveBeenCalled()
      })
    })
  })
})
