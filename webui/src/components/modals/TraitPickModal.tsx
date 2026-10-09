/* 性情抉择：9/12/15 岁孩童的性格定型（师长言传 / 率性而为） */

import { useState } from 'react'
import { useStore, runAction } from '../../store'
import { api } from '../../api/client'
import { Sigil } from '../../heraldry'
import { t } from '../../i18n'

export default function TraitPickModal() {
  const snap = useStore((s) => s.snap)
  const modal = useStore((s) => s.modal)
  const closeModal = useStore((s) => s.closeModal)
  const busy = useStore((s) => s.busy)
  const [selectedChild, setSelectedChild] = useState<number | null>(null)
  const [chosen, setChosen] = useState<string | null>(null)

  const entry = snap?.trait_queue[0] ?? null
  const child =
    entry ?? snap?.trait_queue.find((e) => e.child_id === selectedChild) ?? null

  if (modal !== 'traitpick' || !snap || !child) return null

  const confirm = async () => {
    if (!chosen) return
    const res = await runAction(() => api.traitPick(child.child_id, chosen), { silent: true })
    if (res.ok) {
      setChosen(null)
      setSelectedChild(null)
      const next = useStore.getState().snap
      if (!next || next.trait_queue.length === 0) closeModal()
    }
  }

  return (
    <div className="veil" onClick={closeModal}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 'min(540px, 92vw)' }}>
        <div className="modal-head">
          <span className="modal-title">{t('modal.traitpick')}</span>
          {snap.trait_queue.length > 1 && (
            <span className="panel-sub">{t('traitpick.queue_more', { n: snap.trait_queue.length - 1 })}</span>
          )}
          <button className="btn ghost modal-x" onClick={closeModal}>{t('modal.close')}</button>
        </div>
        <div className="modal-body">
          {snap.trait_queue.length > 1 && (
            <div className="chips" style={{ marginBottom: 14 }}>
              {snap.trait_queue.map((e) => (
                <button
                  key={e.child_id}
                  className={`chip ${e.child_id === child.child_id ? 'positive' : ''}`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => {
                    setSelectedChild(e.child_id)
                    setChosen(null)
                  }}
                >
                  {e.name}
                </button>
              ))}
            </div>
          )}

          <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
            <Sigil name={child.name} gender={child.gender} did={undefined} size={46} />
            <div>
              <div style={{ fontSize: 16, color: 'var(--gold-bright)' }}>
                {child.name}
                {child.relation ? <span style={{ color: 'var(--ink-dim)', fontSize: 12.5 }}> · {child.relation}</span> : null}
              </div>
              <div style={{ color: 'var(--ink-dim)', fontSize: 12.5 }}>
                {child.age} 岁
                {child.guardian_name
                  ? <> · {t('traitpick.guardian_side')}：{child.guardian_name}</>
                  : ` · ${t('traitpick.no_guardian')}`}
              </div>
            </div>
          </div>

          {child.existing.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <span className="divider-label" style={{ marginTop: 0, marginBottom: 4 }}>{t('traitpick.existing')}</span>
              <div className="chips">
                {child.existing.map((n) => (
                  <span key={n} className="chip">{n}</span>
                ))}
              </div>
            </div>
          )}

          <div className="divider-label">择其天性</div>
          <div style={{ display: 'grid', gap: 8 }}>
            {child.options.map((o) => (
              <div
                key={o.id}
                className="save-slot"
                style={{
                  cursor: 'pointer',
                  borderColor: chosen === o.id ? 'var(--gold-dim)' : 'var(--edge)',
                  padding: '9px 12px',
                }}
                onClick={() => setChosen(o.id)}
              >
                <Sigil name={o.name} gender={child.gender} did={undefined} size={28} />
                <span className="s-name" style={{ fontSize: 13.5 }}>{o.name}</span>
                <span
                  style={{
                    color: o.kind === 'taught' ? 'var(--steel)' : 'var(--ink-faint)',
                    fontSize: 11.5,
                  }}
                >
                  {o.kind === 'taught' ? t('traitpick.guardian_side') : t('traitpick.stray')}
                </span>
              </div>
            ))}
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn" onClick={closeModal}>{t('modal.shelve')}</button>
          <button className="btn primary" disabled={busy || !chosen} onClick={() => void confirm()}>
            {t('traitpick.confirm')}
          </button>
        </div>
      </div>
    </div>
  )
}
