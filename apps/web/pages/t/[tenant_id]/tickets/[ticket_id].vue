<script setup lang="ts">
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
    analysisKey = null
    const run = await api<Run>(`/tenants/${tid}/runs/${accepted.run_id}`)
    if (!runs.value.some((r) => r.id === run.id)) runs.value.unshift(run)
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
</script>
<template>
  <div>
    <NuxtLink :to="`/t/${tid}/tickets`" class="back-link"
      ><NIcon name="ArrowLeft" :size="16" />All tickets</NuxtLink
    ><ViewState :loading="loading" :error="error" @retry="load" /><template
      v-if="ticket && !loading && !error"
      ><AppHeader
        :eyebrow="`TICKET / ${ticket.id.slice(0, 8).toUpperCase()}`"
        :title="ticket.subject"
        :description="`Created ${date(ticket.created_at)} · ${ticket.customer_name || ticket.customer_email || 'Customer not specified'}`"
        ><button v-if="canWrite" class="btn" @click="editing = !editing">
          <NIcon name="Settings" :size="16" />{{ editing ? 'Cancel editing' : 'Edit ticket' }}
        </button></AppHeader
      >
      <p v-if="actionError" class="alert-error" role="alert">{{ actionError }}</p>
      <div class="detail-grid">
        <div class="detail-main">
          <section class="panel conversation-panel">
            <div class="panel-heading">
              <h2><NIcon name="Inbox" />Conversation</h2>
              <StatusBadge :value="ticket.status" />
            </div>
            <form v-if="editing" class="stack-form padded" @submit.prevent="save">
              <label for="edit-subject">Subject</label
              ><input id="edit-subject" v-model="form.subject" minlength="3" maxlength="200" required /><label
                for="edit-description"
                >Message</label
              ><textarea
                id="edit-description"
                v-model="form.description"
                rows="8"
                minlength="10"
                maxlength="10000"
                required
              />
              <div class="form-columns">
                <div>
                  <label for="edit-status">Status</label
                  ><select id="edit-status" v-model="form.status">
                    <option v-for="status in transitions" :key="status" :value="status">
                      {{ status.replaceAll('_', ' ') }}
                    </option>
                  </select>
                </div>
                <div>
                  <label for="edit-priority">Priority</label
                  ><select id="edit-priority" v-model="form.priority">
                    <option v-for="p in ['low', 'normal', 'high', 'urgent']" :key="p">{{ p }}</option>
                  </select>
                </div>
              </div>
              <button class="btn btn-primary" :disabled="saving">
                {{ saving ? 'Saving…' : 'Save changes' }}
              </button>
            </form>
            <div v-else class="conversation-body">
              <div class="message-sender">
                <span class="customer-avatar large">{{ (ticket.customer_name || '?').slice(0, 1) }}</span
                ><span
                  ><strong>{{ ticket.customer_name || 'Customer' }}</strong
                  ><small>{{ ticket.customer_email || 'Support request' }}</small></span
                ><time>{{ date(ticket.created_at) }}</time>
              </div>
              <div class="message-content">{{ ticket.description }}</div>
            </div>
            <div class="ticket-metadata">
              <span>Priority <StatusBadge :value="ticket.priority" /></span
              ><span>Updated {{ date(ticket.updated_at) }}</span>
            </div>
          </section>
          <section class="panel history-panel">
            <div class="panel-heading">
              <h2><NIcon name="Activity" />Analysis history</h2>
              <span class="count-label">{{ runs.length }}</span>
            </div>
            <ViewState
              :empty="!runs.length"
              title="The next step is yours."
              description="Run an analysis to see structured insights and a grounded response draft."
            /><button
              v-for="run in runs"
              :key="run.id"
              class="history-row"
              :class="{ selected: selectedRun?.id === run.id }"
              @click="loadResult(run)"
            >
              <span class="history-icon"><NIcon name="Sparkles" :size="16" /></span
              ><span
                ><strong>{{ date(run.created_at) }}</strong
                ><small
                  >{{ run.model_id }} · {{ run.attempt_count }} attempt{{
                    run.attempt_count !== 1 ? 's' : ''
                  }}</small
                ></span
              ><StatusBadge :value="run.status" /><NIcon name="ChevronRight" :size="16" /></button
            ><button v-if="runCursor" class="btn history-more" :disabled="historyBusy" @click="loadHistory">
              {{ historyBusy ? 'Loading…' : 'Load older analyses' }}
            </button>
          </section>
        </div>
        <aside class="ai-workspace panel">
          <div class="ai-workspace-header">
            <div>
              <span class="ai-star"><NIcon name="Sparkles" :size="20" /></span>
              <h2>Intelligence workspace</h2>
            </div>
            <span class="ai-label">NEXUS AI</span>
          </div>
          <div class="ai-body">
            <template v-if="!selectedRun"
              ><span class="ai-hero-symbol"><NIcon name="Sparkles" :size="30" /></span>
              <h3>A second perspective.<br />A clearer next step.</h3>
              <p>
                Analyze this conversation to surface its intent, urgency, and a draft grounded in your team’s
                knowledge.
              </p>
              <div class="ai-capabilities">
                <span><NIcon name="Check" :size="14" />Structured classification</span
                ><span><NIcon name="Check" :size="14" />Tenant-specific knowledge</span
                ><span><NIcon name="Check" :size="14" />Always reviewed by a human</span>
              </div></template
            >
            <div
              v-else-if="['queued', 'processing'].includes(selectedRun.status)"
              class="analysis-progress"
              role="status"
            >
              <span class="spinner" />
              <h3>
                {{ selectedRun.status === 'queued' ? 'In the queue' : 'Making sense of the conversation' }}
              </h3>
              <p>
                {{
                  watcher.stage.value === 'retrieving'
                    ? 'Finding relevant knowledge…'
                    : watcher.stage.value === 'retrying'
                      ? 'Provider temporarily unavailable. Retrying…'
                      : 'Preparing a structured analysis and response draft…'
                }}
              </p>
              <span class="engine-pill">{{
                watcher.connection.value === 'connected'
                  ? 'Live updates connected'
                  : 'Reconnecting · checking saved status'
              }}</span>
            </div>
            <div v-else-if="selectedRun.status === 'failed'" class="analysis-failed">
              <NIcon name="AlertCircle" :size="28" />
              <h3>Analysis couldn’t be completed</h3>
              <p>{{ selectedRun.error_message }}</p>
              <code>{{ selectedRun.error_code }}</code>
              <p>Your ticket is saved. Start a new run to try again.</p>
            </div>
            <template v-if="result"
              ><div class="insight-grid">
                <div>
                  <span class="card-label">Category</span><strong>{{ result.category }}</strong>
                </div>
                <div>
                  <span class="card-label">Suggested priority</span
                  ><StatusBadge :value="result.suggested_priority" />
                </div>
                <div>
                  <span class="card-label">Sentiment</span><strong>{{ result.sentiment }}</strong>
                </div>
                <div><span class="card-label">Review</span><StatusBadge :value="result.review_status" /></div>
              </div>
              <div class="ai-section">
                <h3>At a glance</h3>
                <p>{{ result.summary }}</p>
              </div>
              <div class="ai-section">
                <h3>
                  Suggested response
                  <button class="icon-btn" aria-label="Copy suggested response" @click="copy">
                    <NIcon name="Copy" :size="15" />
                  </button>
                </h3>
                <div class="reply-draft">{{ result.suggested_reply }}</div>
                <span class="draft-caption">DRAFT · HUMAN REVIEW REQUIRED · NEVER AUTO-SENT</span>
              </div>
              <div class="ai-section">
                <h3>
                  Supporting knowledge <span class="count-label">{{ sources.length }}</span>
                </h3>
                <p v-if="!sources.length" class="muted">
                  No supporting documents. Verify business or policy claims before use.
                </p>
                <NuxtLink
                  v-for="source in sources"
                  :key="source.id"
                  :to="`/t/${tid}/knowledge?document=${source.id}`"
                  class="source-link"
                  ><NIcon name="FileText" :size="16" /><span
                    >{{ source.title
                    }}<small v-if="!source.is_active">Archived since this analysis</small></span
                  ><NIcon name="ArrowUpRight" :size="15"
                /></NuxtLink>
                <p v-if="sourceErrors.length" class="form-error">
                  Some original references are unavailable. Verify them with an administrator.
                </p>
              </div>
              <details class="reasoning">
                <summary>Decision rationale</summary>
                <p>{{ result.reasoning_summary }}</p>
              </details>
              <div v-if="result.review_status === 'pending' && canWrite" class="review-actions">
                <button class="btn" :disabled="reviewing" @click="review('reject')">
                  <NIcon name="X" :size="16" />Reject</button
                ><button class="btn btn-primary" :disabled="reviewing" @click="review('approve')">
                  <NIcon name="Check" :size="16" />{{ reviewing ? 'Saving…' : 'Approve draft' }}
                </button>
              </div>
              <p v-if="result.review_status !== 'pending'" class="review-final">
                <NIcon name="ShieldCheck" :size="16" />{{
                  result.review_status === 'approved'
                    ? 'Approved for use. No message has been sent.'
                    : 'Rejected. Start a new analysis for another suggestion.'
                }}<small v-if="result.reviewed_at">Reviewed {{ date(result.reviewed_at) }}</small>
              </p></template
            >
          </div>
          <div class="ai-workspace-footer">
            <button
              v-if="canWrite"
              class="btn btn-primary analyze-button"
              :disabled="analyzing || active"
              @click="analyze"
            >
              <NIcon name="Sparkles" :size="17" />{{
                analyzing
                  ? 'Submitting…'
                  : active
                    ? 'Analysis in progress…'
                    : selectedRun
                      ? 'Run a new analysis'
                      : 'Analyze with AI'
              }}<NIcon name="ArrowRight" :size="16" />
            </button>
            <p><NIcon name="ShieldCheck" :size="13" />AI suggests. You decide.</p>
          </div>
        </aside>
      </div></template
    >
  </div>
</template>
