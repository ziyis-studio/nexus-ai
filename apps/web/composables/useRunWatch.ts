import type { Run } from '~/types'

export const useRunWatch = (tid: string, onUpdate: (run: Run) => Promise<void>) => {
  const api = useApi()
  const auth = useAuth()
  const base = useRuntimeConfig().public.apiBase.replace(/^http/, 'ws').replace(/\/$/, '')
  const connection = ref('idle')
  const stage = ref('queued')
  let socket: WebSocket | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let polling: ReturnType<typeof setInterval> | null = null
  let disposed = false
  let generation = 0
  const stop = () => {
    generation++
    if (timer) clearTimeout(timer)
    if (polling) clearInterval(polling)
    if (socket) {
      socket.onclose = null
      socket.close()
      socket = null
    }
  }
  const watchRun = (runId: string) => {
    stop()
    disposed = false
    const current = generation
    let attempts = 0
    let syncing = false
    const sync = async () => {
      if (disposed || current !== generation || syncing) return
      syncing = true
      try {
        const run = await api<Run>(`/tenants/${tid}/runs/${runId}`)
        if (disposed || current !== generation) return
        await onUpdate(run)
        if (['succeeded', 'failed'].includes(run.status)) {
          stop()
          connection.value = 'complete'
        }
      } catch {
        connection.value = 'reconnecting'
      } finally {
        syncing = false
      }
    }
    const connect = async () => {
      if (disposed || current !== generation) return
      const session = (await auth.supabase?.auth.getSession())?.data.session
      if (!session || disposed || current !== generation) return
      socket = new WebSocket(`${base}/ws/v1/tenants/${tid}/runs/${runId}`)
      socket.onopen = () => {
        connection.value = 'connected'
        socket?.send(JSON.stringify({ type: 'authenticate', token: session.access_token }))
        void sync()
      }
      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          if (message.run_id !== runId || message.tenant_id !== tid) return
          if (message.payload?.stage) stage.value = message.payload.stage
          void sync()
        } catch {
          /* REST reconciliation remains authoritative. */
        }
      }
      socket.onclose = (event) => {
        if (disposed || current !== generation) return
        if (event.code === 4403) {
          connection.value = 'unauthorized'
          stop()
          return
        }
        connection.value = 'reconnecting'
        if (attempts < 6)
          timer = setTimeout(
            () => {
              attempts++
              void connect()
            },
            Math.min(1000 * 2 ** attempts, 15000),
          )
      }
      socket.onerror = () => {
        connection.value = 'reconnecting'
      }
    }
    polling = setInterval(() => void sync(), 2500)
    void connect()
  }
  onBeforeUnmount(() => {
    disposed = true
    stop()
  })
  return { watchRun, connection, stage, stop }
}
