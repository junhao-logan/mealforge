// src/components/inventory/IngredientGroupCard.jsx
// A4: 同一储存区的同一食材合并成一张卡片。收起显示汇总; 展开按过期顺序列批次,
// 每批拆成「未预留」+「被哪个计划的哪一餐预留多少」。点餐次行 → 打开餐次明细弹窗。
import { ChevronDown, ChevronRight, Pencil, Trash2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { Card } from '@/components/ui/card'
import { daysUntil, expiryColor, expiryLabel } from '@/lib/expiry'
import { fmtAmount } from '@/lib/inventoryView'
import { mealTitle } from '@/lib/meals'

export function IngredientGroupCard({
    group, name, unit, shortfall, entriesById, expanded, onToggle,
    freeFirst, onEdit, onDelete, onOpenMeal,
}) {
    const { t } = useTranslation()
    const days = daysUntil(group.earliestExpiry)
    const label = expiryLabel(days)
    const amt = (v) => fmtAmount(v, unit)

    return (
        <Card
            className="border-0 p-3 shadow-none transition-shadow hover:shadow-md"
            style={{ backgroundColor: expiryColor(days) }}
        >
            {/* 汇总行(点击展开/收起) */}
            <button className="flex w-full items-start justify-between text-left" onClick={onToggle}>
                <div className="flex items-start gap-1">
                    {expanded
                        ? <ChevronDown className="mt-0.5 h-4 w-4 text-slate-500" />
                        : <ChevronRight className="mt-0.5 h-4 w-4 text-slate-500" />}
                    <div>
                        <div className="font-medium text-slate-900">{name}</div>
                        <div className="mt-0.5 text-xs text-slate-600">
                            {t('inventory.total', { amount: amt(group.total) })}
                            {' · '}{t('inventory.reserved', { amount: amt(group.reserved) })}
                            {' · '}{t('inventory.available', { amount: amt(group.free) })}
                        </div>
                        <div className="text-xs text-slate-500">
                            {group.earliestExpiry
                                ? t('inventory.earliestExpiry', { date: group.earliestExpiry })
                                : t('inventory.noExpiry')}
                            {group.batches.length > 1 && ` · ${t('inventory.batchCount', { count: group.batches.length })}`}
                        </div>
                    </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                    {label && (
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium text-white ${label.variant === 'expired' ? 'bg-red-600' : 'bg-amber-500'}`}>
                            {label.variant === 'expired' ? t('inventory.expired') : t('inventory.expiring')}
                        </span>
                    )}
                    {shortfall > 0 && (
                        <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                            {t('inventory.short', { amount: amt(shortfall) })}
                        </span>
                    )}
                </div>
            </button>

            {/* 展开: 按过期顺序的批次 */}
            {expanded && (
                <div className="mt-2 space-y-2 border-t border-slate-900/10 pt-2">
                    {group.batches.map((b, i) => (
                        <BatchRow
                            key={b.id} batch={b} index={i} amt={amt}
                            entriesById={entriesById} freeFirst={freeFirst}
                            onEdit={onEdit} onDelete={onDelete} onOpenMeal={onOpenMeal}
                        />
                    ))}
                </div>
            )}
        </Card>
    )
}

function BatchRow({ batch, index, amt, entriesById, freeFirst, onEdit, onDelete, onOpenMeal }) {
    const { t } = useTranslation()
    const bDays = daysUntil(batch.expires_at)
    const bLabel = expiryLabel(bDays)

    const freeLine = batch.free > 0 ? (
        <div key="free" className="rounded bg-white/60 px-2 py-1 text-xs text-slate-600">
            {t('inventory.unreserved', { amount: amt(batch.free) })}
        </div>
    ) : null
    const allocLines = batch.allocations.map((a, i) => (
        <AllocationLine
            key={`${a.entry_id}-${i}`} alloc={a} amt={amt}
            entry={entriesById[a.entry_id]} ingredientId={batch.ingredient_id}
            onOpenMeal={onOpenMeal}
        />
    ))
    const lines = freeFirst ? [freeLine, ...allocLines] : [...allocLines, freeLine]

    return (
        <div className={`rounded-md bg-white/50 p-2 ${batch.quantity <= 0 ? 'opacity-50' : ''}`}>
            <div className="flex items-center justify-between gap-2">
                <div className="text-xs font-medium text-slate-800">
                    <span className="mr-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-slate-800 text-[10px] text-white">
                        {index + 1}
                    </span>
                    {batch.expires_at
                        ? t('inventory.expiresAt', { date: batch.expires_at })
                        : t('inventory.noExpiry')}
                    {' · '}{amt(batch.quantity)}
                    {bLabel && (
                        <span className={`ml-1 rounded px-1 text-[10px] text-white ${bLabel.variant === 'expired' ? 'bg-red-600' : 'bg-amber-500'}`}>
                            {bLabel.variant === 'expired' ? t('inventory.expired') : t('inventory.expiring')}
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <button className="text-slate-400 hover:text-slate-700" onClick={() => onEdit(batch)} title={t('inventory.edit')}>
                        <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button className="text-slate-400 hover:text-red-500" onClick={() => onDelete(batch.id)} title={t('common.delete')}>
                        <Trash2 className="h-3.5 w-3.5" />
                    </button>
                </div>
            </div>
            <div className="mt-1 space-y-1">{lines}</div>
        </div>
    )
}

function AllocationLine({ alloc, amt, entry, ingredientId, onOpenMeal }) {
    const { t } = useTranslation()
    if (!entry) return null
    // 这顿饭的这种食材跨了几批
    const line = entry.lines.find((l) => l.ingredient_id === ingredientId)
    const span = line ? line.allocations.length : 1
    return (
        <button
            className="flex w-full flex-wrap items-center gap-1 rounded bg-white/80 px-2 py-1 text-left text-xs text-slate-700 hover:bg-white"
            onClick={() => onOpenMeal(entry.entry_id)}
            title={t('inventory.viewMeal')}
        >
            <span className="font-medium">{amt(alloc.amount)}</span>
            <span>→ {mealTitle(entry, t)}</span>
            {alloc.manual && (
                <span className="rounded bg-sky-100 px-1 text-[10px] font-medium text-sky-700">{t('inventory.manualBadge')}</span>
            )}
            {span > 1 && (
                <span className="rounded bg-violet-100 px-1 text-[10px] font-medium text-violet-700">{t('inventory.spansBatches', { count: span })}</span>
            )}
        </button>
    )
}
