// src/components/inventory/AddInventoryDialog.jsx
// 三步式加库存:
//   视图1 选食材(tab: 全部食物 / 我的食物; 排序: 最近添加 / 字母; 搜不到可创建)
//   视图2 创建食物(选单位 + 每单位营养, A2)
//   视图3 填详情(数量 + 单位[按 allowed_units] + 过期日 + 储存区域)→ POST /inventory
import { Plus, Search } from 'lucide-react'
import { useEffect, useState } from 'react'

import { CreateIngredientForm } from '@/components/ingredients/CreateIngredientForm'
import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { useDebounce } from '@/hooks/useDebounce'
import { api } from '@/lib/api'
import { unitLabel } from '@/lib/units'

const ZONES = [
    { value: 'pantry', label: '常温' },
    { value: 'fridge', label: '冷藏' },
    { value: 'freezer', label: '冷冻' },
]

// 数字去掉多余小数(220.0 → 220, 1.00 → 1)
function fmtNum(v) {
    if (v === null || v === undefined) return ''
    const n = Number(v)
    return Number.isInteger(n) ? String(n) : String(n)
}

export function AddInventoryDialog({ onAdded }) {
    const [open, setOpen] = useState(false)
    const [step, setStep] = useState('select')     // 'select' | 'create' | 'detail'
    const [chosen, setChosen] = useState(null)
    const [pendingName, setPendingName] = useState('')

    function close() {
        setOpen(false)
        setTimeout(() => { setStep('select'); setChosen(null); setPendingName('') }, 200)
    }

    const title = step === 'select' ? '选择食材'
        : step === 'create' ? '创建食物' : '添加详情'

    return (
        <Dialog open={open} onOpenChange={(o) => (o ? setOpen(true) : close())}>
            <DialogTrigger asChild>
                <span
                    role="button"
                    tabIndex={0}
                    className="inline-flex cursor-pointer rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                >
                    + 加库存
                </span>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                </DialogHeader>

                {step === 'select' && (
                    <SelectIngredientView
                        onPick={(ing) => { setChosen(ing); setStep('detail') }}
                        onCreateNew={(name) => { setPendingName(name); setStep('create') }}
                    />
                )}
                {step === 'create' && (
                    <CreateIngredientForm
                        initialName={pendingName}
                        onCreated={(ing) => { setChosen(ing); setStep('detail') }}
                        onCancel={() => setStep('select')}
                    />
                )}
                {step === 'detail' && (
                    <FillDetailView
                        ingredient={chosen}
                        onBack={() => setStep('select')}
                        onDone={() => { close(); onAdded?.() }}
                    />
                )}
            </DialogContent>
        </Dialog>
    )
}

// ── 视图1: 选食材(tab + 排序 + 搜索 + 创建) ──
function SelectIngredientView({ onPick, onCreateNew }) {
    const { call } = useApi()
    const [tab, setTab] = useState('all')          // 'all'(全部食物) | 'mine'(我的食物)
    const [sort, setSort] = useState('recent')     // 'recent'(最近添加) | 'name'(字母)
    const [query, setQuery] = useState('')
    const debounced = useDebounce(query, 300)
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        let alive = true
        async function search() {
            setLoading(true)
            try {
                const params = { limit: 50, sort }
                if (tab === 'mine') params.scope = 'mine'
                if (debounced) params.name = debounced
                const data = await call(api.get, '/ingredients', { params })
                if (alive) setResults(data || [])
            } catch {
                if (alive) setResults([])
            } finally {
                if (alive) setLoading(false)
            }
        }
        search()
        return () => { alive = false }
    }, [debounced, sort, tab, call])

    const noResult = !loading && results.length === 0 && debounced

    return (
        <div className="space-y-3">
            {/* tab */}
            <div className="flex gap-1 border-b border-slate-200">
                <TabBtn active={tab === 'all'} onClick={() => setTab('all')}>全部食物</TabBtn>
                <TabBtn active={tab === 'mine'} onClick={() => setTab('mine')}>我的食物</TabBtn>
            </div>

            {/* 搜索 + 排序 */}
            <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                <input
                    autoFocus
                    className="w-full rounded-md border border-slate-300 py-2 pl-9 pr-3 text-sm"
                    placeholder="搜索食材…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                />
            </div>
            <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400">排序</span>
                <SortBtn active={sort === 'recent'} onClick={() => setSort('recent')}>最近添加</SortBtn>
                <SortBtn active={sort === 'name'} onClick={() => setSort('name')}>字母</SortBtn>
            </div>

            {/* 常驻: 创建新食物(始终在最上, 不必先搜不到) */}
            <button
                className="flex w-full items-center gap-2 rounded-md border border-dashed border-slate-300 px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                onClick={() => onCreateNew(query.trim())}
            >
                <Plus className="h-4 w-4" /> 创建新食物
            </button>

            {/* 结果列表 */}
            <div className="max-h-72 space-y-1 overflow-y-auto">
                {loading && <p className="py-4 text-center text-sm text-slate-400">加载中…</p>}

                {!loading && results.map((ing) => (
                    <button
                        key={ing.id}
                        className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left hover:bg-slate-100"
                        onClick={() => onPick(ing)}
                    >
                        <div>
                            <div className="flex items-center gap-1.5 text-sm text-slate-800">
                                {ing.name}
                                {ing.visibility === 'private' && (
                                    <span className="text-xs text-slate-400">私人</span>
                                )}
                            </div>
                            {ing.per_100g_calories !== null && ing.per_100g_calories !== undefined && (
                                <div className="mt-0.5 text-xs text-slate-400">
                                    {fmtNum(ing.per_100g_calories)} 千卡 / {fmtNum(ing.nutrition_basis_amount)} {unitLabel(ing.nutrition_basis_unit)}
                                </div>
                            )}
                        </div>
                        <Plus className="h-4 w-4 shrink-0 text-slate-400" />
                    </button>
                ))}

                {noResult && (
                    <p className="py-4 text-center text-sm text-slate-400">
                        没搜到 "{debounced}",可点上方"创建新食物"
                    </p>
                )}

                {!loading && results.length === 0 && !debounced && (
                    <p className="py-6 text-center text-sm text-slate-400">
                        {tab === 'mine' ? '还没有自己创建的食材' : '暂无食材'}
                    </p>
                )}
            </div>
        </div>
    )
}

