import { render, screen, fireEvent, cleanup, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import Registration from './Registration'
import { useRestaurant, useRegister } from '../api/hooks'
import { ApiError } from '../api/client'

vi.mock('../api/hooks', () => ({
  useRestaurant: vi.fn(),
  useRegister: vi.fn(),
}))

const mockUseRestaurant = vi.mocked(useRestaurant)
const mockUseRegister = vi.mocked(useRegister)
const restaurant = { id: 'rest-1', slug: 'la-trattoria', name: 'La Trattoria' }

function renderRegistration() {
  return render(
    <MemoryRouter initialEntries={['/la-trattoria/mesa/5/registro']}>
      <Routes>
        <Route path="/:slug/mesa/:tableNumber/registro" element={<Registration />} />
        <Route path="/:slug/mesa/:tableNumber/menu" element={<div>Menu cargado</div>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('Registration', () => {
  const mockRegister = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseRestaurant.mockReturnValue({ restaurant, isLoading: false, error: null })
    mockUseRegister.mockReturnValue({ register: mockRegister, isLoading: false, error: null })
  })

  afterEach(() => {
    cleanup()
  })

  it('renders name and phone input fields', () => {
    renderRegistration()
    expect(screen.getByLabelText('Nombre')).toBeDefined()
    expect(screen.getByLabelText('Teléfono')).toBeDefined()
  })

  it('renders a CTA submit button with 48px height', () => {
    renderRegistration()
    const btn = screen.getByRole('button', { name: 'Ingresar al menú' }) as HTMLButtonElement
    expect(btn).toBeDefined()
    expect(btn.style.height).toBe('48px')
  })

  it('shows validation error when name is empty on submit', () => {
    renderRegistration()
    fireEvent.change(screen.getByLabelText('Teléfono'), { target: { value: '3101234567' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar al menú' }))
    expect(screen.getByRole('alert')).toBeDefined()
    expect(screen.getByText('Por favor completa tu nombre y teléfono.')).toBeDefined()
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('shows validation error when phone is empty on submit', () => {
    renderRegistration()
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Ana García' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar al menú' }))
    expect(screen.getByRole('alert')).toBeDefined()
    expect(mockRegister).not.toHaveBeenCalled()
  })

  it('calls register with trimmed name, phone, and restaurantId on valid submit', async () => {
    mockRegister.mockResolvedValue(undefined)
    renderRegistration()
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: '  Ana García  ' } })
    fireEvent.change(screen.getByLabelText('Teléfono'), { target: { value: ' 3101234567 ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar al menú' }))
    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith('Ana García', '3101234567', 'rest-1')
    })
  })

  it('redirects to menu on successful registration', async () => {
    mockRegister.mockResolvedValue(undefined)
    renderRegistration()
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Ana García' } })
    fireEvent.change(screen.getByLabelText('Teléfono'), { target: { value: '3101234567' } })
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar al menú' }))
    await waitFor(() => {
      expect(screen.getByText('Menu cargado')).toBeDefined()
    })
  })

  it('shows error banner when useRegister has an error', () => {
    mockUseRegister.mockReturnValue({
      register: mockRegister,
      isLoading: false,
      error: new ApiError(400, 'Bad Request'),
    })
    renderRegistration()
    expect(screen.getByRole('alert')).toBeDefined()
    expect(screen.getByText('No se pudo registrar. Intenta de nuevo.')).toBeDefined()
  })

  it('does not render a back button', () => {
    renderRegistration()
    expect(screen.queryByRole('button', { name: /volver|atrás|back/i })).toBeNull()
  })

  it('disables submit button while registration is in progress', () => {
    mockUseRegister.mockReturnValue({ register: mockRegister, isLoading: true, error: null })
    renderRegistration()
    const btn = screen.getByRole('button') as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('disables submit button while restaurant is loading', () => {
    mockUseRestaurant.mockReturnValue({ restaurant: null, isLoading: true, error: null })
    renderRegistration()
    const btn = screen.getByRole('button', { name: 'Ingresar al menú' }) as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })
})
