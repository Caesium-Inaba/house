/* 应用骨架：顶栏 + 三栏 + 覆盖层 */

import { useEffect } from 'react'
import { useStore, tickTime } from './store'
import TopBar from './components/TopBar'
import CharacterCard from './components/CharacterCard'
import Chronicle from './components/Chronicle'
import DynastyPanel from './components/DynastyPanel'
import FamilyTree from './components/FamilyTree'
import NamingModal from './components/modals/NamingModal'
import TutoringModal from './components/modals/TutoringModal'
import MarriageModal from './components/modals/MarriageModal'
import SaveModal from './components/modals/SaveModal'
import NewGameModal from './components/modals/NewGameModal'
import GameOver from './components/modals/GameOver'
import Toasts from './components/modals/Toasts'

export default function App() {
  const snap = useStore((s) => s.snap)
  const busy = useStore((s) => s.busy)
  const auto = useStore((s) => s.auto)

  useEffect(() => {
    void useStore.getState().boot()
  }, [])

  /* 自动推进：一旬一息；遇命名 / 终局 / 读取中暂停 */
  useEffect(() => {
    if (!auto || busy || !snap || snap.over || snap.naming_queue.length > 0) return
    const t = setTimeout(() => void tickTime('xun'), 320)
    return () => clearTimeout(t)
  }, [auto, busy, snap])

  /* 全局键盘 */
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || e.metaKey || e.ctrlKey || e.altKey) return
      const st = useStore.getState()
      if (e.key === 'Escape') {
        if (st.modal) st.closeModal()
        else if (st.treeOpen) st.setTreeOpen(false)
        return
      }
      if (st.modal || st.treeOpen) return
      switch (e.code) {
        case 'Space':
          e.preventDefault()
          void tickTime('xun')
          break
        case 'KeyY':
          void tickTime('year')
          break
        case 'KeyA':
          st.setAuto(!st.auto)
          break
        case 'KeyT':
          st.setTreeOpen(!st.treeOpen)
          break
        case 'KeyM':
          if (!st.snap?.over) st.openModal('marriage')
          break
        case 'KeyS':
          st.openModal('saves')
          break
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  if (!snap) {
    return (
      <div className="app">
        <div className="empty" style={{ margin: 'auto' }}>
          {busy ? '正在翻开编年史…' : '无法连接游戏服务'}
        </div>
        <Toasts />
      </div>
    )
  }

  return (
    <div className="app">
      <TopBar />
      <main className="columns">
        <div className="col">
          <CharacterCard />
        </div>
        <div className="col">
          <Chronicle />
        </div>
        <div className="col">
          <DynastyPanel />
        </div>
      </main>

      {(snap.over || window.location.search.includes('over-preview')) && <GameOver />}

      <FamilyTree />
      <NamingModal />
      <TutoringModal />
      <MarriageModal />
      <SaveModal />
      <NewGameModal />
      <Toasts />
    </div>
  )
}
