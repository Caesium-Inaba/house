/* 婚配沙龙：联姻（家主）/ 订婚（为自家孩童缔结婚约，可母系） */

import { useEffect, useMemo, useState } from 'react'
import { useStore, runAction } from '../../store'
import { t } from '../../i18n'
import { api } from '../../api/client'
import type { CharacterInfo } from '../../types'
import { Sigil } from '../../heraldry'

type SortKey = 'total' | 'top' | 'age'

export default function MarriageModal() {
  const snap = useStore((s) => s.snap)
  const modal = useStore((s) => s.modal)
  const closeModal = useStore((s) => s.closeModal)
  const busy = useStore((s) => s.busy)
  const select = useStore((s) => s.select)
  const [tab, setTab] = useState<'marriage' | 'betrothal'>('marriage')
  const [cands, setCands] = useState<CharacterInfo[] | null>(null)
  const [own, setOwn] = useState<CharacterInfo[] | null>(null)
  const [other, setOther] = useState<CharacterInfo[] | null>(null)
  const [sort, setSort] = useState<SortKey>('total')
  const [ownSel, setOwnSel] = useState<CharacterInfo | null>(null)
  const [otherSel, setOtherSel] = useState<CharacterInfo | null>(null)
  const [matrilineal, setMatrilineal] = useState(false)

  useEffect(() => {
    if (modal !== 'marriage') return
    setCands(null)
    setOwn(null)
    setOther(null)
    void api.candidates().then((r) => setCands((r.candidates as CharacterInfo[]) ?? []))
    void api.betrothalPools().then((r) => {
      setOwn((r.own as CharacterInfo[]) ?? [])
      setOther((r.other as CharacterInfo[]) ?? [])
    })
  }, [modal, snap?.date.year, snap?.date.month, snap?.date.day])

  const sorted = useMemo(() => {
    if (!cands) return null
    const total = (c: CharacterInfo) => Object.values(c.attributes).reduce((s, v) => s + v, 0)
    const top = (c: CharacterInfo) => Math.max(...Object.values(c.attributes))
    const arr = [...cands]
    if (sort === 'total') arr.sort((a, b) => total(b) - total(a))
    else if (sort === 'top') arr.sort((a, b) => top(b) - top(a))
    else arr.sort((a, b) => a.age - b.age)
    return arr
  }, [cands, sort])

  if (modal !== 'marriage' || !snap) return null
  const player = snap.characters.find((c) => c.id === snap.player_id)
  const married = player?.spouse != null

  const marry = async (target: CharacterInfo) => {
    const res = await runAction(() => api.marry(target.id))
    if (res.ok) {
      select(target.id)
      closeModal()
    }
  }

  const betroth = async () => {
    if (!ownSel || !otherSel) return
    const res = await runAction(() => api.betrothal(ownSel.id, otherSel.id, !matrilineal))
    if (res.ok) {
      setOwnSel(null)
      setOtherSel(null)
    }
  }

  return (
    <div className="veil" onClick={closeModal}>
      <div className="modal" style={{ width: 'min(720px, 94vw)' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">{t('modal.marriage')}</span>
          <div style={{ display: 'flex', gap: 8, marginLeft: 14 }}>
            <button className={`fchip ${tab === 'marriage' ? 'on' : ''}`} onClick={() => setTab('marriage')}>{t('marriage.tab_marriage')}</button>
            <button className={`fchip ${tab === 'betrothal' ? 'on' : ''}`} onClick={() => setTab('betrothal')}>{t('marriage.tab_betrothal')}</button>
          </div>
          <span className="panel-sub" style={{ marginLeft: 'auto' }}>
            {tab === 'marriage'
              ? t('marriage.for', { name: player?.name ?? '', n: married ? 1 : 0, m: snap.meta.consort_limit })
              : t('marriage.betrothal_for')}
          </span>
          <button className="btn ghost modal-x" onClick={closeModal}>✕</button>
        </div>

        <div className="modal-body" style={{ minHeight: 320 }}>
          {tab === 'marriage' && (
            <>
              {married && (
                <div className="empty">
                  {t('marriage.already')}
                  <div style={{ marginTop: 6, fontSize: 12 }}>
                    {t('marriage.spouse')}
                    <span className="link" onClick={() => { select(player!.spouse!); closeModal() }}>
                      {snap.characters.find((c) => c.id === player!.spouse)?.name}
                    </span>
                  </div>
                </div>
              )}
              {!married && sorted == null && <div className="empty"><span className="spin" /></div>}
              {!married && sorted != null && sorted.length === 0 && (
                <div className="empty">{t('marriage.none')}</div>
              )}
              {!married &&
                sorted?.map((c) => (
                  <div key={c.id} className="candidate" onClick={() => void marry(c)}>
                    <Sigil name={c.name} gender={c.gender} did={c.dynasty} size={40} />
                    <div style={{ minWidth: 0 }}>
                      <div>
                        {c.name}
                        <span style={{ color: 'var(--ink-faint)', fontSize: 12 }}>
                          {' · '}{c.culture_label} · {t('dyn.age', { n: c.age })}{c.relation ? ` · ${c.relation}` : ''}
                        </span>
                      </div>
                      <div className="cand-attrs">
                        {snap.meta.attrs.map((a) => (
                          <span key={a.key} className="cand-attr">
                            {a.label}
                            <b>{c.attributes[a.key] ?? 0}</b>
                          </span>
                        ))}
                      </div>
                      {c.genes.filter((g) => g.state === 2).length > 0 && (
                        <div className="chips" style={{ marginTop: 5 }}>
                          {c.genes.filter((g) => g.state === 2).map((g) => (
                            <span key={g.id} className={`chip ${g.polarity}`} style={{ fontSize: 11 }}>
                              {g.name}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    <button className="btn primary" disabled={busy} style={{ padding: '5px 12px', fontSize: 12.5 }}>
                      {t('marriage.marry')}
                    </button>
                  </div>
                ))}
            </>
          )}

          {tab === 'betrothal' && (
            <>
              <div style={{ color: 'var(--ink-faint)', fontSize: 12, marginBottom: 10 }}>
                {t('betrothal.hint')}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div>
                  <div className="divider-label" style={{ marginTop: 0 }}>{t('betrothal.own')}</div>
                  {own == null && <div className="empty"><span className="spin" /></div>}
                  {own != null && own.length === 0 && <div className="empty">{t('betrothal.no_own')}</div>}
                  {own?.map((c) => (
                    <div
                      key={c.id}
                      className="roster-item"
                      style={{
                        borderColor: ownSel?.id === c.id ? 'var(--gold)' : 'transparent',
                        background: ownSel?.id === c.id ? 'var(--gold-faint)' : undefined,
                        cursor: 'pointer',
                      }}
                      onClick={() => setOwnSel(c)}
                    >
                      <Sigil name={c.name} gender={c.gender} did={c.dynasty} size={30} />
                      <span className="r-name">
                        {c.name}
                        <span style={{ color: 'var(--ink-faint)', fontSize: 11.5 }}> · {c.age}岁{c.childhood_trait ? ` · ${c.childhood_trait.name}` : ''}</span>
                      </span>
                    </div>
                  ))}
                </div>
                <div>
                  <div className="divider-label" style={{ marginTop: 0 }}>{t('betrothal.other')}</div>
                  {other == null && <div className="empty"><span className="spin" /></div>}
                  {other != null && other.length === 0 && <div className="empty">{t('betrothal.no_other')}</div>}
                  {other?.map((c) => (
                    <div
                      key={c.id}
                      className="roster-item"
                      style={{
                        borderColor: otherSel?.id === c.id ? 'var(--gold)' : 'transparent',
                        background: otherSel?.id === c.id ? 'var(--gold-faint)' : undefined,
                        cursor: 'pointer',
                      }}
                      onClick={() => setOtherSel(c)}
                    >
                      <Sigil name={c.name} gender={c.gender} did={c.dynasty} size={30} />
                      <span className="r-name">
                        {c.name}
                        <span style={{ color: 'var(--ink-faint)', fontSize: 11.5 }}>
                          {' · '}{t('dyn.age', { n: c.age })} · {c.culture_label}
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14, cursor: 'pointer', color: 'var(--ink-dim)', fontSize: 13 }}>
                <input type="checkbox" checked={matrilineal} onChange={(e) => setMatrilineal(e.target.checked)} />
                {t('betrothal.matrilineal')}
              </label>
            </>
          )}
        </div>

        <div className="modal-foot">
          {tab === 'marriage' && (
            <span style={{ color: 'var(--ink-faint)', fontSize: 12, marginRight: 'auto' }}>
              {t('marriage.candidate_sort')}
              {(['total', 'top', 'age'] as const).map((k) => (
                <button key={k} className={`fchip ${sort === k ? 'on' : ''}`} onClick={() => setSort(k)}>
                  {t(k === 'total' ? 'marriage.sort_total' : k === 'top' ? 'marriage.sort_top' : 'marriage.sort_age')}
                </button>
              ))}
            </span>
          )}
          {tab === 'betrothal' && (
            <button
              className="btn primary"
              style={{ marginRight: 'auto' }}
              disabled={!ownSel || !otherSel || busy}
              onClick={() => void betroth()}
            >
              {ownSel && otherSel
                ? t('betrothal.confirm', {
                    a: ownSel.name,
                    b: otherSel.name,
                    m: matrilineal ? ` (${t('char.betrothal_line_m')})` : '',
                  })
                : t('betrothal.confirm_idle')}
            </button>
          )}
          <button className="btn" onClick={closeModal}>{t('modal.back')}</button>
        </div>
      </div>
    </div>
  )
}
