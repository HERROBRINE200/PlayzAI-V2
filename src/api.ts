import type {
  AiModelConfig,
  AiProviderConfig,
  ApiError,
  AuthState,
  AuditLog,
  Command,
  ConfirmationRecord,
  Device,
  Health,
  Pc,
  SecurityEvent,
  WhatsAppStatus,
} from './types'

const envBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? ''

export function defaultApiBaseUrl(): string {
  return envBase
}

export function normalizeBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, '')
}

function apiError(status: number, body: unknown): ApiError {
  const payload = body as { error?: { code?: string; message?: string }; detail?: string } | null
  const error = new Error(
    payload?.error?.message ?? payload?.detail ?? `Backend request failed with HTTP ${status}.`,
  ) as ApiError
  error.status = status
  error.code = payload?.error?.code
  return error
}

export class PlayzApi {
  readonly baseUrl: string
  readonly auth: AuthState

  constructor(auth: AuthState) {
    this.auth = auth
    this.baseUrl = normalizeBaseUrl(auth.baseUrl)
    if (!this.baseUrl) throw new Error('A backend URL is required.')
  }

  private headers(useApiKey = false): HeadersInit {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Device-ID': this.auth.deviceId,
    }
    if (useApiKey || !this.auth.sessionToken) headers['X-API-Key'] = this.auth.apiKey
    if (this.auth.sessionToken && !useApiKey) headers['X-Session-Token'] = this.auth.sessionToken
    return headers
  }

  async request<T>(path: string, init: RequestInit = {}, useApiKey = false): Promise<T> {
    const controller = new AbortController()
    const timeout = globalThis.setTimeout(() => controller.abort(), 16_000)
    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        headers: { ...this.headers(useApiKey), ...(init.headers ?? {}) },
        signal: controller.signal,
      })
      const text = await response.text()
      let body: unknown = null
      try {
        body = text ? JSON.parse(text) : null
      } catch {
        body = text
      }
      if (!response.ok) throw apiError(response.status, body)
      return body as T
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        const timeoutError = new Error('The backend request timed out.') as ApiError
        timeoutError.code = 'timeout'
        throw timeoutError
      }
      throw error
    } finally {
      globalThis.clearTimeout(timeout)
    }
  }

  async health(): Promise<Health> {
    return this.request<Health>('/health', { method: 'GET' })
  }

  async authStatus(): Promise<{ authenticated: boolean; device_id?: string }> {
    return this.request('/api/auth/status', { method: 'GET' })
  }

  async createSession(): Promise<{ session_token: string; expires_at?: number; device_id: string }> {
    return this.request('/api/auth/session', {
      method: 'POST',
      body: JSON.stringify({ device_id: this.auth.deviceId }),
    }, true)
  }

  async devices(): Promise<{ devices: Device[] }> {
    return this.request('/api/devices', { method: 'GET' })
  }

  async pcs(): Promise<{ pcs: Pc[] }> {
    return this.request('/api/pcs', { method: 'GET' })
  }

  async securityEvents(): Promise<{ events: SecurityEvent[] }> {
    return this.request('/api/security/events', { method: 'GET' })
  }

  async whatsappStatus(): Promise<WhatsAppStatus> {
    return this.request('/api/whatsapp/status', { method: 'GET' })
  }

  async commands(limit = 100): Promise<{ commands: Command[] }> {
    return this.request(`/api/commands?limit=${limit}`, { method: 'GET' })
  }

  async chat(
    message: string,
    conversationId: string,
    providerId?: string,
    model?: string,
    language?: string,
  ): Promise<{
    reply: string
    conversation_id: string
    provider_used?: string
    model_used?: string
    fallback_occurred?: boolean
    requires_confirmation?: boolean
    confirmation?: ConfirmationRecord
  }> {
    const payload: Record<string, unknown> = {
      message,
      conversation_id: conversationId,
    }
    if (providerId) payload.provider_id = providerId
    if (model) payload.model = model
    if (language) payload.language = language

    return this.request('/api/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  async pairingCode(pcName: string): Promise<{ pairing_code: string; expires_at?: number }> {
    return this.request('/api/pairing/codes', {
      method: 'POST',
      body: JSON.stringify({ pc_name: pcName }),
    })
  }

  async command(deviceId: string, action: string, args: Record<string, unknown>, confirmation = false): Promise<Command & { ok: boolean; requires_confirmation?: boolean; risk_level?: string; risk_explanation?: string }> {
    return this.request('/api/command', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId, action, args, confirmation }),
    })
  }

  async wakePc(pcId: string, confirmation: boolean): Promise<Record<string, unknown>> {
    return this.request(`/api/pcs/${encodeURIComponent(pcId)}/wake`, {
      method: 'POST',
      body: JSON.stringify({ confirmation }),
    })
  }

  async revokeDevice(deviceId: string, masterKey: string, confirmation: boolean): Promise<Record<string, unknown>> {
    return this.request('/api/devices/revoke', {
      method: 'POST',
      headers: { 'X-API-Key': masterKey },
      body: JSON.stringify({ device_id: deviceId, confirmation }),
    }, true)
  }

  async lockdown(masterKey: string): Promise<Record<string, unknown>> {
    return this.request('/api/security/lockdown', {
      method: 'POST',
      headers: { 'X-API-Key': masterKey },
    }, true)
  }

  async unlock(masterKey: string): Promise<Record<string, unknown>> {
    return this.request('/api/security/unlock', {
      method: 'POST',
      headers: { 'X-API-Key': masterKey },
    }, true)
  }

  // Multi-AI Endpoints
  async providers(): Promise<{ providers: AiProviderConfig[] }> {
    return this.request('/api/ai/providers', { method: 'GET' })
  }

  async createProvider(data: {
    provider_type: string
    display_name: string
    api_key?: string
    base_url?: string
    default_model?: string
    enabled?: boolean
    priority?: number
    description?: string
  }): Promise<{ ok: boolean; provider: AiProviderConfig }> {
    return this.request('/api/ai/providers', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async updateProvider(
    id: string,
    data: {
      provider_type?: string
      display_name?: string
      api_key?: string
      base_url?: string
      default_model?: string
      enabled?: boolean
      priority?: number
      description?: string
    },
  ): Promise<{ ok: boolean; provider: AiProviderConfig }> {
    return this.request(`/api/ai/providers/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteProvider(id: string): Promise<{ ok: boolean; deleted: string }> {
    return this.request(`/api/ai/providers/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    })
  }

  async testProvider(id: string): Promise<{
    ok: boolean
    result: { ok: boolean; latency_ms?: number; models?: string[]; detail?: string; error_code?: string }
  }> {
    return this.request(`/api/ai/providers/${encodeURIComponent(id)}/test`, {
      method: 'POST',
    })
  }

  async discoverModels(providerId: string): Promise<{ models: string[]; provider_id: string }> {
    return this.request(`/api/ai/providers/${encodeURIComponent(providerId)}/models`, {
      method: 'GET',
    })
  }

  async models(): Promise<{ models: AiModelConfig[] }> {
    return this.request('/api/ai/models', { method: 'GET' })
  }

  async createModel(data: {
    provider_id: string
    model_name: string
    display_name?: string
    description?: string
  }): Promise<{ ok: boolean; model_id: string }> {
    return this.request('/api/ai/models', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async deleteModel(id: string): Promise<{ ok: boolean; deleted: string }> {
    return this.request(`/api/ai/models/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    })
  }

  async aiSettings(): Promise<{ settings: Record<string, string> }> {
    return this.request('/api/ai/settings', { method: 'GET' })
  }

  async updateAiSettings(settings: Record<string, string>): Promise<{ ok: boolean; settings: Record<string, string> }> {
    return this.request('/api/ai/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
  }

  // Security Confirmations
  async pendingConfirmations(): Promise<{ confirmations: ConfirmationRecord[] }> {
    return this.request('/api/security/confirmations/pending', { method: 'GET' })
  }

  async confirmAction(confirmationId: string): Promise<{ ok: boolean; command_id: string; message: string }> {
    return this.request(`/api/security/confirmations/${encodeURIComponent(confirmationId)}/confirm`, {
      method: 'POST',
    })
  }

  async cancelAction(confirmationId: string): Promise<{ ok: boolean; message: string }> {
    return this.request(`/api/security/confirmations/${encodeURIComponent(confirmationId)}/cancel`, {
      method: 'POST',
    })
  }

  // Audit Logs
  async auditLogs(limit = 100): Promise<{ audit_logs: AuditLog[] }> {
    return this.request(`/api/audit/logs?limit=${limit}`, { method: 'GET' })
  }

  websocketUrl(): string {
    const origin = typeof window === 'undefined' ? this.baseUrl : window.location.origin
    const url = new URL(`${this.baseUrl}/ws`, origin)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.searchParams.set('device_id', this.auth.deviceId)
    if (this.auth.sessionToken) url.searchParams.set('session_token', this.auth.sessionToken)
    else url.searchParams.set('api_key', this.auth.apiKey)
    return url.toString()
  }
}
