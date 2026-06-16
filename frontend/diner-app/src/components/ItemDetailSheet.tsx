import { useState } from 'react'
import type { MenuItemRead } from '../types'
import { formatCents } from '../hooks/useCart'

interface Props {
  item: MenuItemRead
  onClose: () => void
  onAdd: (item: MenuItemRead, quantity: number) => void
}

export default function ItemDetailSheet({ item, onClose, onAdd }: Props) {
  const [quantity, setQuantity] = useState(1)

  function handleAdd() {
    onAdd(item, quantity)
    onClose()
  }

  return (
    <>
      <div
        aria-hidden="true"
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.4)',
          zIndex: 200,
        }}
      />
      <div
        role="dialog"
        aria-label={item.name}
        aria-modal="true"
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          background: '#ffffff',
          borderRadius: 'var(--radius-xl) var(--radius-xl) 0 0',
          padding: 'var(--spacing-6)',
          zIndex: 201,
          maxHeight: '80vh',
          overflowY: 'auto',
        }}
      >
        <div
          aria-hidden="true"
          style={{
            width: 40,
            height: 4,
            background: '#e2e8f0',
            borderRadius: 'var(--radius-full)',
            margin: '0 auto var(--spacing-4)',
          }}
        />
        <h2
          style={{
            fontSize: '1.25rem',
            fontWeight: '700',
            color: '#0f172a',
            marginBottom: 'var(--spacing-2)',
          }}
        >
          {item.name}
        </h2>
        {item.description && (
          <p
            style={{
              fontSize: '0.9375rem',
              color: '#374151',
              lineHeight: '1.6',
              marginBottom: 'var(--spacing-4)',
            }}
          >
            {item.description}
          </p>
        )}
        <p
          style={{
            fontWeight: '700',
            fontSize: '1.25rem',
            color: 'var(--color-primary)',
            marginBottom: 'var(--spacing-6)',
          }}
        >
          {formatCents(item.price_cents)}
        </p>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--spacing-4)',
            marginBottom: 'var(--spacing-6)',
          }}
        >
          <button
            onClick={() => setQuantity(q => Math.max(1, q - 1))}
            aria-label="Reducir cantidad"
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-full)',
              border: '1px solid #e2e8f0',
              background: '#ffffff',
              fontSize: '1.25rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            −
          </button>
          <span
            aria-live="polite"
            style={{
              fontWeight: '600',
              fontSize: '1rem',
              minWidth: 24,
              textAlign: 'center',
            }}
          >
            {quantity}
          </span>
          <button
            onClick={() => setQuantity(q => q + 1)}
            aria-label="Aumentar cantidad"
            style={{
              width: 36,
              height: 36,
              borderRadius: 'var(--radius-full)',
              border: 'none',
              background: 'var(--color-primary)',
              color: '#ffffff',
              fontSize: '1.25rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            +
          </button>
        </div>
        <button
          onClick={handleAdd}
          disabled={!item.is_available}
          style={{
            width: '100%',
            padding: 'var(--spacing-4)',
            background: item.is_available ? 'var(--color-primary)' : '#e2e8f0',
            color: item.is_available ? '#ffffff' : '#94a3b8',
            border: 'none',
            borderRadius: 'var(--radius-lg)',
            fontSize: '1rem',
            fontWeight: '600',
            cursor: item.is_available ? 'pointer' : 'not-allowed',
          }}
        >
          {item.is_available ? 'Agregar al pedido' : 'Agotado'}
        </button>
      </div>
    </>
  )
}
