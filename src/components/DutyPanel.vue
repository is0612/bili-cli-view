<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Setting, VideoPlay } from '@element-plus/icons-vue'
import { api } from '../api'
import type { DutySnapshot } from '../types'

const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const duty = ref<DutySnapshot | null>(null)
const report = ref('')
const reportPath = ref('')
const reportOpen = ref(false)

const perDay = ref(5)
const peakValley = ref(true)
const noon = ref(true)
const night = ref(true)
const dmMode = ref<'off' | 'only' | 'both'>('only')
const dmUid = ref(0)
const reportLevel = ref<'full' | 'brief' | 'off'>('brief')
const keywords = ref<string[]>([])
const autoComment = ref(false)
const mentionName = ref('')
const commentPerRound = ref(1)
const replyToComments = ref(false)
const replyPerRound = ref(1)

const remaining = computed(() => duty.value?.state.remaining ?? 0)
const picked = computed(() => duty.value?.state.picked ?? 0)

function fill(snap: DutySnapshot) {
  duty.value = snap
  const c = snap.config
  perDay.value = Number(c.perDay ?? 5)
  peakValley.value = Boolean(c.peakValley)
  noon.value = Boolean(c.noon)
  night.value = Boolean(c.night)
  dmMode.value = (c.dmMode ?? 'off') as typeof dmMode.value
  dmUid.value = Number(c.dmUid ?? 0)
  reportLevel.value = (c.reportLevel ?? 'brief') as typeof reportLevel.value
  keywords.value = Array.isArray(c.keywords) ? [...c.keywords] : []
  autoComment.value = Boolean(c.autoComment)
  mentionName.value = String(c.mentionName ?? '')
  commentPerRound.value = Number(c.commentPerRound ?? 1)
  replyToComments.value = Boolean(c.replyToComments)
  replyPerRound.value = Number(c.replyPerRound ?? 1)
}

async function load() {
  loading.value = true
  try {
    fill(await api.duty())
  } catch (err) {
    ElMessage.error({ message: `读取值班设置失败：${(err as Error).message}`, grouping: true })
  } finally {
    loading.value = false
  }
}

async function loadReport() {
  try {
    const r = await api.dutyReport()
    report.value = r.text || '（今天还没有报告）'
    reportPath.value = r.path
  } catch (err) {
    ElMessage.error({ message: `读报告失败：${(err as Error).message}`, grouping: true })
  }
}

async function save() {
  saving.value = true
  try {
    const res = await api.saveDuty({
      perDay: perDay.value,
      peakValley: peakValley.value,
      noon: noon.value,
      night: night.value,
      dmMode: dmMode.value,
      dmUid: dmUid.value,
      reportLevel: reportLevel.value,
      keywords: keywords.value,
      autoComment: autoComment.value,
      mentionName: mentionName.value,
      commentPerRound: commentPerRound.value,
      replyToComments: replyToComments.value,
      replyPerRound: replyPerRound.value,
    })
    fill(res.duty)
    ElMessage.success({ message: '已保存，下一轮按新设置跑', grouping: true })
  } catch (err) {
    ElMessage.error({ message: `保存失败：${(err as Error).message}`, grouping: true })
  } finally {
    saving.value = false
  }
}

async function resetQuota() {
  try {
    await ElMessageBox.confirm(
      `今天已经挑了 ${picked.value} 条。重置会把今天的报告改名归档，额度归零，判重表不动 —— 她可以重新挑。`,
      '重置今日额度',
      { confirmButtonText: '重置', cancelButtonText: '算了', type: 'warning' },
    )
  } catch {
    return
  }
  resetting.value = true
  try {
    const res = await api.resetDuty()
    fill(res.state)
    await loadReport()
    ElMessage.success({
      message: res.archived ? `额度已重置，旧报告存为 ${res.archived}` : '额度已重置（今天本来就没报告）',
      grouping: true,
      duration: 4000,
    })
  } catch (err) {
    ElMessage.error({ message: `重置失败：${(err as Error).message}`, grouping: true })
  } finally {
    resetting.value = false
  }
}

onMounted(async () => {
  await load()
  void loadReport()
})
</script>

