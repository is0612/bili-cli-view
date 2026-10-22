<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '../api'
import { cardSubtitle, cardTitle, findImage, fmtDur, imgSrc, statBits } from '../utils/format'

const props = defineProps<{ node: Record<string, unknown> }>()

const broken = ref(false)
const title = computed(() => cardTitle(props.node) || '(无标题)')
const subtitle = computed(() => cardSubtitle(props.node))
const stats = computed(() => statBits(props.node))
const duration = computed(() => (props.node.duration != null ? fmtDur(props.node.duration) : ''))
const src = computed(() => {
  const own = findImage(props.node)
  if (own) return imgSrc(own)
  const bvid = props.node.bvid
  return typeof bvid === 'string' && bvid ? api.coverUrl(bvid) : ''
})
const url = computed(() => (typeof props.node.url === 'string' ? props.node.url : ''))
</script>

<template>
  <el-card class="vcard" shadow="never" :body-style="{ padding: '0' }">
    <div v-if="src && !broken" class="cover">
      <img :src="src" loading="lazy" alt="" @error="broken = true" />
      <span v-if="duration" class="duration">{{ duration }}</span>
    </div>
    <div style="padding: 11px 12px 12px">
      <div class="title">
        <a v-if="url" :href="url" target="_blank" rel="noreferrer">{{ title }}</a>
        <template v-else>{{ title }}</template>
      </div>
      <div v-if="subtitle" class="sub">{{ subtitle }}</div>
      <div class="stats">
        <span v-for="(bit, i) in stats" :key="i">{{ bit }}</span>
      </div>
    </div>
  </el-card>
</template>
