<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import {
  ArrowDown,
  Clock,
  CopyDocument,
  MagicStick,
  Operation,
  Refresh,
  Setting,
  VideoPlay,
} from '@element-plus/icons-vue'
import { api } from './api'
import CommandRunner from './components/CommandRunner.vue'
import DutyPanel from './components/DutyPanel.vue'
import DynamicPanel from './components/DynamicPanel.vue'
import HomeView from './components/HomeView.vue'
import JournalPanel from './components/JournalPanel.vue'
import SeenPanel from './components/SeenPanel.vue'
import SelfCheckPanel from './components/SelfCheckPanel.vue'
import LoginModal from './components/LoginModal.vue'
import MenuManagerModal from './components/MenuManagerModal.vue'
import ResultCard from './components/ResultCard.vue'
import SettingsModal from './components/SettingsModal.vue'
import SidebarNav from './components/SidebarNav.vue'
import { useToast } from './composables/useToast'
import { hhmm, runSummary } from './utils/format'
import type { CommandGroup, CommandItem, Meta, RunEntry } from './types'

const groups = ref<CommandGroup[]>([])
const active = ref<CommandItem | null>(null)
const results = ref<RunEntry[]>([])
const meta = ref<Meta | null>(null)
const busy = ref(false)

/** 三个视图：概览 / 命令台 / 运行记录 */
const view = ref<'home' | 'cmd' | 'runs'>('home')
/** 概览页重挂载用：跑完一轮后强制重新拉数据 */
const homeKey = ref(0)

/** 深链想跳的视图：如果同时要 autorun，得等命令跑完再切 */
const pendingView = ref<'runs' | 'home' | null>(null)

const settingsOpen = ref(false)
const loginOpen = ref(false)
const menuOpen = ref(false)
const sideRef = ref<InstanceType<typeof SidebarNav> | null>(null)
const runnerRef = ref<InstanceType<typeof CommandRunner> | null>(null)
const initialValues = ref<Record<string, string>>({})
const autoRun = ref(false)
/** ?demo=1：隐藏版本/账号这三个 chip，方便截公开截图。 */
const demo = ref(false)

/** 侧栏收成 64px 图标栏：手动点了「收起」，或窗口窄于 1080 自动收 */
const railManual = ref(false)
const narrow = ref(false)
const rail = computed(() => railManual.value || narrow.value)

const { notify } = useToast()

const loggedIn = computed(() => Boolean(meta.value?.auth.ok && meta.value?.auth.user))
const spaceUrl = (mid: number | string) => `https://space.bilibili.com/${mid}`
const level = computed(() => meta.value?.auth.user?.level ?? '?')
const userName = computed(() => meta.value?.auth.user?.name ?? '未登录')
const initial = computed(() => userName.value.slice(0, 1).toUpperCase())
const total = computed(() => groups.value.reduce((n, g) => n + g.items.length, 0))
const groupOf = (item: CommandItem | null) =>
  item ? (groups.value.find((g) => g.items.some((i) => i.id === item.id))?.group ?? '') : ''

async function loadMeta() {
  try {
    meta.value = await api.meta()
  } catch (err) {
    notify(`读取账号状态失败：${(err as Error).message}`, true)
  }
}

async function run(argv: string[]) {
  busy.value = true
  runnerRef.value?.setBusy(true)
  try {
    const res = await api.run(argv)
    results.value.unshift({ ...res, at: Date.now() })
    if (results.value.length > 30) results.value.pop()
    if (!res.json?.ok && res.json?.error?.code === 'auth_expired') void loadMeta()
  } catch (err) {
    notify(`执行失败：${(err as Error).message}`, true)
  } finally {
    busy.value = false
    runnerRef.value?.setBusy(false)
    // 深链里同时带了 v=runs：等这条真正跑完再切过去，否则命令台被卸载、命令根本没发出去
    if (pendingView.value) {
      view.value = pendingView.value
      pendingView.value = null
    }
  }
}

/** 概览页的「现在跑一轮」：走值班入口，不是 CLI 命令 */
async function runRound() {
  busy.value = true
  try {
    const res = await api.runAgent()
    notify(
      res.ok ? `本轮完成，采纳 ${res.picked} 条` : `本轮失败（code ${res.code}），去运行记录看日志`,
      !res.ok,
    )
    void loadMeta()
  } catch (err) {
    notify(`跑一轮失败：${(err as Error).message}`, true)
  } finally {
    busy.value = false
    homeKey.value += 1
  }
}

