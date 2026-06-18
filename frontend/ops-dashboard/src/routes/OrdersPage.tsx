import { useAuth } from '../contexts/AuthContext'
import { useOrdersSSE } from '../hooks/useOrdersSSE'
import ErrorBanner from '../components/ErrorBanner'

export default function OrdersPage() {
  const { restaurantId } = useAuth()
  const { orders, connectionStatus } = useOrdersSSE(restaurantId ?? '')

  return (
    <main>
      {connectionStatus === 'disconnected' && (
        <ErrorBanner message="Conexión perdida. Comprueba tu red e intenta recargar." />
      )}
      <p>Orders: {orders.length}</p>
    </main>
  )
}
