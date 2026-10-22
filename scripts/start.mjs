#!/usr/bin/env node
/**
 * 一键启动「日常面板」（生产模式）：双击「启动.bat」走的就是这里。
 *
 * 和 `yarn dev` 的区别：不跑 Vite、不热更新，只起一个 FastAPI（8811），
 * 前端直接用构建好的 dist/ —— 少一个进程、少一个端口，给不懂开发的人用更省心。
 *
 * 该装的东西这里都会自己装（见 scripts/setup.mjs），所以第一次运行可能等 1~3 分钟。
 */
import { spawn } from 'node:child_process'
import { join } from 'node:path'
import { ROOT, ensureBackend, ensureDist, isWin } from './setup.mjs'

const URL = 'http://127.0.0.1:8811/'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function alive() {
  try {
    const res = await fetch(`${URL}api/ping`, { signal: AbortSignal.timeout(1200) })
    return res.ok
  } catch {
    return false
  }
}

function openBrowser(url) {
  const cmd = isWin ? 'cmd' : process.platform === 'darwin' ? 'open' : 'xdg-open'
  const args = isWin ? ['/c', 'start', '', url] : [url]
  try {
    spawn(cmd, args, { stdio: 'ignore', detached: true }).unref()
  } catch {
    console.log(`[面板] 浏览器没打开就手动访问：${url}`)
  }
}

async function main() {
  if (await alive()) {
    console.log(`[面板] 已经在跑了，直接打开：${URL}`)
    openBrowser(URL)
    return
  }

  console.log('[面板] 正在检查运行环境（第一次启动会比较慢，之后就只花几秒）…')
  const { python } = await ensureBackend()
  const built = await ensureDist()
  if (built) console.log('[面板] 前端构建完成')

  console.log(`\n[面板] 启动后端：${python} -m uvicorn app.main:app --port 8811`)
  const api = spawn(python, ['-m', 'uvicorn', 'app.main:app', '--port', '8811'], {
    cwd: join(ROOT, 'backend'),
    stdio: 'inherit',
    env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
  })

  api.on('exit', (code) => {
    if (code && code !== 0) {
      console.error(`\n[面板] 后端退出了（code=${code}）。`)
      console.error('  8811 端口被别的程序占用？先关掉它再试。')
    }
    process.exit(code ?? 0)
  })
  process.on('SIGINT', () => {
    try { api.kill(isWin ? 'SIGTERM' : 'SIGINT') } catch { /* 已经退了 */ }
    process.exit(0)
  })

  // 等它真的能应答，再开浏览器 —— 否则首屏是一堆网络错误
  for (let i = 0; i < 120; i++) {
    if (api.exitCode !== null) return
    if (await alive()) break
    await sleep(250)
  }
  if (!(await alive())) throw new Error('后端 30 秒内没起来，看看上面的报错')

  console.log(`\n[面板] 已就绪：${URL}`)
  console.log('[面板] 第一次用要先「扫码登录」；关掉这个窗口就等于停止面板。\n')
  openBrowser(URL)
}

main().catch((err) => {
  console.error(`\n[面板] 启动失败：${err.message}`)
  process.exit(1)
})
