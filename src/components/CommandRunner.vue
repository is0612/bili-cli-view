<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, MagicStick, Promotion, VideoPlay } from '@element-plus/icons-vue'
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

const preview = computed(
  () => 'bili ' + argv.value.map((a) => (a.includes(' ') ? `"${a}"` : a)).join(' '),
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
  <div class="cmd-h">
    <div class="cmd-ic">
      <el-icon><Promotion v-if="item.write" /><MagicStick v-else /></el-icon>
    </div>
    <div class="hm">
      <h2 class="cmd-title">
        {{ item.label }}
        <span v-if="item.write" class="tag-w">写操作</span>
      </h2>
      <div class="cmd-sub">
        <code>bili {{ item.argv.join(' ') }}</code>
        <span v-if="item.desc">{{ item.desc }}</span>
      </div>
    </div>
  </div>

  <div class="panel">
    <div class="panel-body">
      <div v-if="params.length" class="fields">
        <div v-for="p in inputs" :key="p.key" class="fld" :class="{ wide: p.pos }">
          <label class="fl" :title="p.label">
            {{ p.label }}<i v-if="p.pos">*</i>
          </label>
          <el-select v-if="p.type === 'select'" v-model="values[p.key]" size="default">
            <el-option v-for="c in p.choices" :key="c" :label="c" :value="c" />
          </el-select>
          <el-input
            v-else
            v-model="values[p.key]"
            :type="p.type === 'int' ? 'number' : 'text'"
            :placeholder="p.ph"
            clearable
          />
        </div>

        <div v-for="p in toggles" :key="p.key" class="fld">
          <label class="fl" :title="p.label">{{ p.label }}</label>
          <el-switch v-model="values[p.key]" />
        </div>
      </div>
      <p v-else class="muted" style="margin: 0">这条命令没有参数，直接运行。</p>
    </div>

    <div class="runbar">
      <el-icon class="ri"><Promotion /></el-icon>
      <code :title="preview">{{ preview }}</code>
      <span v-if="item.write && dryRun" class="dry">已加 --dry-run</span>
      <el-button link size="small" title="复制命令" @click="copyCmd">
        <el-icon><CopyDocument /></el-icon>
      </el-button>
      <el-checkbox v-if="item.write" v-model="dryRun" size="small">安全预览</el-checkbox>
      <el-button
        type="primary"
        :loading="busy"
        :disabled="missing.length > 0"
        @click="submit"
      >
        <el-icon v-if="!busy" style="margin-right: 5px"><VideoPlay /></el-icon>
        {{ busy ? '执行中' : '运行' }}
      </el-button>
    </div>
  </div>

  <p v-if="missing.length" class="muted" style="margin: 8px 0 0">
    还差：{{ missing.join('、') }}
  </p>
</template>
