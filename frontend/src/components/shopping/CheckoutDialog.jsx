// src/components/shopping/CheckoutDialog.jsx
// 结算: 列出勾选买的项, 每样分配储存区(默认冷藏), 一次性逐个 purchase 回流。
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { fmtAmount } from '@/lib/inventoryView'

// 储存区: value 存后端, labelKey 显示
const ZONES = [
    { value: 'fridge', labelKey: 'inventory.zoneFridge' },
    { value: 'pantry', labelKey: 'inventory.zonePantry' },
    { value: 'freezer', labelKey: 'inventory.zoneFreezer' },
    { value: '', labelKey: 'inventory.zoneUnspecified' },
]

// checkoutItems: [{ item, name, unit, amount }] —— 勾选且填了量的(每个显示行一个代表 item)
export function CheckoutDialog({ open, listId, checkoutItems, onClose, onDone }) {
    const { t } = useTranslation()
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
            for (const { item, unit, amount } of checkoutItems) {
                const loc = locations[item.id] ?? 'fridge'   // 默认冷藏
                await call(
                    api.patch,
                    `/shopping-lists/${listId}/items/${item.id}/purchase`,
                    {
                        body: {
                            purchased_amount: Number(amount),
                            purchased_unit: unit || 'g',   // 食材规范单位(块 / 个 / g)
                            location: loc || null,   // 空字符串→null(未指定)
                            expires_at: expires[item.id] || null,
                        },
                    },
                )
            }
            onDone?.()
            onClose?.()
        } catch (e) {
            setError(e.message || t('shopping.errCheckout'))
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{t('shopping.checkoutTitle')}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <p className="text-sm text-slate-500">
                        {t('shopping.checkoutDesc')}
                    </p>
                    <div className="max-h-80 space-y-2 overflow-y-auto">
                        {checkoutItems.map(({ item, name, unit, amount }) => (
                            <div key={item.id} className="rounded-lg border border-slate-200 p-3">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="min-w-0">
                                        <div className="truncate font-medium text-slate-900">{name}</div>
                                        <div className="text-xs text-slate-400">{fmtAmount(amount, unit)}</div>
                                    </div>
                                    <select
                                        className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                                        value={locations[item.id] ?? 'fridge'}
                                        onChange={(e) => setLoc(item.id, e.target.value)}
                                    >
                                        {ZONES.map((z) => (
                                            <option key={z.value} value={z.value}>{t(z.labelKey)}</option>
                                        ))}
                                    </select>
                                </div>
                                {/* 过期日(可选, 默认无, 可之后在库存页补) */}
                                <div className="mt-2 flex items-center gap-2">
                                    <span className="text-xs text-slate-400">{t('inventory.expiryOptional')}</span>
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
                        {submitting ? t('shopping.checkingOut') : t('shopping.confirmCheckout', { count: checkoutItems.length })}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
