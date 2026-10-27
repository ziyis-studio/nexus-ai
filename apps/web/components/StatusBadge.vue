<script setup lang="ts">
import { Check, Circle, CircleCheck, CircleDashed, CircleDot, Clock3, X } from '@lucide/vue'
import type { BadgeVariants } from '~/components/ui/badge'
const props = defineProps<{ value: string }>()
const definition = computed(() => {
  const known: Record<string, { label: string; variant: BadgeVariants['variant']; icon?: typeof Circle }> = {
    open: { label: 'Open', variant: 'info', icon: Circle },
    in_progress: { label: 'In progress', variant: 'warning', icon: CircleDot },
    resolved: { label: 'Resolved', variant: 'success', icon: CircleCheck },
    closed: { label: 'Closed', variant: 'secondary', icon: Check },
    queued: { label: 'Queued', variant: 'secondary', icon: Clock3 },
    processing: { label: 'Processing', variant: 'info', icon: CircleDashed },
    succeeded: { label: 'Succeeded', variant: 'success', icon: Check },
    failed: { label: 'Failed', variant: 'destructive', icon: X },
    approved: { label: 'Approved', variant: 'success', icon: Check },
    rejected: { label: 'Rejected', variant: 'destructive', icon: X },
    pending: { label: 'Needs review', variant: 'warning', icon: Clock3 },
    active: { label: 'Active', variant: 'success' },
    archived: { label: 'Archived', variant: 'outline' },
    inactive: { label: 'Inactive', variant: 'outline' },
    urgent: { label: 'Urgent', variant: 'destructive' },
    high: { label: 'High', variant: 'warning' },
    normal: { label: 'Normal', variant: 'outline' },
    low: { label: 'Low', variant: 'secondary' },
  }
  return known[props.value] || { label: props.value.replaceAll('_', ' '), variant: 'outline' as const }
})
</script>
<template>
  <UiBadge :variant="definition.variant"
    ><component :is="definition.icon" v-if="definition.icon" data-icon="inline-start" />{{
      definition.label
    }}</UiBadge
  >
</template>
