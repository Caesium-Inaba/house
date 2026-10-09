/* 档案室：多存档槽的保存 / 读取 / 删除 */

import { useEffect, useState } from 'react'
import { useStore, runAction } from '../../store'
import { api } from '../../api/client'
import type { SaveInfo } from '../../types'

function fmtTime(mtime: number): string {
  const d = new Date(mtime * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

export default function SaveModal() {
  const snap = useStore((s) => s.snap)
  const modal = useStore((s) => s.modal)
  const closeModal = useStore((s) => s.closeModal)
  const busy = useStore((s) => s.busy)
  const [saves, setSaves] = useState<SaveInfo[]>([])
  const [name, setName] = useState('')
  const [overwrite, setOverwrite] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  useEffect(() => {
    if (modal !== 'saves') return
    void api.saves().then((r) => setSaves((r.saves as SaveInfo[]) ?? []))
  }, [modal])

  useEffect(() => {
    if (modal === 'saves' && snap) {
      const dyn = snap.dynasties.find((d) => d.id === snap.characters.find((c) => c.id === snap.player_id)?.dynasty)
      setName(`${dyn?.name ?? ''}${snap.date.year}年`)
      setOverwrite(null)
      setConfirmDelete(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modal])

  if (modal !== 'saves' || !snap) return null

  const doSave = async (force = false) => {
    const res = await runAction(() => api.save(name, force), { silent: true })
    if (res.saves) setSaves(res.saves)
    if (res.exists) setOverwrite(name)
    else if (res.ok) {
      setOverwrite(null)
      useStore.getState().toast(res.message ?? '已保存', 'good')
    }
  }

  const doLoad = async (s: SaveInfo) => {
    const res = await runAction(() => api.load(s.name), { silent: true })
    if (res.ok) {
      useStore.getState().toast(res.message ?? '已读取', 'good')
      closeModal()
    }
  }

  const doDelete = async (s: SaveInfo) => {
    const res = await runAction(() => api.delSave(s.name), { silent: true })
    if (res.saves) setSaves(res.saves)
    setConfirmDelete(null)
  }

  const fresh = name.trim() && !saves.some((s) => s.name === name.trim())

  return (
    <div className="veil" onClick={closeModal}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">档案室</span>
          <span className="panel-sub">当前 {snap.date.label}</span>
          <button className="btn ghost modal-x" onClick={closeModal}>✕</button>
        </div>
        <div className="modal-body">
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input
              type="text"
              value={name}
              maxLength={24}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void doSave(false)}
              style={{ flex: 1 }}
              placeholder="存档名…"
            />
            {overwrite ? (
              <button className="btn danger" disabled={busy} onClick={() => void doSave(true)}>
                覆盖「{overwrite}」
              </button>
            ) : (
              <button className="btn primary" disabled={busy || !name.trim()} onClick={() => void doSave(false)}>
                {fresh ? '保存' : '覆盖保存'}
              </button>
            )}
          </div>

          {saves.length === 0 && <div className="empty">还没有任何存档 —— 历史正等待书写</div>}
          {saves.map((s) => (
            <div key={s.name} className="save-slot">
              <span className="s-name">{s.name}</span>
              <span className="s-meta">
                {s.year}年{s.month}月 · {fmtTime(s.mtime)}
              </span>
              {confirmDelete === s.name ? (
                <>
                  <button className="btn danger" onClick={() => void doDelete(s)}>确认删除</button>
                  <button className="btn ghost" onClick={() => setConfirmDelete(null)}>取消</button>
                </>
              ) : (
                <>
                  <button className="btn" disabled={busy} onClick={() => void doLoad(s)}>读取</button>
                  <button className="btn ghost" title="删除" onClick={() => setConfirmDelete(s.name)}>🗑</button>
                </>
              )}
            </div>
          ))}
        </div>
        <div className="modal-foot">
          <button className="btn ghost" style={{ marginRight: 'auto' }} onClick={() => useStore.getState().openModal('new')}>
            开启新篇章…
          </button>
          <button className="btn" onClick={closeModal}>返回</button>
        </div>
      </div>
    </div>
  )
}
