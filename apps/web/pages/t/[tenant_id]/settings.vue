<script setup lang="ts">
import { Activity, Building2, Copy, Monitor, Moon, ShieldCheck, Sun, Users } from '@lucide/vue'
import type { Member, Audit, Page } from '~/types'
const auth = useAuth()
const tid = String(useRoute().params.tenant_id)
const api = useApi()
const { success } = useFeedback()
const { appearance, setAppearance } = useAppearance()
const members = ref<Member[]>([])
const audits = ref<Audit[]>([])
const cursor = ref<string | null>(null)
const loading = ref(true)
const error = ref('')
const admin = computed(() => auth.selected.value?.role === 'admin')
const load = async () => {
  loading.value = true
  error.value = ''
  try {
    if (admin.value) {
      const [people, history] = await Promise.all([
        api<Member[]>('/tenants/' + tid + '/members'),
        api<Page<Audit>>('/tenants/' + tid + '/audit'),
      ])
      members.value = people
      audits.value = history.items
      cursor.value = history.next_cursor
    }
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
const more = async () => {
  loading.value = true
  try {
    const page = await api<Page<Audit>>('/tenants/' + tid + '/audit', {
      query: { cursor: cursor.value || undefined },
    })
    audits.value.push(...page.items)
    cursor.value = page.next_cursor
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
const copy = async () => {
  try {
    await navigator.clipboard.writeText(tid)
    success('Workspace ID copied.')
  } catch {
    error.value = 'Clipboard unavailable. Select the workspace ID to copy it.'
  }
}
const action = (value: string) => {
  const names: Record<string, string> = {
    'ticket.created': 'Ticket created',
    'ticket.updated': 'Ticket updated',
    'knowledge.created': 'Knowledge created',
    'knowledge.updated': 'Knowledge updated',
    'analysis.requested': 'Analysis requested',
    'analysis.succeeded': 'Analysis completed',
    'analysis.failed': 'Analysis failed',
    'result.approved': 'Draft approved',
    'result.rejected': 'Draft rejected',
  }
  return names[value] || value.replaceAll('.', ' ')
}
onMounted(load)
</script>
<template>
  <div>
    <AppHeader
      title="Organization settings"
      description="Your workspace, its people, and your preferences."
    />
    <UiTabs default-value="general" class="flex flex-col gap-6">
      <div class="overflow-x-auto">
        <UiTabsList variant="line"
          ><UiTabsTrigger value="general"><Building2 />General</UiTabsTrigger
          ><UiTabsTrigger v-if="admin" value="members"><Users />Members</UiTabsTrigger
          ><UiTabsTrigger v-if="admin" value="audit"><Activity />Audit trail</UiTabsTrigger
          ><UiTabsTrigger value="appearance"><Sun />Appearance</UiTabsTrigger></UiTabsList
        >
      </div>
      <ViewState :error="error" @retry="load" />
      <UiTabsContent value="general">
        <UiCard class="max-w-3xl"
          ><UiCardHeader
            ><UiCardTitle><h2>Workspace details</h2></UiCardTitle
            ><UiCardDescription
              >Information about the organization you’re currently working in.</UiCardDescription
            ></UiCardHeader
          >
          <UiCardContent
            ><dl class="metadata-list">
              <div>
                <dt>Organization</dt>
                <dd class="font-medium">{{ auth.selected.value?.name }}</dd>
              </div>
              <div>
                <dt>Workspace</dt>
                <dd>{{ auth.selected.value?.slug }}</dd>
              </div>
              <div>
                <dt>Your role</dt>
                <dd><StatusBadge :value="auth.selected.value?.role || 'viewer'" /></dd>
              </div>
              <div>
                <dt>Workspace ID</dt>
                <dd class="flex min-w-0 items-center gap-2">
                  <span class="truncate font-mono text-xs" :title="tid">{{ tid }}</span
                  ><UiButton variant="ghost" size="icon-sm" aria-label="Copy workspace ID" @click="copy"
                    ><Copy
                  /></UiButton>
                </dd>
              </div></dl
          ></UiCardContent>
          <UiCardFooter
            ><span class="flex items-center gap-2 text-xs text-muted-foreground"
              ><ShieldCheck class="size-4 shrink-0" />Tickets and knowledge are private to this
              workspace.</span
            ></UiCardFooter
          >
        </UiCard>
        <UiAlert v-if="!admin" class="mt-5 max-w-3xl"
          ><ShieldCheck /><UiAlertTitle>Your workspace access</UiAlertTitle
          ><UiAlertDescription
            >Membership and audit history are available to workspace administrators.</UiAlertDescription
          ></UiAlert
        >
      </UiTabsContent>
      <UiTabsContent v-if="admin" value="members">
        <UiCard
          ><UiCardHeader
            ><UiCardTitle><h2>Workspace members</h2></UiCardTitle
            ><UiCardDescription
              >A read-only directory of the people in this workspace.</UiCardDescription
            ></UiCardHeader
          >
          <UiCardContent class="px-0"
            ><ViewState
              :loading="loading && !members.length"
              :empty="!loading && !members.length"
              title="No members to display"
            />
            <UiTable v-if="members.length"
              ><UiTableHeader
                ><UiTableRow
                  ><UiTableHead class="pl-5">Member</UiTableHead><UiTableHead>Role</UiTableHead
                  ><UiTableHead>Status</UiTableHead
                  ><UiTableHead class="hidden pr-5 text-right sm:table-cell">Joined</UiTableHead></UiTableRow
                ></UiTableHeader
              ><UiTableBody
                ><UiTableRow v-for="member in members" :key="member.user_id"
                  ><UiTableCell class="pl-5"
                    ><span class="flex items-center gap-3"
                      ><UiAvatar class="size-8"
                        ><UiAvatarFallback>{{
                          member.user_id.slice(0, 2).toUpperCase()
                        }}</UiAvatarFallback></UiAvatar
                      ><span class="font-mono text-xs" :title="member.user_id"
                        >#{{ member.user_id.slice(0, 8) }}</span
                      ></span
                    ></UiTableCell
                  ><UiTableCell><StatusBadge :value="member.role" /></UiTableCell
                  ><UiTableCell><StatusBadge :value="member.is_active ? 'active' : 'inactive'" /></UiTableCell
                  ><UiTableCell class="hidden pr-5 text-right text-xs text-muted-foreground sm:table-cell">{{
                    new Date(member.created_at).toLocaleDateString()
                  }}</UiTableCell></UiTableRow
                ></UiTableBody
              ></UiTable
            > </UiCardContent
          ><UiCardFooter
            ><p class="text-xs text-muted-foreground">
              {{ members.length }} members · Changes are managed by an authorized administrator.
            </p></UiCardFooter
          >
        </UiCard>
      </UiTabsContent>
      <UiTabsContent v-if="admin" value="audit">
        <UiCard
          ><UiCardHeader
            ><UiCardTitle><h2>Audit trail</h2></UiCardTitle
            ><UiCardDescription
              >Important workspace actions, with a record of who acted and when.</UiCardDescription
            ></UiCardHeader
          ><UiCardContent>
            <ViewState
              :loading="loading && !audits.length"
              :empty="!loading && !audits.length"
              title="No activity yet"
              description="Ticket updates, knowledge changes, and review decisions will appear here."
            />
            <ol class="flex flex-col gap-0">
              <li v-for="audit in audits" :key="audit.id" class="flex flex-wrap items-start gap-3 py-4">
                <UiAvatar class="size-8"
                  ><UiAvatarFallback><Activity class="size-3.5" /></UiAvatarFallback
                ></UiAvatar>
                <div class="flex min-w-0 flex-1 flex-col gap-1">
                  <strong class="text-sm font-medium">{{ action(audit.action) }}</strong
                  ><span class="text-xs text-muted-foreground"
                    >{{ audit.resource_type.replaceAll('_', ' ') }} #{{
                      audit.resource_id?.slice(0, 8) || '—'
                    }}
                    · {{ audit.actor_id ? 'Member #' + audit.actor_id.slice(0, 8) : 'System' }}</span
                  >
                </div>
                <time class="text-xs text-muted-foreground">{{
                  new Date(audit.created_at).toLocaleString()
                }}</time>
              </li>
            </ol> </UiCardContent
          ><UiCardFooter class="justify-between gap-3"
            ><span class="text-xs text-muted-foreground">{{ audits.length }} events loaded</span
            ><UiButton v-if="cursor" variant="outline" size="sm" :disabled="loading" @click="more">{{
              loading ? 'Loading…' : 'Load older events'
            }}</UiButton></UiCardFooter
          ></UiCard
        >
      </UiTabsContent>
      <UiTabsContent value="appearance">
        <UiCard class="max-w-3xl"
          ><UiCardHeader
            ><UiCardTitle><h2>Make it your workspace</h2></UiCardTitle
            ><UiCardDescription>Your preferences stay on this device.</UiCardDescription></UiCardHeader
          ><UiCardContent
            ><UiFieldGroup
              ><UiField
                ><UiFieldLabel id="appearance-label">Theme</UiFieldLabel
                ><UiFieldDescription
                  >Choose a light or dark workspace, or follow your device.</UiFieldDescription
                ><UiToggleGroup
                  type="single"
                  :spacing="2"
                  variant="outline"
                  :model-value="appearance"
                  aria-labelledby="appearance-label"
                  @update:model-value="
                    setAppearance($event === 'dark' || $event === 'system' ? $event : 'light')
                  "
                  ><UiToggleGroupItem value="light"><Sun />Light</UiToggleGroupItem
                  ><UiToggleGroupItem value="dark"><Moon />Dark</UiToggleGroupItem
                  ><UiToggleGroupItem value="system"><Monitor />System</UiToggleGroupItem></UiToggleGroup
                ></UiField
              ></UiFieldGroup
            ></UiCardContent
          ><UiCardFooter
            ><p class="text-xs text-muted-foreground">
              Reduced-motion preferences from your device are respected automatically.
            </p></UiCardFooter
          ></UiCard
        >
      </UiTabsContent>
    </UiTabs>
  </div>
</template>
