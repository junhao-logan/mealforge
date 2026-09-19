// src/pages/MealPlansPage.jsx —— 餐计划(天/周视图 + 周横竖 + plan管理 + AI生成)
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AddEntryDialog } from '@/components/mealplan/AddEntryDialog'
import { GenerateMealPlanDialog } from '@/components/mealplan/GenerateMealPlanDialog'
import { MealEntryCard } from '@/components/mealplan/MealEntryCard'
import { DeletePlanButton, PlanBar } from '@/components/mealplan/PlanBar'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import {
    addDays, fullDate, isToday, shortDate, toISO, weekdayLabel, weekDays, weekStart,
} from '@/lib/dateRange'

export function MealPlansPage() {
    const { t } = useTranslation()
    const { call } = useApi()
    const [granularity, setGranularity] = useState('week')   // 'day' | 'week'
    const [orientation, setOrientation] = useState('vertical')  // 周视图: 'vertical' | 'horizontal'
    const [anchor, setAnchor] = useState(() => weekStart(new Date()))
    const [dayAnchor, setDayAnchor] = useState(() => new Date())   // 天视图的当前天
    const [entries, setEntries] = useState([])
    const [plans, setPlans] = useState([])
    const [activePlanId, setActivePlanId] = useState(null)
    const [addDate, setAddDate] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    // 当前视图的日期范围
    const isWeek = granularity === 'week'
    const days = weekDays(anchor)
    const rangeStart = isWeek ? toISO(days[0]) : toISO(dayAnchor)
    const rangeEnd = isWeek ? toISO(days[6]) : toISO(dayAnchor)

    const reload = useCallback(async () => {
        try {
            setError(null)
            const [data, planList] = await Promise.all([
                call(api.get, '/meal-plans/entries', {
                    params: { start: rangeStart, end: rangeEnd },
                }),
                call(api.get, '/meal-plans'),
            ])
            setEntries(data || [])
            setPlans(planList || [])
        } catch (e) {
            setError(e.message || t('common.loadFailed'))
        } finally {
            setLoading(false)
        }
    }, [call, rangeStart, rangeEnd, t])

    useEffect(() => { reload() }, [reload])

    const visibleEntries = activePlanId === null
        ? entries
        : entries.filter((e) => e.plan_id === activePlanId)

    async function handleComplete(entry) {
        try {
            const res = await call(
                api.patch,
                `/meal-plans/${entry.plan_id}/entries/${entry.id}/complete`,
            )
            if (res?.shortfalls?.length > 0) {
                alert(t('mealPlans.shortStock', { count: res.shortfalls.length }))
            }
            await reload()
        } catch (e) {
            alert(e.message || t('meal.completeFailed'))
        }
    }

    async function handleDelete(entry) {
        if (!confirm(t('mealPlans.confirmDeleteEntry'))) return
        try {
            await call(api.del, `/meal-plans/${entry.plan_id}/entries/${entry.id}`)
            await reload()
        } catch (e) {
            alert(e.message || t('common.deleteFailed'))
        }
    }

    return (
        <div>
            {/* 顶部: 标题 + 视图切换 + AI 生成 */}
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                <h1 className="text-2xl font-bold text-slate-900">{t('mealPlans.title')}</h1>
                <div className="flex items-center gap-3">
                    {/* 天/周 开关 */}
                    <Segmented
                        options={[{ v: 'day', l: t('mealPlans.day') }, { v: 'week', l: t('mealPlans.week') }]}
                        value={granularity}
                        onChange={setGranularity}
                    />
                    {/* 周视图才有横竖开关 */}
                    {isWeek && (
                        <Segmented
                            options={[{ v: 'vertical', l: t('mealPlans.vertical') }, { v: 'horizontal', l: t('mealPlans.horizontal') }]}
                            value={orientation}
                            onChange={setOrientation}
                        />
                    )}
                    <GenerateMealPlanDialog defaultStart={rangeStart} onGenerated={reload} />
                </div>
            </div>

            <PlanBar
                plans={plans}
                activePlanId={activePlanId}
                onSelect={setActivePlanId}
                onChanged={reload}
            />

            {/* 日期导航 */}
            <div className="mb-4 flex items-center gap-4">
                <button
                    className="rounded-md p-1 hover:bg-slate-100"
                    onClick={() => isWeek ? setAnchor(addDays(anchor, -7)) : setDayAnchor(addDays(dayAnchor, -1))}
                >
                    <ChevronLeft className="h-5 w-5 text-slate-600" />
                </button>
                <span className="font-medium text-slate-700">
                    {isWeek ? `${shortDate(days[0])} – ${shortDate(days[6])}` : fullDate(dayAnchor)}
                </span>
                <button
                    className="rounded-md p-1 hover:bg-slate-100"
                    onClick={() => isWeek ? setAnchor(addDays(anchor, 7)) : setDayAnchor(addDays(dayAnchor, 1))}
                >
                    <ChevronRight className="h-5 w-5 text-slate-600" />
                </button>
                <button
                    className="ml-2 text-sm text-slate-400 hover:text-slate-600"
                    onClick={() => isWeek ? setAnchor(weekStart(new Date())) : setDayAnchor(new Date())}
                >
                    {isWeek ? t('mealPlans.backToWeek') : t('mealPlans.backToToday')}
                </button>
                {/* 选中某plan时, 右侧显示删除(避免误触) */}
                {activePlanId !== null && (
                    <div className="ml-auto">
                        <DeletePlanButton
                            plan={plans.find((p) => p.id === activePlanId) || { id: activePlanId }}
                            onDeleted={() => { setActivePlanId(null); reload() }}
                        />
                    </div>
                )}
            </div>

            {loading && <State text={t('common.loading')} />}
            {error && <State text={t('common.errorPrefix', { msg: error })} />}
            {!loading && !error && (
                isWeek ? (
                    <WeekView
                        days={days} entries={visibleEntries} orientation={orientation}
                        onComplete={handleComplete} onDelete={handleDelete}
                        onAdd={(iso) => setAddDate(iso)}
                    />
                ) : (
                    <DayView
                        date={dayAnchor} entries={visibleEntries}
                        onComplete={handleComplete} onDelete={handleDelete}
                        onAdd={(iso) => setAddDate(iso)}
                    />
                )
            )}

            <AddEntryDialog
                open={addDate !== null}
                date={addDate}
                plans={plans}
                defaultPlanId={activePlanId}
                onClose={() => setAddDate(null)}
                onAdded={reload}
            />
        </div>
    )
}

