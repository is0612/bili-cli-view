<script setup lang="ts">
import { computed } from 'vue'
import NodeView from './NodeView.vue'
import ErrorBoundary from './ErrorBoundary.vue'
import type { RunResult } from '../types'

const props = defineProps<{ result: RunResult }>()

const ok = computed(() => Boolean(props.result.json?.ok))
const error = computed(() => props.result.json?.error)
const raw = computed(() => JSON.stringify(props.result.json ?? {}, null, 2))
</script>

<template>
  <div class="card" :class="{ err: !ok }">
    <div class="res-head">
      <span class="pill" :class="ok ? 'ok' : 'bad'">
        {{ ok ? '成功' : `失败 ${result.code ?? ''}` }}
      </span>
      <span class="muted">bili {{ result.argv.join(' ') }}</span>
      <span class="muted">{{ result.elapsed }}s</span>
    </div>

    <template v-if="!result.json">
      <pre>{{ result.stdout || result.stderr || '(无输出)' }}</pre>
    </template>

    <template v-else-if="ok">
      <ErrorBoundary>
        <NodeView :node="result.json.data" />
      </ErrorBoundary>
    </template>

    <template v-else>
      <div class="msg">{{ error?.code || 'error' }}：{{ error?.message }}</div>
      <div v-if="error?.hint" class="hint">→ {{ error.hint }}</div>
    </template>

    <details v-if="result.json" style="margin-top: 10px">
      <summary>原始 JSON</summary>
      <pre>{{ raw }}</pre>
    </details>
  </div>
</template>
