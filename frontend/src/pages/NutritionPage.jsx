// src/pages/NutritionPage.jsx —— 营养目标(身体数据 → 算 TDEE 目标)
import { Target } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { MacroCard } from '@/components/dashboard/MacroCard'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

const SEX = [
    { value: 'male', label: '男' },
    { value: 'female', label: '女' },
    { value: 'other', label: '其他' },
]
const ACTIVITY = [
    { value: 'sedentary', label: '久坐(几乎不运动)' },
    { value: 'light', label: '轻度(每周1-3次)' },
    { value: 'moderate', label: '中等(每周3-5次)' },
    { value: 'active', label: '积极(每周6-7次)' },
    { value: 'very_active', label: '高强度(体力劳动/运动员)' },
]
const GOALS = [
    { value: 'fat_loss', label: '减脂' },
    { value: 'muscle_gain', label: '增肌' },
    { value: 'maintenance', label: '维持' },
]

export function NutritionPage() {
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
        if (!height || !weight || !age) { setError('请填写身高、体重、年龄'); return }
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
            setError(e.message || '计算失败')
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="mx-auto max-w-2xl">
            <div className="mb-6 flex items-center gap-2">
                <Target className="h-6 w-6 text-slate-400" />
                <h1 className="text-2xl font-bold text-slate-900">营养目标</h1>
            </div>

            {/* 已有目标显示 */}
            {!loading && goal && (
                <div className="mb-6">
                    <h2 className="mb-3 font-semibold text-slate-800">
                        当前目标 · {GOALS.find((g) => g.value === goal.goal_type)?.label || goal.goal_type}
                    </h2>
                    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                        <MacroCard label="热量" unit="kcal"
                            macro={{ consumed: null, target: goal.daily_calories, percent: null }} />
                        <MacroCard label="蛋白质" unit="g"
                            macro={{ consumed: null, target: goal.daily_protein_g, percent: null }} />
                        <MacroCard label="碳水" unit="g"
                            macro={{ consumed: null, target: goal.daily_carbs_g, percent: null }} />
                        <MacroCard label="脂肪" unit="g"
                            macro={{ consumed: null, target: goal.daily_fat_g, percent: null }} />
                    </div>
                </div>
            )}

            {/* 身体数据表单 */}
            <div className="rounded-xl border border-slate-200 bg-white p-6">
                <h2 className="mb-4 font-semibold text-slate-800">
                    {goal ? '重新计算' : '填写身体数据'}
                </h2>
                <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="身高 (cm)">
                            <input type="number" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={height}
                                onChange={(e) => setHeight(e.target.value)} placeholder="170" />
                        </Field>
                        <Field label="体重 (kg)">
                            <input type="number" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={weight}
                                onChange={(e) => setWeight(e.target.value)} placeholder="65" />
                        </Field>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="年龄">
                            <input type="number" className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={age}
                                onChange={(e) => setAge(e.target.value)} placeholder="25" />
                        </Field>
                        <Field label="性别">
                            <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={sex} onChange={(e) => setSex(e.target.value)}>
                                {SEX.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                            </select>
                        </Field>
                    </div>
                    <Field label="活动量">
                        <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={activity} onChange={(e) => setActivity(e.target.value)}>
                            {ACTIVITY.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                    </Field>
                    <Field label="目标">
                        <select className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm" value={goalType} onChange={(e) => setGoalType(e.target.value)}>
                            {GOALS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                        </select>
                    </Field>

                    {error && <p className="text-sm text-red-500">{error}</p>}

                    <button
                        className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={computeGoal}
                        disabled={saving}
                    >
                        {saving ? '计算中…' : '计算并保存目标'}
                    </button>
                </div>
            </div>

            <p className="mt-4 text-center text-xs text-slate-400">
                采用 Mifflin-St Jeor 公式计算基础代谢,结合活动量与目标得出每日营养目标。
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