#!/usr/bin/env node
/**
 * `yarn dev` / `npm run dev` 的一键开发入口：
 *   1. 没有后端就先起 FastAPI（8811）
 *   2. 再起 Vite（5199，自动打开浏览器）
 *   3. Ctrl+C 时把后端一起收掉
 */
import { spawn } from 'node:child_process'
import { copyFileSync, existsSync, mkdirSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const isWin = process.platform === 'win32'
const BACKEND = 'http://127.0.0.1:8811'

/**
 * bili 的 HTTP 栈（curl_cffi → libcurl）在 Windows 上读不了中文路径下的证书：
 * 仓库放在 E:\工作\... 时，libcurl 会报 curl: (77) error adding trust anchors，
 * 结果是扫码登录和所有联网命令全挂。
 * 把 certifi 的 cacert.pem 复制到 ASCII 临时目录，用 CURL_CA_BUNDLE 指过去即可。
 */
function caEnv() {
  if (!isWin) return {}
  const src = join(root, '.venv', 'Lib', 'site-packages', 'certifi', 'cacert.pem')
  if (!existsSync(src)) return {}
  try {
    const dir = join(tmpdir(), 'bili-ca')
    const dst = join(dir, 'cacert.pem')
    mkdirSync(dir, { recursive: true })
    copyFileSync(src, dst)
    return { CURL_CA_BUNDLE: dst, SSL_CERT_FILE: dst }
  } catch {
    return {}
  }
}

function pythonPath() {
  const candidates = isWin
    ? [join(root, '.venv', 'Scripts', 'python.exe'), join(root, '.venv', 'Scripts', 'python')]
    : [join(root, '.venv', 'bin', 'python')]
  const hit = candidates.find((p) => existsSync(p))
  if (!hit) {
    console.error('[dev] 找不到 .venv，先跑：uv venv .venv && uv pip install -r backend/requirements.txt')
    process.exit(1)
  }
  return hit
}

async function backendAlive() {
  try {
    // 用 /api/ping 探活：/api/meta 要调三次 bili，慢到会误判成"没起"
    const res = await fetch(`${BACKEND}/api/ping`, { signal: AbortSignal.timeout(1200) })
    return res.ok
  } catch {
    return false
  }
}

const children = []

function shutdown(code = 0) {
  for (const child of children) {
    try {
      child.kill(isWin ? 'SIGTERM' : 'SIGINT')
    } catch {
      /* 已经退了就算了 */
    }
  }
  process.exit(code)
}

process.on('SIGINT', () => shutdown(0))
process.on('SIGTERM', () => shutdown(0))

async function main() {
  if (await backendAlive()) {
    console.log('[dev] 后端已在 8811 上跑着，复用')
  } else {
    const py = pythonPath()
    console.log(`[dev] 启动后端 ${py} -m uvicorn app.main:app --port 8811`)
    const api = spawn(py, ['-m', 'uvicorn', 'app.main:app', '--port', '8811', '--reload'], {
      cwd: join(root, 'backend'),
      stdio: 'inherit',
      env: { ...process.env, ...caEnv() },
    })
    children.push(api)
    api.on('exit', async (code) => {
      // 端口被别的进程占着时 uvicorn 会直接退出，但服务其实是活的 ⇒ 别把整个脚本带走
      if (await backendAlive()) {
        console.log('[dev] 8811 上已有后端在跑，接着用')
        return
      }
      if (code && code !== 0) console.error(`[dev] 后端退出（code=${code}）`)
      shutdown(code ?? 0)
    })
    // 等它起来，避免 Vite 先开浏览器、首屏全是网络错误
    for (let i = 0; i < 40; i++) {
      if (await backendAlive()) break
      await new Promise((r) => setTimeout(r, 250))
    }
  }

  console.log('[dev] 启动前端 Vite（5199，会自动打开浏览器）')
  const vite = spawn(process.execPath, [join(root, 'node_modules', 'vite', 'bin', 'vite.js'), '--open'], {
    cwd: root,
    stdio: 'inherit',
  })
  children.push(vite)
  vite.on('exit', (code) => shutdown(code ?? 0))
}

main()
