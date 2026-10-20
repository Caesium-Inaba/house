/* 新局：选择种子，开启新篇章 */

import { useState } from 'react'
import { useStore, runAction } from '../../store'
import { api } from '../../api/client'
import { t } from '../../i18n'

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
      useStore.getState().toast(res.message ?? t('modal.new'), 'good')
      useStore.getState().select(null)
      closeModal()
    }
  }

  return (
    <div className="veil" onClick={closeModal}>
      <div className="modal" style={{ width: 'min(460px, 92vw)' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">{t('modal.new')}</span>
          <button className="btn ghost modal-x" onClick={closeModal}>✕</button>
        </div>
        <div className="modal-body">
          <p style={{ color: 'var(--ink-dim)', margin: '0 0 14px' }}>
            {t('new.warn')}
          </p>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="number"
              placeholder={t('new.seed')}
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              style={{ flex: 1 }}
              onKeyDown={(e) => e.key === 'Enter' && void start()}
            />
            <button className="btn primary" disabled={busy} onClick={() => void start()}>
              {t('new.start')}
            </button>
          </div>
        </div>
        <div className="modal-foot">
          <button className="btn ghost" style={{ marginRight: 'auto' }} onClick={() => openModal('saves')}>
            {t('new.back_saves')}
          </button>
          <button className="btn" onClick={closeModal}>{t('new.cancel')}</button>
        </div>
      </div>
    </div>
  )
}
