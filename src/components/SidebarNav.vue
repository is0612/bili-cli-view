<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  Aim,
  ArrowRight,
  Bell,
  ChatDotRound,
  Clock,
  Close,
  Expand,
  Film,
  Fold,
  Folder,
  Grid,
  Message,
  Monitor,
  Operation,
  Promotion,
  Reading,
  Search,
  Setting,
  Star,
  Tickets,
  TrendCharts,
  VideoPlay,
  View,
} from '@element-plus/icons-vue'
import type { CommandGroup, CommandItem } from '../types'

const props = defineProps<{
  groups: CommandGroup[]
  activeId: string | null
  view: 'home' | 'cmd' | 'runs'
  runCount: number
  rail: boolean
}>()

const emit = defineEmits<{
  (e: 'select', item: CommandItem): void
  (e: 'open-home'): void
  (e: 'open-runs'): void
  (e: 'manage-menu'): void
  (e: 'toggle-rail'): void
}>()

const query = ref('')
const searchRef = ref<any>(null)

defineExpose({ focusSearch: () => searchRef.value?.focus?.() })

const total = computed(() => props.groups.reduce((n, g) => n + g.items.length, 0))
const allItems = computed(() => props.groups.flatMap((g) => g.items))

/* ── 常用：固定项存 localStorage，点星标可以取消固定 ────── */
const PIN_KEY = 'bili-desk:pins'
const DEFAULT_PINS = ['video.watch', 'hot.rank', 'feed.inbox', 'duty.settings']

function readPins(): string[] {
  try {
    const raw = localStorage.getItem(PIN_KEY)
    if (!raw) return [...DEFAULT_PINS]
    const arr: unknown = JSON.parse(raw)
    return Array.isArray(arr) ? arr.filter((x): x is string => typeof x === 'string') : [...DEFAULT_PINS]
  } catch {
    return [...DEFAULT_PINS]
  }
}

const pinKeys = ref<string[]>(readPins())

function savePins() {
  try {
    localStorage.setItem(PIN_KEY, JSON.stringify(pinKeys.value))
  } catch {
    /* 隐私模式下写不进去，忽略 */
  }
}

function findItem(key: string): CommandItem | undefined {
  return allItems.value.find(
    (i) => i.id === key || i.cmd === key || i.argv.join('.') === key || i.argv.join(' ') === key,
  )
}

/** 只渲染在命令表里真的存在的固定项（隐藏了菜单就自然不显示） */
const pins = computed(() =>
  pinKeys.value.flatMap((key) => {
    const item = findItem(key)
    return item ? [{ key, item }] : []
  }),
)

const PIN_ICON: Record<string, any> = {
  'video.watch': View,
  'hot.rank': TrendCharts,
  'feed.inbox': Bell,
  'duty.settings': Setting,
}

/** 常用项用短名：命令表里的「一次看完所有新消息」放侧栏会把其它项挤歪 */
const PIN_LABEL: Record<string, string> = {
  'video.watch': '看懂视频',
  'hot.rank': '排行榜',
  'feed.inbox': '收件箱',
  'duty.settings': '值班设置',
}

const pinLabel = (it: CommandItem) => PIN_LABEL[it.id] ?? it.label

function pinIcon(it: CommandItem) {
  for (const k of [it.cmd, it.id, it.argv.join('.')]) {
    if (k && PIN_ICON[k]) return PIN_ICON[k]
  }
  return Star
}

function unpin(key: string, e: MouseEvent) {
  e.stopPropagation()
  pinKeys.value = pinKeys.value.filter((x) => x !== key)
  savePins()
}

function restorePins() {
  pinKeys.value = [...DEFAULT_PINS]
  savePins()
}

/* ── 全部命令：就地折叠树 ──────────────────────────────── */
const GROUP_ICON: Record<string, any> = {
  刷B站: Promotion,
  面板: Grid,
  账号: Tickets,
  发现: View,
  视频: VideoPlay,
  搜索: Search,
  用户: Aim,
  动态: ChatDotRound,
  专栏: Reading,
  评论: Message,
  直播: Monitor,
  收藏: Star,
  历史: Clock,
  消息: Message,
  工具箱: Operation,
  电影: Film,
}

const groupIcon = (name: string) => GROUP_ICON[name] ?? Folder

const opened = ref<string[]>([])

function toggle(group: string) {
  opened.value = opened.value.includes(group)
    ? opened.value.filter((x) => x !== group)
    : [...opened.value, group]
}

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.groups
  return props.groups
    .map((g) => ({
      ...g,
      items: g.items.filter(
        (i) =>
          i.label.toLowerCase().includes(q) ||
          (i.cmd ?? i.argv.join(' ')).toLowerCase().includes(q) ||
          (i.desc ?? '').toLowerCase().includes(q),
      ),
    }))
    .filter((g) => g.items.length > 0)
})

