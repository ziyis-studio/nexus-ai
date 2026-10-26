import type { Session } from '@supabase/supabase-js'
import type { Tenant } from '~/types'

export const useAuth = () => {
  const { $supabase } = useNuxtApp()
  const router = useRouter()
  const session = useState<Session | null>('auth.session', () => null)
  const initialized = useState('auth.initialized', () => false)
  const tenants = useState<Tenant[]>('auth.tenants', () => [])
  const selected = useState<Tenant | null>('auth.tenant', () => null)
  const initialize = async () => {
    if (initialized.value) return
    if ($supabase) {
      session.value = (await $supabase.auth.getSession()).data.session
      $supabase.auth.onAuthStateChange((_event, next) => {
        session.value = next
        if (!next) {
          tenants.value = []
          selected.value = null
          if (router.currentRoute.value.path !== '/login') void router.replace('/login')
        }
      })
    }
    initialized.value = true
  }
  const signOut = async () => {
    await $supabase?.auth.signOut()
    session.value = null
    tenants.value = []
    selected.value = null
    await router.replace('/login')
  }
  return { supabase: $supabase, session, initialize, signOut, tenants, selected }
}
