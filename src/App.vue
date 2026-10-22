<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { api } from './api'
import CommandRunner from './components/CommandRunner.vue'
import LoginModal from './components/LoginModal.vue'
import ResultCard from './components/ResultCard.vue'
import SettingsModal from './components/SettingsModal.vue'
import SidebarNav from './components/SidebarNav.vue'
import type { CommandGroup, CommandItem, Meta, RunResult } from './types'

const groups = ref<CommandGroup[]>([])
const active = ref<CommandItem | null>(null)
const results = ref<RunResult[]>([])
const meta = ref<Meta | null>(null)
const busy = ref(false)

const settingsOpen = ref(false)
const loginOpen = ref(false)
const runnerRef = ref<InstanceType<typeof CommandRunner> | null>(null)
const initialValues = ref<Record<string, string>>({})
const autoRun = ref(false)

const toast = ref<{ text: string; error: boolean } | null>(null)
let toastTimer: ReturnType<typeof setTimeout> | undefined

function notify(text: string, error = false) {
  toast.value = { text, error }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = null), 4000)
}

const loggedIn = computed(() => Boolean(meta.value?.auth.ok && meta.value?.auth.user))

async function loadMeta() {
  try {
    meta.value = await api.meta()
  } catch (err) {
    notify(`读取账号状态失败：${(err as Error).message}`, true)
  }
}

async function run(argv: string[]) {
  busy.value = true
  try {
    const res = await api.run(argv)
    results.value.unshift(res)
    if (results.value.length > 12) results.value.pop()
    if (!res.json?.ok && res.json?.error?.code === 'auth_expired') void loadMeta()
  } catch (err) {
    notify(`执行失败：${(err as Error).message}`, true)
  } finally {
    busy.value = false
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

  // 深链：?cmd=video.watch&video_id=BV…&run=1 ；?settings=1 / ?login=1 直接开弹层
  const qs = new URLSearchParams(location.search)
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
</script>

<template>
  <div class="app">
    <header class="topbar">
      <div class="logo">bili<b>·</b>view</div>
      <span class="chip">{{ meta?.version ? `bili ${meta.version}` : '…' }}</span>
      <span class="chip" :class="loggedIn ? 'ok' : 'bad'">
        {{ loggedIn ? `● ${meta?.auth.user?.name}（Lv${meta?.auth.user?.level ?? '?'}）` : '○ 未登录' }}
      </span>
      <span v-if="meta?.owner" class="chip">主人：{{ meta.owner.name }}</span>
      <span class="spacer" />
      <button class="btn" @click="settingsOpen = true">⚙ 设置</button>
      <button class="btn" @click="loginOpen = true">{{ loggedIn ? '重新扫码' : '扫码登录' }}</button>
      <button class="btn" @click="loadMeta">刷新状态</button>
    </header>

    <div class="layout">
      <SidebarNav
        :groups="groups"
        :active-id="active?.id ?? null"
        @select="(item) => { initialValues = {}; autoRun = false; active = item }"
      />

      <section class="work">
        <CommandRunner
          v-if="active"
          ref="runnerRef"
          :item="active"
          :initial="initialValues"
          :autorun="autoRun"
          @run="run"
        />
        <div v-else class="card">
          <h3>选择左边任意一条命令</h3>
          <div class="muted">
            80+ 条命令里的常用集。结果渲染成卡片；写操作默认带
            <code>--dry-run</code> 预览。
          </div>
        </div>

        <div class="results">
          <ResultCard v-for="(res, i) in results" :key="i" :result="res" />
        </div>
      </section>
    </div>

    <footer v-if="meta?.bili">bili 可执行文件：{{ meta.bili }}</footer>

    <SettingsModal :open="settingsOpen" @close="settingsOpen = false" @notify="notify" />
    <LoginModal
      :open="loginOpen"
      :logged-in="loggedIn"
      @close="loginOpen = false"
      @notify="notify"
      @refresh="loadMeta"
    />

    <div v-if="toast" class="toast" :class="{ error: toast.error }">{{ toast.text }}</div>
  </div>
</template>
