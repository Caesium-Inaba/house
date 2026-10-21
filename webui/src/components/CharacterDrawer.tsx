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

/** 亲属芯片：点击切换抽屉；已故者以 † 标记 */
function KinChips({
  ids,
  byId,
  select,
}: {
  ids: (number | null | undefined)[]
  byId: Map<number, CharacterInfo>
  select: (id: number) => void
}) {
  const list = [...new Set(ids.filter((x): x is number => x != null))]
    .map((id) => byId.get(id))
    .filter((c): c is CharacterInfo => c != null)
    .sort((a, b) => b.birth_year - a.birth_year)
  if (list.length === 0) return <span className="kin-none">—</span>
  return (
    <div className="chips" style={{ marginTop: 2 }}>
      {list.map((c) => (
        <button
          key={c.id}
          className={`chip kin-chip ${c.alive ? '' : 'dead'}`}
          onClick={() => select(c.id)}
          title={c.display_name ?? c.name}
        >
          {c.name}{c.alive ? '' : ' †'}
        </button>
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
  const [selfRenameOpen, setSelfRenameOpen] = useState(false)
  const [dynRenameOpen, setDynRenameOpen] = useState(false)
  const [dynName, setDynName] = useState('')
  const [guardianPick, setGuardianPick] = useState<number | ''>('')
  const [giftUid, setGiftUid] = useState<number | null>(null)
  const [giftTarget, setGiftTarget] = useState<number | ''>('')

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
  const dyn = snap.dynasties.find((d) => d.id === char.dynasty)
  const canRenameDynasty = !!player && char.alive && !snap.over && dyn?.head === player.id
  const arts = char.artifacts ?? []
  const ownsArtifacts = isSelfHead && char.alive && !snap.over

  // 亲属：兄弟姐妹 / 长辈（父母 + 祖父母） / 儿女
  const siblingIds = snap.characters
    .filter(
      (c) =>
        c.id !== char.id &&
        ((char.father != null && c.father === char.father) ||
          (char.mother != null && c.mother === char.mother)),
    )
    .map((c) => c.id)
  const elderIds: (number | null)[] = [char.father, char.mother]
  for (const pid of [char.father, char.mother]) {
    if (pid == null) continue
    const p = byId.get(pid)
    if (p) elderIds.push(p.father, p.mother)
  }

  // 监护：家主可以为本族未成年成员指定/更换/解除
  // 家主可以为族内任何未成年人指定/更换/解除监护（不要求抽屉开的是自己）
  const canManageGuardian =
    !!player && char.alive && !snap.over && char.id !== player.id &&
    !char.is_adult && char.dynasty != null && char.dynasty === player.dynasty
  const guardianCandidates = snap.characters.filter(
    (c) => c.alive && c.is_adult && c.id !== char.id && c.dynasty === player?.dynasty,
  )

  // 宝物赠予对象：同族或在世配偶
  const giftTargets = snap.characters.filter(
    (c) => c.alive && c.id !== char.id && (c.dynasty === char.dynasty || c.spouse === char.id || char.spouse === c.id),
  )

  const toast = (msg: string | null | undefined, kind: 'good' | 'bad' | 'info' = 'good') => {
    if (msg) useStore.getState().toast(msg, kind)
  }

  const suicide = async () => {
    const res = await runAction(() => api.suicide(), { silent: true })
    if (res.ok) useStore.getState().toast(res.message ?? t('api.suicide'), 'bad')
  }
  const debugKill = async () => {
    const res = await runAction(() => fetch('/api/debug/kill', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_id: char.id }),
    }).then((r) => r.json()) as Promise<import('../types').ApiResponse>, { silent: true })
    if (res.ok) useStore.getState().toast(res.message ?? t('api.debug_kill', { name: char.name }), 'bad')
  }
  const rename = async () => {
    const res = await runAction(() => api.rename(char.id, renameVal), { silent: true })
    if (res.ok) {
      setRenameVal('')
      useStore.getState().toast(res.message ?? t('api.renamed', { name: renameVal }), 'good')
    }
  }
  const renameSelf = async () => {
    const res = await runAction(() => api.renameSelf(renameVal), { silent: true })
    if (res.ok) {
      setRenameVal('')
      setSelfRenameOpen(false)
      toast(res.message)
    }
  }
  const renameDynasty = async () => {
    const res = await runAction(() => api.renameDynasty(dynName), { silent: true })
    if (res.ok) {
      setDynName('')
      setDynRenameOpen(false)
      toast(res.message)
    }
  }
  const setGuardian = async (gid: number | null) => {
    const res = await runAction(() => api.setGuardian(char.id, gid), { silent: true })
    if (res.ok) {
      setGuardianPick('')
      toast(res.message)
    }
  }
  const artifactOp = async (fn: () => Promise<import('../types').ApiResponse>) => {
    const res = await runAction(fn, { silent: true })
    if (res.ok) toast(res.message)
    return res
  }
  const giftArtifact = async (uid: number) => {
    if (giftTarget === '') return
    const res = await artifactOp(() => api.artifactGift(uid, Number(giftTarget)))
    if (res.ok) {
      setGiftUid(null)
      setGiftTarget('')
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
        {isSelfHead && char.alive && !snap.over && (
          <button
            className="btn ghost mini-pencil"
            title={t('drawer.rename_self')}
            onClick={() => {
              setRenameVal(char.name)
              setSelfRenameOpen((v) => !v)
            }}
          >
            ✎
          </button>
        )}
      </div>
      {isSelfHead && selfRenameOpen && (
        <div style={{ display: 'flex', gap: 6, margin: '2px 0 8px' }}>
          <input
            type="text"
            value={renameVal}
            maxLength={12}
            autoFocus
            onChange={(e) => setRenameVal(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && renameVal.trim() && void renameSelf()}
            style={{ flex: 1, fontSize: 12.5, padding: '5px 10px' }}
          />
          <button className="btn primary" style={{ padding: '4px 10px', fontSize: 12 }} disabled={!renameVal.trim() || busy} onClick={() => void renameSelf()}>
            {t('drawer.rename')}
          </button>
        </div>
      )}
      {!isSelfHead && liege && (
        <div style={{ color: 'var(--ink-dim)', fontSize: 12, marginBottom: 8 }}>
          {t('drawer.relation_to_liege')}：
          <OpBadge v={char.opinion_of_player} />
        </div>
      )}

      {/* 宗族盾徽：点击查看该家族家族树；家主可改宗族名 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <button
          className="drawer-dynasty"
          style={{ flex: 1, minWidth: 0 }}
          onClick={() => {
            setTreeOpen(true)
          }}
          title={t('drawer.view_tree')}
        >
          <Crest did={char.dynasty} female={char.gender === 'female'} size={34} />
          <span>{dyn?.name ?? t('drawer.no_dynasty')}</span>
          <span style={{ color: 'var(--ink-faint)', fontSize: 11 }}>{char.culture_label}</span>
        </button>
        {canRenameDynasty && (
          <button
            className="btn ghost mini-pencil"
            title={t('drawer.rename_dynasty')}
            onClick={() => {
              setDynName(dyn?.name ?? '')
              setDynRenameOpen((v) => !v)
            }}
          >
            ✎
          </button>
        )}
      </div>
      {dynRenameOpen && (
        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
          <input
            type="text"
            value={dynName}
            maxLength={16}
            autoFocus
            onChange={(e) => setDynName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && dynName.trim() && void renameDynasty()}
            style={{ flex: 1, fontSize: 12.5, padding: '5px 10px' }}
          />
          <button className="btn primary" style={{ padding: '4px 10px', fontSize: 12 }} disabled={!dynName.trim() || busy} onClick={() => void renameDynasty()}>
            {t('drawer.rename')}
          </button>
        </div>
      )}

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
        {char.alive && char.relation != null && (
          <>
            <div className="divider-label" style={{ marginTop: 10 }}>
              {t('stress.label')} ·{' '}
              {snap?.meta.stress_tiers.find((tier) => tier.key === char.stress_tier)?.label ?? ''}
              <span style={{ marginLeft: 'auto', color: 'var(--ink-faint)' }}>
                {char.stress}/{snap?.meta.max_stress ?? 400}
              </span>
            </div>
            <div className="bar stress">
              <div className="fill" style={{ width: `${Math.min(100, (char.stress / (snap?.meta.max_stress ?? 400)) * 100)}%` }} />
            </div>
          </>
        )}
        {char.pregnant && (
          <div style={{ color: 'var(--verdant)', fontSize: 12.5, marginTop: 6 }}>
            ♡ {t('char.pregnant', { n: Math.max(1, Math.ceil((char.pregnancy_days_left ?? 0) / 30)) })}
          </div>
        )}
      </div>

      {/* 血脉 / 心性 / 教养 */}
      <div className="chips" style={{ marginTop: 10 }}>
        {char.genes.filter((g) => g.state === 2).map((g) => (
          <span key={g.id} className={`chip ${g.polarity}`}>{g.name}</span>
        ))}
        {char.genes.filter((g) => g.state === 1).map((g) => (
          <span key={g.id} className={`chip carrier ${g.polarity}`}>{t('drawer.carrier')} {g.name}</span>
        ))}
        {char.childhood_trait && !char.education_name && (
          <span className="chip" style={{ borderColor: 'var(--steel)', color: 'var(--steel)' }}>{char.childhood_trait.name}</span>
        )}
        {char.education_name && <span className="chip" style={{ borderColor: 'var(--gold-dim)', color: 'var(--gold)' }}>{char.education_name}</span>}
        {char.traits.map((tr) => <span key={tr.id} className="chip">{tr.name}</span>)}
        <span className="chip" style={{ borderColor: 'var(--plum)', color: 'var(--plum)' }}>{char.sexuality_label}</span>
      </div>

      {/* 宝物：装备/卸下/重铸/销毁/赠予（玩家本人可操作） */}
      {arts.length > 0 && (
        <>
          <div className="divider-label" style={{ marginTop: 12 }}>{t('drawer.artifacts')}</div>
          {arts.map((a) => (
            <div key={a.uid} className="artifact-row">
              <div style={{ minWidth: 0, flex: 1 }}>
                <div className="artifact-title">
                  <b>{a.name}</b>
                  {a.equipped && <span className="artifact-worn">{t('artifact.equipped')}</span>}
                </div>
                <div className="artifact-meta">
                  {a.rarity_label} · {a.slot_label} · {t('artifact.durability', { n: a.durability, max: a.max_durability })}
                </div>
                {a.effect_summary && <div className="artifact-effect">{a.effect_summary}</div>}
              </div>
              {ownsArtifacts && (
                <div className="artifact-actions">
                  <button
                    className="btn ghost"
                    disabled={busy}
                    onClick={() => void artifactOp(() => (a.equipped ? api.artifactUnequip(a.uid) : api.artifactEquip(a.uid)))}
                  >
                    {a.equipped ? t('artifact.unequip') : t('artifact.equip')}
                  </button>
                  {a.reforgeable && (
                    <button className="btn ghost" disabled={busy} onClick={() => void artifactOp(() => api.artifactReforge(a.uid))}>
                      {t('artifact.reforge')}
                    </button>
                  )}
                  <button
                    className="btn ghost"
                    disabled={busy}
                    onClick={() => {
                      if (window.confirm(t('artifact.destroy_confirm', { name: a.name }))) {
                        void artifactOp(() => api.artifactDestroy(a.uid))
                      }
                    }}
                  >
                    {t('artifact.destroy')}
                  </button>
                  <button
                    className="btn ghost"
                    disabled={busy}
                    onClick={() => {
                      setGiftUid(giftUid === a.uid ? null : a.uid)
                      setGiftTarget('')
                    }}
                  >
                    {t('artifact.gift')}
                  </button>
                </div>
              )}
              {ownsArtifacts && giftUid === a.uid && (
                <div className="artifact-gift">
                  <select value={giftTarget} onChange={(e) => setGiftTarget(e.target.value === '' ? '' : Number(e.target.value))}>
                    <option value="">{t('artifact.gift_pick')}</option>
                    {giftTargets.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}（{c.age}）
                      </option>
                    ))}
                  </select>
                  <button
                    className="btn primary"
                    disabled={giftTarget === '' || busy}
                    onClick={() => void giftArtifact(a.uid)}
                  >
                    {t('artifact.gift_confirm')}
                  </button>
                </div>
              )}
            </div>
          ))}
        </>
      )}

      {/* 亲属：兄弟姐妹 / 长辈 / 儿女 */}
      <div className="divider-label" style={{ marginTop: 12 }}>{t('drawer.kin')}</div>
      <div className="kin-head">
        {t('drawer.kin_to_liege')}
        <b>{isSelfHead ? t('relation.self') : (char.relation ?? t('drawer.kin_none'))}</b>
      </div>
      <div className="kin-group">
        <span className="kin-label">{t('drawer.kin_siblings')}</span>
        <KinChips ids={siblingIds} byId={byId} select={select} />
      </div>
      <div className="kin-group">
        <span className="kin-label">{t('drawer.kin_elders')}</span>
        <KinChips ids={elderIds} byId={byId} select={select} />
      </div>
      <div className="kin-group">
        <span className="kin-label">{t('drawer.kin_children')}</span>
        <KinChips ids={char.children} byId={byId} select={select} />
      </div>

      {/* 关系：监护人 / 被监护人（同一位置） */}
      {(myGuardian || wards.length > 0 || canManageGuardian) && (
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
          {canManageGuardian && (
            <div className="guardian-box">
              <div className="guardian-current">
                {t('drawer.guardian_current')}
                <b>{myGuardian ? myGuardian.name : t('drawer.guardian_none')}</b>
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
                <select
                  value={guardianPick}
                  onChange={(e) => setGuardianPick(e.target.value === '' ? '' : Number(e.target.value))}
                  style={{ flex: 1, minWidth: 120, fontSize: 12, padding: '4px 8px' }}
                >
                  <option value="">{t('drawer.guardian_pick')}</option>
                  {guardianCandidates.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}（{c.age}）
                    </option>
                  ))}
                </select>
                <button
                  className="btn primary"
                  style={{ padding: '4px 10px', fontSize: 12 }}
                  disabled={guardianPick === '' || busy}
                  onClick={() => guardianPick !== '' && void setGuardian(Number(guardianPick))}
                >
                  {myGuardian ? t('drawer.guardian_change') : t('drawer.guardian_assign')}
                </button>
                {myGuardian && (
                  <button
                    className="btn ghost"
                    style={{ padding: '4px 10px', fontSize: 12 }}
                    disabled={busy}
                    onClick={() => void setGuardian(null)}
                  >
                    {t('drawer.guardian_clear')}
                  </button>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* 新生儿改名（非玩家自己） */}
      {isNewborn && !isSelfHead && (
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
