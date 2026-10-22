#!/usr/bin/env node
/**
 * 环境自愈：把「换台电脑要敲的那几条命令」变成一段代码。
 *
 * 顺序固定为：找 uv → 建 .venv → 装后端依赖（含 bili-cli）→ 装前端依赖。
 * 每一步都先探活再动手，已经装好的直接跳过，所以重复跑只花几秒。
 *
 * 设计上只依赖 Node ≥ 18（fetch 内置）：
 *   - 没装 uv 就自己下载一份到 .tools/uv.exe，不碰用户 PATH、不用管理员权限；
 *   - 没装 Python 也没关系，uv 会自己下载托管的 CPython 3.12。
 */
import { spawn, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

export const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
export const isWin = process.platform === 'win32'
export const TOOLS = join(ROOT, '.tools')
export const VENV = join(ROOT, '.venv')
export const PYTHON = isWin ? join(VENV, 'Scripts', 'python.exe') : join(VENV, 'bin', 'python')
export const BILI = isWin ? join(VENV, 'Scripts', 'bili.exe') : join(VENV, 'bin', 'bili')

const REQ = join(ROOT, 'backend', 'requirements.txt')
const MARK = join(VENV, '.bili-desk-deps.json')
const UV_LOCAL = isWin ? join(TOOLS, 'uv.exe') : join(TOOLS, 'uv')
const NPM = isWin ? 'npm.cmd' : 'npm'
const YARN = isWin ? 'yarn.cmd' : 'yarn'
// node.exe 旁边的 npm 入口：直接用它，免得 Windows 上 spawn .cmd 报 EINVAL
const NPM_CLI = join(dirname(process.execPath), 'node_modules', 'npm', 'bin', 'npm-cli.js')

const say = (msg) => console.log(msg)
const step = (msg) => console.log(`\n[环境] ${msg}`)

/** 跑一个会打印到自己终端的子进程（安装器要让人看见进度条）。 */
function run(cmd, args, { cwd = ROOT, env, shell = false } = {}) {
  return new Promise((ok, fail) => {
    const child = spawn(cmd, args, { cwd, stdio: 'inherit', shell, env: { ...process.env, ...env } })
    child.on('error', (err) => {
      fail(new Error(err.code === 'ENOENT' ? `找不到命令：${cmd}` : `${cmd} 启动失败：${err.message}`))
    })
    child.on('exit', (code) => {
      if (code === 0) ok()
      else fail(new Error(`${cmd} ${args.join(' ')} 失败（退出码 ${code}）`))
    })
  })
}

function onPath(name) {
  const probe = isWin ? 'where' : 'which'
  return spawnSync(probe, [name], { encoding: 'utf8' }).status === 0
}

/**
 * 跑 npm。
 * Node 18+ 在 Windows 上不允许直接 spawn `npm.cmd`（会抛 EINVAL），
 * 所以优先用 node 直接执行 npm 的 JS 入口，退不回去才借 shell。
 */
function npmRun(args, opts = {}) {
  if (existsSync(NPM_CLI)) return run(process.execPath, [NPM_CLI, ...args], opts)
  return run(NPM, args, { ...opts, shell: true })
}

/** 本项目用 yarn（只有 yarn.lock）；没装 yarn 才退回 npm，并且不生成 package-lock.json。 */
function pkgRun(args, opts = {}) {
  if (onPath('yarn')) return run(YARN, args, { ...opts, shell: isWin })
  const npmArgs = args[0] === 'install' ? [...args, '--no-package-lock'] : args
  return npmRun(npmArgs, opts)
}

export function findUvPath() {
  const candidates = [
    UV_LOCAL,
    join(homedir(), '.local', 'bin', isWin ? 'uv.exe' : 'uv'),
    join(homedir(), '.cargo', 'bin', isWin ? 'uv.exe' : 'uv'),
  ]
  const hit = candidates.find((p) => existsSync(p))
  if (hit) return hit
  return onPath('uv') ? 'uv' : null
}

/** 流式下载 + 进度提示：GitHub 在国内可能只有几百 KB/s，不显示进度会像卡死。 */
async function download(url, dest) {
  const res = await fetch(url, { redirect: 'follow' })
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)
  const total = Number(res.headers.get('content-length') || 0)
  const mb = (n) => (n / 1048576).toFixed(1)

  const chunks = []
  let got = 0
  let shown = 0
  for await (const chunk of res.body) {
    chunks.push(chunk)
    got += chunk.length
    if (got - shown > 512 * 1024) {
      shown = got
      const pct = total ? ` (${Math.round((got / total) * 100)}%)` : ''
      process.stdout.write(`  下载中 ${mb(got)} MB${total ? ` / ${mb(total)} MB` : ''}${pct}\r`)
    }
  }
  process.stdout.write('\n')
  if (!got) throw new Error('下载到 0 字节')
  writeFileSync(dest, Buffer.concat(chunks))
}


