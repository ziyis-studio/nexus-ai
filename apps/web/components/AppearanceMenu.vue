<script setup lang="ts">
import { Check, Monitor, Moon, Sun } from '@lucide/vue'
import type { Appearance } from '~/composables/useAppearance'
const { appearance, setAppearance } = useAppearance()
const choices: { value: Appearance; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
]
</script>
<template>
  <UiDropdownMenu>
    <UiDropdownMenuTrigger as-child>
      <UiButton variant="ghost" size="icon" aria-label="Change appearance"
        ><Moon v-if="appearance === 'dark'" /><Sun v-else
      /></UiButton>
    </UiDropdownMenuTrigger>
    <UiDropdownMenuContent align="end" class="w-40">
      <UiDropdownMenuGroup
        ><UiDropdownMenuLabel>Appearance</UiDropdownMenuLabel>
        <UiDropdownMenuItem
          v-for="choice in choices"
          :key="choice.value"
          @select="setAppearance(choice.value)"
        >
          <component :is="choice.icon" /><span>{{ choice.label }}</span
          ><Check v-if="appearance === choice.value" class="ml-auto" />
        </UiDropdownMenuItem>
      </UiDropdownMenuGroup>
    </UiDropdownMenuContent>
  </UiDropdownMenu>
</template>
