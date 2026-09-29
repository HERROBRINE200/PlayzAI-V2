import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  Bot,
  Brain,
  CheckCircle2,
  CircleHelp,
  Clock,
  Compass,
  Cpu,
  Flame,
  Gamepad2,
  HardDrive,
  Key,
  Layers,
  Lock,
  MessageSquare,
  Monitor,
  Moon,
  Play,
  Plus,
  Power,
  RefreshCw,
  Send,
  Settings,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Sun,
  Terminal,
  Trash2,
  Unlock,
  Video,
  Volume2,
  Wifi,
  XCircle,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { PlayzApi } from './api'
import type {
  AiModelConfig,
  AiProviderConfig,
  AuthState,
  AuditLog,
  ChatMessage,
  Command,
  ConfirmationRecord,
  Conversation,
  Device,
  Health,
  PageKey,
  Pc,
  RealtimeState,
  SecurityEvent,
  WhatsAppStatus,
} from './types'

const AUTH_STORAGE_KEY = 'playzai_dashboard_auth_v2'
const CONVERSATIONS_STORAGE_KEY = 'playzai_dashboard_conversations_v2'

function readSavedAuth(): AuthState | null {
  try {
    const raw = sessionStorage.getItem(AUTH_STORAGE_KEY)
    return raw ? (JSON.parse(raw) as AuthState) : null
  } catch {
    return null
  }
}

function saveAuth(auth: AuthState | null) {
  if (auth) sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth))
  else sessionStorage.removeItem(AUTH_STORAGE_KEY)
}

function readConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(CONVERSATIONS_STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Conversation[]) : []
  } catch {
    return []
  }
}

function saveConversations(value: Conversation[]) {
  localStorage.setItem(CONVERSATIONS_STORAGE_KEY, JSON.stringify(value))
}

