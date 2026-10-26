<script setup lang="ts">
import type { Knowledge, Page } from '~/types'
const route = useRoute()
const tid = String(route.params.tenant_id)
const api = useApi()
const auth = useAuth()
const { success } = useFeedback()
const items = ref<Knowledge[]>([])
const cursor = ref<string | null>(null)
const q = ref('')
const loading = ref(true)
const error = ref('')
const saveError = ref('')
const show = ref(false)
const selected = ref<Knowledge | null>(null)
const saving = ref(false)
const form = reactive({
  title: '',
  content: '',
  document_type: 'general_reference' as Knowledge['document_type'],
  is_active: true,
})
const admin = computed(() => auth.selected.value?.role === 'admin')
const load = async (more = false) => {
  loading.value = true
  error.value = ''
  try {
    const page = await api<Page<Knowledge>>(`/tenants/${tid}/knowledge`, {
      query: { q: q.value || undefined, cursor: more ? cursor.value || undefined : undefined },
    })
    items.value = more ? [...items.value, ...page.items] : page.items
    cursor.value = page.next_cursor
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
const open = (doc: Knowledge | null) => {
  selected.value = doc
  Object.assign(
    form,
    doc
      ? { title: doc.title, content: doc.content, document_type: doc.document_type, is_active: doc.is_active }
      : { title: '', content: '', document_type: 'general_reference', is_active: true },
  )
  saveError.value = ''
  show.value = true
}
const save = async () => {
  if (saving.value) return
  saving.value = true
  saveError.value = ''
  try {
    await api(`/tenants/${tid}/knowledge${selected.value ? `/${selected.value.id}` : ''}`, {
      method: selected.value ? 'PATCH' : 'POST',
      body: form,
    })
    show.value = false
    success('Knowledge document saved.')
    await load()
  } catch (e) {
    saveError.value = (e as Error).message
  } finally {
    saving.value = false
  }
}
onMounted(async () => {
  await load()
  if (route.query.document) {
    try {
      open(
        await api<Knowledge>(`/tenants/${tid}/knowledge/${encodeURIComponent(String(route.query.document))}`),
      )
    } catch (e) {
      error.value = (e as Error).message
    }
  }
})
</script>
<template>
  <div>
    <AppHeader
      eyebrow="YOUR ORGANIZATION’S CONTEXT"
      title="Knowledge that makes answers better."
      description="A shared source of truth for your team and your AI."
      ><button v-if="admin" class="btn btn-primary" @click="open(null)">
        <NIcon name="Plus" />New document
      </button></AppHeader
    >
    <div class="knowledge-banner">
      <span class="knowledge-banner-icon"><NIcon name="BookOpen" :size="25" /></span>
      <div>
        <strong>Good answers start with good context.</strong>
        <p>
          Active documents are available to AI analysis within this workspace. Archive outdated material to
          keep suggestions relevant.
        </p>
      </div>
      <span class="engine-pill"><NIcon name="ShieldCheck" :size="14" />Tenant-scoped retrieval</span>
    </div>
    <div class="section-toolbar">
      <h2>Knowledge library</h2>
      <form class="search-field" @submit.prevent="load()">
        <NIcon name="Search" :size="17" /><input
          v-model="q"
          aria-label="Search knowledge"
          placeholder="Search documents…"
          maxlength="200"
          type="search"
        /><button class="icon-btn" aria-label="Search knowledge library">
          <NIcon name="ArrowRight" :size="16" />
        </button>
      </form>
    </div>
    <ViewState
      :loading="loading && !items.length"
      :error="error"
      :empty="!loading && !items.length"
      title="Build your team’s knowledge."
      description="Add a policy, FAQ, or product guide to give AI useful context."
      @retry="load()"
    />
    <div v-if="!error" class="knowledge-grid">
      <button v-for="doc in items" :key="doc.id" class="knowledge-card" @click="open(doc)">
        <div>
          <span class="doc-icon"><NIcon name="FileText" :size="23" /></span
          ><StatusBadge :value="doc.is_active ? 'active' : 'archived'" />
        </div>
        <span class="eyebrow">{{ doc.document_type.replaceAll('_', ' ') }}</span>
        <h3>{{ doc.title }}</h3>
        <p>{{ doc.content.slice(0, 150) }}{{ doc.content.length > 150 ? '…' : '' }}</p>
        <footer>
          <span
            >Updated
            {{
              new Date(doc.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
            }}</span
          ><NIcon name="ArrowUpRight" :size="17" />
        </footer>
      </button>
    </div>
    <button v-if="cursor" class="btn load-more" :disabled="loading" @click="load(true)">
      {{ loading ? 'Loading…' : 'Load more documents' }}</button
    ><AppModal
      v-model:open="show"
      :title="selected ? (admin ? 'Edit knowledge document' : selected.title) : 'New knowledge document'"
      wide
      ><form v-if="admin" class="stack-form" @submit.prevent="save">
        <label for="doc-title">Title</label
        ><input id="doc-title" v-model="form.title" minlength="3" maxlength="200" required /><label
          for="doc-type"
          >Document type</label
        ><select id="doc-type" v-model="form.document_type">
          <option value="faq">FAQ</option>
          <option value="policy">Policy</option>
          <option value="product_information">Product information</option>
          <option value="general_reference">General reference</option></select
        ><label for="doc-content">Content</label
        ><textarea
          id="doc-content"
          v-model="form.content"
          rows="13"
          minlength="10"
          maxlength="50000"
          required
        /><label class="checkbox-label"
          ><input v-model="form.is_active" type="checkbox" />Active · available to AI retrieval</label
        >
        <p class="muted">Uncheck to archive this document. Previous analyses keep their references.</p>
        <p v-if="saveError" class="form-error" role="alert">{{ saveError }}</p>
        <div class="form-actions">
          <button type="button" class="btn" @click="show = false">Cancel</button
          ><button class="btn btn-primary" :disabled="saving">
            {{ saving ? 'Saving…' : 'Save document' }}
          </button>
        </div>
      </form>
      <div v-else-if="selected" class="document-reader">
        <StatusBadge :value="selected.is_active ? 'active' : 'archived'" />
        <p>{{ selected.content }}</p>
      </div></AppModal
    >
  </div>
</template>
