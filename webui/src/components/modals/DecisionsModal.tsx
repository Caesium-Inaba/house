/* 决议：通用减压活动 + 应对机制专属动作（按日冷却） */

import { useStore, runAction } from '../../store'
import { api } from '../../api/client'
import { t } from '../../i18n'

const COST_LABEL: Record<string, string> = {
  money: 'char.money',
  prestige: 'char.prestige',
  piety: 'char.piety',
}

function fmtItems(items: Record<string, number>): string {
  return Object.entries(items)
    .filter(([, v]) => v)
    .map(([k, v]) => `${t(COST_LABEL[k] ?? k)} ${Math.abs(v)}`)
    .join(' · ')
}

export default function DecisionsModal() {
  const snap = useStore((s) => s.snap)
  const modal = useStore((s) => s.modal)
  const closeModal = useStore((s) => s.closeModal)
  const busy = useStore((s) => s.busy)
  if (modal !== 'decisions' || !snap) return null

  const player = snap.characters.find((c) => c.id === snap.player_id)
  const options = snap.decision_options ?? []
  const generic = options.filter((o) => o.group === 'generic')
  const coping = options.filter((o) => o.group === 'coping')

  const run = async (id: string) => {
    await runAction(() => api.decide(id), { silent: true })
  }

  const row = (o: (typeof options)[number]) => (
    <div
      key={o.id}
      className="save-slot"
      style={{ opacity: o.available ? 1 : 0.55, padding: '8px 12px', marginBottom: 6 }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="s-name">{t(`decision.${o.id}.name`)}</div>
        <div style={{ fontSize: 11.5, color: 'var(--ink-faint)' }}>
          {t('decisions.stress', { n: o.stress })}
          {Object.keys(o.cost ?? {}).length > 0 && ` · ${t('decisions.cost', { items: fmtItems(o.cost) })}`}
          {Object.keys(o.gain ?? {}).length > 0 && ` · ${t('decisions.gain', { items: fmtItems(o.gain) })}`}
        </div>
      </div>
      <div style={{ fontSize: 11.5, color: 'var(--ink-dim)', minWidth: 112, textAlign: 'right' }}>
        {o.reason === 'cooldown'
          ? t('decisions.cd', { n: o.cd_left })
          : o.reason === 'locked'
            ? t('decisions.locked', { trait: o.requires ? t(`trait.${o.requires}`) : '?' })
            : o.reason === 'cost'
              ? t('decisions.cost_missing')
              : t('decisions.ready')}
      </div>
      <button className="btn primary" disabled={!o.available || busy} onClick={() => void run(o.id)}>
        {t('decisions.use')}
      </button>
    </div>
  )

  return (
    <div className="veil" onClick={closeModal}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 'min(660px, 94vw)' }}>
        <div className="modal-head">
          <span className="modal-title">{t('modal.decisions')}</span>
          <span className="panel-sub">
            {t('stress.label')} · {player?.stress ?? 0}/{snap.meta.max_stress}
          </span>
          <button className="btn ghost modal-x" onClick={closeModal}>
            ✕
          </button>
        </div>
        <div className="modal-body" style={{ maxHeight: '62vh', overflow: 'auto' }}>
          <div className="divider-label">{t('decisions.generic')}</div>
          {generic.map(row)}
          <div className="divider-label" style={{ marginTop: 12 }}>
            {t('decisions.coping')}
          </div>
          {coping.length === 0 && <div className="empty">{t('decisions.no_coping')}</div>}
          {coping.map(row)}
        </div>
        <div className="modal-foot">
          <button className="btn" onClick={closeModal}>
            {t('modal.back')}
          </button>
        </div>
      </div>
    </div>
  )
}
