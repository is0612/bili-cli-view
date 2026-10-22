<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, nextTick } from 'vue'
import { Clock, MagicStick, Refresh, Search, TopRight, VideoPlay } from '@element-plus/icons-vue'
import { api } from './api'
import CommandRunner from './components/CommandRunner.vue'
import DutyPanel from './components/DutyPanel.vue'
import DynamicPanel from './components/DynamicPanel.vue'
import SeenPanel from './components/SeenPanel.vue'
import SelfCheckPanel from './components/SelfCheckPanel.vue'
import LoginModal from './components/LoginModal.vue'
import ResultCard from './components/ResultCard.vue'
import SettingsModal from './components/SettingsModal.vue'
import SidebarNav from './components/SidebarNav.vue'
import { useToast } from './composables/useToast'
import type { CommandGroup, CommandItem, Meta, RunResult } from './types'

const groups = ref<CommandGroup[]>([])
const active = ref<CommandItem | null>(null)
const results = ref<RunResult[]>([])
const meta = ref<Meta | null>(null)
const busy = ref(false)

/** 工作区视图：命令台 / 运行记录 */
const view = ref<'cmd' | 'runs'>('cmd')

const settingsOpen = ref(false)
const loginOpen = ref(false)
const sideRef = ref<InstanceType<typeof SidebarNav> | null>(null)
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
const groupOf = (item: CommandItem | null) =>
  item ? (groups.value.find((g) => g.items.some((i) => i.id === item.id))?.group ?? '') : ''

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
}

function quickPick(cmd: string) {
  const item = groups.value
    .flatMap((g) => g.items)
    .find((i) => (i.cmd ?? i.argv.join('.')) === cmd || i.id === cmd)
  if (item) choose(item)
  else notify(`命令表里没有 ${cmd}`, true)
}

function hotkey(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    view.value = 'cmd'
    nextTick(() => sideRef.value?.focusSearch())
  }
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
  autoRun.value = qs.get('run') === '1'
  if (autoRun.value) await nextTick()
})

onUnmounted(() => window.removeEventListener('keydown', hotkey))
</script>

<template>
  <el-container class="shell" direction="vertical">
    <el-header class="topbar" height="60px">
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
        <SidebarNav
          ref="sideRef"
          :groups="groups"
          :active-id="active?.id ?? null"
          :view="view"
          @select="choose"
          @open-runs="view = 'runs'"
        />

        <section class="work">
          <!-- ── 运行记录 ── -->
          <template v-if="view === 'runs'">
            <div class="page-head">
              <div class="page-crumb">概览 <span>/</span> <b>运行记录</b></div>
              <h1>运行记录</h1>
              <p>最近 {{ results.length }} 次执行，最新的在最前。</p>
            </div>
            <div v-if="!results.length" class="empty-block">
              <div class="halo"><el-icon :size="22"><Clock /></el-icon></div>
              <h4>还没跑过命令</h4>
              <p>回到左侧菜单挑一条运行一下就有了。</p>
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
              <div v-if="!active" class="page-head">
                <div class="page-crumb">概览 <span>/</span> <b>命令台</b></div>
                <h1>从左边挑一条命令</h1>
                <p>
                  {{ groups.length }} 组 · {{ total }} 条命令，跟着 bili schema 自动更新。按 Ctrl K 可以直接搜。
                </p>
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
                  <span>{{ active ? `bili ${active.argv.join(' ')}` : `${results.length} 条` }}</span>
                  <button class="more" @click="view = 'runs'">全部记录 ›</button>
                </div>
                <ResultCard :result="results[0]" />
              </template>

              <div v-else-if="!active" class="quick">
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
