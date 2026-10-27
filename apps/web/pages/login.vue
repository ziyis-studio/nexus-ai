<script setup lang="ts">
import { ArrowRight, BookOpen, Eye, EyeOff, Inbox, ShieldCheck, Sparkles } from '@lucide/vue'
const auth = useAuth()
const email = ref('')
const password = ref('')
const passwordVisible = ref(false)
const busy = ref(false)
const error = ref('')
const submit = async () => {
  if (busy.value) return
  if (!auth.supabase) {
    error.value = 'Sign-in is temporarily unavailable. Contact your workspace administrator.'
    return
  }
  busy.value = true
  error.value = ''
  try {
    const result = await auth.supabase.auth.signInWithPassword({
      email: email.value,
      password: password.value,
    })
    if (result.error) {
      error.value = 'Unable to sign in. Check your email and password.'
      return
    }
    auth.session.value = result.data.session
    await navigateTo('/workspaces')
  } catch {
    error.value = 'Unable to connect. Check your network and try again.'
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <div class="login-page">
    <aside class="login-intro">
      <div class="brand-link"><BrandMark class="size-8 text-sidebar-primary" /><span>Nexus /</span></div>
      <div class="login-narrative">
        <h1>Good support.<br />Clearer decisions.</h1>
        <p>Bring customer context, your team’s knowledge, and AI into one focused workspace.</p>
        <div class="login-diagram" aria-label="Your support workflow">
          <div class="login-step">
            <Inbox class="size-5 shrink-0" /><span
              ><strong>Start with the conversation</strong
              ><small>Keep the customer’s needs in focus.</small></span
            >
          </div>
          <div class="login-step">
            <BookOpen class="size-5 shrink-0" /><span
              ><strong>Add the right context</strong
              ><small>Ground every draft in your knowledge.</small></span
            >
          </div>
          <div class="login-step">
            <Sparkles class="size-5 shrink-0" /><span
              ><strong>Make the final call</strong
              ><small>Review, approve, and respond with confidence.</small></span
            >
          </div>
        </div>
      </div>
      <footer class="sidebar-caption">Nexus · Support intelligence, with a human perspective.</footer>
    </aside>
    <main class="login-form-section">
      <div class="absolute right-5 top-5"><AppearanceMenu /></div>
      <form class="login-form" :aria-busy="busy" @submit.prevent="submit">
        <div>
          <h1>Welcome back.</h1>
          <p class="page-description">Sign in to your team’s workspace.</p>
        </div>
        <UiFieldGroup>
          <UiField :data-invalid="!!error || undefined"
            ><UiFieldLabel for="email">Work email</UiFieldLabel
            ><UiInput
              id="email"
              v-model="email"
              type="email"
              placeholder="you@company.com"
              autocomplete="username"
              required
              maxlength="254"
              :aria-invalid="!!error"
              :disabled="busy"
          /></UiField>
          <UiField :data-invalid="!!error || undefined"
            ><UiFieldLabel for="password">Password</UiFieldLabel>
            <UiInputGroup
              ><UiInputGroupInput
                id="password"
                v-model="password"
                :type="passwordVisible ? 'text' : 'password'"
                placeholder="Enter your password"
                autocomplete="current-password"
                required
                :aria-invalid="!!error"
                :disabled="busy" /><UiInputGroupAddon align="inline-end"
                ><UiInputGroupButton
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  :aria-label="passwordVisible ? 'Hide password' : 'Show password'"
                  @click="passwordVisible = !passwordVisible"
                  ><EyeOff v-if="passwordVisible" /><Eye v-else /></UiInputGroupButton></UiInputGroupAddon
            ></UiInputGroup>
          </UiField>
        </UiFieldGroup>
        <UiAlert v-if="error" variant="destructive" role="alert"
          ><UiAlertTitle>Sign-in unsuccessful</UiAlertTitle
          ><UiAlertDescription>{{ error }}</UiAlertDescription></UiAlert
        >
        <UiButton type="submit" size="lg" class="w-full" :disabled="busy"
          ><UiSpinner v-if="busy" data-icon="inline-start" />{{ busy ? 'Signing in…' : 'Sign in to workspace'
          }}<ArrowRight v-if="!busy" data-icon="inline-end"
        /></UiButton>
        <UiSeparator />
        <div class="flex flex-col gap-3 text-center text-xs text-muted-foreground">
          <p class="flex items-center justify-center gap-2">
            <ShieldCheck class="size-4" />Private access to your organization.
          </p>
          <p>Need an account? Contact your workspace administrator.</p>
        </div>
      </form>
    </main>
  </div>
</template>
