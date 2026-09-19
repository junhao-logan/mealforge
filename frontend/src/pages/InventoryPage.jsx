// src/pages/InventoryPage.jsx —— 库存页(三区展示 + 渐变卡片 + 加库存 + 删除)
import { Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { AddInventoryDialog } from '@/components/inventory/AddInventoryDialog'
import { EditInventoryDialog } from '@/components/inventory/EditInventoryDialog'
import { Card } from '@/components/ui/card'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { daysUntil, expiryColor, expiryLabel, sortKey } from '@/lib/expiry'

// 区域: key 用于过滤/存储, labelKey 用于 i18n 显示
const ZONES = [
    { key: 'pantry', labelKey: 'inventory.zonePantry', accent: 'border-t-amber-400' },
    { key: 'fridge', labelKey: 'inventory.zoneFridge', accent: 'border-t-sky-400' },
    { key: 'freezer', labelKey: 'inventory.zoneFreezer', accent: 'border-t-indigo-400' },
]
const ZONED_KEYS = ['pantry', 'fridge', 'freezer']
// 未指定区(灰): location 不在三区(含 null)。采购回流未分区的落这里。
const UNZONED_ZONE = { key: 'unzoned', labelKey: 'inventory.zoneUnzoned', accent: 'border-t-slate-300' }

export function InventoryPage() {
    const { t } = useTranslation()
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
            setError(e.message || t('common.loadFailed'))
        } finally {
            setLoading(false)
        }
    }, [call, t])

    useEffect(() => { reload() }, [reload])

    async function handleDelete(id) {
        if (!confirm(t('inventory.confirmDelete'))) return
        try {
            await call(api.del, `/inventory/${id}`)
            await reload()
        } catch (e) {
            alert(e.message || t('common.deleteFailed'))
        }
    }

    if (loading) return <PageState text={t('common.loading')} />
    if (error) return <PageState text={t('common.errorPrefix', { msg: error })} />

    return (
        <div>
            <div className="mb-6 flex items-center justify-between">
                <h1 className="text-2xl font-bold text-slate-900">{t('inventory.title')}</h1>
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
                name={editItem ? (ingredients[editItem.ingredient_id] || t('inventory.food', { id: editItem.ingredient_id })) : ''}
                onClose={() => setEditItem(null)}
                onSaved={reload}
            />
        </div>
    )
}

function ZoneColumn({ zone, items, ingredients, onDelete, onEdit }) {
    const { t } = useTranslation()
    const sorted = [...items].sort(
        (a, b) => sortKey(daysUntil(a.expires_at)) - sortKey(daysUntil(b.expires_at)),
    )
    return (
        <div className={`rounded-xl border-t-4 bg-white p-4 shadow-sm ${zone.accent}`}>
            <div className="mb-3 flex items-center justify-between">
                <h2 className="font-semibold text-slate-800">{t(zone.labelKey)}</h2>
                <span className="text-sm text-slate-400">{t('inventory.count', { count: items.length })}</span>
            </div>
            <div className="space-y-2">
                {sorted.length === 0 ? (
                    <p className="py-6 text-center text-sm text-slate-300">{t('inventory.empty')}</p>
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
    const { t } = useTranslation()
    const days = daysUntil(item.expires_at)
    const bg = expiryColor(days)
    const label = expiryLabel(days)   // { variant } / null; 文案由 i18n 出
    return (
        <Card
            className="group cursor-pointer border-0 p-3 shadow-none transition-shadow hover:shadow-md"
            style={{ backgroundColor: bg }}
            onClick={() => onEdit(item)}
        >
            <div className="flex items-start justify-between">
                <span className="font-medium text-slate-900">
                    {name || t('inventory.food', { id: item.ingredient_id })}
                </span>
                <div className="flex items-center gap-2">
                    {label && (
                        <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium text-white ${label.variant === 'expired' ? 'bg-red-600' : 'bg-amber-500'
                                }`}
                        >
                            {label.variant === 'expired' ? t('inventory.expired') : t('inventory.expiring')}
                        </span>
                    )}
                    <button
                        className="text-slate-400 opacity-0 transition-opacity hover:text-red-500 group-hover:opacity-100"
                        onClick={(e) => { e.stopPropagation(); onDelete(item.id) }}
                        title={t('common.delete')}
                    >
                        <Trash2 className="h-4 w-4" />
                    </button>
                </div>
            </div>
            <div className="mt-1 text-xs text-slate-600">
                {item.quantity_grams}g
                {item.expires_at ? ` · ${t('inventory.expiresAt', { date: item.expires_at })}` : ` · ${t('inventory.noExpiry')}`}
            </div>
        </Card>
    )
}


function PageState({ text }) {
    return (
        <div className="flex h-64 items-center justify-center text-slate-400">{text}</div>
    )
}
