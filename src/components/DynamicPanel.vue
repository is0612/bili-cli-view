<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Promotion, Refresh } from '@element-plus/icons-vue'
import { api } from '../api'
import type { RunResult } from '../types'
import { useAccount } from '../composables/useAccount'

const text = ref('')
const imagesText = ref('')
const atText = ref('')
const result = ref<RunResult | null>(null)
const sending = ref(false)

const { loggedIn, name: accountName, label: accountLabel, load: loadAccount } = useAccount()

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

/** 这条正文的「指纹」：内容一改，之前的预览就不算数了 */
const draftKey = computed(() => JSON.stringify({ t: text.value, i: images.value, a: ats.value }))
const previewedKey = ref<string | null>(null)
const previewed = computed(() => previewedKey.value === draftKey.value && previewedKey.value !== null)
const needsRepreview = computed(() => previewedKey.value !== null && previewedKey.value !== draftKey.value)

const canPublish = computed(
  () => loggedIn.value && Boolean(text.value.trim()) && !overLimit.value && previewed.value,
)

/** 为什么现在不能发 —— 直接写在按钮旁边，别让人猜 */
const statusHint = computed(() => {
  if (!loggedIn.value) return '还没登录：点右上角「扫码登录」，否则发不出去'
  if (!text.value.trim()) return '先写正文'
  if (overLimit.value) return '图片最多 9 张、正文最多 2000 字'
  if (needsRepreview.value) return '正文/图片/@ 改过了，重新预览一次再发'
  if (!previewed.value) return '先点「预览」，看清了再发'
  return `已预览：将以${accountLabel.value}的身份公开推送`
})

function payload(dryRun: boolean) {
  return { text: text.value, images: images.value, at: ats.value, dry_run: dryRun }
}

async function preview() {
  if (!text.value.trim()) {
    ElMessage.warning({ message: '先写点正文', grouping: true })
    return
  }
  const key = draftKey.value
  sending.value = true
  try {
    result.value = await api.postDynamic(payload(true))
    if (result.value.json?.ok) {
      previewedKey.value = key
      ElMessage.success({ message: '预览成功（没有真发）', grouping: true })
    } else {
      previewedKey.value = null
      ElMessage.error({
        message: `预览没通过：${result.value.json?.error?.message ?? result.value.stderr}`,
        grouping: true,
      })
    }
  } catch (err) {
    previewedKey.value = null
    ElMessage.error({ message: `预览失败：${(err as Error).message}`, grouping: true })
  } finally {
    sending.value = false
  }
}

async function publish() {
  if (!canPublish.value) {
    ElMessage.warning({ message: statusHint.value, grouping: true })
    return
  }
  try {
    await ElMessageBox.confirm(
      `这条会以${accountLabel.value}的身份公开推给粉丝，删了也有痕迹。确定发吗？`,
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
      previewedKey.value = null
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
  void loadAccount()
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
          <el-tag v-if="loggedIn" type="info" effect="plain" size="small" round disable-transitions>
            {{ accountName }}
          </el-tag>
          <el-tag v-else type="danger" effect="plain" size="small" round disable-transitions>
            未登录
          </el-tag>
        </div>
        <div class="cmd-chip" style="margin-top: 7px">bili dynamic post …（默认先 dry-run 预览）</div>
      </div>
      <el-button :icon="Refresh" text @click="preview">重新预览</el-button>
    </div>

    <el-alert
      :type="loggedIn ? 'warning' : 'info'"
      :closable="false"
      show-icon
      style="margin-top: 14px"
      :title="
        loggedIn
          ? `这条会挂在${accountLabel}名下推给粉丝，删了也有痕迹 —— 先预览，看清了再发。`
          : '还没登录：先点右上角「扫码登录」。登录后这里会显示你的账号名，没登录是发不出去的。'
      "
    />

    <el-form label-position="top" style="margin-top: 12px">
      <el-form-item :label="`正文（${text.length} / 2000）`">
        <el-input
          v-model="text"
          type="textarea"
          :rows="6"
          placeholder="今天刷到几条轻松的，随手记两句…"
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

      <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap">
        <span class="muted" style="margin-right: auto; font-size: 12px">{{ statusHint }}</span>
        <el-button :loading="sending" @click="preview">预览（不真发）</el-button>
        <el-tooltip
          :content="canPublish ? '确认无误后发布' : statusHint"
          placement="top"
          :show-after="200"
        >
          <span>
            <el-button type="primary" :disabled="!canPublish" :loading="sending" @click="publish">
              发布
            </el-button>
          </span>
        </el-tooltip>
      </div>
    </el-form>

    <el-collapse v-if="result" style="margin-top: 14px">
      <el-collapse-item :title="`执行结果 · ${result.json?.ok ? '成功' : '失败'}（${result.elapsed}s）`">
        <pre class="code">{{ JSON.stringify(result.json ?? result.stdout, null, 2) }}</pre>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>