function TabBtn({ active, onClick, children }) {
    return (
        <button
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${active
                ? 'border-slate-900 text-slate-900'
                : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
            onClick={onClick}
        >
            {children}
        </button>
    )
}

function SortBtn({ active, onClick, children }) {
    return (
        <button
            className={`rounded-full px-2.5 py-1 ${active
                ? 'bg-slate-900 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
            onClick={onClick}
        >
            {children}
        </button>
    )
}

// ── 视图3: 填详情 ──
function FillDetailView({ ingredient, onBack, onDone }) {
    const { call } = useApi()
    const units = (ingredient.allowed_units && ingredient.allowed_units.length > 0)
        ? ingredient.allowed_units
        : ['g']
    const [amount, setAmount] = useState('')
    const [unit, setUnit] = useState(units[0])
    const [expiresAt, setExpiresAt] = useState('')
    const [location, setLocation] = useState('fridge')
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    async function submit() {
        if (!amount || Number(amount) <= 0) { setError('请填写有效数量'); return }
        try {
            setSubmitting(true)
            setError(null)
            await call(api.post, '/inventory', {
                body: {
                    ingredient_id: ingredient.id,
                    input_amount: Number(amount),
                    input_unit: unit,
                    expires_at: expiresAt || null,
                    location,
                },
            })
            onDone()
        } catch (e) {
            setError(e.message || '添加失败')
        } finally {
            setSubmitting(false)
        }
    }

    return (
        <div className="space-y-4">
            <button
                className="flex items-center gap-2 text-sm font-medium text-slate-900"
                onClick={onBack}
            >
                ← {ingredient.name}
            </button>

            <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">数量</label>
                <div className="flex items-center gap-2">
                    <input
                        type="number" autoFocus
                        className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                        placeholder="例如 500"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value)}
                    />
                    {units.length > 1 ? (
                        <select
                            className="rounded-md border border-slate-300 px-2 py-2 text-sm"
                            value={unit}
                            onChange={(e) => setUnit(e.target.value)}
                        >
                            {units.map((u) => (
                                <option key={u} value={u}>{unitLabel(u)}</option>
                            ))}
                        </select>
                    ) : (
                        <span className="whitespace-nowrap rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-500">
                            {unitLabel(units[0])}
                        </span>
                    )}
                </div>
            </div>

            <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">过期日期(可选)</label>
                <input
                    type="date"
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    value={expiresAt}
                    onChange={(e) => setExpiresAt(e.target.value)}
                />
            </div>

            <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">储存区域</label>
                <select
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                >
                    {ZONES.map((z) => (
                        <option key={z.value} value={z.value}>{z.label}</option>
                    ))}
                </select>
            </div>

            {error && <p className="text-sm text-red-500">{error}</p>}

            <button
                className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                onClick={submit}
                disabled={submitting}
            >
                {submitting ? '添加中…' : '确认添加'}
            </button>
        </div>
    )
}
