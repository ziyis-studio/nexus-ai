<script setup lang="ts">
defineProps<{ value: string }>()
</script>
<template>
  <span class="badge" :class="`badge-${value}`"
    ><span class="status-dot" />{{ value.replaceAll('_', ' ') }}</span
  >
</template>
