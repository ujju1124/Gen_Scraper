/**
 * Tests for Navigation Component
 * Target: 5.98% → 70%+
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, within, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { Navigation } from '../Navigation'
import { AuthContext } from '../../../contexts/AuthContext'

const mockLogout = vi.fn()

const renderWithAuth = (user = null, pathname = '/dashboard') => {
  const authValue = {
    user,
    logout: mockLogout,
    login: vi.fn(),
    register: vi.fn(),
    loading: false
  }

  // Mock useLocation
  window.history.pushState({}, '', pathname)

  return render(
    <AuthContext.Provider value={authValue}>
      <BrowserRouter>
        <Navigation />
      </BrowserRouter>
    </AuthContext.Provider>
  )
}

describe('Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Basic Rendering', () => {
    it('renders navigation bar with logo', () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      expect(screen.getByText('Web Scraping Portal')).toBeInTheDocument()
    })

    it('renders dashboard link', () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
      expect(dashboardLink).toHaveAttribute('href', '/dashboard')
    })

    it('displays user email', () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      expect(screen.getByText('user@example.com')).toBeInTheDocument()
    })

    it('renders logout button', () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
    })
  })

  describe('Admin Role Visibility', () => {
    it('shows admin panel link for admin users', () => {
      renderWithAuth({ email: 'admin@example.com', role: 'admin' })

      const adminLink = screen.getByRole('link', { name: /admin panel/i })
      expect(adminLink).toBeInTheDocument()
      expect(adminLink).toHaveAttribute('href', '/admin')
    })

    it('hides admin panel link for regular users', () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      expect(screen.queryByRole('link', { name: /admin panel/i })).not.toBeInTheDocument()
    })

    it('hides admin panel link when user is null', () => {
      renderWithAuth(null)

      expect(screen.queryByRole('link', { name: /admin panel/i })).not.toBeInTheDocument()
    })
  })

  describe('Active Link Highlighting', () => {
    it('highlights dashboard link when on dashboard page', () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' }, '/dashboard')

      const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
      expect(dashboardLink).toHaveClass('bg-slate-100', 'text-slate-900')
    })

    it('does not highlight dashboard link when on other page', () => {
      renderWithAuth({ email: 'admin@example.com', role: 'admin' }, '/admin')

      const dashboardLink = screen.getByRole('link', { name: /dashboard/i })
      expect(dashboardLink).toHaveClass('text-slate-600')
      expect(dashboardLink).not.toHaveClass('bg-slate-100')
    })

    it('highlights admin panel link when on admin page', () => {
      renderWithAuth({ email: 'admin@example.com', role: 'admin' }, '/admin')

      const adminLink = screen.getByRole('link', { name: /admin panel/i })
      expect(adminLink).toHaveClass('bg-slate-100', 'text-slate-900')
    })

    it('does not highlight admin panel link when on dashboard', () => {
      renderWithAuth({ email: 'admin@example.com', role: 'admin' }, '/dashboard')

      const adminLink = screen.getByRole('link', { name: /admin panel/i })
      expect(adminLink).toHaveClass('text-slate-600')
      expect(adminLink).not.toHaveClass('bg-slate-100')
    })
  })

  describe('Logout Functionality', () => {
    it('calls logout function when logout button clicked', async () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      const logoutButton = screen.getByRole('button', { name: /logout/i })
      fireEvent.click(logoutButton)

      expect(mockLogout).toHaveBeenCalledTimes(1)
    })

    it('logout button is clickable', async () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      const logoutButton = screen.getByRole('button', { name: /logout/i })
      expect(logoutButton).toBeEnabled()

      fireEvent.click(logoutButton)
      expect(mockLogout).toHaveBeenCalled()
    })
  })

  describe('Mobile Menu', () => {
    it('mobile menu is hidden by default', () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      // Mobile menu button should exist
      const menuButton = screen.getByRole('button', { name: /open main menu/i })
      expect(menuButton).toBeInTheDocument()

      // Mobile menu content should not be visible
      const mobileLinks = screen.queryAllByRole('link', { name: /dashboard/i })
      // Should only have desktop link visible initially
      expect(mobileLinks.length).toBe(1)
    })

    it('opens mobile menu when hamburger clicked', async () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      const menuButton = screen.getByRole('button', { name: /open main menu/i })
      fireEvent.click(menuButton)

      // Mobile menu should now be visible with duplicate links
      const mobileLinks = screen.getAllByRole('link', { name: /dashboard/i })
      expect(mobileLinks.length).toBeGreaterThan(1) // Desktop + mobile
    })

    it('closes mobile menu when link clicked', async () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      // Open menu
      const menuButton = screen.getByRole('button', { name: /open main menu/i })
      fireEvent.click(menuButton)

      // Click a link in mobile menu
      const mobileLinks = screen.getAllByRole('link', { name: /dashboard/i })
      const mobileLink = mobileLinks[mobileLinks.length - 1] // Get mobile version
      fireEvent.click(mobileLink)

      // Menu should close (only desktop link remains)
      const linksAfterClose = screen.getAllByRole('link', { name: /dashboard/i })
      expect(linksAfterClose.length).toBe(1)
    })

    it('toggles hamburger icon when menu opens/closes', async () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      const menuButton = screen.getByRole('button', { name: /open main menu/i })
      
      // Initially shows hamburger icon (3 lines)
      expect(menuButton.querySelector('svg path')).toHaveAttribute('d', 'M4 6h16M4 12h16M4 18h16')

      // Click to open
      fireEvent.click(menuButton)

      // Should show X icon
      expect(menuButton.querySelector('svg path')).toHaveAttribute('d', 'M6 18L18 6M6 6l12 12')
    })

    it('shows admin link in mobile menu for admin users', async () => {
      renderWithAuth({ email: 'admin@example.com', role: 'admin' })

      const menuButton = screen.getByRole('button', { name: /open main menu/i })
      fireEvent.click(menuButton)

      const adminLinks = screen.getAllByRole('link', { name: /admin panel/i })
      expect(adminLinks.length).toBeGreaterThan(1) // Desktop + mobile
    })

    it('displays user email in mobile menu', async () => {
      renderWithAuth({ email: 'mobile@example.com', role: 'user' })

      const menuButton = screen.getByRole('button', { name: /open main menu/i })
      fireEvent.click(menuButton)

      // Email should appear twice (desktop + mobile)
      const emailElements = screen.getAllByText('mobile@example.com')
      expect(emailElements.length).toBe(2)
    })

    it('logout button works in mobile menu', async () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      const menuButton = screen.getByRole('button', { name: /open main menu/i })
      fireEvent.click(menuButton)

      const logoutButtons = screen.getAllByRole('button', { name: /logout/i })
      const mobileLogout = logoutButtons[logoutButtons.length - 1]
      
      fireEvent.click(mobileLogout)

      expect(mockLogout).toHaveBeenCalledTimes(1)
    })
  })

  describe('Responsive Behavior', () => {
    it('renders both desktop and mobile navigation elements', () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      // Desktop nav should have hidden class for mobile
      const desktopNav = screen.getByRole('link', { name: /dashboard/i }).closest('div')
      expect(desktopNav).toHaveClass('hidden', 'md:flex')

      // Mobile menu button should be visible
      const mobileButton = screen.getByRole('button', { name: /open main menu/i })
      expect(mobileButton).toBeInTheDocument()
    })
  })

  describe('Logo Link', () => {
    it('logo links to dashboard', () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      const logoLink = screen.getByRole('link', { name: /web scraping portal/i })
      expect(logoLink).toHaveAttribute('href', '/dashboard')
    })

    it('logo is clickable', async () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      const logoLink = screen.getByRole('link', { name: /web scraping portal/i })
      expect(logoLink).toBeEnabled()
    })
  })

  describe('Accessibility', () => {
    it('mobile menu button has aria-expanded attribute', async () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      const menuButton = screen.getByRole('button', { name: /open main menu/i })
      expect(menuButton).toHaveAttribute('aria-expanded')
    })

    it('mobile menu button has screen reader text', () => {
      renderWithAuth({ email: 'user@example.com', role: 'user' })

      expect(screen.getByText('Open main menu')).toHaveClass('sr-only')
    })
  })
})
