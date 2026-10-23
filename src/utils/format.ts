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
  // 用文字标签而不是 emoji：emoji 在明色列表里颜色杂，读起来也不像后台系统
  if (stat) {
    if (stat.view != null) bits.push(`${fmt(stat.view)} 播放`)
    if (stat.like != null) bits.push(`${fmt(stat.like)} 赞`)
    if (stat.coin != null) bits.push(`${fmt(stat.coin)} 币`)
    if (stat.favorite != null) bits.push(`${fmt(stat.favorite)} 藏`)
    if (stat.danmaku != null) bits.push(`${fmt(stat.danmaku)} 弹幕`)
    if (stat.reply != null) bits.push(`${fmt(stat.reply)} 评论`)
  }
  if (node.duration != null) {
    const d = fmtDur(node.duration)
    if (d) bits.push(d)
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

/**
 * 运行记录 / 最近运行用的一句话摘要。
 * 视频类命令的 data 是 `{ zone, items: [...] }`，直接说「6 条 · tech」比「2 个字段」有用。
 */
export function runSummary(res: {
  json?: { ok?: boolean; data?: unknown; error?: { code: string; message: string } } | null
} | null): string {
  const json = res?.json
  if (!json) return '无输出'
  if (json.error) return `${json.error.code}：${json.error.message}`
  const data = json.data
  if (Array.isArray(data)) return `${data.length} 条结果`
  if (data && typeof data === 'object') {
    const o = data as Record<string, unknown>
    if (Array.isArray(o.items)) {
      let zone = ''
      if (typeof o.zone === 'string') zone = o.zone === 'all' ? '全站' : o.zone
      return `${o.items.length} 条${zone ? ` · ${zone}` : ''}`
    }
    // video.watch 这类：说清抓到了什么，比「19 个字段」有用
    if (o.transcript || o.hot_comments || o.frames_sheet) {
      const bits: string[] = []
      if (o.transcript) bits.push('字幕')
      if (o.frames_sheet) bits.push('抽帧图')
      if (Array.isArray(o.hot_comments)) bits.push(`热评 ${o.hot_comments.length} 条`)
      if (bits.length) return bits.join(' · ')
    }
    return `${Object.keys(o).length} 个字段`
  }
  if (typeof data === 'string') return data.length > 60 ? `${data.slice(0, 60)}…` : data
  return json.ok ? '执行成功' : '无输出'
}

/** 本地时间 HH:MM，运行记录里的时间戳用 */
export function hhmm(d = new Date()): string {
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

