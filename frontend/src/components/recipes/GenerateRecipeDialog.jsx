// src/components/recipes/GenerateRecipeDialog.jsx
// AI 生成菜谱弹窗: 填偏好(全可选) → POST /recipes/generate → AI 从库存现编
import { ChefHat, Sparkles } from 'lucide-react'
import { useState } from 'react'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'

const GOALS = [
    { value: '', label: '不限' },
    { value: '高蛋白', label: '高蛋白' },
    { value: '减脂', label: '减脂' },
    { value: '增肌', label: '增肌' },
]

export function GenerateRecipeDialog({ onGenerated }) {
    const { call } = useApi()
    const [open, setOpen] = useState(false)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState(null)

    const [freeText, setFreeText] = useState('')
    const [cuisine, setCuisine] = useState('')
    const [goal, setGoal] = useState('')
    const [servings, setServings] = useState('')

    function reset() {
        setFreeText(''); setCuisine(''); setGoal(''); setServings(''); setError(null)
    }

    async function generate() {
        try {
            setSubmitting(true)
            setError(null)
            // 全可选: 只传填了的
            const body = {}
            if (freeText.trim()) body.free_text = freeText.trim()
            if (cuisine.trim()) body.cuisine = cuisine.trim()
            if (goal) body.goal = goal
            if (servings) body.servings = Number(servings)

            const created = await call(api.post, '/recipes/generate', { body })
            reset()
            setOpen(false)
            onGenerated?.(created)   // 通知父组件(切到我的菜谱 + 刷新)
        } catch (e) {
            // 后端: 空库存 400, AI 失败 502
            if (e.status === 400) {
                setError('库存为空,先去库存页添加食材,AI 才能用它们现编菜谱')
            } else if (e.status === 502) {
                setError('AI 生成暂时不可用,请稍后重试')
            } else {
                setError(e.message || '生成失败')
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
                    <ChefHat className="h-4 w-4" />
                    AI 生成
                </span>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Sparkles className="h-5 w-5 text-amber-500" />
                        AI 生成菜谱
                    </DialogTitle>
                </DialogHeader>

                <div className="space-y-4">
                    <p className="text-sm text-slate-500">
                        AI 会用你库存里的食材现编一道菜。以下都可留空。
                    </p>

                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">补充说明</label>
                        <input
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            placeholder="例如: 清淡少油、适合减脂"
                            value={freeText}
                            onChange={(e) => setFreeText(e.target.value)}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="mb-1 block text-sm font-medium text-slate-700">菜系</label>
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
                                placeholder="如 2"
                                value={servings}
                                onChange={(e) => setServings(e.target.value)}
                            />
                        </div>
                    </div>

                    <div>
                        <label className="mb-1 block text-sm font-medium text-slate-700">目标</label>
                        <select
                            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                            value={goal}
                            onChange={(e) => setGoal(e.target.value)}
                        >
                            {GOALS.map((g) => (
                                <option key={g.value} value={g.value}>{g.label}</option>
                            ))}
                        </select>
                    </div>

                    {error && <p className="text-sm text-red-500">{error}</p>}

                    <button
                        className="flex w-full items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        onClick={generate}
                        disabled={submitting}
                    >
                        {submitting ? (
                            <>
                                <Sparkles className="h-4 w-4 animate-pulse" />
                                AI 生成中…(约需几秒)
                            </>
                        ) : (
                            <>
                                <Sparkles className="h-4 w-4" />
                                开始生成
                            </>
                        )}
                    </button>
                </div>
            </DialogContent>
        </Dialog>
    )
}