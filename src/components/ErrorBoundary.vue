<script setup lang="ts">
import { onErrorCaptured, ref } from 'vue'

/** 渲染结果时万一某条数据形状超预期，至少把错误显示出来，而不是白屏。 */
const error = ref<Error | null>(null)

onErrorCaptured((err) => {
  error.value = err as Error
  return false
})
</script>

<template>
  <div v-if="error" class="err" style="padding: 10px 12px; border-radius: 10px; border: 1px solid #4a2026">
    <div class="msg">渲染出错：{{ error.message }}</div>
    <pre style="margin-top: 8px; max-height: 220px">{{ error.stack }}</pre>
  </div>
  <slot v-else />
</template>
