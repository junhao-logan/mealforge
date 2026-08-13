// src/components/inventory/EditInventoryDialog.jsx
// 编辑库存批次: 改数量/过期日/储存区 → PATCH /inventory/{id}(盘点修正)
import { useEffect, useState } from 'react'

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

export function EditInventoryDialog({ item, name, onClose, onSaved }) {
    const { call } = useApi()
    const [quantity, setQuantity] = useState('')
    const [expiresAt, setExpiresAt] = useState('')
    const [location, setLocation] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    // 打开时预填当前值
    useEffect(() => {
        if (item) {
            setQuantity(item.quantity_grams != null ? Number(item.quantity_grams).toFixed(0) : '')
            setExpiresAt(item.expires_at || '')
            setLocation(['fridge', 'freezer', 'pantry'].includes(item.location) ? item.location : '')
            setError(null)
        }
    }, [item])

    async function save() {
        if (quantity === '' || Number(quantity) < 0) { setError('请填写有效数量(可为0)'); return }
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
            setError(e.message || '保存失败')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={item !== null} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>编辑 · {name}</DialogTitle>
                </DialogHeader>
                <div className="space-y-4">
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">数量 (克)</label>
                        <input
                            type="number" min="0" autoFocus
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={quantity}
                            onChange={(e) => setQuantity(e.target.value)}
                        />
                        <p className="mt-1 text-xs text-slate-400">盘点修正当前余量,可填 0(吃完了)。</p>
                    </div>
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">过期日期</label>
                        <input
                            type="date"
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={expiresAt}
                            onChange={(e) => setExpiresAt(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">储存区域</label>
                        <select
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={location}
                            onChange={(e) => setLocation(e.target.value)}
                        >
                            {ZONES.map((z) => (
                                <option key={z.value} value={z.value}>{z.label}</option>
                            ))}
                        </select>
                    </div>
                    {error && <p className="text-sm text-red-500">{error}</p>}
                    <button
                        className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={save}
                        disabled={submitting}
                    >
                        {submitting ? '保存中…' : '保存'}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}