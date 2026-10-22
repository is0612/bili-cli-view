<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, View } from '@element-plus/icons-vue'
import { api } from '../api'
import type { SeenPayload } from '../types'

const loading = ref(false)
const data = ref<SeenPayload | null>(null)
const filter = ref<'all' | 'picked' | 'skipped'>('all')

const list = computed(() => {
  const videos = data.value?.videos ?? []
  if (filter.value === 'picked') return videos.filter((v) => v.result.startsWith('收'))
  if (filter.value === 'skipped') return videos.filter((v) => !v.result.startsWith('收'))
  return videos
})

async function load() {
  loading.value = true
  try {
    data.value = await api.seen()
  } catch (err) {
    ElMessage.error({ message: `读取判重表失败：${(err as Error).message}`, grouping: true })
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <el-card class="runner-card" shadow="never" v-loading="loading">
    <div class="runner-head">
      <div class="runner-icon"><el-icon :size="17"><View /></el-icon></div>
      <div style="min-width: 0; flex: 1">
        <div class="runner-title">
          她看过什么
          <el-tag type="success" effect="dark" size="small" round disable-transitions>
            共 {{ data?.stats.total ?? 0 }} 条 · 收 {{ data?.stats.picked ?? 0 }} · 跳过
            {{ data?.stats.skipped ?? 0 }}
          </el-tag>
        </div>
        <div class="cmd-chip" style="margin-top: 7px">source: {{ data?.path ?? 'seen.md' }}</div>
      </div>
      <el-button :icon="Refresh" text @click="load">刷新</el-button>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      style="margin-top: 14px"
      title="这里的「看过」是她调接口读字幕/评论记下的，不是播放器观看 —— 所以 B站 的浏览记录里不会有。"
    />

    <div style="display: flex; gap: 8px; margin: 16px 0 10px">
      <el-radio-group v-model="filter" size="small">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="picked">只看收的</el-radio-button>
        <el-radio-button value="skipped">只看跳过的</el-radio-button>
      </el-radio-group>
    </div>

    <el-table :data="list" size="small" max-height="520" stripe>
      <el-table-column prop="date" label="日期" width="110" />
      <el-table-column label="视频" min-width="320">
        <template #default="{ row }">
          <a :href="`https://www.bilibili.com/video/${row.bvid}`" target="_blank" rel="noreferrer">
            {{ row.title || row.bvid }}
          </a>
          <div class="muted mono">{{ row.bvid }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="author" label="UP 主" width="150" show-overflow-tooltip />
      <el-table-column label="结果" width="200">
        <template #default="{ row }">
          <el-tag
            :type="row.result.startsWith('收') ? 'success' : 'info'"
            effect="plain"
            size="small"
            disable-transitions
          >
            {{ row.result }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-collapse v-if="data?.comments?.length" style="margin-top: 16px">
      <el-collapse-item :title="`她发过的评论 · ${data.comments.length} 条`">
        <el-table :data="data.comments" size="small" stripe>
          <el-table-column prop="time" label="时间" width="170" />
          <el-table-column prop="bvid" label="BV" width="140" />
          <el-table-column prop="text" label="正文前 20 字" min-width="240" />
        </el-table>
      </el-collapse-item>
    </el-collapse>

    <el-collapse v-if="data?.rounds?.length" style="margin-top: 10px">
      <el-collapse-item :title="`轮次记录 · ${data.rounds.length} 条`">
        <div v-for="(r, i) in data.rounds" :key="i" class="muted" style="line-height: 2">
          {{ r.date }} · {{ r.note }}
        </div>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>
