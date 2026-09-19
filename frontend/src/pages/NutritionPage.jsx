// src/pages/NutritionPage.jsx —— 营养目标(身体数据 → 算 TDEE 目标)
import { Target } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { MacroCard } from '@/components/dashboard/MacroCard'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

// value 存后端, labelKey 显示
const SEX = [
    { value: 'male', labelKey: 'nutrition.sexMale' },
    { value: 'female', labelKey: 'nutrition.sexFemale' },
    { value: 'other', labelKey: 'nutrition.sexOther' },
]
const ACTIVITY = [
    { value: 'sedentary', labelKey: 'nutrition.actSedentary' },
    { value: 'light', labelKey: 'nutrition.actLight' },
    { value: 'moderate', labelKey: 'nutrition.actModerate' },
    { value: 'active', labelKey: 'nutrition.actActive' },
    { value: 'very_active', labelKey: 'nutrition.actVeryActive' },
]
const GOALS = [
    { value: 'fat_loss', labelKey: 'nutrition.goalFatLoss' },
    { value: 'muscle_gain', labelKey: 'nutrition.goalMuscleGain' },
    { value: 'maintenance', labelKey: 'nutrition.goalMaintenance' },
]

export function NutritionPage() {
    const { t } = useTranslation()
    const { call } = useApi()
    // 身体数据
    const [height, setHeight] = useState('')
    const [weight, setWeight] = useState('')
    const [age, setAge] = useState('')
    const [sex, setSex] = useState('male')
    const [activity, setActivity] = useState('moderate')
    const [goalType, setGoalType] = useState('maintenance')

    const [goal, setGoal] = useState(null)   // 算出的目标
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(true)

    // 进页读已有目标(若有)
    const loadGoal = useCallback(async () => {
        try {
            const g = await call(api.get, '/users/me/nutrition-goal')
            setGoal(g)
            if (g?.goal_type) setGoalType(g.goal_type)
        } catch {
            // 没设过目标会 404, 正常
        } finally {
            setLoading(false)
        }
    }, [call])

    useEffect(() => { loadGoal() }, [loadGoal])

    async function computeGoal() {
        // 校验
        if (!height || !weight || !age) { setError(t('nutrition.errRequired')); return }
        try {
            setSaving(true)
            setError(null)
            // 1. 先存身体数据
            await call(api.put, '/users/me/body-metrics', {
                body: {
                    height_cm: Number(height),
                    weight_kg: Number(weight),
                    age: Number(age),
                    biological_sex: sex,
                    activity_level: activity,
                },
            })
            // 2. 算目标
            const g = await call(api.post, '/users/me/nutrition-goal/compute', {
                body: { goal_type: goalType },
            })
            setGoal(g)
        } catch (e) {
            setError(e.message || t('nutrition.errCompute'))
        } finally {
            setSaving(false)
        }
    }

    const goalKey = GOALS.find((g) => g.value === goal?.goal_type)?.labelKey

    return (
        <div className="mx-auto max-w-2xl">
            <div className="mb-6 flex items-center gap-2">
                <Target className="h-6 w-6 text-slate-400" />
                <h1 className="text-2xl font-bold text-slate-900">{t('nutrition.title')}</h1>
            </div>

            {/* 已有目标显示 */}
            {!loading && goal && (
                <div className="mb-6">
                    <h2 className="mb-3 font-semibold text-slate-800">
                        {t('nutrition.currentGoal')} · {goalKey ? t(goalKey) : goal.goal_type}
                    </h2>
                    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                        <MacroCard label={t('macro.calories')} unit="kcal"
                            macro={{ consumed: null, target: goal.daily_calories, percent: null }} />
                        <MacroCard label={t('macro.protein')} unit="g"
                            macro={{ consumed: null, target: goal.daily_protein_g, percent: null }} />
                        <MacroCard label={t('macro.carbs')} unit="g"
                            macro={{ consumed: null, target: goal.daily_carbs_g, percent: null }} />
                        <MacroCard label={t('macro.fat')} unit="g"
                            macro={{ consumed: null, target: goal.daily_fat_g, percent: null }} />
                    </div>
                </div>
            )}

            {/* 身体数据表单 */}
            <div className="rounded-xl border border-slate-200 bg-white p-6">
                <h2 className="mb-4 font-semibold text-slate-800">
                    {goal ? t('nutrition.recompute') : t('nutrition.enterMetrics')}
                </h2>
                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <Field label={t('nutrition.height')}>
                            <input type="number" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={height}
                                onChange={(e) => setHeight(e.target.value)} placeholder="170" />
                        </Field>
                        <Field label={t('nutrition.weight')}>
                            <input type="number" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={weight}
                                onChange={(e) => setWeight(e.target.value)} placeholder="65" />
                        </Field>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <Field label={t('nutrition.age')}>
                            <input type="number" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={age}
                                onChange={(e) => setAge(e.target.value)} placeholder="25" />
                        </Field>
                        <Field label={t('nutrition.sex')}>
                            <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={sex} onChange={(e) => setSex(e.target.value)}>
                                {SEX.map((o) => <option key={o.value} value={o.value}>{t(o.labelKey)}</option>)}
                            </select>
                        </Field>
                    </div>
                    <Field label={t('nutrition.activity')}>
                        <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={activity} onChange={(e) => setActivity(e.target.value)}>
                            {ACTIVITY.map((o) => <option key={o.value} value={o.value}>{t(o.labelKey)}</option>)}
                        </select>
                    </Field>
                    <Field label={t('nutrition.goal')}>
                        <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={goalType} onChange={(e) => setGoalType(e.target.value)}>
                            {GOALS.map((o) => <option key={o.value} value={o.value}>{t(o.labelKey)}</option>)}
                        </select>
                    </Field>

                    {error && <p className="text-sm text-red-500">{error}</p>}

                    <button
                        className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={computeGoal}
                        disabled={saving}
                    >
                        {saving ? t('nutrition.computing') : t('nutrition.computeSave')}
                    </button>
                </div>
            </div>

            <p className="mt-4 text-center text-xs text-slate-400">
                {t('nutrition.formulaNote')}
            </p>
        </div>
    )
}

function Field({ label, children }) {
    return (
        <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
            {children}
        </div>
    )
}