function choose(item: CommandItem) {
  initialValues.value = {}
  autoRun.value = false
  active.value = item
  view.value = 'cmd'
}

function goHome() {
  view.value = 'home'
  homeKey.value += 1
}

function quickPick(cmd: string) {
  const item = groups.value
    .flatMap((g) => g.items)
    .find((i) => (i.cmd ?? i.argv.join('.')) === cmd || i.id === cmd)
  if (item) choose(item)
  else notify(`命令表里没有 ${cmd}`, true)
}

/** 菜单显隐保存后：用后端过滤好的命令表刷新侧栏 */
function onMenuSaved(nextGroups: CommandGroup[]) {
  groups.value = nextGroups
  // 当前选中的命令若被隐藏，退回概览
  if (active.value && !nextGroups.flatMap((g) => g.items).some((i) => i.id === active.value?.id)) {
    active.value = null
    view.value = 'home'
  }
}

function clearResults() {
  results.value = []
  expandedRun.value = -1
  notify('运行记录已清空（只清本页，磁盘日志还在）')
}

/* ── 运行记录：筛选 + 展开详情 ─────────────────────────── */
const runFilter = ref<'all' | 'ok' | 'err'>('all')
/** 展开的是哪一条（用 at 当 id），-1 表示都收起 */
const expandedRun = ref(-1)
const okRuns = computed(() => results.value.filter((r) => r.json?.ok).length)
const errRuns = computed(() => results.value.length - okRuns.value)
const shownRuns = computed(() => {
  if (runFilter.value === 'ok') return results.value.filter((r) => r.json?.ok)
  if (runFilter.value === 'err') return results.value.filter((r) => !r.json?.ok)
  return results.value
})

function toggleRun(at: number) {
  expandedRun.value = expandedRun.value === at ? -1 : at
}

function exportRuns() {
  if (!results.value.length) {
    notify('还没有记录可导出', true)
    return
  }
  const lines = ['# bili-desk 运行记录', '', `导出时间：${new Date().toLocaleString()}`, '']
  for (const r of results.value) {
    lines.push(`## bili ${r.argv.join(' ')}`)
    lines.push(`- 状态：${r.json?.ok ? '成功' : '失败'}（code ${r.code ?? '—'}）`)
    lines.push(`- 耗时：${r.elapsed}s`)
    if (r.json?.error) lines.push(`- 错误：${r.json.error.code}：${r.json.error.message}`)
    lines.push('', '```json', JSON.stringify(r.json ?? {}, null, 2), '```', '')
  }
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `bili-desk-runs-${new Date().toISOString().slice(0, 10)}.md`
  a.click()
  URL.revokeObjectURL(a.href)
}

function hotkey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    nextTick(() => sideRef.value?.focusSearch())
  }
}

function onResize() {
  narrow.value = window.innerWidth < 1080
}

