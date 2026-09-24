// src/pages/InventoryPage.jsx —— 库存页(A4)
// 三区展示; 同一区的同一食材合并成一张卡片, 可展开看各批次被哪些餐次预留。
// 预留来自 GET /inventory/reservations(读时模拟 FEFO + 手选, 不落库)。
import { ArrowUpDown } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { AddInventoryDialog } from '@/components/inventory/AddInventoryDialog'
import { EditInventoryDialog } from '@/components/inventory/EditInventoryDialog'
import { IngredientGroupCard } from '@/components/inventory/IngredientGroupCard'
import { MealReservationDialog } from '@/components/inventory/MealReservationDialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { daysUntil, sortKey } from '@/lib/expiry'
import { fmtAmount, groupInventory } from '@/lib/inventoryView'

// 区域: key 用于过滤, labelKey 用于 i18n 显示
const ZONES = [
    { key: 'pantry', labelKey: 'inventory.zonePantry', accent: 'border-t-amber-400' },
    { key: 'fridge', labelKey: 'inventory.zoneFridge', accent: 'border-t-sky-400' },
    { key: 'freezer', labelKey: 'inventory.zoneFreezer', accent: 'border-t-indigo-400' },
]
// 未指定区(灰): location 不在三区(含 null)。采购回流未分区的落这里。
const UNZONED_ZONE = { key: 'unzoned', labelKey: 'inventory.zoneUnzoned', accent: 'border-t-slate-300' }

// 「未预留」排前/排后: 每个浏览器自己记住(纯显示偏好)
const SORT_KEY = 'mf_inv_free_first'
function readFreeFirst() {
    try { return localStorage.getItem(SORT_KEY) !== '0' } catch { return true }
}

