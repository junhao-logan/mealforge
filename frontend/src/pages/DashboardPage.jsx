// src/pages/DashboardPage.jsx —— 今日概览(营养汇总 + 今日餐次 + 临期提醒)
import { AlertTriangle, UtensilsCrossed } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'

import { MacroCard } from '@/components/dashboard/MacroCard'
import { MealEntryCard } from '@/components/mealplan/MealEntryCard'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { fullDate, toISO } from '@/lib/dateRange'

export function DashboardPage() {
    const { call } = useApi()
    const today = new Date()
    const todayISO = toISO(today)

    const [summary, setSummary] = useState(null)
    const [entries, setEntries] = useState([])
    const [expiring, setExpiring] = useState([])
    const [ingredients, setIngredients] = useState({})
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const reload = useCallback(async () => {
        try {
            setError(null)
            const [sum, ents, inv, ings] = await Promise.all([
                call(api.get, '/meal-plans/daily-summary', { params: { date: todayISO } }),
                call(api.get, '/meal-plans/entries', { params: { start: todayISO, end: todayISO } }),
                call(api.get, '/inventory'),
                call(api.get, '/ingredients', { params: { limit: 100 } }),
            ])
            setSummary(sum)
            setEntries(ents || [])
            setExpiring((inv || []).filter((it) => it.expiry_status === 'expiring'))
            const map = {}
            for (const ing of ings || []) map[ing.id] = ing.name
            setIngredients(map)
        } catch (e) {
            setError(e.message || '加载失败')
        } finally {
            setLoading(false)
        }
    }, [call, todayISO])

    useEffect(() => { reload() }, [reload])

    async function handleComplete(entry) {
        try {
            const res = await call(
                api.patch,
                `/meal-plans/${entry.plan_id}/entries/${entry.id}/complete`,
            )
            if (res?.shortfalls?.length > 0) {
                alert(`已完成,但库存不足 ${res.shortfalls.length} 样`)
            }
            await reload()
        } catch (e) {
            alert(e.message || '完成失败')
        }
    }

    async function handleDelete(entry) {
        if (!confirm('确定删除?')) return
        try {
            await call(api.del, `/meal-plans/${entry.plan_id}/entries/${entry.id}`)
            await reload()
        } catch (e) {
            alert(e.message || '删除失败')
        }
    }

    if (loading) return <State text="加载中…" />
    if (error) return <State text={`出错了: ${error}`} />

    return (
        <div>
            {/* 标题 */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-slate-900">今日</h1>
                <p className="mt-1 text-sm text-slate-500">{fullDate(today)}</p>
            </div>

            {/* 今日营养 */}
            <section className="mb-8">
                <h2 className="mb-3 font-semibold text-slate-800">今日营养</h2>
                {summary && !summary.has_goal && (
                    <p className="mb-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-700">
                        还没设置营养目标 ·{' '}
                        <Link to="/nutrition" className="font-medium underline">去设置</Link>
                    </p>
                )}
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                    <MacroCard label="热量" unit="kcal" macro={summary?.calories} accent="bg-orange-400" />
                    <MacroCard label="蛋白质" unit="g" macro={summary?.protein_g} accent="bg-red-400" />
                    <MacroCard label="碳水" unit="g" macro={summary?.carbs_g} accent="bg-blue-400" />
                    <MacroCard label="脂肪" unit="g" macro={summary?.fat_g} accent="bg-yellow-400" />
                </div>
            </section>

            {/* 两栏: 今日餐次 + 临期 */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* 今日餐次 */}
                <section>
                    <div className="mb-3 flex items-center justify-between">
                        <h2 className="flex items-center gap-2 font-semibold text-slate-800">
                            <UtensilsCrossed className="h-4 w-4 text-slate-400" />
                            今日餐次
                        </h2>
                        <Link to="/meal-plans" className="text-sm text-slate-400 hover:text-slate-600">
                            去餐计划
                        </Link>
                    </div>
                    {entries.length === 0 ? (
                        <EmptyBox text="今天还没安排,去餐计划排一下" />
                    ) : (
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            {entries.map((e) => (
                                <MealEntryCard key={e.id} entry={e} onComplete={handleComplete} onDelete={handleDelete} />
                            ))}
                        </div>
                    )}
                </section>

                {/* 临期提醒 */}
                <section>
                    <div className="mb-3 flex items-center justify-between">
                        <h2 className="flex items-center gap-2 font-semibold text-slate-800">
                            <AlertTriangle className="h-4 w-4 text-amber-500" />
                            临期提醒
                        </h2>
                        <Link to="/inventory" className="text-sm text-slate-400 hover:text-slate-600">
                            去库存
                        </Link>
                    </div>
                    {expiring.length === 0 ? (
                        <EmptyBox text="没有临期食材,一切新鲜" />
                    ) : (
                        <div className="space-y-2">
                            {expiring.map((it) => (
                                <div
                                    key={it.id}
                                    className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm"
                                >
                                    <span className="font-medium text-slate-900">
                                        {ingredients[it.ingredient_id] || `食材 #${it.ingredient_id}`}
                                    </span>
                                    <span className="text-amber-700">
                                        {it.expires_at ? `${it.expires_at} 过期` : '临期'}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            </div>
        </div>
    )
}

function EmptyBox({ text }) {
    return (
        <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-slate-300">
            {text}
        </div>
    )
}

function State({ text }) {
    return <div className="flex h-64 items-center justify-center text-slate-400">{text}</div>
}