onMounted(async () => {
  try {
    const cat = await api.catalog()
    groups.value = cat.groups
  } catch (err) {
    notify(`读取命令表失败：${(err as Error).message}`, true)
  }
  void loadMeta()
  window.addEventListener('keydown', hotkey)
  onResize()
  window.addEventListener('resize', onResize)

  const qs = new URLSearchParams(location.search)
  demo.value = qs.get('demo') === '1'
  if (qs.get('settings') === '1') settingsOpen.value = true
  if (qs.get('menu') === '1') menuOpen.value = true
  if (qs.get('login') === '1') loginOpen.value = true
  const wantView = qs.get('v')
  const cmdId = qs.get('cmd')
  if (cmdId) {
    const item = groups.value.flatMap((g) => g.items).find((i) => i.id === cmdId)
    if (item) {
      const preset: Record<string, string> = {}
      for (const p of item.params ?? []) {
        const v = qs.get(p.key)
        if (v != null) preset[p.key] = v
      }
      initialValues.value = preset
      active.value = item
      view.value = 'cmd'
      autoRun.value = qs.get('run') === '1'
      if (autoRun.value) await nextTick()
    }
  }
  // ?v=runs 放最后：可以「?cmd=xxx&run=1&v=runs」——跑一条然后直接看运行记录
  if (wantView === 'runs' || wantView === 'home') {
    if (autoRun.value) pendingView.value = wantView
    else view.value = wantView
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', hotkey)
  window.removeEventListener('resize', onResize)
})
</script>

<template>
  <div class="app">
    <!-- ── 顶栏 56px：只放身份与设置，导航交给侧栏 ── -->
    <header class="topbar">
      <div class="brand">
        <div class="brand-mark"><el-icon><VideoPlay /></el-icon></div>
        <div class="brand-name">bili<span>·desk</span></div>
      </div>

      <span v-if="!demo" class="ver">v{{ meta?.version ?? '…' }}</span>

      <span v-if="busy" class="tb-run">
        <i class="pulse" />
        {{ active ? `正在执行 ${active.cmd ?? active.argv.join(' ')}` : '正在执行…' }}
      </span>

      <span class="spacer" />

      <!-- 账号 pill：已登录点开 B站主页，未登录点开扫码 -->
      <a
        v-if="!demo && loggedIn"
        class="acct"
        :href="spaceUrl(meta!.auth.user!.mid)"
        target="_blank"
        rel="noreferrer"
        :title="`打开 ${userName} 的B站主页`"
      >
        <span class="av">{{ initial }}</span>
        <span class="on-dot" />
        <span class="an">{{ userName }}</span>
        <span class="lv">Lv{{ level }}</span>
        <el-icon class="chev"><ArrowDown /></el-icon>
      </a>
      <button
        v-else-if="!demo"
        class="acct is-off"
        title="还没登录，点这里扫码"
        @click="loginOpen = true"
      >
        <span class="av"><el-icon><MagicStick /></el-icon></span>
        <span class="on-dot" />
        <span class="an">未登录</span>
        <el-icon class="chev"><ArrowDown /></el-icon>
      </button>

      <button
        v-if="!demo"
        class="icon-btn"
        :title="loggedIn ? '重新扫码登录' : '扫码登录'"
        @click="loginOpen = true"
      >
        <el-icon><MagicStick /></el-icon>
      </button>
      <button class="icon-btn" title="刷新账号状态" @click="loadMeta">
        <el-icon><Refresh /></el-icon>
      </button>
      <button
        class="icon-btn"
        title="设置：人设 / API Key / 数据备份"
        @click="settingsOpen = true"
      >
        <el-icon><Setting /></el-icon>
      </button>
    </header>

    <div class="body">
      <SidebarNav
        ref="sideRef"
        :groups="groups"
        :active-id="active?.id ?? null"
        :view="view"
        :run-count="results.length"
        :rail="rail"
        @select="choose"
        @open-home="goHome"
        @open-runs="view = 'runs'"
        @manage-menu="menuOpen = true"
        @toggle-rail="railManual = !railManual"
      />

      <main class="work">
        <div class="work-in">
          <!-- ── ① 概览 ── -->
          <HomeView
            v-if="view === 'home'"
            :key="homeKey"
            :groups="groups"
            :results="results"
            :busy="busy"
            @select="quickPick"
            @run-round="runRound"
            @open-runs="view = 'runs'"
            @refresh="loadMeta"
          />

          <!-- ── ② 运行记录 ── -->
          <template v-else-if="view === 'runs'">
            <div class="crumb">工作台 <span>/</span> <b>运行记录</b></div>
            <div class="page-h">
              <div>
                <h1>运行记录</h1>
                <p>最近 {{ results.length }} 次执行，最新的在最前。刷新页面就清空，磁盘日志另外存。</p>
              </div>
              <div class="ph-r">
                <button class="btn" :disabled="!results.length" @click="exportRuns">
                  <el-icon><CopyDocument /></el-icon>导出 Markdown
                </button>
                <button class="btn" :disabled="!results.length" @click="clearResults">清空</button>
              </div>
            </div>

            <div class="filters">
              <button class="chip" :class="{ on: runFilter === 'all' }" @click="runFilter = 'all'">
                全部<span class="n">{{ results.length }}</span>
              </button>
              <button class="chip" :class="{ on: runFilter === 'ok' }" @click="runFilter = 'ok'">
                成功<span class="n">{{ okRuns }}</span>
              </button>
              <button class="chip" :class="{ on: runFilter === 'err' }" @click="runFilter = 'err'">
                失败<span class="n">{{ errRuns }}</span>
              </button>
              <span class="sp" />
              <span v-if="results.length" class="fhint">点一行展开原始 JSON</span>
            </div>

            <div v-if="!results.length" class="empty-block">
              <div class="halo"><el-icon :size="22"><Clock /></el-icon></div>
              <h4>还没跑过命令</h4>
              <p>回概览点「现在跑一轮」，或从左边菜单挑一条命令运行一下就有了。</p>
            </div>
            <div v-else-if="!shownRuns.length" class="empty-block">
              <div class="halo"><el-icon :size="22"><Clock /></el-icon></div>
              <h4>这一类还没有记录</h4>
              <p>{{ runFilter === 'ok' ? '成功的记录是空的' : '失败的记录是空的' }}，切回「全部」看看。</p>
            </div>
            <div v-else class="card runs-list">
              <template v-for="res in shownRuns" :key="res.at">
                <div class="rrow" @click="toggleRun(res.at)">
                  <span class="rdot" :class="res.json?.ok ? 'ok' : 'err'" />
                  <div class="rmain">
                    <div class="rc">bili {{ res.argv.join(' ') }}</div>
                    <div class="rs">{{ runSummary(res) }}</div>
                  </div>
                  <span class="rt">{{ res.elapsed }}s · {{ hhmm(new Date(res.at)) }}</span>
                  <el-icon class="rchev" :class="{ open: expandedRun === res.at }"><ArrowDown /></el-icon>
                </div>
                <div v-if="expandedRun === res.at" class="rdetail">
                  <ResultCard :result="res" />
                </div>
              </template>
            </div>
          </template>

          <!-- ── ③ 命令台 ── -->
          <template v-else>
            <div v-if="active" class="crumb">
              <span>{{ groupOf(active) }}</span>
              <span>/</span>
              <b>{{ active.label }}</b>
            </div>

            <DutyPanel v-if="active?.kind === 'duty'" />
            <DynamicPanel v-else-if="active?.kind === 'dynamic'" />
            <SeenPanel v-else-if="active?.kind === 'seen'" />
            <JournalPanel v-else-if="active?.kind === 'journal'" />
            <SelfCheckPanel v-else-if="active?.kind === 'selfcheck'" />

            <template v-else-if="active">
              <CommandRunner
                ref="runnerRef"
                :item="active"
                :initial="initialValues"
                :autorun="autoRun"
                @run="run"
              />

              <template v-if="results.length">
                <div class="sec-h">
                  <h2>最新结果</h2>
                  <span class="sub">bili {{ active.argv.join(' ') }}</span>
                  <button class="more" @click="view = 'runs'">全部记录</button>
                </div>
                <ResultCard :result="results[0]" />
              </template>
            </template>

            <template v-else>
              <div class="page-h">
                <div>
                  <h1>{{ groups.length ? '从左边挑一条命令' : '命令表还没加载出来' }}</h1>
                  <p>
                    {{ groups.length }} 组 · {{ total }} 条命令，跟着 bili schema 自动更新。按 Ctrl K 直接搜。
                  </p>
                </div>
              </div>
              <div v-if="!groups.length" class="empty-block">
                <div class="halo"><el-icon :size="22"><Operation /></el-icon></div>
                <h4>菜单都被藏起来了</h4>
                <p>点侧栏底部的「管理菜单」，把要用的命令勾回来就行。</p>
              </div>
              <div v-else class="empty-block">
                <div class="halo"><el-icon :size="22"><Operation /></el-icon></div>
                <h4>还没选命令</h4>
                <p>日常操作在侧栏「常用」里；想知道今天怎么样，回概览看。</p>
                <button class="btn" style="margin-top: 14px" @click="goHome">回概览</button>
              </div>
            </template>
          </template>
        </div>
      </main>
    </div>

    <SettingsModal :open="settingsOpen" @close="settingsOpen = false" @notify="notify" />
    <MenuManagerModal
      :open="menuOpen"
      @close="menuOpen = false"
      @saved="onMenuSaved"
      @notify="notify"
    />
    <LoginModal
      :open="loginOpen"
      :logged-in="loggedIn"
      @close="loginOpen = false"
      @notify="notify"
      @refresh="loadMeta"
    />
  </div>
</template>