/** 解 zip：优先用系统自带的 tar（Win10 1803+ 都能解 zip），不行再退回 PowerShell。 */
function unzip(zip, dest) {
  mkdirSync(dest, { recursive: true })
  spawnSync('tar', ['-xf', zip, '-C', dest], { stdio: 'ignore' })
  if (existsSync(join(dest, 'uv.exe'))) return
  spawnSync('powershell', [
    '-NoProfile', '-NonInteractive', '-Command',
    `Expand-Archive -LiteralPath '${zip}' -DestinationPath '${dest}' -Force`,
  ], { stdio: 'ignore' })
}

async function ensureUv() {
  const found = findUvPath()
  if (found) return found

  if (!isWin) {
    throw new Error(
      '没找到 uv。先装一下（只需一次）：\n' +
      '  curl -LsSf https://astral.sh/uv/install.sh | sh\n' +
      '装完重开终端再运行。'
    )
  }

  step('没找到 uv，正在下载一份到 .tools（约 15MB，只下这一次）…')
  mkdirSync(TOOLS, { recursive: true })
  const zip = join(TOOLS, 'uv.zip')
  try {
    await download('https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip', zip)
  } catch (err) {
    throw new Error(
      `下载 uv 失败（${err.message}）。\n` +
      '多半是网络/代理问题，可以手动下载后用「解压到 .tools 目录」的方式救：\n' +
      '  https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip'
    )
  }
  unzip(zip, TOOLS)
  try { rmSync(zip, { force: true }) } catch { /* 删不掉也无所谓 */ }

  if (!existsSync(UV_LOCAL)) {
    // 有些包的目录层级是 uv-x86_64-pc-windows-msvc/uv.exe，捞出来摆平
    const nested = readdirSync(TOOLS, { withFileTypes: true })
      .filter((d) => d.isDirectory())
      .map((d) => join(TOOLS, d.name, 'uv.exe'))
      .find((p) => existsSync(p))
    if (nested) renameSync(nested, UV_LOCAL)
  }
  if (!existsSync(UV_LOCAL)) throw new Error('解压 uv 失败：没找到 uv.exe')
  say(`   uv 就绪：${UV_LOCAL}`)
  return UV_LOCAL
}

async function ensureVenv(uv) {
  if (existsSync(PYTHON)) return
  step('创建 Python 环境（首次约 1 分钟；没装 Python 也没关系，uv 会自己下载 3.12）…')
  await run(uv, ['venv', VENV, '--python', '3.12'])
  if (!existsSync(PYTHON)) throw new Error(`创建 .venv 失败：没生成 ${PYTHON}`)
}

function reqHash() {
  return createHash('sha256').update(readFileSync(REQ)).digest('hex')
}

/** 真的能 import 才算装好 —— 只看标记文件会被"半路中断"骗到。 */
function depsImportable() {
  return spawnSync(PYTHON, ['-c', 'import fastapi, uvicorn'], { stdio: 'ignore' }).status === 0
}

async function ensureDeps(uv) {
  const hash = reqHash()
  if (depsImportable() && existsSync(MARK)) {
    try {
      if (JSON.parse(readFileSync(MARK, 'utf8')).reqHash === hash) return
    } catch { /* 标记文件坏了就当没装过 */ }
  }
  step('安装后端依赖（bili-cli 也装在项目自己的 .venv 里，不污染全局）…')
  await run(uv, ['pip', 'install', '--python', PYTHON, '-r', REQ])
  writeFileSync(MARK, JSON.stringify({ reqHash: hash, at: new Date().toISOString() }, null, 2))
}

/** 前端依赖：有 node_modules 就跳过（判断依据是 vite 的入口文件在不在）。 */
export async function ensureFrontendDeps() {
  if (existsSync(join(ROOT, 'node_modules', 'vite', 'bin', 'vite.js'))) return false
  step('安装前端依赖（首次约 1 分钟）…')
  if (!onPath('node')) {
    throw new Error(
      '这台机器没装 Node.js。\n' +
      '装一个再回来：https://nodejs.org/zh-cn/download （一路「下一步」即可）'
    )
  }
  await pkgRun(['install'])
  return true
}

/** 构建 production 产物 dist/；已经构建过就直接用。 */
export async function ensureDist() {
  if (existsSync(join(ROOT, 'dist', 'index.html'))) return false
  await ensureFrontendDeps()
  step('构建前端（约 10~30 秒）…')
  await pkgRun(['run', 'build'])
  return true
}

/**
 * 保证后端能跑：uv → .venv → 依赖。
 * 返回 { python, uv, bili }，调用方直接用绝对路径起服务，不依赖 PATH。
 */
export async function ensureBackend() {
  const uv = await ensureUv()
  await ensureVenv(uv)
  await ensureDeps(uv)
  if (!existsSync(PYTHON)) throw new Error(`Python 环境不完整：找不到 ${PYTHON}`)
  return { uv, python: PYTHON, bili: existsSync(BILI) ? BILI : null }
}
