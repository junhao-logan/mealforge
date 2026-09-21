// src/pages/DashboardPage.jsx —— 今日概览(营养汇总 + 今日餐次 + 临期提醒)
import { AlertTriangle, UtensilsCrossed } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { MacroCard } from '@/components/dashboard/MacroCard'
import { MealEntryCard } from '@/components/mealplan/MealEntryCard'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { toISO } from '@/lib/dateRange'

export function DashboardPage() {
    const { t, i18n } = useTranslation()
    const { call } = useApi()
    const today = new Date()
    const todayISO = toISO(today)
    const locale = (i18n.language || 'en').startsWith('zh') ? 'zh-CN' : 'en-US'
    const dateStr = today.toLocaleDateString(locale, {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    })

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
            setError(e.message || t('common.loadFailed'))
        } finally {
            setLoading(false)
        }
    }, [call, todayISO, t])

    useEffect(() => { reload() }, [reload])

    async function handleComplete(entry) {
        try {
            const res = await call(
                api.patch,
                `/meal-plans/${entry.plan_id}/entries/${entry.id}/complete`,
            )
            if (res?.shortfalls?.length > 0) {
                alert(t('meal.shortStock', { count: res.shortfalls.length }))
            }
            await reload()
        } catch (e) {
            alert(e.message || t('meal.completeFailed'))
        }
    }

    async function handleUncomplete(entry) {
        try {
            await call(api.patch, `/meal-plans/${entry.plan_id}/entries/${entry.id}/uncomplete`)
            await reload()
        } catch (e) {
            alert(e.message || t('meal.uncompleteFailed'))
        }
    }

    async function handleDelete(entry) {
        if (!confirm(t('meal.confirmDelete'))) return
        try {
            await call(api.del, `/meal-plans/${entry.plan_id}/entries/${entry.id}`)
            await reload()
        } catch (e) {
            alert(e.message || t('common.deleteFailed'))
        }
    }

    if (loading) return <State text={t('common.loading')} />
    if (error) return <State text={t('common.errorPrefix', { msg: error })} />

    return (
        <div>
            {/* 标题 */}
            <div className="mb-6">
                <h1 className="text-2xl font-bold text-slate-900">{t('nav.dashboard')}</h1>
                <p className="mt-1 text-sm text-slate-500">{dateStr}</p>
            </div>

            {/* 今日营养 */}
            <section className="mb-8">
                <h2 className="mb-3 font-semibold text-slate-800">{t('dashboard.nutrition')}</h2>
                {summary && !summary.has_goal && (
                    <p className="mb-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-700">
                        {t('dashboard.noGoal')} ·{' '}
                        <Link to="/nutrition" className="font-medium underline">{t('dashboard.setGoal')}</Link>
                    </p>
                )}
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                    <MacroCard label={t('macro.calories')} unit="kcal" macro={summary?.calories} accent="bg-orange-400" />
                    <MacroCard label={t('macro.protein')} unit="g" macro={summary?.protein_g} accent="bg-red-400" />
                    <MacroCard label={t('macro.carbs')} unit="g" macro={summary?.carbs_g} accent="bg-blue-400" />
                    <MacroCard label={t('macro.fat')} unit="g" macro={summary?.fat_g} accent="bg-yellow-400" />
                </div>
            </section>

            {/* 两栏: 今日餐次 + 临期 */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* 今日餐次 */}
                <section>
                    <div className="mb-3 flex items-center justify-between">
                        <h2 className="flex items-center gap-2 font-semibold text-slate-800">
                            <UtensilsCrossed className="h-4 w-4 text-slate-400" />
                            {t('dashboard.meals')}
                        </h2>
                        <Link to="/meal-plans" className="text-sm text-slate-400 hover:text-slate-600">
                            {t('dashboard.toPlans')}
                        </Link>
                    </div>
                    {entries.length === 0 ? (
                        <EmptyBox text={t('dashboard.noMeals')} />
                    ) : (
                        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                            {entries.map((e) => (
                                <MealEntryCard key={e.id} entry={e} onComplete={handleComplete} onUncomplete={handleUncomplete} onDelete={handleDelete} />
                            ))}
                        </div>
                    )}
                </section>

                {/* 临期提醒 */}
                <section>
                    <div className="mb-3 flex items-center justify-between">
                        <h2 className="flex items-center gap-2 font-semibold text-slate-800">
                            <AlertTriangle className="h-4 w-4 text-amber-500" />
                            {t('dashboard.expiring')}
                        </h2>
                        <Link to="/inventory" className="text-sm text-slate-400 hover:text-slate-600">
                            {t('dashboard.toInventory')}
                        </Link>
                    </div>
                    {expiring.length === 0 ? (
                        <EmptyBox text={t('dashboard.allFresh')} />
                    ) : (
                        <div className="space-y-2">
                            {expiring.map((it) => (
                                <div
                                    key={it.id}
                                    className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm"
                                >
                                    <span className="font-medium text-slate-900">
                                        {ingredients[it.ingredient_id] || t('inventory.food', { id: it.ingredient_id })}
                                    </span>
                                    <span className="text-amber-700">
                                        {it.expires_at ? t('dashboard.expiresOn', { date: it.expires_at }) : t('dashboard.expiringTag')}
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
