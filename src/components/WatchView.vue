<script setup lang="ts">
import { computed } from 'vue'
import { TopRight } from '@element-plus/icons-vue'
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
    <div style="display: flex; align-items: flex-start; gap: 14px; flex-wrap: wrap">
      <div style="min-width: 0; flex: 1">
        <div class="watch-title">{{ node.title }}</div>
        <div class="watch-meta">
          <span v-if="owner">{{ owner }}</span>
          <span v-if="node.duration">· {{ fmtDur(node.duration) }}</span>
          <span v-if="stat">
            · ▶ {{ fmt(stat.view) }} · 👍 {{ fmt(stat.like) }} · 💬 {{ fmt(stat.danmaku) }} · ↩
            {{ fmt(stat.reply ?? 0) }}
          </span>
        </div>
      </div>
      <el-button v-if="node.url" tag="a" :href="node.url" target="_blank" size="small">
        打开 <el-icon style="margin-left: 4px"><TopRight /></el-icon>
      </el-button>
    </div>

    <div v-if="tags.length" style="margin-top: 12px">
      <el-tag
        v-for="tag in tags"
        :key="tag"
        size="small"
        effect="plain"
        style="margin: 0 6px 6px 0"
        >{{ tag }}</el-tag
      >
    </div>

    <div v-if="node.ai_summary" class="summary-block">{{ node.ai_summary }}</div>

    <el-collapse v-if="transcript?.text || comments.length" style="margin-top: 14px">
      <el-collapse-item
        v-if="transcript?.text"
        :title="`字幕全文 · ${transcript.text.length} 字（${transcript.source || ''}）`"
        name="transcript"
      >
        <pre class="code">{{ transcript.text }}</pre>
      </el-collapse-item>
      <el-collapse-item v-if="comments.length" :title="`热评 · ${comments.length} 条`" name="comments">
        <div class="kv">
          <template v-for="(c, i) in comments" :key="i">
            <div class="k">{{ c.user }}</div>
            <div class="v">
              {{ c.content }}<span v-if="c.like != null" class="muted"> ❤{{ c.like }}</span>
            </div>
          </template>
        </div>
      </el-collapse-item>
    </el-collapse>

    <el-image
      v-if="sheet"
      :src="sheet"
      :preview-src-list="[sheet]"
      fit="cover"
      style="width: 100%; aspect-ratio: 16 / 9; margin-top: 14px; border-radius: 14px; border: 1px solid var(--line)"
    />
  </div>
</template>
