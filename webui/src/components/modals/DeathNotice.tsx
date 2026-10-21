/* 玩家角色死亡通知：全屏通知层，确认后继续 */

import { useStore, runAction } from '../../store'
import { api } from '../../api/client'
import { t } from '../../i18n'

export default function DeathNotice() {
  const snap = useStore((s) => s.snap)
  if (!snap?.death_notice) return null
  const n = snap.death_notice

  const dismiss = async () => {
    await runAction(() => api.dismissNotice('death'), { silent: true })
  }

  return (
    <div className="death-veil">
      <div className="death-card">
        <div className="go-orn">✦ ─────── ✦ ─────── ✦</div>
        <h1>{t('death_notice.title')}</h1>
        <div className="death-reason">
          {t('death_notice.body', {
            old: n.old_name,
            reason: n.reason,
            heir: n.heir_name,
            age: n.heir_age ?? '?',
          })}
        </div>
        <button className="btn primary" onClick={() => void dismiss()}>
          {t('death_notice.continue')}
        </button>
      </div>
    </div>
  )
}
