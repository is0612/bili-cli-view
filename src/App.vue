<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { MagicStick, Refresh, Setting, TopRight, VideoPlay } from '@element-plus/icons-vue'
import { api } from './api'
import CommandRunner from './components/CommandRunner.vue'
import DutyPanel from './components/DutyPanel.vue'
import DynamicPanel from './components/DynamicPanel.vue'
import SeenPanel from './components/SeenPanel.vue'
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
    if (results.value.length > 12) results.value.pop()
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
}

onMounted(async () => {
  try {
    const cat = await api.catalog()
    groups.value = cat.groups
  } catch (err) {
    notify(`读取命令表失败：${(err as Error).message}`, true)
  }
  void loadMeta()

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
</script>

<template>
  <el-container class="shell" direction="vertical">
    <el-header class="topbar" height="64px">
      <div class="brand">
        <div class="brand-mark"><el-icon :size="16"><VideoPlay /></el-icon></div>
        <div class="brand-name">bili<span>·view</span></div>
      </div>

      <el-tag v-if="!demo" round effect="plain" type="info" size="default">v{{ meta?.version ?? '…' }}</el-tag>

      <!-- 账号 chip：点一下开自己的 B站 主页 -->
      <a
        v-if="!demo && meta?.auth.user"
        class="tag-link"
        :href="spaceUrl(meta.auth.user.mid)"
        target="_blank"
        rel="noreferrer"
        :title="`打开 ${meta.auth.user.name} 的B站主页`"
      >
        <el-tag round type="success" effect="plain">
          <span
            style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: currentColor; margin-right: 6px"
          />
          {{ meta.auth.user.name }} · Lv{{ level }}
          <el-icon class="tag-link-icon"><TopRight /></el-icon>
        </el-tag>
      </a>
      <el-tag v-else-if="!demo" round type="danger" effect="plain">未登录</el-tag>

      <!-- 主人 chip：同样可点 -->
      <a
        v-if="!demo && meta?.owner"
        class="tag-link"
        :href="spaceUrl(meta.owner.mid)"
        target="_blank"
        rel="noreferrer"
        :title="`打开 ${meta.owner.name} 的B站主页`"
      >
        <el-tag round effect="plain" type="info">
          主人 · {{ meta.owner.name }}
          <el-icon class="tag-link-icon"><TopRight /></el-icon>
        </el-tag>
      </a>

      <span class="spacer" />

      <el-button :icon="Setting" @click="settingsOpen = true">设置</el-button>
      <el-button :icon="MagicStick" @click="loginOpen = true">
        {{ loggedIn ? '重新扫码' : '扫码登录' }}
      </el-button>
      <el-button :icon="Refresh" @click="loadMeta">刷新</el-button>
    </el-header>

    <el-main class="main">
      <div class="layout">
        <SidebarNav :groups="groups" :active-id="active?.id ?? null" @select="choose" />

        <section class="work">
          <DutyPanel v-if="active?.kind === 'duty'" />
          <DynamicPanel v-else-if="active?.kind === 'dynamic'" />
          <SeenPanel v-else-if="active?.kind === 'seen'" />

          <template v-else>
            <CommandRunner
              v-if="active"
              ref="runnerRef"
              :item="active"
              :initial="initialValues"
              :autorun="autoRun"
              @run="run"
            />

            <div v-if="!results.length" class="empty-block">
              <div class="halo"><el-icon :size="24"><MagicStick /></el-icon></div>
              <h4>{{ active ? '执行一下试试' : '从左边挑一条命令' }}</h4>
              <p>
                视频、字幕、热评、UP 主数据都会渲染成卡片；写操作默认带 --dry-run 预览，不会真的发出去。
              </p>
              <div style="display: flex; gap: 7px; flex-wrap: wrap; justify-content: center">
                <el-tag effect="plain" size="small">video.watch 看懂视频</el-tag>
                <el-tag effect="plain" size="small">hot.rank 分区排行</el-tag>
                <el-tag effect="plain" size="small">feed.inbox 收件箱</el-tag>
              </div>
            </div>

            <div v-else class="results" style="display: flex; flex-direction: column; gap: 14px">
              <ResultCard v-for="(res, i) in results" :key="i" :result="res" />
            </div>
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
