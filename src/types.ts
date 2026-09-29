export type PageKey =
  | 'overview'
  | 'chat'
  | 'providers'
  | 'devices'
  | 'pc'
  | 'security'
  | 'commands'
  | 'conversations'
  | 'whatsapp'
  | 'audit'
  | 'settings'
  | 'about'

export type Health = {
  ok: boolean
  service?: string
  version?: string
  database_status?: string
  provider_configured?: boolean
  whatsapp_configured?: boolean
  authenticated_api_enabled?: boolean
  request_id?: string
}

export type MetricSet = {
  cpu_percent?: number | null
  ram_percent?: number | null
  storage_percent?: number | null
  network_status?: string | null
}

export type Device = {
  device_id: string
  name: string
  status?: string
  last_seen?: number | null
  authenticated?: boolean
  kind?: string
  agent_version?: string
  metrics?: MetricSet
  wake_on_lan?: string
}

export type Pc = {
  id: string
  device_id: string
  name: string
  mac_address?: string
  broadcast_address?: string
  agent_version?: string
  status?: string
  last_seen?: number | null
  cpu_percent?: number | null
  ram_percent?: number | null
  storage_percent?: number | null
  network_status?: string | null
  wake_on_lan?: string
}

export type SecurityEvent = {
  id: number | string
  ts?: number
  source?: string
  ip?: string
  event?: string
  detail?: string
  request_id?: string
}

export type Command = {
  id?: string
  command_id?: string
  target_device_id?: string
  requested_by?: string
  action?: string
  args?: Record<string, unknown>
  status?: string
  confirmation?: boolean
  created?: number
  updated?: number
  result_json?: string
}

export type WhatsAppStatus = {
  configured?: boolean
  official_cloud_api?: boolean
  voice_transcription?: string
}

export type ConfirmationRecord = {
  id: string
  confirmation_id?: string
  session_id?: string
  device_id?: string
  action: string
  command?: string
  args?: Record<string, unknown>
  risk_level: string
  risk_explanation: string
  created_at: number
  expires_at: number
  status: string
  consumed?: number
}

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  body: string
  created: number
  provider_used?: string
  model_used?: string
  fallback_occurred?: boolean
  requires_confirmation?: boolean
  confirmation?: ConfirmationRecord
}

export type Conversation = {
  id: string
  title: string
  created: number
  updated: number
  messages: ChatMessage[]
}

export type AuthState = {
  baseUrl: string
  deviceId: string
  apiKey: string
  sessionToken: string
  expiresAt?: number
}

export type RealtimeState = {
  connected: boolean
  lastMessage?: string
  error?: string
}

export type AiProviderConfig = {
  id: string
  provider_type: 'gemini' | 'openai' | 'claude' | 'openai_compatible' | 'custom'
  display_name: string
  api_key_masked?: string
  has_key?: boolean
  base_url?: string
  default_model?: string
  enabled: boolean | number
  priority: number
  description?: string
  status?: string
  last_tested_at?: number | null
  last_error?: string
  created_at?: number
  updated_at?: number
}

export type AiModelConfig = {
  id: string
  provider_id: string
  model_name: string
  display_name?: string
  description?: string
  is_custom?: boolean | number
  created_at?: number
}

export type AiSettings = {
  fallback_enabled?: string
  default_provider?: string
  default_model?: string
  default_language?: string
  pc_control_enabled?: string
}

export type AuditLog = {
  id: number
  timestamp: number
  user_id?: string
  session_id?: string
  device_id?: string
  source_ip?: string
  action: string
  risk_level: string
  command?: string
  confirmation_status?: string
  result: string
  exit_code?: number | null
  execution_time_ms?: number
  provider?: string
  model?: string
  detail?: string
}

export type ApiError = Error & { status?: number; code?: string }
