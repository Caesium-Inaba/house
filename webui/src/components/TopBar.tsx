/* 顶栏：王朝徽识 | 日期铭牌 | 时间控制 */

import { useState } from 'react'
import { useStore } from '../store'
import { tickTime } from '../store'
import { api } from '../api/client'
import { runAction } from '../store'
import { Crest } from '../heraldry'
import { t } from '../i18n'
import { SHOW_MANUAL_TICK } from '../featureFlags'
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
  const lang = useStore((s) => s.lang)
  const setLang = useStore((s) => s.setLang)
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
            {t('top.head')} <b>{player?.display_name ?? player?.name ?? '—'}</b>
            {' · '}{t('top.renown')} <b>{Math.round(playerDyn?.renown ?? 0)}</b>
            {snap.over ? t('top.house_fallen') : ''}
          </div>
        </div>
      </div>

      <div
        className="date-cartouche"
        style={{ cursor: 'pointer' }}
        title={t('top.playtime_hint')}
        onClick={() => setShowPlaytime((v) => !v)}
      >
        <span className="orn">◆</span>
        {showPlaytime ? (
          <span className="d-sub">
            {t('top.playtime')} <b className="d-year">{stats.years_played}</b> {t('top.years')} ·{' '}
            {stats.generations} {t('top.gen')} · {snap.population.alive} {t('top.alive')}
          </span>
        ) : (
          <span className="d-year">{snap.date.label}</span>
        )}
        <span className="orn">◆</span>
      </div>

      <div className="btn-group">
        <button
          className={`btn toggle ${auto ? 'on' : ''}`}
          onClick={() => setAuto(!auto)}
          disabled={snap.over}
          title={t('top.auto_hint')}
        >
          {auto ? <IconPause /> : <IconAuto />}
          {auto ? t('top.pause') : t('top.start')}
          <kbd>{t('top.space')}</kbd>
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
        {/* 手动推进（推一日/推一月/推一年）已从 UI 移除，只保留开始/暂停；
            实现与 i18n 键仍保留，SHOW_MANUAL_TICK 置 true 可恢复入口。 */}
        {SHOW_MANUAL_TICK && (
          <>
            <button className="btn primary" disabled={!canTick || busy} onClick={() => tickTime('day')}>
              {t('top.tick_day')}
            </button>
            <button className="btn" disabled={!canTick || busy} onClick={() => tickTime('month')}>
              {t('top.tick_month')}
            </button>
            <button className="btn primary" disabled={!canTick || busy} onClick={() => tickTime('year')}>
              {t('top.tick_year')} <kbd>Y</kbd>
            </button>
          </>
        )}
        <button
          className="btn"
          onClick={() => setTreeOpen(!treeOpen)}
          title={t('top.tree_hint')}
        >
          {<IconTree />} {t('top.tree')} <kbd>T</kbd>
        </button>
        <button className="btn" onClick={() => openModal('marriage')} disabled={!canTick}>
          {t('top.marriage')} <kbd>M</kbd>
        </button>
        <button className="btn" onClick={() => openModal('decisions')}>
          {t('top.decisions')}
        </button>
        <button className="btn" onClick={() => openModal('saves')}>
          {t('top.saves')} <kbd>S</kbd>
        </button>
        <button
          className="btn"
          title={t('top.lang_switch')}
          onClick={() => {
            const next = lang === 'zh' ? 'en' : 'zh'
            void api.settings(next).then((res) => {
              useStore.getState().apply(res)
              setLang(next)
            })
          }}
        >
          {lang === 'zh' ? 'EN' : '中文'}
        </button>
      </div>
    </header>
  )
}

export async function ensureLoaded() {
  await runAction(() => api.state(), { silent: true })
}
