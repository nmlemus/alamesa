import type { OrderStatus } from '../types'

const NODES = [
  { label: 'Recibido' },
  { label: 'En preparación' },
  { label: '¡Listo!' },
  { label: 'Entregado' },
] as const

const STATUS_TO_INDEX: Partial<Record<OrderStatus, number>> = {
  pending: 0,
  confirmed: 1,
  preparing: 1,
  ready: 2,
  closed: 3,
}

interface Props {
  status: OrderStatus
}

export default function OrderStatusTracker({ status }: Props) {
  const currentIndex = STATUS_TO_INDEX[status] ?? 0

  return (
    <div
      role="list"
      aria-label="Estado del pedido"
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        padding: 'var(--spacing-6) var(--spacing-4)',
      }}
    >
      {NODES.map((node, index) => {
        const isCompleted = index < currentIndex
        const isCurrent = index === currentIndex
        const isLast = index === NODES.length - 1

        return (
          <div
            key={node.label}
            role="listitem"
            aria-current={isCurrent ? 'step' : undefined}
            style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', position: 'relative' }}
          >
            {!isLast && (
              <div
                aria-hidden="true"
                style={{
                  position: 'absolute',
                  top: 16,
                  left: '50%',
                  right: '-50%',
                  height: 3,
                  background: isCompleted || isCurrent ? 'var(--color-primary)' : '#e2e8f0',
                  zIndex: 0,
                }}
              />
            )}

            <div
              aria-hidden="true"
              style={{
                width: 32,
                height: 32,
                borderRadius: 'var(--radius-full)',
                background: isCompleted || isCurrent ? 'var(--color-primary)' : '#e2e8f0',
                border: isCurrent ? '3px solid var(--color-primary)' : 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
                zIndex: 1,
                flexShrink: 0,
              }}
            >
              {(isCompleted || isCurrent) && (
                <span style={{ color: '#ffffff', fontSize: '0.875rem', fontWeight: 700 }}>
                  {isCompleted ? '✓' : index + 1}
                </span>
              )}
            </div>

            <span
              style={{
                marginTop: 'var(--spacing-2)',
                fontSize: '0.75rem',
                fontWeight: isCurrent ? 700 : 400,
                color: isCompleted || isCurrent ? '#0f172a' : '#94a3b8',
                textAlign: 'center',
                lineHeight: 1.3,
              }}
            >
              {node.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}
