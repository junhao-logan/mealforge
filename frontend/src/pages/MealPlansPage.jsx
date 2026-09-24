// src/pages/MealPlansPage.jsx —— 餐计划(天/周视图 + 周横竖 + plan管理 + AI生成)
// AI 草稿(B4.2): 生成后以"闪烁绿虚线"卡片直接铺进视图, 可改份数/删除, 确认才入库;
// 草稿只在本页 state, 切到别的页面组件卸载 → 自动抹掉。
import { ChevronLeft, ChevronRight, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AddEntryDialog } from '@/components/mealplan/AddEntryDialog'
import { GenerateMealPlanDialog } from '@/components/mealplan/GenerateMealPlanDialog'
import { MealEntryCard } from '@/components/mealplan/MealEntryCard'
import { DeletePlanButton, PlanBar } from '@/components/mealplan/PlanBar'
import { useApi } from '@/hooks/useApi'
import { useEntryDelete } from '@/hooks/useEntryDelete'
import { api } from '@/lib/api'
import { reportRestockLosses } from '@/lib/restock'
import { parseDate } from '@/lib/inventoryView'
import { MEAL_OPTIONS, mealLabel } from '@/lib/meals'
import {
    addDays, fullDate, isToday, shortDate, toISO, weekdayLabel, weekDays, weekStart,
} from '@/lib/dateRange'

