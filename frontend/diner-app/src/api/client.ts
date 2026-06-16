export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

function readStoredToken(): string | null {
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith('mesadigital_token_')) {
      return localStorage.getItem(key)
    }
  }
  return null
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit & { token?: string }
): Promise<T> {
  const { token, headers: initHeaders, ...rest } = options ?? {}
  const headers = new Headers(initHeaders)
  const authToken = token ?? readStoredToken()

  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`)
  }

  const response = await fetch(path, { ...rest, headers })

  if (!response.ok) {
    const body = await response.text().catch(() => '')
    throw new ApiError(response.status, body || response.statusText)
  }

  return response.json() as Promise<T>
}
