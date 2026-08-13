// src/components/dashboard/MacroCard.jsx
// 单项营养卡: 消耗/目标 + 进度条。NULL 语义: consumed=None不完整, target=None没设目标。
export function MacroCard({ label, unit, macro, accent = 'bg-slate-900' }) {
    const consumed = macro?.consumed
    const target = macro?.target
    const percent = macro?.percent

    const hasConsumed = consumed !== null && consumed !== undefined
    const hasTarget = target !== null && target !== undefined
    const pct = percent !== null && percent !== undefined ? Number(percent) : null

    return (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
            <div className="text-sm text-slate-500">{label}</div>
            <div className="mt-1 flex items-baseline gap-1">
                <span className="text-2xl font-bold text-slate-900">
                    {hasConsumed ? Number(consumed).toFixed(0) : '—'}
                </span>
                <span className="text-sm text-slate-400">
                    {hasTarget ? `/ ${Number(target).toFixed(0)} ${unit}` : unit}
                </span>
            </div>

            {/* 进度条(有目标才显示) */}
            {hasTarget && (
                <div className="mt-2">
                    <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                        <div
                            className={`h-full rounded-full ${accent}`}
                            style={{ width: `${Math.min(100, pct ?? 0)}%` }}
                        />
                    </div>
                    <div className="mt-1 text-xs text-slate-400">
                        {pct !== null ? `${pct.toFixed(0)}%` : '—'}
                    </div>
                </div>
            )}
            {!hasTarget && (
                <div className="mt-2 text-xs text-slate-300">未设目标</div>
            )}
        </div>
    )
}