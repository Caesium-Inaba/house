/* 中栏：结构化编年史 —— 日期分组 / 类型筛选 / 人名可点 */

import { useMemo, useState, memo, type JSX } from 'react'
import { useStore } from '../store'
import type { CharacterInfo, EventInfo } from '../types'
import { t } from '../i18n'
import { EVENT_COLORS, EVENT_ICONS, IconScroll, IconCradle, IconBrush, IconSprout } from '../icons'

const FILTER_ORDER = ['pregnancy', 'birth', 'marriage', 'betrothal', 'trait', 'adulthood', 'tutoring', 'death', 'succession', 'legacy', 'extinction', 'chronicle'] as const

/* 事件行：props 引用全等时跳过渲染（store 已做引用稳定化） */
const EventRow = memo(
  function EventRow({ e, actors, head }: { e: EventInfo; actors: (CharacterInfo | null)[]; head: boolean }) {
    const Icon = EVENT_ICONS[e.type] ?? IconScroll
    const color = EVENT_COLORS[e.type] ?? 'var(--ink-faint)'
    return (
      <div>
        {head && <div className="day-divider">{dayLabel(e)}</div>}
        <div className={`event type-${e.type}`}>
          <div className="icon" style={{ color }}>
            <Icon />
          </div>
          <div className="text">{renderActors(e, actors)}</div>
        </div>
      </div>
    )
  },
  (a, b) => a.e === b.e && a.head === b.head && a.actors.every((x, i) => x === b.actors[i]),
)

function dayLabel(e: EventInfo): string {
  if (e.year == null) return t('day.before')
  return t('chronicle.date', { y: e.year, m: e.month ?? 1, d: e.day ?? 1 })
}

/* 事件分日渲染：actor 名字可点。人物引用由父层预取（引用稳定化后可跳过） */
function renderActors(e: EventInfo, actors: (CharacterInfo | null)[]): (string | JSX.Element)[] {
  let nodes: (string | JSX.Element)[] = [e.text]
  for (const ch of actors) {
    if (!ch) continue
    nodes = nodes.flatMap((node) => {
      if (typeof node !== 'string' || !node.includes(ch.name)) return [node]
      const parts = node.split(ch.name)
      const out: (string | JSX.Element)[] = []
      parts.forEach((p, i) => {
        if (i > 0)
          out.push(
            <span
              key={`${ch.id}-${i}`}
              className="who"
              onClick={(ev) => {
                ev.stopPropagation()
                useStore.getState().select(ch.id)
                useStore.getState().setDrawerOpen(true)
              }}
            >
              {ch.name}
            </span>,
          )
        out.push(p)
      })
      return out
    })
  }
  return nodes
}

