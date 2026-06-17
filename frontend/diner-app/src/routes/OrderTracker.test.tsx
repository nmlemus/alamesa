import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import OrderTracker from './OrderTracker'
import type { OrderReadWithItems } from '../types'

vi.mock('../hooks/useOrderPoll', () => ({
  useOrderPoll: vi.fn(),
}))

vi.mock('../api/client', () => ({
  apiFetch: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
      this.name = 'ApiError'
    }
  },
}))

import { useOrderPoll } from '../hooks/useOrderPoll'
import { apiFetch } from '../api/client'

const mockUseOrderPoll = vi.mocked(useOrderPoll)
const mockApiFetch = vi.mocked(apiFetch)

function makeOrder(status: OrderReadWithItems['status']): OrderReadWithItems {
  return {
    id: 'order-1',
    restaurant_id: 'rest-1',
    table_id: 'table-1',
    diner_id: 'diner-1',
    status,
    created_at: '2026-06-17T00:00:00Z',
    items: [],
    total_cents: 0,
    item_count: 0,
  }
}

function renderOrderTracker() {
  return render(
    <MemoryRouter initialEntries={['/demo/mesa/3/seguimiento/order-1']}>
      <Routes>
        <Route
          path="/:slug/mesa/:tableNumber/seguimiento/:orderId"
          element={<OrderTracker />}
        />
        <Route path="/:slug/mesa/:tableNumber/menu" element={<div>Menú</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('OrderTracker', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('renders the status tracker for a pending order', () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('pending'), error: null })
    renderOrderTracker()
    expect(screen.getByRole('list', { name: 'Estado del pedido' })).toBeDefined()
  })

  it('marks the first node as current step when status is pending', () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('pending'), error: null })
    renderOrderTracker()
    const items = screen.getAllByRole('listitem')
    expect(items[0].getAttribute('aria-current')).toBe('step')
    expect(items[1].getAttribute('aria-current')).toBeNull()
  })

  it('shows READY banner when status is ready', () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('ready'), error: null })
    renderOrderTracker()
    expect(screen.getByRole('status', { name: 'Pedido listo' })).toBeDefined()
    expect(screen.getByText(/tu pedido está listo/i)).toBeDefined()
  })

  it('does not show READY banner for non-ready statuses', () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('pending'), error: null })
    renderOrderTracker()
    expect(screen.queryByRole('status', { name: 'Pedido listo' })).toBeNull()
  })

  it('shows ErrorBanner and CTA when order is cancelled', () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('cancelled'), error: null })
    renderOrderTracker()
    expect(screen.getByRole('alert')).toBeDefined()
    expect(screen.getByRole('button', { name: 'Hacer otro pedido' })).toBeDefined()
  })

  it('"Hacer otro pedido" navigates to menu', () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('cancelled'), error: null })
    renderOrderTracker()
    fireEvent.click(screen.getByRole('button', { name: 'Hacer otro pedido' }))
    expect(screen.getByText('Menú')).toBeDefined()
  })

  it('shows cancel link only when status is pending', () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('pending'), error: null })
    renderOrderTracker()
    expect(screen.getByRole('button', { name: 'Cancelar pedido' })).toBeDefined()
  })

  it('does not show cancel link when status is confirmed', () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('confirmed'), error: null })
    renderOrderTracker()
    expect(screen.queryByRole('button', { name: 'Cancelar pedido' })).toBeNull()
  })

  it('does not show cancel link when status is ready', () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('ready'), error: null })
    renderOrderTracker()
    expect(screen.queryByRole('button', { name: 'Cancelar pedido' })).toBeNull()
  })

  it('calls POST /api/orders/{id}/cancel when cancel link is clicked', async () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('pending'), error: null })
    mockApiFetch.mockResolvedValue({})
    renderOrderTracker()
    fireEvent.click(screen.getByRole('button', { name: 'Cancelar pedido' }))
    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith('/api/orders/order-1/cancel', { method: 'POST' })
    })
  })

  it('shows error banner when network error occurs on load', () => {
    mockUseOrderPoll.mockReturnValue({ order: null, error: new Error('Network error') as never })
    renderOrderTracker()
    expect(screen.getByRole('alert')).toBeDefined()
  })

  it('does not show status tracker for cancelled orders', () => {
    mockUseOrderPoll.mockReturnValue({ order: makeOrder('cancelled'), error: null })
    renderOrderTracker()
    expect(screen.queryByRole('list', { name: 'Estado del pedido' })).toBeNull()
  })
})
