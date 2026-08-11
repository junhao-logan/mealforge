// src/components/layout/Sidebar.jsx
// 左侧固定导航栏 —— 所有页面共用。NavLink 高亮当前页。
import { UserButton } from '@clerk/clerk-react'
import {
    LayoutDashboard, Package, BookOpen, CalendarDays, ShoppingCart, Target,
} from 'lucide-react'
import { NavLink } from 'react-router'

// 导航项集中定义, 加页面只改这里(复用)
const NAV_ITEMS = [
    { to: '/', label: '今日', icon: LayoutDashboard, end: true },
    { to: '/inventory', label: '库存', icon: Package },
    { to: '/recipes', label: '菜谱', icon: BookOpen },
    { to: '/meal-plans', label: '餐计划', icon: CalendarDays },
    { to: '/shopping', label: '采购', icon: ShoppingCart },
    { to: '/nutrition', label: '营养目标', icon: Target },
]

export function Sidebar() {
    return (
        <aside className="flex h-screen w-60 flex-col border-r bg-white">
            {/* Logo */}
            <div className="flex h-16 items-center gap-2 border-b px-6">
                <span className="text-xl font-bold text-slate-900">MealForge</span>
            </div>

            {/* 导航 */}
            <nav className="flex-1 space-y-1 p-3">
                {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={end}
                        className={({ isActive }) =>
                            `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${isActive
                                ? 'bg-slate-900 text-white'
                                : 'text-slate-600 hover:bg-slate-100'
                            }`
                        }
                    >
                        <Icon className="h-5 w-5" />
                        {label}
                    </NavLink>
                ))}
            </nav>

            {/* 底部用户 */}
            <div className="border-t p-4">
                <UserButton showName />
            </div>
        </aside>
    )
}