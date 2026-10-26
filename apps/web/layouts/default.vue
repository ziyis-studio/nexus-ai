<script setup lang="ts">
const auth = useAuth()
const route = useRoute()
const menuOpen = ref(false)
const { feedback } = useFeedback()
const hasShell = computed(() => route.path.startsWith('/t/'))
const section = computed(() => route.path.split('/')[3] || 'tickets')
const links = [
  { path: 'tickets', label: 'Tickets', icon: 'Inbox' },
  { path: 'knowledge', label: 'Knowledge base', icon: 'BookOpen' },
  { path: 'runs', label: 'Execution history', icon: 'Activity' },
]
watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false
  },
)
</script>
<template>
  <div v-if="hasShell" class="app-frame">
    <aside class="sidebar" :class="{ 'sidebar-open': menuOpen }">
      <NuxtLink class="brand" to="/workspaces" aria-label="Nexus AI workspaces"
        ><span class="brand-symbol">N</span><span>NEXUS<span class="brand-ai">AI</span></span></NuxtLink
      >
      <NuxtLink to="/workspaces" class="workspace-switch"
        ><span class="org-avatar">{{ auth.selected.value?.name.slice(0, 1) || 'N' }}</span
        ><span class="workspace-copy"
          ><strong>{{ auth.selected.value?.name }}</strong
          ><small>Workspace · {{ auth.selected.value?.role }}</small></span
        ><NIcon name="ChevronDown" :size="15"
      /></NuxtLink>
      <span class="nav-caption">WORKSPACE</span>
      <nav aria-label="Workspace navigation">
        <NuxtLink
          v-for="link in links"
          :key="link.path"
          :to="`/t/${route.params.tenant_id}/${link.path}`"
          class="nav-link"
          :class="{ active: section === link.path }"
          ><NIcon :name="link.icon" /><span>{{ link.label }}</span
          ><span v-if="link.path === 'tickets'" class="nav-shortcut">↗</span></NuxtLink
        >
      </nav>
      <div class="sidebar-bottom">
        <div class="engine-card">
          <span class="engine-mark"><NIcon name="Sparkles" :size="17" /></span
          ><strong>Intelligence, with oversight.</strong>
          <p>Every AI suggestion stays a draft until your team reviews it.</p>
          <span class="engine-pill"><span class="status-dot" />Human review enabled</span>
        </div>
        <NuxtLink
          class="nav-link"
          :class="{ active: section === 'settings' }"
          :to="`/t/${route.params.tenant_id}/settings`"
          ><NIcon name="Settings" />Organization settings</NuxtLink
        >
        <div class="profile-row">
          <span class="user-avatar">{{ auth.session.value?.user.email?.slice(0, 1).toUpperCase() }}</span
          ><span
            ><strong>{{ auth.session.value?.user.email?.split('@')[0] }}</strong
            ><small>{{ auth.selected.value?.role }}</small></span
          ><button class="icon-btn" aria-label="Sign out" @click="auth.signOut">
            <NIcon name="LogOut" :size="16" />
          </button>
        </div>
      </div>
    </aside>
    <div v-if="menuOpen" class="sidebar-backdrop" @click="menuOpen = false" />
    <div class="main-frame">
      <header class="topbar">
        <div class="breadcrumb">
          <button class="icon-btn mobile-menu" aria-label="Toggle navigation" @click="menuOpen = !menuOpen">
            <NIcon name="Menu" /></button
          ><NIcon name="Building2" :size="16" /><span>{{ auth.selected.value?.name }}</span
          ><span class="breadcrumb-divider">/</span
          ><strong>{{
            section === 'knowledge'
              ? 'Knowledge base'
              : section === 'runs'
                ? 'Execution history'
                : section === 'settings'
                  ? 'Settings'
                  : 'Tickets'
          }}</strong>
        </div>
        <span class="topbar-note"><NIcon name="ShieldCheck" :size="15" />Tenant-isolated workspace</span>
      </header>
      <main class="main-content"><slot /></main>
      <footer class="app-footer">
        <span>NEXUS AI <span class="muted">/ Ticket intelligence engine</span></span
        ><span>Designed for human decisions <span class="footer-dot" /></span>
      </footer>
    </div>
  </div>
  <slot v-else />
  <Transition name="toast"
    ><div v-if="feedback" class="toast" role="status"><NIcon name="Check" />{{ feedback }}</div></Transition
  >
</template>
