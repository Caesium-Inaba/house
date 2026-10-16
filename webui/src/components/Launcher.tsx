/* 启动器（CK3 式）：左侧栏 + 模组页签；按启用清单开局后进入游戏视图。
 *
 * 与游戏视图（App.tsx)同源不同路由：#/launcher 开局，#/ 启动游戏。
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { launcherApi } from '../api/client'
import type { LauncherInfo, LauncherModInfo } from '../types'
import { stabiliseSnapshot, useStore } from '../store'
import { t } from '../i18n'

export default function Launcher() {
  const nav = useNavigate()
  const [info, setInfo] = useState<LauncherInfo | null>(null)
  const [enabled, setEnabled] = useState<string[]>([])
  const [busy, setBusy] = useState(false)
  const [confirmDiscard, setConfirmDiscard] = useState(false)

  useEffect(() => {
    void (async () => {
      const res = await launcherApi.state()
      setInfo(res)
      setEnabled(res.enabled)
    })()
  }, [])

  if (!info) {
    return <div className="launcher"><aside className="l-rail" /><main className="l-main" /></div>
  }

  const toggle = (folder: string) =>
    setEnabled((cur) => (cur.includes(folder) ? cur.filter((f) => f !== folder) : [...cur, folder]))

  const move = (folder: string, dir: -1 | 1) =>
    setEnabled((cur) => {
      const i = cur.indexOf(folder)
      const j = i + dir
      if (i < 0 || j < 0 || j >= cur.length) return cur
      const next = [...cur]
      next[i] = next[j]
      next[j] = folder
      return next
    })

  const play = async () => {
    if (busy) return
    if (info.started && !confirmDiscard) {
      setConfirmDiscard(true)
      return
    }
    setBusy(true)
    try {
      const res = await launcherApi.start(enabled, null)
      if (res.ok && res.state) {
        const snap = stabiliseSnapshot(res.state)
        useStore.setState({ snap, selectedId: snap.player_id, modal: null, eventWins: [] })
        nav('/')
      }
    } finally {
      setBusy(false)
      setConfirmDiscard(false)
    }
  }

  const orderOf = (folder: string) => enabled.indexOf(folder)
  const sorted = [...info.mods].sort((a, b) => {
    const ao = orderOf(a.folder), bo = orderOf(b.folder)
    if (ao >= 0 && bo >= 0) return ao - bo   // 已启用按载入顺序置顶
    if (ao >= 0) return 0
    if (bo >= 0) return 1
    return a.folder.localeCompare(b.folder)
  })

  return (
    <div className="launcher">
      <aside className="l-rail">
        <div className="l-brand">
          <div className="l-mark">House</div>
          <div className="l-sub">{t('launcher.subtitle')}</div>
        </div>
        <button className="btn primary l-play" disabled={busy} onClick={() => void play()}>
          {t('launcher.play')}
        </button>
        {confirmDiscard && (
          <div className="l-confirm">
            <div>{t('launcher.discard_warn')}</div>
            <div className="l-confirm-row">
              <button className="btn" onClick={() => setConfirmDiscard(false)}>{t('launcher.cancel')}</button>
              <button className="btn primary" disabled={busy} onClick={() => void play()}>{t('launcher.discard_confirm')}</button>
            </div>
          </div>
        )}
        <div className="l-hint">{t('launcher.play_hint')}</div>
      </aside>
      <main className="l-main">
        <header className="l-head">
          <span className="panel-title">{t('launcher.mods_tab')}</span>
          <span className="l-order-hint">{t('launcher.order_hint')}</span>
        </header>
        {sorted.length === 0 && <div className="l-empty">{t('launcher.no_mods')}</div>}
        <div className="l-list">
          {sorted.map((m) => (
            <ModCard
              key={m.folder}
              m={m}
              on={enabled.includes(m.folder)}
              order={orderOf(m.folder)}
              maxOrder={enabled.length - 1}
              onToggle={toggle}
              onMove={move}
            />
          ))}
        </div>
      </main>
    </div>
  )
}

function ModCard({ m, on, order, maxOrder, onToggle, onMove }: {
  m: LauncherModInfo
  on: boolean
  order: number
  maxOrder: number
  onToggle: (folder: string) => void
  onMove: (folder: string, dir: -1 | 1) => void
}) {
  return (
    <div className={`l-mod ${on ? 'on' : ''} ${m.valid ? '' : 'bad'}`}>
      <div className="l-mod-check">
        <button className={`l-check ${on ? 'on' : ''}`} title={t('launcher.toggle')} onClick={() => onToggle(m.folder)}>
          {on ? '✓' : ''}
        </button>
      </div>
      <div className="l-mod-info">
        <div className="l-mod-name">
          {m.name}
          {on && order >= 0 && <span className="l-mod-order"> · {t('launcher.load_n', { n: order + 1 })}</span>}
        </div>
        <div className="l-mod-sub">
          {m.version ? `v${m.version}` : ''}
          {m.tags.length > 0 ? ` · ${m.tags.join(' · ')}` : ''}
        </div>
        {!m.valid && <div className="l-mod-error">{m.error || t('launcher.invalid')}</div>}
      </div>
      {on && (
        <div className="l-mod-order-ctl">
          <button className="l-arr" disabled={order <= 0} onClick={() => onMove(m.folder, -1)}>▲</button>
          <button className="l-arr" disabled={order >= maxOrder} onClick={() => onMove(m.folder, 1)}>▼</button>
        </div>
      )}
    </div>
  )
}
