/* 中栏：结构化编年史 —— 日期分组 / 类型筛选 / 人名可点 */

import { useMemo, useState, type JSX } from 'react'
import { useStore } from '../store'
import type { EventInfo } from '../types'
import { EVENT_COLORS, EVENT_ICONS, EVENT_LABELS, IconScroll, IconCradle } from '../icons'

const FILTER_ORDER = ['pregnancy', 'birth', 'marriage', 'adulthood', 'death', 'succession', 'extinction', 'chronicle'] as const

function dayLabel(e: EventInfo): string {
  if (e.year == null) return '先前的岁月'
  const xun = e.xun != null ? ` ${['上旬', '中旬', '下旬'][e.xun]}` : ''
  return `${e.year}年${e.month != null ? ` ${e.month}月` : ''}${xun}`
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
    return events.filter((e) => {
      if (filter !== 'all' && e.type !== filter) return false
      if (query && !e.text.includes(query)) return false
      return true
    })
  }, [snap?.events, filter, query])

  if (!snap) return <section className="panel" />

  /* 文本渲染：actor 名字可点 */
  function renderText(e: EventInfo) {
    let nodes: (string | JSX.Element)[] = [e.text]
    for (const aid of e.actors) {
      const ch = byId.get(aid)
      if (!ch) continue
      nodes = nodes.flatMap((node) => {
        if (typeof node !== 'string' || !node.includes(ch.name)) return [node]
        const parts = node.split(ch.name)
        const out: (string | JSX.Element)[] = []
        parts.forEach((p, i) => {
          if (i > 0)
            out.push(
              <span
                key={`${aid}-${i}`}
                className="who"
                onClick={(ev) => {
                  ev.stopPropagation()
                  select(aid)
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

  let lastDay = ''

  return (
    <section className="panel">
      <div className="panel-head">
        <span className="panel-title">编年史</span>
        <span className="panel-sub">{snap.events.length} 条记事</span>
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
            待命名 · {snap.naming_queue[0].suggested}（{snap.naming_queue[0].relation}）
            {snap.naming_queue.length > 1 ? ` · 另有 ${snap.naming_queue.length - 1} 位` : ''}
            {' —— 点击举行命名礼'}
          </div>
        </div>
      )}

      <div className="filter-row">
        <button className={`fchip ${filter === 'all' ? 'on' : ''}`} onClick={() => setFilter('all')}>
          全部 <span className="n">{snap.events.length}</span>
        </button>
        {FILTER_ORDER.filter((t) => counts[t]).map((t) => {
          const Icon = EVENT_ICONS[t] ?? IconScroll
          return (
            <button key={t} className={`fchip ${filter === t ? 'on' : ''}`} onClick={() => setFilter(filter === t ? 'all' : t)}>
              <Icon /> {EVENT_LABELS[t]} <span className="n">{counts[t]}</span>
            </button>
          )
        })}
        <input
          type="search"
          placeholder="搜记事…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ marginLeft: 'auto', width: 140, fontSize: 12.5, padding: '4px 10px' }}
        />
      </div>

      <div className="panel-body">
        {shown.length === 0 && <div className="empty">尚无大事发生</div>}
        <div className="chronicle">
          {shown.map((e, i) => {
            const day = dayLabel(e)
            const showDay = day !== lastDay
            lastDay = day
            const Icon = EVENT_ICONS[e.type] ?? IconScroll
            const color = EVENT_COLORS[e.type] ?? 'var(--ink-faint)'
            return (
              <div key={`${e.year}-${e.month}-${e.xun}-${snap.events.length - i}-${e.type}`}>
                {showDay && <div className="day-divider">{day}</div>}
                <div className={`event type-${e.type}`}>
                  <div className="icon" style={{ color }}>
                    <Icon />
                  </div>
                  <div className="text">{renderText(e)}</div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
