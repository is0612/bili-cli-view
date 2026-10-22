<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Hide, Search } from '@element-plus/icons-vue'
import { api } from '../api'
import type { CommandGroup } from '../types'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'saved', groups: CommandGroup[]): void
  (e: 'notify', text: string, error?: boolean): void
}>()

const loading = ref(false)
const saving = ref(false)

/**
 * 完整命令表（含已隐藏项）。
 * 必须用 /api/catalog?all=1 —— 若用过滤后的表，被隐藏的分组在这里也会消失，
 * 就再也没有机会勾回来了。
 */
const fullGroups = ref<CommandGroup[]>([])

/** 编辑态：内部仍存「隐藏清单」（后端契约不变），UI 上勾选 = 显示 */
const hiddenGroups = ref<string[]>([])
const hiddenItems = ref<string[]>([])

/** 弹窗内的搜索词（106 条命令盲翻太费劲） */
const query = ref('')

const groupCount = computed(() => fullGroups.value.length)
const totalItems = computed(() => fullGroups.value.reduce((n, g) => n + g.items.length, 0))

/** 按搜索词过滤后的展示用分组；组名或命令命中就保留 */
const shownGroups = computed<CommandGroup[]>(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return fullGroups.value
  return fullGroups.value
    .map((g) => ({
      ...g,
      items: g.items.filter(
        (i) =>
          g.group.toLowerCase().includes(q) ||
          i.label.toLowerCase().includes(q) ||
          (i.cmd ?? i.argv.join(' ')).toLowerCase().includes(q) ||
          (i.desc ?? '').toLowerCase().includes(q),
      ),
    }))
    .filter((g) => g.items.length > 0)
})

/** 已隐藏条数：整组隐藏按组内条数折算，陈旧 id 不计入 */
const hiddenCount = computed(() => {
  const gs = new Set(hiddenGroups.value)
  const is = new Set(hiddenItems.value)
  let n = 0
  for (const g of fullGroups.value) {
    n += gs.has(g.group) ? g.items.length : g.items.filter((i) => is.has(i.id)).length
  }
  return n
})

const visibleCount = computed(() => totalItems.value - hiddenCount.value)
const allShown = computed(() => totalItems.value > 0 && hiddenCount.value === 0)

/** 取某个组的完整数据（搜索过滤后仍按全量算勾选状态，避免半选判断失真） */
function fullOf(group: string): CommandGroup | undefined {
  return fullGroups.value.find((g) => g.group === group)
}

/** 单个分组的勾选状态：all=全显示 some=显示一部分 none=全隐藏 */
type GroupState = 'all' | 'some' | 'none'
function groupState(g: CommandGroup): GroupState {
  if (hiddenGroups.value.includes(g.group)) return 'none'
  const full = fullOf(g.group) ?? g
  const hiddenN = full.items.filter((i) => hiddenItems.value.includes(i.id)).length
  if (hiddenN === 0) return 'all'
  return hiddenN === full.items.length ? 'none' : 'some'
}

async function load() {
  loading.value = true
  query.value = '' // 每次打开都从全量列表开始，避免上次的搜索词把命令"藏"起来
  try {
    const [m, cat] = await Promise.all([api.menu(), api.catalogAll()])
    fullGroups.value = cat.groups
    hiddenGroups.value = [...m.hidden_groups]
    hiddenItems.value = [...m.hidden_items]
  } catch (err) {
    emit('notify', `读取菜单设置失败：${(err as Error).message}`, true)
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) void load()
  },
)

function toggleGroup(group: string, show: boolean) {
  const g = fullGroups.value.find((x) => x.group === group)
  const ids = new Set((g?.items ?? []).map((i) => i.id))
  // 整组切换时清掉组内单条记录，免得留下互相矛盾的配置
  hiddenItems.value = hiddenItems.value.filter((id) => !ids.has(id))
  hiddenGroups.value = show
    ? hiddenGroups.value.filter((x) => x !== group)
    : [...new Set([...hiddenGroups.value, group])]
}

function toggleItem(id: string, show: boolean) {
  hiddenItems.value = show
    ? hiddenItems.value.filter((x) => x !== id)
    : [...new Set([...hiddenItems.value, id])]
}

/** 全部显示 */
function showAll() {
  hiddenGroups.value = []
  hiddenItems.value = []
}

/** 全部隐藏 */
function hideAll() {
  hiddenGroups.value = fullGroups.value.map((g) => g.group)
  hiddenItems.value = []
}

function toggleAll(show: boolean) {
  if (show) showAll()
  else hideAll()
}

