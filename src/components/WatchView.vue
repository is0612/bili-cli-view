<script setup lang="ts">
import { computed } from 'vue'
import { fmt, fmtDur, imgSrc } from '../utils/format'

interface Comment {
  user?: string
  content?: string
  like?: number
}

const props = defineProps<{ node: Record<string, any> }>()

const owner = computed(() => (props.node.owner?.name as string) || '')
const tags = computed<string[]>(() => props.node.tags ?? [])
const stat = computed<Record<string, number> | undefined>(() => props.node.stat)
const transcript = computed<{ source?: string; text?: string } | undefined>(() => props.node.transcript)
const comments = computed<Comment[]>(() => props.node.hot_comments ?? [])
const sheet = computed(() =>
  typeof props.node.frames_sheet === 'string' ? imgSrc(props.node.frames_sheet) : '',
)
</script>

<template>
  <div>
    <div class="kv">
      <div class="k">标题</div>
      <div class="v">{{ node.title }}</div>
      <div class="k">UP</div>
      <div class="v">{{ owner }}</div>
      <div class="k">时长</div>
      <div class="v">{{ fmtDur(node.duration) }}</div>
      <div v-if="stat" class="k">数据</div>
      <div v-if="stat" class="v">
        ▶{{ fmt(stat.view) }} 👍{{ fmt(stat.like) }} 💬{{ fmt(stat.danmaku) }} ↩{{ fmt(stat.reply ?? 0) }}
      </div>
    </div>

    <div v-if="tags.length" style="margin-top: 10px">
      <span v-for="tag in tags" :key="tag" class="tag">{{ tag }}</span>
    </div>

    <div v-if="node.ai_summary" style="margin-top: 12px">
      <div class="muted">AI 总结</div>
      <div>{{ node.ai_summary }}</div>
    </div>

    <details v-if="transcript?.text" style="margin-top: 10px">
      <summary>
        字幕全文（{{ transcript.text.length }} 字，来源 {{ transcript.source || '未知' }}）
      </summary>
      <pre>{{ transcript.text }}</pre>
    </details>

    <img
      v-if="sheet"
      :src="sheet"
      alt=""
      style="max-width: 100%; margin-top: 12px; border-radius: 10px"
    />

    <details v-if="comments.length" style="margin-top: 10px">
      <summary>热评（{{ comments.length }} 条）</summary>
      <div class="kv">
        <template v-for="(c, i) in comments" :key="i">
          <div class="k">{{ c.user }}</div>
          <div class="v">{{ c.content }}<span v-if="c.like != null">  ❤{{ c.like }}</span></div>
        </template>
      </div>
    </details>

    <div v-if="node.url" style="margin-top: 12px">
      <a :href="node.url" target="_blank" rel="noreferrer">{{ node.url }}</a>
    </div>
  </div>
</template>
