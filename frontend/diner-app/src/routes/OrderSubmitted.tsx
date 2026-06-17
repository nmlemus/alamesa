import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

export default function OrderSubmitted() {
  const { slug, tableNumber, orderId } = useParams<{
    slug: string
    tableNumber: string
    orderId: string
  }>()
  const navigate = useNavigate()

  useEffect(() => {
    const timer = setTimeout(() => {
      navigate(`/${slug}/mesa/${tableNumber}/seguimiento/${orderId}`, { replace: true })
    }, 3000)
    return () => clearTimeout(timer)
  }, [slug, tableNumber, orderId, navigate])

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--color-surface)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 'var(--spacing-6)',
        padding: 'var(--spacing-8)',
        textAlign: 'center',
      }}
    >
      <div
        aria-hidden="true"
        style={{
          width: 80,
          height: 80,
          borderRadius: 'var(--radius-full)',
          background: 'var(--color-primary)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          animation: 'order-pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)',
        }}
      >
        <span style={{ fontSize: '2.5rem', color: '#ffffff' }}>✓</span>
      </div>

      <div>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#0f172a', marginBottom: 'var(--spacing-2)' }}>
          ¡Pedido enviado!
        </h1>
        <p style={{ fontSize: '0.9375rem', color: '#64748b' }}>
          El restaurante ya recibió tu pedido.
        </p>
      </div>

      <p style={{ fontSize: '0.875rem', color: '#94a3b8' }}>
        Redirigiendo al seguimiento…
      </p>

      <style>{`
        @keyframes order-pop {
          0% { transform: scale(0); opacity: 0; }
          100% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
