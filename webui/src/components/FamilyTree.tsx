/* 全屏家族树：宗族域可切换（外嫁支只展示一代+盾徽跳转）、节点展开/合并、缩放平移、联动人物栏 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { t } from '../i18n'
import { useStore } from '../store'
import type { CharacterInfo } from '../types'

const NODE_W = 128
const NODE_H = 54
const SIB_GAP = 30
const COMP_GAP = 90
const GEN_H = 128

interface Unit {
  key: string
  person: CharacterInfo
  parents: string[]
  childUnits: string[]
  gen: number
  x: number
  extent: number
}

interface TreeNode {
  char: CharacterInfo
  x: number
  y: number
  w: number
  outDynasty: boolean
  collapsed: boolean
  hasChildren: boolean
}

interface TreeLayout {
  drawings: TreeNode[]
  nodes: Map<number, { cx: number; cy: number }>
  links: { d: string; kind: 'child' }[]
  genLabels: Map<number, string>
  bbox: { minX: number; minY: number; maxX: number; maxY: number }
  focusDynasty: number | null
}

export default function FamilyTree() {
  const snap = useStore((s) => s.snap)
  const selectedId = useStore((s) => s.selectedId)
  const select = useStore((s) => s.select)
  const setDrawerOpen = useStore((s) => s.setDrawerOpen)
  const setTreeOpen = useStore((s) => s.setTreeOpen)
  const treeOpen = useStore((s) => s.treeOpen)
  const [focusId, setFocusId] = useState<number | null>(null) // null=跟随家主
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set())
  const [scale, setScale] = useState(0.8)
  const [pan, setPan] = useState({ x: 80, y: 40 })
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null)
  const wrap = useRef<HTMLDivElement>(null)
  const camNeedsUpdate = useRef(true)

  const effectiveFocusId: number | null = focusId ?? snap?.player_id ?? null

  const layout = useMemo<TreeLayout | null>(() => {
    if (!snap || effectiveFocusId == null) return null
    return buildLayout(snap.characters, effectiveFocusId, collapsed)
  }, [snap, effectiveFocusId, collapsed])

  /* 镜头：打开家族树 / 切换聚焦人 / 回到家主 时，对准 effectiveFocusId 那个人 */
  useEffect(() => {
    if (!treeOpen || !layout || !snap) return
    if (!camNeedsUpdate.current) return
    camNeedsUpdate.current = false
    const fid = effectiveFocusId
    if (fid == null) return
    const me = layout.nodes.get(fid)
    const el = wrap.current
    if (!me || !el) return
    const s = 0.85
    setScale(s)
    setPan({ x: el.clientWidth / 2 - me.cx * s, y: el.clientHeight * 0.4 - me.cy * s })
  }, [treeOpen, layout, effectiveFocusId, snap])

  if (!treeOpen || !snap || !layout) return null

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const factor = e.deltaY < 0 ? 1.08 : 1 / 1.08
    setScale((s) => Math.max(0.25, Math.min(2.2, s * factor)))
  }

  const focusOn = (id: number) => {
    camNeedsUpdate.current = true
    setFocusId(id === snap.player_id ? null : id)
  }

  const fit = () => {
    const el = wrap.current
    if (!el) return
    const vw = el.clientWidth
    const vh = el.clientHeight
    const s = Math.min(1, Math.min(vw / (layout.bbox.maxX - layout.bbox.minX + 160), vh / (layout.bbox.maxY - layout.bbox.minY + 160)))
    setScale(Math.max(0.25, s))
    setPan({ x: 60, y: 40 })
  }

  const toggleCollapse = (id: number) => {
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const focusDyn = layout.focusDynasty
  const dynName = snap.dynasties.find((d) => d.id === focusDyn)?.name ?? t('tree.title')
  const gens = [...layout.genLabels.entries()].sort((a, b) => a[0] - b[0])

  return (
    <div className="tree-veil">
      <div className="panel-head" style={{ borderRadius: 0, border: 'none', borderBottom: '1px solid var(--edge)' }}>
        <span className="panel-title">{dynName} · {t('tree.title')}</span>
        <span className="panel-sub">{t('tree.hint')}</span>
        <div className="btn-group" style={{ marginLeft: 'auto' }}>
          <button className="btn ghost" onClick={fit}>{t('tree.overview')}</button>
          <button className="btn ghost" onClick={() => focusOn(snap.player_id)}>{t('tree.focus_head')}</button>
          <button className="btn ghost" onClick={() => setTreeOpen(false)}>{t('tree.close')}</button>
        </div>
      </div>
      <div
        ref={wrap}
        className={`tree-canvas ${drag.current ? 'dragging' : ''}`}
        onWheel={onWheel}
        onPointerDown={(e) => {
          drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y }
          ;(e.target as Element).setPointerCapture?.(e.pointerId)
        }}
        onPointerMove={(e) => {
          if (!drag.current) return
          setPan({ x: drag.current.px + (e.clientX - drag.current.x), y: drag.current.py + (e.clientY - drag.current.y) })
        }}
        onPointerUp={() => (drag.current = null)}
        onPointerLeave={() => (drag.current = null)}
      >
        <svg width="100%" height="100%">
          <g transform={`translate(${pan.x} ${pan.y}) scale(${scale})`}>
            {gens.map(([gen, label]) => (
              <text key={gen} x={layout.bbox.minX - 96} y={gen * GEN_H + 46} fill="var(--ink-faint)" fontSize="15" letterSpacing="4">
                {label}
              </text>
            ))}

            {layout.links.map((l, i) => (
              <path key={i} d={l.d} fill="none" stroke="rgba(138,116,74,0.4)" strokeWidth={1.4} />
            ))}

            {layout.drawings.map((n) => {
              const isSel = n.char.id === selectedId
              const isPlayer = n.char.id === snap.player_id
              const shownName = n.char.display_name ?? n.char.name
              return (
                <g
                  key={n.char.id}
                  transform={`translate(${n.x} ${n.y})`}
                  style={{ cursor: 'pointer' }}
                  onClick={(ev) => {
                    ev.stopPropagation()
                    select(n.char.id)
                    setDrawerOpen(true)
                  }}
                >
                  <rect
                    width={n.w}
                    height={NODE_H}
                    rx={9}
                    fill={n.char.alive ? 'var(--panel-2)' : '#1b1611'}
                    stroke={isPlayer ? 'var(--gold)' : isSel ? 'var(--gold-bright)' : n.char.alive ? 'var(--edge)' : '#332a1d'}
                    strokeWidth={isPlayer ? 2.4 : isSel ? 1.8 : 1.2}
                  />
                  {/* 外宗族成员：家族盾徽角标，点之跳转该家族 */}
                  {n.outDynasty && (
                    <g
                      transform={`translate(${n.w - 26} -12)`}
                      style={{ cursor: 'pointer' }}
                      onClick={(ev) => {
                        ev.stopPropagation()
                        focusOn(n.char.id)
                      }}
                    >
                      <CrestGate did={n.char.dynasty} />
                    </g>
                  )}
                  <g transform={`translate(6 ${(NODE_H - 30) / 2})`} pointerEvents="none">
                    <SigilSvg name={n.char.name} gender={n.char.gender} alive={n.char.alive} size={30} />
                  </g>
                  <text x={n.w - (n.outDynasty ? 30 : 8)} y={20} textAnchor="end" fontSize="13.5" fill={n.char.alive ? 'var(--ink)' : 'var(--ink-faint)'} style={{ textDecoration: n.char.alive ? 'none' : 'line-through' }}>
                    {truncate(shownName, 5)}
                  </text>
                  <text x={n.w - 10} y={40} textAnchor="end" fontSize="11.5" fill={n.char.alive ? 'var(--ink-dim)' : '#8a6a55'}>
                    {n.char.alive ? `${n.char.age} 岁` : `†${n.char.death_year} ${n.char.death_reason_label ?? ''}`}
                  </text>
                  {isPlayer && (
                    <text x={n.w / 2} y={NODE_H + 15} textAnchor="middle" fontSize="11" fill="var(--gold)" letterSpacing="3">
                      {t('tree.head_mark')}
                    </text>
                  )}
                  {/* 展开/合并开关（右下角，避免与家主标记重叠） */}
                  {n.hasChildren && (
                    <g
                      transform={`translate(${n.w - 26} ${NODE_H - 20})`}
                      style={{ cursor: 'pointer' }}
                      onClick={(ev) => {
                        ev.stopPropagation()
                        toggleCollapse(n.char.id)
                      }}
                    >
                      <rect width="22" height="16" rx="4" fill="#2a2216" stroke="var(--edge)" style={{ pointerEvents: 'auto' }} />
                      <text x="11" y="12.5" textAnchor="middle" fontSize="11" fill={n.collapsed ? 'var(--gold)' : 'var(--ink-dim)'}>
                        {n.collapsed ? '▸' : '▾'}
                      </text>
                    </g>
                  )}
                </g>
              )
            })}
          </g>
        </svg>
      </div>
    </div>
  )
}