export default function Chronicle() {
  const snap = useStore((s) => s.snap)
  const select = useStore((s) => s.select)
  const openModal = useStore((s) => s.openModal)
  const [filter, setFilter] = useState<string>('all')
  const [query, setQuery] = useState('')

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const e of snap?.events ?? []) c[e.type] = (c[e.type] ?? 0) + 1
    return c
  }, [snap?.events])

  const byId = useMemo(() => new Map((snap?.characters ?? []).map((c) => [c.id, c])), [snap?.characters])

  const shown = useMemo(() => {
    const events = [...(snap?.events ?? [])].reverse()
    const filtered = events.filter((e) => {
      if (filter !== 'all' && e.type !== filter) return false
      if (query && !e.text.includes(query)) return true
      if (query) return false
      return true
    })
    // 日期分组标记：与上一条同日则不重复显示分隔
    const out: { e: EventInfo; head: boolean }[] = []
    let lastDay = ''
    for (const e of filtered) {
      const day = dayLabel(e)
      out.push({ e, head: day !== lastDay })
      lastDay = day
    }
    return out
  }, [snap?.events, filter, query])

  if (!snap) return <section className="panel" />

  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title">{t('panel.chronicle')}</span>
        <span className="panel-sub">{snap.events.length} {t('panel.events_count')}</span>
      </div>

      {snap.naming_queue.length > 0 && (
        <div
          className="event pending"
          style={{ margin: '10px 16px 0', width: 'calc(100% - 32px)' }}
          onClick={() => openModal('naming')}
        >
          <div className="icon" style={{ color: 'var(--gold)' }}>
            <IconCradle />
          </div>
          <div className="text" style={{ color: 'var(--gold-bright)' }}>
            {t('todo.naming_prefix')} · <span className="who" onClick={(ev) => { ev.stopPropagation(); select(snap.naming_queue[0].child_id); useStore.getState().setDrawerOpen(true) }}>{snap.naming_queue[0].suggested}</span>（{snap.naming_queue[0].relation}）
            {snap.naming_queue.length > 1 ? t('todo.naming_more', { n: snap.naming_queue.length - 1 }) : ''}
            {t('chronicle.click_naming')}
          </div>
        </div>
      )}

      {snap.tutoring_queue.length > 0 && (
        <div
          className="event pending"
          style={{ margin: '8px 16px 0', width: 'calc(100% - 32px)' }}
          onClick={() => openModal('tutoring')}
        >
          <div className="icon" style={{ color: '#d0b46a' }}>
            <IconBrush />
          </div>
          <div className="text" style={{ color: '#e0d3a0' }}>
            {t('todo.tutoring_prefix')} ·{' '}
            <span
              className="who"
              onClick={(ev) => {
                ev.stopPropagation()
                select(snap.tutoring_queue[0].child_id)
                useStore.getState().setDrawerOpen(true)
              }}
            >
              {snap.tutoring_queue[0].name}
            </span>
            （{snap.tutoring_queue[0].relation ?? ''}）
            {snap.tutoring_queue.length > 1 ? t('todo.naming_more', { n: snap.tutoring_queue.length - 1 }) : ''}
            {t('chronicle.click_tutoring')}
          </div>
        </div>
      )}

      {snap.trait_queue.length > 0 && (
        <div
          className="event pending"
          style={{ margin: '8px 16px 0', width: 'calc(100% - 32px)' }}
          onClick={() => openModal('traitpick')}
        >
          <div className="icon" style={{ color: 'var(--verdant)' }}>
            <IconSprout />
          </div>
          <div className="text" style={{ color: '#c9d8a8' }}>
            {t('todo.traitpick_prefix')} ·{' '}
            <span
              className="who"
              onClick={(ev) => {
                ev.stopPropagation()
                select(snap.trait_queue[0].child_id)
                useStore.getState().setDrawerOpen(true)
              }}
            >
              {snap.trait_queue[0].name}
            </span>
            （{snap.trait_queue[0].relation ?? ''}）
            {snap.trait_queue.length > 1 ? t('todo.naming_more', { n: snap.trait_queue.length - 1 }) : ''}
            {t('chronicle.click_traitpick')}
          </div>
        </div>
      )}

      <div className="filter-row">
        <button className={`fchip ${filter === 'all' ? 'on' : ''}`} onClick={() => setFilter('all')}>
          {t('chronicle.all')} <span className="n">{snap.events.length}</span>
        </button>
        {FILTER_ORDER.filter((etype) => counts[etype]).map((etype) => {
          const Icon = EVENT_ICONS[etype] ?? IconScroll
          return (
            <button
              key={etype}
              className={`fchip ${filter === etype ? 'on' : ''}`}
              onClick={() => setFilter(filter === etype ? 'all' : etype)}
            >
              <Icon /> {t(`event_label.${etype}`)} <span className="n">{counts[etype]}</span>
            </button>
          )
        })}
        <input
          type="search"
          placeholder={t('panel.search')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ marginLeft: 'auto', width: 140, fontSize: 12.5, padding: '4px 10px' }}
        />
      </div>

      <div className="panel-body">
        {shown.length === 0 && <div className="empty">{t('chronicle.empty')}</div>}
        <div className="chronicle">
          {shown.map(({ e, head }) => (
            <EventRow
              key={`${e.year ?? 'x'}-${e.month ?? 'x'}-${e.day ?? 'x'}-${e.type}-${e.text}`}
              e={e}
              actors={e.actors.map((id) => byId.get(id) ?? null)}
              head={head}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
