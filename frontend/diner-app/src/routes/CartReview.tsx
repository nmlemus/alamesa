import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useCartContext } from '../context/CartContext'
import { useTable } from '../api/hooks'
import { apiFetch, ApiError } from '../api/client'
import CartItemRow from '../components/CartItemRow'
import ErrorBanner from '../components/ErrorBanner'
import { formatCents } from '../hooks/useCart'
import type { OrderReadWithItems } from '../types'

export default function CartReview() {
  const { slug, tableNumber } = useParams<{ slug: string; tableNumber: string }>()
  const navigate = useNavigate()
  const cart = useCartContext()
  const { table, isLoading: tableLoading } = useTable(slug ?? '', tableNumber)
  const [notes, setNotes] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  async function handleConfirm() {
    if (cart.item_count === 0 || !table) return
    setIsSubmitting(true)
    setSubmitError(null)
    try {
      const order = await apiFetch<OrderReadWithItems>('/api/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          restaurant_slug: slug,
          table_id: table.id,
          items: cart.items.map(ci => ({
            menu_item_id: ci.menu_item.id,
            quantity: ci.quantity,
          })),
        }),
      })
      cart.clearCart()
      navigate(`/${slug}/mesa/${tableNumber}/pedido-enviado/${order.id}`, { replace: true })
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 422
          ? 'Algunos ítems ya no están disponibles. Vuelve al menú para actualizar tu pedido.'
          : 'No se pudo crear el pedido. Intenta de nuevo.'
      setSubmitError(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--color-surface)', paddingBottom: 100 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-3)',
          padding: 'var(--spacing-4)',
          background: '#ffffff',
          boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        }}
      >
        <button
          aria-label="Volver al menú"
          onClick={() => navigate(-1)}
          style={{
            width: 36,
            height: 36,
            borderRadius: 'var(--radius-full)',
            border: 'none',
            background: 'transparent',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.25rem',
            color: '#0f172a',
          }}
        >
          ←
        </button>
        <h1 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#0f172a' }}>
          Tu pedido
        </h1>
      </div>

      <div style={{ padding: 'var(--spacing-4)' }}>
        {cart.items.length === 0 ? (
          <p
            style={{
              textAlign: 'center',
              color: '#64748b',
              fontSize: '0.9375rem',
              padding: 'var(--spacing-8)',
            }}
          >
            Tu carrito está vacío.
          </p>
        ) : (
          <>
            {cart.items.map(ci => (
              <CartItemRow
                key={ci.menu_item.id}
                cartItem={ci}
                onUpdateQuantity={cart.updateQuantity}
              />
            ))}

            <div
              style={{
                background: '#ffffff',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--spacing-4)',
                marginBottom: 'var(--spacing-4)',
              }}
            >
              <label
                htmlFor="order-notes"
                style={{ fontSize: '0.875rem', fontWeight: 500, color: '#374151', display: 'block', marginBottom: 'var(--spacing-2)' }}
              >
                Notas adicionales (opcional)
              </label>
              <textarea
                id="order-notes"
                value={notes}
                onChange={e => setNotes(e.target.value)}
                maxLength={280}
                placeholder="Ej. sin cebolla, alergia al maní…"
                rows={3}
                style={{
                  width: '100%',
                  padding: 'var(--spacing-3)',
                  border: '1px solid #d1d5db',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.9375rem',
                  resize: 'none',
                  outline: 'none',
                  fontFamily: 'inherit',
                  color: '#0f172a',
                }}
              />
              <p
                style={{
                  fontSize: '0.75rem',
                  color: notes.length >= 260 ? '#dc2626' : '#94a3b8',
                  textAlign: 'right',
                  marginTop: 'var(--spacing-1)',
                }}
              >
                {notes.length}/280
              </p>
            </div>
          </>
        )}
      </div>

      <div
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          background: '#ffffff',
          borderTop: '1px solid #e2e8f0',
          padding: 'var(--spacing-4)',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 'var(--spacing-3)',
          }}
        >
          <span style={{ fontSize: '0.9375rem', color: '#64748b' }}>Total</span>
          <span style={{ fontSize: '1.125rem', fontWeight: 700, color: '#0f172a' }}>
            {formatCents(cart.total_cents)}
          </span>
        </div>

        {submitError && <ErrorBanner message={submitError} />}

        <button
          onClick={handleConfirm}
          disabled={cart.item_count === 0 || isSubmitting || tableLoading || !table}
          style={{
            width: '100%',
            height: 48,
            background: 'var(--color-primary)',
            color: '#ffffff',
            fontWeight: 600,
            fontSize: '1rem',
            border: 'none',
            borderRadius: 'var(--radius-lg)',
            cursor:
              cart.item_count === 0 || isSubmitting || tableLoading || !table
                ? 'not-allowed'
                : 'pointer',
            opacity:
              cart.item_count === 0 || isSubmitting || tableLoading || !table ? 0.7 : 1,
          }}
        >
          {isSubmitting ? 'Enviando…' : 'Confirmar pedido'}
        </button>
      </div>
    </div>
  )
}
