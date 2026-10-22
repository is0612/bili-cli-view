<script setup lang="ts">
import { ref } from 'vue'
import { Iphone } from '@element-plus/icons-vue'
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
    emit('notify', res.status?.ok ? '已恢复到原登录状态' : '已清除待扫码状态')
    emit('refresh')
    emit('close')
  } catch (err) {
    emit('notify', `取消失败：${(err as Error).message}`, true)
  }
}
</script>

<template>
  <el-dialog
    :model-value="open"
    title="扫码登录"
    width="640px"
    align-center
    @update:model-value="emit('close')"
  >
    <template #header>
      <div style="display: flex; align-items: center; gap: 8px">
        <el-icon><Iphone /></el-icon>
        <span style="font-size: 16px; font-weight: 650">扫码登录</span>
      </div>
    </template>

    <el-alert
      type="info"
      :closable="false"
      title="手机 B站 App →「我的」→ 扫一扫，二维码 3 分钟内有效"
      show-icon
    />

    <div style="display: flex; gap: 9px; flex-wrap: wrap; margin-top: 16px">
      <el-button type="primary" @click="newQr">{{ qr ? '换一张' : '生成二维码' }}</el-button>
      <el-button :disabled="!qr" :loading="checking" @click="check">我已经扫了</el-button>
      <el-button text @click="cancel">取消，回到原登录</el-button>
    </div>

    <div class="qr-box">
      <el-image v-if="qr" :src="qr" fit="contain" style="width: 220px; height: 220px; border-radius: 14px; background: #fff; padding: 8px" />
      <div class="muted" style="max-width: 300px; line-height: 1.9">{{ qrText }}</div>
    </div>
  </el-dialog>
</template>
