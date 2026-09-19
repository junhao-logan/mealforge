// src/lib/dateRange.js
// 日期范围工具 —— 各视图(周/天/月)共用。扩展点: 加视图时复用这些。
// 周一为一周起点。
import i18n from '@/i18n'

// 当前界面语言 → Intl locale(用于星期/完整日期本地化显示)
function localeTag() {
    return (i18n.language || 'en').startsWith('zh') ? 'zh-CN' : 'en-US'
}

export function toISO(d) {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
}

// 给定日期, 返回其所在周的周一
export function weekStart(date) {
    const d = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    const dow = (d.getDay() + 6) % 7   // 周一=0 ... 周日=6
    d.setDate(d.getDate() - dow)
    return d
}

// 周的 7 天(周一→周日)
export function weekDays(anchor) {
    const start = weekStart(anchor)
    return Array.from({ length: 7 }, (_, i) => {
        const d = new Date(start)
        d.setDate(start.getDate() + i)
        return d
    })
}

// 加/减 n 天(用于切换周: ±7)
export function addDays(date, n) {
    const d = new Date(date)
    d.setDate(d.getDate() + n)
    return d
}

// 星期显示: 按当前语言(en: Mon / zh: 周一)。切换语言时组件重渲染即更新。
export function weekdayLabel(d) {
    return d.toLocaleDateString(localeTag(), { weekday: 'short' })
}

// 显示用: "8/11"
export function shortDate(d) {
    return `${d.getMonth() + 1}/${d.getDate()}`
}

// 是否今天
export function isToday(d) {
    const t = new Date()
    return d.getFullYear() === t.getFullYear() &&
        d.getMonth() === t.getMonth() && d.getDate() === t.getDate()
}

// 完整日期显示: 按当前语言(en: "Thursday, September 18, 2026" / zh: "2026年9月18日星期四")
export function fullDate(d) {
    return d.toLocaleDateString(localeTag(), {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    })
}