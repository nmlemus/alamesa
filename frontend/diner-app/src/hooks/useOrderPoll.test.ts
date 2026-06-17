import { renderHook, act } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { useOrderPoll } from './useOrderPoll'
import type { OrderReadWithItems } from '../types'

vi.mock('../api/client', () => ({
  apiFetch: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(status: number, message: string) {
      super(message)
      this.status = status
      this.name = 'ApiError'
    }
  },
}))

import { apiFetch, ApiError } from '../api/client'

const mockApiFetch = vi.mocked(apiFetch)

function makeOrder(status: OrderReadWithItems['status']): OrderReadWithItems {
  return {
    id: 'order-1',
    restaurant_id: 'rest-1',
    table_id: 'table-1',
    diner_id: 'diner-1',
    status,
    created_at: '2026-06-17T00:00:00Z',
    items: [],
    total_cents: 0,
    item_count: 0,
  }
}

describe('useOrderPoll', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('fetches order on mount', async () => {
    mockApiFetch.mockResolvedValue(makeOrder('pending'))

    const { result } = renderHook(() => useOrderPoll('order-1'))

    await act(async () => {
      await Promise.resolve()
    })

    expect(mockApiFetch).toHaveBeenCalledTimes(1)
    expect(mockApiFetch).toHaveBeenCalledWith('/api/orders/order-1')
    expect(result.current.order?.status).toBe('pending')
    expect(result.current.error).toBeNull()
  })

  it('polls again after 5 seconds', async () => {
    mockApiFetch.mockResolvedValue(makeOrder('pending'))

    renderHook(() => useOrderPoll('order-1'))

    await act(async () => {
      await Promise.resolve()
    })
    expect(mockApiFetch).toHaveBeenCalledTimes(1)

    await act(async () => {
      vi.advanceTimersByTime(5000)
      await Promise.resolve()
    })
    expect(mockApiFetch).toHaveBeenCalledTimes(2)

    await act(async () => {
      vi.advanceTimersByTime(5000)
      await Promise.resolve()
    })
    expect(mockApiFetch).toHaveBeenCalledTimes(3)
  })

  it('stops polling when status is closed', async () => {
    mockApiFetch
      .mockResolvedValueOnce(makeOrder('pending'))
      .mockResolvedValueOnce(makeOrder('closed'))

    const { result } = renderHook(() => useOrderPoll('order-1'))

    await act(async () => {
      await Promise.resolve()
    })

    await act(async () => {
      vi.advanceTimersByTime(5000)
      await Promise.resolve()
    })
    expect(result.current.order?.status).toBe('closed')

    await act(async () => {
      vi.advanceTimersByTime(5000)
      await Promise.resolve()
    })
    // No further calls after terminal status
    expect(mockApiFetch).toHaveBeenCalledTimes(2)
  })

  it('stops polling when status is cancelled', async () => {
    mockApiFetch
      .mockResolvedValueOnce(makeOrder('pending'))
      .mockResolvedValueOnce(makeOrder('cancelled'))

    const { result } = renderHook(() => useOrderPoll('order-1'))

    await act(async () => {
      await Promise.resolve()
    })
    await act(async () => {
      vi.advanceTimersByTime(5000)
      await Promise.resolve()
    })
    expect(result.current.order?.status).toBe('cancelled')

    await act(async () => {
      vi.advanceTimersByTime(5000)
      await Promise.resolve()
    })
    expect(mockApiFetch).toHaveBeenCalledTimes(2)
  })

  it('sets error on fetch failure', async () => {
    const apiError = new ApiError(404, 'Not found')
    mockApiFetch.mockRejectedValue(apiError)

    const { result } = renderHook(() => useOrderPoll('order-1'))

    await act(async () => {
      await Promise.resolve()
    })

    expect(result.current.order).toBeNull()
    expect(result.current.error).toBeTruthy()
  })

  it('clears interval on unmount', async () => {
    mockApiFetch.mockResolvedValue(makeOrder('pending'))

    const { unmount } = renderHook(() => useOrderPoll('order-1'))

    await act(async () => {
      await Promise.resolve()
    })

    unmount()

    await act(async () => {
      vi.advanceTimersByTime(10000)
      await Promise.resolve()
    })

    expect(mockApiFetch).toHaveBeenCalledTimes(1)
  })
})
