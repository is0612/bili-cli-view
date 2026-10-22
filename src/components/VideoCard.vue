<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '../api'
import { cardSubtitle, cardTitle, findImage, fmt, imgSrc, statBits } from '../utils/format'

const props = defineProps<{ node: Record<string, unknown> }>()

const broken = ref(false)
const title = computed(() => cardTitle(props.node) || '(无标题)')
const subtitle = computed(() => cardSubtitle(props.node))
const stats = computed(() => statBits(props.node))
const src = computed(() => {
  const own = findImage(props.node)
  if (own) return imgSrc(own)
  const bvid = props.node.bvid
  return typeof bvid === 'string' && bvid ? api.coverUrl(bvid) : ''
})
const url = computed(() => (typeof props.node.url === 'string' ? props.node.url : ''))
</script>

<template>
  <div class="vcard">
    <img
      v-if="src && !broken"
      class="thumb"
      :src="src"
      loading="lazy"
      alt=""
      @error="broken = true"
    />
    <div class="body">
      <div class="t">
        <a v-if="url" :href="url" target="_blank" rel="noreferrer">{{ title }}</a>
        <template v-else>{{ title }}</template>
      </div>
      <div v-if="subtitle" class="muted">{{ subtitle }}</div>
      <div class="s">
        <span v-for="(bit, i) in stats" :key="i">{{ bit }}</span>
      </div>
      <div v-if="node.bvid" class="muted">{{ node.bvid }}</div>
    </div>
  </div>
</template>
