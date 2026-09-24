// src/components/inventory/MealReservationDialog.jsx
// A4: 一顿饭用到的全部食材 + 每种食材从哪几批取(可能跨储存区)。
// 每种食材可「选择批次」: 只能选还没被其他餐预留的余量, 按勾选顺序取够;
// 不够的部分自动从未过期批次补。过期批次只能手动选。
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import {
    Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { daysUntil } from '@/lib/expiry'
import { fefoCompare, fmtAmount, ZONE_LABEL_KEYS, zoneOf } from '@/lib/inventoryView'
import { mealTitle } from '@/lib/meals'

export function MealReservationDialog({ entry, reservations, items, onClose, onSaved }) {
    const { t } = useTranslation()
    return (
        <Dialog open={!!entry} onOpenChange={(o) => { if (!o) onClose?.() }}>
            <DialogContent className="max-h-[85vh] overflow-y-auto">
                {entry && (
                    <>
                        <DialogHeader>
                            <DialogTitle>{entry.recipe_name}</DialogTitle>
                        </DialogHeader>
                        <p className="-mt-2 text-sm text-slate-500">{mealTitle(entry, t)}</p>
                        <div className="space-y-3">
                            {entry.lines.map((line) => (
                                <LineBlock
                                    key={line.ingredient_id} entry={entry} line={line}
                                    reservations={reservations} items={items} onSaved={onSaved}
                                />
                            ))}
                        </div>
                    </>
                )}
            </DialogContent>
        </Dialog>
    )
}

function LineBlock({ entry, line, reservations, items, onSaved }) {
    const { t } = useTranslation()
    const { call } = useApi()
    const ing = reservations.ingredients[line.ingredient_id] || {}
    const unit = ing.unit
    const amt = (v) => fmtAmount(v, unit)
    const itemById = Object.fromEntries(items.map((it) => [it.id, it]))

    const [picking, setPicking] = useState(false)
    const [selected, setSelected] = useState([])
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState(null)

    // 候选批次: 同食材、有余量; 可选量 = 未预留 + 本餐当前从它取的
    const own = {}
    for (const a of line.allocations) own[a.batch_id] = (own[a.batch_id] || 0) + Number(a.amount)
    const candidates = reservations.batches
        .filter((b) => b.ingredient_id === line.ingredient_id && itemById[b.batch_id])
        .map((b) => ({
            ...itemById[b.batch_id],
            pickable: Number(b.free) + (own[b.batch_id] || 0),
            expired: b.expired,
        }))
        .sort(fefoCompare)

    function startPicking() {
        // 预选: 当前手选里仍可选的
        const ok = new Set(candidates.filter((c) => c.pickable > 0).map((c) => c.id))
        setSelected(line.picked_batch_ids.filter((id) => ok.has(id)))
        setError(null)
        setPicking(true)
    }

    function toggle(id) {
        setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
    }

    async function save(ids) {
        try {
            setBusy(true); setError(null)
            await call(api.put, `/meal-plans/${entry.plan_id}/entries/${entry.entry_id}/picks`, {
                body: { ingredient_id: line.ingredient_id, inventory_item_ids: ids },
            })
            setPicking(false)
            await onSaved?.()
        } catch {
            setError(t('inventory.errPick'))
        } finally {
            setBusy(false)
        }
    }

    const batchLabel = (it) => {
        const zone = t(ZONE_LABEL_KEYS[zoneOf(it.location)])
        const exp = it.expires_at ? t('inventory.expiresAt', { date: it.expires_at }) : t('inventory.noExpiry')
        return `${zone} · ${exp}`
    }

    return (
        <div className="rounded-lg border border-slate-200 p-3">
            <div className="flex items-center justify-between">
                <div>
                    <span className="font-medium text-slate-900">{ing.name || t('inventory.food', { id: line.ingredient_id })}</span>
                    <span className="ml-2 text-sm text-slate-500">{t('inventory.needs', { amount: amt(line.need) })}</span>
                </div>
                {!picking && (
                    <button className="text-sm text-sky-700 hover:underline" onClick={startPicking}>
                        {t('inventory.pickBatches')}
                    </button>
                )}
            </div>

            {/* 当前分配 */}
            {!picking && (
                <div className="mt-2 space-y-1">
                    {line.allocations.map((a, i) => {
                        const it = itemById[a.batch_id]
                        return (
                            <div key={`${a.batch_id}-${i}`} className="flex items-center gap-2 text-sm text-slate-700">
                                <span>{it ? batchLabel(it) : `#${a.batch_id}`}</span>
                                <span className="font-medium">{amt(a.amount)}</span>
                                <span className={`rounded px-1 text-[10px] font-medium ${a.manual ? 'bg-sky-100 text-sky-700' : 'bg-slate-100 text-slate-500'}`}>
                                    {a.manual ? t('inventory.manualBadge') : t('inventory.autoBadge')}
                                </span>
                            </div>
                        )
                    })}
                    {Number(line.shortfall) > 0 && (
                        <div className="text-sm font-medium text-red-600">{t('inventory.short', { amount: amt(line.shortfall) })}</div>
                    )}
                </div>
            )}

            {/* 选择批次 */}
            {picking && (
                <div className="mt-2 space-y-2">
                    <p className="text-xs text-slate-500">{t('inventory.pickHint')}</p>
                    {candidates.length === 0 && <p className="text-sm text-slate-400">{t('inventory.noBatches')}</p>}
                    {candidates.map((c) => {
                        const order = selected.indexOf(c.id)
                        const disabled = c.pickable <= 0
                        const expired = c.expired || (daysUntil(c.expires_at) ?? 1) < 0
                        return (
                            <button
                                key={c.id}
                                disabled={disabled}
                                onClick={() => toggle(c.id)}
                                className={`flex w-full items-center justify-between rounded-md border px-3 py-2 text-left text-sm ${order >= 0
                                    ? 'border-slate-900 bg-slate-50'
                                    : 'border-slate-200 hover:bg-slate-50'} disabled:cursor-not-allowed disabled:opacity-40`}
                            >
                                <span className="flex items-center gap-2">
                                    <span className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs ${order >= 0 ? 'bg-slate-900 text-white' : 'border border-slate-300 text-transparent'}`}>
                                        {order >= 0 ? order + 1 : '·'}
                                    </span>
                                    {batchLabel(c)}
                                    {expired && (
                                        <span className="rounded bg-red-600 px-1 text-[10px] text-white">{t('inventory.expired')}</span>
                                    )}
                                </span>
                                <span className="text-xs text-slate-500">
                                    {disabled ? t('inventory.reservedByOthers') : t('inventory.pickable', { amount: amt(c.pickable) })}
                                </span>
                            </button>
                        )
                    })}
                    {error && <p className="text-sm text-red-500">{error}</p>}
                    <div className="flex flex-wrap justify-end gap-2 pt-1">
                        {line.picked_batch_ids.length > 0 && (
                            <button className="rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100" disabled={busy} onClick={() => save([])}>
                                {t('inventory.resetAuto')}
                            </button>
                        )}
                        <button className="rounded-md px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100" disabled={busy} onClick={() => setPicking(false)}>
                            {t('common.cancel')}
                        </button>
                        <button
                            className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                            disabled={busy}
                            onClick={() => save(selected)}
                        >
                            {busy ? t('common.saving') : t('common.save')}
                        </button>
                    </div>
                </div>
            )}
        </div>
    )
}
