// src/components/mealplan/AddEntryDialog.jsx
// 手动排餐: 选 plan + 菜谱 + 餐段 → POST /{plan_id}/entries(指定 plan)
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

// 餐段: value 存后端, labelKey 显示
const MEALS = [
    { value: 'breakfast', labelKey: 'meal.breakfast' },
    { value: 'lunch', labelKey: 'meal.lunch' },
    { value: 'dinner', labelKey: 'meal.dinner' },
    { value: 'snack', labelKey: 'meal.snack' },
]

export function AddEntryDialog({ open, date, plans, defaultPlanId, onClose, onAdded }) {
    const { t } = useTranslation()
    const { call } = useApi()
    const [recipes, setRecipes] = useState([])
    const [planId, setPlanId] = useState('')
    const [variantId, setVariantId] = useState('')
    const [mealType, setMealType] = useState('lunch')
    const [servings, setServings] = useState('1')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    // 默认选中的 plan 优先级: ①当前筛选的 → ②default plan(快速记录) → ③第一个 → ④空
    useEffect(() => {
        if (!open) return
        const defaultPlan = plans.find((p) => p.plan_type === 'default')
        setPlanId(String(defaultPlanId || defaultPlan?.id || plans[0]?.id || ''))
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
                if (alive) setError(e.message || t('mealPlans.errLoadRecipes'))
            }
        }
        load()
        return () => { alive = false }
    }, [open, call, t])

    async function submit() {
        if (!planId) { setError(t('mealPlans.errSelectPlan')); return }
        if (!variantId) { setError(t('mealPlans.errSelectRecipe')); return }
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
            // 注: 这里匹配后端返回的中文错误串, 后端本地化前保持不变
            if (e.status === 422 && String(e.message).includes('超出计划范围')) {
                setError(t('mealPlans.errOutOfRange'))
            } else {
                setError(e.message || t('mealPlans.errAddEntry'))
            }
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{t('mealPlans.addEntryTitle', { date })}</DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    {/* 计划 */}
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">{t('mealPlans.addToPlan')}</label>
                        <select
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={planId}
                            onChange={(e) => setPlanId(e.target.value)}
                        >
                            {plans.map((p) => (
                                <option key={p.id} value={p.id}>
                                    {p.plan_type === 'default'
                                        ? t('mealPlans.defaultPlanName')
                                        : (p.name || t('mealPlans.planFallback', { id: p.id }))}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* 菜谱 */}
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">{t('mealPlans.recipe')}</label>
                        <select
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={variantId}
                            onChange={(e) => setVariantId(e.target.value)}
                        >
                            <option value="">{t('mealPlans.selectRecipePh')}</option>
                            {recipes.map((r) => (
                                <option key={r.variant_id} value={r.variant_id}>{r.name}</option>
                            ))}
                        </select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">{t('mealPlans.mealSlot')}</label>
                            <select
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                value={mealType}
                                onChange={(e) => setMealType(e.target.value)}
                            >
                                {MEALS.map((m) => (
                                    <option key={m.value} value={m.value}>{t(m.labelKey)}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">{t('recipes.servings')}</label>
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
                        {submitting ? t('inventory.adding') : t('mealPlans.addToPlan')}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
