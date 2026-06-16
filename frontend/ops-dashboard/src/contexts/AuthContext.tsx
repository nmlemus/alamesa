import { createContext, useCallback, useContext, useState } from 'react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import type { RestaurantUserRole } from '../types'

const JWT_KEY = 'ops_jwt'

export interface AuthUser {
  id: string
  role: RestaurantUserRole
  restaurantId: string
}

export interface AuthContextValue {
  user: AuthUser | null
  role: RestaurantUserRole | null
  restaurantId: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

function parseJwtPayload(token: string): Record<string, unknown> {
  const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
  return JSON.parse(atob(base64)) as Record<string, unknown>
}

function tokenToUser(token: string): AuthUser | null {
  try {
    const payload = parseJwtPayload(token)
    const exp = payload['exp'] as number | undefined
    if (exp !== undefined && Date.now() / 1000 > exp) return null
    return {
      id: payload['sub'] as string,
      role: payload['role'] as RestaurantUserRole,
      restaurantId: payload['restaurant_id'] as string,
    }
  } catch {
    return null
  }
}

function readStoredUser(): AuthUser | null {
  const token = sessionStorage.getItem(JWT_KEY)
  return token ? tokenToUser(token) : null
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(readStoredUser)
  const navigate = useNavigate()

  const login = useCallback(async (email: string, password: string): Promise<void> => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = new Error('Login failed') as Error & { status: number }
      err.status = res.status
      throw err
    }
    const data = (await res.json()) as { access_token: string }
    sessionStorage.setItem(JWT_KEY, data.access_token)
    setUser(tokenToUser(data.access_token))
  }, [])

  const logout = useCallback((): void => {
    sessionStorage.removeItem(JWT_KEY)
    setUser(null)
    navigate('/dashboard/login', { replace: true })
  }, [navigate])

  return (
    <AuthContext.Provider
      value={{
        user,
        role: user?.role ?? null,
        restaurantId: user?.restaurantId ?? null,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
