/* toast 通知流 */

import { useStore } from '../../store'

export default function Toasts() {
  const toasts = useStore((s) => s.toasts)
  return (
    <div className="toasts">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.kind === 'good' ? 'good' : t.kind === 'bad' ? 'bad' : ''}`}>
          {t.text}
        </div>
      ))}
    </div>
  )
}
