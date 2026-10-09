/* CK3 式可折叠人物栏：全高左侧抽屉，覆盖/收起不影响其它界面布局 */

import { useState } from 'react'
import { useStore, runAction } from '../store'
import { api } from '../api/client'
import { t } from '../i18n'
import { Crest, Sigil } from '../heraldry'
import type { CharacterInfo, Snapshot } from '../types'

function OpBadge({ v }: { v: number | undefined | null }) {
  if (v == null) return <span style={{ color: 'var(--ink-faint)', fontSize: 11 }}>—</span>
  const good = v >= 0
  return (
    <span style={{ color: good ? 'var(--verdant)' : 'var(--wax)', fontSize: 11.5, fontVariantNumeric: 'tabular-nums' }}>
      {good ? '+' : ''}{v}
    </span>
  )
}

function HealthHeart({ char }: { char: CharacterInfo }) {
  const tier = char.health_tier ?? ''
  const color =
    tier === 'excellent' || tier === 'good' ? 'var(--verdant)'
    : tier === 'fine' ? '#d0b46a'
    : tier === 'poor' ? '#c9814d'
    : 'var(--wax)'
  return <span title={char.health_tier_label ?? ''} style={{ color, fontSize: 13 }}>❤</span>
}

function AttrPips({ snap, char }: { snap: Snapshot; char: CharacterInfo }) {
  return (
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
      {snap.meta.attrs.map((a) => (
        <span key={a.key} className="cand-attr" title={a.label}>
          {a.label}
          <b>{char.attributes[a.key] ?? 0}</b>
        </span>
      ))}
    </div>
  )
}

