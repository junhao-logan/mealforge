// src/components/inventory/EditInventoryDialog.jsx
// 编辑库存批次: 改数量/过期日/储存区 → PATCH /inventory/{id}(盘点修正)
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { unitLabel } from '@/lib/units'

// 储存区: value 存后端, labelKey 显示('' = 未指定)
const ZONES = [
    { value: 'fridge', labelKey: 'inventory.zoneFridge' },
    { value: 'pantry', labelKey: 'inventory.zonePantry' },
    { value: 'freezer', labelKey: 'inventory.zoneFreezer' },
    { value: '', labelKey: 'inventory.zoneUnspecified' },
]

export function EditInventoryDialog({ item, name, unit, onClose, onSaved }) {
    const { t } = useTranslation()
    const { call } = useApi()
    const [quantity, setQuantity] = useState('')
    const [expiresAt, setExpiresAt] = useState('')
    const [location, setLocation] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    // 打开时预填当前值
    useEffect(() => {
        if (item) {
            setQuantity(item.quantity_grams != null ? String(Number(Number(item.quantity_grams).toFixed(2))) : '')
            setExpiresAt(item.expires_at || '')
            setLocation(['fridge', 'freezer', 'pantry'].includes(item.location) ? item.location : '')
            setError(null)
        }
    }, [item])

    async function save() {
        if (quantity === '' || Number(quantity) < 0) { setError(t('inventory.errAmountZero')); return }
        try {
            setSubmitting(true)
            setError(null)
            await call(api.patch, `/inventory/${item.id}`, {
                body: {
                    quantity_grams: Number(quantity),
                    expires_at: expiresAt || null,
                    location: location || null,
                },
            })
            onSaved?.()
            onClose?.()
        } catch (e) {
            setError(e.message || t('common.saveFailed'))
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={item !== null} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{t('inventory.editTitle', { name })}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">{t('inventory.quantityUnit', { unit: unitLabel(unit || 'g') })}</label>
                        <input
                            type="number" min="0" step="any" autoFocus
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={quantity}
                            onChange={(e) => setQuantity(e.target.value)}
                        />
                        <p className="mt-1 text-xs text-slate-400">{t('inventory.editHint')}</p>
                    </div>
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">{t('inventory.expiry')}</label>
                        <input
                            type="date"
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={expiresAt}
                            onChange={(e) => setExpiresAt(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">{t('inventory.storageZone')}</label>
                        <select
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={location}
                            onChange={(e) => setLocation(e.target.value)}
                        >
                            {ZONES.map((z) => (
                                <option key={z.value} value={z.value}>{t(z.labelKey)}</option>
                            ))}
                        </select>
                    </div>
                    {error && <p className="text-sm text-red-500">{error}</p>}
                    <button
                        className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={save}
                        disabled={submitting}
                    >
                        {submitting ? t('common.saving') : t('common.save')}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
