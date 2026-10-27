<script setup lang="ts">
import { AlertCircle, Inbox, RefreshCw } from '@lucide/vue'
defineProps<{ loading?: boolean; error?: string; empty?: boolean; title?: string; description?: string }>()
defineEmits<{ retry: [] }>()
</script>
<template>
  <div v-if="loading" class="flex flex-col gap-5 p-6" role="status" aria-label="Loading workspace">
    <div v-for="row in 4" :key="row" class="flex items-center gap-4">
      <UiSkeleton class="size-9 shrink-0 rounded-lg" />
      <div class="flex w-full flex-col gap-2">
        <UiSkeleton class="h-3 w-2/3" /><UiSkeleton class="h-3 w-1/3" />
      </div>
      <UiSkeleton class="h-5 w-16 shrink-0" />
    </div>
    <span class="sr-only">Loading your workspace…</span>
  </div>
  <UiAlert v-else-if="error" variant="destructive" class="my-4" role="alert">
    <AlertCircle /><UiAlertTitle>Unable to load this view</UiAlertTitle>
    <UiAlertDescription
      >{{ error
      }}<UiButton variant="outline" size="sm" class="mt-3 w-fit" @click="$emit('retry')"
        ><RefreshCw data-icon="inline-start" />Try again</UiButton
      ></UiAlertDescription
    >
  </UiAlert>
  <UiEmpty v-else-if="empty" class="py-14">
    <UiEmptyHeader
      ><UiEmptyMedia variant="icon"><Inbox /></UiEmptyMedia
      ><UiEmptyTitle>{{ title || 'Nothing here yet' }}</UiEmptyTitle
      ><UiEmptyDescription>{{
        description || 'Your workspace is ready when you are.'
      }}</UiEmptyDescription></UiEmptyHeader
    >
    <UiEmptyContent v-if="$slots.default"><slot /></UiEmptyContent>
  </UiEmpty>
</template>
