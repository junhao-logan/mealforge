// src/components/recipes/CreateRecipeDialog.jsx
// 手动创建菜谱(精简版): 菜名 + 做法说明 + 配料(≥1) → POST /recipes
// 配料的食材从库里搜/或现场创建(A2 单位本位), 单位下拉用后端 allowed_units。
import { Plus, Search, Trash2, X } from 'lucide-react'
import { useEffect, useState } from 'react'

import { CreateIngredientForm } from '@/components/ingredients/CreateIngredientForm'
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { useDebounce } from '@/hooks/useDebounce'
import { api } from '@/lib/api'
import { unitLabel } from '@/lib/units'

export function CreateRecipeDialog({ onCreated }) {
    const { call } = useApi()
    const [open, setOpen] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    const [name, setName] = useState('')
    const [cuisine, setCuisine] = useState('')
    const [servings, setServings] = useState('')
    const [instructions, setInstructions] = useState('')
    // 配料行: { ingredient|null, amount, unit, creating, pendingName }
    const [rows, setRows] = useState([])

    function reset() {
        setName(''); setCuisine(''); setServings(''); setInstructions('')
        setRows([]); setError(null)
    }

    function addRow() {
        setRows((rs) => [...rs, { ingredient: null, amount: '', unit: 'g', creating: false, pendingName: '' }])
    }
    function removeRow(i) {
        setRows((rs) => rs.filter((_, idx) => idx !== i))
    }
    function setRowIngredient(i, ing) {
        const units = ing.allowed_units && ing.allowed_units.length > 0 ? ing.allowed_units : ['g']
        setRows((rs) => rs.map((r, idx) => idx === i
            ? { ...r, ingredient: ing, unit: units[0], creating: false }
            : r))
    }
    function setRowField(i, field, val) {
        setRows((rs) => rs.map((r, idx) => idx === i ? { ...r, [field]: val } : r))
    }

    async function submit() {
        if (!name.trim()) { setError('请填写菜名'); return }
        if (!instructions.trim()) { setError('请填写做法说明'); return }
        const filled = rows.filter((r) => r.ingredient && Number(r.amount) > 0)
        if (filled.length === 0) { setError('至少添加一样配料(并填数量)'); return }

        try {
            setSubmitting(true)
            setError(null)
            const body = {
                name: name.trim(),
                cuisine: cuisine.trim() || null,
                variant: {
                    name: name.trim(),
                    instructions: instructions.trim(),
                    servings: servings ? Number(servings) : 1,
                    ingredients: filled.map((r) => ({
                        ingredient_id: r.ingredient.id,
                        input_amount: Number(r.amount),
                        input_unit: r.unit,
                    })),
                },
            }
            const created = await call(api.post, '/recipes', { body })
            reset()
            setOpen(false)
            onCreated?.(created)
        } catch (e) {
            setError(e.message || '创建失败')
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
                    className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                    <Plus className="h-4 w-4" />
                    手动创建
                </span>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>手动创建菜谱</DialogTitle>
                </DialogHeader>

                <div className="max-h-[70vh] space-y-4 overflow-y-auto pr-1">
                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">菜名</label>
                        <input
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            placeholder="例如: 番茄炒蛋"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">菜系(可选)</label>
                            <input
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                placeholder="中餐/西餐…"
                                value={cuisine}
                                onChange={(e) => setCuisine(e.target.value)}
                            />
                        </div>
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">份数</label>
                            <input
                                type="number"
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                placeholder="默认 1"
                                value={servings}
                                onChange={(e) => setServings(e.target.value)}
                            />
                        </div>
                    </div>

                    <div>
                        <div className="mb-1 flex items-center justify-between">
                            <label className="text-sm font-medium text-slate-700">配料</label>
                            <button
                                type="button"
                                className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"
                                onClick={addRow}
                            >
                                <Plus className="h-4 w-4" /> 添加配料
                            </button>
                        </div>
                        {rows.length === 0 && (
                            <p className="rounded-md border border-dashed border-slate-300 px-3 py-3 text-center text-sm text-slate-400">
                                点"添加配料"从食材库选择或创建
                            </p>
                        )}
                        <div className="space-y-2">
                            {rows.map((row, i) => (
                                <IngredientRow
                                    key={i}
                                    row={row}
                                    onPick={(ing) => setRowIngredient(i, ing)}
                                    onField={(f, v) => setRowField(i, f, v)}
                                    onRemove={() => removeRow(i)}
                                />
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">做法说明</label>
                        <textarea
                            rows={4}
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            placeholder="每步一行, 例如:&#10;1. 热锅下油&#10;2. 打散鸡蛋炒至凝固盛出&#10;3. 下番茄翻炒出汁, 回锅鸡蛋"
                            value={instructions}
                            onChange={(e) => setInstructions(e.target.value)}
                        />
                    </div>

                    {error && <p className="text-sm text-red-500">{error}</p>}

                    <button
                        className="w-full rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={submit}
                        disabled={submitting}
                    >
                        {submitting ? '创建中…' : '创建菜谱'}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}

// 一条配料: 未选 → 搜索 / 创建食物; 已选 → 名字 + 数量 + 单位 + 删除
function IngredientRow({ row, onPick, onField, onRemove }) {
    // 创建食物模式
    if (row.creating) {
        return (
            <div className="rounded-md border border-slate-200 p-3">
                <CreateIngredientForm
                    initialName={row.pendingName}
                    onCreated={(ing) => onPick(ing)}
                    onCancel={() => onField('creating', false)}
                />
            </div>
        )
    }
    // 未选食材: 搜索
    if (!row.ingredient) {
        return (
            <div className="rounded-md border border-slate-200 p-2">
                <div className="mb-1 flex items-center justify-between">
                    <span className="px-1 text-xs text-slate-400">选择食材</span>
                    <button type="button" onClick={onRemove} className="text-slate-400 hover:text-slate-600">
                        <X className="h-4 w-4" />
                    </button>
                </div>
                <InlineIngredientSearch
                    onPick={onPick}
                    onCreateNew={(name) => { onField('pendingName', name); onField('creating', true) }}
                />
            </div>
        )
    }
    // 已选: 单位来自 allowed_units
    const units = row.ingredient.allowed_units && row.ingredient.allowed_units.length > 0
        ? row.ingredient.allowed_units
        : ['g']
    return (
        <div className="flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2">
            <span className="flex-1 truncate text-sm text-slate-800">{row.ingredient.name}</span>
            <input
                type="number"
                className="w-20 rounded-md border border-slate-300 px-2 py-1 text-sm"
                placeholder="量"
                value={row.amount}
                onChange={(e) => onField('amount', e.target.value)}
            />
            {units.length > 1 ? (
                <select
                    className="rounded-md border border-slate-300 px-2 py-1 text-sm"
                    value={row.unit}
                    onChange={(e) => onField('unit', e.target.value)}
                >
                    {units.map((u) => <option key={u} value={u}>{unitLabel(u)}</option>)}
                </select>
            ) : (
                <span className="rounded-md border border-slate-200 bg-slate-50 px-2 py-1 text-sm text-slate-500">
                    {unitLabel(units[0])}
                </span>
            )}
            <button type="button" onClick={onRemove} className="text-slate-400 hover:text-red-500">
                <Trash2 className="h-4 w-4" />
            </button>
        </div>
    )
}

// 内联食材搜索(/ingredients?name= + 分组); 搜不到 → 交给父级切"创建食物"
function InlineIngredientSearch({ onPick, onCreateNew }) {
    const { call } = useApi()
    const [query, setQuery] = useState('')
    const debounced = useDebounce(query, 300)
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        let alive = true
        async function search() {
            if (!debounced) { setResults([]); return }
            setLoading(true)
            try {
                const data = await call(api.get, '/ingredients', {
                    params: { name: debounced, limit: 50 },
                })
                if (alive) setResults(data || [])
            } catch {
                if (alive) setResults([])
            } finally {
                if (alive) setLoading(false)
            }
        }
        search()
        return () => { alive = false }
    }, [debounced, call])

    const noResult = !loading && results.length === 0 && debounced

    return (
        <div>
            <div className="relative">
                <Search className="absolute left-2.5 top-2 h-4 w-4 text-slate-400" />
                <input
                    autoFocus
                    className="w-full rounded-md border border-slate-300 py-1.5 pl-8 pr-3 text-sm"
                    placeholder="搜索食材…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
            </div>
            {(results.length > 0 || loading || noResult) && (
                <div className="mt-1 max-h-40 space-y-0.5 overflow-y-auto">
                    {loading && <p className="py-2 text-center text-xs text-slate-400">搜索中…</p>}
                    {results.map((ing) => (
                        <button
                            key={ing.id}
                            type="button"
                            className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-sm text-slate-800 hover:bg-slate-100"
                            onClick={() => onPick(ing)}
                        >
                            <span>{ing.name}</span>
                            {ing.visibility === 'private' && (
                                <span className="text-xs text-slate-400">私人</span>
                            )}
                        </button>
                    ))}
                    {noResult && (
                        <button
                            type="button"
                            className="flex w-full items-center gap-2 rounded-md border border-dashed border-slate-300 px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
                            onClick={() => onCreateNew(debounced)}
                        >
                            <Plus className="h-4 w-4" />
                            创建 "{debounced}"
                        </button>
                    )}
                </div>
            )}
        </div>
    )
}