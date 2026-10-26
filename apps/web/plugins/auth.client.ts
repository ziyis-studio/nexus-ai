import { createClient } from '@supabase/supabase-js'

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig().public
  const supabase =
    config.supabaseUrl && config.supabasePublishableKey
      ? createClient(config.supabaseUrl, config.supabasePublishableKey, {
          auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false },
        })
      : null
  return { provide: { supabase } }
})
