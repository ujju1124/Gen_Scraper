/**
 * Tests for UserManagementPage
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { UserManagementPage } from '../UserManagementPage'
import * as adminService from '../../services/adminService'
import * as useAuthHook from '../../hooks/useAuth'

// Mock services
vi.mock('../../services/adminService')
vi.mock('../../hooks/useAuth')

const mockUsers = {
  items: [
    {
      id: 1,
      email: 'admin@example.com',
      role: 'admin',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z'
    },
    {
      id: 2,
      email: 'user@example.com',
      role: 'user',
      is_active: true,
      created_at: '2024-01-02T00:00:00Z'
    },
    {
      id: 3,
      email: 'inactive@example.com',
      role: 'user',
      is_active: false,
      created_at: '2024-01-03T00:00:00Z'
    }
  ],
  total: 3,
  page: 1,
  page_size: 20,
  pages: 1
}

const renderUserManagementPage = (currentUser = { id: 1, email: 'admin@example.com', role: 'admin' }) => {
  useAuthHook.useAuth.mockReturnValue({ user: currentUser })
  
  return render(
    <BrowserRouter>
      <UserManagementPage />
    </BrowserRouter>
  )
}

describe('UserManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    adminService.getUsers.mockResolvedValue(mockUsers)
  })

  it('renders loading state while fetching users', () => {
    adminService.getUsers.mockImplementation(() => new Promise(() => {})) // Never resolves
    
    renderUserManagementPage()
    
    expect(screen.getByText('Loading users...')).toBeInTheDocument()
  })

  it('renders user table with all users', async () => {
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    })
    
    expect(screen.getByText('user@example.com')).toBeInTheDocument()
    expect(screen.getByText('inactive@example.com')).toBeInTheDocument()
    expect(screen.getByText('3 users found')).toBeInTheDocument()
  })

  it('shows role badges correctly', async () => {
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    })
    
    const roleBadges = screen.getAllByText(/admin|user/)
    expect(roleBadges.length).toBeGreaterThan(0)
  })

  it('shows status badges correctly', async () => {
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    })
    
    const activeBadges = screen.getAllByText('Active')
    const inactiveBadges = screen.getAllByText('Inactive')
    
    expect(activeBadges.length).toBe(2) // admin and user
    expect(inactiveBadges.length).toBe(1) // inactive user
  })

  it('shows (You) indicator for current user', async () => {
    renderUserManagementPage({ id: 1, email: 'admin@example.com', role: 'admin' })
    
    await waitFor(() => {
      expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    })
    
    expect(screen.getByText('(You)')).toBeInTheDocument()
  })

  it('calls updateUserStatus when deactivate button clicked', async () => {
    adminService.updateUserStatus.mockResolvedValue({
      id: 2,
      email: 'user@example.com',
      role: 'user',
      is_active: false,
      created_at: '2024-01-02T00:00:00Z'
    })
    
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('user@example.com')).toBeInTheDocument()
    })
    
    // Find deactivate buttons (there should be 2 for active users)
    const deactivateButtons = screen.getAllByText('Deactivate')
    
    // Click the first deactivate button (for user@example.com)
    fireEvent.click(deactivateButtons[1])
    
    await waitFor(() => {
      expect(adminService.updateUserStatus).toHaveBeenCalledWith(2, false)
    })
  })

  it('calls updateUserStatus when activate button clicked', async () => {
    adminService.updateUserStatus.mockResolvedValue({
      id: 3,
      email: 'inactive@example.com',
      role: 'user',
      is_active: true,
      created_at: '2024-01-03T00:00:00Z'
    })
    
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('inactive@example.com')).toBeInTheDocument()
    })
    
    const activateButton = screen.getByText('Activate')
    fireEvent.click(activateButton)
    
    await waitFor(() => {
      expect(adminService.updateUserStatus).toHaveBeenCalledWith(3, true)
    })
  })

  it('disables deactivate button for current admin user', async () => {
    renderUserManagementPage({ id: 1, email: 'admin@example.com', role: 'admin' })
    
    await waitFor(() => {
      expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    })
    
    const deactivateButtons = screen.getAllByText('Deactivate')
    
    // First deactivate button should be disabled (for current admin)
    expect(deactivateButtons[0]).toBeDisabled()
  })

  it('shows error message when fetch fails', async () => {
    adminService.getUsers.mockRejectedValue(new Error('Failed to fetch'))
    
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('Failed to load users')).toBeInTheDocument()
    })
  })

  it('shows empty state when no users found', async () => {
    adminService.getUsers.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      pages: 0
    })
    
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('No users found')).toBeInTheDocument()
    })
  })

  it('shows processing state during status update', async () => {
    adminService.updateUserStatus.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve({
        id: 2,
        email: 'user@example.com',
        role: 'user',
        is_active: false,
        created_at: '2024-01-02T00:00:00Z'
      }), 100))
    )
    
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('user@example.com')).toBeInTheDocument()
    })
    
    const deactivateButtons = screen.getAllByText('Deactivate')
    fireEvent.click(deactivateButtons[1])
    
    await waitFor(() => {
      expect(screen.getByText('Processing...')).toBeInTheDocument()
    })
  })

  it('handles status update error gracefully', async () => {
    adminService.updateUserStatus.mockRejectedValue({
      response: { data: { detail: 'Cannot deactivate your own account' } }
    })
    
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('user@example.com')).toBeInTheDocument()
    })
    
    const deactivateButtons = screen.getAllByText('Deactivate')
    fireEvent.click(deactivateButtons[1])
    
    // Error should be handled (no crash)
    await waitFor(() => {
      expect(adminService.updateUserStatus).toHaveBeenCalled()
    })
  })

  it('shows pagination controls when multiple pages', async () => {
    adminService.getUsers.mockResolvedValue({
      ...mockUsers,
      pages: 3,
      page: 1
    })
    
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    })
    
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
    expect(screen.getByText('Previous')).toBeInTheDocument()
    expect(screen.getByText('Next')).toBeInTheDocument()
  })

  it('handles pagination correctly', async () => {
    adminService.getUsers.mockResolvedValue({
      ...mockUsers,
      pages: 2,
      page: 1
    })
    
    renderUserManagementPage()
    
    await waitFor(() => {
      expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    })
    
    const nextButton = screen.getByText('Next')
    fireEvent.click(nextButton)
    
    await waitFor(() => {
      expect(adminService.getUsers).toHaveBeenCalledWith({ page: 2, page_size: 20 })
    })
  })
})
