// src/pages/ShoppingPage.jsx —— 采购(清单管理 + 缺口预览带加入清单)
import { AlertTriangle, Check, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { CheckoutDialog } from '@/components/shopping/CheckoutDialog'
import { Card } from '@/components/ui/card'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { toISO } from '@/lib/dateRange'

export function ShoppingPage() {
    const [tab, setTab] = useState('lists')   // 默认清单页
    const [ingredients, setIngredients] = useState({})
    const { call } = useApi()

    // 食材名映射(两个 tab 共用)
    useEffect(() => {
        let alive = true
        call(api.get, '/ingredients', { params: { limit: 100 } })
            .then((ings) => {
                if (!alive) return
                const map = {}
                for (const ing of ings || []) map[ing.id] = ing.name
                setIngredients(map)
            })
            .catch(() => { })
        return () => { alive = false }
    }, [call])

    return (
        <div>
            <h1 className="mb-6 text-2xl font-bold text-slate-900">采购</h1>

            <div className="mb-4 flex gap-1 border-b border-slate-200">
                <TabButton active={tab === 'lists'} onClick={() => setTab('lists')}>
                    采购清单
                </TabButton>
                <TabButton active={tab === 'preview'} onClick={() => setTab('preview')}>
                    缺口预览
                </TabButton>
            </div>

            {tab === 'lists'
                ? <ShoppingLists ingredients={ingredients} />
                : <ShortfallPreview ingredients={ingredients} />}
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
function ShoppingLists({ ingredients }) {
    const { call } = useApi()
    const [lists, setLists] = useState([])
    const [activeId, setActiveId] = useState(null)
    const [detail, setDetail] = useState(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [generating, setGenerating] = useState(false)
    // 勾选状态: itemId → {checked, amount}
    const [checkout, setCheckout] = useState({})
    const [showCheckout, setShowCheckout] = useState(false)

    const loadLists = useCallback(async () => {
        try {
            setError(null)
            const data = await call(api.get, '/shopping-lists')
            setLists(data || [])
            // 默认选第一个
            if (data?.length > 0 && activeId === null) setActiveId(data[0].id)
        } catch (e) {
            setError(e.message || '加载失败')
        } finally {
            setLoading(false)
        }
    }, [call, activeId])

    const loadDetail = useCallback(async (id) => {
        if (!id) { setDetail(null); return }
        try {
            const d = await call(api.get, `/shopping-lists/${id}`)
            setDetail(d)
        } catch (e) {
            setError(e.message || '加载清单失败')
        }
    }, [call])

    useEffect(() => { loadLists() }, [loadLists])
    useEffect(() => { loadDetail(activeId) }, [activeId, loadDetail])

    // 生成清单(未来7天缺口)
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
            alert(e.message || '生成失败')
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
            alert(e.message || '重算失败')
        }
    }

    async function deleteList() {
        if (!activeId || !confirm('删除这个采购清单?')) return
        try {
            await call(api.del, `/shopping-lists/${activeId}`)
            setActiveId(null)
            await loadLists()
        } catch (e) {
            alert(e.message || '删除失败')
        }
    }

    if (loading) return <State text="加载中…" />
    if (error) return <State text={`出错了: ${error}`} />

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
                        {l.name || `清单 ${l.forecast_start || ''}`}
                    </button>
                ))}
                <button
                    className="flex items-center gap-1 rounded-full bg-slate-900 px-3 py-1 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
                    onClick={generate}
                    disabled={generating}
                >
                    <Plus className="h-3.5 w-3.5" />
                    {generating ? '生成中…' : '生成清单(未来7天)'}
                </button>
            </div>

            {lists.length === 0 && (
                <State text="还没有采购清单。点「生成清单」按未来7天缺口自动生成" />
            )}

            {/* 清单详情 */}
            {detail && (
                <div>
                    <div className="mb-3 flex items-center justify-between">
                        <div className="text-sm text-slate-500">
                            {detail.forecast_start} ~ {detail.forecast_end} · {detail.items.length} 项
                        </div>
                        <div className="flex gap-2">
                            <button
                                className="flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-50"
                                onClick={regenerate}
                            >
                                <RefreshCw className="h-3.5 w-3.5" /> 重算缺口
                            </button>
                            <button
                                className="flex items-center gap-1 rounded-md border border-red-200 px-2.5 py-1 text-xs text-red-600 hover:bg-red-50"
                                onClick={deleteList}
                            >
                                <Trash2 className="h-3.5 w-3.5" /> 删除清单
                            </button>
                        </div>
                    </div>

                    {detail.items.length === 0 ? (
                        <State text="这个清单没有条目(库存充足或窗口无排餐)" />
                    ) : (
                        <>
                            <div className="space-y-2">
                                {detail.items.map((item) => (
                                    <ShoppingItemRow
                                        key={item.id}
                                        item={item}
                                        name={ingredients[item.ingredient_id] || item.item_name}
                                        state={checkout[item.id]}
                                        onToggle={(checked) => setCheckout((p) => ({
                                            ...p,
                                            [item.id]: {
                                                checked,
                                                amount: p[item.id]?.amount
                                                    ?? (item.needed_grams ? Number(item.needed_grams).toFixed(0) : ''),
                                            },
                                        }))}
                                        onAmount={(amount) => setCheckout((p) => ({
                                            ...p, [item.id]: { checked: p[item.id]?.checked ?? true, amount },
                                        }))}
                                    />
                                ))}
                            </div>

                            {/* 结算按钮: 有勾选才显示 */}
                            {selectedCount(detail, checkout) > 0 && (
                                <button
                                    className="mt-4 w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800"
                                    onClick={() => setShowCheckout(true)}
                                >
                                    结算 ({selectedCount(detail, checkout)} 项) →
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
                    checkoutItems={buildCheckoutItems(detail, checkout, ingredients)}
                    onClose={() => setShowCheckout(false)}
                    onDone={() => { setCheckout({}); loadDetail(activeId) }}
                />
            )}
        </div>
    )
}

// 清单一行: 勾选 + 输入实际购买量(已购的显示状态)
function ShoppingItemRow({ item, name, state, onToggle, onAmount }) {
    if (item.is_purchased) {
        return (
            <Card className="flex items-center justify-between border-green-200 bg-green-50 p-3">
                <div className="flex items-center gap-3">
                    <Check className="h-5 w-5 text-green-600" />
                    <span className="font-medium text-slate-900">{name || '未命名'}</span>
                </div>
                <span className="text-sm text-green-600">
                    已买 {item.purchased_grams ? `${Number(item.purchased_grams).toFixed(0)}g` : ''}
                </span>
            </Card>
        )
    }
    const checked = state?.checked || false
    return (
        <Card className="flex items-center justify-between gap-3 p-3">
            <label className="flex flex-1 items-center gap-3">
                <input
                    type="checkbox"
                    className="h-5 w-5 rounded border-slate-300"
                    checked={checked}
                    onChange={(e) => onToggle(e.target.checked)}
                />
                <span className="font-medium text-slate-900">{name || '未命名'}</span>
                {item.needed_grams && (
                    <span className="text-sm text-slate-400">需 {Number(item.needed_grams).toFixed(0)}g</span>
                )}
            </label>
            {/* 勾选后可填实际买入量 */}
            {checked && (
                <div className="flex items-center gap-1">
                    <input
                        type="number"
                        className="w-24 rounded-md border border-slate-300 px-2 py-1 text-sm"
                        placeholder="买入量"
                        value={state?.amount ?? ''}
                        onChange={(e) => onAmount(e.target.value)}
                    />
                    <span className="text-sm text-slate-400">g</span>
                </div>
            )}
        </Card>
    )
}

// 勾选且填了量的项数
function selectedCount(detail, checkout) {
    return detail.items.filter(
        (it) => !it.is_purchased && checkout[it.id]?.checked && Number(checkout[it.id]?.amount) > 0,
    ).length
}

// 组织结算数据
function buildCheckoutItems(detail, checkout, ingredients) {
    return detail.items
        .filter((it) => !it.is_purchased && checkout[it.id]?.checked && Number(checkout[it.id]?.amount) > 0)
        .map((it) => ({
            item: it,
            name: ingredients[it.ingredient_id] || it.item_name || '未命名',
            amount: checkout[it.id].amount,
        }))
}

// ═══ 缺口预览(第二页)带加入清单 ═══
function ShortfallPreview({ ingredients }) {
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
            setError(e.message || '加载失败')
        } finally {
            setLoading(false)
        }
    }, [call])

    useEffect(() => { reload() }, [reload])

    if (loading) return <State text="分析未来7天缺口…" />
    if (error) return <State text={`出错了: ${error}`} />

    const shortItems = items.filter((it) => Number(it.projected_remaining_grams) < 0)
    const okItems = items.filter((it) => Number(it.projected_remaining_grams) >= 0)

    if (items.length === 0) {
        return <State text="未来7天没有排餐,无需采购。先去餐计划排餐" />
    }

    return (
        <div className="space-y-6">
            <p className="text-sm text-slate-500">按未来 7 天已排的餐,对比当前库存,预计会缺这些:</p>

            {shortItems.length > 0 ? (
                <div className="space-y-2">
                    {shortItems.map((it) => {
                        const short = -Number(it.projected_remaining_grams)
                        return (
                            <Card
                                key={it.ingredient_id}
                                className="flex items-center justify-between border-amber-200 bg-amber-50 p-4"
                            >
                                <div className="flex items-center gap-2">
                                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                                    <span className="font-medium text-slate-900">
                                        {ingredients[it.ingredient_id] || `食材 #${it.ingredient_id}`}
                                    </span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <span className="text-sm text-slate-600">
                                        有 {Number(it.actual_grams).toFixed(0)}g · 需{' '}
                                        {Number(it.demand_grams).toFixed(0)}g ·{' '}
                                        <span className="font-semibold text-amber-700">缺 {short.toFixed(0)}g</span>
                                    </span>
                                    <button
                                        className="rounded-md border border-slate-300 px-2.5 py-1 text-xs text-slate-700 hover:bg-white"
                                        onClick={() => setAddTarget({ ...it, shortGrams: short })}
                                    >
                                        加入清单
                                    </button>
                                </div>
                            </Card>
                        )
                    })}
                </div>
            ) : (
                <Card className="flex items-center gap-2 border-green-200 bg-green-50 p-4 text-sm text-green-700">
                    <Check className="h-4 w-4" /> 库存充足,未来 7 天的餐都能做,无需采购
                </Card>
            )}

            {okItems.length > 0 && (
                <details className="text-sm text-slate-500">
                    <summary className="cursor-pointer">库存充足的 {okItems.length} 样</summary>
                    <div className="mt-2 space-y-1">
                        {okItems.map((it) => (
                            <div key={it.ingredient_id} className="flex justify-between px-1">
                                <span>{ingredients[it.ingredient_id] || `食材 #${it.ingredient_id}`}</span>
                                <span className="text-slate-400">剩 {Number(it.projected_remaining_grams).toFixed(0)}g</span>
                            </div>
                        ))}
                    </div>
                </details>
            )}

            {/* 加入清单弹窗 */}
            <AddToListDialog
                target={addTarget}
                lists={lists}
                name={addTarget ? ingredients[addTarget.ingredient_id] : ''}
                onClose={() => setAddTarget(null)}
                onAdded={reload}
            />
        </div>
    )
}

