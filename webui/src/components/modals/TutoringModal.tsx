/* 教养礼：为满 6 岁的孩子选定教育方向与监护人 */

import { useState } from 'react'
import { useStore, runAction } from '../../store'
import { api } from '../../api/client'
import { Sigil } from '../../heraldry'

export default function TutoringModal() {
  const snap = useStore((s) => s.snap)
  const modal = useStore((s) => s.modal)
  const closeModal = useStore((s) => s.closeModal)
  const busy = useStore((s) => s.busy)
  const queue = snap?.tutoring_queue ?? []
  const [selectedChild, setSelectedChild] = useState<number | null>(null)
  const child = queue.find((e) => e.child_id === (selectedChild ?? queue[0]?.child_id)) ?? null
  const [focus, setFocus] = useState<string | null>(null)
  const [guardianId, setGuardianId] = useState<number | null>(null)

  // 换孩子时重置选择（用 cheap derive：focus 默认取该孩子 suggested_focus）
  const effectiveFocus = focus ?? child?.suggested_focus ?? null
  const effectiveGuardian =
    guardianId ?? child?.guardian_candidates.find((g) => g.suggested)?.id ?? null

  if (modal !== 'tutoring' || !snap || !child) return null

  const confirm = async () => {
    if (!effectiveFocus) return
    const res = await runAction(() => api.tutoring(child.child_id, effectiveFocus, effectiveGuardian), {
      silent: true,
    })
    if (res.ok) {
      useStore.getState().toast(res.message ?? '开蒙落定', 'good')
      setFocus(null)
      setGuardianId(null)
      const next = useStore.getState().snap
      if (!next || next.tutoring_queue.length === 0) closeModal()
      setSelectedChild(null)
    }
  }

  return (
    <div className="veil" onClick={closeModal}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 'min(620px, 92vw)' }}>
        <div className="modal-head">
          <span className="modal-title">教养礼</span>
          {snap.tutoring_queue.length > 1 && (
            <span className="panel-sub">尚有 {snap.tutoring_queue.length - 1} 位孩童待开蒙</span>
          )}
          <button className="btn ghost modal-x" onClick={closeModal}>✕</button>
        </div>
        <div className="modal-body">
          {snap.tutoring_queue.length > 1 && (
            <div className="chips" style={{ marginBottom: 14 }}>
              {snap.tutoring_queue.map((e) => (
                <button
                  key={e.child_id}
                  className={`chip ${e.child_id === child.child_id ? 'positive' : ''}`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => {
                    setSelectedChild(e.child_id)
                    setFocus(null)
                    setGuardianId(null)
                  }}
                >
                  {e.name}
                </button>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 14 }}>
            <Sigil name={child.name} gender={child.gender} did={undefined} size={46} />
            <div>
              <div style={{ fontSize: 16, color: 'var(--gold-bright)' }}>
                {child.name}
                {child.relation ? <span style={{ color: 'var(--ink-dim)', fontSize: 12.5 }}> · {child.relation}</span> : null}
              </div>
              <div style={{ color: 'var(--ink-dim)', fontSize: 12.5 }}>
                {child.age} 岁{child.childhood_trait ? ` · 童年特质「${child.childhood_trait.name}」` : ''}
              </div>
            </div>
          </div>

          <div className="divider-label" style={{ marginTop: 6 }}>教育方向</div>
          <div className="chips">
            {child.focus_options.map((o) => (
              <button
                key={o.key}
                className={`chip ${effectiveFocus === o.key ? 'positive' : ''}`}
                style={{ cursor: 'pointer', fontFamily: 'var(--font-body)' }}
                onClick={() => {
                  setFocus(o.key)
                  setGuardianId(null)
                }}
              >
                {o.label}
                {child.suggested_focus === o.key ? ' ◆推' : ''}
              </button>
            ))}
          </div>
          <div style={{ color: 'var(--ink-faint)', fontSize: 11.5, marginTop: 6 }}>
            与童年特质匹配的教育方向更有可能成才（CK3 判定：+20 权，不匹配 −20 权）。
          </div>

          <div className="divider-label" style={{ marginTop: 14 }}>择师（监护人）</div>
          {child.guardian_candidates.map((g) => (
            <div
              key={g.id}
              className={`save-slot ${effectiveGuardian === g.id ? '' : ''}`}
              style={{
                cursor: 'pointer',
                borderColor: effectiveGuardian === g.id ? 'var(--gold-dim)' : 'var(--edge)',
                padding: '8px 12px',
              }}
              onClick={() => setGuardianId(g.id)}
            >
              <Sigil name={g.name} gender="male" did={undefined} size={28} />
              <span className="s-name" style={{ fontSize: 13 }}>
                {g.name}
                {g.suggested ? <span style={{ color: 'var(--gold)', fontSize: 11 }}> ◆推</span> : ''}
              </span>
              <span style={{ color: 'var(--ink-faint)', fontSize: 11.5 }}>学识 {g.learning}</span>
              <span style={{ color: 'var(--gold)', fontSize: 13 }}>
                {child.focus_options.find((o) => o.key === effectiveFocus)?.label ?? ''} {g.skill}
              </span>
            </div>
          ))}
          {child.guardian_candidates.length === 0 && (
            <div style={{ color: 'var(--ink-faint)', fontSize: 12.5 }}>族中无可为师者 —— 无监护人将显著降低成才率。</div>
          )}
        </div>
        <div className="modal-foot">
          <button className="btn" onClick={closeModal}>先搁置</button>
          <button className="btn primary" disabled={busy || !effectiveFocus} onClick={() => void confirm()}>
            落定教养
          </button>
        </div>
      </div>
    </div>
  )
}
