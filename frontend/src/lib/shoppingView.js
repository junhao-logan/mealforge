// src/lib/shoppingView.js
// A8: 清单里同一食材的自动项 + 手动项在界面上合成一行(数据库仍是多行, 重算时手动部分不丢)。
// 结算时只提交代表行, 后端会把同食材的兄弟行一起标记已购(不重复入库)。

// 返回显示行: { key, rep, items, name, unit, needed, autoAmt, manualAmt, purchased, purchasedAmt, merged }
export function groupListItems(items) {
    const rows = []
    const groups = {}
    for (const it of items) {
        // 纯文本项 / 不入库项: 不合并, 各自一行
        if (it.ingredient_id == null || !it.add_to_inventory) {
            rows.push(single(it))
            continue
        }
        const key = `${it.ingredient_id}|${it.is_purchased ? 'done' : 'todo'}`
        if (!groups[key]) {
            groups[key] = {
                key, items: [], name: it.ingredient_name, unit: it.unit || 'g',
                needed: 0, autoAmt: 0, manualAmt: 0, purchased: it.is_purchased, purchasedAmt: 0,
            }
            rows.push(groups[key])
        }
        const g = groups[key]
        g.items.push(it)
        const n = Number(it.needed_grams) || 0
        g.needed += n
        if (it.source === 'auto') g.autoAmt += n; else g.manualAmt += n
        g.purchasedAmt += Number(it.purchased_amount) || 0
    }
    for (const g of Object.values(groups)) {
        // 代表行: 优先自动项(兄弟行由后端一起关)
        g.rep = g.items.find((i) => i.source === 'auto') || g.items[0]
        g.merged = g.items.length > 1
    }
    return rows
}

function single(it) {
    const n = Number(it.needed_grams) || 0
    return {
        key: `item-${it.id}`, rep: it, items: [it],
        name: it.ingredient_name || it.item_name, unit: it.unit || 'g',
        needed: n, autoAmt: it.source === 'auto' ? n : 0, manualAmt: it.source === 'auto' ? 0 : n,
        purchased: it.is_purchased, purchasedAmt: Number(it.purchased_amount) || 0, merged: false,
    }
}
