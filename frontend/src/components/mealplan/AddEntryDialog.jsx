// src/components/mealplan/AddEntryDialog.jsx
// 手动排餐: 选 plan + 菜谱 + 餐段 → POST /{plan_id}/entries(指定 plan)
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { MEAL_OPTIONS, planLabel } from '@/lib/meals'


export function AddEntryDialog({ open, date, plans, defaultPlanId, defaultMealType, onClose, onAdded }) {
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

    // 每次打开都从干净状态开始; 天视图里从某个餐段点「添加」时, 预选那个餐段
    useEffect(() => {
        if (!open) return
        setVariantId(''); setServings('1'); setError(null)
        setMealType(defaultMealType || 'lunch')
    }, [open, defaultMealType])

    useEffect(() => {
        if (!open) return
        let alive = true
        async function load() {
            try {
                // 列表接口直接带 default_variant_id, 一个请求搞定
                // (原来为每道菜再请求一次详情: 1 + N 个串行请求, 且默认只取前 20 道)
                const list = await call(api.get, '/recipes', { params: { limit: 100 } })
                if (!alive) return
                setRecipes((list || [])
                    .filter((r) => r.default_variant_id)
                    .map((r) => ({ id: r.id, name: r.name, variant_id: r.default_variant_id })))
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
            onAdded?.()
            onClose?.()
        } catch (e) {
            // 注: 以前这里匹配后端中文错误串「超出计划范围」; 后端早已改为自动扩展计划日期范围,
            // 不会再返回这个错误, 分支已删除
            setError(e.message || t('mealPlans.errAddEntry'))
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
                                <option key={p.id} value={p.id}>{planLabel(p, t)}</option>
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
                                {MEAL_OPTIONS.map((m) => (
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
