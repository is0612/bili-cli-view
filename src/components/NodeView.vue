<script setup lang="ts">
import { computed } from 'vue'
import VideoCard from './VideoCard.vue'
import WatchView from './WatchView.vue'
import { cardSubtitle, cardTitle, findImage, imgSrc, looksLikeImage, isVideoLike, isWatchLike } from '../utils/format'

const props = defineProps<{ node: unknown }>()

const kind = computed(() => {
  const n = props.node
  if (n === null || n === undefined) return 'empty'
  if (typeof n === 'string') {
    if (looksLikeImage(n)) return 'image'
    return n.length > 600 ? 'longtext' : 'text'
  }
  if (typeof n === 'number' || typeof n === 'boolean') return 'text'
  if (Array.isArray(n)) return n.length ? 'array' : 'empty'
  if (typeof n === 'object') {
    const obj = n as Record<string, unknown>
    if (isWatchLike(obj)) return 'watch'
    if (isVideoLike(obj)) return 'video'
    if (Array.isArray(obj.items) && obj.items.length) return 'items'
    return 'object'
  }
  return 'text'
})

const asArray = computed(() => (Array.isArray(props.node) ? (props.node as unknown[]) : []))

const cardsOnly = computed(() =>
  asArray.value.every((x) => x && typeof x === 'object' && (findImage(x as any) || (x as any).bvid)),
)

const objectEntries = computed(() => {
  if (typeof props.node !== 'object' || props.node === null || Array.isArray(props.node)) return []
  return Object.entries(props.node as Record<string, unknown>).filter(([, v]) => {
    if (v === null || v === '') return false
    if (Array.isArray(v) && v.length === 0) return false
    return true
  })
})

const items = computed(() => {
  const obj = props.node as Record<string, unknown> | null
  return obj && Array.isArray(obj.items) ? (obj.items as Record<string, unknown>[]) : []
})

function isTagArray(v: unknown): v is string[] {
  return Array.isArray(v) && v.length > 0 && v.every((x) => typeof x === 'string' && x.length < 24)
}
</script>

<template>
  <!-- 空 -->
  <div v-if="kind === 'empty'" class="muted">(空)</div>

  <!-- 图片 -->
  <img
    v-else-if="kind === 'image'"
    :src="imgSrc(node as string)"
    alt=""
    style="max-width: 100%; border-radius: 10px"
  />

  <!-- 长文本 -->
  <details v-else-if="kind === 'longtext'">
    <summary>展开全文（{{ (node as string).length }} 字）</summary>
    <pre>{{ node }}</pre>
  </details>

  <!-- 基本类型 -->
  <div v-else-if="kind === 'text'">{{ node }}</div>

  <!-- 数组 -->
  <template v-else-if="kind === 'array'">
    <div v-if="cardsOnly" class="grid">
      <VideoCard v-for="(item, i) in asArray" :key="i" :node="item as Record<string, unknown>" />
    </div>
    <div v-else class="kv">
      <template v-for="(item, i) in asArray" :key="i">
        <div class="k">#{{ i + 1 }}</div>
        <div class="v">
          <template v-if="item && typeof item === 'object'">
            <div>{{ cardTitle(item as Record<string, unknown>) }}</div>
            <div v-if="cardSubtitle(item as Record<string, unknown>)" class="muted">
              {{ cardSubtitle(item as Record<string, unknown>) }}
            </div>
          </template>
          <template v-else>{{ item }}</template>
        </div>
      </template>
    </div>
  </template>

  <!-- 看懂视频 -->
  <WatchView v-else-if="kind === 'watch'" :node="node as Record<string, any>" />

  <!-- 视频卡片 -->
  <VideoCard v-else-if="kind === 'video'" :node="node as Record<string, unknown>" />

  <!-- 列表容器 -->
  <div v-else-if="kind === 'items'" class="grid">
    <VideoCard v-for="(item, i) in items" :key="i" :node="item" />
  </div>

  <!-- 普通对象 -->
  <div v-else class="kv">
    <template v-for="[key, value] in objectEntries" :key="key">
      <div class="k">{{ key }}</div>
      <div class="v">
        <span v-if="isTagArray(value)">
          <span v-for="tag in value" :key="tag" class="tag">{{ tag }}</span>
        </span>
        <details v-else-if="value && typeof value === 'object'">
          <summary>展开 {{ key }}</summary>
          <NodeView :node="value" />
        </details>
        <NodeView v-else :node="value" />
      </div>
    </template>
  </div>
</template>
