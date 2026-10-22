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
