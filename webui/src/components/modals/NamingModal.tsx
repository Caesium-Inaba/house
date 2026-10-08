/* 命名礼：为新生儿起名的仪式 */

import { useEffect, useState } from 'react'
import { useStore } from '../../store'
import { runAction } from '../../store'
import { api } from '../../api/client'
import { Sigil } from '../../heraldry'

export default function NamingModal() {
  const snap = useStore((s) => s.snap)
  const modal = useStore((s) => s.modal)
  const closeModal = useStore((s) => s.closeModal)
  const busy = useStore((s) => s.busy)
  const [name, setName] = useState('')

  const entry = snap?.naming_queue[0] ?? null

  useEffect(() => {
    if (modal === 'naming' && entry) setName(entry.suggested)
  }, [modal, entry?.child_id])

  if (modal !== 'naming' || !snap || !entry) return null

  const confirm = async () => {
    const res = await runAction(() => api.naming(entry.child_id, name), { silent: true })
    if (res.ok) {
      useStore.getState().toast(res.message ?? '命名完成', 'good')
      const next = useStore.getState().snap
      if (next && next.naming_queue.length > 0) setName(next.naming_queue[0].suggested)
      else {
        useStore.getState().closeModal()
      }
    }
  }

  return (
    <div className="veil" onClick={closeModal}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 'min(500px, 92vw)' }}>
        <div className="modal-head">
          <span className="modal-title">命名礼</span>
          {snap.naming_queue.length > 1 && (
            <span className="panel-sub">尚有 {snap.naming_queue.length - 1} 位新生儿排队</span>
          )}
          <button className="btn ghost modal-x" onClick={closeModal}>✕</button>
        </div>
        <div className="modal-body" style={{ textAlign: 'center' }}>
          <div style={{ margin: '6px 0 10px', display: 'flex', justifyContent: 'center' }}>
            <Sigil name={entry.suggested} gender={entry.gender} did={undefined} size={64} />
          </div>
          <div style={{ color: 'var(--ink-dim)', fontSize: 13 }}>
            {entry.culture_label}血脉 · {entry.gender === 'male' ? '男婴' : '女婴'}
          </div>
          <div style={{ margin: '8px 0 20px', fontSize: 15 }}>
            家中添了{entry.relation === '自己' ? '一位' : `一位${entry.relation}`}，请为他（她）择定终身之名。
          </div>
          <input
            type="text"
            value={name}
            autoFocus
            maxLength={12}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && name.trim() && void confirm()}
            style={{ width: '100%', fontSize: 16, textAlign: 'center', letterSpacing: '0.2em', padding: '10px 12px' }}
          />
          <div className="divider-label" style={{ justifyContent: 'center' }}>{entry.culture_label}名字池</div>
          <div className="chips" style={{ justifyContent: 'center' }}>
            {entry.suggestions.map((n) => (
              <button
                key={n}
                className="chip"
                style={{ cursor: 'pointer', fontFamily: 'var(--font-body)' }}
                onClick={() => setName(n)}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn" onClick={closeModal}>先搁置</button>
          <button className="btn primary" disabled={!name.trim() || busy} onClick={() => void confirm()}>
            正式命名 <kbd>回车</kbd>
          </button>
        </div>
      </div>
    </div>
  )
}
