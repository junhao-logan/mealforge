// src/pages/ShoppingPage.jsx —— 采购(清单管理 + 缺口预览带加入清单)
// A8: 同一食材的自动 + 手动项合成一行; 缺口预览扣掉「已在清单」的在途量; 数量按食材规范单位显示。
import { AlertTriangle, Check, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { CheckoutDialog } from '@/components/shopping/CheckoutDialog'
import { Card } from '@/components/ui/card'
import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { toISO } from '@/lib/dateRange'
import { fmtAmount } from '@/lib/inventoryView'
import { groupListItems } from '@/lib/shoppingView'
import { unitLabel } from '@/lib/units'

export function ShoppingPage() {
    const { t } = useTranslation()
    const [tab, setTab] = useState('lists')   // 默认清单页

    return (
        <div>
            <h1 className="mb-6 text-2xl font-bold text-slate-900">{t('shopping.title')}</h1>

            <div className="mb-4 flex gap-1 border-b border-slate-200">
                <TabButton active={tab === 'lists'} onClick={() => setTab('lists')}>
                    {t('shopping.tabLists')}
                </TabButton>
                <TabButton active={tab === 'preview'} onClick={() => setTab('preview')}>
                    {t('shopping.tabPreview')}
                </TabButton>
            </div>

            {tab === 'lists' ? <ShoppingLists /> : <ShortfallPreview />}
        </div>
    )
}

function TabButton({ active, onClick, children }) {
    return (
        <button
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${active ? 'border-slate-900 text-slate-900'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
            onClick={onClick}
        >
            {children}
        </button>
    )
}

// ═══ 采购清单(第一页) ═══
function ShoppingLists() {
    const { t } = useTranslation()
    const { call } = useApi()
    const [lists, setLists] = useState([])
    const [activeId, setActiveId] = useState(null)
    const [detail, setDetail] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [generating, setGenerating] = useState(false)
    // 勾选状态: 代表行 itemId → {checked, amount}
    const [checkout, setCheckout] = useState({})
    const [showCheckout, setShowCheckout] = useState(false)

    const loadLists = useCallback(async () => {
        try {
            setError(null)
            const data = await call(api.get, '/shopping-lists')
            setLists(data || [])
            // 默认选第一个(函数式更新: 不依赖 activeId, 切换清单时不会重新拉整个列表)
            if (data?.length > 0) setActiveId((prev) => prev ?? data[0].id)
        } catch (e) {
            setError(e.message || t('common.loadFailed'))
        } finally {
            setLoading(false)
        }
    }, [call, t])

    const loadDetail = useCallback(async (id) => {
        if (!id) { setDetail(null); return }
        try {
            const d = await call(api.get, `/shopping-lists/${id}`)
            setDetail(d)
        } catch (e) {
            setError(e.message || t('shopping.errLoadList'))
        }
    }, [call, t])

    useEffect(() => { loadLists() }, [loadLists])
    useEffect(() => { loadDetail(activeId) }, [activeId, loadDetail])

    // 生成清单(未来7天缺口, 已在其他清单里的不会重复加)
    async function generate() {
        try {
            setGenerating(true)
            const today = new Date()
            const end = new Date(today); end.setDate(today.getDate() + 6)
            const created = await call(api.post, '/shopping-lists', {
                body: { start_date: toISO(today), end_date: toISO(end) },
            })
            await loadLists()
            setActiveId(created.id)
        } catch (e) {
            alert(e.message || t('shopping.errGenerate'))
        } finally {
            setGenerating(false)
        }
    }

    async function regenerate() {
        if (!activeId) return
        try {
            await call(api.post, `/shopping-lists/${activeId}/regenerate`)
            await loadDetail(activeId)
        } catch (e) {
            alert(e.message || t('shopping.errRegenerate'))
        }
    }

    async function deleteList() {
        if (!activeId || !confirm(t('shopping.confirmDeleteList'))) return
        try {
            await call(api.del, `/shopping-lists/${activeId}`)
            setActiveId(null)
            await loadLists()
        } catch (e) {
            alert(e.message || t('common.deleteFailed'))
        }
    }

    if (loading) return <State text={t('common.loading')} />
    if (error) return <State text={t('common.errorPrefix', { msg: error })} />

    const rows = detail ? groupListItems(detail.items) : []

    return (
        <div>
            {/* 清单选择 + 生成 */}
            <div className="mb-4 flex flex-wrap items-center gap-2">
                {lists.map((l) => (
                    <button
                        key={l.id}
                        className={`rounded-full px-3 py-1 text-sm ${activeId === l.id ? 'bg-slate-900 text-white'
                                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                            }`}
                        onClick={() => setActiveId(l.id)}
                    >
                        {l.name || t('shopping.listFallback', { date: l.forecast_start || '' })}
                    </button>
                ))}
                <button
                    className="flex items-center gap-1 rounded-full bg-slate-900 px-3 py-1 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
                    onClick={generate}
                    disabled={generating}
                >
                    <Plus className="h-3.5 w-3.5" />
                    {generating ? t('shopping.generating') : t('shopping.generateList')}
                </button>
            </div>

            {lists.length === 0 && (
                <State text={t('shopping.noLists')} />
            )}

            {/* 清单详情 */}
            {detail && (
                <div>
                    <div className="mb-3 flex items-center justify-between">
                        <div className="text-sm text-slate-500">
                            {t('shopping.rangeCount', {
                                start: detail.forecast_start,
                                end: detail.forecast_end,
                                count: rows.length,
                            })}
                        </div>
                        <div className="flex gap-2">
                            <button
                                className="flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
                                onClick={regenerate}
                            >
                                <RefreshCw className="h-3.5 w-3.5" /> {t('shopping.regenerate')}
                            </button>
                            <button
                                className="flex items-center gap-1 rounded-md border border-red-200 px-2.5 py-1 text-xs text-red-600 hover:bg-red-50"
                                onClick={deleteList}
                            >
                                <Trash2 className="h-3.5 w-3.5" /> {t('shopping.deleteList')}
                            </button>
                        </div>
                    </div>

                    {rows.length === 0 ? (
                        <State text={t('shopping.listEmpty')} />
                    ) : (
                        <>
                            <div className="space-y-2">
                                {rows.map((row) => (
                                    <ShoppingItemRow
                                        key={row.key}
                                        row={row}
                                        state={checkout[row.rep.id]}
                                        onToggle={(checked) => setCheckout((p) => ({
                                            ...p,
                                            [row.rep.id]: {
                                                checked,
                                                amount: p[row.rep.id]?.amount
                                                    ?? (row.needed ? String(Number(row.needed.toFixed(2))) : ''),
                                            },
                                        }))}
                                        onAmount={(amount) => setCheckout((p) => ({
                                            ...p, [row.rep.id]: { checked: p[row.rep.id]?.checked ?? true, amount },
                                        }))}
                                    />
                                ))}
                            </div>

                            {/* 结算按钮: 有勾选才显示 */}
                            {selectedCount(rows, checkout) > 0 && (
                                <button
                                    className="mt-4 w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
                                    onClick={() => setShowCheckout(true)}
                                >
                                    {t('shopping.checkout', { count: selectedCount(rows, checkout) })}
                                </button>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* 结算弹窗 */}
            {detail && (
                <CheckoutDialog
                    open={showCheckout}
                    listId={activeId}
                    checkoutItems={buildCheckoutItems(rows, checkout, t)}
                    onClose={() => setShowCheckout(false)}
                    onDone={() => { setCheckout({}); loadDetail(activeId) }}
                    onPartial={(doneIds) => {
                        setCheckout((p) => {
                            const next = { ...p }
                            for (const id of doneIds) delete next[id]
                            return next
                        })
                        loadDetail(activeId)
                    }}
                />
            )}
        </div>
    )
}

// 清单一行(可能是合并的多条): 勾选 + 输入实际购买量; 已购的显示状态
function ShoppingItemRow({ row, state, onToggle, onAmount }) {
    const { t } = useTranslation()
    const name = row.name || t('mealPlans.unnamed')
    const amt = (v) => fmtAmount(v, row.unit)

    if (row.purchased) {
        return (
            <Card className="flex items-center justify-between border-green-200 bg-green-50 p-3">
                <div className="flex items-center gap-3">
                    <Check className="h-5 w-5 text-green-600" />
                    <span className="font-medium text-slate-900">{name}</span>
                </div>
                <span className="text-sm text-green-600">
                    {row.purchasedAmt ? t('shopping.bought', { amount: amt(row.purchasedAmt) }) : ''}
                </span>
            </Card>
        )
    }
    const checked = state?.checked || false
    return (
        <Card className="flex items-center justify-between gap-3 p-3">
            <label className="flex flex-1 flex-wrap items-center gap-x-3 gap-y-1">
                <input
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-300"
                    checked={checked}
                    onChange={(e) => onToggle(e.target.checked)}
                />
                <span className="font-medium text-slate-900">{name}</span>
                {row.needed > 0 && (
                    <span className="text-sm text-slate-400">{t('shopping.need', { amount: amt(row.needed) })}</span>
                )}
                {/* 自动 + 手动合并的行, 标出各自多少 */}
                {row.merged && (
                    <span className="text-xs text-slate-400">
                        ({t('shopping.sourceAuto', { amount: amt(row.autoAmt) })} + {t('shopping.sourceManual', { amount: amt(row.manualAmt) })})
                    </span>
                )}
            </label>
            {/* 勾选后可填实际买入量 */}
            {checked && (
                <div className="flex items-center gap-1">
                    <input
                        type="number" min="0" step="any"
                        className="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm"
                        placeholder={t('shopping.buyAmountPh')}
                        value={state?.amount ?? ''}
                        onChange={(e) => onAmount(e.target.value)}
                    />
                    <span className="text-sm text-slate-400">{unitLabel(row.unit)}</span>
                </div>
            )}
        </Card>
    )
}

// 勾选且填了量的行数
function selectedCount(rows, checkout) {
    return rows.filter(
        (r) => !r.purchased && checkout[r.rep.id]?.checked && Number(checkout[r.rep.id]?.amount) > 0,
    ).length
}

// 组织结算数据: 每个显示行只提交代表行(后端会关掉同食材兄弟行)
function buildCheckoutItems(rows, checkout, t) {
    return rows
        .filter((r) => !r.purchased && checkout[r.rep.id]?.checked && Number(checkout[r.rep.id]?.amount) > 0)
        .map((r) => ({
            item: r.rep,
            name: r.name || t('mealPlans.unnamed'),
            unit: r.unit,
            amount: checkout[r.rep.id].amount,
        }))
}

// ═══ 缺口预览(第二页)带加入清单 ═══
function ShortfallPreview() {
    const { t } = useTranslation()
    const { call } = useApi()
    const [items, setItems] = useState([])
    const [lists, setLists] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [addTarget, setAddTarget] = useState(null)   // 正在加入的缺口项

    const reload = useCallback(async () => {
        try {
            setError(null)
            const [preview, listData] = await Promise.all([
                call(api.get, '/shopping-lists/preview'),
                call(api.get, '/shopping-lists'),
            ])
            setItems(preview || [])
            setLists(listData || [])
        } catch (e) {
            setError(e.message || t('common.loadFailed'))
        } finally {
            setLoading(false)
        }
    }, [call, t])

    useEffect(() => { reload() }, [reload])

    if (loading) return <State text={t('shopping.analyzing')} />
    if (error) return <State text={t('common.errorPrefix', { msg: error })} />

    const shortItems = items.filter((it) => Number(it.projected_remaining_grams) < 0)
    const okItems = items.filter((it) => Number(it.projected_remaining_grams) >= 0)
    const nameOf = (it) => it.name || t('inventory.food', { id: it.ingredient_id })

    if (items.length === 0) {
        return <State text={t('shopping.noMeals')} />
    }

    return (
        <div className="space-y-6">
            <p className="text-sm text-slate-500">{t('shopping.previewDesc')}</p>

            {shortItems.length > 0 ? (
                <div className="space-y-2">
                    {shortItems.map((it) => {
                        const amt = (v) => fmtAmount(v, it.unit)
                        const short = -Number(it.projected_remaining_grams)
                        const inList = Number(it.in_list_grams) || 0
                        const toAdd = Number(it.to_add_grams) || 0
                        return (
                            <Card
                                key={it.ingredient_id}
                                className={`flex flex-wrap items-center justify-between gap-2 p-4 ${toAdd > 0
                                    ? 'border-amber-200 bg-amber-50'
                                    : 'border-slate-200 bg-slate-50'}`}
                            >
                                <div className="flex items-center gap-2">
                                    {toAdd > 0
                                        ? <AlertTriangle className="h-4 w-4 text-amber-500" />
                                        : <Check className="h-4 w-4 text-slate-400" />}
                                    <span className="font-medium text-slate-900">{nameOf(it)}</span>
                                </div>
                                <div className="flex flex-wrap items-center gap-3">
                                    <span className="text-sm text-slate-600">
                                        {t('shopping.have', { amount: amt(it.actual_grams) })} ·{' '}
                                        {t('shopping.needAmt', { amount: amt(it.demand_grams) })} ·{' '}
                                        <span className="font-semibold text-amber-700">{t('shopping.shortAmt', { amount: amt(short) })}</span>
                                        {inList > 0 && <> · {t('shopping.inList', { amount: amt(inList) })}</>}
                                    </span>
                                    {toAdd > 0 ? (
                                        <button
                                            className="rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-700 hover:bg-white"
                                            onClick={() => setAddTarget({ ...it, toAdd })}
                                        >
                                            {t('shopping.addToList')}
                                        </button>
                                    ) : (
                                        <span className="rounded-md bg-slate-200 px-2.5 py-1 text-xs text-slate-600">
                                            {t('shopping.alreadyListed')}
                                        </span>
                                    )}
                                </div>
                            </Card>
                        )
                    })}
                </div>
            ) : (
                <Card className="flex items-center gap-2 border-green-200 bg-green-50 p-4 text-sm text-green-700">
                    <Check className="h-4 w-4" /> {t('shopping.enoughStock')}
                </Card>
            )}

            {okItems.length > 0 && (
                <details className="text-sm text-slate-500">
                    <summary className="cursor-pointer">{t('shopping.enoughCount', { count: okItems.length })}</summary>
                    <div className="mt-2 space-y-1">
                        {okItems.map((it) => (
                            <div key={it.ingredient_id} className="flex justify-between px-1">
                                <span>{nameOf(it)}</span>
                                <span className="text-slate-400">{t('shopping.remaining', { amount: fmtAmount(it.projected_remaining_grams, it.unit) })}</span>
                            </div>
                        ))}
                    </div>
                </details>
            )}

            {/* 加入清单弹窗 */}
            <AddToListDialog
                target={addTarget}
                lists={lists}
                name={addTarget ? nameOf(addTarget) : ''}
                onClose={() => setAddTarget(null)}
                onAdded={reload}
            />
        </div>
    )
}

// 缺口项加入清单(可调量, 默认 = 扣掉在途量后还差的); 清单里已有这个食材的手动项时后端会并进去
function AddToListDialog({ target, lists, name, onClose, onAdded }) {
    const { t } = useTranslation()
    const { call } = useApi()
    const [listId, setListId] = useState('')
    const [amount, setAmount] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (target) {
            setListId(String(lists[0]?.id || ''))
            setAmount(String(Number((target.toAdd || 0).toFixed(2))))
            setError(null)
        }
    }, [target, lists])

    async function submit() {
        if (!listId) { setError(t('shopping.errPickList')); return }
        if (!amount || Number(amount) <= 0) { setError(t('inventory.errAmount')); return }
        try {
            setSubmitting(true)
            setError(null)
            await call(api.post, `/shopping-lists/${listId}/items`, {
                body: {
                    ingredient_id: target.ingredient_id,
                    needed_grams: Number(amount),
                    add_to_inventory: true,
                },
            })
            onAdded?.()
            onClose?.()
        } catch (e) {
            setError(e.message || t('shopping.errAdd'))
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={target !== null} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{t('shopping.addToListTitle', { name })}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    {lists.length === 0 ? (
                        <p className="text-sm text-amber-600">
                            {t('shopping.noListsHint')}
                        </p>
                    ) : (
                        <>
                            <div>
                                <label className="mb-1 block text-sm font-medium text-slate-700">{t('shopping.addToList')}</label>
                                <select
                                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                    value={listId}
                                    onChange={(e) => setListId(e.target.value)}
                                >
                                    {lists.map((l) => (
                                        <option key={l.id} value={l.id}>
                                            {l.name || t('shopping.listFallback', { date: l.forecast_start || '' })}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="mb-1 block text-sm font-medium text-slate-700">
                                    {t('inventory.quantityUnit', { unit: unitLabel(target?.unit || 'g') })}
                                </label>
                                <input
                                    type="number" min="0" step="any" autoFocus
                                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                    value={amount}
                                    onChange={(e) => setAmount(e.target.value)}
                                />
                            </div>
                            {error && <p className="text-sm text-red-500">{error}</p>}
                            <button
                                className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                                onClick={submit}
                                disabled={submitting}
                            >
                                {submitting ? t('inventory.adding') : t('shopping.addToList')}
                            </button>
                        </>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    )
}

function State({ text }) {
    return (
        <div className="flex h-48 items-center justify-center px-4 text-center text-slate-400">{text}</div>
    )
}
