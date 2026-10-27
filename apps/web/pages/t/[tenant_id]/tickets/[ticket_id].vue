<script setup lang="ts">
import {
  Activity,
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  ChevronRight,
  Copy,
  FileText,
  MessageSquare,
  Pencil,
  ShieldCheck,
  Sparkles,
  X,
} from '@lucide/vue'
import type { Ticket, Run, Page, AIResult, Knowledge, TicketStatus, Priority } from '~/types'
const route = useRoute()
const tid = String(route.params.tenant_id)
const ticketId = String(route.params.ticket_id)
const api = useApi()
const auth = useAuth()
const { success } = useFeedback()
const ticket = ref<Ticket | null>(null)
const runs = ref<Run[]>([])
const runCursor = ref<string | null>(null)
const selectedRun = ref<Run | null>(null)
const result = ref<AIResult | null>(null)
const sources = ref<Knowledge[]>([])
const sourceErrors = ref<string[]>([])
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const analyzing = ref(false)
const reviewing = ref(false)
const saving = ref(false)
const editing = ref(false)
const historyBusy = ref(false)
const form = reactive({
  subject: '',
  description: '',
  priority: 'normal' as Priority,
  status: 'open' as TicketStatus,
})
let analysisKey: string | null = null
let selectionVersion = 0
let disposed = false
const canWrite = computed(() => auth.selected.value?.role !== 'viewer')
const active = computed(() => runs.value.some((r) => ['queued', 'processing'].includes(r.status)))
const date = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
const loadResult = async (run: Run) => {
  const version = ++selectionVersion
  selectedRun.value = run
  result.value = null
  sources.value = []
  sourceErrors.value = []
  if (run.status !== 'succeeded') return
  try {
    const value = await api<AIResult>(`/tenants/${tid}/runs/${run.id}/result`)
    if (version !== selectionVersion || disposed) return
    result.value = value
    const documents = await Promise.allSettled(
      value.source_document_ids.map((id) => api<Knowledge>(`/tenants/${tid}/knowledge/${id}`)),
    )
    if (version !== selectionVersion || disposed) return
    sources.value = documents.flatMap((doc) => (doc.status === 'fulfilled' ? [doc.value] : []))
    sourceErrors.value = documents.flatMap((doc, i) =>
      doc.status === 'rejected' ? [value.source_document_ids[i] || 'unavailable'] : [],
    )
  } catch (e) {
    if (version === selectionVersion) actionError.value = (e as Error).message
  }
}
const watcher = useRunWatch(tid, async (run) => {
  const index = runs.value.findIndex((item) => item.id === run.id)
  if (index >= 0) runs.value[index] = run
  if (selectedRun.value?.id === run.id && selectedRun.value.status !== run.status) await loadResult(run)
})
const loadHistory = async () => {
  historyBusy.value = true
  try {
    const page = await api<Page<Run>>(`/tenants/${tid}/runs`, {
      query: { ticket_id: ticketId, cursor: runCursor.value || undefined },
    })
    runs.value.push(...page.items)
    runCursor.value = page.next_cursor
  } catch (e) {
    actionError.value = (e as Error).message
  } finally {
    historyBusy.value = false
  }
}
const load = async () => {
  loading.value = true
  error.value = ''
  try {
    const [data, history] = await Promise.all([
      api<Ticket>(`/tenants/${tid}/tickets/${ticketId}`),
      api<Page<Run>>(`/tenants/${tid}/runs`, { query: { ticket_id: ticketId } }),
    ])
    if (disposed) return
    ticket.value = data
    Object.assign(form, {
      subject: data.subject,
      description: data.description,
      priority: data.priority,
      status: data.status,
    })
    runs.value = history.items
    runCursor.value = history.next_cursor
    const first = history.items[0]
    if (first) {
      await loadResult(first)
      if (['queued', 'processing'].includes(first.status)) watcher.watchRun(first.id)
    }
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
const analyze = async () => {
  if (analyzing.value) return
  analyzing.value = true
  actionError.value = ''
  analysisKey ||= crypto.randomUUID()
  try {
    const accepted = await api<{ run_id: string }>(`/tenants/${tid}/tickets/${ticketId}/analyze`, {
      method: 'POST',
      idempotencyKey: analysisKey,
    })
    const run = await api<Run>(`/tenants/${tid}/runs/${accepted.run_id}`)
    if (!runs.value.some((r) => r.id === run.id)) runs.value.unshift(run)
    analysisKey = null
    await loadResult(run)
    watcher.watchRun(run.id)
    success('Analysis queued. You can stay here as it progresses.')
  } catch (e) {
    actionError.value = (e as Error).message
  } finally {
    analyzing.value = false
  }
}
const review = async (decision: 'approve' | 'reject') => {
  if (!selectedRun.value || reviewing.value) return
  reviewing.value = true
  actionError.value = ''
  try {
    result.value = await api<AIResult>(`/tenants/${tid}/runs/${selectedRun.value.id}/${decision}`, {
      method: 'POST',
    })
    success(
      decision === 'approve'
        ? 'Suggestion approved. No message has been sent.'
        : 'Suggestion rejected. You can start a new analysis.',
    )
  } catch (e) {
    actionError.value = (e as Error).message
  } finally {
    reviewing.value = false
  }
}
const save = async () => {
  if (saving.value) return
  saving.value = true
  actionError.value = ''
  try {
    ticket.value = await api<Ticket>(`/tenants/${tid}/tickets/${ticketId}`, { method: 'PATCH', body: form })
    editing.value = false
    success('Ticket updated.')
  } catch (e) {
    actionError.value = (e as Error).message
  } finally {
    saving.value = false
  }
}
const copy = async () => {
  if (!result.value) return
  try {
    await navigator.clipboard.writeText(result.value.suggested_reply)
    success('Draft copied to clipboard.')
  } catch {
    actionError.value = 'Clipboard is unavailable. Select the draft text to copy it.'
  }
}
const transitions = computed(() => {
  const status = ticket.value?.status || 'open'
  const choices: Record<string, string[]> = {
    open: ['open', 'in_progress', 'resolved'],
    in_progress: ['in_progress', 'resolved'],
    resolved: ['resolved', 'closed', 'open'],
    closed: auth.selected.value?.role === 'admin' ? ['closed', 'open'] : ['closed'],
  }
  return choices[status] || [status]
})
onMounted(load)
onBeforeUnmount(() => {
  disposed = true
  selectionVersion++
})

const resultTab = ref('draft')
const rejectConfirm = ref(false)
const editTicket = () => {
  if (!ticket.value) return
  Object.assign(form, {
    subject: ticket.value.subject,
    description: ticket.value.description,
    priority: ticket.value.priority,
    status: ticket.value.status,
  })
  actionError.value = ''
  editing.value = true
}
const retryResult = () => {
  actionError.value = ''
  if (selectedRun.value) void loadResult(selectedRun.value)
}
const chooseRun = (value: unknown) => {
  const run = runs.value.find((item) => item.id === value)
  if (run) {
    actionError.value = ''
    resultTab.value = 'draft'
    void loadResult(run)
  }
}
</script>
<template>
  <div>
    <UiButton as-child variant="ghost" size="sm" class="mb-5"
      ><NuxtLink :to="'/t/' + tid + '/tickets'"
        ><ArrowLeft data-icon="inline-start" />All tickets</NuxtLink
      ></UiButton
    >
    <ViewState :loading="loading" :error="error" @retry="load" />
    <template v-if="ticket && !loading && !error">
      <AppHeader
        :eyebrow="'Ticket / ' + ticket.id.slice(0, 8)"
        :title="ticket.subject"
        :description="'Created ' + date(ticket.created_at)"
        ><UiButton v-if="canWrite" variant="outline" @click="editTicket"
          ><Pencil data-icon="inline-start" />Edit ticket</UiButton
        ></AppHeader
      >
      <UiAlert v-if="actionError" variant="destructive" class="mb-5" role="alert"
        ><AlertCircle /><UiAlertTitle>We couldn’t complete that action</UiAlertTitle
        ><UiAlertDescription>{{ actionError }}</UiAlertDescription></UiAlert
      >
      <div class="ticket-detail">
        <div class="detail-column">
          <UiCard
            ><UiCardHeader
              ><div class="flex items-center justify-between gap-3">
                <UiCardTitle><h2>Customer message</h2></UiCardTitle
                ><StatusBadge :value="ticket.status" /></div
            ></UiCardHeader>
            <UiCardContent class="flex flex-col gap-6">
              <div class="flex items-center gap-3">
                <UiAvatar class="size-10"
                  ><UiAvatarFallback>{{
                    (ticket.customer_name || ticket.customer_email || '?').slice(0, 2).toUpperCase()
                  }}</UiAvatarFallback></UiAvatar
                >
                <div class="flex min-w-0 flex-col gap-1">
                  <strong class="truncate text-sm font-medium">{{
                    ticket.customer_name || 'Customer'
                  }}</strong
                  ><span class="truncate text-xs text-muted-foreground">{{
                    ticket.customer_email || 'Support request'
                  }}</span>
                </div>
              </div>
              <article class="message-text">{{ ticket.description }}</article> </UiCardContent
            ><UiCardFooter class="justify-between gap-3"
              ><span class="text-xs text-muted-foreground">Last updated {{ date(ticket.updated_at) }}</span
              ><StatusBadge :value="ticket.priority"
            /></UiCardFooter>
          </UiCard>
          <UiCard
            ><UiCardHeader
              ><div class="flex items-center justify-between gap-3">
                <UiCardTitle><h2>Analysis history</h2></UiCardTitle
                ><UiBadge variant="secondary">{{ runs.length }}</UiBadge>
              </div>
              <UiCardDescription>Select a run to review its saved result.</UiCardDescription></UiCardHeader
            >
            <UiCardContent>
              <ViewState
                :empty="!runs.length"
                title="No analyses yet"
                description="Your first analysis will appear here."
              />
              <UiToggleGroup
                v-if="runs.length"
                type="single"
                orientation="vertical"
                :spacing="1"
                :model-value="selectedRun?.id"
                class="w-full"
                aria-label="Select analysis"
                @update:model-value="chooseRun"
              >
                <UiToggleGroupItem
                  v-for="run in runs"
                  :key="run.id"
                  :value="run.id"
                  class="h-auto w-full justify-between gap-3 p-3"
                  ><span class="flex min-w-0 flex-col gap-1 text-left"
                    ><span>{{ date(run.created_at) }}</span
                    ><span class="truncate text-xs text-muted-foreground"
                      >{{ run.model_id === 'fixture' ? 'Demo provider' : run.model_id }} ·
                      {{ run.attempt_count }} attempt{{ run.attempt_count === 1 ? '' : 's' }}</span
                    ></span
                  ><StatusBadge :value="run.status"
                /></UiToggleGroupItem>
              </UiToggleGroup>
              <UiButton
                v-if="runCursor"
                variant="outline"
                class="mt-4 w-full"
                :disabled="historyBusy"
                @click="loadHistory"
                ><UiSpinner v-if="historyBusy" data-icon="inline-start" />{{
                  historyBusy ? 'Loading…' : 'Load older analyses'
                }}</UiButton
              >
            </UiCardContent>
          </UiCard>
        </div>
        <UiCard>
          <UiCardHeader
            ><div class="flex flex-wrap items-center justify-between gap-3">
              <UiCardTitle
                ><h2 class="flex items-center gap-2">
                  <Sparkles class="size-4 text-primary" />AI workspace
                </h2></UiCardTitle
              ><StatusBadge v-if="result" :value="result.review_status" /><StatusBadge
                v-else-if="selectedRun"
                :value="selectedRun.status"
              /><UiBadge v-else variant="outline">Ready to analyze</UiBadge>
            </div>
            <UiCardDescription>{{
              selectedRun?.model_id === 'fixture'
                ? 'Demo analysis · deterministic preview output'
                : 'Grounded in your knowledge. Reviewed by your team.'
            }}</UiCardDescription></UiCardHeader
          >
          <UiCardContent class="flex flex-col gap-6">
            <UiEmpty v-if="!selectedRun" class="py-12"
              ><UiEmptyHeader
                ><UiEmptyMedia variant="icon"><Sparkles /></UiEmptyMedia
                ><UiEmptyTitle>A clearer next reply.</UiEmptyTitle
                ><UiEmptyDescription
                  >Find the intent, urgency, and relevant knowledge behind this conversation. Get a structured
                  analysis and a response draft to review.</UiEmptyDescription
                ></UiEmptyHeader
              ></UiEmpty
            >
            <UiEmpty
              v-else-if="['queued', 'processing'].includes(selectedRun.status)"
              class="py-10"
              role="status"
              ><UiEmptyHeader
                ><UiEmptyMedia variant="icon"><UiSpinner /></UiEmptyMedia
                ><UiEmptyTitle>{{
                  selectedRun.status === 'queued'
                    ? 'Your analysis is queued'
                    : 'Working through the conversation'
                }}</UiEmptyTitle
                ><UiEmptyDescription>{{
                  watcher.stage.value === 'retrieving'
                    ? 'Finding relevant knowledge for this request…'
                    : watcher.stage.value === 'retrying'
                      ? 'The AI provider is temporarily unavailable. Retrying…'
                      : 'Preparing insights and a response draft…'
                }}</UiEmptyDescription></UiEmptyHeader
              ><UiEmptyContent
                ><UiBadge variant="secondary">{{
                  watcher.connection.value === 'connected'
                    ? 'Live updates connected'
                    : 'Checking saved progress'
                }}</UiBadge></UiEmptyContent
              ></UiEmpty
            >
            <UiAlert v-else-if="selectedRun.status === 'failed'" variant="destructive"
              ><AlertCircle /><UiAlertTitle>Analysis couldn’t be completed</UiAlertTitle
              ><UiAlertDescription
                >{{ selectedRun.error_message || 'The analysis could not finish. Your ticket is saved.'
                }}<code v-if="selectedRun.error_code" class="mt-2 block text-xs">{{
                  selectedRun.error_code
                }}</code>
                <p class="mt-2">Start a new analysis to try again.</p></UiAlertDescription
              ></UiAlert
            >
            <ViewState v-else-if="!result && !actionError" loading />
            <UiButton
              v-if="selectedRun?.status === 'succeeded' && !result && actionError"
              variant="outline"
              @click="retryResult"
              >Retry loading result</UiButton
            >
            <template v-if="result">
              <UiTabs v-model="resultTab" class="flex flex-col gap-5">
                <UiTabsList variant="line"
                  ><UiTabsTrigger value="draft"><MessageSquare />Response</UiTabsTrigger
                  ><UiTabsTrigger value="insights"><Activity />Insights</UiTabsTrigger></UiTabsList
                >
                <UiTabsContent value="draft" class="flex flex-col gap-5">
                  <div class="flex flex-col gap-2">
                    <h3 class="text-xs font-medium text-muted-foreground">Summary</h3>
                    <p class="text-sm leading-7">{{ result.summary }}</p>
                  </div>
                  <div class="flex items-center justify-between gap-3">
                    <h3 class="text-sm font-medium">Suggested response</h3>
                    <UiTooltip
                      ><UiTooltipTrigger as-child
                        ><UiButton
                          variant="ghost"
                          size="icon-sm"
                          aria-label="Copy suggested response"
                          @click="copy"
                          ><Copy /></UiButton></UiTooltipTrigger
                      ><UiTooltipContent>Copy draft</UiTooltipContent></UiTooltip
                    >
                  </div>
                  <article class="draft-surface" aria-label="Suggested response draft">
                    {{ result.suggested_reply }}
                  </article>
                  <p class="flex items-center gap-2 text-xs text-muted-foreground">
                    <ShieldCheck class="size-3.5 shrink-0" />AI-generated draft. Check it before use.
                  </p>
                </UiTabsContent>
                <UiTabsContent value="insights" class="flex flex-col gap-5">
                  <dl class="insight-grid">
                    <div>
                      <dt class="text-xs text-muted-foreground">Category</dt>
                      <dd class="m-0 text-sm font-medium capitalize">{{ result.category }}</dd>
                    </div>
                    <div>
                      <dt class="text-xs text-muted-foreground">Suggested priority</dt>
                      <dd class="m-0"><StatusBadge :value="result.suggested_priority" /></dd>
                    </div>
                    <div>
                      <dt class="text-xs text-muted-foreground">Sentiment</dt>
                      <dd class="m-0 text-sm font-medium capitalize">{{ result.sentiment }}</dd>
                    </div>
                  </dl>
                  <div class="flex flex-col gap-2">
                    <h3 class="text-sm font-medium">Decision rationale</h3>
                    <p class="text-sm leading-7 text-muted-foreground">{{ result.reasoning_summary }}</p>
                  </div>
                </UiTabsContent>
              </UiTabs>
              <UiSeparator />
              <section class="flex flex-col gap-3" aria-labelledby="supporting-knowledge">
                <h3 id="supporting-knowledge" class="flex items-center gap-2 text-sm font-medium">
                  <BookOpen class="size-4" />Supporting knowledge<UiBadge variant="secondary">{{
                    sources.length
                  }}</UiBadge>
                </h3>
                <UiButton
                  v-for="source in sources"
                  :key="source.id"
                  as-child
                  variant="outline"
                  class="h-auto w-full justify-between gap-3 p-3"
                  ><NuxtLink :to="'/t/' + tid + '/knowledge?document=' + source.id"
                    ><FileText data-icon="inline-start" /><span
                      class="flex min-w-0 flex-1 flex-col gap-1 text-left"
                      ><span class="truncate">{{ source.title }}</span
                      ><span v-if="!source.is_active" class="text-xs text-muted-foreground"
                        >Archived since this analysis</span
                      ></span
                    ><ArrowRight data-icon="inline-end" /></NuxtLink
                ></UiButton>
                <p
                  v-if="result.source_document_ids.length && !sources.length && !sourceErrors.length"
                  class="text-xs text-muted-foreground"
                  role="status"
                >
                  Loading supporting knowledge…
                </p>
                <UiAlert v-if="!result.source_document_ids.length"
                  ><UiAlertTitle>Verify policy claims before use</UiAlertTitle
                  ><UiAlertDescription
                    >No supporting documents were cited for this response.</UiAlertDescription
                  ></UiAlert
                >
                <UiAlert v-if="sourceErrors.length"
                  ><UiAlertTitle>Some references are unavailable</UiAlertTitle
                  ><UiAlertDescription
                    >Ask an administrator to verify the original documents before using this
                    draft.</UiAlertDescription
                  ></UiAlert
                >
              </section>
              <UiAlert v-if="result.review_status !== 'pending'"
                ><ShieldCheck /><UiAlertTitle>{{
                  result.review_status === 'approved' ? 'Draft approved' : 'Draft rejected'
                }}</UiAlertTitle
                ><UiAlertDescription
                  >{{
                    result.review_status === 'approved'
                      ? 'Approved for use. No message has been sent.'
                      : 'Rejected. Start a new analysis for another suggestion.'
                  }}<span v-if="result.reviewed_at" class="mt-2 block text-xs"
                    >Reviewed {{ date(result.reviewed_at) }}</span
                  ></UiAlertDescription
                ></UiAlert
              >
            </template>
            <UiAlert v-if="!canWrite"
              ><ShieldCheck /><UiAlertTitle>Read-only access</UiAlertTitle
              ><UiAlertDescription
                >You can view analyses. An agent or administrator can run and review
                drafts.</UiAlertDescription
              ></UiAlert
            >
          </UiCardContent>
          <UiCardFooter class="flex-col items-stretch gap-4">
            <template v-if="result?.review_status === 'pending' && canWrite"
              ><div class="flex gap-2">
                <UiButton variant="outline" class="flex-1" :disabled="reviewing" @click="rejectConfirm = true"
                  ><X data-icon="inline-start" />Reject</UiButton
                ><UiButton class="flex-1" :disabled="reviewing" @click="review('approve')"
                  ><UiSpinner v-if="reviewing" data-icon="inline-start" /><Check
                    v-else
                    data-icon="inline-start"
                  />{{ reviewing ? 'Saving…' : 'Approve draft' }}</UiButton
                >
              </div>
              <p class="text-center text-xs text-muted-foreground">
                The decision is final for this draft. No message will be sent.
              </p>
              <UiSeparator
            /></template>
            <UiButton
              v-if="canWrite"
              :variant="result ? 'outline' : 'default'"
              :disabled="analyzing || active"
              class="w-full"
              @click="analyze"
              ><UiSpinner v-if="analyzing || active" data-icon="inline-start" /><Sparkles
                v-else
                data-icon="inline-start" />{{
                analyzing
                  ? 'Submitting…'
                  : active
                    ? 'Analysis in progress…'
                    : selectedRun
                      ? 'Run a new analysis'
                      : 'Analyze with AI'
              }}<ArrowRight v-if="!analyzing && !active" data-icon="inline-end"
            /></UiButton>
          </UiCardFooter>
        </UiCard>
      </div>
      <AppModal
        v-model:open="editing"
        title="Edit ticket"
        description="Update the conversation, priority, or status."
        :busy="saving"
        wide
      >
        <form class="flex flex-col gap-6" @submit.prevent="save">
          <UiFieldGroup>
            <UiField
              ><UiFieldLabel for="edit-subject">Subject</UiFieldLabel
              ><UiInput
                id="edit-subject"
                v-model="form.subject"
                minlength="3"
                maxlength="200"
                required
                :disabled="saving"
            /></UiField>
            <UiField
              ><UiFieldLabel for="edit-description">Message</UiFieldLabel
              ><UiTextarea
                id="edit-description"
                v-model="form.description"
                rows="7"
                minlength="10"
                maxlength="10000"
                required
                :disabled="saving"
            /></UiField>
            <UiFieldGroup class="sm:flex-row"
              ><UiField
                ><UiFieldLabel for="edit-status">Status</UiFieldLabel
                ><UiNativeSelect id="edit-status" v-model="form.status" class="w-full" :disabled="saving"
                  ><option v-for="choice in transitions" :key="choice" :value="choice">
                    {{ choice.replaceAll('_', ' ') }}
                  </option></UiNativeSelect
                ></UiField
              ><UiField
                ><UiFieldLabel for="edit-priority">Priority</UiFieldLabel
                ><UiNativeSelect id="edit-priority" v-model="form.priority" class="w-full" :disabled="saving"
                  ><option v-for="p in ['low', 'normal', 'high', 'urgent']" :key="p" :value="p">
                    {{ p }}
                  </option></UiNativeSelect
                ></UiField
              ></UiFieldGroup
            > </UiFieldGroup
          ><UiAlert v-if="actionError" variant="destructive" role="alert"
            ><UiAlertTitle>Ticket not saved</UiAlertTitle
            ><UiAlertDescription>{{ actionError }}</UiAlertDescription></UiAlert
          ><UiDialogFooter
            ><UiButton type="button" variant="outline" :disabled="saving" @click="editing = false"
              >Cancel</UiButton
            ><UiButton type="submit" :disabled="saving"
              ><UiSpinner v-if="saving" data-icon="inline-start" />{{
                saving ? 'Saving…' : 'Save changes'
              }}</UiButton
            ></UiDialogFooter
          >
        </form>
      </AppModal>
      <UiAlertDialog v-model:open="rejectConfirm"
        ><UiAlertDialogContent
          ><UiAlertDialogHeader
            ><UiAlertDialogTitle>Reject this draft?</UiAlertDialogTitle
            ><UiAlertDialogDescription
              >This decision is final for this analysis. You can start a new analysis to get another
              suggestion.</UiAlertDialogDescription
            ></UiAlertDialogHeader
          ><UiAlertDialogFooter
            ><UiAlertDialogCancel>Keep reviewing</UiAlertDialogCancel
            ><UiAlertDialogAction variant="destructive" @click="review('reject')"
              >Reject draft</UiAlertDialogAction
            ></UiAlertDialogFooter
          ></UiAlertDialogContent
        ></UiAlertDialog
      >
    </template>
  </div>
</template>
