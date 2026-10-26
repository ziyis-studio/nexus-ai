<script setup lang="ts">
defineProps<{ loading?: boolean; error?: string; empty?: boolean; title?: string; description?: string }>()
defineEmits(['retry'])
</script>
<template>
  <div v-if="loading" class="view-state" role="status">
    <span class="spinner" /><span>Loading your workspace…</span>
  </div>
  <div v-else-if="error" class="view-state error-state" role="alert">
    <NIcon name="AlertCircle" :size="28" />
    <h3>We couldn’t load this view</h3>
    <p>{{ error }}</p>
    <button class="btn" @click="$emit('retry')"><NIcon name="RefreshCw" />Try again</button>
  </div>
  <div v-else-if="empty" class="view-state">
    <div class="empty-icon"><NIcon name="Inbox" :size="28" /></div>
    <h3>{{ title || 'Nothing here yet' }}</h3>
    <p>{{ description || 'Your workspace is ready when you are.' }}</p>
  </div>
</template>
