<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  Bell,
  ChatDotRound,
  DataLine,
  Grid,
  Search,
  Setting,
  TrendCharts,
  User,
  VideoPlay,
} from '@element-plus/icons-vue'
import type { CommandGroup, CommandItem } from '../types'

const props = defineProps<{ groups: CommandGroup[]; activeId: string | null }>()
const emit = defineEmits<{ (e: 'select', item: CommandItem): void }>()

const query = ref('')

const GROUP_ICON: Record<string, unknown> = {
  账号: User,
  收件箱: Bell,
  发现: TrendCharts,
  视频: VideoPlay,
  互动: ChatDotRound,
  动态: DataLine,
  数据: Grid,
  系统: Setting,
}

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.groups
  return props.groups
    .map((g) => ({
      ...g,
      items: g.items.filter(
        (i) => i.label.toLowerCase().includes(q) || i.argv.join(' ').toLowerCase().includes(q),
      ),
    }))
    .filter((g) => g.items.length > 0)
})

const total = computed(() => props.groups.reduce((n, g) => n + g.items.length, 0))
</script>

<template>
  <aside class="side-panel">
    <div class="side-search">
      <el-input v-model="query" placeholder="搜索命令…" clearable>
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <div class="side-scroll">
      <template v-for="group in filtered" :key="group.group">
        <div class="nav-group-title">
          <span>{{ group.group }}</span>
          <em>{{ group.items.length }}</em>
        </div>
        <el-menu :default-active="activeId ?? ''" :collapse="false">
          <el-menu-item
            v-for="item in group.items"
            :key="item.id"
            :index="item.id"
            @click="emit('select', item)"
          >
            <el-icon class="ico"><component :is="GROUP_ICON[group.group] ?? Grid" /></el-icon>
            <span>{{ item.label }}</span>
            <el-tag v-if="item.write" size="small" type="warning" effect="plain" round style="margin-left: auto">
              写
            </el-tag>
          </el-menu-item>
        </el-menu>
      </template>

      <div v-if="!filtered.length" class="nav-empty">没有匹配的命令（共 {{ total }} 条）</div>
    </div>
  </aside>
</template>
