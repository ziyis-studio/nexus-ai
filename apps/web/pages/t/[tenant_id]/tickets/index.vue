<script setup lang="ts">
import { ArrowLeft, ArrowRight, BookOpen, Inbox, Plus, RefreshCw, Search, X } from '@lucide/vue'
import { useDebounceFn } from '@vueuse/core'
import type { Page, Ticket } from '~/types'
const tid = String(useRoute().params.tenant_id)
const api = useApi()
const auth = useAuth()
const { success } = useFeedback()
const items = ref<Ticket[]>([])
const cursor = ref<string | null>(null)
const currentCursor = ref<string | undefined>()
const previousCursors = ref<(string | undefined)[]>([])
const loading = ref(true)
const error = ref('')
const q = ref('')
const status = ref('all')
const priority = ref('')
const showCreate = ref(false)
const saving = ref(false)
const saveError = ref('')
const customerDetails = ref(false)
const form = reactive({
  subject: '',
  description: '',
  customer_name: '',
  customer_email: '',
  external_reference: '',
})
const statuses = [
  { value: 'all', label: 'All tickets' },
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
]
const hasFilters = computed(() => !!q.value || status.value !== 'all' || !!priority.value)
let controller: AbortController | null = null
let version = 0
let disposed = false
const load = async (next?: string) => {
  if (disposed) return
  const request = ++version
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  error.value = ''
  currentCursor.value = next
  try {
    const result = await api<Page<Ticket>>('/tenants/' + tid + '/tickets', {
      query: {
        q: q.value || undefined,
        status: status.value === 'all' ? undefined : status.value,
        priority: priority.value || undefined,
        cursor: next,
      },
      signal: controller.signal,
    })
    if (request !== version || disposed) return
    items.value = result.items
    cursor.value = result.next_cursor
  } catch (e) {
    if (request === version && !disposed) error.value = (e as Error).message
  } finally {
    if (request === version && !disposed) loading.value = false
  }
}
const filter = () => {
  previousCursors.value = []
  void load()
}
watch(q, useDebounceFn(filter, 300))
watch([status, priority], filter)
const clearFilters = () => {
  q.value = ''
  status.value = 'all'
  priority.value = ''
}
const openCreate = () => {
  saveError.value = ''
  showCreate.value = true
}
const nextPage = () => {
  if (cursor.value) {
    previousCursors.value.push(currentCursor.value)
    void load(cursor.value)
  }
}
const previousPage = () => {
  if (previousCursors.value.length) void load(previousCursors.value.pop())
}
const create = async () => {
  if (saving.value) return
  saving.value = true
  saveError.value = ''
  try {
    const ticket = await api<Ticket>('/tenants/' + tid + '/tickets', {
      method: 'POST',
      body: {
        ...form,
        customer_name: form.customer_name || null,
        customer_email: form.customer_email || null,
        external_reference: form.external_reference || null,
      },
    })
    showCreate.value = false
    success('Ticket created.')
    await navigateTo('/t/' + tid + '/tickets/' + ticket.id)
  } catch (e) {
    saveError.value = (e as Error).message
  } finally {
    saving.value = false
  }
}
const date = (value: string) =>
  new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
