/* 事件面板体：命名礼 / 教养礼 / 性情抉择。
 * 抽离自（备份的）modal 实现——modal 薄壳与事件浮窗共用此体，逻辑单源。
 */

import { useEffect, useState } from 'react'
import { useStore, runAction } from '../../store'
import { api } from '../../api/client'
import { Sigil } from '../../heraldry'
import { t } from '../../i18n'

/* ── 命名礼 ── */
export function NamingBody({ shelve }: { shelve: () => void }) {
  const snap = useStore((s) => s.snap)
  const busy = useStore((s) => s.busy)
  const [name, setName] = useState('')
  const entry = snap?.naming_queue[0] ?? null

  useEffect(() => {
    if (entry) setName(entry.suggested)
  }, [entry?.child_id])

  if (!snap || !entry) return null

  const confirm = async () => {
    const res = await runAction(() => api.naming(entry.child_id, name), { silent: true })
    if (res.ok) {
      useStore.getState().toast(res.message ?? '命名完成', 'good')
      const next = useStore.getState().snap
      if (next && next.naming_queue.length > 0) setName(next.naming_queue[0].suggested)
    }
  }

  return (
    <>
      <div className="modal-body" style={{ textAlign: 'center' }}>
        <div style={{ margin: '6px 0 10px', display: 'flex', justifyContent: 'center' }}>
          <Sigil name={entry.suggested} gender={entry.gender} did={undefined} size={64} />
        </div>
        <div style={{ color: 'var(--ink-dim)', fontSize: 13 }}>
          {entry.culture_label}血脉 · {entry.gender === 'male' ? '男婴' : '女婴'}
        </div>
        <div style={{ margin: '8px 0 20px', fontSize: 15 }}>
          家中添了{entry.relation === '自己' ? '一位' : `一位${entry.relation}`}，请为他（她）择定终身之名。
        </div>
        <input
          type="text"
          value={name}
          maxLength={12}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && name.trim() && void confirm()}
          style={{ width: '100%', fontSize: 16, textAlign: 'center', letterSpacing: '0.2em', padding: '10px 12px' }}
        />
        <div className="divider-label" style={{ justifyContent: 'center' }}>{entry.culture_label}名字池</div>
        <div className="chips" style={{ justifyContent: 'center' }}>
          {entry.suggestions.map((n) => (
            <button
              key={n}
              className="chip"
              style={{ cursor: 'pointer', fontFamily: 'var(--font-body)' }}
              onClick={() => setName(n)}
            >
              {n}
            </button>
          ))}
        </div>
      </div>
      <div className="modal-foot">
        <button className="btn" onClick={shelve}>{t('modal.shelve')}</button>
        <button className="btn primary" disabled={!name.trim() || busy} onClick={() => void confirm()}>
          正式命名 <kbd>回车</kbd>
        </button>
      </div>
    </>
  )
}

