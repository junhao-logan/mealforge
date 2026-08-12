// src/components/mealplan/MealEntryCard.jsx
// 单个餐次卡片 —— 周/天/月视图共用。含完成、删除、跳详情。
import { Check, Trash2 } from 'lucide-react'
import { Link } from 'react-router'

const MEAL_LABEL = {
    breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐',
}

export function MealEntryCard({ entry, onComplete, onDelete }) {
    return (
        <div className={`rounded-lg border p-2.5 text-sm ${entry.is_completed ? 'border-green-200 bg-green-50' : 'border-slate-200 bg-white'
            }`}>
            <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                    <span className="text-xs font-medium text-slate-400">
                        {MEAL_LABEL[entry.meal_type] || entry.meal_type}
                    </span>
                    <Link
                        to={`/recipes/${entry.recipe_id}`}
                        className="block truncate font-medium text-slate-900 hover:underline"
                    >
                        {entry.recipe_name}
                    </Link>
                    <span className="text-xs text-slate-400">{Number(entry.servings)} 份</span>
                </div>
            </div>

            {/* 完成/删除 */}
            <div className="mt-2 flex items-center gap-2">
                {entry.is_completed ? (
                    <span className="flex items-center gap-1 text-xs text-green-600">
                        <Check className="h-3.5 w-3.5" /> 已完成
                    </span>
                ) : (
                    <button
                        className="flex items-center gap-1 rounded-md bg-slate-900 px-2 py-1 text-xs text-white hover:bg-slate-800"
                        onClick={() => onComplete(entry)}
                    >
                        <Check className="h-3.5 w-3.5" /> 完成
                    </button>
                )}
                <button
                    className="text-slate-300 hover:text-red-500"
                    onClick={() => onDelete(entry)}
                    title="删除"
                >
                    <Trash2 className="h-3.5 w-3.5" />
                </button>
            </div>
        </div>
    )
}