/* 程序化纹章：由家族 id 确定性生成盾徽 / 菱徽；人物徽记与事件图标。 */

import { useId } from 'react'

interface Tincture {
  key: string
  fill: string
  dark: boolean // 深色底（适合浅色 charge）
}

const TINCTURES: Tincture[] = [
  { key: 'gules', fill: '#9e3129', dark: true },
  { key: 'azure', fill: '#2e517f', dark: true },
  { key: 'sable', fill: '#292218', dark: true },
  { key: 'or', fill: '#c9a227', dark: false },
  { key: 'argent', fill: '#d8d0bd', dark: false },
  { key: 'vert', fill: '#3d6b34', dark: true },
  { key: 'purpure', fill: '#6d3d7a', dark: true },
]

const SHIELD =
  'M10 8 H90 V58 C90 84 70 100 50 108 C30 100 10 84 10 58 Z'
const LOZENGE = 'M50 5 L95 58 L50 111 L5 58 Z'

function hash32(n: number): number {
  let x = (n | 0) + 0x9e3779b9
  x = Math.imul(x ^ (x >>> 16), 0x21f0aaad)
  x = Math.imul(x ^ (x >>> 15), 0x735a2d97)
  return (x ^ (x >>> 15)) >>> 0
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/* charge 图形（画在 100x116 视窗中央） */
function Charge({ kind, fill }: { kind: number; fill: string }) {
  switch (((kind % 6) + 6) % 6) {
    case 0: // 五角星
      return (
        <polygon
          fill={fill}
          points="50,32 56.9,49.2 75.4,50 60.8,61.8 65.7,79.5 50,69.5 34.3,79.5 39.2,61.8 24.6,50 43.1,49.2"
        />
      )
    case 1: // 十字
      return <path fill={fill} d="M43 30h14v13h13v14H57v13H43V70H30V56h13z" />
    case 2: // 新月
      return (
        <path
          fill={fill}
          d="M56 30a26 26 0 1 0 0 52 21 21 0 1 1 0-52z"
        />
      )
    case 3: // 塔楼
      return (
        <path
          fill={fill}
          d="M34 34h6v-6h7v6h6v-6h7v6h6v14h-4v34H38V48h-4zm6 20h8v14h-8zm14 0h8v14h-8z"
          fillRule="evenodd"
        />
      )
    case 4: // 人字纹
      return <polygon fill={fill} points="50,42 76,58 76,74 50,58 24,74 24,58" />
    default: // 菱形
      return <polygon fill={fill} points="50,32 68,58 50,84 32,58" />
  }
}

function Partition({
  style,
  fill,
  clipId,
}: {
  style: number
  fill: string
  clipId: string
}) {
  if (style % 5 === 0) return null
  const shapes: Record<number, string> = {
    1: 'M50 0h50v116H50z', // 垂直分割
    2: 'M0 58h100v58H0z', // 水平分割
    3: 'M0 34 L100 74 v30 L0 64 z', // 对角带
    4: 'M50 0h50v58H50z M0 58h50v58H0z', // 四分
  }
  return (
    <path d={shapes[style % 5]} fill={fill} clipPath={`url(#${clipId})`} />
  )
}

/** 家族纹章：dynastyId 决定一切；female 用菱徽 */
export function Crest({
  did,
  female = false,
  size = 44,
  className,
  title,
}: {
  did: number | null
  female?: boolean
  size?: number
  className?: string
  title?: string
}) {
  const clipId = useId()
  const seed = hash32((did ?? 0) * 2654435761 + (female ? 7 : 3))
  const r = mulberry32(seed)
  const fieldA = TINCTURES[Math.floor(r() * TINCTURES.length)]
  let fieldB = TINCTURES[Math.floor(r() * TINCTURES.length)]
  if (fieldB.key === fieldA.key) fieldB = TINCTURES[(TINCTURES.indexOf(fieldA) + 3) % TINCTURES.length]
  // charge 色与底色对比
  const chargePool = TINCTURES.filter((t) => t.dark !== fieldA.dark)
  const charge = chargePool[Math.floor(r() * chargePool.length)]
  const outline = fieldA.dark ? '#e8cf8a' : '#4a3a1c'

  return (
    <svg
      viewBox="0 0 100 116"
      width={size}
      height={size * 1.16}
      className={className}
      role="img"
      aria-label={title ?? '纹章'}
      style={{ display: 'block', flex: 'none' }}
    >
      <defs>
        <clipPath id={clipId}>
          <path d={female ? LOZENGE : SHIELD} />
        </clipPath>
      </defs>
      <path d={female ? LOZENGE : SHIELD} fill={fieldA.fill} />
      <g clipPath={`url(#${clipId})`}>
        <Partition style={Math.floor(r() * 5)} fill={fieldB.fill} clipId={clipId} />
        <Charge kind={Math.floor(r() * 6)} fill={charge.fill} />
      </g>
      <path
        d={female ? LOZENGE : SHIELD}
        fill="none"
        stroke={outline}
        strokeWidth="4"
        opacity="0.75"
      />
    </svg>
  )
}

/** 人物徽记：圆底 + 名字首字 + 性别/存亡环 */
export function Sigil({
  name,
  gender,
  alive = true,
  did = null,
  size = 36,
  player = false,
}: {
  name: string
  gender: 'male' | 'female'
  alive?: boolean
  did?: number | null
  size?: number
  player?: boolean
}) {
  const seed = hash32((did ?? 0) * 40503 + name.length * 97 + name.charCodeAt(0))
  const r = mulberry32(seed)
  const a = TINCTURES[Math.floor(r() * TINCTURES.length)]
  const b = TINCTURES[(Math.floor(r() * TINCTURES.length) + 3) % TINCTURES.length]
  const ring = !alive ? '#4d4438' : player ? 'var(--gold)' : gender === 'male' ? '#4d6a8c' : '#7d5a75'
  const initial = name ? name.slice(0, 1) : '·'
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} style={{ display: 'block', flex: 'none' }}>
      <defs>
        <linearGradient id={`sg${seed}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={a.fill} />
          <stop offset="1" stopColor={b.fill} />
        </linearGradient>
      </defs>
      <circle cx="50" cy="50" r="46" fill={`url(#sg${seed})`} />
      <circle cx="50" cy="50" r="46" fill="none" stroke={ring} strokeWidth={player ? 7 : 4} />
      <text
        x="50"
        y="66"
        textAnchor="middle"
        fontSize="52"
        fill={alive ? '#f2e8d0' : 'rgba(242,232,208,0.45)'}
        fontFamily="var(--font-display)"
      >
        {initial}
      </text>
      {!alive && <text x="86" y="24" textAnchor="middle" fontSize="26">⚰</text>}
    </svg>
  )
}
