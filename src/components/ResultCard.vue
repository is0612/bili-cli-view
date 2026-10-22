<script setup lang="ts">
import { computed } from 'vue'
import { CopyDocument } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ErrorBoundary from './ErrorBoundary.vue'
import NodeView from './NodeView.vue'
import type { RunResult } from '../types'

const props = defineProps<{ result: RunResult }>()

const ok = computed(() => Boolean(props.result.json?.ok))
const error = computed(() => props.result.json?.error)
const raw = computed(() => JSON.stringify(props.result.json ?? {}, null, 2))

async function copyJson() {
  try {
    await navigator.clipboard.writeText(raw.value)
    ElMessage.success({ message: 'JSON 已复制', grouping: true })
  } catch {
    ElMessage.warning({ message: '剪贴板不可用', grouping: true })
  }
}
</script>

<template>
  <el-card class="result-card" :class="{ 'is-error': !ok }" shadow="never">
    <div class="res-head">
      <el-tag :type="ok ? 'success' : 'danger'" effect="dark" round size="small" disable-transitions>
        {{ ok ? '执行成功' : `失败 · ${result.code ?? ''}` }}
      </el-tag>
      <span class="cmd-chip">bili {{ result.argv.join(' ') }}</span>
      <span class="res-time">
        {{ result.elapsed }}s
        <el-button link size="small" @click="copyJson">
          <el-icon><CopyDocument /></el-icon>
        </el-button>
      </span>
    </div>

    <template v-if="!result.json">
      <pre class="code">{{ result.stdout || result.stderr || '(无输出)' }}</pre>
    </template>

    <template v-else-if="ok">
      <ErrorBoundary>
        <NodeView :node="result.json.data" />
      </ErrorBoundary>
    </template>

    <template v-else>
      <el-alert
        :title="`${error?.code || 'error'}：${error?.message}`"
        :description="error?.hint ? `→ ${error.hint}` : undefined"
        type="error"
        :closable="false"
        show-icon
      />
    </template>

    <el-collapse v-if="result.json" style="margin-top: 12px">
      <el-collapse-item title="原始 JSON" name="raw">
        <pre class="code">{{ raw }}</pre>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>
