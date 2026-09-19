// src/components/shopping/PurchaseDialog.jsx
// 打勾购买: 入库项填实际购买量 → PATCH purchase(回流库存 I9)
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

export function PurchaseDialog({ open, listId, item, itemName, onClose, onPurchased }) {
    const { t } = useTranslation()
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
            setError(t('shopping.errPurchaseAmount'))
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
            setError(e.message || t('shopping.errPurchase'))
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{t('shopping.purchaseTitle', { name: itemName })}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    {item?.add_to_inventory ? (
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">
                                {t('shopping.actualAmount')}
                            </label>
                            <input
                                type="number" autoFocus
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                placeholder={defaultAmount || t('inventory.quantityPh')}
                                value={amount}
                                onChange={(e) => setAmount(e.target.value)}
                            />
                            <p className="mt-1 text-xs text-slate-400">
                                {t('shopping.purchaseHint')}
                            </p>
                        </div>
                    ) : (
                        <p className="text-sm text-slate-500">{t('shopping.noRestock')}</p>
                    )}
                    {error && <p className="text-sm text-red-500">{error}</p>}
                    <button
                        className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={submit}
                        disabled={submitting}
                    >
                        {submitting ? t('shopping.processing') : t('shopping.confirmBought')}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
