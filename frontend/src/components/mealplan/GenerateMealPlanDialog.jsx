// src/components/mealplan/GenerateMealPlanDialog.jsx
// AI 生成周计划: 填 天数/餐段/偏好 → POST /meal-plans/generate → AI 从已有菜谱排布
import { Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

// 餐段: value 存后端, labelKey 显示
const MEAL_OPTIONS = [
    { value: 'breakfast', labelKey: 'meal.breakfast' },
    { value: 'lunch', labelKey: 'meal.lunch' },
    { value: 'dinner', labelKey: 'meal.dinner' },
]

export function GenerateMealPlanDialog({ defaultStart, onGenerated }) {
    const { t } = useTranslation()
    const { call } = useApi()
    const [open, setOpen] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    const [days, setDays] = useState(7)
    const [meals, setMeals] = useState(['lunch', 'dinner'])
    const [startDate, setStartDate] = useState(defaultStart || '')
    const [freeText, setFreeText] = useState('')

    function toggleMeal(m) {
        setMeals((prev) =>
            prev.includes(m) ? prev.filter((x) => x !== m) : [...prev, m],
        )
    }

    function reset() {
        setDays(7); setMeals(['lunch', 'dinner'])
        setStartDate(defaultStart || ''); setFreeText(''); setError(null)
    }

    async function generate() {
        if (meals.length === 0) { setError(t('mealPlans.errPickMeal')); return }
        try {
            setSubmitting(true)
            setError(null)
            const body = { days: Number(days), meals }
            if (startDate) body.start_date = startDate
            if (freeText.trim()) body.free_text = freeText.trim()

            await call(api.post, '/meal-plans/generate', { body })
            reset()
            setOpen(false)
            onGenerated?.()
        } catch (e) {
            if (e.status === 400) {
                setError(t('mealPlans.errNoRecipes'))
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
                    <Sparkles className="h-4 w-4" />
                    {t('mealPlans.aiPlan')}
                </span>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-amber-500" />
                        {t('mealPlans.aiPlan')}
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    <p className="text-sm text-slate-500">
                        {t('mealPlans.aiDesc')}
                    </p>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">{t('mealPlans.days')}</label>
                            <input
                                type="number" min="1" max="14"
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                value={days}
                                onChange={(e) => setDays(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">{t('mealPlans.startDate')}</label>
                            <input
                                type="date"
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                value={startDate}
                                onChange={(e) => setStartDate(e.target.value)}
                            />
                        </div>
                    </div>

                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">{t('mealPlans.mealSlot')}</label>
                        <div className="flex gap-2">
                            {MEAL_OPTIONS.map((m) => (
                                <button
                                    key={m.value}
                                    className={`rounded-md border px-3 py-1.5 text-sm ${meals.includes(m.value)
                                            ? 'border-slate-900 bg-slate-900 text-white'
                                            : 'border-slate-300 text-slate-600 hover:bg-slate-50'
                                        }`}
                                    onClick={() => toggleMeal(m.value)}
                                >
                                    {t(m.labelKey)}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">{t('mealPlans.notesOptional')}</label>
                        <input
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            placeholder={t('mealPlans.notesPh')}
                            value={freeText}
                            onChange={(e) => setFreeText(e.target.value)}
                        />
                    </div>

                    {error && <p className="text-sm text-red-500">{error}</p>}

                    <button
                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={generate}
                        disabled={submitting}
                    >
                        {submitting ? (
                            <><Sparkles className="h-4 w-4 animate-pulse" /> {t('mealPlans.generating')}</>
                        ) : (
                            <><Sparkles className="h-4 w-4" /> {t('recipes.generateStart')}</>
                        )}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
