<script setup lang="ts">
import type { CommandGroup, CommandItem } from '../types'

defineProps<{
  groups: CommandGroup[]
  activeId: string | null
}>()

const emit = defineEmits<{
  (e: 'select', item: CommandItem): void
}>()
</script>

<template>
  <aside class="sidebar">
    <template v-for="group in groups" :key="group.group">
      <div class="nav-group-title">{{ group.group }}</div>
      <div
        v-for="item in group.items"
        :key="item.id"
        class="nav-item"
        :class="{ active: item.id === activeId, write: item.write }"
        @click="emit('select', item)"
      >
        <span class="dot" />
        <span>{{ item.label }}</span>
      </div>
    </template>
  </aside>
</template>
