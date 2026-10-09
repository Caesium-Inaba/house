/* 新局：选择种子，开启新篇章 */

import { useState } from 'react'
import { useStore, runAction } from '../../store'
import { api } from '../../api/client'

export default function NewGameModal() {
  const modal = useStore((s) => s.modal)
  const closeModal = useStore((s) => s.closeModal)
  const openModal = useStore((s) => s.openModal)
  const busy = useStore((s) => s.busy)
  const [seed, setSeed] = useState('')

  if (modal !== 'new') return null

  const start = async () => {
    const seedNum = seed.trim() ? Number(seed) : null
    const res = await runAction(() => api.newGame(seedNum ? Math.floor(seedNum) : null), { silent: true })
    if (res.ok) {
      useStore.getState().toast(res.message ?? '新的篇章', 'good')
      useStore.getState().select(null)
      closeModal()
    }
  }

  return (
    <div className="veil" onClick={closeModal}>
      <div className="modal" style={{ width: 'min(460px, 92vw)' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">开启新篇章</span>
          <button className="btn ghost modal-x" onClick={closeModal}>✕</button>
        </div>
        <div className="modal-body">
          <p style={{ color: 'var(--ink-dim)', margin: '0 0 14px' }}>
            以新的种子重开 1066 年的波希米亚。当前进度若尚未保存，将被留在风中。
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="number"
              placeholder="种子（留空随机）"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              style={{ flex: 1 }}
              onKeyDown={(e) => e.key === 'Enter' && void start()}
            />
            <button className="btn primary" disabled={busy} onClick={() => void start()}>
              启程
            </button>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn ghost" style={{ marginRight: 'auto' }} onClick={() => openModal('saves')}>
            回到档案室
          </button>
          <button className="btn" onClick={closeModal}>取消</button>
        </div>
      </div>
    </div>
  )
}
