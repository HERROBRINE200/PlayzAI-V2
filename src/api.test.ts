import { describe, expect, it, vi } from 'vitest'
import { defaultApiBaseUrl, normalizeBaseUrl, PlayzApi } from './api'
import type { AuthState } from './types'

describe('PlayzApi URL and helper utils', () => {
  it('normalizes base urls correctly', () => {
    expect(normalizeBaseUrl('http://localhost:8000/')).toBe('http://localhost:8000')
    expect(normalizeBaseUrl('https://example.com///')).toBe('https://example.com')
  })

  it('exposes default base url', () => {
    expect(typeof defaultApiBaseUrl()).toBe('string')
  })
})

describe('PlayzApi Multi-AI & PC Control client methods', () => {
  const auth: AuthState = {
    baseUrl: 'http://127.0.0.1:8000',
    deviceId: 'admin-tester',
    apiKey: 'plz_test_key_123',
    sessionToken: 'sess_test_token_456',
  }

  it('generates authenticated headers with session token', () => {
    const api = new PlayzApi(auth)
    const wsUrl = api.websocketUrl()
    expect(wsUrl).toContain('ws://127.0.0.1:8000/ws')
    expect(wsUrl).toContain('device_id=admin-tester')
    expect(wsUrl).toContain('session_token=sess_test_token_456')
  })

  it('invokes provider list and confirmation methods', async () => {
    const api = new PlayzApi(auth)

    // Mock global fetch
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/api/ai/providers')) {
        return Promise.resolve({
          ok: true,
          text: () =>
            Promise.resolve(
              JSON.stringify({
                providers: [
                  {
                    id: 'prov_gemini',
                    provider_type: 'gemini',
                    display_name: 'Google Gemini',
                    enabled: true,
                    priority: 1,
                  },
                ],
              }),
            ),
        } as Response)
      }
      if (url.includes('/api/security/confirmations/pending')) {
        return Promise.resolve({
          ok: true,
          text: () =>
            Promise.resolve(
              JSON.stringify({
                confirmations: [
                  {
                    id: 'conf-123',
                    action: 'delete_file',
                    risk_level: 'LEVEL 3 — HIGH RISK / HEAVY',
                    risk_explanation: 'Delete file',
                    created_at: 100,
                    expires_at: 500,
                    status: 'pending',
                  },
                ],
              }),
            ),
        } as Response)
      }
      return Promise.resolve({
        ok: true,
        text: () => Promise.resolve(JSON.stringify({ ok: true })),
      } as Response)
    })

    const provRes = await api.providers()
    expect(provRes.providers.length).toBe(1)
    expect(provRes.providers[0].display_name).toBe('Google Gemini')

    const confRes = await api.pendingConfirmations()
    expect(confRes.confirmations.length).toBe(1)
    expect(confRes.confirmations[0].id).toBe('conf-123')
  })
})