// 分段开关(复用: 天/周、横/竖)
function Segmented({ options, value, onChange }) {
    return (
        <div className="flex rounded-lg bg-slate-100 p-0.5">
            {options.map((o) => (
                <button
                    key={o.v}
                    className={`rounded-md px-3 py-1 text-sm font-medium transition-colors ${value === o.v ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
                        }`}
                    onClick={() => onChange(o.v)}
                >
                    {o.l}
                </button>
            ))}
        </div>
    )
}

// 一天里按日期取该天餐次
function entriesOf(entries, iso) {
    return entries.filter((e) => e.scheduled_date === iso)
}

// ── 周视图: 竖版(每天一块) / 横版(7列并排) ──
function WeekView({ days, entries, orientation, onComplete, onDelete, onAdd }) {
    if (orientation === 'horizontal') {
        return (
            <div className="grid grid-cols-7 gap-2">
                {days.map((d) => {
                    const iso = toISO(d)
                    const dayEntries = entriesOf(entries, iso)
                    return (
                        <div
                            key={iso}
                            className={`rounded-lg border p-2 ${isToday(d) ? 'border-slate-900' : 'border-slate-200'
                                }`}
                        >
                            <div className="mb-2 text-center">
                                <div className="text-xs font-semibold text-slate-700">{weekdayLabel(d)}</div>
                                <div className="text-xs text-slate-400">{shortDate(d)}</div>
                            </div>
                            <div className="space-y-1.5">
                                {dayEntries.map((e) => (
                                    <MealEntryCard key={e.id} entry={e} onComplete={onComplete} onDelete={onDelete} />
                                ))}
                                <button
                                    className="w-full rounded-md border border-dashed border-slate-200 py-1 text-xs text-slate-400 hover:bg-slate-50"
                                    onClick={() => onAdd(iso)}
                                >
                                    +
                                </button>
                            </div>
                        </div>
                    )
                })}
            </div>
        )
    }

    // 竖版
    return (
        <div className="space-y-3">
            {days.map((d) => {
                const iso = toISO(d)
                const dayEntries = entriesOf(entries, iso)
                return (
                    <DayBlock
                        key={iso} date={d} dayEntries={dayEntries}
                        onComplete={onComplete} onDelete={onDelete} onAdd={onAdd}
                    />
                )
            })}
        </div>
    )
}

