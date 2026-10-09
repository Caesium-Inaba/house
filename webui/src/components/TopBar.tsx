/* 顶栏：王朝徽识 | 日期铭牌 | 时间控制 */

import { useState } from 'react'
import { useStore } from '../store'
import { tickTime } from '../store'
import { api } from '../api/client'
import { runAction } from '../store'
import { Crest } from '../heraldry'
import { t } from '../i18n'
import { IconAuto, IconPause, IconTree } from '../icons'

const SPEED_MARKS = ['Ⅰ', 'Ⅱ', 'Ⅲ', 'Ⅳ', 'Ⅴ']

export default function TopBar() {
  const snap = useStore((s) => s.snap)
  const busy = useStore((s) => s.busy)
  const auto = useStore((s) => s.auto)
  const setAuto = useStore((s) => s.setAuto)
  const speed = useStore((s) => s.speed)
  const setSpeed = useStore((s) => s.setSpeed)
  const openModal = useStore((s) => s.openModal)
  const setTreeOpen = useStore((s) => s.setTreeOpen)
  const treeOpen = useStore((s) => s.treeOpen)
  const [showPlaytime, setShowPlaytime] = useState(false)

  if (!snap) return <header className="topbar" />

  const player = snap.characters.find((c) => c.id === snap.player_id)
  const playerDyn = snap.dynasties.find((d) => d.id === player?.dynasty)
  const canTick = !snap.over
  const stats = snap.stats

  return (
    <header className="topbar">
      <div className="brand">
        <Crest did={player?.dynasty ?? null} female={player?.gender === 'female'} size={34} />
        <div>
          <div className="brand-name">{playerDyn?.name ?? '—'}</div>
          <div className="brand-meta">
            家主 <b>{player?.display_name ?? player?.name ?? '—'}</b>
            {player?.relation && player.relation !== '自己' ? '' : ''}
            {' · '}宗族威望 <b>{Math.round(playerDyn?.renown ?? 0)}</b>
            {snap.over ? ' · 大厦已倾' : ''}
          </div>
        </div>
      </div>

      <div
        className="date-cartouche"
        style={{ cursor: 'pointer' }}
        title="点击查看已游玩统计"
        onClick={() => setShowPlaytime((v) => !v)}
      >
        <span className="orn">◆</span>
        {showPlaytime ? (
          <span className="d-sub">
            已游玩 <b className="d-year">{stats.years_played}</b> 年 · {stats.generations} 代 ·{' '}
            {snap.population.alive} 人在世
          </span>
        ) : (
          <>
            <span className="d-year">{snap.date.year}年</span>
            <span className="d-sub">
              {snap.date.month}月 {snap.meta.xun_names[snap.date.xun]}
            </span>
          </>
        )}
        <span className="orn">◆</span>
      </div>

      <div className="btn-group">
        <button
          className={`btn toggle ${auto ? 'on' : ''}`}
          onClick={() => setAuto(!auto)}
          disabled={snap.over}
          title="自动推进 · 空格 = 暂停 / 开始（事件弹出后时间照常流动）"
        >
          {auto ? <IconPause /> : <IconAuto />}
          {auto ? '停' : '自动'}
          <kbd>空格</kbd>
        </button>
        {/* 流速五档 */}
        <div className="speed-group" title={t('top.speed_hint')}>
          {SPEED_MARKS.map((m, i) => (
            <button
              key={m}
              className={`sbtn ${speed === i + 1 ? 'on' : ''}`}
              onClick={() => setSpeed(i + 1)}
            >
              {m}
            </button>
          ))}
        </div>
        <button className="btn primary" disabled={!canTick || busy} onClick={() => tickTime('xun')}>
          推一旬
        </button>
        <button className="btn primary" disabled={!canTick || busy} onClick={() => tickTime('year')}>
          推一年 <kbd>Y</kbd>
        </button>
        <button
          className="btn"
          onClick={() => setTreeOpen(!treeOpen)}
          title="家族树（全屏可缩放）"
        >
          <IconTree /> 家族树 <kbd>T</kbd>
        </button>
        <button className="btn" onClick={() => openModal('marriage')} disabled={!canTick}>
          婚配 <kbd>M</kbd>
        </button>
        <button className="btn" onClick={() => openModal('saves')}>
          存读档 <kbd>S</kbd>
        </button>
      </div>
    </header>
  )
}

export async function ensureLoaded() {
  await runAction(() => api.state(), { silent: true })
}
