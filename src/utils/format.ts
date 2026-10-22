/** 结果渲染用的小工具：标题/作者/统计/时长的取值与格式化。 */

export function fmt(n: unknown): string {
  const v = Number(n)
  if (!Number.isFinite(v)) return String(n ?? '')
  if (v >= 1e8) return (v / 1e8).toFixed(1) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(1) + '万'
  return String(v)
}

export function fmtDur(seconds: unknown): string {
  const s = Math.round(Number(seconds))
  if (!Number.isFinite(s) || s <= 0) return ''
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${m}:${String(r).padStart(2, '0')}`
}

export function looksLikeImage(path: string): boolean {
  if (/^https?:\/\/.+\.(jpg|jpeg|png|webp|gif)(\?|$)/i.test(path)) return true
  return /\.(jpg|jpeg|png|webp)(\?|$)/i.test(path) && (path.includes('/') || path.includes('\\'))
}

export function isImage(value: unknown): value is string {
  return typeof value === 'string' && looksLikeImage(value)
}

export function imgSrc(value: string): string {
  return /^https?:/i.test(value)
    ? `/api/proxy?u=${encodeURIComponent(value)}`
    : `/api/img?p=${encodeURIComponent(value)}`
}

export function cardTitle(node: Record<string, unknown>): string {
  for (const key of ['title', 'name', 'uname', 'content', 'text', 'desc', 'bvid', 'mid']) {
    const v = node[key]
    if (typeof v === 'string' && v.trim()) return v
    if (typeof v === 'number') return String(v)
  }
  return ''
}

export function cardSubtitle(node: Record<string, unknown>): string {
  const owner = node.owner as Record<string, unknown> | undefined
  const author = node.author as Record<string, unknown> | undefined
  const up = node.up as Record<string, unknown> | undefined
  const name = (owner?.name ?? author?.name ?? up?.name) as string | undefined
  return name || (typeof node.bvid === 'string' ? node.bvid : '')
}

export function statBits(node: Record<string, unknown>): string[] {
  const stat = (node.stat ?? node.stats) as Record<string, number> | undefined
  const bits: string[] = []
  if (stat) {
    if (stat.view != null) bits.push('▶ ' + fmt(stat.view))
    if (stat.like != null) bits.push('👍 ' + fmt(stat.like))
    if (stat.danmaku != null) bits.push('💬 ' + fmt(stat.danmaku))
    if (stat.reply != null) bits.push('↩ ' + fmt(stat.reply))
  }
  if (node.duration != null) {
    const d = fmtDur(node.duration)
    if (d) bits.push('⏱ ' + d)
  }
  if (typeof node.pubdate === 'string') bits.push(node.pubdate.slice(0, 10))
  return bits
}

const IMAGE_KEYS = [
  'cover',
  'pic',
  'face',
  'image',
  'img',
  'keyframe',
  'thumb',
  'avatar',
  'sheet',
  'frames_sheet',
]

export function findImage(node: Record<string, unknown>): string | null {
  for (const key of IMAGE_KEYS) {
    const v = node[key]
    if (isImage(v)) return v
  }
  for (const key of Object.keys(node)) {
    const v = node[key]
    if (isImage(v)) return v
  }
  return null
}

export function isVideoLike(node: Record<string, unknown>): boolean {
  return Boolean(node.bvid || node.owner || (node.title && node.stat))
}

export function isWatchLike(node: Record<string, unknown>): boolean {
  return Boolean(node.transcript || node.ai_summary)
}
