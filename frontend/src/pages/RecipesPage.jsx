// src/pages/RecipesPage.jsx —— 菜谱页(默认"我能做什么", 三态食材可视化)
import { Check, Minus, X } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { GenerateRecipeDialog } from '@/components/recipes/GenerateRecipeDialog'
import { Link } from 'react-router'

import { Card } from '@/components/ui/card'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

const SOURCE_LABEL = {
    ai_generated: 'AI 生成', ai: 'AI 生成', user: '自建', manual: '手动',
}

export function RecipesPage() {
    const [tab, setTab] = useState('canmake')   // 默认"我能做什么"
    const [refreshKey, setRefreshKey] = useState(0)   // 生成后强制刷新我的菜谱

    function handleGenerated() {
        setTab('mine')                    // 切到"我的菜谱"
        setRefreshKey((k) => k + 1)       // 触发列表重新加载
    }

    return (
        <div>
            <div className="mb-6 flex items-center justify-between">
                <h1 className="text-2xl font-bold text-slate-900">菜谱</h1>
                <GenerateRecipeDialog onGenerated={handleGenerated} />
            </div>

            <div className="mb-4 flex gap-1 border-b border-slate-200">
                <TabButton active={tab === 'canmake'} onClick={() => setTab('canmake')}>
                    我能做什么
                </TabButton>
                <TabButton active={tab === 'mine'} onClick={() => setTab('mine')}>
                    我的菜谱
                </TabButton>
            </div>

            {tab === 'canmake' ? <CanMake /> : <MyRecipes refreshKey={refreshKey} />}
        </div>
    )
}

function TabButton({ active, onClick, children }) {
    return (
        <button
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${active
                    ? 'border-slate-900 text-slate-900'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
            onClick={onClick}
        >
            {children}
        </button>
    )
}

// ── 我能做什么(反向推荐 + 三态食材) ──
function CanMake() {
    const { call } = useApi()
    const [recs, setRecs] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        let alive = true
        async function load() {
            try {
                setError(null)
                const data = await call(api.get, '/recipes/recommendations', {
                    params: { max_missing: 2 },
                })
                if (alive) setRecs(data || [])
            } catch (e) {
                if (alive) setError(e.message || '加载失败')
            } finally {
                if (alive) setLoading(false)
            }
        }
        load()
        return () => { alive = false }
    }, [call])

    if (loading) return <State text="分析库存中…" />
    if (error) return <State text={`出错了: ${error}`} />
    if (recs.length === 0) {
        return <State text="按当前库存,还没有能做(或接近能做)的菜。先加点库存或生成菜谱吧" />
    }

    return (
        <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {recs.map((rec) => (
                <Card key={rec.variant_id} className="p-4">
                    <div className="mb-3 flex items-start justify-between gap-3">
                        <div>
                            <Link
                                to={`/recipes/${rec.recipe_id}`}
                                className="font-semibold text-slate-900 hover:underline"
                            >
                                {rec.recipe_name}
                            </Link>
                            {rec.variant_name && (
                                <p className="mt-0.5 text-sm text-slate-500">{rec.variant_name}</p>
                            )}
                        </div>
                        {rec.missing_count === 0 ? (
                            <span className="flex items-center gap-1 whitespace-nowrap rounded-full bg-green-100 px-2.5 py-1 text-xs font-medium text-green-700">
                                <Check className="h-3.5 w-3.5" />
                                可做
                            </span>
                        ) : (
                            <span className="whitespace-nowrap rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700">
                                缺 {rec.missing_count} 样
                            </span>
                        )}
                    </div>

                    {/* 完整食材清单, 每样三态图标 */}
                    <div className="space-y-1.5">
                        {rec.ingredients.map((ing) => (
                            <IngredientRow key={ing.id} ingredient={ing} />
                        ))}
                    </div>
                </Card>
            ))}
        </div>
    )
}

// 一行食材 + 三态图标
function IngredientRow({ ingredient }) {
    const config = {
        have: { Icon: Check, color: 'text-green-600', label: '有' },
        partial: { Icon: Minus, color: 'text-amber-500', label: '不够' },
        missing: { Icon: X, color: 'text-red-500', label: '没有' },
    }[ingredient.status] || { Icon: Minus, color: 'text-slate-400', label: '' }

    const { Icon, color, label } = config
    return (
        <div className="flex items-center justify-between text-sm">
            <span className="flex items-center gap-2 text-slate-700">
                <Icon className={`h-4 w-4 ${color}`} />
                {ingredient.name}
            </span>
            <span className={`text-xs ${color}`}>{label}</span>
        </div>
    )
}

// ── 我的菜谱 ──
function MyRecipes({ refreshKey }) {
    const { call } = useApi()
    const [recipes, setRecipes] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    const reload = useCallback(async () => {
        try {
            setError(null)
            const data = await call(api.get, '/recipes')
            setRecipes(data || [])
        } catch (e) {
            setError(e.message || '加载失败')
        } finally {
            setLoading(false)
        }
    }, [call])

    useEffect(() => { reload() }, [reload, refreshKey])

    if (loading) return <State text="加载中…" />
    if (error) return <State text={`出错了: ${error}`} />
    if (recipes.length === 0) return <State text="还没有菜谱,点右上角 AI 生成一道试试" />

    return (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {recipes.map((r) => (
                <Link key={r.id} to={`/recipes/${r.id}`}>
                    <Card className="cursor-pointer p-4 transition-shadow hover:shadow-md">
                        <div className="flex items-start justify-between gap-2">
                            <h3 className="font-semibold text-slate-900">{r.name}</h3>
                            {r.source && (
                                <span className="whitespace-nowrap rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                                    {SOURCE_LABEL[r.source] || r.source}
                                </span>
                            )}
                        </div>
                        {r.cuisine && <p className="mt-1 text-sm text-slate-500">{r.cuisine}</p>}
                    </Card>
                </Link>
            ))}
        </div>
    )
}

function State({ text }) {
    return (
        <div className="flex h-48 items-center justify-center px-4 text-center text-slate-400">
            {text}
        </div>
    )
}