function formatTime(value?: number | null) {
  if (!value) return 'Never'
  const ms = value < 10_000_000_000 ? value * 1000 : value
  return new Intl.DateTimeFormat('en-IN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(ms))
}

function relativeTime(value?: number | null) {
  if (!value) return 'Never'
  const ms = value < 10_000_000_000 ? value * 1000 : value
  const delta = Math.max(0, Math.floor((Date.now() - ms) / 1000))
  if (delta < 15) return 'just now'
  if (delta < 60) return `${delta}s ago`
  if (delta < 3600) return `${Math.floor(delta / 60)}m ago`
  if (delta < 86400) return `${Math.floor(delta / 3600)}h ago`
  return `${Math.floor(delta / 86400)}d ago`
}

function statusKey(value?: string | boolean | null) {
  if (value === true || value === 'online' || value === 'ok' || value === 'configured' || value === 'packet_sent' || value === 'completed') return 'online'
  if (value === 'offline' || value === 'not_configured' || value === 'untested' || value === 'queued') return 'offline'
  if (value === 'blocked' || value === 'failed' || value === 'error' || value === false) return 'danger'
  return 'offline'
}

function StatusPill({ value, label, pulse = false }: { value?: string | boolean | null; label?: string; pulse?: boolean }) {
  const kind = statusKey(value)
  const text = label || String(value || 'unknown')
  return (
    <span className={`status-pill ${kind} ${pulse ? 'pulse' : ''}`}>
      <span className="status-dot" />
      {text}
    </span>
  )
}

function RiskBadge({ level }: { level?: string }) {
  const lvl = level || 'LEVEL 1 — SAFE'
  if (lvl.includes('HIGH') || lvl.includes('LEVEL 3')) {
    return <span className="badge-risk-high"><AlertOctagon size={12} /> {lvl}</span>
  }
  if (lvl.includes('MODERATE') || lvl.includes('LEVEL 2')) {
    return <span className="badge-risk-moderate"><AlertTriangle size={12} /> {lvl}</span>
  }
  return <span className="badge-risk-safe"><ShieldCheck size={12} /> {lvl}</span>
}

function Toast({ message, onClose }: { message: { text: string; kind: 'success' | 'error' | 'info' }; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000)
    return () => clearTimeout(t)
  }, [onClose])
  return (
    <div className={`toast toast-${message.kind}`}>
      {message.kind === 'success' && <CheckCircle2 size={16} className="toast-icon" />}
      {message.kind === 'error' && <XCircle size={16} className="toast-icon" />}
      {message.kind === 'info' && <CircleHelp size={16} className="toast-icon" />}
      <span>{message.text}</span>
      <button className="button-icon" onClick={onClose} style={{ marginLeft: 'auto' }}>×</button>
    </div>
  )
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (auth: AuthState) => void }) {
  const [baseUrl, setBaseUrl] = useState(window.location.origin)
  const [deviceId, setDeviceId] = useState('dashboard-admin')
  const [apiKey, setApiKey] = useState('')
  const [remember, setRemember] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!baseUrl || !deviceId || !apiKey) {
      setError('Please fill in all connection fields.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const tempAuth: AuthState = { baseUrl, deviceId, apiKey, sessionToken: '' }
      const api = new PlayzApi(tempAuth)
      const session = await api.createSession()
      const finalAuth: AuthState = {
        baseUrl,
        deviceId,
        apiKey,
        sessionToken: session.session_token,
        expiresAt: session.expires_at,
      }
      if (remember) saveAuth(finalAuth)
      onAuthenticated(finalAuth)
    } catch (err: any) {
      setError(err?.message || 'Authentication failed. Check backend URL and API key.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-layout">
      <div className="auth-left">
        <div className="brand" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="brand-badge"><Bot size={20} /></div>
          <div>
            <strong style={{ fontSize: 18, letterSpacing: '-0.03em' }}>PlayzAI <span style={{ color: '#8569ff' }}>V2</span></strong>
            <small style={{ display: 'block', fontSize: 10, color: 'var(--muted)' }}>Multi-AI & Windows Automation</small>
          </div>
        </div>
        <div className="auth-hero">
          <h1>Universal Multi-AI & PC Control Hub.</h1>
          <p>Orchestrate Gemini, OpenAI, Claude, local models, and real-time Windows PC automation with zero-trust risk classification.</p>
          <div className="hero-points">
            <span><CheckCircle2 size={14} /> Multi-Provider AI (Gemini, Claude, GPT-4o)</span>
            <span><CheckCircle2 size={14} /> Real Windows Automation & Telemetry</span>
            <span><CheckCircle2 size={14} /> Zero-Trust High-Risk Confirmations</span>
            <span><CheckCircle2 size={14} /> English, Hindi & Indian Hinglish Voice</span>
          </div>
        </div>
        <div className="auth-foot">PLAYZAI V2.0 <span>•</span> SECURE ENTERPRISE CONTROL</div>
      </div>

      <div className="auth-panel">
        <div className="auth-panel-inner">
          <div className="auth-kicker">CONTROL CENTER ACCESS</div>
          <h2>Connect to <span>PlayzAI</span></h2>
          <form className="auth-form" onSubmit={handleSubmit}>
            {error && <div className="form-error"><AlertOctagon size={16} /><span>{error}</span></div>}
            <label>
              Backend URL
              <input type="text" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="http://127.0.0.1:8000" />
            </label>
            <label>
              Device ID
              <input type="text" value={deviceId} onChange={(e) => setDeviceId(e.target.value)} placeholder="dashboard-admin" />
            </label>
            <label>
              API Key / Enrollment Key
              <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="plz_..." />
            </label>
            <label className="check-label">
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
              Remember session in browser storage
            </label>
            <button type="submit" className="button button-primary" disabled={loading} style={{ width: '100%', height: 46, marginTop: 10 }}>
              {loading ? <RefreshCw className="spin" size={16} /> : <Unlock size={16} />}
              {loading ? 'Authenticating...' : 'Connect to Dashboard'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

// Global Context Interface for Pages
interface DashboardContext {
  api: PlayzApi
  auth: AuthState
  health: Health | null
  devices: Device[]
  pcs: Pc[]
  securityEvents: SecurityEvent[]
  commands: Command[]
  whatsapp: WhatsAppStatus | null
  providers: AiProviderConfig[]
  models: AiModelConfig[]
  aiSettings: Record<string, string>
  pendingConfirmations: ConfirmationRecord[]
  auditLogs: AuditLog[]
  conversations: Conversation[]
  setConversations: React.Dispatch<React.SetStateAction<Conversation[]>>
  realtime: RealtimeState
  activePage: PageKey
  go: (p: PageKey) => void
  showToast: (text: string, kind?: 'success' | 'error' | 'info') => void
  refreshAll: () => Promise<void>
}

function StatCard({ label, value, detail, icon: Icon, tone = 'violet' }: { label: string; value: string | number; detail?: string; icon: any; tone?: string }) {
  return (
    <div className={`stat-card tone-${tone}`}>
      <div className="stat-top">
        <span className="stat-label">{label}</span>
        <div className="stat-icon"><Icon size={16} /></div>
      </div>
      <div className="stat-value">{value}</div>
      {detail && <div className="stat-bottom">{detail}</div>}
    </div>
  )
}

function OverviewPage(ctx: DashboardContext) {
  const onlinePcs = ctx.pcs.filter((p) => p.status === 'online')
  const enabledProviders = ctx.providers.filter((p) => p.enabled)

  return (
    <div>
      <div className="hero-strip">
        <div>
          <div className="eyebrow"><Sparkles size={13} /> PLAYZAI V2 ACTIVE CONTROL</div>
          <h2>Unified Multi-AI & <em>PC Automation</em> Hub</h2>
          <p>Real-time telemetry, multi-provider model routing with instant fallback, and zero-trust Windows PC command execution.</p>
        </div>
        <div className="hero-orb">
          <div className="orb-ring" />
          <div className="orb-ring ring-b" />
          <div className="orb-core"><Brain size={26} /></div>
        </div>
      </div>

      <div className="stats-grid">
        <StatCard label="AI Providers Active" value={`${enabledProviders.length} / ${ctx.providers.length}`} detail={`Default: ${ctx.aiSettings.default_provider || 'gemini'}`} icon={Brain} tone="violet" />
        <StatCard label="Connected PCs" value={onlinePcs.length} detail={`${ctx.pcs.length} total enrolled`} icon={Monitor} tone="blue" />
        <StatCard label="Pending Confirmations" value={ctx.pendingConfirmations.length} detail="Zero-trust queue" icon={AlertOctagon} tone={ctx.pendingConfirmations.length > 0 ? 'red' : 'green'} />
        <StatCard label="Commands Executed" value={ctx.commands.length} detail="Audit verified" icon={Terminal} tone="amber" />
      </div>

      <div className="overview-grid">
        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>AI Providers & Models</h3>
              <p>Active multi-provider status and routing</p>
            </div>
            <button className="button button-secondary" onClick={() => ctx.go('providers')} style={{ fontSize: 11 }}>Manage Providers</button>
          </div>
          {ctx.providers.length === 0 ? (
            <div className="empty-state">
              <Brain size={32} />
              <strong>No AI Providers Configured</strong>
              <p>Add Google Gemini, OpenAI, Claude, or custom endpoints.</p>
              <button className="button button-primary" onClick={() => ctx.go('providers')}>Configure Providers</button>
            </div>
          ) : (
            <div>
              {ctx.providers.map((p) => (
                <div key={p.id} className="health-row">
                  <div className="health-icon"><Brain size={16} /></div>
                  <div className="health-copy">
                    <strong>{p.display_name}</strong>
                    <span>{p.provider_type.toUpperCase()} • Model: {p.default_model || 'default'}</span>
                  </div>
                  <StatusPill value={p.status || (p.enabled ? 'online' : 'offline')} />
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="panel">
          <div className="panel-head">
            <div>
              <h3>Primary PC Status</h3>
              <p>Live agent metrics & telemetry</p>
            </div>
            <button className="button button-secondary" onClick={() => ctx.go('pc')} style={{ fontSize: 11 }}>PC Controller</button>
          </div>
          {ctx.pcs.length === 0 ? (
            <div className="empty-state">
              <Monitor size={32} />
              <strong>No Windows PC Connected</strong>
              <p>Pair a PC agent using a secure 6-digit code.</p>
              <button className="button button-primary" onClick={() => ctx.go('devices')}>Pair Device</button>
            </div>
          ) : (
            <div>
              {ctx.pcs.map((pc) => (
                <div key={pc.id}>
                  <div className="pc-summary">
                    <div className="device-avatar pc"><Monitor size={22} /></div>
                    <div>
                      <h4>{pc.name}</h4>
                      <span>ID: {pc.device_id} • Agent: {pc.agent_version || '2.0.0'}</span>
                    </div>
                    <StatusPill value={pc.status} pulse={pc.status === 'online'} />
                  </div>
                  <div className="metric-grid">
                    <div className="mini-metric"><Cpu size={14} /><span>CPU</span><strong>{pc.cpu_percent != null ? `${pc.cpu_percent}%` : 'N/A'}</strong></div>
                    <div className="mini-metric"><Activity size={14} /><span>RAM</span><strong>{pc.ram_percent != null ? `${pc.ram_percent}%` : 'N/A'}</strong></div>
                    <div className="mini-metric"><HardDrive size={14} /><span>Disk</span><strong>{pc.storage_percent != null ? `${pc.storage_percent}%` : 'N/A'}</strong></div>
                    <div className="mini-metric"><Wifi size={14} /><span>Network</span><strong>{pc.network_status || 'online'}</strong></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function AIProvidersPage(ctx: DashboardContext) {
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [providerType, setProviderType] = useState<'gemini' | 'openai' | 'claude' | 'openai_compatible' | 'custom'>('gemini')
  const [displayName, setDisplayName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [defaultModel, setDefaultModel] = useState('')
  const [priority, setPriority] = useState(1)
  const [description, setDescription] = useState('')
  const [enabled, setEnabled] = useState(true)

  const [testingId, setTestingId] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<Record<string, any>>({})
  const [discoveringId, setDiscoveringId] = useState<string | null>(null)
  const [discoveredModels, setDiscoveredModels] = useState<Record<string, string[]>>({})

  const handleOpenAdd = () => {
    setEditingId(null)
    setProviderType('gemini')
    setDisplayName('Google Gemini Pro')
    setApiKey('')
    setBaseUrl('https://generativelanguage.googleapis.com')
    setDefaultModel('gemini-1.5-flash')
    setPriority(ctx.providers.length + 1)
    setDescription('')
    setEnabled(true)
    setModalOpen(true)
  }

  const handleOpenEdit = (p: AiProviderConfig) => {
    setEditingId(p.id)
    setProviderType(p.provider_type)
    setDisplayName(p.display_name)
    setApiKey('') // Masked, leave empty to keep
    setBaseUrl(p.base_url || '')
    setDefaultModel(p.default_model || '')
    setPriority(p.priority)
    setDescription(p.description || '')
    setEnabled(Boolean(p.enabled))
    setModalOpen(true)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingId) {
        await ctx.api.updateProvider(editingId, {
          provider_type: providerType,
          display_name: displayName,
          api_key: apiKey.trim() || undefined,
          base_url: baseUrl.trim(),
          default_model: defaultModel.trim(),
          priority,
          description,
          enabled,
        })
        ctx.showToast('Provider updated successfully.', 'success')
      } else {
        await ctx.api.createProvider({
          provider_type: providerType,
          display_name: displayName,
          api_key: apiKey.trim(),
          base_url: baseUrl.trim(),
          default_model: defaultModel.trim(),
          priority,
          description,
          enabled,
        })
        ctx.showToast('AI Provider created successfully.', 'success')
      }
      setModalOpen(false)
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Failed to save provider.', 'error')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to remove this AI provider?')) return
    try {
      await ctx.api.deleteProvider(id)
      ctx.showToast('Provider deleted.', 'success')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Failed to delete provider.', 'error')
    }
  }

  const handleTestConnection = async (id: string) => {
    setTestingId(id)
    try {
      const res = await ctx.api.testProvider(id)
      setTestResult((prev) => ({ ...prev, [id]: res.result }))
      if (res.ok) {
        ctx.showToast(`Connection successful! Latency: ${res.result?.latency_ms}ms`, 'success')
      } else {
        ctx.showToast(`Test failed: ${res.result?.detail || 'Error'}`, 'error')
      }
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Connection test failed.', 'error')
    } finally {
      setTestingId(null)
    }
  }

  const handleDiscoverModels = async (id: string) => {
    setDiscoveringId(id)
    try {
      const res = await ctx.api.discoverModels(id)
      setDiscoveredModels((prev) => ({ ...prev, [id]: res.models }))
      ctx.showToast(`Discovered ${res.models.length} available models.`, 'success')
    } catch (err: any) {
      ctx.showToast(err?.message || 'Model discovery failed.', 'error')
    } finally {
      setDiscoveringId(null)
    }
  }

  return (
    <div>
      <div className="section-title">
        <div>
          <div className="eyebrow"><Brain size={13} /> MULTI-AI PROVIDER MANAGEMENT</div>
          <h1>AI Providers & Model Routing</h1>
          <p>Configure Google Gemini, OpenAI, Anthropic Claude, OpenAI-compatible and custom endpoints. Multi-API keys remain safely encrypted on the backend.</p>
        </div>
        <button className="button button-primary" onClick={handleOpenAdd}>
          <Plus size={16} /> Add AI Provider
        </button>
      </div>

      <div className="provider-grid">
        {ctx.providers.map((p) => {
          const testInfo = testResult[p.id]
          const modelsList = discoveredModels[p.id]
          return (
            <div key={p.id} className="provider-card">
              <div className="provider-head">
                <div className="provider-title">
                  <div className="provider-icon"><Brain size={18} /></div>
                  <div>
                    <strong style={{ fontSize: 13, display: 'block' }}>{p.display_name}</strong>
                    <span style={{ fontSize: 10, color: 'var(--muted)' }}>Priority #{p.priority} • {p.provider_type.toUpperCase()}</span>
                  </div>
                </div>
                <StatusPill value={p.status || (p.enabled ? 'online' : 'offline')} />
              </div>

              <div className="provider-meta">
                <div className="provider-meta-row">
                  <span>API Key</span>
                  <code style={{ fontSize: 10 }}>{p.api_key_masked || '••••••••'}</code>
                </div>
                <div className="provider-meta-row">
                  <span>Default Model</span>
                  <strong>{p.default_model || 'Auto'}</strong>
                </div>
                <div className="provider-meta-row">
                  <span>Base URL</span>
                  <span style={{ fontSize: 10, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.base_url || 'Default'}</span>
                </div>
                {p.last_tested_at && (
                  <div className="provider-meta-row">
                    <span>Last Test</span>
                    <small>{relativeTime(p.last_tested_at)}</small>
                  </div>
                )}
                {p.last_error && (
                  <div style={{ color: 'var(--red)', fontSize: 10, marginTop: 4 }}>
                    Error: {p.last_error}
                  </div>
                )}
              </div>

              {testInfo && (
                <div style={{ padding: 10, borderRadius: 8, background: testInfo.ok ? 'rgba(101,211,164,0.1)' : 'rgba(255,124,157,0.1)', fontSize: 10 }}>
                  <strong>{testInfo.ok ? '✓ Connected' : '✗ Failed'}:</strong> {testInfo.detail}
                  {testInfo.latency_ms && <span style={{ marginLeft: 8, color: 'var(--muted)' }}>({testInfo.latency_ms}ms)</span>}
                </div>
              )}

              {modelsList && modelsList.length > 0 && (
                <div style={{ fontSize: 10 }}>
                  <span style={{ color: 'var(--muted)' }}>Discovered Models ({modelsList.length}):</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                    {modelsList.slice(0, 5).map((m) => (
                      <span key={m} style={{ padding: '2px 6px', background: 'rgba(255,255,255,0.06)', borderRadius: 4, fontSize: 9 }}>{m}</span>
                    ))}
                    {modelsList.length > 5 && <span style={{ color: 'var(--muted)', fontSize: 9 }}>+{modelsList.length - 5} more</span>}
                  </div>
                </div>
              )}

              <div className="provider-actions">
                <button className="button button-secondary" onClick={() => handleTestConnection(p.id)} disabled={testingId === p.id} style={{ fontSize: 11, flex: 1 }}>
                  {testingId === p.id ? <RefreshCw className="spin" size={13} /> : <Activity size={13} />}
                  {testingId === p.id ? 'Testing...' : 'Test'}
                </button>
                <button className="button button-secondary" onClick={() => handleDiscoverModels(p.id)} disabled={discoveringId === p.id} style={{ fontSize: 11 }}>
                  <Compass size={13} />
                </button>
                <button className="button button-secondary" onClick={() => handleOpenEdit(p)} style={{ fontSize: 11 }}>Edit</button>
                <button className="button button-secondary" onClick={() => handleDelete(p.id)} style={{ fontSize: 11, color: 'var(--red)' }}><Trash2 size={13} /></button>
              </div>
            </div>
          )
        })}
      </div>

      {modalOpen && (
        <div className="modal-backdrop" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)', zIndex: 50, display: 'grid', placeItems: 'center' }}>
          <div className="panel" style={{ width: '100%', maxWidth: 520, maxHeight: '90vh', overflowY: 'auto' }}>
            <div className="panel-head">
              <h3>{editingId ? 'Edit AI Provider' : 'Add New AI Provider'}</h3>
              <button className="button-icon" onClick={() => setModalOpen(false)}>×</button>
            </div>
            <form onSubmit={handleSave} style={{ display: 'grid', gap: 14 }}>
              <label className="field-label">
                Provider Type
                <select value={providerType} onChange={(e: any) => setProviderType(e.target.value)}>
                  <option value="gemini">Google Gemini</option>
                  <option value="openai">OpenAI (Official)</option>
                  <option value="claude">Anthropic Claude</option>
                  <option value="openai_compatible">OpenAI-Compatible (Groq, Together, DeepSeek, Ollama)</option>
                  <option value="custom">Custom AI Endpoint</option>
                </select>
              </label>

              <label className="field-label">
                Display Name
                <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required placeholder="e.g. Google Gemini 1.5 Pro" />
              </label>

              <label className="field-label">
                API Key {editingId && <span style={{ color: 'var(--muted)', fontSize: 9 }}>(Leave blank to keep existing key)</span>}
                <input type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder={editingId ? '••••••••' : 'AIza... or sk-...'} />
              </label>

              <label className="field-label">
                Base URL
                <input type="text" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="https://api.openai.com/v1" />
              </label>

              <label className="field-label">
                Default Model
                <input type="text" value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)} placeholder="gemini-1.5-flash, gpt-4o, claude-3-5-sonnet" />
              </label>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <label className="field-label">
                  Priority Order (1 = Highest)
                  <input type="number" min={1} max={100} value={priority} onChange={(e) => setPriority(Number(e.target.value))} />
                </label>
                <label className="field-label" style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 22 }}>
                  <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
                  Enable Provider
                </label>
              </div>

              <label className="field-label">
                Description / Notes
                <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Used for general reasoning and fast tools." />
              </label>

              <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 10 }}>
                <button type="button" className="button button-secondary" onClick={() => setModalOpen(false)}>Cancel</button>
                <button type="submit" className="button button-primary">Save Provider</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function ChatPage(ctx: DashboardContext) {
  const [selectedConversationId, setSelectedConversationId] = useState<string>(() => {
    return ctx.conversations[0]?.id || `conv-${Date.now()}`
  })
  const [inputMessage, setInputMessage] = useState('')
  const [selectedProvider, setSelectedProvider] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [selectedLanguage, setSelectedLanguage] = useState<string>('en')
  const [sending, setSending] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const activeConversation = useMemo(() => {
    return ctx.conversations.find((c) => c.id === selectedConversationId) || {
      id: selectedConversationId,
      title: 'New Conversation',
      created: Date.now(),
      updated: Date.now(),
      messages: [],
    }
  }, [ctx.conversations, selectedConversationId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeConversation.messages])

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!inputMessage.trim() || sending) return

    const userText = inputMessage.trim()
    setInputMessage('')
    setSending(true)

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      body: userText,
      created: Date.now(),
    }

    const updatedMessages = [...activeConversation.messages, userMsg]
    const updatedConv: Conversation = {
      ...activeConversation,
      title: activeConversation.messages.length === 0 ? userText.slice(0, 24) : activeConversation.title,
      updated: Date.now(),
      messages: updatedMessages,
    }

    ctx.setConversations((prev) => {
      const filtered = prev.filter((c) => c.id !== activeConversation.id)
      const next = [updatedConv, ...filtered]
      saveConversations(next)
      return next
    })

    try {
      const resp = await ctx.api.chat(
        userText,
        activeConversation.id,
        selectedProvider || undefined,
        selectedModel || undefined,
        selectedLanguage || undefined,
      )

      const assistantMsg: ChatMessage = {
        id: `msg-${Date.now()}-reply`,
        role: 'assistant',
        body: resp.reply,
        created: Date.now(),
        provider_used: resp.provider_used,
        model_used: resp.model_used,
        fallback_occurred: resp.fallback_occurred,
        requires_confirmation: resp.requires_confirmation,
        confirmation: resp.confirmation,
      }

      ctx.setConversations((prev) => {
        const c = prev.find((item) => item.id === activeConversation.id) || updatedConv
        const next = [
          { ...c, updated: Date.now(), messages: [...c.messages, assistantMsg] },
          ...prev.filter((item) => item.id !== activeConversation.id),
        ]
        saveConversations(next)
        return next
      })

      if (resp.requires_confirmation) {
        await ctx.refreshAll()
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `msg-${Date.now()}-err`,
        role: 'assistant',
        body: `❌ Error: ${err?.message || 'Failed to obtain AI response.'}`,
        created: Date.now(),
      }
      ctx.setConversations((prev) => {
        const c = prev.find((item) => item.id === activeConversation.id) || updatedConv
        const next = [
          { ...c, updated: Date.now(), messages: [...c.messages, errorMsg] },
          ...prev.filter((item) => item.id !== activeConversation.id),
        ]
        saveConversations(next)
        return next
      })
    } finally {
      setSending(false)
    }
  }

  const handleConfirmActionInChat = async (confirmationId: string) => {
    try {
      const res = await ctx.api.confirmAction(confirmationId)
      ctx.showToast(`Action approved! Command queued: ${res.command_id}`, 'success')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Failed to confirm action.', 'error')
    }
  }

  const handleCancelActionInChat = async (confirmationId: string) => {
    try {
      await ctx.api.cancelAction(confirmationId)
      ctx.showToast('Action cancelled.', 'info')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Failed to cancel action.', 'error')
    }
  }

  const handleNewChat = () => {
    const newId = `conv-${Date.now()}`
    const newConv: Conversation = {
      id: newId,
      title: 'New Conversation',
      created: Date.now(),
      updated: Date.now(),
      messages: [],
    }
    ctx.setConversations((prev) => [newConv, ...prev])
    setSelectedConversationId(newId)
  }

  return (
    <div className="chat-layout" style={{ display: 'grid', gridTemplateColumns: '260px 1fr', minHeight: 'calc(100vh - 160px)', border: '1px solid var(--line)', borderRadius: 16, overflow: 'hidden' }}>
      {/* Sidebar of Conversations */}
      <div className="conversation-rail" style={{ background: 'rgba(0,0,0,0.2)', borderRight: '1px solid var(--line)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: 14, borderBottom: '1px solid var(--line)' }}>
          <button className="button button-primary" onClick={handleNewChat} style={{ width: '100%', fontSize: 11 }}>
            <Plus size={14} /> New Chat
          </button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 8 }}>
          {ctx.conversations.map((c) => (
            <div
              key={c.id}
              onClick={() => setSelectedConversationId(c.id)}
              style={{
                padding: '10px 12px',
                borderRadius: 10,
                marginBottom: 4,
                cursor: 'pointer',
                background: c.id === selectedConversationId ? 'rgba(143,116,255,0.18)' : 'transparent',
                border: c.id === selectedConversationId ? '1px solid rgba(143,116,255,0.3)' : '1px solid transparent',
              }}
            >
              <strong style={{ fontSize: 12, display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{c.title || 'Untitled'}</strong>
              <small style={{ color: 'var(--muted)', fontSize: 9 }}>{c.messages.length} messages • {relativeTime(c.updated)}</small>
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div style={{ display: 'flex', flexDirection: 'column', background: 'var(--panel)' }}>
        {/* Top Controls: Provider / Model / Language */}
        <div className="chat-provider-bar">
          <div className="chat-select-group">
            <Brain size={14} />
            <span>Provider:</span>
            <select value={selectedProvider} onChange={(e) => setSelectedProvider(e.target.value)}>
              <option value="">Default (Auto / Fallback)</option>
              {ctx.providers.map((p) => (
                <option key={p.id} value={p.id}>{p.display_name} ({p.provider_type})</option>
              ))}
            </select>
          </div>

          <div className="chat-select-group">
            <span>Model:</span>
            <input
              type="text"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              placeholder="e.g. gemini-1.5-flash / gpt-4o"
              style={{ height: 32, padding: '0 8px', borderRadius: 8, background: 'rgba(255,255,255,0.05)', border: '1px solid var(--line)', color: 'var(--text)', fontSize: 11, width: 140 }}
            />
          </div>

          <div className="chat-select-group">
            <span>Language:</span>
            <select value={selectedLanguage} onChange={(e) => setSelectedLanguage(e.target.value)}>
              <option value="en">English</option>
              <option value="hi">Hindi (हिंदी)</option>
              <option value="hinglish">Indian Hinglish</option>
            </select>
          </div>

          <div className="active-provider-pill">
            <Sparkles size={12} />
            <span>Active: {selectedProvider ? ctx.providers.find((p) => p.id === selectedProvider)?.display_name : 'Default Fallback Router'}</span>
          </div>
        </div>

        {/* Message Stream */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
          {activeConversation.messages.length === 0 ? (
            <div className="empty-state" style={{ margin: 'auto' }}>
              <Bot size={40} />
              <strong>Welcome to PlayzAI V2</strong>
              <p>Ask a question or issue a PC automation command (e.g. "Start OBS", "Check my RAM", "Run PowerShell Get-Process").</p>
            </div>
          ) : (
            activeConversation.messages.map((m) => (
              <div
                key={m.id}
                style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '85%',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                }}
              >
                <div
                  style={{
                    padding: '14px 18px',
                    borderRadius: 14,
                    background: m.role === 'user' ? 'linear-gradient(135deg, #745df0, #4c56db)' : 'rgba(255,255,255,0.04)',
                    border: m.role === 'user' ? 'none' : '1px solid var(--line)',
                    color: '#fff',
                    fontSize: 12,
                    lineHeight: 1.6,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {m.body}

                  {/* Inline Confirmation Card for High Risk Tasks */}
                  {m.requires_confirmation && m.confirmation && (
                    <div className="confirmation-card">
                      <div className="confirmation-header">
                        <AlertOctagon size={16} />
                        <span>OPERATOR CONFIRMATION REQUIRED</span>
                      </div>
                      <div className="confirmation-body">
                        <div><strong>Action:</strong> {m.confirmation.action}</div>
                        {m.confirmation.command && (
                          <code className="confirmation-code">{m.confirmation.command}</code>
                        )}
                        <div><strong>Risk Level:</strong> <RiskBadge level={m.confirmation.risk_level} /></div>
                        <div style={{ marginTop: 4, color: 'var(--muted)' }}>{m.confirmation.risk_explanation}</div>
                      </div>
                      <div className="confirmation-actions">
                        <button className="button button-primary" onClick={() => handleConfirmActionInChat(m.confirmation!.id || m.confirmation!.confirmation_id!)}>
                          <ShieldCheck size={14} /> Confirm & Execute
                        </button>
                        <button className="button button-secondary" onClick={() => handleCancelActionInChat(m.confirmation!.id || m.confirmation!.confirmation_id!)}>
                          <XCircle size={14} /> Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 9, color: 'var(--faint)', padding: '0 4px' }}>
                  <span>{formatTime(m.created)}</span>
                  {m.provider_used && <span>• Provider: {m.provider_used} ({m.model_used})</span>}
                  {m.fallback_occurred && <span style={{ color: 'var(--amber)' }}>• Fallback Active</span>}
                </div>
              </div>
            ))
          )}
          {sending && (
            <div style={{ alignSelf: 'flex-start', padding: '10px 14px', borderRadius: 12, background: 'rgba(255,255,255,0.03)', color: 'var(--muted)', fontSize: 11, display: 'flex', alignItems: 'center', gap: 8 }}>
              <RefreshCw className="spin" size={14} />
              <span>PlayzAI is processing your request...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} style={{ padding: 16, borderTop: '1px solid var(--line)', display: 'flex', gap: 10 }}>
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Type your message or PC command in English, Hindi, or Hinglish..."
            style={{ flex: 1, height: 44, padding: '0 16px', borderRadius: 12, background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line)', color: 'var(--text)', outline: 'none', fontSize: 12 }}
          />
          <button type="submit" className="button button-primary" disabled={sending || !inputMessage.trim()} style={{ height: 44, padding: '0 20px' }}>
            <Send size={15} /> Send
          </button>
        </form>
      </div>
    </div>
  )
}

function PcControlPage(ctx: DashboardContext) {
  const [selectedPcId, setSelectedPcId] = useState<string>(() => ctx.pcs[0]?.device_id || '')
  const [terminalCmd, setTerminalCmd] = useState('')
  const [terminalType, setTerminalType] = useState<'powershell' | 'cmd'>('powershell')
  const [executing, setExecuting] = useState(false)
  const [terminalOutput, setTerminalOutput] = useState<string>('')

  const activePc = ctx.pcs.find((p) => p.device_id === selectedPcId) || ctx.pcs[0]

  const handleQuickApp = async (appName: string) => {
    if (!activePc) {
      ctx.showToast('No PC selected.', 'error')
      return
    }
    try {
      await ctx.api.command(activePc.device_id, 'open_app', { name: appName })
      ctx.showToast(`Launched ${appName} on ${activePc.name}.`, 'success')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Failed to launch app.', 'error')
    }
  }

  const handleObs = async (action: string) => {
    if (!activePc) return
    try {
      await ctx.api.command(activePc.device_id, action, {})
      ctx.showToast(`OBS action '${action}' triggered.`, 'success')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'OBS action failed.', 'error')
    }
  }

  const handleExecuteTerminal = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!terminalCmd.trim() || !activePc || executing) return

    setExecuting(true)
    const action = terminalType === 'powershell' ? 'run_powershell' : 'run_command'
    try {
      const res = await ctx.api.command(activePc.device_id, action, { command: terminalCmd.trim() })
      if (res.requires_confirmation) {
        setTerminalOutput(`⚠️ HIGH-RISK ACTION: This command requires explicit confirmation.\nAction: ${res.action}\nRisk: ${res.risk_level || 'LEVEL 3'}\n${res.risk_explanation || ''}\n\nPlease check Security / Chat to approve.`)
        ctx.showToast('Confirmation required before execution.', 'info')
      } else {
        setTerminalOutput(`[QUEUED] Command assigned ID: ${res.command_id}\nWaiting for PC Agent result...`)
        ctx.showToast('Command dispatched to PC Agent.', 'success')
      }
      await ctx.refreshAll()
    } catch (err: any) {
      setTerminalOutput(`❌ Execution Error: ${err?.message}`)
      ctx.showToast(err?.message || 'Execution failed.', 'error')
    } finally {
      setExecuting(false)
    }
  }

  return (
    <div>
      <div className="section-title">
        <div>
          <div className="eyebrow"><Monitor size={13} /> WINDOWS PC AUTOMATION</div>
          <h1>Advanced PC Control & Automation</h1>
          <p>Real-time hardware telemetry, application launching, OBS/Minecraft controls, and secure PowerShell/CMD task execution.</p>
        </div>
      </div>

      {/* Target PC Selector */}
      <div className="panel" style={{ marginBottom: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <Monitor size={24} className="text-violet" />
            <div>
              <strong>Target PC: {activePc?.name || 'None'}</strong>
              <small style={{ display: 'block', color: 'var(--muted)' }}>Device ID: {activePc?.device_id || 'Not selected'} • Status: {activePc?.status || 'Unknown'}</small>
            </div>
          </div>
          <select value={selectedPcId} onChange={(e) => setSelectedPcId(e.target.value)} style={{ padding: '8px 14px', borderRadius: 10, background: 'rgba(255,255,255,0.05)', color: 'var(--text)', border: '1px solid var(--line)' }}>
            {ctx.pcs.map((p) => (
              <option key={p.id} value={p.device_id}>{p.name} ({p.device_id})</option>
            ))}
          </select>
        </div>
      </div>

      {/* PC Telemetry Gauges */}
      <div className="stats-grid">
        <StatCard label="CPU Utilization" value={activePc?.cpu_percent != null ? `${activePc.cpu_percent}%` : 'N/A'} icon={Cpu} tone="violet" />
        <StatCard label="RAM Utilization" value={activePc?.ram_percent != null ? `${activePc.ram_percent}%` : 'N/A'} icon={Activity} tone="blue" />
        <StatCard label="Storage Utilization" value={activePc?.storage_percent != null ? `${activePc.storage_percent}%` : 'N/A'} icon={HardDrive} tone="green" />
        <StatCard label="Network Diagnostics" value={activePc?.network_status || 'online'} icon={Wifi} tone="amber" />
      </div>

      {/* Quick Launch & Control Grids */}
      <div className="overview-grid">
        {/* Apps Launcher */}
        <div className="panel">
          <div className="panel-head">
            <h3>Quick Application Launcher</h3>
            <span style={{ fontSize: 10, color: 'var(--muted)' }}>Allowlisted PC Executables</span>
          </div>
          <div className="quick-app-grid">
            <button type="button" className="quick-app-btn" onClick={() => handleQuickApp('notepad')}><Terminal size={18} /><span>Notepad</span></button>
            <button type="button" className="quick-app-btn" onClick={() => handleQuickApp('chrome')}><Compass size={18} /><span>Chrome</span></button>
            <button type="button" className="quick-app-btn" onClick={() => handleQuickApp('vscode')}><Terminal size={18} /><span>VS Code</span></button>
            <button type="button" className="quick-app-btn" onClick={() => handleQuickApp('obs')}><Video size={18} /><span>OBS Studio</span></button>
            <button type="button" className="quick-app-btn" onClick={() => handleQuickApp('minecraft')}><Gamepad2 size={18} /><span>Minecraft</span></button>
            <button type="button" className="quick-app-btn" onClick={() => handleQuickApp('taskmgr')}><Activity size={18} /><span>Task Manager</span></button>
            <button type="button" className="quick-app-btn" onClick={() => handleQuickApp('explorer')}><HardDrive size={18} /><span>Explorer</span></button>
            <button type="button" className="quick-app-btn" onClick={() => handleQuickApp('calc')}><Cpu size={18} /><span>Calculator</span></button>
          </div>
        </div>

        {/* OBS & Minecraft Controllers */}
        <div className="panel">
          <div className="panel-head">
            <h3>OBS & Stream Management</h3>
            <span style={{ fontSize: 10, color: 'var(--muted)' }}>Studio Automation</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <button className="button button-secondary" onClick={() => handleObs('obs_record_start')}><Video size={14} /> Start Recording</button>
            <button className="button button-secondary" onClick={() => handleObs('obs_record_stop')}><Video size={14} /> Stop Recording</button>
            <button className="button button-secondary" onClick={() => handleObs('obs_start')}><Flame size={14} /> Start Stream</button>
            <button className="button button-secondary" onClick={() => handleObs('obs_stop')}><Flame size={14} /> Stop Stream</button>
          </div>
          <div style={{ marginTop: 20, paddingTop: 14, borderTop: '1px solid var(--line)' }}>
            <h4>Minecraft Control</h4>
            <div style={{ display: 'flex', gap: 10, marginTop: 10 }}>
              <button className="button button-secondary" onClick={() => handleObs('minecraft_start')}><Gamepad2 size={14} /> Start Server</button>
              <button className="button button-secondary" onClick={() => handleObs('minecraft_stop')}><Gamepad2 size={14} /> Stop Server</button>
            </div>
          </div>
        </div>
      </div>

      {/* Terminal & Script Execution Runner */}
      <div className="panel">
        <div className="panel-head">
          <div>
            <h3>PowerShell & CMD Execution Runner</h3>
            <p>Direct system automation with automatic risk classification and zero-trust safeguards.</p>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className={`button ${terminalType === 'powershell' ? 'button-primary' : 'button-secondary'}`} onClick={() => setTerminalType('powershell')} style={{ fontSize: 11 }}>PowerShell</button>
            <button className={`button ${terminalType === 'cmd' ? 'button-primary' : 'button-secondary'}`} onClick={() => setTerminalType('cmd')} style={{ fontSize: 11 }}>CMD</button>
          </div>
        </div>

        <form onSubmit={handleExecuteTerminal} style={{ display: 'grid', gap: 10 }}>
          <div style={{ display: 'flex', gap: 10 }}>
            <input
              type="text"
              value={terminalCmd}
              onChange={(e) => setTerminalCmd(e.target.value)}
              placeholder={terminalType === 'powershell' ? 'Get-Process | Sort-Object CPU -Descending | Select-Object -First 5' : 'systeminfo'}
              style={{ flex: 1, height: 42, padding: '0 14px', borderRadius: 10, background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line)', color: 'var(--text)', fontFamily: 'monospace', fontSize: 12 }}
            />
            <button type="submit" className="button button-primary" disabled={executing || !terminalCmd.trim()}>
              {executing ? <RefreshCw className="spin" size={14} /> : <Play size={14} />} Execute
            </button>
          </div>
        </form>

        {terminalOutput && (
          <div className="terminal-box">
            {terminalOutput}
          </div>
        )}
      </div>
    </div>
  )
}

function SecurityPage(ctx: DashboardContext) {
  const [masterKey, setMasterKey] = useState('')
  const [processing, setProcessing] = useState(false)

  const handleConfirm = async (id: string) => {
    try {
      const res = await ctx.api.confirmAction(id)
      ctx.showToast(`Action approved. Queued as command: ${res.command_id}`, 'success')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Failed to approve.', 'error')
    }
  }

  const handleCancel = async (id: string) => {
    try {
      await ctx.api.cancelAction(id)
      ctx.showToast('Confirmation cancelled.', 'info')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Failed to cancel.', 'error')
    }
  }

  const handleLockdown = async () => {
    if (!masterKey) {
      ctx.showToast('Owner master key required for lockdown.', 'error')
      return
    }
    setProcessing(true)
    try {
      await ctx.api.lockdown(masterKey)
      ctx.showToast('System lockdown engaged.', 'success')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Lockdown failed.', 'error')
    } finally {
      setProcessing(false)
    }
  }

  const handleUnlock = async () => {
    if (!masterKey) {
      ctx.showToast('Owner master key required to unlock.', 'error')
      return
    }
    setProcessing(true)
    try {
      await ctx.api.unlock(masterKey)
      ctx.showToast('System unlocked.', 'success')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Unlock failed.', 'error')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div>
      <div className="section-title">
        <div>
          <div className="eyebrow"><Shield size={13} /> SECURITY CENTER</div>
          <h1>Zero-Trust Safeguards & Confirmations</h1>
          <p>Real-time confirmation queue for Level 3 high-risk operations, master-key privileged lockdown, and device revocation.</p>
        </div>
      </div>

      {/* Pending Confirmations Queue */}
      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="panel-head">
          <div>
            <h3>Pending High-Risk Operations ({ctx.pendingConfirmations.length})</h3>
            <p>These actions require explicit operator sign-off before execution.</p>
          </div>
        </div>

        {ctx.pendingConfirmations.length === 0 ? (
          <div className="empty-state">
            <ShieldCheck size={36} />
            <strong>No Pending Confirmations</strong>
            <p>All system actions are currently authorized or safe.</p>
          </div>
        ) : (
          <div>
            {ctx.pendingConfirmations.map((conf) => (
              <div key={conf.id} className="confirmation-card" style={{ marginBottom: 12 }}>
                <div className="confirmation-header">
                  <AlertOctagon size={18} />
                  <span>ACTION AUTHORIZATION REQUEST #{conf.id}</span>
                </div>
                <div className="confirmation-body">
                  <div><strong>Action:</strong> {conf.action}</div>
                  {conf.command && <code className="confirmation-code">{conf.command}</code>}
                  <div><strong>Risk Level:</strong> <RiskBadge level={conf.risk_level} /></div>
                  <div style={{ marginTop: 4, color: 'var(--muted)' }}>{conf.risk_explanation}</div>
                  <small style={{ display: 'block', marginTop: 6, color: 'var(--faint)' }}>Expires in {relativeTime(conf.expires_at)}</small>
                </div>
                <div className="confirmation-actions">
                  <button className="button button-primary" onClick={() => handleConfirm(conf.id)}>
                    <ShieldCheck size={14} /> Confirm & Run
                  </button>
                  <button className="button button-secondary" onClick={() => handleCancel(conf.id)}>
                    <XCircle size={14} /> Reject & Cancel
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Master Key Emergency Controls */}
      <div className="panel">
        <div className="panel-head">
          <div>
            <h3>Emergency Lockdown Controls</h3>
            <p>Revokes all active sessions and blocks non-master commands instantly.</p>
          </div>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'center' }}>
          <input
            type="password"
            value={masterKey}
            onChange={(e) => setMasterKey(e.target.value)}
            placeholder="Enter Owner Master Key..."
            style={{ width: 280, height: 40, padding: '0 12px', borderRadius: 10, background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line)', color: 'var(--text)' }}
          />
          <button className="button button-danger" onClick={handleLockdown} disabled={processing}>
            <Lock size={14} /> Engage Lockdown
          </button>
          <button className="button button-secondary" onClick={handleUnlock} disabled={processing}>
            <Unlock size={14} /> Lift Lockdown
          </button>
        </div>
      </div>
    </div>
  )
}

function DevicesPage(ctx: DashboardContext) {
  const [pcName, setPcName] = useState('My Windows PC')
  const [pairingCode, setPairingCode] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)

  const handleGeneratePairing = async (e: React.FormEvent) => {
    e.preventDefault()
    setGenerating(true)
    try {
      const res = await ctx.api.pairingCode(pcName)
      setPairingCode(res.pairing_code)
      ctx.showToast(`Pairing code generated: ${res.pairing_code}`, 'success')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Failed to generate code.', 'error')
    } finally {
      setGenerating(false)
    }
  }

  const handleWake = async (pcId: string) => {
    try {
      await ctx.api.wakePc(pcId, true)
      ctx.showToast('Wake-on-LAN magic packet sent.', 'success')
    } catch (err: any) {
      ctx.showToast(err?.message || 'Wake-on-LAN failed.', 'error')
    }
  }

  return (
    <div>
      <div className="section-title">
        <div>
          <div className="eyebrow"><Smartphone size={13} /> DEVICE ECOSYSTEM</div>
          <h1>Registered Devices & Agent Pairing</h1>
          <p>Enroll Windows PCs and Android devices securely with short-lived pairing tokens.</p>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="panel-head">
          <div>
            <h3>Pair New Windows Agent</h3>
            <p>Generate a 6-digit one-time code to link the Windows Agent.</p>
          </div>
        </div>
        <form onSubmit={handleGeneratePairing} style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="text"
            value={pcName}
            onChange={(e) => setPcName(e.target.value)}
            placeholder="PC Name (e.g. Living Room PC)"
            style={{ width: 260, height: 40, padding: '0 12px', borderRadius: 10, background: 'rgba(255,255,255,0.04)', border: '1px solid var(--line)', color: 'var(--text)' }}
          />
          <button type="submit" className="button button-primary" disabled={generating}>
            {generating ? <RefreshCw className="spin" size={14} /> : <Key size={14} />} Generate Pairing Code
          </button>
        </form>

        {pairingCode && (
          <div style={{ marginTop: 14, padding: 14, borderRadius: 12, background: 'rgba(143,116,255,0.12)', border: '1px solid rgba(143,116,255,0.3)', display: 'flex', alignItems: 'center', gap: 12 }}>
            <Key size={20} className="text-violet" />
            <div>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>Enter this code in your Windows Agent setup:</span>
              <strong style={{ display: 'block', fontSize: 20, letterSpacing: '0.15em', color: '#a895ff' }}>{pairingCode}</strong>
            </div>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-head">
          <h3>Enrolled Devices ({ctx.devices.length})</h3>
        </div>
        <div style={{ display: 'grid', gap: 12 }}>
          {ctx.devices.map((d) => (
            <div key={d.device_id} className="health-row">
              <div className="health-icon">{d.kind === 'pc' ? <Monitor size={18} /> : <Smartphone size={18} />}</div>
              <div className="health-copy">
                <strong>{d.name}</strong>
                <span>ID: {d.device_id} • Kind: {d.kind?.toUpperCase()} • Last seen: {relativeTime(d.last_seen)}</span>
              </div>
              <StatusPill value={d.status} />
              {d.kind === 'pc' && (
                <button className="button button-secondary" onClick={() => handleWake(d.device_id)} style={{ fontSize: 10 }}>
                  <Power size={12} /> Wake
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function AuditPage(ctx: DashboardContext) {
  const [filterRisk, setFilterRisk] = useState<string>('ALL')

  const filteredLogs = useMemo(() => {
    if (filterRisk === 'ALL') return ctx.auditLogs
    return ctx.auditLogs.filter((l) => l.risk_level.includes(filterRisk))
  }, [ctx.auditLogs, filterRisk])

  return (
    <div>
      <div className="section-title">
        <div>
          <div className="eyebrow"><ShieldAlert size={13} /> COMPLIANCE & SECURITY</div>
          <h1>Immutable Audit Trail</h1>
          <p>Cryptographically sanitized logs recording all AI tool calls, PC commands, exit codes, and operator confirmations. No secrets logged.</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <select value={filterRisk} onChange={(e) => setFilterRisk(e.target.value)} style={{ height: 36, padding: '0 12px', borderRadius: 8, background: 'rgba(255,255,255,0.05)', color: 'var(--text)', border: '1px solid var(--line)' }}>
            <option value="ALL">All Risk Levels</option>
            <option value="SAFE">Level 1 Safe Only</option>
            <option value="MODERATE">Level 2 Moderate Only</option>
            <option value="HIGH">Level 3 High Risk Only</option>
          </select>
        </div>
      </div>

      <div className="panel">
        {filteredLogs.length === 0 ? (
          <div className="empty-state">
            <Clock size={32} />
            <strong>No Audit Logs Found</strong>
            <p>Audit events appear as AI and PC automation commands are executed.</p>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: 8 }}>
            {filteredLogs.map((log) => (
              <div
                key={log.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '120px 180px 1fr 140px 100px',
                  alignItems: 'center',
                  gap: 12,
                  padding: '12px 14px',
                  borderRadius: 10,
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid var(--line)',
                  fontSize: 11,
                }}
              >
                <div style={{ color: 'var(--muted)', fontSize: 10 }}>{formatTime(log.timestamp)}</div>
                <div>
                  <strong>{log.action}</strong>
                  <small style={{ display: 'block', color: 'var(--muted)', fontSize: 9 }}>User: {log.user_id || 'System'}</small>
                </div>
                <div>
                  {log.command && <code style={{ fontSize: 10, padding: '2px 6px', background: 'rgba(0,0,0,0.3)', borderRadius: 4, display: 'inline-block', maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}>{log.command}</code>}
                  {log.detail && <span style={{ display: 'block', color: 'var(--muted)', fontSize: 9, marginTop: 2 }}>{log.detail}</span>}
                </div>
                <div>
                  <RiskBadge level={log.risk_level} />
                </div>
                <div>
                  <StatusPill value={log.result === 'SUCCESS' ? 'online' : 'danger'} label={log.result} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function SettingsPage(ctx: DashboardContext & { theme: string; setTheme: (t: 'dark' | 'light') => void }) {
  const [defaultProvider, setDefaultProvider] = useState(ctx.aiSettings.default_provider || 'gemini')
  const [defaultModel, setDefaultModel] = useState(ctx.aiSettings.default_model || 'gemini-1.5-flash')
  const [fallbackEnabled, setFallbackEnabled] = useState(ctx.aiSettings.fallback_enabled !== 'false')
  const [pcControlEnabled, setPcControlEnabled] = useState(ctx.aiSettings.pc_control_enabled !== 'false')
  const [voiceGender, setVoiceGender] = useState('DEFAULT')
  const [speechRate, setSpeechRate] = useState(1.0)
  const [speechPitch, setSpeechPitch] = useState(1.0)
  const [saving, setSaving] = useState(false)

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await ctx.api.updateAiSettings({
        default_provider: defaultProvider,
        default_model: defaultModel,
        fallback_enabled: String(fallbackEnabled),
        pc_control_enabled: String(pcControlEnabled),
      })
      ctx.showToast('Settings saved successfully.', 'success')
      await ctx.refreshAll()
    } catch (err: any) {
      ctx.showToast(err?.message || 'Failed to save settings.', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleTestVoice = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      const u = new SpeechSynthesisUtterance("Namaste! I am PlayzAI, your multi-AI companion.")
      u.rate = speechRate
      u.pitch = speechPitch
      window.speechSynthesis.speak(u)
      ctx.showToast('Playing voice preview...', 'info')
    } else {
      ctx.showToast('Browser SpeechSynthesis is not supported on this device.', 'error')
    }
  }

  return (
    <div>
      <div className="section-title">
        <div>
          <div className="eyebrow"><Settings size={13} /> SYSTEM PREFERENCES</div>
          <h1>PlayzAI Settings & Voice Config</h1>
          <p>Configure multi-AI defaults, fallback priority, voice synthesizer settings, and automation parameters.</p>
        </div>
      </div>

      <form onSubmit={handleSaveSettings} style={{ display: 'grid', gap: 18 }}>
        <div className="panel">
          <div className="panel-head">
            <h3>Multi-AI & Fallback Engine</h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <label className="field-label">
              Default AI Provider
              <select value={defaultProvider} onChange={(e) => setDefaultProvider(e.target.value)}>
                {ctx.providers.map((p) => (
                  <option key={p.id} value={p.id}>{p.display_name} ({p.provider_type})</option>
                ))}
              </select>
            </label>
            <label className="field-label">
              Default Model
              <input type="text" value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)} placeholder="gemini-1.5-flash" />
            </label>
          </div>
          <div style={{ marginTop: 14, display: 'flex', gap: 20 }}>
            <label className="check-label">
              <input type="checkbox" checked={fallbackEnabled} onChange={(e) => setFallbackEnabled(e.target.checked)} />
              Enable automatic fallback to secondary providers on rate-limits/timeouts
            </label>
            <label className="check-label">
              <input type="checkbox" checked={pcControlEnabled} onChange={(e) => setPcControlEnabled(e.target.checked)} />
              Enable Natural Language PC Control
            </label>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h3>Voice Synthesizer (TTS) & Language</h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
            <label className="field-label">
              Voice Gender Selection
              <select value={voiceGender} onChange={(e) => setVoiceGender(e.target.value)}>
                <option value="DEFAULT">Default / System</option>
                <option value="MALE">Male Voice</option>
                <option value="FEMALE">Female Voice</option>
              </select>
            </label>
            <label className="field-label">
              Speech Rate: {speechRate}x
              <input type="range" min="0.5" max="2.0" step="0.1" value={speechRate} onChange={(e) => setSpeechRate(parseFloat(e.target.value))} />
            </label>
            <label className="field-label">
              Speech Pitch: {speechPitch}x
              <input type="range" min="0.5" max="2.0" step="0.1" value={speechPitch} onChange={(e) => setSpeechPitch(parseFloat(e.target.value))} />
            </label>
          </div>
          <div style={{ marginTop: 14 }}>
            <button type="button" className="button button-secondary" onClick={handleTestVoice}>
              <Volume2 size={14} /> Test Voice Synthesis
            </button>
          </div>
        </div>

        <div>
          <button type="submit" className="button button-primary" disabled={saving}>
            {saving ? <RefreshCw className="spin" size={14} /> : <CheckCircle2 size={14} />} Save Settings
          </button>
        </div>
      </form>
    </div>
  )
}

function AboutPage() {
  return (
    <div>
      <div className="section-title">
        <div>
          <div className="eyebrow"><Bot size={13} /> ABOUT PLAYZAI V2</div>
          <h1>Architectural Principles</h1>
          <p>PlayzAI V2 is an authentic multi-provider AI assistant with native Windows PC automation and cryptographic zero-trust controls.</p>
        </div>
      </div>

      <div className="principles-grid">
        <div className="principle">
          <div className="principle-icon"><Brain size={18} /></div>
          <strong>Authentic Multi-AI</strong>
          <p>Direct Google Gemini REST, OpenAI Chat Completions, and Claude Messages protocols with truthful model discovery and graceful fallback.</p>
        </div>
        <div className="principle">
          <div className="principle-icon"><Shield size={18} /></div>
          <strong>Zero-Trust Risk Engine</strong>
          <p>Every PC command is categorized as Level 1 Safe, Level 2 Moderate, or Level 3 High-Risk. Destructive actions strictly require human confirmation.</p>
        </div>
        <div className="principle">
          <div className="principle-icon"><Lock size={18} /></div>
          <strong>Secret Protection</strong>
          <p>API keys and credentials live exclusively in the backend database and are never leaked to client APKs, frontends, or audit logs.</p>
        </div>
      </div>
    </div>
  )
}

// Top-level Dashboard Layout
function Dashboard({ auth, onLogout }: { auth: AuthState; onLogout: () => void }) {
  const [activePage, setActivePage] = useState<PageKey>('overview')
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [toast, setToast] = useState<{ text: string; kind: 'success' | 'error' | 'info' } | null>(null)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const [health, setHealth] = useState<Health | null>(null)
  const [devices, setDevices] = useState<Device[]>([])
  const [pcs, setPcs] = useState<Pc[]>([])
  const [securityEvents, setSecurityEvents] = useState<SecurityEvent[]>([])
  const [commands, setCommands] = useState<Command[]>([])
  const [whatsapp, setWhatsapp] = useState<WhatsAppStatus | null>(null)
  const [providers, setProviders] = useState<AiProviderConfig[]>([])
  const [models, setModels] = useState<AiModelConfig[]>([])
  const [aiSettings, setAiSettings] = useState<Record<string, string>>({})
  const [pendingConfirmations, setPendingConfirmations] = useState<ConfirmationRecord[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [conversations, setConversations] = useState<Conversation[]>(readConversations)
  const [realtime, setRealtime] = useState<RealtimeState>({ connected: false })

  const api = useMemo(() => new PlayzApi(auth), [auth])

  const showToast = useCallback((text: string, kind: 'success' | 'error' | 'info' = 'info') => {
    setToast({ text, kind })
  }, [])

  const refreshAll = useCallback(async () => {
    try {
      const [h, dev, pcList, evs, cmds, wa, provs, mdls, stg, confs, logs] = await Promise.all([
        api.health().catch(() => null),
        api.devices().then((r) => r.devices).catch(() => []),
        api.pcs().then((r) => r.pcs).catch(() => []),
        api.securityEvents().then((r) => r.events).catch(() => []),
        api.commands().then((r) => r.commands).catch(() => []),
        api.whatsappStatus().catch(() => null),
        api.providers().then((r) => r.providers).catch(() => []),
        api.models().then((r) => r.models).catch(() => []),
        api.aiSettings().then((r) => r.settings).catch(() => ({})),
        api.pendingConfirmations().then((r) => r.confirmations).catch(() => []),
        api.auditLogs().then((r) => r.audit_logs).catch(() => []),
      ])

      setHealth(h)
      setDevices(dev)
      setPcs(pcList)
      setSecurityEvents(evs)
      setCommands(cmds)
      setWhatsapp(wa)
      setProviders(provs)
      setModels(mdls)
      setAiSettings(stg)
      setPendingConfirmations(confs)
      setAuditLogs(logs)
    } catch {
      // Background refresh errors handled gracefully
    }
  }, [api])

  useEffect(() => {
    refreshAll()
    const timer = setInterval(refreshAll, 10_000)
    return () => clearInterval(timer)
  }, [refreshAll])

  // WebSocket Connection
  useEffect(() => {
    let ws: WebSocket | null = null
    try {
      ws = new WebSocket(api.websocketUrl())
      ws.onopen = () => setRealtime((prev) => ({ ...prev, connected: true }))
      ws.onclose = () => setRealtime((prev) => ({ ...prev, connected: false }))
      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          setRealtime((prev) => ({ ...prev, lastMessage: data.type }))
          if (data.type === 'connected' || data.type === 'status') refreshAll()
          // eslint-disable-next-line no-empty
        } catch {}
      }
      // eslint-disable-next-line no-empty
    } catch {}
    return () => {
      ws?.close()
    }
  }, [api, refreshAll])

  const contextValue: DashboardContext = {
    api,
    auth,
    health,
    devices,
    pcs,
    securityEvents,
    commands,
    whatsapp,
    providers,
    models,
    aiSettings,
    pendingConfirmations,
    auditLogs,
    conversations,
    setConversations,
    realtime,
    activePage,
    go: (p) => {
      setActivePage(p)
      setMobileMenuOpen(false)
    },
    showToast,
    refreshAll,
  }

  return (
    <div className="app-shell" data-theme={theme}>
      {toast && <Toast message={toast} onClose={() => setToast(null)} />}

      {/* Sidebar */}
      <aside className={`sidebar ${mobileMenuOpen ? 'open' : ''}`}>
        <div style={{ padding: '24px 20px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="brand-badge"><Bot size={20} /></div>
          <div>
            <strong style={{ fontSize: 16 }}>PlayzAI <span style={{ color: '#8569ff' }}>V2</span></strong>
            <small style={{ display: 'block', fontSize: 9, color: 'var(--muted)' }}>Multi-AI Control Hub</small>
          </div>
        </div>

        <nav style={{ flex: 1, padding: '0 12px' }}>
          <div className="nav-group">WORKSPACE</div>
          <button className={`nav-item ${activePage === 'overview' ? 'active' : ''}`} onClick={() => contextValue.go('overview')}><Layers size={16} /> Overview</button>
          <button className={`nav-item ${activePage === 'chat' ? 'active' : ''}`} onClick={() => contextValue.go('chat')}><MessageSquare size={16} /> AI Chat</button>
          <button className={`nav-item ${activePage === 'providers' ? 'active' : ''}`} onClick={() => contextValue.go('providers')}><Brain size={16} /> AI Providers & Models</button>
          <button className={`nav-item ${activePage === 'pc' ? 'active' : ''}`} onClick={() => contextValue.go('pc')}><Monitor size={16} /> PC Automation</button>

          <div className="nav-group">INFRASTRUCTURE</div>
          <button className={`nav-item ${activePage === 'devices' ? 'active' : ''}`} onClick={() => contextValue.go('devices')}><Smartphone size={16} /> Devices & Pairing</button>
          <button className={`nav-item ${activePage === 'security' ? 'active' : ''}`} onClick={() => contextValue.go('security')}>
            <Shield size={16} /> Security Center
            {pendingConfirmations.length > 0 && <span className="nav-alert" />}
          </button>
          <button className={`nav-item ${activePage === 'audit' ? 'active' : ''}`} onClick={() => contextValue.go('audit')}><Clock size={16} /> Audit Trail</button>

          <div className="nav-group">SYSTEM</div>
          <button className={`nav-item ${activePage === 'settings' ? 'active' : ''}`} onClick={() => contextValue.go('settings')}><Settings size={16} /> Settings</button>
          <button className={`nav-item ${activePage === 'about' ? 'active' : ''}`} onClick={() => contextValue.go('about')}><CircleHelp size={16} /> About PlayzAI</button>
        </nav>

        <div className="sidebar-bottom" style={{ padding: 12 }}>
          <div className="connection-mini">
            <span className={`connection-dot ${realtime.connected ? 'online' : 'offline'}`} />
            <div>
              <strong>{realtime.connected ? 'Realtime Connected' : 'Polling Backend'}</strong>
              <small>{auth.deviceId}</small>
            </div>
          </div>
          <button className="button button-secondary" onClick={onLogout} style={{ width: '100%', fontSize: 11 }}>Log Out</button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-area">
        <header className="topbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <strong style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{activePage.replace('_', ' ')}</strong>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button className="button-icon" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <button className="button button-secondary" onClick={refreshAll} style={{ fontSize: 11 }}>
              <RefreshCw size={13} /> Refresh
            </button>
          </div>
        </header>

        <div className="page-wrap">
          {activePage === 'overview' && <OverviewPage {...contextValue} />}
          {activePage === 'providers' && <AIProvidersPage {...contextValue} />}
          {activePage === 'chat' && <ChatPage {...contextValue} />}
          {activePage === 'pc' && <PcControlPage {...contextValue} />}
          {activePage === 'devices' && <DevicesPage {...contextValue} />}
          {activePage === 'security' && <SecurityPage {...contextValue} />}
          {activePage === 'audit' && <AuditPage {...contextValue} />}
          {activePage === 'settings' && <SettingsPage {...contextValue} theme={theme} setTheme={setTheme} />}
          {activePage === 'about' && <AboutPage />}
        </div>
      </main>
    </div>
  )
}

export default function App() {
  const [auth, setAuth] = useState<AuthState | null>(readSavedAuth)

  if (!auth) {
    return <AuthScreen onAuthenticated={(a) => setAuth(a)} />
  }

  return <Dashboard auth={auth} onLogout={() => { saveAuth(null); setAuth(null) }} />
}
