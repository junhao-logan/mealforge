// src/components/layout/AppLayout.jsx
// 页面外壳: 左侧栏 + 右侧内容区。<Outlet /> 是子路由(各页面)渲染的位置。
import { Outlet } from 'react-router'

import { Sidebar } from './Sidebar'

export function AppLayout() {
    return (
        <div className="flex h-screen bg-slate-50">
            <Sidebar />
            <main className="flex-1 overflow-y-auto">
                <div className="mx-auto max-w-6xl p-8">
                    <Outlet />   {/* 当前路由的页面在这里渲染 */}
                </div>
            </main>
        </div>
    )
}