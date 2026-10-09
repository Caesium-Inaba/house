/* 事件浮窗（CK3 式）：事件弹出后时间照常流动；无遮罩；可拖拽；超时自动落定。
 *
 * 与 modal 的区别：.veil/.modal 有毛玻璃遮罩（存读档/婚配/新局用），
 * 事件窗是普通浮层（.event-win），不阻挡背景交互。
 */

import { useRef, type ReactNode } from 'react'
import { t } from '../../i18n'
import type { EventKind } from '../../store'
import { NamingBody, TutoringBody, TraitPickBody } from './bodies'

const TITLES: Record<EventKind, string> = {
  naming: '命名礼',
  tutoring: '教养礼',
  traitpick: '性情抉择',
}

const WIDTHS: Record<EventKind, string> = {
  naming: 'min(440px, 90vw)',
  tutoring: 'min(500px, 90vw)',
  traitpick: 'min(440px, 90vw)',
}

export function EventWinBox({ kind, x, y, onClose, onMove }: {
  kind: EventKind
  x: number
  y: number
  onClose: () => void
  onMove: (x: number, y: number) => void
}) {
  const drag = useRef<{ px: number; py: number; x: number; y: number } | null>(null)

  return (
    <div className="event-win" style={{ left: x, top: y, width: WIDTHS[kind] }}>
      <div
        className="event-win-head"
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture?.(e.pointerId)
          drag.current = { px: e.clientX, py: e.clientY, x, y }
        }}
        onPointerMove={(e) => {
          if (!drag.current) return
          onMove(
            Math.max(6, drag.current.x + e.clientX - drag.current.px),
            Math.max(44, drag.current.y + e.clientY - drag.current.py),
          )
        }}
        onPointerUp={() => (drag.current = null)}
        onPointerCancel={() => (drag.current = null)}
      >
        <span className="modal-title" style={{ fontSize: 15 }}>{TITLES[kind]}</span>
        <span className="event-win-hint">{t('evwin.timeout_hint')}</span>
        <button className="btn ghost" style={{ marginLeft: 'auto', padding: '2px 8px' }} onClick={onClose}>✕</button>
      </div>
      <Body kind={kind} shelve={onClose} />
    </div>
  )
}

function Body({ kind, shelve }: { kind: EventKind; shelve: () => void }): ReactNode {
  if (kind === 'naming') return <NamingBody shelve={shelve} />
  if (kind === 'tutoring') return <TutoringBody shelve={shelve} />
  return <TraitPickBody shelve={shelve} />
}
