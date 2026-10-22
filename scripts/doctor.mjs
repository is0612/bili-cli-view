#!/usr/bin/env node
/**
 * 自检报告：把「这台机器现在缺什么」用一屏中文说清楚。
 *
 * 给的情况通常是：别人双击「启动.bat」没反应 / 面板进去是空的，
 * 让他双击「诊断.bat」，把窗口里的内容截图发回来，比来回问十句强。
 */
import { spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

import { BILI, PYTHON, ROOT, TOOLS, findUvPath } from './setup.mjs'

const mark = (good) => (good ? '✓' : '✗')
const line = (good, label, extra = '') => `  ${mark(good)} ${label}${extra ? `  ${extra}` : ''}`

function sh(cmd, args, timeout = 15000) {
  const res = spawnSync(cmd, args, { encoding: 'utf8', timeout })
  return { code: res.status, out: (res.stdout || '').trim(), err: (res.stderr || '').trim() }
}

async function http(url, timeout = 3000) {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(timeout) })
    return res.ok
  } catch {
    return false
  }
}

async function main() {
  console.log('===== bili-desk 自检报告 =====')
  console.log(`时间：${new Date().toLocaleString('zh-CN')}`)
  console.log(`目录：${ROOT}`)
  console.log(`系统：${process.platform} ${process.arch}`)
  console.log('')

  console.log('【1. Node.js】')
  const node = sh(process.execPath, ['--version'])
  console.log(line(node.code === 0, `node ${node.out}`, node.code === 0 ? '' : '（没装？https://nodejs.org/zh-cn/download）'))
  console.log('')

  console.log('【2. uv 与 Python 环境】')
  const uv = findUvPath()
  console.log(line(!!uv, 'uv', uv || '没找到（双击启动.bat 会自动下载）'))
  console.log(line(existsSync(PYTHON), '.venv', existsSync(PYTHON) ? PYTHON : '还没建（双击启动.bat 会自动建）'))
  if (existsSync(PYTHON)) {
    const py = sh(PYTHON, ['-c', 'import sys, fastapi, uvicorn; print(sys.version.split()[0])'])
    console.log(line(py.code === 0, '后端依赖', py.code === 0 ? `Python ${py.out}` : '缺包（删掉 .venv 再双击 启动.bat）'))
  }
  console.log('')

  console.log('【3. bili-cli】')
  if (existsSync(BILI)) {
    const ver = sh(BILI, ['--version'])
    console.log(line(ver.code === 0, 'bili', ver.out || ver.err))
    const auth = sh(BILI, ['auth', 'status'], 30000)
    const logged = auth.out.includes('"name"') || (auth.out.includes('"ok": true') && !auth.out.includes('not_logged_in'))
    console.log(line(logged, '登录状态', logged ? '已登录' : `未登录（面板里点「扫码登录」）${auth.out.slice(0, 120)}`))
  } else {
    console.log(line(false, 'bili', '没装（删掉 .venv 再双击 启动.bat）'))
  }
  console.log('')

  console.log('【4. 前端】')
  console.log(line(existsSync(join(ROOT, 'node_modules', 'vite', 'bin', 'vite.js')), 'node_modules'))
  console.log(line(existsSync(join(ROOT, 'dist', 'index.html')), 'dist（生产构建）'))
  console.log('')

  console.log('【5. 服务】')
  const ping = await http('http://127.0.0.1:8811/api/ping')
  console.log(line(ping, '后端 8811', ping ? '在跑' : '没跑（双击 启动.bat）'))
  const vite = await http('http://127.0.0.1:5199/')
  console.log(line(vite, '前端 5199（仅开发模式）', vite ? '在跑' : '没跑'))
  if (ping) {
    try {
      const p = await (await fetch('http://127.0.0.1:8811/api/profile')).json()
      console.log(line(true, '我的数据', `${p.dir}（${p.files} 个文件，报告 ${p.reports} 篇）`))
      if (p.legacy?.length) console.log(line(false, '旧数据还在', p.legacy.join('、')))
    } catch {
      /* 老版本后端没有 /api/profile，忽略 */
    }
  }
  console.log('')

  console.log('【6. 可选：自动值班】')
  const dsh = join(homedir(), 'AppData', 'Roaming', 'npm', 'node_modules', '@deepseek-ai', 'dsh', 'lib', 'bin.js')
  console.log(line(existsSync(dsh), 'dsh（值班要用）', existsSync(dsh) ? '已安装' : '没装，只影响「自动值班」功能'))
  console.log('')

  console.log('===== 报告结束 =====')
  console.log('如果哪一步是 ✗，先试「删掉 .venv 目录再双击 启动.bat」重装一次；')
  console.log(`还是不行，把上面整段截图发回来，并提供目录 ${TOOLS} 里的内容。`)
}

main().catch((err) => {
  console.error(`自检本身出错了：${err.message}`)
  process.exit(1)
})
