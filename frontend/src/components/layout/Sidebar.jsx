// src/components/layout/Sidebar.jsx
// 左侧固定导航栏 —— 所有页面共用。NavLink 高亮当前页。
import { UserButton } from '@clerk/clerk-react'
import {
    LayoutDashboard, Package, BookOpen, CalendarDays, ShoppingCart, Target, User,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router'

// 导航项集中定义, 加页面只改这里(复用)。labelKey → i18n 键
const NAV_ITEMS = [
    { to: '/', labelKey: 'nav.dashboard', icon: LayoutDashboard, end: true },
    { to: '/inventory', labelKey: 'nav.inventory', icon: Package },
    { to: '/recipes', labelKey: 'nav.recipes', icon: BookOpen },
    { to: '/meal-plans', labelKey: 'nav.mealPlans', icon: CalendarDays },
    { to: '/shopping', labelKey: 'nav.shopping', icon: ShoppingCart },
    { to: '/nutrition', labelKey: 'nav.nutrition', icon: Target },
    { to: '/account', labelKey: 'nav.account', icon: User },
]

export function Sidebar() {
    const { t } = useTranslation()
    return (
        <aside className="flex h-screen w-60 flex-col border-r bg-white">
            {/* Logo */}
            <div className="flex h-16 items-center gap-2 border-b px-6">
                <span className="text-xl font-bold text-slate-900">{t('app.name')}</span>
            </div>

            {/* 导航 */}
            <nav className="flex-1 space-y-1 p-3">
                {NAV_ITEMS.map(({ to, labelKey, icon: Icon, end }) => (
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
                        {t(labelKey)}
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