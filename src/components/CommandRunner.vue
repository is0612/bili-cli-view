<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import type { CommandItem } from '../types'

const props = defineProps<{ item: CommandItem; initial?: Record<string, string>; autorun?: boolean }>()
const emit = defineEmits<{ (e: 'run', argv: string[]): void }>()

const values = reactive<Record<string, string | boolean>>({})
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

function submit() {
  if (busy.value) return
  emit('run', argv.value)
}

defineExpose({
  setBusy: (v: boolean) => (busy.value = v),
  submit,
})

// 深链自动执行：组件挂载完再触发，避免父组件抢在 v-if 之前调 ref
onMounted(() => {
  if (props.autorun) setTimeout(submit, 120)
})
</script>

<template>
  <div class="card">
    <h3>
      {{ item.label }}
      <span v-if="item.write" class="pill bad">写操作</span>
    </h3>
    <div class="muted">bili {{ item.argv.join(' ') }}</div>

    <div class="form">
      <div v-for="p in params" :key="p.key" class="field">
        <label>{{ p.label }}</label>
        <select v-if="p.type === 'select'" v-model="values[p.key]">
          <option v-for="c in p.choices" :key="c" :value="c">{{ c }}</option>
        </select>
        <label v-else-if="p.type === 'bool'" class="check">
          <input v-model="values[p.key]" type="checkbox" />
          {{ p.label }}
        </label>
        <input
          v-else
          v-model="values[p.key]"
          :type="p.type === 'int' ? 'number' : 'text'"
          :placeholder="p.ph"
        />
      </div>

      <label v-if="item.write" class="check">
        <input v-model="dryRun" type="checkbox" />
        预览（加 --dry-run，不真的发）
      </label>

      <button class="btn primary" :disabled="busy" @click="submit">
        <span v-if="busy" class="spin" />
        {{ busy ? '跑…' : '运行' }}
      </button>
    </div>

    <div class="cmdline">{{ preview }}</div>
  </div>
</template>
