// src/components/mealplan/PlanBar.jsx
// plan 筛选栏: 全部/某plan 切换 + 新建。删除移到选中后的右上角(避免误触)。
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { toISO } from '@/lib/dateRange'

export function PlanBar({ plans, activePlanId, onSelect, onChanged }) {
    const { t } = useTranslation()
    const { call } = useApi()
    const [showCreate, setShowCreate] = useState(false)
    const [newName, setNewName] = useState('')
    const [creating, setCreating] = useState(false)
    const [error, setError] = useState(null)

    async function createPlan() {
        if (!newName.trim()) { setError(t('mealPlans.errPlanName')); return }
        try {
            setCreating(true)
            setError(null)
            const today = toISO(new Date())
            await call(api.post, '/meal-plans', {
                body: { name: newName.trim(), start_date: today, end_date: today },
            })
            setNewName('')
            setShowCreate(false)
            onChanged?.()
        } catch (e) {
            setError(e.message || t('recipes.errCreate'))
        } finally {
            setCreating(false)
        }
    }

    return (
        <div className="mb-4 flex flex-wrap items-center gap-2">
            <button
                className={`rounded-full px-3 py-1 text-sm ${activePlanId === null
                        ? 'bg-slate-900 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                onClick={() => onSelect(null)}
            >
                {t('mealPlans.allPlans')}
            </button>

            {plans.map((p) => (
                <button
                    key={p.id}
                    className={`rounded-full px-3 py-1 text-sm ${activePlanId === p.id
                            ? 'bg-slate-900 text-white'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                    onClick={() => onSelect(p.id)}
                >
                    {p.plan_type === 'default'
                        ? t('mealPlans.defaultPlanName')
                        : (p.name || t('mealPlans.planFallback', { id: p.id }))}
                </button>
            ))}

            <button
                className="flex items-center gap-1 rounded-full border border-dashed border-slate-300 px-3 py-1 text-sm text-slate-500 hover:bg-slate-50"
                onClick={() => setShowCreate(true)}
            >
                <Plus className="h-3.5 w-3.5" /> {t('mealPlans.newPlan')}
            </button>

            <Dialog open={showCreate} onOpenChange={(o) => { setShowCreate(o); if (!o) { setNewName(''); setError(null) } }}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>{t('mealPlans.newPlan')}</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">{t('mealPlans.planName')}</label>
                            <input
                                autoFocus
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                placeholder={t('mealPlans.planNamePh')}
                                value={newName}
                                onChange={(e) => setNewName(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && createPlan()}
                            />
                            <p className="mt-1 text-xs text-slate-400">
                                {t('mealPlans.planHint')}
                            </p>
                        </div>
                        {error && <p className="text-sm text-red-500">{error}</p>}
                        <button
                            className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                            onClick={createPlan}
                            disabled={creating}
                        >
                            {creating ? t('recipes.creating') : t('mealPlans.create')}
                        </button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    )
}

// 删除按钮(选中某plan后显示在右上角)—— 独立导出
export function DeletePlanButton({ plan, onDeleted }) {
    const { t } = useTranslation()
    const { call } = useApi()
    async function del() {
        const planName = plan.name || t('mealPlans.unnamed')
        if (!confirm(t('mealPlans.confirmDeletePlan', { name: planName }))) return
        try {
            await call(api.del, `/meal-plans/${plan.id}`)
            onDeleted?.()
        } catch (e) {
            alert(e.message || t('common.deleteFailed'))
        }
    }
    return (
        <button
            className="rounded-md border border-red-200 px-3 py-1 text-sm text-red-600 hover:bg-red-50"
            onClick={del}
        >
            {t('mealPlans.deletePlan')}
        </button>
    )
}
