<script setup lang="ts">
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
const status = ref('')
const priority = ref('')
const showCreate = ref(false)
const saving = ref(false)
const saveError = ref('')
const form = reactive({
  subject: '',
  description: '',
  customer_name: '',
  customer_email: '',
  external_reference: '',
})
let controller: AbortController | null = null
let version = 0
const load = async (next?: string) => {
  const request = ++version
  controller?.abort()
  controller = new AbortController()
  loading.value = true
  error.value = ''
  currentCursor.value = next
  try {
    const result = await api<Page<Ticket>>(`/tenants/${tid}/tickets`, {
      query: {
        q: q.value || undefined,
        status: status.value || undefined,
        priority: priority.value || undefined,
        cursor: next,
      },
      signal: controller.signal,
    })
    if (request !== version) return
    items.value = result.items
    cursor.value = result.next_cursor
  } catch (e) {
    if (request === version) error.value = (e as Error).message
  } finally {
    if (request === version) loading.value = false
  }
}
const filter = () => {
  previousCursors.value = []
  void load()
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
    const ticket = await api<Ticket>(`/tenants/${tid}/tickets`, {
      method: 'POST',
      body: {
        ...form,
        customer_name: form.customer_name || null,
        customer_email: form.customer_email || null,
        external_reference: form.external_reference || null,
      },
    })
    showCreate.value = false
    success('Ticket created. Ready for your team.')
    await navigateTo(`/t/${tid}/tickets/${ticket.id}`)
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
  version++
  controller?.abort()
})
</script>
<template>
  <div>
    <AppHeader
      eyebrow="CUSTOMER OPERATIONS"
      title="A clearer view of every conversation."
      description="Triage with context. Respond with confidence."
      ><button
        v-if="auth.selected.value?.role !== 'viewer'"
        class="btn btn-primary"
        @click="showCreate = true"
      >
        <NIcon name="Plus" :size="17" />Create ticket
      </button></AppHeader
    >
    <div class="overview-grid">
      <div class="overview-card">
        <div>
          <span class="card-label">Tickets in view</span
          ><span class="metric-icon"><NIcon name="Inbox" /></span>
        </div>
        <strong>{{ loading ? '—' : String(items.length).padStart(2, '0') }}</strong
        ><small>Conversations on this page</small>
        <div class="mini-bars">
          <i
            v-for="(height, i) in [20, 35, 24, 46, 30, 55, 39, 64, 42, 54, 70, 58]"
            :key="i"
            :style="{ height: `${height}%` }"
          />
        </div>
      </div>
      <div class="overview-card">
        <div>
          <span class="card-label">Open conversations</span
          ><span class="metric-icon"><NIcon name="Clock3" /></span>
        </div>
        <strong>{{
          loading
            ? '—'
            : String(items.filter((t) => ['open', 'in_progress'].includes(t.status)).length).padStart(2, '0')
        }}</strong
        ><small><span class="small-dot" />Ready for the next step · current page</small>
      </div>
      <div class="overview-card overview-ai">
        <div>
          <span class="card-label">High attention</span><span class="metric-icon"><NIcon name="Zap" /></span>
        </div>
        <strong>{{
          loading
            ? '—'
            : String(items.filter((t) => ['urgent', 'high'].includes(t.priority)).length).padStart(2, '0')
        }}</strong
        ><small>High & urgent priority · current page</small><span class="abstract-orbit" />
      </div>
    </div>
    <section class="panel ticket-panel">
      <div class="panel-heading">
        <div>
          <h2>
            All tickets <span class="count-label">{{ items.length }}</span>
          </h2>
          <p>Your team’s conversations, in one place.</p>
        </div>
        <span class="subtle-note"><span class="small-dot" />Newest first</span>
      </div>
      <form class="table-toolbar" @submit.prevent="filter">
        <div class="search-field">
          <NIcon name="Search" :size="17" /><input
            v-model="q"
            aria-label="Search tickets"
            placeholder="Search conversations…"
            maxlength="200"
            type="search"
          />
        </div>
        <div class="filter-controls">
          <select v-model="status" aria-label="Filter by status" @change="filter">
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In progress</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option></select
          ><select v-model="priority" aria-label="Filter by priority" @change="filter">
            <option value="">All priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="normal">Normal</option>
            <option value="low">Low</option></select
          ><button class="btn btn-filter" aria-label="Apply filters">
            <NIcon name="SlidersHorizontal" :size="16" />
          </button>
        </div>
      </form>
      <ViewState
        :loading="loading"
        :error="error"
        :empty="!items.length"
        title="A clean slate."
        description="Create your first ticket or adjust your filters to get started."
        @retry="load(currentCursor)"
      />
      <div v-if="!loading && !error && items.length" class="table-scroll">
        <table class="ticket-table">
          <thead>
            <tr>
              <th>CONVERSATION</th>
              <th>STATUS</th>
              <th>PRIORITY</th>
              <th>CUSTOMER</th>
              <th>CREATED</th>
              <th><span class="sr-only">Open ticket</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ticket in items" :key="ticket.id">
              <td>
                <NuxtLink :to="`/t/${tid}/tickets/${ticket.id}`" class="ticket-subject"
                  ><span class="ticket-symbol"><NIcon name="Inbox" :size="17" /></span
                  ><span
                    ><strong>{{ ticket.subject }}</strong
                    ><small
                      >#{{ ticket.id.slice(0, 8) }}
                      <span
                        >· {{ ticket.description.slice(0, 58)
                        }}{{ ticket.description.length > 58 ? '…' : '' }}</span
                      ></small
                    ></span
                  ></NuxtLink
                >
              </td>
              <td><StatusBadge :value="ticket.status" /></td>
              <td>
                <span class="priority-label" :class="`priority-${ticket.priority}`"
                  ><span class="priority-bars"><i /><i /><i /></span>{{ ticket.priority }}</span
                >
              </td>
              <td>
                <span class="customer-cell"
                  ><span class="customer-avatar">{{
                    (ticket.customer_name || ticket.customer_email || '?').slice(0, 1).toUpperCase()
                  }}</span
                  >{{ ticket.customer_name || ticket.customer_email || 'Unassigned' }}</span
                >
              </td>
              <td class="date-cell">{{ date(ticket.created_at) }}</td>
              <td>
                <NuxtLink
                  :to="`/t/${tid}/tickets/${ticket.id}`"
                  class="icon-btn"
                  :aria-label="`Open ${ticket.subject}`"
                  ><NIcon name="ArrowUpRight" :size="17"
                /></NuxtLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="table-footer">
        <span>{{ items.length }} conversations on this page</span>
        <div>
          <button class="btn btn-small" :disabled="!previousCursors.length || loading" @click="previousPage">
            <NIcon name="ArrowLeft" :size="14" />Previous</button
          ><button class="btn btn-small" :disabled="!cursor || loading" @click="nextPage">
            Next<NIcon name="ArrowRight" :size="14" />
          </button>
        </div>
      </div>
    </section>
    <div class="intelligence-note">
      <span class="note-symbol"><NIcon name="Sparkles" :size="19" /></span>
      <div>
        <strong>Context makes all the difference.</strong
        ><span>Your knowledge base helps AI draft answers grounded in your organization’s policies.</span>
      </div>
      <NuxtLink :to="`/t/${tid}/knowledge`"
        >Explore knowledge base<NIcon name="ArrowRight" :size="15"
      /></NuxtLink>
    </div>
    <AppModal v-model:open="showCreate" title="Create a ticket"
      ><form class="stack-form" @submit.prevent="create">
        <p class="muted">Capture the conversation. AI analysis starts when you choose.</p>
        <label for="subject">Subject</label
        ><input
          id="subject"
          v-model="form.subject"
          required
          minlength="3"
          maxlength="200"
          placeholder="What does your customer need help with?"
        /><label for="description">Customer message</label
        ><textarea
          id="description"
          v-model="form.description"
          required
          minlength="10"
          maxlength="10000"
          rows="6"
          placeholder="Add the details, in English or Chinese…"
        />
        <details>
          <summary>Customer details <span class="muted">(optional)</span></summary>
          <div class="stack-form optional-fields">
            <label for="customer-name">Customer name</label
            ><input id="customer-name" v-model="form.customer_name" maxlength="150" /><label
              for="customer-email"
              >Customer email</label
            ><input id="customer-email" v-model="form.customer_email" type="email" maxlength="254" /><label
              for="external-ref"
              >External reference</label
            ><input id="external-ref" v-model="form.external_reference" maxlength="200" />
          </div>
        </details>
        <p v-if="saveError" class="form-error" role="alert">{{ saveError }}</p>
        <div class="form-actions">
          <button type="button" class="btn" @click="showCreate = false">Cancel</button
          ><button class="btn btn-primary" :disabled="saving">
            {{ saving ? 'Creating…' : 'Create ticket' }}<NIcon name="ArrowRight" :size="16" />
          </button>
        </div></form
    ></AppModal>
  </div>
</template>
