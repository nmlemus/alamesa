import { formatCents } from '../hooks/useCart'

interface Props {
  item_count: number
  total_cents: number
  onClick?: () => void
}

export default function CartBar({ item_count, total_cents, onClick }: Props) {
  return (
    <div
      role="status"
      aria-label="Carrito"
      onClick={onClick}
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        background: 'var(--color-secondary)',
        color: '#ffffff',
        padding: 'var(--spacing-4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 -2px 8px rgba(0,0,0,0.12)',
        zIndex: 100,
        cursor: onClick ? 'pointer' : undefined,
      }}
    >
      <span style={{ fontSize: '0.875rem', fontWeight: '500' }}>
        {item_count} {item_count === 1 ? 'ítem' : 'ítems'}
      </span>
      <span style={{ fontWeight: '700', fontSize: '1rem' }}>
        {formatCents(total_cents)}
      </span>
    </div>
  )
}
