// src/pages/InventoryPage.jsx —— 库存页(三区展示 + 渐变卡片 + 加库存 + 删除)
import { Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { AddInventoryDialog } from '@/components/inventory/AddInventoryDialog'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { daysUntil, expiryColor, sortKey } from '@/lib/expiry'

const ZONES = [
    { key: 'pantry', label: '常温', accent: 'border-t-amber-400' },
    { key: 'fridge', label: '冷藏', accent: 'border-t-sky-400' },
    { key: 'freezer', label: '冷冻', accent: 'border-t-indigo-400' },
]

export function InventoryPage() {
    const { call } = useApi()
    const [items, setItems] = useState([])
    const [ingredients, setIngredients] = useState({})
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

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
                    />
                ))}
            </div>

            <UnzonedNote items={items} />
        </div>
    )
}

function ZoneColumn({ zone, items, ingredients, onDelete }) {
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
                        />
                    ))
                )}
            </div>
        </div>
    )
}

function InventoryCard({ item, name, onDelete }) {
    const days = daysUntil(item.expires_at)
    const bg = expiryColor(days)
    return (
        <Card className="group border-0 p-3 shadow-none" style={{ backgroundColor: bg }}>
            <div className="flex items-start justify-between">
                <span className="font-medium text-slate-900">
                    {name || `食材 #${item.ingredient_id}`}
                </span>
                <div className="flex items-center gap-2">
                    {item.expiry_status === 'expiring' && (
                        <Badge variant="destructive" className="text-xs">临期</Badge>
                    )}
                    <button
                        className="text-slate-400 opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
                        onClick={() => onDelete(item.id)}
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

function UnzonedNote({ items }) {
    const unzoned = items.filter(
        (it) => !['pantry', 'fridge', 'freezer'].includes(it.location),
    )
    if (unzoned.length === 0) return null
    return (
        <p className="mt-4 text-sm text-slate-400">
            另有 {unzoned.length} 项未指定储存位置(加库存时选择区域即可归位)。
        </p>
    )
}

function PageState({ text }) {
    return (
        <div className="flex h-64 items-center justify-center text-slate-400">{text}</div>
    )
}