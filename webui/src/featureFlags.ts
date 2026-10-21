/* 功能开关
 *
 * SHOW_MANUAL_TICK：手动推进（推一日/推一月/推一年、Y 快捷键）已从 UI 移除。
 *   后端 /api/tick 的单位逻辑与前端 tickTime 全部保留，仅隐藏入口并注释；
 *   恢复时把此开关改为 true 即可。
 *
 * SHOW_TREE_TOOLBAR：家族树的「全览」「回到家主」按钮已从 UI 移除，
 *   fit()/focusOn() 实现保留，恢复时把此开关改为 true。
 */
export const SHOW_MANUAL_TICK = false
export const SHOW_TREE_TOOLBAR = false