// ── 天视图: 按早/午/晚/加餐分 block ──
const MEAL_SECTIONS = [
    { type: 'breakfast', labelKey: 'meal.breakfast' },
    { type: 'lunch', labelKey: 'meal.lunch' },
    { type: 'dinner', labelKey: 'meal.dinner' },
    { type: 'snack', labelKey: 'meal.snack' },
]

function DayView({ date, entries, onComplete, onDelete, onAdd }) {
    const { t } = useTranslation()
    const iso = toISO(date)
    const dayEntries = entriesOf(entries, iso)

    return (
        <div className="space-y-4">
            {MEAL_SECTIONS.map((sec) => {
                const secEntries = dayEntries.filter((e) => e.meal_type === sec.type)
                // 加餐没内容就不显示(早午晚始终显示)
                if (sec.type === 'snack' && secEntries.length === 0) return null
                return (
                    <div key={sec.type} className="rounded-xl border border-slate-200 bg-white p-4">
                        <div className="mb-3 flex items-center justify-between">
                            <h3 className="font-semibold text-slate-800">{t(sec.labelKey)}</h3>
                            <button
                                className="text-sm text-slate-400 hover:text-slate-700"
                                onClick={() => onAdd(iso)}
                            >
                                {t('mealPlans.add')}
                            </button>
                        </div>
                        {secEntries.length === 0 ? (
                            <p className="py-2 text-center text-sm text-slate-300">{t('mealPlans.noneScheduled')}</p>
                        ) : (
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                {secEntries.map((e) => (
                                    <MealEntryCard key={e.id} entry={e} onComplete={onComplete} onDelete={onDelete} />
                                ))}
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}

// 一天的块(周竖版 + 天视图共用)
function DayBlock({ date, dayEntries, big, onComplete, onDelete, onAdd }) {
    const { t } = useTranslation()
    const iso = toISO(date)
    return (
        <div className={`rounded-xl border bg-white p-4 ${isToday(date) ? 'border-slate-900' : 'border-slate-200'
            }`}>
            <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-800">{weekdayLabel(date)}</span>
                    <span className="text-sm text-slate-400">{shortDate(date)}</span>
                    {isToday(date) && (
                        <span className="rounded-full bg-slate-900 px-2 py-0.5 text-xs text-white">{t('mealPlans.today')}</span>
                    )}
                </div>
                <button className="text-sm text-slate-400 hover:text-slate-700" onClick={() => onAdd(iso)}>
                    {t('mealPlans.planMeal')}
                </button>
            </div>
            {dayEntries.length === 0 ? (
                <p className="py-2 text-center text-sm text-slate-300">{t('mealPlans.noneThisDay')}</p>
            ) : (
                <div className={`grid grid-cols-1 gap-2 ${big ? 'sm:grid-cols-2' : 'sm:grid-cols-2 lg:grid-cols-3'}`}>
                    {dayEntries.map((e) => (
                        <MealEntryCard key={e.id} entry={e} onComplete={onComplete} onDelete={onDelete} />
                    ))}
                </div>
            )}
        </div>
    )
}

function State({ text }) {
    return <div className="flex h-48 items-center justify-center text-slate-400">{text}</div>
}
