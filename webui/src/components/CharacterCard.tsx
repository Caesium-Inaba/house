/* 左栏：人物卡 —— 信息分层的人物档案 */

import { useStore } from '../store'
import type { CharacterInfo } from '../types'
import { Sigil } from '../heraldry'

function AttrBar({ label, val, max, potential }: { label: string; val: number; max: number; potential: number }) {
  return (
    <div className="attr-row">
      <span className="attr-name">{label}</span>
      <div className="bar">
        <div className="fill" style={{ width: `${Math.min(100, (val / max) * 100)}%` }} />
        <div className="tick" style={{ left: `calc(${Math.min(100, (potential / max) * 100)}% - 1px)` }} title={`潜力 ${potential}`} />
      </div>
      <span className="attr-val">{val}</span>
    </div>
  )
}

function Gened({ char }: { char: CharacterInfo }) {
  const dominant = char.genes.filter((g) => g.state === 2)
  const carriers = char.genes.filter((g) => g.state === 1)
  return (
    <>
      {dominant.length > 0 && (
        <div className="chips" style={{ marginBottom: 6 }}>
          {dominant.map((g) => (
            <span key={g.id} className={`chip ${g.polarity}`} title={`先天特质 · ${g.group ?? ''}`}>
              {g.name}
            </span>
          ))}
        </div>
      )}
      {carriers.length > 0 && (
        <div className="chips">
          {carriers.map((g) => (
            <span
              key={g.id}
              className={`chip carrier ${g.polarity}`}
              title="隐性携带：本人不表现，可能传给后代"
            >
              携 {g.name}
            </span>
          ))}
        </div>
      )}
      {dominant.length === 0 && carriers.length === 0 && (
        <div className="empty" style={{ padding: '8px 0' }}>无先天特质记录</div>
      )}
    </>
  )
}

