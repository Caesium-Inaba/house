/* 右栏：家族仪表盘 —— 继承 / 眷属 / 人口 / 待命名 / 纹章墙 / 成员名录 */

import { useMemo, useState } from 'react'
import { useStore, runAction } from '../store'
import { api } from '../api/client'
import type { CharacterInfo } from '../types'
import { Sigil, Crest } from '../heraldry'

function Meter({ label, val, warn, cap }: { label: string; val: number; warn?: number; cap?: number }) {
  const pct = Math.min(100, (val / cap!) * 100)
  return (
    <>
      <div className="meter-row">
        <span>{label}</span>
        <span>
          <b>{val}</b>
          {cap != null ? ` / ${cap}` : ''}
        </span>
      </div>
      <div className="bar" style={{ height: 6 }}>
        <div
          className="fill"
          style={{
            width: `${pct}%`,
            background:
              warn != null && val >= warn
                ? 'linear-gradient(90deg, var(--wax-deep), var(--wax))'
                : 'linear-gradient(90deg, #8a6d3b, var(--gold))',
          }}
        />
      </div>
    </>
  )
}

export default function DynastyPanel() {
  const snap = useStore((s) => s.snap)
  const select = useStore((s) => s.select)
  const openModal = useStore((s) => s.openModal)
  const [query, setQuery] = useState('')

  const roster = useMemo(() => {
    if (!snap) return []
    const alive = snap.characters.filter((c) => c.alive)
    alive.sort((a, b) => a.age - b.age)
    const q = query.trim()
    const filtered = q ? alive.filter((c) => c.name.includes(q)) : alive
    return filtered.slice(0, 60)
  }, [snap, query])

  if (!snap) return <section className="panel" />
  const byId = new Map(snap.characters.map((c) => [c.id, c]))
  const player = byId.get(snap.player_id)
  const spouse = player?.spouse != null ? byId.get(player.spouse) : undefined
  const heir = snap.heir
  const pop = snap.population
  const playerDyn = snap.dynasties.find((d) => d.id === player?.dynasty)

  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title">家族</span>
        <span className="panel-sub">{snap.gender_law_label}</span>
      </div>
      <div className="panel-body">
        {/* 待命名 */}
        {snap.naming_queue.length > 0 && (
          <>
            <div className="divider-label" style={{ color: 'var(--gold)' }}>
              待命名 · {snap.naming_queue.length}
            </div>
            {snap.naming_queue.map((n) => (
              <div
                key={n.child_id}
                className="save-slot"
                style={{ cursor: 'pointer' }}
                onClick={() => openModal('naming')}
              >
                <Sigil name={n.suggested} gender={n.gender} did={undefined} size={30} />
                <span className="s-name">
                  {n.suggested}
                  <span style={{ color: 'var(--ink-faint)', fontSize: 11.5 }}> · {n.relation}</span>
                </span>
                <button className="btn primary" style={{ padding: '3px 10px', fontSize: 12 }}>
                  命名礼
                </button>
              </div>
            ))}
          </>
        )}

        {/* 王朝传承 */}
        <div className="divider-label">王朝传承 · 威名 <b style={{ color: 'var(--gold)' }}>{snap.legacies.renown}</b></div>
        {snap.legacies.trees.map((t) => (
          <div key={t.id} className="save-slot" style={{ padding: '8px 12px' }}>
            <span className="s-name" style={{ fontSize: 13 }}>
              {t.label}
              <span style={{ color: 'var(--ink-faint)', fontSize: 11, marginLeft: 6 }}>{t.desc}</span>
            </span>
            <span style={{ letterSpacing: 2, color: t.level === 0 ? 'var(--ink-faint)' : 'var(--gold)' }}>
              {'◆'.repeat(t.level)}{'◇'.repeat(t.max - t.level)}
            </span>
            {t.cost != null ? (
              <button
                className={`btn ${t.affordable ? 'primary' : ''}`}
                style={{ padding: '3px 10px', fontSize: 11.5 }}
                disabled={!t.affordable}
                title={`解锁 ${t.label} 第 ${t.level + 1} 级（${t.cost} 威名）`}
                onClick={() => void runAction(() => api.legacyBuy(t.id))}
              >
                {t.cost}
              </button>
            ) : (
              <span style={{ color: 'var(--gold-dim)', fontSize: 11 }}>★ 满</span>
            )}
          </div>
        ))}

        {/* 待教养 */}
        {snap.tutoring_queue.length > 0 && (
          <>
            <div className="divider-label" style={{ color: '#d0b46a' }}>
              待开蒙 · {snap.tutoring_queue.length}
            </div>
            {snap.tutoring_queue.map((n) => (
              <div
                key={n.child_id}
                className="save-slot"
                style={{ cursor: 'pointer' }}
                onClick={() => openModal('tutoring')}
              >
                <Sigil name={n.name} gender={n.gender} did={undefined} size={30} />
                <span className="s-name">
                  {n.name}
                  <span style={{ color: 'var(--ink-faint)', fontSize: 11.5 }}>
                    {' · '}{n.age}岁{n.childhood_trait ? ` · ${n.childhood_trait.name}` : ''}
                  </span>
                </span>
                <button className="btn primary" style={{ padding: '3px 10px', fontSize: 12 }}>
                  教养礼
                </button>
              </div>
            ))}
          </>
        )}

        {/* 继承 */}
        <div className="divider-label">继承</div>
        {heir ? (
          <div className="roster-item" onClick={() => select(heir.id)}>
            <Sigil name={heir.name} gender={heir.gender} alive did={heir.dynasty} size={30} />
            <span className="r-name">{heir.name}</span>
            <span className="r-age" style={{ color: 'var(--ink-dim)' }}>
              {heir.relation ?? ''} · {heir.age}岁
            </span>
          </div>
        ) : (
          <div style={{ color: 'var(--wax)', fontSize: 13 }}>⚠ 暂无继承人 · 绝嗣风险</div>
        )}

        {/* 眷属 */}
        <div className="divider-label">眷属 · {spouse ? 1 : 0}/{snap.meta.consort_limit}</div>
        {spouse ? (
          <div className="roster-item" onClick={() => select(spouse.id)}>
            <Sigil name={spouse.name} gender={spouse.gender} alive={spouse.alive} did={spouse.dynasty} size={30} />
            <span className="r-name">
              {spouse.name}
              {spouse.pregnant ? ' · ♡' : ''}
            </span>
            <span className="r-age">{spouse.alive ? `${spouse.age}岁` : '已故'}</span>
          </div>
        ) : (
          <div style={{ color: 'var(--ink-faint)', fontSize: 12.5 }}>
            家主单身 · <span className="link" onClick={() => openModal('marriage')}>安排婚配（M）</span>
          </div>
        )}

        {/* 人口 */}
        <div className="divider-label">天下人口</div>
        <Meter label="在世" val={pop.alive} cap={pop.hard_cap} warn={pop.soft_cap} />
        <div style={{ color: 'var(--ink-faint)', fontSize: 11.5, marginTop: 4 }}>
          {pop.alive >= pop.hard_cap
            ? '已抵硬上限：自动婚配停止，受孕大幅下降'
            : pop.alive >= pop.soft_cap
              ? '已过软上限：生育与婚配开始节流'
              : `上限 ${pop.soft_cap} / ${pop.hard_cap}`}
        </div>

        {/* 纹章墙 */}
        <div className="divider-label">诸家纹章 · 威名</div>
        {snap.dynasties.map((d) => (
          <div key={d.id} className="save-slot" style={{ padding: '8px 12px' }}>
            <Crest did={d.id} size={26} />
            <span className="s-name" style={{ fontSize: 13.5 }}>
              {d.name}
              <span style={{ color: 'var(--ink-faint)', fontSize: 11.5 }}> · {d.culture_label}</span>
            </span>
            <span style={{ color: 'var(--gold)', fontSize: 13, fontVariantNumeric: 'tabular-nums' }}>
              {Math.round(d.renown)}
            </span>
          </div>
        ))}

        {/* 成员名录 */}
        <div className="divider-label">在世成员 · {playerDyn?.alive_members ?? pop.alive}</div>
        <input
          type="search"
          placeholder="找人…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ width: '100%', marginBottom: 8, fontSize: 12.5, padding: '5px 10px' }}
        />
        {roster.map((c: CharacterInfo) => (
          <div key={c.id} className={`roster-item ${c.alive ? '' : 'dead'}`} onClick={() => select(c.id)}>
            <Sigil name={c.name} gender={c.gender} alive={c.alive} did={c.dynasty} size={28} player={c.id === snap.player_id} />
            <span className="r-name">
              {c.name}
              {c.relation && c.relation !== '自己' ? <span style={{ color: 'var(--ink-faint)', fontSize: 11.5 }}> · {c.relation}</span> : null}
            </span>
            <span className="r-age">{c.age}岁</span>
          </div>
        ))}
        {roster.length === 0 && <div className="empty">没有匹配的成员</div>}
      </div>
    </section>
  )
}
