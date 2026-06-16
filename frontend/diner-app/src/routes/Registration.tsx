import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useRestaurant, useRegister } from '../api/hooks'
import ErrorBanner from '../components/ErrorBanner'

export default function Registration() {
  const { slug, tableNumber } = useParams<{ slug: string; tableNumber: string }>()
  const navigate = useNavigate()
  const { restaurant } = useRestaurant(slug ?? '')
  const { register, isLoading, error } = useRegister()
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [fieldError, setFieldError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() || !phone.trim()) {
      setFieldError('Por favor completa tu nombre y teléfono.')
      return
    }
    setFieldError(null)
    if (!restaurant) return
    try {
      await register(name.trim(), phone.trim(), restaurant.id)
      navigate(`/${slug}/mesa/${tableNumber}/menu`, { replace: true })
    } catch {
      // error displayed via useRegister error state
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-surface)',
        display: 'flex',
        flexDirection: 'column',
        padding: 'var(--spacing-8) var(--spacing-6)',
        gap: 'var(--spacing-6)',
      }}
    >
      <h1
        style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          color: '#0f172a',
        }}
      >
        ¿Cómo te llamamos?
      </h1>

      <form
        onSubmit={handleSubmit}
        noValidate
        style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-4)' }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-1)' }}>
          <label
            htmlFor="name"
            style={{ fontSize: '0.875rem', fontWeight: 500, color: '#374151' }}
          >
            Nombre
          </label>
          <input
            id="name"
            type="text"
            required
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Tu nombre"
            style={{
              height: 44,
              padding: '0 var(--spacing-4)',
              border: '1px solid #d1d5db',
              borderRadius: 'var(--radius-md)',
              fontSize: '1rem',
              outline: 'none',
            }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-1)' }}>
          <label
            htmlFor="phone"
            style={{ fontSize: '0.875rem', fontWeight: 500, color: '#374151' }}
          >
            Teléfono
          </label>
          <input
            id="phone"
            type="tel"
            required
            value={phone}
            onChange={e => setPhone(e.target.value)}
            placeholder="Tu teléfono"
            style={{
              height: 44,
              padding: '0 var(--spacing-4)',
              border: '1px solid #d1d5db',
              borderRadius: 'var(--radius-md)',
              fontSize: '1rem',
              outline: 'none',
            }}
          />
        </div>

        {fieldError && <ErrorBanner message={fieldError} />}
        {error && !fieldError && (
          <ErrorBanner message="No se pudo registrar. Intenta de nuevo." />
        )}

        <button
          type="submit"
          disabled={isLoading || !restaurant}
          style={{
            height: 48,
            background: 'var(--color-primary)',
            color: '#ffffff',
            fontWeight: 600,
            fontSize: '1rem',
            border: 'none',
            borderRadius: 'var(--radius-lg)',
            cursor: isLoading || !restaurant ? 'not-allowed' : 'pointer',
            opacity: isLoading || !restaurant ? 0.7 : 1,
          }}
        >
          {isLoading ? 'Cargando…' : 'Ingresar al menú'}
        </button>
      </form>
    </div>
  )
}
