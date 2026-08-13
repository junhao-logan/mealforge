// src/pages/InventoryPage.jsx —— 库存页(三区展示 + 渐变卡片 + 加库存 + 删除)
import { Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { AddInventoryDialog } from '@/components/inventory/AddInventoryDialog'
import { EditInventoryDialog } from '@/components/inventory/EditInventoryDialog'
import { Card } from '@/components/ui/card'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { daysUntil, expiryColor, expiryLabel, sortKey } from '@/lib/expiry'

const ZONES = [
    { key: 'pantry', label: '常温', accent: 'border-t-amber-400' },
    { key: 'fridge', label: '冷藏', accent: 'border-t-sky-400' },
    { key: 'freezer', label: '冷冻', accent: 'border-t-indigo-400' },
]
const ZONED_KEYS = ['pantry', 'fridge', 'freezer']
// 未指定区(灰): location 不在三区(含 null)。采购回流未分区的落这里。
const UNZONED_ZONE = { key: 'unzoned', label: '未指定区域', accent: 'border-t-slate-300' }

export function InventoryPage() {
    const { call } = useApi()
    const [items, setItems] = useState([])
    const [ingredients, setIngredients] = useState({})
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [editItem, setEditItem] = useState(null)

    // 加载库存 + 食材映射。抽成 reload 供加/删后刷新(复用)
    const reload = useCallback(async () => {
        try {
            setError(null)
            const [inv, ings] = await Promise.all([
                call(api.get, '/inventory'),
                call(api.get, '/ingredients'),
            ])
            setItems(inv || [])
            const map = {}
            for (const ing of ings || []) map[ing.id] = ing.name
            setIngredients(map)
        } catch (e) {
            setError(e.message || '加载失败')
        } finally {
            setLoading(false)
        }
    }, [call])

    useEffect(() => { reload() }, [reload])

    async function handleDelete(id) {
        if (!confirm('确定删除这条库存?')) return
        try {
            await call(api.del, `/inventory/${id}`)
            await reload()
        } catch (e) {
            alert(e.message || '删除失败')
        }
    }

    if (loading) return <PageState text="加载中…" />
    if (error) return <PageState text={`出错了: ${error}`} />

    return (
        <div>
            <div className="mb-6 flex items-center justify-between">
                <h1 className="text-2xl font-bold text-slate-900">库存</h1>
                <AddInventoryDialog ingredients={ingredients} onAdded={reload} />
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {ZONES.map((zone) => (
                    <ZoneColumn
                        key={zone.key}
                        zone={zone}
                        items={items.filter((it) => it.location === zone.key)}
                        ingredients={ingredients}
                        onDelete={handleDelete}
                        onEdit={setEditItem}
                    />
                ))}
                {/* 未指定区: 只在有未分区物品时显示 */}
                {items.some((it) => !ZONED_KEYS.includes(it.location)) && (
                    <ZoneColumn
                        zone={UNZONED_ZONE}
                        items={items.filter((it) => !ZONED_KEYS.includes(it.location))}
                        ingredients={ingredients}
                        onDelete={handleDelete}
                        onEdit={setEditItem}
                    />
                )}
            </div>

            {/* 编辑弹窗 */}
            <EditInventoryDialog
                item={editItem}
                name={editItem ? (ingredients[editItem.ingredient_id] || `食材 #${editItem.ingredient_id}`) : ''}
                onClose={() => setEditItem(null)}
                onSaved={reload}
            />
        </div>
    )
}

function ZoneColumn({ zone, items, ingredients, onDelete, onEdit }) {
    const sorted = [...items].sort(
        (a, b) => sortKey(daysUntil(a.expires_at)) - sortKey(daysUntil(b.expires_at)),
    )
    return (
        <div className={`rounded-xl border-t-4 bg-white p-4 shadow-sm ${zone.accent}`}>
            <div className="mb-3 flex items-center justify-between">
                <h2 className="font-semibold text-slate-800">{zone.label}</h2>
                <span className="text-sm text-slate-400">{items.length} 项</span>
            </div>
            <div className="space-y-2">
                {sorted.length === 0 ? (
                    <p className="py-6 text-center text-sm text-slate-300">空</p>
                ) : (
                    sorted.map((it) => (
                        <InventoryCard
                            key={it.id}
                            item={it}
                            name={ingredients[it.ingredient_id]}
                            onDelete={onDelete}
                            onEdit={onEdit}
                        />
                    ))
                )}
            </div>
        </div>
    )
}

function InventoryCard({ item, name, onDelete, onEdit }) {
    const days = daysUntil(item.expires_at)
    const bg = expiryColor(days)
    const label = expiryLabel(days)   // 已过期 / 临期 / null
    return (
        <Card
            className="group cursor-pointer border-0 p-3 shadow-none transition-shadow hover:shadow-md"
            style={{ backgroundColor: bg }}
            onClick={() => onEdit(item)}
        >
            <div className="flex items-start justify-between">
                <span className="font-medium text-slate-900">
                    {name || `食材 #${item.ingredient_id}`}
                </span>
                <div className="flex items-center gap-2">
                    {label && (
                        <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium text-white ${label.variant === 'expired' ? 'bg-red-600' : 'bg-amber-500'
                                }`}
                        >
                            {label.text}
                        </span>
                    )}
                    <button
                        className="text-slate-400 opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
                        onClick={(e) => { e.stopPropagation(); onDelete(item.id) }}
                        title="删除"
                    >
                        <Trash2 className="h-4 w-4" />
                    </button>
                </div>
            </div>
            <div className="mt-1 text-xs text-slate-600">
                {item.quantity_grams}g
                {item.expires_at ? ` · 过期 ${item.expires_at}` : ' · 无过期日'}
            </div>
        </Card>
    )
}


function PageState({ text }) {
    return (
        <div className="flex h-64 items-center justify-center text-slate-400">{text}</div>
    )
}