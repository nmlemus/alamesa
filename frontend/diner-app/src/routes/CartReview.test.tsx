import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useState, useEffect } from 'react'
import CartReview from './CartReview'
import { CartProvider, useCartContext } from '../context/CartContext'

vi.mock('../api/hooks', () => ({
  useTable: vi.fn(),
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

import { useTable } from '../api/hooks'
import { apiFetch } from '../api/client'

const mockUseTable = vi.mocked(useTable)
const mockApiFetch = vi.mocked(apiFetch)

const mockTable = {
  id: 'table-uuid-1',
  restaurant_id: 'rest-1',
  number: 3,
  label: null,
  is_active: true,
  qr_url: '/qr/demo/3',
}

const mockItem = {
  id: 'item-1',
  restaurant_id: 'rest-1',
  category_id: 'cat-1',
  name: 'Pizza Margarita',
  description: null,
  price_cents: 25000,
  is_available: true,
  display_order: 1,
}

// Pre-loads cart with mockItem ×2 via useEffect to avoid setState-during-render warning
function CartReviewWithItem() {
  const cart = useCartContext()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    cart.addItem(mockItem, 2)
    setReady(true)
    // addItem is stable (useCallback); safe to omit from deps
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return ready ? <CartReview /> : null
}

function renderCartReview(withItem = false) {
  const Component = withItem ? CartReviewWithItem : CartReview
  return render(
    <CartProvider>
      <MemoryRouter initialEntries={['/demo/mesa/3/carrito']}>
        <Routes>
          <Route path="/:slug/mesa/:tableNumber/carrito" element={<Component />} />
          <Route path="/:slug/mesa/:tableNumber/pedido-enviado/:orderId" element={<div>Enviado</div>} />
        </Routes>
      </MemoryRouter>
    </CartProvider>
  )
}

describe('CartReview', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseTable.mockReturnValue({ table: mockTable, isLoading: false, error: null })
  })

  afterEach(() => {
    cleanup()
  })

  it('shows empty state when cart is empty', () => {
    renderCartReview(false)
    expect(screen.getByText('Tu carrito está vacío.')).toBeDefined()
  })

  it('renders cart item row when items are in cart', async () => {
    renderCartReview(true)
    await waitFor(() => {
      expect(screen.getByText('Pizza Margarita')).toBeDefined()
    })
  })

  it('"Confirmar pedido" button is disabled when cart is empty', () => {
    renderCartReview(false)
    const btn = screen.getByRole('button', { name: 'Confirmar pedido' }) as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('"Confirmar pedido" button is enabled when cart has items and table is loaded', async () => {
    renderCartReview(true)
    await waitFor(() => {
      const btn = screen.getByRole('button', { name: 'Confirmar pedido' }) as HTMLButtonElement
      expect(btn.disabled).toBe(false)
    })
  })

  it('"Confirmar pedido" button is disabled while table is loading', async () => {
    mockUseTable.mockReturnValue({ table: null, isLoading: true, error: null })
    renderCartReview(true)
    await waitFor(() => {
      const btn = screen.getByRole('button', { name: 'Confirmar pedido' }) as HTMLButtonElement
      expect(btn.disabled).toBe(true)
    })
  })

  it('shows total price', async () => {
    renderCartReview(true)
    // 2 × 25000 = 50000 → $ 50.000 (appears in both CartItemRow subtotal and footer)
    await waitFor(() => {
      expect(screen.getAllByText('$ 50.000').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('notes textarea has maxLength 280', async () => {
    renderCartReview(true)
    await waitFor(() => {
      const textarea = screen.getByRole('textbox', { name: /notas adicionales/i }) as HTMLTextAreaElement
      expect(textarea.maxLength).toBe(280)
    })
  })

  it('calls POST /api/orders with correct payload on confirm', async () => {
    mockApiFetch.mockResolvedValue({
      id: 'order-new',
      status: 'pending',
      restaurant_id: 'rest-1',
      table_id: 'table-uuid-1',
      diner_id: 'diner-1',
      created_at: '2026-06-17T00:00:00Z',
      items: [],
      total_cents: 50000,
      item_count: 2,
    })

    renderCartReview(true)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Confirmar pedido' }) as HTMLButtonElement).not.toBe(null)
    })

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar pedido' }))

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith('/api/orders', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          restaurant_slug: 'demo',
          table_id: 'table-uuid-1',
          items: [{ menu_item_id: 'item-1', quantity: 2 }],
        }),
      }))
    })
  })

  it('shows error banner when order submission fails', async () => {
    const { ApiError } = await import('../api/client')
    mockApiFetch.mockRejectedValue(new ApiError(500, 'Server error'))

    renderCartReview(true)

    await waitFor(() => {
      expect((screen.getByRole('button', { name: 'Confirmar pedido' }) as HTMLButtonElement).disabled).toBe(false)
    })

    fireEvent.click(screen.getByRole('button', { name: 'Confirmar pedido' }))

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined()
    })
  })

  it('quantity stepper reduces item quantity', async () => {
    renderCartReview(true)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Reducir cantidad de Pizza Margarita' })).toBeDefined()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Reducir cantidad de Pizza Margarita' }))

    // Quantity display should update to 1
    await waitFor(() => {
      expect(screen.getByLabelText('Cantidad de Pizza Margarita: 1')).toBeDefined()
    })
  })

  it('quantity stepper increases item quantity', async () => {
    renderCartReview(true)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Aumentar cantidad de Pizza Margarita' })).toBeDefined()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Aumentar cantidad de Pizza Margarita' }))

    // Quantity display should update to 3
    await waitFor(() => {
      expect(screen.getByLabelText('Cantidad de Pizza Margarita: 3')).toBeDefined()
    })
  })

  it('removing last unit of an item removes it from the list', async () => {
    renderCartReview(true)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Reducir cantidad de Pizza Margarita' })).toBeDefined()
    })

    // 2 → 1
    fireEvent.click(screen.getByRole('button', { name: 'Reducir cantidad de Pizza Margarita' }))
    // 1 → 0 (item removed)
    fireEvent.click(screen.getByRole('button', { name: 'Reducir cantidad de Pizza Margarita' }))

    await waitFor(() => {
      expect(screen.queryByText('Pizza Margarita')).toBeNull()
    })
    expect(screen.getByText('Tu carrito está vacío.')).toBeDefined()
  })
})
