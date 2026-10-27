<script setup lang="ts">
import { cn } from '~/lib/utils'
const props = defineProps<{
  open: boolean
  title: string
  description?: string
  wide?: boolean
  busy?: boolean
}>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()
let opener: HTMLElement | null = null
watch(
  () => props.open,
  (open) => {
    if (open) opener = document.activeElement as HTMLElement | null
  },
)
const update = (open: boolean) => {
  if (!props.busy) emit('update:open', open)
}
const restoreFocus = (event: Event) => {
  if (opener?.isConnected) {
    event.preventDefault()
    opener.focus()
  }
}
</script>
<template>
  <UiDialog :open="open" @update:open="update">
    <UiDialogContent
      :class="cn('max-h-[90svh] overflow-y-auto p-6', wide ? 'sm:max-w-3xl' : 'sm:max-w-xl')"
      :show-close-button="!busy"
      @close-auto-focus="restoreFocus"
      @escape-key-down="busy && $event.preventDefault()"
      @interact-outside="busy && $event.preventDefault()"
    >
      <UiDialogHeader>
        <UiDialogTitle>{{ title }}</UiDialogTitle>
        <UiDialogDescription :class="cn(!description && 'sr-only')">{{
          description || title
        }}</UiDialogDescription>
      </UiDialogHeader>
      <slot />
    </UiDialogContent>
  </UiDialog>
</template>
