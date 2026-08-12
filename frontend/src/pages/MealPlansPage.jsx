// src/pages/MealPlansPage.jsx —— 餐计划(第一步: 周视图纵向 + 切换周 + 完成/删除)
//
// 架构预留(扩展点):
//   - viewMode state: 现只 'week', 以后加 'day'/'month' → 加渲染分支 + 切换器选项
//   - 数据层(loadEntries)按日期范围取, 与视图解耦: 天/月视图改 range 即可复用
//   - MealEntryCard 组件所有视图共用
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { AddEntryDialog } from '@/components/mealplan/AddEntryDialog'
import { GenerateMealPlanDialog } from '@/components/mealplan/GenerateMealPlanDialog'
import { MealEntryCard } from '@/components/mealplan/MealEntryCard'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import {
    addDays, isToday, shortDate, toISO, weekdayLabel, weekDays, weekStart,
} from '@/lib/dateRange'

export function MealPlansPage() {
    const { call } = useApi()
    // 扩展点: viewMode 以后加 'day'/'month'
    const [viewMode] = useState('week')
    const [anchor, setAnchor] = useState(() => weekStart(new Date()))  // 当前周锚点
    const [entries, setEntries] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [addDate, setAddDate] = useState(null)   // 手动排餐: 目标日期

    const days = weekDays(anchor)
    const rangeStart = toISO(days[0])
    const rangeEnd = toISO(days[6])

    // 数据层: 按日期范围取所有餐次(与视图解耦)
    const reload = useCallback(async () => {
        try {
            setError(null)
            const data = await call(api.get, '/meal-plans/entries', {
                params: { start: rangeStart, end: rangeEnd },
            })
            setEntries(data || [])
        } catch (e) {
            setError(e.message || '加载失败')
        } finally {
            setLoading(false)
        }
    }, [call, rangeStart, rangeEnd])

    useEffect(() => { reload() }, [reload])

    // 完成 → 扣库存
    async function handleComplete(entry) {
        try {
            const res = await call(
                api.patch,
                `/meal-plans/${entry.plan_id}/entries/${entry.id}/complete`,
            )
            // 短缺提示
            if (res?.shortfalls?.length > 0) {
                alert(`已完成,但库存不足 ${res.shortfalls.length} 样(短缺已记录,可去采购)`)
            }
            await reload()
        } catch (e) {
            alert(e.message || '完成失败')
        }
    }

    async function handleDelete(entry) {
        if (!confirm('确定删除这条餐次?')) return
        try {
            await call(api.del, `/meal-plans/${entry.plan_id}/entries/${entry.id}`)
            await reload()
        } catch (e) {
            alert(e.message || '删除失败')
        }
    }

    return (
        <div>
            {/* 顶部: 标题 + 视图切换器(预留) + AI 生成(下一步) */}
            <div className="mb-6 flex items-center justify-between">
                <h1 className="text-2xl font-bold text-slate-900">餐计划</h1>
                <div className="flex items-center gap-3">
                    {/* 扩展点: 视图切换器。现只"周", 以后加天/月 + 横竖 */}
                    <div className="rounded-lg bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-600">
                        周视图
                    </div>
                    <GenerateMealPlanDialog defaultStart={rangeStart} onGenerated={reload} />
                </div>
            </div>

            {/* 周切换 */}
            <div className="mb-4 flex items-center gap-4">
                <button
                    className="rounded-md p-1 hover:bg-slate-100"
                    onClick={() => setAnchor(addDays(anchor, -7))}
                >
                    <ChevronLeft className="h-5 w-5 text-slate-600" />
                </button>
                <span className="font-medium text-slate-700">
                    {shortDate(days[0])} – {shortDate(days[6])}
                </span>
                <button
                    className="rounded-md p-1 hover:bg-slate-100"
                    onClick={() => setAnchor(addDays(anchor, 7))}
                >
                    <ChevronRight className="h-5 w-5 text-slate-600" />
                </button>
                <button
                    className="ml-2 text-sm text-slate-400 hover:text-slate-600"
                    onClick={() => setAnchor(weekStart(new Date()))}
                >
                    回到本周
                </button>
            </div>

            {loading && <State text="加载中…" />}
            {error && <State text={`出错了: ${error}`} />}
            {!loading && !error && (
                <WeekView
                    days={days}
                    entries={entries}
                    onComplete={handleComplete}
                    onDelete={handleDelete}
                    onAdd={(iso) => setAddDate(iso)}
                />
            )}

            {/* 手动排餐弹窗 */}
            <AddEntryDialog
                open={addDate !== null}
                date={addDate}
                onClose={() => setAddDate(null)}
                onAdded={reload}
            />
        </div>
    )
}

// ── 周视图(纵向按天)。扩展点: 以后 DayView/MonthView 并列 ──
function WeekView({ days, entries, onComplete, onDelete, onAdd }) {
    // 按日期分组
    const byDate = {}
    for (const e of entries) {
        (byDate[e.scheduled_date] ||= []).push(e)
    }

    return (
        <div className="space-y-3">
            {days.map((d) => {
                const iso = toISO(d)
                const dayEntries = byDate[iso] || []
                return (
                    <div
                        key={iso}
                        className={`rounded-xl border bg-white p-4 ${isToday(d) ? 'border-slate-900' : 'border-slate-200'
                            }`}
                    >
                        <div className="mb-3 flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span className="font-semibold text-slate-800">{weekdayLabel(d)}</span>
                                <span className="text-sm text-slate-400">{shortDate(d)}</span>
                                {isToday(d) && (
                                    <span className="rounded-full bg-slate-900 px-2 py-0.5 text-xs text-white">
                                        今天
                                    </span>
                                )}
                            </div>
                            {/* 扩展点: 排餐按钮(下一步接) */}
                            <button
                                className="text-sm text-slate-400 hover:text-slate-700"
                                onClick={() => onAdd(iso)}
                            >
                                + 排餐
                            </button>
                        </div>

                        {dayEntries.length === 0 ? (
                            <p className="py-2 text-center text-sm text-slate-300">这天还没安排</p>
                        ) : (
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                                {dayEntries.map((e) => (
                                    <MealEntryCard
                                        key={e.id}
                                        entry={e}
                                        onComplete={onComplete}
                                        onDelete={onDelete}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}

function State({ text }) {
    return (
        <div className="flex h-48 items-center justify-center text-slate-400">{text}</div>
    )
}