<template>
  <el-card class="runner-card" shadow="never" v-loading="loading">
    <div class="runner-head">
      <div class="runner-icon"><el-icon :size="17"><Setting /></el-icon></div>
      <div style="min-width: 0; flex: 1">
        <div class="runner-title">
          刷B站 · 值班设置
          <el-tag :type="remaining > 0 ? 'success' : 'info'" effect="dark" size="small" round disable-transitions>
            今天 {{ picked }} / {{ perDay }}{{ remaining > 0 ? ` · 还能挑 ${remaining} 条` : ' · 额度已满' }}
          </el-tag>
        </div>
        <div class="cmd-chip" style="margin-top: 7px">{{ dmMode === 'only' ? '鲸鱼娘每天按谷时自己跑，只发私信' : dmMode === 'both' ? '鲸鱼娘每天按谷时自己跑：私信 + 公开评论' : '鲸鱼娘每天按谷时自己跑，不对外发任何东西' }}</div>
      </div>
      <el-button :icon="Refresh" text @click="load">刷新</el-button>
    </div>

    <el-form label-position="top" style="margin-top: 8px">
      <el-row :gutter="16">
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="每天最多挑几条">
            <el-input-number v-model="perDay" :min="0" :max="50" controls-position="right" style="width: 100%" />
          </el-form-item>
        </el-col>

        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="峰谷时段自动刷">
            <el-switch v-model="peakValley" />
          </el-form-item>
        </el-col>

        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item :label="`中午窗口 ${duty?.windows?.noon?.start ?? '12:00'}–${duty?.windows?.noon?.end ?? '14:00'}`">
            <el-switch v-model="noon" :disabled="!peakValley" />
          </el-form-item>
        </el-col>

        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item :label="`夜间窗口 ${duty?.windows?.night?.start ?? '18:00'}–${duty?.windows?.night?.end ?? '09:00'}`">
            <el-switch v-model="night" :disabled="!peakValley" />
          </el-form-item>
        </el-col>

        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="投递方式">
            <el-select v-model="dmMode" style="width: 100%">
              <el-option label="只发私信（不公开评论）" value="only" />
              <el-option label="私信 + 公开评论" value="both" />
              <el-option label="都不发" value="off" />
            </el-select>
          </el-form-item>
        </el-col>

        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="私信发给谁（UID）">
            <el-input-number v-model="dmUid" :min="0" :controls="false" style="width: 100%" placeholder="你的 UID" />
          </el-form-item>
        </el-col>

        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="日报写多细">
            <el-select v-model="reportLevel" style="width: 100%">
              <el-option label="完整" value="full" />
              <el-option label="薄版（省 token）" value="brief" />
              <el-option label="不写日报" value="off" />
            </el-select>
          </el-form-item>
        </el-col>

        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="自动公开评论">
            <el-switch v-model="autoComment" />
          </el-form-item>
        </el-col>

        <el-col v-if="autoComment" :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="@ 谁（留空 = 不 @ 任何人）">
            <el-input v-model="mentionName" placeholder="没有喵i" />
          </el-form-item>
        </el-col>

        <el-col v-if="autoComment" :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="每轮最多几条评论">
            <el-input-number
              v-model="commentPerRound"
              :min="0"
              :max="20"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>

        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="回复别人在她评论下的留言">
            <el-switch v-model="replyToComments" />
          </el-form-item>
        </el-col>

        <el-col v-if="replyToComments" :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item label="每轮最多回几条">
            <el-input-number
              v-model="replyPerRound"
              :min="1"
              :max="10"
              controls-position="right"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>

        <el-col :span="24">
          <el-form-item label="关注关键词（回车添加，搜这些方向）">
            <el-select
              v-model="keywords"
              multiple
              filterable
              allow-create
              default-first-option
              :reserve-keyword="false"
              placeholder="原神 / 星穹铁道 / 绝区零 …"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px">
        <el-button type="warning" plain :loading="resetting" @click="resetQuota">重置今日额度</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>
    </el-form>

    <el-alert
      v-if="autoComment"
      type="warning"
      :closable="false"
      show-icon
      style="margin-top: 14px"
      title="公开评论会真的发出去（挂在北海大肥鱼那个号上）。「@ 谁」留空就是纯自己评论，不通知任何人。"
    />

    <el-collapse style="margin-top: 16px" @change="(v: any) => v.includes('report') && loadReport()">
      <el-collapse-item name="report">
        <template #title>
          <span style="display: inline-flex; align-items: center; gap: 8px">
            <el-icon><VideoPlay /></el-icon>
            今天的报告
            <span class="muted">{{ reportPath }}</span>
          </span>
        </template>
        <pre class="code" style="max-height: 460px">{{ report }}</pre>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>
