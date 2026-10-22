import type { BiliUser, CommandGroup, DutySnapshot, Meta, RunResult, SeenPayload, SettingsState } from './types'

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  const text = await res.text()
  let body: unknown = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    body = null
  }
  if (!res.ok) {
    const detail =
      (body as { detail?: string; error?: string } | null)?.detail ||
      (body as { error?: string } | null)?.error ||
      text.slice(0, 200)
    throw new Error(detail || `HTTP ${res.status}`)
  }
  return body as T
}

export const api = {
  catalog: () => http<{ groups: CommandGroup[] }>('/api/catalog'),

  meta: () => http<Meta>('/api/meta'),

  run: (argv: string[]) =>
    http<RunResult>('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ argv }),
    }),

  login: () => http<RunResult>('/api/login', { method: 'POST' }),

  cancelLogin: () =>
    http<{ moved: string | null; status: { ok: boolean; data?: { user?: BiliUser } } }>(
      '/api/cancel-login',
      { method: 'POST' },
    ),

  settings: () => http<SettingsState>('/api/settings'),

  saveSettings: (body: {
    workspace: string
    agents_md: string
    api_key: string
    sync_plugin: boolean
  }) =>
    http<{ ok: boolean; notes: string[]; state: SettingsState }>('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  duty: () => http<DutySnapshot>('/api/agent'),

  selfcheck: () =>
    http<{ ok: boolean; version: string | null; advice: string; checks: { name: string; ok: boolean; detail: string; hint: string }[] }>(
      '/api/selfcheck',
    ),

  saveDuty: (patch: Partial<DutySnapshot['config']> & { keywords?: string[] }) =>
    http<{ ok: boolean; notes: string[]; agent: DutySnapshot }>('/api/agent/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    }),

  resetDuty: () =>
    http<{ ok: boolean; archived: string | null; state: DutySnapshot }>('/api/agent/reset', {
      method: 'POST',
    }),

  runAgent: () =>
    http<{ ok: boolean; code: number; log: string; seconds: number; picked: number }>('/api/agent/run', {
      method: 'POST',
    }),

  seen: () => http<SeenPayload>('/api/agent/seen'),

  postDynamic: (body: { text: string; images: string[]; at: string[]; dry_run: boolean }) =>
    http<RunResult>('/api/duty/dynamic', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  dutyReport: () =>
    http<{ day: string; path: string; exists: boolean; picks: number; text: string }>(
      '/api/agent/report',
    ),

  coverUrl: (bvid: string) => `/api/cover?bvid=${encodeURIComponent(bvid)}`,
  imgUrl: (path: string) => `/api/img?p=${encodeURIComponent(path)}`,
  proxyUrl: (url: string) => `/api/proxy?u=${encodeURIComponent(url)}`,
}
