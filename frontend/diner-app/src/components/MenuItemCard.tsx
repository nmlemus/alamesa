import type { MenuItemRead } from '../types'
import { formatCents } from '../hooks/useCart'

interface Props {
  item: MenuItemRead
  onBodyClick: () => void
  onAdd: () => void
}

export default function MenuItemCard({ item, onBodyClick, onAdd }: Props) {
  const isUnavailable = !item.is_available

  return (
    <div
      style={{
        background: '#ffffff',
        borderRadius: 'var(--radius-lg)',
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        overflow: 'hidden',
        opacity: isUnavailable ? 0.5 : 1,
        marginBottom: 'var(--spacing-3)',
        display: 'flex',
        alignItems: 'stretch',
      }}
    >
      <button
        aria-label={`Ver detalles de ${item.name}`}
        onClick={onBodyClick}
        style={{
          flex: 1,
          textAlign: 'left',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          padding: 'var(--spacing-4)',
          paddingRight: 0,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--spacing-2)',
            marginBottom: 'var(--spacing-1)',
          }}
        >
          <span style={{ fontWeight: '600', fontSize: '1rem', color: '#0f172a' }}>
            {item.name}
          </span>
          {isUnavailable && (
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: '600',
                background: '#e2e8f0',
                color: '#64748b',
                borderRadius: 'var(--radius-full)',
                padding: '2px 8px',
              }}
            >
              Agotado
            </span>
          )}
        </div>
        {item.description && (
          <p
            style={{
              fontSize: '0.875rem',
              color: '#64748b',
              marginBottom: 'var(--spacing-2)',
              lineHeight: '1.4',
            }}
          >
            {item.description}
          </p>
        )}
        <span style={{ fontWeight: '700', color: 'var(--color-primary)', fontSize: '1rem' }}>
          {formatCents(item.price_cents)}
        </span>
      </button>

      <div style={{ display: 'flex', alignItems: 'center', padding: 'var(--spacing-4)' }}>
        <button
          aria-label={`Agregar ${item.name}`}
          onClick={onAdd}
          disabled={isUnavailable}
          style={{
            width: 36,
            height: 36,
            borderRadius: 'var(--radius-full)',
            background: isUnavailable ? '#e2e8f0' : 'var(--color-primary)',
            color: isUnavailable ? '#94a3b8' : '#ffffff',
            border: 'none',
            fontSize: '1.25rem',
            cursor: isUnavailable ? 'not-allowed' : 'pointer',
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
