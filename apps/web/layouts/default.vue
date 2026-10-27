<script setup lang="ts">
const route = useRoute()
const hasShell = computed(() => route.path.startsWith('/t/'))
</script>
<template>
  <template v-if="hasShell">
    <a href="#main-content" class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4"
      >Skip to content</a
    >
    <UiSidebarProvider>
      <AppSidebar />
      <UiSidebarInset class="min-w-0">
        <AppTopbar />
        <div id="main-content" tabindex="-1" class="app-content"><slot /></div>
      </UiSidebarInset>
    </UiSidebarProvider>
  </template>
  <slot v-else />
</template>
