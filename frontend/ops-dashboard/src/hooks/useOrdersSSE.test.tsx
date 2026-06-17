import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useOrdersSSE } from './useOrdersSSE'
import type { OrderRead } from '../types'

const JWT_KEY = 'ops_jwt'

// ── helpers ──────────────────────────────────────────────────────────────────

function makeOrder(id: string, status: OrderRead['status'] = 'pending'): OrderRead {
  return {
    id,
    restaurant_id: 'rest-1',
    table_id: 'table-1',
    diner_id: 'diner-1',
    status,
    created_at: '2026-06-17T00:00:00Z',
  }
}

function encodeSSE(events: Array<{ event: string; data: unknown }>): string {
  return (
    'retry: 3000\n\n' +
    events
      .map(e => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`)
      .join('')
  )
}

/**
 * Returns a fetch-response-like object whose body yields `body` once and then
 * blocks forever on the next read() — simulating a live SSE connection.
 * The hook sets status=connected and processes events, then suspends at read().
 */
function makeOpenStreamResponse(body: string): Response {
  const encoder = new TextEncoder()
  let yielded = false
  const reader = {
    read: (): Promise<ReadableStreamReadResult<Uint8Array>> => {
      if (!yielded) {
        yielded = true
        return Promise.resolve({ done: false, value: encoder.encode(body) })
      }
      // Never resolves — simulates an open SSE connection
      return new Promise(() => {})
    },
    releaseLock: () => {},
    cancel: () => Promise.resolve(),
  }
  return {
    ok: true,
    status: 200,
    body: { getReader: () => reader },
  } as unknown as Response
}

// ── setup ────────────────────────────────────────────────────────────────────

let mockFetch: ReturnType<typeof vi.fn>

beforeEach(() => {
  mockFetch = vi.fn()
  vi.stubGlobal('fetch', mockFetch)
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(key =>
    key === JWT_KEY ? 'mock-jwt-token' : null
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

// ── tests ────────────────────────────────────────────────────────────────────

describe('useOrdersSSE', () => {
  it('starts with reconnecting status', () => {
    // fetch never resolves → stays reconnecting
    mockFetch.mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useOrdersSSE('rest-1'))

    expect(result.current.connectionStatus).toBe('reconnecting')
    expect(result.current.orders).toEqual([])
  })

  it('becomes connected and upserts orders from order_updated events', async () => {
    const order = makeOrder('order-1', 'pending')
    const body = encodeSSE([{ event: 'order_updated', data: order }])
    // Use an open stream so the connection stays alive (status remains 'connected')
    mockFetch.mockResolvedValue(makeOpenStreamResponse(body))

    const { result } = renderHook(() => useOrdersSSE('rest-1'))

    await act(async () => {
      await new Promise(r => setTimeout(r, 50))
    })

    expect(result.current.connectionStatus).toBe('connected')
    expect(result.current.orders).toHaveLength(1)
    expect(result.current.orders[0].id).toBe('order-1')
    expect(result.current.orders[0].status).toBe('pending')
  })

  it('upserts (updates) an existing order when a new event arrives for the same id', async () => {
    const orderV1 = makeOrder('order-1', 'pending')
    const orderV2 = makeOrder('order-1', 'confirmed')
    const body = encodeSSE([
      { event: 'order_updated', data: orderV1 },
      { event: 'order_updated', data: orderV2 },
    ])
    mockFetch.mockResolvedValue(makeOpenStreamResponse(body))

    const { result } = renderHook(() => useOrdersSSE('rest-1'))

    await act(async () => {
      await new Promise(r => setTimeout(r, 50))
    })

    expect(result.current.orders).toHaveLength(1)
    expect(result.current.orders[0].status).toBe('confirmed')
  })

  it('adds new orders without removing existing ones', async () => {
    const order1 = makeOrder('order-1', 'pending')
    const order2 = makeOrder('order-2', 'preparing')
    const body = encodeSSE([
      { event: 'order_updated', data: order1 },
      { event: 'order_updated', data: order2 },
    ])
    mockFetch.mockResolvedValue(makeOpenStreamResponse(body))

    const { result } = renderHook(() => useOrdersSSE('rest-1'))

    await act(async () => {
      await new Promise(r => setTimeout(r, 50))
    })

    expect(result.current.orders).toHaveLength(2)
  })

  it('ignores unknown event types', async () => {
    const body = 'retry: 3000\n\nevent: heartbeat\ndata: {}\n\n'
    mockFetch.mockResolvedValue(makeOpenStreamResponse(body))

    const { result } = renderHook(() => useOrdersSSE('rest-1'))

    await act(async () => {
      await new Promise(r => setTimeout(r, 50))
    })

    expect(result.current.orders).toEqual([])
  })

  it('disconnects immediately if no JWT is stored', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue(null)

    const { result } = renderHook(() => useOrdersSSE('rest-1'))

    await act(async () => {
      await new Promise(r => setTimeout(r, 50))
    })

    expect(result.current.connectionStatus).toBe('disconnected')
    expect(mockFetch).not.toHaveBeenCalled()
  })

  it('reaches disconnected after MAX_ERROR_RETRIES consecutive network errors', async () => {
    // Use a network error (not a clean stream close) so errorRetries increments.
    // Once errorRetries > MAX_ERROR_RETRIES no more setTimeout is scheduled,
    // so vi.runAllTimersAsync() naturally terminates.
    mockFetch.mockRejectedValue(new Error('network error'))

    vi.useFakeTimers()
    try {
      const { result } = renderHook(() => useOrdersSSE('rest-1'))

      await act(async () => {
        await vi.runAllTimersAsync()
      })

      expect(result.current.connectionStatus).toBe('disconnected')
    } finally {
      vi.useRealTimers()
    }
  })

  it('sends Authorization header with the JWT token', async () => {
    mockFetch.mockResolvedValue(makeOpenStreamResponse('retry: 3000\n\n'))

    renderHook(() => useOrdersSSE('rest-1'))

    await act(async () => {
      await new Promise(r => setTimeout(r, 50))
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/restaurants/rest-1/orders/stream',
      expect.objectContaining({
        headers: { Authorization: 'Bearer mock-jwt-token' },
      })
    )
  })

  it('closes connection and clears timers on unmount', async () => {
    const abortSpy = vi.spyOn(AbortController.prototype, 'abort')
    // Keep the stream open indefinitely
    mockFetch.mockReturnValue(new Promise(() => {}))

    const { unmount } = renderHook(() => useOrdersSSE('rest-1'))

    await act(async () => {
      await new Promise(r => setTimeout(r, 10))
    })

    unmount()

    expect(abortSpy).toHaveBeenCalled()
  })
})
