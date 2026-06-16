import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import ErrorBanner from '../components/ErrorBanner'

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [inlineError, setInlineError] = useState<string | null>(null)
  const [bannerError, setBannerError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  if (user) {
    return <Navigate to="/dashboard/orders" replace />
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setInlineError(null)
    setBannerError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard/orders', { replace: true })
    } catch (err: unknown) {
      const status = (err as { status?: number }).status
      if (status === 401) {
        setInlineError('Email o contraseña incorrectos.')
      } else {
        setBannerError('Algo salió mal. Por favor inténtelo más tarde.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-surface)',
        padding: 'var(--spacing-4)',
      }}
    >
      <div
        style={{
          background: '#ffffff',
          borderRadius: 'var(--radius-lg)',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)',
          padding: 'var(--spacing-8)',
          width: '100%',
          maxWidth: '400px',
        }}
      >
        <h1
          style={{
            fontSize: '1.5rem',
            fontWeight: '700',
            color: '#0f172a',
            marginBottom: 'var(--spacing-6)',
          }}
        >
          Iniciar sesión
        </h1>

        {bannerError && <ErrorBanner message={bannerError} />}

        <form onSubmit={handleSubmit} noValidate>
          <div style={{ marginBottom: 'var(--spacing-4)' }}>
            <label
              htmlFor="email"
              style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: '500',
                marginBottom: 'var(--spacing-1)',
                color: '#374151',
              }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{
                width: '100%',
                padding: 'var(--spacing-2) var(--spacing-3)',
                border: '1px solid #d1d5db',
                borderRadius: 'var(--radius-md)',
                fontSize: '1rem',
                outline: 'none',
              }}
            />
          </div>

          <div
            style={{
              marginBottom: inlineError ? 'var(--spacing-2)' : 'var(--spacing-6)',
            }}
          >
            <label
              htmlFor="password"
              style={{
                display: 'block',
                fontSize: '0.875rem',
                fontWeight: '500',
                marginBottom: 'var(--spacing-1)',
                color: '#374151',
              }}
            >
              Contraseña
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width: '100%',
                padding: 'var(--spacing-2) var(--spacing-3)',
                border: '1px solid #d1d5db',
                borderRadius: 'var(--radius-md)',
                fontSize: '1rem',
                outline: 'none',
              }}
            />
          </div>

          {inlineError && (
            <p
              role="alert"
              style={{
                color: '#dc2626',
                fontSize: '0.875rem',
                marginBottom: 'var(--spacing-4)',
              }}
            >
              {inlineError}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: 'var(--spacing-3)',
              background: loading ? '#94a3b8' : 'var(--color-primary)',
              color: '#ffffff',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Iniciando sesión…' : 'Entrar'}
          </button>
        </form>
      </div>
    </main>
  )
}
