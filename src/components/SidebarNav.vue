<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Clock, Search } from '@element-plus/icons-vue'
import type { CommandGroup, CommandItem } from '../types'

const props = defineProps<{
  groups: CommandGroup[]
  activeId: string | null
  view: 'cmd' | 'runs'
}>()

const emit = defineEmits<{
  (e: 'select', item: CommandItem): void
  (e: 'open-runs'): void
}>()

const query = ref('')
const searchRef = ref<any>(null)

defineExpose({ focusSearch: () => searchRef.value?.focus?.() })

/** 折叠状态：默认只展开当前命令所在组 + 第一个业务分组 */
const opened = ref<string[]>([])

const total = computed(() => props.groups.reduce((n, g) => n + g.items.length, 0))

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

/** 搜索时全展开，清空后回到默认展开 */
const openList = computed(() => (query.value.trim() ? filtered.value.map((g) => g.group) : opened.value))

/** 选中命令：把所在组加进展开列表，然后清空搜索切回折叠菜单 */
function pick(it: CommandItem) {
  const g = props.groups.find((grp) => grp.items.some((i) => i.id === it.id))
  if (g && !opened.value.includes(g.group)) opened.value = [...opened.value, g.group]
  emit('select', it)
  query.value = ''
}

watch(
  () => [props.activeId, props.groups.length],
  () => {
    const groups = props.groups
    if (!groups.length) return
    const cur = groups.find((g) => g.items.some((i) => i.id === props.activeId))
    if (cur && !opened.value.includes(cur.group)) {
      opened.value = opened.value.length ? [...opened.value, cur.group] : [cur.group]
      return
    }
    if (opened.value.length) return
    const first = groups[0]?.group
    opened.value = first ? [first] : []
  },
  { immediate: true },
)
</script>

<template>
  <aside class="side-panel">
    <div class="side-search">
      <el-input ref="searchRef" v-model="query" :placeholder="`搜索 ${total} 条命令…`" clearable>
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <div class="side-scroll">
      <button class="side-ov" :class="{ 'is-on': view === 'runs' }" @click="emit('open-runs')">
        <el-icon><Clock /></el-icon>
        <span>运行记录</span>
      </button>

      <!-- 搜索时用平铺列表，不搜索时用可折叠的分组菜单 -->
      <template v-if="query.trim()">
        <div v-for="g in filtered" :key="g.group" class="flat-group">
          <div class="flat-head">{{ g.group }} <em>{{ g.items.length }}</em></div>
          <button
            v-for="it in g.items"
            :key="it.id"
            class="nav-item"
            :class="{ 'is-on': activeId === it.id }"
            :title="it.cmd ?? it.argv.join(' ')"
            @click="pick(it)"
          >
            {{ it.label }}<span v-if="it.write" class="w">写</span>
          </button>
        </div>
        <div v-if="!filtered.length" class="nav-empty">没有匹配的命令（共 {{ total }} 条）</div>
      </template>

      <el-menu v-else :key="groups.length" :default-active="activeId ?? ''" :default-openeds="openList" class="side-menu">
        <el-sub-menu v-for="g in groups" :key="g.group" :index="g.group">
          <template #title>
            <span class="grp-name">{{ g.group }}</span>
            <span class="grp-cnt">{{ g.items.length }}</span>
          </template>
          <el-menu-item
            v-for="it in g.items"
            :key="it.id"
            :index="it.id"
            :title="it.cmd ?? it.argv.join(' ')"
            @click="pick(it)"
          >
            <span class="it-label">{{ it.label }}</span>
            <span v-if="it.write" class="w">写</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </div>
  </aside>
</template>
