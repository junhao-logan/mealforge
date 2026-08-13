// src/lib/expiry.js
// 库存卡片"按剩余天数绿→红渐变"的颜色计算(决策3方案B)。
// 抽成纯函数: 复用 + 好测 + 页面只管调。

// 剩余天数: expires_at 距今天多少天。无过期日 → null。
export function daysUntil(expiresAt, today = new Date()) {
    if (!expiresAt) return null
    const exp = new Date(expiresAt + 'T00:00:00')
    const t0 = new Date(today.getFullYear(), today.getMonth(), today.getDate())
    return Math.round((exp - t0) / 86400000)   // 毫秒 → 天
}

// 剩余天数 → 卡片背景色(HSL 从红 0° 到绿 120°)。
// 0 天(或已过期) = 红; >=FULL_GREEN 天 = 绿; 中间线性渐变。
// 无过期日(null) → 中性灰(不参与渐变, 决策4)。
const FULL_GREEN_DAYS = 14   // 剩 14 天以上算"新鲜"(纯绿)

export function expiryColor(days) {
    if (days === null || days === undefined) {
        return 'hsl(220, 14%, 96%)'   // 中性灰(无过期日)
    }
    // 夹到 [0, FULL_GREEN_DAYS]
    const clamped = Math.max(0, Math.min(FULL_GREEN_DAYS, days))
    const ratio = clamped / FULL_GREEN_DAYS   // 0(红) → 1(绿)
    const hue = ratio * 120                    // 0°红 → 120°绿
    // 浅一点的背景(高亮度低饱和), 保证卡片文字可读
    return `hsl(${hue}, 70%, 92%)`
}

// 排序权重: 过期日近的排前, 无过期日排最后(决策: 无过期日在最下)。
export function sortKey(days) {
    return days === null || days === undefined ? Infinity : days
}

// 过期标签: 已过期(days<0) / 临期(0<=days<=EXPIRING_DAYS) / 正常。
// 供卡片显示不同标签(修复"过期了却显示临期")。
const EXPIRING_DAYS = 3
export function expiryLabel(days) {
    if (days === null || days === undefined) return null
    if (days < 0) return { text: '已过期', variant: 'expired' }
    if (days <= EXPIRING_DAYS) return { text: '临期', variant: 'expiring' }
    return null
}