// src/components/shopping/PurchaseDialog.jsx
// 打勾购买: 入库项填实际购买量 → PATCH purchase(回流库存 I9)
import { useState } from 'react'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

export function PurchaseDialog({ open, listId, item, itemName, onClose, onPurchased }) {
    const { call } = useApi()
    // 默认填 needed_grams(缺多少买多少)
    const [amount, setAmount] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    // 打开时预填 needed_grams
    const defaultAmount = item?.needed_grams ? Number(item.needed_grams).toFixed(0) : ''

    async function submit() {
        const amt = amount || defaultAmount
        // 入库项必填量
        if (item?.add_to_inventory && (!amt || Number(amt) <= 0)) {
            setError('入库项需填实际购买量')
            return
        }
        try {
            setSubmitting(true)
            setError(null)
            await call(
                api.patch,
                `/shopping-lists/${listId}/items/${item.id}/purchase`,
                { body: { purchased_amount: amt ? Number(amt) : null, purchased_unit: 'g' } },
            )
            setAmount('')
            onPurchased?.()
            onClose?.()
        } catch (e) {
            setError(e.message || '标记购买失败')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>标记已买 · {itemName}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    {item?.add_to_inventory ? (
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">
                                实际购买量 (克)
                            </label>
                            <input
                                type="number" autoFocus
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                placeholder={defaultAmount || '例如 500'}
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                            />
                            <p className="mt-1 text-xs text-slate-400">
                                购买后会自动回流到库存(建一个新批次)。
                            </p>
                        </div>
                    ) : (
                        <p className="text-sm text-slate-500">此项不回流库存,直接标记已买。</p>
                    )}
                    {error && <p className="text-sm text-red-500">{error}</p>}
                    <button
                        className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={submit}
                        disabled={submitting}
                    >
                        {submitting ? '处理中…' : '确认已买'}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}