<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, nextTick } from 'vue'
import { Clock, MagicStick, Refresh, Search, TopRight, VideoPlay } from '@element-plus/icons-vue'
import { api } from './api'
import CommandRunner from './components/CommandRunner.vue'
import DutyPanel from './components/DutyPanel.vue'
import DynamicPanel from './components/DynamicPanel.vue'
import RailNav from './components/RailNav.vue'
import SeenPanel from './components/SeenPanel.vue'
import SelfCheckPanel from './components/SelfCheckPanel.vue'
import LoginModal from './components/LoginModal.vue'
import ResultCard from './components/ResultCard.vue'
import SettingsModal from './components/SettingsModal.vue'
import { useToast } from './composables/useToast'
import type { CommandGroup, CommandItem, Meta, RunResult } from './types'

const groups = ref<CommandGroup[]>([])
const active = ref<CommandItem | null>(null)
const results = ref<RunResult[]>([])
const meta = ref<Meta | null>(null)
const busy = ref(false)

/** 视图：命令台 / 运行记录 */
const view = ref<'cmd' | 'runs'>('cmd')
/** 当前分组；null = 未限定（靠搜索框找） */
const activeGroup = ref<string | null>(null)
const query = ref('')
const focused = ref(false)
const searchEl = ref<HTMLInputElement | null>(null)

const settingsOpen = ref(false)
const loginOpen = ref(false)
const runnerRef = ref<InstanceType<typeof CommandRunner> | null>(null)
const initialValues = ref<Record<string, string>>({})
const autoRun = ref(false)
/** ?demo=1：隐藏版本/账号/主人这三个 chip，方便截公开截图。 */
const demo = ref(false)

const { notify } = useToast()

const loggedIn = computed(() => Boolean(meta.value?.auth.ok && meta.value?.auth.user))
const spaceUrl = (mid: number | string) => `https://space.bilibili.com/${mid}`
const level = computed(() => meta.value?.auth.user?.level ?? '?')
const total = computed(() => groups.value.reduce((n, g) => n + g.items.length, 0))
const hasDuty = computed(() => groups.value.some((g) => g.items.some((i) => i.kind === 'duty')))

const q = computed(() => query.value.trim().toLowerCase())

/** 搜索：跨全部命令，命中 label / 命令名 / 描述 */
const matched = computed<CommandItem[]>(() => {
  if (!q.value) return []
  const out: CommandItem[] = []
  for (const g of groups.value) {
    for (const it of g.items) {
      const hay = `${it.label} ${it.cmd ?? it.argv.join(' ')} ${it.desc ?? ''}`.toLowerCase()
      if (hay.includes(q.value)) out.push(it)
    }
  }
  return out.slice(0, 30)
})

const currentGroup = computed(() => groups.value.find((g) => g.group === activeGroup.value) ?? null)

const visibleItems = computed<CommandItem[]>(() => {
  if (q.value) return matched.value
  return currentGroup.value?.items ?? []
})

const QUICK = ['video.watch', 'hot.rank', 'feed.inbox']

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
    results.value.unshift(res)
    if (results.value.length > 30) results.value.pop()
    if (!res.json?.ok && res.json?.error?.code === 'auth_expired') void loadMeta()
  } catch (err) {
    notify(`执行失败：${(err as Error).message}`, true)
  } finally {
    busy.value = false
    runnerRef.value?.setBusy(false)
  }
}

function choose(item: CommandItem) {
  initialValues.value = {}
  autoRun.value = false
  active.value = item
  view.value = 'cmd'
  // 选中命令时把分组切到它所在的组，否则命令 chips 里看不到它
  const g = groups.value.find((grp) => grp.items.some((i) => i.id === item.id))
  if (g) activeGroup.value = g.group
}

function pickGroup(name: string | null) {
  view.value = 'cmd'
  query.value = ''
  activeGroup.value = name
  if (name === null) {
    active.value = null
    nextTick(() => searchEl.value?.focus())
  }
}

function pickView(v: 'cmd' | 'runs' | 'duty') {
  if (v === 'duty') {
    const item = groups.value.flatMap((g) => g.items).find((i) => i.kind === 'duty')
    if (item) choose(item)
    else notify('命令表里没有值班命令', true)
    return
  }
  view.value = v
  if (v === 'cmd') nextTick(() => searchEl.value?.focus())
}

function quickPick(cmd: string) {
  const item = groups.value
    .flatMap((g) => g.items)
    .find((i) => (i.cmd ?? i.argv.join('.')) === cmd || i.id === cmd)
  if (item) choose(item)
}

