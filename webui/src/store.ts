/* 全局状态：zustand 单一 store */

import { create } from 'zustand'
import type { ApiResponse, Snapshot } from './types'
import { api } from './api/client'

export type ModalKind = 'naming' | 'tutoring' | 'traitpick' | 'marriage' | 'saves' | 'new' | null

/** 事件窗口：非模态、可拖拽，事件弹出后时间照常流动（CK3 式） */
export type EventKind = 'naming' | 'tutoring' | 'traitpick'

export interface EventWin {
  kind: EventKind
  x: number
  y: number
}

/** 自动推进速率五档（一旬间隔 ms，档位越高越快） */
export const SPEED_INTERVALS = [1300, 650, 340, 170, 80]

export interface Toast {
  id: number
  text: string
  kind: 'info' | 'good' | 'bad'
}

interface Store {
  snap: Snapshot | null
  selectedId: number | null
  busy: boolean
  auto: boolean
  speed: number
  modal: ModalKind
  eventWins: EventWin[]
  treeOpen: boolean
  drawerOpen: boolean
  pinned: number[]
  toasts: Toast[]

  apply: (res: ApiResponse, opts?: { silent?: boolean }) => void
  toast: (text: string, kind?: Toast['kind']) => void
  dropToast: (id: number) => void
  select: (id: number | null) => void
  setBusy: (b: boolean) => void
  setAuto: (a: boolean) => void
  setSpeed: (n: number) => void
  openModal: (m: ModalKind) => void
  closeModal: () => void
  openEventWin: (kind: EventKind) => void
  closeEventWin: (kind: EventKind) => void
  moveEventWin: (kind: EventKind, x: number, y: number) => void
  setDrawerOpen: (b: boolean) => void
  togglePin: (id: number) => void
  setTreeOpen: (b: boolean) => void
  boot: () => Promise<void>
}

let toastSeq = 0

/* ── 快照引用稳定化（性能） ─────────────────────────
 * 每次操作都返回全量快照，若直接替换引用，整棵 React 树每旬都要 diff。
 * 这里按内容比较 characters / events，逐项复用旧引用；
 * 配合事件行的 React.memo，编年史 400 行在普通旬推进时零重渲染。
 */
function shallowEq(a: unknown, b: unknown): boolean {
  if (a === b) return true
  if (typeof a !== 'object' || typeof b !== 'object' || !a || !b) return false
  const ka = Object.keys(a)
  if (ka.length !== Object.keys(b).length) return false
  return ka.every((k) => (a as Record<string, unknown>)[k] === (b as Record<string, unknown>)[k])
}

const charCache = new Map<number, Snapshot['characters'][number]>()
const eventCache = new Map<string, Snapshot['events'][number]>()

/* 事件浮窗跟随队列：队列已空（超时落定/手动处理完）则关掉对应浮窗 */
function syncEventWins(s: Snapshot) {
  const st = useStore.getState()
  if ((s.naming_queue?.length ?? 0) === 0) st.closeEventWin('naming')
  if ((s.tutoring_queue?.length ?? 0) === 0) st.closeEventWin('tutoring')
  if ((s.trait_queue?.length ?? 0) === 0) st.closeEventWin('traitpick')
}

function stabiliseSnapshot(s: Snapshot): Snapshot {
  const chars = s.characters.map((c) => {
    const prev = charCache.get(c.id)
    if (prev && shallowEq(prev, c)) return prev
    charCache.set(c.id, c)
    return c
  })
  // 事件不可变：内容完全相同即复用引用，新增才产生新引用
  const events = s.events.map((e) => {
    const key = `${e.year}|${e.month}|${e.xun}|${e.type}|${e.text}`
    const prev = eventCache.get(key)
    if (prev) return prev
    eventCache.set(key, e)
    return e
  })
  return { ...s, characters: chars, events }
}