/* ── SVG 内绘制的迷你徽记 ── */
function SigilSvg({ name, gender, alive, size }: { name: string; gender: 'male' | 'female'; alive: boolean; size: number }) {
  const ring = !alive ? '#4d4438' : gender === 'male' ? '#4d6a8c' : '#7d5a75'
  const initial = name.slice(0, 1)
  return (
    <g>
      <circle cx={size / 2} cy={size / 2} r={size / 2} fill={gender === 'male' ? '#2c3a4d' : '#4a3542'} stroke={ring} strokeWidth="2.5" />
      <text x={size / 2} y={size / 2 + 7} textAnchor="middle" fontSize={size * 0.58} fill={alive ? '#f2e8d0' : 'rgba(242,232,208,0.4)'}>
        {initial}
      </text>
      {!alive && <text x={size - 2} y={10} textAnchor="middle" fontSize="11">⚰</text>}
    </g>
  )
}

/* 跳转角标用的简化盾徽（纯 SVG，不适用 React 组件树） */
function CrestGate({ did }: { did: number | null }) {
  void did
  return (
    <g transform="scale(0.22) translate(-50, -58)">
      <rect width="100" height="116" rx="6" fill="var(--gold)" opacity="0.9" />
      <path
        d="M10 20 H90 V62 C90 86 72 100 50 106 C28 100 10 86 10 62 Z"
        fill="#2a2216"
        stroke="var(--gold-bright)"
        strokeWidth="4"
      />
    </g>
  )
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}

