import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/tokens.css'
import './styles/base.css'
import './styles/components.css'
import App from './App'
import { useStore } from './store'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

/* 测试与诊断出口：让自动化/诊断脚本可以直接读写应用状态 */
;(globalThis as unknown as Record<string, unknown>).__store = useStore

/* 诊断探针：快照每次变更的绝对时间戳（订阅回调同步触发，不受后台 tab 调度影响） */
;(globalThis as unknown as { __uiProbe?: number[] }).__uiProbe = []
useStore.subscribe((s, prev) => {
  if (s.snap !== prev.snap) {
    const arr = (globalThis as unknown as { __uiProbe?: number[] }).__uiProbe ?? []
    arr.push(performance.now())
    ;(globalThis as unknown as { __uiProbe?: number[] }).__uiProbe = arr
  }
})
