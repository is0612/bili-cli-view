#!/usr/bin/env node
/**
 * 「我的数据」命令行入口：查位置 / 导出 / 导入 / 清空。
 *
 * 走的是正在运行的面板后端（8811），所以先在另一个窗口双击「启动.bat」，
 * 或者直接 `node scripts/start.mjs`。
 *
 *   node scripts/profile.mjs where
 *   node scripts/profile.mjs export [--with-secrets] [文件名.zip]
 *   node scripts/profile.mjs import <备份.zip>
 *   node scripts/profile.mjs reset
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { basename } from 'node:path'

const BASE = 'http://127.0.0.1:8811'

function stamp() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}`
}

function human(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

async function backendUp() {
  try {
    const res = await fetch(`${BASE}/api/ping`, { signal: AbortSignal.timeout(1200) })
    return res.ok
  } catch {
    return false
  }
}

async function json(path, init) {
  const res = await fetch(BASE + path, init)
  const text = await res.text()
  let body = null
  try { body = text ? JSON.parse(text) : null } catch { body = null }
  if (!res.ok) throw new Error(body?.detail || `HTTP ${res.status}`)
  return body
}

async function main() {
  const [cmd, ...rest] = process.argv.slice(2)
  if (!cmd || ['-h', '--help', 'help'].includes(cmd)) {
    console.log('用法：node scripts/profile.mjs <where|export|import|reset>')
    return
  }

  if (!(await backendUp())) {
    console.error('[profile] 面板后端没在跑。先双击「启动.bat」，或另开一个窗口跑 node scripts/start.mjs。')
    process.exit(1)
  }

  if (cmd === 'where') {
    const p = await json('/api/profile')
    console.log(`数据目录：${p.dir}`)
    console.log(`  ${p.files} 个文件，共 ${human(p.bytes)}`)
    console.log(`  报告 ${p.reports} 篇 · 人设 ${p.has_persona ? '已写' : '未写'} · 工作区 ${p.workspace}`)
    if (p.env_override) console.log('  （由 BILI_DESK_HOME 指定）')
    if (p.legacy.length) console.log(`  旧位置还有数据：${p.legacy.join('、')}（重启面板会自动搬走）`)
    return
  }

  if (cmd === 'export') {
    const withSecrets = rest.includes('--with-secrets')
    const out = rest.find((a) => !a.startsWith('--')) || `bili-desk-backup-${stamp()}.zip`
    const res = await fetch(`${BASE}/api/profile/export?secrets=${withSecrets ? 1 : 0}`)
    if (!res.ok) throw new Error(`导出失败：HTTP ${res.status}`)
    const buf = Buffer.from(await res.arrayBuffer())
    writeFileSync(out, buf)
    console.log(`已导出 ${out}（${human(buf.length)}${withSecrets ? '，含 API Key' : '，不含 API Key'}）`)
    return
  }

  if (cmd === 'import') {
    const file = rest[0]
    if (!file) throw new Error('用法：node scripts/profile.mjs import <备份.zip>')
    const data = readFileSync(file)
    const res = await fetch(`${BASE}/api/profile/import`, { method: 'POST', body: data })
    const body = await res.json().catch(() => null)
    if (!res.ok) throw new Error(body?.detail || `HTTP ${res.status}`)
    console.log(`已导入 ${basename(file)}`)
    for (const note of body.notes || []) console.log(`  · ${note}`)
    return
  }

  if (cmd === 'reset') {
    const body = await json('/api/profile/reset', { method: 'POST' })
    console.log('已清空')
    for (const note of body.notes || []) console.log(`  · ${note}`)
    return
  }

  throw new Error(`不认识的子命令：${cmd}`)
}

main().catch((err) => {
  console.error(`[profile] ${err.message}`)
  process.exit(1)
})
