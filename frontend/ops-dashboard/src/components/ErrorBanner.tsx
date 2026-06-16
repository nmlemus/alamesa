interface ErrorBannerProps {
  message: string
}

export default function ErrorBanner({ message }: ErrorBannerProps) {
  return (
    <div
      role="alert"
      style={{
        background: '#fee2e2',
        border: '1px solid #fca5a5',
        borderRadius: 'var(--radius-md)',
        color: '#dc2626',
        padding: 'var(--spacing-3) var(--spacing-4)',
        marginBottom: 'var(--spacing-4)',
        fontSize: '0.875rem',
      }}
    >
      {message}
    </div>
  )
}
