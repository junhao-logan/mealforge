// src/components/mealplan/MealEntryCard.jsx
// 单个餐次卡片 —— 周/天/月视图共用。含完成、删除、跳详情。
import { Check, RotateCcw, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

// 餐次类型 → i18n 键(meal.breakfast 等)
const MEAL_KEY = {
    breakfast: 'meal.breakfast', lunch: 'meal.lunch', dinner: 'meal.dinner', snack: 'meal.snack',
}

export function MealEntryCard({ entry, onComplete, onDelete, onUncomplete }) {
    const { t } = useTranslation()
    return (
        <div className={`rounded-lg border p-2.5 text-sm ${entry.is_completed ? 'border-green-200 bg-green-50' : 'border-slate-200 bg-white'
            }`}>
            <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                    <span className="text-xs font-medium text-slate-400">
                        {MEAL_KEY[entry.meal_type] ? t(MEAL_KEY[entry.meal_type]) : entry.meal_type}
                    </span>
                    <Link
                        to={`/recipes/${entry.recipe_id}`}
                        className="block truncate font-medium text-slate-900 hover:underline"
                    >
                        {entry.recipe_name}
                    </Link>
                    <span className="text-xs text-slate-400">{t('meal.servings', { count: Number(entry.servings) })}</span>
                </div>
            </div>

            {/* 完成/删除 */}
            <div className="mt-2 flex items-center gap-2">
                {entry.is_completed ? (
                    <button
                        className="group/undo flex items-center gap-1 text-xs text-green-600 hover:text-slate-500"
                        onClick={() => onUncomplete?.(entry)}
                        title={t('meal.uncomplete')}
                    >
                        <Check className="h-3.5 w-3.5 group-hover/undo:hidden" />
                        <RotateCcw className="hidden h-3.5 w-3.5 group-hover/undo:inline" />
                        {t('meal.completed')}
                    </button>
                ) : (
                    <button
                        className="flex items-center gap-1 rounded-md bg-slate-900 px-2 py-1 text-xs text-white hover:bg-slate-800"
                        onClick={() => onComplete(entry)}
                    >
                        <Check className="h-3.5 w-3.5" /> {t('meal.complete')}
                    </button>
                )}
                <button
                    className="text-slate-300 hover:text-red-500"
                    onClick={() => onDelete(entry)}
                    title={t('common.delete')}
                >
                    <Trash2 className="h-3.5 w-3.5" />
                </button>
            </div>
        </div>
    )
}