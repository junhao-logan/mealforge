// src/hooks/useEntryDelete.jsx
// A5: 删除餐次的统一流程(餐计划页 / 今日概览共用)。
// · 未完成: 原生 confirm 后直接删
// · 已完成: 弹 RestockChoiceDialog, 选「只删记录」或「删除并退回库存」
// 返回 requestDelete(entry, confirmText) 和需要渲染的 dialog 元素。
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

import { RestockChoiceDialog } from '@/components/mealplan/RestockChoiceDialog'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { reportRestockLosses } from '@/lib/restock'

export function useEntryDelete(onDone) {
    const { t } = useTranslation()
    const { call } = useApi()
    const [pending, setPending] = useState(null)
    const [busy, setBusy] = useState(false)

    async function doDelete(entry, restock) {
        try {
            setBusy(true)
            const res = await call(api.del, `/meal-plans/${entry.plan_id}/entries/${entry.id}`, {
                params: restock ? { restock: true } : undefined,
            })
            setPending(null)
            reportRestockLosses(res, t)
            await onDone?.()
        } catch (e) {
            alert(e.message || t('common.deleteFailed'))
        } finally {
            setBusy(false)
        }
    }

    function requestDelete(entry, confirmText) {
        if (entry.is_completed) { setPending(entry); return }
        if (!confirm(confirmText)) return
        doDelete(entry, false)
    }

    const dialog = (
        <RestockChoiceDialog
            open={pending !== null}
            title={t('meal.deleteCompletedTitle')}
            message={t('meal.deleteCompletedMsg')}
            busy={busy}
            onChoose={(restock) => doDelete(pending, restock)}
            onCancel={() => setPending(null)}
        />
    )
    return { requestDelete, dialog }
}
