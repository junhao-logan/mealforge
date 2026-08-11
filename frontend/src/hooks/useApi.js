// src/hooks/useApi.js
// 把 "拿 Clerk token + 调 api" 封装成 hook, 页面用起来最简单。
//
// 用法(在页面组件里):
//   const { call } = useApi()
//   const data = await call(api.get, '/inventory')
// call 会自动注入当前用户的 token, 页面不用管认证。

import { useAuth } from '@clerk/clerk-react'
import { useCallback } from 'react'

export function useApi() {
    const { getToken } = useAuth()   // Clerk: 拿当前会话 token

    // call(apiFn, path, opts) —— 自动补 token 后调用 apiFn
    const call = useCallback(
        async (apiFn, path, opts = {}) => {
            const token = await getToken()          // 每次取最新 token(会自动刷新)
            return apiFn(path, { ...opts, token })
        },
        [getToken],
    )

    return { call }
}