/* 应用骨架：顶栏 + 三栏 + 覆盖层 */

import { useEffect, useLayoutEffect } from 'react'
import { useStore, tickTime, SPEED_INTERVALS } from './store'
import TopBar from './components/TopBar'
import CharacterDrawer from './components/CharacterDrawer'
import Chronicle from './components/Chronicle'
import DynastyPanel from './components/DynastyPanel'
import FamilyTree from './components/FamilyTree'
import EventWindows from './components/eventwin/EventWindows'
import MarriageModal from './components/modals/MarriageModal'
import SaveModal from './components/modals/SaveModal'
import NewGameModal from './components/modals/NewGameModal'
import GameOver from './components/modals/GameOver'
import Toasts from './components/modals/Toasts'

export default function App() {
  const snap = useStore((s) => s.snap)
  const busy = useStore((s) => s.busy)
  const auto = useStore((s) => s.auto)
  const speed = useStore((s) => s.speed)

  useEffect(() => {
    void useStore.getState().boot()
  }, [])

  /* 渲染性能探针：每次 commit 记时间戳（window.__uiProbe 由测试/诊断读取） */
  useLayoutEffect(() => {
    const arr = (window as unknown as { __uiProbe?: number[] }).__uiProbe ?? []
    arr.push(performance.now())
    ;(window as unknown as { __uiProbe?: number[] }).__uiProbe = arr
  })

  /* 自动推进：按流速档位逐旬推进；事件浮窗弹出时照常流动（CK3 式） */
  useEffect(() => {
    if (!auto || busy || !snap || snap.over) return
    const interval = SPEED_INTERVALS[Math.max(0, Math.min(SPEED_INTERVALS.length - 1, speed - 1))]
    const t = setTimeout(() => void tickTime('xun'), interval)
    return () => clearTimeout(t)
  }, [auto, busy, snap, speed])

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
          // 空格 = 暂停 / 开始（时间流速的五档不受影响）
          e.preventDefault()
          st.setAuto(!st.auto)
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
        {/* 人物栏预留空位：无论抽屉是否呼出，中/右两栏永不位移 */}
        <div className="col col-reserved" />
        <div className="col">
          <Chronicle />
        </div>
        <div className="col">
          <DynastyPanel />
        </div>
      </main>

      {snap.over && <GameOver />}

      <CharacterDrawer />

      <FamilyTree />
      {/* 备份（旧行为）：事件原本用阻塞式 modal 弹出（见 modals/NamingModal 等），
          现由 EventWindows 浮窗承担——事件弹出后时间照常流动。
          modal 组件保留在 modals/ 下作为备份，需要恢复阻塞式时在此挂回。 */}
      <EventWindows />
      <MarriageModal />
      <SaveModal />
      <NewGameModal />
      <Toasts />
    </div>
  )
}
