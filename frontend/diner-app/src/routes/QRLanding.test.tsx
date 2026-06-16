import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import QRLanding from './QRLanding'
import { useRestaurant } from '../api/hooks'
import { ApiError } from '../api/client'

vi.mock('../api/hooks', () => ({
  useRestaurant: vi.fn(),
}))

const mockUseRestaurant = vi.mocked(useRestaurant)
const restaurant = { id: 'rest-1', slug: 'la-trattoria', name: 'La Trattoria' }

function renderQRLanding() {
  return render(
    <MemoryRouter initialEntries={['/la-trattoria/mesa/5']}>
      <Routes>
        <Route path="/:slug/mesa/:tableNumber" element={<QRLanding />} />
        <Route path="/:slug/mesa/:tableNumber/menu" element={<div>Menu cargado</div>} />
        <Route path="/:slug/mesa/:tableNumber/registro" element={<div>Registro</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('QRLanding', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  afterEach(() => {
    cleanup()
  })

  it('shows loading skeleton while fetching restaurant', () => {
    mockUseRestaurant.mockReturnValue({ restaurant: null, isLoading: true, error: null })
    renderQRLanding()
    expect(screen.getByRole('status', { name: 'Cargando restaurante' })).toBeDefined()
  })

  it('shows 404 error banner when restaurant is not found', () => {
    mockUseRestaurant.mockReturnValue({
      restaurant: null,
      isLoading: false,
      error: new ApiError(404, 'Not Found'),
    })
    renderQRLanding()
    expect(screen.getByRole('alert')).toBeDefined()
    expect(screen.getByText('Este restaurante no está disponible.')).toBeDefined()
  })

  it('shows generic error banner for non-404 API errors', () => {
    mockUseRestaurant.mockReturnValue({
      restaurant: null,
      isLoading: false,
      error: new ApiError(500, 'Server Error'),
    })
    renderQRLanding()
    expect(screen.getByText('No se pudo cargar el restaurante.')).toBeDefined()
  })

  it('shows restaurant name when loaded', () => {
    mockUseRestaurant.mockReturnValue({ restaurant, isLoading: false, error: null })
    renderQRLanding()
    expect(screen.getByText('La Trattoria')).toBeDefined()
  })

  it('shows mesa label with table number', () => {
    mockUseRestaurant.mockReturnValue({ restaurant, isLoading: false, error: null })
    renderQRLanding()
    expect(screen.getByText('Mesa 5')).toBeDefined()
  })

  it('shows CTA button when no JWT in localStorage', () => {
    mockUseRestaurant.mockReturnValue({ restaurant, isLoading: false, error: null })
    renderQRLanding()
    expect(screen.getByRole('button', { name: 'Comenzar pedido' })).toBeDefined()
  })

  it('auto-redirects to menu when JWT exists in localStorage', () => {
    localStorage.setItem('mesadigital_token_rest-1', 'some-token')
    mockUseRestaurant.mockReturnValue({ restaurant, isLoading: false, error: null })
    renderQRLanding()
    expect(screen.getByText('Menu cargado')).toBeDefined()
  })

  it('clicking CTA navigates to registration', () => {
    mockUseRestaurant.mockReturnValue({ restaurant, isLoading: false, error: null })
    renderQRLanding()
    fireEvent.click(screen.getByRole('button', { name: 'Comenzar pedido' }))
    expect(screen.getByText('Registro')).toBeDefined()
  })
})
