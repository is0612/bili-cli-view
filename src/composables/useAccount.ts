import { computed, ref } from 'vue'
import { api } from '../api'
import type { Meta } from '../types'

/**
 * 当前登录的 B站 账号：多个面板都要用（发动态、公开评论），只请求一次。
 *
 * 界面上不能再写死某个昵称 —— 这个面板是给别人用的，写死的名字属于作者，
 * 新人看到会以为要发到别人号上，确认弹窗也就失去意义了。
 */
const meta = ref<Meta | null>(null)
let inflight: Promise<void> | null = null

async function load(force = false) {
  if (meta.value && !force) return
  if (inflight) return inflight
  inflight = api
    .meta()
    .then((m) => {
      meta.value = m
    })
    .catch(() => {
      /* 没登录 / 后端没起：保持空，界面上会有对应的提示 */
    })
    .finally(() => {
      inflight = null
    })
  return inflight
}

export function useAccount() {
  const loggedIn = computed(() => Boolean(meta.value?.auth.ok && meta.value?.auth.user))
  const name = computed(() => meta.value?.auth.user?.name || '')
  /** 文案里用：登录了就是「昵称」，没登录就是「你的账号」 */
  const label = computed(() => (loggedIn.value ? `「${name.value}」` : '你的账号'))

  return { meta, loggedIn, name, label, load }
}