async function save() {
  saving.value = true
  try {
    const res = await api.saveMenu({
      hidden_groups: hiddenGroups.value,
      hidden_items: hiddenItems.value,
    })
    hiddenGroups.value = res.config.hidden_groups
    hiddenItems.value = res.config.hidden_items
    ElMessage.success({ message: '菜单已更新', grouping: true })
    emit('saved', res.groups)
    emit('close')
  } catch (err) {
    emit('notify', `保存失败：${(err as Error).message}`, true)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="open"
    title="管理菜单"
    width="680px"
    align-center
    @update:model-value="emit('close')"
  >
    <template #header>
      <div style="display: flex; align-items: baseline; gap: 2px">
        <span style="font-size: 16px; font-weight: 700">管理菜单</span>
        <span class="modal-sub">已选 {{ visibleCount }} / {{ totalItems }} 条</span>
      </div>
    </template>

    <div class="muted" style="margin-bottom: 12px">
      勾上要用的，取消勾就藏起来 —— 改动只影响显示，命令本身都还在，随时能勾回来。
    </div>

    <el-skeleton v-if="loading" :rows="5" animated />

    <div v-else class="menu-mgr">
      <div class="menu-mgr-toolbar">
        <el-checkbox
          :model-value="allShown"
          :indeterminate="!allShown && visibleCount > 0"
          @change="(v: any) => toggleAll(v)"
        >
          全选
        </el-checkbox>
        <el-input
          v-model="query"
          size="small"
          placeholder="搜命令名 / 命令 / 说明…"
          clearable
          class="menu-mgr-search"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <span class="muted" style="font-size: 12px; white-space: nowrap">
          显示 {{ visibleCount }} / {{ totalItems }}
        </span>
      </div>

      <div v-for="g in shownGroups" :key="g.group" class="menu-grp">
        <div class="menu-grp-head">
          <el-checkbox
            :model-value="groupState(g) === 'all'"
            :indeterminate="groupState(g) === 'some'"
            @change="(v: any) => toggleGroup(g.group, v)"
          >
            <b :class="{ 'is-off': hiddenGroups.includes(g.group) }">{{ g.group }}</b>
          </el-checkbox>
          <span class="menu-grp-cnt">{{ (fullOf(g.group) ?? g).items.length }}</span>
        </div>
        <div class="menu-items">
          <el-checkbox
            v-for="it in g.items"
            :key="it.id"
            class="menu-item"
            :model-value="!hiddenGroups.includes(g.group) && !hiddenItems.includes(it.id)"
            :disabled="hiddenGroups.includes(g.group)"
            @change="(v: any) => toggleItem(it.id, v)"
          >
            <span
              class="menu-item-label"
              :class="{ 'is-off': hiddenGroups.includes(g.group) || hiddenItems.includes(it.id) }"
            >
              {{ it.label }}
            </span>
            <code class="menu-item-cmd">{{ it.cmd ?? it.argv.join(' ') }}</code>
          </el-checkbox>
        </div>
      </div>

      <div v-if="!groupCount" class="menu-empty">
        <el-icon :size="22"><Hide /></el-icon>
        <p>命令表还没加载出来</p>
      </div>
      <div v-else-if="!shownGroups.length" class="menu-empty">
        <el-icon :size="22"><Search /></el-icon>
        <p>没找到「{{ query }}」相关的命令</p>
      </div>
    </div>

    <template #footer>
      <div style="display: flex; align-items: center; justify-content: flex-end; gap: 8px">
        <el-button @click="emit('close')">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.menu-mgr {
  max-height: 58vh;
  overflow-y: auto;
  padding-right: 6px;
}
.menu-mgr-toolbar {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 2px 10px;
  background: var(--surface);
  border-bottom: 1px solid var(--line);
  margin-bottom: 4px;
}
.menu-mgr-search {
  flex: 1;
  min-width: 120px;
}
.menu-grp {
  padding: 8px 2px;
}
.menu-grp + .menu-grp {
  border-top: 1px dashed var(--line);
}
.menu-grp-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.menu-grp-head :deep(.el-checkbox__label) b {
  font-size: 14px;
}
.menu-grp-cnt {
  font: 12px/1 Consolas, monospace;
  color: var(--faint);
  background: var(--bg);
  border-radius: 4px;
  padding: 2px 5px;
}
/* 每条命令一行：复选框 + 名称（左）+ 命令行（右），列对齐不挤 */
.menu-items {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 6px 0 2px 24px;
}
.menu-items .el-checkbox.menu-item {
  width: 100%;
  height: 28px;
  margin-right: 0;
}
.menu-items :deep(.el-checkbox__label) {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  color: var(--text-2);
  padding-left: 8px;
  line-height: 1.4;
}
.menu-item-label {
  flex: 1 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.menu-item-label.is-off {
  color: var(--faint);
}
.menu-grp-head b.is-off {
  color: var(--faint);
}
.menu-item-cmd {
  flex: 0 1 auto;
  max-width: 48%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font: 12px/1 Consolas, monospace;
  color: var(--faint);
  text-align: right;
}
.menu-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 36px 0;
  color: var(--dim);
}
</style>
