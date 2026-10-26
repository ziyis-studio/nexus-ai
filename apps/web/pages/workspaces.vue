<script setup lang="ts">
import type { Tenant } from '~/types'
const api = useApi()
const auth = useAuth()
const loading = ref(true)
const error = ref('')
const load = async () => {
  loading.value = true
  error.value = ''
  try {
    auth.tenants.value = await api<Tenant[]>('/me/tenants')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
const select = async (tenant: Tenant) => {
  auth.selected.value = tenant
  await navigateTo(`/t/${tenant.id}/tickets`)
}
onMounted(load)
</script>
<template>
  <div class="workspace-page">
    <header>
      <div class="brand">
        <span class="brand-symbol">N</span><span>NEXUS<span class="brand-ai">AI</span></span>
      </div>
      <button class="btn btn-ghost" @click="auth.signOut"><NIcon name="LogOut" />Sign out</button>
    </header>
    <main>
      <span class="eyebrow">ONE ACCOUNT. YOUR ORGANIZATIONS.</span>
      <h1>Where would you like to work?</h1>
      <p class="page-description">
        Choose a workspace to continue. Each organization has its own secure space.
      </p>
      <ViewState
        :loading="loading"
        :error="error"
        :empty="!auth.tenants.value.length"
        title="No workspaces yet"
        description="Ask your administrator to add you to an organization."
        @retry="load"
      />
      <div v-if="!loading && !error" class="workspace-grid">
        <button
          v-for="tenant in auth.tenants.value"
          :key="tenant.id"
          class="workspace-option"
          @click="select(tenant)"
        >
          <span class="workspace-option-icon">{{ tenant.name.slice(0, 1) }}</span>
          <h2>{{ tenant.name }}</h2>
          <p>{{ tenant.slug }}</p>
          <div>
            <span class="badge">{{ tenant.role }}</span
            ><NIcon name="ArrowUpRight" />
          </div>
        </button>
      </div>
    </main>
    <footer>
      <NIcon name="ShieldCheck" :size="16" />Membership is checked every time you open a workspace.
    </footer>
  </div>
</template>
