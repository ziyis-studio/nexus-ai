<script setup lang="ts">
import { ArrowRight, Building2, LogOut, ShieldCheck } from '@lucide/vue'
import type { Tenant } from '~/types'
const api = useApi()
const auth = useAuth()
const loading = ref(true)
const error = ref('')
const selecting = ref('')
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
  if (selecting.value) return
  selecting.value = tenant.id
  try {
    auth.selected.value = tenant
    await navigateTo('/t/' + tenant.id + '/tickets')
  } finally {
    selecting.value = ''
  }
}
onMounted(load)
</script>
<template>
  <div class="workspace-page">
    <header class="workspace-header">
      <div class="brand-link"><BrandMark class="size-8 text-primary" /><span>Nexus /</span></div>
      <div class="flex items-center gap-2">
        <AppearanceMenu /><UiButton variant="ghost" @click="auth.signOut"
          ><LogOut data-icon="inline-start" />Sign out</UiButton
        >
      </div>
    </header>
    <main class="workspace-main">
      <div>
        <p class="page-kicker">Your workspaces</p>
        <h1>Where would you like to work?</h1>
        <p class="page-description">Choose an organization to pick up where your team left off.</p>
        <p class="mt-3 text-xs text-muted-foreground">{{ auth.session.value?.user.email }}</p>
      </div>
      <ViewState
        :loading="loading"
        :error="error"
        :empty="!auth.tenants.value.length"
        title="No workspaces yet"
        description="Ask your administrator to add you to an organization."
        @retry="load"
      />
      <div v-if="!loading && !error" class="workspace-grid">
        <UiCard v-for="tenant in auth.tenants.value" :key="tenant.id">
          <UiCardHeader class="gap-5"
            ><UiAvatar class="size-12 rounded-xl"
              ><UiAvatarFallback class="rounded-xl"><Building2 class="size-5" /></UiAvatarFallback
            ></UiAvatar>
            <div class="flex flex-col gap-1">
              <UiCardTitle
                ><h2>{{ tenant.name }}</h2></UiCardTitle
              ><UiCardDescription>{{ tenant.slug }}</UiCardDescription>
            </div></UiCardHeader
          >
          <UiCardContent
            ><p class="text-sm text-muted-foreground">
              Your team’s tickets, knowledge, and AI drafts.
            </p></UiCardContent
          >
          <UiCardFooter class="justify-between gap-3"
            ><UiBadge variant="secondary"
              ><span class="capitalize">{{ tenant.role }}</span></UiBadge
            ><UiButton
              variant="outline"
              :disabled="!!selecting"
              :aria-label="'Open workspace: ' + tenant.name"
              @click="select(tenant)"
              ><UiSpinner v-if="selecting === tenant.id" data-icon="inline-start" />Open workspace<ArrowRight
                data-icon="inline-end" /></UiButton
          ></UiCardFooter>
        </UiCard>
      </div>
      <footer class="workspace-footer">
        <ShieldCheck class="size-4 shrink-0" /><span
          >Each workspace keeps its conversations and knowledge private.</span
        >
      </footer>
    </main>
  </div>
</template>