onMounted(() => load())
onBeforeUnmount(() => {
  disposed = true
  version++
  controller?.abort()
})
</script>
<template>
  <div class="flex flex-col gap-0">
    <AppHeader title="Tickets" description="Your customer conversations. One focused queue.">
      <UiButton v-if="auth.selected.value?.role !== 'viewer'" @click="openCreate"
        ><Plus data-icon="inline-start" />Create ticket</UiButton
      >
    </AppHeader>
    <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
      <div class="max-w-full overflow-x-auto">
        <UiToggleGroup
          type="single"
          :model-value="status"
          :spacing="1"
          aria-label="Filter by status"
          @update:model-value="status = String($event || 'all')"
          ><UiToggleGroupItem
            v-for="option in statuses"
            :key="option.value"
            :value="option.value"
            class="shrink-0"
            >{{ option.label }}</UiToggleGroupItem
          ></UiToggleGroup
        >
      </div>
      <span class="text-xs text-muted-foreground">Newest first</span>
    </div>
    <UiCard class="gap-0 py-0">
      <UiCardHeader class="gap-0 p-0"
        ><UiCardTitle class="sr-only"><h2>Ticket queue</h2></UiCardTitle
        ><UiCardDescription class="sr-only"
          >Search, filter, and open your workspace conversations.</UiCardDescription
        >
        <div class="surface-toolbar">
          <form class="min-w-0 flex-1 basis-full sm:basis-auto sm:max-w-sm" @submit.prevent="filter">
            <UiInputGroup
              ><UiInputGroupAddon><Search /></UiInputGroupAddon
              ><UiInputGroupInput
                v-model="q"
                aria-label="Search tickets"
                placeholder="Search tickets…"
                type="search"
                maxlength="200" /><UiInputGroupAddon v-if="q" align="inline-end"
                ><UiInputGroupButton
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  aria-label="Clear search"
                  @click="q = ''"
                  ><X /></UiInputGroupButton></UiInputGroupAddon
            ></UiInputGroup>
          </form>
          <div class="flex items-center gap-2">
            <UiNativeSelect v-model="priority" aria-label="Filter by priority"
              ><option value="">All priorities</option>
              <option value="urgent">Urgent</option>
              <option value="high">High</option>
              <option value="normal">Normal</option>
              <option value="low">Low</option></UiNativeSelect
            >
            <UiTooltip
              ><UiTooltipTrigger as-child
                ><UiButton
                  variant="outline"
                  size="icon"
                  :disabled="loading"
                  aria-label="Refresh tickets"
                  @click="load(currentCursor)"
                  ><RefreshCw /></UiButton></UiTooltipTrigger
              ><UiTooltipContent>Refresh tickets</UiTooltipContent></UiTooltip
            >
          </div>
        </div>
      </UiCardHeader>
      <UiSeparator />
      <UiCardContent class="p-0">
        <ViewState
          :loading="loading"
          :error="error"
          :empty="!items.length"
          :title="hasFilters ? 'No matching tickets' : 'Your queue starts here'"
          :description="
            hasFilters
              ? 'Try a different search or clear your filters.'
              : 'Create a ticket to bring a customer conversation into your workspace.'
          "
          @retry="load(currentCursor)"
        >
          <UiButton v-if="hasFilters" variant="outline" @click="clearFilters">Clear filters</UiButton>
          <UiButton v-else-if="auth.selected.value?.role !== 'viewer'" @click="showCreate = true"
            ><Plus data-icon="inline-start" />Create ticket</UiButton
          >
        </ViewState>
        <UiTable v-if="!loading && !error && items.length" class="table-fixed">
          <UiTableHeader
            ><UiTableRow
              ><UiTableHead class="w-[66%] pl-5 sm:w-[55%] lg:w-[44%]">Conversation</UiTableHead
              ><UiTableHead class="w-[34%] sm:w-[20%] lg:w-[14%]">Status</UiTableHead
              ><UiTableHead class="hidden w-[25%] sm:table-cell md:w-[15%] lg:w-[12%]">Priority</UiTableHead
              ><UiTableHead class="hidden w-[20%] lg:table-cell">Customer</UiTableHead
              ><UiTableHead class="hidden w-[10%] pr-5 text-right md:table-cell"
                >Created</UiTableHead
              ></UiTableRow
            ></UiTableHeader
          >
          <UiTableBody
            ><UiTableRow v-for="ticket in items" :key="ticket.id">
              <UiTableCell class="min-w-0 pl-5">
                <NuxtLink :to="'/t/' + tid + '/tickets/' + ticket.id" class="table-subject">
                  <UiAvatar class="hidden size-8 shrink-0 rounded-lg sm:flex"
                    ><UiAvatarFallback class="rounded-lg"><Inbox class="size-4" /></UiAvatarFallback
                  ></UiAvatar>
                  <span class="table-subject-copy"
                    ><strong class="truncate">{{ ticket.subject }}</strong
                    ><small class="truncate"
                      >#{{ ticket.id.slice(0, 8) }} · {{ ticket.description.slice(0, 75) }}</small
                    ><small class="capitalize sm:hidden">{{ ticket.priority }} priority</small></span
                  >
                </NuxtLink>
              </UiTableCell>
              <UiTableCell><StatusBadge :value="ticket.status" /></UiTableCell
              ><UiTableCell class="hidden sm:table-cell"
                ><StatusBadge :value="ticket.priority"
              /></UiTableCell>
              <UiTableCell class="hidden lg:table-cell"
                ><span class="flex items-center gap-2"
                  ><UiAvatar class="size-6"
                    ><UiAvatarFallback>{{
                      (ticket.customer_name || ticket.customer_email || '?').slice(0, 1).toUpperCase()
                    }}</UiAvatarFallback></UiAvatar
                  ><span class="max-w-36 truncate">{{
                    ticket.customer_name || ticket.customer_email || 'Not specified'
                  }}</span></span
                ></UiTableCell
              >
              <UiTableCell
                class="hidden whitespace-nowrap pr-5 text-right text-muted-foreground md:table-cell"
                >{{ date(ticket.created_at) }}</UiTableCell
              >
            </UiTableRow></UiTableBody
          >
        </UiTable>
      </UiCardContent>
      <UiCardFooter class="p-0"
        ><div class="table-bottom w-full">
          <span>{{
            loading
              ? 'Loading tickets…'
              : items.length + (items.length === 1 ? ' ticket' : ' tickets') + ' on this page'
          }}</span>
          <div class="flex items-center gap-2">
            <UiButton
              variant="outline"
              size="sm"
              :disabled="!previousCursors.length || loading"
              @click="previousPage"
              ><ArrowLeft data-icon="inline-start" />Previous</UiButton
            ><UiButton variant="outline" size="sm" :disabled="!cursor || loading" @click="nextPage"
              >Next<ArrowRight data-icon="inline-end"
            /></UiButton>
          </div></div
      ></UiCardFooter>
    </UiCard>
    <div class="mt-5 flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground">
      <span class="flex items-center gap-2"
        ><BookOpen class="size-4" />Better context makes better drafts.</span
      ><UiButton as-child variant="link" size="sm"
        ><NuxtLink :to="'/t/' + tid + '/knowledge'"
          >Open knowledge base<ArrowRight data-icon="inline-end" /></NuxtLink
      ></UiButton>
    </div>
    <AppModal
      v-model:open="showCreate"
      title="Create a ticket"
      description="Capture the customer’s message. You choose when to run an AI analysis."
      :busy="saving"
      wide
    >
      <form class="flex flex-col gap-6" @submit.prevent="create">
        <UiFieldGroup>
          <UiField
            ><UiFieldLabel for="subject">Subject</UiFieldLabel
            ><UiInput
              id="subject"
              v-model="form.subject"
              required
              minlength="3"
              maxlength="200"
              placeholder="What does the customer need help with?"
              :disabled="saving"
          /></UiField>
          <UiField
            ><div class="flex items-center justify-between">
              <UiFieldLabel for="description">Customer message</UiFieldLabel
              ><span class="text-xs text-muted-foreground"
                >{{ form.description.length.toLocaleString() }} / 10,000</span
              >
            </div>
            <UiTextarea
              id="description"
              v-model="form.description"
              required
              minlength="10"
              maxlength="10000"
              rows="6"
              placeholder="Paste or write the conversation, in English or Chinese…"
              :disabled="saving"
          /></UiField>
          <UiCollapsible v-model:open="customerDetails"
            ><UiCollapsibleTrigger as-child
              ><UiButton type="button" variant="ghost" size="sm"
                ><Plus data-icon="inline-start" />Customer details
                <span class="text-muted-foreground">(optional)</span></UiButton
              ></UiCollapsibleTrigger
            ><UiCollapsibleContent>
              <UiFieldGroup class="mt-5"
                ><UiField
                  ><UiFieldLabel for="customer-name">Customer name</UiFieldLabel
                  ><UiInput
                    id="customer-name"
                    v-model="form.customer_name"
                    maxlength="150"
                    :disabled="saving" /></UiField
                ><UiField
                  ><UiFieldLabel for="customer-email">Customer email</UiFieldLabel
                  ><UiInput
                    id="customer-email"
                    v-model="form.customer_email"
                    type="email"
                    maxlength="254"
                    :disabled="saving" /></UiField
                ><UiField
                  ><UiFieldLabel for="external-ref">External reference</UiFieldLabel
                  ><UiInput
                    id="external-ref"
                    v-model="form.external_reference"
                    maxlength="200"
                    :disabled="saving" /></UiField
              ></UiFieldGroup> </UiCollapsibleContent
          ></UiCollapsible>
        </UiFieldGroup>
        <UiAlert v-if="saveError" variant="destructive" role="alert"
          ><UiAlertTitle>Ticket not created</UiAlertTitle
          ><UiAlertDescription>{{ saveError }}</UiAlertDescription></UiAlert
        >
        <UiDialogFooter
          ><UiButton type="button" variant="outline" :disabled="saving" @click="showCreate = false"
            >Cancel</UiButton
          ><UiButton type="submit" :disabled="saving"
            ><UiSpinner v-if="saving" data-icon="inline-start" />{{ saving ? 'Creating…' : 'Create ticket'
            }}<ArrowRight v-if="!saving" data-icon="inline-end" /></UiButton
        ></UiDialogFooter>
      </form>
    </AppModal>
  </div>
</template>
