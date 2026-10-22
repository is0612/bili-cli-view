#!/usr/bin/env node
/**
 * 打一个「发给别人」的 zip：只装程序和章程，不装任何跑出来的东西。
 *
 *   node scripts/pack.mjs                 → pack/bili-desk-<日期>.zip
 *   node scripts/pack.mjs --with-uv       → 连 .tools/uv.exe 一起带上（对方省一次下载）
 *
 * 不装：.venv、node_modules、dist、runtime、__pycache__、日志、个人数据目录。
 * （个人数据本来就在 %APPDATA%\bili-desk，不在仓库里，所以这里怎么打都是干净的。）
 */
import { spawnSync } from 'node:child_process'
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync, statSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)))
const OUT_DIR = join(ROOT, 'pack')
const withUv = process.argv.includes('--with-uv')

const SKIP = new Set([
  '.git', '.venv', 'node_modules', 'dist', 'runtime', 'pack', '__pycache__', '.vite',
  '.tools', // 默认跳过；--with-uv 时单独处理
])
const SKIP_FILES = new Set(['tsconfig.tsbuildinfo', '.DS_Store'])

function copyTree(from, to) {
  mkdirSync(to, { recursive: true })
  for (const entry of readdirSync(from, { withFileTypes: true })) {
    if (SKIP.has(entry.name) || SKIP_FILES.has(entry.name)) continue
    if (entry.name.endsWith('.log') || entry.name.endsWith('.pyc')) continue
    const src = join(from, entry.name)
    const dst = join(to, entry.name)
    if (entry.isDirectory()) copyTree(src, dst)
    else if (entry.isFile()) cpSync(src, dst)
  }
}

function zipDir(dir, out) {
  if (process.platform === 'win32') {
    const res = spawnSync('powershell', [
      '-NoProfile', '-NonInteractive', '-Command',
      `Compress-Archive -Path '${dir}\\*' -DestinationPath '${out}' -Force`,
    ], { stdio: 'inherit' })
    return res.status === 0
  }
  const res = spawnSync('zip', ['-r', '-q', out, '.'], { cwd: dir, stdio: 'inherit' })
  return res.status === 0
}

function main() {
  const stamp = new Date().toISOString().slice(0, 10)
  const out = join(OUT_DIR, `bili-desk-${stamp}.zip`)
  const tmp = join(tmpdir(), `bili-desk-pack-${Date.now()}`)

  console.log(`[pack] 收集文件 → ${tmp}`)
  try {
    copyTree(ROOT, tmp)
    if (withUv && existsSync(join(ROOT, '.tools', 'uv.exe'))) {
      mkdirSync(join(tmp, '.tools'), { recursive: true })
      cpSync(join(ROOT, '.tools', 'uv.exe'), join(tmp, '.tools', 'uv.exe'))
      console.log('[pack] 带上了 .tools/uv.exe')
    }
    mkdirSync(OUT_DIR, { recursive: true })
    if (existsSync(out)) rmSync(out, { force: true })
    console.log(`[pack] 压缩 → ${out}`)
    if (!zipDir(tmp, out)) throw new Error('压缩失败')
    const mb = (statSync(out).size / 1048576).toFixed(1)
    console.log(`[pack] 完成：${out}（${mb} MB）`)
    console.log('[pack] 对方解压后双击 启动.bat 即可；不需要 .venv / node_modules / dist。')
  } finally {
    rmSync(tmp, { recursive: true, force: true })
  }
}

try {
  main()
} catch (err) {
  console.error(`[pack] 失败：${err.message}`)
  process.exit(1)
}
