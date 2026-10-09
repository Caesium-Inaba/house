/* 婚配沙龙：联姻（家主）/ 订婚（为自家孩童缔结婚约，可母系） */

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
          <span className="modal-title">婚配沙龙</span>
          <div style={{ display: 'flex', gap: 8, marginLeft: 14 }}>
            <button className={`fchip ${tab === 'marriage' ? 'on' : ''}`} onClick={() => setTab('marriage')}>联姻</button>
            <button className={`fchip ${tab === 'betrothal' ? 'on' : ''}`} onClick={() => setTab('betrothal')}>订婚</button>
          </div>
          <span className="panel-sub" style={{ marginLeft: 'auto' }}>
            {tab === 'marriage'
              ? `为 ${player?.name} 择偶 · 眷属 ${married ? 1 : 0}/${snap.meta.consort_limit}`
              : '为自家孩童缔结婚约'}
          </span>
          <button className="btn ghost modal-x" onClick={closeModal}>✕</button>
        </div>

        <div className="modal-body" style={{ minHeight: 320 }}>
          {tab === 'marriage' && (
            <>
              {married && (
                <div className="empty">
                  家主已有配偶，暂不能再婚。
                  <div style={{ marginTop: 6, fontSize: 12 }}>
                    配偶：
                    <span className="link" onClick={() => { select(player!.spouse!); closeModal() }}>
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
            </>
          )}

          {tab === 'betrothal' && (
            <>
              <div style={{ color: 'var(--ink-faint)', fontSize: 12, marginBottom: 10 }}>
                为自家满怀希望的孩子订下婚约；对方到 16 岁将自动成婚。母系婚姻让子女归于母亲家族。
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div>
                  <div className="divider-label" style={{ marginTop: 0 }}>自家孩童</div>
                  {own == null && <div className="empty"><span className="spin" /></div>}
                  {own != null && own.length === 0 && <div className="empty">家中暂无可订婚的孩童（6-15 岁）</div>}
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
                  <div className="divider-label" style={{ marginTop: 0 }}>心仪人家</div>
                  {other == null && <div className="empty"><span className="spin" /></div>}
                  {other != null && other.length === 0 && <div className="empty">别家暂无可订婚的孩童</div>}
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
                          {' · '}{c.age}岁 · {c.culture_label}
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14, cursor: 'pointer', color: 'var(--ink-dim)', fontSize: 13 }}>
                <input type="checkbox" checked={matrilineal} onChange={(e) => setMatrilineal(e.target.checked)} />
                母系婚姻 —— 所生子女入母亲家族（保住血脉的关键选项）
              </label>
            </>
          )}
        </div>

        <div className="modal-foot">
          {tab === 'marriage' && (
            <span style={{ color: 'var(--ink-faint)', fontSize: 12, marginRight: 'auto' }}>
              排序：
              {([['total', '综合'], ['top', '单项'], ['age', '年幼']] as const).map(([k, label]) => (
                <button key={k} className={`fchip ${sort === k ? 'on' : ''}`} onClick={() => setSort(k)}>
                  {label}
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
                ? `缔结婚约：${ownSel.name} × ${otherSel.name}${matrilineal ? '（母系）' : ''}`
                : '缔结婚约（选定两侧后可用）'}
            </button>
          )}
          <button className="btn" onClick={closeModal}>返回</button>
        </div>
      </div>
    </div>
  )
}
