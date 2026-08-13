// src/components/mealplan/AddEntryDialog.jsx
// 手动排餐: 选 plan + 菜谱 + 餐段 → POST /{plan_id}/entries(指定 plan)
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

export function AddEntryDialog({ open, date, plans, defaultPlanId, onClose, onAdded }) {
    const { call } = useApi()
    const [recipes, setRecipes] = useState([])
    const [planId, setPlanId] = useState('')
    const [variantId, setVariantId] = useState('')
    const [mealType, setMealType] = useState('lunch')
    const [servings, setServings] = useState('1')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    // 默认选中当前筛选的 plan(没有则第一个)
    useEffect(() => {
        if (!open) return
        setPlanId(String(defaultPlanId || plans[0]?.id || ''))
    }, [open, defaultPlanId, plans])

    useEffect(() => {
        if (!open) return
        let alive = true
        async function load() {
            try {
                const list = await call(api.get, '/recipes')
                if (!alive) return
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
        if (!planId) { setError('请选择计划'); return }
        if (!variantId) { setError('请选择菜谱'); return }
        try {
            setSubmitting(true)
            setError(null)
            // POST /{plan_id}/entries —— 指定 plan 排餐
            await call(api.post, `/meal-plans/${planId}/entries`, {
                body: {
                    scheduled_date: date,
                    meal_type: mealType,
                    recipe_variant_id: Number(variantId),
                    servings: Number(servings),
                },
            })
            setVariantId(''); setMealType('lunch'); setServings('1')
            onAdded?.()
            onClose?.()
        } catch (e) {
            // add_entry 会校验日期在 plan 范围内; 但新 plan 日期是今天, 排未来餐会 422
            if (e.status === 422 && String(e.message).includes('超出计划范围')) {
                setError('该日期超出所选计划范围。提示: 新建计划后先排今天的餐,范围会自动扩展;或选其他计划。')
            } else {
                setError(e.message || '排餐失败')
            }
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
                    {/* 计划 */}
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">加入计划</label>
                        <select
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={planId}
                            onChange={(e) => setPlanId(e.target.value)}
                        >
                            {plans.map((p) => (
                                <option key={p.id} value={p.id}>{p.name || `计划 #${p.id}`}</option>
                            ))}
                        </select>
                    </div>

                    {/* 菜谱 */}
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