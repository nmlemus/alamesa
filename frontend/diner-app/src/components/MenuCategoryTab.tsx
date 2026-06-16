interface Props {
  name: string
  isActive: boolean
  onClick: () => void
}

export default function MenuCategoryTab({ name, isActive, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: 'var(--spacing-2) var(--spacing-4)',
        background: isActive ? 'var(--color-primary)' : '#ffffff',
        color: isActive ? '#ffffff' : '#374151',
        border: isActive ? 'none' : '1px solid #e2e8f0',
        borderRadius: 'var(--radius-full)',
        fontSize: '0.875rem',
        fontWeight: isActive ? '600' : '400',
        cursor: 'pointer',
        whiteSpace: 'nowrap',
        flexShrink: 0,
      }}
    >
      {name}
    </button>
  )
}
