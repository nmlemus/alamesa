import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useRestaurant } from '../api/hooks'
import ErrorBanner from '../components/ErrorBanner'

function SkeletonBlock({
  width,
  height,
  style,
}: {
  width?: string | number
  height?: string | number
  style?: React.CSSProperties
}) {
  return (
    <div
      aria-hidden="true"
      style={{
        width,
        height,
        background: 'linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%)',
        backgroundSize: '200% 100%',
        animation: 'skeleton-pulse 1.5s ease-in-out infinite',
        borderRadius: 'var(--radius-md)',
        ...style,
      }}
    />
  )
}

export default function QRLanding() {
  const { slug, tableNumber } = useParams<{ slug: string; tableNumber: string }>()
  const navigate = useNavigate()
  const { restaurant, isLoading, error } = useRestaurant(slug ?? '')

  useEffect(() => {
    if (!restaurant) return
    const token = localStorage.getItem(`mesadigital_token_${restaurant.id}`)
    if (token) {
      navigate(`/${slug}/mesa/${tableNumber}/menu`, { replace: true })
    }
  }, [restaurant, slug, tableNumber, navigate])

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-surface)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--spacing-8)',
        gap: 'var(--spacing-4)',
        textAlign: 'center',
      }}
    >
      {isLoading && (
        <div
          role="status"
          aria-label="Cargando restaurante"
          style={{ width: '100%', maxWidth: 320 }}
        >
          <SkeletonBlock
            height={32}
            style={{ marginBottom: 'var(--spacing-2)', borderRadius: 'var(--radius-lg)' }}
          />
          <SkeletonBlock width={120} height={20} style={{ margin: '0 auto' }} />
        </div>
      )}

      {!isLoading && error && (
        <ErrorBanner
          message={
            error.status === 404
              ? 'Este restaurante no está disponible.'
              : 'No se pudo cargar el restaurante.'
          }
        />
      )}

      {!isLoading && !error && restaurant && (
        <>
          <p style={{ color: 'var(--color-secondary)', fontSize: '0.875rem' }}>
            Bienvenido a
          </p>
          <h1
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: '#0f172a',
              lineHeight: 1.2,
            }}
          >
            {restaurant.name}
          </h1>
          <p
            style={{
              fontSize: '1rem',
              color: 'var(--color-secondary)',
              background: '#ffffff',
              border: '1px solid #e2e8f0',
              borderRadius: 'var(--radius-full)',
              padding: 'var(--spacing-1) var(--spacing-4)',
            }}
          >
            Mesa {tableNumber}
          </p>
          <button
            onClick={() => navigate(`/${slug}/mesa/${tableNumber}/registro`)}
            style={{
              marginTop: 'var(--spacing-6)',
              width: '100%',
              maxWidth: 320,
              height: 48,
              background: 'var(--color-primary)',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: '1rem',
              border: 'none',
              borderRadius: 'var(--radius-lg)',
              cursor: 'pointer',
            }}
          >
            Comenzar pedido
          </button>
        </>
      )}
    </div>
  )
}