function hotkey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    view.value = 'cmd'
    nextTick(() => {
      searchEl.value?.focus()
      searchEl.value?.select()
    })
  }
}

onMounted(async () => {
  try {
    const cat = await api.catalog()
    groups.value = cat.groups
    activeGroup.value = cat.groups[0]?.group ?? null
  } catch (err) {
    notify(`读取命令表失败：${(err as Error).message}`, true)
  }
  void loadMeta()
  window.addEventListener('keydown', hotkey)

  const qs = new URLSearchParams(location.search)
  demo.value = qs.get('demo') === '1'
  if (qs.get('settings') === '1') settingsOpen.value = true
  if (qs.get('login') === '1') loginOpen.value = true
  const cmdId = qs.get('cmd')
  if (!cmdId) return
  const item = groups.value.flatMap((g) => g.items).find((i) => i.id === cmdId)
  if (!item) return
  const preset: Record<string, string> = {}
  for (const p of item.params ?? []) {
    const v = qs.get(p.key)
    if (v != null) preset[p.key] = v
  }
  initialValues.value = preset
  active.value = item
  const owner = groups.value.find((g) => g.items.some((i) => i.id === item.id))
  if (owner) activeGroup.value = owner.group
  autoRun.value = qs.get('run') === '1'
  if (autoRun.value) await nextTick()
})

onUnmounted(() => window.removeEventListener('keydown', hotkey))
</script>