/** 搜索时全展开，清空后回到用户手工展开的状态 */
const isOpen = (group: string) => Boolean(query.value.trim()) || opened.value.includes(group)

function pick(it: CommandItem) {
  const g = props.groups.find((grp) => grp.items.some((i) => i.id === it.id))
  if (g && !opened.value.includes(g.group)) opened.value = [...opened.value, g.group]
  emit('select', it)
  query.value = ''
}

/* 默认展开：当前命令所在组；没有选中就展开第一组 */
watch(
  () => [props.activeId, props.groups.length] as const,
  () => {
    const groups = props.groups
    if (!groups.length) return
    const cur = groups.find((g) => g.items.some((i) => i.id === props.activeId))
    if (cur && !opened.value.includes(cur.group)) {
      opened.value = [...opened.value, cur.group]
      return
    }
    // 没有选中命令时全部折叠：14 组一眼扫完，比默认展开第一组好找

  },
  { immediate: true },
)
</script>

<template>
  <aside class="side" :class="{ rail }">
    <div class="side-head">
      <el-input
        ref="searchRef"
        v-model="query"
        :placeholder="`搜索 ${total} 条命令`"
        clearable
        :title="'按 Ctrl K 直接定位到这里'"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
        <template #suffix>
          <kbd>Ctrl K</kbd>
        </template>
      </el-input>
    </div>

    <div class="side-scroll">
      <!-- ① 工作台：视图入口，不是命令 -->
      <div class="sec-label">工作台</div>
      <button class="nav-ov" :class="{ on: view === 'home' }" title="概览" @click="emit('open-home')">
        <el-icon><Grid /></el-icon>
        <span>概览</span>
      </button>
      <button class="nav-ov" :class="{ on: view === 'runs' }" title="运行记录" @click="emit('open-runs')">
        <el-icon><Clock /></el-icon>
        <span>运行记录</span>
        <span v-if="runCount" class="cnt">{{ runCount }}</span>
      </button>

      <!-- ② 常用：只有 4 条，日常 90% 的操作都在这里 -->
      <template v-if="!query.trim()">
        <div class="sec-label">
          常用<span class="cnt">{{ pins.length }} 条</span>
        </div>
        <button
          v-for="p in pins"
          :key="p.key"
          class="pin"
          :class="{ on: view === 'cmd' && activeId === p.item.id }"
          :title="p.item.cmd ?? p.item.argv.join(' ')"
          @click="pick(p.item)"
        >
          <el-icon class="pi"><component :is="pinIcon(p.item)" /></el-icon>
          <span class="pl">{{ pinLabel(p.item) }}</span>
          <span class="pin-mark" title="取消固定" @click="unpin(p.key, $event)">
            <el-icon><Close /></el-icon>
          </span>
        </button>
        <div v-if="!pins.length" class="side-empty">
          常用栏空了<br />
          <button @click="restorePins">恢复默认 4 条</button>
        </div>
      </template>

      <!-- ③ 全部命令：就地折叠，不弹窗 -->
      <div class="sec-label">
        全部命令<span class="cnt">{{ groups.length }} 组 · {{ total }} 条</span>
      </div>
      <div v-for="g in filtered" :key="g.group" class="grp-wrap" :class="{ open: isOpen(g.group) }">
        <button class="grp" :title="g.group" @click="toggle(g.group)">
          <el-icon class="gi"><component :is="groupIcon(g.group)" /></el-icon>
          <span class="grn">{{ g.group }}</span>
          <span class="cnt">{{ g.items.length }}</span>
          <el-icon class="chev"><ArrowRight /></el-icon>
        </button>
        <div class="items">
          <button
            v-for="it in g.items"
            :key="it.id"
            class="item"
            :class="{ on: view === 'cmd' && activeId === it.id }"
            :title="it.cmd ?? it.argv.join(' ')"
            @click="pick(it)"
          >
            <span class="lb">{{ it.label }}</span>
            <span v-if="it.write" class="w-tag">写</span>
          </button>
        </div>
      </div>

      <div v-if="!groups.length" class="side-empty">
        菜单都被藏起来了<br />
        <button @click="emit('manage-menu')">点这里勾回来</button>
      </div>
      <div v-else-if="query.trim() && !filtered.length" class="side-empty">
        没有匹配「{{ query }}」的命令<br />共 {{ total }} 条
      </div>
    </div>

    <div class="side-foot">
      <button title="管理菜单：勾选要显示的命令" @click="emit('manage-menu')">
        <el-icon><Operation /></el-icon><span>管理菜单</span>
      </button>
      <button :title="rail ? '展开侧栏' : '收起侧栏，把宽度让给内容'" @click="emit('toggle-rail')">
        <el-icon><component :is="rail ? Expand : Fold" /></el-icon>
        <span>{{ rail ? '展开' : '收起' }}</span>
      </button>
    </div>
  </aside>
</template>
