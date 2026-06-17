import type { CartItem } from '../types'
import { formatCents } from '../hooks/useCart'

interface Props {
  cartItem: CartItem
  onUpdateQuantity: (menuItemId: string, quantity: number) => void
}

export default function CartItemRow({ cartItem, onUpdateQuantity }: Props) {
  const { menu_item, quantity, subtotal_cents } = cartItem

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--spacing-3)',
        padding: 'var(--spacing-4)',
        background: '#ffffff',
        borderRadius: 'var(--radius-lg)',
        marginBottom: 'var(--spacing-3)',
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontWeight: 600,
            fontSize: '0.9375rem',
            color: '#0f172a',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {menu_item.name}
        </p>
        <p style={{ fontSize: '0.875rem', color: '#64748b', marginTop: 'var(--spacing-1)' }}>
          {formatCents(subtotal_cents)}
        </p>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-2)',
          height: 48,
          flexShrink: 0,
        }}
      >
        <button
          aria-label={`Reducir cantidad de ${menu_item.name}`}
          onClick={() => onUpdateQuantity(menu_item.id, quantity - 1)}
          style={{
            width: 32,
            height: 32,
            borderRadius: 'var(--radius-full)',
            border: '1px solid #e2e8f0',
            background: '#ffffff',
            cursor: 'pointer',
            fontSize: '1.125rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#0f172a',
          }}
        >
          −
        </button>
        <span
          aria-label={`Cantidad de ${menu_item.name}: ${quantity}`}
          style={{ fontWeight: 600, fontSize: '1rem', minWidth: 24, textAlign: 'center' }}
        >
          {quantity}
        </span>
        <button
          aria-label={`Aumentar cantidad de ${menu_item.name}`}
          onClick={() => onUpdateQuantity(menu_item.id, quantity + 1)}
          style={{
            width: 32,
            height: 32,
            borderRadius: 'var(--radius-full)',
            border: 'none',
            background: 'var(--color-primary)',
            color: '#ffffff',
            cursor: 'pointer',
            fontSize: '1.125rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          +
        </button>
      </div>
    </div>
  )
}
