import type { Tenant } from '~/types'

export default defineNuxtRouteMiddleware(async (to) => {
  const auth = useAuth()
  await auth.initialize()
  if (to.path === '/login') return
  if (!auth.session.value) return navigateTo('/login')
  if (to.params.tenant_id) {
    const tid = String(to.params.tenant_id)
    // Refresh membership from the server on each navigation; role is UI only.
    try {
      auth.tenants.value = await useApi()<Tenant[]>('/me/tenants')
      const tenant = auth.tenants.value.find((item) => item.id === tid)
      if (!tenant) return navigateTo('/workspaces')
      auth.selected.value = tenant
    } catch {
      return navigateTo('/workspaces')
    }
  }
})
