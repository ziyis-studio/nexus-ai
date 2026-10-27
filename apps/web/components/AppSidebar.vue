<script setup lang="ts">
import {
  Activity,
  ArrowUpRight,
  BookOpen,
  Building2,
  Check,
  ChevronsUpDown,
  Inbox,
  LogOut,
  Settings,
  ShieldCheck,
} from '@lucide/vue'
import type { Tenant } from '~/types'
import { useSidebar } from '~/components/ui/sidebar'
const auth = useAuth()
const route = useRoute()
const { setOpenMobile } = useSidebar()
const section = computed(() => String(route.path.split('/')[3] || 'tickets'))
const base = computed(() => '/t/' + route.params.tenant_id)
const links = [
  { path: 'tickets', label: 'Tickets', icon: Inbox },
  { path: 'knowledge', label: 'Knowledge base', icon: BookOpen },
  { path: 'runs', label: 'Execution history', icon: Activity },
]
const initials = (value: string) =>
  value
    .split(' ')
    .map((word) => word[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
const selectWorkspace = async (tenant: Tenant) => {
  auth.selected.value = tenant
  setOpenMobile(false)
  await navigateTo('/t/' + tenant.id + '/tickets')
}
watch(
  () => route.fullPath,
  () => setOpenMobile(false),
)
</script>
<template>
  <UiSidebar variant="inset" collapsible="icon">
    <UiSidebarHeader class="gap-6 px-3 pb-5 pt-5">
      <NuxtLink to="/workspaces" class="brand-link px-1" aria-label="Nexus workspaces"
        ><BrandMark class="size-8 shrink-0 text-sidebar-primary" /><span
          class="group-data-[collapsible=icon]:hidden"
          >Nexus<span class="ml-1 text-sidebar-foreground/45">/</span></span
        ></NuxtLink
      >
      <UiSidebarMenu
        ><UiSidebarMenuItem>
          <UiDropdownMenu>
            <UiDropdownMenuTrigger as-child>
              <UiSidebarMenuButton size="lg" tooltip="Switch workspace">
                <span class="sr-only">Switch workspace:</span
                ><span class="sr-only hidden group-data-[collapsible=icon]:inline">{{
                  auth.selected.value?.name
                }}</span>
                <UiAvatar aria-hidden="true" class="size-8 shrink-0 rounded-lg"
                  ><UiAvatarFallback class="rounded-lg">{{
                    initials(auth.selected.value?.name || 'N')
                  }}</UiAvatarFallback></UiAvatar
                >
                <span class="sidebar-copy"
                  ><strong>{{ auth.selected.value?.name }}</strong
                  ><small class="capitalize">{{ auth.selected.value?.role }} workspace</small></span
                >
                <ChevronsUpDown class="ml-auto" />
              </UiSidebarMenuButton>
            </UiDropdownMenuTrigger>
            <UiDropdownMenuContent align="start" side="right" :side-offset="8" class="w-72">
              <UiDropdownMenuGroup
                ><UiDropdownMenuLabel>Your workspaces</UiDropdownMenuLabel>
                <UiDropdownMenuItem
                  v-for="tenant in auth.tenants.value"
                  :key="tenant.id"
                  @select="selectWorkspace(tenant)"
                >
                  <Building2 />
                  <div class="flex min-w-0 flex-1 flex-col">
                    <span class="truncate">{{ tenant.name }}</span
                    ><span class="text-xs text-muted-foreground capitalize">{{ tenant.role }}</span>
                  </div>
                  <Check v-if="tenant.id === auth.selected.value?.id" class="ml-auto" />
                </UiDropdownMenuItem>
              </UiDropdownMenuGroup>
              <UiDropdownMenuSeparator />
              <UiDropdownMenuGroup
                ><UiDropdownMenuItem as-child
                  ><NuxtLink to="/workspaces"><ArrowUpRight />All workspaces</NuxtLink></UiDropdownMenuItem
                ></UiDropdownMenuGroup
              >
            </UiDropdownMenuContent>
          </UiDropdownMenu>
        </UiSidebarMenuItem></UiSidebarMenu
      >
    </UiSidebarHeader>
    <UiSidebarContent>
      <UiSidebarGroup>
        <UiSidebarGroupLabel>Workspace</UiSidebarGroupLabel>
        <UiSidebarGroupContent
          ><nav aria-label="Workspace navigation">
            <UiSidebarMenu>
              <UiSidebarMenuItem v-for="link in links" :key="link.path">
                <UiSidebarMenuButton as-child :is-active="section === link.path" :tooltip="link.label"
                  ><NuxtLink :to="base + '/' + link.path"
                    ><component :is="link.icon" /><span>{{ link.label }}</span></NuxtLink
                  ></UiSidebarMenuButton
                >
              </UiSidebarMenuItem>
            </UiSidebarMenu>
          </nav></UiSidebarGroupContent
        >
      </UiSidebarGroup>
      <UiSidebarGroup class="mt-auto">
        <div class="flex flex-col gap-2 px-2 py-5 group-data-[collapsible=icon]:hidden">
          <ShieldCheck class="size-5 text-sidebar-primary" />
          <p class="text-xs font-medium">A human makes the final call.</p>
          <p class="sidebar-caption">AI drafts stay yours to review.<br />Nothing is sent automatically.</p>
        </div>
        <UiSidebarMenu
          ><UiSidebarMenuItem
            ><UiSidebarMenuButton as-child tooltip="Organization settings" :is-active="section === 'settings'"
              ><NuxtLink :to="base + '/settings'"
                ><Settings /><span>Organization settings</span></NuxtLink
              ></UiSidebarMenuButton
            ></UiSidebarMenuItem
          ></UiSidebarMenu
        >
      </UiSidebarGroup>
    </UiSidebarContent>
    <UiSidebarSeparator class="mx-0" />
    <UiSidebarFooter class="px-3 py-4">
      <div class="flex items-center gap-3">
        <UiAvatar class="size-8 shrink-0"
          ><UiAvatarFallback>{{
            auth.session.value?.user.email?.slice(0, 2).toUpperCase()
          }}</UiAvatarFallback></UiAvatar
        >
        <div class="sidebar-copy group-data-[collapsible=icon]:hidden">
          <strong>{{ auth.session.value?.user.email?.split('@')[0] }}</strong
          ><small>{{ auth.session.value?.user.email }}</small>
        </div>
        <UiSidebarMenuButton
          class="size-8 shrink-0 group-data-[collapsible=icon]:hidden"
          tooltip="Sign out"
          aria-label="Sign out"
          @click="auth.signOut"
          ><LogOut
        /></UiSidebarMenuButton>
      </div>
    </UiSidebarFooter>
    <UiSidebarRail />
  </UiSidebar>
</template>
