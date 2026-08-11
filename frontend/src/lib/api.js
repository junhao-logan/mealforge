// src/lib/api.js
// 后端调用统一封装 —— 所有页面调 API 都走这里, 不直接 fetch。
//
// 职责:
// 1. 自动带上 Clerk JWT(后端所有端点都要认证)
// 2. 统一 base URL、JSON 头、错误处理
// 3. 页面只调 api.get('/inventory') 这种, 不关心 token / 拼 header

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

// Clerk 的 getToken 在组件里通过 useAuth() 拿, 但 api.js 是普通模块。
// 方案: 调用方把 getToken 传进来(见 useApi hook), 或用全局注册。
// 这里用"传入 token"的简单做法: 每个请求带上当前 token。

async function request(method, path, { token, body, params } = {}) {
    // 拼 query 参数
    let url = `${BASE_URL}${path}`
    if (params) {
        const qs = new URLSearchParams(params).toString()
        if (qs) url += `?${qs}`
    }

    const headers = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const resp = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
    })

    // 204 无内容
    if (resp.status === 204) return null

    const data = await resp.json().catch(() => null)

    if (!resp.ok) {
        // 后端错误统一抛出, 页面 catch 显示
        const detail = data?.detail || `请求失败 (${resp.status})`
        throw new ApiError(detail, resp.status)
    }
    return data
}

export class ApiError extends Error {
    constructor(message, status) {
        super(message)
        this.name = 'ApiError'
        this.status = status
    }
}

// 便捷方法: 页面用 api.get(path, {token, params}) 等
export const api = {
    get: (path, opts) => request('GET', path, opts),
    post: (path, opts) => request('POST', path, opts),
    patch: (path, opts) => request('PATCH', path, opts),
    del: (path, opts) => request('DELETE', path, opts),
}