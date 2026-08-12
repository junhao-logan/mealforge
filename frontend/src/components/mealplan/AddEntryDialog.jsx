// src/components/mealplan/AddEntryDialog.jsx
// 手动排餐: 某天选菜谱 + 餐段 → quick-log(自动进 default plan, 免管 plan_id)
import { useEffect, useState } from 'react'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

const MEALS = [
    { value: 'breakfast', label: '早餐' },
    { value: 'lunch', label: '午餐' },
    { value: 'dinner', label: '晚餐' },
    { value: 'snack', label: '加餐' },
]

// 受控弹窗: 父组件用 open/date 控制(点某天的+排餐打开)
export function AddEntryDialog({ open, date, onClose, onAdded }) {
    const { call } = useApi()
    const [recipes, setRecipes] = useState([])   // [{id, name, variant_id}]
    const [variantId, setVariantId] = useState('')
    const [mealType, setMealType] = useState('lunch')
    const [servings, setServings] = useState('1')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    // 打开时拉菜谱(含 variant, 排餐要 variant_id)
    useEffect(() => {
        if (!open) return
        let alive = true
        async function load() {
            try {
                const list = await call(api.get, '/recipes')
                if (!alive) return
                // 每个菜谱拉第一个 variant(简化: 用 detail 拿 variant)
                // 先用列表, variant_id 通过 detail 获取
                const withVariants = []
                for (const r of list || []) {
                    const detail = await call(api.get, `/recipes/${r.id}`)
                    const v = detail.variants?.[0]
                    if (v) withVariants.push({ id: r.id, name: r.name, variant_id: v.id })
                }
                if (alive) setRecipes(withVariants)
            } catch (e) {
                if (alive) setError(e.message || '加载菜谱失败')
            }
        }
        load()
        return () => { alive = false }
    }, [open, call])

    async function submit() {
        if (!variantId) { setError('请选择菜谱'); return }
        try {
            setSubmitting(true)
            setError(null)
            await call(api.post, '/meal-plans/quick-log', {
                body: {
                    recipe_variant_id: Number(variantId),
                    meal_type: mealType,
                    servings: Number(servings),
                    scheduled_date: date,
                },
            })
            setVariantId(''); setMealType('lunch'); setServings('1')
            onAdded?.()
            onClose?.()
        } catch (e) {
            setError(e.message || '排餐失败')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>排餐 · {date}</DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">菜谱</label>
                        <select
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={variantId}
                            onChange={(e) => setVariantId(e.target.value)}
                        >
                            <option value="">选择菜谱…</option>
                            {recipes.map((r) => (
                                <option key={r.variant_id} value={r.variant_id}>{r.name}</option>
                            ))}
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">餐段</label>
                            <select
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                value={mealType}
                                onChange={(e) => setMealType(e.target.value)}
                            >
                                {MEALS.map((m) => (
                                    <option key={m.value} value={m.value}>{m.label}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">份数</label>
                            <input
                                type="number" min="1"
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                value={servings}
                                onChange={(e) => setServings(e.target.value)}
                            />
                        </div>
                    </div>

                    {error && <p className="text-sm text-red-500">{error}</p>}

                    <button
                        className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={submit}
                        disabled={submitting}
                    >
                        {submitting ? '添加中…' : '加入计划'}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}