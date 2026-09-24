// src/lib/meals.js
import { shortDate, weekdayLabel } from '@/lib/dateRange'
import { parseDate } from '@/lib/inventoryView'

// 餐段与计划名的共享定义 —— 之前在 5 个文件里各写一份。

// 餐段: value 存后端(与后端 MEAL_TYPE_PATTERN 一致), labelKey 走 i18n。顺序即显示顺序
export const MEAL_OPTIONS = [
    { value: 'breakfast', labelKey: 'meal.breakfast' },
    { value: 'lunch', labelKey: 'meal.lunch' },
    { value: 'dinner', labelKey: 'meal.dinner' },
    { value: 'snack', labelKey: 'meal.snack' },
]

// 餐段 → 文案 key; 未知值原样显示
export function mealLabel(mealType, t) {
    const opt = MEAL_OPTIONS.find((m) => m.value === mealType)
    return opt ? t(opt.labelKey) : mealType
}

// 计划显示名: 默认计划统一叫 Quick Log; 未命名计划显示「计划 #id」
// 兼容两种形状: 计划列表项 {id, name, plan_type} 与预留视图里的餐次 {plan_id, plan_name, plan_type}
export function planLabel(p, t) {
    if (p.plan_type === 'default') return t('mealPlans.defaultPlanName')
    const name = p.name ?? p.plan_name
    return name || t('mealPlans.planFallback', { id: p.id ?? p.plan_id })
}

// 餐次一行标题:「计划 · 周四 9/26 午餐 · 菜名」(库存预留卡片与餐次明细弹窗共用)
// entry 为预留视图里的餐次: {plan_id, plan_name, plan_type, scheduled_date, meal_type, recipe_name}
export function mealTitle(entry, t) {
    const d = parseDate(entry.scheduled_date)
    return `${planLabel(entry, t)} · ${weekdayLabel(d)} ${shortDate(d)} ${mealLabel(entry.meal_type, t)} · ${entry.recipe_name}`
}
