/* 全屏家族树：世代分层 + 婚姻连线 + 缩放平移 + 选中联动 */

import { useEffect, useMemo, useRef, useState } from 'react'
import { t } from '../i18n'
import { useStore } from '../store'
import type { CharacterInfo } from '../types'

const NODE_W = 128
const NODE_H = 54
const COUPLE_GAP = 16
const SIB_GAP = 30
const COMP_GAP = 90
const GEN_H = 128

interface Unit {
  key: string
  members: CharacterInfo[] // 1 或 2 人（夫妻）
  parents: string[] // 父母所在 unit 的 key
  childUnits: string[]
  gen: number
  x: number // 中心 x（px）
  extent: number // 宽度（px，含子女摊开）
}

interface TreeNode {
  char: CharacterInfo
  x: number
  y: number
  w: number
}

export default function FamilyTree() {
  const snap = useStore((s) => s.snap)
  const selectedId = useStore((s) => s.selectedId)
  const select = useStore((s) => s.select)
  const setTreeOpen = useStore((s) => s.setTreeOpen)
  const treeOpen = useStore((s) => s.treeOpen)
  const [scale, setScale] = useState(0.9)
  const [pan, setPan] = useState({ x: 80, y: 40 })
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null)
  const wrap = useRef<HTMLDivElement>(null)

  const layout = useMemo(() => {
    if (!snap) return null
    return buildLayout(snap.characters, snap.player_id)
  }, [snap])

  const bbox = useMemo(() => {
    if (!layout) return { minX: 0, minY: 0, maxX: 1000, maxY: 600 }
    return layout.bbox
  }, [layout])

  /* 打开时聚焦玩家：以可读缩放居中家主（全览用「全览」按钮） */
  useEffect(() => {
    if (!treeOpen || !layout || !snap) return
    const me = layout.nodes.get(snap.player_id)
    const el = wrap.current
    if (!me || !el) return
    const vw = el.clientWidth
    const vh = el.clientHeight
    const s = 0.8
    setScale(s)
    setPan({ x: vw / 2 - me.cx * s, y: vh / 2 - me.cy * s })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [treeOpen])

  if (!treeOpen || !snap || !layout) return null

  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const factor = e.deltaY < 0 ? 1.08 : 1 / 1.08
    setScale((s) => Math.max(0.25, Math.min(2.2, s * factor)))
  }

  const fit = () => {
    const el = wrap.current
    if (!el) return
    const vw = el.clientWidth
    const vh = el.clientHeight
    const s = Math.min(1, Math.min(vw / (bbox.maxX - bbox.minX + 160), vh / (bbox.maxY - bbox.minY + 160)))
    setScale(Math.max(0.25, s))
    setPan({ x: 60, y: 40 })
  }

  const focusMe = () => {
    const me = layout.nodes.get(snap.player_id)
    const el = wrap.current
    if (!me || !el) return
    setPan({ x: el.clientWidth / 2 - me.cx * scale, y: Math.min(90, el.clientHeight / 4) })
    setScale(1)
  }

  const gens = [...layout.genLabels.entries()].sort((a, b) => a[0] - b[0])

  return (
    <div className="tree-veil">
      <div className="panel-head" style={{ borderRadius: 0, border: 'none', borderBottom: '1px solid var(--edge)' }}>
        <span className="panel-title">家族树</span>
        <span className="panel-sub">滚轮缩放 · 拖拽平移 · 点击人物查看 · Esc 返回</span>
        <div className="btn-group" style={{ marginLeft: 'auto' }}>
          <button className="btn ghost" onClick={fit}>全览</button>
          <button className="btn ghost" onClick={focusMe}>回到家主</button>
          <button className="btn ghost" onClick={() => setTreeOpen(false)}>关闭 ✕</button>
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
            {/* 世代标尺 */}
            {gens.map(([gen, label]) => (
              <text key={gen} x={bbox.minX - 96} y={gen * GEN_H + 46} fill="var(--ink-faint)" fontSize="15" letterSpacing="4">
                {label}
              </text>
            ))}

            {/* 连线 */}
            {layout.links.map((l, i) => (
              <path key={i} d={l.d} fill="none" stroke="rgba(138,116,74,0.4)" strokeWidth={1.4} />
            ))}

            {/* 节点 */}
            {layout.drawings.map((n) => {
              const isSel = n.char.id === selectedId
              const isPlayer = n.char.id === snap.player_id
              const shownName = n.char.display_name ?? n.char.name
              return (
                <g
                  key={n.char.id}
                  transform={`translate(${n.x} ${n.y})`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => select(n.char.id)}
                >
                  <rect
                    width={n.w}
                    height={NODE_H}
                    rx={9}
                    fill={n.char.alive ? 'var(--panel-2)' : '#1b1611'}
                    stroke={isPlayer ? 'var(--gold)' : isSel ? 'var(--gold-bright)' : n.char.alive ? 'var(--edge)' : '#332a1d'}
                    strokeWidth={isPlayer ? 2.4 : isSel ? 1.8 : 1.2}
                  />
                  <g transform={`translate(6 ${(NODE_H - 30) / 2})`} pointerEvents="none">
                    <SigilSvg name={n.char.name} gender={n.char.gender} alive={n.char.alive} size={30} />
                  </g>
                  <text x={n.w - 8} y={20} textAnchor="end" fontSize="13.5" fill={n.char.alive ? 'var(--ink)' : 'var(--ink-faint)'} style={{ textDecoration: n.char.alive ? 'none' : 'line-through' }}>
                    {truncate(shownName, 5)}
                  </text>
                  <text x={n.w - 10} y={40} textAnchor="end" fontSize="11.5" fill={n.char.alive ? 'var(--ink-dim)' : '#8a6a55'}>
                    {n.char.alive ? `${n.char.age} 岁` : `†${n.char.death_year} ${n.char.death_reason_label ?? ''}`}
                  </text>
                  {isPlayer && (
                    <text x={n.w / 2} y={NODE_H + 15} textAnchor="middle" fontSize="11" fill="var(--gold)" letterSpacing="3">
                      ▲ {t('tree.head_mark')}
                    </text>
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

/* ── SVG 内绘制的迷你徽记（heraldry.Sigil 的 SVG 元素版） ── */
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

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…' : s
}

/* ── 布局：世代分层 + 夫妻并置 + 子女居中摊开 ── */
function buildLayout(chars: CharacterInfo[], playerId: number) {
  const byId = new Map(chars.map((c) => [c.id, c]))

  /* 玩家连通域：血亲祖先闭包 + 这些祖先的全部后代 + 配偶 */
  const include = new Set<number>()
  const ancestorsOf = (id: number) => {
    const stack = [id]
    while (stack.length) {
      const x = stack.pop()!
      if (include.has(x)) continue
      include.add(x)
      const c = byId.get(x)
      if (c?.father) stack.push(c.father)
      if (c?.mother) stack.push(c.mother)
    }
  }
  ancestorsOf(playerId)
  const queue = [...include]
  while (queue.length) {
    const c = byId.get(queue.pop()!)
    if (!c) continue
    for (const cid of c.children) {
      if (!include.has(cid)) {
        include.add(cid)
        queue.push(cid)
      }
    }
  }

  /* unit 划分：全部单人节点（不展示配偶；子女挂父系/母系血亲锚点） */
  const unitOf = new Map<number, string>()
  const units = new Map<string, Unit>()
  for (const id of include) {
    const c = byId.get(id)!
    if (unitOf.has(id)) continue
    const key = `u${id}`
    units.set(key, { key, members: [c], parents: [], childUnits: [], gen: 0, x: 0, extent: 0 })
    unitOf.set(id, key)
  }

  /* 世代：person gen = max(parent gen)+1；unit gen = min(member gen) */
  const personGen = new Map<number, number>()
  const genOf = (id: number): number => {
    if (personGen.has(id)) return personGen.get(id)!
    const c = byId.get(id)!
    if (c.father == null && c.mother == null) {
      personGen.set(id, 0)
      return 0
    }
    personGen.set(id, 0) // 防环
    const ps = [c.father, c.mother].filter((p): p is number => p != null && unitOf.has(p))
    const g = ps.length ? Math.max(...ps.map((p) => genOf(p) + 1)) : 0
    personGen.set(id, g)
    return g
  }
  for (const id of include) genOf(id)
  for (const u of units.values()) {
    u.gen = Math.min(...u.members.map((m) => personGen.get(m.id) ?? 0))
  }

  /* unit 父子边：子女挂「血亲锚点」—— 父系婚姻挂父，母系婚姻挂母，缺位回退另一方 */
  for (const u of units.values()) {
    const m = u.members[0]
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
      if (pu && pu !== u.key && !u.parents.includes(pu)) u.parents.push(pu)
    }
  }
  for (const u of units.values()) {
    for (const puKey of u.parents) {
      const pu = units.get(puKey)
      if (pu && !pu.childUnits.includes(u.key)) pu.childUnits.push(u.key)
    }
  }

  /* 根 unit（无父母）按 gen 升序 */
  const roots = [...units.values()].filter((u) => u.parents.length === 0).sort((a, b) => a.gen - b.gen)
  if (roots.length === 0 && units.size > 0) roots.push([...units.values()][0])

  /* 自底向上 extent */
  const widthOf = (u: Unit): number => {
    const own = u.members.length === 2 ? NODE_W * 2 + COUPLE_GAP : NODE_W
    if (u.childUnits.length === 0) {
      u.extent = own
      return own
    }
    const kids = u.childUnits.map((k) => units.get(k)!).sort((a, b) => birthOf(a) - birthOf(b))
    let sum = 0
    for (const k of kids) sum += widthOf(k) + SIB_GAP
    u.extent = Math.max(own, sum - SIB_GAP)
    return u.extent
  }
  const birthOf = (u: Unit): number => Math.min(...u.members.map((m) => m.birth_year))

  /* 自顶向下摆放；连通域（根之间无共享后代时天然分开）横向排列 */
  let cursorX = 0
  let maxGen = 0
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
    const kids = u.childUnits.map((k) => units.get(k)!).sort((a, b) => birthOf(a) - birthOf(b))
    const total = kids.reduce((s, k) => s + k.extent, 0) + SIB_GAP * (kids.length - 1)
    let cx = x0 + (u.extent - total) / 2
    for (const k of kids) {
      place(k, cx)
      cx += k.extent + SIB_GAP
    }
  }

  /* 生成绘制数据 */
  const drawings: TreeNode[] = []
  const nodePos = new Map<number, { x: number; y: number; w: number }>()
  const nodes = new Map<number, { cx: number; cy: number }>()
  for (const u of units.values()) {
    const n = u.members.length
    const totalW = n === 2 ? NODE_W * 2 + COUPLE_GAP : NODE_W
    const sx = u.x - totalW / 2
    u.members.forEach((m, i) => {
      const x = sx + i * (NODE_W + COUPLE_GAP)
      nodePos.set(m.id, { x, y: u.gen * GEN_H, w: NODE_W })
    })
  }
  for (const [id, p] of nodePos) {
    const c = byId.get(id)!
    drawings.push({ char: c, x: p.x, y: p.y, w: p.w })
    nodes.set(id, { cx: p.x + p.w / 2, cy: p.y + NODE_H / 2 })
  }

  /* 连线（纯血缘：父母 -> 子女总线；不画婚姻） */
  const links: { d: string; kind: 'child' }[] = []
  for (const u of units.values()) {
    if (u.childUnits.length) {
      const my = nodePos.get(u.members[0].id)!
      const midX = my.x + NODE_W / 2
      const topY = my.y + NODE_H / 2
      const busY = u.gen * GEN_H + NODE_H + 34
      links.push({ d: `M${midX} ${topY} L${midX} ${busY}`, kind: 'child' })
      let busMinX = Infinity
      let busMaxX = -Infinity
      for (const ku of u.childUnits) {
        const kuUnit = units.get(ku)!
        const cp = nodePos.get(kuUnit.members[0].id)!
        const cx = cp.x + NODE_W / 2
        const cy = cp.y - 8
        busMinX = Math.min(busMinX, cx)
        busMaxX = Math.max(busMaxX, cx)
        links.push({ d: `M${cx} ${busY} L${cx} ${cy}`, kind: 'child' })
      }
      links.push({ d: `M${busMinX} ${busY} L${busMaxX} ${busY}`, kind: 'child' })
    }
  }

  const genLabels = new Map<number, string>()
  for (let g = 0; g <= maxGen; g++) genLabels.set(g, `${g + 1} ${t("tree.gen")}`)

  const xs = [...nodePos.values()].map((p) => p.x)
  const minY = 0
  return {
    nodes,
    drawings,
    links,
    genLabels,
    bbox: {
      minX: Math.min(...xs, 0) - NODE_W,
      minY,
      maxX: Math.max(...[...nodePos.values()].map((p) => p.x + p.w), 400) + NODE_W,
      maxY: (maxGen + 1) * GEN_H + 60,
    },
  }
}
