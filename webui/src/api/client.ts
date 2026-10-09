/* API 客户端：所有请求都走这里 */

import type { ApiResponse } from '../types'

async function jf<T = ApiResponse>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `${res.status}`
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      /* 非 JSON 错误体 */
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

function post(path: string, body?: unknown): Promise<ApiResponse> {
  return fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(jf)
}

export const api = {
  state: (): Promise<ApiResponse> => fetch('/api/state').then(jf),
  tick: (unit: 'xun' | 'year'): Promise<ApiResponse> => post('/api/tick', { unit }),
  naming: (child_id: number, name: string): Promise<ApiResponse> =>
    post('/api/naming', { child_id, name }),
  candidates: (): Promise<ApiResponse> => fetch('/api/marriage/candidates').then(jf),
  marry: (target_id: number): Promise<ApiResponse> => post('/api/marriage', { target_id }),
  saves: (): Promise<ApiResponse> => fetch('/api/saves').then(jf),
  save: (name: string, overwrite: boolean): Promise<ApiResponse> =>
    post('/api/save', { name, overwrite }),
  load: (name: string): Promise<ApiResponse> => post('/api/load', { name }),
  delSave: (name: string): Promise<ApiResponse> =>
    fetch(`/api/saves/${encodeURIComponent(name)}`, { method: 'DELETE' }).then(jf),
  newGame: (seed: number | null): Promise<ApiResponse> => post('/api/new', { seed }),
  tutoring: (child_id: number, focus: string, guardian_id: number | null): Promise<ApiResponse> =>
    post('/api/tutoring', { child_id, focus, guardian_id }),
  traitPick: (child_id: number, trait: string): Promise<ApiResponse> =>
    post('/api/traitpick', { child_id, trait }),
  betrothalPools: (): Promise<ApiResponse> => fetch('/api/betrothal/pools').then(jf),
  betrothal: (a_id: number, b_id: number, patrilineal: boolean): Promise<ApiResponse> =>
    post('/api/betrothal', { a_id, b_id, patrilineal }),
  legacyBuy: (tree: string): Promise<ApiResponse> => post('/api/legacy', { tree }),
}
