// src/components/mealplan/PlanBar.jsx
// plan 筛选栏: 全部/某个 plan 切换 + 创建 + 删除。层次C(默认合并, 可筛选)
import { Plus, Trash2, X } from 'lucide-react'
import { useState } from 'react'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { toISO } from '@/lib/dateRange'

export function PlanBar({ plans, activePlanId, onSelect, onChanged }) {
    const { call } = useApi()
    const [showCreate, setShowCreate] = useState(false)
    const [newName, setNewName] = useState('')
    const [creating, setCreating] = useState(false)
    const [error, setError] = useState(null)

    async function createPlan() {
        if (!newName.trim()) { setError('请填写计划名'); return }
        try {
            setCreating(true)
            setError(null)
            const today = toISO(new Date())
            // 日期用今天(排餐时 expand_plan_range 自动扩展)
            await call(api.post, '/meal-plans', {
                body: { name: newName.trim(), start_date: today, end_date: today },
            })
            setNewName('')
            setShowCreate(false)
            onChanged?.()
        } catch (e) {
            setError(e.message || '创建失败')
        } finally {
            setCreating(false)
        }
    }

    async function deletePlan(plan) {
        if (!confirm(`删除计划「${plan.name || '未命名'}」? 其下所有餐次也会删除。`)) return
        try {
            await call(api.del, `/meal-plans/${plan.id}`)
            if (activePlanId === plan.id) onSelect(null)   // 删的是当前筛选的 → 回到全部
            onChanged?.()
        } catch (e) {
            alert(e.message || '删除失败')
        }
    }

    return (
        <div className="mb-4 flex flex-wrap items-center gap-2">
            {/* 全部 */}
            <button
                className={`rounded-full px-3 py-1 text-sm ${activePlanId === null
                        ? 'bg-slate-900 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                onClick={() => onSelect(null)}
            >
                全部计划
            </button>

            {/* 各 plan */}
            {plans.map((p) => (
                <div
                    key={p.id}
                    className={`group flex items-center gap-1 rounded-full px-3 py-1 text-sm ${activePlanId === p.id
                            ? 'bg-slate-900 text-white'
                            : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        }`}
                >
                    <button onClick={() => onSelect(p.id)}>
                        {p.name || `计划 #${p.id}`}
                    </button>
                    <button
                        className="opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                        onClick={() => deletePlan(p)}
                        title="删除计划"
                    >
                        <Trash2 className="h-3 w-3" />
                    </button>
                </div>
            ))}

            {/* 新建 */}
            <button
                className="flex items-center gap-1 rounded-full border border-dashed border-slate-300 px-3 py-1 text-sm text-slate-500 hover:bg-slate-50"
                onClick={() => setShowCreate(true)}
            >
                <Plus className="h-3.5 w-3.5" /> 新建计划
            </button>

            {/* 创建弹窗 */}
            <Dialog open={showCreate} onOpenChange={(o) => { setShowCreate(o); if (!o) { setNewName(''); setError(null) } }}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>新建计划</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">计划名</label>
                            <input
                                autoFocus
                                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                                placeholder="例如: 减脂周、增肌计划"
                                value={newName}
                                onChange={(e) => setNewName(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && createPlan()}
                            />
                            <p className="mt-1 text-xs text-slate-400">
                                日期会随排餐自动调整,先建个空计划即可。
                            </p>
                        </div>
                        {error && <p className="text-sm text-red-500">{error}</p>}
                        <button
                            className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                            onClick={createPlan}
                            disabled={creating}
                        >
                            {creating ? '创建中…' : '创建'}
                        </button>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    )
}