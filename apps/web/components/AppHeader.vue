<script setup lang="ts">
defineProps<{ eyebrow: string; title: string; description?: string }>()
</script>
<template>
  <div class="page-heading">
    <div>
      <div class="eyebrow">{{ eyebrow }}</div>
      <h1>{{ title }}</h1>
      <p v-if="description" class="page-description">{{ description }}</p>
    </div>
    <div class="heading-actions"><slot /></div>
  </div>
</template>
