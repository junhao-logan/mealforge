// src/lib/dateRange.js
// 日期范围工具 —— 各视图(周/天/月)共用。扩展点: 加视图时复用这些。
// 周一为一周起点。

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

const WEEKDAY_CN = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
export function weekdayLabel(d) {
    return WEEKDAY_CN[d.getDay()]
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

// 完整日期显示: "2026年8月12日 周三"
const WEEKDAY_FULL = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
export function fullDate(d) {
    return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${WEEKDAY_FULL[d.getDay()]}`
}