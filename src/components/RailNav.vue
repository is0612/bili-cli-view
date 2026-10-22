<script setup lang="ts">
import { computed } from 'vue'
import { Clock, Search, Setting, Timer, VideoPlay } from '@element-plus/icons-vue'
import type { CommandGroup } from '../types'

const props = defineProps<{
  groups: CommandGroup[]
  activeGroup: string | null
  view: 'cmd' | 'runs'
  hasDuty: boolean
  owner?: string
}>()

const emit = defineEmits<{
  (e: 'pick-group', group: string | null): void
  (e: 'pick-view', view: 'cmd' | 'runs' | 'duty'): void
  (e: 'settings'): void
}>()

const total = computed(() => props.groups.reduce((n, g) => n + g.items.length, 0))
const initial = computed(() => (props.owner ?? '我').trim().slice(0, 1) || '我')
</script>

<template>
  <aside class="rail">
    <div class="rail-mark" title="bili·view">
      <el-icon :size="16"><VideoPlay /></el-icon>
    </div>

    <div
      class="rail-btn"
      :class="{ 'is-on': view === 'cmd' && activeGroup === null }"
      :title="`全部命令 · ${total} 条`"
      @click="emit('pick-group', null)"
    >
      <el-icon><Search /></el-icon>
    </div>

    <div
      class="rail-btn"
      :class="{ 'is-on': view === 'runs' }"
      title="运行记录"
      @click="emit('pick-view', 'runs')"
    >
      <el-icon><Clock /></el-icon>
    </div>

    <template v-if="hasDuty">
      <div class="rail-div" />
      <div
        class="rail-btn"
        :class="{ 'is-on': view === 'cmd' && activeGroup === '刷B站' }"
        title="自动值班"
        @click="emit('pick-view', 'duty')"
      >
        <el-icon><Timer /></el-icon>
      </div>
    </template>

    <div class="rail-foot">
      <div class="rail-btn" title="设置" @click="emit('settings')">
        <el-icon><Setting /></el-icon>
      </div>
      <div class="rail-ava" :title="owner ?? ''">{{ initial }}</div>
    </div>
  </aside>
</template>
