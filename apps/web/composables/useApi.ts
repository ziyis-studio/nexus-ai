export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public requestId?: string,
  ) {
    super(message)
  }
}

export const useApi = () => {
  const base = useRuntimeConfig().public.apiBase.replace(/\/$/, '')
  const auth = useAuth()
  return async <T>(
    path: string,
    options: {
      method?: 'GET' | 'POST' | 'PATCH'
      body?: unknown
      query?: Record<string, string | number | undefined>
      idempotencyKey?: string
      signal?: AbortSignal
    } = {},
  ): Promise<T> => {
    const { data } = auth.supabase ? await auth.supabase.auth.getSession() : { data: { session: null } }
    if (!data.session) {
      await auth.signOut()
      throw new ApiError('Your session has ended. Sign in again.', 401)
    }
    try {
      return await $fetch<T>(`${base}/api/v1${path}`, {
        method: options.method || 'GET',
        body: options.body as Record<string, unknown> | undefined,
        query: options.query,
        signal: options.signal,
        headers: {
          Authorization: `Bearer ${data.session.access_token}`,
          ...(options.idempotencyKey ? { 'Idempotency-Key': options.idempotencyKey } : {}),
        },
        retry: 0,
        timeout: 15000,
      })
    } catch (raw: unknown) {
      const error = raw as { status?: number; data?: { error?: { message?: string; request_id?: string } } }
      if (error.status === 401) await auth.signOut()
      throw new ApiError(
        error.data?.error?.message || 'Unable to connect. Check your network and try again.',
        error.status || 0,
        error.data?.error?.request_id,
      )
    }
  }
}
