<script setup lang="ts">
import type { Run, Page } from '~/types'
const tid = String(useRoute().params.tenant_id)
const api = useApi()
const items = ref<Run[]>([])
const cursor = ref<string | null>(null)
const loading = ref(true)
const error = ref('')
const load = async (more = false) => {
  loading.value = true
  error.value = ''
  try {
    const page = await api<Page<Run>>(`/tenants/${tid}/runs`, {
      query: { cursor: more ? cursor.value || undefined : undefined },
    })
    items.value = more ? [...items.value, ...page.items] : page.items
    cursor.value = page.next_cursor
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
const duration = (run: Run) =>
  run.started_at && run.completed_at
    ? `${((+new Date(run.completed_at) - +new Date(run.started_at)) / 1000).toFixed(1)}s`
    : '—'
onMounted(() => load())
</script>
<template>
  <div>
    <AppHeader
      eyebrow="ENGINE OPERATIONS"
      title="Every run. A clear record."
      description="Follow the work behind each suggestion, from queue to completion."
      ><button class="btn" :disabled="loading" @click="load()">
        <NIcon name="RefreshCw" :size="16" />Refresh
      </button></AppHeader
    >
    <section class="panel">
      <div class="panel-heading">
        <h2>Execution history</h2>
        <span class="subtle-note">Persisted state · newest first</span>
      </div>
      <ViewState
        :loading="loading && !items.length"
        :error="error"
        :empty="!loading && !items.length"
        title="Your engine is ready."
        description="Start an analysis from a ticket to see its execution here."
        @retry="load()"
      />
      <div v-if="items.length && !error" class="table-scroll">
        <table class="runs-table">
          <thead>
            <tr>
              <th>EXECUTION</th>
              <th>STATUS</th>
              <th>MODEL / ACTOR</th>
              <th>ATTEMPTS</th>
              <th>DURATION</th>
              <th>STARTED</th>
              <th />
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in items" :key="run.id">
              <td>
                <NuxtLink :to="`/t/${tid}/tickets/${run.ticket_id}`" class="run-title"
                  ><NIcon name="Sparkles" :size="17" /><span
                    ><strong>#{{ run.id.slice(0, 8) }}</strong
                    ><small>Ticket #{{ run.ticket_id.slice(0, 8) }}</small
                    ><small
                      v-if="run.error_code"
                      class="text-error"
                      :title="run.error_message || undefined"
                      >{{ run.error_code }}</small
                    ></span
                  ></NuxtLink
                >
              </td>
              <td><StatusBadge :value="run.status" /></td>
              <td>
                <span class="model-name"
                  >{{ run.model_id
                  }}<small :title="run.initiated_by">{{ run.initiated_by.slice(0, 8) }}</small></span
                >
              </td>
              <td>{{ run.attempt_count }}</td>
              <td>{{ duration(run) }}</td>
              <td class="date-cell">{{ new Date(run.created_at).toLocaleString() }}</td>
              <td>
                <NuxtLink
                  :to="`/t/${tid}/tickets/${run.ticket_id}`"
                  class="icon-btn"
                  aria-label="Open associated ticket"
                  ><NIcon name="ArrowUpRight" :size="17"
                /></NuxtLink>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="table-footer">
        <span>{{ items.length }} executions loaded</span
        ><button v-if="cursor" class="btn btn-small" :disabled="loading" @click="load(true)">
          {{ loading ? 'Loading…' : 'Load older runs' }}
        </button>
      </div>
    </section>
  </div>
</template>
