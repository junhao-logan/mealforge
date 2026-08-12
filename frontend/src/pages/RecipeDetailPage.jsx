// src/pages/RecipeDetailPage.jsx —— 菜谱详情(营养 + 配料 + 做法)
import { ArrowLeft, Clock, Flame } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router'

import { Card } from '@/components/ui/card'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

const SOURCE_LABEL = {
    ai_generated: 'AI 生成', ai: 'AI 生成', user: '自建', manual: '手动',
}
const DIFFICULTY_LABEL = { easy: '简单', medium: '中等', hard: '困难' }

export function RecipeDetailPage() {
    const { id } = useParams()
    const navigate = useNavigate()
    const { call } = useApi()
    const [recipe, setRecipe] = useState(null)
    const [ingredients, setIngredients] = useState({})   // id → name
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        let alive = true
        async function load() {
            try {
                setError(null)
                const [r, ings] = await Promise.all([
                    call(api.get, `/recipes/${id}`),
                    call(api.get, '/ingredients', { params: { limit: 100 } }),
                ])
                if (!alive) return
                setRecipe(r)
                const map = {}
                for (const ing of ings || []) map[ing.id] = ing.name
                setIngredients(map)
            } catch (e) {
                if (alive) setError(e.message || '加载失败')
            } finally {
                if (alive) setLoading(false)
            }
        }
        load()
        return () => { alive = false }
    }, [id, call])

    if (loading) return <State text="加载中…" />
    if (error) return <State text={`出错了: ${error}`} />
    if (!recipe) return <State text="菜谱不存在" />

    return (
        <div className="mx-auto max-w-3xl">
            {/* 返回 */}
            <button
                className="mb-4 flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800"
                onClick={() => navigate('/recipes')}
            >
                <ArrowLeft className="h-4 w-4" /> 返回菜谱
            </button>

            {/* 标题 */}
            <div className="mb-6 flex items-start justify-between gap-3">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">{recipe.name}</h1>
                    {recipe.cuisine && (
                        <p className="mt-1 text-sm text-slate-500">{recipe.cuisine}</p>
                    )}
                    {recipe.description && (
                        <p className="mt-2 text-slate-600">{recipe.description}</p>
                    )}
                </div>
                {recipe.source && (
                    <span className="whitespace-nowrap rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-500">
                        {SOURCE_LABEL[recipe.source] || recipe.source}
                    </span>
                )}
            </div>

            {/* 每个 variant(做法) */}
            <div className="space-y-6">
                {recipe.variants.map((v) => (
                    <VariantSection key={v.id} variant={v} ingredients={ingredients} />
                ))}
            </div>
        </div>
    )
}

function VariantSection({ variant: v, ingredients }) {
    return (
        <Card className="p-6">
            {/* variant 名 + 元信息 */}
            <div className="mb-4 flex flex-wrap items-center gap-3">
                <h2 className="text-lg font-semibold text-slate-900">{v.name}</h2>
                {v.cooking_time_minutes && (
                    <span className="flex items-center gap-1 text-sm text-slate-500">
                        <Clock className="h-4 w-4" /> {v.cooking_time_minutes} 分钟
                    </span>
                )}
                {v.difficulty && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                        {DIFFICULTY_LABEL[v.difficulty] || v.difficulty}
                    </span>
                )}
                <span className="text-sm text-slate-400">{v.servings} 份</span>
            </div>

            {/* 营养 */}
            <div className="mb-5 grid grid-cols-4 gap-3">
                <NutritionStat label="热量" value={v.total_calories} unit="kcal" icon={Flame} />
                <NutritionStat label="蛋白" value={v.total_protein_g} unit="g" />
                <NutritionStat label="碳水" value={v.total_carbs_g} unit="g" />
                <NutritionStat label="脂肪" value={v.total_fat_g} unit="g" />
            </div>

            {/* 配料 */}
            <div className="mb-5">
                <h3 className="mb-2 text-sm font-medium text-slate-700">配料</h3>
                <div className="space-y-1">
                    {v.ingredients.map((ing) => (
                        <div key={ing.id} className="flex justify-between text-sm text-slate-600">
                            <span>{ingredients[ing.ingredient_id] || `食材 #${ing.ingredient_id}`}</span>
                            <span className="text-slate-400">
                                {ing.input_amount} {ing.input_unit}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* 做法 */}
            <div>
                <h3 className="mb-2 text-sm font-medium text-slate-700">做法</h3>
                <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-600">
                    {v.instructions}
                </p>
            </div>

            {v.extra_notes && (
                <p className="mt-3 rounded-md bg-amber-50 p-3 text-sm text-amber-800">
                    💡 {v.extra_notes}
                </p>
            )}
        </Card>
    )
}

// 营养格子。NULL = 不完整, 显示"—"(0≠unknown)
function NutritionStat({ label, value, unit, icon: Icon }) {
    return (
        <div className="rounded-lg bg-slate-50 p-3 text-center">
            <div className="flex items-center justify-center gap-1 text-lg font-semibold text-slate-900">
                {Icon && <Icon className="h-4 w-4 text-slate-400" />}
                {value !== null && value !== undefined ? Number(value).toFixed(0) : '—'}
            </div>
            <div className="mt-0.5 text-xs text-slate-400">{label} ({unit})</div>
        </div>
    )
}

function State({ text }) {
    return (
        <div className="flex h-48 items-center justify-center text-slate-400">{text}</div>
    )
}