// 缺口项加入清单(可调量)
function AddToListDialog({ target, lists, name, onClose, onAdded }) {
    const { call } = useApi()
    const [listId, setListId] = useState('')
    const [amount, setAmount] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (target) {
            setListId(String(lists[0]?.id || ''))
            setAmount(String(target.shortGrams?.toFixed(0) || ''))   // 默认加缺口量
            setError(null)
        }
    }, [target, lists])

    async function submit() {
        if (!listId) { setError('请先选或生成一个清单'); return }
        if (!amount || Number(amount) <= 0) { setError('请填写数量'); return }
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
            setError(e.message || '加入失败')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={target !== null} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>加入采购清单 · {name}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    {lists.length === 0 ? (
                        <p className="text-sm text-amber-600">
                            还没有采购清单,请先去「采购清单」页生成一个。
                        </p>
                    ) : (
                        <>
                            <div>
                                <label className="mb-1 block text-sm font-medium text-slate-700">加入清单</label>
                                <select
                                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                    value={listId}
                                    onChange={(e) => setListId(e.target.value)}
                                >
                                    {lists.map((l) => (
                                        <option key={l.id} value={l.id}>
                                            {l.name || `清单 ${l.forecast_start || ''}`}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="mb-1 block text-sm font-medium text-slate-700">数量 (克)</label>
                                <input
                                    type="number" autoFocus
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
                                {submitting ? '添加中…' : '加入清单'}
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