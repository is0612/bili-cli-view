<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  ArrowRight,
  Bell,
  Clock,
  DataLine,
  Document,
  Refresh,
  Setting,
  TrendCharts,
  VideoPlay,
  View,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { api } from '../api'
import type { CommandGroup, DutySnapshot, ProfileInfo, RunResult, SeenPayload } from '../types'

const props = defineProps<{
  groups: CommandGroup[]
  results: RunResult[]
  busy: boolean
}>()

const emit = defineEmits<{
  (e: 'select', cmd: string): void
  (e: 'run-round'): void
  (e: 'open-runs'): void
  (e: 'refresh'): void
}>()

const duty = ref<DutySnapshot | null>(null)
const seen = ref<SeenPayload | null>(null)
const report = ref<{ day: string; path: string; exists: boolean; picks: number; text: string } | null>(null)
const profile = ref<ProfileInfo | null>(null)
const loading = ref(false)
/** 封面加载失败就退回渐变占位，避免一片破图 */
const broken = reactive<Record<string, boolean>>({})

async function load() {
  loading.value = true
  const [d, s, r, p] = await Promise.allSettled([
    api.duty(),
    api.seen(),
    api.dutyReport(),
    api.profile(),
  ])
  if (d.status === 'fulfilled') duty.value = d.value
  if (s.status === 'fulfilled') seen.value = s.value
  if (r.status === 'fulfilled') report.value = r.value
  if (p.status === 'fulfilled') profile.value = p.value
  loading.value = false
}

defineExpose({ load })

onMounted(load)

/* ── KPI ────────────────────────────────────────────────── */
const st = computed(() => duty.value?.state)
const perDay = computed(() => st.value?.perDay ?? 0)
const picked = computed(() => st.value?.picked ?? 0)
const pct = computed(() =>
  perDay.value > 0 ? Math.min(100, Math.round((picked.value / perDay.value) * 100)) : 0,
)

const skipped = computed(() => seen.value?.stats.skipped ?? 0)
const seenTotal = computed(() => seen.value?.stats.total ?? 0)

/** 时长拆成「数值 + 单位」两段，26px 数字后面跟 12px 单位 */
function dur(seconds?: number | null) {
  if (seconds == null || !Number.isFinite(seconds)) return { v: '—', u: '' }
  const s = Math.max(0, Math.round(seconds))
  if (s < 60) return { v: String(s), u: '秒' }
  const m = Math.floor(s / 60)
  const rest = s % 60
  return { v: String(m), u: rest ? `分 ${rest} 秒` : '分钟' }
}

/** 耗时只在内存里，重启就没了 —— 文案要区分「没跑过」和「跑过但记录没了」 */
const lastHint = computed(() => {
  if (st.value?.last?.seconds != null) return '最近一轮值班的耗时'
  if (st.value?.rounds) return '上一轮耗时随重启清空了'
  return '还没有跑过值班'
})

const lastRun = computed(() => {
  const sec = st.value?.last?.seconds ?? props.results[0]?.elapsed
  return dur(sec ?? null)
})

/* ── 她今天看了什么 ────────────────────────────────────── */
const watches = computed(() => (seen.value?.videos ?? []).slice(0, 3))

const COVERS = [
  ['#3f6091', '#21324d'],
  ['#5d3f86', '#382253'],
  ['#2f6b5e', '#1a3b34'],
  ['#8a5a2b', '#4a2e16'],
]

function coverStyle(i: number) {
  const [c1, c2] = COVERS[i % COVERS.length]
  return { '--c1': c1, '--c2': c2 }
}

/** seen.md 里 result 以「收」开头就是被采纳的，其余是跳过 */
const isPicked = (result: string) => result.trim().startsWith('收')

/** seen.md 里写的是「收 · 已评论」，前缀对用户没意义，只留后半句 */
const badgeText = (result: string) => result.replace(/^收\s*[·・]\s*/, '').trim() || '已采纳'

function badgeClass(result: string) {
  if (!isPicked(result)) return 'mute'
  return result.includes('投') ? 'info' : 'ok'
}

