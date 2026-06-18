import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import SidebarNav from './SidebarNav'
import { useAuth } from '../contexts/AuthContext'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockUseAuth = vi.mocked(useAuth)

function mockMatchMedia(matches: boolean) {
  const mq = {
    matches,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  }
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockReturnValue(mq),
  })
  return mq
}

function renderSidebar(path = '/dashboard/orders') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <SidebarNav />
    </MemoryRouter>
  )
}

describe('SidebarNav', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockMatchMedia(false)
  })

  afterEach(() => {
    cleanup()
  })

  describe('role-based visibility', () => {
    it('shows all 6 sections for admin role', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'admin', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      renderSidebar()
      expect(screen.getByText('Live Orders')).toBeDefined()
      expect(screen.getByText('Kitchen View')).toBeDefined()
      expect(screen.getByText('Menu')).toBeDefined()
      expect(screen.getByText('Tables')).toBeDefined()
      expect(screen.getByText('Team')).toBeDefined()
      expect(screen.getByText('Settings')).toBeDefined()
    })

    it('shows only 2 sections for staff role', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'staff', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      renderSidebar()
      expect(screen.getByText('Live Orders')).toBeDefined()
      expect(screen.getByText('Kitchen View')).toBeDefined()
      expect(screen.queryByText('Menu')).toBeNull()
      expect(screen.queryByText('Tables')).toBeNull()
      expect(screen.queryByText('Team')).toBeNull()
      expect(screen.queryByText('Settings')).toBeNull()
    })

    it('admin-only items are absent from DOM (not just hidden) for staff', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'staff', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      renderSidebar()
      const links = screen.getAllByRole('link')
      expect(links).toHaveLength(2)
    })
  })

  describe('active section highlighting', () => {
    it('marks the current route link with aria-current=page', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'admin', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      renderSidebar('/dashboard/orders')
      const activeLink = screen.getByRole('link', { name: /live orders/i })
      expect(activeLink.getAttribute('aria-current')).toBe('page')
    })

    it('does not mark other links as active', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'admin', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      renderSidebar('/dashboard/orders')
      const kitchenLink = screen.getByRole('link', { name: /kitchen view/i })
      expect(kitchenLink.getAttribute('aria-current')).toBeNull()
    })

    it('activates the kitchen link on /dashboard/kitchen', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'admin', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      renderSidebar('/dashboard/kitchen')
      const kitchenLink = screen.getByRole('link', { name: /kitchen view/i })
      expect(kitchenLink.getAttribute('aria-current')).toBe('page')
      const ordersLink = screen.getByRole('link', { name: /live orders/i })
      expect(ordersLink.getAttribute('aria-current')).toBeNull()
    })
  })

  describe('collapse / expand toggle', () => {
    it('starts expanded on desktop (matchMedia returns false)', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'admin', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      mockMatchMedia(false)
      renderSidebar()
      expect(screen.getByText('Live Orders')).toBeDefined()
      const toggleBtn = screen.getByRole('button', { name: /collapse sidebar/i })
      expect(toggleBtn).toBeDefined()
    })

    it('starts collapsed on tablet (matchMedia returns true)', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'admin', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      mockMatchMedia(true)
      renderSidebar()
      expect(screen.queryByText('Live Orders')).toBeNull()
      const toggleBtn = screen.getByRole('button', { name: /expand sidebar/i })
      expect(toggleBtn).toBeDefined()
    })

    it('toggle button expands collapsed sidebar', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'admin', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      mockMatchMedia(true)
      renderSidebar()
      expect(screen.queryByText('Live Orders')).toBeNull()
      fireEvent.click(screen.getByRole('button', { name: /expand sidebar/i }))
      expect(screen.getByText('Live Orders')).toBeDefined()
    })

    it('toggle button collapses expanded sidebar', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'admin', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      mockMatchMedia(false)
      renderSidebar()
      expect(screen.getByText('Live Orders')).toBeDefined()
      fireEvent.click(screen.getByRole('button', { name: /collapse sidebar/i }))
      expect(screen.queryByText('Live Orders')).toBeNull()
    })

    it('icon-only mode provides aria-label on nav links', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'admin', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      mockMatchMedia(true)
      renderSidebar()
      expect(screen.getByRole('link', { name: 'Live Orders' })).toBeDefined()
      expect(screen.getByRole('link', { name: 'Kitchen View' })).toBeDefined()
    })
  })

  describe('navigation', () => {
    it('renders a nav landmark with accessible label', () => {
      mockUseAuth.mockReturnValue({ user: null, role: 'staff', restaurantId: null, login: vi.fn(), logout: vi.fn() })
      renderSidebar()
      expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeDefined()
    })
  })
})
