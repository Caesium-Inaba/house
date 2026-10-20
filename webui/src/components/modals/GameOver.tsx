/* 终局画卷：绝嗣之时，展示王朝的一生 */

import { useStore } from '../../store'
import { t } from '../../i18n'

export default function GameOver() {
  const snap = useStore((s) => s.snap)
  const openModal = useStore((s) => s.openModal)
  const setTreeOpen = useStore((s) => s.setTreeOpen)
  if (!snap || (!snap.over && !window.location.search.includes('over-preview'))) return null

  const player = snap.characters.find((c) => c.id === snap.player_id)
  const dyn = snap.dynasties.find((d) => d.id === player?.dynasty)
  const s = snap.stats

  return (
    <div className="gameover-veil">
      <div className="epitaph">
        <div className="go-orn">✦ ─────── ✦ ─────── ✦</div>
        <h1>{snap.over_reason || t('over.fallback')}</h1>
        <div className="go-reason">
          {t('over.summary', { d: dyn?.name ?? '—', s: s.start_year, y: s.years_played })}
        </div>
        <div className="go-stats">
          <div className="go-stat"><b>{s.years_played}</b><span>{t('over.stat_years')}</span></div>
          <div className="go-stat"><b>{s.generations}</b><span>{t('over.stat_generations')}</span></div>
          <div className="go-stat"><b>{s.births}</b><span>{t('over.stat_births')}</span></div>
          <div className="go-stat"><b>{s.deaths}</b><span>{t('over.stat_deaths')}</span></div>
          <div className="go-stat"><b>{s.marriages}</b><span>{t('over.stat_marriages')}</span></div>
        </div>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
          <button className="btn" onClick={() => setTreeOpen(true)}>
            {t('over.view_tree')}
          </button>
          <button className="btn" onClick={() => openModal('saves')}>
            {t('over.view_saves')}
          </button>
          <button className="btn primary" onClick={() => openModal('new')}>
            {t('over.new_game')}
          </button>
        </div>
        <div className="go-orn" style={{ marginTop: 30, fontSize: 11, color: 'var(--ink-faint)', letterSpacing: '0.3em' }}>
          {t('over.candle')}
        </div>
      </div>
    </div>
  )
}
