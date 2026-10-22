<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Promotion, Refresh } from '@element-plus/icons-vue'
import { api } from '../api'
import type { RunResult } from '../types'

const text = ref('')
const imagesText = ref('')
const atText = ref('')
const previewMode = ref(true)
const result = ref<RunResult | null>(null)
const sending = ref(false)

const images = computed(() =>
  imagesText.value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean),
)
const ats = computed(() =>
  atText.value
    .split(/[,，\s]+/)
    .map((s) => s.trim())
    .filter(Boolean),
)
const overLimit = computed(() => images.value.length > 9 || text.value.length > 2000)

function payload(dryRun: boolean) {
  return { text: text.value, images: images.value, at: ats.value, dry_run: dryRun }
}

async function preview() {
  if (!text.value.trim()) {
    ElMessage.warning({ message: '先写点正文', grouping: true })
    return
  }
  sending.value = true
  try {
    result.value = await api.postDynamic(payload(true))
    ElMessage.success({ message: '预览成功（没有真发）', grouping: true })
  } catch (err) {
    ElMessage.error({ message: `预览失败：${(err as Error).message}`, grouping: true })
  } finally {
    sending.value = false
  }
}

async function publish() {
  if (!text.value.trim()) {
    ElMessage.warning({ message: '先写点正文', grouping: true })
    return
  }
  if (overLimit.value) {
    ElMessage.warning({ message: '图片最多 9 张、正文最多 2000 字', grouping: true })
    return
  }
  try {
    await ElMessageBox.confirm(
      '这条会以「北海大肥鱼」的账号公开推给粉丝，发出去就有痕迹。确定发吗？',
      '确认发布动态',
      { confirmButtonText: '真发', cancelButtonText: '再想想', type: 'warning' },
    )
  } catch {
    return
  }
  sending.value = true
  try {
    result.value = await api.postDynamic(payload(false))
    if (result.value.json?.ok) {
      ElMessage.success({ message: '动态已发布', grouping: true })
      text.value = ''
      imagesText.value = ''
    } else {
      ElMessage.error({
        message: `发布失败：${result.value.json?.error?.message ?? result.value.stderr}`,
        grouping: true,
      })
    }
  } catch (err) {
    ElMessage.error({ message: `发布失败：${(err as Error).message}`, grouping: true })
  } finally {
    sending.value = false
  }
}

onMounted(() => {
  atText.value = 'owner'
})
</script>

<template>
  <el-card class="runner-card" shadow="never">
    <div class="runner-head">
      <div class="runner-icon"><el-icon :size="17"><Promotion /></el-icon></div>
      <div style="min-width: 0; flex: 1">
        <div class="runner-title">
          发动态
          <el-tag type="warning" effect="plain" size="small" round disable-transitions>公开</el-tag>
        </div>
        <div class="cmd-chip" style="margin-top: 7px">bili dynamic post …（默认先 dry-run 预览）</div>
      </div>
      <el-button :icon="Refresh" text @click="preview">重新预览</el-button>
    </div>

    <el-alert
      type="warning"
      :closable="false"
      show-icon
      style="margin-top: 14px"
      title="这条会挂在「北海大肥鱼」名下推给粉丝，删了也有痕迹 —— 先预览，看清了再发。"
    />

    <el-form label-position="top" style="margin-top: 12px">
      <el-form-item :label="`正文（${text.length} / 2000）`">
        <el-input
          v-model="text"
          type="textarea"
          :rows="6"
          placeholder="今天刷到几条轻松的：原神 7.2 前瞻里的「法涅斯」…"
        />
      </el-form-item>

      <el-row :gutter="16">
        <el-col :xs="24" :md="12">
          <el-form-item :label="`图片路径（一行一张，最多 9 张，现在 ${images.length} 张）`">
            <el-input
              v-model="imagesText"
              type="textarea"
              :rows="3"
              placeholder="E:\图片\a.png"
            />
          </el-form-item>
        </el-col>
        <el-col :xs="24" :md="12">
          <el-form-item label="@ 谁（逗号分隔，owner = 主人）">
            <el-input v-model="atText" placeholder="owner" />
          </el-form-item>
        </el-col>
      </el-row>

      <div style="display: flex; gap: 10px; justify-content: flex-end">
        <el-checkbox v-model="previewMode" style="margin-right: auto">预览模式（dry-run，不真发）</el-checkbox>
        <el-button :loading="sending" @click="preview">预览</el-button>
        <el-button type="primary" :loading="sending" @click="publish">发布</el-button>
      </div>
    </el-form>

    <el-collapse v-if="result" style="margin-top: 14px">
      <el-collapse-item :title="`执行结果 · ${result.json?.ok ? '成功' : '失败'}（${result.elapsed}s）`">
        <pre class="code">{{ JSON.stringify(result.json ?? result.stdout, null, 2) }}</pre>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>
