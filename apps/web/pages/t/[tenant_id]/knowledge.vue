<script setup lang="ts">
import { ArrowRight, BookOpen, FileText, Plus, Search } from '@lucide/vue'
import { useDebounceFn } from '@vueuse/core'
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
const kinds = [
  { value: 'faq', label: 'FAQ' },
  { value: 'policy', label: 'Policy' },
  { value: 'product_information', label: 'Product information' },
  { value: 'general_reference', label: 'General reference' },
]
const kind = (value: string) => kinds.find((item) => item.value === value)?.label || value
let version = 0
let disposed = false
let controller: AbortController | null = null
const load = async (more = false) => {
  if (disposed) return
  const request = ++version
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  error.value = ''
  try {
    const page = await api<Page<Knowledge>>('/tenants/' + tid + '/knowledge', {
      query: { q: q.value || undefined, cursor: more ? cursor.value || undefined : undefined },
      signal: controller.signal,
    })
    if (request !== version || disposed) return
    items.value = more ? [...items.value, ...page.items] : page.items
    cursor.value = page.next_cursor
  } catch (e) {
    if (request === version && !disposed) error.value = (e as Error).message
  } finally {
    if (request === version && !disposed) loading.value = false
  }
}
watch(
  q,
  useDebounceFn(() => load(), 300),
)
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
    await api('/tenants/' + tid + '/knowledge' + (selected.value ? '/' + selected.value.id : ''), {
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
        await api<Knowledge>(
          '/tenants/' + tid + '/knowledge/' + encodeURIComponent(String(route.query.document)),
        ),
      )
    } catch (e) {
      error.value = (e as Error).message
    }
  }
})
onBeforeUnmount(() => {
  disposed = true
  version++
  controller?.abort()
})
</script>
<template>
  <div>
    <AppHeader title="Knowledge base" description="The policies and context behind better customer responses."
      ><UiButton v-if="admin" @click="open(null)"
        ><Plus data-icon="inline-start" />New document</UiButton
      ></AppHeader
    >
    <UiAlert class="mb-6"
      ><BookOpen /><UiAlertTitle>Give every draft a reliable foundation.</UiAlertTitle
      ><UiAlertDescription
        >Active documents are available to AI in this workspace. Archive outdated material to keep future
        drafts relevant.</UiAlertDescription
      ></UiAlert
    >
    <div class="mb-5 flex flex-wrap items-center justify-between gap-4">
      <h2 class="text-sm font-medium">
        All documents<span class="ml-2 text-muted-foreground">{{ items.length }} loaded</span>
      </h2>
      <form class="w-full sm:max-w-xs" @submit.prevent="load()">
        <UiInputGroup
          ><UiInputGroupAddon><Search /></UiInputGroupAddon
          ><UiInputGroupInput
            v-model="q"
            aria-label="Search knowledge"
            placeholder="Search document titles…"
            type="search"
            maxlength="200"
        /></UiInputGroup>
      </form>
    </div>
    <ViewState
      :loading="loading && !items.length"
      :error="error"
      :empty="!loading && !items.length"
      :title="q ? 'No matching documents' : 'Build your knowledge base'"
      :description="
        q
          ? 'Try another title or clear your search.'
          : 'Add a policy, FAQ, or product guide to give your team and AI useful context.'
      "
      @retry="load()"
      ><UiButton v-if="q" variant="outline" @click="q = ''">Clear search</UiButton
      ><UiButton v-else-if="admin" @click="open(null)"
        ><Plus data-icon="inline-start" />New document</UiButton
      ></ViewState
    >
    <div v-if="!error" class="document-grid">
      <UiCard v-for="doc in items" :key="doc.id">
        <UiCardHeader class="gap-4"
          ><div class="flex items-center justify-between gap-3">
            <UiAvatar class="size-10 rounded-lg"
              ><UiAvatarFallback class="rounded-lg"><FileText class="size-5" /></UiAvatarFallback></UiAvatar
            ><StatusBadge :value="doc.is_active ? 'active' : 'archived'" />
          </div>
          <div class="flex flex-col gap-2">
            <UiCardDescription>{{ kind(doc.document_type) }}</UiCardDescription
            ><UiCardTitle
              ><h2 class="line-clamp-2">{{ doc.title }}</h2></UiCardTitle
            >
          </div></UiCardHeader
        >
        <UiCardContent class="flex-1"
          ><p class="line-clamp-3 text-sm leading-7 text-muted-foreground">
            {{ doc.content }}
          </p></UiCardContent
        >
        <UiCardFooter class="justify-between gap-3"
          ><span class="text-xs text-muted-foreground"
            >Updated
            {{
              new Date(doc.updated_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
            }}</span
          ><UiButton
            variant="ghost"
            size="sm"
            :aria-label="(admin ? 'Edit ' : 'Open ') + doc.title"
            @click="open(doc)"
            >{{ admin ? 'Edit' : 'Open' }}<ArrowRight data-icon="inline-end" /></UiButton
        ></UiCardFooter>
      </UiCard>
    </div>
    <div v-if="cursor && !error" class="mt-6 flex justify-center">
      <UiButton variant="outline" :disabled="loading" @click="load(true)"
        ><UiSpinner v-if="loading" data-icon="inline-start" />{{
          loading ? 'Loading…' : 'Load more documents'
        }}</UiButton
      >
    </div>
    <AppModal
      v-model:open="show"
      :title="selected ? (admin ? 'Edit knowledge document' : selected.title) : 'New knowledge document'"
      :description="
        admin
          ? 'Keep guidance clear and current. Changes apply to future AI analyses.'
          : selected
            ? kind(selected.document_type)
            : undefined
      "
      :busy="saving"
      wide
    >
      <form v-if="admin" class="flex flex-col gap-6" @submit.prevent="save">
        <UiFieldGroup>
          <UiField
            ><UiFieldLabel for="doc-title">Title</UiFieldLabel
            ><UiInput
              id="doc-title"
              v-model="form.title"
              minlength="3"
              maxlength="200"
              required
              :disabled="saving"
              placeholder="e.g. Delivery support procedure"
          /></UiField>
          <UiField
            ><UiFieldLabel for="doc-type">Document type</UiFieldLabel
            ><UiNativeSelect id="doc-type" v-model="form.document_type" class="w-full" :disabled="saving"
              ><option v-for="item in kinds" :key="item.value" :value="item.value">
                {{ item.label }}
              </option></UiNativeSelect
            ></UiField
          >
          <UiField
            ><div class="flex items-center justify-between">
              <UiFieldLabel for="doc-content">Content</UiFieldLabel
              ><span class="text-xs text-muted-foreground"
                >{{ form.content.length.toLocaleString() }} / 50,000</span
              >
            </div>
            <UiTextarea
              id="doc-content"
              v-model="form.content"
              rows="10"
              minlength="10"
              maxlength="50000"
              required
              :disabled="saving"
              placeholder="Write the guidance your team should reference…"
          /></UiField>
          <UiField orientation="horizontal"
            ><UiCheckbox
              id="doc-active"
              :model-value="form.is_active"
              :disabled="saving"
              @update:model-value="form.is_active = $event === true"
            /><UiFieldContent
              ><UiFieldLabel for="doc-active">Active · available to AI retrieval</UiFieldLabel
              ><UiFieldDescription
                >Uncheck to archive. Previous analyses keep their references.</UiFieldDescription
              ></UiFieldContent
            ></UiField
          >
        </UiFieldGroup>
        <UiAlert v-if="saveError" variant="destructive" role="alert"
          ><UiAlertTitle>Document not saved</UiAlertTitle
          ><UiAlertDescription>{{ saveError }}</UiAlertDescription></UiAlert
        >
        <UiDialogFooter
          ><UiButton type="button" variant="outline" :disabled="saving" @click="show = false">Cancel</UiButton
          ><UiButton type="submit" :disabled="saving"
            ><UiSpinner v-if="saving" data-icon="inline-start" />{{
              saving ? 'Saving…' : 'Save document'
            }}</UiButton
          ></UiDialogFooter
        >
      </form>
      <article v-else-if="selected" class="flex flex-col gap-5">
        <StatusBadge :value="selected.is_active ? 'active' : 'archived'" /><UiSeparator />
        <p class="message-text">{{ selected.content }}</p>
      </article>
    </AppModal>
  </div>
</template>
