<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { EditPen, Refresh, Notebook } from '@element-plus/icons-vue'
import { api } from '../api'
import type { JournalPayload } from '../types'

const loading = ref(false)
const data = ref<JournalPayload | null>(null)
const editing = ref(false)
const draft = ref('')

const lines = computed(() => {
  // 编辑框里一行一条：`- 日期 · 内容` 或纯内容（日期自动补）
  return (data.value?.entries ?? []).map((e) => `- ${e.date} · ${e.text}`).join('\n')
})

async function load() {
  loading.value = true
  try {
    data.value = await api.journal()
    if (!editing.value) draft.value = lines.value
  } catch (err) {
    ElMessage.error({ message: `读取札记失败：${(err as Error).message}`, grouping: true })
  } finally {
    loading.value = false
  }
}

function startEdit() {
  draft.value = lines.value
  editing.value = true
}

function cancelEdit() {
  draft.value = lines.value
  editing.value = false
}

async function save() {
  const entries = draft.value
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean)
  try {
    data.value = await api.saveJournal(entries)
    editing.value = false
    ElMessage.success('札记已保存')
  } catch (err) {
    ElMessage.error({ message: `保存失败：${(err as Error).message}`, grouping: true })
  }
}

async function removeOne(index: number) {
  try {
    await ElMessageBox.confirm('删掉这一条札记？她不会记得自己写过这句了。', '删除', {
      confirmButtonText: '删',
      cancelButtonText: '再想想',
      type: 'warning',
    })
  } catch {
    return
  }
  const entries = (data.value?.entries ?? []).filter((_, i) => i !== index)
  try {
    data.value = await api.saveJournal(entries.map((e) => `- ${e.date} · ${e.text}`))
    if (editing.value) draft.value = lines.value
    ElMessage.success('已删除')
  } catch (err) {
    ElMessage.error({ message: `删除失败：${(err as Error).message}`, grouping: true })
  }
}

onMounted(load)
</script>

<template>
  <el-card class="runner-card" shadow="never" v-loading="loading">
    <div class="runner-head">
      <div class="runner-icon"><el-icon :size="17"><Notebook /></el-icon></div>
      <div style="min-width: 0; flex: 1">
        <div class="runner-title">
          她的札记
          <el-tag type="success" effect="dark" size="small" round disable-transitions>
            {{ data?.count ?? 0 }} 条
          </el-tag>
        </div>
        <div class="cmd-chip" style="margin-top: 7px">source: {{ data?.path ?? 'human-world.md' }}</div>
      </div>
      <el-button v-if="!editing" :icon="EditPen" text @click="startEdit">编辑</el-button>
      <el-button v-if="editing" text @click="cancelEdit">取消</el-button>
      <el-button v-if="editing" type="primary" text @click="save">保存</el-button>
      <el-button v-if="!editing" :icon="Refresh" text @click="load">刷新</el-button>
    </div>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      style="margin-top: 14px"
      title="每次值班结束，她会写一句「今天最触动我的」。下一轮开始前，这些会回读给她 —— 所以她越刷越有她自己的样子。你可以改、可以删。"
    />

    <!-- 编辑态：一整块文本框 -->
    <div v-if="editing" style="margin-top: 16px">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="16"
        placeholder="一行一条，格式：- 日期 · 内容"
      />
      <div class="muted" style="margin-top: 8px; font-size: 12px">
        每行一条；不带日期的行会自动补上今天。保存后整份覆盖。
      </div>
    </div>

    <!-- 浏览态：时间线 -->
    <div v-else-if="data?.entries?.length" class="journal-timeline">
      <div v-for="(e, i) in data.entries" :key="i" class="journal-item">
        <div class="journal-date">{{ e.date }}</div>
        <div class="journal-text">{{ e.text }}</div>
        <el-button class="journal-del" text size="small" @click="removeOne(i)">删</el-button>
      </div>
    </div>

    <div v-else class="empty-block" style="padding: 40px 0">
      <div class="halo"><el-icon :size="22"><Notebook /></el-icon></div>
      <h4>她还没写过札记</h4>
      <p>等她跑完第一轮值班，就会在这里留下第一句话。</p>
    </div>
  </el-card>
</template>

<style scoped>
.journal-timeline {
  margin-top: 18px;
  border-left: 2px solid var(--el-border-color-light);
  padding-left: 16px;
}
.journal-item {
  position: relative;
  padding: 8px 0 14px;
}
.journal-item::before {
  content: '';
  position: absolute;
  left: -22px;
  top: 12px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-primary);
}
.journal-date {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-family: var(--el-font-family-mono, monospace);
  margin-bottom: 4px;
}
.journal-text {
  font-size: 14px;
  line-height: 1.7;
  padding-right: 40px;
}
.journal-del {
  position: absolute;
  right: 0;
  top: 2px;
  opacity: 0.4;
}
.journal-item:hover .journal-del {
  opacity: 1;
}
</style>
