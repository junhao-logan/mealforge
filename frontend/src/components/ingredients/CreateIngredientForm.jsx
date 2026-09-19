// src/components/ingredients/CreateIngredientForm.jsx
// 创建食物(A2): 选单位 + 填"每 N 单位"的营养 → POST /ingredients。
// 作为视图嵌进现有弹窗(加库存 / 手动创建菜谱), 不是独立 Dialog(避免嵌套弹窗)。
import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { FOOD_UNITS, defaultBasisFor, unitLabel } from '@/lib/units'

export function CreateIngredientForm({ initialName = '', onCreated, onCancel }) {
    const { t } = useTranslation()
    const { call } = useApi()
    const [name, setName] = useState(initialName)
    const [unit, setUnit] = useState('g')
    const [basis, setBasis] = useState(String(defaultBasisFor('g')))
    const [cal, setCal] = useState('')
    const [protein, setProtein] = useState('')
    const [carbs, setCarbs] = useState('')
    const [fat, setFat] = useState('')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    function changeUnit(u) {
        setUnit(u)
        setBasis(String(defaultBasisFor(u)))   // 换单位时重置基准量默认值
    }

    async function submit() {
        if (!name.trim()) { setError(t('ingredient.errName')); return }
        if (!basis || Number(basis) <= 0) { setError(t('ingredient.errBasis')); return }
        try {
            setSubmitting(true)
            setError(null)
            const num = (v) => (v === '' ? null : Number(v))
            const created = await call(api.post, '/ingredients', {
                body: {
                    name: name.trim(),
                    nutrition_basis_unit: unit,
                    nutrition_basis_amount: Number(basis),
                    per_100g_calories: num(cal),
                    per_100g_protein: num(protein),
                    per_100g_carbs: num(carbs),
                    per_100g_fat: num(fat),
                },
            })
            onCreated?.(created)
        } catch (e) {
            setError(e.message || t('recipes.errCreate'))
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="space-y-4">
            <button
                type="button"
                className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"
                onClick={onCancel}
            >
                <ArrowLeft className="h-4 w-4" /> {t('common.back')}
            </button>

            <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">{t('ingredient.name')}</label>
                <input
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    placeholder={t('ingredient.namePh')}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                />
            </div>

            {/* 营养基准: 每 [basis] [unit] */}
            <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">
                    {t('ingredient.nutritionPer', { basis: basis || '?', unit: unitLabel(unit) })}
                </label>
                <div className="mb-2 flex items-center gap-2 text-sm">
                    <span className="text-slate-500">{t('ingredient.per')}</span>
                    <input
                        type="number"
                        className="w-20 rounded-md border border-slate-300 px-2 py-1.5"
                        value={basis}
                        onChange={(e) => setBasis(e.target.value)}
                    />
                    <select
                        className="rounded-md border border-slate-300 px-2 py-1.5"
                        value={unit}
                        onChange={(e) => changeUnit(e.target.value)}
                    >
                        {FOOD_UNITS.map((u) => (
                            <option key={u.value} value={u.value}>{unitLabel(u.value)}</option>
                        ))}
                    </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                    <NutInput label={t('ingredient.calories')} value={cal} onChange={setCal} />
                    <NutInput label={t('ingredient.protein')} value={protein} onChange={setProtein} />
                    <NutInput label={t('ingredient.carbs')} value={carbs} onChange={setCarbs} />
                    <NutInput label={t('ingredient.fat')} value={fat} onChange={setFat} />
                </div>
                <p className="mt-1 text-xs text-slate-400">{t('ingredient.hint')}</p>
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}

            <button
                className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                onClick={submit}
                disabled={submitting}
            >
                {submitting ? t('recipes.creating') : t('ingredient.createFood')}
            </button>
        </div>
    )
}

function NutInput({ label, value, onChange }) {
    return (
        <div>
            <label className="mb-1 block text-xs text-slate-500">{label}</label>
            <input
                type="number"
                className="w-full rounded-md border border-slate-300 px-2 py-1.5 text-sm"
                placeholder="—"
                value={value}
                onChange={(e) => onChange(e.target.value)}
            />
        </div>
    )
}
