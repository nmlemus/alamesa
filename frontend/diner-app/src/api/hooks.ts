import { useCallback, useEffect, useState } from 'react'
import { ApiError, apiFetch } from './client'
import type { CategoryRead, RestaurantRead, TableRead } from '../types'

export function useRestaurant(slug: string) {
  const [restaurant, setRestaurant] = useState<RestaurantRead | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)

    apiFetch<RestaurantRead>(`/api/public/restaurants/${slug}`)
      .then((data) => {
        if (!cancelled) setRestaurant(data)
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof ApiError ? err : new ApiError(0, String(err)))
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [slug])

  return { restaurant, isLoading, error }
}

export function useMenu(slug: string) {
  const [categories, setCategories] = useState<CategoryRead[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)

    apiFetch<CategoryRead[]>(`/api/public/restaurants/${slug}/menu`)
      .then((data) => {
        if (!cancelled) setCategories(data)
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof ApiError ? err : new ApiError(0, String(err)))
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [slug])

  return { categories, isLoading, error }
}

export function useTable(slug: string, tableNumber: string | undefined) {
  const [table, setTable] = useState<TableRead | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  useEffect(() => {
    if (!tableNumber) return
    let cancelled = false
    setIsLoading(true)
    setError(null)

    apiFetch<TableRead>(`/api/public/restaurants/${slug}/tables/${tableNumber}`)
      .then((data) => {
        if (!cancelled) setTable(data)
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof ApiError ? err : new ApiError(0, String(err)))
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [slug, tableNumber])

  return { table, isLoading, error }
}

interface DinerTokenResponse {
  access_token: string
  token_type: string
}

export function useRegister() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const register = useCallback(
    async (name: string, phone: string, restaurantId: string): Promise<void> => {
      setIsLoading(true)
      setError(null)
      try {
        const data = await apiFetch<DinerTokenResponse>(
          `/api/public/restaurants/${restaurantId}/diners/register`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, phone }),
          }
        )
        localStorage.setItem(`mesadigital_token_${restaurantId}`, data.access_token)
      } catch (err) {
        const apiErr = err instanceof ApiError ? err : new ApiError(0, String(err))
        setError(apiErr)
        throw apiErr
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  return { register, isLoading, error }
}
