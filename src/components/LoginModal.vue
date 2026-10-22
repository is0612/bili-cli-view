<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'

const props = defineProps<{ open: boolean; loggedIn: boolean }>()
const emit = defineEmits<{
  (e: 'close'): void
  (e: 'notify', text: string, error?: boolean): void
  (e: 'refresh'): void
}>()

const qr = ref('')
const checking = ref(false)
const qrText = ref('')

async function newQr() {
  if (props.loggedIn && !confirm('当前已登录。再扫一次会先覆盖待扫码状态，继续？')) return
  qrText.value = '正在生成二维码…'
  try {
    const res = await api.login()
    if (res.json?.ok) {
      qr.value = `/api/qr.png?v=${Date.now()}`
      qrText.value = '有效期约 180 秒。手机 B站 App 扫码后点「我已经扫了」。'
    } else {
      qrText.value = ''
      emit('notify', `出码失败：${res.json?.error?.message ?? res.stderr}`, true)
    }
  } catch (err) {
    emit('notify', `出码失败：${(err as Error).message}`, true)
  }
}

async function check() {
  checking.value = true
  try {
    const res = await api.run(['auth', 'status', '--wait=90'])
    if (res.json?.ok) {
      emit('notify', '登录成功')
      emit('refresh')
      emit('close')
    } else {
      emit('notify', res.json?.error?.message ?? '还没扫', true)
    }
  } finally {
    checking.value = false
  }
}

async function cancel() {
  try {
    const res = await api.cancelLogin()
    const ok = res.status?.ok
    emit('notify', ok ? '已恢复到原登录状态' : '已清除待扫码状态')
    emit('refresh')
    emit('close')
  } catch (err) {
    emit('notify', `取消失败：${(err as Error).message}`, true)
  }
}
</script>

<template>
  <div v-if="open" class="modal-mask" @click.self="emit('close')">
    <div class="modal">
      <h2>
        扫码登录
        <span class="spacer" />
        <button class="btn ghost" @click="emit('close')">关闭</button>
      </h2>
      <div class="muted">手机 B站 App →「我的」→ 扫一扫。二维码 3 分钟内有效。</div>

      <div class="row">
        <button class="btn primary" @click="newQr">{{ qr ? '换一张' : '生成二维码' }}</button>
        <button class="btn" :disabled="!qr || checking" @click="check">
          <span v-if="checking" class="spin" />
          我已经扫了
        </button>
        <button class="btn ghost" @click="cancel">取消，回到原登录</button>
      </div>

      <div class="qr-wrap">
        <img v-if="qr" :src="qr" alt="二维码" />
        <div class="muted" style="max-width: 380px">{{ qrText }}</div>
      </div>
    </div>
  </div>
</template>
