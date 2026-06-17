import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useOrderPoll } from '../hooks/useOrderPoll'
import OrderStatusTracker from '../components/OrderStatusTracker'
import ErrorBanner from '../components/ErrorBanner'
import { apiFetch, ApiError } from '../api/client'

export default function OrderTracker() {
  const { slug, tableNumber, orderId } = useParams<{
    slug: string
    tableNumber: string
    orderId: string
  }>()
  const navigate = useNavigate()
  const { order, error } = useOrderPoll(orderId ?? '')
  const [isCancelling, setIsCancelling] = useState(false)
  const [cancelError, setCancelError] = useState<string | null>(null)

  async function handleCancel() {
    if (!orderId) return
    setIsCancelling(true)
    setCancelError(null)
    try {
      await apiFetch(`/api/orders/${orderId}/cancel`, { method: 'POST' })
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 403
          ? 'Ya no puedes cancelar este pedido.'
          : 'No se pudo cancelar. Intenta de nuevo.'
      setCancelError(msg)
    } finally {
      setIsCancelling(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-surface)' }}>
      <div
        style={{
          padding: 'var(--spacing-4)',
          background: '#ffffff',
          boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        }}
      >
        <h1 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#0f172a' }}>
          Seguimiento del pedido
        </h1>
      </div>

      {error && !order && (
        <ErrorBanner message="No se pudo obtener el estado del pedido." />
      )}

      {order && order.status !== 'cancelled' && (
        <OrderStatusTracker status={order.status} />
      )}

      {order?.status === 'ready' && (
        <div
          role="status"
          aria-label="Pedido listo"
          style={{
            margin: 'var(--spacing-4)',
            padding: 'var(--spacing-5)',
            background: '#ffedd5',
            borderRadius: 'var(--radius-lg)',
            textAlign: 'center',
            border: '2px solid var(--color-primary)',
          }}
        >
          <p
            style={{
              fontSize: '1.25rem',
              fontWeight: 700,
              color: '#7c2d12',
              marginBottom: 'var(--spacing-1)',
            }}
          >
            ¡Tu pedido está listo! 🛎
          </p>
          <p style={{ fontSize: '0.875rem', color: '#9a3f00' }}>
            Pasa a retirarlo en el mostrador.
          </p>
        </div>
      )}

      {order?.status === 'cancelled' && (
        <div style={{ padding: 'var(--spacing-4)' }}>
          <ErrorBanner message="Tu pedido fue cancelado." />
          <button
            onClick={() => navigate(`/${slug}/mesa/${tableNumber}/menu`)}
            style={{
              width: '100%',
              height: 48,
              marginTop: 'var(--spacing-4)',
              background: 'var(--color-primary)',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: '1rem',
              border: 'none',
              borderRadius: 'var(--radius-lg)',
              cursor: 'pointer',
            }}
          >
            Hacer otro pedido
          </button>
        </div>
      )}

      {cancelError && (
        <div style={{ padding: '0 var(--spacing-4)' }}>
          <ErrorBanner message={cancelError} />
        </div>
      )}

      {order?.status === 'pending' && (
        <div style={{ padding: 'var(--spacing-4)', textAlign: 'center', marginTop: 'var(--spacing-4)' }}>
          <button
            onClick={handleCancel}
            disabled={isCancelling}
            style={{
              background: 'none',
              border: 'none',
              cursor: isCancelling ? 'not-allowed' : 'pointer',
              color: '#dc2626',
              fontSize: '0.875rem',
              textDecoration: 'underline',
              opacity: isCancelling ? 0.6 : 1,
            }}
          >
            {isCancelling ? 'Cancelando…' : 'Cancelar pedido'}
          </button>
        </div>
      )}
    </div>
  )
}
