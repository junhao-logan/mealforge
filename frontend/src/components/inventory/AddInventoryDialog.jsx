// src/components/inventory/AddInventoryDialog.jsx
// 两步式加库存:
//   视图1 选食材(搜索公共库 + 我的食材 + 可创建新食材)
//   视图2 填详情(数量/过期日/储存区域)→ POST /inventory
import { ArrowLeft, Plus, Search } from 'lucide-react'
import { useEffect, useState } from 'react'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { useDebounce } from '@/hooks/useDebounce'
import { api } from '@/lib/api'

const ZONES = [
    { value: 'pantry', label: '常温' },
    { value: 'fridge', label: '冷藏' },
    { value: 'freezer', label: '冷冻' },
]

export function AddInventoryDialog({ onAdded }) {
    const [open, setOpen] = useState(false)
    const [step, setStep] = useState('select')     // 'select' | 'detail'
    const [chosen, setChosen] = useState(null)      // 选中的食材 {id, name}

    function close() {
        setOpen(false)
        // 关闭后重置(延迟一点避免关闭动画时闪回)
        setTimeout(() => { setStep('select'); setChosen(null) }, 200)
    }

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
                    <DialogTitle>
                        {step === 'select' ? '选择食材' : '添加详情'}
                    </DialogTitle>
                </DialogHeader>

                {step === 'select' ? (
                    <SelectIngredientView
                        onPick={(ing) => { setChosen(ing); setStep('detail') }}
                    />
                ) : (
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

// ── 视图1: 选食材(搜索 + 分组 + 创建) ──
function SelectIngredientView({ onPick }) {
    const { call } = useApi()
    const [query, setQuery] = useState('')
    const debounced = useDebounce(query, 300)
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)
    const [creating, setCreating] = useState(false)

    useEffect(() => {
        let alive = true
        async function search() {
            setLoading(true)
            try {
                // 有搜索词就带 name 过滤, 否则拉默认列表
                const params = debounced ? { name: debounced, limit: 50 } : { limit: 50 }
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
    }, [debounced, call])

    // 分组: 我的(private) vs 公共(global)
    const mine = results.filter((r) => r.visibility === 'private')
    const global = results.filter((r) => r.visibility === 'global')
    const noResult = !loading && results.length === 0 && debounced

    async function createIngredient() {
        if (!debounced) return
        try {
            setCreating(true)
            const created = await call(api.post, '/ingredients', {
                body: { name: debounced },
            })
            onPick({ id: created.id, name: created.name })   // 建完直接进详情
        } catch (e) {
            alert(e.message || '创建失败')
        } finally {
            setCreating(false)
        }
    }

    return (
        <div className="space-y-3">
            {/* 搜索栏 */}
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

            {/* 结果列表 */}
            <div className="max-h-72 space-y-3 overflow-y-auto">
                {loading && <p className="py-4 text-center text-sm text-slate-400">搜索中…</p>}

                {mine.length > 0 && (
                    <IngredientGroup title="我的食材" items={mine} onPick={onPick} />
                )}
                {global.length > 0 && (
                    <IngredientGroup title="公共库" items={global} onPick={onPick} />
                )}

                {/* 搜不到 → 可创建 */}
                {noResult && (
                    <button
                        className="flex w-full items-center gap-2 rounded-md border border-dashed border-slate-300 px-3 py-3 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-50"
                        onClick={createIngredient}
                        disabled={creating}
                    >
                        <Plus className="h-4 w-4" />
                        {creating ? '创建中…' : `创建 "${debounced}"`}
                    </button>
                )}

                {!loading && results.length === 0 && !debounced && (
                    <p className="py-4 text-center text-sm text-slate-400">输入名称搜索食材</p>
                )}
            </div>
        </div>
    )
}

function IngredientGroup({ title, items, onPick }) {
    return (
        <div>
            <p className="mb-1 px-1 text-xs font-medium text-slate-400">{title}</p>
            <div className="space-y-1">
                {items.map((ing) => (
                    <button
                        key={ing.id}
                        className="w-full rounded-md px-3 py-2 text-left text-sm text-slate-800 hover:bg-slate-100"
                        onClick={() => onPick({ id: ing.id, name: ing.name })}
                    >
                        {ing.name}
                    </button>
                ))}
            </div>
        </div>
    )
}

// ── 视图2: 填详情 ──
function FillDetailView({ ingredient, onBack, onDone }) {
    const { call } = useApi()
    const [amount, setAmount] = useState('')
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
                    input_unit: 'g',
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
            {/* 选中的食材 + 返回 */}
            <button
                className="flex items-center gap-2 text-sm font-medium text-slate-900"
                onClick={onBack}
            >
                <ArrowLeft className="h-4 w-4" />
                {ingredient.name}
            </button>

            <div>
                <label className="mb-1 block text-sm font-medium text-slate-700">数量 (克)</label>
                <input
                    type="number" autoFocus
                    className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                    placeholder="例如 500"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                />
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