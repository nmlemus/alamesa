export default function ErrorBanner({ message }: { message: string }) {
  return (
    <div
      role="alert"
      style={{
        margin: 'var(--spacing-4)',
        padding: 'var(--spacing-4)',
        background: '#fef2f2',
        border: '1px solid #fca5a5',
        borderRadius: 'var(--radius-md)',
        color: '#dc2626',
        fontSize: '0.9375rem',
        textAlign: 'center',
      }}
    >
      {message}
    </div>
  )
}
