import { ElMessage } from 'element-plus'

/** 全局提示：直接用 Element Plus 的 ElMessage，省掉自绘 toast。 */
export function useToast() {
  function notify(text: string, error = false) {
    ElMessage({
      message: text,
      type: error ? 'error' : 'success',
      grouping: true,
      duration: 3200,
      showClose: true,
    })
  }
  return { notify }
}
