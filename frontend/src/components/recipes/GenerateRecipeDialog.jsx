// src/components/recipes/GenerateRecipeDialog.jsx
// AI 生成菜谱弹窗: 填偏好(全可选) → POST /recipes/generate → AI 从库存现编
import { ChefHat, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

// value 传给后端/AI(保持中文, 供 prompt 使用); labelKey 仅 UI 显示
const GOALS = [
    { value: '', labelKey: 'recipes.goalAny' },
    { value: '高蛋白', labelKey: 'recipes.goalProtein' },
    { value: '减脂', labelKey: 'recipes.goalCut' },
    { value: '增肌', labelKey: 'recipes.goalBulk' },
]

export function GenerateRecipeDialog({ onGenerated }) {
    const { t } = useTranslation()
    const { call } = useApi()
    const [open, setOpen] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    const [freeText, setFreeText] = useState('')
    const [cuisine, setCuisine] = useState('')
    const [goal, setGoal] = useState('')
    const [servings, setServings] = useState('')

    function reset() {
        setFreeText(''); setCuisine(''); setGoal(''); setServings(''); setError(null)
    }

    async function generate() {
        try {
            setSubmitting(true)
            setError(null)
            // 全可选: 只传填了的
            const body = {}
            if (freeText.trim()) body.free_text = freeText.trim()
            if (cuisine.trim()) body.cuisine = cuisine.trim()
            if (goal) body.goal = goal
            if (servings) body.servings = Number(servings)

            const created = await call(api.post, '/recipes/generate', { body })
            reset()
            setOpen(false)
            onGenerated?.(created)   // 通知父组件(切到我的菜谱 + 刷新)
        } catch (e) {
            // 后端: 空库存 400, AI 失败 502
            if (e.status === 400) {
                setError(t('recipes.errEmptyStock'))
            } else if (e.status === 502) {
                setError(t('recipes.errAiDown'))
            } else {
                setError(e.message || t('recipes.errGenerate'))
            }
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) reset() }}>
            <DialogTrigger asChild>
                <span
                    role="button"
                    tabIndex={0}
                    className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                >
                    <ChefHat className="h-4 w-4" />
                    {t('recipes.aiGenerate')}
                </span>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-amber-500" />
                        {t('recipes.aiTitle')}
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    <p className="text-sm text-slate-500">
                        {t('recipes.aiDesc')}
                    </p>

                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">{t('recipes.freeText')}</label>
                        <input
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            placeholder={t('recipes.freeTextPh')}
                            value={freeText}
                            onChange={(e) => setFreeText(e.target.value)}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">{t('recipes.cuisine')}</label>
                            <input
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                placeholder={t('recipes.cuisinePh')}
                                value={cuisine}
                                onChange={(e) => setCuisine(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">{t('recipes.servings')}</label>
                            <input
                                type="number"
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                placeholder={t('recipes.servingsPh')}
                                value={servings}
                                onChange={(e) => setServings(e.target.value)}
                            />
                        </div>
                    </div>

                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">{t('recipes.goal')}</label>
                        <select
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={goal}
                            onChange={(e) => setGoal(e.target.value)}
                        >
                            {GOALS.map((g) => (
                                <option key={g.value} value={g.value}>{t(g.labelKey)}</option>
                            ))}
                        </select>
                    </div>

                    {error && <p className="text-sm text-red-500">{error}</p>}

                    <button
                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={generate}
                        disabled={submitting}
                    >
                        {submitting ? (
                            <>
                                <Sparkles className="h-4 w-4 animate-pulse" />
                                {t('recipes.generating')}
                            </>
                        ) : (
                            <>
                                <Sparkles className="h-4 w-4" />
                                {t('recipes.generateStart')}
                            </>
                        )}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