<template>
  <el-container class="shell" direction="vertical">
    <el-header class="topbar" height="58px">
      <div class="brand">
        <div class="brand-mark"><el-icon :size="15"><VideoPlay /></el-icon></div>
        <div class="brand-name">bili<span>·view</span></div>
      </div>

      <el-tag v-if="!demo" round effect="plain" type="info" size="small">v{{ meta?.version ?? '…' }}</el-tag>

      <!-- 账号 chip：点一下开自己的 B站 主页 -->
      <a
        v-if="!demo && meta?.auth.user"
        class="tag-link"
        :href="spaceUrl(meta.auth.user.mid)"
        target="_blank"
        rel="noreferrer"
        :title="`打开 ${meta.auth.user.name} 的B站主页`"
      >
        <el-tag round type="success" effect="plain" size="small">
          <span
            style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: currentColor; margin-right: 6px"
          />
          {{ meta.auth.user.name }} · Lv{{ level }}
          <el-icon class="tag-link-icon"><TopRight /></el-icon>
        </el-tag>
      </a>
      <el-tag v-else-if="!demo" round type="danger" effect="plain" size="small">未登录</el-tag>

      <!-- 主人 chip：同样可点 -->
      <a
        v-if="!demo && meta?.owner"
        class="tag-link"
        :href="spaceUrl(meta.owner.mid)"
        target="_blank"
        rel="noreferrer"
        :title="`打开 ${meta.owner.name} 的B站主页`"
      >
        <el-tag round effect="plain" type="info" size="small">
          主人 · {{ meta.owner.name }}
          <el-icon class="tag-link-icon"><TopRight /></el-icon>
        </el-tag>
      </a>

      <span class="spacer" />

      <el-button :icon="MagicStick" size="small" @click="loginOpen = true">
        {{ loggedIn ? '重新扫码' : '扫码登录' }}
      </el-button>
      <el-button :icon="Refresh" size="small" circle title="刷新账号状态" @click="loadMeta" />
    </el-header>

    <el-main class="main">
      <div class="layout">
        <RailNav
          :groups="groups"
          :active-group="activeGroup"
          :view="view"
          :has-duty="hasDuty"
          :owner="meta?.auth.user?.name"
          @pick-group="pickGroup"
          @pick-view="pickView"
          @settings="settingsOpen = true"
        />

        <section class="work">
          <!-- ── 运行记录 ── -->
          <template v-if="view === 'runs'">
            <div class="hero">
              <h1>运行记录</h1>
              <p>最近 {{ results.length }} 次执行，最新的在最前。</p>
            </div>
            <div v-if="!results.length" class="empty-block">
              <div class="halo"><el-icon :size="24"><Clock /></el-icon></div>
              <h4>还没跑过命令</h4>
              <p>回到命令台，挑一条运行一下就有了。</p>
            </div>
            <div v-else class="results">
              <ResultCard v-for="(res, i) in results" :key="i" :result="res" />
            </div>
          </template>

          <!-- ── 命令台 ── -->
          <template v-else>
            <DutyPanel v-if="active?.kind === 'duty'" />
            <DynamicPanel v-else-if="active?.kind === 'dynamic'" />
            <SeenPanel v-else-if="active?.kind === 'seen'" />
            <SelfCheckPanel v-else-if="active?.kind === 'selfcheck'" />

            <template v-else>
              <div v-if="!active" class="hero">
                <h1>想看点什么？</h1>
                <p>{{ total }} 条 bili 命令，搜一下就行 —— 不用记是哪个分组。</p>
              </div>

              <div class="search-hero" :class="{ 'is-focus': focused }">
                <el-icon><Search /></el-icon>
                <input
                  ref="searchEl"
                  v-model="query"
                  placeholder="搜命令 / UP主 / 视频号，比如「看懂」「BV1xT6」"
                  @focus="focused = true"
                  @blur="focused = false"
                />
                <span class="kbd">Ctrl K</span>
              </div>

              <!-- 分组 -->
              <div v-if="!q" class="picker">
                <div class="picker-head">
                  <h2>分组</h2>
                  <span>{{ groups.length }} 组 · {{ total }} 条命令</span>
                </div>
                <div class="picker-chips">
                  <button
                    v-for="g in groups"
                    :key="g.group"
                    class="p-chip"
                    :class="{ 'is-on': g.group === activeGroup }"
                    @click="pickGroup(g.group)"
                  >
                    {{ g.group }}<span class="cnt">{{ g.items.length }}</span>
                  </button>
                </div>
              </div>

              <!-- 命令 -->
              <div v-if="visibleItems.length" class="picker">
                <div class="picker-head">
                  <h2>{{ q ? '搜索结果' : '命令' }}</h2>
                  <span>{{ visibleItems.length }} 条</span>
                </div>
                <div class="picker-chips">
                  <button
                    v-for="it in visibleItems"
                    :key="it.id"
                    class="p-chip"
                    :class="{ 'is-on': active?.id === it.id }"
                    :title="it.cmd ?? it.argv.join(' ')"
                    @click="choose(it)"
                  >
                    {{ it.label }}<span v-if="it.write" class="w">写</span>
                  </button>
                </div>
              </div>

              <!-- 没限定分组又没搜索：给三个快捷入口 -->
              <div v-else-if="!active && !q" class="quick">
                <button class="qcard" @click="quickPick('video.watch')">
                  <span class="qi"><el-icon><VideoPlay /></el-icon></span>
                  <b>看懂视频</b>
                  <p>字幕、抽帧、热评，一次出全</p>
                  <code>video.watch</code>
                </button>
                <button class="qcard" @click="quickPick('hot.rank')">
                  <span class="qi"><el-icon><Clock /></el-icon></span>
                  <b>分区排行</b>
                  <p>按分区拉热榜，卡片直读</p>
                  <code>hot.rank</code>
                </button>
                <button class="qcard" @click="quickPick('feed.inbox')">
                  <span class="qi"><el-icon><Search /></el-icon></span>
                  <b>收件箱</b>
                  <p>回复、@、赞、未读数一次收齐</p>
                  <code>feed.inbox</code>
                </button>
              </div>

              <CommandRunner
                v-if="active"
                ref="runnerRef"
                :item="active"
                :initial="initialValues"
                :autorun="autoRun"
                @run="run"
              />

              <template v-if="results.length">
                <div class="section-h">
                  <h2>最新结果</h2>
                  <span>{{ results.length }} 条</span>
                  <button class="more" @click="view = 'runs'">全部记录 ›</button>
                </div>
                <ResultCard :result="results[0]" />
              </template>
              <div v-else-if="!active" class="empty-block" style="min-height: 210px">
                <div class="halo" style="width: 42px; height: 42px; border-radius: 13px">
                  <el-icon :size="19"><MagicStick /></el-icon>
                </div>
                <h4>挑一条命令运行</h4>
                <p style="margin-bottom: 0">
                  结果会以阅读流排在这里，一屏能看五条；写操作默认带 --dry-run 预览，不会真的发出去。
                </p>
              </div>
            </template>
          </template>
        </section>
      </div>
    </el-main>

    <footer v-if="meta?.bili">bili 可执行文件 · {{ meta.bili }}</footer>

    <SettingsModal :open="settingsOpen" @close="settingsOpen = false" @notify="notify" />
    <LoginModal
      :open="loginOpen"
      :logged-in="loggedIn"
      @close="loginOpen = false"
      @notify="notify"
      @refresh="loadMeta"
    />
  </el-container>
</template>
