/* 事件浮窗层：把待办事件渲染成可拖拽浮窗（非模态、无遮罩、时间不停） */

import { useStore } from '../../store'
import { t } from '../../i18n'
import { EventWinBox } from './boxes'

export default function EventWindows() {
  const wins = useStore((s) => s.eventWins)
  const closeEventWin = useStore((s) => s.closeEventWin)
  const moveEventWin = useStore((s) => s.moveEventWin)
  void t
  if (wins.length === 0) return null
  return (
    <>
      {wins.map((w) => (
        <EventWinBox
          key={w.kind}
          kind={w.kind}
          x={w.x}
          y={w.y}
          onClose={() => closeEventWin(w.kind)}
          onMove={(x, y) => moveEventWin(w.kind, x, y)}
        />
      ))}
    </>
  )
}
