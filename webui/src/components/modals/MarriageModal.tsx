/* 婚配沙龙：候选浏览、六维对比、缔结姻缘 */

import { useEffect, useMemo, useState } from 'react'
import { useStore, runAction } from '../../store'
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
  const [cands, setCands] = useState<CharacterInfo[] | null>(null)
  const [sort, setSort] = useState<SortKey>('total')

  useEffect(() => {
    if (modal !== 'marriage') return
    setCands(null)
    void api.candidates().then((r) => setCands((r.candidates as CharacterInfo[]) ?? []))
  }, [modal, snap?.date.year, snap?.date.month, snap?.date.xun])

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

  return (
    <div className="veil" onClick={closeModal}>
      <div className="modal" style={{ width: 'min(640px, 92vw)' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">婚配沙龙</span>
          <span className="panel-sub">
            为 {player?.name} 择偶 · 眷属上限 {married ? 1 : 0}/{snap.meta.consort_limit}
          </span>
          <button className="btn ghost modal-x" onClick={closeModal}>✕</button>
        </div>
        <div className="modal-body">
          {married && (
            <div className="empty" style={{ padding: '18px 0' }}>
              家主已有配偶，暂不能再婚。
              <div style={{ marginTop: 6, fontSize: 12 }}>
                配偶：<span className="link" onClick={() => { select(player!.spouse!); closeModal() }}>
                  {snap.characters.find((c) => c.id === player!.spouse)?.name}
                </span>
              </div>
            </div>
          )}
          {!married && sorted == null && <div className="empty"><span className="spin" /></div>}
          {!married && sorted != null && sorted.length === 0 && (
            <div className="empty">眼下没有合适的候选 —— 且待时日</div>
          )}
          {!married &&
            sorted?.map((c) => (
              <div key={c.id} className="candidate" onClick={() => void marry(c)}>
                <Sigil name={c.name} gender={c.gender} did={c.dynasty} size={40} />
                <div style={{ minWidth: 0 }}>
                  <div>
                    {c.name}
                    <span style={{ color: 'var(--ink-faint)', fontSize: 12 }}>
                      {' · '}{c.culture_label} · {c.age}岁{c.relation ? ` · ${c.relation}` : ''}
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
                  缔结
                </button>
              </div>
            ))}
        </div>
        <div className="modal-foot">
          <span style={{ color: 'var(--ink-faint)', fontSize: 12, marginRight: 'auto' }}>
            排序：
            {([['total', '综合'], ['top', '单项'], ['age', '年幼']] as const).map(([k, label]) => (
              <button key={k} className={`fchip ${sort === k ? 'on' : ''}`} onClick={() => setSort(k)}>
                {label}
              </button>
            ))}
          </span>
          <button className="btn" onClick={closeModal}>返回</button>
        </div>
      </div>
    </div>
  )
}