/* ── 今日报告 ──────────────────────────────────────────── */
const reportHead = computed(() => {
  const text = (report.value?.text ?? '').replace(/^#.*$/gm, '').trim()
  return text
})

const reportName = computed(() => {
  const p = report.value?.path ?? st.value?.report ?? ''
  const parts = p.split(/[\\/]/)
  return parts.slice(-2).join('/')
})

const keywords = computed(() => duty.value?.config.keywords ?? [])

/* ── 快速开始 ──────────────────────────────────────────── */
const QUICK = [
  { cmd: 'video.watch', label: '看懂视频', icon: View },
  { cmd: 'hot.rank', label: '排行榜', icon: TrendCharts },
  { cmd: 'feed.inbox', label: '收件箱', icon: Bell },
  { cmd: 'duty.settings', label: '值班设置', icon: Setting },
]

const hasItems = computed(() => props.groups.length > 0)

function go(cmd: string) {
  if (!hasItems.value) {
    ElMessage.warning({ message: '命令表还没加载出来', grouping: true })
    return
  }
  emit('select', cmd)
}

/* ── 最近运行 ──────────────────────────────────────────── */
const recent = computed(() => props.results.slice(0, 4))

function summary(res: RunResult) {
  const data = res.json?.data as any
  if (res.json?.error) return `${res.json.error.code}：${res.json.error.message}`
  if (Array.isArray(data)) return `${data.length} 条结果`
  if (data && typeof data === 'object') {
    const n = Object.keys(data).length
    return `${n} 个字段`
  }
  return res.json?.ok ? '执行成功' : '无输出'
}

const h1 = computed(() => {
  if (!st.value) return '先看看今天的情况'
  if (perDay.value <= 0) return '值班还没设置每日条数'
  if (picked.value >= perDay.value) return `今天已经刷满 ${perDay.value} 条`
  return `今天刷了 ${picked.value} 条，还剩 ${perDay.value - picked.value} 条配额`
})

/** 下一个谷时窗口：按 windows 的 start/end 算，窗口内就说「进行中」 */
const nextWindow = computed(() => {
  const w = duty.value?.windows
  if (!w) return ''
  const toMin = (s: string) => {
    const [h, m] = (s ?? '').split(':').map(Number)
    return Number.isFinite(h) ? h * 60 + (Number.isFinite(m) ? m : 0) : NaN
  }
  const list = Object.values(w)
    .map((x) => ({ label: x.label, start: x.start, end: x.end, s: toMin(x.start), e: toMin(x.end) }))
    .filter((x) => Number.isFinite(x.s) && Number.isFinite(x.e))
    .sort((a, b) => a.s - b.s)
  if (!list.length) return ''
  const now = new Date()
  const mins = now.getHours() * 60 + now.getMinutes()
  const cur = list.find((x) => mins >= x.s && mins < x.e)
  if (cur) return `谷时窗口${cur.label}进行中（${cur.start}–${cur.end}）`
  const next = list.find((x) => x.s > mins) ?? list[0]
  const day = next.s > mins ? '今天' : '明天'
  return `下次谷时窗口 ${next.start} 开启（${day}）`
})

const subtitle = computed(() => {
  const bits: string[] = []
  const w = nextWindow.value
  if (w) bits.push(w)
  if (st.value?.rounds) bits.push(`今天跑了 ${st.value.rounds} 轮`)
  bits.push(`判重表已记 ${seenTotal.value} 条`)
  if (profile.value?.dir) bits.push(`数据在 ${profile.value.dir}`)
  return bits.join(' · ')
})
</script>

<template>
  <div>
    <div class="crumb">工作台 <span>/</span> <b>概览</b></div>

    <div class="page-h">
      <div>
        <h1>{{ h1 }}</h1>
        <p>{{ subtitle }}</p>
      </div>
      <div class="ph-r">
        <button class="btn" :disabled="loading" @click="load">
          <el-icon><Refresh /></el-icon>刷新状态
        </button>
        <button class="btn primary lg" :disabled="busy" @click="emit('run-round')">
          <el-icon><VideoPlay /></el-icon>{{ busy ? '正在跑…' : '现在跑一轮' }}
        </button>
      </div>
    </div>

    <!-- 先给「今天怎么样」，再给内容 -->
    <div v-if="loading" class="kpi-row">
      <div v-for="i in 4" :key="i" class="kpi">
        <div class="sk" style="height: 12px; width: 46%; margin-bottom: 10px" />
        <div class="sk" style="height: 26px; width: 58%; margin-bottom: 10px" />
        <div class="sk" style="height: 10px; width: 74%" />
      </div>
    </div>
    <div v-else class="kpi-row">
      <div class="kpi">
        <div class="k"><el-icon><Clock /></el-icon>今日进度</div>
        <div class="v">
          {{ picked }}<small>/ {{ perDay || '—' }} 条</small>
        </div>
        <div class="bar"><i :style="{ width: pct + '%' }" /></div>
        <div class="foot">
          {{ perDay ? `已用 ${pct}% 配额` : '还没设置每日条数' }}
        </div>
      </div>

      <div class="kpi">
        <div class="k"><el-icon><Bell /></el-icon>待处理消息</div>
        <div class="v"><span class="na">—</span></div>
        <div class="foot">点「收件箱」拉一次才有未读数</div>
      </div>

      <div class="kpi">
        <div class="k"><el-icon><View /></el-icon>判重跳过</div>
        <div class="v">
          {{ skipped }}<small>条</small>
        </div>
        <div class="foot">seen.md 累计记录 {{ seenTotal }} 条</div>
      </div>

      <div class="kpi">
        <div class="k"><el-icon><DataLine /></el-icon>本轮耗时</div>
        <div class="v">
          <span v-if="lastRun.v === '—'" class="na">—</span>
          <template v-else>{{ lastRun.v }}<small>{{ lastRun.u }}</small></template>
        </div>
        <div class="foot">{{ lastHint }}</div>
      </div>
    </div>

    <div v-if="loading" class="home-cols">
      <div>
        <div class="sec-h"><h2>她今天看了什么</h2></div>
        <div class="card">
          <div v-for="i in 3" :key="i" class="wrow is-skel">
            <div class="sk" style="width: 56px; height: 56px; border-radius: 8px; flex: none" />
            <div style="flex: 1; min-width: 0">
              <div class="sk" style="height: 13px; width: 82%; margin-bottom: 8px" />
              <div class="sk" style="height: 11px; width: 46%" />
            </div>
          </div>
        </div>
        <div class="sec-h"><h2>今日报告</h2></div>
        <div class="card">
          <div class="sk-card">
            <div class="sk" style="height: 12px; width: 96%; margin-bottom: 9px" />
            <div class="sk" style="height: 12px; width: 90%; margin-bottom: 9px" />
            <div class="sk" style="height: 12px; width: 62%" />
          </div>
        </div>
      </div>
      <div>
        <div class="sec-h"><h2>快速开始</h2></div>
        <div class="card">
          <div class="sk-card">
            <div v-for="i in 4" :key="i" class="sk" style="height: 34px; margin-bottom: 7px" />
          </div>
        </div>
        <div class="sec-h"><h2>最近运行</h2></div>
        <div class="card">
          <div class="sk-card">
            <div v-for="i in 4" :key="i" class="sk" style="height: 34px; margin-bottom: 7px" />
          </div>
        </div>
      </div>
    </div>
    <div v-else class="home-cols">
      <!-- 左栏：她今天看了什么 + 今日报告 -->
      <div>
        <div class="sec-h">
          <h2>她今天看了什么</h2>
          <span v-if="seen" class="sub">{{ seen.stats.picked }} 条采纳 · {{ seen.stats.skipped }} 条跳过</span>
          <button class="more" @click="go('duty.seen')">筛选记录</button>
        </div>
        <div class="card">
          <div v-for="(v, i) in watches" :key="v.bvid" class="wrow" @click="go('video.watch')">
            <div class="mcover" :style="coverStyle(i)">
              <img
                v-if="!broken[v.bvid]"
                :src="api.coverUrl(v.bvid)"
                alt=""
                loading="lazy"
                @error="broken[v.bvid] = true"
              />
              <span v-else>{{ v.title.slice(0, 3) }}</span>
            </div>
            <div class="wb">
              <div class="wt">{{ v.title }}</div>
              <div class="wm">
                <span>{{ v.author }}</span>
                <i class="sep" />
                <span>{{ v.date }}</span>
                <span class="badge" :class="badgeClass(v.result)">{{ badgeText(v.result) }}</span>
              </div>
            </div>
            <el-icon class="arw"><ArrowRight /></el-icon>
          </div>

          <div v-if="!watches.length" class="empty-mini">
            <el-icon><View /></el-icon>
            <span>判重表里还没有今天的记录</span>
            <span>跑一轮值班，她看过什么就会记在这里</span>
          </div>
        </div>

        <div class="sec-h">
          <h2>今日报告</h2>
          <span class="sub">{{ reportName }}</span>
          <button class="more" @click="go('duty.seen')">看全部记录</button>
        </div>
        <div class="card">
          <div class="report">
            <p v-if="reportHead">{{ reportHead }}</p>
            <p v-else class="muted">今天还没有报告。跑一轮之后，这里会是她写的当日小结。</p>
            <div v-if="keywords.length" class="rm">
              <span>关键词 <b>{{ keywords.join(' · ') }}</b></span>
              <span v-if="report?.picks">采纳 <b>{{ report.picks }} 条</b></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右栏：快速开始 + 最近运行 -->
      <div>
        <div class="sec-h"><h2>快速开始</h2></div>
        <div class="card">
          <div class="qlist">
            <button v-for="q in QUICK" :key="q.cmd" class="qirow" @click="go(q.cmd)">
              <span class="qic"><el-icon><component :is="q.icon" /></el-icon></span>
              <span class="qn">{{ q.label }}</span>
              <code class="qc">{{ q.cmd }}</code>
              <el-icon class="arw"><ArrowRight /></el-icon>
            </button>
          </div>
        </div>

        <div class="sec-h">
          <h2>最近运行</h2>
          <button class="more" @click="emit('open-runs')">全部记录</button>
        </div>
        <div class="card">
          <div v-for="(res, i) in recent" :key="i" class="rrow" @click="emit('open-runs')">
            <span class="rdot" :class="res.json?.ok ? 'ok' : 'err'" />
            <div class="rmain">
              <div class="rc">bili {{ res.argv.join(' ') }}</div>
              <div class="rs">{{ summary(res) }}</div>
            </div>
            <span class="rt">{{ res.elapsed }}s</span>
          </div>
          <div v-if="!recent.length" class="empty-mini">
            <el-icon><Document /></el-icon>
            <span>这次启动还没跑过命令</span>
            <span>右边「快速开始」挑一条试试</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
