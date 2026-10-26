export type Role = 'admin' | 'agent' | 'viewer'
export interface Tenant {
  id: string
  name: string
  slug: string
  role: Role
}
export interface Page<T> {
  items: T[]
  next_cursor: string | null
}
export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'
export type Priority = 'low' | 'normal' | 'high' | 'urgent'
export interface Ticket {
  id: string
  tenant_id: string
  subject: string
  description: string
  status: TicketStatus
  priority: Priority
  created_at: string
  updated_at: string
  customer_name: string | null
  customer_email: string | null
  external_reference: string | null
}
export interface Run {
  id: string
  tenant_id: string
  ticket_id: string
  initiated_by: string
  status: 'queued' | 'processing' | 'succeeded' | 'failed'
  model_id: string
  attempt_count: number
  error_code: string | null
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}
export interface AIResult {
  id: string
  run_id: string
  category: string
  suggested_priority: Priority
  sentiment: string
  summary: string
  suggested_reply: string
  reasoning_summary: string
  source_document_ids: string[]
  needs_human_review: boolean
  review_status: 'pending' | 'approved' | 'rejected'
  reviewed_by: string | null
  reviewed_at: string | null
  created_at: string
}
export interface Knowledge {
  id: string
  title: string
  content: string
  document_type: 'faq' | 'policy' | 'product_information' | 'general_reference'
  is_active: boolean
  created_at: string
  updated_at: string
}
export interface Member {
  user_id: string
  role: Role
  is_active: boolean
  created_at: string
}
export interface Audit {
  id: string
  action: string
  actor_id: string | null
  resource_type: string
  resource_id: string | null
  created_at: string
}
