<script setup lang="ts">
const auth = useAuth()
const email = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')
const submit = async () => {
  if (busy.value) return
  if (!auth.supabase) {
    error.value = 'Authentication is not configured. Follow the deployment guide to connect Supabase.'
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
  <div class="login-frame">
    <div class="login-story">
      <div class="brand">
        <span class="brand-symbol">N</span><span>NEXUS<span class="brand-ai">AI</span></span>
      </div>
      <div class="story-content">
        <div class="eyebrow">THE HUMAN SIDE OF INTELLIGENCE</div>
        <h1>Less noise.<br />More understanding.</h1>
        <p>
          Turn customer conversations into clear next steps. Grounded in your knowledge. Guided by your team.
        </p>
        <div class="story-visual">
          <div class="orbit orbit-one" />
          <div class="orbit orbit-two" />
          <div class="orbit orbit-three" />
          <span class="orbit-core"><NIcon name="Sparkles" :size="36" /></span>
          <div class="orbit-label label-one"><NIcon name="Inbox" />Customer context</div>
          <div class="orbit-label label-two"><NIcon name="BookOpen" />Your knowledge</div>
          <div class="orbit-label label-three"><NIcon name="ShieldCheck" />Human judgment</div>
        </div>
      </div>
      <span class="login-copyright">NEXUS AI · Ticket intelligence engine</span>
    </div>
    <main class="login-form-area">
      <form class="login-form" @submit.prevent="submit">
        <span class="eyebrow">YOUR WORKSPACE AWAITS</span>
        <h2>Welcome back.</h2>
        <p>Sign in to bring clarity to your customer support.</p>
        <label for="email">Work email</label
        ><input
          id="email"
          v-model="email"
          type="email"
          placeholder="you@company.com"
          autocomplete="username"
          required
          maxlength="254"
        /><label for="password">Password</label
        ><input
          id="password"
          v-model="password"
          type="password"
          placeholder="Enter your password"
          autocomplete="current-password"
          required
        />
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="btn btn-primary login-submit" :disabled="busy">
          <span v-if="busy" class="spinner" />{{ busy ? 'Signing in…' : 'Sign in to workspace'
          }}<NIcon name="ArrowRight" />
        </button>
        <div class="login-security">
          <NIcon name="ShieldCheck" :size="15" />Secure access. Your organization’s data stays yours.
        </div>
        <p class="login-help">Need access? Contact your workspace administrator.</p>
      </form>
    </main>
  </div>
</template>