export function InventoryPage() {
    const { t } = useTranslation()
    const { call } = useApi()
    const [items, setItems] = useState([])
    const [res, setRes] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [editItem, setEditItem] = useState(null)
    const [mealId, setMealId] = useState(null)
    const [expanded, setExpanded] = useState(() => new Set())
    const [freeFirst, setFreeFirst] = useState(readFreeFirst)

    // 库存批次 + 预留视图, 并行拉。加/删/改/手选后都复用它刷新
    const reload = useCallback(async () => {
        try {
            setError(null)
            const [inv, reservations] = await Promise.all([
                call(api.get, '/inventory'),
                call(api.get, '/inventory/reservations'),
            ])
            setItems(inv || [])
            setRes(reservations)
        } catch (e) {
            setError(e.message || t('common.loadFailed'))
        } finally {
            setLoading(false)
        }
    }, [call, t])

    useEffect(() => { reload() }, [reload])

    const groups = useMemo(() => groupInventory(items, res), [items, res])
    const entriesById = useMemo(
        () => Object.fromEntries((res?.entries || []).map((e) => [e.entry_id, e])),
        [res],
    )
    const shortByIng = useMemo(
        () => Object.fromEntries((res?.shortfalls || []).map((s) => [s.ingredient_id, Number(s.amount)])),
        [res],
    )
    const ingInfo = (id) => res?.ingredients?.[id] || {}
    const nameOf = (id) => ingInfo(id).name || t('inventory.food', { id })

    function toggleExpand(key) {
        setExpanded((prev) => {
            const next = new Set(prev)
            if (next.has(key)) next.delete(key); else next.add(key)
            return next
        })
    }

    function toggleSort() {
        setFreeFirst((v) => {
            try { localStorage.setItem(SORT_KEY, v ? '0' : '1') } catch { /* 存不了就只在本次生效 */ }
            return !v
        })
    }

    async function handleDelete(id) {
        if (!confirm(t('inventory.confirmDelete'))) return
        try {
            await call(api.del, `/inventory/${id}`)
            await reload()
        } catch (e) {
            alert(e.message || t('common.deleteFailed'))
        }
    }

    if (loading) return <PageState text={t('common.loading')} />
    if (error) return <PageState text={t('common.errorPrefix', { msg: error })} />

    const hasUnzoned = groups.some((g) => g.zone === 'unzoned')
    const zones = hasUnzoned ? [...ZONES, UNZONED_ZONE] : ZONES
    const ingredientNames = Object.fromEntries(
        Object.entries(res?.ingredients || {}).map(([id, v]) => [id, v.name]),
    )

    return (
        <div>
            <div className="mb-4 flex items-center justify-between">
                <h1 className="text-2xl font-bold text-slate-900">{t('inventory.title')}</h1>
                <div className="flex items-center gap-2">
                    <button
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
                        onClick={toggleSort}
                    >
                        <ArrowUpDown className="h-4 w-4" />
                        {freeFirst ? t('inventory.sortFreeFirst') : t('inventory.sortFreeLast')}
                    </button>
                    <AddInventoryDialog ingredients={ingredientNames} onAdded={reload} />
                </div>
            </div>

            {/* 缺口提示: 计划中的餐次会缺的食材(含完全没库存的) */}
            {res?.shortfalls?.length > 0 && (
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3">
                    <div className="text-sm text-red-800">
                        <span className="font-medium">{t('inventory.shortfallTitle')}</span>{' '}
                        {res.shortfalls
                            .map((s) => `${nameOf(s.ingredient_id)} ${fmtAmount(s.amount, ingInfo(s.ingredient_id).unit)}`)
                            .join(t('inventory.listSep'))}
                    </div>
                    <Link
                        to="/shopping"
                        className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                    >
                        {t('inventory.goShopping')}
                    </Link>
                </div>
            )}

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {zones.map((zone) => {
                    const zoneGroups = groups
                        .filter((g) => g.zone === zone.key)
                        .sort((a, b) => sortKey(daysUntil(a.earliestExpiry)) - sortKey(daysUntil(b.earliestExpiry)))
                    return (
                        <div key={zone.key} className={`rounded-xl border-t-4 bg-white p-4 shadow-sm ${zone.accent}`}>
                            <div className="mb-3 flex items-center justify-between">
                                <h2 className="font-semibold text-slate-800">{t(zone.labelKey)}</h2>
                                <span className="text-sm text-slate-400">{t('inventory.count', { count: zoneGroups.length })}</span>
                            </div>
                            <div className="space-y-2">
                                {zoneGroups.length === 0 ? (
                                    <p className="py-6 text-center text-sm text-slate-300">{t('inventory.empty')}</p>
                                ) : (
                                    zoneGroups.map((g) => (
                                        <IngredientGroupCard
                                            key={g.key}
                                            group={g}
                                            name={nameOf(g.ingredient_id)}
                                            unit={ingInfo(g.ingredient_id).unit}
                                            shortfall={shortByIng[g.ingredient_id] || 0}
                                            entriesById={entriesById}
                                            expanded={expanded.has(g.key)}
                                            onToggle={() => toggleExpand(g.key)}
                                            freeFirst={freeFirst}
                                            onEdit={setEditItem}
                                            onDelete={handleDelete}
                                            onOpenMeal={setMealId}
                                        />
                                    ))
                                )}
                            </div>
                        </div>
                    )
                })}
            </div>

            {/* 编辑批次 */}
            <EditInventoryDialog
                item={editItem}
                name={editItem ? nameOf(editItem.ingredient_id) : ''}
                unit={editItem ? ingInfo(editItem.ingredient_id).unit : undefined}
                onClose={() => setEditItem(null)}
                onSaved={reload}
            />

            {/* 餐次明细 + 选择批次 */}
            <MealReservationDialog
                entry={mealId != null ? entriesById[mealId] : null}
                reservations={res}
                items={items}
                onClose={() => setMealId(null)}
                onSaved={reload}
            />
        </div>
    )
}

function PageState({ text }) {
    return (
        <div className="flex h-64 items-center justify-center text-slate-400">{text}</div>
    )
}