/* ── 教养礼 ── */
export function TutoringBody({ shelve }: { shelve: () => void }) {
  const snap = useStore((s) => s.snap)
  const busy = useStore((s) => s.busy)
  const queue = snap?.tutoring_queue ?? []
  const [selectedChild, setSelectedChild] = useState<number | null>(null)
  const child = queue.find((e) => e.child_id === (selectedChild ?? queue[0]?.child_id)) ?? null
  const [focus, setFocus] = useState<string | null>(null)
  const [guardianId, setGuardianId] = useState<number | null>(null)

  const effectiveFocus = focus ?? child?.suggested_focus ?? null
  const effectiveGuardian =
    guardianId ?? child?.guardian_candidates.find((g) => g.suggested)?.id ?? null

  if (!snap || !child) return null

  const confirm = async () => {
    if (!effectiveFocus) return
    const res = await runAction(() => api.tutoring(child.child_id, effectiveFocus, effectiveGuardian), {
      silent: true,
    })
    if (res.ok) {
      useStore.getState().toast(res.message ?? '开蒙落定', 'good')
      setFocus(null)
      setGuardianId(null)
      const next = useStore.getState().snap
      if (!next || next.tutoring_queue.length === 0) shelve()
      setSelectedChild(null)
    }
  }

  return (
    <>
      <div className="modal-body">
        {queue.length > 1 && (
          <div className="chips" style={{ marginBottom: 14 }}>
            {queue.map((e) => (
              <button
                key={e.child_id}
                className={`chip ${e.child_id === child.child_id ? 'positive' : ''}`}
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  setSelectedChild(e.child_id)
                  setFocus(null)
                  setGuardianId(null)
                }}
              >
                {e.name}
              </button>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 14 }}>
          <Sigil name={child.name} gender={child.gender} did={undefined} size={46} />
          <div>
            <div style={{ fontSize: 16, color: 'var(--gold-bright)' }}>
              {child.name}
              {child.relation ? <span style={{ color: 'var(--ink-dim)', fontSize: 12.5 }}> · {child.relation}</span> : null}
            </div>
            <div style={{ color: 'var(--ink-dim)', fontSize: 12.5 }}>
              {child.age} 岁{child.childhood_trait ? ` · 童年特质「${child.childhood_trait.name}」` : ''}
            </div>
          </div>
        </div>

        <div className="divider-label" style={{ marginTop: 6 }}>教育方向</div>
        <div className="chips">
          {child.focus_options.map((o) => (
            <button
              key={o.key}
              className={`chip ${effectiveFocus === o.key ? 'positive' : ''}`}
              style={{ cursor: 'pointer', fontFamily: 'var(--font-body)' }}
              onClick={() => {
                setFocus(o.key)
                setGuardianId(null)
              }}
            >
              {o.label}
              {child.suggested_focus === o.key ? ' ◆推' : ''}
            </button>
          ))}
        </div>
        <div style={{ color: 'var(--ink-faint)', fontSize: 11.5, marginTop: 6 }}>
          与童年特质匹配的教育方向更有可能成才（CK3 判定：+20 权，不匹配 −20 权）。
        </div>

        <div className="divider-label" style={{ marginTop: 14 }}>择师（监护人）</div>
        {child.guardian_candidates.map((g) => (
          <div
            key={g.id}
            className="save-slot"
            style={{
              cursor: 'pointer',
              borderColor: effectiveGuardian === g.id ? 'var(--gold-dim)' : 'var(--edge)',
              padding: '8px 12px',
            }}
            onClick={() => setGuardianId(g.id)}
          >
            <Sigil name={g.name} gender="male" did={undefined} size={28} />
            <span className="s-name" style={{ fontSize: 13 }}>
              {g.name}
              {g.suggested ? <span style={{ color: 'var(--gold)', fontSize: 11 }}> ◆推</span> : ''}
            </span>
            <span style={{ color: 'var(--ink-faint)', fontSize: 11.5 }}>学识 {g.learning}</span>
            <span style={{ color: 'var(--gold)', fontSize: 13 }}>
              {child.focus_options.find((o) => o.key === effectiveFocus)?.label ?? ''} {g.skill}
            </span>
          </div>
        ))}
        {child.guardian_candidates.length === 0 && (
          <div style={{ color: 'var(--ink-faint)', fontSize: 12.5 }}>族中无可为师者 —— 无监护人将显著降低成才率。</div>
        )}
      </div>
      <div className="modal-foot">
        <button className="btn" onClick={shelve}>{t('modal.shelve')}</button>
        <button className="btn primary" disabled={busy || !effectiveFocus} onClick={() => void confirm()}>
          落定教养
        </button>
      </div>
    </>
  )
}

/* ── 性情抉择 ── */
export function TraitPickBody({ shelve }: { shelve: () => void }) {
  const snap = useStore((s) => s.snap)
  const busy = useStore((s) => s.busy)
  const [selectedChild, setSelectedChild] = useState<number | null>(null)
  const [chosen, setChosen] = useState<string | null>(null)

  const queue = snap?.trait_queue ?? []
  const child = queue.find((e) => e.child_id === (selectedChild ?? queue[0]?.child_id)) ?? null

  if (!snap || !child) return null

  const confirm = async () => {
    if (!chosen) return
    const res = await runAction(() => api.traitPick(child.child_id, chosen), { silent: true })
    if (res.ok) {
      setChosen(null)
      setSelectedChild(null)
      const next = useStore.getState().snap
      if (!next || next.trait_queue.length === 0) shelve()
    }
  }

  return (
    <>
      <div className="modal-body">
        {queue.length > 1 && (
          <div className="chips" style={{ marginBottom: 14 }}>
            {queue.map((e) => (
              <button
                key={e.child_id}
                className={`chip ${e.child_id === child.child_id ? 'positive' : ''}`}
                style={{ cursor: 'pointer' }}
                onClick={() => {
                  setSelectedChild(e.child_id)
                  setChosen(null)
                }}
              >
                {e.name}
              </button>
            ))}
          </div>
        )}

        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 12 }}>
          <Sigil name={child.name} gender={child.gender} did={undefined} size={46} />
          <div>
            <div style={{ fontSize: 16, color: 'var(--gold-bright)' }}>
              {child.name}
              {child.relation ? <span style={{ color: 'var(--ink-dim)', fontSize: 12.5 }}> · {child.relation}</span> : null}
            </div>
            <div style={{ color: 'var(--ink-dim)', fontSize: 12.5 }}>
              {child.age} 岁
              {child.guardian_name
                ? <> · {t('traitpick.guardian_side')}：{child.guardian_name}</>
                : ` · ${t('traitpick.no_guardian')}`}
            </div>
          </div>
        </div>

        {child.existing.length > 0 && (
          <div style={{ marginBottom: 10 }}>
            <span className="divider-label" style={{ marginTop: 0, marginBottom: 4 }}>{t('traitpick.existing')}</span>
            <div className="chips">
              {child.existing.map((n) => (
                <span key={n} className="chip">{n}</span>
              ))}
            </div>
          </div>
        )}

        <div className="divider-label">择其天性</div>
        <div style={{ display: 'grid', gap: 8 }}>
          {child.options.map((o) => (
            <div
              key={o.id}
              className="save-slot"
              style={{
                cursor: 'pointer',
                borderColor: chosen === o.id ? 'var(--gold-dim)' : 'var(--edge)',
                padding: '9px 12px',
              }}
              onClick={() => setChosen(o.id)}
            >
              <Sigil name={o.name} gender={child.gender} did={undefined} size={28} />
              <span className="s-name" style={{ fontSize: 13.5 }}>{o.name}</span>
              <span
                style={{
                  color: o.kind === 'taught' ? 'var(--steel)' : 'var(--ink-faint)',
                  fontSize: 11.5,
                }}
              >
                {o.kind === 'taught' ? t('traitpick.guardian_side') : t('traitpick.stray')}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div className="modal-foot">
        <button className="btn" onClick={shelve}>{t('modal.shelve')}</button>
        <button className="btn primary" disabled={busy || !chosen} onClick={() => void confirm()}>
          {t('traitpick.confirm')}
        </button>
      </div>
    </>
  )
}
