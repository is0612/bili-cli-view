<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, CircleCheck, WarningFilled } from '@element-plus/icons-vue'
import { api } from '../api'

interface Check {
  name: string
  ok: boolean
  detail: string
  hint: string
}

const loading = ref(false)
const result = ref<{ ok: boolean; version: string | null; checks: Check[]; advice: string } | null>(null)

async function run() {
  loading.value = true
  try {
    result.value = await api.selfcheck()
  } catch (err) {
    ElMessage.error({ message: `自检失败：${(err as Error).message}`, grouping: true })
  } finally {
    loading.value = false
  }
}

onMounted(run)
</script>

<template>
  <el-card class="runner-card" shadow="never" v-loading="loading">
    <div class="runner-head">
      <div class="runner-icon">
        <el-icon :size="17"><CircleCheck /></el-icon>
      </div>
      <div style="min-width: 0; flex: 1">
        <div class="runner-title">
          升级自检
          <el-tag
            v-if="result"
            :type="result.ok ? 'success' : 'danger'"
            effect="dark"
            size="small"
            round
            disable-transitions
          >
            {{ result.ok ? '全部通过' : '有问题' }}
          </el-tag>
          <el-tag v-if="result?.version" type="info" effect="plain" size="small" round disable-transitions>
            bili {{ result.version }}
          </el-tag>
        </div>
        <div class="cmd-chip" style="margin-top: 7px">
          检查面板依赖的命令与字段，bili 升级后跑一遍就知道要不要改代码
        </div>
      </div>
      <el-button :icon="Refresh" text @click="run">重新自检</el-button>
    </div>

    <el-alert
      v-if="result"
      :type="result.ok ? 'success' : 'warning'"
      :title="result.advice"
      :closable="false"
      show-icon
      style="margin-top: 14px"
    />

    <div v-if="result" style="margin-top: 14px">
      <div
        v-for="c in result.checks"
        :key="c.name"
        style="
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 11px 0;
          border-bottom: 1px solid var(--line);
        "
      >
        <el-icon :size="16" :style="{ color: c.ok ? 'var(--green)' : 'var(--red)', marginTop: '2px' }">
          <CircleCheck v-if="c.ok" />
          <WarningFilled v-else />
        </el-icon>
        <div style="min-width: 0">
          <div style="font-size: 13px; font-weight: 600">{{ c.name }}</div>
          <div class="muted">{{ c.detail }}</div>
          <div v-if="c.hint" style="color: var(--amber); font-size: 12px; margin-top: 3px">
            → {{ c.hint }}
          </div>
        </div>
      </div>
    </div>
  </el-card>
</template>
