// src/lib/restock.js
// A5: 撤销完成 / 删除餐次 / 删除计划后, 如有退不回去的部分(原批次已删), 提示用户。
import { fmtAmount } from '@/lib/inventoryView'

export function reportRestockLosses(res, t) {
    const lost = res?.unrestorable || []
    if (lost.length === 0) return
    const list = lost
        .map((x) => `${x.name || t('inventory.food', { id: x.ingredient_id })} ${fmtAmount(x.amount, x.unit)}`)
        .join(t('inventory.listSep'))
    alert(t('meal.restockLost', { list }))
}
