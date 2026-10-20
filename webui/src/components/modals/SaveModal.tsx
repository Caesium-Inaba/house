/* 档案室：多存档槽的保存 / 读取 / 删除 */

import { useEffect, useState } from 'react'
import { useStore, runAction } from '../../store'
import { api } from '../../api/client'
import type { SaveInfo } from '../../types'
import { t } from '../../i18n'

function fmtTime(mtime: number): string {
  const d = new Date(mtime * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

export default function SaveModal() {
  const snap = useStore((s) => s.snap)
  const modal = useStore((s) => s.modal)
  const closeModal = useStore((s) => s.closeModal)
  const busy = useStore((s) => s.busy)
  const [saves, setSaves] = useState<SaveInfo[]>([])
  const [name, setName] = useState('')
  const [overwrite, setOverwrite] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  useEffect(() => {
    if (modal !== 'saves') return
    void api.saves().then((r) => setSaves((r.saves as SaveInfo[]) ?? []))
  }, [modal])

  useEffect(() => {
    if (modal === 'saves' && snap) {
      const dyn = snap.dynasties.find((d) => d.id === snap.characters.find((c) => c.id === snap.player_id)?.dynasty)
      setName(`${dyn?.name ?? ''}${snap.date.year}年`)
      setOverwrite(null)
      setConfirmDelete(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modal])

  if (modal !== 'saves' || !snap) return null

  /* 存档与当前版本/模组的差异 → 红感叹号 + 悬浮说明 */
  function warnings(sv: SaveInfo): string | null {
    const issues: string[] = []
    if ((sv.version ?? 0) < snap!.meta.save_version) {
      issues.push(t('saves.old_format'))
    }
    if ((sv.game_version || '') !== snap!.meta.game_version) {
      issues.push(t('saves.version_diff', { saved: sv.game_version || '?', current: snap!.meta.game_version }))
    }
    const savedMods = sv.mods?.enabled ?? []
    const curMods = snap!.meta.active_mods?.enabled ?? []
    const missing = curMods.filter((f) => !savedMods.includes(f))
    const extra = savedMods.filter((f) => !curMods.includes(f))
    const versions = savedMods.filter(
      (f) => (sv.mods?.versions ?? {})[f] !== (snap!.meta.active_mods?.versions ?? {})[f],
    )
    if (missing.length || extra.length || versions.length) {
      issues.push(
        t('saves.mods_diff', {
          missing: missing.join(', ') || t('saves.none_label'),
          extra: extra.join(', ') || t('saves.none_label'),
          versions: versions.join(', ') || t('saves.none_label'),
        }),
      )
    }
    return issues.length ? issues.join('\n') : null
  }

  const doSave = async (force = false) => {
    const res = await runAction(() => api.save(name, force), { silent: true })
    if (res.saves) setSaves(res.saves)
    if (res.exists) setOverwrite(name)
    else if (res.ok) {
      setOverwrite(null)
      useStore.getState().toast(res.message ?? t('saves.save'), 'good')
    }
  }

  const doLoad = async (s: SaveInfo) => {
    const res = await runAction(() => api.load(s.name), { silent: true })
    if (res.ok) {
      useStore.getState().toast(res.message ?? t('saves.load'), 'good')
      closeModal()
    }
  }

  const doDelete = async (s: SaveInfo) => {
    const res = await runAction(() => api.delSave(s.name), { silent: true })
    if (res.saves) setSaves(res.saves)
    setConfirmDelete(null)
  }

  const fresh = name.trim() && !saves.some((s) => s.name === name.trim())

  return (
    <div className="veil" onClick={closeModal}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span className="modal-title">{t('modal.saves')}</span>
          <span className="panel-sub">{t('saves.current', { date: snap.date.label })}</span>
          <button className="btn ghost modal-x" onClick={closeModal}>✕</button>
        </div>
        <div className="modal-body">
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input
              type="text"
              value={name}
              maxLength={24}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && void doSave(false)}
              style={{ flex: 1 }}
              placeholder={t('saves.placeholder')}
            />
            {overwrite ? (
              <button className="btn danger" disabled={busy} onClick={() => void doSave(true)}>
                {t('saves.overwrite_named', { name: overwrite })}
              </button>
            ) : (
              <button className="btn primary" disabled={busy || !name.trim()} onClick={() => void doSave(false)}>
                {fresh ? t('saves.save') : t('saves.overwrite')}
              </button>
            )}
          </div>

          {saves.length === 0 && <div className="empty">{t('saves.none')}</div>}
          {saves.map((s) => (
            <div key={s.name} className="save-slot">
              <span
                className={`s-warn ${warnings(s) ? 'on' : ''}`}
                title={warnings(s) ?? ''}
                style={{ display: warnings(s) ? 'inline' : 'none' }}
              >
                ❗
              </span>
              <span className="s-name">{s.name}</span>
              <span className="s-meta">
                {t('saves.date', { y: s.year, m: s.month, d: s.day ?? 1 })} · {fmtTime(s.mtime)}
              </span>
              {confirmDelete === s.name ? (
                <>
                  <button className="btn danger" onClick={() => void doDelete(s)}>{t('saves.confirm_delete')}</button>
                  <button className="btn ghost" onClick={() => setConfirmDelete(null)}>{t('saves.cancel')}</button>
                </>
              ) : (
                <>
                  <button className="btn" disabled={busy} onClick={() => void doLoad(s)}>{t('saves.load')}</button>
                  <button className="btn ghost" title={t('saves.delete_title')} onClick={() => setConfirmDelete(s.name)}>{t('saves.delete')}</button>
                </>
              )}
            </div>
          ))}
        </div>
        <div className="modal-foot">
          <button className="btn ghost" style={{ marginRight: 'auto' }} onClick={() => useStore.getState().openModal('new')}>
            {t('saves.new_game')}
          </button>
          <button className="btn" onClick={closeModal}>{t('modal.back')}</button>
        </div>
      </div>
    </div>
  )
}
