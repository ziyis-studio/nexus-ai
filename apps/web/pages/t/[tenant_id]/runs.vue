<script setup lang="ts">
import { Activity, ArrowRight, Clock3, MoreHorizontal, RefreshCw } from '@lucide/vue'
import type { Run, Page } from '~/types'
const tid = String(useRoute().params.tenant_id)
const api = useApi()
const items = ref<Run[]>([])
const cursor = ref<string | null>(null)
const loading = ref(true)
const error = ref('')
const selected = ref<Run | null>(null)
const detailsOpen = ref(false)
const load = async (more = false) => {
  loading.value = true
  error.value = ''
  try {
    const page = await api<Page<Run>>('/tenants/' + tid + '/runs', {
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
    ? ((+new Date(run.completed_at) - +new Date(run.started_at)) / 1000).toFixed(1) + 's'
    : '—'
const date = (value: string) =>
  new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
const open = (run: Run) => {
  selected.value = run
  detailsOpen.value = true
}
onMounted(() => load())
</script>
<template>
  <div>
    <AppHeader
      title="Execution history"
      description="A clear record of every analysis, from queue to decision."
      ><UiButton variant="outline" :disabled="loading" @click="load()"
        ><UiSpinner v-if="loading" data-icon="inline-start" /><RefreshCw
          v-else
          data-icon="inline-start"
        />Refresh</UiButton
      ></AppHeader
    >
    <UiCard class="gap-0 py-0">
      <UiCardHeader class="py-5"
        ><UiCardTitle><h2>Analysis runs</h2></UiCardTitle
        ><UiCardDescription
          >Newest first · {{ items.length }} executions loaded</UiCardDescription
        ></UiCardHeader
      >
      <UiSeparator />
      <UiCardContent class="p-0">
        <ViewState
          :loading="loading && !items.length"
          :error="error"
          :empty="!loading && !items.length"
          title="No analyses yet"
          description="Start an AI analysis from a ticket. Its progress and outcome will appear here."
          @retry="load()"
          ><UiButton as-child variant="outline"
            ><NuxtLink :to="'/t/' + tid + '/tickets'"
              >Open tickets<ArrowRight data-icon="inline-end" /></NuxtLink></UiButton
        ></ViewState>
        <UiTable v-if="items.length && !error">
          <UiTableHeader
            ><UiTableRow
              ><UiTableHead class="pl-5">Execution</UiTableHead><UiTableHead>Status</UiTableHead
              ><UiTableHead class="hidden md:table-cell">Model</UiTableHead
              ><UiTableHead class="hidden text-right md:table-cell">Attempts</UiTableHead
              ><UiTableHead class="hidden lg:table-cell">Duration</UiTableHead
              ><UiTableHead class="hidden lg:table-cell">Created</UiTableHead
              ><UiTableHead class="pr-5"><span class="sr-only">Run details</span></UiTableHead></UiTableRow
            ></UiTableHeader
          >
          <UiTableBody
            ><UiTableRow v-for="run in items" :key="run.id">
              <UiTableCell class="pl-5"
                ><NuxtLink :to="'/t/' + tid + '/tickets/' + run.ticket_id" class="table-subject"
                  ><Activity class="hidden size-4 shrink-0 text-muted-foreground sm:block" /><span
                    class="table-subject-copy"
                    ><strong class="font-mono">#{{ run.id.slice(0, 8) }}</strong
                    ><small>Ticket #{{ run.ticket_id.slice(0, 8) }}</small></span
                  ></NuxtLink
                ></UiTableCell
              >
              <UiTableCell
                ><StatusBadge :value="run.status" />
                <p v-if="run.error_code" class="mt-2 text-xs text-destructive">
                  {{ run.error_code }}
                </p></UiTableCell
              >
              <UiTableCell class="hidden md:table-cell"
                ><span class="text-xs">{{
                  run.model_id === 'fixture' ? 'Demo provider' : run.model_id
                }}</span></UiTableCell
              ><UiTableCell class="hidden text-right tabular-nums md:table-cell">{{
                run.attempt_count
              }}</UiTableCell
              ><UiTableCell class="hidden tabular-nums text-muted-foreground lg:table-cell">{{
                duration(run)
              }}</UiTableCell
              ><UiTableCell class="hidden whitespace-nowrap text-xs text-muted-foreground lg:table-cell">{{
                date(run.created_at)
              }}</UiTableCell>
              <UiTableCell class="pr-5"
                ><UiButton
                  variant="ghost"
                  size="icon"
                  :aria-label="'Run details for ' + run.id.slice(0, 8)"
                  @click="open(run)"
                  ><MoreHorizontal /></UiButton
              ></UiTableCell> </UiTableRow
          ></UiTableBody>
        </UiTable> </UiCardContent
      ><UiCardFooter class="justify-between gap-3 py-4"
        ><span class="flex items-center gap-2 text-xs text-muted-foreground"
          ><Clock3 class="size-3.5" />Your saved execution record</span
        ><UiButton v-if="cursor" variant="outline" size="sm" :disabled="loading" @click="load(true)">{{
          loading ? 'Loading…' : 'Load older runs'
        }}</UiButton></UiCardFooter
      >
    </UiCard>
    <UiSheet v-model:open="detailsOpen"
      ><UiSheetContent class="overflow-y-auto sm:max-w-md">
        <UiSheetHeader
          ><UiSheetTitle>Run details</UiSheetTitle
          ><UiSheetDescription v-if="selected"
            >Execution #{{ selected.id.slice(0, 8) }}</UiSheetDescription
          ></UiSheetHeader
        >
        <div v-if="selected" class="flex flex-col gap-6 px-4">
          <StatusBadge :value="selected.status" />
          <dl class="metadata-list text-sm">
            <div>
              <dt>Model</dt>
              <dd>{{ selected.model_id === 'fixture' ? 'Demo provider' : selected.model_id }}</dd>
            </div>
            <div>
              <dt>Attempts</dt>
              <dd>{{ selected.attempt_count }}</dd>
            </div>
            <div>
              <dt>Duration</dt>
              <dd>{{ duration(selected) }}</dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>{{ date(selected.created_at) }}</dd>
            </div>
            <div>
              <dt>Started</dt>
              <dd>{{ selected.started_at ? date(selected.started_at) : 'Not started' }}</dd>
            </div>
            <div>
              <dt>Completed</dt>
              <dd>{{ selected.completed_at ? date(selected.completed_at) : 'Not completed' }}</dd>
            </div>
          </dl>
          <UiAlert v-if="selected.error_code" variant="destructive"
            ><UiAlertTitle>{{ selected.error_code }}</UiAlertTitle
            ><UiAlertDescription>{{
              selected.error_message || 'The analysis could not complete. Your ticket is saved.'
            }}</UiAlertDescription></UiAlert
          >
          <UiSeparator />
          <p class="text-xs leading-6 text-muted-foreground">
            To try again, open the ticket and start a new analysis. Previous execution records stay available.
          </p>
          <UiButton as-child
            ><NuxtLink :to="'/t/' + tid + '/tickets/' + selected.ticket_id"
              >Open associated ticket<ArrowRight data-icon="inline-end" /></NuxtLink
          ></UiButton>
        </div> </UiSheetContent
    ></UiSheet>
  </div>
</template>
