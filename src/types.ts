export interface Param {
  key: string
  label: string
  pos: boolean
  flag: string | null
  type: 'text' | 'int' | 'select' | 'bool' | string
  default: string
  choices: string[]
  ph: string
}

export interface CommandItem {
  id: string
  label: string
  argv: string[]
  write?: boolean
  kind?: string
  params?: Param[]
}

export interface CommandGroup {
  group: string
  items: CommandItem[]
}

export interface BiliUser {
  mid: number
  name: string
  level?: number
}

export interface Meta {
  version: string | null
  auth: { ok: boolean; user: BiliUser | null; error?: unknown }
  owner: { mid: number; name: string } | null
  bili: string
}

export interface RunResult {
  code: number | null
  json: {
    ok: boolean
    data?: unknown
    error?: { code: string; message: string; hint?: string }
  } | null
  stdout: string
  stderr: string
  elapsed: number
  argv: string[]
}

export interface SettingsState {
  workspace: string
  workspace_default: string
  agents_path: string
  agents_md: string
  api_key_set: boolean
  api_key_mask: string
  api_key_in_env: boolean
  duty_home: string
}
export interface DutyConfig {
  perDay: number
  peakValley: boolean
  noon: boolean
  night: boolean
  autoComment: boolean
  dmMode: 'off' | 'only' | 'both'
  dmUid: number
  reportLevel: 'full' | 'brief' | 'off'
  workspace: string
  keywords: string[]
  transcribe: boolean
  asrModel: string
  mentionName: string
  commentPerRound: number
  replyToComments: boolean
  replyPerRound: number
}

export interface DutyState {
  day: string
  picked: number
  rounds: number
  perDay: number
  remaining: number
  report: string
}

export interface DutySnapshot {
  config: DutyConfig
  state: DutyState
  windows: Record<string, { label: string; start: string; end: string }>
}

export interface SeenVideo {
  date: string
  bvid: string
  title: string
  author: string
  result: string
}

export interface SeenPayload {
  path: string
  videos: SeenVideo[]
  comments: { bvid: string; rpid: string; root: string; time: string; text: string }[]
  rounds: { date: string; note: string }[]
  stats: { total: number; picked: number; skipped: number; rounds: number }
}