export default function CharacterCard() {
  const snap = useStore((s) => s.snap)
  const selectedId = useStore((s) => s.selectedId)
  const select = useStore((s) => s.select)

  if (!snap) return <section className="panel" />
  const byId = new Map(snap.characters.map((c) => [c.id, c]))
  const char = byId.get(selectedId ?? snap.player_id) ?? snap.characters.find((c) => c.id === snap.player_id)
  if (!char) return <section className="panel" />
  const spouse = char.spouse != null ? byId.get(char.spouse) : undefined
  const maxAttr = Math.max(20, ...Object.values(char.potential), ...Object.values(char.attributes))
  const children = char.children
    .map((id) => byId.get(id))
    .filter((c): c is CharacterInfo => !!c)
    .sort((a, b) => b.birth_year - a.birth_year)

  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title">人物</span>
        <span className="panel-sub">
          {char.relation === '自己' ? '家主' : (char.relation ?? '外人')}
        </span>
      </div>
      <div className="panel-body">
        {/* 头部 */}
        <div style={{ display: 'flex', gap: 14, alignItems: 'center', marginBottom: 14 }}>
          <Sigil
            name={char.name}
            gender={char.gender}
            alive={char.alive}
            did={char.dynasty}
            size={62}
            player={char.id === snap.player_id}
          />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 19, color: 'var(--gold-bright)', letterSpacing: '0.06em' }}>
              {char.display_name ?? char.name}
            </div>
            <div style={{ color: 'var(--ink-dim)', fontSize: 12.5, marginTop: 2 }}>
              {char.gender === 'male' ? '♂' : '♀'}
              {' · '}
              {snap.dynasties.find((d) => d.id === char.dynasty)?.name ?? '无家族'}
              {' · '}
              {char.culture_label}
            </div>
            <div style={{ color: char.alive ? 'var(--ink-faint)' : 'var(--wax)', fontSize: 12.5, marginTop: 2 }}>
              {char.alive ? `${char.age} 岁 · 在世` : `${char.birth_year}–${char.death_year} · 卒于${char.death_reason_label ?? char.death_reason ?? '未知'} · 享年 ${char.age} 岁`}
            </div>
          </div>
        </div>

        {/* 健康 */}
        <div className="divider-label">健康</div>
        <div className="attr-row">
          <span className="attr-name">体魄</span>
          <div className="bar health" style={{ opacity: char.alive ? 1 : 0.45 }}>
            <div className="fill" style={{ width: `${char.health_norm * 100}%` }} />
          </div>
          <span className="attr-val">{char.health.toFixed(1)}</span>
        </div>
        <div style={{ color: 'var(--ink-faint)', fontSize: 12, textAlign: 'right', marginTop: -2 }}>
          {char.alive ? (char.health_tier_label ?? char.health_tier) : '（终末体魄）'}
        </div>

        {/* 六维 */}
        <div className="divider-label">六维 · 刻度线为潜力</div>
        {snap.meta.attrs.map((a) => (
          <AttrBar
            key={a.key}
            label={a.label}
            val={char.attributes[a.key] ?? 0}
            potential={char.potential[a.key] ?? 0}
            max={maxAttr}
          />
        ))}

        {/* 先天基因 */}
        <div className="divider-label">先天血脉</div>
        <Gened char={char} />

        {/* 性格与教育 */}
        {(char.traits.length > 0 || char.education_name) && (
          <>
            <div className="divider-label">心性 · 教养</div>
            <div className="chips">
              {char.childhood_trait && !char.education_name && (
                <span className="chip" style={{ borderColor: 'var(--steel)', color: 'var(--steel)' }}>
                  {char.childhood_trait.name}
                </span>
              )}
              {char.education_name && <span className="chip" style={{ borderColor: 'var(--gold-dim)', color: 'var(--gold)' }}>{char.education_name}</span>}
              {char.traits.map((t) => (
                <span key={t.id} className="chip">{t.name}</span>
              ))}
            </div>
          </>
        )}

        {/* 教养安排（未成年在学者） */}
        {char.alive && !char.is_adult && char.education_focus && (
          <>
            <div className="divider-label">教养</div>
            <div className="kv">
              <span className="k">开蒙方向</span>
              <span className="v">{char.education_focus_label ?? '—'}</span>
            </div>
            <div className="kv">
              <span className="k">监护人</span>
              <span className="v">
                {char.guardian_name
                  ? <span className="link" onClick={() => char.guardian && select(char.guardian)}>{char.guardian_name}</span>
                  : '尚无（教育受损）'}
              </span>
            </div>
            <div className="kv">
              <span className="k">素养进度</span>
              <span className="v">{char.education_score} / 22</span>
            </div>
          </>
        )}

        {/* 产业 */}
        <div className="divider-label">产业</div>
        <div className="kv"><span className="k">金钱</span><span className="v">{char.money}</span></div>
        <div className="kv"><span className="k">威望</span><span className="v">{char.prestige}</span></div>
        <div className="kv"><span className="k">虔诚</span><span className="v">{char.piety}</span></div>

        {/* 怀孕 */}
        {char.pregnant && (
          <>
            <div className="divider-label">身孕</div>
            <div style={{ color: 'var(--verdant)', fontSize: 13 }}>
              ♡ 有孕在身 · 约余 {char.pregnancy_months_left ?? '?'} 月临盆
            </div>
          </>
        )}

        {/* 印象（好感） */}
        {char.opinions.length > 0 && (
          <>
            <div className="divider-label">印象</div>
            {char.opinions.map((o) => (
              <div key={o.id} className="kv">
                <span className="k">
                  <span className="link" onClick={() => select(o.id)}>{o.name}</span>
                </span>
                <span className="v" style={{ color: o.value >= 0 ? 'var(--verdant)' : 'var(--wax)' }}>
                  {o.value > 0 ? '+' : ''}{o.value}
                </span>
              </div>
            ))}
          </>
        )}

        {/* 婚约（CK3） */}
        {char.betrothed && (
          <>
            <div className="divider-label">婚约</div>
            <div className="roster-item" onClick={() => char.betrothed && select(char.betrothed.id)}>
              <span className="r-name">
                ♍ {char.betrothed.name ?? '貌合之人'}
                <span style={{ color: 'var(--ink-faint)', fontSize: 11.5 }}>
                  {' · '}{char.betrothed.patrilineal === false ? '母系' : '父系'} · 满 16 岁成婚
                </span>
              </span>
            </div>
          </>
        )}

        {/* 配偶 */}
        {spouse && (
          <>
            <div className="divider-label">眷属</div>
            <div className="roster-item" onClick={() => select(spouse.id)}>
              <Sigil name={spouse.name} gender={spouse.gender} alive={spouse.alive} did={spouse.dynasty} size={30} />
              <span className="r-name">
                {spouse.display_name ?? spouse.name}
                {spouse.pregnant ? ' · ♡ 有孕' : ''}
              </span>
              <span className="r-age">{spouse.alive ? `${spouse.age}岁` : '已故'}</span>
            </div>
          </>
        )}

        {/* 子女 */}
        {children.length > 0 && (
          <>
            <div className="divider-label">子女 · {children.length}</div>
            {children.map((c) => (
              <div key={c.id} className={`roster-item ${c.alive ? '' : 'dead'}`} onClick={() => select(c.id)}>
                <Sigil name={c.name} gender={c.gender} alive={c.alive} did={c.dynasty} size={30} />
                <span className="r-name">{c.display_name ?? c.name}</span>
                <span className="r-age">{c.alive ? `${c.age}岁` : `卒于${c.death_year}`}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </section>
  )
}