export const useStore = create<Store>((set, get) => {
  function toast(text: string, kind: Toast['kind'] = 'info') {
    if (!text) return
    const id = ++toastSeq
    set((s) => ({ toasts: [...s.toasts, { id, text, kind }] }))
    setTimeout(() => get().dropToast(id), 3400)
  }

  return {
    snap: null,
    selectedId: null,
    busy: false,
    auto: false,
    speed: 3,
    modal: null,
    eventWins: [],
    treeOpen: false,
    drawerOpen: true,
    pinned: [],
    toasts: [],

    apply(res, opts) {
      if (res.state) {
        const s = stabiliseSnapshot(res.state)
        set({ snap: s })
        syncEventWins(s)
      }
      if (res.message && !opts?.silent) toast(res.message, res.ok ? 'good' : 'bad')
    },

    toast,
    dropToast(id) {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    },

    select(id) {
      set({ selectedId: id })
    },

    setBusy(b) {
      set({ busy: b })
    },

    setAuto(a) {
      set({ auto: a })
    },

    setSpeed(n) {
      set({ speed: Math.max(1, Math.min(5, Math.round(n))) })
    },

    openModal(m) {
      set({ modal: m })
    },

    /* 事件浮窗：同 kind 一窗；默认落在中栏（避让左侧人物抽屉） */
    openEventWin(kind) {
      set((s) =>
        s.eventWins.some((w) => w.kind === kind)
          ? s
          : (() => {
              const vw = typeof window !== 'undefined' ? window.innerWidth : 1280
              const vh = typeof window !== 'undefined' ? window.innerHeight : 800
              const x = Math.max(470, Math.min(vw - 520, vw * 0.38 + s.eventWins.length * 36))
              const y = Math.max(52, Math.min(vh - 420, vh * 0.14 + s.eventWins.length * 40))
              return { eventWins: [...s.eventWins, { kind, x, y }] }
            })()
      )
    },

    closeEventWin(kind) {
      set((s) => ({ eventWins: s.eventWins.filter((w) => w.kind !== kind) }))
    },

    moveEventWin(kind, x, y) {
      set((s) => ({
        eventWins: s.eventWins.map((w) => (w.kind === kind ? { ...w, x, y } : w)),
      }))
    },

    setDrawerOpen(b) {
      set({ drawerOpen: b })
    },

    togglePin(id) {
      set((s) => ({
        pinned: s.pinned.includes(id) ? s.pinned.filter((x) => x !== id) : [...s.pinned, id],
      }))
    },

    closeModal() {
      set({ modal: null })
    },

    setTreeOpen(b) {
      set({ treeOpen: b })
    },

    async boot() {
      set({ busy: true })
      try {
        const res = await api.state()
        const snap = res as unknown as Snapshot
        set({ snap: stabiliseSnapshot(snap), selectedId: snap.player_id })
      } catch (e) {
        toast(`无法连接游戏服务：${(e as Error).message}`, 'bad')
      } finally {
        set({ busy: false })
      }
    },
  }
})

/** 统一的动作封装：请求 -> 应用快照 + toast */
export async function runAction(
  fn: () => Promise<ApiResponse>,
  opts?: { silent?: boolean },
): Promise<ApiResponse> {
  const { busy, apply, setBusy } = useStore.getState()
  if (busy) return { ok: false, message: null }
  setBusy(true)
  try {
    const res = await fn()
    apply(res, opts)
    return res
  } catch (e) {
    useStore.getState().toast((e as Error).message, 'bad')
    return { ok: false, message: (e as Error).message }
  } finally {
    setBusy(false)
  }
}

/** 推进时间（旬 / 年）；事件弹出后时间照常流动（CK3 式）——只开浮窗，不停表。
 *
 * 备份（旧行为）：遇事件 setAuto(false) 并打开阻塞式 modal；已由事件浮窗替代，
 * 恢复方法：在 openEventWin 处换回 setAuto(false)+openModal(...)。
 */
export async function tickTime(unit: 'xun' | 'year'): Promise<void> {
  await runAction(() => api.tick(unit), { silent: true })
  const snap = useStore.getState().snap
  if (snap?.over) {
    useStore.getState().setAuto(false)
    useStore.getState().closeEventWin('naming')
    useStore.getState().closeEventWin('tutoring')
    useStore.getState().closeEventWin('traitpick')
    useStore.getState().toast(snap.over_reason || '故事终结', 'bad')
  } else if (snap && snap.naming_queue.length > 0) {
    useStore.getState().openEventWin('naming')
  } else if (snap && (snap.tutoring_queue.length > 0 || snap.trait_queue.length > 0)) {
    useStore
      .getState()
      .openEventWin(snap.tutoring_queue.length > 0 ? 'tutoring' : 'traitpick')
  }
}
