<script setup lang="ts">
import { Activity, BookOpen, Building2, Inbox, Search, Settings } from '@lucide/vue'
import { useEventListener } from '@vueuse/core'
import type { Tenant } from '~/types'
const auth = useAuth()
const route = useRoute()
const commandOpen = ref(false)
const base = computed(() => '/t/' + route.params.tenant_id)
const sections = [
  { path: 'tickets', label: 'Tickets', icon: Inbox },
  { path: 'knowledge', label: 'Knowledge base', icon: BookOpen },
  { path: 'runs', label: 'Execution history', icon: Activity },
  { path: 'settings', label: 'Organization settings', icon: Settings },
]
const current = computed(
  () => sections.find((item) => item.path === route.path.split('/')[3])?.label || 'Workspace',
)
const shortcut = navigator.platform.toLowerCase().includes('mac') ? '⌘ K' : 'Ctrl K'
const go = async (path: string) => {
  commandOpen.value = false
  await navigateTo(path)
}
const workspace = async (tenant: Tenant) => {
  auth.selected.value = tenant
  await go('/t/' + tenant.id + '/tickets')
}
useEventListener(window, 'keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    if (!commandOpen.value && document.querySelector('[role="dialog"], [role="alertdialog"]')) return
    event.preventDefault()
    commandOpen.value = !commandOpen.value
  }
})
</script>
<template>
  <header class="app-topbar">
    <div class="flex min-w-0 items-center gap-3">
      <UiSidebarTrigger aria-label="Toggle navigation" />
      <UiSeparator orientation="vertical" class="h-4" />
      <span class="hidden min-w-0 truncate text-xs text-muted-foreground sm:inline">{{
        auth.selected.value?.name
      }}</span>
      <span class="hidden text-muted-foreground/40 sm:inline">/</span>
      <span class="truncate text-sm font-medium">{{ current }}</span>
    </div>
    <div class="flex shrink-0 items-center gap-2">
      <UiButton
        variant="outline"
        class="hidden w-48 justify-between md:flex"
        aria-keyshortcuts="Control+K Meta+K"
        @click="commandOpen = true"
        ><span class="flex items-center gap-2 text-muted-foreground"
          ><Search data-icon="inline-start" />Quick navigation</span
        ><kbd class="text-[10px] text-muted-foreground">{{ shortcut }}</kbd></UiButton
      >
      <UiButton
        variant="ghost"
        size="icon"
        class="md:hidden"
        aria-label="Open quick navigation"
        @click="commandOpen = true"
        ><Search
      /></UiButton>
      <AppearanceMenu />
    </div>
  </header>
  <UiCommandDialog
    v-model:open="commandOpen"
    title="Quick navigation"
    description="Find a page or switch to one of your workspaces."
    class="sm:max-w-xl"
  >
    <UiCommandInput placeholder="Find a page or workspace…" aria-label="Search pages and workspaces" />
    <UiCommandList aria-label="Pages and workspaces"
      ><UiCommandEmpty>No matching pages or workspaces.</UiCommandEmpty>
      <UiCommandGroup heading="Go to">
        <UiCommandItem
          v-for="item in sections"
          :key="item.path"
          :value="item.label"
          @select="go(base + '/' + item.path)"
          ><component :is="item.icon" /><span>{{ item.label }}</span></UiCommandItem
        >
      </UiCommandGroup>
      <UiCommandSeparator />
      <UiCommandGroup heading="Switch workspace"
        ><UiCommandItem
          v-for="tenant in auth.tenants.value"
          :key="tenant.id"
          :value="tenant.name"
          @select="workspace(tenant)"
          ><Building2 /><span>{{ tenant.name }}</span
          ><UiCommandShortcut>{{ tenant.role }}</UiCommandShortcut></UiCommandItem
        ></UiCommandGroup
      >
    </UiCommandList>
  </UiCommandDialog>
</template>