/* ── 布局：聚焦人物的宗族域（外宗族只展开一代）、世代分层、子女总线 ── */
function buildLayout(chars: CharacterInfo[], focusId: number, collapsed: Set<number>): TreeLayout {
  const byId = new Map(chars.map((c) => [c.id, c]))
  const me = byId.get(focusId)
  const focusDynasty = me?.dynasty ?? null

  const include = new Map<number, boolean>() // id -> 是否外宗族（聚焦宗族=false）
  const stack = [focusId]
  while (stack.length) {
    const x = stack.pop()!
    if (include.has(x)) continue
    const c = byId.get(x)
    if (!c) continue
    include.set(x, c.dynasty !== focusDynasty)
    for (const p of [c.father, c.mother]) {
      if (p != null && byId.has(p)) stack.push(p)
    }
  }

  const queue = [...include.keys()]
  while (queue.length) {
    const c = byId.get(queue.pop()!)
    if (!c) continue
    const parentOut = include.get(c.id) ?? false
    for (const cid of c.children) {
      const kid = byId.get(cid)
      if (!kid || include.has(cid)) continue
      // 外宗族者只展示其本人这一代（其子女不再展开）
      if (parentOut && kid.dynasty !== focusDynasty) continue
      include.set(cid, kid.dynasty !== focusDynasty)
      queue.push(cid)
    }
  }

  const unitOf = new Map<number, string>()
  const units = new Map<string, Unit>()
  for (const id of include.keys()) {
    const c = byId.get(id)!
    const key = `u${id}`
    units.set(key, { key, person: c, parents: [], childUnits: [], gen: 0, x: 0, extent: 0 })
    unitOf.set(id, key)
  }

  /* 血亲锚点：父系挂父、母系挂母，缺位回退另一方 */
  for (const u of units.values()) {
    const m = u.person
    const anchorId =
      m.patrilineal && m.father != null && include.has(m.father)
        ? m.father
        : !m.patrilineal && m.mother != null && include.has(m.mother)
          ? m.mother
          : m.father != null && include.has(m.father)
            ? m.father
            : m.mother != null && include.has(m.mother)
              ? m.mother
              : null
    if (anchorId != null) {
      const pu = unitOf.get(anchorId)
      if (pu && pu !== u.key) u.parents.push(pu)
    }
  }
  for (const u of units.values()) {
    for (const puKey of u.parents) {
      const pu = units.get(puKey)
      if (pu && !pu.childUnits.includes(u.key)) pu.childUnits.push(u.key)
    }
  }

  const personGen = new Map<number, number>()
  const genOf = (id: number): number => {
    if (personGen.has(id)) return personGen.get(id)!
    const c = byId.get(id)!
    if (c.father == null && c.mother == null) {
      personGen.set(id, 0)
      return 0
    }
    personGen.set(id, 0)
    const ps = [c.father, c.mother].filter((p): p is number => p != null && unitOf.has(p))
    const g = ps.length ? Math.max(...ps.map((p) => genOf(p) + 1)) : 0
    personGen.set(id, g)
    return g
  }
  for (const id of include.keys()) genOf(id)
  for (const u of units.values()) u.gen = personGen.get(u.person.id) ?? 0

  /* 节点合并：被合并者的整棵子树从布局剔除 */
  /* 节点合并：只剔除被折叠者的后代，本人保留（否则折叠家主会清空整棵树） */
  const excluded = new Set<string>()
  const markExcluded = (u: Unit) => {
    for (const k of u.childUnits) {
      const ku = units.get(k)
      if (!ku || excluded.has(ku.key)) continue
      excluded.add(ku.key)
      markExcluded(ku)
    }
  }
  for (const u of units.values()) if (collapsed.has(u.person.id)) markExcluded(u)

  const roots = [...units.values()]
    .filter((u) => u.parents.length === 0 && !excluded.has(u.key))
    .sort((a, b) => a.gen - b.gen)
  if (roots.length === 0 && units.size > 0) {
    const anyUnit = [...units.values()].find((u) => !excluded.has(u.key))
    if (anyUnit) roots.push(anyUnit)
  }

  let maxGen = 0
  const widthOf = (u: Unit): number => {
    const own = NODE_W
    if (u.childUnits.length === 0) {
      u.extent = own
      return own
    }
    const kids = u.childUnits.filter((k) => !excluded.has(k)).map((k) => units.get(k)!).sort((a, b) => a.person.birth_year - b.person.birth_year)
    let sum = 0
    for (const k of kids) sum += widthOf(k) + SIB_GAP
    u.extent = Math.max(own, sum - SIB_GAP)
    return u.extent
  }

  let cursorX = 0
  const placed = new Set<string>()
  for (const root of roots) {
    if (placed.has(root.key)) continue
    const extent = widthOf(root)
    place(root, cursorX)
    cursorX += extent + COMP_GAP
  }
  function place(u: Unit, x0: number) {
    if (placed.has(u.key)) return
    placed.add(u.key)
    u.x = x0 + u.extent / 2
    maxGen = Math.max(maxGen, u.gen)
    if (u.childUnits.length === 0) return
    const kids = u.childUnits.filter((k) => !excluded.has(k)).map((k) => units.get(k)!).sort((a, b) => a.person.birth_year - b.person.birth_year)
    const total = kids.reduce((s, k) => s + k.extent, 0) + SIB_GAP * (kids.length - 1)
    let cx = x0 + (u.extent - total) / 2
    for (const k of kids) {
      place(k, cx)
      cx += k.extent + SIB_GAP
    }
  }

  const drawings: TreeNode[] = []
  const nodePos = new Map<number, { x: number; y: number; w: number }>()
  const nodes = new Map<number, { cx: number; cy: number }>()
  for (const u of units.values()) {
    if (!placed.has(u.key)) continue
    const p = { x: u.x - NODE_W / 2, y: u.gen * GEN_H, w: NODE_W }
    nodePos.set(u.person.id, p)
    drawings.push({
      char: u.person,
      x: p.x,
      y: p.y,
      w: p.w,
      outDynasty: u.person.dynasty !== focusDynasty,
      collapsed: collapsed.has(u.person.id),
      hasChildren: u.childUnits.length > 0,
    })
    nodes.set(u.person.id, { cx: p.x + p.w / 2, cy: p.y + NODE_H / 2 })
  }

  const links: { d: string; kind: 'child' }[] = []
  for (const u of units.values()) {
    if (!placed.has(u.key) || excluded.has(u.key)) continue
    const visibleKids = u.childUnits.filter((k) => !excluded.has(k))
    if (!visibleKids.length) continue
    const my = nodePos.get(u.person.id)!
    const midX = my.x + NODE_W / 2
    const topY = my.y + NODE_H / 2
    const busY = u.gen * GEN_H + NODE_H + 34
    links.push({ d: `M${midX} ${topY} L${midX} ${busY}`, kind: 'child' })
    let busMinX = Infinity
    let busMaxX = -Infinity
    for (const ku of visibleKids) {
      const kuUnit = units.get(ku)!
      const cp = nodePos.get(kuUnit.person.id)!
      const cx = cp.x + NODE_W / 2
      const cy = cp.y - 8
      busMinX = Math.min(busMinX, cx)
      busMaxX = Math.max(busMaxX, cx)
      links.push({ d: `M${cx} ${busY} L${cx} ${cy}`, kind: 'child' })
    }
    links.push({ d: `M${busMinX} ${busY} L${busMaxX} ${busY}`, kind: 'child' })
  }

  const genLabels = new Map<number, string>()
  for (let g = 0; g <= maxGen; g++) genLabels.set(g, `${g + 1} ${t('tree.gen')}`)

  const xs = [...nodePos.values()].map((p) => p.x)
  return {
    drawings,
    nodes,
    links,
    genLabels,
    bbox: {
      minX: Math.min(...xs, 0) - NODE_W,
      minY: 0,
      maxX: Math.max(...[...nodePos.values()].map((p) => p.x + p.w), 400) + NODE_W,
      maxY: (maxGen + 1) * GEN_H + 60,
    },
    focusDynasty,
  }
}
