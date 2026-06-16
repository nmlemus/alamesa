import { render, screen, fireEvent, within, cleanup } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import MenuPage from './MenuPage'
import { useMenu } from '../api/hooks'
import type { CategoryRead } from '../types'

vi.mock('../api/hooks', () => ({
  useMenu: vi.fn(),
}))

const mockUseMenu = vi.mocked(useMenu)

const availableItem = {
  id: 'item-1',
  restaurant_id: 'rest-1',
  category_id: 'cat-1',
  name: 'Margarita',
  description: 'Tomate y mozzarella',
  price_cents: 12000,
  is_available: true,
  display_order: 1,
}

const unavailableItem = {
  id: 'item-2',
  restaurant_id: 'rest-1',
  category_id: 'cat-1',
  name: 'Napolitana',
  description: null,
  price_cents: 14000,
  is_available: false,
  display_order: 2,
}

const pizzaCategory: CategoryRead = {
  id: 'cat-1',
  restaurant_id: 'rest-1',
  name: 'Pizzas',
  is_visible: true,
  display_order: 1,
  items: [availableItem, unavailableItem],
}

const drinksCategory: CategoryRead = {
  id: 'cat-2',
  restaurant_id: 'rest-1',
  name: 'Bebidas',
  is_visible: true,
  display_order: 2,
  items: [
    {
      id: 'item-3',
      restaurant_id: 'rest-1',
      category_id: 'cat-2',
      name: 'Gaseosa',
      description: null,
      price_cents: 3000,
      is_available: true,
      display_order: 1,
    },
  ],
}

const hiddenCategory: CategoryRead = {
  id: 'cat-3',
  restaurant_id: 'rest-1',
  name: 'Oculta',
  is_visible: false,
  display_order: 3,
  items: [],
}

function renderMenuPage() {
  return render(
    <MemoryRouter initialEntries={['/mi-restaurante/mesa/3/menu']}>
      <Routes>
        <Route path="/:slug/mesa/:tableNumber/menu" element={<MenuPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('MenuPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    cleanup()
  })

  it('shows loading skeleton while fetching menu', () => {
    mockUseMenu.mockReturnValue({ categories: [], isLoading: true, error: null })
    renderMenuPage()
    expect(screen.getByRole('status', { name: 'Cargando menú' })).toBeDefined()
  })

  it('shows empty state when there are no visible categories', () => {
    mockUseMenu.mockReturnValue({ categories: [], isLoading: false, error: null })
    renderMenuPage()
    expect(screen.getByText('El menú está vacío en este momento.')).toBeDefined()
  })

  it('hides categories with is_visible false and shows empty state', () => {
    mockUseMenu.mockReturnValue({ categories: [hiddenCategory], isLoading: false, error: null })
    renderMenuPage()
    expect(screen.getByText('El menú está vacío en este momento.')).toBeDefined()
  })

  it('renders a tab button for each visible category', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory, drinksCategory], isLoading: false, error: null })
    renderMenuPage()
    expect(screen.getByRole('button', { name: 'Pizzas' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Bebidas' })).toBeDefined()
  })

  it('renders items of the first category by default', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    expect(screen.getByText('Margarita')).toBeDefined()
    expect(screen.getByText('Napolitana')).toBeDefined()
  })

  it('shows Agotado label for unavailable items', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    expect(screen.getByText('Agotado')).toBeDefined()
  })

  it('disables the add button for unavailable items', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    const addBtn = screen.getByRole('button', { name: 'Agregar Napolitana' }) as HTMLButtonElement
    expect(addBtn.disabled).toBe(true)
  })

  it('does not disable the add button for available items', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    const addBtn = screen.getByRole('button', { name: 'Agregar Margarita' }) as HTMLButtonElement
    expect(addBtn.disabled).toBe(false)
  })

  it('CartBar is not shown when the cart is empty', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    expect(screen.queryByRole('status', { name: 'Carrito' })).toBeNull()
  })

  it('CartBar appears after adding an item via the quick-add button', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    fireEvent.click(screen.getByRole('button', { name: 'Agregar Margarita' }))
    expect(screen.getByRole('status', { name: 'Carrito' })).toBeDefined()
  })

  it('CartBar shows correct item count and total', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    fireEvent.click(screen.getByRole('button', { name: 'Agregar Margarita' }))
    const cartBar = screen.getByRole('status', { name: 'Carrito' })
    expect(within(cartBar).getByText('1 ítem')).toBeDefined()
    expect(within(cartBar).getByText('$ 12.000')).toBeDefined()
  })

  it('opens ItemDetailSheet when clicking the item card body', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    fireEvent.click(screen.getByRole('button', { name: 'Ver detalles de Margarita' }))
    expect(screen.getByRole('dialog', { name: 'Margarita' })).toBeDefined()
  })

  it('ItemDetailSheet shows item description', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    fireEvent.click(screen.getByRole('button', { name: 'Ver detalles de Margarita' }))
    const dialog = screen.getByRole('dialog', { name: 'Margarita' })
    expect(within(dialog).getByText('Tomate y mozzarella')).toBeDefined()
  })

  it('Agregar al pedido adds to cart and closes the sheet', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    fireEvent.click(screen.getByRole('button', { name: 'Ver detalles de Margarita' }))
    fireEvent.click(screen.getByRole('button', { name: 'Agregar al pedido' }))
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(screen.getByRole('status', { name: 'Carrito' })).toBeDefined()
  })

  it('ItemDetailSheet CTA is disabled for unavailable items', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    fireEvent.click(screen.getByRole('button', { name: 'Ver detalles de Napolitana' }))
    const cta = screen.getByRole('button', { name: 'Agotado' }) as HTMLButtonElement
    expect(cta.disabled).toBe(true)
  })

  it('clicking the backdrop closes the ItemDetailSheet', () => {
    mockUseMenu.mockReturnValue({ categories: [pizzaCategory], isLoading: false, error: null })
    renderMenuPage()
    fireEvent.click(screen.getByRole('button', { name: 'Ver detalles de Margarita' }))
    expect(screen.getByRole('dialog', { name: 'Margarita' })).toBeDefined()
    // The backdrop is the div preceding the dialog; click fires on dialog's container
    // Clicking outside the dialog (on the overlay) closes it
    const dialog = screen.getByRole('dialog', { name: 'Margarita' })
    // The overlay is the element behind the dialog — fire click on the parent container
    fireEvent.click(dialog.previousElementSibling as HTMLElement)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('switching category tab shows items of the selected category only', () => {
    mockUseMenu.mockReturnValue({
      categories: [pizzaCategory, drinksCategory],
      isLoading: false,
      error: null,
    })
    renderMenuPage()
    expect(screen.getByText('Margarita')).toBeDefined()
    fireEvent.click(screen.getByRole('button', { name: 'Bebidas' }))
    expect(screen.queryByText('Margarita')).toBeNull()
    expect(screen.getByText('Gaseosa')).toBeDefined()
  })
})
