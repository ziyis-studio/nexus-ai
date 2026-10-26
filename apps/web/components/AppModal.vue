<script setup lang="ts">
const props = defineProps<{ open: boolean; title: string; wide?: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()
const dialog = ref<HTMLDialogElement | null>(null)
watch(
  () => props.open,
  async (value) => {
    await nextTick()
    if (value && !dialog.value?.open) dialog.value?.showModal()
    else if (!value) dialog.value?.close()
  },
  { immediate: true },
)
onMounted(() => {
  if (props.open) dialog.value?.showModal()
})
</script>
<template>
  <dialog
    ref="dialog"
    class="modal"
    :class="{ 'modal-wide': wide }"
    @close="emit('update:open', false)"
    @click="
      (event) => {
        if (event.target === dialog) dialog?.close()
      }
    "
  >
    <div class="modal-header">
      <h2>{{ title }}</h2>
      <button class="icon-btn" aria-label="Close dialog" @click="dialog?.close()"><NIcon name="X" /></button>
    </div>
    <slot />
  </dialog>
</template>
