/* 终局画卷：绝嗣之时，展示王朝的一生 */

import { useStore } from '../../store'

export default function GameOver() {
  const snap = useStore((s) => s.snap)
  const openModal = useStore((s) => s.openModal)
  const setTreeOpen = useStore((s) => s.setTreeOpen)
  if (!snap || (!snap.over && !window.location.search.includes('over-preview'))) return null

  const player = snap.characters.find((c) => c.id === snap.player_id)
  const dyn = snap.dynasties.find((d) => d.id === player?.dynasty)
  const s = snap.stats

  return (
    <div className="gameover-veil">
      <div className="epitaph">
        <div className="go-orn">✦ ─────── ✦ ─────── ✦</div>
        <h1>{snap.over_reason || '宗族落幕'}</h1>
        <div className="go-reason">
          {dyn?.name ?? '家族'}的历史至此合卷 —— 自 {s.start_year} 年弗拉季斯拉夫执掌家业，凡 {s.years_played} 年。
        </div>
        <div className="go-stats">
          <div className="go-stat"><b>{s.years_played}</b><span>存续之年</span></div>
          <div className="go-stat"><b>{s.generations}</b><span>传承世代</span></div>
          <div className="go-stat"><b>{s.births}</b><span>降生人数</span></div>
          <div className="go-stat"><b>{s.deaths}</b><span>逝去之人</span></div>
          <div className="go-stat"><b>{s.marriages}</b><span>缔结姻缘</span></div>
        </div>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
          <button className="btn" onClick={() => setTreeOpen(true)}>
            瞻仰族谱
          </button>
          <button className="btn" onClick={() => openModal('saves')}>
            翻检档案
          </button>
          <button className="btn primary" onClick={() => openModal('new')}>
            开启新篇章
          </button>
        </div>
        <div className="go-orn" style={{ marginTop: 30, fontSize: 11, color: 'var(--ink-faint)', letterSpacing: '0.3em' }}>
          🕯 愿烛火不灭 🕯
        </div>
      </div>
    </div>
  )
}
