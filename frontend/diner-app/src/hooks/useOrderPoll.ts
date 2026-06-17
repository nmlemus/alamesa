import { useEffect, useRef, useState } from 'react'
import { ApiError, apiFetch } from '../api/client'
import type { OrderReadWithItems, OrderStatus } from '../types'

const TERMINAL: ReadonlySet<OrderStatus> = new Set(['closed', 'cancelled'])

export function useOrderPoll(orderId: string) {
  const [order, setOrder] = useState<OrderReadWithItems | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const isTerminal = useRef(false)

  useEffect(() => {
    if (order && TERMINAL.has(order.status)) {
      isTerminal.current = true
    }
  }, [order])

  useEffect(() => {
    let isMounted = true

    async function fetchOrder() {
      try {
        const data = await apiFetch<OrderReadWithItems>(`/api/orders/${orderId}`)
        if (isMounted) {
          setOrder(data)
          setError(null)
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof ApiError ? err : new ApiError(0, String(err)))
        }
      }
    }

    fetchOrder()

    const interval = setInterval(() => {
      if (!isTerminal.current) {
        fetchOrder()
      }
    }, 5000)

    return () => {
      isMounted = false
      clearInterval(interval)
    }
  }, [orderId])

  return { order, error }
}