// 'YYYY-MM-DD' → 本地日期(与库存页共用 inventoryView.parseDate)
const parseISO = parseDate

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
    const [addMeal, setAddMeal] = useState(null)   // 天视图从某餐段点「添加」时预选该餐段
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    // AI 草稿(未确认): {start_date, targetPlanId, entries:[{_key,day_offset,meal_type,...}]}
    const [draft, setDraft] = useState(null)
    const [committing, setCommitting] = useState(false)

    // 当前视图的日期范围
    const isWeek = granularity === 'week'
    const days = weekDays(anchor)
    // 范围字符串直接从 anchor 算, 不从 days 数组取: days 会传给子组件, React Compiler 视其为
    // 「之后可能被修改」, 导致 reload 的 useCallback 无法保留(整个组件跳过编译优化)
    const rangeStart = toISO(isWeek ? weekStart(anchor) : dayAnchor)
    const rangeEnd = toISO(isWeek ? addDays(weekStart(anchor), 6) : dayAnchor)

    const reload = useCallback(async () => {
        try {
            setError(null)
            const [data, planList] = await Promise.all([
                call(api.get, '/meal-plans/entries', {
                    params: { start: rangeStart, end: rangeEnd },
                }),
                call(api.get, '/meal-plans', { params: { limit: 100 } }),   // 默认只取 20 个
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

    // ── AI 草稿处理 ──
    function handleDraft(d, targetPlanId) {
        const es = (d.entries || []).map((e, i) => ({
            ...e, _key: `d${i}`, servings: Number(e.servings) || 1,
        }))
        setDraft({ start_date: d.start_date, targetPlanId, entries: es })
        // 自动跳到草稿起始那周, 保证看得到绿色虚线卡
        setGranularity('week')
        setAnchor(weekStart(parseISO(d.start_date)))
    }

    function onDraftDelete(key) {
        setDraft((prev) => {
            if (!prev) return prev
            const es = prev.entries.filter((e) => e._key !== key)
            return es.length ? { ...prev, entries: es } : null   // 删空 → 清掉草稿
        })
    }

    async function commitDraft() {
        try {
            setCommitting(true)
            const body = {
                start_date: draft.start_date,
                entries: draft.entries.map((e) => {
                    const base = {
                        day_offset: e.day_offset,
                        meal_type: e.meal_type,
                        servings: Number(e.servings) || 1,
                    }
                    return e.is_new
                        ? { ...base, new_recipe: e.new_recipe }        // 现编 → 确认时才落库
                        : { ...base, recipe_variant_id: e.recipe_variant_id }
                }),
            }
            if (draft.targetPlanId) body.target_plan_id = Number(draft.targetPlanId)
            await call(api.post, '/meal-plans/generate/commit', { body })
            setDraft(null)
            await reload()
        } catch (e) {
            alert(e.message || t('mealPlans.errCommit'))
        } finally {
            setCommitting(false)
        }
    }

    // 草稿按日期分组(scheduled_date = start_date + day_offset)
    const draftByDate = {}
    if (draft) {
        const base = parseISO(draft.start_date)
        for (const e of draft.entries) {
            const iso = toISO(addDays(base, e.day_offset))
            ;(draftByDate[iso] = draftByDate[iso] || []).push(e)
        }
    }

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

    async function handleUncomplete(entry) {
        try {
            const res = await call(api.patch, `/meal-plans/${entry.plan_id}/entries/${entry.id}/uncomplete`)
            reportRestockLosses(res, t)
            await reload()
        } catch (e) {
            alert(e.message || t('meal.uncompleteFailed'))
        }
    }

    // A5: 已完成的餐次删除时问要不要退回库存(见 useEntryDelete)
    const { requestDelete, dialog: deleteDialog } = useEntryDelete(reload)
    function handleDelete(entry) {
        requestDelete(entry, t('mealPlans.confirmDeleteEntry'))
    }

    const draftProps = { draftByDate, onDraftDelete }

    return (
        <div className="pb-20">
            {deleteDialog}
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
                    <GenerateMealPlanDialog
                        defaultStart={rangeStart}
                        plans={plans}
                        activePlanId={activePlanId}
                        onDraft={handleDraft}
                    />
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
                {/* 选中某plan时, 右侧显示删除(避免误触); 默认 plan(Quick Log)不可删除, 不显示按钮 */}
                {activePlanId !== null
                    && plans.find((p) => p.id === activePlanId)?.plan_type !== 'default' && (
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
                        onComplete={handleComplete} onUncomplete={handleUncomplete} onDelete={handleDelete}
                        onAdd={(iso, meal) => { setAddDate(iso); setAddMeal(meal || null) }}
                        {...draftProps}
                    />
                ) : (
                    <DayView
                        date={dayAnchor} entries={visibleEntries}
                        onComplete={handleComplete} onUncomplete={handleUncomplete} onDelete={handleDelete}
                        onAdd={(iso, meal) => { setAddDate(iso); setAddMeal(meal || null) }}
                        {...draftProps}
                    />
                )
            )}

            <AddEntryDialog
                open={addDate !== null}
                date={addDate}
                plans={plans}
                defaultPlanId={activePlanId}
                defaultMealType={addMeal}
                onClose={() => setAddDate(null)}
                onAdded={reload}
            />

            {/* 草稿确认条(浮在底部) */}
            {draft && draft.entries.length > 0 && (
                <div className="fixed bottom-6 left-1/2 z-40 flex -translate-x-1/2 items-center gap-3 rounded-full border border-green-300 bg-white px-4 py-2 shadow-lg">
                    <span className="text-sm text-slate-600">
                        {t('mealPlans.draftBar', { count: draft.entries.length })}
                    </span>
                    <button
                        className="rounded-full px-3 py-1 text-sm text-slate-500 hover:bg-slate-100"
                        onClick={() => setDraft(null)}
                        disabled={committing}
                    >
                        {t('mealPlans.discardDraft')}
                    </button>
                    <button
                        className="rounded-full bg-slate-900 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={commitDraft}
                        disabled={committing}
                    >
                        {t('mealPlans.confirmAddPlan', { count: draft.entries.length })}
                    </button>
                </div>
            )}
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

// 一张 AI 草稿卡片: 闪烁绿虚线, 仅删除(未入库; 份数用 AI 排的, 不在此改)
function DraftEntryCard({ entry, onDelete }) {
    const { t } = useTranslation()
    return (
        <div className="animate-pulse rounded-lg border-2 border-dashed border-green-400 bg-green-50 p-2.5 text-sm">
            <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                    <span className="text-xs font-medium text-green-600">
                        {mealLabel(entry.meal_type, t)}
                        {' · '}{t('mealPlans.draftBadge')}
                    </span>
                    <div className="truncate font-medium text-slate-900">
                        {entry.is_new && (
                            <span className="mr-1 rounded bg-amber-100 px-1 py-0.5 text-[10px] font-medium text-amber-700">
                                {t('mealPlans.newRecipeBadge')}
                            </span>
                        )}
                        {entry.recipe_name}
                        {Number(entry.servings) !== 1 && (
                            <span className="ml-1 text-xs text-slate-400">×{Number(entry.servings)}</span>
                        )}
                    </div>
                </div>
                <button
                    className="shrink-0 text-slate-400 hover:text-red-500"
                    onClick={() => onDelete(entry._key)}
                    title={t('common.delete')}
                >
                    <Trash2 className="h-3.5 w-3.5" />
                </button>
            </div>
        </div>
    )
}

// 渲染某天的草稿卡片(可按 meal_type 过滤, 供天视图分区用)
function DraftCards({ list, mealType, onDraftDelete }) {
    const items = mealType ? (list || []).filter((e) => e.meal_type === mealType) : (list || [])
    return items.map((e) => (
        <DraftEntryCard key={e._key} entry={e} onDelete={onDraftDelete} />
    ))
}

// 一天里按日期取该天餐次
function entriesOf(entries, iso) {
    return entries.filter((e) => e.scheduled_date === iso)
}

// ── 周视图: 竖版(每天一块) / 横版(7列并排) ──
function WeekView({ days, entries, orientation, onComplete, onUncomplete, onDelete, onAdd,
    draftByDate, onDraftDelete }) {
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
                                    <MealEntryCard key={e.id} entry={e} onComplete={onComplete} onUncomplete={onUncomplete} onDelete={onDelete} />
                                ))}
                                <DraftCards list={draftByDate[iso]} onDraftDelete={onDraftDelete} />
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
                        key={iso} date={d} dayEntries={dayEntries} draftList={draftByDate[iso]}
                        onComplete={onComplete} onUncomplete={onUncomplete} onDelete={onDelete} onAdd={onAdd}
                        onDraftDelete={onDraftDelete}
                    />
                )
            })}
        </div>
    )
}

