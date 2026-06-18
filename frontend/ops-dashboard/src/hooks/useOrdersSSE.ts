import { useEffect, useState } from 'react'
import type { OrderRead } from '../types'

const JWT_KEY = 'ops_jwt'

export type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected'

// After this many consecutive network/auth errors, give up and show ErrorBanner.
const MAX_ERROR_RETRIES = 3

export function useOrdersSSE(restaurantId: string) {
  const [orders, setOrders] = useState<OrderRead[]>([])
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('reconnecting')

  useEffect(() => {
    let mounted = true
    let retryDelay = 3000
    let errorRetries = 0
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let currentController = new AbortController()

    function upsertOrder(order: OrderRead) {
      setOrders(prev => {
        const idx = prev.findIndex(o => o.id === order.id)
        if (idx === -1) return [...prev, order]
        const next = [...prev]
        next[idx] = order
        return next
      })
    }

    async function connect() {
      if (!mounted) return

      const token = sessionStorage.getItem(JWT_KEY)
      if (!token) {
        setConnectionStatus('disconnected')
        return
      }

      currentController = new AbortController()

      let streamClosedCleanly = false
      try {
        const response = await fetch(`/api/restaurants/${restaurantId}/orders/stream`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: currentController.signal,
        })

        if (!response.ok || !response.body) {
          throw new Error(`HTTP ${response.status}`)
        }

        if (!mounted) return
        setConnectionStatus('connected')
        errorRetries = 0  // reset on any successful HTTP connection

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (mounted) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          // SSE events are separated by double newline
          const parts = buffer.split('\n\n')
          buffer = parts.pop() ?? ''

          for (const part of parts) {
            if (!part.trim()) continue

            let eventType = ''
            const dataLines: string[] = []

            for (const line of part.split('\n')) {
              if (line.startsWith('event: ')) {
                eventType = line.slice(7).trim()
              } else if (line.startsWith('data: ')) {
                dataLines.push(line.slice(6))
              } else if (line.startsWith('retry: ')) {
                const parsed = parseInt(line.slice(7), 10)
                if (!isNaN(parsed)) retryDelay = parsed
              }
            }

            if (eventType === 'order_updated' && dataLines.length > 0) {
              try {
                const order = JSON.parse(dataLines.join('\n')) as OrderRead
                upsertOrder(order)
              } catch {
                // ignore malformed event data
              }
            }
          }
        }

        // Stream closed normally — reconnect indefinitely (native EventSource behavior)
        streamClosedCleanly = true
      } catch (err) {
        if (!mounted) return
        if ((err as Error).name === 'AbortError') return

        // Network or HTTP error: count toward giving up
        errorRetries++
        if (errorRetries > MAX_ERROR_RETRIES) {
          setConnectionStatus('disconnected')
          return
        }
      }

      if (!mounted) return

      // Reconnect: reset retryDelay only on clean close (server sent retry directive)
      // On error, keep whatever delay we have (default 3000ms)
      if (streamClosedCleanly) {
        // retryDelay may have been set by the server's retry: field
      }

      setConnectionStatus('reconnecting')
      retryTimer = setTimeout(connect, retryDelay)
    }

    connect()

    return () => {
      mounted = false
      currentController.abort()
      if (retryTimer !== null) clearTimeout(retryTimer)
    }
  }, [restaurantId])

  return { orders, connectionStatus }
}
