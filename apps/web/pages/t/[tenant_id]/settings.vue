<script setup lang="ts">
import type { Member, Audit, Page } from '~/types'
const auth = useAuth()
const tid = String(useRoute().params.tenant_id)
const api = useApi()
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
        api<Member[]>(`/tenants/${tid}/members`),
        api<Page<Audit>>(`/tenants/${tid}/audit`),
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
    const page = await api<Page<Audit>>(`/tenants/${tid}/audit`, {
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
onMounted(load)
</script>
<template>
  <div>
    <AppHeader
      eyebrow="ORGANIZATION"
      title="Your workspace, thoughtfully contained."
      description="Organization details, membership, and an accountable record of activity."
    />
    <section class="panel organization-panel">
      <div class="panel-heading">
        <h2><NIcon name="Building2" />Organization details</h2>
        <StatusBadge :value="auth.selected.value?.role || 'viewer'" />
      </div>
      <dl class="organization-details">
        <div>
          <dt>Name</dt>
          <dd>{{ auth.selected.value?.name }}</dd>
        </div>
        <div>
          <dt>Workspace slug</dt>
          <dd>{{ auth.selected.value?.slug }}</dd>
        </div>
        <div>
          <dt>Tenant ID</dt>
          <dd class="mono">{{ tid }}</dd>
        </div>
        <div>
          <dt>Access model</dt>
          <dd>Membership authorization + PostgreSQL row-level security</dd>
        </div>
      </dl>
    </section>
    <ViewState :loading="loading && !members.length" :error="error" @retry="load" />
    <p v-if="!admin" class="info-note">
      <NIcon name="ShieldCheck" />Membership and audit history are available to workspace administrators.
    </p>
    <template v-if="admin && !error"
      ><section class="panel settings-section">
        <div class="panel-heading">
          <div>
            <h2>
              Workspace members <span class="count-label">{{ members.length }}</span>
            </h2>
            <p>Read-only directory. Membership is provisioned by an authorized administrator.</p>
          </div>
          <NIcon name="ShieldCheck" />
        </div>
        <div v-for="member in members" :key="member.user_id" class="member-row">
          <span class="user-avatar"><NIcon name="Building2" :size="16" /></span
          ><span class="mono"
            >{{ member.user_id
            }}<small>Added {{ new Date(member.created_at).toLocaleDateString() }}</small></span
          ><StatusBadge :value="member.role" /><StatusBadge
            :value="member.is_active ? 'active' : 'inactive'"
          />
        </div>
      </section>
      <section class="panel settings-section">
        <div class="panel-heading">
          <h2>Audit trail</h2>
          <span class="subtle-note">Append-only business activity</span>
        </div>
        <ViewState
          :empty="!audits.length"
          title="A clear record starts here."
          description="Important workspace actions will appear here."
        />
        <div v-for="audit in audits" :key="audit.id" class="audit-row">
          <span class="history-icon"><NIcon name="Activity" :size="15" /></span
          ><span
            ><strong>{{ audit.action.replaceAll('.', ' · ') }}</strong
            ><small
              >{{ audit.resource_type }} #{{ audit.resource_id?.slice(0, 8) }} · Actor
              {{ audit.actor_id?.slice(0, 8) || 'system' }}</small
            ></span
          ><time>{{ new Date(audit.created_at).toLocaleString() }}</time>
        </div>
        <div v-if="cursor" class="table-footer">
          <span>{{ audits.length }} events loaded</span
          ><button class="btn btn-small" :disabled="loading" @click="more">Load older events</button>
        </div>
      </section></template
    >
  </div>
</template>