// ── 天视图: 按早/午/晚/加餐分 block ──
const MEAL_SECTIONS = MEAL_OPTIONS.map((m) => ({ type: m.value, labelKey: m.labelKey }))

function DayView({ date, entries, onComplete, onUncomplete, onDelete, onAdd,
    draftByDate, onDraftDelete }) {
    const { t } = useTranslation()
    const iso = toISO(date)
    const dayEntries = entriesOf(entries, iso)
    const dayDraft = draftByDate[iso] || []

    return (
        <div className="space-y-4">
            {MEAL_SECTIONS.map((sec) => {
                const secEntries = dayEntries.filter((e) => e.meal_type === sec.type)
                const secDraft = dayDraft.filter((e) => e.meal_type === sec.type)
                // 加餐没内容(且没草稿)就不显示(早午晚始终显示)
                if (sec.type === 'snack' && secEntries.length === 0 && secDraft.length === 0) return null
                return (
                    <div key={sec.type} className="rounded-xl border border-slate-200 bg-white p-4">
                        <div className="mb-3 flex items-center justify-between">
                            <h3 className="font-semibold text-slate-800">{t(sec.labelKey)}</h3>
                            <button
                                className="text-sm text-slate-400 hover:text-slate-700"
                                onClick={() => onAdd(iso, sec.type)}
                            >
                                {t('mealPlans.add')}
                            </button>
                        </div>
                        {secEntries.length === 0 && secDraft.length === 0 ? (
                            <p className="py-2 text-center text-sm text-slate-300">{t('mealPlans.noneScheduled')}</p>
                        ) : (
                            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                                {secEntries.map((e) => (
                                    <MealEntryCard key={e.id} entry={e} onComplete={onComplete} onUncomplete={onUncomplete} onDelete={onDelete} />
                                ))}
                                <DraftCards list={dayDraft} mealType={sec.type} onDraftDelete={onDraftDelete} />
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}

// 一天的块(周竖版 + 天视图共用)
function DayBlock({ date, dayEntries, draftList, big, onComplete, onUncomplete, onDelete, onAdd,
    onDraftDelete }) {
    const { t } = useTranslation()
    const iso = toISO(date)
    const draft = draftList || []
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
            {dayEntries.length === 0 && draft.length === 0 ? (
                <p className="py-2 text-center text-sm text-slate-300">{t('mealPlans.noneThisDay')}</p>
            ) : (
                <div className={`grid grid-cols-1 gap-2 ${big ? 'sm:grid-cols-2' : 'sm:grid-cols-2 lg:grid-cols-3'}`}>
                    {dayEntries.map((e) => (
                        <MealEntryCard key={e.id} entry={e} onComplete={onComplete} onUncomplete={onUncomplete} onDelete={onDelete} />
                    ))}
                    <DraftCards list={draft} onDraftDelete={onDraftDelete} />
                </div>
            )}
        </div>
    )
}

function State({ text }) {
    return <div className="flex h-48 items-center justify-center text-slate-400">{text}</div>
}