export default function CharacterDrawer() {
  const snap = useStore((s) => s.snap)
  const selectedId = useStore((s) => s.selectedId)
  const select = useStore((s) => s.select)
  const drawerOpen = useStore((s) => s.drawerOpen)
  const setDrawerOpen = useStore((s) => s.setDrawerOpen)
  const pinned = useStore((s) => s.pinned)
  const togglePin = useStore((s) => s.togglePin)
  const openModal = useStore((s) => s.openModal)
  const setTreeOpen = useStore((s) => s.setTreeOpen)
  const busy = useStore((s) => s.busy)
  const [renameVal, setRenameVal] = useState('')

  if (!snap) return null
  const byId = new Map(snap.characters.map((c) => [c.id, c]))
  const char = byId.get(selectedId ?? snap.player_id) ?? byId.get(snap.player_id)
  if (!char) return null

  const player = byId.get(snap.player_id)
  const spouse = char.spouse != null ? byId.get(char.spouse) : undefined
  const isSelfHead = char.id === snap.player_id
  const liege = player ?? undefined
  const heir = snap.heir
  const wards = snap.characters.filter((c) => c.guardian === char.id && c.alive)
  const myGuardian = char.guardian != null ? byId.get(char.guardian) : undefined
  const canSeekSpouse = char.alive && char.is_adult && char.spouse == null && char.betrothed == null && !snap.over
  const isNewborn = char.alive && char.age < 1

  const suicide = async () => {
    const res = await runAction(() => api.suicide(), { silent: true })
    if (res.ok) useStore.getState().toast(res.message ?? '自尽身亡', 'bad')
  }
  const debugKill = async () => {
    const res = await runAction(() => fetch('/api/debug/kill', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_id: char.id }),
    }).then((r) => r.json()) as Promise<import('../types').ApiResponse>, { silent: true })
    if (res.ok) useStore.getState().toast(res.message ?? '已身亡', 'bad')
  }
  const rename = async () => {
    const res = await runAction(() => api.rename(char.id, renameVal), { silent: true })
    if (res.ok) {
      setRenameVal('')
      useStore.getState().toast(res.message ?? '已更名', 'good')
    }
  }

  return (
    <aside className={`char-drawer ${drawerOpen ? 'open' : ''}`}>
      {/* 顶部工具行 */}
      <div className="drawer-tools">
        <button
          className={`btn ghost ${pinned.includes(char.id) ? 'toggle on' : ''}`}
          title={t('drawer.pin')}
          onClick={() => togglePin(char.id)}
        >
          📌
        </button>
        <button className="btn ghost" title={t('drawer.close')} onClick={() => setDrawerOpen(false)}>
          ✕
        </button>
      </div>

      {/* 头像区：主头像 + 配偶；右侧领主/继承人列 */}
      <div className="drawer-portrait-row">
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', minWidth: 0 }}>
          <Sigil name={char.name} gender={char.gender} alive={char.alive} did={char.dynasty} size={92} player={isSelfHead} />
          {spouse ? (
            <div className="drawer-spouse" style={{ cursor: 'pointer' }} onClick={() => select(spouse.id)}>
              <Sigil name={spouse.name} gender={spouse.gender} alive={spouse.alive} did={spouse.dynasty} size={52} />
              <span style={{ fontSize: 11, color: 'var(--ink-faint)' }}>
                {t('drawer.spouse')}
                {spouse.pregnant ? ' ♡' : ''}
              </span>
            </div>
          ) : canSeekSpouse ? (
            <button
              className="drawer-add"
              title={t('drawer.open_marriage')}
              onClick={() => openModal('marriage')}
            >
              ＋
            </button>
          ) : null}
        </div>

        <div className="drawer-liege-col">
          {liege && !isSelfHead && (
            <div className="drawer-mini" onClick={() => select(liege.id)}>
              <Sigil name={liege.name} gender={liege.gender} alive={liege.alive} did={liege.dynasty} size={38} player />
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 10.5, color: 'var(--ink-dim)', letterSpacing: 2 }}>{t('drawer.liege')}</div>
                <div style={{ fontSize: 11.5 }}>{liege.display_name ?? liege.name}</div>
                <OpBadge v={char.opinion_of_player} />
              </div>
            </div>
          )}
          {heir && heir.id !== char.id && (
            <div className="drawer-mini" onClick={() => select(heir.id)}>
              <Sigil name={heir.name} gender={heir.gender} alive did={heir.dynasty} size={38} />
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 10.5, color: 'var(--ink-dim)', letterSpacing: 2 }}>{t('drawer.heir')}</div>
                <div style={{ fontSize: 11.5 }}>{heir.display_name ?? heir.name}</div>
                <OpBadge v={heir.player_opinion} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 名字行（CK3 位置：头像下方） */}
      <div className="drawer-name-line">
        <span className="drawer-name">{char.display_name ?? char.name}</span>
        <span style={{ color: 'var(--ink-dim)' }}>, {char.age}</span>
        <HealthHeart char={char} />
        {char.relation && !isSelfHead && (
          <span style={{ color: 'var(--ink-faint)', fontSize: 12 }}> · {char.relation}</span>
        )}
      </div>
      {!isSelfHead && liege && (
        <div style={{ color: 'var(--ink-dim)', fontSize: 12, marginBottom: 8 }}>
          {t('drawer.relation_to_liege')}：
          <OpBadge v={char.opinion_of_player} />
        </div>
      )}

      {/* 宗族盾徽：点击查看该家族家族树 */}
      <button
        className="drawer-dynasty"
        onClick={() => {
          setTreeOpen(true)
        }}
        title={t('drawer.view_tree')}
      >
        <Crest did={char.dynasty} female={char.gender === 'female'} size={34} />
        <span>{snap.dynasties.find((d) => d.id === char.dynasty)?.name ?? t('drawer.no_dynasty')}</span>
        <span style={{ color: 'var(--ink-faint)', fontSize: 11 }}>{char.culture_label}</span>
      </button>

      {/* 六维 / 产业 / 健康 */}
      <div className="drawer-rows">
        <AttrPips snap={snap} char={char} />
        <div className="divider-label" style={{ marginTop: 10 }}>{t('char.wealth')}</div>
        <div style={{ display: 'flex', gap: 14 }}>
          <span className="cand-attr">{t('char.money')}<b>{char.money}</b></span>
          <span className="cand-attr">{t('char.prestige')}<b>{char.prestige}</b></span>
          <span className="cand-attr">{t('char.piety')}<b>{char.piety}</b></span>
        </div>
        <div className="divider-label" style={{ marginTop: 10 }}>
          {t('char.health')} · {char.alive ? (char.health_tier_label ?? char.health_tier) : t('char.dead')}
        </div>
        {char.alive && (
          <div className="bar health">
            <div className="fill" style={{ width: `${char.health_norm * 100}%` }} />
          </div>
        )}
        {char.pregnant && (
          <div style={{ color: 'var(--verdant)', fontSize: 12.5, marginTop: 6 }}>
            ♡ {t('char.pregnant', { n: char.pregnancy_months_left ?? '?' })}
          </div>
        )}
      </div>

      {/* 血脉 / 心性 / 教养 */}
      <div className="chips" style={{ marginTop: 10 }}>
        {char.genes.filter((g) => g.state === 2).map((g) => (
          <span key={g.id} className={`chip ${g.polarity}`}>{g.name}</span>
        ))}
        {char.genes.filter((g) => g.state === 1).map((g) => (
          <span key={g.id} className={`chip carrier ${g.polarity}`}>携 {g.name}</span>
        ))}
        {char.childhood_trait && !char.education_name && (
          <span className="chip" style={{ borderColor: 'var(--steel)', color: 'var(--steel)' }}>{char.childhood_trait.name}</span>
        )}
        {char.education_name && <span className="chip" style={{ borderColor: 'var(--gold-dim)', color: 'var(--gold)' }}>{char.education_name}</span>}
        {char.traits.map((tr) => <span key={tr.id} className="chip">{tr.name}</span>)}
        <span className="chip" style={{ borderColor: 'var(--plum)', color: 'var(--plum)' }}>{char.sexuality_label}</span>
      </div>

      {/* 关系：监护人 / 被监护人（同一位置） */}
      {(myGuardian || wards.length > 0) && (
        <>
          <div className="divider-label" style={{ marginTop: 12 }}>{t('drawer.relations')}</div>
          {myGuardian && (
            <div className="roster-item" onClick={() => select(myGuardian.id)}>
              <Sigil name={myGuardian.name} gender={myGuardian.gender} alive={myGuardian.alive} did={myGuardian.dynasty} size={28} />
              <span className="r-name">{myGuardian.display_name ?? myGuardian.name}</span>
              <span className="r-age">{t('drawer.my_guardian')}</span>
            </div>
          )}
          {wards.map((w) => (
            <div key={w.id} className="roster-item" onClick={() => select(w.id)}>
              <Sigil name={w.name} gender={w.gender} alive did={w.dynasty} size={28} />
              <span className="r-name">{w.display_name ?? w.name}</span>
              <span className="r-age">{t('drawer.my_ward')}</span>
            </div>
          ))}
        </>
      )}

      {/* 新生儿改名 */}
      {isNewborn && (
        <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
          <input
            type="text"
            value={renameVal}
            maxLength={12}
            placeholder={t('drawer.rename_hint')}
            onChange={(e) => setRenameVal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && renameVal.trim() && void rename()}
            style={{ flex: 1, fontSize: 12.5, padding: '5px 10px' }}
          />
          <button className="btn" style={{ padding: '4px 10px', fontSize: 12 }} disabled={!renameVal.trim() || busy} onClick={() => void rename()}>
            {t('drawer.rename')}
          </button>
        </div>
      )}

      {/* 调试区 */}
      <div className="drawer-debug">
        <button className="btn danger" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy || !isSelfHead || snap.over} onClick={() => void suicide()}>
          {t('drawer.suicide')}
        </button>
        {!isSelfHead && snap.debug && (
          <button className="btn danger" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy || !char.alive} onClick={() => void debugKill()} title={t('drawer.debug_kill')}>
            {t('drawer.debug_kill')}
          </button>
        )}
      </div>
    </aside>
  )
}
