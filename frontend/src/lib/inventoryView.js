// src/lib/inventoryView.js
// 库存页(A4)的纯函数: 数量格式化 / FEFO 排序 / 按「食材 + 储存区」合并。
import { unitLabel } from '@/lib/units'

export const ZONED_KEYS = ['pantry', 'fridge', 'freezer']

// 批次所在区: 三区之外(含 null)一律归「未指定」
export function zoneOf(location) {
    return ZONED_KEYS.includes(location) ? location : 'unzoned'
}

export const ZONE_LABEL_KEYS = {
    pantry: 'inventory.zonePantry',
    fridge: 'inventory.zoneFridge',
    freezer: 'inventory.zoneFreezer',
    unzoned: 'inventory.zoneUnzoned',
}

// 数量 + 单位: 最多两位小数、去掉多余的 0。单位按界面语言显示(块 → chunk)
export function fmtAmount(value, unit) {
    const n = Number(value) || 0
    const s = String(Number(n.toFixed(2)))
    return unit ? `${s} ${unitLabel(unit)}` : s
}

// 'YYYY-MM-DD' → 本地日期(避免 UTC 解析差一天)
export function parseDate(s) {
    return s ? new Date(s + 'T00:00:00') : null
}

// FEFO 全序: 过期日 → 购买日 → id, 空值排最后(与后端扣减顺序一致)
export function fefoCompare(a, b) {
    const k = (v) => (v ? v : '9999-12-31')
    return (
        k(a.expires_at).localeCompare(k(b.expires_at)) ||
        k(a.purchased_at).localeCompare(k(b.purchased_at)) ||
        a.id - b.id
    )
}

// 批次 + 预留 → 按「食材 + 储存区」合并的卡片数据
export function groupInventory(items, reservations) {
    const resByBatch = {}
    for (const b of reservations?.batches || []) resByBatch[b.batch_id] = b

    const groups = {}
    for (const it of items) {
        const zone = zoneOf(it.location)
        const key = `${it.ingredient_id}|${zone}`
        const r = resByBatch[it.id]
        const qty = Number(it.quantity_grams) || 0
        const batch = {
            ...it,
            quantity: qty,
            reserved: r ? Number(r.reserved) : 0,
            free: r ? Number(r.free) : qty,
            allocations: r ? r.allocations : [],
        }
        if (!groups[key]) {
            groups[key] = { key, zone, ingredient_id: it.ingredient_id, batches: [] }
        }
        groups[key].batches.push(batch)
    }

    for (const g of Object.values(groups)) {
        g.batches.sort(fefoCompare)
        g.total = g.batches.reduce((s, b) => s + b.quantity, 0)
        g.reserved = g.batches.reduce((s, b) => s + b.reserved, 0)
        g.free = g.batches.reduce((s, b) => s + b.free, 0)
        // 最早过期: 只看还有余量的批次(都为 0 时退回全部)
        const live = g.batches.filter((b) => b.quantity > 0)
        g.earliestExpiry = (live.length ? live : g.batches)
            .map((b) => b.expires_at).filter(Boolean).sort()[0] || null
    }
    return Object.values(groups)
}
