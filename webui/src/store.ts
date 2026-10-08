/* 全局状态：zustand 单一 store */

import { create } from 'zustand'
import type { ApiResponse, Snapshot } from './types'
import { api } from './api/client'

export type ModalKind = 'naming' | 'tutoring' | 'marriage' | 'saves' | 'new' | null

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
  modal: ModalKind
  treeOpen: boolean
  toasts: Toast[]

  apply: (res: ApiResponse, opts?: { silent?: boolean }) => void
  toast: (text: string, kind?: Toast['kind']) => void
  dropToast: (id: number) => void
  select: (id: number | null) => void
  setBusy: (b: boolean) => void
  setAuto: (a: boolean) => void
  openModal: (m: ModalKind) => void
  closeModal: () => void
  setTreeOpen: (b: boolean) => void
  boot: () => Promise<void>
}

let toastSeq = 0

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
    modal: null,
    treeOpen: false,
    toasts: [],

    apply(res, opts) {
      if (res.state) set({ snap: res.state })
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

    openModal(m) {
      set({ modal: m })
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
        set({ snap: res as unknown as Snapshot, selectedId: (res as unknown as Snapshot).player_id })
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

/** 推进时间（旬 / 年），返回快照里是否出现需要处理的事 */
export async function tickTime(unit: 'xun' | 'year'): Promise<void> {
  await runAction(() => api.tick(unit), { silent: true })
  const snap = useStore.getState().snap
  if (snap?.over) {
    useStore.getState().setAuto(false)
    useStore.getState().toast(snap.over_reason || '故事终结', 'bad')
  } else if (snap && snap.naming_queue.length > 0) {
    useStore.getState().setAuto(false)
    useStore.getState().openModal('naming')
    useStore.getState().toast('家族添了新丁，需要命名', 'info')
  }
}
