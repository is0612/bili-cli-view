<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, Check, VideoPlay, MagicStick, Promotion } from '@element-plus/icons-vue'
import type { CommandItem } from '../types'

const props = defineProps<{ item: CommandItem; initial?: Record<string, string>; autorun?: boolean }>()
const emit = defineEmits<{ (e: 'run', argv: string[]): void }>()

const values = reactive<Record<string, any>>({})
const dryRun = ref(true)
const busy = ref(false)

function reset() {
  for (const key of Object.keys(values)) delete values[key]
  for (const p of props.item.params ?? []) {
    const preset = props.initial?.[p.key]
    values[p.key] = p.type === 'bool' ? preset === '1' : (preset ?? p.default ?? '')
  }
  dryRun.value = true
}

watch(() => props.item, reset, { immediate: true })

const params = computed(() => props.item.params ?? [])
const inputs = computed(() => params.value.filter((p) => p.type !== 'bool'))
const toggles = computed(() => params.value.filter((p) => p.type === 'bool'))

const argv = computed(() => {
  const out = [...props.item.argv]
  for (const p of params.value) {
    const v = values[p.key]
    if (p.type === 'bool') {
      if (v && p.flag) out.push(p.flag)
      continue
    }
    const text = String(v ?? '').trim()
    if (!text) continue
    if (p.pos) out.push(text)
    else if (p.flag) out.push(p.flag, text)
  }
  if (props.item.write && dryRun.value) out.push('--dry-run')
  return out
})

const preview = computed(() =>
  'bili ' + argv.value.map((a) => (a.includes(' ') ? `"${a}"` : a)).join(' '),
)

/** 位置参数就是必填：空着直接跑，CLI 只会回一句 Missing argument。 */
const missing = computed(() =>
  inputs.value
    .filter((p) => p.pos && !String(values[p.key] ?? '').trim())
    .map((p) => p.label),
)

function submit() {
  if (busy.value) return
  if (missing.value.length) {
    ElMessage.warning({ message: `还差：${missing.value.join('、')}`, grouping: true })
    return
  }
  emit('run', argv.value)
}

async function copyCmd() {
  try {
    await navigator.clipboard.writeText(preview.value)
    ElMessage.success({ message: '命令已复制', grouping: true })
  } catch {
    ElMessage.warning({ message: '剪贴板不可用', grouping: true })
  }
}

defineExpose({ setBusy: (v: boolean) => (busy.value = v), submit })

onMounted(() => {
  if (props.autorun) setTimeout(submit, 120)
})
</script>

<template>
  <el-card class="runner-card" shadow="never">
    <div class="runner-head">
      <div class="runner-icon">
        <el-icon :size="17"><Promotion v-if="item.write" /><MagicStick v-else /></el-icon>
      </div>
      <div style="min-width: 0; flex: 1">
        <div class="runner-title">
          {{ item.label }}
          <el-tag v-if="item.write" type="warning" effect="plain" size="small" round>写操作</el-tag>
        </div>
        <div class="cmd-chip" style="margin-top: 7px">bili {{ item.argv.join(' ') }}</div>
        <div v-if="item.desc" class="muted" style="margin-top: 6px; line-height: 1.6">{{ item.desc }}</div>
      </div>
    </div>

    <el-form class="runner-form" label-position="top" @submit.prevent>
      <el-row :gutter="12">
        <el-col v-for="p in inputs" :key="p.key" :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item>
            <template #label>
              <span>{{ p.label }}</span>
              <span v-if="p.pos" style="color: var(--el-color-danger); margin-left: 3px">*</span>
            </template>
            <el-select v-if="p.type === 'select'" v-model="values[p.key]" style="width: 100%">
              <el-option v-for="c in p.choices" :key="c" :label="c" :value="c" />
            </el-select>
            <el-input
              v-else
              v-model="values[p.key]"
              :type="p.type === 'int' ? 'number' : 'text'"
              :placeholder="p.ph"
              clearable
            />
          </el-form-item>
        </el-col>

        <el-col v-for="p in toggles" :key="p.key" :xs="24" :sm="12" :md="8" :lg="6">
          <el-form-item :label="p.label">
            <el-checkbox v-model="values[p.key]">启用</el-checkbox>
          </el-form-item>
        </el-col>
      </el-row>

      <div
        style="
          display: flex;
          align-items: center;
          gap: 12px;
          justify-content: flex-end;
          margin-bottom: 14px;
        "
      >
        <span v-if="missing.length" class="muted" style="margin-right: auto">
          还差必填：{{ missing.join('、') }}
        </span>
        <el-checkbox v-if="item.write" v-model="dryRun">安全预览（加 --dry-run）</el-checkbox>
        <el-button
          type="primary"
          :loading="busy"
          :disabled="missing.length > 0"
          style="width: 128px"
          @click="submit"
        >
          <el-icon v-if="!busy" style="margin-right: 5px"><VideoPlay /></el-icon>
          {{ busy ? '执行中' : '运行' }}
        </el-button>
      </div>
    </el-form>

    <div class="preview">
      <el-icon style="color: #55637a"><Promotion /></el-icon>
      <code>{{ preview }}</code>
      <el-button link size="small" @click="copyCmd">
        <el-icon><CopyDocument /></el-icon>
      </el-button>
    </div>
  </el-card>
</template>
