// src/components/shopping/CheckoutDialog.jsx
// 结算: 列出勾选买的项, 每样分配储存区(默认冷藏), 一次性逐个 purchase 回流。
import { useState } from 'react'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

const ZONES = [
    { value: 'fridge', label: '冷藏' },
    { value: 'pantry', label: '常温' },
    { value: 'freezer', label: '冷冻' },
    { value: '', label: '未指定' },
]

// checkoutItems: [{ item, name, amount }] —— 勾选且填了量的
export function CheckoutDialog({ open, listId, checkoutItems, onClose, onDone }) {
    const { call } = useApi()
    const [locations, setLocations] = useState({})   // itemId → location
    const [expires, setExpires] = useState({})       // itemId → expires_at(可选)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    function setLoc(itemId, loc) {
        setLocations((prev) => ({ ...prev, [itemId]: loc }))
    }
    function setExp(itemId, val) {
        setExpires((prev) => ({ ...prev, [itemId]: val }))
    }

    async function checkout() {
        try {
            setSubmitting(true)
            setError(null)
            // 逐个 purchase(前端组织批量; 后端是逐项端点)
            for (const { item, amount } of checkoutItems) {
                const loc = locations[item.id] ?? 'fridge'   // 默认冷藏
                await call(
                    api.patch,
                    `/shopping-lists/${listId}/items/${item.id}/purchase`,
                    {
                        body: {
                            purchased_amount: Number(amount),
                            purchased_unit: 'g',
                            location: loc || null,   // 空字符串→null(未指定)
                            expires_at: expires[item.id] || null,
                        },
                    },
                )
            }
            onDone?.()
            onClose?.()
        } catch (e) {
            setError(e.message || '结算失败(部分可能已处理)')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>结算 · 分配储存区</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <p className="text-sm text-slate-500">
                        这些将回流入库,请为每样选择储存区(默认冷藏):
                    </p>
                    <div className="max-h-80 space-y-2 overflow-y-auto">
                        {checkoutItems.map(({ item, name, amount }) => (
                            <div key={item.id} className="rounded-lg border border-slate-200 p-3">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="truncate font-medium text-slate-900">{name}</div>
                                        <div className="text-xs text-slate-400">{amount}g</div>
                                    </div>
                                    <select
                                        className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                                        value={locations[item.id] ?? 'fridge'}
                                        onChange={(e) => setLoc(item.id, e.target.value)}
                                    >
                                        {ZONES.map((z) => (
                                            <option key={z.value} value={z.value}>{z.label}</option>
                                        ))}
                                    </select>
                                </div>
                                {/* 过期日(可选, 默认无, 可之后在库存页补) */}
                                <div className="mt-2 flex items-center gap-2">
                                    <span className="text-xs text-slate-400">过期日(可选)</span>
                                    <input
                                        type="date"
                                        className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                                        value={expires[item.id] || ''}
                                        onChange={(e) => setExp(item.id, e.target.value)}
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                    {error && <p className="text-sm text-red-500">{error}</p>}
                    <button
                        className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={checkout}
                        disabled={submitting}
                    >
                        {submitting ? '结算中…' : `确认结算 (${checkoutItems.length} 项)`}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}