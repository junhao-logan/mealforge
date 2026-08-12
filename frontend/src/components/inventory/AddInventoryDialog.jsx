// src/components/inventory/AddInventoryDialog.jsx
// 加库存弹窗: 选食材 + 数量 + 过期日 + 储存区域 → POST /inventory
import { useState } from 'react'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

const ZONES = [
    { value: 'pantry', label: '常温' },
    { value: 'fridge', label: '冷藏' },
    { value: 'freezer', label: '冷冻' },
]

export function AddInventoryDialog({ ingredients, onAdded }) {
    const { call } = useApi()
    const [open, setOpen] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    // 表单字段
    const [ingredientId, setIngredientId] = useState('')
    const [amount, setAmount] = useState('')
    const [expiresAt, setExpiresAt] = useState('')
    const [location, setLocation] = useState('fridge')

    // ingredients 是 {id: name} 映射, 转成数组供下拉
    const ingredientList = Object.entries(ingredients).map(([id, name]) => ({
        id: Number(id), name,
    }))

    function reset() {
        setIngredientId(''); setAmount(''); setExpiresAt(''); setLocation('fridge')
        setError(null)
    }

    async function handleSubmit() {
        if (!ingredientId) { setError('请选择食材'); return }
        if (!amount || Number(amount) <= 0) { setError('请填写有效数量'); return }
        try {
            setSubmitting(true)
            setError(null)
            await call(api.post, '/inventory', {
                body: {
                    ingredient_id: Number(ingredientId),
                    input_amount: Number(amount),
                    input_unit: 'g',
                    expires_at: expiresAt || null,
                    location,
                },
            })
            reset()
            setOpen(false)
            onAdded?.()   // 通知父组件刷新列表
        } catch (e) {
            setError(e.message || '添加失败')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) reset() }}>
            <DialogTrigger asChild>
                <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800">
                    + 加库存
                </button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>添加库存</DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    {/* 食材 */}
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">食材</label>
                        <select
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={ingredientId}
                            onChange={(e) => setIngredientId(e.target.value)}
                        >
                            <option value="">选择食材…</option>
                            {ingredientList.map((ing) => (
                                <option key={ing.id} value={ing.id}>{ing.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* 数量 */}
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">数量 (克)</label>
                        <input
                            type="number"
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            placeholder="例如 500"
                            value={amount}
                            onChange={(e) => setAmount(e.target.value)}
                        />
                    </div>

                    {/* 过期日 */}
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">过期日期(可选)</label>
                        <input
                            type="date"
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={expiresAt}
                            onChange={(e) => setExpiresAt(e.target.value)}
                        />
                    </div>

                    {/* 储存区域 */}
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
                        onClick={handleSubmit}
                        disabled={submitting}
                    >
                        {submitting ? '添加中…' : '添加'}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}